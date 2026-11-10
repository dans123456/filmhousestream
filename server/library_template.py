LIBRARY_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>FilmHouse Cinema Library</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <!-- Monetag Telegram Mini App Rewarded Ad SDK -->
  <script src="https://libtl.com/sdk.js" data-zone="12146431" data-sdk="show_12146431"></script>
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
      padding: max(14px, env(safe-area-inset-top)) 14px 100px 14px;
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
    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
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
    }
    .btn-select-toggle {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.3);
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-select-toggle.active {
      background: #6366f1;
      color: #fff;
      border-color: #6366f1;
    }
    .btn-refresh {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.2s ease;
      user-select: none;
      white-space: nowrap;
    }
    .btn-refresh:hover:not(:disabled) {
      background: rgba(16, 185, 129, 0.25);
      border-color: rgba(16, 185, 129, 0.55);
      transform: translateY(-1px);
    }
    .btn-refresh:active:not(:disabled) {
      transform: translateY(0);
    }
    .btn-refresh:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .refresh-icon {
      display: inline-block;
      font-size: 0.82rem;
      line-height: 1;
    }
    .refresh-icon.spinning {
      animation: spinRefresh 0.75s linear infinite;
    }
    @keyframes spinRefresh {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    @media (max-width: 400px) {
      .btn-refresh .refresh-text {
        display: none;
      }
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
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 13px;
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
      background: linear-gradient(135deg, #6366f1, #7c3aed);
      color: #fff;
      border-color: #6366f1;
      box-shadow: 0 2px 10px rgba(99, 102, 241, 0.35);
    }
    .tab-count {
      font-size: 0.68rem;
      font-weight: 700;
      background: rgba(0, 0, 0, 0.3);
      padding: 1px 6px;
      border-radius: 999px;
      color: #cbd5e1;
    }
    .tab.active .tab-count {
      background: rgba(255, 255, 255, 0.25);
      color: #fff;
    }
    .category-section {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 22px;
      width: 100%;
    }
    .category-section-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 11px 15px;
      background: linear-gradient(90deg, rgba(28, 33, 54, 0.95), rgba(18, 21, 35, 0.9));
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-left: 4px solid #6366f1;
      border-radius: 14px;
      cursor: pointer;
      user-select: none;
      transition: all 0.2s ease;
    }
    .category-section-banner:hover {
      background: linear-gradient(90deg, rgba(34, 40, 66, 0.95), rgba(22, 26, 44, 0.9));
      border-color: rgba(99, 102, 241, 0.45);
    }
    .category-banner-left {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      min-width: 0;
    }
    .category-banner-icon {
      font-size: 1.25rem;
      line-height: 1;
      flex-shrink: 0;
    }
    .category-banner-title {
      font-size: 0.93rem;
      font-weight: 700;
      color: #f8fafc;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .category-banner-count {
      font-size: 0.72rem;
      font-weight: 600;
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.35);
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .category-banner-toggle {
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      color: #94a3b8;
      transition: transform 0.2s ease;
      flex-shrink: 0;
    }
    .category-banner-toggle.collapsed {
      transform: rotate(-90deg);
    }
    .category-section-content {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
    }
    .category-section-content.collapsed {
      display: none;
    }
    .badge-category {
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 6px;
      background: rgba(255, 188, 0, 0.12);
      color: #facc15;
      border: 1px solid rgba(255, 188, 0, 0.25);
      cursor: pointer;
      white-space: nowrap;
      user-select: none;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }
    .badge-category:hover {
      background: rgba(255, 188, 0, 0.22);
      border-color: rgba(255, 188, 0, 0.45);
    }
    .btn-bulk-category {
      background: rgba(255, 188, 0, 0.15);
      color: #facc15;
      border: 1px solid rgba(255, 188, 0, 0.3);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-bulk-category:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .category-modal-options {
      display: flex;
      flex-direction: column;
      gap: 7px;
      width: 100%;
      margin: 10px 0;
    }
    .cat-modal-btn {
      width: 100%;
      padding: 10px 14px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #f1f5f9;
      font-size: 0.84rem;
      font-weight: 600;
      text-align: left;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
    }
    .cat-modal-btn:hover {
      background: rgba(99, 102, 241, 0.2);
      border-color: rgba(99, 102, 241, 0.45);
      color: #fff;
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
      transition: all 0.2s ease;
      position: relative;
    }
    .media-card.selected {
      border-color: rgba(255, 188, 0, 0.5);
      background: rgba(30, 28, 22, 0.95);
      box-shadow: 0 0 16px rgba(255, 188, 0, 0.15);
    }
    .card-top {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      width: 100%;
    }
    .card-checkbox {
      display: none;
      align-items: center;
      justify-content: center;
      margin-top: 2px;
      flex-shrink: 0;
    }
    .card-checkbox input[type="checkbox"] {
      width: 20px;
      height: 20px;
      accent-color: #ffbc00;
      cursor: pointer;
      border-radius: 5px;
    }
    .select-mode-active .card-checkbox {
      display: flex;
    }
    .card-title-wrap {
      flex: 1;
      min-width: 0;
    }
    .card-title {
      font-size: 0.96rem;
      font-weight: 700;
      color: #f8fafc;
      line-height: 1.35;
      word-break: break-word;
      overflow-wrap: break-word;
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
      gap: 6px;
      width: 100%;
      margin-top: 2px;
      box-sizing: border-box;
    }
    .action-row {
      display: flex;
      gap: 6px;
      width: 100%;
      box-sizing: border-box;
    }
    .btn {
      min-height: 36px;
      padding: 6px 10px;
      border-radius: 10px;
      font-size: 0.78rem;
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
      box-sizing: border-box;
      white-space: nowrap;
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
      width: 38px;
      flex: 0 0 38px;
      background: rgba(239, 68, 68, 0.12);
      color: #fca5a5;
      border-color: rgba(239, 68, 68, 0.25);
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s;
    }
    .btn-edit {
      width: 38px;
      flex: 0 0 38px;
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.3);
      padding: 0;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      transition: all 0.2s ease;
    }
    .btn-edit:hover {
      background: rgba(99, 102, 241, 0.3);
      border-color: rgba(99, 102, 241, 0.6);
      transform: translateY(-1px);
    }
    /* Series Folder Card Styling */
    .series-folder-card {
      width: 100%;
      background: linear-gradient(180deg, rgba(24, 27, 40, 0.98) 0%, rgba(14, 16, 26, 0.98) 100%);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 18px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transition: all 0.2s ease;
      position: relative;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .folder-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      cursor: pointer;
      user-select: none;
    }
    .folder-title-box {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      min-width: 0;
    }
    .folder-icon {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(168, 85, 247, 0.3));
      border: 1px solid rgba(99, 102, 241, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
    }
    .folder-info {
      flex: 1;
      min-width: 0;
    }
    .folder-name {
      font-size: 1.05rem;
      font-weight: 700;
      color: #fff;
      line-height: 1.3;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .folder-meta {
      font-size: 0.74rem;
      color: #94a3b8;
      margin-top: 2px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .folder-toggle-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      transition: transform 0.2s ease;
      flex-shrink: 0;
      cursor: pointer;
    }
    .folder-toggle-btn.expanded {
      transform: rotate(180deg);
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
    }

    /* Season Tabs within Series Folder */
    .season-tabs {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
      padding-bottom: 2px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      padding-top: 4px;
    }
    .season-tabs::-webkit-scrollbar { display: none; }
    .season-tab {
      padding: 5px 12px;
      border-radius: 8px;
      font-size: 0.76rem;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.04);
      color: #94a3b8;
      border: 1px solid rgba(255, 255, 255, 0.06);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }
    .season-tab.active {
      background: #ffbc00;
      color: #000;
      border-color: #ffbc00;
      box-shadow: 0 2px 8px rgba(255, 188, 0, 0.35);
    }

    /* Season Subfolders Inside Series Card */
    .season-subfolders-container {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 6px;
    }
    .season-subfolder-box {
      background: rgba(10, 12, 18, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      overflow: hidden;
      transition: all 0.2s ease;
    }
    .season-subfolder-header {
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      cursor: pointer;
      user-select: none;
      background: rgba(255, 255, 255, 0.03);
      transition: background 0.2s ease;
    }
    .season-subfolder-header:hover {
      background: rgba(99, 102, 241, 0.12);
    }
    .season-subfolder-title {
      font-size: 0.9rem;
      font-weight: 700;
      color: #f8fafc;
    }
    .season-badge-count {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(255, 188, 0, 0.15);
      color: #ffbc00;
    }

    /* Multi-Quality Movie Grouping */
    .multi-quality-card {
      width: 100%;
      background: linear-gradient(180deg, rgba(24, 27, 40, 0.98) 0%, rgba(14, 16, 26, 0.98) 100%);
      border: 1px solid rgba(168, 85, 247, 0.35);
      border-radius: 18px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .multi-quality-badge {
      font-size: 0.72rem;
      font-weight: 800;
      background: linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25));
      border: 1px solid rgba(168, 85, 247, 0.4);
      color: #d8b4fe;
      padding: 3px 9px;
      border-radius: 7px;
      white-space: nowrap;
    }
    .quality-versions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 4px;
    }
    .quality-version-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px 10px;
      background: rgba(10, 12, 18, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 10px;
    }
    .quality-version-info {
      display: flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      min-width: 180px;
    }
    .quality-version-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    /* Episode Row within Folder */
    .episodes-wrapper {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 4px;
      box-sizing: border-box;
      max-width: 100%;
    }
    .episode-row {
      background: rgba(10, 12, 18, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-sizing: border-box;
      max-width: 100%;
      overflow: hidden;
    }
    .episode-row-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      min-width: 0;
      width: 100%;
      box-sizing: border-box;
    }
    .episode-num-badge {
      font-weight: 800;
      font-size: 0.8rem;
      color: #ffbc00;
      background: rgba(255, 188, 0, 0.1);
      padding: 2px 8px;
      border-radius: 6px;
      white-space: nowrap;
    }
    .episode-title-text {
      font-size: 0.84rem;
      font-weight: 600;
      color: #f1f5f9;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .folder-admin-bar {
      display: flex;
      gap: 8px;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      margin-top: 4px;
    }
    .btn-folder-all {
      flex: 1;
      background: rgba(255, 188, 0, 0.12);
      color: #ffbc00;
      border: 1px solid rgba(255, 188, 0, 0.3);
      font-size: 0.78rem;
      font-weight: 700;
      padding: 8px 12px;
      border-radius: 9px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-folder-all:active {
      transform: scale(0.97);
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

    /* Floating Bulk Delete Action Bar */
    .bulk-bar {
      position: fixed;
      bottom: max(14px, env(safe-area-inset-bottom));
      left: 50%;
      transform: translateX(-50%);
      width: calc(100% - 28px);
      max-width: 550px;
      background: #141724;
      border: 1px solid rgba(255, 188, 0, 0.35);
      border-radius: 16px;
      padding: 10px 14px;
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
      z-index: 200;
    }
    .bulk-count {
      font-size: 0.82rem;
      font-weight: 700;
      color: #ffbc00;
      white-space: nowrap;
    }
    .btn-bulk-text {
      background: transparent;
      border: none;
      color: #a5b4fc;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .btn-bulk-delete {
      padding: 8px 16px;
      background: #ef4444;
      color: #fff;
      border: none;
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-bulk-delete:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .btn-bulk-cancel {
      background: rgba(255, 255, 255, 0.08);
      border: none;
      color: #94a3b8;
      width: 32px;
      height: 32px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.9rem;
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

    /* Mobile Responsive Optimizations */
    @media (max-width: 480px) {
      .container {
        padding-left: 10px;
        padding-right: 10px;
      }
      .series-folder-card {
        padding: 12px 10px;
      }
      .season-subfolders-container {
        padding: 6px;
      }
      .season-subfolder-box {
        border-radius: 10px;
      }
      .episodes-wrapper {
        padding: 6px !important;
        gap: 6px;
      }
      .episode-row {
        padding: 8px 10px;
        gap: 6px;
      }
      .action-row {
        gap: 5px;
      }
      .btn {
        min-height: 32px;
        font-size: 0.74rem;
        padding: 4px 6px;
      }
      .btn-del, .btn-edit {
        width: 36px;
        flex: 0 0 36px;
      }
      .quality-version-row {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        padding: 8px;
      }
      .quality-version-info {
        width: 100%;
        min-width: 0;
      }
      .quality-version-actions {
        width: 100%;
        display: flex;
        gap: 5px;
      }
      .quality-version-actions .btn {
        flex: 1;
        min-width: 0;
        padding: 4px 6px;
        font-size: 0.72rem;
      }
      .quality-version-actions .btn-edit,
      .quality-version-actions .btn-del {
        flex: 0 0 34px;
        width: 34px;
      }
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
      <div class="header-actions">
        <span id="statsBadge" class="stats-badge">Loading...</span>
        <button id="refreshBtn" class="btn-refresh" onclick="refreshLibrary(event)" title="Refresh library without reloading the page">
          <span class="refresh-icon" id="refreshIcon">🔄</span>
          <span class="refresh-text">Refresh</span>
        </button>
        <button id="selectToggleBtn" class="btn-select-toggle" onclick="toggleSelectMode()">☑️ Select</button>
      </div>
    </div>

    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" class="search-input" placeholder="Search movies, episodes, seasons...">
      <span id="searchClear" class="search-clear" onclick="clearSearch()">✕</span>
    </div>

    <div class="filter-tabs" id="categoryTabs">
      <button class="tab active" data-filter="all">🌐 All <span class="tab-count" id="count-all">0</span></button>
      <button class="tab" data-filter="movies">🎬 Movies <span class="tab-count" id="count-movies">0</span></button>
      <button class="tab" data-filter="series">📺 Series <span class="tab-count" id="count-series">0</span></button>
      <button class="tab" data-filter="anime">⚔️ Anime <span class="tab-count" id="count-anime">0</span></button>
      <button class="tab" data-filter="kdrama">🌸 K-Drama <span class="tab-count" id="count-kdrama">0</span></button>
      <button class="tab" data-filter="african">🌍 African <span class="tab-count" id="count-african">0</span></button>
      <button class="tab" data-filter="bollywood">👳 Bollywood <span class="tab-count" id="count-bollywood">0</span></button>
      <button class="tab" data-filter="cartoons">🎨 Cartoons <span class="tab-count" id="count-cartoons">0</span></button>
      <button class="tab" data-filter="incomplete" style="border-color:rgba(239,68,68,0.35); color:#fca5a5;" title="Series with missing episodes or incomplete seasons">⚠️ Incomplete <span class="tab-count" id="count-incomplete" style="background:rgba(239,68,68,0.25); color:#fca5a5;">0</span></button>
    </div>

    <div id="mediaGrid" class="media-grid">
      <div id="loadingPlaceholder" class="empty-state" style="padding: 50px 20px;">
        <div style="font-size:2.4rem; margin-bottom:12px;">🍿</div>
        <div style="font-size:1.05rem; font-weight:700; color:#fff; margin-bottom:6px;">Opening Cinema Library...</div>
        <div style="font-size:0.8rem; color:#94a3b8;">Loading over 6,400 titles...</div>
      </div>
    </div>
  </div>

  <!-- Floating Bulk Action Bar -->
  <div id="bulkActionBar" class="bulk-bar">
    <button class="btn-bulk-text" onclick="toggleSelectAll()">
      <span id="selectAllIcon">☑️</span> <span id="selectAllLabel">All</span>
    </button>
    <span id="selectedCountBadge" class="bulk-count">0 Selected</span>
    <button id="bulkCatBtn" class="btn-bulk-category" onclick="openBulkCategoryModal()" disabled>🏷️ Set Category</button>
    <button id="bulkDeleteBtn" class="btn-bulk-delete" onclick="executeBulkDelete()" disabled>🗑️ Delete</button>
    <button class="btn-bulk-cancel" onclick="exitSelectMode()" title="Cancel Selection">✕</button>
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

  <!-- Category Change Modal -->
  <div id="categoryModal" class="auth-overlay" style="display:none;">
    <div class="auth-card" style="max-width: 360px;">
      <div class="auth-icon">🏷️</div>
      <h2 id="catModalTitle" style="font-size:1.1rem; margin-bottom:4px;">Set Category</h2>
      <p id="catModalDesc" style="font-size:0.8rem; margin-bottom:12px; color:#94a3b8;">Choose a category for this media:</p>
      <div class="category-modal-options">
        <button class="cat-modal-btn" onclick="applyCategoryChange('movies')">🎬 Hollywood & Global Movies</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('series')">📺 Western TV Series</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('anime')">⚔️ Anime</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('kdrama')">🌸 K-Drama & Asian Drama</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('african')">🌍 African Cinema & Series</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('bollywood')">👳 Bollywood & Indian Cinema</button>
        <button class="cat-modal-btn" onclick="applyCategoryChange('cartoons')">🎨 Cartoons & Animation</button>
      </div>
      <button onclick="closeCategoryModal()" class="btn" style="width:100%; margin-top:10px; background:rgba(255,255,255,0.06); color:#94a3b8;">Cancel</button>
    </div>
  </div>

  <!-- Edit Media Metadata Modal -->
  <div id="editModal" class="auth-overlay" style="display:none;">
    <div class="auth-card" style="max-width: 380px; text-align: left;">
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <span style="font-size:1.4rem;">✏️</span>
        <div>
          <h2 style="font-size:1.1rem; margin:0; color:#fff;">Edit Media Info</h2>
          <p style="font-size:0.75rem; color:#94a3b8; margin:0;">Fix title, season, episode, or category</p>
        </div>
      </div>

      <input type="hidden" id="editMid">

      <div style="margin-bottom:10px;">
        <label style="font-size:0.75rem; color:#a5b4fc; font-weight:600; display:block; margin-bottom:4px;">Title</label>
        <input type="text" id="editTitle" class="auth-input" style="width:100%; box-sizing:border-box; margin:0;" placeholder="e.g. Friends">
      </div>

      <div style="margin-bottom:10px;">
        <label style="font-size:0.75rem; color:#a5b4fc; font-weight:600; display:block; margin-bottom:4px;">Type</label>
        <select id="editIsSeries" class="auth-input" style="width:100%; box-sizing:border-box; margin:0; background:#12141d; color:#fff;" onchange="toggleEditSeriesFields()">
          <option value="true">📺 TV / Web Series</option>
          <option value="false">🎬 Movie</option>
        </select>
      </div>

      <div id="editSeriesFields" style="display:flex; gap:10px; margin-bottom:10px;">
        <div style="flex:1;">
          <label style="font-size:0.75rem; color:#a5b4fc; font-weight:600; display:block; margin-bottom:4px;">Season #</label>
          <input type="number" id="editSeason" class="auth-input" style="width:100%; box-sizing:border-box; margin:0;" placeholder="1" min="1">
        </div>
        <div style="flex:1;">
          <label style="font-size:0.75rem; color:#a5b4fc; font-weight:600; display:block; margin-bottom:4px;">Episode #</label>
          <input type="number" id="editEpisode" class="auth-input" style="width:100%; box-sizing:border-box; margin:0;" placeholder="16" min="1">
        </div>
      </div>

      <div style="margin-bottom:14px;">
        <label style="font-size:0.75rem; color:#a5b4fc; font-weight:600; display:block; margin-bottom:4px;">Category Hub</label>
        <select id="editCategory" class="auth-input" style="width:100%; box-sizing:border-box; margin:0; background:#12141d; color:#fff;">
          <option value="series">📺 Western TV Series</option>
          <option value="movies">🎬 Hollywood & Global Movies</option>
          <option value="anime">⚔️ Anime</option>
          <option value="kdrama">🌸 K-Drama & Asian Drama</option>
          <option value="african">🌍 African Cinema & Nollywood</option>
          <option value="bollywood">👳 Bollywood & Indian</option>
          <option value="cartoons">🎨 Cartoons & Animation</option>
        </select>
      </div>

      <div style="display:flex; gap:8px;">
        <button onclick="closeEditModal()" class="btn" style="flex:1; background:rgba(255,255,255,0.06); color:#94a3b8;">Cancel</button>
        <button onclick="submitEditMedia()" class="btn" style="flex:1.5; background:linear-gradient(135deg, #10b981, #059669); color:#fff; font-weight:700;">💾 Save Changes</button>
      </div>
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
    let isSelectMode = false;
    let selectedIds = new Set();

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

    // Monetag Rewarded Interstitial Ad Integration
    function openWithAd(event, targetUrl) {
      if (event) {
        try { event.preventDefault(); } catch(e) {}
      }

      function proceed() {
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(targetUrl);
        } else {
          window.open(targetUrl, '_blank');
        }
      }

      // Check if Monetag SDK is loaded and available
      if (typeof show_12146431 === 'function') {
        show_12146431()
          .then(() => {
            proceed();
          })
          .catch((err) => {
            console.warn('Monetag ad error or closed:', err);
            proceed();
          });
      } else {
        proceed();
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

    async function refreshLibrary(event) {
      if (event) event.stopPropagation();
      const btn = document.getElementById('refreshBtn');
      const icon = document.getElementById('refreshIcon');
      if (btn) btn.disabled = true;
      if (icon) icon.classList.add('spinning');

      try {
        await loadMedia(true);
      } finally {
        setTimeout(() => {
          if (btn) btn.disabled = false;
          if (icon) icon.classList.remove('spinning');
        }, 400);
      }
    }

    function safeParseJson(rawText) {
      if (!rawText || typeof rawText !== 'string') return null;
      const trimmed = rawText.trim();
      try {
        return JSON.parse(trimmed);
      } catch (e) {
        const sIdx = trimmed.indexOf('{');
        const eIdx = trimmed.lastIndexOf('}');
        if (sIdx !== -1 && eIdx > sIdx) {
          try {
            return JSON.parse(trimmed.substring(sIdx, eIdx + 1));
          } catch (inner) {}
        }
        const aIdx = trimmed.indexOf('[');
        const aeIdx = trimmed.lastIndexOf(']');
        if (aIdx !== -1 && aeIdx > aIdx) {
          try {
            return JSON.parse(trimmed.substring(aIdx, aeIdx + 1));
          } catch (inner) {}
        }
        throw new Error(trimmed.substring(0, 40));
      }
    }

    async function loadMedia(isManualRefresh = false) {
      const statsBadge = document.getElementById('statsBadge');
      if (statsBadge && isManualRefresh) statsBadge.textContent = 'Loading...';
      try {
        const tgInit = window.Telegram?.WebApp?.initData || '';
        const urlKey = new URLSearchParams(window.location.search).get('admin_key') || '';
        const storedKey = sessionStorage.getItem('filmhouse_admin_key') || urlKey;

        let apiUrl = '/api/media';
        const params = new URLSearchParams();
        if (tgInit) params.append('tgWebAppData', tgInit);
        if (storedKey) params.append('admin_key', storedKey);
        const qs = params.toString();
        if (qs) apiUrl += '?' + qs;

        const res = await fetch(apiUrl, {
          headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) {
          if (statsBadge) statsBadge.textContent = 'Auth Required';
          showAuthModal();
          return;
        }

        if (!res.ok) {
          throw new Error(`Server status ${res.status}`);
        }

        const rawText = await res.text();
        const data = safeParseJson(rawText);
        if (!data || !data.success) {
          throw new Error((data && data.error) || 'Invalid server response');
        }

        hideAuthModal();
        allMedia = data.items || [];
        if (statsBadge) statsBadge.textContent = `${allMedia.length} Titles`;
        updateCategoryCounts();
        renderMedia();
        fetchAuditData();

        if (isManualRefresh) {
          showToast(`🔄 Library refreshed! (${allMedia.length} titles)`);
        }

        // Quietly preload Monetag ad in background
        try {
          if (typeof show_12146431 === 'function') {
            show_12146431({ type: 'preload' });
          }
        } catch(e) {}
      } catch (e) {
        console.error("loadMedia error:", e);
        if (statsBadge) statsBadge.textContent = 'Connection Error';
        if (isManualRefresh) {
          showToast('⚠️ Refresh failed: ' + (e.message || 'Check network connection.'));
        } else {
          document.getElementById('mediaGrid').innerHTML = `
            <div class="empty-state">
              <p>⚠️ Failed to load media: ${escapeHtml(e.message || 'Check network connection')}.</p>
              <button onclick="loadMedia(true)" class="btn btn-watch" style="margin-top:12px; display:inline-block;">🔄 Retry</button>
            </div>`;
        }
      }
    }

    async function submitAuth() {
      const input = document.getElementById('adminKeyInput');
      const key = input.value.trim();
      const err = document.getElementById('authError');
      if (!key) return;

      sessionStorage.setItem('filmhouse_admin_key', key);
      try {
        const res = await fetch('/api/media?admin_key=' + encodeURIComponent(key), {
          headers: getAuthHeaders()
        });

        if (res.ok) {
          const rawText = await res.text();
          const data = safeParseJson(rawText);
          if (data && data.success) {
            err.style.display = 'none';
            hideAuthModal();
            allMedia = data.items || [];
            document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
            updateCategoryCounts();
            renderMedia();
            return;
          }
        }
        err.textContent = '❌ Incorrect Admin Passcode or Unauthorized Account.';
        err.style.display = 'block';
      } catch (e) {
        err.textContent = '❌ Connection failed.';
        err.style.display = 'block';
      }
    }

    // Toggle Multi-Select Mode
    function toggleSelectMode() {
      isSelectMode = !isSelectMode;
      const btn = document.getElementById('selectToggleBtn');
      const bulkBar = document.getElementById('bulkActionBar');
      const grid = document.getElementById('mediaGrid');

      if (isSelectMode) {
        btn.classList.add('active');
        btn.textContent = 'Done';
        bulkBar.style.display = 'flex';
        grid.classList.add('select-mode-active');
      } else {
        exitSelectMode();
      }
      updateBulkUI();
    }

    function exitSelectMode() {
      isSelectMode = false;
      selectedIds.clear();
      document.getElementById('selectToggleBtn').classList.remove('active');
      document.getElementById('selectToggleBtn').textContent = '☑️ Select';
      document.getElementById('bulkActionBar').style.display = 'none';
      document.getElementById('mediaGrid').classList.remove('select-mode-active');
      document.querySelectorAll('.media-card').forEach(c => c.classList.remove('selected'));
      document.querySelectorAll('.card-checkbox input').forEach(cb => cb.checked = false);
    }

    function onCardCheck(event, messageId) {
      event.stopPropagation();
      const card = document.getElementById(`card-${messageId}`);
      if (event.target.checked) {
        selectedIds.add(messageId);
        card?.classList.add('selected');
      } else {
        selectedIds.delete(messageId);
        card?.classList.remove('selected');
      }
      updateBulkUI();
    }

    function toggleSelectAll() {
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const visible = allMedia.filter(item => {
        const titleMatch = (item.display_name || item.file_name || item.series_title || '').toLowerCase().includes(query);
        if (!titleMatch) return false;
        if (currentFilter === "all") return true;
        const itemCat = item.category || (item.is_series ? 'series' : 'movies');
        return itemCat === currentFilter;
      });

      if (selectedIds.size === visible.length && visible.length > 0) {
        selectedIds.clear();
      } else {
        visible.forEach(item => selectedIds.add(item.message_id));
      }
      renderMedia();
      updateBulkUI();
    }

    function updateBulkUI() {
      const count = selectedIds.size;
      const countBadge = document.getElementById('selectedCountBadge');
      const deleteBtn = document.getElementById('bulkDeleteBtn');
      const bulkCatBtn = document.getElementById('bulkCatBtn');
      const selectAllLabel = document.getElementById('selectAllLabel');

      countBadge.textContent = `${count} Selected`;
      deleteBtn.disabled = count === 0;
      deleteBtn.textContent = count > 0 ? `🗑️ Delete (${count})` : '🗑️ Delete';
      if (bulkCatBtn) {
        bulkCatBtn.disabled = count === 0;
        bulkCatBtn.textContent = count > 0 ? `🏷️ Set Category (${count})` : '🏷️ Set Category';
      }

      const visibleCount = document.querySelectorAll('.media-card, .episode-row, .quality-version-row').length;
      selectAllLabel.textContent = (count === visibleCount && visibleCount > 0) ? 'None' : 'All';
    }

    async function executeBulkDelete() {
      const count = selectedIds.size;
      if (count === 0) return;
      if (!confirm(`Permanently delete ${count} selected files from your storage channel?`)) return;

      const idsToDelete = Array.from(selectedIds);
      try {
        const res = await fetch('/api/media/delete', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ message_ids: idsToDelete })
        });
        const result = await res.json();
        if (result.success) {
          showToast(`🗑️ ${count} items deleted!`);
          allMedia = allMedia.filter(m => !selectedIds.has(m.message_id));
          document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
          updateCategoryCounts();
          exitSelectMode();
          renderMedia();
        } else {
          alert("Error: " + (result.error || "Could not delete items."));
        }
      } catch (e) {
        alert("Failed to delete items: " + e.message);
      }
    }

    async function deleteMedia(messageId, optionalTitle) {
      const item = allMedia.find(m => m.message_id === messageId);
      const title = optionalTitle || (item && (item.display_name || item.file_name)) || 'this media';
      if (!confirm(`Delete "${title}" from your storage channel permanently?`)) return;
      try {
        const res = await fetch('/api/media/delete', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ message_ids: [messageId] })
        });
        const result = await res.json();
        if (result.success) {
          showToast("🗑️ Media deleted successfully!");
          allMedia = allMedia.filter(m => m.message_id !== messageId);
          document.getElementById('statsBadge').textContent = `${allMedia.length} Titles`;
          updateCategoryCounts();
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

    // Safe Canonical Key Generator (strips punctuation and apostrophes so keys never break HTML attributes)
    function getCanonicalSeriesKey(rawTitle) {
      if (!rawTitle) return '';
      let norm = String(rawTitle).toLowerCase().replace(/['’`]/g, '');
      norm = norm.replace(/&/g, ' and ');
      norm = norm.replace(/[^a-z0-9\s]/g, ' ');
      norm = norm.trim().replace(/\s+/g, '_');

      // Universal article stripper: "the_", "a_", "an_" so titles with/without articles unite automatically!
      norm = norm.replace(/^(the|a|an)_+/, '');

      // Strip leading and trailing End / Finale markers (e.g. "end_hotel_del_luna" -> "hotel_del_luna", "mr_queen_end" -> "mr_queen")
      norm = norm.replace(/^(the_)?(end|finale|final)_+/, '');
      norm = norm.replace(/_+(the_)?(end|finale|final)$/, '');

      // Proactively strip trailing part, season, volume, year, and release descriptors
      for (let i = 0; i < 3; i++) {
        norm = norm.replace(/_(season|s|part|pt|vol|volume|book|chapter|cdrama|kdrama|series|miniseries|tv|complete|full|hd|sd|hq|fhd|uhd|4k|1080p|720p|480p)(_\d+)*$/g, '');
        norm = norm.replace(/_\d{4}$/g, '');
      }

      // Known Franchise Aliases
      if (norm.startsWith('flex_x_cop') || norm.startsWith('flexxcop') || norm.includes('flex_x_cop')) return 'flex_x_cop';
      if (norm.startsWith('mr_bean') || norm.startsWith('mrbean') || (norm.includes('bean') && !norm.includes('lord_of_the_beans'))) return 'mr_bean';
      if (norm.startsWith('georgie_and_mandy')) return 'georgie_and_mandys_first_marriage';
      if (norm.includes('ruthless')) return 'tyler_perrys_ruthless';
      if (norm.includes('sista')) return 'tyler_perrys_sistas';
      if (norm.includes('oval')) return 'tyler_perrys_the_oval';
      if (norm.includes('zatima')) return 'tyler_perrys_zatima';
      if (norm.startsWith('wings') || (norm.includes('wing') && (norm.includes('innovat') || norm.includes('initiat')))) return 'the_wings_initiative';
      if (norm.startsWith('low_priest')) return 'the_low_priest';
      if (norm.startsWith('koleoso')) return 'koleoso';
      if (norm === 'black_ish' || norm === 'blackish' || norm === 'black') return 'black_ish';
      if (norm === 'grown_ish' || norm === 'grownish') return 'grown_ish';
      if (norm === 'mixed_ish' || norm === 'mixedish') return 'mixed_ish';
      if (norm === 'utd' || norm === 'under_the_dome') return 'under_the_dome';
      if (norm === 'tvd' || norm === 'vampire_diaries' || norm === 'the_vampire_diaries' || norm === 'the') return 'the_vampire_diaries';
      if (norm.startsWith('noobees')) return 'noobees';
      if (norm.includes('adthe_bible') || norm.includes('ad_the_bible') || norm.includes('a_d_the_bible')) return 'a_d_the_bible_continues';
      if (norm.includes('kaibutsu') || norm === 'my_little_monster') return 'my_little_monster';
      if (norm.includes('fixie') || norm === 'the_fixies') return 'the_fixies';
      if (norm.startsWith('veggietales')) return 'veggietales';
      if (norm.includes('anikulapo')) return 'anikulapo_rise_of_the_spectre';
      if (norm.startsWith('aiyetoro')) return 'aiyetoro_town';
      if (norm.startsWith('testament')) return 'the_testaments';
      if (norm.includes('aang') || norm.includes('airbender')) return 'avatar_aang_the_last_airbender';
      if (norm.includes('nero_the_assassin')) return 'nero_the_assassin';

      return norm;
    }

    function stripSeriesSuffix(key) {
      return key.replace(/_(part|pt|vol|volume|book|chapter|season|s|kdrama|cdrama|series|miniseries|complete|full)(_?\d+)*$/ig, '');
    }

    function canMergeKeys(keyA, keyB) {
      if (!keyA || !keyB) return false;
      if (keyA === keyB) return true;
      const baseA = stripSeriesSuffix(keyA);
      const baseB = stripSeriesSuffix(keyB);
      if (baseA.length >= 4 && baseA === baseB) return true;
      const [shorter, longer] = keyA.length < keyB.length ? [keyA, keyB] : [keyB, keyA];
      if (shorter.length >= 4 && longer.startsWith(shorter + '_')) {
        const diff = longer.slice(shorter.length + 1);
        if (/^(part|pt|vol|volume|book|chapter|season|s|kdrama|cdrama|series|miniseries|complete|full|\d{1,4})(_?\d+)*$/i.test(diff)) {
          return true;
        }
      }
      return false;
    }

    function getCleanFolderTitle(rawTitle) {
      if (!rawTitle) return '';
      const col = String(rawTitle).toLowerCase().replace(/[^a-z0-9]/g, '');
      if (col === 'blackish' || col === 'black') return 'Black-ish';
      if (col === 'grownish') return 'Grown-ish';
      if (col === 'mixedish') return 'Mixed-ish';
      if (col === 'utd' || col === 'underthedome') return 'Under the Dome';
      if (col === 'tvd' || col === 'thevampirediaries' || col === 'vampirediaries' || col === 'the') return 'The Vampire Diaries';
      if (col.startsWith('noobees')) return 'Noobees';
      if (col.includes('adthebible') || col.includes('adthebiblecontinues')) return 'A.D. The Bible Continues';
      if (col.includes('kaibutsu') || col === 'mylittlemonster') return 'My Little Monster';
      if (col.includes('fixie') || col === 'thefixies') return 'The Fixies';
      if (col.startsWith('veggietales')) return 'VeggieTales';
      if (col.includes('anikulapo')) return 'Aníkúlápó: Rise of the Spectre';
      if (col.startsWith('aiyetoro')) return 'Aiyetoro Town';
      if (col.startsWith('testament')) return 'The Testaments';
      if (col.includes('aang') || col.includes('airbender')) return 'Avatar Aang: The Last Airbender';
      if (col.includes('nerotheassassin')) return 'Néro The Assassin';

      let clean = String(rawTitle).trim();
      clean = clean.replace(/^(the\s+)?(end|finale|final)\s+/i, '');
      clean = clean.replace(/[\s\.\-_]+(the\s+)?(end|finale|final)$/i, '');
      for (let i = 0; i < 3; i++) {
        clean = clean.replace(/\(\s*(part|pt|vol|volume|book|chapter|season|s)\s*\d*\s*\)/gi, '');
        clean = clean.replace(/[\s\.\-_]+(part|pt|vol|volume|book|chapter|season|s)\s*\d*$/i, '');
        clean = clean.replace(/[\s\.\-_]+(kdrama|cdrama|k-drama|c-drama|series|tv|miniseries|mini-series|complete|full)$/i, '');
        clean = clean.replace(/[\s\.\-_]+\(?\d{4}\)?$/i, '');
        clean = clean.trim();
      }
      return clean || rawTitle;
    }

    // Track expanded folders and collapsed seasons
    const expandedFolders = new Set();
    const collapsedSeasons = new Set();
    window.seasonDataMap = {};

    function toggleFolder(key) {
      if (expandedFolders.has(key)) {
        expandedFolders.delete(key);
      } else {
        expandedFolders.add(key);
      }
      renderMedia();
    }

    function isFolderExpanded(groupKey) {
      return expandedFolders.has(groupKey);
    }

    function toggleSeason(event, seasonKey) {
      if (event) event.stopPropagation();
      if (collapsedSeasons.has(seasonKey)) {
        collapsedSeasons.delete(seasonKey);
      } else {
        collapsedSeasons.add(seasonKey);
      }
      renderMedia();
    }

    function isSeasonExpanded(seasonKey) {
      return !collapsedSeasons.has(seasonKey);
    }

    function copyAllSeasonLinks(event, seasonKey, seasonNum) {
      if (event) event.stopPropagation();
      const eps = (window.seasonDataMap && window.seasonDataMap[seasonKey]) || [];
      if (!eps || eps.length === 0) return;
      const text = eps.map(e => `• Ep ${e.episode || 1}: ${e.stream_url}`).join('\n');
      copyToClipboard(text);
      showToast(`📋 Copied all ${eps.length} links for Season ${seasonNum}!`);
    }

    // FilmHouse Category Definitions (Hollywood Movies & Western Series start first as requested)
    const CATEGORIES = [
      { id: 'movies', name: 'Hollywood & Global Movies', icon: '🎬', tag: 'Hollywood' },
      { id: 'series', name: 'Western TV Series', icon: '📺', tag: 'Series' },
      { id: 'anime', name: 'Anime', icon: '⚔️', tag: 'Anime' },
      { id: 'kdrama', name: 'K-Drama & Asian Drama', icon: '🌸', tag: 'K-Drama' },
      { id: 'african', name: 'African Cinema & Series', icon: '🌍', tag: 'African' },
      { id: 'bollywood', name: 'Bollywood & Indian Cinema', icon: '👳', tag: 'Bollywood' },
      { id: 'cartoons', name: 'Cartoons & Animation', icon: '🎨', tag: 'Cartoons' },
    ];

    function getCategoryObj(catId) {
      return CATEGORIES.find(c => c.id === catId) || CATEGORIES[0];
    }

    window.auditData = null;

    async function fetchAuditData() {
      try {
        const res = await fetch(`${API_BASE}/api/audit`, { headers: getAuthHeaders() });
        if (res.ok) {
          const d = await res.json();
          if (d.success && d.audit) {
            window.auditData = d.audit;
            updateCategoryCounts();
            if (currentFilter === 'incomplete' || currentFilter === 'single_ep') {
              renderMedia();
            }
          }
        }
      } catch (e) {
        console.warn("Audit fetch notice:", e);
      }
    }

    async function syncAuditTMDB(e) {
      if (e) e.stopPropagation();
      const btn = document.getElementById('syncTmdbBtn');
      if (btn) {
        btn.textContent = '⏳ Syncing...';
        btn.disabled = true;
      }
      try {
        const res = await fetch(`${API_BASE}/api/audit/sync`, {
          method: 'POST',
          headers: getAuthHeaders()
        });
        if (res.ok) {
          showToast("🚀 TMDB Background Audit Started! Scanning series against TMDB.");
          setTimeout(fetchAuditData, 4000);
          setTimeout(fetchAuditData, 12000);
        } else {
          showToast("⚠️ Could not start audit sync.");
        }
      } catch (err) {
        showToast("⚠️ Network error starting audit.");
      } finally {
        if (btn) {
          btn.textContent = '🔄 Sync TMDB';
          btn.disabled = false;
        }
      }
    }

    function updateCategoryCounts() {
      const counts = { all: allMedia.length, movies: 0, series: 0, anime: 0, kdrama: 0, african: 0, bollywood: 0, cartoons: 0 };
      const seriesEpCounts = new Map();

      allMedia.forEach(m => {
        const cat = m.category || (m.is_series ? 'series' : 'movies');
        if (counts[cat] !== undefined) {
          counts[cat]++;
        } else {
          counts[m.is_series ? 'series' : 'movies']++;
        }

        if (m.is_series && m.series_title) {
          const k = getCanonicalSeriesKey(m.series_title);
          seriesEpCounts.set(k, (seriesEpCounts.get(k) || 0) + 1);
        }
      });

      for (const [key, val] of Object.entries(counts)) {
        const el = document.getElementById(`count-${key}`);
        if (el) el.textContent = val;
      }

      let auditIncompleteKeys = new Set();
      if (window.auditData && window.auditData.incomplete_series) {
        window.auditData.incomplete_series.forEach(s => auditIncompleteKeys.add(s.canonical_key));
      }

      let incompleteCount = 0;
      seriesEpCounts.forEach((c, k) => {
        if (auditIncompleteKeys.size > 0) {
          if (auditIncompleteKeys.has(k)) incompleteCount++;
        } else if (c === 1) {
          incompleteCount++;
        }
      });
      const incompEl = document.getElementById('count-incomplete') || document.getElementById('count-single_ep');
      if (incompEl) incompEl.textContent = incompleteCount;
    }

    const collapsedSections = new Set();
    function toggleSectionCollapse(catId) {
      if (collapsedSections.has(catId)) {
        collapsedSections.delete(catId);
      } else {
        collapsedSections.add(catId);
      }
      renderMedia();
    }

    let currentCategoryTargetMid = null;
    let isBulkCategoryTarget = false;

    function openCategoryModal(event, messageId) {
      if (event) event.stopPropagation();
      currentCategoryTargetMid = messageId;
      isBulkCategoryTarget = false;
      document.getElementById('catModalTitle').textContent = 'Change Category';
      document.getElementById('catModalDesc').textContent = 'Select a new category for this media:';
      document.getElementById('categoryModal').style.display = 'flex';
    }

    function openBulkCategoryModal() {
      if (selectedIds.size === 0) return;
      currentCategoryTargetMid = null;
      isBulkCategoryTarget = true;
      document.getElementById('catModalTitle').textContent = 'Change Category (Bulk)';
      document.getElementById('catModalDesc').textContent = `Assign category for all ${selectedIds.size} selected items:`;
      document.getElementById('categoryModal').style.display = 'flex';
    }

    function closeCategoryModal() {
      document.getElementById('categoryModal').style.display = 'none';
      currentCategoryTargetMid = null;
      isBulkCategoryTarget = false;
    }

    async function applyCategoryChange(category) {
      const mids = isBulkCategoryTarget ? Array.from(selectedIds) : (currentCategoryTargetMid ? [currentCategoryTargetMid] : []);
      if (mids.length === 0) {
        closeCategoryModal();
        return;
      }

      closeCategoryModal();
      showToast("⏳ Updating category...");

      try {
        const res = await fetch('/api/media/category', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ message_ids: mids, category: category })
        });
        const result = await res.json();
        if (result.success) {
          showToast(`🏷️ Updated to ${getCategoryObj(category).name}!`);
          allMedia.forEach(m => {
            if (mids.includes(m.message_id)) {
              m.category = category;
            }
          });
          updateCategoryCounts();
          renderMedia();
          if (isBulkCategoryTarget) {
            exitSelectMode();
          }
        } else {
          alert("Error: " + (result.error || "Could not update category."));
        }
      } catch (e) {
        alert("Failed to update category.");
      }
    }

    function openEditModal(event, messageId) {
      if (event) event.stopPropagation();
      const item = allMedia.find(m => m.message_id === messageId);
      if (!item) return;

      document.getElementById('editMid').value = messageId;
      document.getElementById('editTitle').value = item.series_title || item.display_name || item.file_name || '';
      document.getElementById('editIsSeries').value = item.is_series ? "true" : "false";
      document.getElementById('editSeason').value = item.season || 1;
      document.getElementById('editEpisode').value = item.episode || 1;
      document.getElementById('editCategory').value = item.category || (item.is_series ? 'series' : 'movies');

      toggleEditSeriesFields();
      document.getElementById('editModal').style.display = 'flex';
    }

    function toggleEditSeriesFields() {
      const isSeries = document.getElementById('editIsSeries').value === "true";
      document.getElementById('editSeriesFields').style.display = isSeries ? 'flex' : 'none';
      if (!isSeries && document.getElementById('editCategory').value === 'series') {
        document.getElementById('editCategory').value = 'movies';
      }
    }

    function closeEditModal() {
      document.getElementById('editModal').style.display = 'none';
    }

    async function submitEditMedia() {
      const mid = parseInt(document.getElementById('editMid').value);
      const title = document.getElementById('editTitle').value.trim();
      const isSeries = document.getElementById('editIsSeries').value === "true";
      const season = parseInt(document.getElementById('editSeason').value) || 1;
      const episode = parseInt(document.getElementById('editEpisode').value) || 1;
      const category = document.getElementById('editCategory').value;

      if (!mid || !title) {
        alert("Please enter a valid title.");
        return;
      }

      closeEditModal();
      showToast("⏳ Saving changes...");

      try {
        const res = await fetch('/api/media/edit', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            message_id: mid,
            title: title,
            is_series: isSeries,
            season: isSeries ? season : null,
            episode: isSeries ? episode : null,
            category: category
          })
        });

        const data = await res.json();
        if (data.success) {
          showToast("✨ Media updated successfully!");
          await loadMedia();
        } else {
          alert("Error updating media: " + (data.error || "Unknown error"));
        }
      } catch (e) {
        alert("Failed to update media: " + e.message);
      }
    }

    const sectionPageLimits = {};
    function loadMoreSection(catId) {
      sectionPageLimits[catId] = (sectionPageLimits[catId] || 35) + 35;
      renderMedia();
    }

    function renderItemListHtml(items, query, catId = '') {
      // 1. Group series using smart canonical keys with O(1) Map indexing
      const seriesGroupMap = new Map();
      const seriesGroupList = [];
      const standaloneItems = [];

      items.forEach(item => {
        if (item.is_series && item.series_title) {
          const rawTitle = item.series_title;
          const normKey = getCanonicalSeriesKey(rawTitle);
          if (!normKey) return;

          let matchGroup = seriesGroupMap.get(normKey);
          if (!matchGroup) {
            const baseKey = stripSeriesSuffix(normKey);
            matchGroup = seriesGroupMap.get(baseKey);
          }

          if (!matchGroup) {
            matchGroup = {
              canonicalKey: normKey,
              title: getCleanFolderTitle(rawTitle),
              category: item.category || (item.is_series ? 'series' : 'movies'),
              firstMid: item.message_id,
              seasons: {},
              allEpisodes: [],
              quality: item.quality || 'HD',
            };
            seriesGroupMap.set(normKey, matchGroup);
            const baseKey = stripSeriesSuffix(normKey);
            if (baseKey && baseKey !== normKey) {
              seriesGroupMap.set(baseKey, matchGroup);
            }
            seriesGroupList.push(matchGroup);
          } else {
            const candidate = getCleanFolderTitle(rawTitle);
            const hasThe = candidate.toLowerCase().startsWith('the ') && !matchGroup.title.toLowerCase().startsWith('the ');
            if (hasThe || (!matchGroup.title.toLowerCase().startsWith('the ') && candidate.length < matchGroup.title.length && candidate.length >= 4)) {
              matchGroup.title = candidate;
            }
          }

          const sNum = item.season || 1;
          if (!matchGroup.seasons[sNum]) {
            matchGroup.seasons[sNum] = [];
          }
          if (!matchGroup.seasons[sNum].some(ep => ep.message_id === item.message_id)) {
            matchGroup.seasons[sNum].push(item);
            matchGroup.allEpisodes.push(item);
          }
        } else {
          standaloneItems.push(item);
        }
      });

      // 2. Render Movies (with Smart Multi-Quality Grouping)
      const movieGroups = {};
      standaloneItems.forEach(item => {
        const cleanTitle = (item.display_name || item.file_name || '')
          .replace(/\[\s*(1080p|720p|480p|2160p|4k|uhd|bluray|webrip|web-dl|hdrip|hd|cam)\s*\]/gi, '')
          .replace(/\b(1080p|720p|480p|2160p|4k|uhd|bluray|webrip|web-dl|hdrip|hd|cam|6ch|x264|x265|hevc)\b/gi, '')
          .replace(/\s+/g, ' ')
          .trim()
          .toLowerCase();

        const groupKey = cleanTitle || (item.display_name || item.file_name).toLowerCase();
        if (!movieGroups[groupKey]) {
          movieGroups[groupKey] = {
            title: item.display_name || item.file_name,
            category: item.category || 'movies',
            items: []
          };
        }
        movieGroups[groupKey].items.push(item);
      });

      const sortedSeries = seriesGroupList.sort((a, b) => a.title.localeCompare(b.title));
      const movieGroupList = Object.values(movieGroups);
      const totalUnits = sortedSeries.length + movieGroupList.length;
      const maxDisplay = (!query && catId) ? (sectionPageLimits[catId] || 35) : 999999;

      let subHtml = '';
      let renderedCount = 0;

      // Render Series Folders up to display limit
      for (const group of sortedSeries) {
        if (renderedCount >= maxDisplay) break;
        renderedCount++;

        const seasonKeys = Object.keys(group.seasons).map(Number).sort((a, b) => a - b);
        const isExpanded = isFolderExpanded(group.canonicalKey);
        const totalEpCount = group.allEpisodes.length;
        const catObj = getCategoryObj(group.category);

        subHtml += `
        <div class="series-folder-card">
          <div class="folder-header" onclick="toggleFolder('${group.canonicalKey}')">
            <div class="folder-title-box">
              <div class="folder-icon">📺</div>
              <div class="folder-info">
                <div class="folder-name" title="${escapeHtml(group.title)}">${escapeHtml(group.title)}</div>
                <div class="folder-meta">
                  <span>${seasonKeys.length === 1 ? `Season ${seasonKeys[0]}` : `${seasonKeys.length} Seasons (S${seasonKeys[0]}–S${seasonKeys[seasonKeys.length - 1]})`}</span> • 
                  <span>${totalEpCount} Episode${totalEpCount > 1 ? 's' : ''}</span>
                </div>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="badge-category" onclick="openCategoryModal(event, ${group.firstMid})" title="Change Category">${catObj.icon} ${catObj.tag} ▾</span>
              <span class="badge-quality">${escapeHtml(group.quality)}</span>
              <div class="folder-toggle-btn ${isExpanded ? 'expanded' : ''}">▼</div>
            </div>
          </div>

          ${isExpanded ? `
            <div class="season-subfolders-container">
              ${seasonKeys.map(sNum => {
                const seasonKey = `${group.canonicalKey}__s${sNum}`;
                const isSeasonOpen = isSeasonExpanded(seasonKey);
                const seasonEpisodes = (group.seasons[sNum] || []).sort((a, b) => (a.episode || 0) - (b.episode || 0));
                window.seasonDataMap[seasonKey] = seasonEpisodes;

                return `
                <div class="season-subfolder-box">
                  <div class="season-subfolder-header" onclick="toggleSeason(event, '${seasonKey}')">
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span style="font-size:1.1rem;">📂</span>
                      <span class="season-subfolder-title">Season ${sNum}</span>
                      <span class="season-badge-count">${seasonEpisodes.length} Episodes</span>
                    </div>
                    <div class="folder-toggle-btn ${isSeasonOpen ? 'expanded' : ''}" style="width:28px; height:28px; font-size:0.75rem;">▼</div>
                  </div>

                  ${isSeasonOpen ? `
                    <div class="episodes-wrapper" style="padding: 10px;">
                      ${seasonEpisodes.map(ep => {
                        const isChecked = selectedIds.has(ep.message_id);
                        const epSub = ep.episode_title ? ` — ${ep.episode_title}` : '';
                        return `
                        <div id="card-${ep.message_id}" class="episode-row ${isChecked ? 'selected' : ''}">
                          <div class="episode-row-header">
                            <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0;">
                              <div class="card-checkbox">
                                <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="onCardCheck(event, ${ep.message_id})">
                              </div>
                              <span class="episode-num-badge">Ep ${ep.episode || 1}</span>
                              <span class="episode-title-text" title="${escapeHtml(ep.file_name)}">${escapeHtml(epSub || ep.file_name)}</span>
                            </div>
                            <span style="font-size:0.7rem; color:#94a3b8;">${escapeHtml(ep.file_size_str || '')}</span>
                          </div>
                          <div class="card-actions" style="margin-top:2px;">
                            <div class="action-row">
                              <a href="${ep.watch_url}" onclick="openWithAd(event, '${ep.watch_url}')" class="btn btn-watch" style="min-height:32px; font-size:0.75rem;">▶ Play</a>
                              <a href="${ep.blogger_url}" onclick="openWithAd(event, '${ep.blogger_url}')" class="btn btn-blogger" style="min-height:32px; font-size:0.75rem;">🍿 Player</a>
                            </div>
                            <div class="action-row">
                              <button onclick="copyToClipboard('${ep.stream_url}')" class="btn btn-copy" style="min-height:32px; font-size:0.75rem;">📋 Link</button>
                              <button onclick="openEditModal(event, ${ep.message_id})" class="btn btn-edit" style="min-height:32px; width:38px;" title="Edit Info">✏️</button>
                              <button onclick="deleteMedia(${ep.message_id})" class="btn btn-del" style="min-height:32px; width:38px;" title="Delete">🗑️</button>
                            </div>
                          </div>
                        </div>
                        `;
                      }).join('')}
                    </div>

                    <div class="folder-admin-bar" style="margin: 0 10px 10px 10px;">
                      <button class="btn-folder-all" onclick="copyAllSeasonLinks(event, '${seasonKey}', ${sNum})">
                        📋 Copy All Season ${sNum} Links (${seasonEpisodes.length})
                      </button>
                    </div>
                  ` : ''}
                </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>
        `;
      }

      // Render Movies up to display limit
      for (const mGroup of movieGroupList) {
        if (renderedCount >= maxDisplay) break;
        renderedCount++;

        const catObj = getCategoryObj(mGroup.category);
        if (mGroup.items.length === 1) {
          const item = mGroup.items[0];
          const isChecked = selectedIds.has(item.message_id);
          subHtml += `
          <div id="card-${item.message_id}" class="media-card ${isChecked ? 'selected' : ''}">
            <div class="card-top">
              <div class="card-checkbox">
                <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="onCardCheck(event, ${item.message_id})">
              </div>
              <div class="card-title-wrap">
                <div class="card-title">🎬 ${escapeHtml(item.display_name)}</div>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="badge-category" onclick="openCategoryModal(event, ${item.message_id})" title="Change Category">${catObj.icon} ${catObj.tag} ▾</span>
                <span class="badge-quality">${escapeHtml(item.quality || 'HD')}</span>
              </div>
            </div>
            <div class="card-meta">
              <div class="file-badge">📁 ${escapeHtml(item.file_name)}</div>
              ${item.file_size_str ? `<span class="size-badge">📦 ${escapeHtml(item.file_size_str)}</span>` : ''}
            </div>
            <div class="card-actions">
              <div class="action-row">
                <a href="${item.watch_url}" onclick="openWithAd(event, '${item.watch_url}')" class="btn btn-watch">▶ Play Stream</a>
                <a href="${item.blogger_url}" onclick="openWithAd(event, '${item.blogger_url}')" class="btn btn-blogger">🍿 Player</a>
              </div>
              <div class="action-row">
                <button onclick="copyToClipboard('${item.stream_url}')" class="btn btn-copy">📋 Copy Stream Link</button>
                <button onclick="openEditModal(event, ${item.message_id})" class="btn btn-edit" title="Edit Info">✏️</button>
                <button onclick="deleteMedia(${item.message_id})" class="btn btn-del" title="Delete from Storage">🗑️</button>
              </div>
            </div>
          </div>
          `;
        } else {
          // Multi-Quality Grouped Movie Card
          const qualityTags = mGroup.items.map(it => it.quality || 'HD');
          subHtml += `
          <div class="multi-quality-card">
            <div class="card-top">
              <div class="card-title-wrap">
                <div class="card-title" style="font-size:1.05rem;">🎬 ${escapeHtml(mGroup.title)}</div>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="badge-category" onclick="openCategoryModal(event, ${mGroup.items[0]?.message_id})" title="Change Category">${catObj.icon} ${catObj.tag} ▾</span>
                <span class="multi-quality-badge">✨ ${mGroup.items.length} Qualities</span>
              </div>
            </div>
            <div class="card-meta" style="margin-top: -4px;">
              <span style="font-size:0.75rem; color:#94a3b8;">Versions: ${escapeHtml(qualityTags.join(' • '))}</span>
            </div>
            <div class="quality-versions-list">
              ${mGroup.items.map(v => {
                const isChecked = selectedIds.has(v.message_id);
                return `
                <div id="card-${v.message_id}" class="quality-version-row ${isChecked ? 'selected' : ''}">
                  <div class="quality-version-info">
                    <div class="card-checkbox">
                      <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="onCardCheck(event, ${v.message_id})">
                    </div>
                    <span class="badge-quality">${escapeHtml(v.quality || 'HD')}</span>
                    ${v.file_size_str ? `<span class="size-badge">📦 ${escapeHtml(v.file_size_str)}</span>` : ''}
                    <span style="font-size:0.72rem; color:#94a3b8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">${escapeHtml(v.file_name)}</span>
                  </div>
                  <div class="quality-version-actions">
                    <a href="${v.watch_url}" onclick="openWithAd(event, '${v.watch_url}')" class="btn btn-watch" style="min-height:30px; font-size:0.75rem; padding:4px 8px;">▶ Play</a>
                    <a href="${v.blogger_url}" onclick="openWithAd(event, '${v.blogger_url}')" class="btn btn-blogger" style="min-height:30px; font-size:0.75rem; padding:4px 8px;">🍿 Player</a>
                    <button onclick="copyToClipboard('${v.stream_url}')" class="btn btn-copy" style="min-height:30px; font-size:0.75rem; padding:4px 8px;">📋 Link</button>
                    <button onclick="openEditModal(event, ${v.message_id})" class="btn btn-edit" style="min-height:30px; padding:4px 8px;" title="Edit Info">✏️</button>
                    <button onclick="deleteMedia(${v.message_id})" class="btn btn-del" style="min-height:30px; padding:4px 8px;" title="Delete">🗑️</button>
                  </div>
                </div>
                `;
              }).join('')}
            </div>
          </div>
          `;
        }
      }

      if (totalUnits > maxDisplay) {
        subHtml += `
        <div style="text-align:center; padding:18px 0; width:100%; display:flex; justify-content:center;">
          <button onclick="loadMoreSection('${catId}')" class="btn btn-watch" style="padding:10px 24px; font-size:0.85rem; border-radius:12px; cursor:pointer;">
            ⬇️ Load More (${totalUnits - maxDisplay} remaining)
          </button>
        </div>
        `;
      }

      return subHtml;
    }

    function renderMedia() {
      const grid = document.getElementById('mediaGrid');
      const query = document.getElementById('searchInput').value.toLowerCase().trim();

      const filtered = allMedia.filter(item => {
        const titleMatch = (item.display_name || item.file_name || item.series_title || '').toLowerCase().includes(query);
        return titleMatch;
      });

      if (filtered.length === 0) {
        grid.innerHTML = '<div class="empty-state">No media found matching your filter.</div>';
        return;
      }

      let html = '';

      if (currentFilter === 'all') {
        // Render each category in the requested order: Movies, Series, Anime, K-Drama, African, Bollywood, Cartoons
        CATEGORIES.forEach(cat => {
          const catItems = filtered.filter(item => {
            const itemCat = item.category || (item.is_series ? 'series' : 'movies');
            return itemCat === cat.id;
          });

          if (catItems.length === 0 && query) {
            return;
          }

          const isCollapsed = collapsedSections.has(cat.id) && !query;

          html += `
          <div class="category-section" id="section-${cat.id}">
            <div class="category-section-banner" onclick="toggleSectionCollapse('${cat.id}')">
              <div class="category-banner-left">
                <span class="category-banner-icon">${cat.icon}</span>
                <span class="category-banner-title">${cat.name}</span>
                <span class="category-banner-count">${catItems.length} Titles</span>
              </div>
              <div class="category-banner-toggle ${isCollapsed ? 'collapsed' : ''}">▼</div>
            </div>
            <div class="category-section-content ${isCollapsed ? 'collapsed' : ''}">
              ${catItems.length > 0 ? renderItemListHtml(catItems, query, cat.id) : '<div class="empty-state" style="padding:15px; font-size:0.8rem; margin:0;">No items in this category.</div>'}
            </div>
          </div>
          `;
        });
      } else if (currentFilter === 'incomplete' || currentFilter === 'single_ep') {
        // Incomplete Series & TMDB Audit Filter
        const seriesCountMap = new Map();
        allMedia.forEach(item => {
          if (item.is_series && item.series_title) {
            const k = getCanonicalSeriesKey(item.series_title);
            seriesCountMap.set(k, (seriesCountMap.get(k) || 0) + 1);
          }
        });

        let auditIncompleteKeys = new Set();
        if (window.auditData && window.auditData.incomplete_series) {
          window.auditData.incomplete_series.forEach(s => auditIncompleteKeys.add(s.canonical_key));
        }

        const incompleteItems = filtered.filter(item => {
          if (!item.is_series || !item.series_title) return false;
          const k = getCanonicalSeriesKey(item.series_title);
          if (auditIncompleteKeys.size > 0) {
            return auditIncompleteKeys.has(k);
          }
          return seriesCountMap.get(k) === 1;
        });

        html += `
        <div class="category-section" id="section-incomplete">
          <div class="category-section-banner" style="cursor:default; border-color:rgba(239,68,68,0.35); display:flex; justify-content:space-between; align-items:center;">
            <div class="category-banner-left">
              <span class="category-banner-icon">⚠️</span>
              <span class="category-banner-title" style="color:#fca5a5;">Incomplete Series (TMDB &amp; Gap Audit)</span>
              <span class="category-banner-count" style="background:rgba(239,68,68,0.25); color:#fca5a5;">${incompleteItems.length} Titles</span>
            </div>
            <button onclick="syncAuditTMDB(event)" class="btn btn-watch" style="padding:6px 14px; font-size:0.75rem; border-radius:10px; margin-right:8px; cursor:pointer;" id="syncTmdbBtn">
              🔄 Sync TMDB
            </button>
          </div>
          <div class="category-section-content">
            ${incompleteItems.length > 0 ? renderItemListHtml(incompleteItems, query, 'incomplete') : '<div class="empty-state">🎉 Great news! All series in your library have complete seasons and no missing episodes!</div>'}
          </div>
        </div>
        `;
      } else {
        // Specific Category Filter
        const activeCat = CATEGORIES.find(c => c.id === currentFilter) || CATEGORIES[0];
        const catItems = filtered.filter(item => {
          const itemCat = item.category || (item.is_series ? 'series' : 'movies');
          return itemCat === activeCat.id;
        });

        html += `
        <div class="category-section" id="section-${activeCat.id}">
          <div class="category-section-banner" style="cursor:default;">
            <div class="category-banner-left">
              <span class="category-banner-icon">${activeCat.icon}</span>
              <span class="category-banner-title">${activeCat.name}</span>
              <span class="category-banner-count">${catItems.length} Titles</span>
            </div>
          </div>
          <div class="category-section-content">
            ${catItems.length > 0 ? renderItemListHtml(catItems, query, activeCat.id) : '<div class="empty-state">No media found in this category.</div>'}
          </div>
        </div>
        `;
      }

      grid.innerHTML = html;

      if (isSelectMode) {
        grid.classList.add('select-mode-active');
      }
    }

    let searchDebounceTimer = null;
    let prevSearchVal = '';
    function clearSearch() {
      const input = document.getElementById('searchInput');
      input.value = '';
      document.getElementById('searchClear').style.display = 'none';
      prevSearchVal = '';
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
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        const q = searchInput.value.toLowerCase().trim();
        if (q && q !== prevSearchVal) {
          allMedia.forEach(m => {
            if (m.is_series && m.series_title) {
              const titleMatch = (m.display_name || m.file_name || m.series_title || '').toLowerCase().includes(q);
              if (titleMatch) {
                const k = getCanonicalSeriesKey(m.series_title);
                if (k) expandedFolders.add(k);
              }
            }
          });
        }
        prevSearchVal = q;
        renderMedia();
      }, 250);
    });

    // Initial load
    loadMedia();
  </script>
</body>
</html>
"""
