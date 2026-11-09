import os
import secrets
import hashlib
from pathlib import Path
try:
    from dotenv import load_dotenv
    # Load .env file from current directory
    BASE_DIR = Path(__file__).resolve().parent
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# 1. Telegram API Credentials
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# 2. Bin Storage Channel
BIN_CHANNEL_ID = int(os.getenv("BIN_CHANNEL_ID", "0"))

# 3. Web Server Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
SERVER_URL = os.getenv("SERVER_URL", f"http://localhost:{PORT}").rstrip("/")
BLOGGER_URL = os.getenv("BLOGGER_URL", "https://dans123456.github.io/filmhouse/player.html").rstrip("/")

# 4. Security & Protection
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)

ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_RAW.strip() == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [orig.strip() for orig in ALLOWED_ORIGINS_RAW.split(",") if orig.strip()]

# 5. Admin Authorization
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
if not ADMIN_SECRET:
    # Deterministic fallback based on SECRET_KEY if not explicitly specified
    ADMIN_SECRET = hashlib.sha256((SECRET_KEY + ":admin_secret").encode("utf-8")).hexdigest()[:24]


def validate_config():
    """Verify that required credentials have been configured."""
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not BIN_CHANNEL_ID:
        missing.append("BIN_CHANNEL_ID")
    
    if missing:
        raise ValueError(
            f"Missing required configuration values in .env: {', '.join(missing)}\n"
            f"Please copy .env.example to .env and fill in your credentials."
        )
