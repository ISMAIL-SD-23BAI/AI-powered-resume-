"""Tests for /history/* endpoints: list and delete with authorization."""
import pytest
from tests.helpers import register_and_login, auth_headers


class TestListHistory:
    def test_list_history_empty(self, client):
        token = register_and_login(client)
        resp = client.get("/history/", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_history_returns_own_items(self, client, cover_letter_fixture):
        resp = client.get("/history/", headers=cover_letter_fixture["headers"])
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        item = items[0]
        assert item["id"] == cover_letter_fixture["tailored"]["id"]
        assert item["has_cover_letter"] is True
        assert item["cover_letter_id"] is not None
        assert item["match_score"] == 78
        assert item["role_title"] == "Software Engineer"

    def test_list_history_does_not_include_other_users_items(self, client, cover_letter_fixture):
        token_b = register_and_login(client, "other@test.com")
        resp = client.get("/history/", headers=auth_headers(token_b))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_history_unauthenticated_returns_401(self, client):
        resp = client.get("/history/")
        assert resp.status_code == 401

    def test_list_history_has_expected_fields(self, client, tailored_resume):
        resp = client.get("/history/", headers=tailored_resume["headers"])
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        item = items[0]
        assert "id" in item
        assert "resume_filename" in item
        assert "role_title" in item
        assert "match_score" in item
        assert "has_cover_letter" in item
        assert "created_at" in item


class TestDeleteHistory:
    def test_delete_own_history_item_returns_204(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.delete(f"/history/{tid}", headers=tailored_resume["headers"])
        assert resp.status_code == 204

        # Confirm it is gone from the list
        list_resp = client.get("/history/", headers=tailored_resume["headers"])
        assert list_resp.status_code == 200
        assert all(item["id"] != tid for item in list_resp.json())

    def test_delete_other_users_history_returns_404(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        token_b = register_and_login(client, "intruder@test.com")
        resp = client.delete(f"/history/{tid}", headers=auth_headers(token_b))
        assert resp.status_code == 404

        # Original owner's item must still exist
        owner_resp = client.get("/history/", headers=tailored_resume["headers"])
        ids = [item["id"] for item in owner_resp.json()]
        assert tid in ids

    def test_delete_nonexistent_history_returns_404(self, client):
        token = register_and_login(client)
        resp = client.delete("/history/99999", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_delete_unauthenticated_returns_401(self, client, tailored_resume):
        tid = tailored_resume["tailored"]["id"]
        resp = client.delete(f"/history/{tid}")
        assert resp.status_code == 401
