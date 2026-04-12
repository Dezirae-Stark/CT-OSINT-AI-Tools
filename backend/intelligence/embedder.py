"""
nomic-embed-text embeddings via Ollama API.
"""
import logging
import httpx
from typing import Optional

from config import settings

logger = logging.getLogger("ghostexodus.embedder")


async def embed_text(text: str) -> Optional[list[float]]:
    """Generate an embedding vector for the given text."""
    if not text or not text.strip():
        return None
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": settings.EMBED_MODEL,
        "prompt": text[:2000],  # Respect context limit
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding")
    except Exception as e:
        logger.error(f"embed_text failed: {e}")
        return None


async def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed a list of texts, one at a time (Ollama does not support batch)."""
    results = []
    for text in texts:
        emb = await embed_text(text)
        results.append(emb)
    return results
