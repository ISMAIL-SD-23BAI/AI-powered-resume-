"""
Evaluation dataset for the AI Resume Tailor matching engine.

All resumes and job descriptions are SYNTHETIC and do not represent any real person.
They were designed to exercise specific matching behaviours documented in each case.

Ground-truth labels (`expected_matched`, `expected_missing`) use the canonical
normalized skill names produced by services.skill_normalizer.normalize_list(), since
that is what the engine stores in its result dicts.

Evaluation uses the deterministic word-overlap (Jaccard) similarity function —
no ML model or internet connection is required.
"""

TEST_CASES = [
    # ─────────────────────────────────────────────────────────────────────────────
    # TC01  Perfect match — all required skills present verbatim in skills list.
    # Expected behaviour: engine matches all four; score near-perfect.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC01_perfect_match",
        "description": (
            "All four required skills appear verbatim in the resume skills list. "
            "The engine should achieve exact matches with confidence 1.0 for every "
            "required skill."
        ),
        "structured_resume": {
            "skills": ["python", "fastapi", "postgresql", "docker"],
            "experience": [
                {
                    "title": "Backend Engineer",
                    "company": "Acme Software",
                    "dates": "2022-2024",
                    "bullets": [
                        "Built REST APIs with FastAPI and Python.",
                        "Managed PostgreSQL databases in production.",
                        "Containerised services using Docker.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Computer Science",
                    "institution": "State University",
                    "dates": "2018-2022",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Backend Engineer",
            "required_skills": ["python", "fastapi", "postgresql", "docker"],
            "preferred_skills": ["redis", "kubernetes"],
            "responsibilities": [
                "Build and maintain REST APIs.",
                "Manage relational databases.",
                "Deploy services in containers.",
            ],
            "qualifications": ["Bachelor degree in CS or related"],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        "expected_matched": ["python", "fastapi", "postgresql", "docker"],
        "expected_missing": [],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC02  Synonym / abbreviation match — resume uses abbreviations only.
    # Expected behaviour: engine normalises ML→machine learning, k8s→kubernetes,
    # DL→deep learning, py→python and matches all four.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC02_synonym_match",
        "description": (
            "Resume skills list contains only abbreviations (ML, k8s, DL, py). "
            "The JD uses canonical long-form names. The engine must expand aliases "
            "and match; the keyword baseline cannot."
        ),
        "structured_resume": {
            "skills": ["ML", "k8s", "DL", "py"],
            "experience": [
                {
                    "title": "ML Engineer",
                    "company": "AI Startup",
                    "dates": "2021-2023",
                    "bullets": [
                        "Trained deep neural networks for image recognition.",
                        "Deployed models to a k8s cluster.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Artificial Intelligence",
                    "institution": "Tech Institute",
                    "dates": "2017-2021",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Machine Learning Engineer",
            "required_skills": ["machine learning", "kubernetes", "deep learning", "python"],
            "preferred_skills": ["tensorflow", "pytorch"],
            "responsibilities": [
                "Design and train ML models.",
                "Orchestrate workloads on Kubernetes.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        # After normalize_list the engine stores canonical forms:
        "expected_matched": ["machine learning", "kubernetes", "deep learning", "python"],
        "expected_missing": [],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC03  Evidence only in experience bullets — skills section is empty.
    # Expected behaviour: engine finds each skill by scanning experience bullets;
    # keyword baseline also succeeds since skills appear verbatim in bullet text.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC03_evidence_in_bullets",
        "description": (
            "The resume has no skills section. All required skills appear explicitly "
            "in experience bullet text. The engine must locate them via corpus search."
        ),
        "structured_resume": {
            "skills": [],
            "experience": [
                {
                    "title": "Data Analyst",
                    "company": "Retail Analytics Co.",
                    "dates": "2020-2023",
                    "bullets": [
                        "Analyzed sales data using pandas and matplotlib to produce weekly reports.",
                        "Built scikit-learn classification models to predict churn.",
                        "Automated ETL pipelines in Python.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Sc. Statistics",
                    "institution": "National University",
                    "dates": "2016-2020",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Data Scientist",
            "required_skills": ["python", "pandas", "scikit-learn", "matplotlib"],
            "preferred_skills": ["tensorflow", "numpy"],
            "responsibilities": [
                "Build predictive models.",
                "Produce data visualisations.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        "expected_matched": ["python", "pandas", "scikit-learn", "matplotlib"],
        "expected_missing": [],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC04  Mixed — one required skill present, four missing.
    # Expected behaviour: engine matches only Python; missing fastapi, docker,
    # kubernetes, postgresql.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC04_partial_match",
        "description": (
            "Resume has Python, Django, and Git. JD requires Python, FastAPI, Docker, "
            "Kubernetes, PostgreSQL. Django is distinct from FastAPI; engine must not "
            "conflate them. Only Python is matched."
        ),
        "structured_resume": {
            "skills": ["python", "django", "git"],
            "experience": [
                {
                    "title": "Junior Developer",
                    "company": "Web Agency",
                    "dates": "2023-2024",
                    "bullets": [
                        "Built Django web applications for small businesses.",
                        "Maintained Git repositories.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Information Technology",
                    "institution": "City College",
                    "dates": "2019-2023",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Backend Engineer",
            "required_skills": ["python", "fastapi", "docker", "kubernetes", "postgresql"],
            "preferred_skills": ["redis"],
            "responsibilities": [
                "Develop microservices with FastAPI.",
                "Deploy containers with Docker and Kubernetes.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 1,
        },
        "expected_matched": ["python"],
        "expected_missing": ["fastapi", "docker", "kubernetes", "postgresql"],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC05  Irrelevant resume — completely wrong domain.
    # Expected behaviour: zero required skills matched; all appear in missing list.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC05_irrelevant_resume",
        "description": (
            "Resume is from a retail worker with no technical skills. JD is for an "
            "ML engineer. No required skill should be matched."
        ),
        "structured_resume": {
            "skills": ["inventory management", "customer service", "microsoft excel"],
            "experience": [
                {
                    "title": "Store Associate",
                    "company": "Retail Chain",
                    "dates": "2019-2024",
                    "bullets": [
                        "Restocked shelves and managed inventory daily.",
                        "Assisted customers with product queries.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "High School Diploma",
                    "institution": "Central High School",
                    "dates": "2015-2019",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "ML Engineer",
            "required_skills": ["python", "tensorflow", "pytorch", "cuda"],
            "preferred_skills": ["docker", "kubernetes"],
            "responsibilities": [
                "Train and deploy neural networks.",
                "Optimise GPU workloads with CUDA.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        "expected_matched": [],
        "expected_missing": ["python", "tensorflow", "pytorch", "cuda"],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC06  Misleading keyword overlap — "Java" appears only in company name.
    # Ground truth: java IS missing (it is not a programming skill on this resume).
    # KNOWN LIMITATION: the engine searches ALL corpus text including company names,
    # so "java" in "Java Rocks Entertainment" causes a FALSE POSITIVE.
    # This test documents that known limitation honestly.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC06_misleading_keyword_overlap",
        "description": (
            "KNOWN LIMITATION. The company name contains 'Java' as a proper noun. "
            "The JD requires Java the programming language. Ground truth: java is "
            "missing. The engine incorrectly matches it (FP) because it does not "
            "distinguish programming-skill tokens from company-name tokens."
        ),
        "structured_resume": {
            "skills": ["python", "flask"],
            "experience": [
                {
                    "title": "Software Engineer",
                    "company": "Java Rocks Entertainment",
                    "dates": "2021-2023",
                    "bullets": [
                        "Managed event logistics using Python scripts.",
                        "Built internal tools with Flask.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Computer Science",
                    "institution": "State University",
                    "dates": "2017-2021",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Java Developer",
            "required_skills": ["java"],
            "preferred_skills": ["spring boot"],
            "responsibilities": ["Develop enterprise Java applications."],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        # Ground truth: java is NOT a programming skill on this resume.
        "expected_matched": [],
        "expected_missing": ["java"],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC07  Java vs JavaScript disambiguation.
    # The resume has "javascript"; the JD requires "java". These are distinct skills.
    # Expected behaviour: engine correctly reports java as MISSING.
    # The plain-substring baseline FAILS here ("java" is a substring of "javascript").
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC07_java_vs_javascript",
        "description": (
            "Resume skills: javascript, typescript, react, css. JD requires java. "
            "'java' is a substring of 'javascript' but they are different skills. "
            "The engine normalises and splits correctly; the baseline does not."
        ),
        "structured_resume": {
            "skills": ["javascript", "typescript", "react", "css"],
            "experience": [
                {
                    "title": "Frontend Developer",
                    "company": "UI Studio",
                    "dates": "2022-2024",
                    "bullets": [
                        "Built React components with TypeScript.",
                        "Wrote CSS animations for marketing pages.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Sc. Computer Science",
                    "institution": "City University",
                    "dates": "2018-2022",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Java Backend Developer",
            "required_skills": ["java"],
            "preferred_skills": ["spring boot", "postgresql"],
            "responsibilities": ["Build Java backend services."],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 1,
        },
        "expected_matched": [],
        "expected_missing": ["java"],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC08  Seniority gap — right skills, but experience years not met.
    # Skill matching: all four matched → P=1, R=1.
    # Overall score: lower due to experience-years penalty.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC08_seniority_gap",
        "description": (
            "All four required skills are present. JD requires 5 years experience; "
            "resume has only 1 year (2023–2024). Skill matching should be perfect; "
            "overall_score reflects the experience gap."
        ),
        "structured_resume": {
            "skills": ["python", "fastapi", "postgresql", "docker"],
            "experience": [
                {
                    "title": "Junior Backend Developer",
                    "company": "TechStart",
                    "dates": "2023-2024",
                    "bullets": [
                        "Developed FastAPI microservices in Python.",
                        "Maintained PostgreSQL schemas.",
                        "Deployed services in Docker containers.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Software Engineering",
                    "institution": "Engineering College",
                    "dates": "2019-2023",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Senior Backend Engineer",
            "required_skills": ["python", "fastapi", "postgresql", "docker"],
            "preferred_skills": ["kubernetes", "terraform"],
            "responsibilities": [
                "Lead backend architecture decisions.",
                "Build high-throughput FastAPI services.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 5,
        },
        "expected_matched": ["python", "fastapi", "postgresql", "docker"],
        "expected_missing": [],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC09  All required skills missing — administrative resume, dev JD.
    # Expected behaviour: all five required skills absent; matched list empty.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC09_all_missing",
        "description": (
            "Resume is from an office administrator with no development skills. "
            "JD requires React, TypeScript, Node.js, MongoDB, GraphQL. "
            "None should be matched."
        ),
        "structured_resume": {
            "skills": ["microsoft word", "microsoft excel", "powerpoint", "data entry"],
            "experience": [
                {
                    "title": "Office Administrator",
                    "company": "Healthcare Clinic",
                    "dates": "2018-2024",
                    "bullets": [
                        "Maintained patient records in Excel.",
                        "Scheduled appointments and managed correspondence.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.A. Business Administration",
                    "institution": "Commerce College",
                    "dates": "2014-2018",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Frontend Developer",
            "required_skills": ["react", "typescript", "node.js", "mongodb", "graphql"],
            "preferred_skills": ["docker"],
            "responsibilities": [
                "Build React applications.",
                "Develop Node.js backend services.",
            ],
            "qualifications": [],
            "education_requirement": "bachelor",
            "experience_years": 2,
        },
        "expected_matched": [],
        "expected_missing": ["react", "typescript", "node.js", "mongodb", "graphql"],
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TC10  Education mismatch — all skills present, PhD required, bachelor's only.
    # Skill matching: all four matched → P=1, R=1.
    # education_score: penalised (40) because resume has bachelor < phd.
    # ─────────────────────────────────────────────────────────────────────────────
    {
        "id": "TC10_education_mismatch",
        "description": (
            "All four required skills are present and matched. The JD requires a PhD; "
            "the resume shows only a B.Tech. Skill P/R/F1 = 1.0; "
            "education_score is penalised in overall_score."
        ),
        "structured_resume": {
            "skills": ["python", "pytorch", "tensorflow", "cuda"],
            "experience": [
                {
                    "title": "Research Engineer",
                    "company": "AI Lab",
                    "dates": "2022-2024",
                    "bullets": [
                        "Trained PyTorch models on GPU clusters.",
                        "Optimised TensorFlow inference pipelines.",
                        "Used CUDA kernels for custom operations.",
                    ],
                }
            ],
            "education": [
                {
                    "degree": "B.Tech Computer Science",
                    "institution": "Science University",
                    "dates": "2018-2022",
                }
            ],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Research Scientist",
            "required_skills": ["python", "pytorch", "tensorflow", "cuda"],
            "preferred_skills": ["large language models", "hugging face"],
            "responsibilities": [
                "Conduct original ML research.",
                "Publish results in academic venues.",
            ],
            "qualifications": [],
            "education_requirement": "phd",
            "experience_years": 2,
        },
        "expected_matched": ["python", "pytorch", "tensorflow", "cuda"],
        "expected_missing": [],
    },
    {
        "id": "TC11_partial_semantic_evidence",
        "description": (
            "The resume states 'data pipelines and engineering', overlapping the "
            "required skill 'data engineering' without an exact normalized phrase. "
            "The expected classification is partial evidence, not a confirmed match."
        ),
        "structured_resume": {
            "skills": ["data pipelines and engineering"],
            "experience": [],
            "education": [],
            "projects": [],
        },
        "jd_requirements": {
            "role_title": "Data Engineer",
            "required_skills": ["data engineering"],
            "preferred_skills": [],
            "responsibilities": [],
            "qualifications": [],
            "education_requirement": None,
            "experience_years": None,
        },
        "expected_matched": [],
        "expected_missing": [],
        "expected_partial": ["data engineering"],
    },
]

# Hand-authored ground-truth evidence for every required skill. `section` names
# the source field, while `quote` is a short synthetic excerpt that can be
# checked against the dataset itself. Missing skills intentionally have no
# evidence entry. These labels are independent of the engine output.
_EVIDENCE = {
    "TC01_perfect_match": {s: ("skills", s) for s in ("python", "fastapi", "postgresql", "docker")},
    "TC02_synonym_match": {
        "machine learning": ("skills", "ML"), "kubernetes": ("skills", "k8s"),
        "deep learning": ("skills", "DL"), "python": ("skills", "py"),
    },
    "TC03_evidence_in_bullets": {
        "python": ("experience[0]", "Automated ETL pipelines in Python"),
        "pandas": ("experience[0]", "using pandas"),
        "scikit-learn": ("experience[0]", "scikit-learn classification models"),
        "matplotlib": ("experience[0]", "pandas and matplotlib"),
    },
    "TC04_partial_match": {"python": ("skills", "python")},
    "TC05_irrelevant_resume": {},
    "TC06_misleading_keyword_overlap": {},
    "TC07_java_vs_javascript": {},
    "TC08_seniority_gap": {s: ("skills", s) for s in ("python", "fastapi", "postgresql", "docker")},
    "TC09_all_missing": {},
    "TC10_education_mismatch": {s: ("skills", s) for s in ("python", "pytorch", "tensorflow", "cuda")},
    "TC11_partial_semantic_evidence": {"data engineering": ("skills", "data pipelines and engineering")},
}

for _case in TEST_CASES:
    _case.setdefault("expected_partial", [])
    _case["pair_label"] = "relevant" if _case["expected_matched"] or _case["expected_partial"] else "irrelevant"
    _case["expected_evidence"] = {
        skill: {"section": section, "quote": quote}
        for skill, (section, quote) in _EVIDENCE[_case["id"]].items()
    }
