"""Reports router — generate and retrieve intelligence reports."""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select, col

from database import get_session, Report, write_audit_log
from auth.dependencies import get_current_user, require_analyst
from database import User

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportRequest(BaseModel):
    title: str
    case_reference: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    channel_ids: Optional[list[int]] = None
    severity_threshold: str = "LOW"


@router.get("")
async def list_reports(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    reports = session.exec(
        select(Report).order_by(col(Report.generated_at).desc()).limit(50)
    ).all()

    # Build username map
    from database import User as UserModel
    user_ids = list(set(r.generated_by for r in reports))
    users = {}
    if user_ids:
        us = session.exec(select(UserModel).where(col(UserModel.id).in_(user_ids))).all()
        users = {u.id: u.username for u in us}

    return [
        {
            "id": r.id,
            "title": r.title,
            "case_reference": r.case_reference,
            "generated_by": users.get(r.generated_by, str(r.generated_by)),
            "generated_at": r.generated_at.isoformat(),
            "report_type": r.report_type,
            "status": r.status,
            "has_file": os.path.exists(r.content_path) if r.content_path else False,
        }
        for r in reports
    ]


@router.post("/generate")
async def generate_report(
    payload: ReportRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    start_date = datetime.fromisoformat(payload.start_date) if payload.start_date else None
    end_date = datetime.fromisoformat(payload.end_date) if payload.end_date else None

    background_tasks.add_task(
        _run_report,
        payload.title,
        payload.case_reference,
        current_user.id,
        current_user.username,
        start_date,
        end_date,
        payload.channel_ids,
        payload.severity_threshold,
    )

    return {"status": "queued", "message": "Report generation started. Check /api/reports for status."}


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "COMPLETE":
        raise HTTPException(status_code=409, detail=f"Report status: {report.status}")
    if not report.content_path or not os.path.exists(report.content_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    write_audit_log(
        session,
        action="REPORT_DOWNLOADED",
        user_id=current_user.id,
        target_type="REPORT",
        target_id=str(report_id),
        detail={"case_reference": report.case_reference},
    )

    ext = os.path.splitext(report.content_path)[1]
    media_type = "application/pdf" if ext == ".pdf" else "text/html"
    filename = f"{report.case_reference.replace(' ', '_')}{ext}"

    return FileResponse(
        path=report.content_path,
        media_type=media_type,
        filename=filename,
    )


async def _run_report(title, case_reference, user_id, username, start_date, end_date, channel_ids, severity_threshold):
    from reports.generator import generate_report as _generate
    await _generate(title, case_reference, user_id, username, start_date, end_date, channel_ids, severity_threshold)
