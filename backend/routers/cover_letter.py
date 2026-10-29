import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from limiter import limiter
from schemas import CoverLetterRequest, CoverLetterUpdateRequest, CoverLetterOut
import models
from auth import get_current_user
from services.cover_letter import generate_cover_letter

router = APIRouter(prefix="/cover-letter", tags=["cover-letter"])


@router.post("/generate", response_model=CoverLetterOut, status_code=201)
@limiter.limit("5/minute")
def generate(
    request: Request,
    body: CoverLetterRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tailored = db.query(models.TailoredResume).filter(
        models.TailoredResume.id == body.tailored_resume_id,
        models.TailoredResume.user_id == current_user.id,
    ).first()
    if not tailored:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    if not tailored.tailored_content_json:
        raise HTTPException(status_code=400, detail="Tailored resume has no content")

    tc = json.loads(tailored.tailored_content_json) if isinstance(tailored.tailored_content_json, str) else tailored.tailored_content_json
    tailored_resume_obj = tc.get("tailored_resume", {})

    jd = tailored.job_description
    requirements = (
        json.loads(jd.extracted_requirements_json)
        if isinstance(jd.extracted_requirements_json, str)
        else (jd.extracted_requirements_json or {})
    )

    try:
        content = generate_cover_letter(
            tailored_resume=tailored_resume_obj,
            requirements=requirements,
            jd_raw_text=jd.raw_text,
            candidate_name=current_user.full_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cover letter generation failed: {exc}")

    record = models.CoverLetter(
        tailored_resume_id=tailored.id,
        content=content,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/{cover_letter_id}", response_model=CoverLetterOut)
def update(
    cover_letter_id: int,
    body: CoverLetterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cl = db.query(models.CoverLetter).join(models.TailoredResume).filter(
        models.CoverLetter.id == cover_letter_id,
        models.TailoredResume.user_id == current_user.id,
    ).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    cl.content = body.content
    db.commit()
    db.refresh(cl)
    return cl


@router.get("/for/{tailored_resume_id}", response_model=CoverLetterOut)
def get_for_tailored(
    tailored_resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the most recently generated cover letter for a tailored resume."""
    cl = (
        db.query(models.CoverLetter)
        .join(models.TailoredResume)
        .filter(
            models.CoverLetter.tailored_resume_id == tailored_resume_id,
            models.TailoredResume.user_id == current_user.id,
        )
        .order_by(models.CoverLetter.created_at.desc())
        .first()
    )
    if not cl:
        raise HTTPException(status_code=404, detail="No cover letter found")
    return cl
