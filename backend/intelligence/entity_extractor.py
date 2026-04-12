"""
Entity extraction — regex + LLM hybrid.
Finds usernames, domains, emails, phones, aliases, Telegram links.
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from sqlmodel import Session, select

from database import engine, Entity, MessageEntityLink, Message
from intelligence.llm_client import extract_entities as llm_extract_entities

logger = logging.getLogger("ghostexodus.entity_extractor")

# ─── Regex patterns ───────────────────────────────────────────────────────────
RE_USERNAME = re.compile(r'@([A-Za-z0-9_]{4,32})')
RE_TELEGRAM_LINK = re.compile(r't\.me/(?:\+|joinchat/)?([A-Za-z0-9_-]{4,})')
RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
RE_DOMAIN = re.compile(r'\b(?:https?://)?([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+\.[A-Za-z]{2,})\b')
RE_PHONE_E164 = re.compile(r'\+[1-9]\d{6,14}\b')
RE_PHONE_UK = re.compile(r'\b0[1-9]\d{8,9}\b')


def _regex_extract(content: str) -> list[dict]:
    found = []
    for m in RE_USERNAME.finditer(content):
        found.append({"entity_type": "USERNAME", "value": m.group(1)})
    for m in RE_TELEGRAM_LINK.finditer(content):
        found.append({"entity_type": "CHANNEL", "value": m.group(0)})
    for m in RE_EMAIL.finditer(content):
        found.append({"entity_type": "EMAIL", "value": m.group(0).lower()})
    for m in RE_PHONE_E164.finditer(content):
        found.append({"entity_type": "PHONE", "value": m.group(0)})
    for m in RE_PHONE_UK.finditer(content):
        found.append({"entity_type": "PHONE", "value": m.group(0)})
    # Domains — exclude common benign ones
    benign = {"google.com", "telegram.org", "t.me", "wikipedia.org"}
    for m in RE_DOMAIN.finditer(content):
        domain = m.group(1).lower()
        if domain not in benign and "." in domain:
            found.append({"entity_type": "DOMAIN", "value": domain})
    return found


def _dedup(entities: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for e in entities:
        key = (e["entity_type"], e["value"].lower())
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


async def extract_and_store(message_id: int, content: str, channel_id: int) -> list[int]:
    """Extract entities from content and store in DB. Returns list of entity IDs."""
    regex_entities = _regex_extract(content)

    # LLM extraction for aliases (only if short enough)
    llm_entities = []
    if len(content) < 1500:
        try:
            llm_entities = await llm_extract_entities(content)
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")

    all_entities = _dedup(regex_entities + llm_entities)
    entity_ids = []

    with Session(engine) as session:
        for ent_data in all_entities:
            etype = ent_data.get("entity_type", "ALIAS")
            value = str(ent_data.get("value", "")).strip()
            if not value:
                continue

            # Upsert entity
            existing = session.exec(
                select(Entity).where(
                    Entity.entity_type == etype,
                    Entity.value == value,
                )
            ).first()

            if existing:
                existing.last_seen = datetime.utcnow()
                existing.occurrence_count += 1
                channels = json.loads(existing.source_channels or "[]")
                if str(channel_id) not in channels:
                    channels.append(str(channel_id))
                    existing.source_channels = json.dumps(channels)
                session.add(existing)
                session.commit()
                entity_id = existing.id
            else:
                new_entity = Entity(
                    entity_type=etype,
                    value=value,
                    source_channels=json.dumps([str(channel_id)]),
                )
                session.add(new_entity)
                session.commit()
                session.refresh(new_entity)
                entity_id = new_entity.id

            entity_ids.append(entity_id)

            # Link to message
            link_exists = session.exec(
                select(MessageEntityLink).where(
                    MessageEntityLink.message_id == message_id,
                    MessageEntityLink.entity_id == entity_id,
                )
            ).first()
            if not link_exists:
                session.add(MessageEntityLink(message_id=message_id, entity_id=entity_id))
                session.commit()

    return entity_ids


async def correlate_new_entities():
    """Find entities that co-appear in the same messages and update linked_entities."""
    with Session(engine) as session:
        links = session.exec(select(MessageEntityLink)).all()

    # Group entity IDs by message_id
    msg_to_entities: dict[int, list[int]] = {}
    for link in links:
        msg_to_entities.setdefault(link.message_id, []).append(link.entity_id)

    # Build co-occurrence counts
    co_occurrence: dict[tuple, int] = {}
    for entities in msg_to_entities.values():
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                pair = (min(entities[i], entities[j]), max(entities[i], entities[j]))
                co_occurrence[pair] = co_occurrence.get(pair, 0) + 1

    # Update linked_entities for pairs with >= 2 co-occurrences
    with Session(engine) as session:
        for (eid_a, eid_b), count in co_occurrence.items():
            if count < 2:
                continue
            for target_id, linked_id in [(eid_a, eid_b), (eid_b, eid_a)]:
                ent = session.get(Entity, target_id)
                if ent:
                    linked = json.loads(ent.linked_entities or "[]")
                    if linked_id not in linked:
                        linked.append(linked_id)
                        ent.linked_entities = json.dumps(linked)
                        session.add(ent)
        session.commit()

    logger.info(f"Entity correlation complete: {len(co_occurrence)} pairs evaluated")


def get_entity_graph() -> dict:
    """Return nodes and edges for React Flow visualization."""
    with Session(engine) as session:
        entities = session.exec(select(Entity)).all()
        links = session.exec(select(MessageEntityLink)).all()

    # Build co-occurrence edges
    msg_to_entities: dict[int, list[int]] = {}
    for link in links:
        msg_to_entities.setdefault(link.message_id, []).append(link.entity_id)

    edge_counts: dict[tuple, int] = {}
    for entities_in_msg in msg_to_entities.values():
        for i in range(len(entities_in_msg)):
            for j in range(i + 1, len(entities_in_msg)):
                pair = (
                    min(entities_in_msg[i], entities_in_msg[j]),
                    max(entities_in_msg[i], entities_in_msg[j]),
                )
                edge_counts[pair] = edge_counts.get(pair, 0) + 1

    type_color = {
        "USERNAME": "#3b82f6",
        "DOMAIN": "#f59e0b",
        "EMAIL": "#22c55e",
        "PHONE": "#a855f7",
        "ALIAS": "#ec4899",
        "CHANNEL": "#06b6d4",
    }

    nodes = [
        {
            "id": str(e.id),
            "data": {
                "label": e.value,
                "type": e.entity_type,
                "occurrences": e.occurrence_count,
            },
            "position": {"x": 0, "y": 0},
            "style": {"background": type_color.get(e.entity_type, "#374151")},
        }
        for e in entities
    ]

    edges = [
        {
            "id": f"e{a}-{b}",
            "source": str(a),
            "target": str(b),
            "label": str(count),
            "style": {"strokeWidth": min(count, 8)},
        }
        for (a, b), count in edge_counts.items()
        if count >= 1
    ]

    return {"nodes": nodes, "edges": edges}
