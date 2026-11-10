import asyncio
import logging
import signal
from aiohttp import web
import config
from bot.client import get_tg_client
from bot.handlers import register_handlers
from bot.tunnel_sync import auto_sync_tunnel_loop
from server.stream_server import create_stream_app, prewarm_media_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("filmhouse.main")


async def main():
    logger.info("Initializing FilmHouse Stream Bot...")
    
    # 1. Validate configuration
    config.validate_config()
    logger.info(f"Loaded configuration. Port: {config.PORT}, Host: {config.HOST}")
    logger.info(f"Stream Base URL: {config.SERVER_URL}")

    # 2. Initialize Telegram Bot MTProto Client
    bot = get_tg_client()
    register_handlers(bot)

    logger.info("Starting Telegram MTProto bot client...")
    await bot.start()
    bot_info = await bot.get_me()
    logger.info(f"Bot connected successfully as @{bot_info.username} (ID: {bot_info.id})")

    # Register Telegram Bot Menu commands
    try:
        from hydrogram.types import BotCommand
        await bot.set_bot_commands([
            BotCommand("start", "Launch main dashboard"),
            BotCommand("help", "How to forward and stream"),
            BotCommand("status", "Server & stream health"),
            BotCommand("clear_bin", "Storage channel maintenance"),
            BotCommand("cancel", "Cancel current batch/task"),
        ])
        logger.info("Registered Telegram Bot Menu commands.")
    except Exception as e:
        logger.warning(f"Could not register bot commands: {e}")

    # 3. Initialize HTTP Streaming Web Server
    app = create_stream_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HOST, config.PORT)
    await site.start()
    logger.info(f"HTTP 206 Streaming Engine active on http://{config.HOST}:{config.PORT}")

    # Pre-warm media cache in background so initial WebApp loads in <1ms
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, prewarm_media_cache)

    # 4. Start Cloudflare Tunnel Auto-Sync watcher (self-healing URL updater)
    asyncio.create_task(auto_sync_tunnel_loop())

    # 5. Keep alive until signal received
    stop_event = asyncio.Event()

    def handle_stop():
        logger.info("Termination signal received. Shutting down...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_stop)
        except NotImplementedError:
            # Windows event loop doesn't support add_signal_handler
            pass

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Cleaning up connections...")
        await runner.cleanup()
        await bot.stop()
        logger.info("FilmHouse Stream Bot stopped gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process exited.")
