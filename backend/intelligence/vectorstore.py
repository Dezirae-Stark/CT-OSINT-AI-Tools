"""
ChromaDB CRUD operations for semantic message storage.
"""
import logging
import os
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlmodel import Session, select

from config import settings
from database import engine, Message

logger = logging.getLogger("ghostexodus.vectorstore")

_client: Optional[chromadb.Client] = None
_collection = None

COLLECTION_NAME = "osint_messages"


def get_chroma_client() -> chromadb.Client:
    global _client
    if _client is None:
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def upsert_message_by_id(message_id: int):
    """Load a message from SQLite and upsert its embedding into ChromaDB."""
    from intelligence.embedder import embed_text
    import json

    with Session(engine) as session:
        msg = session.get(Message, message_id)
        if not msg or not msg.content_text:
            return

        embedding = await embed_text(msg.content_text)
        if embedding is None:
            return

        doc_id = f"msg_{msg.telegram_message_id}_{msg.channel_id}"
        metadata = {
            "channel_id": str(msg.channel_id),
            "sender_username": msg.sender_username or "",
            "timestamp_utc": msg.timestamp_utc.isoformat(),
            "severity": msg.severity,
            "flagged_keywords": msg.flagged_keywords[:500],  # trim for metadata
            "message_db_id": str(msg.id),
        }

        coll = get_collection()
        coll.upsert(
            ids=[doc_id],
            documents=[msg.content_text[:2000]],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.debug(f"Upserted message {message_id} to ChromaDB")


async def semantic_search(
    query: str,
    n_results: int = 20,
    filters: Optional[dict] = None,
) -> list[dict]:
    """Search by semantic similarity. Returns list of result dicts."""
    from intelligence.embedder import embed_text

    embedding = await embed_text(query)
    if embedding is None:
        return []

    coll = get_collection()
    where = filters or None

    try:
        results = coll.query(
            query_embeddings=[embedding],
            n_results=min(n_results, coll.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error(f"ChromaDB query error: {e}")
        return []

    output = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
        output.append({
            "chroma_id": doc_id,
            "content": doc,
            "metadata": meta,
            "relevance_score": round(1 - dist, 4),
            "message_db_id": meta.get("message_db_id"),
        })

    return output


async def search_by_entity(entity_value: str, n_results: int = 50) -> list[dict]:
    """Find messages semantically similar to an entity value."""
    return await semantic_search(entity_value, n_results=n_results)


async def get_temporal_cluster(
    start: str, end: str, channel_id: Optional[int] = None
) -> list[dict]:
    """Retrieve all documents in a time window via metadata filtering."""
    coll = get_collection()
    where: dict = {
        "$and": [
            {"timestamp_utc": {"$gte": start}},
            {"timestamp_utc": {"$lte": end}},
        ]
    }
    if channel_id:
        where["$and"].append({"channel_id": {"$eq": str(channel_id)}})

    try:
        results = coll.get(where=where, include=["documents", "metadatas"])
    except Exception as e:
        logger.error(f"Temporal cluster query failed: {e}")
        return []

    output = []
    for doc, meta in zip(results.get("documents", []), results.get("metadatas", [])):
        output.append({"content": doc, "metadata": meta})
    return output


def get_collection_stats() -> dict:
    try:
        coll = get_collection()
        count = coll.count()
        return {"collection": COLLECTION_NAME, "document_count": count, "status": "OK"}
    except Exception as e:
        return {"collection": COLLECTION_NAME, "document_count": 0, "status": f"ERROR: {e}"}
