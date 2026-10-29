"""
Two-step resume tailoring via Claude.

Step 1 — extract_jd_requirements(jd_text)
  Parses the job description into a structured requirements dict.

Step 2 — tailor_resume(structured_resume, requirements)
  Rewrites resume sections to align with the role.
  NEVER fabricates experience, skills, or metrics not in the original resume.
"""
import json
import re
from typing import Any

from services.bedrock_client import get_anthropic_client, get_model


# ── Prompt: JD requirements extraction ────────────────────────────────────────

_JD_EXTRACTION_SYSTEM = """\
You are a technical recruiter parsing a job description.
Extract key information and return it as a single valid JSON object.
No markdown fences, no commentary — output must start with { and end with }.

Required keys (use empty arrays/strings if data is absent):
- "role_title": string — the job title
- "seniority_level": string — one of: intern / junior / mid-level / senior / lead / principal / staff / director
- "required_skills": array of strings — explicitly required technical skills and tools
- "preferred_skills": array of strings — nice-to-have or preferred skills
- "key_responsibilities": array of strings — up to 6 concise bullet points of what the person will do
- "keywords": array of strings — important domain/industry terms, technologies, and methodologies
- "industry": string — the domain or sector (e.g. "fintech", "healthcare", "e-commerce")

Return ONLY the JSON object."""


# ── Prompt: resume tailoring (fabrication-proof) ──────────────────────────────

_TAILORING_SYSTEM = """\
You are a professional resume writer. Your job is to tailor a candidate's resume
for a specific role by emphasising what is most relevant — using ONLY information
that already exists in their original resume.

═══════════════════════════════════════════════════════════════
MANDATORY HONESTY RULES — violating these produces a fraudulent resume:
1. Use ONLY skills, tools, technologies, job titles, companies, dates, degrees,
   and accomplishments that are explicitly present in the original resume.
2. Do NOT add any skill, certification, or tool the candidate has not listed.
3. Do NOT invent numbers, metrics, percentages, or quantifications not in the original.
4. Do NOT infer that the candidate has expertise in something they have not mentioned.
5. If a required skill is absent, list it in "missing_skills" — do not add it to the resume.
6. You MAY rephrase existing bullet points to use JD terminology if the underlying
   meaning is preserved and the candidate demonstrably has that skill/experience.
7. You MAY reorder bullets and sections so the most relevant items appear first.
8. You MAY write a targeted "summary" section, but only using facts verifiable
   from the original resume content.
═══════════════════════════════════════════════════════════════

Return a single valid JSON object — no markdown fences, no commentary.
Output must start with { and end with }."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> str:
    """Extract the outermost JSON object from text that may have preamble or trailing content."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _call_claude(system: str, user_content: str, max_tokens: int) -> dict:
    client = get_anthropic_client()
    response = client.messages.create(
        model=get_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    raw = _extract_json_object(_strip_fences(response.content[0].text))
    return json.loads(raw)


def extract_jd_requirements(jd_text: str) -> dict:
    """Step 1: Parse job description into structured requirements."""
    return _call_claude(_JD_EXTRACTION_SYSTEM, jd_text, max_tokens=1024)


def tailor_resume(structured_resume: dict, requirements: dict) -> dict:
    """
    Step 2: Tailor resume to match JD requirements without fabrication.

    Returns a dict with keys:
      tailored_resume   — same shape as structured_resume + optional "summary"
      alignment_note    — 2-3 sentences on fit based solely on existing experience
      match_score       — integer 0-100, honest fit assessment
      matched_skills    — JD skills the candidate actually has
      missing_skills    — required JD skills absent from the resume
    """
    user_content = (
        "## Original Resume (JSON)\n\n"
        + json.dumps(structured_resume, indent=2)
        + "\n\n## Target Job Requirements (JSON)\n\n"
        + json.dumps(requirements, indent=2)
        + "\n\n## Instructions\n\n"
        "Tailor the resume for this role following the honesty rules in the system prompt.\n"
        "Return a JSON object with exactly these keys:\n\n"
        '- "tailored_resume": object with keys:\n'
        '    "summary" (string — a 2-3 sentence targeted profile; omit if nothing relevant to say),\n'
        '    "skills" (array of strings — reordered/filtered from original, most relevant first),\n'
        '    "experience" (array of {title, company, dates, bullets} — bullets rewritten/reordered for relevance),\n'
        '    "education" (array of {degree, institution, dates} — unchanged from original),\n'
        '    "projects" (array of {name, description, bullets} — reordered/rewritten for relevance)\n\n'
        '- "alignment_note": string — 2-3 honest sentences on how well this candidate fits the role,\n'
        '  based only on their existing experience\n\n'
        '- "match_score": integer 0-100 — realistic fit score (do not inflate);\n'
        '  100 = perfect match, 0 = completely unrelated background\n\n'
        '- "matched_skills": array of strings — skills/tools/keywords from the JD that the candidate has\n\n'
        '- "missing_skills": array of strings — required JD skills the candidate does NOT have\n\n'
        "Critical reminder: use ONLY information from the original resume. Never fabricate."
    )
    return _call_claude(_TAILORING_SYSTEM, user_content, max_tokens=4096)
