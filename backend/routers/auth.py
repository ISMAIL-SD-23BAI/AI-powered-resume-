from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import get_db
from schemas import UserCreate, UserOut, Token, LoginRequest
import models
import auth as auth_helpers

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_user(user_in: UserCreate, db: Session) -> models.User:
    if db.query(models.User).filter(models.User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=user_in.email,
        hashed_password=auth_helpers.hash_password(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _authenticate(email: str, password: str, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not auth_helpers.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )
    return user


# ── JSON endpoints (used by fetch() in the browser) ──────────────────────────

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new account. Accepts JSON."""
    return _create_user(user_in, db)


@router.post("/login", response_model=Token)
def login_json(body: LoginRequest, db: Session = Depends(get_db)):
    """Login with JSON body. Returns JWT access token."""
    user = _authenticate(body.email, body.password, db)
    token = auth_helpers.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# ── OAuth2 form endpoint (used by /docs Authorize button) ────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Alias for /signup — kept for compatibility."""
    return _create_user(user_in, db)


@router.post("/token", response_model=Token)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login — powers the /docs Authorize button."""
    user = _authenticate(form.username, form.password, db)
    token = auth_helpers.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
