import os
import json
import time
import re
import logging
import urllib.parse
from typing import Dict, List, Any, Optional
import aiohttp
import asyncio

import config
from bot.storage import get_tracked_files

logger = logging.getLogger("filmhouse.tmdb_auditor")

AUDIT_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "series_audit_cache.json")
_mem_audit_cache: Optional[Dict[str, Any]] = None
_tv_search_cache: Dict[str, Any] = {}
_movie_search_cache: Dict[str, Any] = {}
_tv_details_cache: Dict[int, Any] = {}
_is_auditing = False
_audit_status: Dict[str, Any] = {
    "is_running": False,
    "current_index": 0,
    "total_count": 0,
    "current_title": "",
    "incomplete_count": 0,
}


def format_episode_ranges(nums: List[int]) -> str:
    """Formats a list of episode numbers into clean ranges like 'Ep 2–16' or 'Ep 3, Ep 7–9'."""
    if not nums:
        return ""
    sorted_nums = sorted(list(set(nums)))
    ranges = []
    start = sorted_nums[0]
    prev = start
    for n in sorted_nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            if start == prev:
                ranges.append(f"{start}")
            else:
                ranges.append(f"{start}–{prev}")
            start = n
            prev = n
    if start == prev:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}–{prev}")
    return "Ep " + ", ".join(ranges)


def _ensure_data_dir():
    d = os.path.dirname(AUDIT_CACHE_FILE)
    if not os.path.exists(d):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


def load_cached_audit() -> Dict[str, Any]:
    """Returns the cached audit results from memory or disk instantly (0ms latency)."""
    global _mem_audit_cache, _audit_status
    data = None
    if _mem_audit_cache is not None:
        data = dict(_mem_audit_cache)
    else:
        _ensure_data_dir()
        if os.path.exists(AUDIT_CACHE_FILE):
            try:
                with open(AUDIT_CACHE_FILE, "r", encoding="utf-8") as f:
                    _mem_audit_cache = json.load(f)
                    data = dict(_mem_audit_cache)
            except Exception as e:
                logger.warning(f"Error reading audit cache: {e}")

    if not data:
        data = {
            "total_series": 0,
            "incomplete_count": 0,
            "incomplete_series": [],
            "last_audit_time": 0,
        }

    data["status"] = dict(_audit_status)
    return data


def save_cached_audit(data: Dict[str, Any]):
    global _mem_audit_cache
    _mem_audit_cache = data
    _ensure_data_dir()
    try:
        with open(AUDIT_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving audit cache to disk: {e}")


async def search_tmdb_tv(session: aiohttp.ClientSession, title: str) -> Optional[Dict[str, Any]]:
    """Searches TMDB for a TV series by title. Cached in memory."""
    clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
    # Strip any trailing number: e.g. "Embrace In The Dark Night 1" -> "Embrace In The Dark Night"
    clean_title = re.sub(r"[\s\.\-_]+\d+$", "", clean_title).strip()

    norm_key = re.sub(r"[^a-z0-9]+", " ", clean_title.lower()).strip()
    if not norm_key:
        return None

    if norm_key in _tv_search_cache:
        return _tv_search_cache[norm_key]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(clean_title)}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    best = results[0]
                    _tv_search_cache[norm_key] = best
                    return best
                
                # Fallback: if no results, try without punctuation / simplified
                simple_title = re.sub(r"['’`]", "", clean_title)
                if simple_title != clean_title:
                    fallback_url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(simple_title)}"
                    async with session.get(fallback_url, timeout=aiohttp.ClientTimeout(total=8)) as fb_resp:
                        if fb_resp.status == 200:
                            fb_data = await fb_resp.json()
                            fb_results = fb_data.get("results", [])
                            if fb_results:
                                best = fb_results[0]
                                _tv_search_cache[norm_key] = best
                                return best
    except Exception as e:
        logger.warning(f"TMDB TV search error for '{clean_title}': {e}")

    _tv_search_cache[norm_key] = None
    return None


async def search_tmdb_movie(session: aiohttp.ClientSession, title: str) -> Optional[Dict[str, Any]]:
    """Searches TMDB for a movie by title. Cached in memory."""
    clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+\d+$", "", clean_title).strip()

    norm_key = re.sub(r"[^a-z0-9]+", " ", clean_title.lower()).strip()
    if not norm_key:
        return None

    if norm_key in _movie_search_cache:
        return _movie_search_cache[norm_key]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote(clean_title)}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results:
                    best = results[0]
                    _movie_search_cache[norm_key] = best
                    return best

                simple_title = re.sub(r"['’`]", "", clean_title)
                if simple_title != clean_title:
                    fallback_url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote(simple_title)}"
                    async with session.get(fallback_url, timeout=aiohttp.ClientTimeout(total=8)) as fb_resp:
                        if fb_resp.status == 200:
                            fb_data = await fb_resp.json()
                            fb_results = fb_data.get("results", [])
                            if fb_results:
                                best = fb_results[0]
                                _movie_search_cache[norm_key] = best
                                return best
    except Exception as e:
        logger.warning(f"TMDB Movie search error for '{clean_title}': {e}")

    _movie_search_cache[norm_key] = None
    return None


async def get_tmdb_tv_details(session: aiohttp.ClientSession, tv_id: int) -> Optional[Dict[str, Any]]:
    """Fetches full TV show details including season episode counts. Cached in memory."""
    if tv_id in _tv_details_cache:
        return _tv_details_cache[tv_id]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={api_key}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                _tv_details_cache[tv_id] = data
                return data
    except Exception as e:
        logger.warning(f"TMDB TV details error for ID {tv_id}: {e}")

    return None


async def run_series_completeness_audit(force_tmdb: bool = True) -> Dict[str, Any]:
    """
    Scans all series in FilmHouse library:
    1. Collects all uploaded episodes per season.
    2. Identifies local missing episode gaps (e.g. has 1, 2, 4 -> missing 3).
    3. Cross-checks against TMDB to verify if the season has all expected episodes (e.g. 10/16 uploaded).
    4. Caches result to disk.
    """
    global _is_auditing, _audit_status
    if _is_auditing:
        return load_cached_audit()

    _is_auditing = True
    _audit_status["is_running"] = True
    _audit_status["current_index"] = 0
    _audit_status["total_count"] = 0
    _audit_status["current_title"] = ""
    _audit_status["incomplete_count"] = 0

    try:
        from server.stream_server import build_api_media_payload
        payload = build_api_media_payload()
        items = payload.get("items", [])

        # Group series by canonical key
        series_groups: Dict[str, Dict[str, Any]] = {}
        for it in items:
            if it.get("is_series") and it.get("series_title"):
                raw_title = str(it["series_title"]).strip()
                # Clean title of End / Finale
                clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", raw_title, flags=re.IGNORECASE).strip()
                clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
                k = re.sub(r"[^a-z0-9]+", "_", clean_title.lower()).strip("_")
                # Normalize trailing digits/part numbers from k (e.g. embrace_in_the_dark_night_1 -> embrace_in_the_dark_night)
                base_k = re.sub(r"_\d+$", "", k)
                if base_k and len(base_k) >= 3:
                    k = base_k
                if not k:
                    continue

                if k not in series_groups:
                    series_groups[k] = {
                        "canonical_key": k,
                        "title": clean_title,
                        "category": it.get("category", "series"),
                        "seasons": {},  # season_num -> list of episodes
                        "total_uploaded": 0,
                    }

                s_num = int(it.get("season") or 1)
                e_num = int(it.get("episode") or 1)
                end_e_num = int(it.get("end_episode")) if it.get("end_episode") else None
                if s_num not in series_groups[k]["seasons"]:
                    series_groups[k]["seasons"][s_num] = []

                if not any(x["episode"] == e_num for x in series_groups[k]["seasons"][s_num]):
                    series_groups[k]["seasons"][s_num].append({
                        "episode": e_num,
                        "end_episode": end_e_num,
                        "message_id": it.get("message_id"),
                        "file_name": it.get("file_name") or it.get("original_file_name"),
                        "quality": it.get("quality", "HD"),
                    })
                    series_groups[k]["total_uploaded"] += (end_e_num - e_num + 1) if (end_e_num and end_e_num > e_num) else 1

        incomplete_list = []
        api_key = getattr(config, "TMDB_API_KEY", "")
        total_series = len(series_groups)
        _audit_status["total_count"] = total_series

        async with aiohttp.ClientSession() as session:
            for idx, (k, group) in enumerate(series_groups.items(), start=1):
                title = group["title"]
                category = group["category"]
                total_uploaded = group["total_uploaded"]

                _audit_status["current_index"] = idx
                _audit_status["current_title"] = title
                _audit_status["incomplete_count"] = len(incomplete_list)

                # 1. Local Gap Analysis (Works 100% offline without TMDB)
                missing_gaps = []
                for s_num, eps in group["seasons"].items():
                    covered_set = set()
                    for e in eps:
                        ep_start = e["episode"]
                        ep_end = e.get("end_episode")
                        if ep_end and ep_end >= ep_start and ep_end < 900:
                            covered_set.update(range(ep_start, ep_end + 1))
                        elif ep_start < 900:
                            covered_set.add(ep_start)
                    ep_nums = sorted(list(covered_set))
                    if len(ep_nums) > 1:
                        # Check for gaps between min and max
                        min_ep = ep_nums[0]
                        max_ep = ep_nums[-1]
                        expected_range = set(range(min_ep, max_ep + 1))
                        missing = sorted(list(expected_range - covered_set))
                        if missing:
                            missing_gaps.append((s_num, missing))

                # 2. TMDB Cross-Check
                tmdb_data = None
                tmdb_id = None
                expected_by_season = {}

                if api_key and force_tmdb:
                    tmdb_res = await search_tmdb_tv(session, title)
                    if tmdb_res:
                        tmdb_id = tmdb_res.get("id")
                        details = await get_tmdb_tv_details(session, tmdb_id)
                        if details and "seasons" in details:
                            tmdb_data = details
                            for s in details["seasons"]:
                                s_no = s.get("season_number", 0)
                                if s_no > 0:  # Ignore specials (season 0)
                                    expected_by_season[s_no] = s.get("episode_count", 0)
                    # Breathing pause: 200ms between TMDB queries to be polite to TMDB API limits
                    await asyncio.sleep(0.2)

                # 3. Determine Incompleteness
                is_incomplete = False
                reasons = []
                status_summary = []

                # Check each recorded season against TMDB
                for s_num, eps in group["seasons"].items():
                    covered_set = set()
                    for e in eps:
                        ep_start = e["episode"]
                        ep_end = e.get("end_episode")
                        if ep_end and ep_end >= ep_start and ep_end < 900:
                            covered_set.update(range(ep_start, ep_end + 1))
                        elif ep_start < 900:
                            covered_set.add(ep_start)
                    ep_nums = sorted(list(covered_set))
                    uploaded_count = len(ep_nums)
                    max_uploaded_ep = ep_nums[-1] if ep_nums else len(eps)

                    if s_num in expected_by_season:
                        expected_count = expected_by_season[s_num]
                        if uploaded_count < expected_count:
                            is_incomplete = True
                            full_expected_set = set(range(1, expected_count + 1))
                            missing_all = sorted(list(full_expected_set - covered_set))
                            missing_str = format_episode_ranges(missing_all)
                            reasons.append(f"Season {s_num}: {uploaded_count}/{expected_count} uploaded (Missing: {missing_str})")
                            status_summary.append({
                                "season": s_num,
                                "uploaded": uploaded_count,
                                "expected": expected_count,
                                "missing_episodes": missing_all,
                                "missing_episodes_str": missing_str,
                                "missing_tail": [e for e in missing_all if e > max_uploaded_ep],
                            })
                    elif total_uploaded == 1:
                        # Check if TMDB has a movie or if no TV series was found on TMDB
                        is_movie = False
                        if api_key and force_tmdb:
                            movie_res = await search_tmdb_movie(session, title)
                            if movie_res:
                                is_movie = True

                        # If it's a confirmed movie or TMDB found no TV show, DO NOT classify as incomplete TV series!
                        if is_movie or not tmdb_res:
                            continue
                        else:
                            is_incomplete = True
                            reasons.append(f"Season {s_num}: Only 1 episode uploaded (Episode {max_uploaded_ep}).")
                            status_summary.append({
                                "season": s_num,
                                "uploaded": 1,
                                "expected": None,
                                "missing_episodes": [],
                                "missing_episodes_str": "",
                            })

                # Check if internal gaps were found
                if missing_gaps:
                    is_incomplete = True
                    for s_num, gaps in missing_gaps:
                        reasons.append(f"Season {s_num} has missing gaps: {format_episode_ranges(gaps)}")

                if is_incomplete:
                    incomplete_list.append({
                        "canonical_key": k,
                        "title": title,
                        "category": category,
                        "total_uploaded": total_uploaded,
                        "reasons": reasons,
                        "tmdb_id": tmdb_id,
                        "seasons_summary": status_summary,
                        "sample_file": group["seasons"].get(1, [{}])[0].get("file_name", ""),
                    })

        incomplete_list.sort(key=lambda x: x["title"].lower())
        _audit_status["incomplete_count"] = len(incomplete_list)
        _audit_status["is_running"] = False
        _audit_status["current_index"] = total_series

        audit_result = {
            "total_series": len(series_groups),
            "incomplete_count": len(incomplete_list),
            "incomplete_series": incomplete_list,
            "last_audit_time": int(time.time()),
            "status": dict(_audit_status),
        }
        save_cached_audit(audit_result)
        return audit_result

    except Exception as e:
        logger.error(f"Error during series completeness audit: {e}", exc_info=True)
        return load_cached_audit()
    finally:
        _is_auditing = False
        _audit_status["is_running"] = False

