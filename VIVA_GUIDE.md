# AI Resume Tailor — College Project Viva Guide

This guide describes the implementation in this repository as reviewed. It distinguishes working code and measured tests from model/provider behavior that was not exercised live. The project is a prototype that assists with job-application preparation; it does not predict hiring success.

## 1. Problem statement

Applicants often need to identify which resume evidence maps to a job description, tailor application documents, and prepare for interviews. Doing this manually across multiple applications is repetitive. A system can help organize resume evidence and produce drafts, but it must avoid treating missing resume evidence as proof that a person lacks a skill and must not fabricate experience.

## 2. Objectives

- Parse text-based PDF resumes into structured skills, experience, education, and project data.
- Compare structured resume evidence with job-description requirements and explain matches and gaps.
- Generate editable role-focused resume and cover-letter drafts using the existing resume content.
- Provide interview question practice, answer coaching, skill-gap guidance, and an application tracker.
- Persist sessions and records by authenticated user.
- Evaluate requirement matching against a small synthetic labelled dataset and test API correctness.

## 3. Existing system and proposed system

**Existing approach:** Manual resume-to-job comparison, document edits, interview preparation, and application tracking performed separately. Basic keyword search can miss abbreviations and synonyms or falsely match substrings.

**Proposed system:** A browser-based application combines local job-description parsing, resume PDF text extraction, an explainable matching heuristic, Claude-assisted writing/coaching, authenticated persistence, and PDF export in one workflow. The proposal is an integrated student project, not a novel trained model or an experimentally proven replacement for recruiters.

## 4. Contributions and novelty

- Integrated resume upload, parsing, matching, tailoring, interview practice, and job tracking in one prototype.
- Skill normalization and evidence-section reporting make match results more inspectable than a single opaque score.
- User-scoped API queries and repeat-answer history support private practice sessions.
- Prompts and improvement validators are designed to discourage fabricated resume claims; automated output remains review-required.
- A synthetic 11-pair dataset compares strict requirement matching with a simple substring baseline and records evidence localization.

The contribution is an engineering integration and evaluation exercise. It does not claim a new ML algorithm or prove fairness, validity, or hiring prediction.

## 5. Technology stack

- Python 3.12, FastAPI, Uvicorn, Pydantic 2.
- SQLAlchemy 2 and SQLite by default.
- Anthropic SDK for Claude; optional Bedrock SDK path via boto3.
- pypdf for PDF text extraction; ReportLab for PDF output.
- sentence-transformers `all-MiniLM-L6-v2` for semantic vectors if available, with scikit-learn TF-IDF fallback.
- JWT (`python-jose`) and bcrypt password hashing (`passlib` / `bcrypt`).
- slowapi route-level rate limits.
- Static HTML, CSS, and JavaScript frontend.
- pytest, httpx, pytest-mock for tests.

Dependency versions are listed in `requirements.txt`. The default model setting is `claude-sonnet-5`; Anthropic model availability can change. See the official model lifecycle page linked from the README. The current review did not call the live API.

## 6. System architecture

The browser sends multipart PDF uploads and JSON requests to FastAPI. Routers validate request schemas, authenticate bearer tokens, and apply user ownership filters. Service modules parse PDFs/JDs, call the AI provider where required, compute match scores, and build export PDFs. SQLAlchemy persists application state to SQLite. The frontend is served separately as static files.

Three Mermaid diagrams are in the README: overall architecture, resume processing, and matching workflow. The Docker image, if built, contains only the API; the frontend is separate.

## 7. AI and ML algorithms

### Resume and writing tasks

Claude is called by the resume parser, tailoring pipeline, cover-letter generator, improvement engine, interview coach, and skill-gap roadmap flow. Prompts ask for structured JSON or prose and impose factual-preservation instructions. Outputs are parsed and some features validate claims, but prompt constraints do not guarantee correctness. Users must check every generated document and feedback item.

### Job-description parsing

`jd_parser.py` is deterministic local code. It detects section headers such as required, preferred, responsibilities, and qualifications; extracts known skills using the alias map; detects education levels and experience years using regular expressions. It does not call an LLM and can miss unrecognized phrasing or skills.

### Skill normalization and matching

The skill normalizer maps selected known abbreviations/aliases to canonical forms (for example `ML` to `machine learning`) and aims not to merge distinct technologies. Matching first checks normalized evidence, then calls a similarity function over resume text sections. The production function uses 384-dimensional `all-MiniLM-L6-v2` embeddings and cosine similarity when it can load the model. If not, it uses TF-IDF with word/bigram features and cosine similarity. The model is not trained by this project.

The evaluator injects deterministic Jaccard word overlap instead of production embeddings, so the reported synthetic results are repeatable but do not measure the live embedding backend.

### Score formula

```text
overall = round(
    0.40 × required_skill_score
  + 0.15 × preferred_skill_score
  + 0.30 × experience_score
  + 0.15 × education_score
)
```

Every component ranges 0–100. Skill confidences are averaged over unique normalized requirements. Exact matches score 1.0; similarity at least 0.65 is marked semantic; 0.45–0.65 is partial and weighted by half its similarity; lower is not evidenced. Experience combines a 50-point entry base, up to 30 responsibility-similarity points, and up to 20 approximate years points; absence of experience entries gives 10. Education uses the detected bachelor/master/PhD level and fixed rule-based values. These choices are heuristic weights, not learned or calibrated probabilities. See `backend/MATCHING_ENGINE.md`.

## 8. Database design

Tables are declared in `backend/models.py`:

| Table | Main role |
|---|---|
| `users` | Email, password hash, active flag, timestamps |
| `resumes` | User-owned filename, extracted raw text, structured JSON |
| `job_descriptions` | User-owned raw JD and extracted requirements |
| `tailored_resumes` | User, source resume, JD, tailored JSON |
| `cover_letters` | Generated/editable letter linked to a tailored resume |
| `match_results` | User, resume, JD text, match JSON and score |
| `improvement_sessions` | User-owned suggestion session and applied status |
| `learning_roadmaps` | User/resume, classifications, roadmap JSON and progress timestamps |
| `job_applications` | Company, role, dates, status, notes, optional resume links |
| `interview_sessions` | User/resume, job description, question set |
| `interview_answers` | Per-question answer attempts and feedback |

Foreign keys and SQLAlchemy relationships link the records. Most ownership is enforced by filtering queries on the authenticated user ID. Passwords are stored as hashes. SQLite files are not encrypted by this application.

Startup runs `Base.metadata.create_all`, which creates missing tables on a fresh database. There is no Alembic migration history; `create_all` does not alter existing schemas. Existing database upgrades require explicit migration work and backup.

## 9. API design

The API is organized by router and uses JSON request/response schemas. Protected calls send `Authorization: Bearer <JWT>`.

- `/auth`: signup, JSON login, OAuth2 form token.
- `/resumes`: PDF upload and resume CRUD.
- `/tailor`, `/cover-letter`, `/history`, `/export`: tailor, edit/generate letters, history and PDF output.
- `/match`: execute and retrieve match results.
- `/improve`: suggestions and applying accepted edits.
- `/skill-gap`: roadmap generation and status updates.
- `/tracker`: application CRUD and statistics.
- `/interview`: practice sessions, answer submissions, attempts, and deletion.
- `/health`, `/me`: health and authenticated profile.

FastAPI OpenAPI docs at `/docs` describe exact methods and fields. Selected AI routes have slowapi rate limits; these are in-memory and not shared across multiple workers.

## 10. Testing and measured evaluation

The suite has **324 tests passing** in the final full run. It covers authentication, authorization/user isolation, PDF parsing and export, malformed/empty/oversized upload cases, mocked AI failures, tailoring, tracker CRUD, interview flows, and matching. AI calls are mocked in tests; passing tests do not prove live-provider access or output quality.

The evaluation has 11 synthetic resume/JD pairs with exact matches, aliases, bullet evidence, a partial similarity case, missing skills, irrelevant roles, misleading overlap, and experience/education variations. Hand-authored labels define matched, partial, missing skills, and evidence quotes. On the recorded run:

| Metric | Engine | Keyword baseline |
|---|---:|---:|
| Macro precision / recall / F1 | 0.909 / 0.977 / 0.896 | 0.818 / 0.909 / 0.727 |
| Micro precision / recall / F1 | 0.952 / 0.952 / 0.952 | 0.895 / 0.810 / 0.850 |

Evidence source localization was 21/22 (0.955). The dataset surfaced two engine limitations: a Python mention in experience bullets was missed, and Java in a company name caused a false positive. The ranking task was not evaluable because there is no set of candidates sharing the same JD. See `PHASE8_EVALUATION.md` and `backend/tests/evaluation/results.json` for formulas, per-case output, runtime, resource scope, exact commands, and limitations.

## 11. Limitations and future scope

**Known limitations:**

- Small synthetic dataset; it does not represent real applicant populations or estimate generalization.
- No human-labelled real resumes or inter-rater check; no hiring outcome data.
- JD extraction is regex/known-skill based and can miss context.
- Similarity can miss true evidence or use misleading evidence; the evaluation records examples.
- Claude outputs can be incomplete or incorrect despite prompts/validators.
- Experience duration and education scoring are coarse heuristics.
- Production embedding model first load may download weights; fallback scores can differ.
- No database migrations, encrypted persistence, deployment automation, or load/penetration/fairness study.
- Docker build/startup was not executed in the review environment.

**Potential future work:** migration system and backups; database encryption and retention controls; configurable API base URL and HTTPS deployment; explicit PDF text extraction quality checks; richer labelled evaluation including same-JD candidate rankings; repeated latency tests on both similarity backends; human review of AI output; privacy/fairness evaluation and accessible UX.

## 12. Security considerations

- Keep `.env`, credentials, JWT keys, and SQLite files private. Use `.env.example` as a template only.
- The safe submission packager allowlists source/document files and excludes environment secrets, databases, caches, and virtual environments.
- JWT authentication and user-ID filters protect app routes, but do not substitute for production security review.
- API traffic in the local demo is HTTP; do not expose it on an untrusted network.
- Resume-derived text and JDs are sent to the selected AI provider for AI operations; consult provider terms before using real personal data.
- Startup config checks warn rather than fail closed; replace placeholder secrets before execution.
- Rate limits use in-process state; they do not coordinate across workers.

## 13. Exact demonstration steps

Prerequisite: Windows, Python 3.12, dependencies installed, `.env` populated with an Anthropic key and strong JWT secret. Docker is not required.

1. Open PowerShell in the project folder.
2. Start API: `Set-Location backend`, then `..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload`.
3. In a second PowerShell window, set the current directory to the project root and run `.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend`.
4. Browse to `http://127.0.0.1:5500`, create an account, and log in.
5. Upload a synthetic, text-based PDF below 5 MiB. Avoid personal data for the class demonstration.
6. Open **ATS Analyzer**, enter a synthetic job description, run matching, and show requirement evidence/partial/missing results and the disclaimer.
7. Open **Tailor Resume**, generate a role-focused draft and cover letter; review/edit the result and show PDF export.
8. Optionally show **Interview Prep** by selecting the resume and pasting the JD, submit an answer, inspect the rubric/feedback, then repeat it to show attempt history.
9. Optionally create a job in **Job Tracker** and show status/statistics. Use **Skill Gap** or **Improve Resume** only if time permits.
10. Stop the local servers with Ctrl+C. The app data remains in the SQLite database; do not include that DB in the submission.

If an Anthropic key is unavailable, use the already tested unit/API suite and deterministic offline evaluation for the presentation; do not imply a live AI generation was demonstrated. To verify Docker separately, a Docker engine must be installed and available, then build and run the commands in the README.

## 14. Likely viva questions and accurate answers

### Project, design, and scope

1. **What problem does your project address?**  
   It reduces the manual work of comparing a resume with a job description and organizing preparation tasks by bringing parsing, evidence matching, document drafts, interview practice, and application tracking into one prototype.

2. **What is the main objective?**  
   To build a user-scoped web application that assists with resume-to-job document alignment and application preparation, while exposing evidence and limitations.

3. **What is the proposed system?**  
   A static browser frontend, FastAPI API, Python service layer, SQLAlchemy persistence, local matching algorithms, and Claude-assisted writing/coaching.

4. **How does it differ from the existing manual system?**  
   It automates repeated extraction and draft generation, provides a consistent match breakdown, and saves practice/application history. It does not remove the need for human review.

5. **What is novel about the project?**  
   The defensible contribution is integrating several workflows and returning skill evidence with match categories, plus a small reproducible synthetic evaluation. It is not a new foundational ML algorithm.

6. **Does the score say whether a candidate will be hired?**  
   No. It estimates how well the provided resume text documents requirements. It is not a hiring probability or assessment of a person's full ability.

7. **Why use a static frontend?**  
   It avoids a build pipeline for a small demonstration project. The tradeoff is that API URLs are currently configured in frontend JavaScript and are local-development oriented.

### AI, ML, and matching

8. **Which AI model is used?**  
   The default provider model setting is `claude-sonnet-5`; the exact model is configurable through `ANTHROPIC_MODEL`. The matching engine separately uses `all-MiniLM-L6-v2` embeddings when available or TF-IDF fallback. These roles should not be conflated.

9. **Does the project train Claude or the embedding model?**  
   No. Claude is called through an API; the sentence transformer is a pretrained model used for embeddings. This project performs no model fine-tuning.

10. **How is a job description parsed?**  
    Local regex/header logic groups sections and extracts known skills, education level, and years of experience. It can miss unusual wording or skills outside the dictionary.

11. **How are synonyms handled?**  
    A curated alias map canonicalizes selected equivalents such as `ML` to `machine learning`. It is conservative and cannot cover every industry synonym.

12. **What similarity algorithm is used?**  
    Production uses cosine similarity on normalized sentence embeddings when `all-MiniLM-L6-v2` loads. TF-IDF word/bigram cosine is a fallback. The offline evaluation injects Jaccard word overlap for deterministic repeatability.

13. **What is cosine similarity?**  
    It compares vector direction using the dot product divided by vector magnitudes. For normalized sentence embeddings, the dot product is cosine similarity.

14. **What do exact, semantic, partial, and missing mean?**  
    Exact is normalized evidence found; semantic is similarity at least 0.65; partial is 0.45 to below 0.65 and receives half weight; below 0.45 is not evidenced. A missing label means absent from this resume text, not absent from the person.

15. **Explain the final score formula.**  
    It is 40% required skill score, 15% preferred skill score, 30% experience score, and 15% education score. Each component uses rule-based calculations documented in `backend/MATCHING_ENGINE.md`.

16. **Why does the engine use a TF-IDF fallback?**  
    It lets matching continue if the sentence-transformer library/model is unavailable. Because it uses lexical word/bigram overlap rather than dense semantic embeddings, its results can differ.

17. **How do you prevent fabricated resume claims?**  
    Prompts instruct Claude to use source facts only; improvement code performs additional checks on some suggestions; answer feedback labels claims not evidenced by the resume. These controls reduce risk but cannot guarantee zero fabrication, so outputs require review.

### Data, API, and security

18. **What database tables are central?**  
    Users, Resumes, JobDescriptions, TailoredResumes, CoverLetters, MatchResults, ImprovementSessions, LearningRoadmaps, JobApplications, InterviewSessions, and InterviewAnswers.

19. **How are records isolated between users?**  
    JWT identifies the user, and routers filter user-owned queries by that user's database ID. Tests cover cross-user access for key resources.

20. **Are passwords stored as plain text?**  
    No. The password is hashed using bcrypt through passlib. API responses exclude the password hash.

21. **Where is resume content stored?**  
    The app stores extracted raw text and structured JSON in SQLite, along with related generated records. The uploaded PDF bytes are not stored as the resume record.

22. **Is the database encrypted?**  
    No application-level encryption at rest is implemented. Protect the SQLite file with OS permissions and do not submit/share it.

23. **What is the purpose of Pydantic?**  
    It validates request bodies and shapes response objects at the API boundary, helping return consistent 422 validation errors for malformed input.

24. **How does the frontend authenticate?**  
    It stores the JWT in browser localStorage under `token` and sends it as a bearer token. The localStorage approach is simple for a prototype but is not equivalent to a hardened secure-cookie deployment.

25. **What is the API rate limiter?**  
    slowapi applies per-route limits using a key derived from the bearer token or remote address. Its memory is local to a process, so it is not a distributed limiter.

26. **Does the project support schema migrations?**  
    No. Startup `create_all` creates missing tables on a new database but does not evolve existing tables. A migration system is future work.

### Evaluation, testing, and operations

27. **How many tests passed in the reviewed run?**  
    324 tests passed in the final full-suite run, with dependency deprecation warnings. The report lists commands and outcomes.

28. **What is the evaluation dataset?**  
    Eleven synthetic resume/JD pairs with hand-labelled matched, partial, and missing skills and source evidence. It is designed for diagnostic cases, not to represent real applicant data.

29. **What is precision?**  
    TP divided by TP plus FP: among predicted matches, the fraction that are labelled matches.

30. **What is recall?**  
    TP divided by TP plus FN: among labelled matches, the fraction the engine finds.

31. **What was the measured micro F1?**  
    0.952 for the engine and 0.850 for a simple substring baseline on this specific dataset. These are not generalization claims.

32. **What did the evaluation reveal?**  
    It exposed a missed Python mention in experience bullets and a Java false positive caused by a company name. It also showed that the engine detected the synthetic partial-match case.

33. **Did you evaluate ranking quality?**  
    No. Each pair uses a different JD, so there is no same-job candidate ranking group or ranking ground truth.

34. **Why use synthetic resumes?**  
    They avoid sharing real personal information and make expected evidence labels reproducible. The tradeoff is limited realism and generalizability.

35. **Does the full test suite call Anthropic?**  
    AI calls are mocked in the test suite. Passing tests verify application behavior under controlled responses, not live credentials or live model output.

36. **Can an image-only scanned PDF be processed?**  
    The current PDF parser requires extractable text and rejects a PDF with no extracted text. OCR is not implemented.

37. **Was Docker deployment verified?**  
    No. Docker files are present and the app command was corrected, but a Docker executable was unavailable in the review environment, so no image/container run is claimed.

38. **What is the most important limitation?**  
    The matching score depends on resume text extraction, curated aliases, heuristic weights, and a small synthetic evaluation. It should be used as a review aid, not as a final decision.

39. **What would you improve next?**  
    Add Alembic migrations, configurable frontend API origin and HTTPS deployment, richer human-labelled evaluation with shared-JD rankings, repeated load tests, improved PDF OCR/accessibility, and stronger privacy controls.

40. **How do you demonstrate the project?**  
    Start FastAPI and the static frontend on the documented local ports, create an account, upload a synthetic text PDF, run matching, show tailoring/export, then optionally demonstrate interview attempts and tracker status. Exact commands are in the README.
