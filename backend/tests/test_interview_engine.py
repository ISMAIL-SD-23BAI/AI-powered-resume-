"""Unit tests for services/interview_engine.py."""
import json
import pytest
from unittest.mock import patch

from tests.helpers import (
    MOCK_INTERVIEW_QUESTIONS_OUTPUT,
    MOCK_INTERVIEW_FEEDBACK_OUTPUT,
    MOCK_STRUCTURED_RESUME,
    MOCK_JD_REQUIREMENTS,
    make_mock_client,
)
from services.interview_engine import (
    _validate_question,
    _validate_feedback,
    _clamp_score,
    generate_questions,
    evaluate_answer,
)

# ── _clamp_score ───────────────────────────────────────────────────────────────

def test_clamp_score_within_range():
    assert _clamp_score(3) == 3

def test_clamp_score_below_min():
    assert _clamp_score(0) == 1

def test_clamp_score_above_max():
    assert _clamp_score(10) == 5

def test_clamp_score_non_numeric():
    assert _clamp_score("bad") == 3


# ── _validate_question ─────────────────────────────────────────────────────────

def test_validate_question_valid():
    item = {"type": "technical", "question": "Tell me about Python.", "guidance": "Be specific."}
    result = _validate_question(item, 0)
    assert result is not None
    assert result["index"] == 0
    assert result["type"] == "technical"

def test_validate_question_invalid_type():
    item = {"type": "unknown", "question": "Q?", "guidance": "G."}
    assert _validate_question(item, 0) is None

def test_validate_question_missing_question():
    item = {"type": "hr", "guidance": "G."}
    assert _validate_question(item, 0) is None

def test_validate_question_empty_question():
    item = {"type": "behavioral", "question": "   ", "guidance": "G."}
    assert _validate_question(item, 0) is None

def test_validate_question_not_dict():
    assert _validate_question("not a dict", 0) is None


# ── _validate_feedback ─────────────────────────────────────────────────────────

def test_validate_feedback_technical():
    raw = dict(MOCK_INTERVIEW_FEEDBACK_OUTPUT)
    raw["_question_type"] = "technical"
    result = _validate_feedback(raw)
    assert result["technical_score"] is not None
    assert 1 <= result["technical_score"] <= 5
    assert result["overall_score"] >= 1
    assert result["disclaimer"] == (
        "This evaluation is for practice purposes only and does not predict performance "
        "in real interviews or hiring decisions."
    )

def test_validate_feedback_behavioral_nullifies_technical():
    raw = dict(MOCK_INTERVIEW_FEEDBACK_OUTPUT)
    raw["_question_type"] = "behavioral"
    raw["technical_score"] = 4
    result = _validate_feedback(raw)
    assert result["technical_score"] is None

def test_validate_feedback_clamps_scores():
    raw = {
        "_question_type": "technical",
        "relevance_score": 10,
        "clarity_score": 0,
        "structure_score": 3,
        "technical_score": 6,
        "overall_score": 5,
        "strengths": [],
        "improvements": [],
        "unsupported_claims": [],
        "feedback_text": "ok",
        "disclaimer": "x",
    }
    result = _validate_feedback(raw)
    assert result["relevance_score"] == 5
    assert result["clarity_score"] == 1
    assert result["technical_score"] == 5

def test_validate_feedback_injects_disclaimer():
    raw = {
        "_question_type": "hr",
        "relevance_score": 3,
        "clarity_score": 3,
        "structure_score": 3,
        "technical_score": None,
        "overall_score": 3,
        "strengths": [],
        "improvements": [],
        "unsupported_claims": [],
        "feedback_text": "ok",
        "disclaimer": "wrong disclaimer text",
    }
    result = _validate_feedback(raw)
    assert "practice purposes only" in result["disclaimer"]
    assert "scale" in result["criteria"]

def test_validate_feedback_non_list_fields_become_lists():
    raw = {
        "_question_type": "technical",
        "relevance_score": 3,
        "clarity_score": 3,
        "structure_score": 3,
        "technical_score": 3,
        "overall_score": 3,
        "strengths": "one strength",
        "improvements": None,
        "unsupported_claims": None,
        "feedback_text": "ok",
        "disclaimer": "x",
    }
    result = _validate_feedback(raw)
    assert isinstance(result["strengths"], list)
    assert isinstance(result["improvements"], list)
    assert isinstance(result["unsupported_claims"], list)


# ── generate_questions ─────────────────────────────────────────────────────────

def test_generate_questions_success():
    mock_output = json.dumps(MOCK_INTERVIEW_QUESTIONS_OUTPUT)
    mock_client = make_mock_client(mock_output)
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        questions = generate_questions(MOCK_STRUCTURED_RESUME, "We need a Python developer with FastAPI experience.", MOCK_JD_REQUIREMENTS)
    assert len(questions) == 8
    for i, q in enumerate(questions):
        assert q["index"] == i
        assert q["type"] in {"technical", "behavioral", "hr", "project"}
        assert q["question"]
        assert q["answer_structure"]

def test_generate_questions_rejects_missing_required_category():
    items = [dict(q) for q in MOCK_INTERVIEW_QUESTIONS_OUTPUT]
    items = [q for q in items if q["type"] != "hr"]
    mock_client = make_mock_client(json.dumps(items))
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        with pytest.raises(json.JSONDecodeError, match="missing required"):
            generate_questions(MOCK_STRUCTURED_RESUME, "Python developer role with FastAPI.", MOCK_JD_REQUIREMENTS)

def test_generate_questions_reindexes():
    items = [dict(q) for q in MOCK_INTERVIEW_QUESTIONS_OUTPUT]
    # Scramble indices
    for i, item in enumerate(items):
        item["index"] = i * 3
    mock_client = make_mock_client(json.dumps(items))
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        questions = generate_questions(MOCK_STRUCTURED_RESUME, "Python developer role with FastAPI.", MOCK_JD_REQUIREMENTS)
    for i, q in enumerate(questions):
        assert q["index"] == i

def test_generate_questions_raises_on_bad_json():
    mock_client = make_mock_client("not json at all")
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        with pytest.raises(json.JSONDecodeError):
            generate_questions(MOCK_STRUCTURED_RESUME, "Python developer role with FastAPI.", MOCK_JD_REQUIREMENTS)

def test_generate_questions_raises_on_too_few_valid():
    # Only 2 valid items, should raise
    items = [
        {"index": 0, "type": "technical", "question": "Q1?", "guidance": "G"},
        {"index": 1, "type": "behavioral", "question": "Q2?", "guidance": "G"},
        {"index": 2, "type": "INVALID_TYPE", "question": "Q3?", "guidance": "G"},
    ]
    mock_client = make_mock_client(json.dumps(items))
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        with pytest.raises(json.JSONDecodeError):
            generate_questions(MOCK_STRUCTURED_RESUME, "Python developer role with FastAPI.", MOCK_JD_REQUIREMENTS)


# ── evaluate_answer ────────────────────────────────────────────────────────────

def test_evaluate_answer_success():
    mock_output = json.dumps(MOCK_INTERVIEW_FEEDBACK_OUTPUT)
    mock_client = make_mock_client(mock_output)
    question_dict = MOCK_INTERVIEW_QUESTIONS_OUTPUT[0]
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        result = evaluate_answer(question_dict, "I used FastAPI routing and Pydantic models.", MOCK_STRUCTURED_RESUME)
    assert result["relevance_score"] in range(1, 6)
    assert "disclaimer" in result
    assert "practice purposes only" in result["disclaimer"]

def test_evaluate_answer_raises_on_bad_json():
    mock_client = make_mock_client("{bad json}")
    question_dict = MOCK_INTERVIEW_QUESTIONS_OUTPUT[0]
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        with pytest.raises(json.JSONDecodeError):
            evaluate_answer(question_dict, "Some answer text here.", MOCK_STRUCTURED_RESUME)

def test_evaluate_answer_behavioral_nullifies_technical():
    feedback = dict(MOCK_INTERVIEW_FEEDBACK_OUTPUT)
    feedback["technical_score"] = 5
    mock_client = make_mock_client(json.dumps(feedback))
    behavioral_question = MOCK_INTERVIEW_QUESTIONS_OUTPUT[2]  # index 2 is behavioral
    assert behavioral_question["type"] == "behavioral"
    with patch("services.interview_engine.get_anthropic_client", return_value=mock_client):
        result = evaluate_answer(behavioral_question, "I escalated the issue and helped resolve it.", MOCK_STRUCTURED_RESUME)
    assert result["technical_score"] is None
