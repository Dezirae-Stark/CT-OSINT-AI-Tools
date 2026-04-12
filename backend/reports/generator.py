"""
INTELREPORT PDF generation using WeasyPrint + Jinja2.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, select, col

from config import settings
from database import (
    engine, Message, MonitoredChannel, Entity,
    EvidenceManifest, Report, write_audit_log
)
from intelligence.llm_client import generate_summary, complete

logger = logging.getLogger("ghostexodus.reports")

_template_dir = Path(__file__).parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_template_dir)),
        autoescape=True,
    )


async def _llm_assessment(prompt: str) -> str:
    try:
        return await complete(
            prompt,
            system="You are a senior intelligence analyst. Be concise and formal.",
            max_tokens=200,
        )
    except Exception:
        return "Assessment unavailable — manual review required."


async def generate_report(
    title: str,
    case_reference: str,
    generated_by_user_id: int,
    generated_by_username: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    channel_ids: Optional[list[int]] = None,
    severity_threshold: str = "LOW",
) -> int:
    """
    Generate an INTELREPORT PDF. Returns Report record ID.
    """
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)

    severity_order = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_sev_idx = severity_order.index(severity_threshold)

    with Session(engine) as session:
        # Create placeholder report record
        sequence = session.exec(select(Report)).all()
        seq_num = str(len(sequence) + 1).zfill(4)
        report_ref = f"GX-{datetime.utcnow().strftime('%Y%m%d')}-{seq_num}"

        filename = f"{report_ref.replace('/', '_')}.pdf"
        content_path = str(Path(settings.REPORTS_DIR) / filename)

        report = Report(
            title=title,
            generated_by=generated_by_user_id,
            report_type="INTELREPORT",
            content_path=content_path,
            case_reference=case_reference,
            status="GENERATING",
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        report_id = report.id

        # Query messages
        msg_query = select(Message)
        if start_date:
            msg_query = msg_query.where(Message.timestamp_utc >= start_date)
        if end_date:
            msg_query = msg_query.where(Message.timestamp_utc <= end_date)
        if channel_ids:
            msg_query = msg_query.where(col(Message.channel_id).in_(channel_ids))
        msg_query = msg_query.order_by(col(Message.timestamp_utc).desc())

        all_messages = session.exec(msg_query).all()
        filtered = [
            m for m in all_messages
            if severity_order.index(m.severity) >= min_sev_idx
        ]

        # Top 10 key messages
        key_messages_raw = sorted(
            filtered,
            key=lambda m: severity_order.index(m.severity),
            reverse=True,
        )[:10]

        # Channel metadata
        all_channel_ids = list(set(m.channel_id for m in filtered))
        channels = {
            c.id: c for c in session.exec(
                select(MonitoredChannel).where(col(MonitoredChannel.id).in_(all_channel_ids))
            ).all()
        }

        # Entities
        entity_ids_set: set[int] = set()
        for m in filtered[:100]:
            from database import MessageEntityLink
            links = session.exec(
                select(MessageEntityLink).where(MessageEntityLink.message_id == m.id)
            ).all()
            for l in links:
                entity_ids_set.add(l.entity_id)

        actors_raw = []
        if entity_ids_set:
            actors_raw = session.exec(
                select(Entity).where(col(Entity.id).in_(list(entity_ids_set)))
                .order_by(col(Entity.occurrence_count).desc())
                .limit(30)
            ).all()

        # Evidence manifests
        message_ids = [m.id for m in filtered[:200]]
        evidence_list_raw = []
        if message_ids:
            evidence_list_raw = session.exec(
                select(EvidenceManifest).where(
                    col(EvidenceManifest.message_id).in_(message_ids)
                ).limit(200)
            ).all()

        # UK relevance check
        uk_relevant = any(
            m.llm_classification and
            json.loads(m.llm_classification).get("uk_relevance", False)
            for m in filtered[:50]
            if m.llm_classification
        )

    # ─── LLM-generated sections ─────────────────────────────────────────────
    content_samples = [m.content_text[:200] for m in key_messages_raw[:15] if m.content_text]

    executive_summary = await generate_summary(content_samples) if content_samples else "No flagged content in selected period."

    ttp_prompt = f"Based on {len(filtered)} flagged messages, briefly describe observed TTPs (max 150 words)."
    ttp_assessment = await _llm_assessment(ttp_prompt)

    network_prompt = f"Describe entity network from {len(actors_raw)} identified actors (max 150 words)."
    network_assessment = await _llm_assessment(network_prompt)

    temporal_prompt = f"Analyse posting patterns from {len(filtered)} messages across {len(channels)} channels (max 100 words)."
    temporal_analysis = await _llm_assessment(temporal_prompt)

    uk_prompt = (
        f"{'UK-relevant indicators were detected.' if uk_relevant else 'No explicit UK indicators flagged.'} "
        "Assess UK threat relevance (max 100 words)."
    )
    uk_assessment = await _llm_assessment(uk_prompt)

    recommended_actions = await _llm_assessment(
        f"Based on severity distribution and findings, recommend intelligence actions (max 100 words)."
    )

    # ─── Build template context ──────────────────────────────────────────────
    def channel_name(channel_id: int) -> str:
        ch = channels.get(channel_id)
        return ch.display_name if ch else str(channel_id)

    key_messages = []
    for m in key_messages_raw:
        keywords = []
        try:
            kw_data = json.loads(m.flagged_keywords or "[]")
            keywords = [k.get("keyword", "") for k in kw_data[:5]]
        except Exception:
            pass
        key_messages.append({
            "severity": m.severity,
            "channel_name": channel_name(m.channel_id),
            "timestamp_utc": m.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "sender_username": m.sender_username,
            "content_preview": (m.content_text or "")[:400],
            "flagged_keywords_display": ", ".join(keywords),
        })

    actors = []
    for e in actors_raw:
        try:
            channels_list = json.loads(e.source_channels or "[]")
            channels_display = ", ".join(
                channel_name(int(cid)) if cid.isdigit() else cid
                for cid in channels_list[:3]
            )
        except Exception:
            channels_display = ""
        actors.append({
            "value": e.value,
            "entity_type": e.entity_type,
            "source_channels_display": channels_display,
            "first_seen": e.first_seen.strftime("%Y-%m-%d"),
            "last_seen": e.last_seen.strftime("%Y-%m-%d"),
            "occurrence_count": e.occurrence_count,
        })

    evidence_list = [
        {
            "id": ev.id,
            "message_id": ev.message_id,
            "captured_at_utc": ev.captured_at_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "sha256_hash": ev.sha256_hash,
            "capture_method": ev.capture_method,
        }
        for ev in evidence_list_raw
    ]

    date_range = (
        f"{start_date.strftime('%Y-%m-%d') if start_date else 'All time'} — "
        f"{end_date.strftime('%Y-%m-%d') if end_date else 'Present'}"
    )

    ctx = {
        "report_reference": report_ref,
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_by": generated_by_username,
        "case_reference": case_reference,
        "date_range": date_range,
        "channel_count": len(channels),
        "executive_summary": executive_summary,
        "actors": actors,
        "key_messages": key_messages,
        "ttp_assessment": ttp_assessment,
        "network_assessment": network_assessment,
        "temporal_analysis": temporal_analysis,
        "uk_relevant": uk_relevant,
        "uk_assessment": uk_assessment,
        "evidence_list": evidence_list,
        "analyst_notes": f"Report auto-generated. {len(filtered)} messages analysed. Manual analyst review recommended before operational use.",
        "confidence_level": "MEDIUM (AI-assisted, analyst validation required)",
        "recommended_actions": recommended_actions,
    }

    # ─── Render HTML + PDF ───────────────────────────────────────────────────
    env = _get_jinja_env()
    template = env.get_template("intelreport.html")
    html_content = template.render(**ctx)

    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(content_path)
        status = "COMPLETE"
    except ImportError:
        # Fallback: save as HTML
        html_path = content_path.replace(".pdf", ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        content_path = html_path
        status = "COMPLETE"
        logger.warning("WeasyPrint not installed — report saved as HTML")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        # Save HTML as fallback so report record points to a valid file
        html_path = content_path.replace(".pdf", ".html")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            content_path = html_path
            status = "COMPLETE"
            logger.warning("PDF failed — report saved as HTML fallback")
        except Exception as e2:
            logger.error(f"HTML fallback also failed: {e2}")
            status = "FAILED"

    with Session(engine) as session:
        report = session.get(Report, report_id)
        if report:
            report.status = status
            report.content_path = content_path
            session.add(report)

        write_audit_log(
            session,
            action="REPORT_GENERATED",
            user_id=generated_by_user_id,
            target_type="REPORT",
            target_id=str(report_id),
            detail={"case_reference": case_reference, "status": status, "messages_analysed": len(filtered)},
        )

    return report_id
