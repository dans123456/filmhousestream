import asyncio
import logging
import urllib.parse
from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from server.security import generate_stream_token
from server.parser import parse_filename
from server.stream_server import format_bytes
import config

logger = logging.getLogger("filmhouse.bot")

# In-memory batch buffers: user_id -> {"items": [...], "task": asyncio.Task, "status_msg": Message}
_batch_buffers: dict[int, dict] = {}


def is_authorized(user_id: int) -> bool:
    """Verifies whether the user is permitted to use the bot."""
    if not config.ADMIN_IDS:
        return True
    return user_id in config.ADMIN_IDS


def build_blogspot_url(stream_url: str, title: str) -> str:
    """Builds the direct Blogspot player URL with Monetag ads."""
    encoded_stream = urllib.parse.quote(stream_url, safe="")
    encoded_title = urllib.parse.quote(title, safe="")
    return f"{config.BLOGGER_URL}/?watch={encoded_stream}&title={encoded_title}"


async def flush_batch(client: Client, user_id: int):
    """
    Called after debounce delay to send the finalized batch summary of all forwarded episodes.
    """
    buffer_data = _batch_buffers.pop(user_id, None)
    if not buffer_data:
        return

    items = buffer_data["items"]
    status_msg: Message = buffer_data["status_msg"]

    if not items:
        return

    # If only 1 file was forwarded, format as a single detailed card
    if len(items) == 1:
        item = items[0]
        parsed = item["parsed"]
        clean_name = parsed["clean_name"]
        stream_url = item["stream_url"]
        token = item["token"]
        file_name = item["file_name"]
        file_size_str = item["file_size_str"]
        blogger_url = build_blogspot_url(stream_url, parsed["title"])

        if parsed["is_series"]:
            title = parsed["title"]
            season = parsed["season"] or 1
            episode = parsed["episode"] or 1
            quality_badge = f" • {parsed['quality']}" if parsed['quality'] else ""

            text = (
                f"📺 **{title} — Season {season}**\n\n"
                f"• **Episode {episode}**{quality_badge}\n"
                f"📁 `{file_name}` ({file_size_str})\n\n"
                f"🔗 **Stream URL (FilmHouse):**\n`{stream_url}`\n\n"
                f"🔑 **Token:**\n`{token}`\n\n"
                f"🍿 **Blogspot Player (Monetag Ads):**\n{blogger_url}"
            )
        else:
            title = parsed["title"]
            year_str = f" ({parsed['year']})" if parsed['year'] else ""
            qual_str = f" [{parsed['quality']}]" if parsed['quality'] else ""

            text = (
                f"🎬 **{title}{year_str}{qual_str}**\n\n"
                f"📁 `{file_name}` ({file_size_str})\n\n"
                f"🔗 **Stream URL (FilmHouse):**\n`{stream_url}`\n\n"
                f"🔑 **Token:**\n`{token}`\n\n"
                f"🍿 **Blogspot Player (Monetag Ads):**\n{blogger_url}"
            )

        buttons = [
            [InlineKeyboardButton("🍿 Play on Blogspot", url=blogger_url)],
            [InlineKeyboardButton("⬇️ Direct Stream Link", url=stream_url)],
        ]
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        return

    # Multiple files forwarded: Group by Show Title & Season
    groups: dict[tuple, list] = {}
    for item in items:
        p = item["parsed"]
        key = (p["title"], p["season"] or 1)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    for (show_title, season), ep_items in groups.items():
        # Sort episodes numerically by episode number
        ep_items.sort(key=lambda x: (x["parsed"]["episode"] or 0, x["file_name"]))

        first_stream = ep_items[0]["stream_url"]
        first_blogger_url = build_blogspot_url(first_stream, f"{show_title} S{season:02d}E01")

        header = (
            f"📺 **{show_title} — Season {season}**\n"
            f"⚡ **{len(ep_items)} Episodes Indexed Successfully!**\n\n"
            f"📋 **Copy & Paste into FilmHouse Admin:**\n"
        )

        lines = []
        for ep in ep_items:
            ep_num = ep["parsed"]["episode"]
            ep_label = f"Ep {ep_num}" if ep_num else "Ep"
            lines.append(f"• **{ep_label}:** `{ep['stream_url']}`")

        # Telegram message length limit chunking (4000 characters)
        current_chunk = header
        for line in lines:
            if len(current_chunk) + len(line) + 100 > 3800:
                await client.send_message(user_id, current_chunk, disable_web_page_preview=True)
                current_chunk = f"📺 **{show_title} — Season {season} (Continued):**\n\n"
            current_chunk += line + "\n"

        current_chunk += f"\n🍿 **Blogspot Player (Ep 1):**\n{first_blogger_url}"

        buttons = [
            [InlineKeyboardButton("🍿 Test on Blogspot", url=first_blogger_url)],
        ]

        try:
            await status_msg.edit_text(current_chunk, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except Exception:
            await client.send_message(user_id, current_chunk, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


def register_handlers(app: Client):
    """Registers all Telegram bot command and message handlers."""

    @app.on_message(filters.command(["start", "help"]) & filters.private)
    async def start_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            await message.reply_text("⛔ You are not authorized to use this bot.")
            return

        welcome_text = (
            "🎬 **Welcome to FilmHouse Stream Bot!**\n\n"
            "Forward any **Movie** or **TV Series batch** here, and I will instantly generate:\n"
            "• ⚡ High-Speed HTTP 206 Direct Stream URLs\n"
            "• 🍿 Direct Blogspot Player Links (with your Monetag Ads)\n"
            "• 📺 Smart Season & Episode recognition (up to 100+ episodes at once)\n\n"
            "Forward your video files to get started!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍿 FilmHouse Blogspot", url=config.BLOGGER_URL)],
            [InlineKeyboardButton("⚙️ Server Status", callback_data="status_check")]
        ])
        await message.reply_text(welcome_text, reply_markup=keyboard)

    @app.on_callback_query(filters.regex("status_check"))
    async def status_callback(client: Client, query):
        await query.answer("⚡ Streaming server is active and online!", show_alert=True)

    @app.on_message((filters.video | filters.document) & filters.private)
    async def media_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_authorized(user_id):
            await message.reply_text("⛔ You are not authorized to use this bot.")
            return

        media = message.video or message.document
        if not media:
            return

        # Initialize or retrieve user's batch buffer
        if user_id not in _batch_buffers:
            status_msg = await message.reply_text("⏳ *Indexing file to storage channel...*", quote=True)
            _batch_buffers[user_id] = {
                "items": [],
                "task": None,
                "status_msg": status_msg,
            }
        else:
            status_msg = _batch_buffers[user_id]["status_msg"]

        try:
            # 1. Forward media to private bin channel
            forwarded = await message.forward(config.BIN_CHANNEL_ID)
            message_id = forwarded.id

            # 2. Extract metadata
            file_name = getattr(media, "file_name", None) or f"video_{message_id}.mp4"
            file_size = getattr(media, "file_size", 0)
            file_size_str = format_bytes(file_size)

            # 3. Parse filename and build token & stream URL
            parsed = parse_filename(file_name)
            token = generate_stream_token(message_id)
            stream_url = f"{config.SERVER_URL}/dl/{token}"

            item_data = {
                "message_id": message_id,
                "file_name": file_name,
                "file_size": file_size,
                "file_size_str": file_size_str,
                "parsed": parsed,
                "token": token,
                "stream_url": stream_url,
            }

            _batch_buffers[user_id]["items"].append(item_data)
            count = len(_batch_buffers[user_id]["items"])

            # Update status message if multiple files arrive
            if count > 1:
                try:
                    await status_msg.edit_text(f"⏳ *Indexed {count} episodes so far... Processing batch...*")
                except Exception:
                    pass

            # 4. Debounce Timer: Wait 3.5 seconds after last forwarded file
            if _batch_buffers[user_id]["task"]:
                _batch_buffers[user_id]["task"].cancel()

            async def delayed_flush():
                await asyncio.sleep(3.5)
                await flush_batch(client, user_id)

            _batch_buffers[user_id]["task"] = asyncio.create_task(delayed_flush())

        except Exception as e:
            logger.error(f"Error handling media: {e}", exc_info=True)
            await message.reply_text(f"❌ **Error indexing file:** `{str(e)}`")
