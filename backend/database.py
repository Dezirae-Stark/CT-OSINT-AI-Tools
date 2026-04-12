"""
GhostExodus OSINT Platform — Database Setup
SQLite via SQLModel with all table definitions.
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import text
import json
import os

from config import settings


def get_db_url() -> str:
    os.makedirs(os.path.dirname(settings.SQLITE_PATH), exist_ok=True)
    return f"sqlite:///{settings.SQLITE_PATH}"


engine = create_engine(
    get_db_url(),
    echo=False,
    connect_args={"check_same_thread": False}
)


# ─── Models ──────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="VIEWER")  # ADMIN / ANALYST / VIEWER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True)


class MonitoredChannel(SQLModel, table=True):
    __tablename__ = "monitored_channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: str = Field(index=True)
    display_name: str = ""
    username: str = ""
    category: str = "GENERAL"
    added_at: datetime = Field(default_factory=datetime.utcnow)
    added_by: Optional[int] = None  # FK user id
    is_active: bool = Field(default=True)
    last_checked: Optional[datetime] = None
    message_count: int = Field(default=0)


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    telegram_message_id: int = Field(index=True)
    sender_id: Optional[str] = None
    sender_username: Optional[str] = None
    content_text: str = ""
    content_hash: str = ""  # SHA-256 of raw content JSON
    media_type: Optional[str] = None
    media_path: Optional[str] = None
    forwarded_from: Optional[str] = None
    reply_to_id: Optional[int] = None
    timestamp_utc: datetime
    captured_at_utc: datetime = Field(default_factory=datetime.utcnow)
    severity: str = Field(default="NONE")  # NONE/LOW/MEDIUM/HIGH/CRITICAL
    flagged_keywords: str = Field(default="[]")  # JSON array
    llm_classification: Optional[str] = None  # JSON
    is_archived: bool = Field(default=False)
    views: Optional[int] = None
    forwards: Optional[int] = None


class Entity(SQLModel, table=True):
    __tablename__ = "entities"

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str  # USERNAME/DOMAIN/EMAIL/ALIAS/PHONE/CHANNEL
    value: str = Field(index=True)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    source_channels: str = Field(default="[]")  # JSON array
    linked_entities: str = Field(default="[]")  # JSON array of entity IDs
    notes: Optional[str] = None
    occurrence_count: int = Field(default=1)


class MessageEntityLink(SQLModel, table=True):
    __tablename__ = "message_entity_links"

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(index=True)
    entity_id: int = Field(index=True)


class AlertRule(SQLModel, table=True):
    __tablename__ = "alert_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    trigger_type: str  # KEYWORD/ENTITY/FREQUENCY
    trigger_value: str  # keyword string, entity value, or "N:M" for frequency
    action_type: str  # ARCHIVE/NOTIFY/BOTH
    is_active: bool = Field(default=True)
    created_by: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = Field(default=0)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    detail: str = Field(default="{}")  # JSON
    ip_address: Optional[str] = None
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    generated_by: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_type: str = "INTELREPORT"
    content_path: str
    case_reference: str
    status: str = Field(default="PENDING")  # PENDING/GENERATING/COMPLETE/FAILED


class EvidenceManifest(SQLModel, table=True):
    __tablename__ = "evidence_manifest"

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(index=True)
    file_path: str
    sha256_hash: str
    captured_at_utc: datetime = Field(default_factory=datetime.utcnow)
    capture_method: str = "AUTOMATED"  # AUTOMATED/MANUAL
    notes: Optional[str] = None
    exported_in_bundle: bool = Field(default=False)
    verified_at: Optional[datetime] = None
    verification_status: Optional[str] = None  # VERIFIED/TAMPERED


class ChannelFrequencyCache(SQLModel, table=True):
    """Used by frequency-based alert rules."""
    __tablename__ = "channel_frequency_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    window_start: datetime
    message_count: int = Field(default=0)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def create_db_and_tables():
    """Create all tables on startup."""
    os.makedirs(os.path.dirname(settings.SQLITE_PATH), exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def write_audit_log(
    session: Session,
    action: str,
    user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: dict = None,
    ip_address: Optional[str] = None,
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        detail=json.dumps(detail or {}),
        ip_address=ip_address,
    )
    session.add(log)
    session.commit()
    return log


def user_count(session: Session) -> int:
    return len(session.exec(select(User)).all())
