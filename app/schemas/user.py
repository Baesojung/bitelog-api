from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    nickname: Optional[str] = None
    daily_goal_kcal: int = 2000

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None
    daily_goal_kcal: Optional[int] = None

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
