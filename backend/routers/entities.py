"""Entities router — correlation graph and entity CRUD."""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select, col

from database import get_session, Entity, MessageEntityLink, Message
from auth.dependencies import get_current_user, require_analyst
from database import User

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("")
async def list_entities(
    entity_type: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Entity).order_by(col(Entity.occurrence_count).desc()).limit(limit)
    if entity_type:
        query = query.where(Entity.entity_type == entity_type.upper())
    entities = session.exec(query).all()
    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "value": e.value,
            "first_seen": e.first_seen.isoformat(),
            "last_seen": e.last_seen.isoformat(),
            "occurrence_count": e.occurrence_count,
            "source_channels": json.loads(e.source_channels or "[]"),
            "linked_entities": json.loads(e.linked_entities or "[]"),
            "notes": e.notes,
        }
        for e in entities
    ]


@router.get("/graph")
async def entity_graph(
    current_user: User = Depends(get_current_user),
):
    from intelligence.entity_extractor import get_entity_graph
    return get_entity_graph()


@router.get("/{entity_id}")
async def get_entity(
    entity_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entity = session.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get linked messages
    links = session.exec(
        select(MessageEntityLink).where(MessageEntityLink.entity_id == entity_id)
    ).all()
    message_ids = [l.message_id for l in links]
    messages = []
    if message_ids:
        msgs = session.exec(
            select(Message).where(col(Message.id).in_(message_ids[:20]))
            .order_by(col(Message.timestamp_utc).desc())
        ).all()
        messages = [
            {
                "id": m.id,
                "content_preview": (m.content_text or "")[:200],
                "timestamp_utc": m.timestamp_utc.isoformat(),
                "severity": m.severity,
            }
            for m in msgs
        ]

    # Stylometry on all messages for this entity
    all_msgs = session.exec(
        select(Message).where(col(Message.id).in_(message_ids))
    ).all() if message_ids else []

    from intelligence.stylometry import extract_features
    style_features = extract_features(" ".join(m.content_text or "" for m in all_msgs[:50]))

    return {
        "id": entity.id,
        "entity_type": entity.entity_type,
        "value": entity.value,
        "first_seen": entity.first_seen.isoformat(),
        "last_seen": entity.last_seen.isoformat(),
        "occurrence_count": entity.occurrence_count,
        "source_channels": json.loads(entity.source_channels or "[]"),
        "linked_entities": json.loads(entity.linked_entities or "[]"),
        "notes": entity.notes,
        "recent_messages": messages,
        "style_features": style_features,
    }


class MergeRequest(BaseModel):
    entity_id_a: int
    entity_id_b: int
    keep_id: int


@router.post("/merge")
async def merge_entities(
    payload: MergeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_analyst),
):
    ent_a = session.get(Entity, payload.entity_id_a)
    ent_b = session.get(Entity, payload.entity_id_b)
    if not ent_a or not ent_b:
        raise HTTPException(status_code=404, detail="One or both entities not found")
    if payload.keep_id not in (payload.entity_id_a, payload.entity_id_b):
        raise HTTPException(status_code=400, detail="keep_id must be one of the two entity IDs")

    remove_id = payload.entity_id_b if payload.keep_id == payload.entity_id_a else payload.entity_id_a
    keep_ent = session.get(Entity, payload.keep_id)
    remove_ent = session.get(Entity, remove_id)

    # Reassign links
    links = session.exec(
        select(MessageEntityLink).where(MessageEntityLink.entity_id == remove_id)
    ).all()
    for link in links:
        link.entity_id = payload.keep_id
        session.add(link)

    keep_ent.occurrence_count += remove_ent.occurrence_count

    # Merge source channels
    channels_keep = json.loads(keep_ent.source_channels or "[]")
    channels_remove = json.loads(remove_ent.source_channels or "[]")
    merged_channels = list(set(channels_keep + channels_remove))
    keep_ent.source_channels = json.dumps(merged_channels)

    session.delete(remove_ent)
    session.commit()

    return {"status": "merged", "kept_id": payload.keep_id, "removed_id": remove_id}
