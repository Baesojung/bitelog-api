import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserResponse, UserCreate
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/email-exists")
def check_email_exists(email: str, db: Session = Depends(get_db)):
    # Keep this endpoint resilient: never raise 500 from this lightweight probe.
    try:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            return {"exists": False}
        user = db.query(User).filter(User.email == normalized_email).first()
        return {"exists": user is not None}
    except SQLAlchemyError as e:
        logger.exception("email-exists query failed: %s", e)
        return {"exists": False}
    except Exception as e:
        logger.exception("email-exists unexpected error: %s", e)
        return {"exists": False}

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        normalized_email = str(user_in.email).strip().lower()
        user = db.query(User).filter(User.email == normalized_email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this username already exists in the system.",
            )
        try:
            hashed_password = get_password_hash(user_in.password)
        except Exception as e:
            logger.exception("register password hash error: %s", e)
            detail = "Registration failed while processing password."
            if settings.debug:
                detail = f"{detail} ({type(e).__name__}: {e})"
            raise HTTPException(status_code=500, detail=detail)

        user = User(
            email=normalized_email,
            hashed_password=hashed_password,
            nickname=user_in.nickname,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("register db error: %s", e)
        detail = "Registration failed due to a database error."
        if settings.debug:
            detail = f"{detail} ({type(e).__name__}: {e})"
        raise HTTPException(
            status_code=500,
            detail=detail,
        )
    except Exception as e:
        logger.exception("register unexpected error: %s", e)
        detail = "Registration failed due to an unexpected server error."
        if settings.debug:
            detail = f"{detail} ({type(e).__name__}: {e})"
        raise HTTPException(
            status_code=500,
            detail=detail,
        )

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.email == form_data.username).first()
    try:
        password_ok = bool(user) and verify_password(form_data.password, user.hashed_password)
    except ValueError:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not password_ok:
        raise HTTPException(
            status_code=400, detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=60 * 24 * 7) # 1 week expiration
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
