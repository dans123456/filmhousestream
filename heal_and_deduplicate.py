#!/usr/bin/env python3
"""
FilmHouse Stream Engine - Full Server Ledger Healing & Deduplication Script
"""

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"
BACKUP_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json.before_heal.bak"


def heal():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Loaded {len(records)} records from {DATA_FILE.name}.")

    # Make safety backup
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Created safety backup at {BACKUP_FILE.name}.")

    # 1. Deduplicate by message_id (keep first/newest)
    seen_ids = set()
    deduped = []
    for r in records:
        mid = r.get("message_id")
        if not mid or mid not in seen_ids:
            if mid:
                seen_ids.add(mid)
            deduped.append(r)

    print(f"After deduplicating: {len(deduped)} unique records (removed {len(records) - len(deduped)} duplicates).")

    # 2. Heal specific known records
    kdg_healed = 0
    beast_healed = 0

    for r in deduped:
        orig = str(r.get("original_filename") or "")
        curr = str(r.get("file_name") or "")
        parsed = r.get("parsed") or {}

        # Heal Kdg -> It's Okay to Not Be Okay
        if "kdg" in orig.lower() or "kdg" in curr.lower():
            # Extract episode number
            ep_m = re.search(r"[eE](\d{1,2})", orig) or re.search(r"[eE](\d{1,2})", curr)
            ep_num = int(ep_m.group(1)) if ep_m else 1
            golden = f"Its.Okay.To.Not.Be.Okay.S01E{ep_num:02d}.720p.mp4"
            r["file_name"] = golden
            r["category"] = "k-drama"
            parsed["title"] = "It's Okay to Not Be Okay"
            parsed["clean_name"] = f"It's Okay to Not Be Okay S01E{ep_num:02d} (720p)"
            parsed["golden_name"] = golden
            parsed["is_series"] = True
            parsed["season"] = 1
            parsed["episode"] = ep_num
            parsed["category"] = "k-drama"
            r["parsed"] = parsed
            kdg_healed += 1

        # Heal Beast Of No Nation -> Beasts Of No Nation
        elif "beast.of.no.nation" in orig.lower() or "beast.of.no.nation" in curr.lower():
            golden = "Beasts.Of.No.Nation.2015.720p.mp4"
            r["file_name"] = golden
            parsed["title"] = "Beasts of No Nation"
            parsed["clean_name"] = "Beasts of No Nation (2015)"
            parsed["golden_name"] = golden
            r["parsed"] = parsed
            beast_healed += 1

    print(f"Healed {kdg_healed} 'Kdg' episodes -> 'It's Okay to Not Be Okay'.")
    print(f"Healed {beast_healed} 'Beast of No Nation' -> 'Beasts of No Nation'.")

    # 3. Save back to disk
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(deduped)} healed records to {DATA_FILE.name} successfully!\n")


if __name__ == "__main__":
    heal()
