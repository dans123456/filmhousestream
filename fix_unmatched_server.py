#!/usr/bin/env python3
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracked_media.json"

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Search for items where parsed clean title or original filename is bare S01E or Kdg
    exact_unmatched = []
    for r in records:
        orig = str(r.get("original_filename") or "").strip()
        curr = str(r.get("file_name") or "").strip()
        parsed = r.get("parsed") or {}
        p_title = str(parsed.get("title") or "").strip()
        p_clean = str(parsed.get("clean_name") or "").strip()

        # Check for bare .S01E
        if orig.startswith(".S01E") or orig.startswith(".s01e") or orig in [".S01E11.mkv", ".S01E12.mkv", ".S01E13.mkv", ".S01E15.mkv", ".S01E16.mkv", ".S01E17.mkv", ".S01E18.mkv", ".S01E19.mkv", ".S01E20.mkv"]:
            exact_unmatched.append(("dot_s01e", r))
        elif "kdg" in orig.lower() or "kdg" in curr.lower():
            exact_unmatched.append(("kdg", r))
        elif "episode.15.s01e15" in orig.lower() or "episode.15.s01e15" in curr.lower() or orig == "Episode 15.FilmHouse..mkv":
            exact_unmatched.append(("ep15", r))
        elif p_title in ["S01E11", "S01E12", "S01E13", "S01E15", "S01E16", "S01E17", "S01E18", "S01E19", "S01E20"]:
            exact_unmatched.append(("bare_title", r))

    print(f"Total matching exact unmatched targets: {len(exact_unmatched)}")
    for tag, r in exact_unmatched:
        mid = r.get("message_id")
        orig = r.get("original_filename")
        curr = r.get("file_name")
        p_title = (r.get("parsed") or {}).get("title")
        print(f"  [{tag}] ID {mid} | orig: '{orig}' | curr: '{curr}' | title: '{p_title}'")

if __name__ == "__main__":
    main()
