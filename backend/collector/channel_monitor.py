"""
Continuous channel monitoring — subscribes to new messages via Telethon event handlers.
"""
import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Optional

from telethon import events, errors
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    MessageMediaWebPage, PeerChannel, PeerUser
)
from sqlmodel import Session, select

from config import settings
from database import (
    engine, Message, MonitoredChannel, write_audit_log,
    AlertRule, ChannelFrequencyCache
)
from collector.keyword_engine import match_keywords, compute_severity, matches_to_json
from collector.telegram_client import get_client, safe_get_entity
from evidence.archiver import archive_message

logger = logging.getLogger("ghostexodus.monitor")

# Track active event handlers per channel
_active_handlers: dict[str, callable] = {}


async def _process_message(raw_msg, channel_db_id: int, channel_name: str):
    """Process a single Telethon message object — extract, hash, keyword match, store."""
    try:
        content = raw_msg.text or ""
        media_type = None
        media_path = None

        if raw_msg.media:
            if isinstance(raw_msg.media, MessageMediaPhoto):
                media_type = "PHOTO"
            elif isinstance(raw_msg.media, MessageMediaDocument):
                media_type = "DOCUMENT"
            elif isinstance(raw_msg.media, MessageMediaWebPage):
                media_type = "WEBPAGE"
            else:
                media_type = "OTHER"

        # Sender info
        sender_id = None
        sender_username = None
        if raw_msg.sender_id:
            sender_id = str(raw_msg.sender_id)
        if hasattr(raw_msg, "sender") and raw_msg.sender:
            sender_username = getattr(raw_msg.sender, "username", None)

        # Forward info
        forwarded_from = None
        if raw_msg.fwd_from:
            fwd = raw_msg.fwd_from
            if hasattr(fwd, "from_name") and fwd.from_name:
                forwarded_from = fwd.from_name
            elif hasattr(fwd, "channel_id") and fwd.channel_id:
                forwarded_from = str(fwd.channel_id)

        # Raw payload for hashing
        raw_payload = json.dumps({
            "channel_id": channel_db_id,
            "telegram_message_id": raw_msg.id,
            "sender_id": sender_id,
            "sender_username": sender_username,
            "content_text": content,
            "media_type": media_type,
            "forwarded_from": forwarded_from,
            "timestamp_utc": raw_msg.date.isoformat() if raw_msg.date else None,
        }, sort_keys=True)
        content_hash = hashlib.sha256(raw_payload.encode()).hexdigest()

        with Session(engine) as session:
            # Deduplicate
            existing = session.exec(
                select(Message).where(
                    Message.channel_id == channel_db_id,
                    Message.telegram_message_id == raw_msg.id,
                )
            ).first()
            if existing:
                return

            # Load active alert rules for keyword matching
            rules = session.exec(
                select(AlertRule).where(AlertRule.is_active == True)
            ).all()

            matches = match_keywords(content, rules)
            severity = compute_severity(matches)

            msg = Message(
                channel_id=channel_db_id,
                telegram_message_id=raw_msg.id,
                sender_id=sender_id,
                sender_username=sender_username,
                content_text=content,
                content_hash=content_hash,
                media_type=media_type,
                media_path=media_path,
                forwarded_from=forwarded_from,
                reply_to_id=raw_msg.reply_to_msg_id if hasattr(raw_msg, "reply_to_msg_id") else None,
                timestamp_utc=raw_msg.date or datetime.utcnow(),
                severity=severity,
                flagged_keywords=matches_to_json(matches),
                views=getattr(raw_msg, "views", None),
                forwards=getattr(raw_msg, "forwards", None),
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)

            # Archive to filesystem
            await archive_message(msg, raw_payload)

            # Embed asynchronously (fire and forget)
            asyncio.create_task(_embed_message_async(msg.id, content))

            # LLM classification for medium+ severity (async, non-blocking)
            if severity in ("MEDIUM", "HIGH", "CRITICAL"):
                asyncio.create_task(_classify_async(msg.id, content, channel_name))

            # Evaluate alert rules
            asyncio.create_task(_evaluate_alerts(msg.id, channel_db_id, content, matches, severity, rules))

            # Update channel last_checked + message_count
            ch = session.get(MonitoredChannel, channel_db_id)
            if ch:
                ch.last_checked = datetime.utcnow()
                ch.message_count = (ch.message_count or 0) + 1
                session.add(ch)
                session.commit()

            logger.info(f"Message {msg.id} ingested | channel={channel_name} | severity={severity}")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)


async def _embed_message_async(message_id: int, content: str):
    """Embed and upsert to ChromaDB."""
    try:
        from intelligence.vectorstore import upsert_message_by_id
        await upsert_message_by_id(message_id)
    except Exception as e:
        logger.error(f"Embedding failed for msg {message_id}: {e}")


async def _classify_async(message_id: int, content: str, channel_name: str):
    """Run LLM classification and update message severity."""
    try:
        from intelligence.classifier import classify_message_text
        from database import Message as MsgModel
        result = await classify_message_text(content, f"Channel: {channel_name}")

        with Session(engine) as session:
            msg = session.get(MsgModel, message_id)
            if msg:
                msg.llm_classification = json.dumps(result)
                # LLM can override severity to CRITICAL
                if result.get("severity") == "CRITICAL":
                    msg.severity = "CRITICAL"
                elif result.get("requires_immediate_action"):
                    _sev_list = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
                    _cur = _sev_list.index(msg.severity) if msg.severity in _sev_list else 0
                    _sev_idx = max(_cur, _sev_list.index("HIGH"))
                    msg.severity = _sev_list[_sev_idx]
                session.add(msg)
                session.commit()
    except Exception as e:
        logger.error(f"LLM classification failed for msg {message_id}: {e}")


async def _evaluate_alerts(
    message_id: int, channel_id: int, content: str,
    keyword_matches: list, severity: str, rules: list
):
    """Evaluate active alert rules against the new message."""
    try:
        from alerts.rules_engine import evaluate_rules
        await evaluate_rules(message_id, channel_id, content, keyword_matches, severity, rules)
    except Exception as e:
        logger.error(f"Alert evaluation failed: {e}")


async def monitor_channel(channel_db: MonitoredChannel):
    """Subscribe to live messages from a Telegram channel."""
    client = await get_client()
    entity = await safe_get_entity(client, channel_db.username or str(channel_db.telegram_id))
    if entity is None:
        logger.error(f"Cannot resolve channel {channel_db.display_name}")
        return

    channel_id = channel_db.id
    channel_name = channel_db.display_name

    @client.on(events.NewMessage(chats=entity))
    async def handler(event):
        await _process_message(event.message, channel_id, channel_name)

    _active_handlers[str(channel_id)] = handler
    logger.info(f"Monitoring channel: {channel_name} ({channel_db.telegram_id})")


def unsubscribe_channel(channel_db_id: int):
    handler = _active_handlers.pop(str(channel_db_id), None)
    if handler:
        logger.info(f"Unsubscribed handler for channel {channel_db_id}")


async def scrape_history(channel_db: MonitoredChannel, limit: int = 500):
    """Backfill historical messages from a channel."""
    client = await get_client()
    entity = await safe_get_entity(client, channel_db.username or str(channel_db.telegram_id))
    if entity is None:
        return 0

    count = 0
    logger.info(f"Backfilling up to {limit} messages from {channel_db.display_name}...")

    async for message in client.iter_messages(entity, limit=limit):
        if message.text or message.media:
            await _process_message(message, channel_db.id, channel_db.display_name)
            count += 1
            await asyncio.sleep(0.05)  # be gentle

    logger.info(f"Backfilled {count} messages from {channel_db.display_name}")
    return count


async def start_all_monitors():
    """Called on startup: subscribe to all active channels in DB."""
    with Session(engine) as session:
        channels = session.exec(
            select(MonitoredChannel).where(MonitoredChannel.is_active == True)
        ).all()

    for ch in channels:
        try:
            await monitor_channel(ch)
        except Exception as e:
            logger.error(f"Failed to start monitor for {ch.display_name}: {e}")

    logger.info(f"Started monitoring {len(channels)} channels")
