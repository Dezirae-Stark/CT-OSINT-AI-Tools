"""Timeline router — temporal activity analysis."""
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, col

from database import get_session, Message, MonitoredChannel
from auth.dependencies import get_current_user
from database import User

router = APIRouter(prefix="/api/timeline", tags=["timeline"])

SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


@router.get("")
async def timeline(
    channels: Optional[str] = Query(None, description="Comma-separated channel IDs"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    granularity: str = Query("day", description="hour or day"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Message)

    channel_ids = []
    if channels:
        try:
            channel_ids = [int(c.strip()) for c in channels.split(",") if c.strip()]
        except ValueError:
            pass

    if channel_ids:
        query = query.where(col(Message.channel_id).in_(channel_ids))

    start_dt = datetime.fromisoformat(start) if start else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.fromisoformat(end) if end else datetime.utcnow()

    query = query.where(
        Message.timestamp_utc >= start_dt,
        Message.timestamp_utc <= end_dt,
    ).order_by(col(Message.timestamp_utc).asc())

    messages = session.exec(query).all()

    # Group by channel + time bucket
    channel_names = {}
    all_channel_ids = list(set(m.channel_id for m in messages))
    if all_channel_ids:
        chs = session.exec(
            select(MonitoredChannel).where(col(MonitoredChannel.id).in_(all_channel_ids))
        ).all()
        channel_names = {c.id: c.display_name for c in chs}

    def bucket_key(dt: datetime) -> str:
        if granularity == "hour":
            return dt.strftime("%Y-%m-%dT%H:00")
        return dt.strftime("%Y-%m-%d")

    # Series per channel
    series: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    severity_over_time: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for m in messages:
        key = bucket_key(m.timestamp_utc)
        series[m.channel_id][key] += 1
        severity_over_time[key][m.severity] = severity_over_time[key].get(m.severity, 0) + 1

    # Format for Recharts
    all_buckets = sorted(set(
        bucket_key(m.timestamp_utc) for m in messages
    ))

    chart_series = []
    for ch_id, counts in series.items():
        chart_series.append({
            "channel_id": ch_id,
            "channel_name": channel_names.get(ch_id, str(ch_id)),
            "data": [{"time": b, "count": counts.get(b, 0)} for b in all_buckets],
        })

    severity_series = [
        {
            "time": b,
            **{sev: severity_over_time[b].get(sev, 0) for sev in SEVERITY_ORDER},
        }
        for b in all_buckets
    ]

    return {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "granularity": granularity,
        "channel_series": chart_series,
        "severity_series": severity_series,
        "total_messages": len(messages),
    }


@router.get("/hourly")
async def hourly_distribution(
    channel_id: Optional[int] = Query(None),
    days: int = Query(30, le=90),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """UTC hour-of-day distribution for timezone inference."""
    since = datetime.utcnow() - timedelta(days=days)
    query = select(Message).where(Message.timestamp_utc >= since)
    if channel_id:
        query = query.where(Message.channel_id == channel_id)

    messages = session.exec(query).all()
    hour_counts = defaultdict(int)
    for m in messages:
        hour_counts[m.timestamp_utc.hour] += 1

    distribution = [{"hour_utc": h, "count": hour_counts.get(h, 0)} for h in range(24)]
    peak_hour = max(hour_counts, key=hour_counts.get, default=0) if hour_counts else 0

    # Infer likely timezone (naive heuristic: peak hour shifted from UTC)
    if hour_counts:
        peak_activity_utc = peak_hour
        # Assume human active hours 9–22 local. Infer offset.
        likely_tz_offset = (14 - peak_activity_utc) % 24
        if likely_tz_offset > 12:
            likely_tz_offset -= 24
    else:
        likely_tz_offset = 0

    return {
        "distribution": distribution,
        "peak_hour_utc": peak_hour,
        "likely_tz_offset_hours": likely_tz_offset,
        "total_messages": len(messages),
    }
