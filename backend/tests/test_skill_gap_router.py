"""
API integration tests for the /skill-gap/* endpoints.

Both the matching engine and Claude roadmap generator are mocked —
no real API key or ML model is needed.

Coverage
────────
  POST /skill-gap/
  - 201 on success
  - Requires authentication
  - 404 for non-existent resume
  - 422 for short job description
  - Session persisted in DB
  - skill_classifications present in response
  - disclaimer present in response
  - roadmap_items present when gaps exist

  GET /skill-gap/
  - Empty list before creation
  - Returns created roadmap
  - Requires auth
  - User-isolated

  GET /skill-gap/{id}
  - 200 for own roadmap
  - 404 for wrong user
  - Requires auth

  PATCH /skill-gap/{id}/item/{idx}
  - Updates item status to "in_progress"
  - Updates item status to "completed"
  - 422 for invalid status value
  - 404 for invalid item index
  - Requires auth

  DELETE /skill-gap/{id}
  - 204 on success
  - Subsequent GET returns 404
  - Requires auth
  - 404 for wrong user
"""
import json
from unittest.mock import patch

import pytest

from tests.helpers import (
    register_and_login,
    auth_headers,
    MOCK_MATCH_FOR_GAP,
    MOCK_ROADMAP_CLAUDE_OUTPUT,
    make_mock_client,
)

_LONG_JD = (
    "We are looking for a Backend Engineer with Python and Kubernetes experience. "
    "The role involves building REST APIs with FastAPI, containerising services "
    "with Docker, and deploying via Kubernetes and CI/CD pipelines. "
    "Experience with Terraform is preferred."
)


@pytest.fixture
def mock_matching():
    """Patch compute_from_structured so no ML model is loaded."""
    with patch(
        "routers.skill_gap.compute_from_structured",
        return_value=MOCK_MATCH_FOR_GAP,
    ):
        yield


@pytest.fixture
def mock_roadmap_gen():
    """Patch generate_roadmap (the Claude call) in the router module."""
    # Assign item_index since the router does it after calling generate_roadmap
    items = []
    for idx, item in enumerate(MOCK_ROADMAP_CLAUDE_OUTPUT):
        items.append({**item, "item_index": idx, "status": "not_started"})

    with patch(
        "routers.skill_gap.generate_roadmap",
        return_value=items,
    ):
        yield


@pytest.fixture
def roadmap_fixture(client, uploaded_resume, mock_matching, mock_roadmap_gen):
    """Fixture: a created LearningRoadmap."""
    resp = client.post(
        "/skill-gap/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**uploaded_resume, "roadmap": resp.json()}


# ── POST /skill-gap/ ───────────────────────────────────────────────────────────

def test_create_roadmap_success(client, uploaded_resume, mock_matching, mock_roadmap_gen):
    resp = client.post(
        "/skill-gap/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["resume_id"] == uploaded_resume["resume"]["id"]
    assert "skill_classifications" in data
    assert "roadmap_items" in data
    assert "disclaimer" in data
    assert "overall_score" in data


def test_create_roadmap_requires_auth(client, uploaded_resume, mock_matching, mock_roadmap_gen):
    resp = client.post(
        "/skill-gap/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _LONG_JD},
    )
    assert resp.status_code == 401


def test_create_roadmap_nonexistent_resume(client, uploaded_resume, mock_matching, mock_roadmap_gen):
    resp = client.post(
        "/skill-gap/",
        json={"resume_id": 99999, "job_description_text": _LONG_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_create_roadmap_short_jd(client, uploaded_resume, mock_matching, mock_roadmap_gen):
    resp = client.post(
        "/skill-gap/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": "Too short"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_roadmap_persisted(client, roadmap_fixture):
    roadmap_id = roadmap_fixture["roadmap"]["id"]
    get_resp = client.get(f"/skill-gap/{roadmap_id}", headers=roadmap_fixture["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == roadmap_id


def test_roadmap_has_skill_classifications(client, roadmap_fixture):
    classifications = roadmap_fixture["roadmap"]["skill_classifications"]
    assert isinstance(classifications, list)
    assert len(classifications) > 0
    # Each entry has required fields
    for c in classifications:
        assert "skill" in c
        assert "classification" in c
        assert c["classification"] in (
            "demonstrated", "partially_demonstrated",
            "requires_verification", "not_found",
        )


def test_roadmap_has_disclaimer(client, roadmap_fixture):
    disclaimer = roadmap_fixture["roadmap"]["disclaimer"]
    assert isinstance(disclaimer, str)
    assert len(disclaimer) > 20
    # Must reference document, not ability
    assert "resume" in disclaimer.lower() or "document" in disclaimer.lower()


def test_roadmap_has_roadmap_items(client, roadmap_fixture):
    items = roadmap_fixture["roadmap"]["roadmap_items"]
    assert isinstance(items, list)
    assert len(items) > 0
    for item in items:
        assert "skill" in item
        assert "why_it_matters" in item
        assert "learning_sequence" in item
        assert "practical_project" in item
        assert "status" in item
        assert "item_index" in item


def test_roadmap_not_found_classifications_present(client, roadmap_fixture):
    classifications = roadmap_fixture["roadmap"]["skill_classifications"]
    not_found = [c for c in classifications if c["classification"] == "not_found"]
    # MOCK_MATCH_FOR_GAP has 3 missing skills (kubernetes, ci/cd, terraform)
    assert len(not_found) >= 1


def test_not_found_skill_note_references_document(client, roadmap_fixture):
    classifications = roadmap_fixture["roadmap"]["skill_classifications"]
    not_found = [c for c in classifications if c["classification"] == "not_found"]
    for c in not_found:
        note = (c.get("notes") or "").lower()
        assert "resume" in note or "document" in note


# ── GET /skill-gap/ ────────────────────────────────────────────────────────────

def test_list_roadmaps_empty(client, uploaded_resume):
    resp = client.get("/skill-gap/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_roadmaps_returns_created(client, roadmap_fixture):
    resp = client.get("/skill-gap/", headers=roadmap_fixture["headers"])
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == roadmap_fixture["roadmap"]["id"]


def test_list_roadmaps_requires_auth(client, roadmap_fixture):
    resp = client.get("/skill-gap/")
    assert resp.status_code == 401


def test_list_roadmaps_user_isolated(client, roadmap_fixture, sample_pdf):
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.get("/skill-gap/", headers=auth_headers(token2))
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_summary_has_counts(client, roadmap_fixture):
    resp = client.get("/skill-gap/", headers=roadmap_fixture["headers"])
    summary = resp.json()[0]
    assert "gap_count" in summary
    assert "total_roadmap_items" in summary
    assert "completed_count" in summary
    assert summary["gap_count"] >= 0


# ── GET /skill-gap/{id} ────────────────────────────────────────────────────────

def test_get_roadmap_not_found(client, uploaded_resume):
    resp = client.get("/skill-gap/99999", headers=uploaded_resume["headers"])
    assert resp.status_code == 404


def test_get_roadmap_wrong_user(client, roadmap_fixture):
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.get(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_get_roadmap_requires_auth(client, roadmap_fixture):
    resp = client.get(f"/skill-gap/{roadmap_fixture['roadmap']['id']}")
    assert resp.status_code == 401


# ── PATCH /skill-gap/{id}/item/{idx} ──────────────────────────────────────────

def _first_item_index(roadmap: dict) -> int:
    items = roadmap.get("roadmap_items") or []
    assert items, "No roadmap items to test against"
    return items[0]["item_index"]


def test_patch_item_to_in_progress(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "in_progress"},
        headers=roadmap_fixture["headers"],
    )
    assert resp.status_code == 200
    updated_items = resp.json()["roadmap_items"]
    item = next(i for i in updated_items if i["item_index"] == idx)
    assert item["status"] == "in_progress"


def test_patch_item_to_completed(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "completed"},
        headers=roadmap_fixture["headers"],
    )
    assert resp.status_code == 200
    updated_items = resp.json()["roadmap_items"]
    item = next(i for i in updated_items if i["item_index"] == idx)
    assert item["status"] == "completed"


def test_patch_item_updates_completed_count(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "completed"},
        headers=roadmap_fixture["headers"],
    )
    # List summary should reflect completed count
    list_resp = client.get("/skill-gap/", headers=roadmap_fixture["headers"])
    summary = list_resp.json()[0]
    assert summary["completed_count"] >= 1


def test_patch_item_invalid_status(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "finished"},  # not a valid status
        headers=roadmap_fixture["headers"],
    )
    assert resp.status_code == 422


def test_patch_item_out_of_bounds(client, roadmap_fixture):
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/9999",
        json={"status": "completed"},
        headers=roadmap_fixture["headers"],
    )
    assert resp.status_code == 404


def test_patch_item_requires_auth(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "completed"},
    )
    assert resp.status_code == 401


def test_patch_item_wrong_user(client, roadmap_fixture):
    idx = _first_item_index(roadmap_fixture["roadmap"])
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.patch(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}/item/{idx}",
        json={"status": "completed"},
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


# ── DELETE /skill-gap/{id} ─────────────────────────────────────────────────────

def test_delete_roadmap(client, roadmap_fixture):
    roadmap_id = roadmap_fixture["roadmap"]["id"]
    del_resp = client.delete(f"/skill-gap/{roadmap_id}", headers=roadmap_fixture["headers"])
    assert del_resp.status_code == 204
    get_resp = client.get(f"/skill-gap/{roadmap_id}", headers=roadmap_fixture["headers"])
    assert get_resp.status_code == 404


def test_delete_requires_auth(client, roadmap_fixture):
    resp = client.delete(f"/skill-gap/{roadmap_fixture['roadmap']['id']}")
    assert resp.status_code == 401


def test_delete_wrong_user(client, roadmap_fixture):
    token2 = register_and_login(client, email="user2@example.com")
    resp = client.delete(
        f"/skill-gap/{roadmap_fixture['roadmap']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404
