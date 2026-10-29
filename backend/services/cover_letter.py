"""
Cover letter generation via Claude.

Inputs: tailored resume JSON, extracted JD requirements, raw JD text, candidate name.
Output: 3-4 paragraph cover letter that cites specific JD requirements and resume
        achievements — no generic filler, no fabricated experience.
"""
import json
import re

from services.bedrock_client import get_anthropic_client, get_model


_SYSTEM = """\
You are an expert cover letter writer. Your letters are remembered because they are
specific, confident, and free of the hollow phrases that plague most cover letters.

════════════════════════════════════════════════════════════
MANDATORY STYLE RULES:

Opening paragraph
  • Start with a strong, direct sentence naming the specific role and immediately
    surfacing the candidate's single most relevant concrete achievement.
  • FORBIDDEN openers (any variant): "I am excited to apply", "I am writing to express
    my interest", "I am a passionate", "I have always been passionate about",
    "I came across this posting", "Please consider my application".

Body paragraph(s) — 1 or 2 paragraphs
  • Connect SPECIFIC requirements from the JD to SPECIFIC accomplishments, job titles,
    companies, technologies, and outcomes from the resume.
  • Name real things: actual job titles, company names, project names, skill names.
  • Do NOT write vague claims like "I have strong communication skills" or
    "I work well in fast-paced environments" unless backed by a concrete example.

Closing paragraph
  • One or two direct sentences. State availability and invite a conversation.
  • FORBIDDEN closings: "I look forward to discussing this opportunity",
    "Thank you for your time and consideration", "I am eager to contribute",
    "I am confident I would be a great fit".

General
  • Tone: confident, direct, professional. No adjective stacking
    ("results-driven self-motivated team player").
  • Length: 250–380 words, 3–4 paragraphs.
  • If the JD mentions a company name, use it. Never write [Company Name].
  • Do NOT invent any experience, skill, achievement, or metric not present in the resume.
  • Return ONLY the cover letter body text — no subject line, no date, no salutation
    ("Dear Hiring Manager"), no closing salutation ("Sincerely, …"), no signature block.
════════════════════════════════════════════════════════════"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_cover_letter(
    tailored_resume: dict,
    requirements: dict,
    jd_raw_text: str,
    candidate_name: str | None,
) -> str:
    """
    Generate a personalized cover letter.

    tailored_resume  — the tailored_resume sub-object from TailoredResume.tailored_content_json
    requirements     — the extracted_requirements_json from JobDescription
    jd_raw_text      — the full raw job description text (for company name, tone, details)
    candidate_name   — the user's full name (may be None)
    """
    name_line = f"Candidate name: {candidate_name}" if candidate_name else "Candidate name: not provided"

    user_content = (
        f"{name_line}\n\n"
        "## Tailored Resume (JSON)\n\n"
        + json.dumps(tailored_resume, indent=2)
        + "\n\n## Extracted Job Requirements (JSON)\n\n"
        + json.dumps(requirements, indent=2)
        + "\n\n## Full Job Description (raw text)\n\n"
        + jd_raw_text
        + "\n\n## Task\n\n"
        "Write the cover letter following the style rules in the system prompt.\n"
        "Cite concrete achievements from the resume and specific requirements from the JD.\n"
        "Return only the letter body — no salutation, no sign-off."
    )

    client = get_anthropic_client()
    response = client.messages.create(
        model=get_model(),
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    return _strip_fences(response.content[0].text)
