import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models import InterviewAnswer, InterviewSession, Resume, User
from schemas import (
    AnswerSubmitRequest,
    InterviewAnswerOut,
    InterviewRequest,
    InterviewSessionOut,
    InterviewSessionSummaryOut,
    QuestionAttemptsOut,
)
from auth import get_current_user
from services.interview_engine import generate_questions, evaluate_answer
from services.jd_parser import parse_jd
from limiter import limiter

router = APIRouter(prefix="/interview", tags=["interview"])


def _session_to_summary(session: InterviewSession, db: Session) -> InterviewSessionSummaryOut:
    answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == session.id
    ).all()
    answered_indices = {a.question_index for a in answers}
    return InterviewSessionSummaryOut(
        id=session.id,
        resume_id=session.resume_id,
        role_title=session.role_title,
        question_count=session.question_count,
        answered_count=len(answered_indices),
        answer_count=len(answers),
        created_at=session.created_at,
    )


def _session_to_out(session: InterviewSession, db: Session) -> InterviewSessionOut:
    answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == session.id
    ).all()
    answered_indices = {a.question_index for a in answers}
    try:
        questions = json.loads(session.questions_json)
    except (json.JSONDecodeError, TypeError):
        questions = []
    return InterviewSessionOut(
        id=session.id,
        resume_id=session.resume_id,
        role_title=session.role_title,
        questions=questions,
        question_count=session.question_count,
        answered_count=len(answered_indices),
        answer_count=len(answers),
        created_at=session.created_at,
    )


def _answer_to_out(answer: InterviewAnswer) -> InterviewAnswerOut:
    feedback = None
    if answer.feedback_json:
        try:
            feedback = json.loads(answer.feedback_json)
        except (json.JSONDecodeError, TypeError):
            feedback = None
    return InterviewAnswerOut(
        id=answer.id,
        session_id=answer.session_id,
        question_index=answer.question_index,
        question_text=answer.question_text,
        user_answer=answer.user_answer,
        feedback=feedback,
        evaluation_error=answer.evaluation_error,
        created_at=answer.created_at,
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=InterviewSessionOut)
@limiter.limit("3/minute")
def create_session(
    request: Request,
    body: InterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(
        Resume.id == body.resume_id,
        Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.structured_json:
        raise HTTPException(status_code=422, detail="Resume has not been parsed yet")

    try:
        structured = json.loads(resume.structured_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="Resume structured data is invalid")

    jd_requirements = parse_jd(body.job_description_text)

    try:
        questions = generate_questions(structured, body.job_description_text, jd_requirements)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Interview questions could not be validated. Please try again.",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Interview question service is temporarily unavailable. Please try again.")

    role_title = jd_requirements.get("role_title") or None

    session = InterviewSession(
        user_id=current_user.id,
        resume_id=body.resume_id,
        job_description_text=body.job_description_text,
        role_title=role_title,
        questions_json=json.dumps(questions),
        question_count=len(questions),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_out(session, db)


@router.get("/", response_model=list[InterviewSessionSummaryOut])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )
    return [_session_to_summary(s, db) for s in sessions]


@router.get("/{session_id}", response_model=InterviewSessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return _session_to_out(session, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    db.delete(session)
    db.commit()


@router.post(
    "/{session_id}/answer",
    status_code=status.HTTP_201_CREATED,
    response_model=InterviewAnswerOut,
)
@limiter.limit("10/minute")
def submit_answer(
    request: Request,
    session_id: int,
    body: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    try:
        questions = json.loads(session.questions_json)
    except (json.JSONDecodeError, TypeError):
        questions = []

    if body.question_index >= len(questions):
        raise HTTPException(
            status_code=422,
            detail=f"question_index {body.question_index} is out of range (session has {len(questions)} questions)",
        )

    question_dict = questions[body.question_index]
    question_text = question_dict.get("question", "")

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    structured = {}
    if resume and resume.structured_json:
        try:
            structured = json.loads(resume.structured_json)
        except (json.JSONDecodeError, TypeError):
            structured = {}

    feedback_json: Optional[str] = None
    evaluation_error: Optional[str] = None

    try:
        feedback = evaluate_answer(question_dict, body.user_answer, structured)
        feedback_json = json.dumps(feedback)
    except json.JSONDecodeError:
        evaluation_error = "Feedback could not be validated. Your answer is saved; try submitting it again for feedback."
    except Exception:
        evaluation_error = "Feedback service is temporarily unavailable. Your answer is saved; try again shortly."

    answer = InterviewAnswer(
        session_id=session_id,
        user_id=current_user.id,
        question_index=body.question_index,
        question_text=question_text,
        user_answer=body.user_answer,
        feedback_json=feedback_json,
        evaluation_error=evaluation_error,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return _answer_to_out(answer)


@router.get("/{session_id}/answers", response_model=list[InterviewAnswerOut])
def list_answers(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    answers = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.session_id == session_id)
        .order_by(InterviewAnswer.question_index, InterviewAnswer.created_at)
        .all()
    )
    return [_answer_to_out(a) for a in answers]


@router.get("/{session_id}/question/{q_idx}", response_model=QuestionAttemptsOut)
def get_question_attempts(
    session_id: int,
    q_idx: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    try:
        questions = json.loads(session.questions_json)
    except (json.JSONDecodeError, TypeError):
        questions = []

    if q_idx >= len(questions):
        raise HTTPException(status_code=404, detail="Question index out of range")

    answers = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id == session_id,
            InterviewAnswer.question_index == q_idx,
        )
        .order_by(InterviewAnswer.created_at)
        .all()
    )

    return QuestionAttemptsOut(
        question_index=q_idx,
        question=questions[q_idx],
        attempts=[_answer_to_out(a).__dict__ for a in answers],
        attempt_count=len(answers),
    )
