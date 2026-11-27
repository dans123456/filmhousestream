import os
import json
import time
import re
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import asyncio

import config

logger = logging.getLogger("filmhouse.tmdb_auditor")

AUDIT_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "series_audit_cache.json")
COMPLETED_SEASONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "completed_seasons.json")
_mem_audit_cache: Optional[Dict[str, Any]] = None
_tv_search_cache: Dict[str, Any] = {}
_movie_search_cache: Dict[str, Any] = {}
_tv_details_cache: Dict[int, Any] = {}
_tv_season_cache: Dict[Tuple[int, int], Any] = {}
_is_auditing = False
_audit_status: Dict[str, Any] = {
    "is_running": False,
    "current_index": 0,
    "total_count": 0,
    "current_title": "",
    "incomplete_count": 0,
}

PLACEHOLDER_TITLES = {
    "mp4", "mkv", "avi", "ts", "webm", "mov", "flv", "wmv",
    "video", "series", "tv series", "episode", "unknown",
    "unknown media", "unnamed", "unnamed series", "sample", "file",
}


def get_completed_seasons() -> Dict[str, bool]:
    """Returns a dict of series/season keys manually marked complete by the admin."""
    _ensure_data_dir()
    if os.path.exists(COMPLETED_SEASONS_FILE):
        try:
            with open(COMPLETED_SEASONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    return {k: True for k in data}
        except Exception as e:
            logger.warning(f"Error reading completed_seasons.json: {e}")
    return {}


def toggle_completed_season(key: str, complete: Optional[bool] = None) -> bool:
    """Toggles or sets the completion status for a series key or season key."""
    _ensure_data_dir()
    current = get_completed_seasons()
    if complete is None:
        if key in current and current[key]:
            del current[key]
            new_state = False
        else:
            current[key] = True
            new_state = True
    elif complete:
        current[key] = True
        new_state = True
    else:
        if key in current:
            del current[key]
        new_state = False

    try:
        tmp_path = COMPLETED_SEASONS_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, COMPLETED_SEASONS_FILE)
    except Exception as e:
        logger.error(f"Error saving completed_seasons.json: {e}")

    # Update in-memory audit cache so next load reflects updated completed state immediately
    global _mem_audit_cache
    if _mem_audit_cache and isinstance(_mem_audit_cache, dict):
        _mem_audit_cache["completed_seasons"] = current
        if new_state and "__s" not in key:
            _mem_audit_cache["incomplete_series"] = [
                s for s in _mem_audit_cache.get("incomplete_series", [])
                if s.get("canonical_key") != key
            ]
            _mem_audit_cache["incomplete_count"] = len(_mem_audit_cache["incomplete_series"])

    return new_state


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
            ranges.append(f"{start}" if start == prev else f"{start}–{prev}")
            start = n
            prev = n
    ranges.append(f"{start}" if start == prev else f"{start}–{prev}")
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
    data["completed_seasons"] = get_completed_seasons()
    return data


def save_cached_audit(data: Dict[str, Any]):
    global _mem_audit_cache
    _mem_audit_cache = data
    _ensure_data_dir()
    try:
        tmp_path = AUDIT_CACHE_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, AUDIT_CACHE_FILE)
    except Exception as e:
        logger.error(f"Error saving audit cache to disk: {e}")


def invalidate_series_audit(series_name: Optional[str] = None):
    """Clears cached audit data so re-audit runs fresh."""
    global _mem_audit_cache, _tv_search_cache, _tv_season_cache
    if not series_name:
        _mem_audit_cache = None
        _tv_search_cache.clear()
        _tv_season_cache.clear()
        return
    norm = re.sub(r"[^a-z0-9]+", "_", series_name.lower()).strip("_")
    for k in list(_tv_search_cache.keys()):
        if norm in k:
            _tv_search_cache.pop(k, None)
    if _mem_audit_cache and "incomplete_series" in _mem_audit_cache:
        _mem_audit_cache["incomplete_series"] = [
            s for s in _mem_audit_cache.get("incomplete_series", [])
            if norm not in s.get("canonical_key", "")
        ]
        _mem_audit_cache["incomplete_count"] = len(_mem_audit_cache["incomplete_series"])


def _normalize_tmdb_compare(text: str) -> str:
    """Normalizes a title for strict TMDB candidate scoring."""
    s = re.sub(r"['’`]", "", str(text or "").lower())
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_compare_prefixes(norm_text: str) -> str:
    """Strips leading articles and studio possessives for secondary title comparison."""
    s = re.sub(r"^(?:the|a|an)\s+", "", norm_text).strip()
    s = re.sub(r"^(?:marvels|marvel\s+studios|dcs|tyler\s+perrys)\s+", "", s).strip()
    return s


def _is_placeholder_title(norm_space_key: str) -> bool:
    if not norm_space_key or len(norm_space_key) < 2:
        return True
    if norm_space_key in PLACEHOLDER_TITLES:
        return True
    return False


async def search_tmdb_tv(session: aiohttp.ClientSession, title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Searches TMDB for a TV series with strict title similarity + year confidence scoring.
    Rejects low-confidence matches (< 70 points) to prevent false missing-episode alerts.
    """
    if not year:
        m_yr = re.search(r"\b(19\d{2}|20\d{2})\b", title)
        if m_yr:
            year = int(m_yr.group(1))

    clean_title = re.sub(r"\b(19\d{2}|20\d{2})\b", "", title).strip()
    clean_title = re.sub(r"[\(\)\[\]]", " ", clean_title).strip()
    clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+(?!of\b)", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"\s+", " ", clean_title).strip()

    norm_key = _normalize_tmdb_compare(clean_title)
    if _is_placeholder_title(norm_key):
        return None

    q_core = _strip_compare_prefixes(norm_key) or norm_key
    q_tokens = set(q_core.split())

    cache_key = f"{norm_key}_{year}" if year else norm_key
    if cache_key in _tv_search_cache:
        return _tv_search_cache[cache_key]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    def rank_tv_results(results: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], float]:
        if not results:
            return None, 0.0

        def score(res: Dict[str, Any]) -> float:
            pts = 0.0
            r_name = _normalize_tmdb_compare(res.get("name") or "")
            r_orig = _normalize_tmdb_compare(res.get("original_name") or "")
            r_core = _strip_compare_prefixes(r_name) or r_name
            r_orig_core = _strip_compare_prefixes(r_orig) or r_orig
            air_year_str = (res.get("first_air_date") or "")[:4]

            # Explicit priority pin for Netflix Archive 81 (TMDB ID 126947)
            if norm_key == "archive 81" and res.get("id") == 126947:
                return 500.0

            matched_title = False
            if (r_name and r_name == norm_key) or (r_orig and r_orig == norm_key):
                pts += 150.0
                matched_title = True
            elif (r_core and r_core == q_core) or (r_orig_core and r_orig_core == q_core):
                pts += 120.0
                matched_title = True
            else:
                # Subtitle / colon prefix match (requires >= 6 chars and >= 2 tokens)
                best_prefix = False
                for cand in (r_core, r_orig_core):
                    if not cand:
                        continue
                    shorter_len = min(len(q_core), len(cand))
                    if shorter_len >= 6 and len(q_tokens) >= 2 and (cand.startswith(q_core + " ") or q_core.startswith(cand + " ")):
                        best_prefix = True
                        break
                if best_prefix:
                    pts += 85.0
                    matched_title = True
                else:
                    # Token Jaccard similarity
                    best_jac = 0.0
                    is_subset_match = False
                    for cand in (r_core, r_orig_core):
                        if not cand:
                            continue
                        t_set = set(cand.split())
                        union = q_tokens | t_set
                        if not union:
                            continue
                        jac = len(q_tokens & t_set) / len(union)
                        if jac > best_jac:
                            best_jac = jac
                            is_subset_match = (len(q_tokens) >= 2 and q_tokens <= t_set)
                    if best_jac >= 0.75:
                        pts += 75.0
                        matched_title = True
                    elif best_jac >= 0.6 and is_subset_match:
                        pts += 65.0
                        matched_title = True

            if not matched_title:
                # Do not allow popularity/year alone to pass confidence gate
                return 0.0

            # Year scoring
            if year and air_year_str.isdigit():
                yr_diff = abs(int(air_year_str) - int(year))
                if yr_diff == 0:
                    pts += 100.0
                elif yr_diff == 1:
                    pts += 35.0
                elif yr_diff >= 3:
                    pts -= 60.0

            # Popularity tie-breaker
            try:
                pop = float(res.get("popularity") or 0.0)
                pts += min(pop / 10.0, 20.0)
            except Exception:
                pass

            return pts

        scored = sorted(((score(r), r) for r in results), key=lambda pair: pair[0], reverse=True)
        top_score, top_res = scored[0]
        return top_res, top_score

    MIN_CONFIDENCE_SCORE = 70.0

    query_variants = []
    if year:
        query_variants.append(
            f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(clean_title)}&first_air_date_year={year}"
        )
    query_variants.append(
        f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(clean_title)}"
    )
    stripped_title = re.sub(r"[\s\.\-_]+[0-9]$", "", clean_title).strip()
    if stripped_title and stripped_title != clean_title and not _is_placeholder_title(_normalize_tmdb_compare(stripped_title)):
        query_variants.append(
            f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(stripped_title)}"
        )
    simple_title = re.sub(r"['’`]", "", clean_title)
    if simple_title != clean_title:
        query_variants.append(
            f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={urllib.parse.quote(simple_title)}"
        )

    try:
        for url in query_variants:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    best, best_score = rank_tv_results(data.get("results", []))
                    if best and best_score >= MIN_CONFIDENCE_SCORE:
                        _tv_search_cache[cache_key] = best
                        return best
    except Exception as e:
        logger.warning(f"TMDB TV search error for '{clean_title}': {e}")

    _tv_search_cache[cache_key] = None
    return None


async def search_tmdb_movie(session: aiohttp.ClientSession, title: str) -> Optional[Dict[str, Any]]:
    """Searches TMDB for a movie by title with strict match validation. Cached in memory."""
    clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+(?!of\b)", "", title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
    clean_title = re.sub(r"[\s\.\-_]+\d+$", "", clean_title).strip()

    norm_key = _normalize_tmdb_compare(clean_title)
    if _is_placeholder_title(norm_key):
        return None

    if norm_key in _movie_search_cache:
        return _movie_search_cache[norm_key]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    q_core = _strip_compare_prefixes(norm_key) or norm_key
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={urllib.parse.quote(clean_title)}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                for res in data.get("results", []):
                    r_t = _strip_compare_prefixes(_normalize_tmdb_compare(res.get("title") or ""))
                    r_o = _strip_compare_prefixes(_normalize_tmdb_compare(res.get("original_title") or ""))
                    if r_t == q_core or r_o == q_core:
                        _movie_search_cache[norm_key] = res
                        return res
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


async def get_tmdb_season_details(session: aiohttp.ClientSession, tv_id: int, season_num: int) -> Optional[Dict[str, Any]]:
    """Fetches TMDB season episode list to count strictly AIRED episodes (ignoring future/unaired ones)."""
    c_key = (int(tv_id), int(season_num))
    if c_key in _tv_season_cache:
        return _tv_season_cache[c_key]

    api_key = getattr(config, "TMDB_API_KEY", "")
    if not api_key:
        return None

    url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_num}?api_key={api_key}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                data = await resp.json()
                _tv_season_cache[c_key] = data
                return data
    except Exception as e:
        logger.warning(f"TMDB Season details error for TV {tv_id} S{season_num}: {e}")

    _tv_season_cache[c_key] = None
    return None


def get_auditor_canonical_key(raw_title: str) -> str:
    """
    Produces a unified canonical key for grouping TV series episodes.
    Synchronized identically with frontend getCanonicalSeriesKey() in library_template.py
    so backend audit keys and WebApp folder keys always match 1:1.
    """
    if not raw_title:
        return ""
    norm = re.sub(r"['’`]", "", str(raw_title).lower())
    norm = norm.replace("&", " and ")
    norm = re.sub(r"[^a-z0-9\s]", " ", norm)
    norm = re.sub(r"\s+", "_", norm.strip())

    # Strip leading season or "series_" prefix (e.g. "s01_the_early_spring", "series_one_of_us_is_lying")
    norm = re.sub(r"^s\d{1,2}_+", "", norm)
    norm = re.sub(r"^(?:tv_)?series_+(?!of_unfortunate)", "", norm)

    # Universal article stripper: "the_", "a_", "an_"
    norm = re.sub(r"^(?:the|a|an)_+", "", norm)

    # Strip End / Finale markers (NEVER strip "End of ...")
    norm = re.sub(r"^(?:the_)?(?:end|finale|final)_(?!of_)", "", norm)
    norm = re.sub(r"_+(?:the_)?(?:end|finale|final)$", "", norm)

    # Proactively strip trailing part, season, volume, year, resolution, codec, and release descriptors
    for _ in range(4):
        norm = re.sub(r"_(?:season|s|s\d{1,2}|part|pt|vol|volume|book|chapter|cdrama|kdrama|series|miniseries|tv|complete|full|hd|sd|hq|fhd|uhd|4k|2160p|1440p|1080p|720p|576p|540p|480p|360p|240p|264|265|x264|x265|h264|h265|fi|fil|film|filmh|filmho|filmhou|filmhous|filmhouse|telegram|d)(?:_\d+)*$", "", norm)
        norm = re.sub(r"_\d{4}$", "", norm)

    # Normalize trailing single digits like _1, _2 and strip A.K.A. alt-titles
    norm = re.sub(r"_[0-9]$", "", norm)
    norm = re.sub(r"_a_k_a_.*$", "", norm).strip("_")

    # Known franchise aliases (100% synced with frontend getCanonicalSeriesKey)
    if norm == "forever" or norm.startswith("forever_"):
        return "forever"
    if norm.startswith("avatar_aang") or norm.startswith("avatar_the_last_airbender") or norm.startswith("legend_of_aang") or "last_airbender" in norm:
        return "avatar_the_last_airbender"
    if "ossan_newbie_adventurer" in norm:
        return "the_ossan_newbie_adventurer"
    if "undefeated_bahamut" in norm:
        return "undefeated_bahamut_chronicle"
    if "knights_of_the_apocalypse" in norm:
        return "four_knights_of_the_apocalypse"
    if "let_this_grieving_soul_retire" in norm:
        return "let_this_grieving_soul_retire"
    if norm in ("gods_game", "gods_games_we_play"):
        return "gods_games_we_play"
    if norm.startswith("irregular_at_magic"):
        return "the_irregular_at_magic_high_school"
    if norm.startswith("fog_hill_of_five"):
        return "fog_hill_of_five_elements"
    if "marvel_disk_wars" in norm:
        return "marvel_disk_wars_the_avengers"
    if "agents_of_s_h_i_e_l" in norm or "agent_of_shield" in norm:
        return "marvels_agents_of_shield_slingshot" if "slingshot" in norm else "marvels_agents_of_shield"
    if "moon_girl_and_devil_dinosaur" in norm:
        return "marvels_moon_girl_and_devil_dinosaur"
    if "avengers_earths_mightiest_heroes" in norm:
        return "avengers_earths_mightiest_heroes"
    if "avengers_assemble" in norm or "avengers_ultron_revolution" in norm or "avengers_secret_wars" in norm:
        return "marvels_avengers_assemble"
    if "x_men_97" in norm:
        return "x_men_97"
    if "silver_surfer" in norm and "animated" in norm:
        return "silver_surfer_the_animated_series"
    if "end_of_the_fucking_world" in norm or "end_of_the_f_ing_world" in norm or norm.startswith("end_of_the_f"):
        return "the_end_of_the_f_ing_world"
    if "legend_of_korra" in norm:
        return "the_legend_of_korra"
    if "one_of_us_is_lying" in norm or "on_of_us_is_lying" in norm or norm == "of_us_is_lying":
        return "one_of_us_is_lying"
    if norm.startswith("wandavision"):
        return "wandavision"
    if "casa_de_papel" in norm or "money_heist" in norm:
        return "money_heist"
    if "tales_of_ladybug" in norm or "miraculous" in norm:
        return "miraculous_tales_of_ladybug_and_cat_noir"
    if "baker_and_the_beauty" in norm:
        return "the_baker_and_the_beauty"
    if "on_my_block" in norm:
        return "on_my_block"
    if "love_other_than_yours" in norm:
        return "a_love_other_than_yours"
    if norm.startswith("girls_hostel"):
        return "girls_hostel"
    if "generator_rex" in norm:
        return "generator_rex"
    if "trinkets" in norm:
        return "trinkets"
    if "alrawabi_school_for_girls" in norm:
        return "alrawabi_school_for_girls"
    if norm.startswith("macgyver"):
        return "macgyver"
    if norm.startswith("love_in_disguise"):
        return "love_in_disguise"
    if norm.startswith("maxton_hall"):
        return "maxton_hall"
    if norm in ("mother_of_the_bride", "mother_of_the_brides", "mother_of_brides"):
        return "mother_of_the_brides"
    if norm.startswith("a_good_day_to_be_a_dog") or "good_day_to_be_a_dog" in norm:
        return "a_good_day_to_be_a_dog"
    if norm.startswith("hidden_love"):
        return "hidden_love"
    if norm == "arcane" or norm.startswith("arcane_league_of_legends"):
        return "arcane"
    if norm.startswith("flex_x_cop") or norm.startswith("flexxcop") or norm.startswith("flex_cop") or "flex_x_cop" in norm or "flex_cop" in norm:
        return "flex_x_cop"
    if "mr_bean" in norm and "animated" in norm:
        return "mr_bean_the_animated_series"
    if norm.startswith("mr_bean") or norm.startswith("mrbean") or ("bean" in norm and "lord_of_the_beans" not in norm):
        return "mr_bean"
    if norm.startswith("georgie_and_mandy"):
        return "georgie_and_mandys_first_marriage"
    if "ruthless" in norm:
        return "tyler_perrys_ruthless"
    if "sista" in norm:
        return "tyler_perrys_sistas"
    if "oval" in norm:
        return "tyler_perrys_the_oval"
    if "zatima" in norm:
        return "tyler_perrys_zatima"
    if norm.startswith("wings") or ("wing" in norm and ("innovat" in norm or "initiat" in norm)):
        return "the_wings_initiative"
    if norm.startswith("low_priest"):
        return "the_low_priest"
    if norm.startswith("koleoso"):
        return "koleoso"
    if norm in ("black_ish", "blackish", "black"):
        return "black_ish"
    if norm in ("grown_ish", "grownish"):
        return "grown_ish"
    if norm in ("mixed_ish", "mixedish"):
        return "mixed_ish"
    if norm in ("utd", "under_the_dome"):
        return "under_the_dome"
    if norm in ("tvd", "vampire_diaries", "the_vampire_diaries", "the"):
        return "the_vampire_diaries"
    if norm.startswith("noobees"):
        return "noobees"
    if "adthe_bible" in norm or "ad_the_bible" in norm or "a_d_the_bible" in norm:
        return "a_d_the_bible_continues"
    if "kaibutsu" in norm or norm == "my_little_monster":
        return "my_little_monster"
    if "fixie" in norm or norm == "the_fixies":
        return "the_fixies"
    if norm.startswith("veggietales"):
        return "veggietales"
    if "anikulapo" in norm:
        return "anikulapo_rise_of_the_spectre"
    if norm.startswith("aiyetoro"):
        return "aiyetoro_town"
    if norm.startswith("testament"):
        return "the_testaments"
    if "aang" in norm or "airbender" in norm:
        return "avatar_the_last_airbender"
    if "nero_the_assassin" in norm:
        return "nero_the_assassin"

    return norm.strip("_")


async def run_series_completeness_audit(force_tmdb: bool = True) -> Dict[str, Any]:
    """
    Strict TMDB + local gap completeness audit across all series in the library:
    - Rejects low-confidence TMDB matches so local/broken titles never get mismatched.
    - Counts strictly AIRED TMDB episodes (future/unaired episodes never flag as missing).
    - Recognizes 2-in-1 combined cartoon segments / half-hour K-Dramas and Multi-Cour Anime packing.
    - Checks missing entire prior seasons (S1..max_S-1), missing Ep 1, and internal gaps.
    - Always populates seasons_summary for every incomplete entry so none vanish in the WebApp.
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

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        from server.stream_server import build_api_media_payload
        payload = build_api_media_payload()
        items = payload.get("items", [])

        # Group series by canonical key
        series_groups: Dict[str, Dict[str, Any]] = {}
        for it in items:
            if it.get("is_series") and it.get("series_title"):
                raw_title = str(it["series_title"]).strip()
                item_year = it.get("year")
                tmdb_id = it.get("tmdb_id")

                clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+(?!of\b)", "", raw_title, flags=re.IGNORECASE).strip()
                clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE).strip()
                k = get_auditor_canonical_key(clean_title)
                if not k:
                    continue

                if k == "macgyver":
                    item_year = 2016
                    tmdb_id = 67133
                    clean_title = "MacGyver"
                elif k == "forever":
                    item_year = 2025
                    tmdb_id = 248394
                    clean_title = "Forever"
                elif k == "avatar_the_last_airbender":
                    clean_title = "Avatar: The Last Airbender"
                    if not tmdb_id:
                        tmdb_id = 82452
                elif k == "love_in_disguise":
                    clean_title = "Love in Disguise"
                    if not item_year:
                        item_year = 2026

                if k not in series_groups:
                    series_groups[k] = {
                        "canonical_key": k,
                        "title": clean_title,
                        "year": item_year,
                        "tmdb_id": tmdb_id,
                        "category": it.get("category", "series"),
                        "seasons": {},
                        "total_uploaded": 0,
                    }
                else:
                    if item_year and not series_groups[k].get("year"):
                        series_groups[k]["year"] = item_year
                    if tmdb_id and not series_groups[k].get("tmdb_id"):
                        series_groups[k]["tmdb_id"] = tmdb_id
                    if clean_title and len(clean_title) > len(series_groups[k]["title"]):
                        series_groups[k]["title"] = clean_title

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
        completed_seasons = get_completed_seasons()
        api_key = getattr(config, "TMDB_API_KEY", "")
        total_series = len(series_groups)
        _audit_status["total_count"] = total_series

        def _season_covered_set(eps_list: List[Dict[str, Any]]) -> set:
            cov = set()
            for e in eps_list:
                ep_s = e["episode"]
                ep_e = e.get("end_episode")
                if ep_s == 999:
                    continue
                if ep_e and ep_e >= ep_s and ep_e < 2000:
                    cov.update(range(ep_s, ep_e + 1))
                elif ep_s < 2000:
                    cov.add(ep_s)
            return cov

        async with aiohttp.ClientSession() as session:
            for idx, (k, group) in enumerate(series_groups.items(), start=1):
                title = group["title"]
                year = group.get("year")
                category = group["category"]
                total_uploaded = group["total_uploaded"]

                _audit_status["current_index"] = idx
                _audit_status["current_title"] = f"{title} ({year})" if year else title
                _audit_status["incomplete_count"] = len(incomplete_list)

                # Skip if entire series was marked complete by admin
                if completed_seasons.get(k):
                    continue

                norm_space_t = _normalize_tmdb_compare(title)
                if _is_placeholder_title(norm_space_t):
                    placeholder_summary = []
                    for s_no in sorted(group["seasons"].keys()):
                        if completed_seasons.get(f"{k}__s{s_no}"):
                            continue
                        cnt = len(_season_covered_set(group["seasons"][s_no])) or len(group["seasons"][s_no])
                        placeholder_summary.append({
                            "season": s_no,
                            "uploaded": cnt,
                            "expected": None,
                            "missing_episodes": [],
                            "missing_episodes_str": "",
                            "issue_type": "broken_title",
                        })
                    if placeholder_summary:
                        first_eps = next(iter(group["seasons"].values()), [{}])
                        incomplete_list.append({
                            "canonical_key": k,
                            "title": title,
                            "year": year,
                            "category": category,
                            "total_uploaded": total_uploaded,
                            "reasons": ["Broken/placeholder series title — tap ✏️ Rename to set the real show title."],
                            "tmdb_id": None,
                            "seasons_summary": placeholder_summary,
                            "issue_types": ["broken_title"],
                            "sample_file": first_eps[0].get("file_name", "") if first_eps else "",
                        })
                    continue

                # 1. TMDB Cross-Check (Strictly matching high-confidence results & aired episodes)
                tmdb_data = None
                tmdb_id = None
                tmdb_res = None
                raw_season_meta: Dict[int, Dict[str, Any]] = {}

                if api_key and force_tmdb:
                    if group.get("tmdb_id"):
                        tmdb_id = int(group["tmdb_id"])
                        details = await get_tmdb_tv_details(session, tmdb_id)
                        if details and "seasons" in details:
                            tmdb_data = details
                    else:
                        tmdb_res = await search_tmdb_tv(session, title, year=year)
                        if tmdb_res:
                            tmdb_id = tmdb_res.get("id")
                            details = await get_tmdb_tv_details(session, tmdb_id)
                            if details and "seasons" in details:
                                tmdb_data = details

                    if tmdb_data and "seasons" in tmdb_data:
                        for s in tmdb_data["seasons"]:
                            s_no = s.get("season_number") or 0
                            s_ep_cnt = s.get("episode_count") or 0
                            s_air = (s.get("air_date") or "")[:10]
                            if s_no <= 0 or s_ep_cnt <= 0:
                                continue
                            # Skip strictly future / unscheduled seasons
                            if not s_air or s_air > today_str:
                                continue
                            raw_season_meta[s_no] = s

                    await asyncio.sleep(0.06)

                async def _get_aired_ep_set(tv_id_val: int, s_no_val: int, fallback_cnt: int) -> set:
                    s_det = await get_tmdb_season_details(session, tv_id_val, s_no_val)
                    await asyncio.sleep(0.05)
                    if s_det and isinstance(s_det.get("episodes"), list) and s_det["episodes"]:
                        aired = {
                            int(ep["episode_number"])
                            for ep in s_det["episodes"]
                            if (ep.get("episode_number") or 0) > 0
                            and ep.get("air_date")
                            and str(ep["air_date"])[:10] <= today_str
                        }
                        return aired
                    # Fallback cap if currently airing and season details unavailable
                    cap = fallback_cnt
                    if tmdb_data:
                        last_ep = tmdb_data.get("last_episode_to_air") or {}
                        if last_ep.get("season_number") == s_no_val and (tmdb_data.get("in_production") or tmdb_data.get("next_episode_to_air")):
                            last_no = int(last_ep.get("episode_number") or 0)
                            if 0 < last_no < cap:
                                cap = last_no
                    return set(range(1, cap + 1)) if cap > 0 else set()

                is_incomplete = False
                reasons: List[str] = []
                status_summary: List[Dict[str, Any]] = []

                # Multi-cour Anime Season 1 packing check:
                # If TMDB packs S1+S2+... into Season 1 ONLY, validate sequentially across uploaded cours.
                multi_cour_handled = False
                if (
                    tmdb_id
                    and set(raw_season_meta.keys()) == {1}
                    and len(group["seasons"]) > 1
                    and 1 in group["seasons"]
                ):
                    raw_s1_cnt = int(raw_season_meta[1].get("episode_count") or 0)
                    aired_s1_set = await _get_aired_ep_set(tmdb_id, 1, raw_s1_cnt)
                    expected_total = len(aired_s1_set)
                    combined_covered = set()
                    offset = 0
                    all_cours_contiguous = True
                    for s_no_iter in sorted(group["seasons"].keys()):
                        cov = _season_covered_set(group["seasons"][s_no_iter])
                        if not cov:
                            all_cours_contiguous = False
                            break
                        s_max = max(cov)
                        if cov != set(range(1, s_max + 1)):
                            all_cours_contiguous = False
                        for ep_v in cov:
                            combined_covered.add(offset + ep_v)
                        offset += s_max

                    if expected_total > 0 and combined_covered == aired_s1_set:
                        multi_cour_handled = True
                    elif expected_total > 0 and all_cours_contiguous and len(combined_covered) >= expected_total:
                        multi_cour_handled = True
                    elif expected_total > 0 and len(combined_covered) > len(_season_covered_set(group["seasons"][1])):
                        # Partially complete multi-cour show: evaluate combined missing list cleanly once
                        missing_cour = sorted(aired_s1_set - combined_covered)
                        if not missing_cour:
                            multi_cour_handled = True
                        elif not completed_seasons.get(f"{k}__s1"):
                            is_incomplete = True
                            max_comb = max(combined_covered) if combined_covered else 0
                            missing_str = format_episode_ranges(missing_cour)
                            has_gap = any(m < max_comb for m in missing_cour)
                            reasons.append(
                                f"All Cours Combined: {len(combined_covered)}/{expected_total} aired uploaded (Missing: {missing_str})"
                            )
                            status_summary.append({
                                "season": 1,
                                "uploaded": len(combined_covered),
                                "expected": expected_total,
                                "missing_episodes": missing_cour,
                                "missing_episodes_str": missing_str,
                                "missing_tail": [e for e in missing_cour if e > max_comb],
                                "issue_type": "gap" if has_gap else "tail",
                            })
                            multi_cour_handled = True

                # 2. Check each uploaded season strictly
                if not multi_cour_handled:
                    for s_num in sorted(group["seasons"].keys()):
                        s_key = f"{k}__s{s_num}"
                        if completed_seasons.get(s_key):
                            continue

                        eps = group["seasons"][s_num]
                        covered_set = _season_covered_set(eps)
                        ep_nums = sorted(list(covered_set))
                        uploaded_count = len(ep_nums)
                        min_uploaded_ep = ep_nums[0] if ep_nums else 1
                        max_uploaded_ep = ep_nums[-1] if ep_nums else len(eps)

                        if s_num in raw_season_meta and tmdb_id:
                            raw_expected = int(raw_season_meta[s_num].get("episode_count") or 0)
                            if uploaded_count < raw_expected:
                                expected_set = await _get_aired_ep_set(tmdb_id, s_num, raw_expected)
                            else:
                                expected_set = set(range(1, raw_expected + 1))

                            expected_count = len(expected_set)
                            if expected_count == 0:
                                continue

                            # 2-in-1 Cartoon / K-Drama combined-episode check (e.g. Spidey 25 full files vs 50 segments)
                            if (
                                uploaded_count >= 6
                                and covered_set == set(range(1, uploaded_count + 1))
                                and expected_count == 2 * uploaded_count
                            ):
                                continue

                            missing_all = sorted(list(expected_set - covered_set))
                            local_expected = set(range(1, max_uploaded_ep + 1)) if min_uploaded_ep <= 5 else set(range(min_uploaded_ep, max_uploaded_ep + 1))
                            local_gaps = sorted(list(local_expected - covered_set))

                            if missing_all:
                                # Detect offset-cumulative season numbering (e.g. X-Men TAS Ep 63..76 stored under S05 where TMDB expects Ep 1..14)
                                if (
                                    len(missing_all) >= expected_count - 1
                                    and min_uploaded_ep > expected_count
                                    and len(covered_set) > 1
                                ):
                                    shifted_cov = {e - min_uploaded_ep + 1 for e in covered_set}
                                    shifted_missing = sorted(list(expected_set - shifted_cov))
                                    if len(shifted_missing) < len(missing_all):
                                        missing_all = shifted_missing
                                        max_uploaded_ep = max(shifted_cov) if shifted_cov else 0
                                        local_gaps = sorted(list(set(range(1, max_uploaded_ep + 1)) - shifted_cov))

                                if not missing_all and not local_gaps:
                                    continue

                                is_incomplete = True
                                combined_missing = sorted(set(missing_all) | set(local_gaps))
                                missing_str = format_episode_ranges(combined_missing)
                                has_gap = any(m < max_uploaded_ep for m in combined_missing) or bool(local_gaps)
                                reasons.append(
                                    f"Season {s_num}: {uploaded_count}/{expected_count} aired uploaded (Missing: {missing_str})"
                                )
                                status_summary.append({
                                    "season": s_num,
                                    "uploaded": uploaded_count,
                                    "expected": expected_count,
                                    "missing_episodes": combined_missing,
                                    "missing_episodes_str": missing_str,
                                    "missing_tail": [e for e in combined_missing if e > max_uploaded_ep],
                                    "issue_type": "gap" if has_gap else "tail",
                                })
                            elif local_gaps:
                                is_incomplete = True
                                missing_str = format_episode_ranges(local_gaps)
                                reasons.append(
                                    f"Season {s_num}: Missing {missing_str} (uploaded up to Ep {max_uploaded_ep})"
                                )
                                status_summary.append({
                                    "season": s_num,
                                    "uploaded": uploaded_count,
                                    "expected": max_uploaded_ep,
                                    "missing_episodes": local_gaps,
                                    "missing_episodes_str": missing_str,
                                    "missing_tail": [],
                                    "issue_type": "gap",
                                })
                        else:
                            # Not matched on TMDB (or season beyond TMDB count): strict local continuity check
                            if len(ep_nums) > 1:
                                local_expected = (
                                    set(range(1, max_uploaded_ep + 1))
                                    if min_uploaded_ep <= 10
                                    else set(range(min_uploaded_ep, max_uploaded_ep + 1))
                                )
                                local_gaps = sorted(list(local_expected - covered_set))
                                if local_gaps:
                                    is_incomplete = True
                                    missing_str = format_episode_ranges(local_gaps)
                                    reasons.append(
                                        f"Season {s_num}: Missing {missing_str} (uploaded up to Ep {max_uploaded_ep})"
                                    )
                                    status_summary.append({
                                        "season": s_num,
                                        "uploaded": uploaded_count,
                                        "expected": max_uploaded_ep,
                                        "missing_episodes": local_gaps,
                                        "missing_episodes_str": missing_str,
                                        "missing_tail": [],
                                        "issue_type": "gap",
                                    })
                            elif total_uploaded == 1:
                                is_movie = False
                                if api_key and force_tmdb:
                                    movie_res = await search_tmdb_movie(session, title)
                                    if movie_res:
                                        is_movie = True
                                if not is_movie and (tmdb_res or tmdb_data):
                                    is_incomplete = True
                                    reasons.append(f"Season {s_num}: Only 1 episode uploaded (Episode {max_uploaded_ep}).")
                                    status_summary.append({
                                        "season": s_num,
                                        "uploaded": 1,
                                        "expected": None,
                                        "missing_episodes": [],
                                        "missing_episodes_str": "",
                                        "missing_tail": [],
                                        "issue_type": "single",
                                    })

                # 3. Missing Entire Prior/Intermediate Seasons Check (e.g. has S2/S3 but missing S1)
                if tmdb_id and raw_season_meta and group["seasons"]:
                    max_uploaded_s = max(group["seasons"].keys())
                    for s_prior in range(1, max_uploaded_s):
                        if s_prior in group["seasons"] or s_prior not in raw_season_meta:
                            continue
                        if completed_seasons.get(f"{k}__s{s_prior}"):
                            continue
                        raw_prior_cnt = int(raw_season_meta[s_prior].get("episode_count") or 0)
                        aired_prior = await _get_aired_ep_set(tmdb_id, s_prior, raw_prior_cnt)
                        aired_prior_cnt = len(aired_prior)
                        if aired_prior_cnt > 0:
                            is_incomplete = True
                            prior_list = sorted(list(aired_prior))
                            prior_str = format_episode_ranges(prior_list)
                            reasons.append(
                                f"Season {s_prior}: Entire season missing (0/{aired_prior_cnt} episodes uploaded)"
                            )
                            status_summary.append({
                                "season": s_prior,
                                "uploaded": 0,
                                "expected": aired_prior_cnt,
                                "missing_episodes": prior_list,
                                "missing_episodes_str": prior_str,
                                "missing_tail": prior_list,
                                "issue_type": "missing_season",
                            })

                if is_incomplete and status_summary:
                    status_summary.sort(key=lambda s: s.get("season") or 0)
                    issue_types = sorted(list({s.get("issue_type", "tail") for s in status_summary}))
                    first_season_eps = next(iter(group["seasons"].values()), [{}])
                    incomplete_list.append({
                        "canonical_key": k,
                        "title": title,
                        "year": year,
                        "category": category,
                        "total_uploaded": total_uploaded,
                        "reasons": reasons,
                        "tmdb_id": tmdb_id,
                        "seasons_summary": status_summary,
                        "issue_types": issue_types,
                        "sample_file": first_season_eps[0].get("file_name", "") if first_season_eps else "",
                    })

        incomplete_list.sort(key=lambda x: x["title"].lower())
        _audit_status["incomplete_count"] = len(incomplete_list)
        _audit_status["is_running"] = False
        _audit_status["current_index"] = total_series

        audit_result = {
            "total_series": len(series_groups),
            "incomplete_count": len(incomplete_list),
            "incomplete_series": incomplete_list,
            "completed_seasons": completed_seasons,
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
