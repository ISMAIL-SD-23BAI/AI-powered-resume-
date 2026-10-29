"""Build a source submission zip from an explicit allowlist of project files."""
from __future__ import annotations

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist" / "ai_resume_tailor_submission.zip"
TOP_LEVEL_FILES = {
    "README.md", "PHASE8_EVALUATION.md", "VIVA_GUIDE.md", "RELEASE_READINESS.md", "requirements.txt",
    ".env.example", ".gitignore", ".dockerignore", "Dockerfile", "docker-compose.yml",
}
TOP_LEVEL_DIRS = {"backend", "frontend", "tools"}
EXCLUDED_DIRS = {".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", "dist", "build", "node_modules"}
EXCLUDED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".log"}


def allowed(path: Path) -> bool:
    if path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example":
        return False
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> None:
    files = [ROOT / name for name in TOP_LEVEL_FILES if (ROOT / name).is_file()]
    for directory in TOP_LEVEL_DIRS:
        base = ROOT / directory
        if base.exists():
            files.extend(path for path in base.rglob("*") if allowed(path))
    files = sorted(set(files))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if allowed(path):
                archive.write(path, path.relative_to(ROOT).as_posix())

    forbidden_fragments = (".venv/", "__pycache__/", ".pytest_cache/", "/dist/")
    with zipfile.ZipFile(DEST, "r") as archive:
        names = archive.namelist()
        bad = [name for name in names if name == ".env" or name.endswith(".db")
               or name.endswith(".sqlite3") or name.endswith(".pyc")
               or any(fragment in f"/{name}" for fragment in forbidden_fragments)]
        if bad or archive.testzip() is not None:
            DEST.unlink(missing_ok=True)
            raise SystemExit(f"Submission archive validation failed: {bad}")
    print(f"Created and validated: {DEST}")
    print(f"Included files: {len(files)}")
    print("Excluded: .env, database files, virtual environments, caches, and local build output")


if __name__ == "__main__":
    main()
