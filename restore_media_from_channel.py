#!/usr/bin/env bash
"""
FilmHouse Stream Engine - Restore & Resync Ledger from Storage Channel
Fetches messages from the Telegram Bin Channel and restores any missing records
into data/tracked_media.json.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from bot.client import get_tg_client
from bot.storage import get_tracked_files, record_indexed_file, _ensure_storage
from server.parser import parse_filename
from server.stream_server import format_bytes, invalidate_media_cache

# The 93 message IDs from the recent removal
TARGET_IDS = [
    9238, 9237, 9112, 8877, 8876, 2892, 2891, 2890, 2889, 2888,
    2887, 2886, 2885, 2884, 2883, 2882, 2881, 2880, 2879, 2878,
    2877, 2876, 2875, 2874, 2873, 2872, 2871, 2870, 2869, 2868,
    2867, 2866, 2865, 2864, 2863, 2862, 2861, 2860, 2859, 2858,
    2857, 2856, 2855, 2854, 2853, 1793, 1792, 1791, 1790, 1789,
    1788, 1787, 1786, 1785, 1784, 1783, 1782, 1781, 1780, 1779,
    1778, 1777, 1776, 1775, 1774, 865, 695, 694, 693, 692,
    691, 690, 687, 686, 685, 684, 683, 682, 681, 680,
    679, 678, 677, 44, 43, 42, 41, 40, 39, 38,
    37, 36, 35
]


async def main():
    print("🔄 Restoring media records from Telegram storage channel...")
    client = get_tg_client()
    restored_count = 0

    try:
        await client.start()
        print(f"📡 Connected to Telegram. Fetching {len(TARGET_IDS)} messages from channel {config.BIN_CHANNEL_ID}...")

        # Fetch in chunks of 50
        for i in range(0, len(TARGET_IDS), 50):
            chunk = TARGET_IDS[i:i + 50]
            messages = await client.get_messages(config.BIN_CHANNEL_ID, chunk)
            for msg in messages:
                if not msg:
                    continue
                media = msg.video or msg.document or msg.audio or msg.animation
                if not media:
                    continue

                fn = getattr(media, "file_name", None) or f"media_{msg.id}"
                fsize = getattr(media, "file_size", 0)
                size_str = format_bytes(fsize) if fsize else ""

                parsed = parse_filename(fn)
                record_indexed_file(
                    message_id=msg.id,
                    file_name=fn,
                    parsed=parsed,
                    file_size_str=size_str
                )
                restored_count += 1
                title = parsed.get("title") or fn
                print(f"  ✅ Restored [ID {msg.id}] {title} ({fn})")

        invalidate_media_cache()
        print(f"\n🎉 Successfully restored {restored_count} media records to data/tracked_media.json!")

    except Exception as e:
        print(f"❌ Error during restore: {e}")
    finally:
        try:
            await client.stop()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
