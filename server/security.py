from __future__ import annotations
import hmac
import hashlib
import base64
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from aiohttp import web
import config

# Delimiter used in the token payload
DELIMITER = ":"


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
