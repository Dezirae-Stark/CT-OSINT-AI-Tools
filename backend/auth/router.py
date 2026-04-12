"""Auth routes: /auth/login, /auth/refresh"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select

from database import get_session, User, write_audit_log, user_count
from auth.models import LoginRequest, TokenResponse, RefreshRequest
from auth.utils import verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, session: Session = Depends(get_session)):
    ip = request.client.host if request.client else "unknown"

    user = session.exec(select(User).where(User.username == payload.username)).first()

    if not user or not verify_password(payload.password, user.password_hash):
        write_audit_log(
            session,
            action="LOGIN_FAILED",
            detail={"username": payload.username, "reason": "Invalid credentials"},
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role, "username": user.username})

    user.last_login = datetime.utcnow()
    session.add(user)
    session.commit()

    write_audit_log(
        session,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        detail={"username": user.username},
        ip_address=ip,
    )

    return TokenResponse(access_token=token, role=user.role, username=user.username)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, session: Session = Depends(get_session)):
    data = decode_access_token(payload.access_token)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = session.get(User, int(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_token = create_access_token({"sub": str(user.id), "role": user.role, "username": user.username})
    return TokenResponse(access_token=new_token, role=user.role, username=user.username)
