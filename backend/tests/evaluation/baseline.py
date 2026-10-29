"""
Keyword baseline for comparison against the matching engine.

Algorithm:
    concat_text = lowercase join of all skills + bullet points + job titles +
                  company names + project names and descriptions.

    For each required skill: hit if required_skill.lower() in concat_text.

This is intentionally simple — no synonym expansion, no word-boundary checks,
no normalisation beyond lowercasing.  Known failure modes:
    - TC02: ML/k8s/DL/py abbreviations are NOT expanded → misses all four.
    - TC07: "java" is a substring of "javascript" → false positive.

These failures are documented in the evaluation report as evidence that the
matching engine adds meaningful value over a trivial baseline.
"""

from __future__ import annotations

from typing import Any


def _build_corpus_text(structured_resume: dict[str, Any]) -> str:
    """Concatenate all resume text into one lowercase string."""
    parts: list[str] = []

    for skill in structured_resume.get("skills", []):
        parts.append(str(skill))

    for exp in structured_resume.get("experience", []):
        if exp.get("title"):
            parts.append(str(exp["title"]))
        if exp.get("company"):
            parts.append(str(exp["company"]))
        for bullet in exp.get("bullets", []):
            parts.append(str(bullet))

    for edu in structured_resume.get("education", []):
        if edu.get("degree"):
            parts.append(str(edu["degree"]))
        if edu.get("institution"):
            parts.append(str(edu["institution"]))

    for proj in structured_resume.get("projects", []):
        if proj.get("name"):
            parts.append(str(proj["name"]))
        if proj.get("description"):
            parts.append(str(proj["description"]))
        for tech in proj.get("technologies", []):
            parts.append(str(tech))

    return " ".join(parts).lower()


def baseline_match(
    structured_resume: dict[str, Any],
    required_skills: list[str],
) -> dict[str, list[str]]:
    """
    Return {"matched": [...], "missing": [...]} using pure substring matching.

    No word boundaries, no normalisation, no synonym expansion.
    """
    corpus = _build_corpus_text(structured_resume)
    matched: list[str] = []
    missing: list[str] = []

    for skill in required_skills:
        if skill.lower() in corpus:
            matched.append(skill)
        else:
            missing.append(skill)

    return {"matched": matched, "missing": missing}
