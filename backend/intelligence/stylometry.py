"""
Writing style fingerprinting for cross-message author comparison.
"""
import re
import math
import logging
from collections import Counter
from typing import Optional

try:
    from langdetect import detect as _langdetect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger("ghostexodus.stylometry")


def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b\w+\b', text.lower())


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


def _trigrams(tokens: list[str]) -> list[tuple]:
    return [(tokens[i], tokens[i+1], tokens[i+2]) for i in range(len(tokens) - 2)]


def extract_features(text: str) -> dict:
    """Extract stylometric features from a body of text."""
    if not text:
        return {}

    tokens = _tokenize(text)
    sentences = _sentences(text)
    words = [t for t in tokens if t.isalpha()]

    # Average sentence length
    avg_sent_len = (
        sum(len(_tokenize(s)) for s in sentences) / len(sentences)
        if sentences else 0.0
    )

    # Vocabulary richness (type-token ratio)
    ttr = len(set(words)) / len(words) if words else 0.0

    # Punctuation frequency
    punct_count = sum(1 for c in text if c in "!?,;:…")
    punct_ratio = punct_count / len(text) if text else 0.0

    # Top 10 trigrams
    tgrams = _trigrams(tokens)
    top_trigrams = [" ".join(t) for t, _ in Counter(tgrams).most_common(10)]

    # Emoji/special char frequency
    emoji_count = sum(1 for c in text if ord(c) > 0x1F300)
    emoji_ratio = emoji_count / len(text) if text else 0.0

    # Capitalisation pattern
    cap_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0.0

    # Language detection
    language = "unknown"
    if LANGDETECT_AVAILABLE and len(text) > 20:
        try:
            language = _langdetect(text)
        except Exception:
            pass

    return {
        "avg_sentence_length": round(avg_sent_len, 2),
        "vocabulary_richness": round(ttr, 4),
        "punctuation_ratio": round(punct_ratio, 4),
        "top_trigrams": top_trigrams,
        "emoji_ratio": round(emoji_ratio, 4),
        "cap_ratio": round(cap_ratio, 4),
        "language": language,
        "word_count": len(words),
    }


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    keys = set(vec_a) | set(vec_b)
    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(v**2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v**2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _features_to_vector(features: dict) -> dict[str, float]:
    """Convert feature dict to a numeric vector for cosine similarity."""
    vec = {
        "avg_sentence_length": features.get("avg_sentence_length", 0) / 50.0,
        "vocabulary_richness": features.get("vocabulary_richness", 0),
        "punctuation_ratio": features.get("punctuation_ratio", 0) * 10,
        "emoji_ratio": features.get("emoji_ratio", 0) * 20,
        "cap_ratio": features.get("cap_ratio", 0) * 5,
    }
    # Trigram overlap as binary features
    for tg in features.get("top_trigrams", []):
        vec[f"tg_{tg}"] = 1.0
    return vec


def compare_authors(
    messages_a: list[str], messages_b: list[str]
) -> dict:
    """
    Compare two sets of messages for authorship similarity.
    Returns {similarity_score, features_a, features_b}.
    """
    text_a = " ".join(messages_a)
    text_b = " ".join(messages_b)

    feat_a = extract_features(text_a)
    feat_b = extract_features(text_b)

    vec_a = _features_to_vector(feat_a)
    vec_b = _features_to_vector(feat_b)

    score = _cosine_similarity(vec_a, vec_b)

    return {
        "similarity_score": round(score, 4),
        "features_a": feat_a,
        "features_b": feat_b,
        "high_similarity": score > 0.75,
        "language_match": feat_a.get("language") == feat_b.get("language"),
    }
