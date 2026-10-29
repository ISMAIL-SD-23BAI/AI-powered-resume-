from dotenv import load_dotenv
load_dotenv()  # Keep explicitly supplied process/container variables authoritative.

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import validate_startup_config
from database import engine, Base
from limiter import limiter
from routers import auth, resumes, tailor, cover_letter, history, export, match, improve, skill_gap, tracker, interview
from auth import get_current_user
import models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
_logger = logging.getLogger(__name__)


# ── App factory ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_config()
    Base.metadata.create_all(bind=engine)
    _logger.info("Database tables verified")
    yield


app = FastAPI(title="Resume Tailor", version="1.0.0", lifespan=lifespan)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── CORS ───────────────────────────────────────────────────────────────────────
# The "null" origin (file:// pages) is only allowed in DEBUG mode.
# Production deployments must not set DEBUG=true.

_DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:5500"]
if _DEBUG:
    _CORS_ORIGINS.append("null")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Validation error formatting ────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        # Skip generic location tokens like "body", "query", "path"
        parts = [str(loc) for loc in error["loc"] if loc not in ("body", "query", "path")]
        field = ".".join(parts) if parts else None
        msg = error["msg"]
        messages.append(f"{field}: {msg}" if field else msg)
    detail = "; ".join(messages) if messages else "Validation error"
    _logger.debug("Validation error on %s %s: %s", request.method, request.url.path, detail)
    return JSONResponse(status_code=422, content={"detail": detail})


# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(tailor.router)
app.include_router(cover_letter.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(match.router)
app.include_router(improve.router)
app.include_router(skill_gap.router)
app.include_router(tracker.router)
app.include_router(interview.router)


# ── Utility endpoints ──────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/me", tags=["meta"])
def me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at,
    }
