"""Tests for /export/* endpoints: PDF generation and authorization."""
import pytest
from tests.helpers import register_and_login, auth_headers

_PDF_MAGIC = b"%PDF"


class TestExportResume:
    def test_export_resume_returns_pdf(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.post(f"/export/resume/{tid}", headers=tailored_resume["headers"])
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == _PDF_MAGIC

    def test_export_resume_has_download_header(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.post(f"/export/resume/{tid}", headers=tailored_resume["headers"])
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert ".pdf" in resp.headers["content-disposition"]

    def test_export_resume_other_users_returns_404(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        token_b = register_and_login(client, "thief@test.com")
        resp = client.post(f"/export/resume/{tid}", headers=auth_headers(token_b))
        assert resp.status_code == 404

    def test_export_resume_nonexistent_returns_404(self, client):
        token = register_and_login(client)
        resp = client.post("/export/resume/99999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_export_resume_unauthenticated_returns_401(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.post(f"/export/resume/{tid}")
        assert resp.status_code == 401


class TestExportCoverLetter:
    def test_export_cover_letter_returns_pdf(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        resp = client.post(
            f"/export/cover-letter/{cl_id}", headers=cover_letter_fixture["headers"]
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == _PDF_MAGIC

    def test_export_cover_letter_has_download_header(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        resp = client.post(
            f"/export/cover-letter/{cl_id}", headers=cover_letter_fixture["headers"]
        )
        assert "attachment" in resp.headers["content-disposition"]
        assert ".pdf" in resp.headers["content-disposition"]

    def test_export_cover_letter_other_users_returns_404(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        token_b = register_and_login(client, "spy@test.com")
        resp = client.post(f"/export/cover-letter/{cl_id}", headers=auth_headers(token_b))
        assert resp.status_code == 404

    def test_export_cover_letter_nonexistent_returns_404(self, client):
        token = register_and_login(client)
        resp = client.post("/export/cover-letter/99999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_export_cover_letter_unauthenticated_returns_401(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        resp = client.post(f"/export/cover-letter/{cl_id}")
        assert resp.status_code == 401
