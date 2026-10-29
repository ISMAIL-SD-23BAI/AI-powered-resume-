"""
ATS-safe PDF generation with ReportLab PLATYPUS.

Design constraints (all intentional):
  - Single column, no multi-column layout
  - No tables, no text boxes, no frames-within-frames
  - No images or vector graphics
  - Standard fonts only (Helvetica family — always available, no embedding issues)
  - All text is selectable, correct reading order
  - Bullet points use ASCII hyphen so every ATS can parse them
"""
import io
from datetime import date
from typing import Optional
from xml.sax.saxutils import escape as _esc

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

# ── Page geometry ──────────────────────────────────────────────────────────────

_W, _H = letter
_ML = _MR = 0.9 * inch
_MT = _MB = 0.85 * inch

_GREY = colors.HexColor("#6b7280")
_DARK = colors.HexColor("#1f2937")
_RULE = colors.HexColor("#d1d5db")

# ── Shared style factory ───────────────────────────────────────────────────────

def _styles() -> dict:
    base = dict(fontName="Helvetica", alignment=TA_LEFT, textColor=_DARK)
    bold = {**base, "fontName": "Helvetica-Bold"}
    grey = {**base, "textColor": _GREY}   # override textColor to avoid duplicate kwarg
    return {
        "name":      ParagraphStyle("name",      **bold, fontSize=17, leading=22, spaceAfter=2),
        "sub":       ParagraphStyle("sub",       **grey, fontSize=9,  leading=13, spaceAfter=4),
        "section":   ParagraphStyle("section",   **bold, fontSize=9,  leading=13, spaceBefore=10, spaceAfter=3),
        "job_title": ParagraphStyle("job_title", **bold, fontSize=10, leading=14, spaceAfter=1),
        "meta":      ParagraphStyle("meta",      **grey, fontSize=9,  leading=12, spaceAfter=2),
        "body":      ParagraphStyle("body",      **base, fontSize=10, leading=14, spaceAfter=3),
        "bullet":    ParagraphStyle("bullet",    **base, fontSize=10, leading=14, leftIndent=12, firstLineIndent=0, spaceAfter=2),
        "skills":    ParagraphStyle("skills",    **base, fontSize=10, leading=14, spaceAfter=4),
        # cover letter styles
        "cl_header": ParagraphStyle("cl_header", **bold, fontSize=12, leading=18, spaceAfter=2),
        "cl_date":   ParagraphStyle("cl_date",   **grey, fontSize=10, leading=14, spaceAfter=4),
        "cl_body":   ParagraphStyle("cl_body",   **base, fontSize=11, leading=18, spaceAfter=10),
    }


def _doc(buf: io.BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=_ML, rightMargin=_MR,
        topMargin=_MT, bottomMargin=_MB,
        title="",
        author="",
    )


def _rule() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.5, color=_RULE,
                      spaceBefore=4, spaceAfter=6)


def _para(text: str, style) -> Paragraph:
    return Paragraph(_esc(str(text or "")), style)


# ── Resume PDF ─────────────────────────────────────────────────────────────────

def build_resume_pdf(
    tailored_resume: dict,
    candidate_name: Optional[str],
    role_title: Optional[str] = None,
) -> bytes:
    """
    Build an ATS-safe resume PDF from the tailored_resume dict.

    Expected dict keys (all optional):
      summary, skills (list), experience (list), education (list), projects (list)
    """
    buf = io.BytesIO()
    doc = _doc(buf)
    st = _styles()
    story = []

    # ── Header ──
    story.append(_para(candidate_name or "Candidate", st["name"]))
    if role_title:
        story.append(_para(role_title, st["sub"]))
    story.append(_rule())

    # ── Summary ──
    summary = (tailored_resume.get("summary") or "").strip()
    if summary:
        story.append(_para(summary, st["body"]))
        story.append(Spacer(1, 4))

    # ── Skills ──
    skills = [s for s in (tailored_resume.get("skills") or []) if s]
    if skills:
        story.append(_para("Skills", st["section"]))
        story.append(_para(", ".join(skills), st["skills"]))

    # ── Experience ──
    experience = tailored_resume.get("experience") or []
    if experience:
        story.append(_para("Experience", st["section"]))
        for job in experience:
            title = (job.get("title") or "").strip()
            company = (job.get("company") or "").strip()
            dates = (job.get("dates") or "").strip()
            heading = title + (f"  —  {company}" if company else "")
            story.append(_para(heading, st["job_title"]))
            if dates:
                story.append(_para(dates, st["meta"]))
            for bullet in (job.get("bullets") or []):
                if bullet:
                    story.append(_para(f"- {bullet}", st["bullet"]))
            story.append(Spacer(1, 4))

    # ── Education ──
    education = tailored_resume.get("education") or []
    if education:
        story.append(_para("Education", st["section"]))
        for edu in education:
            degree = (edu.get("degree") or "").strip()
            institution = (edu.get("institution") or "").strip()
            dates = (edu.get("dates") or "").strip()
            heading = degree + (f"  —  {institution}" if institution else "")
            story.append(_para(heading, st["job_title"]))
            if dates:
                story.append(_para(dates, st["meta"]))
            story.append(Spacer(1, 3))

    # ── Projects ──
    projects = tailored_resume.get("projects") or []
    if projects:
        story.append(_para("Projects", st["section"]))
        for proj in projects:
            name = (proj.get("name") or "").strip()
            desc = (proj.get("description") or "").strip()
            story.append(_para(name, st["job_title"]))
            if desc:
                story.append(_para(desc, st["body"]))
            for bullet in (proj.get("bullets") or []):
                if bullet:
                    story.append(_para(f"- {bullet}", st["bullet"]))
            story.append(Spacer(1, 4))

    doc.build(story)
    return buf.getvalue()


# ── Cover letter PDF ───────────────────────────────────────────────────────────

def build_cover_letter_pdf(
    content: str,
    candidate_name: Optional[str],
    role_title: Optional[str] = None,
) -> bytes:
    """Build a clean PDF from plain-text cover letter content."""
    buf = io.BytesIO()
    doc = _doc(buf)
    st = _styles()
    story = []

    # ── Header ──
    if candidate_name:
        story.append(_para(candidate_name, st["cl_header"]))
    date_line = date.today().strftime("%B %d, %Y")
    if role_title:
        date_line += f"  ·  {role_title}"
    story.append(_para(date_line, st["cl_date"]))
    story.append(_rule())
    story.append(Spacer(1, 8))

    # ── Body ──
    # Normalise: split on blank lines to get paragraphs; join soft-wrapped lines.
    raw_paras = (content or "").strip().split("\n\n")
    for raw in raw_paras:
        text = " ".join(line.strip() for line in raw.strip().splitlines() if line.strip())
        if text:
            story.append(_para(text, st["cl_body"]))

    doc.build(story)
    return buf.getvalue()
