#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Total records: {len(records)}")
    counts = Counter(r.get("message_id") for r in records if r.get("message_id"))
    dups = {mid: c for mid, c in counts.items() if c > 1}
    print(f"Total duplicate message_ids: {len(dups)}")
    for mid, c in list(dups.items())[:20]:
        print(f"  ID {mid}: appears {c} times")

if __name__ == "__main__":
    main()
