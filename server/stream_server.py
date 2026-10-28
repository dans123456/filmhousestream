import re
import math
import logging
from aiohttp import web
from bot.client import get_tg_client, get_media_info
from server.security import verify_stream_token, is_origin_allowed
from server.parser import parse_filename
from server.cache import get_cached_chunk, store_cached_chunk, get_cache_stats
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
    .toast-resume {
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
    }
    .adblock-banner {
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
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translate(-50%, 10px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }
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

    # 2. MIME Type Optimization for iOS Safari & Telegram WebApp
    lower_name = file_name.lower()
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
    start = 0
    end = file_size - 1

    if range_header:
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start_str, end_str = range_match.groups()
            start = int(start_str) if start_str else 0
            if end_str:
                end = int(end_str)

    if start > end or start >= file_size:
        return web.Response(
            status=416,
            headers={
                **base_headers,
                "Content-Range": f"bytes */{file_size}",
            }
        )

    end = min(end, file_size - 1)
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


def create_stream_app() -> web.Application:
    """Builds and returns the aiohttp web application with route aliases."""
    app = web.Application()
    app.router.add_get("/", handle_home)
    app.router.add_get("/watch/{token}", handle_watch)
    
    # In aiohttp, add_get automatically registers both GET and HEAD!
    for path in ("/stream/{token}", "/dl/{token}"):
        app.router.add_get(path, handle_stream)
        app.router.add_route("OPTIONS", path, handle_stream)
        
    return app
