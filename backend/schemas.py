from pydantic import BaseModel, EmailStr, field_validator, AnyHttpUrl, Field
from datetime import datetime
from typing import Optional, Any, List, Literal
import json

_TRACKER_STATUSES = {"saved", "applied", "assessment", "interview", "offer", "rejected"}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _deserialize_json_field(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return None
    return v


# ── Auth ───────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if len(v) > 200:
                raise ValueError("Name must not exceed 200 characters")
        return v or None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password is required")
        return v


# ── Resumes ────────────────────────────────────────────────────────────────────

class ResumeOut(BaseModel):
    id: int
    filename: str
    raw_text: Optional[str]
    structured_json: Optional[Any]
    uploaded_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("structured_json", mode="before")
    @classmethod
    def deserialize_structured(cls, v: Any) -> Any:
        return _deserialize_json_field(v)


# ── Job descriptions ───────────────────────────────────────────────────────────

class JobDescriptionOut(BaseModel):
    id: int
    raw_text: str
    extracted_requirements_json: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("extracted_requirements_json", mode="before")
    @classmethod
    def deserialize_requirements(cls, v: Any) -> Any:
        return _deserialize_json_field(v)


# ── Tailoring ──────────────────────────────────────────────────────────────────

class TailorRequest(BaseModel):
    resume_id: int
    job_description_text: str

    @field_validator("resume_id")
    @classmethod
    def positive_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("resume_id must be a positive integer")
        return v

    @field_validator("job_description_text", mode="before")
    @classmethod
    def validate_jd_text(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_description_text must be a string")
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Job description must be at least 50 characters")
        if len(v) > 15_000:
            raise ValueError("Job description must not exceed 15,000 characters")
        return v


class TailoredResumeOut(BaseModel):
    id: int
    resume_id: int
    job_description_id: int
    tailored_content_json: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("tailored_content_json", mode="before")
    @classmethod
    def deserialize_content(cls, v: Any) -> Any:
        return _deserialize_json_field(v)


# ── Cover letters ──────────────────────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    tailored_resume_id: int

    @field_validator("tailored_resume_id")
    @classmethod
    def positive_cl_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("tailored_resume_id must be a positive integer")
        return v


class CoverLetterUpdateRequest(BaseModel):
    content: str

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("content must be a string")
        v = v.strip()
        if len(v) < 20:
            raise ValueError("Cover letter content must be at least 20 characters")
        if len(v) > 10_000:
            raise ValueError("Cover letter content must not exceed 10,000 characters")
        return v


class CoverLetterOut(BaseModel):
    id: int
    tailored_resume_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── History ────────────────────────────────────────────────────────────────────

class HistoryItemOut(BaseModel):
    id: int
    resume_filename: str
    role_title: Optional[str]
    seniority_level: Optional[str]
    match_score: Optional[int]
    alignment_note: Optional[str]
    has_cover_letter: bool
    cover_letter_id: Optional[int]
    created_at: datetime


# ── Match ──────────────────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    resume_id: int
    job_description_text: str

    @field_validator("resume_id")
    @classmethod
    def positive_resume_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("resume_id must be a positive integer")
        return v

    @field_validator("job_description_text", mode="before")
    @classmethod
    def validate_jd(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_description_text must be a string")
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Job description must be at least 10 characters")
        if len(v) > 20_000:
            raise ValueError("Job description must not exceed 20,000 characters")
        return v


class SkillMatchDetail(BaseModel):
    skill: str
    match_type: str
    confidence: float
    resume_sections: List[str]


class MatchResultOut(BaseModel):
    id: int
    resume_id: int
    overall_score: int
    required_skill_score: float
    preferred_skill_score: float
    experience_score: float
    education_score: float
    matched_requirements: List[SkillMatchDetail]
    partial_matches: List[SkillMatchDetail]
    missing_requirements: List[str]
    missing_preferred: List[str]
    resume_evidence: Any
    recommendations: List[str]
    disclaimer: str
    jd_role_title: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator(
        "matched_requirements", "partial_matches", "missing_requirements",
        "missing_preferred", "recommendations",
        mode="before",
    )
    @classmethod
    def parse_list_field(cls, v: Any) -> Any:
        return _deserialize_json_field(v) if isinstance(v, str) else v

    @field_validator("resume_evidence", mode="before")
    @classmethod
    def parse_evidence(cls, v: Any) -> Any:
        return _deserialize_json_field(v) if isinstance(v, str) else v


class MatchSummaryOut(BaseModel):
    id: int
    resume_id: int
    overall_score: int
    jd_role_title: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("jd_role_title", mode="before")
    @classmethod
    def parse_role_title(cls, v: Any) -> Any:
        return v


# ── Improvement ────────────────────────────────────────────────────────────────

class ImproveRequest(BaseModel):
    resume_id: int
    job_description_text: str

    @field_validator("resume_id")
    @classmethod
    def positive_improve_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("resume_id must be a positive integer")
        return v

    @field_validator("job_description_text", mode="before")
    @classmethod
    def validate_improve_jd(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_description_text must be a string")
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Job description must be at least 50 characters")
        if len(v) > 15_000:
            raise ValueError("Job description must not exceed 15,000 characters")
        return v


class SuggestionUpdate(BaseModel):
    """Body for PATCH /improve/{id}/suggestion"""
    section: str          # "experience" | "project" | "skills" | "summary"
    job_index: Optional[int] = None      # for experience sections
    project_index: Optional[int] = None  # for project sections
    bullet_index: Optional[int] = None   # for bullet-level updates
    status: str           # "accepted" | "rejected" | "pending"
    custom_text: Optional[str] = None

    @field_validator("section")
    @classmethod
    def valid_section(cls, v: str) -> str:
        if v not in ("experience", "project", "skills", "summary"):
            raise ValueError("section must be experience, project, skills, or summary")
        return v

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("accepted", "rejected", "pending"):
            raise ValueError("status must be accepted, rejected, or pending")
        return v

    @field_validator("custom_text", mode="before")
    @classmethod
    def trim_custom(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v


class ImprovementSessionSummaryOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    status: str
    total_suggestions: int
    accepted_count: int
    created_at: datetime
    tailored_resume_id: Optional[int]

    model_config = {"from_attributes": True}


class ImprovementSessionOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    status: str
    session_data: Any   # the full session_json parsed as dict
    total_suggestions: int
    accepted_count: int
    created_at: datetime
    tailored_resume_id: Optional[int]

    model_config = {"from_attributes": True}


# ── Skill Gap Analyzer ──────────────────────────────────────────────────────────

class SkillGapRequest(BaseModel):
    resume_id: int
    job_description_text: str

    @field_validator("resume_id")
    @classmethod
    def positive_gap_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("resume_id must be a positive integer")
        return v

    @field_validator("job_description_text", mode="before")
    @classmethod
    def validate_gap_jd(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_description_text must be a string")
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Job description must be at least 50 characters")
        if len(v) > 20_000:
            raise ValueError("Job description must not exceed 20,000 characters")
        return v


class RoadmapItemUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_item_status(cls, v: str) -> str:
        if v not in ("not_started", "in_progress", "completed"):
            raise ValueError("status must be not_started, in_progress, or completed")
        return v


class LearningRoadmapSummaryOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    overall_score: int
    gap_count: int
    completed_count: int
    total_roadmap_items: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LearningRoadmapOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    overall_score: int
    skill_classifications: Any  # list of SkillClassification dicts
    roadmap_items: Any          # list of RoadmapItem dicts
    disclaimer: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Job Application Tracker ────────────────────────────────────────────────────

class JobApplicationCreate(BaseModel):
    company_name: str
    job_title: str
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    status: str = "saved"
    application_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    notes: Optional[str] = None
    resume_id: Optional[int] = None
    tailored_resume_id: Optional[int] = None

    @field_validator("company_name", mode="before")
    @classmethod
    def validate_company(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("company_name must be a string")
        v = v.strip()
        if not v:
            raise ValueError("company_name is required")
        if len(v) > 200:
            raise ValueError("company_name must not exceed 200 characters")
        return v

    @field_validator("job_title", mode="before")
    @classmethod
    def validate_title(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_title must be a string")
        v = v.strip()
        if not v:
            raise ValueError("job_title is required")
        if len(v) > 200:
            raise ValueError("job_title must not exceed 200 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _TRACKER_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(_TRACKER_STATUSES))}")
        return v

    @field_validator("job_url", mode="before")
    @classmethod
    def validate_url(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("job_url must be a string")
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("job_url must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("job_url must not exceed 2048 characters")
        return v

    @field_validator("job_description", mode="before")
    @classmethod
    def validate_jd(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("job_description must be a string")
        v = v.strip()
        if len(v) > 20_000:
            raise ValueError("job_description must not exceed 20,000 characters")
        return v or None

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("notes must be a string")
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("notes must not exceed 5,000 characters")
        return v or None

    @field_validator("resume_id", "tailored_resume_id", mode="before")
    @classmethod
    def validate_optional_id(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        return v


class JobApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    status: Optional[str] = None
    application_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    notes: Optional[str] = None
    resume_id: Optional[int] = None
    tailored_resume_id: Optional[int] = None

    @field_validator("company_name", mode="before")
    @classmethod
    def validate_update_company(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("company_name must be a string")
        v = v.strip()
        if not v:
            raise ValueError("company_name cannot be empty")
        if len(v) > 200:
            raise ValueError("company_name must not exceed 200 characters")
        return v

    @field_validator("job_title", mode="before")
    @classmethod
    def validate_update_title(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("job_title must be a string")
        v = v.strip()
        if not v:
            raise ValueError("job_title cannot be empty")
        if len(v) > 200:
            raise ValueError("job_title must not exceed 200 characters")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_update_status(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if v not in _TRACKER_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(_TRACKER_STATUSES))}")
        return v

    @field_validator("job_url", mode="before")
    @classmethod
    def validate_update_url(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("job_url must be a string")
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("job_url must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("job_url must not exceed 2048 characters")
        return v

    @field_validator("notes", "job_description", mode="before")
    @classmethod
    def validate_update_text(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            raise ValueError("field must be a string")
        return v.strip() or None

    @field_validator("resume_id", "tailored_resume_id", mode="before")
    @classmethod
    def validate_update_id(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        return v


class JobApplicationOut(BaseModel):
    id: int
    company_name: str
    job_title: str
    job_description: Optional[str]
    job_url: Optional[str]
    status: str
    application_date: Optional[datetime]
    deadline: Optional[datetime]
    interview_date: Optional[datetime]
    notes: Optional[str]
    resume_id: Optional[int]
    tailored_resume_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackerStatsOut(BaseModel):
    total: int
    saved: int
    active: int       # applied + assessment + interview
    interviews: int
    offers: int
    rejected: int


# ── Interview Preparation ──────────────────────────────────────────────────────

class InterviewRequest(BaseModel):
    resume_id: int
    job_description_text: str

    @field_validator("resume_id")
    @classmethod
    def positive_interview_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("resume_id must be a positive integer")
        return v

    @field_validator("job_description_text", mode="before")
    @classmethod
    def validate_interview_jd(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("job_description_text must be a string")
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Job description must be at least 50 characters")
        if len(v) > 20_000:
            raise ValueError("Job description must not exceed 20,000 characters")
        return v


class AnswerSubmitRequest(BaseModel):
    question_index: int
    user_answer: str

    @field_validator("question_index")
    @classmethod
    def non_negative_index(cls, v: int) -> int:
        if v < 0:
            raise ValueError("question_index must be non-negative")
        return v

    @field_validator("user_answer", mode="before")
    @classmethod
    def validate_answer(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("user_answer must be a string")
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Answer must be at least 10 characters")
        if len(v) > 5_000:
            raise ValueError("Answer must not exceed 5,000 characters")
        return v


class InterviewQuestionOut(BaseModel):
    index: int = Field(ge=0)
    type: Literal["technical", "behavioral", "hr", "project"]
    question: str = Field(min_length=1, max_length=2_000)
    guidance: str = Field(default="", max_length=1_000)
    answer_structure: str = Field(default="", max_length=1_000)


class InterviewFeedbackOut(BaseModel):
    relevance_score: int = Field(ge=1, le=5)
    clarity_score: int = Field(ge=1, le=5)
    structure_score: int = Field(ge=1, le=5)
    technical_score: Optional[int] = Field(default=None, ge=1, le=5)
    overall_score: int = Field(ge=1, le=5)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    feedback_text: str = ""
    disclaimer: str
    criteria: dict[str, str] = Field(default_factory=dict)


class InterviewSessionSummaryOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    question_count: int
    answered_count: int   # distinct questions with at least one answer
    answer_count: int     # total submissions
    created_at: datetime


class InterviewSessionOut(BaseModel):
    id: int
    resume_id: int
    role_title: Optional[str]
    questions: List[InterviewQuestionOut]
    question_count: int
    answered_count: int
    answer_count: int
    created_at: datetime


class InterviewAnswerOut(BaseModel):
    id: int
    session_id: int
    question_index: int
    question_text: str
    user_answer: str
    feedback: Optional[InterviewFeedbackOut]       # None if evaluation not yet done or failed
    evaluation_error: Optional[str]
    created_at: datetime


class QuestionAttemptsOut(BaseModel):
    question_index: int
    question: InterviewQuestionOut
    attempts: List[Any]    # list of InterviewAnswerOut dicts
    attempt_count: int
