import re
from typing import Dict, Any, Optional

# Common garbage tags to strip from titles
CLEANUP_TAGS = [
    r"\b(2160p|4k|1080p|720p|480p|360p)\b",
    r"\b(bluray|blu-ray|web-dl|webrip|hdrip|hdtv|dvdrip|brrip|camrip)\b",
    r"\b(x264|x265|h264|h265|hevc|avc|10bit|8bit)\b",
    r"\b(aac|ac3|dts|eac3|mp3|flac|ddp5\.1|dd5\.1|5\.1ch)\b",
    r"\b(yts|rarbg|psa|pahe|galaxytv|galaxyrg|tgx|cinevood|katmoviehd|mkvcinemas|nk)\b",
    r"\b(esub|esubs|multisubs|multi-sub|dual audio|hindi|english|org)\b",
    r"\b\d+(\.\d+)?\s*(mb|gb)\b",  # File sizes like 800mb, 1.4gb
    r"\b(filmhouse|telefilm|stream)\b",
    r"\[.*?\]",  # Bracketed group names like [TGx]
    r"\(.*?\b(1080p|720p|bluray|web)\b.*?\)",
]

# Patterns for Season and Episode detection
SERIES_PATTERNS = [
    # S01E02, S1E2, s01e02, S01.E02, S01 - E02
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]*[eE](?P<episode>\d{1,3})"),
    # 1x02, 01x02
    re.compile(r"(?P<season>\d{1,2})[xX](?P<episode>\d{1,3})"),
    # Season 1 Episode 2, Season 01 Ep 2
    re.compile(r"[sS]eason[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*[eE]p(?:isode)?[\s\.\-_]*(?P<episode>\d{1,3})", re.IGNORECASE),
    # Just Episode / Ep 01 (assumes Season 1)
    re.compile(r"\b(?:[eE]p(?:isode)?|EP)[\s\.\-_]*(?P<episode>\d{1,3})\b"),
]

QUALITY_PATTERN = re.compile(r"\b(2160p|4K|1080p|720p|480p)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_filename(raw_filename: str) -> Dict[str, Any]:
    """
    Parses a media filename to automatically identify:
    - Series vs Movie
    - Season & Episode numbers
    - Quality (1080p, 720p, etc.)
    - Cleaned Title & Release Year
    """
    if not raw_filename:
        return {
            "is_series": False,
            "title": "Unknown Media",
            "season": None,
            "episode": None,
            "quality": None,
            "year": None,
            "clean_name": "Unknown Media",
        }

    # Remove file extension (.mkv, .mp4, .avi, etc.)
    name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", raw_filename)
    
    # Replace dots, underscores, and dashes with spaces for analysis
    working_name = name.replace(".", " ").replace("_", " ")

    # 1. Detect Quality
    quality_match = QUALITY_PATTERN.search(working_name)
    if quality_match:
        matched_str = quality_match.group(1)
        quality = "4K" if matched_str.upper() in ("4K", "2160P") else matched_str.lower()
    else:
        quality = None

    # 2. Detect Season & Episode
    season = None
    episode = None
    episode_title = None
    is_series = False

    for pat in SERIES_PATTERNS:
        m = pat.search(name)
        if m:
            is_series = True
            groups = m.groupdict()
            if "season" in groups and groups["season"]:
                season = int(groups["season"])
            else:
                season = 1  # Default to Season 1 if only Episode is mentioned
            if "episode" in groups and groups["episode"]:
                episode = int(groups["episode"])
            
            # Extract subtitle / episode name after the SxxExx tag
            after_text = name[m.end():].replace(".", " ").replace("_", " ")
            for tag_pattern in CLEANUP_TAGS + [r"\bfilmhouse\b"]:
                after_text = re.sub(tag_pattern, "", after_text, flags=re.IGNORECASE)
            after_text = re.sub(r"\s+", " ", after_text).strip(" -_")
            if after_text:
                episode_title = " ".join([w.capitalize() for w in after_text.split()])

            # Cut title before the season/episode marker
            working_name = name[:m.start()].replace(".", " ").replace("_", " ")
            break

    # 3. Detect Year
    year = None
    year_match = YEAR_PATTERN.search(working_name)
    if year_match:
        year = int(year_match.group(1))
        # Remove year from working name to prevent duplicate title display
        working_name = re.sub(rf"\b{year}\b", "", working_name)

    # 4. Clean up Title
    clean_title = working_name
    for tag_pattern in CLEANUP_TAGS + [r"\bfilmhouse\b"]:
        clean_title = re.sub(tag_pattern, "", clean_title, flags=re.IGNORECASE)

    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -_")
    if not clean_title:
        clean_title = name.strip()

    # Title Case formatting for presentation
    clean_title = " ".join([word.capitalize() for word in clean_title.split()])

    # 5. Build Human-Readable Display Name
    if is_series:
        s_str = f"S{season:02d}" if season else "S01"
        e_str = f"E{episode:02d}" if episode else "E01"
        ep_sub = f" — {episode_title}" if episode_title else ""
        clean_name = f"{clean_title} {s_str}{e_str}{ep_sub}"
        if quality:
            clean_name += f" ({quality})"
    else:
        year_str = f" ({year})" if year else ""
        qual_str = f" [{quality}]" if quality else ""
        clean_name = f"{clean_title}{year_str}{qual_str}"

    return {
        "is_series": is_series,
        "title": clean_title,
        "season": season,
        "episode": episode,
        "episode_title": episode_title,
        "quality": quality,
        "year": year,
        "clean_name": clean_name,
        "original_filename": raw_filename,
    }
