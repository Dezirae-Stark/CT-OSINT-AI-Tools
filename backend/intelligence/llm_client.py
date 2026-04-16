"""
Async wrapper around Ollama REST API.
Request queue prevents concurrent calls from overloading VRAM.
"""
import asyncio
import json
import logging
from typing import Optional
import httpx

from config import settings

logger = logging.getLogger("ghostexodus.llm")

_semaphore = asyncio.Semaphore(1)  # single concurrent LLM call


async def _post_ollama(endpoint: str, payload: dict, timeout: int = 120) -> dict:
    url = f"{settings.OLLAMA_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def complete(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 1000,
) -> str:
    """Generate a completion from the configured LLM model (default: ghostexodus-analyst)."""
    async with _semaphore:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
                "temperature": 0.1,
            },
        }
        try:
            result = await _post_ollama("/api/chat", payload)
            return result["message"]["content"].strip()
        except Exception as e:
            logger.error(f"LLM complete() failed: {e}")
            raise


async def classify_message(content: str, context: str) -> dict:
    """Classify a message for threat indicators. Returns structured dict."""
    system = (
        "You are an expert counter-terrorism intelligence analyst working within UK CONTEST/Prevent frameworks. "
        "Analyse the provided message for extremist indicators. Return ONLY valid JSON with no additional text.\n\n"
        "Required fields:\n"
        "- threat_category: one of [NONE, PROPAGANDA, RECRUITMENT, OPERATIONAL_PLANNING, FINANCING, INCITEMENT, UNKNOWN]\n"
        "- severity: one of [NONE, LOW, MEDIUM, HIGH, CRITICAL]\n"
        "- uk_relevance: boolean — does this reference UK targets, locations, or actors?\n"
        "- indicators_found: list of specific indicators identified\n"
        "- analyst_notes: brief assessment (max 100 words)\n"
        "- requires_immediate_action: boolean\n\n"
        "Be conservative. Flag uncertain cases as LOW rather than NONE. Do not hallucinate indicators."
    )
    prompt = f"Context: {context}\n\nMessage to analyse:\n{content[:3000]}"

    try:
        raw = await complete(prompt, system=system, max_tokens=500)
        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"classify_message failed: {e}")

    return {
        "threat_category": "UNKNOWN",
        "severity": "LOW",
        "uk_relevance": False,
        "indicators_found": [],
        "analyst_notes": "LLM classification failed — manual review required.",
        "requires_immediate_action": False,
    }


async def extract_entities(content: str) -> list[dict]:
    """Extract entities from content. Returns list of {type, value} dicts."""
    system = (
        "You are an intelligence analyst extracting named entities from a Telegram message. "
        "Return ONLY valid JSON array. Each item must have: "
        '"entity_type" (USERNAME/DOMAIN/EMAIL/PHONE/ALIAS/CHANNEL) and "value" (the extracted value). '
        "Extract only entities clearly present in the text. Do not invent entities."
    )
    prompt = f"Extract all entities from:\n{content[:2000]}"

    try:
        raw = await complete(prompt, system=system, max_tokens=400)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.error(f"extract_entities failed: {e}")
    return []


async def generate_summary(messages: list[str]) -> str:
    """Generate a 200-word analytical summary of a collection of messages."""
    combined = "\n---\n".join(messages[:20])[:3000]
    system = (
        "You are a senior intelligence analyst. Write a concise 200-word executive summary "
        "of the key findings from these collected messages. Focus on threats, actors, and patterns. "
        "Write in formal intelligence report style."
    )
    try:
        return await complete(combined, system=system, max_tokens=300)
    except Exception as e:
        logger.error(f"generate_summary failed: {e}")
        return "Summary generation failed — manual review required."


async def compare_style(text_a: str, text_b: str) -> dict:
    """LLM-based writing style comparison for stylometry confirmation."""
    system = (
        "You are a forensic linguist. Compare two texts for authorship indicators. "
        "Return ONLY valid JSON with: "
        '"similarity_score" (0.0-1.0), '
        '"shared_patterns" (list of observed similarities), '
        '"differences" (list of differences), '
        '"confidence" (LOW/MEDIUM/HIGH), '
        '"same_author_likely" (boolean).'
    )
    prompt = f"Text A:\n{text_a[:1200]}\n\nText B:\n{text_b[:1200]}"
    try:
        raw = await complete(prompt, system=system, max_tokens=300)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception as e:
        logger.error(f"compare_style failed: {e}")
    return {
        "similarity_score": 0.0,
        "shared_patterns": [],
        "differences": [],
        "confidence": "LOW",
        "same_author_likely": False,
    }


async def ping_ollama() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
