"""
Alert notifications — SMTP email + ntfy.sh push.
"""
import logging
from datetime import datetime
from typing import Optional
import aiosmtplib
from email.message import EmailMessage
import httpx

from config import settings

logger = logging.getLogger("ghostexodus.notifier")


async def send_email_alert(subject: str, body: str) -> bool:
    if not settings.SMTP_HOST or not settings.ALERT_EMAIL_TO:
        logger.debug("SMTP not configured — skipping email alert")
        return False
    try:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_USER or "ghostexodus@localhost"
        msg["To"] = settings.ALERT_EMAIL_TO
        msg["Subject"] = f"[GhostExodus Alert] {subject}"
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASS or None,
            use_tls=settings.SMTP_PORT == 465,
            start_tls=settings.SMTP_PORT == 587,
        )
        logger.info(f"Email alert sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email alert failed: {e}")
        return False


async def send_push_alert(title: str, message: str, priority: str = "high") -> bool:
    if not settings.NTFY_TOPIC:
        logger.debug("ntfy.sh not configured — skipping push alert")
        return False
    try:
        url = f"{settings.NTFY_SERVER}/{settings.NTFY_TOPIC}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": "warning,intelligence",
                },
                content=message.encode(),
            )
            resp.raise_for_status()
        logger.info(f"Push alert sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Push alert failed: {e}")
        return False


async def notify_alert(rule_name: str, message_id: int, channel_name: str, severity: str, content_preview: str):
    """Send all configured notifications for an alert trigger."""
    subject = f"{severity} — {rule_name} triggered in {channel_name}"
    body = (
        f"Alert: {rule_name}\n"
        f"Severity: {severity}\n"
        f"Channel: {channel_name}\n"
        f"Message ID: {message_id}\n"
        f"Time: {datetime.utcnow().isoformat()} UTC\n\n"
        f"Content preview:\n{content_preview[:300]}\n\n"
        f"Review in GhostExodus at http://localhost:8000"
    )
    await send_email_alert(subject, body)
    await send_push_alert(subject, body[:500])
