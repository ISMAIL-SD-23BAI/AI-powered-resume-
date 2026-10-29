"""
Unit tests for services/improvement_engine.py

No LLM calls are made — Claude is mocked via make_mock_client.

Coverage:
  - Factual preservation (company names, years)
  - Fabricated-metric detection and flagging
  - Year-injection detection
  - claude changes_facts flag respected
  - Skills addition detected and blocked
  - Malformed JSON raises json.JSONDecodeError (caught at router level)
  - Empty experience/project sections don't crash
  - Required keys always present in session output
  - apply_session: accepted bullets used, rejected bullets use original
  - apply_session: no mutation of original resume
  - count_suggestions: total and accepted counts correct
"""
import json
from copy import deepcopy
from unittest.mock import patch

import pytest

from tests.helpers import (
    MOCK_STRUCTURED_RESUME,
    MOCK_JD_REQUIREMENTS,
    MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
    make_mock_client,
)
from services.improvement_engine import (
    _validate_bullet,
    _validate_skills,
    _build_session,
    apply_session,
    count_suggestions,
    generate_improvements,
)


# ── _validate_bullet ───────────────────────────────────────────────────────────

def test_validate_bullet_clean_passes():
    flagged, reason = _validate_bullet(
        "Built REST APIs using Python and FastAPI for ACME Corp",
        "Developed scalable REST APIs using Python and FastAPI for ACME Corp",
        False,
        [],
    )
    assert not flagged
    assert reason is None


def test_validate_bullet_claude_changes_facts_flagged():
    flagged, reason = _validate_bullet(
        "Worked on backend services",
        "Increased performance by 30% at ACME Corp",
        True,
        ["performance metric"],
    )
    assert flagged
    assert "performance metric" in reason


def test_validate_bullet_fabricated_percentage_flagged():
    original = "Worked on caching layers at ACME Corp"
    suggested = "Improved cache hit rate by 40% at ACME Corp"
    flagged, reason = _validate_bullet(original, suggested, False, [])
    assert flagged
    assert reason is not None


def test_validate_bullet_fabricated_team_size_flagged():
    original = "Led the backend team on a migration project"
    suggested = "Managed a team of 8 engineers on a migration project"
    flagged, reason = _validate_bullet(original, suggested, False, [])
    assert flagged


def test_validate_bullet_year_injection_flagged():
    original = "Worked on microservices at ACME Corp"
    suggested = "Designed microservices at ACME Corp since 2019"
    flagged, reason = _validate_bullet(original, suggested, False, [])
    assert flagged
    assert "2019" in reason


def test_validate_bullet_same_year_passes():
    original = "Worked at ACME Corp from 2022 to 2024"
    suggested = "Developed REST APIs at ACME Corp from 2022 to 2024"
    flagged, reason = _validate_bullet(original, suggested, False, [])
    assert not flagged


def test_validate_bullet_suggestion_without_year_passes():
    original = "Worked at ACME Corp from 2022 to 2024"
    suggested = "Developed REST APIs at ACME Corp"  # no year — fine
    flagged, reason = _validate_bullet(original, suggested, False, [])
    assert not flagged


# ── _validate_skills ───────────────────────────────────────────────────────────

def test_validate_skills_reorder_no_additions():
    original = ["Python", "FastAPI", "Docker"]
    suggested = ["FastAPI", "Python", "Docker"]
    added, removed = _validate_skills(original, suggested)
    assert added == []
    assert removed == []


def test_validate_skills_addition_detected():
    original = ["Python", "FastAPI"]
    suggested = ["Python", "FastAPI", "Kubernetes"]
    added, removed = _validate_skills(original, suggested)
    assert "Kubernetes" in added


def test_validate_skills_removal_detected():
    original = ["Python", "FastAPI", "Docker"]
    suggested = ["Python", "FastAPI"]
    added, removed = _validate_skills(original, suggested)
    assert "Docker" in removed


# ── _build_session ─────────────────────────────────────────────────────────────

def test_build_session_required_keys():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    assert "role_analysis" in session
    assert "summary_suggestion" in session
    assert "experience_suggestions" in session
    assert "project_suggestions" in session
    assert "skills_suggestion" in session


def test_build_session_experience_bullets_all_present():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    exp = session["experience_suggestions"]
    assert len(exp) == 1
    bullets = exp[0]["bullet_suggestions"]
    # Original resume has 2 bullets; both should appear
    assert len(bullets) == 2


def test_build_session_original_preserved_in_bullets():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    bsug = session["experience_suggestions"][0]["bullet_suggestions"][0]
    assert bsug["original"] == "Built REST APIs using Python and FastAPI"
    assert bsug["has_suggestion"] is True
    assert bsug["status"] == "pending"


def test_build_session_out_of_bounds_index_skipped():
    bad_output = deepcopy(MOCK_IMPROVEMENT_CLAUDE_OUTPUT)
    bad_output["experience_suggestions"][0]["bullet_suggestions"].append({
        "bullet_index": 999,  # doesn't exist
        "suggested": "phantom bullet",
        "reason": "test",
        "changes_facts": False,
        "unsupported_claims": [],
    })
    session = _build_session(MOCK_STRUCTURED_RESUME, bad_output, MOCK_JD_REQUIREMENTS)
    bullets = session["experience_suggestions"][0]["bullet_suggestions"]
    # Only 2 real bullets should appear (999 skipped)
    assert len(bullets) == 2


def test_build_session_skills_added_blocked():
    bad_output = deepcopy(MOCK_IMPROVEMENT_CLAUDE_OUTPUT)
    bad_output["skills_reorder"] = ["Python", "FastAPI", "SQLAlchemy", "Docker", "Kubernetes"]
    session = _build_session(MOCK_STRUCTURED_RESUME, bad_output, MOCK_JD_REQUIREMENTS)
    skl = session["skills_suggestion"]
    assert "Kubernetes" in skl["added_skills"]
    # Suggested should fall back to original when skills are added
    assert skl["suggested"] == MOCK_STRUCTURED_RESUME["skills"]


def test_build_session_empty_experience_no_crash():
    resume = {**MOCK_STRUCTURED_RESUME, "experience": []}
    session = _build_session(resume, MOCK_IMPROVEMENT_CLAUDE_OUTPUT, MOCK_JD_REQUIREMENTS)
    assert session["experience_suggestions"] == []


def test_build_session_role_title_from_requirements():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    assert session["role_title"] == MOCK_JD_REQUIREMENTS["role_title"]


# ── apply_session ──────────────────────────────────────────────────────────────

def _accepted_session() -> dict:
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    # Accept all suggestions
    for job_sug in session["experience_suggestions"]:
        for bsug in job_sug["bullet_suggestions"]:
            if bsug["has_suggestion"]:
                bsug["status"] = "accepted"
    for proj_sug in session["project_suggestions"]:
        for bsug in proj_sug["bullet_suggestions"]:
            if bsug["has_suggestion"]:
                bsug["status"] = "accepted"
    if session["summary_suggestion"].get("has_suggestion"):
        session["summary_suggestion"]["status"] = "accepted"
    return session


def test_apply_accepted_uses_suggested_text():
    session = _accepted_session()
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    bullet = applied["experience"][0]["bullets"][0]
    assert bullet == "Developed scalable REST APIs using Python and FastAPI for ACME Corp"


def test_apply_rejected_uses_original_text():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    # Reject all suggestions (they default to "pending" — also uses original)
    for job_sug in session["experience_suggestions"]:
        for bsug in job_sug["bullet_suggestions"]:
            bsug["status"] = "rejected"
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    # Rejected bullet must equal original
    assert applied["experience"][0]["bullets"][0] == "Built REST APIs using Python and FastAPI"


def test_apply_pending_uses_original_text():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    # Leave all as "pending" — apply_session should use original
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    assert applied["experience"][0]["bullets"][0] == "Built REST APIs using Python and FastAPI"


def test_apply_custom_text_used_over_suggested():
    session = _accepted_session()
    bsug = session["experience_suggestions"][0]["bullet_suggestions"][0]
    bsug["custom_text"] = "Custom edited bullet text"
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    assert applied["experience"][0]["bullets"][0] == "Custom edited bullet text"


def test_apply_does_not_mutate_original_resume():
    original_copy = deepcopy(MOCK_STRUCTURED_RESUME)
    session = _accepted_session()
    apply_session(session, MOCK_STRUCTURED_RESUME)
    assert MOCK_STRUCTURED_RESUME == original_copy


def test_apply_education_unchanged():
    session = _accepted_session()
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    assert applied["education"] == MOCK_STRUCTURED_RESUME["education"]


def test_apply_summary_accepted():
    session = _accepted_session()
    applied = apply_session(session, MOCK_STRUCTURED_RESUME)
    assert "FastAPI" in applied.get("summary", "")


# ── count_suggestions ──────────────────────────────────────────────────────────

def test_count_suggestions_pending():
    session = _build_session(
        MOCK_STRUCTURED_RESUME,
        MOCK_IMPROVEMENT_CLAUDE_OUTPUT,
        MOCK_JD_REQUIREMENTS,
    )
    total, accepted = count_suggestions(session)
    assert total > 0
    assert accepted == 0  # all pending


def test_count_suggestions_after_accept_all():
    session = _accepted_session()
    total, accepted = count_suggestions(session)
    assert total == accepted
    assert total > 0


# ── generate_improvements (integration via mock) ───────────────────────────────

def test_generate_improvements_mocked():
    mock_response = json.dumps(MOCK_IMPROVEMENT_CLAUDE_OUTPUT)
    mock_client = make_mock_client(mock_response)
    with patch("services.improvement_engine.get_anthropic_client", return_value=mock_client):
        session = generate_improvements(
            MOCK_STRUCTURED_RESUME,
            "We need a Python engineer with FastAPI REST API experience at our tech startup",
            MOCK_JD_REQUIREMENTS,
        )
    assert "experience_suggestions" in session
    assert session["experience_suggestions"][0]["bullet_suggestions"][0]["has_suggestion"] is True


def test_generate_improvements_malformed_json_raises():
    mock_client = make_mock_client("This is not JSON at all")
    with patch("services.improvement_engine.get_anthropic_client", return_value=mock_client):
        with pytest.raises(Exception):  # json.JSONDecodeError or similar
            generate_improvements(
                MOCK_STRUCTURED_RESUME,
                "We need a Python engineer with FastAPI REST API experience at our tech startup",
                MOCK_JD_REQUIREMENTS,
            )
