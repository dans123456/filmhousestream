import re
from typing import Dict, Any, Optional

# Common garbage tags to strip from titles
CLEANUP_TAGS = [
    r"@[\w\d_\-\.]+",  # Telegram handles like @pharaohsofm
    r"\b(2160p|4k|1080p|1080i|720p|576p|480p|360p|240p|bd1080p|bd720p|bd480p)\b",
    r"\b(uhd|fhd|hd|sd|hq)\b",
    r"\b(hd-in|hd_in|hdin|hd-tc|hdtc|hd-cam|hdcam|hd-ts|hdts|hdtv|hdrip)\b",
    r"\b(bluray|blu-ray|web-dl|webdl|web-rip|webrip|dvdrip|brrip|bdrip|camrip|web|dvd)\b",
    r"\b(x264|x265|h264|h265|hevc|avc|10bit|8bit|hdr|hdr10|hdr10\+|dovi|dv)\b",
    r"\b(aac|ac3|dts|dtshd|eac3|mp3|flac|ddp5\.1|dd5\.1|ddp|dd|truehd|atmos)\b",
    r"\b(2ch|2\.0ch|2\.1ch|5\.1ch|6ch|8ch|stereo|mono|ch)\b",
    r"\b(dd5[\.\s]?1|ddp5[\.\s]?1|dd\+?5[\.\s]?1|dts[\.\s]?hd)\b",
    r"\b(nf|amzn|dsnp|dplus|hulu|atvp|max|stan|zee5|hotstar)\b",  # Streamer tags
    r"\b(yts|rarbg|psa|pahe|galaxytv|galaxyrg|tgx|cinevood|katmoviehd|mkvcinemas|nk)\b",
    r"\b(esub|esubs|multisubs|multi-sub|multi audio|dual audio|dual|dubbed|subbed)\b",
    r"\b(hindi|english|eng|hin|kor|jap|japanese|korean|mandarin|chi|org)\b",
    r"\b(repack|proper|remastered|extended|unrated|imax|complete|final)\b",
    r"\b\d+(\.\d+)?\s*(mb|gb)\b",  # File sizes like 800mb, 1.4gb
    r"\b(iq|iqiyi)\b",  # iQIYI streaming platform tag
    r"\b(fil|filmh|filmhouse|telefilm|stream)\b",
    r"\b(film|movie|full movie)\b",  # Trailing descriptor words
    r"\[.*?\]",  # Bracketed group names like [TGx]
    r"\(.*?\b(1080p|720p|bluray|web)\b.*?\)",
]

# Words that should NEVER be considered episode titles on their own
GARBAGE_EPISODE_WORDS = {
    "hd", "in", "hd in", "hd-in", "sd", "hq", "uhd", "fhd", "4k", "720p", "1080p", "480p",
    "web", "web dl", "webdl", "web rip", "webrip", "bluray", "hdtv", "dvdrip", "brrip",
    "x264", "x265", "hevc", "h264", "h265", "aac", "ac3", "dts", "ddp", "atmos", "truehd",
    "hindi", "eng", "english", "dual", "dual audio", "esub", "esubs", "sub", "dub", "dubbed",
    "filmhouse", "filmh", "stream", "telefilm", "galaxy", "tgx", "psa", "pahe", "rarbg",
    "2ch", "6ch"
}

FIXIES_PHRASES = (
    "remote and the barcode", "robot and friction", "pen and noliks cube", "refrigerator and the airbag",
    "oven and the magnifying glass", "paper and the knots", "microphone and the mixer", "music box and modelling clay",
    "magnet and the doorbell", "magic wand and the chain reaction", "magifying glass and the zipper", "lever and the microwave",
    "lie detector and tubes", "keyboard and the catapult", "globe and the disguise", "instructions and the shadow play",
    "electric kettle and the hair dryer", "flashlight and the prosthesis", "drain and the motion sensor", "and the keycard",
    "draftsmen and the internet", "compass and the washing machine", "constructor set", "combination lock and the wires",
    "cartoon and the alarm", "cell phone and the night light", "can and the piggy bank", "balloon and the batteries",
    "armor and the dog", "baby monitor", "alarm clock and the talking doll", "aquarium and the drum", "level and the camera",
    "sms and the laboratory", "chess and the stain", "invisible ink and the gramophone", "candy and the chick",
    "tideesh", "why do fixies", "who are the fixies", "what is friction", "where do fixies", "pack-o-mat",
    "dangerous place for fixies", "meet professor eugenius", "how do talking dolls", "teach their kids", "save electricity",
    "whipped cream and the kaleidoscope", "video call and the bee", "vacuum and the manipulator", "toothbrush and the antenna",
    "tools and the fixiphone", "thermometer and the pack o mat", "thermos and the electric train", "stapler and the suction cup",
    "spare part and the team", "short circuit and gps", "solar battery and the crowbar", "scale and the mirror",
    "screws and the ecotester", "different kinds of robots", "different uses for sensors", "how does a drain trap work",
    "how does a microphone work", "how does a mobile phone work", "how does a motion sensor work",
    "how does a remote work", "how does a vacuum work", "how does an alarm clock work",
    "how does a keycard work", "how does a lever work", "our world without friction",
    "what cant you put in a microwave", "hockeys our game", "my smart phone", "telephone is ringing"
)

VEGGIETALES_PHRASES = (
    "penniless princess", "lyle the kindly viking", "stnicholas", "pistachio", "wheres god when im scared",
    "sweetpeabeauty", "sillysongcountdown", "girl who became queen", "autotainment", "star of christmas",
    "toy that saved christmas", "sumo of the opera", "little joe", "rack shack and benny", "sheerluck holmes",
    "moe and the big exit", "madam blueberry", "samsons hairbrush", "lord of the beans", "josh and the big wall",
    "king george and the ducky", "great pie war", "forgive them", "are you my neighbor", "giant pickle",
    "easter carol", "snoodles tale"
)

# Patterns for Season and Episode detection
SERIES_PATTERNS = [
    # Multi-episode: S01E01-E02, S01E01-02, S01E01E02, S01E01 - E02
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]*[eE](?P<episode>\d{1,3})[\s\.\-_]*(?:-|to|e|E)[\s\.\-_]*(?:[eE])?(?P<end_episode>\d{1,3})"),
    # 1x01-02, 01x01-02
    re.compile(r"(?P<season>\d{1,2})[xX](?P<episode>\d{1,3})[\s\.\-_]*(?:-|to)[\s\.\-_]*(?P<end_episode>\d{1,3})"),
    # S01E02, S1E2, s01e02, S01.E02, S01 - E02
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]*[eE](?P<episode>\d{1,3})"),
    # S1 - 01, S01 - 02, S1 01, S1 - 1, S01.01 (e.g. Archive 81 S1 - 01)
    re.compile(r"\b[sS](?P<season>\d{1,2})[\s\.\-_]+(?P<episode>\d{1,3})\b"),
    # 1x02, 01x02
    re.compile(r"(?P<season>\d{1,2})[xX](?P<episode>\d{1,3})"),
    # Season 1 Episode 2, Season 01 Ep 2
    re.compile(r"[sS]eason[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*[eE]p(?:isode)?[\s\.\-_]*(?P<episode>\d{1,3})", re.IGNORECASE),
    # S01 Part 1, S1 Part 2, S0 Part 1, S01.Part1
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]*(?:part|pt)[\s\.\-_]*(?P<episode>\d{1,3})", re.IGNORECASE),
    # Season 1 Part 2
    re.compile(r"[sS]eason[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*(?:part|pt)[\s\.\-_]*(?P<episode>\d{1,3})", re.IGNORECASE),
    # Standalone Part / Pt (assumes Season 1): e.g. "Part 1", "Pt 2"
    re.compile(r"\b(?:part|pt)[\s\.\-_]*(?P<episode>\d{1,3})\b", re.IGNORECASE),
    # Spanish/Portuguese/French: T1 Episodio 01, T02 Episodio 60, T1 Ep 01, T01E02, T1 01
    re.compile(r"\b[tT](?P<season>\d{1,2})[\s\.\-_]*(?:episodio|capitulo|episode|ep|e)?[\s\.\-_]*(?P<episode>\d{1,3})\b", re.IGNORECASE),
    # Temporada 1 Episodio 02
    re.compile(r"\b[tT]emporada[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]*(?:episodio|capitulo|episode|ep|e)?[\s\.\-_]*(?P<episode>\d{1,3})\b", re.IGNORECASE),
    # Anime Dash-Episode format: e.g. "Tonari.No.Kaibutsu-kun.-.13.Bd1080p.F.mkv", "Show Name - 01"
    re.compile(r"[\s\.\-_]+-[\s\.\-_]+(?P<episode>\d{1,3})(?:[\s\.\-_]|\b)"),
    # Just Episode / Ep 01 (assumes Season 1)
    re.compile(r"\b(?:[eE]p(?:isode)?|EP)[\s\.\-_]*(?P<episode>\d{1,3})\b"),
    # Standalone E01, E02 (assumes Season 1) (e.g. The.Remarried.Empress.E01.720p)
    re.compile(r"(?:^|[\s\.\-_])[eE](?P<episode>\d{1,3})(?:[\s\.\-_]|\b)"),
    # S01 Special, Season 1 Special, S1 Specials, S01 OVA
    re.compile(r"[sS](?P<season>\d{1,2})[\s\.\-_]+(?P<special>special|specials|sp|ova)\b", re.IGNORECASE),
    re.compile(r"[sS]eason[\s\.\-_]*(?P<season>\d{1,2})[\s\.\-_]+(?P<special>special|specials|sp|ova)\b", re.IGNORECASE),
]

# Pattern for bare episode names with no show name (e.g. "01", "02", "Ep 03", "Episode 4", "S01E05")
BARE_EPISODE_REGEX = re.compile(r"^[\s\.\-_]*(?:[sS]\d{1,2}[\s\.\-_]*)?(?:[eE]p(?:isode)?|EP|\d{1,3})[\s\.\-_0-9]*$", re.IGNORECASE)

QUALITY_PATTERN = re.compile(r"\b(2160p|4K|1080p|720p|480p|bd1080p|bd720p|bd480p)\b", re.IGNORECASE)
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

    # Normalize common letter 'o' / 'O' typos in S01E02 (e.g. So1e03 -> S01E03, S01eO3 -> S01E03)
    name = re.sub(r"\b[sS][oO](\d{1,2})", r"S0\1", name)
    name = re.sub(r"[eE][oO](\d{1,2})", r"E0\1", name)
    
    # Replace dots, underscores, and dashes with spaces for analysis
    working_name = name.replace(".", " ").replace("_", " ")

    # 1. Detect Quality
    quality_match = QUALITY_PATTERN.search(working_name)
    if quality_match:
        matched_str = quality_match.group(1).lower()
        if matched_str in ("4k", "2160p"):
            quality = "4K"
        elif "1080p" in matched_str:
            quality = "1080p"
        elif "720p" in matched_str:
            quality = "720p"
        elif "480p" in matched_str:
            quality = "480p"
        else:
            quality = matched_str
    else:
        quality = None

    # 2. Detect Season & Episode
    season = None
    episode = None
    end_episode = None
    episode_title = None
    is_series = False

    for pat in SERIES_PATTERNS:
        m = pat.search(name)
        if m:
            is_series = True
            groups = m.groupdict()
            if "season" in groups and groups["season"]:
                season = int(groups["season"])
                if season == 0:
                    season = 1  # S0 with episode or part is almost always a Season 1 typo
            else:
                season = 1  # Default to Season 1 if only Episode is mentioned
            if "episode" in groups and groups["episode"]:
                episode = int(groups["episode"])
            if "special" in groups and groups["special"]:
                episode = 0
                episode_title = "Special"
            if "end_episode" in groups and groups["end_episode"]:
                end_episode = int(groups["end_episode"])
            
            # Extract subtitle / episode name after the SxxExx tag
            after_text = name[m.end():].replace(".", " ").replace("_", " ")
            for tag_pattern in CLEANUP_TAGS + [r"\bfilmhouse\b"]:
                after_text = re.sub(tag_pattern, "", after_text, flags=re.IGNORECASE)
            # Repeatedly strip trailing descriptor words like -hd, -in, etc.
            after_text = re.sub(r"[\s\.\-_]+(hd|in|sd|hq|uhd|fhd|4k|1080p|720p|480p|x264|x265|hevc|aac|ac3|hindi|eng|esub|tgx|galaxy|filmhouse|filmh)$", "", after_text, flags=re.IGNORECASE)
            after_text = re.sub(r"\s+", " ", after_text).strip(" -_")

            # If multi-episode, strip any remaining secondary episode marker from after_text (e.g. "E02", "-E02", "02")
            if end_episode:
                after_text = re.sub(rf"^(?:[\s\.\-_]*(?:e|ep|episode)?[\s\.\-_]*0?{end_episode}\b)", "", after_text, flags=re.IGNORECASE).strip(" -_")

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
                # Check if after_text is pure release junk or empty
                words = after_text.lower().split()
                all_garbage = len(words) > 0 and all(w in GARBAGE_EPISODE_WORDS for w in words)
                if (
                    after_text
                    and len(after_text) > 3
                    and not re.match(r"^[\d\s\-_]+$", after_text)
                    and not all_garbage
                    and after_text.lower() not in GARBAGE_EPISODE_WORDS
                ):
                    episode_title = " ".join([w.capitalize() for w in after_text.split()])
                else:
                    episode_title = None
            break

    # 2b. Episodic detection for bare numeric filenames, End/Finale markers, and franchise series
    if not is_series:
        lower_name = name.lower()
        # Check for Finale / End markers: e.g. "End Hotel Del Luna", "End Mr Queen", "Hotel Del Luna End"
        end_lead_match = re.search(r"^(?:the\s+)?(?:end|finale|final\s+episode)[\s\.\-_]+(.+)$", name, re.IGNORECASE)
        end_trail_match = re.search(r"^(.+?)[\s\.\-_]+(?:the\s+)?(?:end|finale|final\s+episode)(?:[\s\.\-_]+.*)?$", name, re.IGNORECASE)
        movie_end_exceptions = ("avengers end", "pirates end", "world's end", "worlds end", "dead end", "deep end", "week end", "weekend")

        if end_lead_match:
            is_series = True
            season = 1
            num_m = re.search(r"\b(?:ep|episode|e)?\s*0?(\d{1,3})\b", name, re.IGNORECASE)
            episode = int(num_m.group(1)) if num_m else 999
            working_name = end_lead_match.group(1).replace(".", " ").replace("_", " ").strip()
        elif end_trail_match and not any(ex in lower_name for ex in movie_end_exceptions):
            is_series = True
            season = 1
            num_m = re.search(r"\b(?:ep|episode|e)?\s*0?(\d{1,3})\b", name, re.IGNORECASE)
            episode = int(num_m.group(1)) if num_m else 999
            working_name = end_trail_match.group(1).replace(".", " ").replace("_", " ").strip()
        else:
            # Universal episode detector: allows quality or format tags after the number (e.g. Flex X Cop 01 720p)
            bare_ep_match = re.search(r"^(.*?)(?:[\s\.\-_]+(?:ep|episode|part|pt|e)?[\s\.\-_]*)(\d{1,3})(?:[\s\.\-_]+(?:1080p|720p|480p|4k|2160p|bluray|webrip|web-dl|web|hdrip|hd|hevc|x264|x265|aac|ac3|hindi|eng|dual|filmhouse|filmh|\b).*)?$", name, re.IGNORECASE)
            if bare_ep_match:
                pot_title = bare_ep_match.group(1).replace(".", " ").replace("_", " ").strip()
                pot_num = int(bare_ep_match.group(2))
                lower_pot = pot_title.lower()
                has_ep_keyword = bool(re.search(r"[\s\.\-_]+(?:ep|episode|part|pt|e)[\s\.\-_]*\d{1,3}", name, re.IGNORECASE))
                is_known_series = any(k in lower_pot for k in ("flex", "bean", "koleoso", "yoruba", "fixie", "veggie", "noobee"))
                if has_ep_keyword or is_known_series or (len(pot_title) >= 2 and 1 <= pot_num <= 300 and not (1920 <= pot_num <= 2030)):
                    is_series = True
                    season = 1
                    episode = pot_num
                    working_name = pot_title
            elif any(k in lower_name for k in ("flex x cop", "flexxcop", "mr bean", "mr. bean")):
                is_series = True
                season = 1
                num_match = re.search(r"\b(\d{1,3})\b", name)
                episode = int(num_match.group(1)) if num_match else 1
                if "flex" in lower_name:
                    working_name = "Flex X Cop"
                elif "bean" in lower_name:
                    working_name = "Mr. Bean"

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

    # Strip trailing scene release group names (e.g. "-PlayfulDarkness", "-Galaxy", "-eng"), preserving titles like Black-ish
    clean_title = re.sub(r"\s+-\s*(?!ish\b)[\w\d]{2,}$", "", clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r"-(?!ish\b)[\w\d]{3,}$", "", clean_title, flags=re.IGNORECASE)

    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -_")

    if is_series:
        # Strip any leading or trailing End / Finale keywords
        clean_title = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", clean_title, flags=re.IGNORECASE)
        # Universal Series Title Cleanup: strip trailing batch/part/volume tokens, release tags, and years
        for _ in range(3):
            clean_title = re.sub(r"\(\s*(part|pt|vol|volume|book|chapter)\s*\d*\s*\)", "", clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r"[\s\.\-_]+(part|pt|vol|volume|book|chapter)\s*\d*$", "", clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r"[\s\.\-_]+(kdrama|cdrama|k-drama|c-drama|series|tv|miniseries|mini-series|complete|full)$", "", clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r"[\s\.\-_]+\(?\d{4}\)?$", "", clean_title, flags=re.IGNORECASE)
            clean_title = clean_title.strip(" -_")

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

        # Acronyms, compound titles, and collapsed aliases
        collapsed = re.sub(r"[^a-z0-9]", "", lower_t)
        if collapsed == "utd":
            clean_title = "Under the Dome"
            is_series = True
        elif collapsed == "tvd":
            clean_title = "The Vampire Diaries"
            is_series = True
        elif collapsed == "blackish" or (collapsed == "black" and is_series and season and season > 1):
            clean_title = "Black-ish"
            is_series = True
        elif collapsed == "grownish":
            clean_title = "Grown-ish"
            is_series = True
        elif collapsed == "mixedish":
            clean_title = "Mixed-ish"
            is_series = True

        # Check The Fixies (bilingual Russian/English episodic titles)
        lower_raw = raw_filename.lower()
        norm_raw = re.sub(r"[\._\-]+", " ", lower_raw).strip()
        norm_clean = re.sub(r"['’`]", "", norm_raw)
        if (
            "fixie" in lower_t
            or "fixies" in lower_t
            or "tideesh" in lower_t
            or any(p in norm_clean for p in FIXIES_PHRASES)
            or any(p in lower_t for p in FIXIES_PHRASES)
            or (re.search(r"[\u0400-\u04FF]", raw_filename) and any(w in norm_clean for w in ("remote", "robot", "pen", "refrigerator", "oven", "paper", "microphone", "magnet", "lever", "keyboard", "globe", "flashlight", "drain", "compass", "alarm", "aquarium", "chess", "candy", "screws", "sensor", "vacuum", "tools", "thermometer", "thermos", "stapler", "battery", "mirror")))
        ):
            if not episode_title and clean_title != "The Fixies":
                episode_title = clean_title
            clean_title = "The Fixies"
            is_series = True
            if not season:
                season = 1
            if not episode:
                episode = 1

        # Check VeggieTales (franchise movies and episodes)
        elif lower_raw.startswith("veggietales") or any(p in norm_clean for p in VEGGIETALES_PHRASES) or any(p in lower_t for p in VEGGIETALES_PHRASES):
            clean_title = "VeggieTales"
            is_series = True
            if not season:
                season = 1
            if not episode:
                episode = 1

        # Canonical Series Normalization (unifies truncated titles and missing apostrophes)
        norm_t = re.sub(r"['’`]", "", lower_t)
        norm_t = re.sub(r"&", "and", norm_t)
        norm_t = re.sub(r"\s+", " ", norm_t).strip()

        if norm_t.startswith("georgie and mandy"):
            clean_title = "Georgie & Mandy's First Marriage"
        elif "ruthless" in norm_t:
            clean_title = "Tyler Perry's Ruthless"
        elif "sista" in norm_t:
            clean_title = "Tyler Perry's Sistas"
        elif "the oval" in norm_t or norm_t == "oval":
            clean_title = "Tyler Perry's The Oval"
        elif "zatima" in norm_t:
            clean_title = "Tyler Perry's Zatima"
        elif (
            norm_t.startswith("wings")
            or norm_t.startswith("the wings")
            or ("wing" in norm_t and ("innovat" in norm_t or "initiat" in norm_t))
            or norm_t in ("wings", "the wings", "the wings initiative", "wings initiative", "wings innovative")
        ):
            clean_title = "The Wings Initiative"
        elif norm_t.startswith("the low priest") or norm_t.startswith("low priest"):
            clean_title = "The Low Priest"
        elif "koleoso" in norm_t:
            clean_title = "Koleoso"
            is_series = True
            if not season:
                season = 1
        elif norm_t == "friends":
            clean_title = "Friends"
            is_series = True
            # Special handling for Friends Season 8 two-part finale ("The One Where Rachel Has a Baby", Ep 23 & 24)
            # Frequently tagged in rip packs as Friends.S0.part1 / Friends.S0.part2
            lower_raw = raw_filename.lower()
            if re.search(r"\bpart[\s\.\-_]*1\b", lower_raw) or re.search(r"part1\b", lower_raw):
                season = 8
                episode = 23
                episode_title = "The One Where Rachel Has a Baby: Part 1"
            elif re.search(r"\bpart[\s\.\-_]*2\b", lower_raw) or re.search(r"part2\b", lower_raw):
                season = 8
                episode = 24
                episode_title = "The One Where Rachel Has a Baby: Part 2"
        elif lower_t in ("the", "the series") and is_series:
            clean_title = "The Vampire Diaries"
        elif "tonari no kaibutsu" in norm_t or "kaibutsu" in norm_t:
            clean_title = "Tonari no Kaibutsu-kun"
            is_series = True
            if not season:
                season = 1
        elif "adthe bible" in norm_t or "ad the bible" in norm_t or "a d the bible" in norm_t:
            clean_title = "A.D. The Bible Continues"
            is_series = True
        elif "nero the assassin" in norm_t or "néro the assassin" in lower_t:
            clean_title = "Néro The Assassin"
            is_series = True
        elif norm_t.startswith("the testaments") or norm_t in ("testament", "testaments"):
            clean_title = "The Testaments"
            is_series = True
        elif norm_t.startswith("aiyetoro"):
            clean_title = "Aiyetoro Town"
            is_series = True
        elif norm_t.startswith("anikulapo"):
            clean_title = "Aníkúlápó: Rise of the Spectre"
            is_series = True
        elif "legend of aang" in norm_t or "aang t l a" in norm_t or "aang tla" in norm_t:
            clean_title = "Avatar Aang: The Last Airbender"
            is_series = True
        elif norm_t.startswith("noobees"):
            clean_title = "Noobees"
            is_series = True

    # 5. Build Human-Readable Display Name
    if is_series:
        s_str = f"S{season:02d}" if season else "S01"
        if end_episode:
            e_str = f"E{episode:02d}-E{end_episode:02d}"
        else:
            e_str = f"E{episode:02d}" if episode else "E01"
        ep_sub = f" — {episode_title}" if episode_title else ""
        clean_name = f"{clean_title} {s_str}{e_str}{ep_sub}"
        if quality:
            clean_name += f" ({quality})"
    else:
        year_str = f" ({year})" if year else ""
        qual_str = f" [{quality}]" if quality else ""
        clean_name = f"{clean_title}{year_str}{qual_str}"

    category = detect_category(raw_filename, clean_title, is_series)

    result = {
        "is_series": is_series,
        "title": clean_title,
        "season": season,
        "episode": episode,
        "end_episode": end_episode,
        "episode_title": episode_title,
        "quality": quality,
        "year": year,
        "clean_name": clean_name,
        "original_filename": raw_filename,
        "needs_title": needs_title,
        "category": category,
    }
    result["golden_name"] = build_golden_filename(result, raw_filename)
    return result


def build_golden_filename(parsed: dict, original_filename: str) -> str:
    """Builds the pure Golden Dot standard filename for movies and series."""
    ext_match = re.search(r"\.([a-zA-Z0-9]{2,4})$", original_filename or "")
    ext = f".{ext_match.group(1).lower()}" if ext_match else ".mkv"

    clean_title = re.sub(r"[^\w\s\-]", "", parsed.get("title") or "Unknown Media").strip()
    dots_title = ".".join(clean_title.split())

    if parsed.get("is_series"):
        s_num = parsed.get("season") or 1
        e_num = parsed.get("episode") or 1
        s_tag = f"S{s_num:02d}E{e_num:02d}"
        q_tag = f".{parsed['quality']}" if parsed.get("quality") else ""
        return f"{dots_title}.{s_tag}{q_tag}{ext}"
    else:
        y_tag = f".{parsed['year']}" if parsed.get("year") else ""
        q_tag = f".{parsed['quality']}" if parsed.get("quality") else ""
        return f"{dots_title}{y_tag}{q_tag}{ext}"


def detect_category(raw_filename: str, clean_title: str, is_series: bool) -> str:
    """
    Auto-detects media category:
    - movies (Hollywood & Global Movies)
    - series (Western & Hollywood TV Series)
    - anime (Anime Series & Movies)
    - kdrama (K-Drama & Asian Drama)
    - african (African Cinema & Nollywood/Ghallywood)
    - bollywood (Bollywood & Indian Cinema)
    - cartoons (Cartoons & Western Animation)
    """
    text = f"{raw_filename} {clean_title}".lower()

    # 1. Anime
    anime_patterns = [
        r"\[(subsplease|erai-raws|judas|asw|horriblesubs|commie|ember|kayo|neohevc|cleo|pas)\]",
        r"\b(anime|manga|otaku|tonari no kaibutsu|kaibutsu-kun|kaibutsu kun)\b",
        r"\b(jap|japanese)\b",
        r"\b(solo leveling|demon slayer|kimetsu no yaiba|jujutsu kaisen|attack on titan|shingeki no kyojin)\b",
        r"\b(naruto|boruto|one piece|bleach|chainsaw man|death note|my hero academia|boku no hero)\b",
        r"\b(dragon ball|black clover|hunter x hunter|spy x family|tokyo ghoul|vinland saga|blue lock)\b",
        r"\b(kaiju no|dan da dan|dandadan|frieren|wind breaker|oshi no ko|sword art online|overlord)\b",
        r"\b(fullmetal alchemist|haikyuu|mob psycho|one punch man|hells paradise|jigokuraku)\b",
    ]
    for pat in anime_patterns:
        if re.search(pat, text):
            return "anime"

    # 2. K-Drama & Asian Drama
    kdrama_patterns = [
        r"\b(kdrama|k-drama|cdrama|c-drama|korean drama|asian drama)\b",
        r"\b(the remarried empress|queen of tears|crash landing on you|squid game|all of us are dead)\b",
        r"\b(the glory|vincenzo|itaewon class|descendants of the sun|goblin|business proposal)\b",
        r"\b(twinkling watermelon|marry my husband|lovely runner|hotel del luna|strong girl)\b",
        r"\b(weightlifting fairy|true beauty|extraordinary attorney woo|sweet home|moving|pyramid game)\b",
        r"\b(a good day to be a dog|hidden love|mr queen|mr. queen|flex x cop|flexxcop)\b",
    ]
    for pat in kdrama_patterns:
        if re.search(pat, text):
            return "kdrama"

    # 3. African Cinema & Series (Nollywood / Ghallywood)
    # Notice: NEVER use 'filmhouse' keyword as it is the bot/channel branding!
    african_patterns = [
        r"\b(nollywood|ghallywood|kumawood|african movie|african series|koleoso|yoruba|yorubahood)\b",
        r"\b(accra medic|a tribe called judah|jagun jagun|anikulapo|king of boys|the black book|aiyetoro)\b",
        r"\b(blood sisters|shanty town|far from home|brotherhood|gangs of lagos|lisabi|breath of life)\b",
        r"\b(olishe|afamefuna|house of ga'a|house of gaa|battle on buka street|wedding party)\b",
        r"\b(accra|ghanaian|nigerian)\b",
    ]
    for pat in african_patterns:
        if re.search(pat, text):
            return "african"

    # 4. Bollywood & Indian Cinema
    bollywood_patterns = [
        r"\b(bollywood|kollywood|tollywood|mollywood|sandalwood)\b",
        r"\b(stree 2|stree|jawan|pathaan|dangal|rrr|kgf|pushpa|bahubali|salaar|kalki 2898|kalki|devara|shaitaan)\b",
    ]
    for pat in bollywood_patterns:
        if re.search(pat, text):
            return "bollywood"

    # 5. Cartoons & Western Animation
    cartoon_patterns = [
        r"\b(disney|pixar|dreamworks|illumination|nickelodeon|cartoon network|the fixies|fixies|veggietales|avatar aang|the last airbender)\b",
        r"\b(moana|inside out|kung fu panda|despicable me|minions|toy story|frozen|shrek|zootopia)\b",
        r"\b(spider-man across the spider-verse|spider-man into the spider-verse|puss in boots|sing 2)\b",
        r"\b(encanto|coco|the lion king|madagascar|ice age|cars|ratatouille|finding nemo|the incredibles)\b",
    ]
    for pat in cartoon_patterns:
        if re.search(pat, text):
            return "cartoons"

    # 6. Default Western / Hollywood
    return "series" if is_series else "movies"
