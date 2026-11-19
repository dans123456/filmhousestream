import os
import json
import time
import re
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("filmhouse.storage")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STORAGE_FILE = DATA_DIR / "tracked_media.json"

_storage_lock = threading.RLock()
_records_cache: Optional[List[Dict[str, Any]]] = None
_records_mtime: float = 0.0
_canonical_index: Optional[Dict[str, Dict[str, Any]]] = None


def _ensure_storage():
    """Ensure data directory and JSON file exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        tmp_path = STORAGE_FILE.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        os.replace(tmp_path, STORAGE_FILE)


def _load_records_raw() -> List[Dict[str, Any]]:
    """Loads tracked_media.json with mtime-based in-memory caching."""
    global _records_cache, _records_mtime, _canonical_index
    with _storage_lock:
        _ensure_storage()
        try:
            mtime = STORAGE_FILE.stat().st_mtime
        except OSError:
            mtime = 0.0
        if _records_cache is not None and mtime == _records_mtime:
            return _records_cache
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except Exception as e:
            logger.error(f"Failed to read tracked media ledger: {e}")
            data = []
        _records_cache = data
        _records_mtime = mtime
        _canonical_index = None
        return _records_cache


def _save_records_atomic(records: List[Dict[str, Any]]):
    """Atomically writes tracked_media.json via temp file + os.replace and updates caches."""
    global _records_cache, _records_mtime, _canonical_index
    with _storage_lock:
        _ensure_storage()
        tmp_path = STORAGE_FILE.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, STORAGE_FILE)
        _records_cache = records
        try:
            _records_mtime = STORAGE_FILE.stat().st_mtime
        except OSError:
            _records_mtime = time.time()
        _canonical_index = None
    try:
        from server.stream_server import invalidate_media_cache
        invalidate_media_cache()
    except Exception:
        pass


def parse_size_bytes(size_val: Any) -> int:
    """Safely converts file size strings (e.g. '750.5 MB', '1.4 GB') or numbers to integer bytes."""
    if not size_val:
        return 0
    if isinstance(size_val, (int, float)):
        return int(size_val)
    s = str(size_val).strip().upper()
    try:
        m = re.match(r"^([\d\.]+)\s*([KMGT]?B?)$", s)
        if not m:
            return 0
        num = float(m.group(1))
        unit = m.group(2)
        if "G" in unit:
            return int(num * 1024 * 1024 * 1024)
        if "M" in unit:
            return int(num * 1024 * 1024)
        if "K" in unit:
            return int(num * 1024)
        return int(num)
    except Exception:
        return 0


def get_canonical_item_key(parsed: dict, file_name: str) -> str:
    """
    Computes a canonical deduplication key for any media file.
    - Series: series:<canonical_title>:s<season>:e<episode>
    - Movie: movie:<canonical_title>:<year>:<quality>
    """
    p = parsed or {}
    raw_title = str(p.get("title") or file_name or "").strip().lower()

    # Universal normalization
    norm = re.sub(r"['’`]", "", raw_title)
    norm = norm.replace("&", " and ")
    norm = re.sub(r"[^a-z0-9\s]", " ", norm)
    norm = re.sub(r"\s+", "_", norm.strip())
    norm = re.sub(r"^(the|a|an)_+", "", norm)
    norm = re.sub(r"^(the_)?(end|finale|final)_+", "", norm)
    norm = re.sub(r"_+(the_)?(end|finale|final)$", "", norm)

    # Franchise canonical aliases
    if norm.startswith("avatar_aang") or norm.startswith("avatar_the_last_airbender") or norm.startswith("legend_of_aang") or "last_airbender" in norm:
        norm = "avatar_the_last_airbender"
    elif norm.startswith("macgyver"):
        norm = "macgyver"
    elif norm.startswith("love_in_disguise"):
        norm = "love_in_disguise"
    elif norm == "forever" or norm.startswith("forever_"):
        norm = "forever"
    elif "ruthless" in norm:
        norm = "tyler_perrys_ruthless"
    elif "sista" in norm:
        norm = "tyler_perrys_sistas"
    elif norm.startswith("flex_x_cop") or norm.startswith("flexxcop") or norm.startswith("flex_cop") or norm == "flex_cop":
        norm = "flex_x_cop"

    is_series = bool(p.get("is_series"))
    if is_series:
        s = p.get("season") or 1
        e = p.get("episode") or 1
        try:
            s_int = int(s)
            e_int = int(e)
        except Exception:
            s_int, e_int = 1, 1
        return f"series:{norm}:s{s_int:02d}:e{e_int:02d}"
    else:
        y = str(p.get("year") or "").strip()
        q = str(p.get("quality") or "hd").lower().strip()
        if "4k" in q or "2160" in q:
            q = "4k"
        elif "1080" in q:
            q = "1080p"
        elif "720" in q:
            q = "720p"
        elif "480" in q:
            q = "480p"
        else:
            q = "hd"
        return f"movie:{norm}:{y}:{q}"


def _get_canonical_index() -> Dict[str, Dict[str, Any]]:
    """Builds or returns the cached O(1) canonical key -> newest record index."""
    global _canonical_index
    with _storage_lock:
        records = _load_records_raw()
        if _canonical_index is not None:
            return _canonical_index
        idx: Dict[str, Dict[str, Any]] = {}
        # Iterate oldest -> newest so newest record wins for each canonical key
        for r in records:
            r_parsed = r.get("parsed") or {}
            r_fn = r.get("original_filename") or r.get("file_name") or ""
            r_key = get_canonical_item_key(r_parsed, r_fn)
            if r_key and not r_key.startswith("movie:::") and not r_key.startswith("series::"):
                idx[r_key] = r
        _canonical_index = idx
        return _canonical_index


def find_library_duplicate(parsed: dict, file_name: str, new_size_bytes: int = 0) -> Optional[Dict[str, Any]]:
    """
    Checks if a media file already exists in the tracking ledger (O(1) cached lookup).
    Returns None if unique, or a dict describing the duplicate and whether the incoming
    file qualifies as an upgrade (e.g. >10MB larger / higher bitrate).
    """
    target_key = get_canonical_item_key(parsed, file_name)
    if not target_key or target_key.startswith("movie:::") or target_key.startswith("series::"):
        return None

    with _storage_lock:
        idx = _get_canonical_index()
        r = idx.get(target_key)
        if r is not None:
            r_parsed = r.get("parsed") or {}
            old_size = parse_size_bytes(r.get("file_size_str") or r_parsed.get("file_size"))
            # If new file is > 10MB larger, it qualifies as an upgrade
            is_upgrade = bool(new_size_bytes and (new_size_bytes > old_size + 10 * 1024 * 1024))
            return {
                "is_duplicate": True,
                "is_upgrade": is_upgrade,
                "existing_record": r,
                "old_message_id": r.get("message_id"),
                "old_file_name": r.get("file_name"),
                "old_size_str": r.get("file_size_str") or "",
            }

    return None


def replace_tracked_file(old_message_id: int, new_message_id: int, file_name: str, parsed: dict = None, file_size_str: str = None):
    """Replaces an existing duplicate record with the upgraded higher quality file."""
    from server.parser import build_golden_filename
    golden = (parsed and parsed.get("golden_name")) or (parsed and build_golden_filename(parsed, file_name)) or file_name
    category = (parsed and parsed.get("category")) or "movies"

    with _storage_lock:
        records = list(_load_records_raw())
        updated = False
        for r in records:
            if r.get("message_id") == old_message_id:
                r["message_id"] = new_message_id
                r["file_name"] = golden
                r["original_filename"] = file_name
                r["category"] = category
                r["parsed"] = parsed or {}
                r["file_size_str"] = file_size_str or ""
                r["created_at"] = int(time.time())
                updated = True
                break

        if not updated:
            records.append({
                "message_id": new_message_id,
                "file_name": golden,
                "original_filename": file_name,
                "category": category,
                "parsed": parsed or {},
                "file_size_str": file_size_str or "",
                "created_at": int(time.time()),
            })

        try:
            _save_records_atomic(records)
        except Exception as e:
            logger.error(f"Failed to save updated tracked media: {e}")


def deduplicate_entire_library() -> tuple:
    """
    Scans the entire tracking ledger and removes redundant duplicate entries,
    keeping the version with the highest quality / largest file size.
    Returns (removed_count, list_of_removed_message_ids).
    """
    from collections import defaultdict
    with _storage_lock:
        records = list(_load_records_raw())
        if not records:
            return 0, []

        groups = defaultdict(list)
        for r in records:
            p = r.get("parsed") or {}
            fn = r.get("original_filename") or r.get("file_name") or ""
            k = get_canonical_item_key(p, fn)
            groups[k].append(r)

        kept_records = []
        removed_mids = []

        for k, items in groups.items():
            if len(items) == 1 or not k or k.startswith("movie:::") or k.startswith("series::"):
                kept_records.extend(items)
                continue

            def item_score(it):
                size = parse_size_bytes(it.get("file_size_str") or (it.get("parsed") or {}).get("file_size"))
                created = it.get("created_at") or 0
                has_tmdb = 1 if (it.get("tmdb_id") or (it.get("parsed") or {}).get("tmdb_id")) else 0
                return (size, has_tmdb, created)

            sorted_items = sorted(items, key=item_score, reverse=True)
            winner = sorted_items[0]
            kept_records.append(winner)

            for loser in sorted_items[1:]:
                mid = loser.get("message_id")
                if mid:
                    removed_mids.append(mid)

        kept_records.sort(key=lambda x: x.get("message_id", 0))

        try:
            _save_records_atomic(kept_records)
        except Exception as e:
            logger.error(f"Failed to save deduplicated tracked media: {e}")

        return len(removed_mids), removed_mids


def record_indexed_file(message_id: int, file_name: str, parsed: dict = None, file_size_str: str = None):
    """Save forwarded message_id, filename, and parsed metadata to the tracking ledger."""
    from server.parser import build_golden_filename
    golden = (parsed and parsed.get("golden_name")) or (parsed and build_golden_filename(parsed, file_name)) or file_name
    category = (parsed and parsed.get("category")) or "movies"

    with _storage_lock:
        records = list(_load_records_raw())
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
            _save_records_atomic(records)
        except Exception as e:
            logger.error(f"Failed to save tracked media: {e}")


def get_tracked_files(limit: int = None) -> List[Dict[str, Any]]:
    """Retrieve tracked file records (newest first)."""
    with _storage_lock:
        records = list(reversed(_load_records_raw()))
        if limit:
            return records[:limit]
        return records


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
    try:
        with _storage_lock:
            records = _load_records_raw()
            id_set = set(message_ids)
            filtered = [r for r in records if r.get("message_id") not in id_set]
            _save_records_atomic(filtered)
    except Exception as e:
        logger.error(f"Failed to update tracked media ledger: {e}")


def update_tracked_category(message_ids: List[int], category: str):
    """Update category for message IDs in the local ledger."""
    try:
        with _storage_lock:
            records = list(_load_records_raw())
            id_set = set(message_ids)
            for r in records:
                if r.get("message_id") in id_set:
                    r["category"] = category
                    if "parsed" in r and isinstance(r["parsed"], dict):
                        r["parsed"]["category"] = category
            _save_records_atomic(records)
    except Exception as e:
        logger.error(f"Failed to update tracked media category: {e}")


def update_tracked_metadata(message_id: int, updates: dict):
    """Updates metadata (title, year, season, episode, is_series, category, tmdb_id) for a message ID in the local ledger.
    Supports bulk-updating all episodes in a series when apply_all_series is True."""
    try:
        from server.parser import build_golden_filename, safe_int
        with _storage_lock:
            records = list(_load_records_raw())

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

            _save_records_atomic(records)

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
    try:
        from server.parser import parse_filename, build_golden_filename
        with _storage_lock:
            records = list(_load_records_raw())

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
                _save_records_atomic(records)
                logger.info("Successfully healed tracked_media.json records on disk.")
    except Exception as e:
        logger.warning(f"Notice during heal_stored_series_ledger: {e}")

