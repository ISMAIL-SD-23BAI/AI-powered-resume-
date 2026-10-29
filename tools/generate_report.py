"""
Generate BCSE497J Project-I Report for AI Resume Tailor project.
Run with: python generate_report.py
Output: AI_Resume_Tailor_Project_Report.docx
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page setup ──────────────────────────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Inches(8.27)   # A4
section.page_height = Inches(11.69)
section.left_margin   = Inches(1.25)
section.right_margin  = Inches(1.0)
section.top_margin    = Inches(1.0)
section.bottom_margin = Inches(1.0)

# ── Styles helper ────────────────────────────────────────────────────────────
def set_font(run, name="Times New Roman", size=12, bold=False, italic=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)

def para_format(para, space_before=0, space_after=6, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    para.paragraph_format.space_before = Pt(space_before)
    para.paragraph_format.space_after  = Pt(space_after)
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    para.paragraph_format.line_spacing = line_spacing
    para.alignment = align

def add_heading(doc, text, level=1, center=False):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    for run in h.runs:
        run.font.name = "Times New Roman"
        run.font.color.rgb = RGBColor(0, 0, 0)
    return h

def add_body(doc, text, indent=False):
    p = doc.add_paragraph(text)
    para_format(p)
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.3)
    for run in p.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    return p

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(text, style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    for run in p.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
    return p

def add_page_break(doc):
    doc.add_page_break()

def simple_table(doc, headers, rows, caption=None, cap_num=None):
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(f"Table {cap_num}: {caption}" if cap_num else f"Table: {caption}")
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for para in hdr_cells[i].paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(11)
    for row_data in rows:
        row_cells = table.add_row().cells
        for i, cell_text in enumerate(row_data):
            row_cells[i].text = cell_text
            for para in row_cells[i].paragraphs:
                for run in para.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
    doc.add_paragraph()
    return table

def center_para(doc, text, size=12, bold=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(size)
    r.font.bold = bold
    return p

# ═══════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════
center_para(doc, "VELLORE INSTITUTE OF TECHNOLOGY", 14, True)
center_para(doc, "School of Computer Science and Engineering", 13, False)
center_para(doc, "Department of Computer Science and Engineering (AI & ML)", 12, False)
doc.add_paragraph()
center_para(doc, "BCSE497J — PROJECT I", 13, True)
doc.add_paragraph()
center_para(doc, "PROJECT REPORT", 16, True)
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("AI POWERED RESUME & COVER LETTER TAILORING")
r.font.name = "Times New Roman"; r.font.size = Pt(16); r.font.bold = True

doc.add_paragraph()
center_para(doc, "Submitted by", 12, False)
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("SYED ISMAIL\t\t23BAI0206\n").font.name = "Times New Roman"
run2 = p.add_run("VIKAS NAIDU\t\t23BCE0204")
run2.font.name = "Times New Roman"

doc.add_paragraph()
center_para(doc, "Under the guidance of", 12, False)
center_para(doc, "Prof. Subramanyam Reddy", 12, True)
doc.add_paragraph()
center_para(doc, "Head of the Department", 12, False)
center_para(doc, "Dr. Gayathri P", 12, True)
doc.add_paragraph()
center_para(doc, "Bachelor of Technology", 12, False)
center_para(doc, "Computer Science and Engineering (Artificial Intelligence & Machine Learning)", 12, False)
doc.add_paragraph()
center_para(doc, "October 2026", 12, False)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# DECLARATION
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "DECLARATION", 1, center=True)
add_body(doc,
    "We hereby declare that the project report entitled \"AI Powered Resume & Cover Letter "
    "Tailoring\" submitted to Vellore Institute of Technology in partial fulfilment of the "
    "requirements for the award of the degree of Bachelor of Technology in Computer Science and "
    "Engineering (Artificial Intelligence & Machine Learning) is a record of original work done by "
    "us under the supervision of Prof. Subramanyam Reddy, Department of Computer Science and "
    "Engineering, VIT.")
add_body(doc,
    "We further declare that the work reported in this project has not been submitted, either in "
    "part or in full, for the award of any other degree or diploma in this institute or any other "
    "institute or university.")
doc.add_paragraph()
p = doc.add_paragraph()
p.add_run("Place: Vellore\nDate: October 2026")
p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(12)
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run("Syed Ismail (23BAI0206)                    Vikas Naidu (23BCE0204)")
r.font.name = "Times New Roman"; r.font.size = Pt(12)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CERTIFICATE
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CERTIFICATE", 1, center=True)
add_body(doc,
    "This is to certify that the project report entitled \"AI Powered Resume & Cover Letter "
    "Tailoring\" submitted by Syed Ismail (23BAI0206) and Vikas Naidu (23BCE0204) to Vellore "
    "Institute of Technology in partial fulfilment of the requirements for the award of the degree "
    "of Bachelor of Technology in Computer Science and Engineering (Artificial Intelligence & "
    "Machine Learning) is a bonafide record of work carried out by them under my supervision.")
add_body(doc,
    "The contents of this report have not been submitted and will not be submitted either in part "
    "or in full for the award of any other degree or diploma.")
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run(
    "Prof. Subramanyam Reddy\n"
    "Project Guide\n"
    "Department of CSE (AI & ML)\n"
    "Vellore Institute of Technology, Vellore"
)
r.font.name = "Times New Roman"; r.font.size = Pt(12)
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run(
    "Dr. Gayathri P\n"
    "Head of the Department\n"
    "Department of CSE (AI & ML)\n"
    "Vellore Institute of Technology, Vellore"
)
r.font.name = "Times New Roman"; r.font.size = Pt(12)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGEMENTS
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "ACKNOWLEDGEMENTS", 1, center=True)
add_body(doc,
    "We take this opportunity to express our deep sense of gratitude and sincere thanks to "
    "Prof. Subramanyam Reddy for his invaluable guidance, continuous encouragement, and constructive "
    "suggestions throughout the course of this project. His insights on software architecture, "
    "evaluation methodology, and responsible AI design were instrumental in shaping this work.")
add_body(doc,
    "We are grateful to Dr. Gayathri P, Head of the Department of Computer Science and Engineering "
    "(AI & ML), for providing the necessary infrastructure and academic environment for pursuing this "
    "project.")
add_body(doc,
    "We thank the faculty of the School of Computer Science and Engineering, VIT, for their "
    "encouragement and the academic foundation that made this work possible.")
add_body(doc,
    "We acknowledge the open-source communities behind FastAPI, SQLAlchemy, sentence-transformers, "
    "pypdf, ReportLab, Anthropic's Python SDK, and the many other libraries that this project depends "
    "on. Their documentation and communities were essential references throughout development.")
add_body(doc,
    "Finally, we thank our families and peers for their patience, support, and feedback during "
    "the development and evaluation phases of this project.")
doc.add_paragraph()
p = doc.add_paragraph()
r = p.add_run("Syed Ismail\nVikas Naidu")
r.font.name = "Times New Roman"; r.font.size = Pt(12)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# ABSTRACT
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "ABSTRACT", 1, center=True)
add_body(doc,
    "The contemporary job market demands that candidates submit application documents "
    "tailored precisely to each role. Manually aligning a resume and cover letter to every job "
    "description is time-consuming, error-prone, and inconsistent. This project presents "
    "AI Powered Resume & Cover Letter Tailoring, a local-first web application that assists "
    "job seekers in producing evidence-grounded, role-specific application documents while "
    "preserving full transparency about what the system can and cannot conclude.")
add_body(doc,
    "The system combines a static HTML/CSS/JavaScript frontend with a FastAPI backend. Users "
    "register an account and upload a text-based PDF resume, which is extracted by pypdf and "
    "parsed into a structured JSON record (skills, experience, education, and projects) by "
    "Claude, Anthropic's large language model. Job descriptions are parsed locally using "
    "regex-based section and skill extraction without any LLM call. A weighted matching engine "
    "then computes a document-to-job alignment score by combining required-skill coverage (40%), "
    "experience relevance (30%), preferred-skill coverage (15%), and education alignment (15%). "
    "Skill matching proceeds through exact alias normalisation, sentence-embedding cosine "
    "similarity using the all-MiniLM-L6-v2 model, and a TF-IDF cosine-similarity fallback when "
    "the embedding library is unavailable. Each matched skill is attributed to a specific resume "
    "section, providing explainable evidence for every score component.")
add_body(doc,
    "Beyond matching, the system supports Claude-assisted resume tailoring, cover-letter "
    "generation, targeted improvement suggestions, skill-gap roadmap creation, interview "
    "practice with structured answer feedback, and job application tracking. All generated "
    "documents can be exported as formatted PDFs using ReportLab. User accounts are secured "
    "with bcrypt password hashing and JWT bearer authentication. All application data are "
    "scoped to the authenticated user.")
add_body(doc,
    "The project was evaluated using a synthetic dataset of 11 resume/job-description pairs. "
    "The matching engine achieved a micro F1 score of 0.952 against hand-labelled skill "
    "classifications, compared to 0.850 for a substring keyword baseline. Evidence source "
    "localisation was correct in 21 of 22 expected cases. The full regression suite comprises "
    "324 automated tests covering authentication, data ownership, parsing, matching, tailoring, "
    "export, tracking, and interview workflows; all AI calls in tests are mocked.")
add_body(doc,
    "The project is acknowledged as a local prototype. It does not predict hiring outcomes, "
    "assess candidate ability, or rank candidates against each other. The evaluation dataset "
    "is small and synthetic; ranking quality and real-world resume diversity are untested. "
    "No database migration system is implemented, and the Docker configuration was reviewed "
    "but not executed. Despite these limitations, the project demonstrates a complete, "
    "tested, and responsibly scoped pipeline for AI-assisted application document preparation.")
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS (manual, representative)
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "TABLE OF CONTENTS", 1, center=True)
toc_entries = [
    ("Declaration", "ii"),
    ("Certificate", "iii"),
    ("Acknowledgements", "iv"),
    ("Abstract", "v"),
    ("Table of Contents", "vi"),
    ("List of Figures", "vii"),
    ("List of Tables", "viii"),
    ("List of Abbreviations", "ix"),
    ("Chapter 1 — Introduction", "1"),
    ("    1.1  Background and Motivation", "1"),
    ("    1.2  Scope and Report Organisation", "3"),
    ("Chapter 2 — Project Description and Plan", "4"),
    ("    2.1  Project Overview", "4"),
    ("    2.2  Related Work and Research Gap", "5"),
    ("    2.3  Objectives", "6"),
    ("    2.4  Problem Statement", "6"),
    ("    2.5  Stakeholders", "7"),
    ("    2.6  Project Plan", "7"),
    ("Chapter 3 — Requirements and Feasibility", "8"),
    ("    3.1  Functional Requirements", "8"),
    ("    3.2  Non-Functional Requirements", "9"),
    ("    3.3  Feasibility Analysis", "10"),
    ("    3.4  Hardware and Software Specifications", "10"),
    ("    3.5  Constraints and Interfaces", "11"),
    ("Chapter 4 — System Architecture and Design", "12"),
    ("    4.1  System Architecture", "12"),
    ("    4.2  Data Flow", "13"),
    ("    4.3  Use Cases", "14"),
    ("    4.4  Matching Model Design", "15"),
    ("    4.5  Security Design", "16"),
    ("    4.6  Database Design", "17"),
    ("Chapter 5 — Implementation and Testing", "19"),
    ("    5.1  Module Overview", "19"),
    ("    5.2  Methodology", "21"),
    ("    5.3  Testing Approach", "22"),
    ("    5.4  Test Coverage and Results", "23"),
    ("    5.5  Limitations", "24"),
    ("Chapter 6 — Demonstration", "25"),
    ("    6.1  Environment", "25"),
    ("    6.2  Workflow", "25"),
    ("Chapter 7 — Results and Discussion", "27"),
    ("    7.1  Evaluation Results", "27"),
    ("    7.2  Cost Analysis", "29"),
    ("    7.3  Key Observations", "29"),
    ("Chapter 8 — Conclusion and Future Work", "31"),
    ("    8.1  Conclusion", "31"),
    ("    8.2  Limitations", "31"),
    ("    8.3  Future Enhancements", "32"),
    ("References", "33"),
    ("Appendix A — User Guide", "34"),
    ("Appendix B — API Route Catalogue", "36"),
    ("Appendix C — Data Dictionary", "38"),
    ("Appendix D — Requirement Traceability and Test Plan", "40"),
    ("Appendix E — Synthetic Evaluation Notes", "42"),
    ("Appendix F — Demonstration Scenarios", "43"),
    ("Appendix G — Risk and Privacy Notes", "44"),
    ("Appendix H — Installation and Configuration Guide", "45"),
    ("Appendix I — Glossary", "47"),
    ("Appendix J — Representative Code Excerpts", "48"),
]
for entry, page in toc_entries:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r1 = p.add_run(entry)
    r1.font.name = "Times New Roman"; r1.font.size = Pt(12)
    r2 = p.add_run(f"{'.' * (max(2, 70 - len(entry) - len(page)))}{page}")
    r2.font.name = "Times New Roman"; r2.font.size = Pt(12)
add_page_break(doc)

# LIST OF FIGURES
add_heading(doc, "LIST OF FIGURES", 1, center=True)
figs = [
    ("1.1", "AI Resume Tailor — Application Context Diagram", "2"),
    ("4.1", "System Architecture Overview", "12"),
    ("4.2", "Resume Upload and Parsing Sequence Diagram", "13"),
    ("4.3", "Job-Description Matching Flowchart", "14"),
    ("4.4", "Use-Case Diagram", "15"),
    ("4.5", "Database Entity-Relationship Diagram", "18"),
    ("5.1", "Module Dependency Overview", "20"),
    ("6.1", "User Workflow Screenshot — Upload and Match", "26"),
]
for num, caption, page in figs:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"Figure {num} — {caption}")
    r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p.add_run(f"{'.' * max(2, 65 - len(caption) - len(page))}{page}").font.name = "Times New Roman"
add_page_break(doc)

# LIST OF TABLES
add_heading(doc, "LIST OF TABLES", 1, center=True)
tabs = [
    ("2.1", "Project Milestones and Deliverables", "7"),
    ("3.1", "Functional Requirements and Verification", "8"),
    ("3.2", "Non-Functional Requirements", "9"),
    ("3.3", "Hardware and Software Specifications", "10"),
    ("4.1", "Database Entities and Attributes", "17"),
    ("4.2", "Score Component Weights and Rationale", "15"),
    ("5.1", "Backend API Modules", "19"),
    ("5.2", "Test Suite Outcomes", "23"),
    ("7.1", "Synthetic Evaluation Metrics", "28"),
    ("7.2", "Evaluation Case Coverage", "28"),
    ("7.3", "Estimated Cost Analysis", "29"),
    ("B.1", "API Route Catalogue", "36"),
    ("D.1", "Requirement Traceability Matrix", "40"),
    ("G.1", "Risk and Mitigation Register", "44"),
]
for num, caption, page in tabs:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"Table {num} — {caption}")
    r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p.add_run(f"{'.' * max(2, 65 - len(caption) - len(page))}{page}").font.name = "Times New Roman"
add_page_break(doc)

# LIST OF ABBREVIATIONS
add_heading(doc, "LIST OF ABBREVIATIONS", 1, center=True)
abbrs = [
    ("AI",       "Artificial Intelligence"),
    ("API",      "Application Programming Interface"),
    ("ATS",      "Applicant Tracking System"),
    ("AWS",      "Amazon Web Services"),
    ("B.Tech",   "Bachelor of Technology"),
    ("CORS",     "Cross-Origin Resource Sharing"),
    ("CSE",      "Computer Science and Engineering"),
    ("CRUD",     "Create, Read, Update, Delete"),
    ("CSV",      "Comma-Separated Values"),
    ("DB",       "Database"),
    ("F1",       "Harmonic Mean of Precision and Recall"),
    ("HTML",     "HyperText Markup Language"),
    ("HTTP",     "HyperText Transfer Protocol"),
    ("HTTPS",    "HTTP Secure"),
    ("JD",       "Job Description"),
    ("JSON",     "JavaScript Object Notation"),
    ("JWT",      "JSON Web Token"),
    ("LLM",      "Large Language Model"),
    ("ML",       "Machine Learning"),
    ("NLP",      "Natural Language Processing"),
    ("ORM",      "Object-Relational Mapper"),
    ("PDF",      "Portable Document Format"),
    ("TF-IDF",   "Term Frequency–Inverse Document Frequency"),
    ("URL",      "Uniform Resource Locator"),
    ("VIT",      "Vellore Institute of Technology"),
]
table = doc.add_table(rows=1 + len(abbrs), cols=2)
table.style = "Table Grid"
table.rows[0].cells[0].text = "Abbreviation"
table.rows[0].cells[1].text = "Expansion"
for cell in table.rows[0].cells:
    for para in cell.paragraphs:
        for run in para.runs:
            run.bold = True; run.font.name = "Times New Roman"; run.font.size = Pt(11)
for i, (abbr, full) in enumerate(abbrs, 1):
    table.rows[i].cells[0].text = abbr
    table.rows[i].cells[1].text = full
    for cell in table.rows[i].cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.name = "Times New Roman"; run.font.size = Pt(11)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 1 — INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 1 — INTRODUCTION", 1)
add_heading(doc, "1.1  Background and Motivation", 2)
add_body(doc,
    "The modern employment landscape is characterised by high application volumes, automated "
    "candidate screening systems, and increasingly specialised job requirements. Recruitment "
    "analytics platforms consistently report that the majority of submitted resumes never reach "
    "a human reader because they are filtered at the applicant tracking system (ATS) stage. "
    "An ATS parses submitted documents and ranks candidates based on keyword and phrase "
    "alignment with the job description. Resumes that fail this automated stage are discarded "
    "regardless of the candidate's actual qualifications.")
add_body(doc,
    "For job seekers, this creates a practical dilemma. A generic resume that accurately "
    "summarises a candidate's background is unlikely to score highly across diverse roles. "
    "Manually tailoring a resume for each application is laborious: it involves reading the "
    "job description carefully, identifying the specific skills and experiences it emphasises, "
    "restructuring resume content to foreground those elements, adjusting language to match "
    "the role's terminology, and writing a role-specific cover letter. Candidates applying to "
    "tens or hundreds of positions face this burden repeatedly, often producing inconsistent "
    "results or reverting to a single generic document out of exhaustion.")
add_body(doc,
    "Large language models (LLMs) such as Anthropic Claude have demonstrated strong capability "
    "for text comprehension, structured extraction, and controlled document generation. "
    "These capabilities are relevant to the tailoring problem: an LLM can read resume text, "
    "identify structured fields, and rewrite content sections to foreground specific skills "
    "and experiences without fabricating credentials. At the same time, pure LLM reliance "
    "for matching introduces transparency and reproducibility concerns: if the system cannot "
    "show exactly which resume sentence justified a skill claim, candidates and reviewers "
    "cannot audit the result.")
add_body(doc,
    "This project combines an LLM for document parsing and controlled generation with a "
    "deterministic, evidence-attributed local matching engine. The matching engine processes "
    "job descriptions locally using regex-based extraction and ranks candidate skills using "
    "sentence-transformer embeddings with an interpretable score decomposition. The LLM is "
    "used only for workflows that require fluent text generation: resume parsing, tailoring, "
    "cover-letter writing, improvement coaching, skill-gap roadmaps, and interview feedback. "
    "This separation makes the system's alignment scores auditable and reproducible regardless "
    "of LLM provider availability.")
add_body(doc,
    "The application context is illustrated in Figure 1.1. The user interacts with a static "
    "web frontend served locally. The frontend communicates with a FastAPI backend over HTTP. "
    "The backend stores application data in SQLite using SQLAlchemy and calls Anthropic's "
    "Claude API for generation tasks. The matching and job-description parsing pipelines run "
    "entirely within the backend process without any external API calls.")

# Figure reference placeholder
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Figure 1.1 — AI Resume Tailor Application Context Diagram")
r.italic = True; r.font.name = "Times New Roman"; r.font.size = Pt(11)

add_heading(doc, "1.2  Scope and Report Organisation", 2)
add_body(doc,
    "This project is a local-first prototype intended for demonstration and academic evaluation. "
    "It does not constitute a production deployment and does not predict hiring outcomes, assess "
    "candidate ability, or rank candidates relative to one another. The scope covers the full "
    "software development lifecycle for the described feature set: requirements analysis, "
    "architecture design, implementation, automated testing, and evaluation against a synthetic "
    "dataset.")
add_body(doc,
    "This report is organised as follows. Chapter 2 describes the project in detail, surveys "
    "related work, and establishes the research gap, objectives, and project plan. Chapter 3 "
    "specifies functional and non-functional requirements, feasibility, hardware/software "
    "specifications, and interface constraints. Chapter 4 presents the system architecture, "
    "data flow, use cases, matching model, security design, and database schema. Chapter 5 "
    "describes implemented modules, methodology, testing approach, coverage, results, and known "
    "limitations. Chapter 6 documents the demonstration environment and workflow. Chapter 7 "
    "presents evaluation results, cost analysis, and key observations. Chapter 8 concludes "
    "with a summary of findings, limitations, and proposed future enhancements. References and "
    "appendices follow.")
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 2 — PROJECT DESCRIPTION AND PLAN
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 2 — PROJECT DESCRIPTION AND PLAN", 1)
add_heading(doc, "2.1  Project Overview", 2)
add_body(doc,
    "AI Powered Resume & Cover Letter Tailoring is a full-stack local web application that "
    "assists job seekers in understanding how well their resume aligns with a specific job "
    "description, generating role-aligned application documents, and tracking their application "
    "pipeline. The system is designed to be transparent: every score component is explained "
    "with a direct evidence link to the candidate's own resume text, and every generated "
    "document is clearly labelled as AI-assisted content requiring human review.")
add_body(doc,
    "The core features are: authenticated user accounts with bcrypt-hashed passwords and JWT "
    "bearer tokens; PDF resume upload with format and size validation; AI-assisted resume "
    "parsing to structured JSON; local ATS-style matching with skill evidence attribution and "
    "weighted alignment scoring; Claude-assisted resume tailoring and cover-letter generation "
    "with prompts that prohibit skill fabrication; improvement suggestions, skill-gap roadmap "
    "creation, interview practice with answer evaluation, application tracker, and history; "
    "and PDF export of tailored documents.")

add_heading(doc, "2.2  Related Work and Research Gap", 2)
add_body(doc,
    "Existing approaches to resume optimisation fall into three broad categories. Rule-based "
    "ATS keyword tools scan resumes for keyword frequency without structural awareness. "
    "Commercial products such as Jobscan and Resume Worded offer resume-to-JD scoring but "
    "treat their matching algorithms as proprietary, offer no source-code auditability, and "
    "require cloud submission of sensitive resume data. LLM-only approaches use a model to "
    "generate tailored documents but produce no structured evidence map showing which resume "
    "sections justify each aligned skill.")
add_body(doc,
    "The research gap addressed by this project is the combination of an explainable, "
    "locally executed, evidence-attributed matching engine with LLM-assisted document "
    "generation in a unified, open, self-hosted application. The matching engine exposes its "
    "full score formula, component weights, normalisation alias map, and per-skill evidence "
    "attribution. The LLM generation prompts include explicit constraints against fabrication. "
    "The matching evaluation is synthetic and diagnostic, not a claim of production-level "
    "accuracy.")

add_heading(doc, "2.3  Objectives", 2)
objectives = [
    "Design and implement a local-first web application supporting the full resume tailoring workflow.",
    "Build a deterministic, explainable ATS-style matching engine with weighted component scoring and skill-evidence attribution.",
    "Integrate Anthropic Claude for resume parsing, tailoring, cover-letter generation, improvement coaching, skill-gap analysis, and interview feedback.",
    "Implement JWT-based authentication and per-user data ownership enforcement.",
    "Achieve 300+ automated tests covering all major functional paths with mocked AI calls.",
    "Evaluate the matching engine against a synthetic labelled dataset and report micro F1, evidence localisation, and comparison to a keyword baseline.",
    "Document limitations, known defects, and boundary conditions honestly.",
]
for obj in objectives:
    add_bullet(doc, obj)

add_heading(doc, "2.4  Problem Statement", 2)
add_body(doc,
    "Given a text-based PDF resume and a job description in free text, the system shall: "
    "(a) parse the resume into a structured representation of skills, experience, education, "
    "and projects; (b) extract required and preferred skills, experience requirements, and "
    "education level from the job description locally; (c) compute an evidence-attributed "
    "alignment score between the resume and the job description; (d) generate a role-aligned "
    "tailored resume and cover letter without fabricating skills or experiences; "
    "(e) provide actionable improvement recommendations; and (f) persist all results in a "
    "per-user database accessible through a web interface.")

add_heading(doc, "2.5  Stakeholders", 2)
add_body(doc,
    "Primary users are job seekers preparing application documents for specific roles. "
    "Secondary stakeholders include the academic supervisors evaluating this project, future "
    "developers who might extend the system, and privacy-conscious users who need to understand "
    "that their resume data is processed by an external AI provider under the provider's terms.")

add_heading(doc, "2.6  Project Plan", 2)
simple_table(doc,
    ["Phase", "Activities", "Deliverable"],
    [
        ("1 — Requirements", "Stakeholder analysis, use-case modelling, requirements specification", "SRS document"),
        ("2 — Architecture", "Component design, data model, API contract, security model", "Architecture doc"),
        ("3 — Backend Core", "Auth, resume upload/parse, database, JWT middleware", "Working API skeleton"),
        ("4 — Matching Engine", "JD parser, skill normaliser, embedding service, scoring formula", "Matching engine + tests"),
        ("5 — LLM Workflows", "Tailor, cover-letter, improve, skill-gap, interview routers + services", "AI-backed endpoints"),
        ("6 — Frontend", "Static HTML pages, JS API client, CORS configuration", "Working frontend"),
        ("7 — Export & Tracker", "PDF export (ReportLab), application tracker CRUD", "Export + tracker"),
        ("8 — Testing & Eval", "Full pytest suite (324 tests), synthetic eval dataset (11 pairs), documentation", "Final release package"),
    ],
    caption="Project Milestones and Deliverables", cap_num="2.1"
)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 3 — REQUIREMENTS AND FEASIBILITY
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 3 — REQUIREMENTS AND FEASIBILITY", 1)
add_heading(doc, "3.1  Functional Requirements", 2)
simple_table(doc,
    ["ID", "Requirement", "Verification"],
    [
        ("FR-01", "User shall be able to register with email and password; passwords shall be bcrypt-hashed", "test_auth.py signup tests"),
        ("FR-02", "User shall log in and receive a JWT bearer token valid for subsequent API calls", "test_auth.py login tests"),
        ("FR-03", "User shall upload a PDF resume; system shall reject non-PDF, oversized (>5 MiB), or empty files", "test_resumes.py, test_edge_cases.py"),
        ("FR-04", "System shall extract plain text from uploaded PDF using pypdf and parse it to structured JSON via Claude", "test_resumes.py parse tests"),
        ("FR-05", "System shall accept a job description and compute an alignment score with skill evidence", "test_match_router.py, test_matching_engine.py"),
        ("FR-06", "System shall generate a tailored resume via Claude without fabricating skills", "test_tailor.py"),
        ("FR-07", "System shall generate a cover letter linked to a tailored resume", "test_cover_letter.py"),
        ("FR-08", "System shall generate improvement suggestions for a resume against a JD", "test_improve_router.py"),
        ("FR-09", "System shall produce a skill-gap roadmap identifying gaps and learning resources", "test_skill_gap_router.py"),
        ("FR-10", "System shall generate interview questions and evaluate user answers", "test_interview_router.py"),
        ("FR-11", "System shall allow users to create, read, update, and delete job application tracker entries", "test_tracker.py"),
        ("FR-12", "System shall export tailored resumes and cover letters as PDF files", "test_export.py"),
        ("FR-13", "All application data shall be scoped to the authenticated user; cross-user access shall return 403", "test_edge_cases.py ownership tests"),
    ],
    caption="Functional Requirements and Verification", cap_num="3.1"
)

add_heading(doc, "3.2  Non-Functional Requirements", 2)
simple_table(doc,
    ["ID", "Category", "Requirement"],
    [
        ("NFR-01", "Security", "Passwords stored as bcrypt hashes; JWTs signed with a configurable secret of ≥32 characters"),
        ("NFR-02", "Security", "All protected endpoints validate Bearer token before processing; invalid tokens return 401"),
        ("NFR-03", "Performance", "Local matching engine responds within 10 ms median per request on reference hardware (measured: 1.4 ms mean on Windows 11 / Python 3.12)"),
        ("NFR-04", "Reliability", "System operates correctly with TF-IDF fallback when sentence-transformers is unavailable"),
        ("NFR-05", "Maintainability", "Backend structured as separate router and service modules per feature domain; 324 automated tests"),
        ("NFR-06", "Usability", "Frontend uses standard HTML/JS with no build step; works in modern browsers served over HTTP"),
        ("NFR-07", "Privacy", "Resume text and structured data stored only in local SQLite; original PDF bytes not retained"),
        ("NFR-08", "Portability", "Runs on Windows 10/11 and Linux with Python 3.12 and the requirements.txt dependency set"),
        ("NFR-09", "Rate limiting", "AI-calling endpoints enforce per-user request rate limits via slowapi"),
    ],
    caption="Non-Functional Requirements", cap_num="3.2"
)

add_heading(doc, "3.3  Feasibility Analysis", 2)
add_body(doc,
    "Technical feasibility: the required technology stack (FastAPI, SQLAlchemy, Anthropic SDK, "
    "sentence-transformers, pypdf, ReportLab) is mature, well-documented, and available as "
    "open-source packages on PyPI. The LLM is accessed as an external API service requiring "
    "only an API key, with no local GPU requirement. The sentence-transformer model "
    "(all-MiniLM-L6-v2) is approximately 80 MB and runs on CPU with acceptable latency for "
    "single-user local use.")
add_body(doc,
    "Economic feasibility: all server-side libraries are open-source with no licensing cost. "
    "The Anthropic API is a pay-per-token service; costs are low for a prototype used by a "
    "single user. A cost estimate is provided in Chapter 7.")
add_body(doc,
    "Operational feasibility: the system is designed for local operation on a developer "
    "machine. It does not require cloud deployment, container orchestration, or a managed "
    "database. The only external dependency during operation is network access to the "
    "Anthropic API for AI-backed routes.")

add_heading(doc, "3.4  Hardware and Software Specifications", 2)
simple_table(doc,
    ["Component", "Specification"],
    [
        ("Operating System", "Windows 10/11 (64-bit); also compatible with Linux"),
        ("Processor", "Intel Core i5 or equivalent; ≥4 cores recommended for test suite"),
        ("RAM", "≥8 GB; ≥16 GB recommended for sentence-transformers model loading"),
        ("Storage", "≥2 GB free space for Python venv and model weights"),
        ("Python", "3.12 (tested on 3.12.0)"),
        ("FastAPI", "0.115.6"),
        ("Uvicorn", "0.32.1"),
        ("SQLAlchemy", "2.0.36"),
        ("Anthropic SDK", "≥1.3.0, <2.0.0"),
        ("pypdf", "5.1.0"),
        ("ReportLab", "4.2.5"),
        ("sentence-transformers", "≥2.0.0 (all-MiniLM-L6-v2)"),
        ("scikit-learn / NumPy", "≥1.3.0 / ≥1.24.0 (TF-IDF fallback)"),
        ("Browser", "Chrome, Firefox, or Edge (modern versions)"),
    ],
    caption="Hardware and Software Specifications", cap_num="3.3"
)

add_heading(doc, "3.5  Constraints and Interfaces", 2)
add_body(doc,
    "The system is constrained to SQLite as the default database; no Alembic migration system "
    "is included, so schema changes require manual migration for existing databases. The PDF "
    "upload limit is 5 MiB; encrypted, image-only, or malformed PDFs are rejected. The "
    "frontend must be served from a local HTTP server (not file:// in production mode) to "
    "satisfy CORS constraints. AI-dependent endpoints require a valid Anthropic API key or "
    "Bedrock configuration; their absence causes those endpoints to fail at runtime without "
    "affecting non-AI endpoints. Rate limits on AI routes are in-process and are reset on "
    "server restart; they are not suitable for multi-instance production deployment.")
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 4 — ARCHITECTURE AND DESIGN
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 4 — SYSTEM ARCHITECTURE AND DESIGN", 1)
add_heading(doc, "4.1  System Architecture", 2)
add_body(doc,
    "The system follows a two-tier local architecture with a static frontend and a FastAPI "
    "backend. Figure 4.1 illustrates the major components and their relationships.")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 4.1 — System Architecture Overview").italic = True

add_body(doc,
    "The static frontend comprises HTML/CSS/JavaScript pages served from a local HTTP server "
    "or opened directly in a browser in DEBUG mode. Each page communicates with the backend "
    "API using the Fetch API with a Bearer token stored in browser localStorage. The backend "
    "is a FastAPI application served by Uvicorn. It is organised into authenticated router "
    "modules (auth, resumes, tailor, cover-letter, history, match, improve, skill-gap, "
    "tracker, interview, export) and corresponding service modules that implement the "
    "domain logic. A shared SQLAlchemy ORM layer persists application state in SQLite. "
    "Selected service modules call the Anthropic API (or AWS Bedrock) for generation tasks.")

add_heading(doc, "4.2  Data Flow", 2)
add_body(doc,
    "Resume Processing (Figure 4.2): the user selects a PDF in the frontend and submits it "
    "with a Bearer token. The FastAPI resume router validates the token, checks the file "
    "extension, reads at most 5 MiB + 1 byte to detect oversized files, verifies the PDF "
    "magic bytes (%PDF-), and passes the file to the PDF parser service. pypdf extracts "
    "plain text. The backend then calls Claude via the Anthropic Messages API, asking for a "
    "structured JSON object containing skills, experience entries, education, and projects. "
    "The parsed text and structured JSON are stored in the resumes table. The API response "
    "returns the resume ID and parse status.")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 4.2 — Resume Upload and Parsing Sequence Diagram").italic = True

add_body(doc,
    "Matching Flow (Figure 4.3): the user submits a resume ID and job description text. "
    "The job description is parsed locally by the JD parser service using regex patterns "
    "to identify section headers (Required, Preferred, Responsibilities, Qualifications) and "
    "extract skills using the alias normaliser's known-skill vocabulary. The matching engine "
    "loads the stored structured resume, constructs a corpus of normalised skill and experience "
    "text, and evaluates each extracted JD requirement through the three-tier matching "
    "hierarchy: exact normalised match, semantic cosine similarity (sentence-transformer or "
    "TF-IDF fallback), and partial match. The weighted alignment score is computed and the "
    "full result (scores, matched/partial/missing requirements, per-skill evidence, "
    "recommendations) is persisted in match_results.")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 4.3 — Job-Description Matching Flowchart").italic = True

add_heading(doc, "4.3  Use Cases", 2)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 4.4 — Use-Case Diagram").italic = True

add_body(doc,
    "The primary actor is an authenticated User. The main use cases are: Register Account, "
    "Login, Upload Resume, Run ATS Match, Generate Tailored Resume, Generate Cover Letter, "
    "View Improvement Suggestions, Create Skill-Gap Roadmap, Practice Interview, Track "
    "Applications, Export PDF, and View History. All use cases except Register and Login "
    "include the Authenticate extend relationship (JWT validation by the backend middleware).")

add_heading(doc, "4.4  Matching Model Design", 2)
add_body(doc,
    "The matching engine produces a score between 0 and 100 using the following weighted formula:")
p = doc.add_paragraph()
p.style = "No Spacing"
r = p.add_run(
    "    overall = round(\n"
    "        0.40 × required_skill_score\n"
    "      + 0.15 × preferred_skill_score\n"
    "      + 0.30 × experience_score\n"
    "      + 0.15 × education_score\n"
    "    )"
)
r.font.name = "Courier New"; r.font.size = Pt(11)
doc.add_paragraph()

simple_table(doc,
    ["Weight", "Component", "Rationale"],
    [
        ("40%", "Required skill score", "Primary hiring criterion; meeting hard requirements is the strongest document signal"),
        ("30%", "Experience relevance", "Demonstrated track record; combines presence, responsibility similarity, and years estimate"),
        ("15%", "Preferred skill score", "Nice-to-have; meaningful but not decisive"),
        ("15%", "Education alignment", "Important credential signal; rarely the sole deciding factor"),
    ],
    caption="Score Component Weights and Rationale", cap_num="4.2"
)

add_body(doc,
    "Skill matching proceeds in three tiers. An exact match is declared when the normalised "
    "canonical form of the JD skill matches any normalised resume skill exactly, yielding "
    "confidence 1.0. A semantic match is declared when the cosine similarity between the "
    "sentence-transformer embedding (or TF-IDF vector) of the normalised JD skill and any "
    "corpus item meets or exceeds 0.65; the confidence equals the similarity value. A partial "
    "match is declared for similarity between 0.45 and 0.65, with confidence equal to "
    "similarity × 0.5. Below 0.45 the skill is classified as not evidenced (confidence 0.0). "
    "The skill normaliser maps common aliases to canonical names (e.g. ML → machine learning, "
    "ReactJS → react, k8s → kubernetes) before matching.")

add_heading(doc, "4.5  Security Design", 2)
add_body(doc,
    "Passwords are hashed with bcrypt (cost factor 12) using passlib. Authentication issues "
    "a signed JWT with configurable expiry using python-jose. Every protected endpoint "
    "dependency injects the current user from the token; requests with missing, expired, or "
    "tampered tokens receive HTTP 401. Ownership checks on individual records return HTTP 403 "
    "when the record's user_id does not match the authenticated user. File upload inputs are "
    "validated for extension, MIME magic bytes, and size before any parsing occurs. Rate "
    "limiting on AI-calling endpoints uses slowapi with per-user keys. CORS is configured to "
    "allow the local frontend origin; the null origin is permitted only when DEBUG=true.")

add_heading(doc, "4.6  Database Design", 2)
add_body(doc,
    "The database comprises 11 tables managed by SQLAlchemy with SQLite as the default "
    "engine. Table 4.1 lists the entities and their key attributes. Figure 4.5 shows the "
    "entity-relationship diagram.")

simple_table(doc,
    ["Table", "Key Columns", "Relationships"],
    [
        ("users", "id, email, hashed_password, full_name, is_active, created_at", "Parent of all user-owned entities"),
        ("resumes", "id, user_id, filename, raw_text, structured_json, uploaded_at", "Belongs to users; referenced by many entities"),
        ("job_descriptions", "id, user_id, raw_text, extracted_requirements_json, created_at", "Belongs to users; referenced by tailored_resumes"),
        ("tailored_resumes", "id, user_id, resume_id, job_description_id, tailored_content_json, created_at", "Belongs to users/resumes/job_descriptions; parent of cover_letters"),
        ("cover_letters", "id, tailored_resume_id, content, created_at", "Belongs to tailored_resumes"),
        ("match_results", "id, user_id, resume_id, job_description_text, result_json, overall_score, created_at", "Belongs to users/resumes"),
        ("improvement_sessions", "id, user_id, resume_id, job_description_text, session_json, status, tailored_resume_id, created_at", "Belongs to users/resumes; optionally linked to tailored_resumes"),
        ("learning_roadmaps", "id, user_id, resume_id, job_description_text, role_title, overall_score, skill_classifications_json, roadmap_items_json, created_at", "Belongs to users/resumes"),
        ("job_applications", "id, user_id, company_name, job_title, status, application_date, deadline, interview_date, notes, resume_id, tailored_resume_id, created_at", "Belongs to users; optionally linked to resumes and tailored_resumes"),
        ("interview_sessions", "id, user_id, resume_id, job_description_text, role_title, questions_json, question_count, created_at", "Belongs to users/resumes; parent of interview_answers"),
        ("interview_answers", "id, session_id, user_id, question_index, question_text, user_answer, feedback_json, evaluation_error, created_at", "Belongs to interview_sessions/users"),
    ],
    caption="Database Entities and Attributes", cap_num="4.1"
)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 4.5 — Database Entity-Relationship Diagram").italic = True

add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 5 — IMPLEMENTATION AND TESTING
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 5 — IMPLEMENTATION AND TESTING", 1)
add_heading(doc, "5.1  Module Overview", 2)
add_body(doc,
    "The backend is structured as a FastAPI application (backend/main.py) that mounts "
    "authenticated router modules from backend/routers/ and uses service modules from "
    "backend/services/ for domain logic. Figure 5.1 shows the module dependency overview.")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 5.1 — Module Dependency Overview").italic = True

simple_table(doc,
    ["Module", "Location", "Responsibility"],
    [
        ("main.py", "backend/", "FastAPI app factory, CORS, rate-limit middleware, router registration, startup schema creation"),
        ("auth.py (router)", "backend/routers/", "POST /signup, POST /login, POST /token; bcrypt verify; JWT issue"),
        ("resumes.py (router)", "backend/routers/", "PDF upload validation; calls pdf_parser + resume_parser; CRUD for resumes"),
        ("match.py (router)", "backend/routers/", "Calls jd_parser + matching_engine; persists and returns MatchResult"),
        ("tailor.py (router)", "backend/routers/", "Calls ai_tailor service; persists TailoredResume"),
        ("cover_letter.py (router)", "backend/routers/", "Calls cover_letter service; persists CoverLetter linked to tailored resume"),
        ("improve.py (router)", "backend/routers/", "Calls improvement_engine; manages ImprovementSession and apply workflow"),
        ("skill_gap.py (router)", "backend/routers/", "Calls skill_gap_analyzer; CRUD for LearningRoadmap"),
        ("interview.py (router)", "backend/routers/", "Calls interview_engine; manages InterviewSession and InterviewAnswer"),
        ("tracker.py (router)", "backend/routers/", "CRUD for JobApplication with filter and stats"),
        ("export.py (router)", "backend/routers/", "Calls pdf_builder; returns PDF bytes as StreamingResponse"),
        ("history.py (router)", "backend/routers/", "List and delete tailored resume history"),
        ("pdf_parser.py", "backend/services/", "pypdf text extraction with magic-byte and size checks"),
        ("resume_parser.py", "backend/services/", "Claude prompt for structured resume JSON extraction"),
        ("jd_parser.py", "backend/services/", "Local regex/header section and skill extraction from JD text"),
        ("matching_engine.py", "backend/services/", "Weighted scoring; exact/semantic/partial classification; evidence attribution"),
        ("embedding_service.py", "backend/services/", "sentence-transformers or TF-IDF cosine similarity; in-memory embedding cache"),
        ("skill_normalizer.py", "backend/services/", "Alias map for canonical skill names"),
        ("ai_tailor.py", "backend/services/", "Claude prompt for role-aligned resume tailoring"),
        ("cover_letter.py", "backend/services/", "Claude prompt for cover-letter generation"),
        ("improvement_engine.py", "backend/services/", "Claude prompt for targeted resume improvement suggestions"),
        ("skill_gap_analyzer.py", "backend/services/", "Claude prompt for skill-gap analysis and roadmap creation"),
        ("interview_engine.py", "backend/services/", "Claude prompts for question generation and answer evaluation"),
        ("pdf_builder.py", "backend/services/", "ReportLab PDF generation for tailored resumes and cover letters"),
        ("bedrock_client.py", "backend/services/", "Optional AWS Bedrock Anthropic client wrapper"),
    ],
    caption="Backend API Modules", cap_num="5.1"
)

add_heading(doc, "5.2  Methodology", 2)
add_body(doc,
    "Development followed an iterative, phase-based approach (see Table 2.1). Each phase "
    "produced working code and a corresponding test increment. The architecture separates "
    "router logic (request validation, ownership checks, response shaping) from service logic "
    "(domain computation, AI calls, PDF generation). This separation allowed unit testing of "
    "service modules in isolation from HTTP context and mocking of AI calls at the service "
    "boundary in integration tests.")
add_body(doc,
    "The JD parser and matching engine were developed with test-driven practices: the synthetic "
    "evaluation dataset was authored before the engine's matching logic was finalised, "
    "providing a regression target. The evaluation uses a deterministic Jaccard word-overlap "
    "similarity function instead of production embeddings, ensuring that evaluation results are "
    "reproducible without a network connection or model download.")
add_body(doc,
    "AI prompts include explicit constraints: tailoring prompts specify that the system shall "
    "not add skills, qualifications, or metrics that are not present in the candidate's "
    "original resume. This constraint is enforced at the prompt level, not at the model "
    "architecture level; live model behaviour is not verified by automated tests.")

add_heading(doc, "5.3  Testing Approach", 2)
add_body(doc,
    "All tests use pytest and httpx. The test client is configured via a conftest.py fixture "
    "that creates a separate in-memory SQLite database, applies the application schema, and "
    "overrides the production database dependency injection. This ensures that tests do not "
    "touch or corrupt the developer's local database.")
add_body(doc,
    "AI calls are mocked using pytest-mock at the service module boundary. Mocks return "
    "representative structured payloads, allowing API contract and data-persistence logic "
    "to be tested without incurring API costs or requiring a live credential. The evaluation "
    "script uses a deterministic similarity function rather than the production embedding "
    "model.")
add_body(doc,
    "Test categories include: authentication (signup, login, invalid credentials, tampered "
    "tokens); resume CRUD (upload, parse, list, delete, ownership); tailoring (success, "
    "validation, missing resume, AI mock); cover-letter; matching engine (unit); match router "
    "(integration); improvement; skill-gap; interview; tracker; export; history; frontend "
    "contract; and evaluation dataset structure.")

add_heading(doc, "5.4  Test Coverage and Results", 2)
simple_table(doc,
    ["Category", "Test File(s)", "Tests"],
    [
        ("Authentication", "test_auth.py", "~45"),
        ("Resume CRUD", "test_resumes.py", "~40"),
        ("Tailoring", "test_tailor.py", "~25"),
        ("Cover Letter", "test_cover_letter.py", "~15"),
        ("Matching Engine", "test_matching_engine.py", "~35"),
        ("Match Router", "test_match_router.py", "~20"),
        ("Improvement", "test_improve_router.py, test_improvement_engine.py", "~30"),
        ("Skill Gap", "test_skill_gap_router.py, test_skill_gap_analyzer.py", "~25"),
        ("Interview", "test_interview_router.py, test_interview_engine.py", "~30"),
        ("Tracker", "test_tracker.py", "~25"),
        ("Export", "test_export.py", "~10"),
        ("History", "test_history.py", "~10"),
        ("Edge Cases / Auth", "test_edge_cases.py", "~10"),
        ("Frontend Contract", "test_frontend_contracts.py", "1"),
        ("Eval Dataset Schema", "included in evaluation", "5"),
        ("TOTAL", "", "324 passed"),
    ],
    caption="Test Suite Outcomes", cap_num="5.2"
)

add_heading(doc, "5.5  Limitations", 2)
add_body(doc, "The following limitations are documented:")
limits = [
    "No database migration system (Alembic): create_all does not modify existing tables on schema changes.",
    "AI calls in tests are fully mocked; live Claude or Bedrock behaviour is not tested automatically.",
    "Docker configuration was reviewed and corrected but not executed; container startup is unverified.",
    "Frontend API base URLs are hardcoded to localhost:8000; a remote deployment requires configuration changes and HTTPS.",
    "Rate limits are in-process and are not suitable for multi-instance production use.",
    "SQLite data is not encrypted at rest; the application lacks a backup or rotation mechanism.",
    "The synthetic evaluation dataset has 11 pairs and cannot establish general real-world matching performance.",
    "Ranking quality (multiple candidates against one JD) is not evaluated.",
]
for lim in limits:
    add_bullet(doc, lim)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 6 — DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 6 — DEMONSTRATION", 1)
add_heading(doc, "6.1  Environment", 2)
add_body(doc,
    "The demonstration environment is a Windows 11 machine running Python 3.12.0. The "
    "project venv is located at resume-tailor/venv/. The Anthropic API key and JWT secret "
    "are configured in resume-tailor/.env. The FastAPI backend is served by Uvicorn on "
    "http://127.0.0.1:8000; the static frontend is served by Python's http.server module "
    "on http://127.0.0.1:5500.")

add_heading(doc, "6.2  Workflow", 2)
add_body(doc, "The demonstration follows these steps:")
steps = [
    "Start the backend: from backend/, run ../venv/Scripts/uvicorn main:app --host 127.0.0.1 --port 8000 --reload. Confirm /health returns {\"status\":\"ok\"}.",
    "Start the frontend server: from the project root, run venv/Scripts/python -m http.server 5500 --bind 127.0.0.1 --directory frontend.",
    "Open http://127.0.0.1:5500 in a browser. Navigate to signup.html and create a new account.",
    "Log in at login.html. The JWT token is stored in browser localStorage under the key 'token'.",
    "Navigate to upload.html. Upload a text-based PDF resume under 5 MiB. Observe the parse status and structured fields returned by the API.",
    "Navigate to index.html (ATS match). Enter or paste a job description and click Match. Review the overall score, required/preferred skill breakdown, evidence sections, and recommendations.",
    "Click 'Tailor Resume' from the match result. Review the Claude-generated tailored resume; observe the alignment note and the disclaimer that AI content requires human review.",
    "Generate a cover letter for the tailored resume. Export both documents as PDF and download them.",
    "Navigate to improve.html to view targeted improvement suggestions. Accept or dismiss suggestions and observe the apply workflow.",
    "Navigate to skill_gap.html to generate a learning roadmap for the identified skill gaps.",
    "Navigate to interview.html to generate interview questions, submit an answer, and view structured feedback.",
    "Navigate to tracker.html to create a job application entry with status 'applied' and observe the status pipeline (saved → applied → interview → offer/rejected).",
    "Visit http://127.0.0.1:8000/docs to demonstrate the interactive OpenAPI documentation.",
]
for i, step in enumerate(steps, 1):
    p = doc.add_paragraph(f"{i}. {step}")
    para_format(p, space_after=3)
    for run in p.runs:
        run.font.name = "Times New Roman"; run.font.size = Pt(12)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Figure 6.1 — User Workflow Screenshot — Upload and Match").italic = True

add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 7 — RESULTS AND DISCUSSION
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 7 — RESULTS AND DISCUSSION", 1)
add_heading(doc, "7.1  Evaluation Results", 2)
add_body(doc,
    "The matching engine was evaluated against 11 synthetic resume/job-description pairs in "
    "backend/tests/evaluation/dataset.py. The evaluation script (tests/evaluation/run_eval.py) "
    "uses a deterministic Jaccard word-overlap similarity function in place of the production "
    "sentence-transformer backend to ensure reproducibility. Partial matches are excluded from "
    "strict precision/recall positives.")

simple_table(doc,
    ["Metric", "Matching Engine", "Keyword Baseline"],
    [
        ("Macro Precision", "0.909", "0.818"),
        ("Macro Recall", "0.977", "0.909"),
        ("Macro F1", "0.896", "0.727"),
        ("Micro Precision", "0.952", "0.895"),
        ("Micro Recall", "0.952", "0.810"),
        ("Micro F1", "0.952", "0.850"),
        ("Evidence Source Localisation", "21/22 (0.955)", "N/A"),
    ],
    caption="Synthetic Evaluation Metrics", cap_num="7.1"
)

simple_table(doc,
    ["Coverage Area", "Cases"],
    [
        ("Exact skill matches", "Multiple cases"),
        ("Alias/abbreviation matches (e.g. ML, k8s)", "Covered"),
        ("Evidence in experience bullets", "Covered"),
        ("Semantic partial match", "TC11 (partial, excluded from strict metrics)"),
        ("Partially relevant roles", "Covered"),
        ("Irrelevant roles", "Covered"),
        ("Misleading company-name overlap (Java false positive)", "TC06 — documented engine FP"),
        ("Java/JavaScript substring overlap", "Covered"),
        ("Junior/senior experience mismatch", "Covered"),
        ("All-missing requirements", "Covered"),
        ("Education mismatch", "Covered"),
        ("Missed Python evidence (experience bullet)", "TC03 — documented engine FN"),
    ],
    caption="Evaluation Case Coverage", cap_num="7.2"
)

add_body(doc,
    "The engine achieved higher micro F1 (0.952) than the substring baseline (0.850), "
    "demonstrating that skill normalisation and evidence-attributed matching improve over "
    "naive keyword search. Two documented failures are TC03 (Python missed in an experience "
    "bullet) and TC06 (Java false positive from a company name match). These failures are "
    "visible in the evaluation case records and are not concealed in the reported metrics.")
add_body(doc,
    "Evidence source localisation (21/22) indicates that when a skill is matched, the "
    "engine correctly identifies the resume section (skills, experience, education, projects) "
    "from which the evidence was drawn in 95.5% of expected cases.")
add_body(doc,
    "IMPORTANT LIMITATION: these results are from 11 hand-authored synthetic pairs. They "
    "cannot be generalised to real-world hiring performance, candidate ability assessment, "
    "or rank ordering of candidates. No same-JD multi-candidate ranking was evaluated.")

add_heading(doc, "7.2  Cost Analysis", 2)
simple_table(doc,
    ["Activity", "Estimated Tokens", "Estimated Cost (USD)"],
    [
        ("Resume parse (Claude Haiku 4.5 input ~1k + output ~500)", "~1,500 tokens", "~$0.001 per parse"),
        ("Resume tailoring (input ~2k + output ~1k)", "~3,000 tokens", "~$0.003 per tailor"),
        ("Cover letter generation (input ~2k + output ~500)", "~2,500 tokens", "~$0.002 per letter"),
        ("Improvement suggestions (input ~2k + output ~800)", "~2,800 tokens", "~$0.003 per session"),
        ("Interview feedback (per answer, input ~1k + output ~400)", "~1,400 tokens", "~$0.001 per answer"),
        ("Typical session (parse + match + tailor + cover letter)", "~10,000 tokens", "~$0.01 per session"),
    ],
    caption="Estimated Cost Analysis", cap_num="7.3"
)
add_body(doc,
    "All cost estimates are approximate and depend on actual prompt/response lengths and "
    "the current Anthropic pricing for the configured model. Matching, JD parsing, and "
    "scoring do not consume any API tokens. Costs are incurred only by AI-backed routes. "
    "These estimates are based on the claude-haiku-4-5 pricing tier; using a more capable "
    "model will increase costs proportionally.")

add_heading(doc, "7.3  Key Observations", 2)
obs = [
    "MEASURED: The matching engine achieved micro F1 = 0.952 on 11 synthetic pairs, versus 0.850 for the substring baseline. Skill normalisation is the primary driver of the improvement.",
    "MEASURED: Evidence source localisation was correct in 21/22 expected cases (0.955). The one failure (TC03) was a missed Python mention in an experience bullet, not a section misclassification.",
    "MEASURED: 324 automated tests passed in the final reviewed checkout; all AI calls are mocked.",
    "MEASURED: Local matching engine mean latency was 1.46 ms per request on Windows 11 / Python 3.12 (single-run, no warm-up, not a load test).",
    "DOCUMENTED FAILURE: TC06 produces a Java false positive because the company name contains a Java-related term. The alias normaliser does not currently suppress company-name context.",
    "DOCUMENTED FAILURE: TC03 misses Python in an experience bullet because the evidence search does not index individual responsibility sub-clauses separately.",
    "LIMITATION: Evaluation is diagnostic only. It does not establish general real-world performance, candidate ranking ability, or hiring outcome prediction.",
    "LIMITATION: No migration system exists; schema changes require manual intervention on existing databases.",
    "OBSERVATION: Separating the matching engine (local, deterministic) from the generation workflows (LLM) provides transparency and reproducibility for the scoring component regardless of LLM provider availability.",
    "OBSERVATION: The TF-IDF fallback enables the system to function for matching even without sentence-transformers installed, though results may differ from the embedding-based backend.",
]
for i, ob in enumerate(obs, 1):
    add_bullet(doc, f"{i}. {ob}")
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 8 — CONCLUSION AND FUTURE WORK
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "CHAPTER 8 — CONCLUSION AND FUTURE WORK", 1)
add_heading(doc, "8.1  Conclusion", 2)
add_body(doc,
    "This project designed, implemented, tested, and evaluated a local-first AI-assisted "
    "resume and cover-letter tailoring application. The system combines a deterministic, "
    "evidence-attributed matching engine with Claude-assisted document generation, achieving "
    "a micro F1 of 0.952 on a synthetic evaluation dataset and passing 324 automated tests "
    "covering all major functional paths.")
add_body(doc,
    "The architecture demonstrates that an LLM can be responsibly integrated into a job "
    "application workflow without delegating all decision-making to the model. Score "
    "components are computed locally, decomposed, and attributed to specific resume sections; "
    "the LLM is confined to fluent text generation with prompts that prohibit skill "
    "fabrication. This separation makes the system's alignment scores auditable and "
    "reproducible.")

add_heading(doc, "8.2  Limitations", 2)
add_body(doc,
    "The following limitations are acknowledged and should be addressed before any production "
    "deployment: no database migration system; unverified Docker deployment; hardcoded "
    "localhost API URLs in the frontend; in-process rate limiting unsuitable for multi-instance "
    "use; no SQLite encryption at rest; synthetic evaluation dataset too small to generalise "
    "performance claims; ranking quality not evaluated; and live AI behaviour untested by "
    "automated regression.")

add_heading(doc, "8.3  Future Enhancements", 2)
future = [
    "Implement Alembic database migrations to support schema evolution without data loss.",
    "Add a production-grade deployment configuration with HTTPS, environment-injected secrets, and a managed database.",
    "Expand the evaluation dataset with diverse real-world resume/JD pairs (with consent) and include multi-candidate ranking evaluation.",
    "Add a real-time ATS keyword density overlay in the frontend, highlighting coverage gaps directly in the resume text.",
    "Implement OAuth2/social login for improved user experience.",
    "Support additional resume input formats (DOCX, plain text) and multi-page structured extraction.",
    "Add a job search API integration (e.g. LinkedIn or Indeed) to import job descriptions directly into the tracker.",
    "Explore privacy-preserving local inference for resume parsing to reduce AI provider data exposure.",
    "Add automated monitoring and alerting for AI endpoint error rates.",
    "Extend the skill normaliser alias map to cover more domains (healthcare, legal, finance) and support multi-language resumes.",
]
for f in future:
    add_bullet(doc, f)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# REFERENCES
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "REFERENCES", 1)
refs = [
    "[1] S. Arora, A. Kale, and P. Singh, \"Resume Screening Automation Using Natural Language Processing,\" in Proc. Int. Conf. on Computing, Communication, and Informatics (ICCCI), 2023, pp. 1–6.",
    "[2] N. Reimers and I. Gurevych, \"Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks,\" in Proc. 2019 Conf. on Empirical Methods in Natural Language Processing (EMNLP), 2019, pp. 3982–3992.",
    "[3] Anthropic, \"Claude API Reference,\" Anthropic Inc., 2024. [Online]. Available: https://docs.anthropic.com/",
    "[4] S. Bird, E. Klein, and E. Loper, Natural Language Processing with Python. Sebastopol, CA: O'Reilly Media, 2009.",
    "[5] T. Akidau, S. Chernyak, and R. Lax, Streaming Systems. Sebastopol, CA: O'Reilly Media, 2018.",
    "[6] FastAPI Documentation, \"FastAPI — Modern, Fast Web Framework for Building APIs with Python,\" Sebastián Ramírez, 2024. [Online]. Available: https://fastapi.tiangolo.com/",
    "[7] SQLAlchemy Documentation, \"The Python SQL Toolkit and Object Relational Mapper,\" SQLAlchemy Project, 2024. [Online]. Available: https://docs.sqlalchemy.org/",
    "[8] A. Vaswani et al., \"Attention Is All You Need,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, 2017.",
    "[9] T. Mikolov, K. Chen, G. Corrado, and J. Dean, \"Efficient Estimation of Word Representations in Vector Space,\" in Proc. ICLR Workshop, 2013.",
    "[10] Hugging Face, \"sentence-transformers/all-MiniLM-L6-v2,\" Hugging Face Model Hub, 2023. [Online]. Available: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
    "[11] G. Salton and C. Buckley, \"Term-Weighting Approaches in Automatic Text Retrieval,\" Information Processing & Management, vol. 24, no. 5, pp. 513–523, 1988.",
    "[12] Passlib Documentation, \"passlib — Password Hashing Library for Python,\" 2023. [Online]. Available: https://passlib.readthedocs.io/",
    "[13] ReportLab, \"ReportLab PDF Library User Guide,\" ReportLab Inc., 2023. [Online]. Available: https://www.reportlab.com/docs/reportlab-userguide.pdf",
    "[14] pypdf Documentation, \"pypdf — A Pure-Python PDF Library,\" 2024. [Online]. Available: https://pypdf.readthedocs.io/",
    "[15] OWASP, \"OWASP Top 10 Web Application Security Risks,\" OWASP Foundation, 2021. [Online]. Available: https://owasp.org/www-project-top-ten/",
]
for ref in refs:
    p = doc.add_paragraph(ref)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    p.paragraph_format.left_indent = Inches(0.3)
    for run in p.runs:
        run.font.name = "Times New Roman"; run.font.size = Pt(11)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX A — USER GUIDE
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX A — USER GUIDE", 1)
add_heading(doc, "A.1  Prerequisites", 2)
add_body(doc, "Python 3.12, an Anthropic API key (or AWS Bedrock credentials), and a modern web browser are required. Git and Docker are optional.")
add_heading(doc, "A.2  Installation", 2)
steps_install = [
    "Clone or extract the project to a local directory.",
    "From the project root, create a virtual environment: py -3.12 -m venv venv",
    "Activate it: venv\\Scripts\\Activate.ps1 (PowerShell) or source venv/bin/activate (Linux/Mac).",
    "Install dependencies: pip install -r requirements.txt",
    "Copy .env.example to .env and set ANTHROPIC_API_KEY and JWT_SECRET_KEY.",
    "Optionally set ANTHROPIC_MODEL (default: claude-sonnet-5), DATABASE_URL, CLAUDE_CODE_USE_BEDROCK, AWS_REGION.",
]
for i, s in enumerate(steps_install, 1):
    p = doc.add_paragraph(f"{i}. {s}")
    para_format(p, space_after=3)
    for run in p.runs:
        run.font.name = "Times New Roman"; run.font.size = Pt(12)

add_heading(doc, "A.3  Running the Application", 2)
add_body(doc,
    "Terminal 1 (from backend/): ../venv/Scripts/uvicorn main:app --host 127.0.0.1 --port 8000 --reload\n"
    "Terminal 2 (from project root): venv/Scripts/python -m http.server 5500 --bind 127.0.0.1 --directory frontend\n"
    "Open http://127.0.0.1:5500 in your browser.")

add_heading(doc, "A.4  Using the Application", 2)
user_steps = [
    ("Register", "Navigate to signup.html, enter email, full name, and password (min 8 characters), and click Register."),
    ("Login", "Navigate to login.html, enter credentials, and click Login. The JWT token is stored in localStorage."),
    ("Upload Resume", "Navigate to upload.html, click Choose File, select a text-based PDF under 5 MiB, and click Upload. Wait for the parse to complete."),
    ("Run ATS Match", "On index.html, select your uploaded resume from the dropdown, paste or type a job description, and click Match. Review the score breakdown and evidence."),
    ("Generate Tailored Resume", "Click Tailor Resume from the match result page. Review the AI-generated content and alignment note. All generated content requires human review."),
    ("Cover Letter", "On the tailored resume page, click Generate Cover Letter. Review and export to PDF."),
    ("Improvement Suggestions", "Navigate to improve.html, select a resume and job description, and generate suggestions. Accept individual suggestions to apply them."),
    ("Skill-Gap Roadmap", "Navigate to skill_gap.html to generate a personalised learning roadmap for skill gaps identified in a match."),
    ("Interview Practice", "Navigate to interview.html, generate questions for a role, type your answers, and receive structured feedback from Claude."),
    ("Application Tracker", "Navigate to tracker.html to add, update, and track job applications through their status pipeline."),
    ("Export PDF", "On the tailored resume or cover letter view, click Export PDF to download a formatted PDF."),
]
for action, desc in user_steps:
    p = doc.add_paragraph()
    r = p.add_run(f"{action}: ")
    r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p.add_run(desc).font.name = "Times New Roman"
    p.paragraph_format.space_after = Pt(4)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX B — API ROUTE CATALOGUE
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX B — API ROUTE CATALOGUE", 1)
add_body(doc, "All routes except /auth/signup, /auth/login, /auth/token, /health, and /docs require Authorization: Bearer <token>.")
simple_table(doc,
    ["Method", "Path", "Description"],
    [
        ("POST", "/auth/signup", "Register new user; returns user record"),
        ("POST", "/auth/login", "Authenticate; returns JWT access token"),
        ("POST", "/auth/token", "OAuth2 token endpoint (same as login)"),
        ("GET",  "/me", "Return authenticated user profile"),
        ("GET",  "/health", "Health check; returns {\"status\":\"ok\"}"),
        ("POST", "/resumes/", "Upload PDF resume; validates, parses, persists"),
        ("GET",  "/resumes/", "List current user's resumes"),
        ("GET",  "/resumes/{id}", "Get a specific resume"),
        ("DELETE","/resumes/{id}", "Delete a resume and related records"),
        ("POST", "/match/", "Run matching on resume + JD text"),
        ("GET",  "/match/", "List current user's match results"),
        ("GET",  "/match/{id}", "Get full match result"),
        ("DELETE","/match/{id}", "Delete a match result"),
        ("POST", "/tailor/", "Generate tailored resume via Claude"),
        ("GET",  "/tailor/", "List tailored resumes"),
        ("GET",  "/tailor/{id}", "Get a tailored resume"),
        ("DELETE","/tailor/{id}", "Delete a tailored resume"),
        ("POST", "/cover-letter/{tailored_id}", "Generate cover letter for a tailored resume"),
        ("GET",  "/cover-letter/{tailored_id}", "Get cover letter for a tailored resume"),
        ("PUT",  "/cover-letter/{id}", "Update cover letter content"),
        ("GET",  "/history/", "List tailoring history"),
        ("DELETE","/history/{id}", "Delete a history entry"),
        ("POST", "/improve/", "Generate improvement suggestions"),
        ("GET",  "/improve/", "List improvement sessions"),
        ("GET",  "/improve/{id}", "Get improvement session"),
        ("POST", "/improve/{id}/apply", "Apply accepted improvements"),
        ("POST", "/skill-gap/", "Create skill-gap roadmap"),
        ("GET",  "/skill-gap/", "List roadmaps"),
        ("GET",  "/skill-gap/{id}", "Get a roadmap"),
        ("PUT",  "/skill-gap/{id}", "Update roadmap item status"),
        ("DELETE","/skill-gap/{id}", "Delete a roadmap"),
        ("POST", "/interview/", "Generate interview session"),
        ("GET",  "/interview/", "List interview sessions"),
        ("GET",  "/interview/{id}", "Get session with questions"),
        ("POST", "/interview/{id}/answers", "Submit and evaluate an answer"),
        ("GET",  "/interview/{id}/answers", "Get all answers for a session"),
        ("GET",  "/interview/{id}/compare", "Compare multiple attempts for a question"),
        ("DELETE","/interview/{id}", "Delete a session"),
        ("POST", "/tracker/", "Create job application"),
        ("GET",  "/tracker/", "List applications with optional status filter"),
        ("GET",  "/tracker/stats", "Return application count by status"),
        ("GET",  "/tracker/{id}", "Get a specific application"),
        ("PUT",  "/tracker/{id}", "Update application fields"),
        ("DELETE","/tracker/{id}", "Delete an application"),
        ("GET",  "/export/resume/{id}", "Download tailored resume as PDF"),
        ("GET",  "/export/cover-letter/{id}", "Download cover letter as PDF"),
    ],
    caption="API Route Catalogue", cap_num="B.1"
)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX C — DATA DICTIONARY
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX C — DATA DICTIONARY", 1)
add_body(doc, "Key fields across the 11 database tables are described below.")
dd_entries = [
    ("users.email", "VARCHAR(255)", "Unique user email address; used as login identity"),
    ("users.hashed_password", "VARCHAR(255)", "bcrypt hash of user password; plaintext never stored"),
    ("resumes.raw_text", "TEXT", "Plain text extracted from uploaded PDF by pypdf"),
    ("resumes.structured_json", "TEXT", "JSON: {skills:[], experience:[], education:[], projects:[]} — parsed by Claude"),
    ("job_descriptions.extracted_requirements_json", "TEXT", "JSON: {role_title, required_skills[], preferred_skills[], responsibilities[], education_level, years_experience} — extracted locally"),
    ("match_results.result_json", "TEXT", "Full JSON result from the matching engine including component scores, evidence map, recommendations, and disclaimer"),
    ("match_results.overall_score", "INTEGER", "Cached overall alignment score (0–100); denormalised for list queries"),
    ("improvement_sessions.session_json", "TEXT", "JSON: {suggestions:[], applied:[]} — current improvement session state"),
    ("improvement_sessions.status", "VARCHAR(32)", "'active' or 'applied'; 'applied' after accepted suggestions are written to a new tailored resume"),
    ("learning_roadmaps.skill_classifications_json", "TEXT", "JSON list of {skill, status, confidence, resume_evidence} — output of skill-gap analyser"),
    ("learning_roadmaps.roadmap_items_json", "TEXT", "JSON list of {skill, resources[], status} — learner's progress tracker"),
    ("job_applications.status", "VARCHAR(32)", "One of: saved, applied, assessment, interview, offer, rejected"),
    ("interview_answers.feedback_json", "TEXT", "JSON: {strengths:[], improvements:[], score, overall_feedback} — null until evaluation completes"),
    ("tailored_resumes.tailored_content_json", "TEXT", "JSON: {tailored_resume, alignment_note, match_score, ...} — Claude output"),
]
simple_table(doc,
    ["Field", "Type", "Description"],
    dd_entries,
    caption="Data Dictionary — Key Fields", cap_num="C.1"
)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX D — REQUIREMENT TRACEABILITY AND TEST PLAN
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX D — REQUIREMENT TRACEABILITY AND TEST PLAN", 1)
simple_table(doc,
    ["Req ID", "Requirement Summary", "Implementation", "Test(s)", "Status"],
    [
        ("FR-01", "User registration with bcrypt hash", "auth.py router + auth service", "test_auth.py::test_signup_*", "PASS"),
        ("FR-02", "JWT login", "auth.py router", "test_auth.py::test_login_*", "PASS"),
        ("FR-03", "PDF upload validation", "resumes.py router + pdf_parser", "test_resumes.py, test_edge_cases.py", "PASS"),
        ("FR-04", "Resume parse to structured JSON", "resume_parser.py (Claude)", "test_resumes.py parse tests", "PASS (mocked)"),
        ("FR-05", "ATS matching with evidence", "matching_engine.py + match router", "test_matching_engine.py, test_match_router.py", "PASS"),
        ("FR-06", "Tailored resume generation", "ai_tailor.py (Claude)", "test_tailor.py", "PASS (mocked)"),
        ("FR-07", "Cover letter generation", "cover_letter service", "test_cover_letter.py", "PASS (mocked)"),
        ("FR-08", "Improvement suggestions", "improvement_engine.py", "test_improve_router.py, test_improvement_engine.py", "PASS (mocked)"),
        ("FR-09", "Skill-gap roadmap", "skill_gap_analyzer.py", "test_skill_gap_router.py, test_skill_gap_analyzer.py", "PASS (mocked)"),
        ("FR-10", "Interview practice + feedback", "interview_engine.py", "test_interview_router.py, test_interview_engine.py", "PASS (mocked)"),
        ("FR-11", "Application tracker CRUD", "tracker.py router", "test_tracker.py", "PASS"),
        ("FR-12", "PDF export", "pdf_builder.py + export router", "test_export.py", "PASS"),
        ("FR-13", "Cross-user access blocked (403)", "JWT dependency + ownership checks", "test_edge_cases.py ownership tests", "PASS"),
    ],
    caption="Requirement Traceability Matrix", cap_num="D.1"
)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX E — SYNTHETIC EVALUATION NOTES
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX E — SYNTHETIC EVALUATION NOTES", 1)
add_body(doc,
    "The evaluation dataset contains 11 hand-authored resume/job-description pairs stored in "
    "backend/tests/evaluation/dataset.py. Each pair includes: a synthetic structured resume, "
    "parsed job requirements, a relevant/irrelevant label, expected matched/partial/missing "
    "skills, and manually labelled evidence quotes with declared source sections.")
add_body(doc,
    "The evaluation script (tests/evaluation/run_eval.py) runs both the matching engine and "
    "a substring keyword baseline against each pair using a deterministic Jaccard word-overlap "
    "similarity function (not the production sentence-transformer) to ensure reproducibility "
    "without a network connection. Machine-readable per-case results are written to "
    "tests/evaluation/results.json.")
add_body(doc,
    "Documented failures: TC03 (Python missed in experience bullet — evidence search does "
    "not index individual sub-clauses); TC06 (Java false positive from company name — alias "
    "normaliser does not filter company-name context). Both are visible in case results.")
add_body(doc,
    "Reproduction: install requirements, run python tests/evaluation/run_eval.py from "
    "backend/. No API key required. The script prints aggregate metrics and updates results.json.")
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX F — DEMONSTRATION SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX F — DEMONSTRATION SCENARIOS", 1)
add_body(doc, "The following scenarios cover the main system capabilities for a live demonstration:")
scenarios = [
    ("Scenario 1: High-match resume", "Upload a resume that closely matches the job description. Observe overall score >70, matched skills with 'exact' evidence, and tailored resume preserving all original skills."),
    ("Scenario 2: Low-match resume", "Upload a resume that is largely irrelevant to the JD. Observe low overall score, large missing_requirements list, and skill-gap roadmap with multiple learning items."),
    ("Scenario 3: Alias normalisation", "Use a JD requiring 'Machine Learning' and a resume listing 'ML'. Observe that the engine correctly classifies this as an exact match via alias normalisation."),
    ("Scenario 4: Partial match", "Use a JD requiring 'Kubernetes' and a resume mentioning 'container orchestration'. Observe the partial match classification with reduced confidence."),
    ("Scenario 5: PDF export", "Generate a tailored resume and cover letter. Export both as PDFs and verify the formatted output includes all content sections."),
    ("Scenario 6: Interview practice", "Generate five interview questions for a backend engineering role. Submit an answer to question 1. Review structured feedback including strengths, improvements, and a score."),
    ("Scenario 7: Application tracking", "Create three tracker entries with different statuses. Use the stats endpoint to verify the count breakdown. Update one entry to 'interview' status."),
    ("Scenario 8: Offline matching", "Demonstrate that matching, scoring, and JD parsing work without any internet connection (AI-dependent tailoring will fail, but matching will not)."),
]
for name, desc in scenarios:
    p = doc.add_paragraph()
    r = p.add_run(f"{name}: ")
    r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p.add_run(desc).font.name = "Times New Roman"
    p.paragraph_format.space_after = Pt(5)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX G — RISK AND PRIVACY NOTES
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX G — RISK AND PRIVACY NOTES", 1)
simple_table(doc,
    ["Risk", "Likelihood", "Impact", "Mitigation"],
    [
        ("User submits real personal resume data; provider receives it", "Medium", "High", "Document that AI providers receive user content for generation tasks; advise using synthetic or anonymised data for demonstrations"),
        ("SQLite database contains extracted resume text at rest, unencrypted", "High", "Medium", "Database file is excluded from submission archive; document that production use requires encryption at rest"),
        ("JWT secret leaked via .env committed to version control", "Low", "High", ".env is git-ignored and excluded from submission ZIP; README instructs to generate a random secret"),
        ("Matching engine false positive misleads user about their qualifications", "Medium", "Medium", "Score is labelled as document-alignment estimate; disclaimer is included in every match result"),
        ("No database migration: schema upgrade corrupts existing data", "Medium", "High", "Documented limitation; recommended mitigation is backup + explicit migration before upgrading"),
        ("AI model generates fabricated skills in tailored resume", "Low", "High", "Tailoring prompt explicitly prohibits skill fabrication; generated content labelled as AI-assisted, requiring human review"),
        ("Rate limiter bypassed via multiple accounts", "Low", "Low", "Prototype; not designed for multi-user production; rate limiter documented as insufficient for that use case"),
        ("Docker configuration untested; container fails to start", "High", "Low", "Documented in release readiness; venv approach confirmed working; Docker not required for demonstration"),
    ],
    caption="Risk and Mitigation Register", cap_num="G.1"
)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX H — INSTALLATION AND CONFIGURATION GUIDE
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX H — INSTALLATION AND CONFIGURATION GUIDE", 1)
add_heading(doc, "H.1  Windows (PowerShell)", 2)
code_win = (
    "# From the project root (resume-tailor/)\n"
    "py -3.12 -m venv venv\n"
    ".\\venv\\Scripts\\python.exe -m pip install --upgrade pip\n"
    ".\\venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
    "Copy-Item .env.example .env\n"
    "notepad .env  # Set ANTHROPIC_API_KEY and JWT_SECRET_KEY\n\n"
    "# Terminal 1 — Backend\n"
    "Set-Location backend\n"
    "..\\venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload\n\n"
    "# Terminal 2 — Frontend\n"
    "Set-Location ..\n"
    ".\\venv\\Scripts\\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend"
)
p = doc.add_paragraph()
p.style = "No Spacing"
r = p.add_run(code_win)
r.font.name = "Courier New"; r.font.size = Pt(10)
doc.add_paragraph()

add_heading(doc, "H.2  Environment Variables", 2)
simple_table(doc,
    ["Variable", "Required", "Default", "Purpose"],
    [
        ("ANTHROPIC_API_KEY", "Yes (direct)", "—", "Claude API credential"),
        ("JWT_SECRET_KEY", "Yes", "—", "JWT signing secret; random, ≥32 characters"),
        ("ANTHROPIC_MODEL", "No", "claude-sonnet-5", "Claude model identifier"),
        ("CLAUDE_CODE_USE_BEDROCK", "No", "false", "Use AWS Bedrock client when true"),
        ("AWS_REGION", "No", "us-east-1", "Bedrock region"),
        ("DATABASE_URL", "No", "sqlite:///./resume_tailor.db", "SQLAlchemy URL"),
        ("DEBUG", "No", "false", "Allow null CORS origin for file:// pages; do not use in deployment"),
    ],
    caption="Environment Variable Reference", cap_num="H.1"
)

add_heading(doc, "H.3  Running Tests", 2)
add_body(doc, "From backend/:")
p = doc.add_paragraph()
p.style = "No Spacing"
r = p.add_run(
    "..\\venv\\Scripts\\python.exe -m pytest tests -q\n"
    "..\\venv\\Scripts\\python.exe tests\\evaluation\\run_eval.py"
)
r.font.name = "Courier New"; r.font.size = Pt(10)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX I — GLOSSARY
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX I — GLOSSARY", 1)
glossary = [
    ("ATS", "Applicant Tracking System — software used by recruiters to filter and rank applications by keyword/skill match against a job description."),
    ("Cosine Similarity", "A measure of similarity between two non-zero vectors computed as the cosine of the angle between them; used here for semantic skill matching."),
    ("Embedding", "A dense vector representation of text produced by a neural encoder model (sentence-transformers all-MiniLM-L6-v2), enabling semantic similarity computation."),
    ("Evidence Attribution", "The practice of linking a score component or classification decision directly to the specific resume section and text that justified it."),
    ("F1 Score", "The harmonic mean of precision and recall; used here as the primary metric for evaluating the matching engine against hand-labelled cases."),
    ("FastAPI", "A modern Python web framework for building APIs with automatic OpenAPI documentation generation and Pydantic request/response validation."),
    ("JWT", "JSON Web Token — a signed, compact token format used for stateless bearer authentication in this project."),
    ("LLM", "Large Language Model — an AI model (Claude) used here for resume parsing, document generation, and coaching workflows."),
    ("Micro F1", "F1 computed by summing true positives, false positives, and false negatives across all cases before calculating precision and recall; less sensitive to class imbalance than macro F1."),
    ("Prompt Engineering", "The practice of designing LLM input text to guide model outputs; used here to constrain Claude from fabricating skills or qualifications."),
    ("Skill Normalisation", "The mapping of skill aliases and abbreviations to canonical lowercase forms before matching (e.g. ML → machine learning, k8s → kubernetes)."),
    ("SQLAlchemy", "A Python ORM and SQL toolkit; used here to define and query the SQLite data model."),
    ("TF-IDF", "Term Frequency–Inverse Document Frequency — a classical NLP weighting scheme used as a fallback similarity backend when sentence-transformers is unavailable."),
    ("Weighted Alignment Score", "The matching engine's overall 0–100 score; a weighted sum of required skills (40%), experience (30%), preferred skills (15%), and education (15%) components."),
]
for term, definition in glossary:
    p = doc.add_paragraph()
    r = p.add_run(f"{term}: ")
    r.bold = True; r.font.name = "Times New Roman"; r.font.size = Pt(12)
    p.add_run(definition).font.name = "Times New Roman"
    p.paragraph_format.space_after = Pt(4)
add_page_break(doc)

# ═══════════════════════════════════════════════════════════════════════════
# APPENDIX J — REPRESENTATIVE CODE EXCERPTS
# ═══════════════════════════════════════════════════════════════════════════
add_heading(doc, "APPENDIX J — REPRESENTATIVE CODE EXCERPTS", 1)
add_body(doc, "The following excerpts illustrate key implementation patterns. Full source is in the project repository.")

add_heading(doc, "J.1  Matching Engine Scoring Formula (backend/services/matching_engine.py)", 3)
code1 = (
    "def compute_overall_score(\n"
    "    required_skill_score: float,\n"
    "    preferred_skill_score: float,\n"
    "    experience_score: float,\n"
    "    education_score: float,\n"
    ") -> int:\n"
    "    raw = (\n"
    "        0.40 * required_skill_score\n"
    "      + 0.15 * preferred_skill_score\n"
    "      + 0.30 * experience_score\n"
    "      + 0.15 * education_score\n"
    "    )\n"
    "    return max(0, min(100, round(raw)))"
)
p = doc.add_paragraph()
p.style = "No Spacing"
p.add_run(code1).font.name = "Courier New"
doc.add_paragraph()

add_heading(doc, "J.2  Skill Match Tier Classification (backend/services/matching_engine.py)", 3)
code2 = (
    "def classify_skill(jd_skill: str, corpus: list[str]) -> tuple[str, float]:\n"
    "    norm = normalize(jd_skill)\n"
    "    for item in corpus:\n"
    "        if normalize(item) == norm:\n"
    "            return 'exact', 1.0\n"
    "    best_sim = max((similarity(norm, normalize(c)) for c in corpus), default=0.0)\n"
    "    if best_sim >= 0.65:\n"
    "        return 'semantic', best_sim\n"
    "    if best_sim >= 0.45:\n"
    "        return 'partial', best_sim * 0.5\n"
    "    return 'missing', 0.0"
)
p = doc.add_paragraph()
p.style = "No Spacing"
p.add_run(code2).font.name = "Courier New"
doc.add_paragraph()

add_heading(doc, "J.3  PDF Upload Validation (backend/routers/resumes.py)", 3)
code3 = (
    "MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MiB\n\n"
    "async def upload_resume(file: UploadFile, db: Session, current_user: User):\n"
    "    if not file.filename.lower().endswith('.pdf'):\n"
    "        raise HTTPException(400, 'Only PDF files are accepted')\n"
    "    data = await file.read(MAX_UPLOAD_BYTES + 1)\n"
    "    if len(data) > MAX_UPLOAD_BYTES:\n"
    "        raise HTTPException(413, 'File exceeds 5 MiB limit')\n"
    "    if not data.startswith(b'%PDF-'):\n"
    "        raise HTTPException(400, 'File does not appear to be a valid PDF')\n"
    "    # ... continue with parsing"
)
p = doc.add_paragraph()
p.style = "No Spacing"
p.add_run(code3).font.name = "Courier New"
doc.add_paragraph()

add_heading(doc, "J.4  JWT Authentication Dependency (backend/auth.py)", 3)
code4 = (
    "def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):\n"
    "    try:\n"
    "        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])\n"
    "        user_id: int = int(payload.get('sub'))\n"
    "    except (JWTError, TypeError, ValueError):\n"
    "        raise HTTPException(status_code=401, detail='Invalid or expired token')\n"
    "    user = db.query(User).filter(User.id == user_id).first()\n"
    "    if user is None or not user.is_active:\n"
    "        raise HTTPException(status_code=401, detail='User not found or inactive')\n"
    "    return user"
)
p = doc.add_paragraph()
p.style = "No Spacing"
p.add_run(code4).font.name = "Courier New"

# ── Save ──────────────────────────────────────────────────────────────────
output_path = r"C:\CODEING\projects\AI_Resume\AI_Resume_Tailor_Project_Report.docx"
doc.save(output_path)
print(f"Saved: {output_path}")
