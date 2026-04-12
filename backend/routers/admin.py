"""Admin router — user management, audit log, system status."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, col

from database import get_session, User, AuditLog, write_audit_log
from auth.models import UserCreate, UserOut, PasswordReset, RoleUpdate
from auth.utils import hash_password
from auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    return session.exec(select(User).order_by(col(User.created_at).asc())).all()


@router.post("/users", response_model=UserOut)
async def create_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    existing = session.exec(select(User).where(User.username == payload.username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    valid_roles = {"ADMIN", "ANALYST", "VIEWER"}
    if payload.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of {valid_roles}")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role.upper(),
    )
    session.add(user)
    write_audit_log(
        session,
        action="USER_CREATED",
        user_id=current_user.id,
        target_type="USER",
        detail={"username": payload.username, "role": payload.role.upper()},
    )
    session.commit()
    session.refresh(user)
    return user


@router.patch("/users/{user_id}/role")
async def update_role(
    user_id: int,
    payload: RoleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    valid_roles = {"ADMIN", "ANALYST", "VIEWER"}
    if payload.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of {valid_roles}")

    old_role = user.role
    user.role = payload.role.upper()
    session.add(user)
    write_audit_log(
        session,
        action="ROLE_UPDATED",
        user_id=current_user.id,
        target_type="USER",
        target_id=str(user_id),
        detail={"old_role": old_role, "new_role": user.role},
    )
    session.commit()
    return {"user_id": user_id, "role": user.role}


@router.patch("/users/{user_id}/password")
async def reset_password(
    user_id: int,
    payload: PasswordReset,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(payload.new_password)
    session.add(user)
    write_audit_log(
        session,
        action="PASSWORD_RESET",
        user_id=current_user.id,
        target_type="USER",
        target_id=str(user_id),
        detail={"target_username": user.username},
    )
    session.commit()
    return {"status": "password updated"}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    session.add(user)
    write_audit_log(
        session,
        action="USER_DEACTIVATED",
        user_id=current_user.id,
        target_type="USER",
        target_id=str(user_id),
        detail={"username": user.username},
    )
    session.commit()
    return {"status": "deactivated"}


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    from evidence.chain_of_custody import get_audit_trail
    return get_audit_trail(limit=limit, user_id=user_id, action=action)


@router.get("/system/status")
async def system_status(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from intelligence.llm_client import ping_ollama
    from intelligence.vectorstore import get_collection_stats
    import os

    ollama_ok = await ping_ollama()

    chroma_stats = get_collection_stats()

    sqlite_size = 0
    from config import settings
    if os.path.exists(settings.SQLITE_PATH):
        sqlite_size = os.path.getsize(settings.SQLITE_PATH)

    from database import Message, MonitoredChannel, User as UserModel
    msg_count = len(session.exec(select(Message)).all())
    channel_count = len(session.exec(
        select(MonitoredChannel).where(MonitoredChannel.is_active == True)
    ).all())
    user_count = len(session.exec(select(UserModel)).all())

    from collector.channel_monitor import _active_handlers
    active_monitors = len(_active_handlers)

    return {
        "ollama": {"status": "OK" if ollama_ok else "UNREACHABLE"},
        "chromadb": chroma_stats,
        "sqlite": {
            "path": settings.SQLITE_PATH,
            "size_bytes": sqlite_size,
            "message_count": msg_count,
        },
        "channels": {
            "total_active": channel_count,
            "currently_monitoring": active_monitors,
        },
        "users": user_count,
    }
