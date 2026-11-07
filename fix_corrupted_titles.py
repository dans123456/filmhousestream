#!/usr/bin/env python3
"""
FilmHouse Stream Engine - Database Metadata Repair Utility
Fixes corrupted titles (e.g., 'Episode 1', 'Episode 2', '2ch - Fi')
in data/tracked_media.json using the upgraded filename parser.
"""

import json
import shutil
import re
from pathlib import Path
from server.parser import parse_filename

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"
BACKUP_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json.bak"


def build_golden_filename(parsed: dict, original_filename: str) -> str:
    """Builds the pure Golden Dot standard filename for movies and series."""
    ext_match = re.search(r"\.([a-zA-Z0-9]{2,4})$", original_filename)
    ext = f".{ext_match.group(1).lower()}" if ext_match else ".mkv"

    clean_title = re.sub(r"[^\w\s\-]", "", parsed.get("title", "Unknown Media")).strip()
    dots_title = ".".join(clean_title.split())

    if parsed.get("is_series"):
        s_num = parsed.get("season") or 1
        e_num = parsed.get("episode") or 1
        s_tag = f"S{s_num:02d}E{e_num:02d}"
        q_tag = f".{parsed['quality']}" if parsed.get("quality") else ""
        return f"{dots_title}.{s_tag}{q_tag}{ext}"
    else:
        y_tag = f".{parsed['year']}" if parsed.get("year") else ""
        q_tag = f".{parsed['quality']}" if parsed.get("quality") else ""
        return f"{dots_title}{y_tag}{q_tag}{ext}"


def fix_database():
    if not DATA_FILE.exists():
        print(f"No tracked media file found at {DATA_FILE}. Nothing to fix.")
        return

    # Create safety backup
    shutil.copy2(DATA_FILE, BACKUP_FILE)
    print(f"Created safety backup at {BACKUP_FILE}")

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
    except Exception as e:
        print(f"Error loading database: {e}")
        return

    if not isinstance(records, list):
        print("Database format unrecognized (not a list).")
        return

    fixed_count = 0
    total_count = len(records)

    for item in records:
        file_name = item.get("file_name", "")
        orig_fn = item.get("original_filename") or file_name
        if not orig_fn:
            continue

        stored_parsed = item.get("parsed") or {}
        old_title = stored_parsed.get("title", "")
        old_ep_title = stored_parsed.get("episode_title", "")

        # Re-parse using the new parser on original filename
        new_parsed = parse_filename(orig_fn)

        # Build pure Golden Standard filename
        golden_filename = build_golden_filename(new_parsed, orig_fn)
        new_parsed["golden_name"] = golden_filename

        # Preserve original filename for audit
        if "original_filename" not in item:
            item["original_filename"] = orig_fn

        # Update to Golden standard
        item["file_name"] = golden_filename
        item["parsed"] = new_parsed
        item["category"] = new_parsed.get("category", "movies" if not new_parsed.get("is_series") else "series")
        fixed_count += 1

        print(f"[GOLDEN CONVERT] ID {item.get('message_id')}:")
        print(f"   OLD: {orig_fn}")
        print(f"   NEW: {golden_filename}\n")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nScan complete! Converted all {fixed_count} items to the Golden Standard Format.")
    print("Restart your streaming bot (pm2 restart filmhouse-stream-bot) to load the clean library!")


if __name__ == "__main__":
    fix_database()

