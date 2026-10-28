LIBRARY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>FilmHouse Cinema Library</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    *, *::before, *::after {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    html, body {
      width: 100%;
      max-width: 100vw;
      min-height: 100vh;
      overflow-x: hidden;
      background: #090a0f;
      color: #f1f5f9;
      -webkit-font-smoothing: antialiased;
      -webkit-tap-highlight-color: transparent;
    }
    .glow-bg {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: radial-gradient(circle at 80% 10%, rgba(99, 102, 241, 0.14) 0%, rgba(9, 10, 15, 0) 65%);
      pointer-events: none;
      z-index: 0;
    }
    .container {
      width: 100%;
      max-width: 580px;
      margin: 0 auto;
      padding: max(14px, env(safe-area-inset-top)) 14px max(24px, env(safe-area-inset-bottom)) 14px;
      position: relative;
      z-index: 1;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
      gap: 10px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .logo {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #ffd700, #ff8c00);
      border-radius: 11px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      color: #000;
      box-shadow: 0 4px 14px rgba(255, 188, 0, 0.35);
      flex-shrink: 0;
    }
    .title-area h1 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.01em;
      line-height: 1.2;
    }
    .stats-badge {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(255, 188, 0, 0.12);
      color: #ffbc00;
      border: 1px solid rgba(255, 188, 0, 0.25);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .search-box {
      width: 100%;
      position: relative;
      margin-bottom: 12px;
    }
    .search-input {
      width: 100%;
      padding: 11px 36px 11px 38px;
      border-radius: 12px;
      background: rgba(18, 20, 29, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #fff;
      font-size: 0.9rem;
      outline: none;
      transition: all 0.2s ease;
    }
    .search-input:focus {
      border-color: #6366f1;
      background: rgba(22, 25, 38, 0.95);
      box-shadow: 0 0 14px rgba(99, 102, 241, 0.25);
    }
    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: #94a3b8;
      font-size: 0.95rem;
      pointer-events: none;
    }
    .search-clear {
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: #64748b;
      cursor: pointer;
      display: none;
      font-size: 0.9rem;
      padding: 4px;
    }
    .filter-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
      padding-bottom: 2px;
      width: 100%;
    }
    .filter-tabs::-webkit-scrollbar {
      display: none;
    }
    .tab {
      flex: 1 0 auto;
      text-align: center;
      padding: 7px 14px;
      border-radius: 9px;
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
      box-shadow: 0 2px 10px rgba(99, 102, 241, 0.35);
    }
    .media-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }
    .media-card {
      width: 100%;
      background: rgba(18, 20, 29, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      transition: border-color 0.2s ease;
    }
    .media-card:hover {
      border-color: rgba(99, 102, 241, 0.35);
    }
    .card-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      width: 100%;
    }
    .card-title {
      font-size: 0.96rem;
      font-weight: 700;
      color: #f8fafc;
      line-height: 1.35;
      word-break: break-word;
      overflow-wrap: break-word;
      flex: 1;
    }
    .badge-quality {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.35);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .card-meta {
      display: flex;
      flex-direction: column;
      gap: 6px;
      width: 100%;
    }
    .file-badge {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.72rem;
      color: #94a3b8;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      padding: 5px 8px;
      border-radius: 8px;
      word-break: break-all;
      overflow-wrap: anywhere;
      line-height: 1.3;
    }
    .size-badge {
      font-size: 0.73rem;
      color: #cbd5e1;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .card-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
      margin-top: 2px;
    }
    .action-row {
      display: flex;
      gap: 8px;
      width: 100%;
    }
    .btn {
      min-height: 38px;
      padding: 8px 12px;
      border-radius: 10px;
      font-size: 0.8rem;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.15s ease;
      user-select: none;
    }
    .btn:active {
      transform: scale(0.97);
    }
    .btn-watch {
      flex: 1;
      background: linear-gradient(135deg, #6366f1, #7c3aed);
      color: #fff;
      border-color: #6366f1;
      font-weight: 700;
      box-shadow: 0 3px 10px rgba(99, 102, 241, 0.3);
    }
    .btn-blogger {
      flex: 1;
      background: #191c2b;
      color: #ffbc00;
      border-color: rgba(255, 188, 0, 0.3);
      font-weight: 600;
    }
    .btn-copy {
      flex: 1;
      background: rgba(255, 255, 255, 0.05);
      color: #e2e8f0;
      border-color: rgba(255, 255, 255, 0.1);
    }
    .btn-del {
      width: 40px;
      flex-shrink: 0;
      background: rgba(239, 68, 68, 0.12);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.25);
      padding: 0;
    }
    .btn-del:active {
      background: rgba(239, 68, 68, 0.25);
    }
    .empty-state {
      text-align: center;
      padding: 40px 16px;
      color: #94a3b8;
      font-size: 0.88rem;
    }
    .toast {
      position: fixed;
      bottom: max(20px, env(safe-area-inset-bottom));
      left: 50%;
      transform: translateX(-50%);
      background: #10b981;
      color: #fff;
      font-weight: 600;
      font-size: 0.82rem;
      padding: 8px 18px;
      border-radius: 20px;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
      z-index: 100;
      display: none;
      white-space: nowrap;
    }
    .auth-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(9, 10, 15, 0.95);
      backdrop-filter: blur(14px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 20px;
      box-sizing: border-box;
    }
    .auth-card {
      background: #141724;
      border: 1px solid rgba(255, 188, 0, 0.35);
      border-radius: 18px;
      padding: 28px 20px;
      max-width: 360px;
      width: 100%;
      text-align: center;
      box-shadow: 0 12px 50px rgba(0, 0, 0, 0.8);
      box-sizing: border-box;
    }
    .auth-icon {
      font-size: 2.2rem;
      margin-bottom: 10px;
    }
    .auth-card h2 {
      font-size: 1.2rem;
      color: #fff;
      margin-bottom: 6px;
    }
    .auth-card p {
      font-size: 0.8rem;
      color: #94a3b8;
      margin-bottom: 18px;
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
      margin-bottom: 12px;
      outline: none;
      box-sizing: border-box;
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
      box-sizing: border-box;
    }
    .auth-btn:active {
      transform: scale(0.98);
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
      <input type="text" id="searchInput" class="search-input" placeholder="Search movies, episodes, seasons...">
      <span id="searchClear" class="search-clear" onclick="clearSearch()">✕</span>
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
      try {
        window.Telegram.WebApp.setHeaderColor('#090a0f');
        window.Telegram.WebApp.setBackgroundColor('#090a0f');
      } catch(e) {}
    }

    let allMedia = [];
    let currentFilter = "all";

    function showToast(text) {
      const toast = document.getElementById('copyToast');
      toast.textContent = text;
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 2200);
    }

    function copyToClipboard(text) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          showToast("✅ Stream URL copied!");
        }).catch(() => {
          prompt("Copy Stream URL:", text);
        });
      } else {
        prompt("Copy Stream URL:", text);
      }
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
        document.getElementById('mediaGrid').innerHTML = '<div class="empty-state">Failed to load media. Check network connection.</div>';
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
      if (!confirm(`Delete "${title}" from your storage channel permanently?`)) return;
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

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/'/g, '&#39;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
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
        grid.innerHTML = '<div class="empty-state">No media found matching your filter.</div>';
        return;
      }

      grid.innerHTML = filtered.map(item => `
        <div class="media-card">
          <div class="card-top">
            <div class="card-title">${escapeHtml(item.display_name)}</div>
            <span class="badge-quality">${escapeHtml(item.quality || 'HD')}</span>
          </div>
          <div class="card-meta">
            <div class="file-badge">📁 ${escapeHtml(item.file_name)}</div>
            ${item.file_size_str ? `<span class="size-badge">📦 ${escapeHtml(item.file_size_str)}</span>` : ''}
          </div>
          <div class="card-actions">
            <div class="action-row">
              <a href="${item.watch_url}" target="_blank" class="btn btn-watch">▶ Play Stream</a>
              <a href="${item.blogger_url}" target="_blank" class="btn btn-blogger">🍿 Blogspot</a>
            </div>
            <div class="action-row">
              <button onclick="copyToClipboard('${item.stream_url}')" class="btn btn-copy">📋 Copy Stream Link</button>
              <button onclick="deleteMedia(${item.message_id}, '${escapeHtml(item.display_name)}')" class="btn btn-del" title="Delete from Storage">🗑️</button>
            </div>
          </div>
        </div>
      `).join('');
    }

    function clearSearch() {
      const input = document.getElementById('searchInput');
      input.value = '';
      document.getElementById('searchClear').style.display = 'none';
      renderMedia();
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

    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', () => {
      document.getElementById('searchClear').style.display = searchInput.value ? 'block' : 'none';
      renderMedia();
    });

    // Initial load
    loadMedia();
  </script>
</body>
</html>
"""
