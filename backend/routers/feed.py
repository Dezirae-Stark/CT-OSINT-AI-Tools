"""Feed router — live message feed + WebSocket broadcast."""
import asyncio
import json
import logging
from typing import Optional, Set
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlmodel import Session, select, col

from database import get_session, Message, MonitoredChannel
from auth.dependencies import get_current_user
from database import User

router = APIRouter(prefix="/api", tags=["feed"])
logger = logging.getLogger("ghostexodus.feed")

# Global WebSocket connection manager
_connections: Set[WebSocket] = set()


async def broadcast(event: dict):
    """Broadcast a JSON event to all connected WebSocket clients."""
    if not _connections:
        return
    data = json.dumps(event)
    dead = set()
    for ws in list(_connections):
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


@router.get("/feed")
async def get_feed(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    severity: Optional[str] = Query(None),
    channel_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Message).order_by(col(Message.captured_at_utc).desc())

    if severity:
        sev_idx = SEVERITY_ORDER.get(severity.upper(), 0)
        sev_levels = [k for k, v in SEVERITY_ORDER.items() if v >= sev_idx]
        query = query.where(col(Message.severity).in_(sev_levels))

    if channel_id:
        query = query.where(Message.channel_id == channel_id)

    query = query.offset(offset).limit(limit)
    messages = session.exec(query).all()

    # Build channel name map
    channel_ids = list(set(m.channel_id for m in messages))
    channels = {}
    if channel_ids:
        chs = session.exec(
            select(MonitoredChannel).where(col(MonitoredChannel.id).in_(channel_ids))
        ).all()
        channels = {c.id: c.display_name for c in chs}

    return {
        "total": len(messages),
        "offset": offset,
        "messages": [
            {
                "id": m.id,
                "channel_id": m.channel_id,
                "channel_name": channels.get(m.channel_id, str(m.channel_id)),
                "telegram_message_id": m.telegram_message_id,
                "sender_username": m.sender_username,
                "content_text": m.content_text,
                "content_preview": (m.content_text or "")[:300],
                "media_type": m.media_type,
                "forwarded_from": m.forwarded_from,
                "timestamp_utc": m.timestamp_utc.isoformat(),
                "captured_at_utc": m.captured_at_utc.isoformat(),
                "severity": m.severity,
                "flagged_keywords": json.loads(m.flagged_keywords or "[]"),
                "llm_classification": json.loads(m.llm_classification) if m.llm_classification else None,
                "is_archived": m.is_archived,
            }
            for m in messages
        ],
    }


@router.get("/messages/{message_id}")
async def get_message(
    message_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    msg = session.get(Message, message_id)
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Message not found")

    channel = session.get(MonitoredChannel, msg.channel_id)

    # Load linked entities
    from database import MessageEntityLink, Entity
    links = session.exec(
        select(MessageEntityLink).where(MessageEntityLink.message_id == message_id)
    ).all()
    entity_ids = [l.entity_id for l in links]
    entities = []
    if entity_ids:
        entities = session.exec(
            select(Entity).where(col(Entity.id).in_(entity_ids))
        ).all()

    return {
        "id": msg.id,
        "channel_id": msg.channel_id,
        "channel_name": channel.display_name if channel else str(msg.channel_id),
        "telegram_message_id": msg.telegram_message_id,
        "sender_id": msg.sender_id,
        "sender_username": msg.sender_username,
        "content_text": msg.content_text,
        "content_hash": msg.content_hash,
        "media_type": msg.media_type,
        "media_path": msg.media_path,
        "forwarded_from": msg.forwarded_from,
        "reply_to_id": msg.reply_to_id,
        "timestamp_utc": msg.timestamp_utc.isoformat(),
        "captured_at_utc": msg.captured_at_utc.isoformat(),
        "severity": msg.severity,
        "flagged_keywords": json.loads(msg.flagged_keywords or "[]"),
        "llm_classification": json.loads(msg.llm_classification) if msg.llm_classification else None,
        "is_archived": msg.is_archived,
        "views": msg.views,
        "forwards": msg.forwards,
        "entities": [{"id": e.id, "type": e.entity_type, "value": e.value} for e in entities],
    }


from pydantic import BaseModel as PydanticBase

class SeverityOverride(PydanticBase):
    severity: str


@router.patch("/messages/{message_id}/severity")
async def override_severity(
    message_id: int,
    payload: SeverityOverride,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from auth.dependencies import require_analyst
    if current_user.role not in ("ADMIN", "ANALYST"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Analyst role required")

    msg = session.get(Message, message_id)
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Message not found")

    valid = {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    if payload.severity.upper() not in valid:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid severity. Must be one of: {valid}")

    old_severity = msg.severity
    msg.severity = payload.severity.upper()
    session.add(msg)

    write_audit_log = __import__("database", fromlist=["write_audit_log"]).write_audit_log
    write_audit_log(
        session,
        action="SEVERITY_OVERRIDE",
        user_id=current_user.id,
        target_type="MESSAGE",
        target_id=str(message_id),
        detail={"old": old_severity, "new": msg.severity},
    )
    session.commit()
    return {"id": message_id, "severity": msg.severity}


@router.websocket("/feed/live")
async def websocket_feed(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_connections)}")
    try:
        while True:
            # Keep alive — clients can send pings
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(_connections)}")
