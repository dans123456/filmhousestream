LIBRARY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>FilmHouse Cinema Library</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    body {
      background: #090a0f;
      color: #f1f5f9;
      min-height: 100vh;
      padding: 16px;
      overflow-x: hidden;
    }
    .glow-bg {
      position: fixed;
      top: -100px;
      right: -100px;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, rgba(0, 0, 0, 0) 70%);
      pointer-events: none;
      z-index: 0;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #ffd700, #ff8c00);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 20px;
      color: #000;
      box-shadow: 0 4px 14px rgba(255, 188, 0, 0.4);
    }
    .title-area h1 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.01em;
    }
    .stats-badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(255, 188, 0, 0.15);
      color: #ffbc00;
      border: 1px solid rgba(255, 188, 0, 0.3);
    }
    .search-box {
      width: 100%;
      position: relative;
      margin-bottom: 14px;
    }
    .search-input {
      width: 100%;
      padding: 12px 16px 12px 42px;
      border-radius: 12px;
      background: rgba(18, 20, 29, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #fff;
      font-size: 0.92rem;
      outline: none;
      transition: all 0.2s ease;
    }
    .search-input:focus {
      border-color: #6366f1;
      box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
    }
    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: #94a3b8;
      font-size: 1rem;
    }
    .filter-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .tab {
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #94a3b8;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .tab.active {
      background: #6366f1;
      color: #fff;
      border-color: #6366f1;
    }
    .media-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    .media-card {
      background: rgba(18, 20, 29, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.2s ease;
    }
    .media-card:hover {
      border-color: rgba(99, 102, 241, 0.4);
    }
    .card-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }
    .card-title {
      font-size: 0.95rem;
      font-weight: 600;
      color: #f8fafc;
      line-height: 1.35;
    }
    .badge-quality {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 6px;
      background: rgba(99, 102, 241, 0.2);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.3);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .card-meta {
      font-size: 0.78rem;
      color: #94a3b8;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .card-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 4px;
    }
    .btn {
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.2s ease;
    }
    .btn-watch {
      background: #6366f1;
      color: #fff;
      border-color: #6366f1;
    }
    .btn-watch:hover {
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    .btn-copy {
      background: #1e2235;
      color: #ffbc00;
      border-color: rgba(255, 188, 0, 0.3);
    }
    .btn-copy:hover {
      background: rgba(255, 188, 0, 0.15);
    }
    .btn-del {
      background: rgba(239, 68, 68, 0.12);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.25);
      margin-left: auto;
    }
    .btn-del:hover {
      background: rgba(239, 68, 68, 0.3);
    }
    .empty-state {
      text-align: center;
      padding: 40px 20px;
      color: #94a3b8;
    }
    .toast {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #10b981;
      color: #fff;
      font-weight: 600;
      font-size: 0.85rem;
      padding: 8px 18px;
      border-radius: 20px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
      z-index: 100;
      display: none;
    }
    .auth-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(9, 10, 15, 0.95);
      backdrop-filter: blur(14px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
    }
    .auth-card {
      background: #141724;
      border: 1px solid rgba(255, 188, 0, 0.35);
      border-radius: 18px;
      padding: 32px 24px;
      max-width: 380px;
      width: 100%;
      text-align: center;
      box-shadow: 0 12px 50px rgba(0, 0, 0, 0.8);
    }
    .auth-icon {
      font-size: 2.2rem;
      margin-bottom: 12px;
    }
    .auth-card h2 {
      font-size: 1.25rem;
      color: #fff;
      margin-bottom: 6px;
    }
    .auth-card p {
      font-size: 0.82rem;
      color: #94a3b8;
      margin-bottom: 20px;
      line-height: 1.4;
    }
    .auth-input {
      width: 100%;
      padding: 12px 14px;
      background: #090a0f;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 10px;
      color: #fff;
      font-size: 0.92rem;
      text-align: center;
      letter-spacing: 1px;
      margin-bottom: 14px;
      outline: none;
    }
    .auth-input:focus {
      border-color: #ffbc00;
      box-shadow: 0 0 12px rgba(255, 188, 0, 0.3);
    }
    .auth-btn {
      width: 100%;
      padding: 12px;
      background: linear-gradient(135deg, #ffd700, #ff8c00);
      color: #000;
      border: none;
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.92rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .auth-btn:hover {
      opacity: 0.92;
      transform: translateY(-1px);
    }
    .auth-error {
      color: #ef4444;
      font-size: 0.78rem;
      margin-top: 10px;
      display: none;
    }
  </style>
</head>
<body>
  <div class="glow-bg"></div>
  <div class="container">
    <div class="header">
      <div class="brand">
        <div class="logo">F</div>
        <div class="title-area">
          <h1>FilmHouse Library</h1>
        </div>
      </div>
      <span id="statsBadge" class="stats-badge">Loading...</span>
    </div>

    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" class="search-input" placeholder="Search by movie title, episode, or season...">
    </div>

    <div class="filter-tabs">
      <button class="tab active" data-filter="all">All Media</button>
      <button class="tab" data-filter="series">TV Series</button>
      <button class="tab" data-filter="movies">Movies</button>
    </div>

    <div id="mediaGrid" class="media-grid">
      <!-- Media Cards Injected Here -->
    </div>
  </div>

  <div id="copyToast" class="toast">✅ Stream URL copied to clipboard!</div>

  <!-- Admin Verification Modal -->
  <div id="authModal" class="auth-overlay">
    <div class="auth-card">
      <div class="auth-icon">🔐</div>
      <h2>Admin Access Required</h2>
      <p>This library contains private streaming keys. Please enter your Admin Passcode to unlock:</p>
      <input type="password" id="adminKeyInput" class="auth-input" placeholder="Admin Passcode..." onkeydown="if(event.key==='Enter') submitAuth()">
      <button onclick="submitAuth()" class="auth-btn">Unlock Library</button>
      <div id="authError" class="auth-error">❌ Unauthorized or invalid passcode.</div>
    </div>
  </div>

  <script>
    // Initialize Telegram WebApp API if inside Telegram
    if (window.Telegram && window.Telegram.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }

    let allMedia = [];
    let currentFilter = "all";

    function showToast(text) {
      const toast = document.getElementById('copyToast');
      toast.textContent = text;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 2000);
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast("✅ Stream URL copied to clipboard!");
      }).catch(() => {
        prompt("Copy Stream URL:", text);
      });
    }

    function showAuthModal() {
      document.getElementById('authModal').style.display = 'flex';
      document.getElementById('adminKeyInput').focus();
    }

    function hideAuthModal() {
      document.getElementById('authModal').style.display = 'none';
    }

    function getAuthHeaders() {
      const headers = { 'Content-Type': 'application/json' };
      const tgInit = window.Telegram?.WebApp?.initData;
      if (tgInit) {
        headers['X-Telegram-Init-Data'] = tgInit;
      }
      const urlKey = new URLSearchParams(window.location.search).get('admin_key');
      const storedKey = sessionStorage.getItem('filmhouse_admin_key') || urlKey;
      if (storedKey) {
        headers['X-Admin-Key'] = storedKey;
      }
      return headers;
    }

    async function loadMedia() {
      try {
        const res = await fetch('/api/media', {
          headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) {
          showAuthModal();
          return;
        }

        const data = await res.json();
        if (!data.success) {
          showAuthModal();
          return;
        }

        hideAuthModal();
        allMedia = data.items || [];
        document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
        renderMedia();
      } catch (e) {
        document.getElementById('mediaGrid').innerHTML = '<div class="empty-state">Failed to load media: ' + e.message + '</div>';
      }
    }

    async function submitAuth() {
      const input = document.getElementById('adminKeyInput');
      const key = input.value.trim();
      const err = document.getElementById('authError');
      if (!key) return;

      sessionStorage.setItem('filmhouse_admin_key', key);
      try {
        const res = await fetch('/api/media', {
          headers: getAuthHeaders()
        });

        if (res.ok) {
          err.style.display = 'none';
          hideAuthModal();
          const data = await res.json();
          allMedia = data.items || [];
          document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
          renderMedia();
        } else {
          err.textContent = '❌ Incorrect Admin Passcode or Unauthorized Account.';
          err.style.display = 'block';
        }
      } catch (e) {
        err.textContent = '❌ Connection failed.';
        err.style.display = 'block';
      }
    }

    async function deleteMedia(messageId, title) {
      if (!confirm(`Are you sure you want to delete "${title}" from your storage channel?`)) return;
      try {
        const res = await fetch('/api/media/delete', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ message_id: messageId })
        });
        const result = await res.json();
        if (result.success) {
          showToast("🗑️ Media deleted successfully!");
          allMedia = allMedia.filter(m => m.message_id !== messageId);
          document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
          renderMedia();
        } else {
          alert("Error: " + (result.error || "Could not delete."));
        }
      } catch (e) {
        alert("Failed to delete media.");
      }
    }

    function renderMedia() {
      const grid = document.getElementById('mediaGrid');
      const query = document.getElementById('searchInput').value.toLowerCase().trim();

      const filtered = allMedia.filter(item => {
        const titleMatch = (item.display_name || item.file_name).toLowerCase().includes(query);
        if (!titleMatch) return false;

        if (currentFilter === "series") return item.is_series;
        if (currentFilter === "movies") return !item.is_series;
        return true;
      });

      if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-state">No media matches your search.</div>';
        return;
      }

      grid.innerHTML = filtered.map(item => `
        <div class="media-card">
          <div class="card-top">
            <div class="card-title">${item.display_name}</div>
            <span class="badge-quality">${item.quality || 'HD'}</span>
          </div>
          <div class="card-meta">
            <span>📁 ${item.file_name}</span>
            ${item.file_size_str ? `<span>📦 ${item.file_size_str}</span>` : ''}
          </div>
          <div class="card-actions">
            <a href="${item.watch_url}" target="_blank" class="btn btn-watch">▶ Play</a>
            <button onclick="copyToClipboard('${item.stream_url}')" class="btn btn-copy">📋 Copy Link</button>
            <a href="${item.blogger_url}" target="_blank" class="btn" style="background:#141724;color:#ffbc00;">🍿 Blogspot</a>
            <button onclick="deleteMedia(${item.message_id}, '${item.display_name}')" class="btn btn-del">🗑️</button>
          </div>
        </div>
      `).join('');
    }

    // Filter tabs
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter;
        renderMedia();
      });
    });

    document.getElementById('searchInput').addEventListener('input', renderMedia);

    // Initial load
    loadMedia();
  </script>
</body>
</html>
"""
