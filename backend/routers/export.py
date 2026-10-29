import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
import models
from auth import get_current_user
from services.pdf_builder import build_resume_pdf, build_cover_letter_pdf

router = APIRouter(prefix="/export", tags=["export"])


def _safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in (s or "")).strip() or "file"


def _role_title_from_jd(jd: models.JobDescription | None) -> str | None:
    if not jd or not jd.extracted_requirements_json:
        return None
    try:
        reqs = (
            json.loads(jd.extracted_requirements_json)
            if isinstance(jd.extracted_requirements_json, str)
            else jd.extracted_requirements_json
        )
        return reqs.get("role_title") or None
    except Exception:
        return None


@router.post("/resume/{tailored_resume_id}")
def export_resume(
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
    if not record.tailored_content_json:
        raise HTTPException(status_code=400, detail="No tailored content to export")

    tc = (
        json.loads(record.tailored_content_json)
        if isinstance(record.tailored_content_json, str)
        else record.tailored_content_json
    )
    tailored_resume = tc.get("tailored_resume", {})
    role_title = _role_title_from_jd(record.job_description)

    pdf = build_resume_pdf(
        tailored_resume=tailored_resume,
        candidate_name=current_user.full_name,
        role_title=role_title,
    )

    slug = _safe_filename(current_user.full_name or "resume")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}_resume.pdf"'},
    )


@router.post("/cover-letter/{cover_letter_id}")
def export_cover_letter(
    cover_letter_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cl = (
        db.query(models.CoverLetter)
        .join(models.TailoredResume)
        .filter(
            models.CoverLetter.id == cover_letter_id,
            models.TailoredResume.user_id == current_user.id,
        )
        .first()
    )
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    role_title = _role_title_from_jd(
        cl.tailored_resume.job_description if cl.tailored_resume else None
    )

    pdf = build_cover_letter_pdf(
        content=cl.content,
        candidate_name=current_user.full_name,
        role_title=role_title,
    )

    slug = _safe_filename(current_user.full_name or "cover_letter")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}_cover_letter.pdf"'},
    )
