"""Tests for /cover-letter/* endpoints: generate, update, fetch, and authorization."""
import pytest
from tests.helpers import register_and_login, auth_headers, MOCK_COVER_LETTER


class TestGenerateCoverLetter:
    def test_generate_success_returns_201(self, client, tailored_resume, mock_cover_letter):
        resp = client.post(
            "/cover-letter/generate",
            json={"tailored_resume_id": tailored_resume["tailored"]["id"]},
            headers=tailored_resume["headers"],
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["content"] == MOCK_COVER_LETTER
        assert data["tailored_resume_id"] == tailored_resume["tailored"]["id"]

    def test_generate_wrong_tailored_id_returns_404(self, client, tailored_resume, mock_cover_letter):
        resp = client.post(
            "/cover-letter/generate",
            json={"tailored_resume_id": 99999},
            headers=tailored_resume["headers"],
        )
        assert resp.status_code == 404

    def test_generate_other_users_tailored_returns_404(self, client, tailored_resume, mock_cover_letter):
        tid = tailored_resume["tailored"]["id"]
        token_b = register_and_login(client, "spy@test.com")
        resp = client.post(
            "/cover-letter/generate",
            json={"tailored_resume_id": tid},
            headers=auth_headers(token_b),
        )
        assert resp.status_code == 404

    def test_generate_unauthenticated_returns_401(self, client, tailored_resume):
        resp = client.post(
            "/cover-letter/generate",
            json={"tailored_resume_id": tailored_resume["tailored"]["id"]},
        )
        assert resp.status_code == 401

    def test_generate_invalid_id_returns_422(self, client, tailored_resume, mock_cover_letter):
        resp = client.post(
            "/cover-letter/generate",
            json={"tailored_resume_id": -1},
            headers=tailored_resume["headers"],
        )
        assert resp.status_code == 422


class TestUpdateCoverLetter:
    def test_update_success(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        new_content = "Updated cover letter content that is longer than 20 characters."
        resp = client.put(
            f"/cover-letter/{cl_id}",
            json={"content": new_content},
            headers=cover_letter_fixture["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == new_content

    def test_update_other_users_cover_letter_returns_404(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        token_b = register_and_login(client, "thief@test.com")
        resp = client.put(
            f"/cover-letter/{cl_id}",
            json={"content": "Stolen content that is at least 20 chars long."},
            headers=auth_headers(token_b),
        )
        assert resp.status_code == 404

    def test_update_content_too_short_returns_422(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        resp = client.put(
            f"/cover-letter/{cl_id}",
            json={"content": "Too short"},
            headers=cover_letter_fixture["headers"],
        )
        assert resp.status_code == 422

    def test_update_content_too_long_returns_422(self, client, cover_letter_fixture):
        cl_id = cover_letter_fixture["cover_letter"]["id"]
        resp = client.put(
            f"/cover-letter/{cl_id}",
            json={"content": "x" * 10_001},
            headers=cover_letter_fixture["headers"],
        )
        assert resp.status_code == 422


class TestFetchCoverLetter:
    def test_fetch_for_tailored_returns_latest(self, client, cover_letter_fixture):
        tid = cover_letter_fixture["tailored"]["id"]
        resp = client.get(
            f"/cover-letter/for/{tid}",
            headers=cover_letter_fixture["headers"],
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == MOCK_COVER_LETTER

    def test_fetch_nonexistent_returns_404(self, client):
        token = register_and_login(client)
        resp = client.get("/cover-letter/for/99999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_fetch_other_users_returns_404(self, client, cover_letter_fixture):
        tid = cover_letter_fixture["tailored"]["id"]
        token_b = register_and_login(client, "peeper@test.com")
        resp = client.get(f"/cover-letter/for/{tid}", headers=auth_headers(token_b))
        assert resp.status_code == 404
