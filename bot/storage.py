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

    from server.parser import build_golden_filename
    golden = (parsed and parsed.get("golden_name")) or (parsed and build_golden_filename(parsed, file_name)) or file_name
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


def is_nameless_record(r: dict) -> bool:
    """
    Checks if a media record has NO actual movie/show title at all.
    Strictly matches ONLY:
      - .S01E11.mkv, S01E11.mkv (only season and episode, no show name)
      - Episode.15.S01E15.mkv, Episode 15.mkv (no show name)
    Does NOT match files with legitimate titles like:
      - S05E01.All.The.Queen's.Men.mkv
      - .A.Shop.for.Killers.mkv
      - Pursuit Of Jade, Never Ending Summer, etc.
    """
    import re
    fn = (r.get("original_filename") or r.get("file_name") or "").strip()
    title = (r.get("title") or "").strip()
    parsed = r.get("parsed") or {}
    parsed_title = (parsed.get("title") or "").strip()

    base_fn = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", fn).strip()

    # 1. Bare SxxExx (e.g. ".S01E11", "S01E12", ".s1e05")
    if re.match(r"^\.?\s*[sS]\d{1,2}[\s\._\-]*[eE]\d{1,3}(?:[\s\._\-]*[eE]\d{1,3})?$", base_fn):
        return True

    # 2. Bare Episode XX or Episode XX SxxExx (e.g. "Episode.15.S01E15", "Episode 15", "Ep 12")
    if re.match(r"^\.?\s*(?:[eE]p(?:isode)?|EP)[\s\._\-]*\d{1,3}(?:[\s\._\-]*[sS]\d{1,2}[\s\._\-]*[eE]\d{1,3})?$", base_fn, re.IGNORECASE):
        return True

    # 3. Check if parsed title is purely generic ("Episode X", "S01EX", "Unnamed Series") and filename has no actual title words
    for t in (title, parsed_title):
        if t and re.match(r"^[\s\._\-]*(?:episode\s*\d+|s\d{1,2}e\d{1,3}|unnamed\s*series)[\s\._\-]*$", t, re.IGNORECASE):
            words = [w for w in re.split(r"[\s\._\-]+", base_fn) if w and not re.match(r"^(?:s\d{1,2}e\d{1,3}|ep\d*|episode\d*|720p|1080p|480p|filmhouse|fil|x264|x265|mkv|mp4)$", w, re.IGNORECASE)]
            if len(words) == 0:
                return True

    return False


def get_nameless_records() -> List[Dict[str, Any]]:
    """Retrieve all nameless or dot-prefixed corrupted file records."""
    records = get_tracked_files()
    return [r for r in records if is_nameless_record(r)]


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


def update_tracked_metadata(message_id: int, updates: dict):
    """Updates metadata (title, year, season, episode, is_series, category, tmdb_id) for a message ID in the local ledger.
    Supports bulk-updating all episodes in a series when apply_all_series is True."""
    _ensure_storage()
    try:
        from server.parser import build_golden_filename, safe_int
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        target_r = next((r for r in records if r.get("message_id") == message_id), None)
        if not target_r:
            return

        target_parsed = target_r.get("parsed") or {}
        old_series_title = (target_parsed.get("title") or target_r.get("series_title") or "").strip().lower()
        apply_all = bool(updates.get("apply_all_series"))

        updated_count = 0
        for r in records:
            p = r.get("parsed") or {}
            is_match = (r.get("message_id") == message_id)
            if not is_match and apply_all and old_series_title:
                r_title = (p.get("title") or r.get("series_title") or "").strip().lower()
                if r_title == old_series_title and (p.get("is_series") or r.get("is_series")):
                    is_match = True

            if is_match:
                updated_count += 1
                if "title" in updates and updates["title"]:
                    new_t = str(updates["title"]).strip()
                    p["title"] = new_t
                    r["title"] = new_t
                if "year" in updates:
                    y = safe_int(updates["year"])
                    p["year"] = y
                    r["year"] = y
                if "tmdb_id" in updates:
                    t_id = safe_int(updates["tmdb_id"])
                    p["tmdb_id"] = t_id
                    r["tmdb_id"] = t_id
                if "is_series" in updates:
                    is_s = bool(updates["is_series"])
                    p["is_series"] = is_s
                    r["is_series"] = is_s
                if not apply_all:
                    if "season" in updates and updates["season"] is not None:
                        p["season"] = safe_int(updates["season"], default=1)
                    if "episode" in updates and updates["episode"] is not None:
                        p["episode"] = safe_int(updates["episode"], default=1)
                if "category" in updates and updates["category"]:
                    cat = str(updates["category"]).strip().lower()
                    r["category"] = cat
                    p["category"] = cat

                orig_fn = r.get("original_filename") or r.get("file_name", "")
                golden = build_golden_filename(p, orig_fn)
                p["golden_name"] = golden
                r["file_name"] = golden
                r["parsed"] = p

        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated metadata for {updated_count} record(s) (apply_all={apply_all}).")

        # Invalidate in-memory audit cache for this show
        try:
            from server.tmdb_auditor import invalidate_series_audit
            invalidate_series_audit(old_series_title)
            if updates.get("title"):
                invalidate_series_audit(updates["title"])
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to update tracked media metadata: {e}")


def heal_stored_series_ledger():
    """Scans tracked_media.json and permanently heals misclassified series (Chucky, My Demon, A Killer Paradox, leading episode numbers)."""
    _ensure_storage()
    try:
        import re
        from server.parser import parse_filename, build_golden_filename
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

        changed = False
        for r in records:
            fn = r.get("file_name") or r.get("original_filename") or ""
            parsed = r.get("parsed") or {}
            lower_fn = fn.lower()
            lower_title = str(parsed.get("title") or "").lower()

            needs_heal = (
                "chucky" in lower_fn or "chucky" in lower_title or
                "killer paradox" in lower_fn or "killer paradox" in lower_title or
                "my demon" in lower_fn or "my demon" in lower_title or "mydemon" in lower_fn or
                (not parsed.get("is_series") and re.search(r"^(?:(?:ep|episode|e)[\s\.\-_]*)?(0[1-9]|[1-9]\d?)[\s\.\-_]+[a-zA-Z]", fn, re.IGNORECASE))
            )

            if needs_heal:
                fresh = parse_filename(fn)
                if fresh.get("is_series"):
                    parsed.update(fresh)
                    r["parsed"] = parsed
                    r["is_series"] = True
                    r["category"] = fresh.get("category") or r.get("category") or "series"
                    golden = build_golden_filename(parsed, fn)
                    r["file_name"] = golden
                    changed = True

        if changed:
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            logger.info("Successfully healed tracked_media.json records on disk.")
    except Exception as e:
        logger.warning(f"Notice during heal_stored_series_ledger: {e}")

