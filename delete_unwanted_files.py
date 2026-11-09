#!/usr/bin/env python3
"""
FilmHouse Stream Engine - Bulk File Deletion Utility
Deletes unwanted files from the Telegram Storage Channel and removes them
from the local tracking ledger (data/tracked_media.json).

Usage:
  python3 delete_unwanted_files.py          # Deletes the 16 educational short files
  python3 delete_unwanted_files.py -y       # Automatically confirm without prompting
  python3 delete_unwanted_files.py "keyword" # Delete files matching custom keyword
"""

import sys
import json
import asyncio
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from bot.client import get_tg_client
from bot.storage import get_tracked_files, remove_tracked_files

DEFAULT_TARGETS = [
    "different.kinds.of.robots",
    "different.uses.for.sensors",
    "how.does.a.drain.trap.work",
    "how.does.a.microphone.work",
    "how.does.a.mobile.phone.work",
    "how.does.a.motion.sensor.work",
    "how.does.a.remote.work",
    "how.does.a.vacuum.work",
    "how.does.an.alarm.clock.work",
    "how.does.a.keycard.work",
    "how.does.a.lever.work",
    "our.world.without.friction",
    "what.cant.you.put.in.a.microwave",
    "hockeys.our.game",
    "my.smart.phone",
    "telephone.is.ringing",
]


def normalize_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


async def main():
    args = sys.argv[1:]
    auto_confirm = "-y" in args or "--yes" in args
    custom_keywords = [a for a in args if not a.startswith("-")]

    records = get_tracked_files()
    if not records:
        print("⚠️ No tracked media found in data/tracked_media.json.")
        return

    matched_records = []
    
    if custom_keywords:
        print(f"🔍 Searching for files matching: {custom_keywords}")
        for r in records:
            fn = r.get("original_filename") or r.get("file_name") or ""
            fn_norm = normalize_name(fn)
            if any(normalize_name(kw) in fn_norm for kw in custom_keywords):
                matched_records.append(r)
    else:
        print("🔍 Searching for the 16 educational short files...")
        target_norms = [normalize_name(t) for t in DEFAULT_TARGETS]
        for r in records:
            fn = r.get("original_filename") or r.get("file_name") or ""
            fn_norm = normalize_name(fn)
            if any(t in fn_norm for t in target_norms):
                matched_records.append(r)

    if not matched_records:
        print("✅ None of the targeted files were found in the database. They may already be deleted.")
        return

    print(f"\nFound {len(matched_records)} files to delete:")
    message_ids = []
    for i, r in enumerate(matched_records, 1):
        mid = r.get("message_id")
        fn = r.get("original_filename") or r.get("file_name")
        print(f"  {i}. [ID {mid}] {fn}")
        if mid:
            message_ids.append(int(mid))

    if not auto_confirm:
        confirm = input(f"\nAre you sure you want to delete these {len(message_ids)} files permanently? (y/N): ").strip().lower()
        if confirm != "y":
            print("❌ Deletion aborted.")
            return

    # Delete from Telegram channel
    print(f"\n📡 Connecting to Telegram to delete messages from channel {config.BIN_CHANNEL_ID}...")
    client = get_tg_client()
    try:
        await client.start()
        for i in range(0, len(message_ids), 50):
            chunk = message_ids[i:i + 50]
            try:
                await client.delete_messages(config.BIN_CHANNEL_ID, chunk)
                print(f"  🗑️ Deleted batch of {len(chunk)} messages from Telegram.")
            except Exception as e:
                print(f"  ⚠️ Telegram deletion notice: {e}")
    except Exception as e:
        print(f"  ⚠️ Could not connect to Telegram client: {e}")
    finally:
        try:
            await client.stop()
        except Exception:
            pass

    # Remove from local ledger
    print("💾 Removing entries from local tracked_media ledger...")
    remove_tracked_files(message_ids)
    print(f"✨ Done! Successfully deleted {len(message_ids)} files.\n")


if __name__ == "__main__":
    asyncio.run(main())
