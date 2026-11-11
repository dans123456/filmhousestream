import io
import time
import re
import asyncio
import logging
import urllib.parse
from hydrogram import Client, filters
from hydrogram.errors import FloodWait
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from server.security import generate_stream_token
from server.parser import parse_filename
from server.stream_server import format_bytes
from bot.storage import record_indexed_file, get_tracked_files, remove_tracked_files
import config

logger = logging.getLogger("filmhouse.bot")

async def safe_copy_message(raw_msg: Message, target_channel_id, status_msg: Message = None, ep_info: str = "", max_retries: int = 5) -> Message:
    """Copies a message to the target channel with automatic FloodWait retry protection."""
    for attempt in range(max_retries):
        try:
            return await raw_msg.copy(target_channel_id)
        except FloodWait as fw:
            wait_time = int(fw.value) + 1
            logger.warning(f"[FloodWait] Telegram rate limit hit. Sleeping {wait_time}s before retry (attempt {attempt+1}/{max_retries})")
            if status_msg:
                try:
                    info_label = f" ({ep_info})" if ep_info else ""
                    await status_msg.edit_text(
                        f"⏳ *Telegram channel speed limit reached.*\n\n"
                        f"🛡️ *Safely pausing for {wait_time}s to avoid bot ban...*\n"
                        f"Will automatically resume{info_label} in {wait_time} seconds!"
                    )
                except Exception:
                    pass
            await asyncio.sleep(wait_time)
        except Exception as err:
            if attempt == max_retries - 1:
                raise err
            logger.warning(f"[CopyRetry] Attempt {attempt+1}/{max_retries} failed ({err}), retrying in 1.5s...")
            await asyncio.sleep(1.5)
    raise RuntimeError("Failed to copy message after maximum retries.")

# In-memory batch buffers: user_id -> {"items": [...], "task": asyncio.Task, "status_msg": Message}
_batch_buffers: dict[int, dict] = {}
_batch_locks: dict[int, asyncio.Lock] = {}
_processing_locks: dict[int, asyncio.Lock] = {}
# For Option B: user_id -> {"items": [...], "status_msg": Message} waiting for title text from admin
_pending_title_batches: dict[int, dict] = {}


def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _batch_locks:
        _batch_locks[user_id] = asyncio.Lock()
    return _batch_locks[user_id]


def get_processing_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _processing_locks:
        _processing_locks[user_id] = asyncio.Lock()
    return _processing_locks[user_id]


def is_authorized(user_id: int) -> bool:
    """Verifies whether the user is an authorized FilmHouse administrator."""
    if not config.ADMIN_IDS:
        logger.error(f"SECURITY CRITICAL: ADMIN_IDS is empty! Rejecting access for user {user_id}")
        return False
    return user_id in config.ADMIN_IDS


def build_blogspot_url(stream_url: str, title: str) -> str:
    """Builds the direct Web Player URL."""
    encoded_stream = urllib.parse.quote(stream_url, safe="")
    encoded_title = urllib.parse.quote(title, safe="")
    base = config.BLOGGER_URL.rstrip("/")
    sep = "&" if "?" in base else "?"
    if base.endswith(".html"):
        return f"{base}{sep}watch={encoded_stream}&title={encoded_title}"
    return f"{base}/{sep}watch={encoded_stream}&title={encoded_title}"


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Constructs the interactive main dashboard buttons."""
    library_url = f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Open Media Library (WebApp)", web_app=WebAppInfo(url=library_url))],
        [InlineKeyboardButton("🍿 FilmHouse Web Player", url=config.BLOGGER_URL)],
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
    lock = get_user_lock(user_id)
    async with lock:
        buffer_data = _batch_buffers.pop(user_id, None)
        if not buffer_data:
            return

        items = buffer_data["items"]
        status_msg: Message = buffer_data["status_msg"]

    if not items:
        return

    # Check for Option B: Did the user forward nameless episodes?
    # (e.g. 01.mp4, Episode 02, etc.)
    all_need_title = all(item["parsed"].get("needs_title") for item in items)
    if all_need_title:
        _pending_title_batches[user_id] = {
            "items": items,
            "status_msg": status_msg,
        }
        sample_names = ", ".join([f"`{it['file_name']}`" for it in items[:3]])
        if len(items) > 3:
            sample_names += f" and {len(items) - 3} more..."

        prompt_text = (
            f"❓ **Series Title Needed!**\n\n"
            f"Received **{len(items)} episodes** ({sample_names}), but they don't have a series name.\n\n"
            f"💬 **Please reply to this message with the Series & Season name:**\n"
            f"*(Example: `Teach You A Lesson S1` or `Squid Game Season 2`)*\n\n"
            f"*(Or tap Cancel below to abort)*"
        )
        cancel_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Batch", callback_data="batch_cancel_now")]
        ])
        try:
            await status_msg.edit_text(prompt_text, reply_markup=cancel_kb)
        except Exception:
            await client.send_message(user_id, prompt_text, reply_markup=cancel_kb)
        return

    # Ensure only one batch processes at a time per user to prevent concurrent channel spam & Telegram FloodWaits
    proc_lock = get_processing_lock(user_id)
    async with proc_lock:
        # Case 1: Single file forwarded (Movie or 1 Episode)
        if len(items) == 1:
            item = items[0]
            msg: Message = item["msg"]
            parsed = item["parsed"]
            file_name = item["file_name"]
            file_size_str = item["file_size_str"]

            # Auto-detect TV Series via TMDB if parser was uncertain
            if not parsed.get("is_series") and getattr(config, "TMDB_API_KEY", ""):
                try:
                    from server.tmdb_auditor import search_tmdb_tv
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        tv_match = await search_tmdb_tv(s, parsed.get("title") or file_name)
                        if tv_match and (tv_match.get("vote_count", 0) >= 3 or tv_match.get("popularity", 0) >= 1.0):
                            parsed["is_series"] = True
                            parsed["title"] = tv_match.get("name") or parsed["title"]
                            parsed["season"] = parsed.get("season") or 1
                            parsed["episode"] = parsed.get("episode") or 1
                            logger.info(f"Auto-promoted '{file_name}' to TV Series via TMDB ('{parsed['title']}')")
                except Exception as tmdb_err:
                    logger.debug(f"TMDB single-file check notice: {tmdb_err}")

            try:
                # Post copy to bin channel without "Forwarded from" header
                forwarded = await safe_copy_message(msg, config.BIN_CHANNEL_ID, status_msg=status_msg, ep_info=file_name)
                record_indexed_file(forwarded.id, file_name, parsed=parsed, file_size_str=file_size_str)
                token = generate_stream_token(forwarded.id)
                stream_url = f"{config.SERVER_URL}/watch/{token}"

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
                        f"🔗 **Stream Link (Player):**\n`{stream_url}`\n\n"
                        f"🔑 **Token:**\n`{token}`"
                    )
                else:
                    title = parsed["title"]
                    year_str = f" ({parsed['year']})" if parsed['year'] else ""
                    qual_str = f" [{parsed['quality']}]" if parsed['quality'] else ""

                    text = (
                        f"🎬 **{title}{year_str}{qual_str}**\n\n"
                        f"📁 `{file_name}` ({file_size_str})\n\n"
                        f"🔗 **Stream Link (Player):**\n`{stream_url}`\n\n"
                        f"🔑 **Token:**\n`{token}`"
                    )

                buttons = [
                    [InlineKeyboardButton("▶️ Test Stream (Player)", url=stream_url)],
                    [InlineKeyboardButton("📱 View in Library (Admin WebApp)", web_app=WebAppInfo(url=f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"))],
                ]
                await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Error indexing single file: {e}")
                await status_msg.edit_text(f"❌ Error indexing file: `{str(e)}`")
            return

        # Case 2: Multi-file Batch (Smart Universal Series vs Movie detection)
        all_movies = all(not item["parsed"].get("is_series") for item in items)
        if all_movies and len(items) > 1:
            # Check if this multi-file batch is actually an episodic series
            titles = [it["parsed"].get("title") or it["file_name"] for it in items]
            clean_titles = [re.sub(r"[\s\.\-_0-9]+$", "", t).strip().lower() for t in titles]
            same_title = len(set(clean_titles)) == 1

            # Check for movie qualities (e.g. 720p, 1080p, 480p)
            qualities = [it["parsed"].get("quality") for it in items if it["parsed"].get("quality")]
            has_qual_diff = len(set(qualities)) > 1 and len(qualities) == len(items)
            has_year = any(it["parsed"].get("year") for it in items)

            # Extract distinct episode numbers (excluding year, quality tags, and file sizes)
            distinct_ep_nums = set()
            for it in items:
                clean_fn = re.sub(r"\b(19\d{2}|20\d{2})\b", "", it["file_name"])
                clean_fn = re.sub(r"\b(2160p|1080p|720p|480p|360p|4k)\b", "", clean_fn, flags=re.IGNORECASE)
                clean_fn = re.sub(r"\b\d+(?:mb|gb)\b", "", clean_fn, flags=re.IGNORECASE)
                m = re.search(r"\b(?:ep|episode|e)?\s*0?(\d{1,3})\b", clean_fn, re.IGNORECASE)
                if m:
                    distinct_ep_nums.add(int(m.group(1)))

            # If all files share the same movie title AND (have different qualities or a release year), AND don't have distinct episode numbers:
            # IT IS 100% A MULTI-QUALITY MOVIE BATCH (e.g. Elf 2003 in 720p and 1080p)!
            if same_title and (has_qual_diff or has_year) and len(distinct_ep_nums) <= 1:
                all_movies = True
            elif len(distinct_ep_nums) >= 2 and len(distinct_ep_nums) == len(items):
                # Genuine TV series with distinct episode sequence (e.g. 1, 2, 3...)
                logger.info(f"Auto-Promoting multi-file batch ({len(items)} files) to Series Batch (Distinct episodic numbers detected: {distinct_ep_nums})")
                sorted_eps = sorted(list(distinct_ep_nums))
                for it, ep_num in zip(items, sorted_eps):
                    it["parsed"]["is_series"] = True
                    it["parsed"]["season"] = it["parsed"].get("season") or 1
                    it["parsed"]["episode"] = ep_num
                all_movies = False

        if all_movies:
            await process_movies_batch(client, user_id, items, status_msg)
            return

        # Case 3: Multiple files forwarded (Series Batch)
        await process_series_batch(client, user_id, items, status_msg)


async def process_movies_batch(client: Client, user_id: int, items: list, status_msg: Message):
    """
    Handles batches where all items are non-series Movies.
    Groups identical movies into Multi-Quality packages (e.g. 1080p + 720p).
    """
    movie_groups: dict[tuple, list] = {}
    for item in items:
        p = item["parsed"]
        key = (p["title"], p.get("year"))
        if key not in movie_groups:
            movie_groups[key] = []
        movie_groups[key].append(item)

    total_files = len(items)
    try:
        await status_msg.edit_text(f"⏳ *Processing and storing {total_files} movie file(s)...*")
    except Exception:
        pass

    quality_ranks = {"4k": 4, "2160p": 4, "1080p": 3, "720p": 2, "480p": 1, "360p": 0}

    for (movie_title, year), m_items in movie_groups.items():
        # Sort highest quality first (4K -> 1080p -> 720p)
        m_items.sort(
            key=lambda x: quality_ranks.get((x["parsed"].get("quality") or "").lower(), 0),
            reverse=True
        )

        processed_versions = []
        for it in m_items:
            raw_msg: Message = it["msg"]
            try:
                forwarded = await safe_copy_message(
                    raw_msg,
                    config.BIN_CHANNEL_ID,
                    status_msg=status_msg,
                    ep_info=f"movie {it['file_name']}"
                )
                record_indexed_file(
                    forwarded.id,
                    it["file_name"],
                    parsed=it["parsed"],
                    file_size_str=it["file_size_str"]
                )
                token = generate_stream_token(forwarded.id)
                stream_url = f"{config.SERVER_URL}/watch/{token}"
                processed_versions.append({
                    "quality": it["parsed"].get("quality") or "HD",
                    "file_name": it["file_name"],
                    "file_size_str": it["file_size_str"],
                    "stream_url": stream_url,
                    "token": token,
                })
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error forwarding movie {it['file_name']}: {e}")

        if not processed_versions:
            continue

        year_str = f" ({year})" if year else ""
        top_version = processed_versions[0]
        buttons = [
            [InlineKeyboardButton("▶️ Test Stream (Player)", url=top_version["stream_url"])],
            [InlineKeyboardButton("📱 View Library (Admin WebApp)", web_app=WebAppInfo(url=f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"))],
        ]

        if len(processed_versions) > 1:
            qual_tags = " • ".join([v["quality"] for v in processed_versions])
            text = (
                f"🎬 **{movie_title}{year_str}**\n"
                f"✨ **{len(processed_versions)} Qualities Available ({qual_tags})**\n\n"
                f"📋 **Tap Code Box Below to Copy All Links (1-Tap Copy):**\n"
            )
            code_lines = []
            for v in processed_versions:
                sz = f" ({v['file_size_str']})" if v.get("file_size_str") else ""
                code_lines.append(f"{v['quality']}{sz}: {v['stream_url']}")
            text += "```\n" + "\n".join(code_lines) + "\n```"
        else:
            v = processed_versions[0]
            text = (
                f"🎬 **{movie_title}{year_str} [{v['quality']}]**\n\n"
                f"📁 `{v['file_name']}` ({v['file_size_str']})\n\n"
                f"🔗 **Stream Link (Player):**\n`{v['stream_url']}`\n\n"
                f"🔑 **Token:**\n`{v['token']}`"
            )

        try:
            await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except Exception:
            await client.send_message(user_id, text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


def harmonize_batch_missing_episodes(items: list):
    """
    Analyzes series episodes in a forwarded batch. If a show has a clear dominant season
    (e.g. Season 8 with 22 episodes), any anomalous items (e.g. S0.part1, S0.part2, or part files)
    are automatically inherited into that dominant season to fill in missing episode gaps (e.g. Ep 23 & 24).
    """
    from server.parser import build_golden_filename

    # Group items by normalized show title
    shows: dict[str, list] = {}
    for item in items:
        p = item.get("parsed") or {}
        fn = (item.get("file_name") or "").lower()
        if not p.get("is_series") and not any(k in fn for k in ("part", "s0")):
            continue
        title = (p.get("title") or "Unknown").strip().lower()
        if title not in shows:
            shows[title] = []
        shows[title].append(item)

    for title, show_items in shows.items():
        if len(show_items) < 2:
            continue

        # Count frequencies of positive seasons
        season_counts: dict[int, int] = {}
        for it in show_items:
            s = it["parsed"].get("season")
            if s and s > 0:
                season_counts[s] = season_counts.get(s, 0) + 1

        if not season_counts:
            continue

        # Find dominant season (the season with the most episodes in this batch)
        dominant_season = max(season_counts, key=season_counts.get)
        dominant_count = season_counts[dominant_season]

        if dominant_count < 2:
            continue

        # Existing episodes in the dominant season
        existing_eps = set()
        for it in show_items:
            if it["parsed"].get("season") == dominant_season and it["parsed"].get("episode"):
                existing_eps.add(it["parsed"]["episode"])

        # Detect ambiguous / anomalous items:
        # Files that already have a clear SxxExx or 1x01 tag and positive season are NEVER ambiguous!
        ambiguous_items = []
        for it in show_items:
            fn = (it.get("file_name") or "").lower()
            s = it["parsed"].get("season")
            has_real_tag = bool(re.search(r"\b[sS]\d{1,2}[eE]\d{1,3}\b", fn) or re.search(r"\b\d{1,2}[xX]\d{1,3}\b", fn))
            if has_real_tag and s and s > 0:
                continue
            is_explicit_s0 = bool(re.search(r"\bs0+(?:[^\d]|$)", fn))
            if s == 0 or s is None:
                ambiguous_items.append(it)
            elif is_explicit_s0 or ("part" in fn and not has_real_tag):
                ambiguous_items.append(it)

        if not ambiguous_items:
            continue

        # Sort ambiguous items by their initial episode or filename order
        ambiguous_items.sort(key=lambda x: (x["parsed"].get("episode") or 0, x.get("file_name") or ""))

        # Assign each ambiguous item to the dominant season and the next missing episode
        next_ep = 1
        for amb in ambiguous_items:
            while next_ep in existing_eps:
                next_ep += 1

            p = amb["parsed"]
            p["is_series"] = True
            p["season"] = dominant_season
            p["episode"] = next_ep
            p["category"] = "series"

            # Update golden filename
            orig_fn = amb.get("file_name") or ""
            golden = build_golden_filename(p, orig_fn)
            p["golden_name"] = golden

            existing_eps.add(next_ep)
            logger.info(f"[Batch Harmonizer] Snapped '{orig_fn}' into {p.get('title')} Season {dominant_season} Episode {next_ep} ({golden})")


async def process_series_batch(client: Client, user_id: int, items: list, status_msg: Message):
    """Processes, sorts, forwards to bin, and outputs a formatted list for a batch of episodes."""
    # Harmonize anomalous part / S0 files into dominant season filling in missing episode slots
    harmonize_batch_missing_episodes(items)

    groups: dict[tuple, list] = {}
    for item in items:
        p = item["parsed"]
        key = (p["title"], p["season"] or 1)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    for (show_title, season), ep_items in groups.items():
        # Deduplicate identical episodes in the batch (keeping the largest file size)
        deduped_eps: dict[int, dict] = {}
        for it in ep_items:
            e_num = it["parsed"].get("episode") or 1
            if e_num not in deduped_eps:
                deduped_eps[e_num] = it
            else:
                if it.get("file_size", 0) > deduped_eps[e_num].get("file_size", 0):
                    deduped_eps[e_num] = it
        ep_items = list(deduped_eps.values())

        # 1. SORT STRICTLY BY EPISODE NUMBER (Ep 1 -> Ep 100+)
        ep_items.sort(key=lambda x: (x["parsed"]["episode"] or 0, x["file_name"]))
        total_eps = len(ep_items)

        try:
            await status_msg.edit_text(f"⏳ *Forwarding {total_eps} episodes in strict numerical order to storage channel...*")
        except Exception:
            pass

        processed_links = []
        last_status_edit = 0.0
        for idx, ep_item in enumerate(ep_items, start=1):
            raw_msg: Message = ep_item["msg"]
            try:
                # Post copy to bin channel without "Forwarded from" header (with auto-FloodWait retry)
                forwarded = await safe_copy_message(
                    raw_msg,
                    config.BIN_CHANNEL_ID,
                    status_msg=status_msg,
                    ep_info=f"at episode {idx}/{total_eps}"
                )
                record_indexed_file(
                    forwarded.id,
                    ep_item["file_name"],
                    parsed=ep_item["parsed"],
                    file_size_str=ep_item["file_size_str"]
                )
                token = generate_stream_token(forwarded.id)
                stream_url = f"{config.SERVER_URL}/watch/{token}"

                ep_num = ep_item["parsed"]["episode"] or idx
                end_ep_num = ep_item["parsed"].get("end_episode")
                ep_title = ep_item["parsed"]["episode_title"]
                title_label = f" — {ep_title}" if ep_title else ""

                processed_links.append({
                    "ep_num": ep_num,
                    "end_ep_num": end_ep_num,
                    "title_label": title_label,
                    "stream_url": stream_url,
                    "file_name": ep_item["file_name"],
                })

                # Throttled live progress update (max once every 3s) so Telegram never rate-limits
                now = time.time()
                if (now - last_status_edit >= 3.0) or idx == total_eps:
                    try:
                        await status_msg.edit_text(f"⏳ *Storing & indexing: {idx} / {total_eps} episodes in storage channel...*")
                        last_status_edit = now
                    except Exception:
                        pass

                # Pause to guarantee Telegram timestamp order in channel and respect rate limits
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error forwarding episode {idx}: {e}")

        # Quick TMDB Audit for this Show & Season
        audit_note = ""
        try:
            from server.tmdb_auditor import search_tmdb_tv, get_tmdb_tv_details, format_episode_ranges
            import aiohttp
            async with aiohttp.ClientSession() as s:
                tv_match = await search_tmdb_tv(s, show_title)
                if tv_match and tv_match.get("id"):
                    details = await get_tmdb_tv_details(s, tv_match["id"])
                    if details and "seasons" in details:
                        s_match = next((x for x in details["seasons"] if x.get("season_number") == season), None)
                        if s_match:
                            expected_count = s_match.get("episode_count", 0)
                            if expected_count > 0:
                                if len(processed_links) >= expected_count:
                                    audit_note = f"✅ **TMDB Check: Complete Season ({len(processed_links)}/{expected_count} Episodes)**\n"
                                else:
                                    up_nums = set([p["ep_num"] for p in processed_links])
                                    missing = [n for n in range(1, expected_count + 1) if n not in up_nums]
                                    m_str = format_episode_ranges(missing)
                                    audit_note = f"⚠️ **TMDB Check: Incomplete ({len(processed_links)}/{expected_count} Episodes • Missing: {m_str})**\n"
        except Exception:
            pass

        # 3. BUILD CLEAN 1-TAP COPY OUTPUT (50 links per message)
        first_stream = processed_links[0]["stream_url"] if processed_links else ""
        buttons = [
            [InlineKeyboardButton("▶️ Test Stream (Player)", url=first_stream)],
            [InlineKeyboardButton("📱 View Library (Admin WebApp)", web_app=WebAppInfo(url=f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"))],
        ]

        chunk_size = 50
        total_chunks = (len(processed_links) + chunk_size - 1) // chunk_size

        for c_idx in range(total_chunks):
            start_i = c_idx * chunk_size
            end_i = min(start_i + chunk_size, len(processed_links))
            chunk_eps = processed_links[start_i:end_i]

            start_ep_num = chunk_eps[0]["ep_num"]
            end_ep_num = chunk_eps[-1].get("end_ep_num") or chunk_eps[-1]["ep_num"]
            ep_range = f"Ep {start_ep_num:02d} – {end_ep_num:02d}"

            part_label = f" (Part {c_idx + 1}/{total_chunks} • {ep_range})" if total_chunks > 1 else ""
            header = (
                f"📺 **{show_title} — Season {season}**{part_label}\n"
                f"⚡ **{len(processed_links)} Episodes Indexed & Sorted!**\n"
                f"{audit_note}\n"
                f"📋 **Tap Code Box Below to Copy All Links (1-Tap Copy):**\n"
            )

            lines = []
            for ep in chunk_eps:
                if ep.get("end_ep_num"):
                    ep_tag = f"E{ep['ep_num']:02d}-E{ep['end_ep_num']:02d}"
                else:
                    ep_tag = f"E{ep['ep_num']:02d}"
                title_part = f" ({ep['title_label'].lstrip(' — ')})" if ep['title_label'] else ""
                lines.append(f"{ep_tag}{title_part}: {ep['stream_url']}")

            code_block = "\n".join(lines)
            body_text = f"{header}```{code_block}```"

            reply_markup = InlineKeyboardMarkup(buttons) if c_idx == 0 else None
            try:
                if c_idx == 0:
                    await status_msg.edit_text(body_text, reply_markup=reply_markup, disable_web_page_preview=True)
                else:
                    await client.send_message(user_id, body_text, disable_web_page_preview=True)
            except Exception as send_err:
                logger.warning(f"Status message edit failed ({send_err}), sending as fresh message.")
                await client.send_message(user_id, body_text, reply_markup=reply_markup, disable_web_page_preview=True)


def register_handlers(app: Client):
    """Registers all Telegram bot command and message handlers."""

    @app.on_message(filters.command(["start", "menu"]) & filters.private)
    async def start_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            logger.warning(f"SECURITY: Unauthorized /start by user {message.from_user.id} (@{message.from_user.username or 'none'})")
            await message.reply_text("⛔ **Access Denied.**\nThis streaming bot is strictly restricted to FilmHouse Administrators.")
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
        if not is_authorized(message.from_user.id):
            return
        help_text = (
            "🌟 **FilmHouse Stream Bot Master Guide:**\n\n"
            "🎬 **1. Movies:**\n"
            "• Forward single movie file $\\rightarrow$ receive instant stream & Blogger links.\n"
            "• Forward 2 qualities (1080p and 720p) $\\rightarrow$ automatically groups as a **Multi-Quality Movie Card**.\n\n"
            "📺 **2. TV Series:**\n"
            "• Select up to 60 episodes and forward all together.\n"
            "• Bot buffers, numerically sorts strictly Ep 1 $\\rightarrow$ Ep 60.\n"
            "• Delivers a clean continuous Option A message with all links ready to copy.\n\n"
            "🌟 **3. Golden Naming Format:**\n"
            "• Movies: `Movie.Title.Year.1080p.mkv`\n"
            "• Series: `Series.Title.S01E01.720p.mkv`\n\n"
            "❌ **4. Cancelling:**\n"
            "• Send `/cancel` or tap `[❌ Cancel Batch]` anytime to abort a batch.\n\n"
            "🔍 **5. Library & Series Audit:**\n"
            "• Send `/library` or `/app` to open the WebApp library.\n"
            "• Send `/audit` or `/checkepisodes` to list all series with only 1 episode uploaded.\n\n"
            "📡 **6. Auto Catalog Matching:**\n"
            "• Run `/scanlibrary` in your Admin Bot to automatically link all stored files to your website!"
        )
        await message.reply_text(help_text, reply_markup=get_main_menu_keyboard())

    @app.on_message(filters.command("status") & filters.private)
    async def status_command_handler(client: Client, message: Message):
        if not is_authorized(message.from_user.id):
            return
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
        web_app_url = f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"
        browser_url = f"{config.SERVER_URL}/library?admin_key={config.ADMIN_SECRET}"
        buttons = [
            [InlineKeyboardButton("📱 Open Media Library (WebApp)", web_app=WebAppInfo(url=web_app_url))],
            [InlineKeyboardButton("🌐 Open in Web Browser", url=browser_url)],
        ]
        await message.reply_text(
            "📚 **FilmHouse Media Library**\n\n"
            "Browse, search, stream, and manage all your indexed movies and series directly inside Telegram:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    @app.on_message(filters.command("cancel") & filters.private)
    async def cancel_command_handler(client: Client, message: Message):
        """Cancels any ongoing batch buffer or pending title request immediately."""
        user_id = message.from_user.id
        if not is_authorized(user_id):
            return

        lock = get_user_lock(user_id)
        async with lock:
            buf = _batch_buffers.pop(user_id, None)
            if buf and buf.get("task"):
                buf["task"].cancel()
            _pending_title_batches.pop(user_id, None)

        await message.reply_text("🛑 **Current batch cancelled.**\nYou can start fresh whenever you're ready.")

    @app.on_message(filters.command(["audit", "checkepisodes", "single_episodes", "synctmdb"]) & filters.private)
    async def audit_episodes_command_handler(client: Client, message: Message):
        """Audits all series in the library to identify incomplete series, gaps, and single-episode titles using TMDB."""
        if not is_authorized(message.from_user.id):
            return

        is_sync = "synctmdb" in (message.text or "")
        status_msg = await message.reply_text("🔍 **Auditing Library with TMDB...**\nCross-checking episode completeness and detecting missing episodes.")

        try:
            from server.tmdb_auditor import run_series_completeness_audit, load_cached_audit
            if is_sync:
                audit_data = await run_series_completeness_audit(force_tmdb=True)
            else:
                audit_data = load_cached_audit()
                if not audit_data or audit_data.get("total_series", 0) == 0:
                    audit_data = await run_series_completeness_audit(force_tmdb=True)

            incomplete = audit_data.get("incomplete_series", [])
        except Exception as e:
            logger.error(f"Audit error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Failed to run audit: {e}")
            return

        if not incomplete:
            await status_msg.edit_text("🎉 **Audit Complete!**\n\nAll TV series in your library have complete seasons and no missing episodes detected!")
            return

        total_count = len(incomplete)
        header = (
            f"⚠️ **Series Completeness Audit ({total_count} Incomplete Titles)**\n"
            f"Cross-checked with TMDB & local gap analysis. Use this checklist to locate and upload missing episodes:\n\n"
        )

        lines = []
        for i, s in enumerate(incomplete, 1):
            cat_icon = "🎬" if s["category"] == "kdrama" else ("🎨" if s["category"] == "anime" else "📺")
            reasons_str = "; ".join(s.get("reasons", []))
            lines.append(f"**{i}. {cat_icon} {s['title']}**\n   └ ⚠️ {reasons_str}")

        # Send in chunks under 3800 characters to adhere to Telegram limits safely
        messages_to_send = []
        current_chunk = header

        for line in lines:
            if len(current_chunk) + len(line) + 2 > 3800:
                messages_to_send.append(current_chunk)
                current_chunk = line + "\n\n"
            else:
                current_chunk += line + "\n\n"
        if current_chunk.strip():
            messages_to_send.append(current_chunk)

        # Edit status message with first chunk
        await status_msg.edit_text(messages_to_send[0])
        # Send subsequent chunks if any
        for chunk in messages_to_send[1:]:
            await message.reply_text(chunk)

    # ==========================================
    # Interactive Callback Handlers
    # ==========================================

    @app.on_callback_query(filters.regex("status_check"))
    async def status_callback(client: Client, query: CallbackQuery):
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
        tracked = get_tracked_files()
        await query.answer(f"⚡ Streaming Engine Online! {len(tracked)} files indexed.", show_alert=True)

    @app.on_callback_query(filters.regex("menu_main"))
    async def menu_main_callback(client: Client, query: CallbackQuery):
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
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
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
        help_text = (
            "🌟 **FilmHouse Stream Bot Master Guide:**\n\n"
            "🎬 **1. Movies:**\n"
            "• Forward single movie file $\\rightarrow$ receive instant stream & Blogger links.\n"
            "• Forward 2 qualities (1080p and 720p) $\\rightarrow$ automatically groups as a **Multi-Quality Movie Card**.\n\n"
            "📺 **2. TV Series:**\n"
            "• Select up to 60 episodes and forward all together.\n"
            "• Bot buffers, numerically sorts strictly Ep 1 $\\rightarrow$ Ep 60.\n"
            "• Delivers a clean continuous Option A message with all links ready to copy.\n\n"
            "🌟 **3. Golden Naming Format:**\n"
            "• Movies: `Movie.Title.Year.1080p.mkv`\n"
            "• Series: `Series.Title.S01E01.720p.mkv`\n\n"
            "❌ **4. Cancelling:**\n"
            "• Send `/cancel` or tap `[❌ Cancel Batch]` anytime to abort a batch.\n\n"
            "🔍 **5. Library & Series Audit:**\n"
            "• Send `/library` or `/app` to open the WebApp library.\n"
            "• Send `/audit` or `/checkepisodes` to list all series with only 1 episode uploaded.\n\n"
            "📡 **6. Auto Catalog Matching:**\n"
            "• Run `/scanlibrary` in your Admin Bot to automatically link all stored files to your website!"
        )
        buttons = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]]
        await query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons))

    @app.on_callback_query(filters.regex("bin_manage"))
    async def bin_manage_callback(client: Client, query: CallbackQuery):
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
        await send_bin_manager_menu(query.message, edit=True)

    @app.on_callback_query(filters.regex("bin_del_recent"))
    async def bin_del_recent_callback(client: Client, query: CallbackQuery):
        """Deletes the last 25 test uploads."""
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
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
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
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
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
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
        if not is_authorized(query.from_user.id):
            await query.answer("⛔ Access Denied: Admin authorization required.", show_alert=True)
            return
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

    @app.on_callback_query(filters.regex("batch_flush_now"))
    async def batch_flush_now_callback(client: Client, query: CallbackQuery):
        """Immediately processes the accumulated batch without waiting for the 25s timer."""
        user_id = query.from_user.id
        if not is_authorized(user_id):
            await query.answer("⛔ Access Denied.", show_alert=True)
            return

        lock = get_user_lock(user_id)
        async with lock:
            if user_id in _batch_buffers and _batch_buffers[user_id].get("task"):
                _batch_buffers[user_id]["task"].cancel()

        await query.answer("⚡ Processing all collected episodes now!")
        await flush_batch(client, user_id)

    @app.on_callback_query(filters.regex("batch_cancel_now"))
    async def batch_cancel_now_callback(client: Client, query: CallbackQuery):
        """Immediately cancels and discards the accumulated batch."""
        user_id = query.from_user.id
        if not is_authorized(user_id):
            await query.answer("⛔ Access Denied.", show_alert=True)
            return

        lock = get_user_lock(user_id)
        async with lock:
            buf = _batch_buffers.pop(user_id, None)
            if buf and buf.get("task"):
                buf["task"].cancel()
            _pending_title_batches.pop(user_id, None)

        await query.answer("❌ Batch cancelled.")
        try:
            await query.message.edit_text("🛑 **Batch upload cancelled.**\nForward video files whenever you want to start a new batch.")
        except Exception:
            pass

    # ==========================================
    # Option B: Title Reply Listener for Nameless Batches
    # ==========================================

    @app.on_message(filters.text & filters.private & ~filters.command(["start", "menu", "help", "status", "clear_bin", "library", "app", "cancel", "audit", "checkepisodes", "single_episodes", "synctmdb"]))
    async def title_reply_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_authorized(user_id):
            return

        if user_id not in _pending_title_batches:
            return

        pending = _pending_title_batches.pop(user_id)
        items = pending["items"]
        status_msg: Message = pending["status_msg"]

        custom_text = message.text.strip()
        # Parse season from the user's reply if provided (e.g., "Teach You A Lesson S2" or "Squid Game Season 1")
        custom_parsed = parse_filename(f"{custom_text}.S01E01.mkv")
        series_title = custom_parsed["title"]
        season_num = custom_parsed["season"] or 1

        # Check if user explicitly wrote "S2" or "Season 2"
        s_match = re.search(r"\b(?:[sS]|season[\s\-_]*)(\d{1,2})\b", custom_text, re.IGNORECASE)
        if s_match:
            season_num = int(s_match.group(1))

        # Update parsed metadata for all items in the batch
        for item in items:
            item["parsed"]["title"] = series_title
            item["parsed"]["season"] = season_num
            item["parsed"]["is_series"] = True
            ep_num = item["parsed"].get("episode") or 1
            item["parsed"]["clean_name"] = f"{series_title} S{season_num:02d}E{ep_num:02d}"

        await message.reply_text(f"✅ Set Series: **{series_title} — Season {season_num}** ({len(items)} episodes)!\nForwarding to bin channel now...")
        await process_series_batch(client, user_id, items, status_msg)

    # ==========================================
    # Media Batch Listener
    # ==========================================

    @app.on_message((filters.video | filters.document) & filters.private)
    async def media_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if not is_authorized(user_id):
            logger.warning(f"SECURITY: Unauthorized media upload attempt from user_id {user_id} (@{message.from_user.username or 'none'})")
            await message.reply_text("⛔ **Access Denied.**\nThis streaming bot is strictly restricted to FilmHouse Administrators.")
            return

        media = message.video or message.document
        if not media:
            return

        lock = get_user_lock(user_id)
        async with lock:
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

                btn = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"⚡ Finish & Process All {count} Episodes Now", callback_data="batch_flush_now")],
                    [InlineKeyboardButton("❌ Cancel Batch", callback_data="batch_cancel_now")],
                ])

                now = time.time()
                last_edit = _batch_buffers[user_id].get("last_status_edit", 0.0)
                if count == 1 or (now - last_edit >= 3.0) or (count % 10 == 0):
                    _batch_buffers[user_id]["last_status_edit"] = now
                    try:
                        if count > 1:
                            await status_msg.edit_text(
                                f"📥 **Batch Buffer: {count} episodes collected!**\n\n"
                                f"💡 *Keep forwarding files (50 to 100+ files supported).*\n\n"
                                f"When finished sending all files, tap below or wait 25s:",
                                reply_markup=btn
                            )
                        else:
                            await status_msg.edit_text(
                                f"⏳ *Received 1 file... Forwarding more episodes?*\n"
                                f"Send the rest now, or tap below to process:",
                                reply_markup=btn
                            )
                    except Exception:
                        pass

                # Debounce timer: wait 25.0 seconds after last forwarded message arrives to capture large multi-part batches
                if _batch_buffers[user_id]["task"]:
                    _batch_buffers[user_id]["task"].cancel()

                async def delayed_flush():
                    await asyncio.sleep(25.0)
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
