"""
Unit tests for the matching engine.

All tests use a deterministic word-overlap similarity function instead of
sentence-transformers so tests run fast and without any ML model.
"""
import pytest

from services.matching_engine import compute_from_structured, _skill_list_score, _resume_text_corpus
from services.skill_normalizer import normalize


# ── Deterministic similarity function (word overlap, no ML) ───────────────────

def _word_overlap_sim(text_a: str, text_b: str) -> float:
    """Jaccard similarity on lowercased word sets. Deterministic and fast."""
    a = set(text_a.lower().split())
    b = set(text_b.lower().split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_resume(skills=None, experience=None, education=None, projects=None):
    return {
        "skills": skills or [],
        "experience": experience or [],
        "education": education or [],
        "projects": projects or [],
    }


def _make_jd(required=None, preferred=None, responsibilities=None, education_req=None, exp_years=None):
    return {
        "role_title": "Software Engineer",
        "required_skills": required or [],
        "preferred_skills": preferred or [],
        "responsibilities": responsibilities or [],
        "qualifications": [],
        "education_requirement": education_req,
        "experience_years": exp_years,
    }


# ── Exact match ────────────────────────────────────────────────────────────────

def test_exact_skill_match_returns_full_confidence():
    """A skill present verbatim in the resume skills list → confidence 1.0, type 'exact'."""
    resume = _make_resume(skills=["python", "fastapi"])
    jd = _make_jd(required=["python"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert result["overall_score"] > 50
    matched = result["matched_requirements"]
    assert len(matched) == 1
    assert matched[0]["match_type"] == "exact"
    assert matched[0]["confidence"] == 1.0
    assert matched[0]["skill"] == "python"


def test_all_exact_matches_score_100_for_required():
    """When all required skills are exactly present, required_skill_score == 100."""
    resume = _make_resume(skills=["python", "fastapi", "postgresql"])
    jd = _make_jd(required=["python", "fastapi", "postgresql"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert result["required_skill_score"] == 100.0
    assert result["missing_requirements"] == []


# ── Synonym / normalization matching ──────────────────────────────────────────

def test_synonym_match_ml_to_machine_learning():
    """'ML' in resume skills should match 'machine learning' requirement via normalization."""
    resume = _make_resume(skills=["ML", "python"])
    jd = _make_jd(required=["machine learning"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    # After normalization both become "machine learning" → exact match
    matched = result["matched_requirements"]
    assert len(matched) >= 1
    matched_skills = [m["skill"] for m in matched]
    assert "machine learning" in matched_skills
    assert "machine learning" not in result["missing_requirements"]


def test_synonym_k8s_to_kubernetes():
    """'k8s' in resume should match 'kubernetes' in JD."""
    resume = _make_resume(skills=["k8s", "docker"])
    jd = _make_jd(required=["kubernetes"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert "kubernetes" not in result["missing_requirements"]
    assert result["required_skill_score"] == 100.0


def test_synonym_js_to_javascript():
    """'js' abbreviation should match 'javascript' requirement."""
    resume = _make_resume(skills=["js", "react"])
    jd = _make_jd(required=["javascript"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert "javascript" not in result["missing_requirements"]


# ── Missing skills ─────────────────────────────────────────────────────────────

def test_missing_skill_has_zero_confidence():
    """A required skill not in the resume → confidence 0, in missing_requirements."""
    resume = _make_resume(skills=["python"])
    jd = _make_jd(required=["kubernetes"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert "kubernetes" in result["missing_requirements"]
    assert result["required_skill_score"] == 0.0


def test_multiple_missing_skills_all_reported():
    resume = _make_resume(skills=["python"])
    jd = _make_jd(required=["java", "golang", "rust"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert set(result["missing_requirements"]) == {"java", "go", "rust"}


def test_missing_uses_not_evidenced_language():
    """Missing skills must appear in missing_requirements, not as 'does not possess'."""
    resume = _make_resume(skills=[])
    jd = _make_jd(required=["tensorflow"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert "tensorflow" in result["missing_requirements"]
    # Disclaimer must clarify absence ≠ non-possession
    assert "not evidenced" in result["disclaimer"].lower() or "absent" in result["disclaimer"].lower()


# ── Irrelevant resume ──────────────────────────────────────────────────────────

def test_irrelevant_resume_low_score():
    """A resume about cooking should score very low against an ML engineer JD."""
    resume = _make_resume(
        skills=["chopping", "sauteing", "plating"],
        experience=[{
            "title": "Chef",
            "company": "Restaurant ABC",
            "dates": "2020-2023",
            "bullets": ["Prepared Italian cuisine", "Managed kitchen inventory"],
        }],
    )
    jd = _make_jd(
        required=["python", "machine learning", "tensorflow", "pytorch", "numpy"],
        responsibilities=["Build ML models", "Train neural networks", "Deploy to production"],
    )
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    # Very low required skill score
    assert result["required_skill_score"] == 0.0
    assert result["overall_score"] < 40


# ── Empty / edge case inputs ───────────────────────────────────────────────────

def test_empty_jd_returns_valid_result():
    """Empty JD requirements should not crash — returns a valid result dict."""
    resume = _make_resume(skills=["python"])
    jd = _make_jd()  # empty required/preferred
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 100


def test_empty_resume_returns_valid_result():
    """Resume with no content should produce a valid result, not an exception."""
    resume = _make_resume()
    jd = _make_jd(required=["python", "fastapi"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert result["required_skill_score"] == 0.0
    assert set(result["missing_requirements"]) == {"python", "fastapi"}


def test_both_empty_returns_valid_result():
    resume = _make_resume()
    jd = _make_jd()
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert 0 <= result["overall_score"] <= 100
    assert isinstance(result["recommendations"], list)


def test_none_skills_in_resume_handled():
    """None values in skills list should not cause exceptions."""
    resume = _make_resume(skills=[None, "python", None])
    jd = _make_jd(required=["python"])
    # Should not raise
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)
    assert "overall_score" in result


# ── Duplicate requirements ─────────────────────────────────────────────────────

def test_duplicate_requirements_counted_once():
    """Duplicate required skills should be deduplicated before scoring."""
    resume = _make_resume(skills=["python"])
    jd = _make_jd(required=["python", "python", "Python", "py"])  # all normalize to "python"
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    # De-duped to single "python" → full score
    assert result["required_skill_score"] == 100.0
    assert len(result["matched_requirements"]) == 1


# ── Score range ────────────────────────────────────────────────────────────────

def test_overall_score_always_0_to_100():
    """Overall score must always be in [0, 100]."""
    cases = [
        (_make_resume(), _make_jd()),
        (_make_resume(skills=["x"] * 50), _make_jd(required=["x"] * 50)),
        (_make_resume(skills=["python"]), _make_jd(required=["python", "java", "kubernetes"])),
    ]
    for resume, jd in cases:
        result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)
        assert 0 <= result["overall_score"] <= 100, f"Out of range: {result['overall_score']}"


# ── Formula verification ───────────────────────────────────────────────────────

def test_score_formula_weights():
    """Verify the weighted formula: 40% required + 15% preferred + 30% exp + 15% edu."""
    resume = _make_resume(
        skills=["python", "fastapi"],
        experience=[{
            "title": "Software Engineer",
            "company": "TechCorp",
            "dates": "2021-2024",
            "bullets": ["Developed REST APIs with Python and FastAPI"],
        }],
        education=[{"degree": "B.Tech Computer Science", "institution": "MIT", "dates": "2017-2021"}],
    )
    jd = _make_jd(
        required=["python", "fastapi"],
        education_req="bachelor",
        exp_years=2,
    )
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    expected = round(
        0.40 * result["required_skill_score"]
        + 0.15 * result["preferred_skill_score"]
        + 0.30 * result["experience_score"]
        + 0.15 * result["education_score"]
    )
    assert result["overall_score"] == expected


# ── Semantic matching (using word_overlap as proxy) ────────────────────────────

def test_partial_match_from_experience_bullets():
    """Skill not in skills list but mentioned in an experience bullet should score > 0."""
    resume = _make_resume(
        skills=[],  # no skills section
        experience=[{
            "title": "Data Scientist",
            "company": "AI Corp",
            "dates": "2022-2024",
            "bullets": ["Built machine learning models in Python", "Deployed TensorFlow pipelines"],
        }],
    )
    jd = _make_jd(required=["machine learning", "tensorflow"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    # With word-overlap sim, "machine learning" in bullet text should produce some match
    assert result["required_skill_score"] > 0


# ── Result structure ───────────────────────────────────────────────────────────

def test_result_has_all_required_keys():
    """compute_from_structured must return all documented keys."""
    resume = _make_resume(skills=["python"])
    jd = _make_jd(required=["python"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    required_keys = {
        "overall_score", "required_skill_score", "preferred_skill_score",
        "experience_score", "education_score", "matched_requirements",
        "partial_matches", "missing_requirements", "missing_preferred",
        "resume_evidence", "recommendations", "disclaimer", "jd_role_title",
    }
    assert required_keys.issubset(result.keys())


def test_recommendations_are_non_empty_list():
    resume = _make_resume(skills=["python"])
    jd = _make_jd(required=["python", "kubernetes", "tensorflow"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0


def test_missing_requirements_not_in_matched():
    """No skill should appear in both matched_requirements and missing_requirements."""
    resume = _make_resume(skills=["python", "docker"])
    jd = _make_jd(required=["python", "kubernetes", "docker", "terraform"])
    result = compute_from_structured(resume, jd, similarity_fn=_word_overlap_sim)

    matched_skills = {m["skill"] for m in result["matched_requirements"]}
    missing_skills = set(result["missing_requirements"])
    overlap = matched_skills & missing_skills
    assert overlap == set(), f"Skills in both matched and missing: {overlap}"
