import json
import re
from typing import Any, Optional

from services.bedrock_client import get_anthropic_client, get_model

_VALID_TYPES = {"technical", "behavioral", "hr", "project"}

_SYSTEM_GENERATE = """You are an expert technical interviewer preparing practice questions.

════════════════════════════════════════
ABSOLUTE RULES — never violate these:
1. Generate ONLY questions that can be answered using information in the candidate's resume.
2. Generate between 8 and 12 questions total.
3. Each question must have a "type": one of "technical", "behavioral", "hr", or "project".
4. Each question must have an "index" starting at 0 and incrementing by 1.
5. Include a mix of types: at least 2 technical, 2 behavioral, 1 hr, 1 project.
6. Include "guidance": a 1-2 sentence hint on what a strong answer covers.
7. Include "answer_structure": a short reusable outline (for behavioral: STAR; for technical: approach, trade-offs, result; for HR: concise context and motivation).
8. Include at least one question grounded in a named project or experience from the resume when available; mention its actual name/details.
9. Never invent job requirements not mentioned in the job description.
10. Never predict hiring outcomes or suitability.
11. Respond with a JSON array only — no markdown, no prose.
════════════════════════════════════════

Output format (JSON array, no fences):
[
  {
    "index": 0,
    "type": "technical",
    "question": "...",
    "guidance": "..."
    ,"answer_structure": "..."
  },
  ...
]"""

_SYSTEM_EVALUATE = """You are an expert interview coach providing constructive feedback on practice answers.

════════════════════════════════════════
ABSOLUTE RULES — never violate these:
1. Score each dimension 1-5 (integers only). Never use 0 or values above 5.
2. technical_score must be null for behavioral and hr questions.
3. Overall score is the weighted average: relevance 30%, clarity 25%, structure 25%, technical 20% (skip technical for behavioral/hr, reweight).
4. If the candidate's answer contains claims not evidenced in their resume, list them in "unsupported_claims" as: "Claim not evidenced in resume: <claim>". Never assert the claim is false.
5. Never predict actual interview performance or hiring probability.
6. The "disclaimer" field MUST always be: "This evaluation is for practice purposes only and does not predict performance in real interviews or hiring decisions."
7. Keep "feedback_text" constructive, educational, and specific to the answer given.
8. unsupported_claims must only identify answer statements not evidenced by the supplied resume; describe these as unverified, never false.
9. Respond with a single JSON object only — no markdown, no prose.
════════════════════════════════════════

Output format (JSON object, no fences):
{
  "relevance_score": 1-5,
  "clarity_score": 1-5,
  "structure_score": 1-5,
  "technical_score": 1-5 or null,
  "overall_score": 1-5,
  "strengths": ["..."],
  "improvements": ["..."],
  "unsupported_claims": [],
  "feedback_text": "...",
  "disclaimer": "This evaluation is for practice purposes only and does not predict performance in real interviews or hiring decisions."
}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_array(text: str) -> list:
    text = _strip_fences(text)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON array found", text, 0)
    return json.loads(text[start : end + 1])


def _extract_json_object(text: str) -> dict:
    text = _strip_fences(text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    return json.loads(text[start : end + 1])


def _validate_question(item: Any, expected_index: int) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    q_type = item.get("type", "")
    if q_type not in _VALID_TYPES:
        return None
    if not isinstance(item.get("question"), str) or not item["question"].strip():
        return None
    guidance = item.get("guidance", "")
    return {
        "index": expected_index,
        "type": q_type,
        "question": item["question"].strip(),
        "guidance": guidance.strip() if isinstance(guidance, str) else "",
        "answer_structure": (item.get("answer_structure", "") or "").strip()
        if isinstance(item.get("answer_structure", ""), str) else "",
    }


def _clamp_score(val: Any) -> int:
    try:
        v = int(val)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, v))


def _validate_feedback(raw: dict) -> dict:
    q_type = raw.get("_question_type", "technical")

    relevance = _clamp_score(raw.get("relevance_score", 3))
    clarity = _clamp_score(raw.get("clarity_score", 3))
    structure = _clamp_score(raw.get("structure_score", 3))

    raw_tech = raw.get("technical_score")
    if q_type in ("behavioral", "hr") or raw_tech is None:
        technical = None
    else:
        technical = _clamp_score(raw_tech)

    if technical is not None:
        overall = round((relevance * 0.30 + clarity * 0.25 + structure * 0.25 + technical * 0.20))
    else:
        overall = round((relevance * 0.375 + clarity * 0.3125 + structure * 0.3125))
    overall = max(1, min(5, overall))

    disclaimer = "This evaluation is for practice purposes only and does not predict performance in real interviews or hiring decisions."

    strengths = raw.get("strengths", [])
    if not isinstance(strengths, list):
        strengths = []

    improvements = raw.get("improvements", [])
    if not isinstance(improvements, list):
        improvements = []

    unsupported = raw.get("unsupported_claims", [])
    if not isinstance(unsupported, list):
        unsupported = []

    feedback_text = raw.get("feedback_text", "")
    if not isinstance(feedback_text, str):
        feedback_text = ""

    return {
        "relevance_score": relevance,
        "clarity_score": clarity,
        "structure_score": structure,
        "technical_score": technical,
        "overall_score": overall,
        "strengths": [str(s) for s in strengths],
        "improvements": [str(i) for i in improvements],
        "unsupported_claims": [str(u) for u in unsupported],
        "criteria": {
            "relevance": "How directly the answer addresses the question and role.",
            "clarity": "How easy the answer is to follow, with specific and concise language.",
            "structure": "How logically the answer is organized (for example, STAR for behavioral answers).",
            "technical": "Accuracy and completeness of technical reasoning; not scored for HR or behavioral questions.",
            "scale": "1 = needs substantial development; 3 = adequate foundation; 5 = clear, specific, and well-supported. Scores are coaching signals, not hiring predictions.",
        },
        "feedback_text": feedback_text.strip(),
        "disclaimer": disclaimer,
    }


def generate_questions(
    structured_resume: dict,
    jd_text: str,
    jd_requirements: dict,
) -> list[dict]:
    """Return 8-12 validated question dicts. Raises json.JSONDecodeError on unparseable response."""
    client = get_anthropic_client()

    role_title = jd_requirements.get("role_title", "")
    prompt = (
        f"<USER_CONTENT>\n"
        f"ROLE: {role_title}\n\n"
        f"JOB DESCRIPTION:\n{jd_text}\n\n"
        f"CANDIDATE RESUME (structured):\n{json.dumps(structured_resume, indent=2)}\n"
        f"</USER_CONTENT>\n\n"
        f"Generate interview practice questions based on the above."
    )

    response = client.messages.create(
        model=get_model(),
        max_tokens=2048,
        system=_SYSTEM_GENERATE,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text
    items = _extract_json_array(raw_text)

    questions = []
    for idx, item in enumerate(items):
        validated = _validate_question(item, idx)
        if validated:
            questions.append(validated)

    if len(questions) < 4:
        raise json.JSONDecodeError(
            f"Too few valid questions returned ({len(questions)})", raw_text, 0
        )
    if len(questions) > 12:
        raise json.JSONDecodeError("Question set exceeds the 12-question limit", raw_text, 0)

    types = [q["type"] for q in questions]
    if types.count("technical") < 2 or types.count("behavioral") < 2 or "hr" not in types:
        raise json.JSONDecodeError("Question set is missing required practice categories", raw_text, 0)

    # Reindex sequentially in case Claude skipped indices
    for i, q in enumerate(questions):
        q["index"] = i

    # Keep prompts actionable even when a model omits an optional coaching field.
    for q in questions:
        if not q["guidance"]:
            q["guidance"] = "Answer directly, use a specific example, and connect it to the role."
        if not q["answer_structure"]:
            q["answer_structure"] = (
                "Situation and task → your actions and reasoning → result and learning."
                if q["type"] in ("behavioral", "project")
                else "Brief context → approach and key trade-offs → outcome or takeaway."
            )
    return questions


def evaluate_answer(
    question_dict: dict,
    user_answer: str,
    structured_resume: dict,
) -> dict:
    """Return validated feedback dict. Raises json.JSONDecodeError on unparseable response."""
    client = get_anthropic_client()

    q_type = question_dict.get("type", "technical")
    prompt = (
        f"<USER_CONTENT>\n"
        f"QUESTION TYPE: {q_type}\n"
        f"QUESTION: {question_dict.get('question', '')}\n\n"
        f"CANDIDATE'S ANSWER:\n{user_answer}\n\n"
        f"CANDIDATE RESUME (structured):\n{json.dumps(structured_resume, indent=2)}\n"
        f"</USER_CONTENT>\n\n"
        f"Evaluate the candidate's practice answer and provide structured feedback."
    )

    response = client.messages.create(
        model=get_model(),
        max_tokens=1024,
        system=_SYSTEM_EVALUATE,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text
    raw_dict = _extract_json_object(raw_text)
    raw_dict["_question_type"] = q_type
    return _validate_feedback(raw_dict)
