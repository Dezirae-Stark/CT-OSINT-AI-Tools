"""Auth Pydantic schemas (request/response models)."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class RefreshRequest(BaseModel):
    access_token: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "VIEWER"


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool


class PasswordReset(BaseModel):
    new_password: str


class RoleUpdate(BaseModel):
    role: str
