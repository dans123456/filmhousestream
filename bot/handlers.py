import asyncio
import logging
import urllib.parse
from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from server.security import generate_stream_token
from server.parser import parse_filename
from server.stream_server import format_bytes
from bot.storage import record_indexed_file, get_tracked_files, remove_tracked_files
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


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Constructs the interactive main dashboard buttons."""
    library_url = f"{config.SERVER_URL}/library"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Open Media Library (WebApp)", web_app=WebAppInfo(url=library_url))],
        [InlineKeyboardButton("🍿 FilmHouse Blogspot", url=config.BLOGGER_URL)],
        [
            InlineKeyboardButton("⚙️ Server Status", callback_data="status_check"),
            InlineKeyboardButton("ℹ️ How to Use", callback_data="help_menu"),
        ],
        [InlineKeyboardButton("🧹 Manage Bin Storage (Delete)", callback_data="bin_manage")],
    ])


async def flush_batch(client: Client, user_id: int):
    """
    Called after debounce delay to sort episodes numerically, forward them in order
    into the Bin Channel, record them, and output a clean, verifiable list with episode titles.
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
            # Post copy to bin channel without "Forwarded from" header
            forwarded = await msg.copy(config.BIN_CHANNEL_ID)
            record_indexed_file(forwarded.id, file_name, parsed=parsed, file_size_str=file_size_str)
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
                [InlineKeyboardButton("📱 View in Library (WebApp)", web_app=WebAppInfo(url=f"{config.SERVER_URL}/library"))],
                [InlineKeyboardButton("⬇️ Direct Stream Link", url=stream_url)],
            ]
            await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Error indexing single file: {e}")
            await status_msg.edit_text(f"❌ Error indexing file: `{str(e)}`")
        return

    # Case 2: Multiple files forwarded (Series Batch)
    groups: dict[tuple, list] = {}
    for item in items:
        p = item["parsed"]
        key = (p["title"], p["season"] or 1)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    for (show_title, season), ep_items in groups.items():
        # 1. SORT STRICTLY BY EPISODE NUMBER (Ep 1 -> Ep 100)
        ep_items.sort(key=lambda x: (x["parsed"]["episode"] or 0, x["file_name"]))
        total_eps = len(ep_items)

        try:
            await status_msg.edit_text(f"⏳ *Forwarding {total_eps} episodes in strict numerical order to storage channel...*")
        except Exception:
            pass

        processed_links = []
        for idx, ep_item in enumerate(ep_items, start=1):
            raw_msg: Message = ep_item["msg"]
            try:
                # Post copy to bin channel without "Forwarded from" header
                forwarded = await raw_msg.copy(config.BIN_CHANNEL_ID)
                record_indexed_file(
                    forwarded.id,
                    ep_item["file_name"],
                    parsed=ep_item["parsed"],
                    file_size_str=ep_item["file_size_str"]
                )
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
            [InlineKeyboardButton("📱 View Library (All Episodes)", web_app=WebAppInfo(url=f"{config.SERVER_URL}/library"))],
        ]

        try:
            await status_msg.edit_text(current_chunk, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except Exception:
            await client.send_message(user_id, current_chunk, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


def register_handlers(app: Client):
    """Registers all Telegram bot command and message handlers."""

    @app.on_message(filters.command(["start", "menu"]) & filters.private)
    async def start_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            await message.reply_text("⛔ You are not authorized to use this bot.")
            return

        welcome_text = (
            "🎬 **FilmHouse Stream Engine Dashboard**\n\n"
            "Forward any **Movie** or **TV Series batch** here to instantly generate:\n"
            "• ⚡ High-Speed HTTP 206 Direct Stream URLs\n"
            "• 📁 Ordered Backup in your Private Bin Channel\n"
            "• 📺 Smart Episode Title Extraction & Numerical Sorting\n\n"
            "Select an option below or forward video files directly:"
        )
        await message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard())

    @app.on_message(filters.command("help") & filters.private)
    async def help_command_handler(client: Client, message: Message):
        help_text = (
            "ℹ️ **How to Use FilmHouse Stream Bot:**\n\n"
            "1. **For Movies:** Forward 1 movie file $\\rightarrow$ receive direct stream link $\\rightarrow$ paste into FilmHouse Admin.\n\n"
            "2. **For TV Series:** Select multiple episodes (e.g. 10 to 50 files) and forward all at once. The bot will:\n"
            "   - Buffer all incoming episodes.\n"
            "   - Sort them strictly Ep 1 $\\rightarrow$ Ep 100.\n"
            "   - Forward into your Bin Channel in exact sequence.\n"
            "   - Send you an organized list with Episode Titles ready to copy."
        )
        await message.reply_text(help_text, reply_markup=get_main_menu_keyboard())

    @app.on_message(filters.command("status") & filters.private)
    async def status_command_handler(client: Client, message: Message):
        tracked = get_tracked_files()
        status_text = (
            "⚙️ **System & Stream Health:**\n\n"
            f"• **Streaming Server:** 🟢 Online (Port {config.PORT})\n"
            f"• **Public URL:** `{config.SERVER_URL}`\n"
            f"• **Bin Channel:** `{config.BIN_CHANNEL_ID}`\n"
            f"• **Tracked Video Files:** {len(tracked)} items\n"
            f"• **MTProto Crypto:** ⚡ High-Speed C-Accelerated (`tgcrypto`)"
        )
        await message.reply_text(status_text, reply_markup=get_main_menu_keyboard())

    @app.on_message(filters.command("clear_bin") & filters.private)
    async def clear_bin_command_handler(client: Client, message: Message):
        """Triggers the interactive Bin Storage Manager."""
        if not is_authorized(message.from_user.id):
            return
        await send_bin_manager_menu(message)

    @app.on_message(filters.command(["library", "app"]) & filters.private)
    async def library_command_handler(client: Client, message: Message):
        """Opens the FilmHouse Media Library Mini App."""
        if not is_authorized(message.from_user.id):
            return
        web_url = f"{config.SERVER_URL}/library"
        buttons = [
            [InlineKeyboardButton("📱 Open Media Library (WebApp)", web_app=WebAppInfo(url=web_url))],
            [InlineKeyboardButton("🌐 Open in Web Browser", url=web_url)],
        ]
        await message.reply_text(
            "📚 **FilmHouse Media Library**\n\n"
            "Browse, search, stream, and manage all your indexed movies and series directly inside Telegram:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ==========================================
    # Interactive Callback Handlers
    # ==========================================

    @app.on_callback_query(filters.regex("status_check"))
    async def status_callback(client: Client, query: CallbackQuery):
        tracked = get_tracked_files()
        await query.answer(f"⚡ Streaming Engine Online! {len(tracked)} files indexed.", show_alert=True)

    @app.on_callback_query(filters.regex("menu_main"))
    async def menu_main_callback(client: Client, query: CallbackQuery):
        welcome_text = (
            "🎬 **FilmHouse Stream Engine Dashboard**\n\n"
            "Forward any **Movie** or **TV Series batch** here to instantly generate:\n"
            "• ⚡ High-Speed HTTP 206 Direct Stream URLs\n"
            "• 📁 Ordered Backup in your Private Bin Channel\n"
            "• 📺 Smart Episode Title Extraction & Numerical Sorting"
        )
        await query.message.edit_text(welcome_text, reply_markup=get_main_menu_keyboard())

    @app.on_callback_query(filters.regex("help_menu"))
    async def help_menu_callback(client: Client, query: CallbackQuery):
        help_text = (
            "ℹ️ **How to Use FilmHouse Stream Bot:**\n\n"
            "1. **Movies:** Forward any single movie file $\\rightarrow$ receive direct stream link $\\rightarrow$ paste into FilmHouse Admin.\n\n"
            "2. **TV Series:** Select multiple episodes (e.g. 10 to 50 files) and forward all at once. The bot will:\n"
            "   - Buffer all incoming episodes.\n"
            "   - Sort them strictly Ep 1 $\\rightarrow$ Ep 100.\n"
            "   - Forward into your Bin Channel in exact sequence.\n"
            "   - Send you an organized list with Episode Titles ready to copy."
        )
        buttons = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]]
        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_callback_query(filters.regex("bin_manage"))
    async def bin_manage_callback(client: Client, query: CallbackQuery):
        await send_bin_manager_menu(query.message, edit=True)

    @app.on_callback_query(filters.regex("bin_del_recent"))
    async def bin_del_recent_callback(client: Client, query: CallbackQuery):
        """Deletes the last 25 test uploads."""
        tracked = get_tracked_files(limit=25)
        if not tracked:
            await query.answer("No tracked files found to delete.", show_alert=True)
            return

        ids = [item["message_id"] for item in tracked]
        try:
            await client.delete_messages(config.BIN_CHANNEL_ID, ids)
            remove_tracked_files(ids)
            await query.answer(f"✅ Deleted {len(ids)} recent test files from storage!", show_alert=True)
            await send_bin_manager_menu(query.message, edit=True)
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)

    @app.on_callback_query(filters.regex("bin_del_all_confirm"))
    async def bin_del_all_confirm_callback(client: Client, query: CallbackQuery):
        """Shows danger confirmation before deleting all files."""
        tracked = get_tracked_files()
        confirm_text = (
            "🚨 **CRITICAL WARNING — PERMANENT DELETION** 🚨\n\n"
            f"You are about to delete **ALL {len(tracked)} files** from your Bin Channel!\n\n"
            "⚠️ **CONSEQUENCE:** Any movie or series episode in FilmHouse that relies on these files will **STOP STREAMING PERMANENTLY**.\n\n"
            "Are you completely sure you want to proceed?"
        )
        buttons = [
            [InlineKeyboardButton("🔴 Yes, Delete Everything", callback_data="bin_del_all_exec")],
            [InlineKeyboardButton("🟢 Cancel & Keep Safe", callback_data="bin_manage")],
        ]
        await query.message.edit_text(confirm_text, reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_callback_query(filters.regex("bin_del_all_exec"))
    async def bin_del_all_exec_callback(client: Client, query: CallbackQuery):
        """Executes deletion of all tracked files in batches."""
        tracked = get_tracked_files()
        if not tracked:
            await query.answer("Storage is already empty.", show_alert=True)
            await send_bin_manager_menu(query.message, edit=True)
            return

        ids = [item["message_id"] for item in tracked]
        deleted_count = 0

        # Delete in chunks of 50 (Telegram limit per delete_messages call)
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            try:
                await client.delete_messages(config.BIN_CHANNEL_ID, chunk)
                deleted_count += len(chunk)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error deleting batch: {e}")

        remove_tracked_files(ids)
        await query.answer(f"🧹 Cleaned {deleted_count} files from storage channel!", show_alert=True)
        await send_bin_manager_menu(query.message, edit=True)

    @app.on_callback_query(filters.regex("bin_manual_help"))
    async def bin_manual_help_callback(client: Client, query: CallbackQuery):
        """Explains how to manually clear files in Telegram channel."""
        info_text = (
            "📱 **How to Clear Directly in Telegram Channel:**\n\n"
            "If you want to clear older test files that were uploaded before the bot started tracking:\n\n"
            "1. Open your **Private Bin Channel** in Telegram.\n"
            "2. Long-press any message $\\rightarrow$ tap **Select**.\n"
            "3. Select all the test messages you want to remove.\n"
            "4. Tap the **Trash Can icon** (Delete) $\\rightarrow$ choose **Delete for Everyone**.\n\n"
            "Telegram will erase them instantly without needing any bot command!"
        )
        buttons = [[InlineKeyboardButton("🔙 Back to Bin Manager", callback_data="bin_manage")]]
        await query.message.edit_text(info_text, reply_markup=InlineKeyboardMarkup(buttons))

    # ==========================================
    # Media Batch Listener
    # ==========================================

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
            file_name = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
            file_size = getattr(media, "file_size", 0)
            file_size_str = format_bytes(file_size)
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


async def send_bin_manager_menu(message: Message, edit: bool = False):
    """Renders the Bin Storage Manager with safety warnings and options."""
    tracked = get_tracked_files()
    count = len(tracked)

    menu_text = (
        "🧹 **Bin Channel Storage Manager**\n\n"
        "⚠️ **SAFETY WARNING:**\n"
        "Deleting video files from your storage channel will **permanently break** the streaming links for those files in FilmHouse.\n\n"
        f"📊 **Tracked Video Files:** `{count} files`\n\n"
        "Select an option below:"
    )

    buttons = [
        [InlineKeyboardButton(f"🗑️ Delete Last 25 Test Files", callback_data="bin_del_recent")],
        [InlineKeyboardButton("⚠️ Empty All Test Files (Danger)", callback_data="bin_del_all_confirm")],
        [InlineKeyboardButton("📱 Clear Directly in Telegram", callback_data="bin_manual_help")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")],
    ]
    markup = InlineKeyboardMarkup(buttons)

    if edit:
        await message.edit_text(menu_text, reply_markup=markup)
    else:
        await message.reply_text(menu_text, reply_markup=markup)
