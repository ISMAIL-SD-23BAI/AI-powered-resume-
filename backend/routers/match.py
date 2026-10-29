"""
Match router — POST /match/ runs the matching engine and persists the result.
All routes require authentication; users can only access their own results.
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from schemas import MatchRequest, MatchResultOut, MatchSummaryOut
import models
from services.jd_parser import parse_jd
from services.matching_engine import compute_from_structured

router = APIRouter(prefix="/match", tags=["match"])
_logger = logging.getLogger(__name__)


def _build_result_response(match: models.MatchResult) -> dict:
    """Merge ORM scalar fields with the persisted result_json blob."""
    data = json.loads(match.result_json)
    return {
        "id": match.id,
        "resume_id": match.resume_id,
        "overall_score": match.overall_score,
        "created_at": match.created_at,
        # pull list/dict fields from the JSON blob
        "required_skill_score": data.get("required_skill_score", 0.0),
        "preferred_skill_score": data.get("preferred_skill_score", 0.0),
        "experience_score": data.get("experience_score", 0.0),
        "education_score": data.get("education_score", 0.0),
        "matched_requirements": data.get("matched_requirements", []),
        "partial_matches": data.get("partial_matches", []),
        "missing_requirements": data.get("missing_requirements", []),
        "missing_preferred": data.get("missing_preferred", []),
        "resume_evidence": data.get("resume_evidence", {}),
        "recommendations": data.get("recommendations", []),
        "disclaimer": data.get("disclaimer", ""),
        "jd_role_title": data.get("jd_role_title"),
    }


def _build_summary(match: models.MatchResult) -> dict:
    try:
        data = json.loads(match.result_json)
        jd_role_title = data.get("jd_role_title")
    except Exception:
        jd_role_title = None
    return {
        "id": match.id,
        "resume_id": match.resume_id,
        "overall_score": match.overall_score,
        "jd_role_title": jd_role_title,
        "created_at": match.created_at,
    }


@router.post("/", response_model=MatchResultOut, status_code=201)
def run_match(
    req: MatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Run the matching engine on a previously uploaded resume against a job description.
    Persists and returns the full explainable result.
    """
    resume = (
        db.query(models.Resume)
        .filter(
            models.Resume.id == req.resume_id,
            models.Resume.user_id == current_user.id,
        )
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Deserialize structured resume — gracefully handle missing/malformed data
    structured: dict = {}
    if resume.structured_json:
        try:
            structured = json.loads(resume.structured_json)
        except json.JSONDecodeError:
            _logger.warning(
                "Could not parse structured_json for resume_id=%d", resume.id
            )

    # Parse JD locally (no LLM)
    jd_requirements = parse_jd(req.job_description_text)

    # Compute match (uses embedding_service internally, with TF-IDF fallback)
    _logger.info(
        "Running match: user_id=%d resume_id=%d", current_user.id, resume.id
    )
    result = compute_from_structured(structured, jd_requirements)

    # Persist
    match_obj = models.MatchResult(
        user_id=current_user.id,
        resume_id=resume.id,
        job_description_text=req.job_description_text,
        result_json=json.dumps(result),
        overall_score=result["overall_score"],
    )
    db.add(match_obj)
    db.commit()
    db.refresh(match_obj)

    _logger.info(
        "Match complete: user_id=%d resume_id=%d score=%d",
        current_user.id,
        resume.id,
        result["overall_score"],
    )

    return _build_result_response(match_obj)


@router.get("/", response_model=List[MatchSummaryOut])
def list_matches(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all match results for the current user, newest first."""
    matches = (
        db.query(models.MatchResult)
        .filter(models.MatchResult.user_id == current_user.id)
        .order_by(models.MatchResult.created_at.desc())
        .all()
    )
    return [_build_summary(m) for m in matches]


@router.get("/{match_id}", response_model=MatchResultOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the full match result for a specific match ID."""
    match = (
        db.query(models.MatchResult)
        .filter(
            models.MatchResult.id == match_id,
            models.MatchResult.user_id == current_user.id,
        )
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")
    return _build_result_response(match)


@router.delete("/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete a match result."""
    match = (
        db.query(models.MatchResult)
        .filter(
            models.MatchResult.id == match_id,
            models.MatchResult.user_id == current_user.id,
        )
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found")
    db.delete(match)
    db.commit()
