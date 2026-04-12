"""Evidence router — archive management and case bundle export."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select, col
import io

from database import get_session, EvidenceManifest, Message, MonitoredChannel, write_audit_log
from auth.dependencies import get_current_user, require_analyst
from database import User

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("")
async def list_evidence(
    channel_id: Optional[int] = None,
    severity: Optional[str] = None,
    exported: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(EvidenceManifest, Message)
        .join(Message, EvidenceManifest.message_id == Message.id)
        .order_by(col(EvidenceManifest.captured_at_utc).desc())
    )

    if channel_id:
        query = query.where(Message.channel_id == channel_id)
    if severity:
        query = query.where(Message.severity == severity.upper())
    if exported is not None:
        query = query.where(EvidenceManifest.exported_in_bundle == exported)

    query = query.offset(offset).limit(limit)
    rows = session.exec(query).all()

    channel_ids = list(set(msg.channel_id for _, msg in rows))
    channels = {}
    if channel_ids:
        chs = session.exec(
            select(MonitoredChannel).where(col(MonitoredChannel.id).in_(channel_ids))
        ).all()
        channels = {c.id: c.display_name for c in chs}

    return {
        "count": len(rows),
        "items": [
            {
                "manifest_id": m.id,
                "message_id": m.message_id,
                "channel_name": channels.get(msg.channel_id, str(msg.channel_id)),
                "captured_at_utc": m.captured_at_utc.isoformat(),
                "sha256_hash": m.sha256_hash,
                "sha256_short": m.sha256_hash[:12],
                "capture_method": m.capture_method,
                "exported_in_bundle": m.exported_in_bundle,
                "verification_status": m.verification_status,
                "verified_at": m.verified_at.isoformat() if m.verified_at else None,
                "severity": msg.severity,
            }
            for m, msg in rows
        ],
    }


@router.get("/{manifest_id}/verify")
async def verify_evidence(
    manifest_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from evidence.archiver import verify_integrity
    result = await verify_integrity(manifest_id, user_id=current_user.id)
    return result


class ExportBundleRequest(BaseModel):
    case_reference: str
    message_ids: list[int]


@router.post("/export-bundle")
async def export_bundle(
    payload: ExportBundleRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    if not payload.message_ids:
        raise HTTPException(status_code=400, detail="No message IDs provided")
    if len(payload.message_ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 messages per bundle")

    write_audit_log(
        session,
        action="EVIDENCE_BUNDLE_REQUESTED",
        user_id=current_user.id,
        target_type="CASE_BUNDLE",
        target_id=payload.case_reference,
        detail={"message_count": len(payload.message_ids)},
    )

    from evidence.export import generate_case_bundle
    zip_bytes = await generate_case_bundle(
        case_reference=payload.case_reference,
        message_ids=payload.message_ids,
        user_id=current_user.id,
    )

    filename = f"ghostexodus_{payload.case_reference.replace(' ', '_')}.zip"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
