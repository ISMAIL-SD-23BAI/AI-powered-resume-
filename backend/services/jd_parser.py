"""
Local (no LLM) job description parser.

Extracts structured requirements from raw JD text using section-header
detection, bullet-point splitting, and keyword-pattern matching.
No external API calls — runs fully offline.

Returned dict schema:
{
  "role_title":            str | None,
  "required_skills":       list[str],
  "preferred_skills":      list[str],
  "responsibilities":      list[str],
  "qualifications":        list[str],
  "education_requirement": str | None,  # "bachelor" | "master" | "phd" | None
  "experience_years":      int | None,
}
"""
import re
from typing import Optional

from services.skill_normalizer import _ALIAS_MAP, normalize

# ── Section-header patterns (case-insensitive) ─────────────────────────────────

_REQUIRED_HDRS = re.compile(
    r"(?:required|requirements|must[- ]have|essential|mandatory|"
    r"what you['']ll need|what we require|minimum qualifications?|"
    r"basic qualifications?)",
    re.I,
)
_PREFERRED_HDRS = re.compile(
    r"(?:preferred|nice[- ]to[- ]have|bonus|plus|desired|"
    r"additional qualifications?|good[- ]to[- ]have|advantageous)",
    re.I,
)
_RESP_HDRS = re.compile(
    r"(?:responsibilities?|duties|what you['']ll do|role overview|"
    r"key responsibilities?|primary responsibilities?|day[- ]to[- ]day|"
    r"your role|about the role|job duties)",
    re.I,
)
_QUAL_HDRS = re.compile(
    r"(?:qualifications?|education|about you|who you are|"
    r"experience[- ]requirements?|technical[- ]requirements?|"
    r"skills[- ]requirements?)",
    re.I,
)

# ── Education-level patterns ───────────────────────────────────────────────────

_EDU_PHD = re.compile(r"\b(?:ph\.?d|doctorate|doctoral)\b", re.I)
_EDU_MASTER = re.compile(
    r"\b(?:master['']?s?|m\.?s\.?|m\.?tech\.?|m\.?e\.?|mba)\b", re.I
)
_EDU_BACHELOR = re.compile(
    r"\b(?:bachelor['']?s?|b\.?s\.?|b\.?e\.?|b\.?tech\.?|"
    r"undergraduate|b\.?a\.?|bs|ba|be)\b",
    re.I,
)

# ── Experience-years pattern ───────────────────────────────────────────────────

_EXP_YEARS = re.compile(
    r"(\d+)\+?\s*(?:to\s*\d+)?\s*(?:\+\s*)?years?\s*(?:of\s*)?(?:experience|exp)",
    re.I,
)

# ── Bullet / list-item splitter ────────────────────────────────────────────────

_BULLET_RE = re.compile(r"^\s*[-•*·▪▸◦‣]\s+|\s*\d+\.\s+", re.M)


def _split_bullets(text: str) -> list[str]:
    """Split a block of text into individual bullet items."""
    lines = _BULLET_RE.split(text)
    result = []
    for line in lines:
        line = line.strip()
        if len(line) > 4:
            result.append(line)
    return result


def _is_section_header(line: str) -> bool:
    stripped = line.strip().rstrip(":").strip()
    if len(stripped) > 80:
        return False
    if re.search(r"[.!?]", stripped):
        return False
    return bool(
        _REQUIRED_HDRS.search(stripped)
        or _PREFERRED_HDRS.search(stripped)
        or _RESP_HDRS.search(stripped)
        or _QUAL_HDRS.search(stripped)
    )


def _classify_header(line: str) -> str:
    """Return the section category this header line belongs to."""
    stripped = line.strip()
    if _REQUIRED_HDRS.search(stripped):
        return "required"
    if _PREFERRED_HDRS.search(stripped):
        return "preferred"
    if _RESP_HDRS.search(stripped):
        return "responsibilities"
    if _QUAL_HDRS.search(stripped):
        return "qualifications"
    return "unknown"


# ── Known-skill extraction ─────────────────────────────────────────────────────

# All canonical skill forms from the alias map — sorted longest first so
# multi-word phrases match before their sub-words do.
_ALL_CANONICAL = sorted(set(_ALIAS_MAP.values()), key=len, reverse=True)
_ALL_ALIASES = sorted(_ALIAS_MAP.keys(), key=len, reverse=True)


def _extract_skills_from_text(text: str) -> list[str]:
    """Return canonical skill names found anywhere in `text`."""
    lower = text.lower()
    found: set[str] = set()
    for alias in _ALL_ALIASES:
        if len(alias) < 2:
            continue
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        if re.search(pattern, lower):
            found.add(_ALIAS_MAP[alias])
    return list(found)


def _detect_education_level(text: str) -> Optional[str]:
    if _EDU_PHD.search(text):
        return "phd"
    if _EDU_MASTER.search(text):
        return "master"
    if _EDU_BACHELOR.search(text):
        return "bachelor"
    return None


def _detect_experience_years(text: str) -> Optional[int]:
    matches = _EXP_YEARS.findall(text)
    if not matches:
        return None
    years = [int(m) for m in matches]
    return min(years)


def _extract_role_title(text: str) -> Optional[str]:
    """Heuristic: first non-empty short line of the JD is often the title."""
    for line in text.splitlines():
        line = line.strip()
        if 5 < len(line) < 100 and not line.endswith(":"):
            clean = re.sub(r"[#*_>|\\]", "", line).strip()
            if clean:
                return clean
    return None


# ── Main entry point ───────────────────────────────────────────────────────────

def parse_jd(raw_text: str) -> dict:
    """
    Parse a raw job description string into structured requirements.
    Returns a dict matching the schema described in the module docstring.
    Never raises — returns empty collections on any error.
    """
    empty = {
        "role_title": None,
        "required_skills": [],
        "preferred_skills": [],
        "responsibilities": [],
        "qualifications": [],
        "education_requirement": None,
        "experience_years": None,
    }

    if not raw_text or not raw_text.strip():
        return empty

    text = raw_text.strip()

    # ── Step 1: split into sections by header lines ──
    sections: dict[str, list[str]] = {
        "required": [],
        "preferred": [],
        "responsibilities": [],
        "qualifications": [],
        "preamble": [],
    }

    current_section = "preamble"
    current_lines: list[str] = []

    def _flush():
        block = "\n".join(current_lines).strip()
        if block:
            sections[current_section].append(block)
        current_lines.clear()

    for line in text.splitlines():
        if _is_section_header(line):
            _flush()
            current_section = _classify_header(line)
        else:
            current_lines.append(line)
    _flush()

    # ── Step 2: extract bullets from each section ──
    def _bullets_from_section(key: str) -> list[str]:
        items: list[str] = []
        for block in sections.get(key, []):
            items.extend(_split_bullets(block))
        return items

    required_bullets = _bullets_from_section("required")
    preferred_bullets = _bullets_from_section("preferred")
    resp_bullets = _bullets_from_section("responsibilities")
    qual_bullets = _bullets_from_section("qualifications")

    # ── Step 3: extract skills from each section ──
    # Required section first; also scan preamble for common "Required: X, Y, Z" patterns
    required_skills: list[str] = []
    preferred_skills: list[str] = []

    required_block = " ".join(sections.get("required", []))
    preferred_block = " ".join(sections.get("preferred", []))
    preamble_block = " ".join(sections.get("preamble", []))

    # If no explicit required section, scan preamble + qualifications
    if not required_block.strip():
        required_block = preamble_block + " " + " ".join(sections.get("qualifications", []))

    required_skills = _extract_skills_from_text(required_block)
    preferred_skills = _extract_skills_from_text(preferred_block)

    # Remove preferred skills that are already in required (to avoid double-counting)
    req_set = set(required_skills)
    preferred_skills = [s for s in preferred_skills if s not in req_set]

    # ── Step 4: education + experience ──
    full_text = text
    edu = _detect_education_level(full_text)
    exp_years = _detect_experience_years(full_text)

    # ── Step 5: role title ──
    role_title = _extract_role_title(text)

    return {
        "role_title": role_title,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "responsibilities": resp_bullets,
        "qualifications": qual_bullets,
        "education_requirement": edu,
        "experience_years": exp_years,
    }
