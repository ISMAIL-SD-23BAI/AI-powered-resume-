import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from limiter import limiter
from schemas import TailorRequest, TailoredResumeOut
import models
from auth import get_current_user
from services.ai_tailor import extract_jd_requirements, tailor_resume

router = APIRouter(prefix="/tailor", tags=["tailor"])


@router.post("/", response_model=TailoredResumeOut)
@limiter.limit("5/minute")
def create_tailored_resume(
    request: Request,
    body: TailorRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resume = db.query(models.Resume).filter(
        models.Resume.id == body.resume_id,
        models.Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.structured_json:
        raise HTTPException(
            status_code=400,
            detail="Resume has no structured content — please re-upload the PDF",
        )

    structured = (
        json.loads(resume.structured_json)
        if isinstance(resume.structured_json, str)
        else resume.structured_json
    )

    # Step 1: parse the job description into structured requirements
    try:
        requirements = extract_jd_requirements(body.job_description_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to parse job description: {exc}")

    # Persist the JobDescription record (flush to get its id before commit)
    jd_record = models.JobDescription(
        user_id=current_user.id,
        raw_text=body.job_description_text,
        extracted_requirements_json=json.dumps(requirements),
    )
    db.add(jd_record)
    db.flush()

    # Step 2: tailor the resume against the extracted requirements
    try:
        tailored = tailor_resume(structured, requirements)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Failed to tailor resume: {exc}")

    record = models.TailoredResume(
        user_id=current_user.id,
        resume_id=resume.id,
        job_description_id=jd_record.id,
        tailored_content_json=json.dumps(tailored),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[TailoredResumeOut])
def list_tailored(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.TailoredResume)
        .filter(models.TailoredResume.user_id == current_user.id)
        .order_by(models.TailoredResume.created_at.desc())
        .all()
    )


@router.get("/{tailored_resume_id}", response_model=TailoredResumeOut)
def get_tailored(
    tailored_resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.TailoredResume).filter(
        models.TailoredResume.id == tailored_resume_id,
        models.TailoredResume.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    return record
