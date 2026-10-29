"""Tests for /resumes/* endpoints: upload, list, get, delete, and authorization."""
import io
import json
from unittest.mock import patch

import pytest
from tests.helpers import (
    register_and_login,
    auth_headers,
    make_mock_client,
    MOCK_STRUCTURED_RESUME,
)


def _upload(client, token, pdf_bytes, filename="resume.pdf"):
    return client.post(
        "/resumes/upload",
        files={"file": (filename, pdf_bytes, "application/pdf")},
        headers=auth_headers(token),
    )


class TestUpload:
    def test_upload_valid_pdf_returns_200(self, client, sample_pdf, mock_parse_resume):
        token = register_and_login(client)
        resp = _upload(client, token, sample_pdf)
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "resume.pdf"
        assert data["id"] is not None
        assert data["raw_text"] is not None

    def test_upload_stores_structured_json(self, client, sample_pdf, mock_parse_resume):
        token = register_and_login(client)
        resp = _upload(client, token, sample_pdf)
        assert resp.status_code == 200
        structured = resp.json()["structured_json"]
        assert isinstance(structured, dict)
        assert "skills" in structured

    def test_upload_non_pdf_extension_returns_400(self, client, sample_pdf):
        token = register_and_login(client)
        resp = client.post(
            "/resumes/upload",
            files={"file": ("resume.docx", sample_pdf, "application/octet-stream")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "pdf" in resp.json()["detail"].lower()

    def test_upload_fake_pdf_magic_bytes_returns_422(self, client):
        """A file that ends in .pdf but lacks the %PDF magic header."""
        token = register_and_login(client)
        fake_content = b"This is not a PDF file at all"
        resp = _upload(client, token, fake_content, filename="fake.pdf")
        assert resp.status_code == 422
        assert "pdf" in resp.json()["detail"].lower()

    def test_upload_too_large_returns_413(self, client):
        token = register_and_login(client)
        oversized = b"%PDF-fake" + b"x" * (5 * 1024 * 1024 + 1)
        resp = _upload(client, token, oversized)
        assert resp.status_code == 413
        assert "5 mb" in resp.json()["detail"].lower()

    def test_upload_unauthenticated_returns_401(self, client, sample_pdf):
        resp = client.post(
            "/resumes/upload",
            files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_parse_failure_gracefully_degrades(self, client, sample_pdf):
        """If Claude fails, the upload still succeeds with a parse_error field."""
        token = register_and_login(client)
        with patch(
            "services.resume_parser.get_anthropic_client",
            side_effect=Exception("Simulated AI failure"),
        ):
            resp = _upload(client, token, sample_pdf)
        assert resp.status_code == 200
        structured = resp.json()["structured_json"]
        assert "parse_error" in structured


class TestListResumes:
    def test_list_empty_returns_empty_array(self, client):
        token = register_and_login(client)
        resp = client.get("/resumes/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_own_resumes_only(self, client, sample_pdf, mock_parse_resume):
        token_a = register_and_login(client, "usera@test.com")
        token_b = register_and_login(client, "userb@test.com")

        _upload(client, token_a, sample_pdf)
        _upload(client, token_a, sample_pdf)

        resp_a = client.get("/resumes/", headers=auth_headers(token_a))
        resp_b = client.get("/resumes/", headers=auth_headers(token_b))

        assert resp_a.status_code == 200
        assert len(resp_a.json()) == 2
        assert resp_b.status_code == 200
        assert len(resp_b.json()) == 0

    def test_list_unauthenticated_returns_401(self, client):
        resp = client.get("/resumes/")
        assert resp.status_code == 401


class TestGetResume:
    def test_get_own_resume(self, client, uploaded_resume):
        resume_id = uploaded_resume["resume"]["id"]
        resp = client.get(f"/resumes/{resume_id}", headers=uploaded_resume["headers"])
        assert resp.status_code == 200
        assert resp.json()["id"] == resume_id

    def test_get_other_users_resume_returns_404(self, client, sample_pdf, mock_parse_resume):
        token_a = register_and_login(client, "owner@test.com")
        token_b = register_and_login(client, "other@test.com")

        resp_a = _upload(client, token_a, sample_pdf)
        resume_id = resp_a.json()["id"]

        resp = client.get(f"/resumes/{resume_id}", headers=auth_headers(token_b))
        assert resp.status_code == 404

    def test_get_nonexistent_resume_returns_404(self, client):
        token = register_and_login(client)
        resp = client.get("/resumes/99999", headers=auth_headers(token))
        assert resp.status_code == 404


class TestDeleteResume:
    def test_delete_own_resume_returns_204(self, client, uploaded_resume):
        resume_id = uploaded_resume["resume"]["id"]
        resp = client.delete(f"/resumes/{resume_id}", headers=uploaded_resume["headers"])
        assert resp.status_code == 204

        # Confirm it is gone
        get_resp = client.get(f"/resumes/{resume_id}", headers=uploaded_resume["headers"])
        assert get_resp.status_code == 404

    def test_delete_other_users_resume_returns_404(self, client, sample_pdf, mock_parse_resume):
        token_a = register_and_login(client, "owner2@test.com")
        token_b = register_and_login(client, "other2@test.com")

        resp_a = _upload(client, token_a, sample_pdf)
        resume_id = resp_a.json()["id"]

        resp = client.delete(f"/resumes/{resume_id}", headers=auth_headers(token_b))
        assert resp.status_code == 404

        # Confirm the original owner can still access it
        assert client.get(f"/resumes/{resume_id}", headers=auth_headers(token_a)).status_code == 200

    def test_delete_unauthenticated_returns_401(self, client, uploaded_resume):
        resume_id = uploaded_resume["resume"]["id"]
        resp = client.delete(f"/resumes/{resume_id}")
        assert resp.status_code == 401
