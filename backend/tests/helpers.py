"""
Shared test helpers: mock data, mock factory, and auth utilities.
Import these in test files — do NOT import test fixtures from here.
"""
import io
import json
from unittest.mock import MagicMock

# ── Mock AI responses ──────────────────────────────────────────────────────────

MOCK_STRUCTURED_RESUME = {
    "skills": ["Python", "FastAPI", "SQLAlchemy", "Docker"],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "ACME Corp",
            "dates": "2022-2024",
            "bullets": [
                "Built REST APIs using Python and FastAPI",
                "Maintained SQL databases with SQLAlchemy",
            ],
        }
    ],
    "education": [
        {
            "degree": "B.Tech Computer Science and Engineering (AI & ML)",
            "institution": "Test University",
            "dates": "2018-2022",
        }
    ],
    "projects": [
        {
            "name": "Resume Tailor",
            "description": "AI-powered resume tailoring tool",
            "bullets": ["Built with FastAPI and Claude API"],
        }
    ],
}

MOCK_JD_REQUIREMENTS = {
    "role_title": "Software Engineer",
    "seniority_level": "junior",
    "required_skills": ["Python", "FastAPI"],
    "preferred_skills": ["Docker"],
    "key_responsibilities": ["Build REST APIs", "Write tests"],
    "keywords": ["Python", "FastAPI", "REST", "API"],
    "industry": "tech",
}

MOCK_TAILORED = {
    "tailored_resume": {
        "summary": "Python engineer with FastAPI and REST API experience.",
        "skills": ["Python", "FastAPI", "SQLAlchemy"],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "ACME Corp",
                "dates": "2022-2024",
                "bullets": ["Built REST APIs using FastAPI"],
            }
        ],
        "education": [
            {
                "degree": "B.Tech Computer Science and Engineering (AI & ML)",
                "institution": "Test University",
                "dates": "2018-2022",
            }
        ],
        "projects": [],
    },
    "alignment_note": "Strong Python and FastAPI match for this role.",
    "match_score": 78,
    "matched_skills": ["Python", "FastAPI"],
    "missing_skills": ["Docker"],
}

MOCK_COVER_LETTER = (
    "With three years of REST API development at ACME Corp using FastAPI, "
    "I built the exact kind of services your Software Engineer role requires.\n\n"
    "The team's focus on Python microservices maps directly to my work maintaining "
    "production SQLAlchemy models and FastAPI endpoints at ACME.\n\n"
    "I am available to start immediately and welcome a conversation this week."
)


# ── Mock client factory ────────────────────────────────────────────────────────

def make_mock_client(response_text: str) -> MagicMock:
    """Return a mock Anthropic client whose .messages.create() returns response_text."""
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


# ── PDF fixture factory ────────────────────────────────────────────────────────

def make_test_pdf(text: str = "Software Engineer with Python and FastAPI experience.") -> bytes:
    """Build a minimal valid PDF using ReportLab (already installed)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    doc.build([Paragraph(text, styles["Normal"])])
    return buf.getvalue()


# ── Auth helpers ───────────────────────────────────────────────────────────────

def register_and_login(
    client,
    email: str = "test@example.com",
    password: str = "Password123!",
    full_name: str = "Test User",
) -> str:
    """Register a user and return a valid JWT token string."""
    client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": full_name},
    )
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Mock improvement responses ─────────────────────────────────────────────────

MOCK_IMPROVEMENT_CLAUDE_OUTPUT = {
    "role_analysis": "Strong Python and FastAPI match; lacks Kubernetes experience.",
    "summary_suggestion": {
        "suggested": "Python engineer with 2 years of FastAPI REST API development at ACME Corp.",
        "reason": "Directly mentions FastAPI and REST API experience matching the JD requirements.",
    },
    "experience_suggestions": [
        {
            "job_index": 0,
            "bullet_suggestions": [
                {
                    "bullet_index": 0,
                    "suggested": "Developed scalable REST APIs using Python and FastAPI for ACME Corp",
                    "reason": "Emphasises FastAPI and REST APIs which are primary JD requirements.",
                    "changes_facts": False,
                    "unsupported_claims": [],
                },
                {
                    "bullet_index": 1,
                    "suggested": "Maintained production SQL databases with SQLAlchemy ORM",
                    "reason": "Adds ORM keyword from JD while preserving original meaning.",
                    "changes_facts": False,
                    "unsupported_claims": [],
                },
            ],
        }
    ],
    "project_suggestions": [
        {
            "project_index": 0,
            "bullet_suggestions": [
                {
                    "bullet_index": 0,
                    "suggested": "Built AI-powered resume tailoring tool using FastAPI and Anthropic Claude API",
                    "reason": "Highlights Claude API usage which aligns with AI-related JD requirements.",
                    "changes_facts": False,
                    "unsupported_claims": [],
                }
            ],
        }
    ],
    "skills_reorder": ["Python", "FastAPI", "SQLAlchemy", "Docker"],
    "skills_reason": "Python and FastAPI moved to front as primary JD requirements.",
}


# ── Mock skill gap / roadmap responses ────────────────────────────────────────

# A canned compute_from_structured result with mixed classifications
MOCK_MATCH_FOR_GAP = {
    "overall_score": 58,
    "required_skill_score": 60.0,
    "preferred_skill_score": 40.0,
    "experience_score": 65.0,
    "education_score": 90.0,
    "matched_requirements": [
        {
            "skill": "python",
            "match_type": "exact",
            "confidence": 1.0,
            "resume_sections": ["skills", "experience"],
        },
        {
            "skill": "fastapi",
            "match_type": "semantic",
            "confidence": 0.85,
            "resume_sections": ["experience"],
        },
    ],
    "partial_matches": [
        {
            "skill": "docker",
            "match_type": "partial",
            "confidence": 0.55,
            "resume_sections": ["skills"],  # only in skills list → requires_verification
        },
    ],
    "missing_requirements": ["kubernetes", "ci/cd"],
    "missing_preferred": ["terraform"],
    "resume_evidence": {"python": ["skills", "experience"], "fastapi": ["experience"]},
    "recommendations": ["Add kubernetes experience to your resume."],
    "disclaimer": "A skill marked 'not evidenced' was not found in the uploaded resume.",
    "jd_role_title": "Backend Engineer",
}

# ── Mock interview responses ──────────────────────────────────────────────────

MOCK_INTERVIEW_QUESTIONS_OUTPUT = [
    {
        "index": 0,
        "type": "technical",
        "question": "Can you explain how you used FastAPI to build REST APIs at ACME Corp?",
        "guidance": "Discuss routing, dependency injection, and any performance considerations.",
    },
    {
        "index": 1,
        "type": "technical",
        "question": "How did you design your SQLAlchemy models in the Resume Tailor project?",
        "guidance": "Mention relationships, constraints, and any migration strategy you used.",
    },
    {
        "index": 2,
        "type": "behavioral",
        "question": "Describe a time when you had to debug a production issue under pressure.",
        "guidance": "Use the STAR framework: situation, task, action, result.",
    },
    {
        "index": 3,
        "type": "behavioral",
        "question": "Tell me about a project where you had to learn a new technology quickly.",
        "guidance": "Focus on how you approached the learning and what outcomes you achieved.",
    },
    {
        "index": 4,
        "type": "hr",
        "question": "Why are you interested in this Software Engineer role?",
        "guidance": "Connect your background and goals to the specific responsibilities listed.",
    },
    {
        "index": 5,
        "type": "project",
        "question": "Walk me through the architecture of the Resume Tailor project you built.",
        "guidance": "Explain the key components, how they interact, and design trade-offs you made.",
    },
    {
        "index": 6,
        "type": "technical",
        "question": "How does Docker improve your development workflow?",
        "guidance": "Discuss containerisation benefits, image building, and deployment consistency.",
    },
    {
        "index": 7,
        "type": "behavioral",
        "question": "Describe a situation where you disagreed with a technical decision and how you handled it.",
        "guidance": "Show communication skills, respect for process, and outcome focus.",
    },
]

MOCK_INTERVIEW_FEEDBACK_OUTPUT = {
    "relevance_score": 4,
    "clarity_score": 4,
    "structure_score": 3,
    "technical_score": 4,
    "overall_score": 4,
    "strengths": [
        "Clearly connected FastAPI experience to the question asked.",
        "Provided a concrete example from a real project.",
    ],
    "improvements": [
        "Add more detail about specific performance trade-offs.",
        "Quantify impact where possible (e.g., request throughput improvements).",
    ],
    "unsupported_claims": [],
    "criteria": {
        "relevance": "How directly the answer addresses the question and role.",
        "clarity": "How easy the answer is to follow.",
        "structure": "How logically the answer is organized.",
        "technical": "Accuracy and completeness of technical reasoning.",
        "scale": "1 = needs development; 3 = adequate; 5 = clear and well-supported.",
    },
    "feedback_text": (
        "Your answer demonstrates solid FastAPI knowledge grounded in real experience. "
        "To strengthen it further, quantify the impact of your work and discuss specific "
        "design decisions like async routing or background tasks."
    ),
    "disclaimer": (
        "This evaluation is for practice purposes only and does not predict performance "
        "in real interviews or hiring decisions."
    ),
}


MOCK_ROADMAP_CLAUDE_OUTPUT = [
    {
        "skill": "kubernetes",
        "why_it_matters": "Kubernetes is the primary container orchestration platform used for deploying Backend Engineer services in this role.",
        "learning_sequence": [
            "Understand container fundamentals using Docker (which you already know)",
            "Learn Kubernetes core concepts: pods, deployments, services, and namespaces",
            "Practice deploying a simple FastAPI application to a local Kubernetes cluster",
            "Explore configuration management with ConfigMaps and Secrets",
            "Study basic cluster monitoring and troubleshooting commands",
        ],
        "practical_project": "Deploy the Resume Tailor FastAPI application you have already built to a local Kubernetes cluster using minikube, including a Deployment, Service, and ConfigMap for environment variables.",
        "resources_note": "search: kubernetes official documentation, search: kubernetes for python developers",
    },
    {
        "skill": "ci/cd",
        "why_it_matters": "CI/CD pipelines are required for the Backend Engineer role to automate testing and deployment of REST API services.",
        "learning_sequence": [
            "Understand the purpose of continuous integration and deployment",
            "Set up a basic pipeline that runs your existing Python tests automatically",
            "Add a build step that creates a Docker image on each commit",
            "Learn to configure environment-specific deployments",
            "Explore rollback strategies for failed deployments",
        ],
        "practical_project": "Create a CI pipeline for the Resume Tailor project that runs pytest and builds a Docker image automatically on each code push.",
        "resources_note": "search: GitHub Actions tutorial for Python, search: GitLab CI CD beginner guide",
    },
]
