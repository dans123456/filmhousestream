import logging
from typing import Optional, Tuple, Any
from hydrogram import Client
from hydrogram.types import Message
import config

logger = logging.getLogger("filmhouse.bot")

# Global Telegram Bot MTProto Client
tg_client: Optional[Client] = None

# In-memory metadata cache: message_id -> (file_size, file_name, mime_type, file_id)
_media_cache: dict[int, dict[str, Any]] = {}


def get_tg_client() -> Client:
    """Returns or creates the Pyrogram/Hydrogram MTProto client singleton."""
    global tg_client
    if tg_client is None:
        tg_client = Client(
            name="filmhouse_stream_session",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            workers=16,
            max_concurrent_transmissions=8,
        )
    return tg_client


async def get_media_info(message_id: int) -> Optional[dict[str, Any]]:
    """
    Fetches the media object and its metadata from the storage channel.
    Caches metadata in memory for ultra-fast seek operations.
    """
    if message_id in _media_cache:
        return _media_cache[message_id]

    client = get_tg_client()
    try:
        msg: Message = await client.get_messages(config.BIN_CHANNEL_ID, message_id)
        if not msg or msg.empty:
            return None

        media = msg.video or msg.document or msg.audio or msg.animation
        if not media:
            return None

        file_name = getattr(media, "file_name", None) or f"video_{message_id}.mp4"
        mime_type = getattr(media, "mime_type", None) or "video/mp4"
        file_size = getattr(media, "file_size", 0)

        info = {
            "message": msg,
            "media": media,
            "file_name": file_name,
            "mime_type": mime_type,
            "file_size": file_size,
        }
        
        # Keep cache bounded
        if len(_media_cache) > 2000:
            _media_cache.pop(next(iter(_media_cache)))
            
        _media_cache[message_id] = info
        return info
    except Exception as e:
        logger.error(f"Error fetching media for message_id {message_id}: {e}")
        return None
