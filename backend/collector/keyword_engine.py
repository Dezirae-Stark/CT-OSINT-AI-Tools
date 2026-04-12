"""
Keyword matching engine — organized by threat category.
Returns match results with severity contributions.
"""
import re
import json
from dataclasses import dataclass, field
from typing import Optional
from sqlmodel import Session, select

from database import AlertRule


@dataclass
class KeywordMatch:
    category: str
    keyword: str
    severity_contribution: int  # 1 = low, 2 = medium, 3 = high
    context_window: str  # ±50 chars around match
    match_type: str = "EXACT"  # EXACT / REGEX


# ─── Built-in keyword lists ───────────────────────────────────────────────────

KEYWORD_LISTS = {
    "OPERATIONAL_PLANNING": {
        "severity": 3,
        "terms": [
            "target acquisition", "surveillance of", "reconnaissance",
            "attack vector", "entry point", "timing of attack",
            "soft target", "high value target", "crowded venue",
            "improvised explosive", "IED", "vehicle ramming",
            "suicide vest", "martyrdom operation", "lone wolf",
            "cell activation", "go time", "zero hour", "d-day",
            "safe house", "exfiltration", "operational security",
            "opsec protocol", "burner phone", "encrypted comms only",
            "clean device", "dry run", "trial run before",
        ],
    },
    "RECRUITMENT": {
        "severity": 2,
        "terms": [
            "join the cause", "join our ranks", "brothers needed",
            "sisters needed", "willing to fight", "ready to sacrifice",
            "hijra", "make bay'ah", "pledge allegiance",
            "ingroup only", "contact for vetting", "dm for access",
            "private channel link", "selected brothers",
            "willing to travel", "experienced only apply",
            "bring your skills", "technical skills needed",
            "sleeper", "embedded", "deep cover",
        ],
    },
    "FINANCING": {
        "severity": 2,
        "terms": [
            "hawala", "send via crypto", "monero only", "bitcoin donation",
            "untraceable transfer", "anonymous wallet",
            "fund the operation", "operational expenses",
            "zakat for jihad", "equipment purchase",
            "arms procurement", "weapons supply",
            "financial support needed", "sponsor a fighter",
            "send funds urgently",
        ],
    },
    "PROPAGANDA": {
        "severity": 1,
        "terms": [
            "infidel", "kuffar", "crusaders", "kafir",
            "death to", "destroy the west", "allah's soldiers",
            "righteous killing", "justified slaughter",
            "martyrs of", "paradise awaits", "honour killing",
            "apostates deserve", "sharia enforcement",
            "caliphate now", "islamic state victory",
            "nasheed", "anasheed", "takfir",
            "dawlah", "wilayah",
        ],
    },
    "UK_SPECIFIC": {
        "severity": 2,
        "terms": [
            "london bridge", "westminster", "parliament", "buckingham",
            "10 downing", "trafalgar", "oxford street",
            "manchester arena", "king's cross", "victoria station",
            "heathrow", "gatwick", "stansted",
            "met police", "mi5", "mi6", "gchq",
            "far right uk", "nar", "national action",
            "ukip extremist", "britain first",
            "mosque attack uk", "synagogue uk",
        ],
    },
    "INCITEMENT": {
        "severity": 3,
        "terms": [
            "kill them all", "slaughter", "massacre", "exterminate",
            "wage war against", "rise up and fight",
            "attack now", "time to act", "enough talk",
            "blood must flow", "make them pay",
            "no mercy", "spare no one",
        ],
    },
}

# Regex patterns for structured data indicators
REGEX_PATTERNS = {
    "CRYPTO_ADDRESS": (re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'), 2),
    "ONION_LINK": (re.compile(r'\b[a-z2-7]{16,56}\.onion\b'), 2),
    "TELEGRAM_INVITE": (re.compile(r't\.me/\+[A-Za-z0-9_-]{16,}'), 1),
    "PHONE_UK": (re.compile(r'\+44\s?[0-9]{2,4}\s?[0-9]{3,4}\s?[0-9]{3,4}'), 1),
    "ENCRYPTED_CONTACT": (re.compile(r'signal:|wickr:|proton(mail)?:|element:|session id'), 2),
}


def _context(text: str, start: int, end: int, window: int = 50) -> str:
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end]
    if ctx_start > 0:
        snippet = "…" + snippet
    if ctx_end < len(text):
        snippet = snippet + "…"
    return snippet


def match_keywords(content: str, db_rules: list[AlertRule] = None) -> list[KeywordMatch]:
    """Run all keyword lists against content. Returns list of matches."""
    if not content:
        return []

    content_lower = content.lower()
    matches: list[KeywordMatch] = []
    seen: set[str] = set()

    # Built-in keyword lists
    for category, config in KEYWORD_LISTS.items():
        for term in config["terms"]:
            term_lower = term.lower()
            idx = content_lower.find(term_lower)
            if idx != -1 and term_lower not in seen:
                seen.add(term_lower)
                matches.append(KeywordMatch(
                    category=category,
                    keyword=term,
                    severity_contribution=config["severity"],
                    context_window=_context(content, idx, idx + len(term)),
                    match_type="EXACT",
                ))

    # Regex patterns
    for pattern_name, (pattern, sev) in REGEX_PATTERNS.items():
        m = pattern.search(content)
        if m and pattern_name not in seen:
            seen.add(pattern_name)
            matches.append(KeywordMatch(
                category=pattern_name,
                keyword=m.group(0)[:50],
                severity_contribution=sev,
                context_window=_context(content, m.start(), m.end()),
                match_type="REGEX",
            ))

    # User-defined alert rules (KEYWORD type)
    if db_rules:
        for rule in db_rules:
            if rule.trigger_type != "KEYWORD" or not rule.is_active:
                continue
            val = rule.trigger_value
            try:
                # Try as regex first
                pattern = re.compile(val, re.IGNORECASE)
                m = pattern.search(content)
                if m and f"RULE_{rule.id}" not in seen:
                    seen.add(f"RULE_{rule.id}")
                    matches.append(KeywordMatch(
                        category="USER_RULE",
                        keyword=val,
                        severity_contribution=2,
                        context_window=_context(content, m.start(), m.end()),
                        match_type="REGEX",
                    ))
            except re.error:
                if val.lower() in content_lower and f"RULE_{rule.id}" not in seen:
                    seen.add(f"RULE_{rule.id}")
                    idx = content_lower.find(val.lower())
                    matches.append(KeywordMatch(
                        category="USER_RULE",
                        keyword=val,
                        severity_contribution=2,
                        context_window=_context(content, idx, idx + len(val)),
                        match_type="EXACT",
                    ))

    return matches


def compute_severity(matches: list[KeywordMatch]) -> str:
    """Aggregate matches into a severity level."""
    if not matches:
        return "NONE"

    total_score = sum(m.severity_contribution for m in matches)
    count = len(matches)

    if count >= 6 or total_score >= 12:
        return "HIGH"
    elif count >= 3 or total_score >= 6:
        return "MEDIUM"
    elif count >= 1 or total_score >= 1:
        return "LOW"
    return "NONE"


def matches_to_json(matches: list[KeywordMatch]) -> str:
    return json.dumps([
        {
            "category": m.category,
            "keyword": m.keyword,
            "severity_contribution": m.severity_contribution,
            "context": m.context_window,
            "match_type": m.match_type,
        }
        for m in matches
    ])
