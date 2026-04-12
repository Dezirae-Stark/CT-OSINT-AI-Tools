"""
Telethon session management with keepalive and reconnect logic.
"""
import asyncio
import logging
from typing import Optional
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

from config import settings

logger = logging.getLogger("ghostexodus.telegram")

_client: Optional[TelegramClient] = None
_lock = asyncio.Lock()


async def get_client() -> TelegramClient:
    global _client
    async with _lock:
        if _client is None or not _client.is_connected():
            _client = await _create_client()
        return _client


async def _create_client() -> TelegramClient:
    client = TelegramClient(
        settings.TELEGRAM_SESSION_PATH,
        settings.TELEGRAM_API_ID,
        settings.TELEGRAM_API_HASH,
        connection_retries=5,
        retry_delay=2,
        auto_reconnect=True,
        sequential_updates=True,
    )
    await client.start(phone=settings.TELEGRAM_PHONE)
    logger.info("Telegram client connected and authenticated")
    return client


async def disconnect_client():
    global _client
    if _client and _client.is_connected():
        await _client.disconnect()
        _client = None
        logger.info("Telegram client disconnected")


async def safe_get_entity(client: TelegramClient, channel_id: str):
    """Resolve a channel identifier to a Telegram entity with flood-wait handling."""
    retries = 5
    delay = 2
    for attempt in range(retries):
        try:
            return await client.get_entity(channel_id)
        except errors.FloodWaitError as e:
            wait = e.seconds + 5
            logger.warning(f"FloodWait: sleeping {wait}s (attempt {attempt+1}/{retries})")
            await asyncio.sleep(wait)
        except (ValueError, errors.UsernameNotOccupiedError):
            logger.error(f"Channel not found: {channel_id}")
            return None
        except Exception as ex:
            logger.error(f"Error resolving entity {channel_id}: {ex}")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))
    return None
