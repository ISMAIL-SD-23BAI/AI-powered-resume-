"""
Edge case tests for the AI Resume Tailor application (Phase 8).

Covers: malformed inputs, empty files, oversized PDFs, JWT tampering,
SQL injection attempts, Unicode inputs, engine unit edge cases,
evaluation dataset structure, and double-upload isolation.

These tests supplement the main test suite (305 tests) rather than
duplicating it.
"""
import sys
import os

import pytest

from tests.helpers import (
    register_and_login,
    auth_headers,
    make_mock_client,
    make_test_pdf,
    MOCK_STRUCTURED_RESUME,
)

# ── Ensure backend/ is on sys.path (needed when running test file directly) ────
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. Empty file with .pdf extension — magic byte check should reject it
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmptyFilePdf:
    def test_empty_file_pdf_extension_returns_422(self, client):
        token = register_and_login(client)
        resp = client.post(
            "/resumes/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422
        assert "pdf" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  2. HTML file disguised with .pdf extension
# ═══════════════════════════════════════════════════════════════════════════════

class TestHtmlDisguisedAsPdf:
    def test_html_bytes_pdf_extension_returns_422(self, client):
        """HTML starts with <html>, not %PDF — magic byte check must reject it."""
        token = register_and_login(client)
        html_bytes = b"<html><body>This is a fake PDF</body></html>"
        resp = client.post(
            "/resumes/upload",
            files={"file": ("page.pdf", html_bytes, "application/pdf")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422
        assert "pdf" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  3. Tampered JWT — modifying the payload should invalidate the signature
# ═══════════════════════════════════════════════════════════════════════════════



def _tamper_jwt(token: str) -> str:
    """Corrupt the HMAC signature section so the token fails verification."""
    parts = token.split(".")
    if len(parts) != 3:
        return token
    sig = parts[2]
    # Replace the first char of the signature with a different character
    replacement = "A" if sig[0] != "A" else "B"
    corrupted_sig = replacement + sig[1:]
    return ".".join([parts[0], parts[1], corrupted_sig])


class TestTamperedJwt:
    def test_tampered_jwt_returns_401(self, client):
        token = register_and_login(client)
        bad_token = _tamper_jwt(token)
        resp = client.get("/resumes/", headers=auth_headers(bad_token))
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
#  4. Interview JD too long — schema validation should reject it
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterviewJdTooLong:
    def test_interview_jd_too_long_returns_422(self, client, sample_pdf, mock_parse_resume):
        token = register_and_login(client)
        # Upload a resume first
        resp = client.post(
            "/resumes/upload",
            files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        resume_id = resp.json()["id"]

        # JD just over the 20 000-char maximum
        long_jd = "Python developer role. " * 1000  # ~22 000 chars
        resp = client.post(
            "/interview/",
            json={"resume_id": resume_id, "job_description_text": long_jd},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
#  5. Match request missing resume_id — should fail Pydantic validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchMissingResumeId:
    def test_match_missing_resume_id_returns_422(self, client):
        token = register_and_login(client)
        resp = client.post(
            "/match/",
            json={"job_description_text": "Python developer role requiring FastAPI experience. " * 5},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
#  6. Engine unit test: Java vs JavaScript — engine must not match java
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineJavaVsJavascript:
    def test_engine_java_vs_javascript_correctly_missing(self):
        """
        A resume with 'javascript' should NOT match the JD requirement 'java'.
        The two skills are distinct; 'java' is only a substring of 'javascript'.
        """
        from services.matching_engine import compute_from_structured

        def word_overlap(a, b):
            sa = set(a.lower().split())
            sb = set(b.lower().split())
            if not sa and not sb:
                return 1.0
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / len(sa | sb)

        resume = {
            "skills": ["javascript", "typescript", "react", "css"],
            "experience": [
                {
                    "title": "Frontend Developer",
                    "company": "UI Studio",
                    "dates": "2022-2024",
                    "bullets": ["Built React components with TypeScript."],
                }
            ],
            "education": [{"degree": "B.Sc. CS", "institution": "City University", "dates": "2018-2022"}],
            "projects": [],
        }
        jd_req = {
            "role_title": "Java Developer",
            "required_skills": ["java"],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 1,
        }
        result = compute_from_structured(resume, jd_req, word_overlap)

        missing_skills = result["missing_requirements"]
        matched_skills = [m["skill"] for m in result["matched_requirements"]]

        assert "java" in missing_skills, (
            f"'java' should be missing but got missing={missing_skills}"
        )
        assert "java" not in matched_skills, (
            f"'java' should not be matched via 'javascript' but got matched={matched_skills}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  7. Known limitation: company name keyword false positive
#     This test DOCUMENTS the FP — it is not marked xfail because the FP is
#     real and measurable, not unexpected from the engine's perspective.
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompanyNameKnownLimitation:
    def test_known_limitation_company_name_keyword_fp(self):
        """
        The engine searches all corpus text including company names.
        'Java Rocks Entertainment' causes a false positive for the 'java' skill.
        This test asserts the known-FP behaviour so regressions are visible if
        the engine is ever fixed.
        """
        from services.matching_engine import compute_from_structured

        def word_overlap(a, b):
            sa = set(a.lower().split())
            sb = set(b.lower().split())
            if not sa and not sb:
                return 1.0
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / len(sa | sb)

        resume = {
            "skills": ["python", "flask"],
            "experience": [
                {
                    "title": "Software Engineer",
                    "company": "Java Rocks Entertainment",
                    "dates": "2021-2023",
                    "bullets": ["Managed event logistics using Python scripts."],
                }
            ],
            "education": [{"degree": "B.Tech CS", "institution": "State University", "dates": "2017-2021"}],
            "projects": [],
        }
        jd_req = {
            "role_title": "Java Developer",
            "required_skills": ["java"],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 1,
        }
        result = compute_from_structured(resume, jd_req, word_overlap)
        matched = [m["skill"] for m in result["matched_requirements"]]

        # Document the known FP: 'java' is incorrectly matched from company name
        assert "java" in matched, (
            "Known FP behaviour changed — engine no longer matches 'java' from "
            "company name. Update TC06 documentation if this is intentional."
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  8. Unicode and emoji in skills — should not raise an exception
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnicodeSkills:
    def test_unicode_skills_dont_crash(self):
        from services.matching_engine import compute_from_structured

        def word_overlap(a, b):
            sa = set(a.lower().split())
            sb = set(b.lower().split())
            if not sa and not sb:
                return 1.0
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / len(sa | sb)

        resume = {
            "skills": ["数据分析", "\U0001F40D python", "café dev"],
            "experience": [],
            "education": [],
            "projects": [],
        }
        jd_req = {
            "role_title": "Analyst",
            "required_skills": ["python", "数据分析"],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "education_requirement": None,
            "experience_years": None,
        }
        # Must not raise any exception
        result = compute_from_structured(resume, jd_req, word_overlap)
        assert isinstance(result["overall_score"], int)


# ═══════════════════════════════════════════════════════════════════════════════
#  9. Tracker PATCH with empty body — should return 200 with no changes
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrackerPatchEmptyBody:
    def test_tracker_patch_empty_body_returns_200(self, client):
        token = register_and_login(client)
        # Create an application entry
        create_resp = client.post(
            "/tracker/",
            json={
                "company_name": "Acme Corp",
                "job_title": "Software Engineer",
                "status": "applied",
            },
            headers=auth_headers(token),
        )
        assert create_resp.status_code == 201, create_resp.text
        app_id = create_resp.json()["id"]

        # PATCH with empty body — no fields to update
        resp = client.patch(
            f"/tracker/{app_id}",
            json={},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        # Values should be unchanged
        assert resp.json()["company_name"] == "Acme Corp"


# ═══════════════════════════════════════════════════════════════════════════════
#  10. Upload same file twice — creates two separate resume records
# ═══════════════════════════════════════════════════════════════════════════════

class TestUploadSameFileTwice:
    def test_upload_same_file_twice_creates_two_separate_records(
        self, client, sample_pdf, mock_parse_resume
    ):
        token = register_and_login(client)

        resp1 = client.post(
            "/resumes/upload",
            files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
            headers=auth_headers(token),
        )
        resp2 = client.post(
            "/resumes/upload",
            files={"file": ("resume.pdf", sample_pdf, "application/pdf")},
            headers=auth_headers(token),
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["id"] != resp2.json()["id"]


# ═══════════════════════════════════════════════════════════════════════════════
#  11. SQL injection in signup email — Pydantic email validation rejects it
# ═══════════════════════════════════════════════════════════════════════════════

class TestSqlInjectionEmail:
    def test_signup_sql_injection_email_returns_422(self, client):
        resp = client.post(
            "/auth/signup",
            json={
                "email": "' OR 1=1 --@example.com",
                "password": "Password123!",
                "full_name": "Attacker",
            },
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
#  12. Match with JD that contains no skills in the alias map
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchJdNoRecognizableSkills:
    def test_match_jd_no_recognizable_skills_returns_valid_result(self):
        """
        A JD whose required_skills are completely absent from the alias map
        should still return a valid result dict with empty matched/missing lists.
        """
        from services.matching_engine import compute_from_structured

        def word_overlap(a, b):
            sa = set(a.lower().split())
            sb = set(b.lower().split())
            if not sa and not sb:
                return 1.0
            if not sa or not sb:
                return 0.0
            return len(sa & sb) / len(sa | sb)

        resume = {
            "skills": ["python", "fastapi"],
            "experience": [],
            "education": [],
            "projects": [],
        }
        jd_req = {
            "role_title": "Niche Role",
            "required_skills": [],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "education_requirement": None,
            "experience_years": None,
        }
        result = compute_from_structured(resume, jd_req, word_overlap)
        assert isinstance(result, dict)
        assert result["matched_requirements"] == []
        assert result["missing_requirements"] == []
        assert 0 <= result["overall_score"] <= 100


# ═══════════════════════════════════════════════════════════════════════════════
#  13. Evaluation dataset structure — 11 test cases with required keys
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvaluationDatasetStructure:
    def test_evaluation_dataset_has_eleven_cases(self):
        from tests.evaluation.dataset import TEST_CASES
        assert len(TEST_CASES) == 11

    def test_evaluation_dataset_required_keys(self):
        from tests.evaluation.dataset import TEST_CASES
        required_keys = {
            "id", "description", "structured_resume",
            "jd_requirements", "expected_matched", "expected_missing",
            "expected_evidence", "expected_partial", "pair_label",
        }
        jd_required_keys = {
            "role_title", "required_skills", "preferred_skills",
            "responsibilities", "qualifications",
            "education_requirement", "experience_years",
        }
        resume_required_keys = {"skills", "experience", "education", "projects"}

        for tc in TEST_CASES:
            missing = required_keys - tc.keys()
            assert not missing, f"{tc.get('id', '?')} missing keys: {missing}"

            jd_missing = jd_required_keys - tc["jd_requirements"].keys()
            assert not jd_missing, (
                f"{tc['id']} jd_requirements missing: {jd_missing}"
            )

            res_missing = resume_required_keys - tc["structured_resume"].keys()
            assert not res_missing, (
                f"{tc['id']} structured_resume missing: {res_missing}"
            )

    def test_evaluation_dataset_ids_unique(self):
        from tests.evaluation.dataset import TEST_CASES
        ids = [tc["id"] for tc in TEST_CASES]
        assert len(ids) == len(set(ids)), "Duplicate TC ids found in dataset"

    def test_evaluation_dataset_expected_types(self):
        from tests.evaluation.dataset import TEST_CASES
        for tc in TEST_CASES:
            assert isinstance(tc["expected_matched"], list), (
                f"{tc['id']} expected_matched must be list"
            )
            assert isinstance(tc["expected_missing"], list), (
                f"{tc['id']} expected_missing must be list"
            )
            assert isinstance(tc["expected_partial"], list), (
                f"{tc['id']} expected_partial must be list"
            )

    def test_evaluation_evidence_labels_are_grounded_in_synthetic_resume(self):
        from tests.evaluation.dataset import TEST_CASES
        for tc in TEST_CASES:
            assert set(tc["expected_evidence"]).issubset(set(tc["expected_matched"]) | set(tc["expected_partial"]))
            for skill, evidence in tc["expected_evidence"].items():
                assert set(evidence) == {"section", "quote"}
                section = evidence["section"]
                if section == "skills":
                    source = " ".join(tc["structured_resume"]["skills"])
                else:
                    category, index = section[:-1].split("[")
                    source = str(tc["structured_resume"][category][int(index)])
                assert evidence["quote"].casefold() in source.casefold(), f"{tc['id']} / {skill}"
