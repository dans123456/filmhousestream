import logging
from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from server.security import generate_stream_token
from server.parser import parse_filename
from server.stream_server import format_bytes
import config

logger = logging.getLogger("filmhouse.bot")


def is_authorized(user_id: int) -> bool:
    """Verifies whether the user is permitted to use the bot."""
    if not config.ADMIN_IDS:
        return True
    return user_id in config.ADMIN_IDS


def register_handlers(app: Client):
    """Registers all Telegram bot command and message handlers."""

    @app.on_message(filters.command(["start", "help"]) & filters.private)
    async def start_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            await message.reply_text("⛔ You are not authorized to use this bot.")
            return

        welcome_text = (
            "🎬 **Welcome to FilmHouse Stream Bot!**\n\n"
            "Forward any **Movie** or **TV Series episode** here, and I will instantly generate:\n"
            "• ⚡ Instant HTTP 206 Direct Stream URL\n"
            "• 🌐 Web Player Link (Seeking & Scrubbing supported)\n"
            "• 📺 Smart Season & Episode recognition\n\n"
            "Just forward your video file to get started!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 FilmHouse Web", url="https://filmhouse.com" if not config.SERVER_URL.startswith("http://localhost") else config.SERVER_URL)],
            [InlineKeyboardButton("⚙️ Server Status", callback_data="status_check")]
        ])
        await message.reply_text(welcome_text, reply_markup=keyboard)

    @app.on_callback_query(filters.regex("status_check"))
    async def status_callback(client: Client, query):
        await query.answer("⚡ Streaming server is active and online!", show_alert=True)

    @app.on_message((filters.video | filters.document) & filters.private)
    async def media_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            await message.reply_text("⛔ You are not authorized to use this bot.")
            return

        media = message.video or message.document
        if not media:
            return

        # Status update
        status_msg = await message.reply_text("⏳ *Indexing file to storage channel...*", quote=True)

        try:
            # 1. Forward media to private bin channel to get persistent message_id
            forwarded = await message.forward(config.BIN_CHANNEL_ID)
            message_id = forwarded.id

            # 2. Extract filename and size
            file_name = getattr(media, "file_name", None) or f"video_{message_id}.mp4"
            file_size = getattr(media, "file_size", 0)
            file_size_str = format_bytes(file_size)

            # 3. Parse filename for series vs movie
            parsed = parse_filename(file_name)
            token = generate_stream_token(message_id)

            watch_url = f"{config.SERVER_URL}/watch/{token}"
            stream_url = f"{config.SERVER_URL}/stream/{token}"

            # 4. Format Output
            if parsed["is_series"]:
                title = parsed["title"]
                season = parsed["season"] or 1
                episode = parsed["episode"] or 1
                quality_badge = f" • {parsed['quality']}" if parsed['quality'] else ""

                reply_text = (
                    f"📺 **{title} — Season {season}**\n\n"
                    f"• **Episode {episode}**{quality_badge}\n"
                    f"📁 `{file_name}` ({file_size_str})\n\n"
                    f"🔗 **Stream URL:**\n`{stream_url}`\n\n"
                    f"🌐 **Web Player:**\n{watch_url}"
                )
            else:
                title = parsed["title"]
                year_str = f" ({parsed['year']})" if parsed['year'] else ""
                qual_str = f" [{parsed['quality']}]" if parsed['quality'] else ""

                reply_text = (
                    f"🎬 **{title}{year_str}{qual_str}**\n\n"
                    f"📁 `{file_name}` ({file_size_str})\n\n"
                    f"🔗 **Direct Stream URL:**\n`{stream_url}`\n\n"
                    f"🌐 **Web Player:**\n{watch_url}"
                )

            buttons = [
                [InlineKeyboardButton("▶️ Watch in Browser", url=watch_url)],
                [InlineKeyboardButton("⬇️ Direct Stream Link", url=stream_url)],
            ]

            await status_msg.edit_text(
                reply_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )

        except Exception as e:
            logger.error(f"Error handling media: {e}", exc_info=True)
            await status_msg.edit_text(
                f"❌ **Error indexing file:** `{str(e)}`\n\n"
                f"Make sure the bot has been added as an Administrator to your `BIN_CHANNEL_ID` ({config.BIN_CHANNEL_ID})."
            )
