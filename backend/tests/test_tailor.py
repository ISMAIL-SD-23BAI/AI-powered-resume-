"""Tests for /tailor/* endpoints: create, list, get, and authorization."""
import json
from unittest.mock import patch

import pytest
from tests.helpers import (
    register_and_login,
    auth_headers,
    make_mock_client,
    MOCK_JD_REQUIREMENTS,
    MOCK_TAILORED,
    MOCK_STRUCTURED_RESUME,
)

_VALID_JD = "Software Engineer role requiring Python and FastAPI skills for backend development. " * 3


class TestCreateTailored:
    def test_create_tailored_resume_success(self, client, uploaded_resume, mock_ai_tailor):
        resp = client.post(
            "/tailor/",
            json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _VALID_JD},
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["resume_id"] == uploaded_resume["resume"]["id"]

    def test_create_stores_tailored_content(self, client, uploaded_resume, mock_ai_tailor):
        resp = client.post(
            "/tailor/",
            json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _VALID_JD},
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 200
        tc = resp.json()["tailored_content_json"]
        assert isinstance(tc, dict)
        assert "tailored_resume" in tc
        assert "match_score" in tc
        assert "matched_skills" in tc
        assert "missing_skills" in tc

    def test_create_wrong_resume_id_returns_404(self, client, uploaded_resume, mock_ai_tailor):
        resp = client.post(
            "/tailor/",
            json={"resume_id": 99999, "job_description_text": _VALID_JD},
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 404

    def test_create_other_users_resume_returns_404(self, client, sample_pdf):
        from tests.conftest import _override_get_db
        from unittest.mock import patch as _patch
        import json

        # User A uploads a resume
        with _patch(
            "services.resume_parser.get_anthropic_client",
            return_value=make_mock_client(json.dumps(MOCK_STRUCTURED_RESUME)),
        ):
            token_a = register_and_login(client, "ownera@test.com")
            from tests.helpers import auth_headers as ah
            resp_a = client.post(
                "/resumes/upload",
                files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
                headers=ah(token_a),
            )
        resume_id = resp_a.json()["id"]

        # User B tries to tailor user A's resume
        token_b = register_and_login(client, "otherb@test.com")
        clients = [
            make_mock_client(json.dumps(MOCK_JD_REQUIREMENTS)),
            make_mock_client(json.dumps(MOCK_TAILORED)),
        ]
        with _patch("services.ai_tailor.get_anthropic_client", side_effect=clients):
            resp = client.post(
                "/tailor/",
                json={"resume_id": resume_id, "job_description_text": _VALID_JD},
                headers=ah(token_b),
            )
        assert resp.status_code == 404

    def test_create_unauthenticated_returns_401(self, client, uploaded_resume):
        resp = client.post(
            "/tailor/",
            json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _VALID_JD},
        )
        assert resp.status_code == 401

    def test_create_jd_too_short_returns_422(self, client, uploaded_resume):
        resp = client.post(
            "/tailor/",
            json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": "short"},
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 422

    def test_create_jd_too_long_returns_422(self, client, uploaded_resume):
        resp = client.post(
            "/tailor/",
            json={
                "resume_id": uploaded_resume["resume"]["id"],
                "job_description_text": "x" * 15_001,
            },
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 422

    def test_create_invalid_resume_id_returns_422(self, client, uploaded_resume):
        resp = client.post(
            "/tailor/",
            json={"resume_id": -1, "job_description_text": _VALID_JD},
            headers=uploaded_resume["headers"],
        )
        assert resp.status_code == 422


class TestListTailored:
    def test_list_tailored_returns_own_records(self, client, tailored_resume, mock_ai_tailor):
        resp = client.get("/tailor/", headers=tailored_resume["headers"])
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        ids = [item["id"] for item in items]
        assert tailored_resume["tailored"]["id"] in ids

    def test_list_tailored_unauthenticated_returns_401(self, client):
        resp = client.get("/tailor/")
        assert resp.status_code == 401

    def test_list_tailored_empty_returns_empty_array(self, client):
        token = register_and_login(client, "empty@test.com")
        resp = client.get("/tailor/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_does_not_return_other_users_records(self, client, tailored_resume):
        token_b = register_and_login(client, "spy@test.com")
        resp = client.get("/tailor/", headers=auth_headers(token_b))
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetTailored:
    def test_get_own_tailored_resume(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.get(f"/tailor/{tid}", headers=tailored_resume["headers"])
        assert resp.status_code == 200
        assert resp.json()["id"] == tid

    def test_get_other_users_tailored_returns_404(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        token_b = register_and_login(client, "other@test.com")
        resp = client.get(f"/tailor/{tid}", headers=auth_headers(token_b))
        assert resp.status_code == 404

    def test_get_nonexistent_tailored_returns_404(self, client):
        token = register_and_login(client)
        resp = client.get("/tailor/99999", headers=auth_headers(token))
        assert resp.status_code == 404
