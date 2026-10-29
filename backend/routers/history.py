import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from database import get_db
from schemas import HistoryItemOut
import models
from auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


def _parse_json(value) -> dict:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return value or {}


@router.get("/", response_model=List[HistoryItemOut])
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    records = (
        db.query(models.TailoredResume)
        .options(
            joinedload(models.TailoredResume.source_resume),
            joinedload(models.TailoredResume.job_description),
            joinedload(models.TailoredResume.cover_letters),
        )
        .filter(models.TailoredResume.user_id == current_user.id)
        .order_by(models.TailoredResume.created_at.desc())
        .all()
    )

    items = []
    for r in records:
        reqs = _parse_json(
            r.job_description.extracted_requirements_json if r.job_description else None
        )
        tc = _parse_json(r.tailored_content_json)

        latest_cl = (
            max(r.cover_letters, key=lambda c: c.created_at)
            if r.cover_letters
            else None
        )

        items.append(
            HistoryItemOut(
                id=r.id,
                resume_filename=r.source_resume.filename if r.source_resume else "Unknown",
                role_title=reqs.get("role_title") or None,
                seniority_level=reqs.get("seniority_level") or None,
                match_score=tc.get("match_score"),
                alignment_note=tc.get("alignment_note"),
                has_cover_letter=bool(r.cover_letters),
                cover_letter_id=latest_cl.id if latest_cl else None,
                created_at=r.created_at,
            )
        )

    return items


@router.delete("/{tailored_resume_id}", status_code=204)
def delete_history_item(
    tailored_resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.TailoredResume).filter(
        models.TailoredResume.id == tailored_resume_id,
        models.TailoredResume.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(record)
    db.commit()
