import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("filmhouse.storage")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORAGE_FILE = DATA_DIR / "tracked_media.json"


def _ensure_storage():
    """Ensure data directory and JSON file exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


import time

def record_indexed_file(message_id: int, file_name: str, parsed: dict = None, file_size_str: str = None):
    """Save forwarded message_id, filename, and parsed metadata to the tracking ledger."""
    _ensure_storage()
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records: List[Dict[str, Any]] = json.load(f)
    except Exception:
        records = []

    golden = (parsed and parsed.get("golden_name")) or file_name
    category = (parsed and parsed.get("category")) or "movies"

    records.append({
        "message_id": message_id,
        "file_name": golden,
        "original_filename": file_name,
        "category": category,
        "parsed": parsed or {},
        "file_size_str": file_size_str or "",
        "created_at": int(time.time()),
    })

    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save tracked media: {e}")


def get_tracked_files(limit: int = None) -> List[Dict[str, Any]]:
    """Retrieve tracked file records (newest first)."""
    _ensure_storage()
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
            records.reverse()  # Newest first
            if limit:
                return records[:limit]
            return records
    except Exception:
        return []


def remove_tracked_files(message_ids: List[int]):
    """Remove deleted message IDs from the local ledger."""
    _ensure_storage()
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        id_set = set(message_ids)
        filtered = [r for r in records if r["message_id"] not in id_set]

        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update tracked media ledger: {e}")


def update_tracked_category(message_ids: List[int], category: str):
    """Update category for message IDs in the local ledger."""
    _ensure_storage()
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        id_set = set(message_ids)
        for r in records:
            if r.get("message_id") in id_set:
                r["category"] = category
                if "parsed" in r and isinstance(r["parsed"], dict):
                    r["parsed"]["category"] = category

        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to update tracked media category: {e}")
