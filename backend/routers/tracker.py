"""
POST   /tracker/          — create job application
GET    /tracker/stats     — summary statistics (MUST be before /{id})
GET    /tracker/          — list applications (optional ?status= ?search=)
GET    /tracker/{id}      — get single application
PATCH  /tracker/{id}      — update fields / status
DELETE /tracker/{id}      — delete application

All queries enforce user_id == current_user.id ownership.
No LLM calls — pure CRUD.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models
import schemas

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/tracker", tags=["tracker"])

_ACTIVE_STATUSES = {"applied", "assessment", "interview"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_app_or_404(app_id: int, user: models.User, db: Session) -> models.JobApplication:
    app = db.query(models.JobApplication).filter(
        models.JobApplication.id == app_id,
        models.JobApplication.user_id == user.id,
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Job application not found")
    return app


def _verify_resume_ownership(resume_id: int, user: models.User, db: Session) -> None:
    if not db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first():
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")


def _verify_tailored_ownership(tailored_id: int, user: models.User, db: Session) -> None:
    if not db.query(models.TailoredResume).filter(
        models.TailoredResume.id == tailored_id,
        models.TailoredResume.user_id == user.id,
    ).first():
        raise HTTPException(status_code=404, detail=f"Tailored resume {tailored_id} not found")


# ── POST /tracker/ ─────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.JobApplicationOut)
def create_application(
    body: schemas.JobApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.resume_id is not None:
        _verify_resume_ownership(body.resume_id, current_user, db)
    if body.tailored_resume_id is not None:
        _verify_tailored_ownership(body.tailored_resume_id, current_user, db)

    app = models.JobApplication(
        user_id=current_user.id,
        company_name=body.company_name,
        job_title=body.job_title,
        job_description=body.job_description,
        job_url=body.job_url,
        status=body.status,
        application_date=body.application_date,
        deadline=body.deadline,
        interview_date=body.interview_date,
        notes=body.notes,
        resume_id=body.resume_id,
        tailored_resume_id=body.tailored_resume_id,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


# ── GET /tracker/stats ─────────────────────────────────────────────────────────
# Registered BEFORE /{id} so "stats" is not treated as an integer path param.

@router.get("/stats", response_model=schemas.TrackerStatsOut)
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.JobApplication.status, func.count(models.JobApplication.id))
        .filter(models.JobApplication.user_id == current_user.id)
        .group_by(models.JobApplication.status)
        .all()
    )
    counts: dict[str, int] = {r[0]: r[1] for r in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "saved": counts.get("saved", 0),
        "active": sum(counts.get(s, 0) for s in _ACTIVE_STATUSES),
        "interviews": counts.get("interview", 0),
        "offers": counts.get("offer", 0),
        "rejected": counts.get("rejected", 0),
    }


# ── GET /tracker/ ──────────────────────────────────────────────────────────────

@router.get("/", response_model=list[schemas.JobApplicationOut])
def list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.JobApplication).filter(
        models.JobApplication.user_id == current_user.id
    )

    if status_filter:
        if status_filter not in schemas._TRACKER_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status filter. Must be one of: {', '.join(sorted(schemas._TRACKER_STATUSES))}",
            )
        q = q.filter(models.JobApplication.status == status_filter)

    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                models.JobApplication.company_name.ilike(term),
                models.JobApplication.job_title.ilike(term),
            )
        )

    return q.order_by(models.JobApplication.created_at.desc()).all()


# ── GET /tracker/{id} ──────────────────────────────────────────────────────────

@router.get("/{app_id}", response_model=schemas.JobApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_app_or_404(app_id, current_user, db)


# ── PATCH /tracker/{id} ───────────────────────────────────────────────────────

@router.patch("/{app_id}", response_model=schemas.JobApplicationOut)
def update_application(
    app_id: int,
    body: schemas.JobApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    app = _get_app_or_404(app_id, current_user, db)

    # Verify foreign key ownership if being changed
    if body.resume_id is not None and body.resume_id != app.resume_id:
        _verify_resume_ownership(body.resume_id, current_user, db)
    if body.tailored_resume_id is not None and body.tailored_resume_id != app.tailored_resume_id:
        _verify_tailored_ownership(body.tailored_resume_id, current_user, db)

    update_fields = body.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(app, field, value)

    db.commit()
    db.refresh(app)
    return app


# ── DELETE /tracker/{id} ──────────────────────────────────────────────────────

@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    app = _get_app_or_404(app_id, current_user, db)
    db.delete(app)
    db.commit()
