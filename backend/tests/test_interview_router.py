"""
API integration tests for /interview/* endpoints.

Coverage
────────
  POST /interview/
  - 201 on success
  - requires auth
  - 404 unknown resume_id
  - 404 resume owned by other user
  - 422 jd too short
  - 422 resume not parsed (no structured_json)
  - 502 on AI error

  GET /interview/
  - empty before creation
  - returns created session
  - user isolated
  - requires auth

  GET /interview/{session_id}
  - 200 for own session
  - 404 wrong user
  - requires auth

  DELETE /interview/{session_id}
  - 204 on success
  - subsequent GET returns 404
  - 404 wrong user
  - requires auth

  POST /interview/{session_id}/answer
  - 201 on success with feedback
  - answer saved even when evaluation fails
  - 404 unknown session
  - 404 wrong user
  - 422 question_index out of range
  - 422 answer too short
  - requires auth

  GET /interview/{session_id}/answers
  - empty before submission
  - returns submitted answer
  - 404 wrong user
  - requires auth

  GET /interview/{session_id}/question/{q_idx}
  - 200 with attempts list
  - multiple attempts returned
  - 404 q_idx out of range
  - 404 wrong user
  - requires auth
"""
import json
import pytest
from unittest.mock import patch

from tests.helpers import (
    MOCK_INTERVIEW_QUESTIONS_OUTPUT,
    MOCK_INTERVIEW_FEEDBACK_OUTPUT,
    MOCK_STRUCTURED_RESUME,
    register_and_login,
    auth_headers,
    make_mock_client,
)

_JD_TEXT = (
    "We are looking for a Python Software Engineer with experience in FastAPI and REST APIs. "
    "Responsibilities include building microservices, writing tests, and maintaining SQL databases. "
    "Required: Python, FastAPI, SQLAlchemy. Preferred: Docker, Kubernetes."
)

_SHORT_JD = "Too short."

_ANSWER_TEXT = "I used FastAPI with Pydantic models and dependency injection to build production-grade REST APIs."


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_generate():
    with patch(
        "routers.interview.generate_questions",
        return_value=MOCK_INTERVIEW_QUESTIONS_OUTPUT,
    ):
        yield


@pytest.fixture
def mock_evaluate():
    with patch(
        "routers.interview.evaluate_answer",
        return_value=MOCK_INTERVIEW_FEEDBACK_OUTPUT,
    ):
        yield


@pytest.fixture
def session_fixture(client, uploaded_resume, mock_generate):
    """A created interview session owned by uploaded_resume user."""
    resp = client.post(
        "/interview/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _JD_TEXT},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**uploaded_resume, "session": resp.json()}


@pytest.fixture
def answered_fixture(client, session_fixture, mock_evaluate):
    """A session with one submitted answer."""
    resp = client.post(
        f"/interview/{session_fixture['session']['id']}/answer",
        json={"question_index": 0, "user_answer": _ANSWER_TEXT},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 201, resp.text
    return {**session_fixture, "answer": resp.json()}


# ── POST /interview/ ───────────────────────────────────────────────────────────

def test_create_session_success(client, uploaded_resume, mock_generate):
    resp = client.post(
        "/interview/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _JD_TEXT},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["resume_id"] == uploaded_resume["resume"]["id"]
    assert data["question_count"] == len(MOCK_INTERVIEW_QUESTIONS_OUTPUT)
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) == data["question_count"]
    assert "id" in data
    assert "created_at" in data


def test_create_session_requires_auth(client, mock_generate):
    resp = client.post(
        "/interview/",
        json={"resume_id": 1, "job_description_text": _JD_TEXT},
    )
    assert resp.status_code == 401


def test_create_session_resume_not_found(client, uploaded_resume, mock_generate):
    resp = client.post(
        "/interview/",
        json={"resume_id": 9999, "job_description_text": _JD_TEXT},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_create_session_resume_belongs_to_other_user(client, uploaded_resume, sample_pdf, mock_generate):
    # Second user uploads a resume
    from tests.helpers import make_test_pdf
    token2 = register_and_login(client, email="other@example.com")
    hdrs2 = auth_headers(token2)
    from unittest.mock import patch as _patch
    with _patch(
        "services.resume_parser.get_anthropic_client",
        return_value=make_mock_client(json.dumps(MOCK_STRUCTURED_RESUME)),
    ):
        r2 = client.post(
            "/resumes/upload",
            files={"file": ("r.pdf", sample_pdf, "application/pdf")},
            headers=hdrs2,
        )
    resume2_id = r2.json()["id"]
    # First user tries to use second user's resume
    resp = client.post(
        "/interview/",
        json={"resume_id": resume2_id, "job_description_text": _JD_TEXT},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_create_session_jd_too_short(client, uploaded_resume, mock_generate):
    resp = client.post(
        "/interview/",
        json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _SHORT_JD},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 422


def test_create_session_ai_error(client, uploaded_resume):
    with patch(
        "routers.interview.generate_questions",
        side_effect=Exception("AI unavailable"),
    ):
        resp = client.post(
            "/interview/",
            json={"resume_id": uploaded_resume["resume"]["id"], "job_description_text": _JD_TEXT},
            headers=uploaded_resume["headers"],
        )
    assert resp.status_code == 502


# ── GET /interview/ ────────────────────────────────────────────────────────────

def test_list_sessions_empty(client, uploaded_resume):
    resp = client.get("/interview/", headers=uploaded_resume["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_created(client, session_fixture):
    resp = client.get("/interview/", headers=session_fixture["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == session_fixture["session"]["id"]
    assert "question_count" in data[0]
    assert "answered_count" in data[0]
    assert "answer_count" in data[0]


def test_list_sessions_user_isolated(client, session_fixture):
    token2 = register_and_login(client, email="other@example.com")
    resp = client.get("/interview/", headers=auth_headers(token2))
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_requires_auth(client, session_fixture):
    resp = client.get("/interview/")
    assert resp.status_code == 401


# ── GET /interview/{session_id} ────────────────────────────────────────────────

def test_get_session_success(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}", headers=session_fixture["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sid
    assert isinstance(data["questions"], list)


def test_get_session_wrong_user(client, session_fixture):
    token2 = register_and_login(client, email="other@example.com")
    sid = session_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}", headers=auth_headers(token2))
    assert resp.status_code == 404


def test_get_session_requires_auth(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}")
    assert resp.status_code == 401


# ── DELETE /interview/{session_id} ────────────────────────────────────────────

def test_delete_session_success(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.delete(f"/interview/{sid}", headers=session_fixture["headers"])
    assert resp.status_code == 204


def test_delete_session_subsequent_get_404(client, session_fixture):
    sid = session_fixture["session"]["id"]
    client.delete(f"/interview/{sid}", headers=session_fixture["headers"])
    resp = client.get(f"/interview/{sid}", headers=session_fixture["headers"])
    assert resp.status_code == 404


def test_delete_session_wrong_user(client, session_fixture):
    token2 = register_and_login(client, email="other@example.com")
    sid = session_fixture["session"]["id"]
    resp = client.delete(f"/interview/{sid}", headers=auth_headers(token2))
    assert resp.status_code == 404


def test_delete_session_requires_auth(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.delete(f"/interview/{sid}")
    assert resp.status_code == 401


# ── POST /interview/{session_id}/answer ───────────────────────────────────────

def test_submit_answer_success(client, session_fixture, mock_evaluate):
    sid = session_fixture["session"]["id"]
    resp = client.post(
        f"/interview/{sid}/answer",
        json={"question_index": 0, "user_answer": _ANSWER_TEXT},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["session_id"] == sid
    assert data["question_index"] == 0
    assert data["user_answer"] == _ANSWER_TEXT
    assert data["feedback"] is not None
    assert "disclaimer" in data["feedback"]
    assert "relevance" in data["feedback"]["criteria"]
    assert data["evaluation_error"] is None


def test_submit_answer_evaluation_error_still_saves(client, session_fixture):
    """If evaluation fails the answer must still be saved (evaluation_error set)."""
    with patch(
        "routers.interview.evaluate_answer",
        side_effect=Exception("Claude unavailable"),
    ):
        sid = session_fixture["session"]["id"]
        resp = client.post(
            f"/interview/{sid}/answer",
            json={"question_index": 0, "user_answer": _ANSWER_TEXT},
            headers=session_fixture["headers"],
        )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["feedback"] is None
    assert data["evaluation_error"] is not None
    assert "temporarily unavailable" in data["evaluation_error"]
    assert "Claude unavailable" not in data["evaluation_error"]


def test_submit_answer_session_not_found(client, uploaded_resume, mock_evaluate):
    resp = client.post(
        "/interview/9999/answer",
        json={"question_index": 0, "user_answer": _ANSWER_TEXT},
        headers=uploaded_resume["headers"],
    )
    assert resp.status_code == 404


def test_submit_answer_wrong_user(client, session_fixture, mock_evaluate):
    token2 = register_and_login(client, email="other@example.com")
    sid = session_fixture["session"]["id"]
    resp = client.post(
        f"/interview/{sid}/answer",
        json={"question_index": 0, "user_answer": _ANSWER_TEXT},
        headers=auth_headers(token2),
    )
    assert resp.status_code == 404


def test_submit_answer_q_index_out_of_range(client, session_fixture, mock_evaluate):
    sid = session_fixture["session"]["id"]
    resp = client.post(
        f"/interview/{sid}/answer",
        json={"question_index": 999, "user_answer": _ANSWER_TEXT},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 422


def test_submit_answer_too_short(client, session_fixture, mock_evaluate):
    sid = session_fixture["session"]["id"]
    resp = client.post(
        f"/interview/{sid}/answer",
        json={"question_index": 0, "user_answer": "short"},
        headers=session_fixture["headers"],
    )
    assert resp.status_code == 422


def test_submit_answer_requires_auth(client, session_fixture, mock_evaluate):
    sid = session_fixture["session"]["id"]
    resp = client.post(
        f"/interview/{sid}/answer",
        json={"question_index": 0, "user_answer": _ANSWER_TEXT},
    )
    assert resp.status_code == 401


# ── GET /interview/{session_id}/answers ───────────────────────────────────────

def test_list_answers_empty(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/answers", headers=session_fixture["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_answers_returns_submitted(client, answered_fixture):
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/answers", headers=answered_fixture["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["question_index"] == 0


def test_list_answers_wrong_user(client, answered_fixture):
    token2 = register_and_login(client, email="other@example.com")
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/answers", headers=auth_headers(token2))
    assert resp.status_code == 404


def test_list_answers_requires_auth(client, answered_fixture):
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/answers")
    assert resp.status_code == 401


# ── GET /interview/{session_id}/question/{q_idx} ──────────────────────────────

def test_get_question_attempts_success(client, answered_fixture):
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/question/0", headers=answered_fixture["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_index"] == 0
    assert data["attempt_count"] == 1
    assert len(data["attempts"]) == 1
    assert "question" in data


def test_get_question_multiple_attempts(client, session_fixture, mock_evaluate):
    sid = session_fixture["session"]["id"]
    for _ in range(3):
        client.post(
            f"/interview/{sid}/answer",
            json={"question_index": 0, "user_answer": _ANSWER_TEXT},
            headers=session_fixture["headers"],
        )
    resp = client.get(f"/interview/{sid}/question/0", headers=session_fixture["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["attempt_count"] == 3
    assert len(data["attempts"]) == 3


def test_get_question_q_idx_out_of_range(client, session_fixture):
    sid = session_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/question/999", headers=session_fixture["headers"])
    assert resp.status_code == 404


def test_get_question_wrong_user(client, answered_fixture):
    token2 = register_and_login(client, email="other@example.com")
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/question/0", headers=auth_headers(token2))
    assert resp.status_code == 404


def test_get_question_requires_auth(client, answered_fixture):
    sid = answered_fixture["session"]["id"]
    resp = client.get(f"/interview/{sid}/question/0")
    assert resp.status_code == 401
