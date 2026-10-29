"""
Pytest configuration and shared fixtures for the AI Resume Tailor test suite.

Key design decisions:
- A StaticPool in-memory SQLite engine is used for all test DB operations so
  each test gets a completely isolated database without touching the real .db file.
- The get_db FastAPI dependency is overridden per test via dependency_overrides.
- AI (Anthropic) calls are always mocked — no real API key is needed to run tests.
- Env vars are set with setdefault so that a local .env file still works, but
  CI environments without .env also get valid values.
"""
import io
import json
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# The Windows Proactor loop's self-pipe socketpair can block in restricted
# runners; Starlette's synchronous TestClient works with the selector loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Supply mock credentials only when the caller has not provided values; app
# loading leaves these process-level test values intact.
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-minimum-32-chars-okay!!")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

# Add backend/ to path so imports like `from database import ...` work
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from database import Base, get_db  # noqa: E402 — must come after sys.path setup
from main import app  # noqa: E402

# ── Isolated test database ─────────────────────────────────────────────────────

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # all sessions share one in-memory connection
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables before/after each test for a clean slate."""
    Base.metadata.drop_all(bind=_TEST_ENGINE)
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture
def client(reset_db):
    """FastAPI TestClient with the test DB wired in."""
    app.dependency_overrides[get_db] = _override_get_db
    # main.lifespan creates tables on main.engine. Keep startup on the same
    # in-memory test engine as the overridden request dependency; otherwise
    # every test touches the developer's local SQLite database.
    with patch("main.engine", _TEST_ENGINE):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


# ── Shared PDF fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_pdf():
    """A real, pypdf-parseable PDF built with ReportLab."""
    from tests.helpers import make_test_pdf
    return make_test_pdf(
        "Software Engineer at ACME Corp with Python, FastAPI, and SQLAlchemy experience. "
        "B.Tech CSE (AI & ML) from Test University 2018-2022."
    )


# ── AI mock fixtures ───────────────────────────────────────────────────────────

from tests.helpers import (  # noqa: E402
    make_mock_client,
    MOCK_STRUCTURED_RESUME,
    MOCK_JD_REQUIREMENTS,
    MOCK_TAILORED,
    MOCK_COVER_LETTER,
)


@pytest.fixture
def mock_parse_resume():
    """Mock the Anthropic client used by services/resume_parser.py."""
    with patch(
        "services.resume_parser.get_anthropic_client",
        return_value=make_mock_client(json.dumps(MOCK_STRUCTURED_RESUME)),
    ):
        yield


@pytest.fixture
def mock_ai_tailor():
    """Mock Anthropic for the two sequential calls in services/ai_tailor.py."""
    clients = [
        make_mock_client(json.dumps(MOCK_JD_REQUIREMENTS)),  # extract_jd_requirements
        make_mock_client(json.dumps(MOCK_TAILORED)),          # tailor_resume
    ]
    with patch(
        "services.ai_tailor.get_anthropic_client",
        side_effect=clients,
    ):
        yield


@pytest.fixture
def mock_cover_letter():
    """Mock Anthropic for services/cover_letter.py."""
    with patch(
        "services.cover_letter.get_anthropic_client",
        return_value=make_mock_client(MOCK_COVER_LETTER),
    ):
        yield


# ── Composite state fixtures ───────────────────────────────────────────────────

from tests.helpers import register_and_login, auth_headers  # noqa: E402


@pytest.fixture
def uploaded_resume(client, sample_pdf, mock_parse_resume):
    """Fixture: returns {token, headers, resume} for a freshly uploaded resume."""
    token = register_and_login(client)
    hdrs = auth_headers(token)
    resp = client.post(
        "/resumes/upload",
        files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
        headers=hdrs,
    )
    assert resp.status_code == 200, resp.text
    return {"token": token, "headers": hdrs, "resume": resp.json()}


@pytest.fixture
def tailored_resume(client, uploaded_resume, mock_ai_tailor):
    """Fixture: returns {token, headers, resume, tailored} after AI tailoring."""
    resp = client.post(
        "/tailor/",
        json={
            "resume_id": uploaded_resume["resume"]["id"],
            "job_description_text": "Software Engineer role requiring Python and FastAPI. "
            * 5,
        },
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 200, resp.text
    return {**uploaded_resume, "tailored": resp.json()}


@pytest.fixture
def cover_letter_fixture(client, tailored_resume, mock_cover_letter):
    """Fixture: returns {…, cover_letter} after cover letter generation."""
    resp = client.post(
        "/cover-letter/generate",
        json={"tailored_resume_id": tailored_resume["tailored"]["id"]},
        headers=tailored_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**tailored_resume, "cover_letter": resp.json()}
