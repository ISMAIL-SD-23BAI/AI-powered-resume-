"""Tests for /auth/* endpoints: signup, login, token, /me, and edge cases."""
import pytest
from tests.helpers import register_and_login, auth_headers


class TestSignup:
    def test_signup_success_returns_201_and_user(self, client):
        resp = client.post(
            "/auth/signup",
            json={"email": "new@example.com", "password": "StrongPass1!", "full_name": "Alice"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "Alice"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data  # never expose the hash

    def test_signup_duplicate_email_returns_400(self, client):
        payload = {"email": "dup@example.com", "password": "StrongPass1!"}
        client.post("/auth/signup", json=payload)
        resp = client.post("/auth/signup", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_signup_weak_password_returns_422(self, client):
        resp = client.post(
            "/auth/signup",
            json={"email": "weak@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_signup_password_too_long_returns_422(self, client):
        resp = client.post(
            "/auth/signup",
            json={"email": "long@example.com", "password": "x" * 129},
        )
        assert resp.status_code == 422

    def test_signup_invalid_email_returns_422(self, client):
        resp = client.post(
            "/auth/signup",
            json={"email": "not-an-email", "password": "StrongPass1!"},
        )
        assert resp.status_code == 422

    def test_signup_register_alias_works(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "alias@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 201

    def test_signup_optional_full_name(self, client):
        resp = client.post(
            "/auth/signup",
            json={"email": "noname@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 201
        assert resp.json()["full_name"] is None


class TestLogin:
    def test_login_json_success(self, client):
        client.post(
            "/auth/signup",
            json={"email": "login@example.com", "password": "StrongPass1!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        client.post(
            "/auth/signup",
            json={"email": "wrongpw@example.com", "password": "StrongPass1!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "wrongpw@example.com", "password": "WrongPassword!"},
        )
        assert resp.status_code == 401
        # Must not reveal whether the email exists
        assert resp.json()["detail"] == "Incorrect email or password"

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Incorrect email or password"

    def test_login_form_token_endpoint(self, client):
        """OAuth2 form endpoint used by /docs Authorize button."""
        client.post(
            "/auth/signup",
            json={"email": "form@example.com", "password": "StrongPass1!"},
        )
        resp = client.post(
            "/auth/token",
            data={"username": "form@example.com", "password": "StrongPass1!"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_empty_password_returns_422(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "blank@example.com", "password": "   "},
        )
        assert resp.status_code == 422


class TestMe:
    def test_me_returns_own_user_info(self, client):
        token = register_and_login(client, "me@example.com", "Password123!")
        resp = client.get("/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@example.com"
        assert "hashed_password" not in data
        assert "id" in data

    def test_me_unauthenticated_returns_401(self, client):
        resp = client.get("/me")
        assert resp.status_code == 401

    def test_me_invalid_token_returns_401(self, client):
        resp = client.get("/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status_code == 401

    def test_me_missing_bearer_prefix_returns_401(self, client):
        token = register_and_login(client)
        resp = client.get("/me", headers={"Authorization": token})
        assert resp.status_code == 401


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
