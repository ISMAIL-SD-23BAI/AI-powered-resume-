import json
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import ResumeOut
import models
from auth import get_current_user
from services.pdf_parser import extract_text, PDFParseError
from services.resume_parser import parse_resume

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read at most one byte beyond the configured maximum so an oversized
    # multipart upload cannot be copied wholesale into application memory.
    contents = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB limit")

    logger.info(
        "Resume upload: user_id=%d filename=%r size=%d bytes",
        current_user.id,
        file.filename,
        len(contents),
    )

    # Extract text — raises PDFParseError for bad/image-only PDFs
    try:
        raw_text = extract_text(contents)
    except PDFParseError as exc:
        logger.warning(
            "PDF parse failed: user_id=%d filename=%r reason=%s",
            current_user.id,
            file.filename,
            exc,
        )
        raise HTTPException(status_code=422, detail=str(exc))

    # Structured extraction via Claude (gracefully degrades on AI failure)
    structured = parse_resume(raw_text)

    resume = models.Resume(
        user_id=current_user.id,
        filename=file.filename,
        raw_text=raw_text,
        structured_json=json.dumps(structured),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/", response_model=List[ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Resume)
        .filter(models.Resume.user_id == current_user.id)
        .order_by(models.Resume.uploaded_at.desc())
        .all()
    )


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
