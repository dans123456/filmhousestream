import collections
import logging
from typing import Optional, Dict

logger = logging.getLogger("filmhouse.cache")

# Standard MTProto chunk size (1 MB)
TG_CHUNK_SIZE = 1024 * 1024

# Cache up to the first 6 MB (chunks 0 through 5) per media file
MAX_CHUNKS_PER_MEDIA = 6

# Maximum number of unique movies/episodes to keep in RAM cache (LRU)
MAX_CACHED_ITEMS = 60

# In-memory storage: OrderedDict[message_id, Dict[chunk_index, bytes]]
_lru_chunk_cache: collections.OrderedDict[int, Dict[int, bytes]] = collections.OrderedDict()


def get_cached_chunk(message_id: int, chunk_index: int) -> Optional[bytes]:
    """
    Retrieves a cached 1MB chunk for the given message_id if present.
    Updates LRU recency.
    """
    if message_id in _lru_chunk_cache:
        # Move to end (most recently used)
        _lru_chunk_cache.move_to_end(message_id)
        chunks = _lru_chunk_cache[message_id]
        return chunks.get(chunk_index)
    return None


def store_cached_chunk(message_id: int, chunk_index: int, chunk_data: bytes):
    """
    Stores an initial chunk (up to MAX_CHUNKS_PER_MEDIA) in RAM cache.
    Evicts oldest items if cache size exceeds MAX_CACHED_ITEMS.
    """
    if chunk_index >= MAX_CHUNKS_PER_MEDIA:
        return

    if message_id not in _lru_chunk_cache:
        # Check eviction
        if len(_lru_chunk_cache) >= MAX_CACHED_ITEMS:
            oldest_id, _ = _lru_chunk_cache.popitem(last=False)
            logger.debug(f"Evicted message_id {oldest_id} from chunk cache.")
        _lru_chunk_cache[message_id] = {}

    _lru_chunk_cache[message_id][chunk_index] = chunk_data
    _lru_chunk_cache.move_to_end(message_id)


def get_cache_stats() -> dict:
    """Returns statistics about the current RAM cache."""
    total_chunks = sum(len(chunks) for chunks in _lru_chunk_cache.values())
    approx_mb = round((total_chunks * TG_CHUNK_SIZE) / (1024 * 1024), 2)
    return {
        "cached_media_count": len(_lru_chunk_cache),
        "total_cached_chunks": total_chunks,
        "approx_memory_mb": approx_mb,
    }
