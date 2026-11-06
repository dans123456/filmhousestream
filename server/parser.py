import re
from typing import Dict, Any, Optional

# Common garbage tags to strip from titles
CLEANUP_TAGS = [
    r"@[\w\d_\-\.]+",  # Telegram handles like @pharaohsofm
    r"\b(2160p|4k|1080p|720p|480p|360p)\b",
    r"\b(bluray|blu-ray|web-dl|webrip|hdrip|hdtv|dvdrip|brrip|camrip|web)\b",
    r"\b(x264|x265|h264|h265|hevc|avc|10bit|8bit)\b",
    r"\b(aac|ac3|dts|dtshd|eac3|mp3|flac|ddp5\.1|dd5\.1|truehd|atmos)\b",
    r"\b(2ch|2\.0ch|2\.1ch|5\.1ch|6ch|8ch|stereo|mono|ch)\b",
    r"\b(dd5[\.\s]?1|ddp5[\.\s]?1|dd\+?5[\.\s]?1|dts[\.\s]?hd)\b",
    r"\b(nf|amzn|dsnp|dplus|hulu|atvp|max|stan|zee5|hotstar)\b",  # Streamer tags
    r"\b(yts|rarbg|psa|pahe|galaxytv|galaxyrg|tgx|cinevood|katmoviehd|mkvcinemas|nk)\b",
    r"\b(esub|esubs|multisubs|multi-sub|multi audio|dual audio|dual|hindi|english|eng|fi|fin|kor|jap|mandarin|org)\b",
    r"\b(repack|proper|remastered|extended|unrated|imax)\b",
    r"\b\d+(\.\d+)?\s*(mb|gb)\b",  # File sizes like 800mb, 1.4gb
    r"\b(iq|iqiyi)\b",  # iQIYI streaming platform tag
    r"\b(fil|filmh|filmhouse|telefilm|stream)\b",
    r"\b(film|movie|full movie)\b",  # Trailing descriptor words
    r"\[.*?\]",  # Bracketed group names like [TGx]
    r"\(.*?\b(1080p|720p|bluray|web)\b.*?\)",
]

# Patterns for Season and Episode detection
SERIES_PATTERNS = [
    # S01E02, S1E2, s01e02, S01.E02, S01 - E02
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]*[eE](?P<episode>\d{1,3})"),
    # S1 - 01, S01 - 02, S1 01, S1 - 1, S01.01 (e.g. Archive 81 S1 - 01)
    re.compile(r"\b[sS](?P<season>\d{1,2})[\s\.\-_]+(?P<episode>\d{1,3})\b"),
    # 1x02, 01x02
    re.compile(r"(?P<season>\d{1,2})[xX](?P<episode>\d{1,3})"),
    # Season 1 Episode 2, Season 01 Ep 2
    re.compile(r"[sS]eason[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*[eE]p(?:isode)?[\s\.\-_]*(?P<episode>\d{1,3})", re.IGNORECASE),
    # Just Episode / Ep 01 (assumes Season 1)
    re.compile(r"\b(?:[eE]p(?:isode)?|EP)[\s\.\-_]*(?P<episode>\d{1,3})\b"),
    # Standalone E01, E02 (assumes Season 1) (e.g. The.Remarried.Empress.E01.720p)
    re.compile(r"(?:^|[\s\.\-_])[eE](?P<episode>\d{1,3})(?:[\s\.\-_]|\b)"),
]

# Pattern for bare episode names with no show name (e.g. "01", "02", "Ep 03", "Episode 4", "S01E05")
BARE_EPISODE_REGEX = re.compile(r"^[\s\.\-_]*(?:[sS]\d{1,2}[\s\.\-_]*)?(?:[eE]p(?:isode)?|EP|\d{1,3})[\s\.\-_0-9]*$", re.IGNORECASE)

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

            # Extract title before the season/episode marker
            before_text = name[:m.start()].replace(".", " ").replace("_", " ")
            for tag_pattern in CLEANUP_TAGS + [r"\bfilmhouse\b"]:
                before_text = re.sub(tag_pattern, "", before_text, flags=re.IGNORECASE)
            before_text = re.sub(r"\s+", " ", before_text).strip(" -_")

            # CRITICAL FIX for "Episode 1 - Show Name" filenames:
            # If before_text is empty or bare (e.g. filename was "Episode 1 - Never Ending Summer"):
            # The real series title is in after_text!
            if (not before_text or BARE_EPISODE_REGEX.match(before_text)) and after_text:
                working_name = after_text
                episode_title = None
            else:
                working_name = before_text
                # Discard after_text if too short (<= 3 chars, e.g. "Fi", "Eng", "2ch") or purely numbers/acronyms
                if after_text and len(after_text) > 3 and not re.match(r"^[\d\s\-_]+$", after_text):
                    episode_title = " ".join([w.capitalize() for w in after_text.split()])
                else:
                    episode_title = None
            break

    # 3. Detect Year
    year = None
    year_match = YEAR_PATTERN.search(working_name)
    if year_match:
        year = int(year_match.group(1))
        # For movies (non-series): The clean title is everything before the release year
        if not is_series:
            before_year = working_name[:year_match.start()].strip(" -_()[]")
            if before_year and len(before_year) >= 2:
                working_name = before_year
            else:
                working_name = re.sub(rf"\b{year}\b", "", working_name)
        else:
            working_name = re.sub(rf"\b{year}\b", "", working_name)

    # 4. Clean up Title
    clean_title = working_name
    for tag_pattern in CLEANUP_TAGS + [r"\bfilmhouse\b"]:
        clean_title = re.sub(tag_pattern, "", clean_title, flags=re.IGNORECASE)

    # Strip empty parentheses and brackets: e.g. "()", "[]"
    clean_title = re.sub(r"\(\s*\)|\[\s*\]", "", clean_title)

    # Strip trailing scene release group names (e.g. "-PlayfulDarkness", "-Galaxy", "-eng")
    clean_title = re.sub(r"\s*-\s*[\w\d]{2,}$", "", clean_title)

    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -_")

    # Check if the title is actually empty or just a bare number / episode tag
    needs_title = False
    if not clean_title or BARE_EPISODE_REGEX.match(clean_title) or clean_title.isdigit():
        needs_title = True
        # If is_series was not caught yet (e.g. "01.mp4"), parse numeric episode
        if not is_series:
            num_match = re.search(r"\b(\d{1,3})\b", name)
            if num_match:
                is_series = True
                season = 1
                episode = int(num_match.group(1))
        clean_title = f"Episode {episode}" if episode else "Unnamed Series"
    else:
        # Title Case formatting for presentation
        clean_title = " ".join([word.capitalize() for word in clean_title.split()])

        # Common short aliases
        lower_t = clean_title.lower()
        if lower_t == "bel" and is_series:
            clean_title = "Bel-Air"
        elif lower_t in ("matchbox the", "the matchbox"):
            clean_title = "Matchbox"
        elif lower_t == "girls raised in the south":
            clean_title = "GRITS"
        elif lower_t == "hard matter":
            clean_title = "Kill Code"
        elif lower_t.startswith("nymphomaniac") and ("2" in lower_t or "ii" in lower_t):
            clean_title = "Nymphomaniac: Vol. II"
        elif lower_t in ("its okay", "it's okay"):
            clean_title = "It's Okay!"

        # Canonical Series Normalization (unifies truncated titles and missing apostrophes)
        norm_t = re.sub(r"['’`]", "", lower_t)
        norm_t = re.sub(r"&", "and", norm_t)
        norm_t = re.sub(r"\s+", " ", norm_t).strip()

        if norm_t.startswith("georgie and mandy"):
            clean_title = "Georgie & Mandy's First Marriage"
        elif norm_t.startswith("tyler perry") and "ruthless" in norm_t:
            clean_title = "Tyler Perry's Ruthless"
        elif norm_t.startswith("tyler perry") and "sista" in norm_t:
            clean_title = "Tyler Perry's Sistas"
        elif norm_t.startswith("tyler perry") and "oval" in norm_t:
            clean_title = "Tyler Perry's The Oval"

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
        "needs_title": needs_title,
    }
