from __future__ import annotations
import hmac
import hashlib
import base64
import time
import json
import logging
import urllib.parse
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from aiohttp import web
import config

logger = logging.getLogger("filmhouse.security")

# Delimiter used in the token payload
DELIMITER = ":"

# In-memory security rate limiting and blocklist
# ip -> list of request timestamps
_request_records: dict[str, list[float]] = {}
# ip -> {"failed_count": int, "blocked_until": float}
_failed_auth_records: dict[str, dict] = {}


def generate_stream_token(message_id: int) -> str:
    """
    Generates a secure, URL-safe signed token encoding the message_id.
    Format: base64(message_id:hmac_signature)
    """
    msg_str = str(message_id)
    signature = hmac.new(
        config.SECRET_KEY.encode("utf-8"),
        msg_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()[:16]  # 16-char truncated hex signature

    raw_payload = f"{msg_str}{DELIMITER}{signature}"
    return base64.urlsafe_b64encode(raw_payload.encode("utf-8")).decode("utf-8").rstrip("=")


def verify_stream_token(token: str) -> Optional[int]:
    """
    Decodes and cryptographically verifies the token.
    Returns the integer message_id if valid, or None if invalid or tampered with.
    """
    try:
        # Add back URL-safe base64 padding if needed
        padding = 4 - (len(token) % 4)
        if padding < 4:
            token += "=" * padding

        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        if DELIMITER not in decoded:
            return None

        msg_str, signature = decoded.split(DELIMITER, 1)
        expected_sig = hmac.new(
            config.SECRET_KEY.encode("utf-8"),
            msg_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:16]

        if not hmac.compare_digest(signature, expected_sig):
            return None

        return int(msg_str)
    except Exception:
        return None


def is_origin_allowed(request: web.Request) -> bool:
    """
    Hotlink protection: checks Referer and Origin headers against ALLOWED_ORIGINS.
    """
    if "*" in config.ALLOWED_ORIGINS:
        return True

    referer = request.headers.get("Referer", "")
    origin = request.headers.get("Origin", "")

    # Direct browser URL visits or mobile apps without referer
    if not referer and not origin:
        return True

    for allowed in config.ALLOWED_ORIGINS:
        if origin and allowed.lower() in origin.lower():
            return True
        if referer and allowed.lower() in referer.lower():
            return True

    return False


def get_client_ip(request: web.Request) -> str:
    """Extracts client IP considering Cloudflare and proxy headers."""
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote
        or "127.0.0.1"
    )


def is_ip_blocked(ip: str) -> bool:
    """Checks if IP is temporarily blocked due to repeated authentication failures."""
    record = _failed_auth_records.get(ip)
    if not record:
        return False
    if time.time() < record.get("blocked_until", 0):
        return True
    return False


def record_auth_failure(ip: str):
    """Tracks failed authentication and blocks IP if threshold exceeded."""
    now = time.time()
    record = _failed_auth_records.get(ip, {"failed_count": 0, "blocked_until": 0})
    record["failed_count"] += 1
    if record["failed_count"] >= 5:
        # Block for 15 minutes after 5 consecutive failures
        record["blocked_until"] = now + 900
        logger.warning(f"SECURITY: Blocked IP {ip} for 15 minutes after 5 failed admin attempts.")
    _failed_auth_records[ip] = record


def record_auth_success(ip: str):
    """Resets failed count upon successful authentication."""
    if ip in _failed_auth_records:
        _failed_auth_records.pop(ip, None)


def check_rate_limit(request: web.Request, max_requests: int = 60, window_sec: int = 60) -> bool:
    """
    Returns True if request is within rate limit, False if exceeded.
    """
    ip = get_client_ip(request)
    now = time.time()

    if is_ip_blocked(ip):
        return False

    timestamps = _request_records.get(ip, [])
    # Filter out timestamps older than window
    timestamps = [t for t in timestamps if now - t < window_sec]
    if len(timestamps) >= max_requests:
        return False

    timestamps.append(now)
    _request_records[ip] = timestamps
    return True


def validate_telegram_init_data(init_data_raw: str, max_age_seconds: int = 86400) -> Optional[int]:
    """
    Validates Telegram WebApp initData string using HMAC-SHA256 per Telegram specification.
    Returns the admin's Telegram user_id if valid and in ADMIN_IDS, else None.
    """
    if not init_data_raw or not config.BOT_TOKEN:
        return None

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        hash_val = parsed_data.pop("hash", None)
        if not hash_val:
            return None

        # Check auth_date for replay attack protection
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > max_age_seconds:
            logger.warning("Telegram initData expired (auth_date too old).")
            return None

        # Sort keys alphabetically and format as "key=val\n"
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # Secret key = HMAC_SHA256(key="WebAppData", msg=bot_token)
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()

        # Calculated hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, hash_val):
            logger.warning("Telegram initData signature mismatch!")
            return None

        user_str = parsed_data.get("user")
        if not user_str:
            return None

        user_obj = json.loads(user_str)
        user_id = user_obj.get("id")

        if user_id and int(user_id) in config.ADMIN_IDS:
            return int(user_id)

        logger.warning(f"Unauthorized Telegram user {user_id} attempted WebApp access.")
        return None
    except Exception as e:
        logger.error(f"Error validating Telegram initData: {e}")
        return None


def verify_admin_access(request: web.Request) -> bool:
    """
    Strictly verifies whether an incoming HTTP request is authenticated by an Admin.
    Accepts:
    1. Valid Telegram WebApp initData in 'X-Telegram-Init-Data' header or '?tgWebAppData='
    2. Valid Admin Secret Passcode in 'X-Admin-Key', 'Authorization: Bearer <key>', or '?admin_key='
    """
    ip = get_client_ip(request)

    if is_ip_blocked(ip):
        logger.warning(f"SECURITY: Blocked IP {ip} attempted access.")
        return False

    # 1. Check Telegram WebApp initData
    init_data = request.headers.get("X-Telegram-Init-Data") or request.query.get("tgWebAppData")
    if init_data:
        admin_id = validate_telegram_init_data(init_data)
        if admin_id:
            record_auth_success(ip)
            return True

    # 2. Check Admin Passcode / Key
    admin_key = (
        request.headers.get("X-Admin-Key")
        or request.query.get("admin_key")
        or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    )
    if admin_key and config.ADMIN_SECRET:
        if hmac.compare_digest(admin_key, config.ADMIN_SECRET):
            record_auth_success(ip)
            return True

    # Auth failed
    record_auth_failure(ip)
    logger.warning(f"SECURITY: Failed admin authentication attempt from IP {ip}")
    return False

