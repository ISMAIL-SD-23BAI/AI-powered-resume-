"""
Unit tests for services/skill_gap_analyzer.py

No LLM calls — Claude is mocked for roadmap generation tests.

Coverage
────────
  Skill classification
  - Exact match → demonstrated
  - Semantic match → demonstrated (with note)
  - Partial match not in experience → requires_verification
  - Partial match in experience → partially_demonstrated
  - Missing required skill → not_found
  - Missing preferred skill → not_found (is_preferred=True)
  - not_found note never implies absence of ability
  - Empty match result doesn't crash
  - All skills classified (no silent drops)
  - count_by_classification totals

  Roadmap generation
  - Skipped when no gap skills (no Claude call)
  - Returns validated items for gap skills
  - Malformed JSON raises json.JSONDecodeError
  - Out-of-scope skills in Claude response are filtered out
  - Items have all required keys
  - Items have status "not_started"
  - learning_sequence has 3–5 items
  - No URL patterns in roadmap items
"""
import json
import re
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from tests.helpers import (
    MOCK_MATCH_FOR_GAP,
    MOCK_ROADMAP_CLAUDE_OUTPUT,
    MOCK_STRUCTURED_RESUME,
    MOCK_JD_REQUIREMENTS,
    make_mock_client,
)
from services.skill_gap_analyzer import (
    classify_skills,
    count_by_classification,
    generate_roadmap,
    SKILL_ABSENCE_DISCLAIMER,
)

# ── classify_skills ────────────────────────────────────────────────────────────

def test_exact_match_is_demonstrated():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    python = next(c for c in result if c["skill"] == "python")
    assert python["classification"] == "demonstrated"
    assert python["confidence"] == 1.0


def test_semantic_match_is_demonstrated_with_note():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    fastapi = next(c for c in result if c["skill"] == "fastapi")
    assert fastapi["classification"] == "demonstrated"
    assert fastapi["notes"] is not None
    assert "semantic" in fastapi["notes"].lower()


def test_skills_only_partial_is_requires_verification():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    docker = next(c for c in result if c["skill"] == "docker")
    assert docker["classification"] == "requires_verification"


def test_partial_with_experience_is_partially_demonstrated():
    match = deepcopy(MOCK_MATCH_FOR_GAP)
    match["partial_matches"] = [
        {
            "skill": "redis",
            "match_type": "partial",
            "confidence": 0.55,
            "resume_sections": ["experience", "skills"],  # has experience section
        }
    ]
    result = classify_skills(match)
    redis = next(c for c in result if c["skill"] == "redis")
    assert redis["classification"] == "partially_demonstrated"


def test_missing_required_is_not_found():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    kubernetes = next(c for c in result if c["skill"] == "kubernetes")
    assert kubernetes["classification"] == "not_found"
    assert kubernetes["confidence"] == 0.0
    assert kubernetes["resume_sections"] == []


def test_missing_preferred_is_not_found_with_flag():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    terraform = next(c for c in result if c["skill"] == "terraform")
    assert terraform["classification"] == "not_found"
    assert terraform["is_preferred"] is True


def test_not_found_note_does_not_blame_candidate():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    not_found = [c for c in result if c["classification"] == "not_found"]
    for c in not_found:
        note = c.get("notes", "")
        assert note is not None
        # Must NOT say the person lacks or doesn't have the skill
        lower_note = note.lower()
        assert "you lack" not in lower_note
        assert "you don't have" not in lower_note
        assert "you do not have" not in lower_note
        # MUST mention "resume" to clarify it's document-only
        assert "resume" in lower_note


def test_empty_match_result_no_crash():
    result = classify_skills({})
    assert result == []


def test_all_skills_classified():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    skills_in = set()
    for sm in MOCK_MATCH_FOR_GAP.get("matched_requirements", []):
        skills_in.add(sm["skill"].lower())
    for sm in MOCK_MATCH_FOR_GAP.get("partial_matches", []):
        skills_in.add(sm["skill"].lower())
    for s in MOCK_MATCH_FOR_GAP.get("missing_requirements", []):
        skills_in.add(s.lower())
    for s in MOCK_MATCH_FOR_GAP.get("missing_preferred", []):
        skills_in.add(s.lower())

    classified_skills = {c["skill"].lower() for c in result}
    assert skills_in == classified_skills


def test_no_duplicates_in_classifications():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    skills = [c["skill"].lower() for c in result]
    assert len(skills) == len(set(skills))


def test_count_by_classification():
    result = classify_skills(MOCK_MATCH_FOR_GAP)
    counts = count_by_classification(result)
    assert counts["demonstrated"] == 2   # python + fastapi
    assert counts["requires_verification"] == 1  # docker
    assert counts["not_found"] == 3  # kubernetes + ci/cd + terraform
    assert counts["partially_demonstrated"] == 0


def test_disclaimer_mentions_document_not_ability():
    disclaimer = SKILL_ABSENCE_DISCLAIMER
    lower = disclaimer.lower()
    assert "resume" in lower or "document" in lower
    assert "actual abilities" in lower or "abilities" in lower


# ── generate_roadmap ───────────────────────────────────────────────────────────

def _gap_classifications():
    return [
        c for c in classify_skills(MOCK_MATCH_FOR_GAP)
        if c["classification"] in ("not_found", "partially_demonstrated")
    ]


def test_generate_roadmap_empty_gap_skips_claude():
    with patch("services.skill_gap_analyzer.get_anthropic_client") as mock_factory:
        result = generate_roadmap([], MOCK_JD_REQUIREMENTS, MOCK_STRUCTURED_RESUME)
    mock_factory.assert_not_called()
    assert result == []


def test_generate_roadmap_mocked():
    mock_client = make_mock_client(json.dumps(MOCK_ROADMAP_CLAUDE_OUTPUT))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    assert len(items) >= 1


def test_roadmap_items_have_required_keys():
    mock_client = make_mock_client(json.dumps(MOCK_ROADMAP_CLAUDE_OUTPUT))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    for item in items:
        assert "skill" in item
        assert "why_it_matters" in item
        assert "learning_sequence" in item
        assert "practical_project" in item
        assert "resources_note" in item
        assert "status" in item


def test_roadmap_items_start_as_not_started():
    mock_client = make_mock_client(json.dumps(MOCK_ROADMAP_CLAUDE_OUTPUT))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    for item in items:
        assert item["status"] == "not_started"


def test_roadmap_items_learning_sequence_length():
    mock_client = make_mock_client(json.dumps(MOCK_ROADMAP_CLAUDE_OUTPUT))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    for item in items:
        assert 3 <= len(item["learning_sequence"]) <= 5


def test_roadmap_filters_out_of_scope_skills():
    # Claude returns an extra skill not in the gap list
    bad_output = deepcopy(MOCK_ROADMAP_CLAUDE_OUTPUT)
    bad_output.append({
        "skill": "hacking_not_in_gap",
        "why_it_matters": "Test.",
        "learning_sequence": ["step 1", "step 2", "step 3"],
        "practical_project": "A project.",
        "resources_note": "search: something",
    })
    mock_client = make_mock_client(json.dumps(bad_output))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    skill_names = {item["skill"] for item in items}
    assert "hacking_not_in_gap" not in skill_names


def test_roadmap_no_urls_in_resources_note():
    mock_client = make_mock_client(json.dumps(MOCK_ROADMAP_CLAUDE_OUTPUT))
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        items = generate_roadmap(
            _gap_classifications(),
            MOCK_JD_REQUIREMENTS,
            MOCK_STRUCTURED_RESUME,
        )
    url_pattern = re.compile(r"https?://\S+")
    for item in items:
        # resources_note should not contain raw URLs
        assert not url_pattern.search(item["resources_note"]), (
            f"resources_note contains a URL: {item['resources_note']}"
        )


def test_generate_roadmap_malformed_json_raises():
    mock_client = make_mock_client("not valid json")
    with patch("services.skill_gap_analyzer.get_anthropic_client", return_value=mock_client):
        with pytest.raises(Exception):
            generate_roadmap(
                _gap_classifications(),
                MOCK_JD_REQUIREMENTS,
                MOCK_STRUCTURED_RESUME,
            )
