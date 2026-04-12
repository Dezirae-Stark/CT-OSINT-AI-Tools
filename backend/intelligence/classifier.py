"""
Threat classifier — wraps llm_client with structured prompt logic.
"""
from intelligence.llm_client import classify_message


async def classify_message_text(content: str, context: str = "") -> dict:
    """
    Classify a message and return structured threat assessment.
    Delegates to llm_client.classify_message with enriched context.
    """
    return await classify_message(content, context)
