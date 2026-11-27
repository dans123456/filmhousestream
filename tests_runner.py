import sys
import time
import hmac
import hashlib
import json
import urllib.parse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import server.parser as parser_mod
from server.parser import parse_filename
from server.security import (
    generate_stream_token,
    verify_stream_token,
    verify_admin_access,
    validate_telegram_init_data,
    check_rate_limit,
    record_auth_failure,
    record_auth_success,
    is_ip_blocked
)
from server.cache import get_cached_chunk, store_cached_chunk, get_cache_stats
from server.stream_server import format_bytes, parse_range_header
from server.tmdb_auditor import get_auditor_canonical_key, format_episode_ranges, _is_placeholder_title
from bot.storage import record_indexed_file, get_tracked_files, remove_tracked_files, merge_tracked_items

def test_parser():
    print("[TEST] Running parser tests...")
    
    # Series with episode title
    t1 = parse_filename("The.Equalizer.S04E05.The.Mama.Who.Came.to.Dinner.1080p.mkv")
    assert t1["is_series"] == True, "Failed is_series check"
    assert t1["season"] == 4, f"Expected S4, got {t1['season']}"
    assert t1["episode"] == 5, f"Expected E5, got {t1['episode']}"
    assert "Mama" in (t1["episode_title"] or ""), f"Missing episode title: {t1}"
    assert t1["quality"] == "1080p", f"Expected 1080p, got {t1['quality']}"

    # Standard movie with year
    t2 = parse_filename("Oppenheimer.2023.IMAX.2160p.UHD.HDR.x265.mp4")
    assert t2["is_series"] == False, "Expected movie"
    assert t2["year"] == 2023, f"Expected year 2023, got {t2['year']}"
    assert t2["quality"] == "4K", f"Expected 4K, got {t2['quality']}"

    # Short series tag
    t3 = parse_filename("Shogun_1x01_Anjin_720p.mp4")
    assert t3["is_series"] == True
    assert t3["season"] == 1 and t3["episode"] == 1

    # Anime & bracket/symbol evasion & 3-digit episodes
    a1 = parse_filename("[E017] Black Clover [720p] [Dual].mkv")
    assert a1["is_series"] == True and a1["season"] == 1 and a1["episode"] == 17, f"Got {a1}"
    assert a1["title"] == "Black Clover" and a1["category"] == "anime", f"Got {a1}"

    a2 = parse_filename("[E170] Black Clover [720p] [Dual].mkv")
    assert a2["is_series"] == True and a2["season"] == 1 and a2["episode"] == 170, f"Got {a2}"
    assert a2["title"] == "Black Clover" and a2["category"] == "anime", f"Got {a2}"

    a3 = parse_filename("_S01_01_The_Ossan_Newbie_Adventurer_1080p_Sub_@Animes_Ocean.mkv")
    assert a3["is_series"] == True and a3["season"] == 1 and a3["episode"] == 1, f"Got {a3}"
    assert a3["title"] == "The Ossan Newbie Adventurer" and a3["category"] == "anime", f"Got {a3}"

    a4 = parse_filename("[S01-08] Ossan Newbie Adventurer [1080p] [Sub] @Animes_Ocean.mkv")
    assert a4["is_series"] == True and a4["season"] == 1 and a4["episode"] == 8, f"Got {a4}"
    assert a4["title"] == "The Ossan Newbie Adventurer" and a4["category"] == "anime", f"Got {a4}"

    a5 = parse_filename("10 - Undefeated Bahamut Chronicals.mkv")
    assert a5["is_series"] == True and a5["season"] == 1 and a5["episode"] == 10, f"Got {a5}"
    assert a5["title"] == "Undefeated Bahamut Chronicle" and a5["category"] == "anime", f"Got {a5}"

    a6 = parse_filename("๏ 01 God Eater Dual 1080p.mkv")
    assert a6["is_series"] == True and a6["season"] == 1 and a6["episode"] == 1, f"Got {a6}"
    assert a6["title"] == "God Eater" and a6["category"] == "anime", f"Got {a6}"

    a7 = parse_filename("๏ S2 01 Goblin Slayer Dual 1080p.mkv")
    assert a7["is_series"] == True and a7["season"] == 2 and a7["episode"] == 1, f"Got {a7}"
    assert a7["title"] == "Goblin Slayer" and a7["category"] == "anime", f"Got {a7}"

    a8 = parse_filename("@Entirelything. Classroom For Heroes [S01-€03] [1080p].mkv")
    assert a8["is_series"] == True and a8["season"] == 1 and a8["episode"] == 3, f"Got {a8}"
    assert a8["title"].lower() == "classroom for heroes" and a8["category"] == "anime", f"Got {a8}"

    # Movies protected against 'web' / numeric splits
    m1 = parse_filename("Madame.Web.2024.1080p.10bit.WEBRip.6CH.x265.HEVC-PSA.mkv")
    assert m1["is_series"] == False and m1["year"] == 2024 and m1["title"] == "Madame Web", f"Got {m1}"

    m2 = parse_filename("365.Days.2020.1080p.WEBRip.mp4")
    assert m2["is_series"] == False and m2["year"] == 2020 and m2["title"] == "365 Days", f"Got {m2}"

    print("  ✅ Parser tests passed!")

def test_security_tokens():
    print("[TEST] Running security token tests...")
    msg_id = 987654321
    token = generate_stream_token(msg_id)
    assert token, "Token generation returned empty"
    
    verified = verify_stream_token(token)
    assert verified == msg_id, f"Expected {msg_id}, got {verified}"

    # Tampered token
    tampered = token[:-2] + "xx"
    assert verify_stream_token(tampered) is None, "Tampered token should be rejected"

    # Garbage token
    assert verify_stream_token("invalid_token_string") is None

    print("  ✅ Security token tests passed!")

def test_cache():
    print("[TEST] Running RAM chunk cache tests...")
    test_id = 12345
    chunk_0 = b"A" * 1024
    chunk_1 = b"B" * 2048

    store_cached_chunk(test_id, 0, chunk_0)
    store_cached_chunk(test_id, 1, chunk_1)

    c0 = get_cached_chunk(test_id, 0)
    c1 = get_cached_chunk(test_id, 1)
    c2 = get_cached_chunk(test_id, 2)

    assert c0 == chunk_0, "Cache chunk 0 mismatch"
    assert c1 == chunk_1, "Cache chunk 1 mismatch"
    assert c2 is None, "Cache chunk 2 should be miss"

    stats = get_cache_stats()
    assert stats["cached_media_count"] >= 1, "Cache stats mismatch"
    print("  ✅ RAM cache tests passed!")

def test_range_parser():
    print("[TEST] Running HTTP 206 Range parser tests...")
    file_size = 1000000

    # Safari probe
    s, e = parse_range_header("bytes=0-1", file_size)
    assert s == 0 and e == 1, f"Expected (0, 1), got ({s}, {e})"

    # Normal range
    s, e = parse_range_header("bytes=1000-5000", file_size)
    assert s == 1000 and e == 5000

    # Prefix
    s, e = parse_range_header("bytes=500-", file_size)
    assert s == 500 and e == file_size - 1

    # Suffix
    s, e = parse_range_header("bytes=-500", file_size)
    assert s == file_size - 500 and e == file_size - 1

    # Invalid range
    assert parse_range_header("invalid", file_size) is None
    assert parse_range_header("bytes=2000-1000", file_size) is None

    print("  ✅ HTTP Range tests passed!")

def test_admin_auth():
    print("[TEST] Running Admin authorization tests...")
    class MockRequest:
        def __init__(self, headers=None, query=None, remote="127.0.0.1"):
            self.headers = headers or {}
            self.query = query or {}
            self.remote = remote

    # 1. Without auth
    req_unauth = MockRequest()
    assert verify_admin_access(req_unauth) == False, "Unauthenticated request should fail"

    # 2. With valid Admin Key header
    req_key = MockRequest(headers={"X-Admin-Key": config.ADMIN_SECRET})
    assert verify_admin_access(req_key) == True, "Valid admin key should pass"

    # 3. With valid query param
    req_query = MockRequest(query={"admin_key": config.ADMIN_SECRET})
    assert verify_admin_access(req_query) == True, "Valid query key should pass"

    # 4. With Bearer token
    req_bearer = MockRequest(headers={"Authorization": f"Bearer {config.ADMIN_SECRET}"})
    assert verify_admin_access(req_bearer) == True, "Valid bearer token should pass"

    # 5. Invalid key
    req_bad_key = MockRequest(headers={"X-Admin-Key": "wrong_password"})
    assert verify_admin_access(req_bad_key) == False, "Wrong key should fail"

    print("  ✅ Admin authorization tests passed!")

def test_telegram_init_data():
    print("[TEST] Running Telegram initData HMAC validation tests...")
    if not config.BOT_TOKEN or not config.ADMIN_IDS:
        print("  ⚠️ Skipped: BOT_TOKEN or ADMIN_IDS not set")
        return

    admin_id = config.ADMIN_IDS[0]
    auth_date = int(time.time())
    user_json = json.dumps({"id": admin_id, "first_name": "Admin"})

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF60gAAAAAN0XrSCx0f4n",
        "user": user_json
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    init_data_str = f"auth_date={auth_date}&query_id={params['query_id']}&user={urllib.parse.quote(user_json)}&hash={calc_hash}"

    val_res = validate_telegram_init_data(init_data_str)
    assert val_res == admin_id, f"Expected {admin_id}, got {val_res}"

    # Test non-admin ID
    params_fake = dict(params)
    fake_user_json = json.dumps({"id": 999999999, "first_name": "Hacker"})
    params_fake["user"] = fake_user_json
    data_check_fake = "\n".join(f"{k}={v}" for k, v in sorted(params_fake.items()))
    fake_hash = hmac.new(secret_key, data_check_fake.encode("utf-8"), hashlib.sha256).hexdigest()
    fake_init_data = f"auth_date={auth_date}&query_id={params['query_id']}&user={urllib.parse.quote(fake_user_json)}&hash={fake_hash}"

    val_fake = validate_telegram_init_data(fake_init_data)
    assert val_fake is None, "Non-admin ID should be rejected!"

    print("  ✅ Telegram initData HMAC validation tests passed!")


def test_merge_and_custom_rules():
    print("[TEST] Running folder merge & custom merge rules tests...")
    merges_file = parser_mod.CUSTOM_MERGES_FILE
    had_file = merges_file.exists()
    orig_content = merges_file.read_text(encoding="utf-8") if had_file else None
    test_mids = [99999901, 99999902]

    try:
        remove_tracked_files(test_mids)
        fn1 = "Split Anime Part A S01E01.mkv"
        fn2 = "Split Anime Part B 02 1080p.mkv"
        record_indexed_file(test_mids[0], fn1, parse_filename(fn1), "250 MB")
        record_indexed_file(test_mids[1], fn2, parse_filename(fn2), "260 MB")

        updated = merge_tracked_items(
            test_mids,
            target_title="Unified Test Anime",
            is_series=True,
            category="anime",
            remember_rule=True,
        )
        assert updated == 2, f"Expected 2 updated records, got {updated}"

        tracked = {r.get("message_id"): r for r in get_tracked_files() if r.get("message_id") in test_mids}
        assert len(tracked) == 2, f"Expected 2 tracked records, got {len(tracked)}"
        for mid, expected_ep in ((test_mids[0], 1), (test_mids[1], 2)):
            rec = tracked[mid]
            p = rec.get("parsed") or {}
            assert p.get("title") == "Unified Test Anime", f"Unexpected title: {p}"
            assert rec.get("title") == "Unified Test Anime"
            assert p.get("is_series") is True
            assert rec.get("category") == "anime" and p.get("category") == "anime"
            assert p.get("episode") == expected_ep, f"Expected ep {expected_ep}, got {p.get('episode')}"

        future_parsed = parse_filename("Split Anime Part B S01E05 1080p.mkv")
        assert future_parsed["title"] == "Unified Test Anime", f"Rule not applied: {future_parsed}"
        assert future_parsed["category"] == "anime", f"Category override not applied: {future_parsed}"
        assert future_parsed["episode"] == 5

        print("  ✅ Folder merge & custom rules tests passed!")
    finally:
        remove_tracked_files(test_mids)
        if had_file:
            merges_file.write_text(orig_content, encoding="utf-8")
        elif merges_file.exists():
            merges_file.unlink()
        parser_mod._custom_merges_cache = None
        parser_mod._custom_merges_mtime = -1.0


def test_auditor_keys_and_rules():
    print("[TEST] Running TMDB auditor canonical key & strict rules tests...")
    assert get_auditor_canonical_key("The End of the F***ing World") == "the_end_of_the_f_ing_world"
    assert get_auditor_canonical_key("Avengers Ultron Revolution") == "marvels_avengers_assemble"
    assert get_auditor_canonical_key("Avengers Secret Wars") == "marvels_avengers_assemble"
    assert get_auditor_canonical_key("The Ossan Newbie Adventurer") == "the_ossan_newbie_adventurer"
    assert get_auditor_canonical_key("The Vampire Diaries") == "the_vampire_diaries"
    assert get_auditor_canonical_key("The Fixies") == "the_fixies"
    assert get_auditor_canonical_key("Black Clover") == "black_clover"

    assert format_episode_ranges([1, 2, 3, 5, 7, 8, 9]) == "Ep 1–3, 5, 7–9"
    assert format_episode_ranges([32]) == "Ep 32"

    assert _is_placeholder_title("mp4") is True
    assert _is_placeholder_title("l") is True
    assert _is_placeholder_title("this is") is False
    assert _is_placeholder_title("24") is False

    # Verify "This Is the End" and "Avengers Ultron Revolution" parse cleanly
    tie = parse_filename("This.Is.The.End.2013.720p.mp4")
    assert tie["is_series"] is False and tie["year"] == 2013, f"Got {tie}"
    avr = parse_filename("Avengers.Ultron.Revolution.S03E01.720p.mkv")
    assert avr["is_series"] is True and avr["title"] == "Marvel's Avengers Assemble", f"Got {avr}"

    print("  ✅ TMDB auditor key & strict rules tests passed!")


if __name__ == "__main__":
    test_parser()
    test_security_tokens()
    test_cache()
    test_range_parser()
    test_admin_auth()
    test_telegram_init_data()
    test_merge_and_custom_rules()
    test_auditor_keys_and_rules()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! ZERO BUGS FOUND.")
