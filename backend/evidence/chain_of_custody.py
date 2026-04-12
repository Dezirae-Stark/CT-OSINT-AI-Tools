"""
Chain of custody audit trail queries.
"""
import json
from datetime import datetime
from sqlmodel import Session, select, col
from database import engine, AuditLog, EvidenceManifest, User


def get_audit_trail(
    limit: int = 100,
    user_id: int = None,
    action: str = None,
    target_type: str = None,
) -> list[dict]:
    """Query audit log with optional filters."""
    with Session(engine) as session:
        query = select(AuditLog).order_by(col(AuditLog.timestamp_utc).desc())
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if target_type:
            query = query.where(AuditLog.target_type == target_type)
        query = query.limit(limit)

        logs = session.exec(query).all()
        result = []
        for log in logs:
            # Resolve username
            username = None
            if log.user_id:
                user = session.get(User, log.user_id)
                username = user.username if user else None

            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "username": username,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "detail": json.loads(log.detail or "{}"),
                "ip_address": log.ip_address,
                "timestamp_utc": log.timestamp_utc.isoformat(),
            })
        return result


def format_custody_text(message_ids: list[int], case_reference: str) -> str:
    """Generate human-readable chain of custody text for an export bundle."""
    lines = [
        "CHAIN OF CUSTODY RECORD",
        "=" * 60,
        f"Case Reference: {case_reference}",
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"Message IDs: {', '.join(str(i) for i in message_ids)}",
        "",
        "ACCESS AND MODIFICATION LOG",
        "-" * 60,
    ]

    with Session(engine) as session:
        # Get evidence manifest entries for these messages
        manifests = session.exec(
            select(EvidenceManifest).where(
                col(EvidenceManifest.message_id).in_(message_ids)
            )
        ).all()

        manifest_ids = [m.id for m in manifests]

        for manifest in manifests:
            lines.append(
                f"[CAPTURE] Message {manifest.message_id} | "
                f"File: {manifest.file_path} | "
                f"SHA-256: {manifest.sha256_hash} | "
                f"At: {manifest.captured_at_utc.isoformat()} UTC | "
                f"Method: {manifest.capture_method}"
            )

        # Get audit log entries related to these evidence items
        if manifest_ids:
            audit_entries = session.exec(
                select(AuditLog)
                .where(AuditLog.target_type == "EVIDENCE_MANIFEST")
                .order_by(col(AuditLog.timestamp_utc).asc())
            ).all()

            for entry in audit_entries:
                if entry.target_id and int(entry.target_id) in manifest_ids:
                    user = session.get(User, entry.user_id) if entry.user_id else None
                    username = user.username if user else "SYSTEM"
                    lines.append(
                        f"[{entry.action}] {username} | "
                        f"Target: {entry.target_type} {entry.target_id} | "
                        f"At: {entry.timestamp_utc.isoformat()} UTC | "
                        f"IP: {entry.ip_address or 'N/A'}"
                    )

    lines += [
        "",
        "=" * 60,
        "This chain of custody was generated automatically by GhostExodus OSINT Platform.",
        "All evidence hashes can be independently verified using the included verification_script.py.",
        "For queries, contact the generating analyst.",
    ]
    return "\n".join(lines)
