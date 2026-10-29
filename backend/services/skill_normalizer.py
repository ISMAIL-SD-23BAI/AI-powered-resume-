"""
Skill normalizer: maps abbreviations and aliases to canonical skill names.

Design principles:
- Only normalize CLEARLY equivalent terms (abbreviations, common aliases).
- Do NOT conflate related-but-distinct skills (e.g. "Docker" ≠ "Kubernetes").
- Be conservative: false negatives (missed synonyms) are less harmful than
  false positives (wrongly matching unrelated skills).
- The canonical form is always the most widely recognized full name.
"""

# fmt: off
# Maps every alias (lowercase) → canonical form (lowercase).
# Keys include the canonical itself so lookups always succeed.
_ALIAS_MAP: dict[str, str] = {
    # ── Programming languages ───────────────────────────────────────────────
    "python":                   "python",
    "python3":                  "python",
    "python 3":                 "python",
    "py":                       "python",

    "javascript":               "javascript",
    "js":                       "javascript",
    "ecmascript":               "javascript",
    "es6":                      "javascript",
    "es2015":                   "javascript",
    "es2020":                   "javascript",

    "typescript":               "typescript",
    "ts":                       "typescript",

    "java":                     "java",

    "c++":                      "c++",
    "cpp":                      "c++",
    "c plus plus":              "c++",

    "c#":                       "c#",
    "csharp":                   "c#",
    "c sharp":                  "c#",
    ".net":                     "c#",
    "dotnet":                   "c#",

    "golang":                   "go",
    "go":                       "go",

    "r":                        "r",
    "r language":               "r",

    "kotlin":                   "kotlin",
    "swift":                    "swift",
    "ruby":                     "ruby",
    "php":                      "php",
    "scala":                    "scala",
    "matlab":                   "matlab",
    "bash":                     "bash",
    "shell scripting":          "bash",
    "shell script":             "bash",

    # ── AI / ML ──────────────────────────────────────────────────────────────
    "machine learning":         "machine learning",
    "ml":                       "machine learning",

    "deep learning":            "deep learning",
    "dl":                       "deep learning",
    "neural networks":          "deep learning",
    "neural network":           "deep learning",

    "natural language processing": "natural language processing",
    "nlp":                      "natural language processing",
    "text processing":          "natural language processing",

    "computer vision":          "computer vision",
    "cv":                       "computer vision",
    "image processing":         "computer vision",

    "artificial intelligence":  "artificial intelligence",
    "ai":                       "artificial intelligence",

    "generative ai":            "generative ai",
    "gen ai":                   "generative ai",
    "genai":                    "generative ai",

    "large language models":    "large language models",
    "llm":                      "large language models",
    "llms":                     "large language models",

    "reinforcement learning":   "reinforcement learning",
    "rl":                       "reinforcement learning",

    "data science":             "data science",
    "ds":                       "data science",

    # ── Cloud ────────────────────────────────────────────────────────────────
    "amazon web services":      "aws",
    "aws":                      "aws",

    "google cloud platform":    "google cloud",
    "google cloud":             "google cloud",
    "gcp":                      "google cloud",

    "microsoft azure":          "azure",
    "azure":                    "azure",

    # ── Databases ────────────────────────────────────────────────────────────
    "postgresql":               "postgresql",
    "postgres":                 "postgresql",

    "mongodb":                  "mongodb",
    "mongo":                    "mongodb",

    "mysql":                    "mysql",
    "sqlite":                   "sqlite",
    "sql":                      "sql",
    "redis":                    "redis",
    "elasticsearch":            "elasticsearch",
    "elastic search":           "elasticsearch",

    # ── Containers / DevOps ──────────────────────────────────────────────────
    "kubernetes":               "kubernetes",
    "k8s":                      "kubernetes",

    "docker":                   "docker",
    "containerization":         "docker",

    "ci/cd":                    "ci/cd",
    "continuous integration":   "ci/cd",
    "continuous deployment":    "ci/cd",
    "continuous delivery":      "ci/cd",
    "cicd":                     "ci/cd",

    "terraform":                "terraform",
    "ansible":                  "ansible",
    "jenkins":                  "jenkins",
    "github actions":           "github actions",
    "gitlab ci":                "gitlab ci",

    # ── Frameworks & libraries ───────────────────────────────────────────────
    "fastapi":                  "fastapi",
    "fast api":                 "fastapi",

    "react":                    "react",
    "react.js":                 "react",
    "reactjs":                  "react",

    "node.js":                  "node.js",
    "nodejs":                   "node.js",
    "node":                     "node.js",

    "vue.js":                   "vue",
    "vuejs":                    "vue",
    "vue":                      "vue",

    "angular":                  "angular",
    "angularjs":                "angular",

    "django":                   "django",
    "flask":                    "flask",
    "spring boot":              "spring boot",
    "spring":                   "spring boot",

    "tensorflow":               "tensorflow",
    "tf":                       "tensorflow",

    "pytorch":                  "pytorch",
    "torch":                    "pytorch",

    "scikit-learn":             "scikit-learn",
    "sklearn":                  "scikit-learn",

    "pandas":                   "pandas",
    "numpy":                    "numpy",
    "hugging face":             "hugging face",
    "huggingface":              "hugging face",

    # ── Concepts ─────────────────────────────────────────────────────────────
    "rest":                     "rest api",
    "restful":                  "rest api",
    "rest api":                 "rest api",
    "restful api":              "rest api",
    "restful apis":             "rest api",

    "graphql":                  "graphql",
    "graph ql":                 "graphql",

    "microservices":            "microservices",
    "micro services":           "microservices",
    "microservice":             "microservices",
    "microservice architecture": "microservices",

    "object-oriented programming": "oop",
    "object oriented programming": "oop",
    "oop":                      "oop",
    "object oriented":          "oop",

    "data structures":          "data structures",
    "data structure":           "data structures",
    "algorithms":               "algorithms",
    "algo":                     "algorithms",

    "agile":                    "agile",
    "scrum":                    "scrum",
    "devops":                   "devops",

    "git":                      "git",
    "version control":          "git",
    "github":                   "github",
    "gitlab":                   "gitlab",

    "linux":                    "linux",
    "unix":                     "linux",

    "api":                      "api",
    "apis":                     "api",
}
# fmt: on


def normalize(skill: str) -> str:
    """
    Return the canonical lowercase form of a skill.
    If no mapping exists, returns the skill lowercased and stripped.

    >>> normalize("ML")
    'machine learning'
    >>> normalize("K8s")
    'kubernetes'
    >>> normalize("unknown skill XYZ")
    'unknown skill xyz'
    """
    return _ALIAS_MAP.get(skill.lower().strip(), skill.lower().strip())


def normalize_list(skills: list[str]) -> list[str]:
    """Normalize a list of skills, removing duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        norm = normalize(s)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def skills_match(skill_a: str, skill_b: str) -> bool:
    """Return True if two skill strings are equivalent after normalization."""
    return normalize(skill_a) == normalize(skill_b)
