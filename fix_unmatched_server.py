#!/usr/bin/env python3
import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Total records: {len(records)}")

    # 1. Search for Kdg
    kdg_records = []
    for r in records:
        fn = str(r.get("original_filename") or r.get("file_name") or "")
        if fn.lower().startswith("kdg."):
            kdg_records.append(r)
    print(f"\nKdg records: {len(kdg_records)}")
    for r in kdg_records:
        print(f"  ID {r.get('message_id')}: orig='{r.get('original_filename')}' curr='{r.get('file_name')}'")

    # 2. Search for any file whose name literally contains '.S01E' or starts with '.'
    dot_files = []
    for r in records:
        orig = str(r.get("original_filename") or "")
        curr = str(r.get("file_name") or "")
        if orig.startswith(".S01E") or curr.startswith(".S01E") or ".s01e" in orig.lower() or ".s01e" in curr.lower():
            # Filter out known valid series
            combined = (orig + " " + curr).lower()
            if not any(k in combined for k in ["penguins", "zane", "swat", "zoey", "victorious", "school", "julien", "ruthless", "blacklist"]):
                dot_files.append(r)
    print(f"\nNameless / Dot files found: {len(dot_files)}")
    for r in dot_files:
        print(f"  ID {r.get('message_id')}: orig='{r.get('original_filename')}' curr='{r.get('file_name')}'")

if __name__ == "__main__":
    main()
