"""
Alert rules engine — evaluates IF/THEN rules against incoming messages.
"""
import logging
import re
from datetime import datetime, timedelta
from sqlmodel import Session, select, col

from database import engine, AlertRule, Message, ChannelFrequencyCache, write_audit_log
from alerts.notifier import notify_alert

logger = logging.getLogger("ghostexodus.rules_engine")


async def evaluate_rules(
    message_id: int,
    channel_id: int,
    content: str,
    keyword_matches: list,
    severity: str,
    rules: list[AlertRule],
) -> list[int]:
    """
    Evaluate all active rules against the new message.
    Returns list of triggered rule IDs.
    """
    triggered = []
    matched_keyword_values = {m.keyword.lower() for m in keyword_matches}

    with Session(engine) as session:
        msg = session.get(Message, message_id)
        channel_name = str(channel_id)

        for rule in rules:
            if not rule.is_active:
                continue

            triggered_flag = False

            if rule.trigger_type == "KEYWORD":
                val = rule.trigger_value
                try:
                    pattern = re.compile(val, re.IGNORECASE)
                    triggered_flag = bool(pattern.search(content))
                except re.error:
                    triggered_flag = val.lower() in content.lower()

            elif rule.trigger_type == "ENTITY":
                val_lower = rule.trigger_value.lower()
                triggered_flag = val_lower in content.lower()

            elif rule.trigger_type == "FREQUENCY":
                # Format: "N:M" — N messages in M minutes
                try:
                    parts = rule.trigger_value.split(":")
                    threshold = int(parts[0])
                    window_minutes = int(parts[1])
                    triggered_flag = await _check_frequency(
                        session, channel_id, threshold, window_minutes
                    )
                except (ValueError, IndexError):
                    logger.warning(f"Invalid FREQUENCY rule value: {rule.trigger_value}")

            if triggered_flag:
                triggered.append(rule.id)

                # Update rule metadata
                db_rule = session.get(AlertRule, rule.id)
                if db_rule:
                    db_rule.last_triggered = datetime.utcnow()
                    db_rule.trigger_count = (db_rule.trigger_count or 0) + 1
                    session.add(db_rule)

                # Archive action
                if rule.action_type in ("ARCHIVE", "BOTH") and msg:
                    msg.is_archived = True
                    session.add(msg)

                write_audit_log(
                    session,
                    action="ALERT_TRIGGERED",
                    target_type="ALERT_RULE",
                    target_id=str(rule.id),
                    detail={
                        "rule_name": rule.name,
                        "message_id": message_id,
                        "channel_id": channel_id,
                        "trigger_type": rule.trigger_type,
                        "severity": severity,
                    },
                )

                # Notify action
                if rule.action_type in ("NOTIFY", "BOTH"):
                    import asyncio
                    asyncio.create_task(notify_alert(
                        rule_name=rule.name,
                        message_id=message_id,
                        channel_name=channel_name,
                        severity=severity,
                        content_preview=content[:300],
                    ))

        session.commit()

    return triggered


async def _check_frequency(
    session: Session,
    channel_id: int,
    threshold: int,
    window_minutes: int,
) -> bool:
    """Check if a channel has exceeded N messages in M minutes."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)

    # Count recent messages in SQLite
    recent_msgs = session.exec(
        select(Message).where(
            Message.channel_id == channel_id,
            Message.captured_at_utc >= window_start,
        )
    ).all()

    return len(recent_msgs) >= threshold


async def test_rule_against_recent(rule: AlertRule, limit: int = 100) -> dict:
    """Test a rule against the last N messages. Returns match count and samples."""
    with Session(engine) as session:
        messages = session.exec(
            select(Message).order_by(col(Message.captured_at_utc).desc()).limit(limit)
        ).all()

    matches = []
    for msg in messages:
        content = msg.content_text or ""
        hit = False

        if rule.trigger_type == "KEYWORD":
            try:
                pattern = re.compile(rule.trigger_value, re.IGNORECASE)
                hit = bool(pattern.search(content))
            except re.error:
                hit = rule.trigger_value.lower() in content.lower()
        elif rule.trigger_type == "ENTITY":
            hit = rule.trigger_value.lower() in content.lower()

        if hit:
            matches.append({
                "message_id": msg.id,
                "content_preview": content[:200],
                "severity": msg.severity,
                "timestamp_utc": msg.timestamp_utc.isoformat(),
            })

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "messages_tested": len(messages),
        "match_count": len(matches),
        "matches": matches[:10],
    }
