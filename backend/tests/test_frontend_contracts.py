"""Static checks for browser/API contracts that do not need a browser runtime."""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_interview_auth_token_matches_login_and_signup_storage_key():
    login = (PROJECT_ROOT / "frontend" / "js" / "login.js").read_text(encoding="utf-8")
    signup = (PROJECT_ROOT / "frontend" / "js" / "signup.js").read_text(encoding="utf-8")
    interview = (PROJECT_ROOT / "frontend" / "js" / "interview.js").read_text(encoding="utf-8")

    assert 'localStorage.setItem("token", data.access_token)' in login
    assert 'localStorage.setItem("token", loginData.access_token)' in signup
    assert 'localStorage.getItem("token")' in interview
    assert 'localStorage.removeItem("token")' in interview
    assert 'localStorage.getItem("access_token")' not in interview
    assert 'localStorage.removeItem("access_token")' not in interview
