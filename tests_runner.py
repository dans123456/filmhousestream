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
from bot.storage import record_indexed_file, get_tracked_files, remove_tracked_files

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

if __name__ == "__main__":
    test_parser()
    test_security_tokens()
    test_cache()
    test_range_parser()
    test_admin_auth()
    test_telegram_init_data()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! ZERO BUGS FOUND.")
