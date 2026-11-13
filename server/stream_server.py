import os
import shutil
import re
import math
import time
import gzip
import json
import asyncio
import logging
from aiohttp import web
from bot.client import get_tg_client, get_media_info
from server.security import (
    verify_stream_token,
    is_origin_allowed,
    generate_stream_token,
    verify_admin_access,
    check_rate_limit,
)
from server.parser import parse_filename, build_golden_filename, safe_int
from server.cache import get_cached_chunk, store_cached_chunk, get_cache_stats
from bot.storage import get_tracked_files, remove_tracked_files, update_tracked_category, update_tracked_metadata
from server.library_template import LIBRARY_HTML
import urllib.parse
import config

logger = logging.getLogger("filmhouse.stream")

# Standard MTProto chunk size (1 MB)
TG_CHUNK_SIZE = 1024 * 1024

# HTML5 Video Player Template with Plyr.io
PLAYER_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — FilmHouse Stream</title>
  <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    body {{
      background: #090a0f;
      color: #f1f5f9;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow-x: hidden;
    }}
    .glow-bg {{
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 600px;
      height: 600px;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
      pointer-events: none;
      z-index: 0;
    }}
    .container {{
      width: 100%;
      max-width: 1100px;
      padding: 24px;
      position: relative;
      z-index: 1;
    }}
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo {{
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #6366f1, #a855f7);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 20px;
      color: #fff;
      box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }}
    .title-area h1 {{
      font-size: 1.35rem;
      font-weight: 600;
      color: #f8fafc;
      letter-spacing: -0.02em;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      background: rgba(99, 102, 241, 0.2);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.3);
      margin-left: 8px;
    }}
    .player-wrapper {{
      width: 100%;
      background: #000;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.08);
      position: relative;
    }}
    .plyr {{
      --plyr-color-main: #6366f1;
      --plyr-video-background: #000;
      border-radius: 16px;
    }}
    .meta-bar {{
      margin-top: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(18, 20, 29, 0.7);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      padding: 14px 20px;
      font-size: 0.88rem;
      color: #94a3b8;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .btn {{
      background: #1e2235;
      color: #e2e8f0;
      padding: 8px 16px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.82rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .btn:hover {{
      background: #6366f1;
      color: #fff;
      border-color: #6366f1;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }}
    .toast-resume {{
      position: absolute;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(18, 20, 29, 0.95);
      backdrop-filter: blur(16px);
      padding: 12px 20px;
      border-radius: 12px;
      border: 1px solid rgba(99, 102, 241, 0.4);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
      z-index: 20;
      display: none;
      align-items: center;
      gap: 12px;
      font-size: 0.88rem;
      animation: fadeIn 0.3s ease;
    }}
    .adblock-banner {{
      background: linear-gradient(90deg, rgba(239, 68, 68, 0.15), rgba(249, 115, 22, 0.15));
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 10px;
      padding: 10px 16px;
      margin-bottom: 16px;
      font-size: 0.85rem;
      color: #fca5a5;
      display: none;
      align-items: center;
      justify-content: space-between;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translate(-50%, 10px); }}
      to {{ opacity: 1; transform: translate(-50%, 0); }}
    }}
  </style>
</head>
<body>
  <div class="glow-bg"></div>
  <div class="container">
    <!-- AdBlock Detection Banner -->
    <div id="adblockBanner" class="adblock-banner">
      <span>🛡️ <b>AdBlocker Detected:</b> Please consider pausing your AdBlocker on FilmHouse to support free 1080p high-speed streaming!</span>
      <button onclick="document.getElementById('adblockBanner').style.display='none'" style="background:none;border:none;color:#fca5a5;cursor:pointer;font-size:16px;">✖</button>
    </div>

    <div class="header">
      <div class="brand">
        <div class="logo">F</div>
        <div class="title-area">
          <h1>{clean_name} <span class="badge">{quality}</span></h1>
        </div>
      </div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        <!-- Subtitle Loader Button -->
        <label for="subFileInput" class="btn" style="cursor: pointer;" title="Load local subtitle file">
          💬 Subtitles (.srt/.vtt)
          <input type="file" id="subFileInput" accept=".srt,.vtt" style="display: none;" />
        </label>
        <a href="{stream_url}" download="{file_name}" class="btn">⬇️ Download File</a>
      </div>
    </div>

    <div class="player-wrapper">
      <!-- Resume Playback Toast -->
      <div id="resumeToast" class="toast-resume">
        <span>⏱️ Resume from <b id="resumeTimeText" style="color: #818cf8;">00:00</b>?</span>
        <button id="btnResume" class="btn" style="background: #6366f1; padding: 4px 10px; font-size: 0.78rem;">▶ Resume</button>
        <button id="btnDismissResume" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:14px;padding:2px 6px;">✖</button>
      </div>

      <video id="player" playsinline controls preload="metadata">
        <source src="{stream_url}" type="{mime_type}">
        Your browser does not support the video tag.
      </video>
    </div>

    <div class="meta-bar">
      <span>📁 {file_name} • {file_size_formatted}</span>
      <span>⚡ Powered by FilmHouse High-Speed MTProto Engine</span>
    </div>
  </div>

  <!-- AdBlock Bait Element -->
  <div class="adsbox ad-placement pub_300x250 pub_728x90" id="adBait" style="position:absolute;left:-9999px;width:1px;height:1px;">&nbsp;</div>

  <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
  <script>
    const videoToken = "{token}";
    const playerEl = document.getElementById('player');
    const player = new Plyr(playerEl, {{
      controls: [
        'play-large', 'restart', 'play', 'progress', 'current-time',
        'duration', 'mute', 'volume', 'captions', 'settings',
        'pip', 'airplay', 'fullscreen'
      ],
      captions: {{ active: true, update: true }},
      seekTime: 10,
      keyboard: {{ focused: true, global: true }},
      tooltips: {{ controls: true, seek: true }}
    }});

    // 1. Resume Playback Progress Logic
    const resumeKey = 'filmhouse_prog_' + videoToken;
    const resumeToast = document.getElementById('resumeToast');
    const resumeText = document.getElementById('resumeTimeText');
    const btnResume = document.getElementById('btnResume');
    const btnDismiss = document.getElementById('btnDismissResume');

    function formatTime(secs) {{
      const m = Math.floor(secs / 60);
      const s = Math.floor(secs % 60);
      return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }}

    player.on('loadedmetadata', () => {{
      const savedTime = parseFloat(localStorage.getItem(resumeKey) || '0');
      if (savedTime > 15 && player.duration && (player.duration - savedTime) > 30) {{
        resumeText.textContent = formatTime(savedTime);
        resumeToast.style.display = 'flex';

        btnResume.onclick = () => {{
          player.currentTime = savedTime;
          player.play();
          resumeToast.style.display = 'none';
        }};
        btnDismiss.onclick = () => {{
          resumeToast.style.display = 'none';
        }};
        // Auto-hide after 8 seconds
        setTimeout(() => {{ resumeToast.style.display = 'none'; }}, 8000);
      }}
    }});

    // Save playback position every 4 seconds
    player.on('timeupdate', () => {{
      if (player.currentTime > 5 && player.duration && (player.duration - player.currentTime) > 15) {{
        localStorage.setItem(resumeKey, player.currentTime);
      }}
    }});

    // 2. Subtitle File Loader (.srt / .vtt)
    const subInput = document.getElementById('subFileInput');
    subInput.addEventListener('change', function(e) {{
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function(evt) {{
        let content = evt.target.result;
        // Convert SRT to WebVTT if needed
        if (file.name.endsWith('.srt')) {{
          content = "WEBVTT\\n\\n" + content
            .replace(/(\\d{{2}}:\\d{{2}}:\\d{{2}}),(\\d{{3}})/g, "$1.$2");
        }}
        const blob = new Blob([content], {{ type: 'text/vtt' }});
        const trackUrl = URL.createObjectURL(blob);

        // Add track element
        const track = document.createElement('track');
        track.kind = 'subtitles';
        track.label = file.name.replace(/\\.[^/.]+$/, "");
        track.srclang = 'en';
        track.src = trackUrl;
        track.default = true;

        playerEl.appendChild(track);
        player.currentTrack = playerEl.textTracks.length - 1;
        alert("✅ Subtitles loaded: " + file.name);
      }};
      reader.readAsText(file);
    }});

    // 3. AdBlocker Detection
    window.addEventListener('load', () => {{
      setTimeout(() => {{
        const bait = document.getElementById('adBait');
        if (!bait || bait.offsetHeight === 0 || bait.clientHeight === 0) {{
          document.getElementById('adblockBanner').style.display = 'flex';
        }}
      }}, 1000);
    }});
  </script>
</body>
</html>
"""


def format_bytes(size: int) -> str:
    """Format bytes to human readable string (MB, GB)."""
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {units[i]}"


async def handle_home(request: web.Request) -> web.Response:
    """Health check endpoint with live cache stats."""
    return web.json_response({
        "status": "online",
        "service": "FilmHouse Telegram Streaming Engine",
        "version": "2.1.0",
        "cache": get_cache_stats(),
    })


async def handle_watch(request: web.Request) -> web.Response:
    """
    Renders the Plyr.io web video player page for the given video token.
    """
    token = request.match_info.get("token", "")
    # Strip optional extensions (.mp4, .mkv) for apps that require a video file extension in URL
    if "." in token:
        token = token.split(".")[0]
    message_id = verify_stream_token(token)
    if not message_id:
        return web.Response(text="Invalid or expired video link.", status=403)

    info = await get_media_info(message_id)
    if not info:
        return web.Response(text="Video not found in storage channel.", status=404)

    file_name = info["file_name"]
    file_size = info["file_size"]
    mime_type = info["mime_type"]

    parsed = parse_filename(file_name)
    clean_name = parsed["clean_name"]
    quality = parsed["quality"] or "HD"

    stream_url = f"{config.SERVER_URL}/stream/{token}"

    html = PLAYER_HTML_TEMPLATE.format(
        title=clean_name,
        clean_name=clean_name,
        quality=quality,
        file_name=file_name,
        file_size_formatted=format_bytes(file_size),
        stream_url=stream_url,
        mime_type=mime_type,
        token=token,
    )

    return web.Response(
        text=html,
        content_type="text/html",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Security-Policy": "frame-ancestors *",
        }
    )


def parse_range_header(range_header: str | None, file_size: int) -> tuple[int, int] | None:
    """
    Parses HTTP Range header according to RFC 7233.
    Returns (start, end) tuple or None if range is invalid/unsatisfiable.
    """
    if not range_header or file_size <= 0:
        return (0, max(0, file_size - 1))

    if not range_header.startswith("bytes="):
        return None

    range_spec = range_header[6:].strip()
    if "," in range_spec:
        # We only support single ranges for media streaming
        range_spec = range_spec.split(",")[0].strip()

    if range_spec.startswith("-"):
        # Suffix range: bytes=-500 (last 500 bytes)
        try:
            suffix_len = int(range_spec[1:])
            if suffix_len <= 0:
                return None
            start = max(0, file_size - suffix_len)
            end = file_size - 1
            return (start, end)
        except ValueError:
            return None

    parts = range_spec.split("-", 1)
    if len(parts) != 2:
        return None

    try:
        start = int(parts[0])
        if parts[1].strip():
            end = int(parts[1])
        else:
            end = file_size - 1

        if start > end or start >= file_size or start < 0:
            return None

        end = min(end, file_size - 1)
        return (start, end)
    except ValueError:
        return None



async def stream_transmuxed_mp4(request: web.Request, message, file_name: str) -> web.StreamResponse:
    """
    On-the-fly zero-delay video transmuxer (MKV/TS -> fragmented MP4).
    Uses 'ffmpeg -c:v copy -c:a aac' to repackage containers in real time
    for iOS Safari / Telegram WebApp compatibility with 0% CPU re-encoding overhead.
    """
    ffmpeg_bin = shutil.which("ffmpeg") or ("/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else None)
    if not ffmpeg_bin:
        return None

    # Handle HEAD request for transmuxed stream
    if request.method == "HEAD":
        return web.Response(
            status=200,
            headers={
                "Content-Type": "video/mp4",
                "Accept-Ranges": "none",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Content-Range, Origin, Accept, Content-Type",
                "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
                "Content-Security-Policy": "frame-ancestors *",
            }
        )

    audio_req = request.query.get("audio") or request.query.get("audio_track")
    audio_map = f"0:a:{audio_req}" if (audio_req is not None and str(audio_req).isdigit()) else "0:a?"

    ss_param = request.query.get("ss") or request.query.get("t")
    ss_args = []
    if ss_param and (str(ss_param).replace(".", "", 1).isdigit()) and float(ss_param) > 0:
        ss_args = ["-ss", str(ss_param)]

    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel", "error",
        "-i", "pipe:0",
        *ss_args,
        "-map", "0:v:0",
        "-map", audio_map,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4",
        "pipe:1"
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        logger.warning(f"[Transmux] Failed to spawn ffmpeg: {e}")
        return None

    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "none",
        "Content-Disposition": f'inline; filename="{file_name}.mp4"',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Content-Range, Origin, Accept, Content-Type",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        "Content-Security-Policy": "frame-ancestors *",
    }

    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)

    client = get_tg_client()

    async def feed_input():
        try:
            async for chunk in client.stream_media(message, offset=0):
                if proc.stdin.is_closing():
                    break
                proc.stdin.write(chunk)
                await proc.stdin.drain()
        except Exception:
            pass
        finally:
            try:
                proc.stdin.close()
                await proc.stdin.wait_closed()
            except Exception:
                pass

    feed_task = asyncio.create_task(feed_input())

    try:
        while True:
            out_chunk = await proc.stdout.read(64 * 1024)
            if not out_chunk:
                break
            await response.write(out_chunk)
    except (ConnectionResetError, web.HTTPException, Exception):
        pass
    finally:
        feed_task.cancel()
        try:
            proc.kill()
        except Exception:
            pass
        await proc.wait()

    return response

async def handle_stream(request: web.Request) -> web.StreamResponse:
    """
    Core HTTP 206 Partial Content video streaming handler.
    Optimized for iOS Safari, Telegram WebApp, and Chrome seeking.
    Supports GET, HEAD, and OPTIONS requests.
    """
    # 1. Handle CORS Preflight (OPTIONS)
    if request.method == "OPTIONS":
        return web.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Content-Range, Origin, Accept, Content-Type",
                "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
                "Access-Control-Max-Age": "86400",
            }
        )

    token = request.match_info.get("token", "")
    # Strip optional extensions (.mp4, .mkv) for apps that require a video file extension in URL
    if "." in token:
        token = token.split(".")[0]
    message_id = verify_stream_token(token)
    if not message_id:
        return web.Response(text="Invalid or unauthorized stream token.", status=403)

    if not is_origin_allowed(request):
        return web.Response(text="Hotlinking is not permitted.", status=403)

    info = await get_media_info(message_id)
    if not info:
        return web.Response(text="Media not found.", status=404)

    file_size = info["file_size"]
    raw_mime = info["mime_type"]
    file_name = info["file_name"]
    message = info["message"]

    # 2. MIME Type & On-The-Fly Transmuxing for iOS Safari & Telegram WebApp
    lower_name = file_name.lower()
    user_agent = request.headers.get("User-Agent", "").lower()
    has_audio_select = (request.query.get("audio") is not None or request.query.get("audio_track") is not None)
    wants_remux = (
        request.query.get("remux") in ("1", "mp4", "true") or
        has_audio_select or
        ("remux=mp4" in str(request.rel_url)) or
        (lower_name.endswith((".mkv", ".avi", ".ts")) and ("iphone" in user_agent or "ipad" in user_agent))
    )

    if wants_remux and (has_audio_select or (lower_name.endswith((".mkv", ".avi", ".ts", ".webm")) and not lower_name.endswith(".mp4"))):
        remux_resp = await stream_transmuxed_mp4(request, message, file_name)
        if remux_resp is not None:
            return remux_resp
    if lower_name.endswith((".mp4", ".m4v", ".mov")):
        mime_type = "video/mp4"
    elif lower_name.endswith(".webm"):
        mime_type = "video/webm"
    elif lower_name.endswith((".mkv", ".avi", ".ts")):
        # iOS Safari AVPlayer & Telegram WebApp natively decode H.264 video streams when served as video/mp4
        mime_type = "video/mp4"
    elif not raw_mime or raw_mime == "application/octet-stream":
        mime_type = "video/mp4"
    else:
        mime_type = raw_mime

    # Standard headers for all responses
    base_headers = {
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Content-Range, Origin, Accept, Content-Type",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        "Content-Security-Policy": "frame-ancestors *",
    }

    # 3. Handle iOS Safari HEAD Probe Request
    if request.method == "HEAD":
        headers = {
            **base_headers,
            "Content-Length": str(file_size),
        }
        return web.Response(status=200, headers=headers)

    # 4. Parse Range Header: bytes=start-end (including Safari bytes=0-1 test)
    range_header = request.headers.get("Range")
    range_parsed = parse_range_header(range_header, file_size)

    if range_header and range_parsed is None:
        return web.Response(
            status=416,
            headers={
                **base_headers,
                "Content-Range": f"bytes */{file_size}",
            }
        )

    start, end = range_parsed if range_parsed else (0, file_size - 1)
    content_length = (end - start) + 1

    # Prepare response headers for HTTP 206
    status = 206 if range_header else 200
    headers = {
        **base_headers,
        "Content-Length": str(content_length),
    }

    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    response = web.StreamResponse(status=status, headers=headers)
    await response.prepare(request)

    # 5. Serve from RAM Cache first (0.001s instant seek)
    offset_chunks = math.floor(start / TG_CHUNK_SIZE)
    skip_bytes = start % TG_CHUNK_SIZE
    bytes_remaining = content_length
    current_chunk_idx = offset_chunks

    # Check RAM Cache
    while bytes_remaining > 0:
        cached_data = get_cached_chunk(message_id, current_chunk_idx)
        if not cached_data:
            break

        chunk = cached_data
        if skip_bytes > 0:
            if len(chunk) <= skip_bytes:
                skip_bytes -= len(chunk)
                current_chunk_idx += 1
                continue
            else:
                chunk = chunk[skip_bytes:]
                skip_bytes = 0

        to_send = chunk[:bytes_remaining]
        try:
            await response.write(to_send)
        except (ConnectionResetError, web.HTTPException, Exception):
            return response

        bytes_remaining -= len(to_send)
        current_chunk_idx += 1

    # 6. If remaining bytes needed, stream remainder from Telegram MTProto
    if bytes_remaining > 0:
        client = get_tg_client()
        try:
            async for chunk in client.stream_media(message, offset=current_chunk_idx):
                # Cache initial chunks for future fast hits
                store_cached_chunk(message_id, current_chunk_idx, chunk)

                if skip_bytes > 0:
                    if len(chunk) <= skip_bytes:
                        skip_bytes -= len(chunk)
                        current_chunk_idx += 1
                        continue
                    else:
                        chunk = chunk[skip_bytes:]
                        skip_bytes = 0

                if len(chunk) > bytes_remaining:
                    chunk = chunk[:bytes_remaining]

                await response.write(chunk)
                bytes_remaining -= len(chunk)
                current_chunk_idx += 1

                if bytes_remaining <= 0:
                    break
        except (ConnectionResetError, web.HTTPException, Exception):
            # Client sought to new timestamp or closed tab
            pass

    return response


async def handle_library(request: web.Request) -> web.Response:
    """Renders the mobile-first Telegram Mini App Library."""
    return web.Response(
        text=LIBRARY_HTML,
        content_type="text/html",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Security-Policy": "frame-ancestors *",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


async def handle_cors_options(request: web.Request) -> web.Response:
    """Handles CORS preflight requests for API endpoints."""
    return web.Response(
        status=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data, X-Admin-Key",
        }
    )


_api_media_cache = None
_api_media_cache_time = 0.0
_api_media_cache_ttl = 300.0  # 5-minute cache TTL (instantly invalidated on any modification)
_api_media_cache_json = b""
_api_media_cache_gzip = b""
_parsed_filename_cache = {}


def update_media_cache_buffers(payload: dict):
    global _api_media_cache, _api_media_cache_time, _api_media_cache_json, _api_media_cache_gzip
    _api_media_cache = payload
    _api_media_cache_time = time.time()
    try:
        raw_json = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _api_media_cache_json = raw_json
        _api_media_cache_gzip = gzip.compress(raw_json, compresslevel=6)
    except Exception as e:
        logger.warning(f"Error compressing media cache buffers: {e}")


def invalidate_media_cache():
    global _api_media_cache, _api_media_cache_time, _api_media_cache_json, _api_media_cache_gzip
    _api_media_cache = None
    _api_media_cache_time = 0.0
    _api_media_cache_json = b""
    _api_media_cache_gzip = b""


def build_api_media_payload() -> dict:
    """Ultra-fast payload generator leveraging stored metadata and memoization to avoid redundant parsing."""
    global _parsed_filename_cache
    records = get_tracked_files()
    items = []

    for r in records:
        try:
            mid = r.get("message_id")
            if not mid:
                continue
            fn = r.get("file_name") or r.get("original_filename") or f"video_{mid}.mp4"
            stored_parsed = r.get("parsed") or {}

            # Fast path 1: use already parsed data stored during indexing if valid
            if isinstance(stored_parsed, dict) and stored_parsed.get("title") and stored_parsed.get("title") != "Unknown Media":
                parsed = dict(stored_parsed)
            # Fast path 2: check memory cache for this exact filename
            elif fn in _parsed_filename_cache:
                parsed = dict(_parsed_filename_cache[fn])
            else:
                parsed = parse_filename(fn)
                _parsed_filename_cache[fn] = dict(parsed)

            # Override/coalesce any fields updated directly
            if stored_parsed.get("season") is not None:
                try:
                    parsed["season"] = int(stored_parsed["season"])
                except Exception:
                    pass

            if stored_parsed.get("episode") is not None:
                try:
                    parsed["episode"] = int(stored_parsed["episode"])
                except Exception:
                    pass

            if stored_parsed.get("is_series") is not None:
                parsed["is_series"] = bool(stored_parsed["is_series"])

            # Auto-Heal Series: Upgrade files with franchise, End/Finale markers, or episode markers to series
            lower_fn = fn.lower()
            lower_title = str(parsed.get("title") or "").lower()
            movie_end_exceptions = ("avengers", "pirates", "dead end", "deep end", "world's end", "weekend")
            has_end_marker = (lower_fn.startswith("end ") or " end" in lower_fn or lower_title.startswith("end ") or " end" in lower_title) and not any(ex in lower_fn for ex in movie_end_exceptions)

            if has_end_marker:
                parsed["is_series"] = True
                cleaned = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", parsed.get("title") or fn, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", cleaned, flags=re.IGNORECASE).strip()
                parsed["title"] = cleaned
                if not parsed.get("episode"):
                    m = re.search(r"\b(?:e|ep|episode)?\s*0?(\d{1,3})\b", fn, re.IGNORECASE)
                    parsed["episode"] = int(m.group(1)) if m else 999
                parsed["season"] = parsed.get("season") or 1
            elif not parsed.get("is_series"):
                if "flex x cop" in lower_fn or "flexxcop" in lower_fn or "flex x cop" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "Flex X Cop"
                    parsed["category"] = "kdrama"
                    m = re.search(r"\b(?:e|ep|episode)?\s*0?(\d{1,3})\b", fn, re.IGNORECASE)
                    if m: parsed["episode"] = int(m.group(1))
                    parsed["season"] = parsed.get("season") or 1
                elif "mr bean" in lower_fn or "mr. bean" in lower_fn or "mr bean" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "Mr. Bean"
                    parsed["category"] = "series"
                    m = re.search(r"\b(?:e|ep|episode)?\s*0?(\d{1,3})\b", fn, re.IGNORECASE)
                    if m: parsed["episode"] = int(m.group(1))
                    parsed["season"] = parsed.get("season") or 1
                elif re.search(r"\b(?:ep|episode)\s*0?(\d{1,3})\b", fn, re.IGNORECASE):
                    parsed["is_series"] = True
                    m = re.search(r"\b(?:ep|episode)\s*0?(\d{1,3})\b", fn, re.IGNORECASE)
                    if m: parsed["episode"] = int(m.group(1))
                    parsed["season"] = parsed.get("season") or 1

            # Auto-Heal specific series & letter 'o' typos
            if not parsed.get("is_series") or "so1" in lower_fn or "hidden love" in lower_fn or "a good day" in lower_fn:
                o_m = re.search(r"\b[sS][oO](\d{1,2})[eE](?:[oO])?(\d{1,3})\b", fn)
                if o_m:
                    parsed["is_series"] = True
                    parsed["season"] = int(o_m.group(1))
                    parsed["episode"] = int(o_m.group(2))
                    t = re.sub(r"\b[sS][oO]\d{1,2}[eE][oO]?\d{1,3}.*$", "", parsed.get("title") or fn, flags=re.IGNORECASE).strip(" .-_")
                    if t: parsed["title"] = t

                if "a good day to be a dog" in lower_fn or "a good day to be a dog" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "A Good Day To Be A Dog"
                    parsed["category"] = "kdrama"
                    if not parsed.get("season"): parsed["season"] = 1
                    if not parsed.get("episode"):
                        m = re.search(r"\b0?(\d{1,3})\b", fn)
                        parsed["episode"] = int(m.group(1)) if m else 1

                if "hidden love" in lower_fn or "hidden love" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "Hidden Love"
                    parsed["category"] = "kdrama"
                    parsed["season"] = 1
                    if "special" in lower_fn:
                        parsed["episode"] = 0
                        parsed["episode_title"] = "Special"

                if "chucky" in lower_fn or "chucky" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "Chucky"
                    parsed["category"] = "series"
                    if not parsed.get("season"):
                        s_m = re.search(r"\b[sS](\d{1,2})\b", fn)
                        parsed["season"] = int(s_m.group(1)) if s_m else 1
                    if not parsed.get("episode") or parsed.get("episode") == 999:
                        m = re.search(r"\b0?(\d{1,3})\b", fn)
                        parsed["episode"] = int(m.group(1)) if m else 1

                if "killer paradox" in lower_fn or "killer paradox" in lower_title:
                    parsed["is_series"] = True
                    parsed["title"] = "A Killer Paradox"
                    parsed["category"] = "kdrama"
                    if not parsed.get("season"):
                        parsed["season"] = 1
                    if not parsed.get("episode") or parsed.get("episode") == 999:
                        m = re.search(r"\b0?(\d{1,3})\b", fn)
                        parsed["episode"] = int(m.group(1)) if m else 1

                if "my demon" in lower_fn or "my demon" in lower_title or "mydemon" in lower_fn:
                    parsed["is_series"] = True
                    parsed["title"] = "My Demon"
                    parsed["category"] = "kdrama"
                    if not parsed.get("season"):
                        parsed["season"] = 1
                    if not parsed.get("episode") or parsed.get("episode") == 999:
                        m = re.search(r"\b0?(\d{1,3})\b", fn)
                        parsed["episode"] = int(m.group(1)) if m else 1

                # Generic leading episode healing (e.g. 08 A Killer Paradox, 01 My Demon)
                if not parsed.get("is_series") and re.search(r"^(?:(?:ep|episode|e)[\s\.\-_]*)?(0[1-9]|[1-9]\d?)[\s\.\-_]+[a-zA-Z]", fn, re.IGNORECASE):
                    fresh_p = parse_filename(fn)
                    if fresh_p.get("is_series"):
                        parsed.update(fresh_p)

            # Auto-heal false TV series from older parser (e.g. Return of Beyonce 1, Iron Man 2)
            if parsed.get("is_series"):
                has_explicit_ep = bool(re.search(r"\b(?:s\d{1,2}|e\d{1,3}|ep|episode|s\d{1,2}e\d{1,3})\b", fn, re.IGNORECASE))
                has_zero_pad = bool(re.search(r"[\s\.\-_]0\d{1,2}\b", fn))
                if not has_explicit_ep and not has_zero_pad:
                    fresh_p = parse_filename(fn)
                    if not fresh_p.get("is_series"):
                        parsed["is_series"] = False
                        parsed["title"] = fresh_p.get("title") or parsed.get("title")
                        parsed["season"] = None
                        parsed["episode"] = None
                        parsed["category"] = fresh_p.get("category") or ("african" if "beyonce" in lower_fn else "movies")

            title_clean = str(parsed.get("title") or fn or "Unknown")
            if parsed.get("is_series"):
                title_clean = re.sub(r"^(?:the\s+)?(?:end|finale|final)\s+", "", title_clean, flags=re.IGNORECASE).strip()
                title_clean = re.sub(r"[\s\.\-_]+(?:the\s+)?(?:end|finale|final)$", "", title_clean, flags=re.IGNORECASE).strip()

            if parsed.get("is_series"):
                s_num = safe_int(parsed.get("season"), default=1)
                e_num = safe_int(parsed.get("episode"), default=1)
                end_num = safe_int(parsed.get("end_episode"), default=None)
                s_str = f"S{s_num:02d}"
                if end_num and end_num > e_num:
                    e_str = f"E{e_num:02d}-E{end_num:02d}"
                else:
                    e_str = f"E{e_num:02d}"
                ep_sub = f" — {parsed['episode_title']}" if parsed.get("episode_title") else ""
                display_title = f"{title_clean} {s_str}{e_str}{ep_sub}"
            else:
                year_str = f" ({parsed['year']})" if parsed.get("year") else ""
                display_title = f"{title_clean}{year_str}"

            token = generate_stream_token(mid)
            stream_url = f"{config.SERVER_URL}/dl/{token}"
            watch_url = f"{config.SERVER_URL}/watch/{token}"

            category = r.get("category")
            if not category or (category == "african" and parsed.get("category") != "african"):
                category = parsed.get("category") or ("series" if parsed.get("is_series") else "movies")
            elif parsed.get("category") and parsed.get("category") not in ("movies", "series") and category in ("movies", "series"):
                category = parsed.get("category")
            elif parsed.get("is_series") and category == "movies":
                category = "series"
            elif not parsed.get("is_series") and category == "series":
                category = "movies"

            golden_fn = parsed.get("golden_name")
            if not golden_fn or " " in golden_fn or "_" in golden_fn or "filmhouse" in golden_fn.lower():
                golden_fn = build_golden_filename(parsed, fn)
            parsed["golden_name"] = golden_fn

            items.append({
                "message_id": mid,
                "file_name": golden_fn,
                "original_file_name": fn,
                "display_name": display_title or golden_fn,
                "series_title": title_clean if parsed.get("is_series") else None,
                "season": safe_int(parsed.get("season"), default=1) if parsed.get("is_series") else None,
                "episode": safe_int(parsed.get("episode"), default=1) if parsed.get("is_series") else None,
                "end_episode": safe_int(parsed.get("end_episode"), default=None) if parsed.get("is_series") else None,
                "episode_title": parsed.get("episode_title") if parsed.get("is_series") else None,
                "quality": parsed.get("quality") or "HD",
                "is_series": bool(parsed.get("is_series", False)),
                "category": category,
                "file_size_str": r.get("file_size_str", ""),
                "stream_url": stream_url,
                "watch_url": watch_url,
                "created_at": r.get("created_at", 0),
            })
        except Exception as item_err:
            logger.warning(f"Error processing item message_id={r.get('message_id')}: {item_err}")
            continue

    return {
        "success": True,
        "total": len(items),
        "items": items,
    }


def prewarm_media_cache():
    """Builds the in-memory media payload cache at startup so the very first request is served in <1ms."""
    try:
        from bot.storage import heal_stored_series_ledger
        heal_stored_series_ledger()
    except Exception as e:
        logger.warning(f"Notice during ledger healing: {e}")
    try:
        logger.info("Pre-warming media library cache for 6,400+ titles...")
        payload = build_api_media_payload()
        update_media_cache_buffers(payload)
        logger.info(f"Media library cache pre-warmed: {len(payload.get('items', []))} titles loaded into RAM (Gzip size: {len(_api_media_cache_gzip) // 1024} KB).")
    except Exception as e:
        logger.warning(f"Notice during media cache pre-warming: {e}")


async def handle_api_media(request: web.Request) -> web.Response:
    """Returns JSON array of all tracked media items."""
    # 1. Rate limiting & anti-abuse (generous 300 req/min for smooth admin browsing)
    if not check_rate_limit(request, max_requests=300, window_sec=60):
        return web.json_response(
            {"success": False, "error": "Rate limit exceeded. Please wait a moment."},
            status=429,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # 2. Check admin status for capabilities
    is_admin = verify_admin_access(request)

    # 3. Check fast in-memory cache
    global _api_media_cache, _api_media_cache_time, _api_media_cache_json, _api_media_cache_gzip
    now = time.time()
    if _api_media_cache is None or (now - _api_media_cache_time) >= _api_media_cache_ttl:
        try:
            payload = build_api_media_payload()
            update_media_cache_buffers(payload)
        except Exception as e:
            logger.error(f"Error rebuilding media cache: {e}", exc_info=True)
            if _api_media_cache is None:
                return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

    accept_encoding = request.headers.get("Accept-Encoding", "").lower()
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data, X-Admin-Key",
        "Cache-Control": "no-cache",
    }

    if "gzip" in accept_encoding and _api_media_cache_gzip:
        headers["Content-Encoding"] = "gzip"
        return web.Response(
            body=_api_media_cache_gzip,
            content_type="application/json",
            headers=headers
        )
    elif _api_media_cache_json:
        return web.Response(
            body=_api_media_cache_json,
            content_type="application/json",
            headers=headers
        )
    else:
        resp_data = dict(_api_media_cache)
        resp_data["is_admin"] = is_admin
        return web.json_response(resp_data, headers=headers)


async def handle_api_delete(request: web.Request) -> web.Response:
    """Deletes an item from the bin channel and local ledger (ADMIN ONLY)."""
    # 1. Rate limiting & anti-abuse
    if not check_rate_limit(request, max_requests=30, window_sec=60):
        return web.json_response(
            {"success": False, "error": "Rate limit exceeded. Please wait a moment."},
            status=429,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # 2. Strict Admin Verification
    if not verify_admin_access(request):
        return web.json_response(
            {"success": False, "error": "Unauthorized: FilmHouse Admin authorization required."},
            status=401,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data, X-Admin-Key",
            }
        )

    try:
        data = await request.json()
        mids = data.get("message_ids")
        if not mids:
            single_mid = data.get("message_id")
            if single_mid:
                mids = [single_mid]

        if not mids:
            return web.json_response({"success": False, "error": "Missing message_id(s)"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        mids = [int(m) for m in mids]
        client = get_tg_client()
        for i in range(0, len(mids), 50):
            chunk = mids[i:i + 50]
            try:
                await client.delete_messages(config.BIN_CHANNEL_ID, chunk)
            except Exception as e:
                logger.error(f"Error deleting batch from Telegram: {e}")

        remove_tracked_files(mids)
        invalidate_media_cache()
        return web.json_response({"success": True, "deleted_count": len(mids)}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"Error in handle_api_delete: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_category(request: web.Request) -> web.Response:
    """Updates the category tag for media items (ADMIN ONLY)."""
    if not check_rate_limit(request, max_requests=30, window_sec=60):
        return web.json_response({"success": False, "error": "Rate limit exceeded."}, status=429, headers={"Access-Control-Allow-Origin": "*"})

    if not verify_admin_access(request):
        return web.json_response({"success": False, "error": "Unauthorized: FilmHouse Admin authorization required."}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    try:
        data = await request.json()
        mids = data.get("message_ids")
        if not mids:
            single_mid = data.get("message_id")
            if single_mid:
                mids = [single_mid]

        category = (data.get("category") or "").strip().lower()
        if not mids or not category:
            return web.json_response({"success": False, "error": "Missing message_ids or category."}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        mids = [int(m) for m in mids]
        update_tracked_category(mids, category)
        invalidate_media_cache()
        return web.json_response({"success": True, "updated_count": len(mids), "category": category}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"Error in handle_api_category: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_edit(request: web.Request) -> web.Response:
    """Updates metadata (title, season, episode, is_series, category) for a media item (ADMIN ONLY)."""
    if not check_rate_limit(request, max_requests=30, window_sec=60):
        return web.json_response({"success": False, "error": "Rate limit exceeded."}, status=429, headers={"Access-Control-Allow-Origin": "*"})

    if not verify_admin_access(request):
        return web.json_response({"success": False, "error": "Unauthorized: FilmHouse Admin authorization required."}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    try:
        data = await request.json()
        mid = data.get("message_id")
        if not mid:
            return web.json_response({"success": False, "error": "Missing message_id."}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        mid = int(mid)
        update_tracked_metadata(mid, data)
        invalidate_media_cache()
        return web.json_response({"success": True, "message_id": mid}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"Error in handle_api_edit: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_audit(request: web.Request) -> web.Response:
    """Returns cached series completeness audit data."""
    from server.tmdb_auditor import load_cached_audit
    data = load_cached_audit()
    return web.json_response({"success": True, "audit": data}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Init-Data, X-Admin-Key",
    })


async def handle_api_audit_sync(request: web.Request) -> web.Response:
    """Triggers background series completeness audit using TMDB."""
    try:
        from server.tmdb_auditor import run_series_completeness_audit
        asyncio.create_task(run_series_completeness_audit(force_tmdb=True))
        return web.json_response({
            "success": True,
            "message": "Audit started in background."
        }, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        })
    except Exception as e:
        logger.error(f"Error starting audit sync: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def handle_api_toggle_complete(request: web.Request) -> web.Response:
    """Toggles complete status for a season or series (ADMIN ONLY)."""
    if not check_rate_limit(request, max_requests=60, window_sec=60):
        return web.json_response({"success": False, "error": "Rate limit exceeded."}, status=429, headers={"Access-Control-Allow-Origin": "*"})

    if not verify_admin_access(request):
        return web.json_response({"success": False, "error": "Unauthorized: FilmHouse Admin authorization required."}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    try:
        data = await request.json()
        key = data.get("key")
        canonical_key = data.get("canonical_key")
        season = data.get("season")
        if not key:
            if canonical_key and season:
                key = f"{canonical_key}__s{season}"
            elif canonical_key:
                key = canonical_key

        if not key:
            return web.json_response({"success": False, "error": "Missing key or canonical_key."}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        from server.tmdb_auditor import toggle_completed_season, get_completed_seasons
        new_state = toggle_completed_season(key)
        return web.json_response({
            "success": True,
            "key": key,
            "is_complete": new_state,
            "completed_seasons": get_completed_seasons()
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"Error in handle_api_toggle_complete: {e}")
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


def create_stream_app() -> web.Application:
    """Builds and returns the aiohttp web application with route aliases."""
    app = web.Application()
    app.router.add_get("/", handle_home)
    app.router.add_get("/library", handle_library)
    
    # Protected Admin API routes
    app.router.add_get("/api/media", handle_api_media)
    app.router.add_route("OPTIONS", "/api/media", handle_cors_options)
    app.router.add_get("/api/audit", handle_api_audit)
    app.router.add_route("OPTIONS", "/api/audit", handle_cors_options)
    app.router.add_get("/api/audit/sync", handle_api_audit_sync)
    app.router.add_post("/api/audit/sync", handle_api_audit_sync)
    app.router.add_route("OPTIONS", "/api/audit/sync", handle_cors_options)
    app.router.add_post("/api/audit/toggle-complete", handle_api_toggle_complete)
    app.router.add_route("OPTIONS", "/api/audit/toggle-complete", handle_cors_options)
    app.router.add_post("/api/media/delete", handle_api_delete)
    app.router.add_route("OPTIONS", "/api/media/delete", handle_cors_options)
    app.router.add_post("/api/media/category", handle_api_category)
    app.router.add_route("OPTIONS", "/api/media/category", handle_cors_options)
    app.router.add_post("/api/media/edit", handle_api_edit)
    app.router.add_route("OPTIONS", "/api/media/edit", handle_cors_options)
    
    app.router.add_get("/watch/{token}", handle_watch)
    
    # In aiohttp, add_get automatically registers both GET and HEAD!
    # Supports direct tokens, extensions (/dl/token.mp4), and named paths (/dl/token/video.mp4)
    for path in (
        "/stream/{token}",
        "/dl/{token}",
        "/stream/{token}/{filename:.*}",
        "/dl/{token}/{filename:.*}",
    ):
        app.router.add_get(path, handle_stream)
        app.router.add_route("OPTIONS", path, handle_stream)
        
    return app
