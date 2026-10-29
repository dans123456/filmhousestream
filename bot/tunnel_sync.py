import os
import re
import asyncio
import logging
import urllib.request
import json
from pathlib import Path
import config

logger = logging.getLogger("filmhouse.tunnel_sync")

TUNNEL_REGEX = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def find_latest_tunnel_url() -> str | None:
    """Scans potential tunnel.log locations for the most recent trycloudflare URL."""
    candidates = [
        Path(config.BASE_DIR) / "tunnel.log",
        Path("/home/ubuntu/filmhouse-stream-bot/tunnel.log"),
        Path("/home/ubuntu/filmhousestream/tunnel.log"),
        Path(config.BASE_DIR).parent / "tunnel.log",
    ]

    for p in candidates:
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                matches = TUNNEL_REGEX.findall(content)
                if matches:
                    return matches[-1].rstrip("/")
            except Exception as e:
                logger.debug(f"Could not read {p}: {e}")
    return None


def update_env_server_url(new_url: str):
    """Safely updates SERVER_URL in the .env file if it exists."""
    env_path = Path(config.BASE_DIR) / ".env"
    if not env_path.exists():
        return

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("SERVER_URL="):
                new_lines.append(f"SERVER_URL={new_url}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"SERVER_URL={new_url}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.info(f"Updated .env with SERVER_URL={new_url}")
    except Exception as e:
        logger.error(f"Failed to update .env: {e}")


def update_telegram_menu_button(library_url: str) -> bool:
    """Updates the bot's Menu Button inside Telegram to open the WebApp directly."""
    if not config.BOT_TOKEN:
        return False

    api_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton"
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "📱 Open Library",
            "web_app": {
                "url": library_url
            }
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            if res_json.get("ok"):
                logger.info(f"✅ Telegram Chat Menu Button updated to: {library_url}")
                return True
            else:
                logger.warning(f"Telegram setChatMenuButton responded: {res_json}")
    except Exception as e:
        logger.warning(f"Could not update Telegram Menu Button via API: {e}")
    return False


async def auto_sync_tunnel_loop():
    """
    Background worker that continuously watches tunnel.log for new Cloudflare URLs,
    synchronizing config.SERVER_URL, .env, and the Telegram WebApp Menu Button.
    """
    logger.info("Starting Cloudflare Tunnel Auto-Sync watcher...")

    while True:
        try:
            latest_url = find_latest_tunnel_url()
            if latest_url and latest_url != config.SERVER_URL:
                logger.info(f"Detected new Cloudflare Tunnel URL: {latest_url} (was: {config.SERVER_URL})")
                config.SERVER_URL = latest_url
                update_env_server_url(latest_url)
                update_telegram_menu_button(f"{latest_url}/library")
        except Exception as e:
            logger.error(f"Error in tunnel sync loop: {e}")

        await asyncio.sleep(20)
