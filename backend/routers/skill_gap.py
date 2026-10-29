"""
POST /skill-gap/                        — run gap analysis + generate roadmap
GET  /skill-gap/                        — list roadmaps for current user
GET  /skill-gap/{id}                    — get full roadmap
PATCH /skill-gap/{id}/item/{item_idx}   — update a roadmap item's status
DELETE /skill-gap/{id}                  — delete roadmap

Design notes
────────────
- The matching engine (compute_from_structured + parse_jd) is reused as-is.
  No matching logic is duplicated here.
- Claude is only called when gap skills exist.  Zero-gap resumes skip the LLM
  entirely and return instantly.
- The original Resume record is never modified.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from limiter import limiter
import models
import schemas
from services.jd_parser import parse_jd
from services.matching_engine import compute_from_structured
from services.skill_gap_analyzer import (
    classify_skills,
    count_by_classification,
    generate_roadmap,
    SKILL_ABSENCE_DISCLAIMER,
)

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/skill-gap", tags=["skill-gap"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_json_field(text: str) -> list:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []


def _summary_counts(roadmap: models.LearningRoadmap) -> tuple[int, int, int]:
    """Returns (gap_count, completed_count, total_roadmap_items)."""
    classifications = _parse_json_field(roadmap.skill_classifications_json)
    roadmap_items = _parse_json_field(roadmap.roadmap_items_json)

    counts = count_by_classification(classifications)
    gap_count = counts["not_found"] + counts["partially_demonstrated"]
    completed = sum(1 for item in roadmap_items if item.get("status") == "completed")
    return gap_count, completed, len(roadmap_items)


def _build_summary(roadmap: models.LearningRoadmap) -> dict:
    gap_count, completed, total = _summary_counts(roadmap)
    return {
        "id": roadmap.id,
        "resume_id": roadmap.resume_id,
        "role_title": roadmap.role_title,
        "overall_score": roadmap.overall_score,
        "gap_count": gap_count,
        "completed_count": completed,
        "total_roadmap_items": total,
        "created_at": roadmap.created_at,
    }


def _build_response(roadmap: models.LearningRoadmap) -> dict:
    return {
        "id": roadmap.id,
        "resume_id": roadmap.resume_id,
        "role_title": roadmap.role_title,
        "overall_score": roadmap.overall_score,
        "skill_classifications": _parse_json_field(roadmap.skill_classifications_json),
        "roadmap_items": _parse_json_field(roadmap.roadmap_items_json),
        "disclaimer": SKILL_ABSENCE_DISCLAIMER,
        "created_at": roadmap.created_at,
        "updated_at": roadmap.updated_at,
    }


def _get_roadmap_or_404(
    roadmap_id: int,
    user: models.User,
    db: Session,
) -> models.LearningRoadmap:
    roadmap = db.query(models.LearningRoadmap).filter(
        models.LearningRoadmap.id == roadmap_id,
        models.LearningRoadmap.user_id == user.id,
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Learning roadmap not found")
    return roadmap


# ── POST /skill-gap/ ───────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_roadmap(
    request: Request,
    body: schemas.SkillGapRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify resume ownership
    resume = db.query(models.Resume).filter(
        models.Resume.id == body.resume_id,
        models.Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    structured_resume = {}
    if resume.structured_json:
        try:
            structured_resume = json.loads(resume.structured_json)
        except (json.JSONDecodeError, TypeError):
            pass

    if not structured_resume:
        raise HTTPException(
            status_code=422,
            detail="Resume has no structured content — re-upload the PDF",
        )

    # ── Step 1: Local matching (no LLM) ──────────────────────────────────────
    jd_requirements = parse_jd(body.job_description_text)
    match_result = compute_from_structured(structured_resume, jd_requirements)

    # ── Step 2: Deterministic skill classification (no LLM) ──────────────────
    classifications = classify_skills(match_result)

    # ── Step 3: Claude roadmap — only for gap skills ──────────────────────────
    gap_skills = [
        c for c in classifications
        if c["classification"] in ("not_found", "partially_demonstrated")
        and not c.get("is_preferred")  # skip preferred-only gaps in roadmap priority
    ]
    # Include preferred gaps too, but after required ones
    preferred_gaps = [
        c for c in classifications
        if c["classification"] in ("not_found", "partially_demonstrated")
        and c.get("is_preferred")
    ]
    all_gaps = gap_skills + preferred_gaps

    roadmap_items: list[dict] = []
    if all_gaps:
        try:
            roadmap_items = generate_roadmap(all_gaps, jd_requirements, structured_resume)
        except json.JSONDecodeError as exc:
            _log.warning("Roadmap generation returned malformed JSON: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="AI returned an invalid response. Please try again.",
            )
        except Exception as exc:
            _log.error("Roadmap generation error: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="AI service error. Please try again in a moment.",
            )

    # Assign sequential item_index for stable PATCH addressing
    for idx, item in enumerate(roadmap_items):
        item["item_index"] = idx

    roadmap = models.LearningRoadmap(
        user_id=current_user.id,
        resume_id=body.resume_id,
        job_description_text=body.job_description_text,
        role_title=jd_requirements.get("role_title") or None,
        overall_score=match_result.get("overall_score", 0),
        skill_classifications_json=json.dumps(classifications),
        roadmap_items_json=json.dumps(roadmap_items),
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)

    return _build_response(roadmap)


# ── GET /skill-gap/ ────────────────────────────────────────────────────────────

@router.get("/")
def list_roadmaps(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    roadmaps = (
        db.query(models.LearningRoadmap)
        .filter(models.LearningRoadmap.user_id == current_user.id)
        .order_by(models.LearningRoadmap.created_at.desc())
        .all()
    )
    return [_build_summary(r) for r in roadmaps]


# ── GET /skill-gap/{id} ────────────────────────────────────────────────────────

@router.get("/{roadmap_id}")
def get_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    roadmap = _get_roadmap_or_404(roadmap_id, current_user, db)
    return _build_response(roadmap)


# ── PATCH /skill-gap/{id}/item/{item_idx} ─────────────────────────────────────

@router.patch("/{roadmap_id}/item/{item_idx}")
def update_roadmap_item(
    roadmap_id: int,
    item_idx: int,
    body: schemas.RoadmapItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    roadmap = _get_roadmap_or_404(roadmap_id, current_user, db)

    items = _parse_json_field(roadmap.roadmap_items_json)

    # Find item by item_index (not list position, in case order changes)
    matched_item = next(
        (item for item in items if item.get("item_index") == item_idx), None
    )
    if matched_item is None:
        raise HTTPException(status_code=404, detail=f"Roadmap item {item_idx} not found")

    matched_item["status"] = body.status
    roadmap.roadmap_items_json = json.dumps(items)
    db.commit()
    db.refresh(roadmap)

    return _build_response(roadmap)


# ── DELETE /skill-gap/{id} ────────────────────────────────────────────────────

@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    roadmap = _get_roadmap_or_404(roadmap_id, current_user, db)
    db.delete(roadmap)
    db.commit()
