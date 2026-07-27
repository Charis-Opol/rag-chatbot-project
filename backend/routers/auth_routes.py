"""
Authentication routes (proposal §1.6.2, §3.3.1 req. #3).
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_role,
)
from backend.utils_logging import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        log_action(db, None, f"Failed login attempt for '{form_data.username}'", tag="deny")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.user_id), "role": user.role_name})
    user.last_login = datetime.datetime.utcnow()
    db.commit()
    log_action(db, user.user_id, f"Signed in as {user.role_name}", tag="ok")
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/register", response_model=schemas.UserOut)
def register(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_role("admin")),
):
    """Only an existing IT Officer (admin) can create new accounts."""
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    role = db.query(models.Role).filter(models.Role.role_name == payload.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Unknown role '{payload.role}'")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_id=role.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, current_admin.user_id, f"Created account for {user.full_name} ({user.role_name})", tag="ok")
    return schemas.UserOut.model_validate(user)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserOut.model_validate(current_user)
