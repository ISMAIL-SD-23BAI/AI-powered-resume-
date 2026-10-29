"""
API integration tests for the /improve/* endpoints.

Claude (improvement engine) is mocked so no real API key is needed.
The DB is the standard in-memory SQLite from conftest.

Coverage:
  - POST /improve/ creates a session (201)
  - Requires authentication
  - 404 on non-existent resume
  - 422 on short job description
  - Session data persisted in DB
  - GET /improve/ lists sessions (empty then populated)
  - GET /improve/ is user-isolated
  - GET /improve/{id} returns full session
  - GET /improve/{id} returns 404 for wrong user
  - PATCH /improve/{id}/suggestion accepts a bullet
  - PATCH /improve/{id}/suggestion rejects a bullet
  - PATCH /improve/{id}/suggestion with custom_text
  - POST /improve/{id}/apply creates TailoredResume
  - POST /improve/{id}/apply: rejected bullets not in applied resume
  - POST /improve/{id}/apply: original resume record unchanged
  - DELETE /improve/{id} removes session
  - DELETE /improve/{id} wrong user returns 404
"""
import json
from unittest.mock import patch

import pytest

from tests.helpers import (
    register_and_login,
    auth_headers,
    MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
    make_mock_client,
)

_LONG_JD = (
    "We are looking for a Software Engineer with Python and FastAPI experience. "
    "The role involves building REST APIs, maintaining SQL databases, "
    "and collaborating with cross-functional teams. "
    "Strong Python skills are required along with experience in FastAPI."
)


@pytest.fixture
def mock_improve_engine():
    """Patch the Claude client used by improvement_engine.py."""
    mock_client = make_mock_client(json.dumps(MOCK_IMPROVEMENT_CLAUDE_OUTPUT))
    with patch(
        "services.improvement_engine.get_anthropic_client",
        return_value=mock_client,
    ):
        yield


@pytest.fixture
def session_fixture(client, uploaded_resume, mock_improve_engine):
    """Fixture: an active improvement session for the uploaded resume."""
    resp = client.post(
        "/improve/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**uploaded_resume, "session": resp.json()}


# ── POST /improve/ ─────────────────────────────────────────────────────────────

def test_create_session_success(client, uploaded_resume, mock_improve_engine):
    resp = client.post(
        "/improve/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["resume_id"] == uploaded_resume["resume"]["id"]
    assert data["status"] == "active"
    assert "session_data" in data
    assert "total_suggestions" in data
    assert "accepted_count" in data
    assert data["accepted_count"] == 0


def test_create_session_requires_auth(client, uploaded_resume, mock_improve_engine):
    resp = client.post(
        "/improve/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
    )
    assert resp.status_code == 401


def test_create_session_nonexistent_resume(client, uploaded_resume, mock_improve_engine):
    resp = client.post(
        "/improve/",
        json={"resume_id": 99999, "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_create_session_short_jd(client, uploaded_resume, mock_improve_engine):
    resp = client.post(
        "/improve/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": "Short"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_session_persisted(client, session_fixture):
    session_id = session_fixture["session"]["id"]
    get_resp = client.get(f"/improve/{session_id}", headers=session_fixture["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id


def test_create_session_has_experience_suggestions(client, session_fixture):
    data = session_fixture["session"]
    sd = data["session_data"]
    assert isinstance(sd["experience_suggestions"], list)
    assert len(sd["experience_suggestions"]) > 0


# ── GET /improve/ ──────────────────────────────────────────────────────────────

def test_list_sessions_empty(client, uploaded_resume):
    resp = client.get("/improve/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_created(client, session_fixture):
    resp = client.get("/improve/", headers=session_fixture["headers"])
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == session_fixture["session"]["id"]


def test_list_sessions_requires_auth(client, session_fixture):
    resp = client.get("/improve/")
    assert resp.status_code == 401


def test_list_sessions_user_isolated(client, session_fixture, sample_pdf, mock_improve_engine):
    # Second user
    token2 = register_and_login(client, email="user2@example.com")
    hdrs2 = auth_headers(token2)

    # Upload a resume for the second user
    up = client.post(
        "/resumes/upload",
        files={"file": ("r.pdf", sample_pdf, "application/pdf")},
        headers=hdrs2,
    )
    assert up.status_code == 200

    # Second user's session list should be empty (only user1 has a session)
    resp = client.get("/improve/", headers=hdrs2)
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /improve/{id} ─────────────────────────────────────────────────────────

def test_get_session_not_found(client, uploaded_resume):
    resp = client.get("/improve/99999", headers=uploaded_resume["headers"])
    assert resp.status_code == 404


def test_get_session_wrong_user(client, session_fixture):
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.get(
        f"/improve/{session_fixture['session']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_get_session_requires_auth(client, session_fixture):
    resp = client.get(f"/improve/{session_fixture['session']['id']}")
    assert resp.status_code == 401


# ── PATCH /improve/{id}/suggestion ────────────────────────────────────────────

def _first_bullet_coords(session_data: dict) -> dict | None:
    for job_sug in session_data.get("experience_suggestions") or []:
        for bsug in job_sug.get("bullet_suggestions") or []:
            if bsug.get("has_suggestion"):
                return {
                    "section": "experience",
                    "job_index": job_sug["job_index"],
                    "bullet_index": bsug["bullet_index"],
                }
    return None


def test_patch_accept_suggestion(client, session_fixture):
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    assert coords is not None, "No suggestion found in session"

    resp = client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={**coords, "status": "accepted"},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["accepted_count"] >= 1


def test_patch_reject_suggestion(client, session_fixture):
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    assert coords is not None

    resp = client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={**coords, "status": "rejected"},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 200
    updated = resp.json()
    # Rejected → accepted_count stays 0
    assert updated["accepted_count"] == 0


def test_patch_custom_text(client, session_fixture):
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    assert coords is not None

    resp = client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={**coords, "status": "accepted", "custom_text": "My custom edited bullet"},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 200
    # Verify custom_text stored in session_data
    sd = resp.json()["session_data"]
    ji = coords["job_index"]
    bi = coords["bullet_index"]
    for job_sug in sd["experience_suggestions"]:
        if job_sug["job_index"] == ji:
            for bsug in job_sug["bullet_suggestions"]:
                if bsug["bullet_index"] == bi:
                    assert bsug["custom_text"] == "My custom edited bullet"


def test_patch_requires_auth(client, session_fixture):
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    assert coords is not None
    resp = client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={**coords, "status": "accepted"},
    )
    assert resp.status_code == 401


def test_patch_invalid_section_422(client, session_fixture):
    resp = client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={"section": "unknown_section", "status": "accepted"},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 422


# ── POST /improve/{id}/apply ──────────────────────────────────────────────────

def test_apply_creates_tailored_resume(client, session_fixture):
    # Accept a suggestion first
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    if coords:
        client.patch(
            f"/improve/{session_fixture['session']['id']}/suggestion",
            json={**coords, "status": "accepted"},
            headers=session_fixture["headers"],
        )

    resp = client.post(
        f"/improve/{session_fixture['session']['id']}/apply",
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["resume_id"] == session_fixture["resume"]["id"]
    assert "tailored_content_json" in data


def test_apply_marks_session_applied(client, session_fixture):
    client.post(
        f"/improve/{session_fixture['session']['id']}/apply",
        headers=session_fixture["headers"],
    )
    get_resp = client.get(
        f"/improve/{session_fixture['session']['id']}",
        headers=session_fixture["headers"],
    )
    assert get_resp.json()["status"] == "applied"


def test_apply_rejected_suggestion_not_in_output(client, session_fixture):
    coords = _first_bullet_coords(session_fixture["session"]["session_data"])
    assert coords is not None

    # Reject the first suggestion
    client.patch(
        f"/improve/{session_fixture['session']['id']}/suggestion",
        json={**coords, "status": "rejected"},
        headers=session_fixture["headers"],
    )

    apply_resp = client.post(
        f"/improve/{session_fixture['session']['id']}/apply",
        headers=session_fixture["headers"],
    )
    assert apply_resp.status_code == 201

    # The applied bullet should be the ORIGINAL text
    tc = apply_resp.json()["tailored_content_json"]
    original_bullet = "Built REST APIs using Python and FastAPI"
    experience = tc.get("tailored_resume", {}).get("experience", [])
    found = any(original_bullet in b for job in experience for b in job.get("bullets", []))
    assert found, "Rejected bullet should keep original text in applied resume"


def test_apply_original_resume_unchanged(client, session_fixture):
    """The source Resume record must not be modified by apply."""
    resume_id = session_fixture["resume"]["id"]

    # Get original resume text
    orig_resp = client.get(f"/resumes/{resume_id}", headers=session_fixture["headers"])
    orig_structured = orig_resp.json()["structured_json"]

    # Accept all and apply
    for job_sug in session_fixture["session"]["session_data"].get("experience_suggestions", []):
        for bsug in job_sug.get("bullet_suggestions", []):
            if bsug.get("has_suggestion"):
                client.patch(
                    f"/improve/{session_fixture['session']['id']}/suggestion",
                    json={
                        "section": "experience",
                        "job_index": job_sug["job_index"],
                        "bullet_index": bsug["bullet_index"],
                        "status": "accepted",
                    },
                    headers=session_fixture["headers"],
                )

    client.post(
        f"/improve/{session_fixture['session']['id']}/apply",
        headers=session_fixture["headers"],
    )

    # Check original resume is untouched
    after_resp = client.get(f"/resumes/{resume_id}", headers=session_fixture["headers"])
    assert after_resp.json()["structured_json"] == orig_structured


def test_apply_requires_auth(client, session_fixture):
    resp = client.post(f"/improve/{session_fixture['session']['id']}/apply")
    assert resp.status_code == 401


# ── DELETE /improve/{id} ──────────────────────────────────────────────────────

def test_delete_session(client, session_fixture):
    session_id = session_fixture["session"]["id"]
    del_resp = client.delete(f"/improve/{session_id}", headers=session_fixture["headers"])
    assert del_resp.status_code == 204
    get_resp = client.get(f"/improve/{session_id}", headers=session_fixture["headers"])
    assert get_resp.status_code == 404


def test_delete_requires_auth(client, session_fixture):
    resp = client.delete(f"/improve/{session_fixture['session']['id']}")
    assert resp.status_code == 401


def test_delete_wrong_user(client, session_fixture):
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.delete(
        f"/improve/{session_fixture['session']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404
