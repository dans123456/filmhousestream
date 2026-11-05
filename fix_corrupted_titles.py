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
        if not file_name:
            continue

        stored_parsed = item.get("parsed") or {}
        old_title = stored_parsed.get("title", "")
        old_ep_title = stored_parsed.get("episode_title", "")

        # Re-parse using the new parser
        new_parsed = parse_filename(file_name)

        # Check if new parse changes title, is_series, season, episode, or cleaned episode_title
        diff_title = (new_parsed.get("title") != old_title)
        diff_series = (new_parsed.get("is_series") != stored_parsed.get("is_series"))
        diff_ep = (new_parsed.get("episode_title") != old_ep_title)
        diff_season = (new_parsed.get("season") != stored_parsed.get("season"))

        if diff_title or diff_series or diff_ep or diff_season or not stored_parsed:
            item["parsed"] = new_parsed
            fixed_count += 1
            if diff_series:
                print(f"[RECLASSIFIED SERIES] ID {item.get('message_id')}: '{file_name}' -> Series: {new_parsed['title']} S{new_parsed.get('season')}E{new_parsed.get('episode')}")
            elif diff_title:
                print(f"[CLEANED TITLE] ID {item.get('message_id')}: '{old_title}' -> '{new_parsed['title']}'")
            elif diff_ep:
                print(f"[CLEANED EP TITLE] ID {item.get('message_id')}: '{old_ep_title}' -> '{new_parsed.get('episode_title')}'")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nScan complete! Repaired {fixed_count} out of {total_count} tracked items.")
    print("Restart your streaming bot (pm2 restart filmhouse-stream-bot) to load the clean library!")


if __name__ == "__main__":
    fix_database()

