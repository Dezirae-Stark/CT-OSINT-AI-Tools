"""
Evidence archiver — SHA-256 hashing, timestamped filesystem storage, manifest.
"""
import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from sqlmodel import Session, select

from config import settings
from database import engine, Message, EvidenceManifest, write_audit_log

logger = logging.getLogger("ghostexodus.archiver")


def _hash_content(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _archive_path(message: Message) -> Path:
    date_str = message.timestamp_utc.strftime("%Y-%m-%d")
    base = Path(settings.EVIDENCE_DIR) / date_str
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{message.channel_id}_{message.telegram_message_id}.json"


async def archive_message(message: Message, raw_payload: str) -> Optional[int]:
    """
    Write raw message JSON to evidence directory and record in manifest.
    Returns manifest record ID.
    """
    file_path = _archive_path(message)
    sha256 = _hash_content(raw_payload)

    try:
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(raw_payload)
    except Exception as e:
        logger.error(f"Failed to write evidence file {file_path}: {e}")
        return None

    with Session(engine) as session:
        manifest = EvidenceManifest(
            message_id=message.id,
            file_path=str(file_path),
            sha256_hash=sha256,
            capture_method="AUTOMATED",
        )
        session.add(manifest)
        session.commit()
        session.refresh(manifest)
        return manifest.id


async def archive_media(message_id: int, file_data: bytes, filename: str) -> Optional[int]:
    """Archive a media file and record in manifest."""
    media_dir = Path(settings.EVIDENCE_DIR) / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    file_path = media_dir / filename
    sha256 = _hash_content(file_data)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)
    except Exception as e:
        logger.error(f"Failed to write media file: {e}")
        return None

    with Session(engine) as session:
        manifest = EvidenceManifest(
            message_id=message_id,
            file_path=str(file_path),
            sha256_hash=sha256,
            capture_method="AUTOMATED",
        )
        session.add(manifest)
        session.commit()
        session.refresh(manifest)
        return manifest.id


async def verify_integrity(manifest_id: int, user_id: Optional[int] = None) -> dict:
    """Re-hash the evidence file and compare to stored hash."""
    with Session(engine) as session:
        manifest = session.get(EvidenceManifest, manifest_id)
        if not manifest:
            return {"status": "NOT_FOUND", "manifest_id": manifest_id}

        try:
            async with aiofiles.open(manifest.file_path, "rb") as f:
                data = await f.read()
            computed = hashlib.sha256(data).hexdigest()
        except FileNotFoundError:
            return {"status": "FILE_MISSING", "manifest_id": manifest_id}
        except Exception as e:
            return {"status": f"ERROR: {e}", "manifest_id": manifest_id}

        status = "VERIFIED" if computed == manifest.sha256_hash else "TAMPERED"
        manifest.verification_status = status
        manifest.verified_at = datetime.utcnow()
        session.add(manifest)

        write_audit_log(
            session,
            action="EVIDENCE_VERIFY",
            user_id=user_id,
            target_type="EVIDENCE_MANIFEST",
            target_id=str(manifest_id),
            detail={"status": status, "stored_hash": manifest.sha256_hash, "computed_hash": computed},
        )

        return {
            "status": status,
            "manifest_id": manifest_id,
            "stored_hash": manifest.sha256_hash,
            "computed_hash": computed,
            "file_path": manifest.file_path,
        }


async def verify_integrity_batch(batch_size: int = 50):
    """Verify a batch of unverified evidence records."""
    with Session(engine) as session:
        manifests = session.exec(
            select(EvidenceManifest)
            .where(EvidenceManifest.verification_status == None)
            .limit(batch_size)
        ).all()
        ids = [m.id for m in manifests]

    for mid in ids:
        await verify_integrity(mid)
        await asyncio.sleep(0.01)
