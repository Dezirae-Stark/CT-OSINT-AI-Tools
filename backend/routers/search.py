"""Search router — semantic, keyword, and entity search."""
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select, col

from database import get_session, Message, MonitoredChannel
from auth.dependencies import get_current_user
from database import User

router = APIRouter(prefix="/api/search", tags=["search"])
logger = logging.getLogger("ghostexodus.search")


class SearchRequest(BaseModel):
    query: str
    mode: str = "SEMANTIC"  # SEMANTIC / KEYWORD / ENTITY
    filters: Optional[dict] = None
    limit: int = 20
    offset: int = 0


@router.post("")
async def search(
    payload: SearchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    results = []

    if payload.mode == "SEMANTIC":
        from intelligence.vectorstore import semantic_search
        chroma_results = await semantic_search(
            payload.query,
            n_results=payload.limit,
            filters=payload.filters,
        )
        # Enrich with DB data
        for r in chroma_results:
            db_id = r.get("metadata", {}).get("message_db_id")
            if db_id:
                msg = session.get(Message, int(db_id))
                if msg:
                    ch = session.get(MonitoredChannel, msg.channel_id)
                    results.append({
                        "message_id": msg.id,
                        "channel_name": ch.display_name if ch else str(msg.channel_id),
                        "sender_username": msg.sender_username,
                        "content_text": msg.content_text,
                        "timestamp_utc": msg.timestamp_utc.isoformat(),
                        "severity": msg.severity,
                        "relevance_score": r.get("relevance_score", 0),
                        "flagged_keywords": json.loads(msg.flagged_keywords or "[]"),
                    })

    elif payload.mode == "RAG":
        from intelligence.rag_query import rag_query
        rag_result = await rag_query(payload.query, top_k=payload.limit)
        return {"mode": "RAG", "answer": rag_result["answer"], "sources": rag_result["sources"]}

    elif payload.mode == "KEYWORD":
        query = (
            select(Message)
            .where(col(Message.content_text).contains(payload.query))
            .order_by(col(Message.timestamp_utc).desc())
            .offset(payload.offset)
            .limit(payload.limit)
        )
        messages = session.exec(query).all()
        channel_ids = list(set(m.channel_id for m in messages))
        channels = {}
        if channel_ids:
            chs = session.exec(
                select(MonitoredChannel).where(col(MonitoredChannel.id).in_(channel_ids))
            ).all()
            channels = {c.id: c.display_name for c in chs}

        results = [
            {
                "message_id": m.id,
                "channel_name": channels.get(m.channel_id, str(m.channel_id)),
                "sender_username": m.sender_username,
                "content_text": m.content_text,
                "timestamp_utc": m.timestamp_utc.isoformat(),
                "severity": m.severity,
                "relevance_score": 1.0,
                "flagged_keywords": json.loads(m.flagged_keywords or "[]"),
            }
            for m in messages
        ]

    elif payload.mode == "ENTITY":
        from intelligence.vectorstore import search_by_entity
        chroma_results = await search_by_entity(payload.query, n_results=payload.limit)
        for r in chroma_results:
            db_id = r.get("metadata", {}).get("message_db_id")
            if db_id:
                msg = session.get(Message, int(db_id))
                if msg:
                    ch = session.get(MonitoredChannel, msg.channel_id)
                    results.append({
                        "message_id": msg.id,
                        "channel_name": ch.display_name if ch else str(msg.channel_id),
                        "sender_username": msg.sender_username,
                        "content_text": msg.content_text,
                        "timestamp_utc": msg.timestamp_utc.isoformat(),
                        "severity": msg.severity,
                        "relevance_score": r.get("relevance_score", 0),
                        "flagged_keywords": json.loads(msg.flagged_keywords or "[]"),
                    })

    return {
        "mode": payload.mode,
        "query": payload.query,
        "count": len(results),
        "results": results,
    }
