"""Alert rules router — CRUD for alert rules."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, col

from database import get_session, AlertRule, write_audit_log
from auth.dependencies import get_current_user, require_analyst, require_admin
from database import User

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class RuleCreate(BaseModel):
    name: str
    trigger_type: str  # KEYWORD / ENTITY / FREQUENCY
    trigger_value: str
    action_type: str   # ARCHIVE / NOTIFY / BOTH


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    action_type: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/rules")
async def list_rules(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rules = session.exec(
        select(AlertRule).order_by(col(AlertRule.last_triggered).desc())
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "trigger_type": r.trigger_type,
            "trigger_value": r.trigger_value,
            "action_type": r.action_type,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
            "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
            "trigger_count": r.trigger_count,
        }
        for r in rules
    ]


@router.post("/rules")
async def create_rule(
    payload: RuleCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    valid_types = {"KEYWORD", "ENTITY", "FREQUENCY"}
    valid_actions = {"ARCHIVE", "NOTIFY", "BOTH"}
    if payload.trigger_type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"trigger_type must be one of {valid_types}")
    if payload.action_type.upper() not in valid_actions:
        raise HTTPException(status_code=400, detail=f"action_type must be one of {valid_actions}")

    rule = AlertRule(
        name=payload.name,
        trigger_type=payload.trigger_type.upper(),
        trigger_value=payload.trigger_value,
        action_type=payload.action_type.upper(),
        created_by=current_user.id,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)

    write_audit_log(
        session,
        action="ALERT_RULE_CREATED",
        user_id=current_user.id,
        target_type="ALERT_RULE",
        target_id=str(rule.id),
        detail={"name": rule.name, "trigger_type": rule.trigger_type},
    )

    return {"id": rule.id, "name": rule.name, "status": "created"}


@router.patch("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    rule = session.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if payload.name is not None:
        rule.name = payload.name
    if payload.trigger_type is not None:
        rule.trigger_type = payload.trigger_type.upper()
    if payload.trigger_value is not None:
        rule.trigger_value = payload.trigger_value
    if payload.action_type is not None:
        rule.action_type = payload.action_type.upper()
    if payload.is_active is not None:
        rule.is_active = payload.is_active

    session.add(rule)
    write_audit_log(
        session,
        action="ALERT_RULE_UPDATED",
        user_id=current_user.id,
        target_type="ALERT_RULE",
        target_id=str(rule_id),
        detail=payload.model_dump(exclude_none=True),
    )
    session.commit()
    return {"id": rule_id, "status": "updated"}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    rule = session.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    session.delete(rule)
    write_audit_log(
        session,
        action="ALERT_RULE_DELETED",
        user_id=current_user.id,
        target_type="ALERT_RULE",
        target_id=str(rule_id),
        detail={"name": rule.name},
    )
    session.commit()
    return {"status": "deleted"}


@router.post("/rules/{rule_id}/test")
async def test_rule(
    rule_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    rule = session.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    from alerts.rules_engine import test_rule_against_recent
    result = await test_rule_against_recent(rule)
    return result
