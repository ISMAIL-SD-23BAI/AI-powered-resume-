"""
API integration tests for /tracker/* endpoints.

No LLM calls needed — tracker is pure CRUD.

Coverage
────────
  POST /tracker/
  - 201 on success (minimal fields)
  - 201 with all optional fields
  - Requires auth
  - 422 missing company_name
  - 422 missing job_title
  - 422 invalid status
  - 422 invalid URL (missing scheme)
  - 404 when resume_id belongs to another user

  GET /tracker/stats
  - empty stats before creation
  - counts correct after creation
  - requires auth

  GET /tracker/
  - empty before creation
  - returns created application
  - status filter works
  - search filter works (company name)
  - search filter works (job title)
  - user isolated (other user sees nothing)
  - requires auth

  GET /tracker/{id}
  - 200 for own application
  - 404 for wrong user
  - requires auth

  PATCH /tracker/{id}
  - update status
  - update multiple fields
  - 422 invalid status value
  - 404 wrong user
  - requires auth

  DELETE /tracker/{id}
  - 204 on success
  - subsequent GET returns 404
  - 404 wrong user
  - requires auth
"""
import pytest

from tests.helpers import register_and_login, auth_headers

_VALID_APP = {
    "company_name": "Acme Corp",
    "job_title": "Backend Engineer",
}

_FULL_APP = {
    "company_name": "Globex Inc",
    "job_title": "Senior Python Developer",
    "job_description": "We need a Python engineer with FastAPI experience. " * 3,
    "job_url": "https://jobs.globex.example/123",
    "status": "applied",
    "notes": "Applied via referral from Jane.",
}


@pytest.fixture
def app_fixture(client, uploaded_resume):
    """A created job application owned by the uploaded_resume user."""
    resp = client.post(
        "/tracker/",
        json=_VALID_APP,
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**uploaded_resume, "app": resp.json()}


# ── POST /tracker/ ─────────────────────────────────────────────────────────────

def test_create_minimal(client, uploaded_resume):
    resp = client.post("/tracker/", json=_VALID_APP, headers=uploaded_resume["headers"])
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["company_name"] == "Acme Corp"
    assert data["job_title"] == "Backend Engineer"
    assert data["status"] == "saved"
    assert "id" in data
    assert "created_at" in data


def test_create_full(client, uploaded_resume):
    resp = client.post("/tracker/", json=_FULL_APP, headers=uploaded_resume["headers"])
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "applied"
    assert data["job_url"] == "https://jobs.globex.example/123"
    assert data["notes"] == "Applied via referral from Jane."


def test_create_requires_auth(client):
    resp = client.post("/tracker/", json=_VALID_APP)
    assert resp.status_code == 401


def test_create_missing_company(client, uploaded_resume):
    resp = client.post(
        "/tracker/",
        json={"job_title": "Engineer"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_missing_job_title(client, uploaded_resume):
    resp = client.post(
        "/tracker/",
        json={"company_name": "Acme"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_invalid_status(client, uploaded_resume):
    resp = client.post(
        "/tracker/",
        json={**_VALID_APP, "status": "pending"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_invalid_url_no_scheme(client, uploaded_resume):
    resp = client.post(
        "/tracker/",
        json={**_VALID_APP, "job_url": "jobs.example.com/123"},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_with_valid_resume(client, uploaded_resume):
    resp = client.post(
        "/tracker/",
        json={**_VALID_APP, "resume_id": uploaded_resume["resume"]["id"]},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["resume_id"] == uploaded_resume["resume"]["id"]


def test_create_wrong_resume_id(client, uploaded_resume, sample_pdf, mock_parse_resume):
    """resume_id belonging to a different user returns 404."""
    token2 = register_and_login(client, email="other@example.com")
    resp2 = client.post(
        "/resumes/upload",
        files={"file": ("r.pdf", sample_pdf, "application/pdf")},
        headers=auth_headers(token2),
    )
    other_resume_id = resp2.json()["id"]

    resp = client.post(
        "/tracker/",
        json={**_VALID_APP, "resume_id": other_resume_id},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


# ── GET /tracker/stats ────────────────────────────────────────────────────────

def test_stats_empty(client, uploaded_resume):
    resp = client.get("/tracker/stats", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["saved"] == 0
    assert data["active"] == 0
    assert data["interviews"] == 0
    assert data["offers"] == 0
    assert data["rejected"] == 0


def test_stats_counts(client, uploaded_resume):
    hdrs = uploaded_resume["headers"]
    for payload in [
        {**_VALID_APP, "status": "saved"},
        {**_VALID_APP, "status": "applied"},
        {**_VALID_APP, "status": "interview"},
        {**_VALID_APP, "status": "offer"},
        {**_VALID_APP, "status": "rejected"},
    ]:
        client.post("/tracker/", json=payload, headers=hdrs)

    resp = client.get("/tracker/stats", headers=hdrs)
    data = resp.json()
    assert data["total"] == 5
    assert data["saved"] == 1
    assert data["active"] == 2      # applied + interview
    assert data["interviews"] == 1
    assert data["offers"] == 1
    assert data["rejected"] == 1


def test_stats_requires_auth(client):
    resp = client.get("/tracker/stats")
    assert resp.status_code == 401


# ── GET /tracker/ ─────────────────────────────────────────────────────────────

def test_list_empty(client, uploaded_resume):
    resp = client.get("/tracker/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created(client, app_fixture):
    resp = client.get("/tracker/", headers=app_fixture["headers"])
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == app_fixture["app"]["id"]


def test_list_status_filter(client, uploaded_resume):
    hdrs = uploaded_resume["headers"]
    client.post("/tracker/", json={**_VALID_APP, "status": "saved"},    headers=hdrs)
    client.post("/tracker/", json={**_VALID_APP, "status": "applied"},  headers=hdrs)
    client.post("/tracker/", json={**_VALID_APP, "status": "rejected"}, headers=hdrs)

    resp = client.get("/tracker/?status=applied", headers=hdrs)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["status"] == "applied"


def test_list_invalid_status_filter(client, uploaded_resume):
    resp = client.get("/tracker/?status=bogus", headers=uploaded_resume["headers"])
    assert resp.status_code == 422


def test_list_search_company(client, uploaded_resume):
    hdrs = uploaded_resume["headers"]
    client.post("/tracker/", json={"company_name": "Google", "job_title": "SWE"},  headers=hdrs)
    client.post("/tracker/", json={"company_name": "Amazon", "job_title": "SDE"},  headers=hdrs)

    resp = client.get("/tracker/?search=google", headers=hdrs)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["company_name"] == "Google"


def test_list_search_title(client, uploaded_resume):
    hdrs = uploaded_resume["headers"]
    client.post("/tracker/", json={"company_name": "ACME", "job_title": "ML Engineer"},    headers=hdrs)
    client.post("/tracker/", json={"company_name": "ACME", "job_title": "Data Scientist"}, headers=hdrs)

    resp = client.get("/tracker/?search=ml+engineer", headers=hdrs)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_user_isolated(client, app_fixture):
    token2 = register_and_login(client, email="other2@example.com")
    resp = client.get("/tracker/", headers=auth_headers(token2))
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_requires_auth(client):
    resp = client.get("/tracker/")
    assert resp.status_code == 401


# ── GET /tracker/{id} ─────────────────────────────────────────────────────────

def test_get_own(client, app_fixture):
    resp = client.get(f"/tracker/{app_fixture['app']['id']}", headers=app_fixture["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == app_fixture["app"]["id"]


def test_get_wrong_user(client, app_fixture):
    token2 = register_and_login(client, email="stranger@example.com")
    resp = client.get(
        f"/tracker/{app_fixture['app']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_get_requires_auth(client, app_fixture):
    resp = client.get(f"/tracker/{app_fixture['app']['id']}")
    assert resp.status_code == 401


# ── PATCH /tracker/{id} ───────────────────────────────────────────────────────

def test_patch_status(client, app_fixture):
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"status": "interview"},
        headers=app_fixture["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "interview"


def test_patch_multiple_fields(client, app_fixture):
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"company_name": "NewCo", "notes": "Updated notes."},
        headers=app_fixture["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["company_name"] == "NewCo"
    assert data["notes"] == "Updated notes."


def test_patch_invalid_status(client, app_fixture):
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"status": "ghosted"},
        headers=app_fixture["headers"],
    )
    assert resp.status_code == 422


def test_patch_wrong_user(client, app_fixture):
    token2 = register_and_login(client, email="patch_stranger@example.com")
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"status": "offer"},
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_patch_requires_auth(client, app_fixture):
    resp = client.patch(f"/tracker/{app_fixture['app']['id']}", json={"status": "offer"})
    assert resp.status_code == 401


def test_patch_with_url(client, app_fixture):
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"job_url": "https://new-url.example.com/job"},
        headers=app_fixture["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["job_url"] == "https://new-url.example.com/job"


def test_patch_invalid_url(client, app_fixture):
    resp = client.patch(
        f"/tracker/{app_fixture['app']['id']}",
        json={"job_url": "not-a-url"},
        headers=app_fixture["headers"],
    )
    assert resp.status_code == 422


# ── DELETE /tracker/{id} ──────────────────────────────────────────────────────

def test_delete_success(client, app_fixture):
    app_id = app_fixture["app"]["id"]
    del_resp = client.delete(f"/tracker/{app_id}", headers=app_fixture["headers"])
    assert del_resp.status_code == 204

    get_resp = client.get(f"/tracker/{app_id}", headers=app_fixture["headers"])
    assert get_resp.status_code == 404


def test_delete_wrong_user(client, app_fixture):
    token2 = register_and_login(client, email="del_stranger@example.com")
    resp = client.delete(
        f"/tracker/{app_fixture['app']['id']}",
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_delete_requires_auth(client, app_fixture):
    resp = client.delete(f"/tracker/{app_fixture['app']['id']}")
    assert resp.status_code == 401
