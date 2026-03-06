from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if user_in.password is not None:
        if len(user_in.password.encode("utf-8")) > 72:
            raise HTTPException(status_code=400, detail="Password is too long. Please use 72 bytes or fewer.")
        current_user.hashed_password = get_password_hash(user_in.password)
    if user_in.nickname is not None:
        current_user.nickname = user_in.nickname

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
