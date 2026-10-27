import re
import math
import logging
from aiohttp import web
from bot.client import get_tg_client, get_media_info
from server.security import verify_stream_token, is_origin_allowed
from server.parser import parse_filename
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
  </style>
</head>
<body>
  <div class="glow-bg"></div>
  <div class="container">
    <div class="header">
      <div class="brand">
        <div class="logo">F</div>
        <div class="title-area">
          <h1>{clean_name} <span class="badge">{quality}</span></h1>
        </div>
      </div>
      <div>
        <a href="{stream_url}" download="{file_name}" class="btn">⬇️ Download File</a>
      </div>
    </div>

    <div class="player-wrapper">
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

  <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
  <script>
    const player = new Plyr('#player', {{
      controls: [
        'play-large', 'restart', 'play', 'progress', 'current-time',
        'duration', 'mute', 'volume', 'captions', 'settings',
        'pip', 'airplay', 'fullscreen'
      ],
      seekTime: 10,
      keyboard: {{ focused: true, global: true }},
      tooltips: {{ controls: true, seek: true }}
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
    """Health check endpoint."""
    return web.json_response({
        "status": "online",
        "service": "FilmHouse Telegram Streaming Engine",
        "version": "1.0.0",
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
    )

    return web.Response(text=html, content_type="text/html")


async def handle_stream(request: web.Request) -> web.StreamResponse:
    """
    Core HTTP 206 Partial Content video streaming handler.
    Proxies byte ranges directly from Telegram MTProto to the browser.
    """
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
    mime_type = info["mime_type"]
    file_name = info["file_name"]
    message = info["message"]

    # Parse Range Header: bytes=start-end
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
            headers={"Content-Range": f"bytes */{file_size}"}
        )

    end = min(end, file_size - 1)
    content_length = (end - start) + 1

    # Prepare response headers for HTTP 206
    status = 206 if range_header else 200
    headers = {
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range, Content-Type",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
    }

    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    response = web.StreamResponse(status=status, headers=headers)
    await response.prepare(request)

    # Calculate MTProto chunk boundaries
    client = get_tg_client()
    
    # Calculate offset in 1MB chunks
    offset_chunks = math.floor(start / TG_CHUNK_SIZE)
    skip_bytes = start % TG_CHUNK_SIZE
    bytes_remaining = content_length

    try:
        # Stream chunks from Pyrogram/Hydrogram
        async for chunk in client.stream_media(message, offset=offset_chunks):
            if skip_bytes > 0:
                if len(chunk) <= skip_bytes:
                    skip_bytes -= len(chunk)
                    continue
                else:
                    chunk = chunk[skip_bytes:]
                    skip_bytes = 0

            if len(chunk) > bytes_remaining:
                chunk = chunk[:bytes_remaining]

            await response.write(chunk)
            bytes_remaining -= len(chunk)

            if bytes_remaining <= 0:
                break
    except (ConnectionResetError, web.HTTPException, Exception) as e:
        # Browser seeked away or closed tab - this is normal in HTTP streaming
        pass

    return response


def create_stream_app() -> web.Application:
    """Builds and returns the aiohttp web application."""
    app = web.Application()
    app.router.add_get("/", handle_home)
    app.router.add_get("/watch/{token}", handle_watch)
    app.router.add_get("/stream/{token}", handle_stream)
    return app
