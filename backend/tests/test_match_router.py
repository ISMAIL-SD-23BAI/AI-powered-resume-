"""
API integration tests for the /match/* endpoints.

The matching engine (compute_from_structured) is mocked so tests run fast
without loading ML models. The mock returns a deterministic result dict.
"""
import json
from unittest.mock import patch, MagicMock

import pytest

from tests.helpers import register_and_login, auth_headers

# ── Mock matching engine result ────────────────────────────────────────────────

_MOCK_MATCH_RESULT = {
    "overall_score": 72,
    "required_skill_score": 80.0,
    "preferred_skill_score": 50.0,
    "experience_score": 65.0,
    "education_score": 90.0,
    "matched_requirements": [
        {"skill": "python", "match_type": "exact", "confidence": 1.0, "resume_sections": ["skills"]}
    ],
    "partial_matches": [],
    "missing_requirements": ["kubernetes"],
    "missing_preferred": ["terraform"],
    "resume_evidence": {"python": ["skills"]},
    "recommendations": ["Add kubernetes to your resume."],
    "disclaimer": "A skill marked 'not evidenced in resume' means it was not found in the uploaded resume.",
    "jd_role_title": "Backend Engineer",
}


@pytest.fixture
def mock_matching_engine():
    """Patch compute_from_structured in the router to return a canned result."""
    with patch(
        "routers.match.compute_from_structured",
        return_value=_MOCK_MATCH_RESULT,
    ):
        yield


# ── POST /match/ ───────────────────────────────────────────────────────────────

def test_match_success(client, uploaded_resume, mock_matching_engine):
    resp = client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Backend Engineer with Python and Kubernetes experience required. " * 3,
        },
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["overall_score"] == 72
    assert data["required_skill_score"] == 80.0
    assert len(data["matched_requirements"]) == 1
    assert data["matched_requirements"][0]["skill"] == "python"
    assert "kubernetes" in data["missing_requirements"]
    assert data["jd_role_title"] == "Backend Engineer"
    assert "id" in data
    assert "created_at" in data
    assert "disclaimer" in data


def test_match_requires_auth(client, uploaded_resume, mock_matching_engine):
    resp = client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Backend Engineer needing Python skills. " * 3,
        },
    )
    assert resp.status_code == 401


def test_match_nonexistent_resume(client, uploaded_resume, mock_matching_engine):
    resp = client.post(
        "/match/",
        json={
            "resume_id": 99999,
            "job_description_text": "Software Engineer with Python and FastAPI. " * 3,
        },
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_match_jd_too_short(client, uploaded_resume, mock_matching_engine):
    resp = client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "short",
        },
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_match_result_persisted(client, uploaded_resume, mock_matching_engine):
    """After POST /match/, the result must be retrievable via GET /match/{id}."""
    post_resp = client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Backend Engineer with Python and Kubernetes experience. " * 3,
        },
        headers=uploaded_resume["headers"],
    )
    assert post_resp.status_code == 201
    match_id = post_resp.json()["id"]

    get_resp = client.get(f"/match/{match_id}", headers=uploaded_resume["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == match_id
    assert get_resp.json()["overall_score"] == 72


# ── GET /match/ ────────────────────────────────────────────────────────────────

def test_list_matches_empty(client, uploaded_resume):
    resp = client.get("/match/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_matches_returns_all(client, uploaded_resume, mock_matching_engine):
    jd_text = "Backend Engineer with Python and Kubernetes experience required. " * 3

    # Run match twice
    client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )
    client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )

    resp = client.get("/match/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Summary fields
    for item in data:
        assert "id" in item
        assert "overall_score" in item
        assert "created_at" in item


def test_list_matches_requires_auth(client):
    resp = client.get("/match/")
    assert resp.status_code == 401


def test_list_matches_isolated_per_user(client, uploaded_resume, sample_pdf, mock_parse_resume, mock_matching_engine):
    """User A's matches must not appear in User B's list."""
    jd_text = "Backend Engineer with Python experience. " * 3

    # User A runs a match
    client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )

    # User B registers and checks their list
    token_b = register_and_login(client, email="b@example.com", password="password123")
    headers_b = auth_headers(token_b)
    resp = client.post(
        "/resumes/upload",
        files={"file": ("resume_b.pdf", sample_pdf, "application/pdf")},
        headers=headers_b,
    )
    assert resp.status_code == 200

    list_resp = client.get("/match/", headers=headers_b)
    assert list_resp.status_code == 200
    assert list_resp.json() == []


# ── GET /match/{id} ────────────────────────────────────────────────────────────

def test_get_match_not_found(client, uploaded_resume):
    resp = client.get("/match/99999", headers=uploaded_resume["headers"])
    assert resp.status_code == 404


def test_get_match_wrong_user_forbidden(client, uploaded_resume, mock_matching_engine):
    """User B must not be able to read User A's match result."""
    jd_text = "Backend Engineer with Python and Kubernetes experience required. " * 3

    # User A creates a match
    post_resp = client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )
    match_id = post_resp.json()["id"]

    # User B tries to access it
    token_b = register_and_login(client, email="b@example.com", password="password123")
    resp = client.get(f"/match/{match_id}", headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_get_match_requires_auth(client):
    resp = client.get("/match/1")
    assert resp.status_code == 401


# ── DELETE /match/{id} ─────────────────────────────────────────────────────────

def test_delete_match(client, uploaded_resume, mock_matching_engine):
    jd_text = "Backend Engineer with Python and Kubernetes experience required. " * 3

    post_resp = client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )
    match_id = post_resp.json()["id"]

    del_resp = client.delete(f"/match/{match_id}", headers=uploaded_resume["headers"])
    assert del_resp.status_code == 204

    # Confirm deleted
    get_resp = client.get(f"/match/{match_id}", headers=uploaded_resume["headers"])
    assert get_resp.status_code == 404


def test_delete_match_requires_auth(client):
    resp = client.delete("/match/1")
    assert resp.status_code == 401


def test_delete_match_wrong_user_forbidden(client, uploaded_resume, mock_matching_engine):
    jd_text = "Backend Engineer with Python and Kubernetes experience required. " * 3

    post_resp = client.post(
        "/match/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": jd_text},
        headers=uploaded_resume["headers"],
    )
    match_id = post_resp.json()["id"]

    token_b = register_and_login(client, email="b@example.com", password="password123")
    del_resp = client.delete(f"/match/{match_id}", headers=auth_headers(token_b))
    assert del_resp.status_code == 404

    # Original owner can still access it
    get_resp = client.get(f"/match/{match_id}", headers=uploaded_resume["headers"])
    assert get_resp.status_code == 200


# ── Response structure validation ──────────────────────────────────────────────

def test_match_response_has_all_fields(client, uploaded_resume, mock_matching_engine):
    resp = client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Backend Engineer with Python experience required. " * 3,
        },
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()

    required_fields = {
        "id", "resume_id", "overall_score", "required_skill_score",
        "preferred_skill_score", "experience_score", "education_score",
        "matched_requirements", "partial_matches", "missing_requirements",
        "missing_preferred", "resume_evidence", "recommendations",
        "disclaimer", "created_at",
    }
    missing = required_fields - set(data.keys())
    assert missing == set(), f"Response missing fields: {missing}"


def test_summary_list_fields(client, uploaded_resume, mock_matching_engine):
    """GET /match/ returns summaries with at minimum id, overall_score, created_at."""
    client.post(
        "/match/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Backend Engineer with Python experience required. " * 3,
        },
        headers=uploaded_resume["headers"],
    )
    resp = client.get("/match/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "id" in item
    assert "overall_score" in item
    assert "created_at" in item
    assert "resume_id" in item
