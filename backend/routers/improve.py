"""
POST /improve/                  — generate improvement session (AI call)
GET  /improve/                  — list sessions for current user
GET  /improve/{id}              — get session details
PATCH /improve/{id}/suggestion  — accept / reject / edit one suggestion
POST /improve/{id}/apply        — apply accepted changes → TailoredResume
DELETE /improve/{id}            — delete session

The original resume is NEVER modified.  Only after the user calls /apply does
a new TailoredResume record get created from the accepted suggestions.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from limiter import limiter
from fastapi import Request
import models
import schemas
from services.improvement_engine import (
    generate_improvements,
    apply_session,
    count_suggestions,
)
from services.jd_parser import parse_jd

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/improve", tags=["improve"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_session_json(session: models.ImprovementSession) -> dict:
    try:
        return json.loads(session.session_json)
    except (json.JSONDecodeError, TypeError):
        return {}


def _build_response(
    session: models.ImprovementSession,
    session_data: dict,
) -> dict:
    total, accepted = count_suggestions(session_data)
    return {
        "id": session.id,
        "resume_id": session.resume_id,
        "role_title": session_data.get("role_title") or None,
        "status": session.status,
        "session_data": session_data,
        "total_suggestions": total,
        "accepted_count": accepted,
        "created_at": session.created_at,
        "tailored_resume_id": session.tailored_resume_id,
    }


def _build_summary(session: models.ImprovementSession, session_data: dict) -> dict:
    total, accepted = count_suggestions(session_data)
    return {
        "id": session.id,
        "resume_id": session.resume_id,
        "role_title": session_data.get("role_title") or None,
        "status": session.status,
        "total_suggestions": total,
        "accepted_count": accepted,
        "created_at": session.created_at,
        "tailored_resume_id": session.tailored_resume_id,
    }


def _get_session_or_404(
    session_id: int,
    user: models.User,
    db: Session,
) -> models.ImprovementSession:
    session = db.query(models.ImprovementSession).filter(
        models.ImprovementSession.id == session_id,
        models.ImprovementSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Improvement session not found")
    return session


# ── POST /improve/ ─────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_session(
    request: Request,
    body: schemas.ImproveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify resume belongs to current user
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
            raise HTTPException(status_code=422, detail="Resume has no structured content — re-upload the PDF")

    if not structured_resume:
        raise HTTPException(status_code=422, detail="Resume has no structured content — re-upload the PDF")

    # Parse JD for requirements (local — no LLM)
    jd_requirements = parse_jd(body.job_description_text)

    # Call Claude to generate suggestions
    try:
        session_data = generate_improvements(
            structured_resume=structured_resume,
            jd_text=body.job_description_text,
            jd_requirements=jd_requirements,
        )
    except json.JSONDecodeError as exc:
        _log.warning("Improvement engine returned malformed JSON: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI returned an invalid response. Please try again.",
        )
    except Exception as exc:
        _log.error("Improvement engine error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI service error. Please try again in a moment.",
        )

    session = models.ImprovementSession(
        user_id=current_user.id,
        resume_id=body.resume_id,
        job_description_text=body.job_description_text,
        session_json=json.dumps(session_data),
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return _build_response(session, session_data)


# ── GET /improve/ ──────────────────────────────────────────────────────────────

@router.get("/")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sessions = (
        db.query(models.ImprovementSession)
        .filter(models.ImprovementSession.user_id == current_user.id)
        .order_by(models.ImprovementSession.created_at.desc())
        .all()
    )
    return [_build_summary(s, _parse_session_json(s)) for s in sessions]


# ── GET /improve/{id} ──────────────────────────────────────────────────────────

@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)
    return _build_response(session, _parse_session_json(session))


# ── PATCH /improve/{id}/suggestion ────────────────────────────────────────────

@router.patch("/{session_id}/suggestion")
def update_suggestion(
    session_id: int,
    body: schemas.SuggestionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)

    if session.status == "applied":
        raise HTTPException(status_code=409, detail="Session is already applied — cannot modify suggestions")

    data = _parse_session_json(session)

    def _apply_update(suggestion: dict) -> None:
        suggestion["status"] = body.status
        if body.custom_text is not None:
            suggestion["custom_text"] = body.custom_text
        elif body.status != "accepted":
            suggestion["custom_text"] = None  # clear custom text when rejecting

    updated = False

    if body.section == "summary":
        ss = data.get("summary_suggestion")
        if ss and ss.get("has_suggestion"):
            _apply_update(ss)
            updated = True

    elif body.section == "experience":
        ji = body.job_index
        bi = body.bullet_index
        if ji is None or bi is None:
            raise HTTPException(status_code=422, detail="job_index and bullet_index required for experience section")
        for job_sug in data.get("experience_suggestions") or []:
            if job_sug.get("job_index") == ji:
                for bsug in job_sug.get("bullet_suggestions") or []:
                    if bsug.get("bullet_index") == bi and bsug.get("has_suggestion"):
                        _apply_update(bsug)
                        updated = True
                        break
                break

    elif body.section == "project":
        pi = body.project_index
        bi = body.bullet_index
        if pi is None or bi is None:
            raise HTTPException(status_code=422, detail="project_index and bullet_index required for project section")
        for proj_sug in data.get("project_suggestions") or []:
            if proj_sug.get("project_index") == pi:
                for bsug in proj_sug.get("bullet_suggestions") or []:
                    if bsug.get("bullet_index") == bi and bsug.get("has_suggestion"):
                        _apply_update(bsug)
                        updated = True
                        break
                break

    elif body.section == "skills":
        skills_sug = data.get("skills_suggestion")
        if skills_sug:
            skills_sug["status"] = body.status
            updated = True

    if not updated:
        raise HTTPException(status_code=404, detail="Suggestion not found or has no AI-generated content")

    session.session_json = json.dumps(data)
    db.commit()
    db.refresh(session)

    return _build_response(session, data)


# ── POST /improve/{id}/apply ───────────────────────────────────────────────────

@router.post("/{session_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_improvements(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Merge accepted suggestions with the original resume, save as a new
    TailoredResume, and return TailoredResumeOut.

    The original Resume record is never modified.
    """
    session = _get_session_or_404(session_id, current_user, db)

    if session.status == "applied":
        # Return the existing tailored resume
        if session.tailored_resume_id:
            tr = db.query(models.TailoredResume).filter(
                models.TailoredResume.id == session.tailored_resume_id
            ).first()
            if tr:
                return schemas.TailoredResumeOut.model_validate(tr)
        raise HTTPException(status_code=409, detail="Session already applied but tailored resume not found")

    resume = db.query(models.Resume).filter(
        models.Resume.id == session.resume_id,
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

    session_data = _parse_session_json(session)
    applied_resume = apply_session(session_data, structured_resume)

    # Build job description record for the new TailoredResume
    jd = models.JobDescription(
        user_id=current_user.id,
        raw_text=session.job_description_text,
    )
    db.add(jd)
    db.flush()

    role_title = session_data.get("role_title") or "Improved Resume"
    content = json.dumps({
        "tailored_resume": applied_resume,
        "alignment_note": f"Accepted improvements for {role_title}",
        "match_score": None,
        "matched_skills": [],
        "missing_skills": [],
    })

    tailored = models.TailoredResume(
        user_id=current_user.id,
        resume_id=session.resume_id,
        job_description_id=jd.id,
        tailored_content_json=content,
    )
    db.add(tailored)
    db.flush()

    session.tailored_resume_id = tailored.id
    session.status = "applied"
    db.commit()
    db.refresh(tailored)

    return schemas.TailoredResumeOut.model_validate(tailored)


# ── DELETE /improve/{id} ───────────────────────────────────────────────────────

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_session_or_404(session_id, current_user, db)
    db.delete(session)
    db.commit()
