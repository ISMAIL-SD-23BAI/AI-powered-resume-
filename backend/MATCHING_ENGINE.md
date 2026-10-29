# Matching Engine — Scoring Formula and Design

## Overview

The matching engine computes a transparent, explainable score (0–100) that
estimates how well a candidate's resume aligns with a specific job description.

**This score estimates document-to-job alignment, not hiring probability.**
A skill absent from the resume does not mean the candidate lacks that skill —
they may have it but not listed it.

---

## Scoring Formula

```
final_score = round(
    0.40 × required_skill_score
  + 0.15 × preferred_skill_score
  + 0.30 × experience_score
  + 0.15 × education_score
)
```

All component scores are in [0, 100]. The result is clamped to [0, 100].

### Weight rationale

| Weight | Component | Rationale |
|--------|-----------|-----------|
| 40% | Required skills | Primary hiring criterion — meeting hard requirements is most important |
| 30% | Experience relevance | Demonstrated track record is the second strongest signal |
| 15% | Preferred skills | Nice-to-have; meaningful but not decisive |
| 15% | Education alignment | Important but rarely the only deciding factor |

---

## Component Scores

### Required Skill Score (0–100)

For each required skill R in the JD (deduplicated by canonical form):

1. **Exact match** — `normalize(R) == normalize(resume_skill)` → confidence = 1.0
2. **Semantic match** — `similarity(normalize(R), corpus_item) ≥ 0.65` → confidence = similarity value
3. **Partial match** — `0.45 ≤ similarity < 0.65` → confidence = similarity × 0.5
4. **Missing** — no match anywhere → confidence = 0.0

```
required_skill_score = mean(confidences over all unique required skills) × 100
```

If there are no required skills, this component returns 0.

### Preferred Skill Score (0–100)

Same algorithm as required skills, applied to the preferred/nice-to-have list.
Skills that also appear in the required list are excluded to avoid double-counting.

### Experience Score (0–100)

| Condition | Points |
|-----------|--------|
| At least one experience entry exists | 50 pts base |
| JD responsibility bullets match experience text (semantic) | 0–30 pts |
| Required years of experience met (estimated from date ranges) | 0–20 pts |
| No experience on resume | 10 pts (floor) |

The responsibility similarity is the mean of per-responsibility best-match
scores over all experience bullets (capped at 10 JD responsibilities).

### Education Score (0–100)

| Resume level vs. JD requirement | Score |
|----------------------------------|-------|
| No JD education requirement detected | 70 (neutral) |
| Meets requirement exactly | 90 |
| Exceeds requirement | 100 |
| Below requirement | 40 |
| No education on resume | 20 |

---

## Skill Normalization

Before any matching, skills are normalized to canonical lowercase forms:

- Abbreviations → full names: `ML` → `machine learning`, `k8s` → `kubernetes`
- Alternate spellings: `ReactJS` → `react`, `sklearn` → `scikit-learn`
- Only **clearly equivalent** terms are merged. Related-but-distinct skills
  are kept separate (e.g. `docker` ≠ `kubernetes`).

See `backend/services/skill_normalizer.py` for the complete alias map.

---

## Semantic Similarity

Two backends are supported, selected automatically:

| Backend | When used | Notes |
|---------|-----------|-------|
| `sentence-transformers` (all-MiniLM-L6-v2) | When installed | 384-dim dense vectors, cosine similarity |
| TF-IDF + cosine | Fallback if sentence-transformers unavailable | Word/bigram overlap |

Embeddings are cached in-memory (MD5-keyed). The active backend is logged
at startup and returned by `embedding_service.get_backend_name()`.

No paid API is required. Both backends run entirely offline.

---

## JD Parsing

The JD parser extracts structured requirements from raw text locally (no LLM):

- **Section detection**: header lines matching "Required", "Preferred",
  "Responsibilities", "Qualifications" patterns
- **Skill extraction**: scans for known skills from the normalizer alias map
- **Education detection**: regex for bachelor/master/PhD keywords
- **Experience years**: regex for "X years of experience" patterns

See `backend/services/jd_parser.py`.

---

## Result Structure

```json
{
  "overall_score": 72,
  "required_skill_score": 80.0,
  "preferred_skill_score": 50.0,
  "experience_score": 65.0,
  "education_score": 90.0,
  "matched_requirements": [
    {
      "skill": "python",
      "match_type": "exact",
      "confidence": 1.0,
      "resume_sections": ["skills"]
    }
  ],
  "partial_matches": [],
  "missing_requirements": ["kubernetes"],
  "missing_preferred": ["terraform"],
  "resume_evidence": {
    "python": ["skills"]
  },
  "recommendations": [
    "Add kubernetes to your resume."
  ],
  "disclaimer": "A skill marked 'not evidenced in resume' means it was not found...",
  "jd_role_title": "Backend Engineer"
}
```

### match_type values

| Value | Meaning |
|-------|---------|
| `exact` | Normalized string equality |
| `semantic` | Cosine similarity ≥ 0.65 |
| `partial` | Cosine similarity 0.45–0.65 (halved confidence) |
| `missing` | No match found |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/match/` | Run matching on a resume + JD; persist and return full result |
| GET | `/match/` | List all match results for the current user (summary only) |
| GET | `/match/{id}` | Get the full result for a specific match |
| DELETE | `/match/{id}` | Delete a match result |

All endpoints require a valid JWT Bearer token.

### Request (POST /match/)

```json
{
  "resume_id": 1,
  "job_description_text": "We are looking for a Backend Engineer..."
}
```

---

## Running the Tests

```powershell
# From resume-tailor\ with .venv active:
cd backend
..\.venv\Scripts\python.exe -m pytest tests\test_matching_engine.py -v
..\.venv\Scripts\python.exe -m pytest tests\test_match_router.py -v

# Or all tests at once:
..\.venv\Scripts\python.exe -m pytest tests\ -v
```

The unit tests in `test_matching_engine.py` use a deterministic word-overlap
similarity function — no ML model is loaded, so they run in milliseconds.

The API tests in `test_match_router.py` mock `compute_from_structured` entirely
and run as fast as the other API tests.
