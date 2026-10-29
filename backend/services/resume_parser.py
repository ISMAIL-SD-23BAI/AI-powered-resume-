"""
Uses Claude to convert raw resume text into a structured JSON object.
"""
import json
import re

from services.bedrock_client import get_anthropic_client, get_model

_SYSTEM = """\
You are a precise resume data extractor.
Given raw resume text, return ONLY a valid JSON object — no markdown fences, no commentary.

The JSON schema must be exactly:
{
  "skills": ["string", ...],
  "experience": [
    {
      "title": "string",
      "company": "string",
      "dates": "string",
      "bullets": ["string", ...]
    }
  ],
  "education": [
    {
      "degree": "string",
      "institution": "string",
      "dates": "string"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "bullets": ["string", ...]
    }
  ]
}

Rules:
- Use empty arrays [] for sections not present.
- Keep bullets concise and verbatim where possible.
- Do not invent data; extract only what is present.
- Return ONLY the JSON object, starting with { and ending with }."""


def parse_resume(raw_text: str) -> dict:
    """
    Call Claude to extract structured resume data.
    Returns a dict on success, or a partial dict with a 'parse_error' key on failure.
    Never raises — all exceptions are caught so upload always succeeds.
    """
    _EMPTY = {"skills": [], "experience": [], "education": [], "projects": []}

    try:
        client = get_anthropic_client()
        model = get_model()
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": raw_text}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # Extract just the JSON object; Haiku sometimes appends extra text
        start = raw.find("{")
        if start != -1:
            depth = 0
            in_str = esc = False
            for i, ch in enumerate(raw[start:], start):
                if esc: esc = False; continue
                if ch == "\\" and in_str: esc = True; continue
                if ch == '"': in_str = not in_str; continue
                if in_str: continue
                if ch == "{": depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0: raw = raw[start:i+1]; break
        return json.loads(raw)

    except json.JSONDecodeError as exc:
        return {**_EMPTY, "parse_error": f"Claude returned non-JSON output: {exc}"}
    except Exception as exc:
        return {**_EMPTY, "parse_error": f"AI parsing failed: {exc}"}
