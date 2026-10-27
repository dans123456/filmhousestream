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
    Called after debounce delay to sort episodes numerically, forward them in order
    into the Bin Channel, and output a clean, verifiable list with episode titles.
    """
    buffer_data = _batch_buffers.pop(user_id, None)
    if not buffer_data:
        return

    items = buffer_data["items"]
    status_msg: Message = buffer_data["status_msg"]

    if not items:
        return

    # Case 1: Single file forwarded (Movie or 1 Episode)
    if len(items) == 1:
        item = items[0]
        msg: Message = item["msg"]
        parsed = item["parsed"]
        file_name = item["file_name"]
        file_size_str = item["file_size_str"]

        try:
            forwarded = await msg.forward(config.BIN_CHANNEL_ID)
            token = generate_stream_token(forwarded.id)
            stream_url = f"{config.SERVER_URL}/dl/{token}"
            blogger_url = build_blogspot_url(stream_url, parsed["title"])

            if parsed["is_series"]:
                title = parsed["title"]
                season = parsed["season"] or 1
                episode = parsed["episode"] or 1
                ep_sub = f" — {parsed['episode_title']}" if parsed['episode_title'] else ""
                quality_badge = f" • {parsed['quality']}" if parsed['quality'] else ""

                text = (
                    f"📺 **{title} — Season {season}**\n\n"
                    f"• **Episode {episode}{ep_sub}**{quality_badge}\n"
                    f"📁 `{file_name}` ({file_size_str})\n\n"
                    f"🔗 **Stream URL (FilmHouse):**\n`{stream_url}`\n\n"
                    f"🔑 **Token:**\n`{token}`"
                )
            else:
                title = parsed["title"]
                year_str = f" ({parsed['year']})" if parsed['year'] else ""
                qual_str = f" [{parsed['quality']}]" if parsed['quality'] else ""

                text = (
                    f"🎬 **{title}{year_str}{qual_str}**\n\n"
                    f"📁 `{file_name}` ({file_size_str})\n\n"
                    f"🔗 **Stream URL (FilmHouse):**\n`{stream_url}`\n\n"
                    f"🔑 **Token:**\n`{token}`"
                )

            buttons = [
                [InlineKeyboardButton("🍿 Test on Blogspot", url=blogger_url)],
                [InlineKeyboardButton("⬇️ Direct Stream Link", url=stream_url)],
            ]
            await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Error indexing single file: {e}")
            await status_msg.edit_text(f"❌ Error indexing file: `{str(e)}`")
        return

    # Case 2: Multiple files forwarded (Series Batch)
    # Group by (Show Title, Season)
    groups: dict[tuple, list] = {}
    for item in items:
        p = item["parsed"]
        key = (p["title"], p["season"] or 1)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    for (show_title, season), ep_items in groups.items():
        # 1. SORT STRICTLY BY EPISODE NUMBER (Ep 1 -> Ep 22)
        ep_items.sort(key=lambda x: (x["parsed"]["episode"] or 0, x["file_name"]))
        total_eps = len(ep_items)

        # 2. FORWARD INTO BIN CHANNEL IN STRICT NUMERICAL ORDER
        try:
            await status_msg.edit_text(f"⏳ *Forwarding {total_eps} episodes in strict numerical order to storage channel...*")
        except Exception:
            pass

        processed_links = []
        for idx, ep_item in enumerate(ep_items, start=1):
            raw_msg: Message = ep_item["msg"]
            try:
                # Forward to bin channel in sequence
                forwarded = await raw_msg.forward(config.BIN_CHANNEL_ID)
                token = generate_stream_token(forwarded.id)
                stream_url = f"{config.SERVER_URL}/dl/{token}"

                ep_num = ep_item["parsed"]["episode"] or idx
                ep_title = ep_item["parsed"]["episode_title"]
                title_label = f" — {ep_title}" if ep_title else ""

                processed_links.append({
                    "ep_num": ep_num,
                    "title_label": title_label,
                    "stream_url": stream_url,
                    "file_name": ep_item["file_name"],
                })
                # Small pause to guarantee Telegram timestamp order in channel
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error forwarding episode {idx}: {e}")

        # 3. BUILD CLEAN, VERIFIABLE OUTPUT WITH EPISODE TITLES
        header = (
            f"📺 **{show_title} — Season {season}**\n"
            f"⚡ **{len(processed_links)} Episodes Indexed in Strict Numerical Order!**\n\n"
            f"📋 **Copy & Paste into FilmHouse Admin:**\n\n"
        )

        lines = []
        for ep in processed_links:
            lines.append(f"• **Ep {ep['ep_num']}{ep['title_label']}**\n  `{ep['stream_url']}`\n")

        # Chunk messages if exceeding Telegram 4000 char limit
        current_chunk = header
        for line in lines:
            if len(current_chunk) + len(line) + 100 > 3800:
                await client.send_message(user_id, current_chunk, disable_web_page_preview=True)
                current_chunk = f"📺 **{show_title} — Season {season} (Continued):**\n\n"
            current_chunk += line

        first_stream = processed_links[0]["stream_url"] if processed_links else ""
        first_blogger = build_blogspot_url(first_stream, f"{show_title} S{season:02d}E01") if first_stream else config.BLOGGER_URL
        buttons = [
            [InlineKeyboardButton("🍿 Test Ep 1 on Blogspot", url=first_blogger)],
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
            "Forward any **Movie** or **TV Series batch** here, and I will:\n"
            "• ⚡ Sort episodes in strict numerical order (Ep 1 $\\rightarrow$ Ep 100)\n"
            "• 📁 Back up into your Bin Channel in clean sequence\n"
            "• 📺 Extract each Episode Title so you can verify before adding to FilmHouse\n\n"
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

    @app.on_message(filters.command("clear_bin") & filters.private)
    async def clear_bin_handler(client: Client, message: Message):
        """Allows an admin to clean out old test messages from the bin channel."""
        if not is_authorized(message.from_user.id):
            return
        
        status = await message.reply_text("🧹 *Cleaning out old test files from storage channel...*")
        count = 0
        try:
            # Delete messages from bin channel in batches
            msg_ids_to_delete = []
            async for m in client.get_chat_history(config.BIN_CHANNEL_ID, limit=100):
                msg_ids_to_delete.append(m.id)
                if len(msg_ids_to_delete) >= 50:
                    await client.delete_messages(config.BIN_CHANNEL_ID, msg_ids_to_delete)
                    count += len(msg_ids_to_delete)
                    msg_ids_to_delete = []
            if msg_ids_to_delete:
                await client.delete_messages(config.BIN_CHANNEL_ID, msg_ids_to_delete)
                count += len(msg_ids_to_delete)
            await status.edit_text(f"✅ *Successfully deleted {count} old messages from your Bin Channel!* Your channel is fresh and clean.")
        except Exception as e:
            await status.edit_text(f"❌ Error clearing bin channel: `{e}`")

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
            status_msg = await message.reply_text("⏳ *Receiving and preparing episodes...*", quote=True)
            _batch_buffers[user_id] = {
                "items": [],
                "task": None,
                "status_msg": status_msg,
            }
        else:
            status_msg = _batch_buffers[user_id]["status_msg"]

        try:
            # Extract metadata without forwarding yet
            file_name = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
            file_size = getattr(media, "file_size", 0)
            file_size_str = format_bytes(file_size)

            # Parse filename
            parsed = parse_filename(file_name)

            item_data = {
                "msg": message,
                "file_name": file_name,
                "file_size": file_size,
                "file_size_str": file_size_str,
                "parsed": parsed,
            }

            _batch_buffers[user_id]["items"].append(item_data)
            count = len(_batch_buffers[user_id]["items"])

            # Update live counter
            if count > 1:
                try:
                    await status_msg.edit_text(f"⏳ *Received {count} episodes... Waiting for all files in batch...*")
                except Exception:
                    pass

            # Debounce timer: wait 3.5 seconds after last forwarded message arrives
            if _batch_buffers[user_id]["task"]:
                _batch_buffers[user_id]["task"].cancel()

            async def delayed_flush():
                await asyncio.sleep(3.5)
                await flush_batch(client, user_id)

            _batch_buffers[user_id]["task"] = asyncio.create_task(delayed_flush())

        except Exception as e:
            logger.error(f"Error handling media: {e}", exc_info=True)
            await message.reply_text(f"❌ **Error indexing file:** `{str(e)}`")
