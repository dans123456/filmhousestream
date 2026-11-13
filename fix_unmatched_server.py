#!/usr/bin/env python3
"""
FilmHouse Stream Engine - Diagnose & Fix Unmatched Items Directly
"""

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"

def main():
    if not DATA_FILE.exists():
        print(f"Error: {DATA_FILE} does not exist!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"Total records in tracked_media.json: {len(records)}")

    # 1. Search for .S01E files
    dot_s01e = []
    # 2. Search for Kdg files
    kdg_files = []
    # 3. Search for Episode 15 files
    ep15_files = []
    # 4. Search for Beast Of No Nation
    beast_files = []
    # 5. Search for any other nameless or bare episode files
    other_bare = []

    for r in records:
        fn = str(r.get("original_filename") or r.get("file_name") or "")
        title = str(r.get("title") or (r.get("parsed") or {}).get("title") or "")
        fn_lower = fn.lower()

        if "beast.of.no.nation" in fn_lower or "beasts.of.no.nation" in fn_lower or fn_lower.startswith("beast"):
            beast_files.append(r)
        elif fn_lower.startswith("kdg.") or "kdg.s01" in fn_lower:
            kdg_files.append(r)
        elif "episode.15.s01e15" in fn_lower or (fn_lower.startswith("episode") and "15" in fn_lower):
            ep15_files.append(r)
        elif fn.startswith(".S01E") or fn.startswith(".s01e") or re.match(r"^\.?s\d{1,2}e\d{1,3}\.", fn, re.I):
            dot_s01e.append(r)
        elif re.match(r"^\.?[sS]\d{1,2}[eE]\d{1,3}\b", fn):
            other_bare.append(r)

    print(f"\n1. Beast Of No Nation: {len(beast_files)} files")
    for r in beast_files:
        print(f"   ID {r.get('message_id')}: {r.get('original_filename')} -> current file_name: {r.get('file_name')}")

    print(f"\n2. Kdg files: {len(kdg_files)} files")
    for r in kdg_files:
        print(f"   ID {r.get('message_id')}: {r.get('original_filename')} -> current file_name: {r.get('file_name')}")

    print(f"\n3. Episode 15 files: {len(ep15_files)} files")
    for r in ep15_files:
        print(f"   ID {r.get('message_id')}: {r.get('original_filename')} -> current file_name: {r.get('file_name')}")

    print(f"\n4. Nameless .S01E files: {len(dot_s01e)} files")
    for r in dot_s01e:
        print(f"   ID {r.get('message_id')}: {r.get('original_filename')} -> current file_name: {r.get('file_name')}")

    print(f"\n5. Other bare files: {len(other_bare)} files")
    for r in other_bare[:10]:
        print(f"   ID {r.get('message_id')}: {r.get('original_filename')} -> current file_name: {r.get('file_name')}")


if __name__ == "__main__":
    main()
