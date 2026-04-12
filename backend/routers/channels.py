"""Channels router — manage monitored Telegram targets."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select

from database import get_session, MonitoredChannel, write_audit_log
from auth.dependencies import get_current_user, require_analyst, require_admin
from database import User

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelAdd(BaseModel):
    identifier: str  # username or channel URL
    display_name: str = ""
    category: str = "GENERAL"


@router.get("")
async def list_channels(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    channels = session.exec(select(MonitoredChannel).order_by(MonitoredChannel.added_at)).all()
    return [
        {
            "id": c.id,
            "telegram_id": c.telegram_id,
            "display_name": c.display_name,
            "username": c.username,
            "category": c.category,
            "is_active": c.is_active,
            "added_at": c.added_at.isoformat(),
            "last_checked": c.last_checked.isoformat() if c.last_checked else None,
            "message_count": c.message_count,
        }
        for c in channels
    ]


@router.post("")
async def add_channel(
    payload: ChannelAdd,
    background_tasks: BackgroundTasks,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    identifier = payload.identifier.strip().lstrip("@").replace("https://t.me/", "").replace("http://t.me/", "")

    existing = session.exec(
        select(MonitoredChannel).where(
            (MonitoredChannel.username == identifier) |
            (MonitoredChannel.telegram_id == identifier)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Channel already monitored")

    channel = MonitoredChannel(
        telegram_id=identifier,
        username=identifier,
        display_name=payload.display_name or identifier,
        category=payload.category,
        added_by=current_user.id,
    )
    session.add(channel)
    session.commit()
    session.refresh(channel)

    write_audit_log(
        session,
        action="CHANNEL_ADDED",
        user_id=current_user.id,
        target_type="CHANNEL",
        target_id=str(channel.id),
        detail={"identifier": identifier, "display_name": channel.display_name},
        ip_address=request.client.host if request.client else None,
    )

    # Start monitoring in background
    background_tasks.add_task(_start_monitor, channel.id)

    return {"id": channel.id, "display_name": channel.display_name, "status": "MONITORING_STARTED"}


@router.delete("/{channel_id}")
async def remove_channel(
    channel_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    channel = session.get(MonitoredChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from collector.channel_monitor import unsubscribe_channel
    unsubscribe_channel(channel_id)

    channel.is_active = False
    session.add(channel)

    write_audit_log(
        session,
        action="CHANNEL_REMOVED",
        user_id=current_user.id,
        target_type="CHANNEL",
        target_id=str(channel_id),
        detail={"display_name": channel.display_name},
        ip_address=request.client.host if request.client else None,
    )
    session.commit()
    return {"status": "removed"}


@router.post("/{channel_id}/rescrape")
async def rescrape_channel(
    channel_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    channel = session.get(MonitoredChannel, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    background_tasks.add_task(_scrape_history, channel_id)
    return {"status": "scrape_queued", "channel_id": channel_id}


async def _start_monitor(channel_id: int):
    from sqlmodel import Session
    from database import engine, MonitoredChannel
    from collector.channel_monitor import monitor_channel
    with Session(engine) as session:
        ch = session.get(MonitoredChannel, channel_id)
        if ch:
            try:
                await monitor_channel(ch)
            except Exception as e:
                import logging
                logging.getLogger("ghostexodus").error(f"Failed to monitor channel {channel_id}: {e}")


async def _scrape_history(channel_id: int):
    from sqlmodel import Session
    from database import engine, MonitoredChannel
    from collector.channel_monitor import scrape_history
    with Session(engine) as session:
        ch = session.get(MonitoredChannel, channel_id)
        if ch:
            await scrape_history(ch)
