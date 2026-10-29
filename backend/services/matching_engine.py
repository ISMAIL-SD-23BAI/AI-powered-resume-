"""
Explainable Resume–Job Matching Engine.

Scoring formula (all components 0–100):
  final_score = round(
      0.40 * required_skill_score
    + 0.15 * preferred_skill_score
    + 0.30 * experience_score
    + 0.15 * education_score
  )

See MATCHING_ENGINE.md for the full formula documentation.

Public API:
  compute_from_structured(
      resume_structured: dict,
      jd_requirements:   dict,
      similarity_fn:     Callable[[str, str], float] | None,
  ) -> dict

The `similarity_fn` parameter is injectable for testing — unit tests pass a
deterministic word-overlap function; production uses embedding_service.compute_similarity.
Missing from resume ≠ "definitely does not possess" — see the `disclaimer` key
in the returned dict.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from services.skill_normalizer import normalize, normalize_list

# ── Thresholds ─────────────────────────────────────────────────────────────────

_EXACT_THRESH = 1.0        # normalized string equality
_SEMANTIC_HIGH = 0.80      # very strong semantic match
_SEMANTIC_LOW = 0.65       # acceptable semantic match
_PARTIAL_LOW = 0.45        # partial / weak match (halved weight)

# ── Education level ordering ───────────────────────────────────────────────────

_EDU_LEVELS = {"bachelor": 1, "master": 2, "phd": 3}
_EDU_KEYWORDS = {
    "phd": re.compile(r"\b(?:ph\.?d|doctoral|doctorate)\b", re.I),
    "master": re.compile(
        r"\b(?:master|m\.?s\.?|m\.?tech|m\.?e\.?|mba)\b", re.I
    ),
    "bachelor": re.compile(
        r"\b(?:bachelor|b\.?s\.?|b\.?tech|b\.?e\.?|b\.?a\.?)\b", re.I
    ),
}


def _detect_resume_edu_level(education: list[dict]) -> Optional[str]:
    """Return the highest education level found in resume education entries."""
    best = None
    for entry in education:
        degree = (entry.get("degree") or "") + " " + (entry.get("institution") or "")
        for level_name, pattern in _EDU_KEYWORDS.items():
            if pattern.search(degree):
                if best is None or _EDU_LEVELS[level_name] > _EDU_LEVELS[best]:
                    best = level_name
    return best


# ── Text corpus helpers ────────────────────────────────────────────────────────

def _resume_text_corpus(resume: dict) -> list[tuple[str, str]]:
    """
    Return a list of (text, source_label) from all textual parts of the resume.
    Used for semantic matching when a required skill is not in the skills list.
    """
    corpus: list[tuple[str, str]] = []

    for skill in (resume.get("skills") or []):
        if skill:
            corpus.append((skill, "skills"))

    for i, job in enumerate((resume.get("experience") or [])):
        title = job.get("title") or ""
        company = job.get("company") or ""
        if title or company:
            corpus.append((f"{title} {company}".strip(), f"experience[{i}]"))
        for bullet in (job.get("bullets") or []):
            if bullet:
                corpus.append((bullet, f"experience[{i}]"))

    for i, proj in enumerate((resume.get("projects") or [])):
        name = proj.get("name") or ""
        desc = proj.get("description") or ""
        combined = f"{name} {desc}".strip()
        if combined:
            corpus.append((combined, f"projects[{i}]"))
        for bullet in (proj.get("bullets") or []):
            if bullet:
                corpus.append((bullet, f"projects[{i}]"))

    return corpus


# ── Single-skill matching ──────────────────────────────────────────────────────

def _match_skill(
    required_skill: str,
    resume_corpus: list[tuple[str, str]],
    similarity_fn: Callable[[str, str], float],
) -> dict:
    """
    Find the best evidence for `required_skill` anywhere in the resume corpus.

    Returns:
      {
        "skill":           str,  # original required skill string
        "match_type":      str,  # "exact" | "semantic" | "partial" | "missing"
        "confidence":      float,
        "resume_sections": list[str],
      }
    """
    norm_req = normalize(required_skill)
    best_conf = 0.0
    best_type = "missing"
    best_sections: list[str] = []
    exact_sections: list[str] = []

    for text, label in resume_corpus:
        norm_text = normalize(text)

        # Exact normalized match
        if norm_req == norm_text or norm_req in norm_text.split() or norm_text in norm_req.split():
            if label not in exact_sections:
                exact_sections.append(label)
            best_conf = 1.0
            best_type = "exact"
            continue

        # Check each word of a multi-word resume item for exact match
        if " " in norm_text:
            words_in_text = [normalize(w) for w in norm_text.split()]
            if norm_req in words_in_text:
                if label not in exact_sections:
                    exact_sections.append(label)
                best_conf = 1.0
                best_type = "exact"
                continue

    if best_type == "exact":
        # Collect all sections with exact match (deduplicated)
        seen = set()
        for text, label in resume_corpus:
            norm_text = normalize(text)
            if (
                norm_req == norm_text
                or norm_req in norm_text.split()
                or norm_text in norm_req.split()
                or (" " in norm_text and norm_req in [normalize(w) for w in norm_text.split()])
            ):
                if label not in seen:
                    seen.add(label)
                    best_sections.append(label)
        return {
            "skill": required_skill,
            "match_type": "exact",
            "confidence": 1.0,
            "resume_sections": best_sections,
        }

    # Semantic matching — check against all corpus items
    top_conf = 0.0
    top_sections: list[str] = []

    for text, label in resume_corpus:
        sim = similarity_fn(norm_req, normalize(text))
        if sim > top_conf:
            top_conf = sim
            top_sections = [label]
        elif sim == top_conf and label not in top_sections:
            top_sections.append(label)

    if top_conf >= _SEMANTIC_HIGH:
        return {
            "skill": required_skill,
            "match_type": "semantic",
            "confidence": round(top_conf, 3),
            "resume_sections": top_sections[:3],
        }
    if top_conf >= _SEMANTIC_LOW:
        return {
            "skill": required_skill,
            "match_type": "semantic",
            "confidence": round(top_conf, 3),
            "resume_sections": top_sections[:3],
        }
    if top_conf >= _PARTIAL_LOW:
        return {
            "skill": required_skill,
            "match_type": "partial",
            "confidence": round(top_conf * 0.5, 3),
            "resume_sections": top_sections[:2],
        }

    return {
        "skill": required_skill,
        "match_type": "missing",
        "confidence": 0.0,
        "resume_sections": [],
    }


# ── Component scores ───────────────────────────────────────────────────────────

def _skill_list_score(
    skill_list: list[str],
    resume_corpus: list[tuple[str, str]],
    similarity_fn: Callable[[str, str], float],
) -> tuple[float, list[dict], list[dict], list[str]]:
    """
    Score a list of skills against the resume corpus.
    Returns (score_0_100, matched, partial, missing_labels).
    """
    if not skill_list:
        return 0.0, [], [], []

    matched: list[dict] = []
    partial: list[dict] = []
    missing: list[str] = []
    total_confidence = 0.0

    # Deduplicate requirements by canonical form
    seen_canonical: set[str] = set()
    unique_skills: list[str] = []
    for s in skill_list:
        canon = normalize(s)
        if canon not in seen_canonical:
            seen_canonical.add(canon)
            unique_skills.append(s)

    for skill in unique_skills:
        result = _match_skill(skill, resume_corpus, similarity_fn)
        total_confidence += result["confidence"]
        if result["match_type"] == "missing":
            missing.append(skill)
        elif result["match_type"] == "partial":
            partial.append(result)
        else:
            matched.append(result)

    score = (total_confidence / len(unique_skills)) * 100 if unique_skills else 0.0
    return round(score, 1), matched, partial, missing


def _experience_score(
    resume: dict,
    jd_responsibilities: list[str],
    jd_experience_years: Optional[int],
    similarity_fn: Callable[[str, str], float],
) -> float:
    """
    Score 0–100 for experience alignment.

    Base (50 pts): resume has at least one experience entry
    Responsibility similarity (30 pts): how well experience bullets match JD responsibilities
    Years met (20 pts): resume experience covers required years
    """
    experience = resume.get("experience") or []

    if not experience:
        return 10.0

    base = 50.0

    # Responsibility similarity
    resp_sim = 0.0
    if jd_responsibilities:
        all_exp_text = []
        for job in experience:
            for bullet in (job.get("bullets") or []):
                if bullet:
                    all_exp_text.append(bullet)
            title = job.get("title") or ""
            if title:
                all_exp_text.append(title)

        if all_exp_text:
            resp_scores = []
            for resp in jd_responsibilities[:10]:
                best = max(
                    (similarity_fn(resp, exp_text) for exp_text in all_exp_text),
                    default=0.0,
                )
                resp_scores.append(best)
            resp_sim = (sum(resp_scores) / len(resp_scores)) if resp_scores else 0.0

    resp_contribution = resp_sim * 30.0

    # Years of experience check (rough heuristic via date parsing)
    years_met = 0.0
    if jd_experience_years is not None:
        total_years = _estimate_experience_years(experience)
        if total_years >= jd_experience_years:
            years_met = 20.0
        elif total_years > 0:
            years_met = 20.0 * (total_years / jd_experience_years)

    return round(min(100.0, base + resp_contribution + years_met), 1)


def _estimate_experience_years(experience: list[dict]) -> float:
    """Rough estimate: count non-'present' date ranges from experience entries."""
    year_re = re.compile(r"\b(20\d{2}|19\d{2})\b")
    total = 0.0
    import datetime
    current_year = datetime.datetime.now().year

    for job in experience:
        dates = job.get("dates") or ""
        years = year_re.findall(dates)
        if len(years) >= 2:
            start, end = int(years[0]), int(years[-1])
            total += max(0, end - start)
        elif len(years) == 1:
            start = int(years[0])
            if re.search(r"present|current|now", dates, re.I):
                total += max(0, current_year - start)
            else:
                total += 1.0  # single year → assume ~1 year

    return total


def _education_score(
    resume: dict,
    edu_requirement: Optional[str],
) -> float:
    """Score 0–100 for education alignment."""
    resume_level = _detect_resume_edu_level(resume.get("education") or [])

    if edu_requirement is None:
        return 70.0  # neutral: no explicit requirement

    req_rank = _EDU_LEVELS.get(edu_requirement, 1)
    res_rank = _EDU_LEVELS.get(resume_level, 0) if resume_level else 0

    if res_rank == 0:
        return 20.0  # no education on resume
    if res_rank >= req_rank:
        return 90.0 if res_rank == req_rank else 100.0  # meets or exceeds
    return 40.0  # below requirement


# ── Recommendations ────────────────────────────────────────────────────────────

def _generate_recommendations(
    missing_required: list[str],
    partial_required: list[dict],
    missing_preferred: list[str],
    required_score: float,
    experience_score: float,
    education_score: float,
) -> list[str]:
    recs: list[str] = []

    if missing_required:
        top5 = missing_required[:5]
        recs.append(
            f"Add explicit mentions of these required skills to your resume: "
            f"{', '.join(top5)}"
            + (" (and others)" if len(missing_required) > 5 else "")
        )

    if partial_required:
        skills = [p["skill"] for p in partial_required[:3]]
        recs.append(
            f"Strengthen evidence for: {', '.join(skills)}. "
            f"Add specific project bullets or accomplishments that demonstrate these skills."
        )

    if required_score < 40:
        recs.append(
            "Your skills section is missing many required skills for this role. "
            "Consider whether this role matches your current skill set, or add any "
            "relevant skills you have that are not yet on your resume."
        )

    if experience_score < 50:
        recs.append(
            "Rewrite experience bullets to reflect the responsibilities in the job description. "
            "Use similar language and highlight relevant outcomes."
        )

    if education_score < 50:
        recs.append(
            "The job description mentions an education requirement that your resume may not "
            "explicitly address. If you meet the requirement, make sure your degree details "
            "are clearly listed."
        )

    if missing_preferred:
        recs.append(
            f"Preferred skills not evidenced: {', '.join(missing_preferred[:4])}. "
            f"Including these would strengthen your application."
        )

    if not recs:
        recs.append(
            "Your resume aligns well with this job description. "
            "Focus on tailoring your summary and cover letter for maximum impact."
        )

    return recs


# ── Public entry point ─────────────────────────────────────────────────────────

_DISCLAIMER = (
    "A skill marked 'not evidenced in resume' means it was not found in "
    "the text of the uploaded resume. It does not mean the candidate does "
    "not possess the skill — they may have it but not listed it. "
    "This score estimates document-to-job alignment, not hiring probability."
)


def compute_from_structured(
    resume_structured: dict,
    jd_requirements: dict,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> dict:
    """
    Compute a match result from structured resume + parsed JD requirements.

    Parameters
    ----------
    resume_structured : dict
        Output of resume_parser.parse_resume — keys: skills, experience, education, projects
    jd_requirements : dict
        Output of jd_parser.parse_jd — keys: required_skills, preferred_skills, ...
    similarity_fn : callable | None
        f(text_a, text_b) -> float in [0, 1].
        Defaults to embedding_service.compute_similarity.
        Pass a custom fn in tests for deterministic results.

    Returns
    -------
    dict with keys: overall_score, required_skill_score, preferred_skill_score,
    experience_score, education_score, matched_requirements, partial_matches,
    missing_requirements, missing_preferred, resume_evidence, recommendations, disclaimer
    """
    if similarity_fn is None:
        from services.embedding_service import compute_similarity
        similarity_fn = compute_similarity

    # Build resume corpus: (text, label) pairs
    resume_corpus = _resume_text_corpus(resume_structured)

    # ── Required skills ──
    required_skills = normalize_list(jd_requirements.get("required_skills") or [])
    req_score, req_matched, req_partial, req_missing = _skill_list_score(
        required_skills, resume_corpus, similarity_fn
    )

    # ── Preferred skills ──
    preferred_skills = normalize_list(jd_requirements.get("preferred_skills") or [])
    pref_score, pref_matched, pref_partial, pref_missing = _skill_list_score(
        preferred_skills, resume_corpus, similarity_fn
    )

    # ── Experience ──
    exp_score = _experience_score(
        resume_structured,
        jd_requirements.get("responsibilities") or [],
        jd_requirements.get("experience_years"),
        similarity_fn,
    )

    # ── Education ──
    edu_score = _education_score(
        resume_structured,
        jd_requirements.get("education_requirement"),
    )

    # ── Final score ──
    final = round(
        0.40 * req_score
        + 0.15 * pref_score
        + 0.30 * exp_score
        + 0.15 * edu_score
    )
    final = max(0, min(100, final))

    # ── Recommendations ──
    recommendations = _generate_recommendations(
        req_missing,
        req_partial,
        pref_missing,
        req_score,
        exp_score,
        edu_score,
    )

    # ── Resume evidence map: skill → sections ──
    all_matches = req_matched + pref_matched + req_partial + pref_partial
    resume_evidence = {
        m["skill"]: m["resume_sections"] for m in all_matches
    }

    return {
        "overall_score": final,
        "required_skill_score": req_score,
        "preferred_skill_score": pref_score,
        "experience_score": exp_score,
        "education_score": edu_score,
        "matched_requirements": req_matched,
        "partial_matches": req_partial,
        "missing_requirements": req_missing,
        "missing_preferred": pref_missing,
        "resume_evidence": resume_evidence,
        "recommendations": recommendations,
        "disclaimer": _DISCLAIMER,
        "jd_role_title": jd_requirements.get("role_title"),
    }
