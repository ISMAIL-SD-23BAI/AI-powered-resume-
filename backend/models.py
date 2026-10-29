from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")
    job_descriptions = relationship("JobDescription", back_populates="owner", cascade="all, delete-orphan")
    tailored_resumes = relationship("TailoredResume", back_populates="owner", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="owner", cascade="all, delete-orphan")
    improvement_sessions = relationship("ImprovementSession", back_populates="owner", cascade="all, delete-orphan")
    learning_roadmaps = relationship("LearningRoadmap", back_populates="owner", cascade="all, delete-orphan")
    job_applications = relationship("JobApplication", back_populates="owner", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="owner", cascade="all, delete-orphan")
    interview_answers = relationship("InterviewAnswer", back_populates="owner", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text)
    structured_json = Column(Text)           # JSON: {skills, experience, education, projects}
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="resumes")
    tailored_resumes = relationship("TailoredResume", back_populates="source_resume")
    match_results = relationship("MatchResult", back_populates="resume", cascade="all, delete-orphan")
    improvement_sessions = relationship("ImprovementSession", back_populates="resume", cascade="all, delete-orphan")
    learning_roadmaps = relationship("LearningRoadmap", back_populates="resume", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="resume", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    extracted_requirements_json = Column(Text)   # JSON: {role_title, required_skills, ...}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="job_descriptions")
    tailored_resumes = relationship("TailoredResume", back_populates="job_description")


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    tailored_content_json = Column(Text)         # JSON: {tailored_resume, alignment_note, match_score, ...}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="tailored_resumes")
    source_resume = relationship("Resume", back_populates="tailored_resumes")
    job_description = relationship("JobDescription", back_populates="tailored_resumes")
    cover_letters = relationship("CoverLetter", back_populates="tailored_resume", cascade="all, delete-orphan")


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    tailored_resume_id = Column(Integer, ForeignKey("tailored_resumes.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tailored_resume = relationship("TailoredResume", back_populates="cover_letters")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_text = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)  # full JSON result from matching engine
    overall_score = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="match_results")
    resume = relationship("Resume", back_populates="match_results")


class ImprovementSession(Base):
    __tablename__ = "improvement_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_text = Column(Text, nullable=False)
    session_json = Column(Text, nullable=False)  # full session state as JSON
    status = Column(String(32), nullable=False, default="active")  # active | applied
    tailored_resume_id = Column(Integer, ForeignKey("tailored_resumes.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="improvement_sessions")
    resume = relationship("Resume", back_populates="improvement_sessions")
    tailored_resume = relationship("TailoredResume", foreign_keys=[tailored_resume_id])


class LearningRoadmap(Base):
    __tablename__ = "learning_roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_text = Column(Text, nullable=False)
    role_title = Column(String(255))
    overall_score = Column(Integer, nullable=False, default=0)
    skill_classifications_json = Column(Text, nullable=False)  # list of SkillClassification dicts
    roadmap_items_json = Column(Text, nullable=False, default="[]")  # list of RoadmapItem dicts
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="learning_roadmaps")
    resume = relationship("Resume", back_populates="learning_roadmaps")


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    job_description = Column(Text)
    job_url = Column(String(2048))
    status = Column(String(32), nullable=False, default="saved")
    # saved | applied | assessment | interview | offer | rejected
    application_date = Column(DateTime(timezone=True))
    deadline = Column(DateTime(timezone=True))
    interview_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    tailored_resume_id = Column(Integer, ForeignKey("tailored_resumes.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="job_applications")
    resume = relationship("Resume", foreign_keys=[resume_id])
    tailored_resume = relationship("TailoredResume", foreign_keys=[tailored_resume_id])


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_description_text = Column(Text, nullable=False)
    role_title = Column(String(255))
    questions_json = Column(Text, nullable=False, default="[]")
    question_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="interview_sessions")
    resume = relationship("Resume", back_populates="interview_sessions")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_index = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=False)
    feedback_json = Column(Text)          # null until evaluation completes
    evaluation_error = Column(Text)       # set if evaluation failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("InterviewSession", back_populates="answers")
    owner = relationship("User", back_populates="interview_answers")
