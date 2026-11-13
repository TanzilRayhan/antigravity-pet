import os
import sys
import json
import time
import base64
import shutil
import urllib.parse
import re
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from PIL import Image

from config import load_config, save_config, SETTINGS_FILE, PETS_DIR, CONFIG_DIR, get_asset_path
from pet_loader import get_available_pets, PetDefinition
from downloader import PetCatalog
import pet_importer

catalog = PetCatalog(PETS_DIR)

# In-memory thumbnail cache to prevent repeated disk reads and file locking race conditions
_THUMBNAIL_CACHE = {}

def safe_slug(raw: str) -> str:
    """Sanitize slug to prevent path traversal and arbitrary directory escapes."""
    if not raw:
        return ""
    clean = re.sub(r'[^a-zA-Z0-9_\-]', '', str(raw))
    return os.path.basename(clean)

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Antigravity Pet Settings</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <style>
        :root {
            --bg-body: #09090b;
            --bg-card: #18181b;
            --bg-card-hover: #202024;
            --border: #27272a;
            --border-highlight: #38bdf8;
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --badge-bg: rgba(56, 189, 248, 0.12);
            --badge-border: rgba(56, 189, 248, 0.35);
            --font-stack: "Segoe UI Variable Display", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
        }

        @media (prefers-color-scheme: light) {
            :root {
                --bg-body: #f8fafc;
                --bg-card: #ffffff;
                --bg-card-hover: #f1f5f9;
                --border: #e2e8f0;
                --border-highlight: #0284c7;
                --text-main: #0f172a;
                --text-muted: #64748b;
                --accent: #0284c7;
                --accent-hover: #0369a1;
                --danger: #ef4444;
                --danger-hover: #b91c1c;
                --badge-bg: rgba(2, 132, 199, 0.08);
                --badge-border: rgba(2, 132, 199, 0.3);
            }
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: var(--font-stack);
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            user-select: none;
        }

        header {
            padding: 14px 28px;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand img {
            width: 32px;
            height: 32px;
            object-fit: contain;
        }

        .brand h1 {
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }

        .brand p {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 1px;
        }

        .tabs {
            display: flex;
            gap: 4px;
            background: var(--bg-body);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 600;
            padding: 7px 15px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.18s ease;
            display: inline-flex;
            align-items: center;
            gap: 7px;
        }

        .tab-btn svg {
            width: 15px;
            height: 15px;
            stroke-width: 2;
        }

        .tab-btn:hover {
            color: var(--text-main);
        }

        .tab-btn.active {
            background: var(--bg-card);
            color: var(--accent);
            box-shadow: 0 1px 3px rgba(0,0,0,0.25);
        }

        main {
            flex: 1;
            padding: 24px 28px;
            max-width: 1240px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
            animation: fadeIn 0.18s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .grid-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            gap: 16px;
        }

        .grid-header h2 {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }

        .search-box {
            position: relative;
            flex: 1;
            max-width: 380px;
        }

        .search-box input {
            width: 100%;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 9px 14px 9px 36px;
            color: var(--text-main);
            font-size: 13px;
            outline: none;
            transition: border 0.18s;
        }

        .search-box input:focus {
            border-color: var(--border-highlight);
        }

        .search-icon {
            position: absolute;
            left: 11px;
            top: 50%;
            transform: translateY(-50%);
            width: 15px;
            height: 15px;
            color: var(--text-muted);
            pointer-events: none;
        }

        .category-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 18px;
        }

        .category-chip {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 9999px;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .category-chip:hover {
            border-color: var(--border-highlight);
            color: var(--text-main);
        }

        .category-chip.active {
            background: var(--badge-bg);
            border-color: var(--border-highlight);
            color: var(--accent);
        }

        .pets-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 16px;
        }

        .pet-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            position: relative;
            transition: all 0.18s ease;
        }

        .pet-card:hover {
            border-color: var(--border-highlight);
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.18);
        }

        .pet-card.active-pet {
            border-color: var(--border-highlight);
            background: linear-gradient(180deg, var(--bg-card) 0%, var(--badge-bg) 100%);
        }

        .badge-active {
            position: absolute;
            top: 10px;
            right: 10px;
            background: var(--badge-bg);
            color: var(--accent);
            border: 1px solid var(--badge-border);
            font-size: 10px;
            font-weight: 700;
            padding: 3px 9px;
            border-radius: 9999px;
            letter-spacing: 0.4px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .badge-active svg {
            width: 7px;
            height: 7px;
            fill: currentColor;
        }

        .pet-preview {
            width: 110px;
            height: 110px;
            margin: 8px 0 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            background: rgba(0,0,0,0.12);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 10px;
            overflow: hidden;
        }

        .pet-preview img {
            max-width: 100%;
            max-height: 100%;
            image-rendering: pixelated;
            object-fit: contain;
            transition: transform 0.2s ease;
        }

        .pet-card:hover .pet-preview img {
            transform: scale(1.08);
        }

        .pet-sprite {
            width: 92px;
            height: 100px;
            background-repeat: no-repeat;
            background-position-x: 0%;
            background-position-y: 0%;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            animation: sprite-pet-play-6 1.15s steps(1) infinite;
            contain: paint;
            will-change: background-position;
            transition: transform 0.2s ease;
        }

        .pet-card:hover .pet-sprite {
            transform: scale(1.1);
        }

        @keyframes sprite-pet-play-6 {
            0%, 16.665% { background-position-x: 0%; }
            16.666%, 33.332% { background-position-x: 14.2857%; }
            33.333%, 49.999% { background-position-x: 28.5714%; }
            50%, 66.665% { background-position-x: 42.8571%; }
            66.666%, 83.332% { background-position-x: 57.1429%; }
            83.333%, 100% { background-position-x: 71.4286%; }
        }

        .pet-info {
            width: 100%;
            margin-bottom: 12px;
        }

        .pet-info h3 {
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 3px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .pet-info p {
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.4;
            height: 34px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }

        .card-actions {
            display: flex;
            gap: 8px;
            width: 100%;
            margin-top: auto;
        }

        .btn {
            background: var(--accent);
            color: #000;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            transition: all 0.18s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .btn svg {
            width: 13px;
            height: 13px;
            stroke-width: 2.2;
        }

        .btn:hover {
            background: var(--accent-hover);
            color: #fff;
        }

        .btn-outline {
            background: transparent;
            color: var(--text-main);
            border: 1px solid var(--border);
        }

        .btn-outline:hover:not(:disabled) {
            border-color: var(--border-highlight);
            color: var(--accent);
            background: var(--badge-bg);
        }

        .btn-outline:disabled {
            opacity: 0.65;
            cursor: default;
        }

        .btn:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .spinner {
            display: inline-block;
            width: 13px;
            height: 13px;
            border: 2px solid rgba(255, 255, 255, 0.35);
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.75s linear infinite;
            margin-right: 2px;
        }

        .btn-danger {
            background: transparent;
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.35);
            width: auto;
            padding: 8px 10px;
        }

        .btn-danger svg {
            width: 14px;
            height: 14px;
        }

        .btn-danger:hover {
            background: var(--danger);
            color: #fff;
            border-color: var(--danger);
        }

        .btn-icon {
            width: auto;
            padding: 8px 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .btn-icon svg {
            width: 14px;
            height: 14px;
        }

        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.68);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            animation: fadeIn 0.15s ease;
        }

        .modal-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 90%;
            max-width: 440px;
            padding: 22px 24px;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.55);
            animation: popIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes popIn {
            from { transform: scale(0.95); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }

        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
        }

        .modal-header h3 {
            font-size: 16px;
            font-weight: 700;
            margin: 0;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 22px;
            line-height: 1;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .modal-close:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.08);
        }

        .settings-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            max-width: 640px;
            margin: 0 auto;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .form-group p {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .range-container {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        input[type="range"] {
            flex: 1;
            accent-color: var(--accent);
            cursor: pointer;
        }

        .switch-group {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }

        .switch-group:last-child {
            border-bottom: none;
        }

        .shortcut-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            gap: 16px;
        }
        .shortcut-row:last-child {
            border-bottom: none;
        }
        .shortcut-info {
            flex: 1;
        }
        .shortcut-name {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 2px;
        }
        .shortcut-desc {
            font-size: 11.5px;
            color: var(--text-muted);
        }
        .shortcut-input-wrap {
            display: flex;
            align-items: center;
            position: relative;
            min-width: 170px;
        }
        .shortcut-input {
            width: 100%;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--accent);
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12.5px;
            font-weight: 600;
            padding: 8px 30px 8px 12px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s ease;
        }
        .shortcut-input:hover {
            border-color: rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.45);
        }
        .shortcut-input.recording {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.25);
            background: rgba(56, 189, 248, 0.08);
            color: #fff;
        }
        .shortcut-input::placeholder {
            color: var(--text-muted);
            font-weight: 400;
            font-family: inherit;
            font-size: 11.5px;
        }
        .shortcut-clear-btn {
            position: absolute;
            right: 8px;
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 16px;
            line-height: 1;
            padding: 2px 4px;
            border-radius: 4px;
            transition: color 0.15s ease;
        }
        .shortcut-clear-btn:hover {
            color: var(--danger);
        }

        .creator-container {
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
        }

        .drop-zone {
            border: 2px dashed var(--border);
            border-radius: 12px;
            padding: 32px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: var(--bg-card);
        }

        .drop-zone:hover, .drop-zone.dragover {
            border-color: var(--border-highlight);
            background: var(--badge-bg);
        }

        .drop-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
            color: var(--text-muted);
        }

        .drop-icon svg {
            width: 40px;
            height: 40px;
            stroke-width: 1.5;
        }

        .creator-preview-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }

        .creator-img-box {
            width: 160px;
            height: 170px;
            background: rgba(0,0,0,0.12);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin: 16px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }

        .creator-img-box img {
            max-width: 100%;
            max-height: 100%;
            image-rendering: pixelated;
        }

        .form-input {
            width: 100%;
            background: var(--bg-body);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 9px 12px;
            color: var(--text-main);
            font-size: 13px;
            outline: none;
            margin-top: 6px;
        }

        .form-input:focus {
            border-color: var(--border-highlight);
        }

        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--bg-card);
            border: 1px solid var(--border-highlight);
            color: var(--text-main);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            display: none;
            z-index: 1000;
            font-size: 13px;
            font-weight: 600;
            align-items: center;
            gap: 8px;
        }

        .toast.error {
            border-color: rgba(239, 68, 68, 0.6);
            color: #fca5a5;
        }

        .toast.show {
            display: inline-flex;
            animation: fadeIn 0.18s ease;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <img src="/logo.png" alt="Antigravity">
            <div>
                <h1>Antigravity Pet</h1>
                <p>Desktop Companion & Pet Gallery</p>
            </div>
        </div>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('installed')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                <span>My Pets</span>
            </button>
            <button class="tab-btn" onclick="switchTab('gallery')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
                <span>Pet Gallery</span>
            </button>
            <button class="tab-btn" onclick="switchTab('creator')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                <span>Custom Pet</span>
            </button>
            <button class="tab-btn" onclick="switchTab('settings')">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                <span>Settings</span>
            </button>
        </div>
    </header>

    <main>
        <!-- Tab 1: Installed Pets -->
        <div id="tab-installed" class="tab-pane active">
            <div class="grid-header">
                <div>
                    <h2>Installed Pets</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-top:2px;">Select an active companion to roam your desktop or sync with Antigravity</p>
                </div>
            </div>
            <div class="pets-grid" id="installed-grid"></div>
        </div>

        <!-- Tab 2: Pet Gallery -->
        <div id="tab-gallery" class="tab-pane">
            <div class="grid-header">
                <div>
                    <h2>Pet Gallery</h2>
                    <p id="gallery-subtitle" style="color:var(--text-muted); font-size:13px; margin-top:2px;">Showing 0 of 0 community pets</p>
                    <div style="font-size:12px; color:var(--text-muted); margin-top:4px; display:flex; align-items:center; gap:5px;">
                        <span>Source:</span>
                        <a href="https://codexpets.net/" target="_blank" style="color:var(--accent); text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:3px;">
                            CodexPets.net
                            <svg style="width:11px; height:11px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </a>
                    </div>
                </div>
                <div class="search-box">
                    <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <input type="text" id="catalog-search" placeholder="Search pets (e.g. Digimon, Cat, Robot, Game)..." oninput="filterCatalog()">
                </div>
            </div>
            <div class="category-chips" id="category-chips"></div>
            <div class="pets-grid" id="catalog-grid"></div>
            <div id="gallery-load-more" style="text-align:center; margin:24px 0; display:none;">
                <button class="btn btn-outline" style="width:auto; padding:9px 24px;" onclick="loadMoreCatalogPets()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    Load More Pets
                </button>
            </div>
        </div>

        <!-- Tab 3: DIY Pet Maker & Customizer -->
        <div id="tab-creator" class="tab-pane">
            <div class="creator-container">
                <div class="settings-card" style="max-width:none; margin:0;">
                    <h2 style="margin-bottom:6px;">Create / Import a Pet</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-bottom:20px;">Upload an animated GIF, image, or drag & drop a downloaded Codex Pet .ZIP package.</p>
                    
                    <div class="drop-zone" id="drop-zone">
                        <div class="drop-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                        </div>
                        <h4 style="margin-bottom:4px;" id="drop-title">Drag & Drop Pet .ZIP or Image / GIF Here</h4>
                        <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Supports .zip (Codex pet packages), .gif (animated), .webp, .png, or .jpg</p>
                        <div style="display:inline-flex; gap:10px;">
                            <button type="button" class="btn btn-outline" style="width:auto;" onclick="event.stopPropagation(); document.getElementById('pet-file-input').click();">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                                Browse Image / GIF
                            </button>
                            <button type="button" class="btn btn-outline" style="width:auto;" onclick="event.stopPropagation(); document.getElementById('zip-file-input').click();">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                                Browse .ZIP
                            </button>
                        </div>
                        <input type="file" id="pet-file-input" accept=".webp,.png,.gif,.jpg,.jpeg" style="display:none;" onchange="handleImageSelected(event)">
                        <input type="file" id="zip-file-input" accept=".zip" style="display:none;" onchange="handleZipSelected(event)">
                    </div>

                    <div style="margin-top:20px;">
                        <div class="form-group">
                            <label>Character Display Name</label>
                            <input type="text" id="creator-name" class="form-input" placeholder="e.g. Cyber Pup, Pixel Dragon" oninput="updateCreatorPreview()">
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <input type="text" id="creator-desc" class="form-input" placeholder="A short description of your pet" oninput="updateCreatorPreview()">
                        </div>
                    </div>
                </div>

                <div class="creator-preview-card">
                    <h3 style="font-size:15px; font-weight:700;">Character Preview</h3>
                    <div class="creator-img-box">
                        <img id="creator-img-preview" src="" alt="Preview">
                    </div>
                    <h4 id="preview-title" style="margin-bottom:4px; font-size:14px;">My Custom Pet</h4>
                    <p id="preview-desc" style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">Ready to create & slice</p>
                    <button class="btn" onclick="saveCustomPet()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        Create & Install Pet
                    </button>
                </div>
            </div>
        </div>

        <!-- Tab 4: Settings -->
        <div id="tab-settings" class="tab-pane">
            <div class="settings-card">
                <h2 style="margin-bottom:6px;">Companion Settings</h2>
                <p style="color:var(--text-muted); font-size:13px; margin-bottom:20px;">Configure how your desktop pet behaves, scales, and syncs with Antigravity 2.0.</p>

                <div class="form-group">
                    <label>Pet Scale (Size)</label>
                    <div class="range-container">
                        <input type="range" id="setting-scale" min="40" max="150" step="5" oninput="updateScale(this.value)">
                        <span id="scale-val" style="font-weight:700; width:45px;">75%</span>
                    </div>
                    <p>Immediately scales mascot from compact (40%) to large (150%) on screen.</p>
                </div>

                <div class="form-group">
                    <label>Behavior Mode</label>
                    <select id="setting-behavior" class="form-input" onchange="updateBehavior(this.value)">
                        <option value="zero_g">Zero-G Float (Gentle vertical hover floating)</option>
                        <option value="static">Stationary (Locked position)</option>
                    </select>
                </div>

                <div class="switch-group">
                    <div>
                        <div style="font-weight:600; font-size:13px;">Antigravity Auto-Sync</div>
                        <p style="font-size:12px; color:var(--text-muted);">Only show pet when Antigravity 2.0 is running on Windows</p>
                    </div>
                    <input type="checkbox" id="setting-sync" style="width:18px; height:18px; accent-color:var(--accent);" onchange="updateSync(this.checked)">
                </div>

                <div class="switch-group">
                    <div>
                        <div style="font-weight:600; font-size:13px;">Start with Windows</div>
                        <p style="font-size:12px; color:var(--text-muted);">Automatically launch pet companion and global shortcut (Ctrl+Alt+P) on boot</p>
                    </div>
                    <input type="checkbox" id="setting-startup" style="width:18px; height:18px; accent-color:var(--accent);" onchange="updateStartup(this.checked)">
                </div>

                <div class="switch-group">
                    <div>
                        <div style="font-weight:600; font-size:13px;">Audio Chimes & Sound Effects</div>
                        <p style="font-size:12px; color:var(--text-muted);">Play audio chime when dragging, clicking dock icons, or waving</p>
                    </div>
                    <input type="checkbox" id="setting-sound" style="width:18px; height:18px; accent-color:var(--accent);" onchange="updateSound(this.checked)">
                </div>

                <div style="margin-top:24px; padding-top:20px; border-top:1px solid var(--border);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <h3 style="font-size:15px; font-weight:700; margin:0;">Keyboard Shortcuts</h3>
                        <button class="btn btn-secondary" onclick="resetShortcutsToDefault()" style="font-size:12px; padding:4px 10px; height:auto;">Reset Defaults</button>
                    </div>
                    <p style="color:var(--text-muted); font-size:12px; margin-bottom:16px;">Click any shortcut input and press your desired key combination, or click Clear to leave it blank.</p>

                    <!-- Shortcut 1: Run & Exit Pet -->
                    <div class="shortcut-row">
                        <div class="shortcut-info">
                            <div class="shortcut-name">Run & Exit Pet Companion</div>
                            <div class="shortcut-desc">Launch when closed; cleanly exit when pet is showing</div>
                        </div>
                        <div class="shortcut-input-wrap">
                            <input type="text" id="shortcut-toggle_pet" class="shortcut-input" readonly placeholder="Click to record..." onclick="startRecordingShortcut('toggle_pet')" onkeydown="handleShortcutKeydown(event, 'toggle_pet')">
                            <button class="shortcut-clear-btn" title="Clear shortcut" onclick="clearShortcut('toggle_pet')">&times;</button>
                        </div>
                    </div>

                    <!-- Shortcut 2: Hide & Show Mini -->
                    <div class="shortcut-row">
                        <div class="shortcut-info">
                            <div class="shortcut-name">Hide & Show Mini (Tray)</div>
                            <div class="shortcut-desc">Toggle pet visibility between screen and tray without exiting</div>
                        </div>
                        <div class="shortcut-input-wrap">
                            <input type="text" id="shortcut-toggle_visibility" class="shortcut-input" readonly placeholder="Click to record..." onclick="startRecordingShortcut('toggle_visibility')" onkeydown="handleShortcutKeydown(event, 'toggle_visibility')">
                            <button class="shortcut-clear-btn" title="Clear shortcut" onclick="clearShortcut('toggle_visibility')">&times;</button>
                        </div>
                    </div>

                    <!-- Shortcut 3: Switch Pet -->
                    <div class="shortcut-row">
                        <div class="shortcut-info">
                            <div class="shortcut-name">Switch Pet</div>
                            <div class="shortcut-desc">Cycle to the next installed companion mascot</div>
                        </div>
                        <div class="shortcut-input-wrap">
                            <input type="text" id="shortcut-switch_pet" class="shortcut-input" readonly placeholder="Click to record..." onclick="startRecordingShortcut('switch_pet')" onkeydown="handleShortcutKeydown(event, 'switch_pet')">
                            <button class="shortcut-clear-btn" title="Clear shortcut" onclick="clearShortcut('switch_pet')">&times;</button>
                        </div>
                    </div>

                    <!-- Shortcut 4: Switch Pet Behavior Mode -->
                    <div class="shortcut-row">
                        <div class="shortcut-info">
                            <div class="shortcut-name">Switch Behavior Mode</div>
                            <div class="shortcut-desc">Toggle between Zero-G Float (hover) and Stationary</div>
                        </div>
                        <div class="shortcut-input-wrap">
                            <input type="text" id="shortcut-toggle_behavior" class="shortcut-input" readonly placeholder="Click to record..." onclick="startRecordingShortcut('toggle_behavior')" onkeydown="handleShortcutKeydown(event, 'toggle_behavior')">
                            <button class="shortcut-clear-btn" title="Clear shortcut" onclick="clearShortcut('toggle_behavior')">&times;</button>
                        </div>
                    </div>

                    <!-- Shortcut 5: Open Settings Hub -->
                    <div class="shortcut-row">
                        <div class="shortcut-info">
                            <div class="shortcut-name">Open Settings Hub</div>
                            <div class="shortcut-desc">Open the Pet Settings and Gallery Hub in your browser</div>
                        </div>
                        <div class="shortcut-input-wrap">
                            <input type="text" id="shortcut-open_settings" class="shortcut-input" readonly placeholder="Click to record..." onclick="startRecordingShortcut('open_settings')" onkeydown="handleShortcutKeydown(event, 'open_settings')">
                            <button class="shortcut-clear-btn" title="Clear shortcut" onclick="clearShortcut('open_settings')">&times;</button>
                        </div>
                    </div>
                </div>

                <div style="margin-top:24px; padding-top:16px; border-top:1px solid var(--border);">
                    <div style="font-weight:600; font-size:13px; margin-bottom:4px;">Pet Gallery Attribution</div>
                    <p style="font-size:12px; color:var(--text-muted); line-height:1.5;">All community mascot characters and gallery sprites are hosted by and sourced from <a href="https://codexpets.net/" target="_blank" style="color:var(--accent); text-decoration:none; font-weight:600;">CodexPets.net</a>.</p>
                </div>
            </div>
        </div>
    </main>

    <!-- Edit Pet Modal -->
    <div id="edit-modal" class="modal-overlay" style="display:none;" onclick="if(event.target === this) closeEditPetModal()">
        <div class="modal-card">
            <div class="modal-header">
                <h3>Edit Pet Details</h3>
                <button class="modal-close" onclick="closeEditPetModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="edit-pet-slug">
                <div class="form-group" style="margin-bottom:16px;">
                    <label style="display:block; font-size:12px; font-weight:600; margin-bottom:6px; color:var(--text-main);">Pet Name</label>
                    <input type="text" id="edit-pet-name" class="form-input" style="width:100%; box-sizing:border-box;" placeholder="Enter pet name...">
                </div>
                <div class="form-group">
                    <label style="display:block; font-size:12px; font-weight:600; margin-bottom:6px; color:var(--text-main);">Subheading / Description</label>
                    <textarea id="edit-pet-desc" class="form-input" style="width:100%; height:80px; box-sizing:border-box; resize:vertical; font-family:inherit;" placeholder="Enter pet subheading or description..."></textarea>
                </div>
            </div>
            <div class="modal-footer" style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button class="btn btn-outline" style="width:auto; padding:8px 16px;" onclick="closeEditPetModal()">Cancel</button>
                <button class="btn" style="width:auto; padding:8px 20px;" onclick="saveEditPet()">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Delete Pet Confirmation Modal -->
    <div id="delete-modal" class="modal-overlay" style="display:none;" onclick="if(event.target === this) closeDeletePetModal()">
        <div class="modal-card">
            <div class="modal-header">
                <h3 style="color:#ef4444; display:flex; align-items:center; gap:8px;">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    Delete Pet Permanently
                </h3>
                <button class="modal-close" onclick="closeDeletePetModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="delete-pet-slug">
                <p style="font-size:14px; color:var(--text-main); margin-bottom:12px;">
                    Are you sure you want to permanently delete <strong id="delete-pet-name-display" style="color:var(--text-main);"></strong>?
                </p>
                <div style="background:rgba(239, 68, 68, 0.1); border:1px solid rgba(239, 68, 68, 0.25); border-radius:8px; padding:12px; font-size:12px; color:var(--text-muted); line-height:1.5;">
                    <strong style="color:#ef4444;">Warning:</strong> This will permanently remove the mascot from your device. You can reinstall it anytime from the <strong>Pet Gallery</strong>.
                </div>
            </div>
            <div class="modal-footer" style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button class="btn btn-outline" style="width:auto; padding:8px 16px;" onclick="closeDeletePetModal()">Cancel</button>
                <button class="btn btn-danger" id="confirm-delete-btn" style="width:auto; padding:8px 20px;" onclick="confirmDeletePet()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px; height:14px;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    Delete Permanently
                </button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">
        <svg id="toast-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span id="toast-text">Success</span>
    </div>

    <script>
        let currentTab = 'installed';
        let installedPets = [];
        let catalogPets = [];
        let activeCategory = 'All';
        let catalogRenderLimit = 48;
        let currentPetSlug = '';

        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab-btn').forEach((b, i) => {
                b.classList.toggle('active', ['installed', 'gallery', 'creator', 'settings'][i] === tabId);
            });
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');

            if (tabId === 'installed') loadInstalledPets();
            if (tabId === 'gallery') loadCatalog();
            if (tabId === 'settings') loadSettings();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            const icon = document.getElementById('toast-icon');
            document.getElementById('toast-text').innerText = msg;
            if (isError) {
                t.classList.add('error');
                if (icon) {
                    icon.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>';
                    icon.setAttribute('stroke', '#ef4444');
                }
            } else {
                t.classList.remove('error');
                if (icon) {
                    icon.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
                    icon.setAttribute('stroke', 'currentColor');
                }
            }
            t.classList.add('show');
            clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => {
                t.classList.remove('show');
                t.classList.remove('error');
            }, 3000);
        }

        async function loadInstalledPets() {
            try {
                const res = await fetch('/api/pets');
                const data = await res.json();
                installedPets = data.pets || [];
                currentPetSlug = data.current || '';
                renderInstalledGrid();
            } catch (e) {
                console.error(e);
            }
        }

        function renderInstalledGrid() {
            const grid = document.getElementById('installed-grid');
            grid.innerHTML = '';
            installedPets.forEach(p => {
                const isAct = p.slug === currentPetSlug;
                const isV2 = p.version === 2;
                const rows = isV2 ? 11 : 9;
                const sheetUrl = `/pet_spritesheet?slug=${encodeURIComponent(p.slug)}`;
                const card = document.createElement('div');
                card.className = `pet-card ${isAct ? 'active-pet' : ''}`;
                card.innerHTML = `
                    ${isAct ? `
                        <span class="badge-active">
                            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle></svg>
                            Active
                        </span>` : ''}
                    <div class="pet-preview">
                        <div class="pet-sprite" style="background-image: url('${sheetUrl}'); background-size: 800% ${rows * 100}%;"></div>
                    </div>
                    <div class="pet-info">
                        <h3>${escapeHtml(p.displayName)}</h3>
                        <p>${escapeHtml(p.description || 'Community companion for your desktop.')}</p>
                    </div>
                    <div class="card-actions">
                        ${isAct ? 
                            `<button class="btn btn-outline" style="flex:1;" disabled>
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                Active
                            </button>` : 
                            `<button class="btn" style="flex:1;" onclick="activatePet('${p.slug}')">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                Activate
                            </button>`
                        }
                        <button class="btn btn-outline btn-icon" title="Edit pet name & subheading" onclick="openEditPetModal('${p.slug}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                        </button>
                        <button class="btn btn-danger btn-icon" title="Delete pet permanently" onclick="openDeletePetModal('${p.slug}', '${escapeHtml(p.displayName)}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function openDeletePetModal(slug, displayName) {
            document.getElementById('delete-pet-slug').value = slug;
            document.getElementById('delete-pet-name-display').innerText = displayName || slug;
            const modal = document.getElementById('delete-modal');
            modal.style.display = 'flex';
        }

        function closeDeletePetModal() {
            document.getElementById('delete-modal').style.display = 'none';
        }

        async function confirmDeletePet() {
            const slug = document.getElementById('delete-pet-slug').value;
            const displayName = document.getElementById('delete-pet-name-display').innerText;
            if (!slug) return;

            const btn = document.getElementById('confirm-delete-btn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner"></span> Deleting...`;
            }

            try {
                const res = await fetch('/api/pets/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({slug})
                });
                const data = await res.json();
                closeDeletePetModal();
                if (data.success) {
                    showToast(`Permanently deleted ${displayName}`);
                    await loadInstalledPets();
                    filterCatalog();
                } else {
                    showToast('Failed to delete: ' + (data.error || 'Unknown error'), true);
                }
            } catch (e) {
                closeDeletePetModal();
                showToast('Delete error', true);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:14px; height:14px;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg> Delete Permanently`;
                }
            }
        }

        function openEditPetModal(slug) {
            const pet = installedPets.find(p => p.slug === slug);
            if (!pet) return;
            document.getElementById('edit-pet-slug').value = slug;
            document.getElementById('edit-pet-name').value = pet.displayName || '';
            document.getElementById('edit-pet-desc').value = pet.description || '';
            const modal = document.getElementById('edit-modal');
            modal.style.display = 'flex';
            setTimeout(() => document.getElementById('edit-pet-name').focus(), 50);
        }

        function closeEditPetModal() {
            document.getElementById('edit-modal').style.display = 'none';
        }

        async function saveEditPet() {
            const slug = document.getElementById('edit-pet-slug').value;
            const name = document.getElementById('edit-pet-name').value.trim();
            const desc = document.getElementById('edit-pet-desc').value.trim();
            if (!name) {
                showToast('Please enter a pet name', true);
                return;
            }

            try {
                const res = await fetch('/api/pets/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ slug, name, desc })
                });
                const data = await res.json();
                if (data.success) {
                    closeEditPetModal();
                    showToast('Pet details updated!');
                    await loadInstalledPets();
                } else {
                    showToast('Update failed: ' + (data.error || 'Unknown error'), true);
                }
            } catch (e) {
                showToast('Error updating pet details', true);
            }
        }

        async function activatePet(slug) {
            try {
                const res = await fetch('/api/pets/activate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({slug})
                });
                const data = await res.json();
                if (data.success) {
                    currentPetSlug = slug;
                    renderInstalledGrid();
                    showToast(`Switched active pet to ${slug}`);
                }
            } catch (e) {
                showToast('Failed to switch pet', true);
            }
        }

        async function loadCatalog() {
            try {
                const res = await fetch('/api/catalog');
                catalogPets = await res.json();
                renderCategoryChips();
                filterCatalog();
            } catch (e) {
                console.error(e);
            }
        }

        function renderCategoryChips() {
            const chipsBox = document.getElementById('category-chips');
            const cats = ['All'];
            catalogPets.forEach(p => {
                if (p.primary_category && !cats.includes(p.primary_category)) {
                    cats.push(p.primary_category);
                }
            });

            chipsBox.innerHTML = '';
            cats.slice(0, 10).forEach(cat => {
                const count = cat === 'All' ? catalogPets.length : catalogPets.filter(p => p.primary_category === cat).length;
                const btn = document.createElement('button');
                btn.className = `category-chip ${activeCategory === cat ? 'active' : ''}`;
                btn.innerText = `${cat} (${count})`;
                btn.onclick = () => {
                    activeCategory = cat;
                    catalogRenderLimit = 48;
                    renderCategoryChips();
                    filterCatalog();
                };
                chipsBox.appendChild(btn);
            });
        }

        function filterCatalog() {
            const q = document.getElementById('catalog-search').value.toLowerCase().trim();
            let filtered = catalogPets;

            if (activeCategory !== 'All') {
                filtered = filtered.filter(p => p.primary_category === activeCategory);
            }

            if (q) {
                filtered = filtered.filter(p => 
                    (p.name && p.name.toLowerCase().includes(q)) ||
                    (p.slug && p.slug.toLowerCase().includes(q)) ||
                    (p.description && p.description.toLowerCase().includes(q)) ||
                    (p.primary_category && p.primary_category.toLowerCase().includes(q))
                );
            }

            document.getElementById('gallery-subtitle').innerText = `Showing ${filtered.length} of ${catalogPets.length} community pets`;
            renderCatalogGrid(filtered);
        }

        const installingSlugs = new Set();

        function renderCatalogGrid(pets) {
            const grid = document.getElementById('catalog-grid');
            grid.innerHTML = '';
            const installedSlugs = new Set(installedPets.map(p => p.slug));

            const visible = pets.slice(0, catalogRenderLimit);
            visible.forEach(p => {
                const isInst = installedSlugs.has(p.slug);
                const isInstalling = installingSlugs.has(p.slug);
                const isV2 = p.spriteVersionNumber === 2;
                const rows = isV2 ? 11 : 9;
                const sheetUrl = `https://raw.githubusercontent.com/legeling/awesome-codex-pet/main/pets/${encodeURIComponent(p.slug)}/spritesheet.webp`;
                const card = document.createElement('div');
                card.className = 'pet-card';
                card.innerHTML = `
                    <div class="pet-preview">
                        <div class="pet-sprite" style="background-image: url('${sheetUrl}'); background-size: 800% ${rows * 100}%;"></div>
                    </div>
                    <div class="pet-info">
                        <h3>${escapeHtml(p.name)}</h3>
                        <p>${escapeHtml(p.description || p.primary_category || 'Community Codex Pet')}</p>
                    </div>
                    ${isInst ? 
                        `<button class="btn btn-outline" disabled>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Installed
                        </button>` : 
                        (isInstalling ?
                        `<button class="btn" id="install-btn-${p.slug}" disabled>
                            <span class="spinner"></span>
                            Installing...
                        </button>` :
                        `<button class="btn" id="install-btn-${p.slug}" onclick="installPet('${p.slug}', '${escapeHtml(p.name)}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                            Install
                        </button>`)
                    }
                `;
                grid.appendChild(card);
            });

            const loadMoreBtn = document.getElementById('gallery-load-more');
            if (pets.length > catalogRenderLimit) {
                loadMoreBtn.style.display = 'block';
            } else {
                loadMoreBtn.style.display = 'none';
            }
        }

        function loadMoreCatalogPets() {
            catalogRenderLimit += 48;
            filterCatalog();
        }

        async function installPet(slug, name) {
            if (installingSlugs.has(slug)) return;
            installingSlugs.add(slug);

            const displayName = name || slug;
            const btn = document.getElementById('install-btn-' + slug);
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span class="spinner"></span> Installing...`;
            }

            showToast(`Installing ${displayName}...`);
            try {
                const res = await fetch('/api/catalog/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({slug})
                });
                const data = await res.json();
                if (data.success) {
                    installingSlugs.delete(slug);
                    showToast(`Installed ${displayName}!`);
                    if (btn) {
                        btn.className = 'btn btn-outline';
                        btn.disabled = true;
                        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Installed`;
                    }
                    await loadInstalledPets();
                    filterCatalog();
                } else {
                    installingSlugs.delete(slug);
                    showToast('Installation error: ' + (data.error || 'Failed to install'), true);
                    if (btn) {
                        btn.disabled = false;
                        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> Install`;
                    }
                }
            } catch (e) {
                installingSlugs.delete(slug);
                showToast(`Failed to install ${displayName}`, true);
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> Install`;
                }
            }
        }

        function downloadPet(slug, name) {
            return installPet(slug, name);
        }

        async function loadSettings() {
            try {
                const res = await fetch('/api/settings');
                const cfg = await res.json();
                const sPct = Math.round((cfg.scale || 0.75) * 100);
                document.getElementById('setting-scale').value = sPct;
                document.getElementById('scale-val').innerText = sPct + '%';
                document.getElementById('setting-behavior').value = cfg.behavior || 'zero_g';
                document.getElementById('setting-sync').checked = cfg.sync_with_antigravity !== false;
                document.getElementById('setting-startup').checked = cfg.start_with_windows === true;
                document.getElementById('setting-sound').checked = cfg.sound_enabled !== false;
                loadShortcutsUI(cfg.shortcuts);
            } catch (e) {
                console.error(e);
            }
        }

        const DEFAULT_SHORTCUTS = {
            toggle_pet: "Ctrl + Alt + P",
            toggle_visibility: "Ctrl + Alt + H",
            switch_pet: "Ctrl + Alt + N",
            toggle_behavior: "Ctrl + Alt + B",
            open_settings: "Ctrl + Alt + S"
        };

        let currentShortcuts = { ...DEFAULT_SHORTCUTS };
        let activeRecordingAction = null;

        function loadShortcutsUI(shortcuts) {
            const sc = shortcuts || {};
            for (const key of ['toggle_pet', 'toggle_visibility', 'switch_pet', 'toggle_behavior', 'open_settings']) {
                const val = (sc[key] !== undefined && sc[key] !== null) ? sc[key] : (DEFAULT_SHORTCUTS[key] || '');
                currentShortcuts[key] = val;
                const el = document.getElementById('shortcut-' + key);
                if (el) {
                    el.value = val;
                    el.classList.remove('recording');
                }
            }
        }

        function startRecordingShortcut(action) {
            if (activeRecordingAction && activeRecordingAction !== action) {
                const prev = document.getElementById('shortcut-' + activeRecordingAction);
                if (prev) {
                    prev.classList.remove('recording');
                    prev.value = currentShortcuts[activeRecordingAction] || '';
                }
            }
            activeRecordingAction = action;
            const input = document.getElementById('shortcut-' + action);
            if (input) {
                input.classList.add('recording');
                input.value = 'Press keys...';
            }
        }

        async function handleShortcutKeydown(e, action) {
            e.preventDefault();
            e.stopPropagation();

            if (e.key === 'Escape') {
                const input = document.getElementById('shortcut-' + action);
                if (input) {
                    input.classList.remove('recording');
                    input.value = currentShortcuts[action] || '';
                }
                activeRecordingAction = null;
                return;
            }

            if (e.key === 'Backspace' || e.key === 'Delete') {
                await setShortcutValue(action, '');
                activeRecordingAction = null;
                return;
            }

            // Collect modifiers
            const parts = [];
            if (e.ctrlKey) parts.push('Ctrl');
            if (e.altKey) parts.push('Alt');
            if (e.shiftKey) parts.push('Shift');
            if (e.metaKey) parts.push('Win');

            // If only modifier is pressed so far, display partial
            const k = e.key;
            if (['Control', 'Alt', 'Shift', 'Meta'].includes(k)) {
                const input = document.getElementById('shortcut-' + action);
                if (input && parts.length > 0) {
                    input.value = parts.join(' + ') + ' + ...';
                }
                return;
            }

            // Format primary key
            let keyName = k.length === 1 ? k.toUpperCase() : k;
            if (keyName === ' ') keyName = 'Space';
            parts.push(keyName);

            const shortcutStr = parts.join(' + ');
            await setShortcutValue(action, shortcutStr);
            activeRecordingAction = null;
        }

        async function clearShortcut(action) {
            await setShortcutValue(action, '');
        }

        async function setShortcutValue(action, value) {
            currentShortcuts[action] = value;
            const input = document.getElementById('shortcut-' + action);
            if (input) {
                input.value = value;
                input.classList.remove('recording');
            }
            await saveShortcuts();
        }

        async function resetShortcutsToDefault() {
            currentShortcuts = { ...DEFAULT_SHORTCUTS };
            loadShortcutsUI(currentShortcuts);
            await saveShortcuts();
            showToast('Shortcuts reset to defaults');
        }

        async function saveShortcuts() {
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ shortcuts: currentShortcuts })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Shortcuts updated successfully');
                }
            } catch (err) {
                console.error('Failed to save shortcuts:', err);
                showToast('Failed to save shortcuts');
            }
        }

        async function updateScale(val) {
            document.getElementById('scale-val').innerText = val + '%';
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({scale: parseFloat(val) / 100})
            });
        }

        async function updateBehavior(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({behavior: val})
            });
            showToast(val === 'zero_g' ? 'Behavior: Zero-G Float' : 'Behavior: Stationary');
        }

        async function updateSync(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sync_with_antigravity: val})
            });
            showToast(val ? 'Auto-sync enabled' : 'Auto-sync disabled');
        }

        async function updateStartup(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({start_with_windows: val})
            });
            showToast(val ? 'Launch on startup enabled' : 'Launch on startup disabled');
        }

        async function updateSound(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sound_enabled: val})
            });
            showToast(val ? 'Sound effects enabled' : 'Sound effects muted');
        }

        // --- DIY Creator & Drag-and-Drop ---
        let selectedFileDataUrl = '';
        let selectedFileExt = '';
        let selectedZipFile = null;

        const dropZone = document.getElementById('drop-zone');
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                processSelectedFile(e.dataTransfer.files[0]);
            }
        });

        function handleImageSelected(e) {
            if (e.target.files && e.target.files.length > 0) {
                processSelectedFile(e.target.files[0]);
            }
        }

        function handleZipSelected(e) {
            if (e.target.files && e.target.files.length > 0) {
                processSelectedFile(e.target.files[0]);
            }
        }

        function processSelectedFile(file) {
            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            const baseName = file.name.substring(0, file.name.lastIndexOf('.'));

            if (!document.getElementById('creator-name').value) {
                document.getElementById('creator-name').value = baseName;
            }

            if (ext === '.zip') {
                selectedZipFile = file;
                selectedFileExt = '.zip';
                document.getElementById('drop-title').innerText = `Loaded ZIP: ${file.name}`;
                document.getElementById('preview-title').innerText = document.getElementById('creator-name').value || baseName;
                document.getElementById('preview-desc').innerText = 'Codex Pet Package ready to install';
                
                const reader = new FileReader();
                reader.onload = (e) => { selectedFileDataUrl = e.target.result; };
                reader.readAsDataURL(file);
                return;
            }

            if (['.gif', '.png', '.webp', '.jpg', '.jpeg'].includes(ext)) {
                selectedFileExt = ext;
                selectedZipFile = null;
                const reader = new FileReader();
                reader.onload = (e) => {
                    selectedFileDataUrl = e.target.result;
                    document.getElementById('creator-img-preview').src = selectedFileDataUrl;
                    document.getElementById('drop-title').innerText = `Loaded: ${file.name}`;
                    updateCreatorPreview();
                };
                reader.readAsDataURL(file);
            } else {
                showToast('Unsupported file type. Use .zip, .gif, .png, or .webp');
            }
        }

        function updateCreatorPreview() {
            const name = document.getElementById('creator-name').value.trim();
            const desc = document.getElementById('creator-desc').value.trim();
            document.getElementById('preview-title').innerText = name || 'My Custom Pet';
            document.getElementById('preview-desc').innerText = desc || 'Ready to create & slice';
        }

        async function saveCustomPet() {
            const name = document.getElementById('creator-name').value.trim();
            const desc = document.getElementById('creator-desc').value.trim();

            if (!name) {
                showToast('Please enter a pet name');
                return;
            }
            if (!selectedFileDataUrl) {
                showToast('Please upload an image, GIF, or ZIP file first');
                return;
            }

            showToast('Creating pet & generating animation frames...');
            try {
                const res = await fetch('/api/custom/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: name,
                        desc: desc,
                        fileData: selectedFileDataUrl,
                        ext: selectedFileExt
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Pet "${name}" created and installed!`);
                    await loadInstalledPets();
                    switchTab('installed');
                } else {
                    showToast('Creation failed: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Failed to create custom pet');
            }
        }

        // Initialize on load
        loadInstalledPets();
    </script>
</body>
</html>
"""

class HubHandler(BaseHTTPRequestHandler):
    def _send_html(self, content):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Restrict CORS to local origins only
        origin = self.headers.get("Origin", "")
        if origin in ("http://127.0.0.1:54321", "http://localhost:54321", "null"):
            self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_html(HTML_CONTENT)
            return

        if path == "/logo.png":
            logo_path = get_asset_path("logo.png")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f:
                    b = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return

        if path == "/api/pets":
            cfg = load_config()
            deleted = set(cfg.get("deleted_pets", []))
            pets = [p for p in get_available_pets(PETS_DIR) if p.slug not in deleted]
            pets_data = [
                {
                    "slug": p.slug,
                    "displayName": p.display_name,
                    "description": p.description,
                    "version": p.version
                }
                for p in pets
            ]
            self._send_json({"pets": pets_data, "current": cfg.get("current_pet", "desk-otter--zihualiu1997")})
            return

        if path == "/api/catalog":
            data = catalog.fetch_catalog()
            self._send_json(data)
            return

        if path == "/api/settings":
            self._send_json(load_config())
            return

        if path == "/pet_spritesheet":
            raw_slug = qs.get("slug", ["desk-otter--zihualiu1997"])[0]
            slug = safe_slug(raw_slug)
            pet_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not pet_dir.startswith(os.path.abspath(PETS_DIR)):
                self.send_response(403)
                self.end_headers()
                return

            candidates = ["spritesheet.webp", "spritesheet.png", "pet.png", "sheet.png", "spritesheet.gif"]
            for fname in candidates:
                fpath = os.path.join(pet_dir, fname)
                if os.path.exists(fpath):
                    ext = os.path.splitext(fname)[1].lower()
                    ctype = "image/webp" if ext == ".webp" else ("image/gif" if ext == ".gif" else "image/png")
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    try:
                        with open(fpath, "rb") as f:
                            self.wfile.write(f.read())
                        return
                    except Exception:
                        pass
            self.send_response(404)
            self.end_headers()
            return

        if path == "/pet_thumbnail":
            raw_slug = qs.get("slug", ["desk-otter--zihualiu1997"])[0]
            slug = safe_slug(raw_slug)

            # 1. Check in-memory cache
            if slug in _THUMBNAIL_CACHE:
                b = _THUMBNAIL_CACHE[slug]
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(b)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(b)
                return

            pet_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not pet_dir.startswith(os.path.abspath(PETS_DIR)):
                self.send_response(403)
                self.end_headers()
                return

            # 2. Check disk .thumb.png
            thumb_path = os.path.join(pet_dir, ".thumb.png")
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                try:
                    with open(thumb_path, "rb") as f:
                        b = f.read()
                    _THUMBNAIL_CACHE[slug] = b
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(b)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(b)
                    return
                except Exception:
                    pass

            # 3. Check spritesheet or image candidates
            candidate_files = [
                os.path.join(pet_dir, "spritesheet.webp"),
                os.path.join(pet_dir, "spritesheet.png"),
                os.path.join(pet_dir, "pet.png"),
                os.path.join(pet_dir, "spritesheet.gif")
            ]
            sheet_path = next((f for f in candidate_files if os.path.exists(f)), None)

            if sheet_path:
                try:
                    with Image.open(sheet_path) as im:
                        cols = 8
                        rows = 11 if im.size[1] >= 2100 else 9
                        cell_w = max(1, im.size[0] // cols)
                        cell_h = max(1, im.size[1] // rows)
                        f0 = im.crop((0, 0, cell_w, cell_h))
                        buf = io.BytesIO()
                        f0.save(buf, format="PNG")
                        b = buf.getvalue()
                        _THUMBNAIL_CACHE[slug] = b
                        try:
                            f0.save(thumb_path, format="PNG")
                        except Exception:
                            pass
                        self.send_response(200)
                        self.send_header("Content-Type", "image/png")
                        self.send_header("Content-Length", str(len(b)))
                        self.send_header("Cache-Control", "public, max-age=86400")
                        self.end_headers()
                        self.wfile.write(b)
                        return
                except Exception:
                    pass

            # 4. Reliable SVG placeholder fallback (never 404!)
            initial = (slug[:1] or "P").upper()
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
                <rect width="128" height="128" rx="16" fill="#18181b"/>
                <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="44" font-weight="bold" fill="#38bdf8">{initial}</text>
            </svg>'''
            b = svg.encode("utf-8")
            _THUMBNAIL_CACHE[slug] = b
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        # CSRF Protection: Ensure request is coming from local browser/app
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send_response(403)
            self.end_headers()
            return

        origin = self.headers.get("Origin")
        if origin and origin not in ("http://127.0.0.1:54321", "http://localhost:54321", "null"):
            self.send_response(403)
            self.end_headers()
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/pets/activate":
            slug = safe_slug(body.get("slug"))
            if slug:
                cfg = load_config()
                cfg["current_pet"] = slug
                save_config(cfg)
                try:
                    os.utime(SETTINGS_FILE, None)
                except Exception:
                    pass
                self._send_json({"success": True})
            else:
                self._send_json({"success": False, "error": "Missing or invalid slug"}, 400)
            return

        if path == "/api/pets/update":
            slug = safe_slug(body.get("slug"))
            new_name = str(body.get("name", "")).strip()
            new_desc = str(body.get("desc", "")).strip()

            if not slug or not new_name:
                self._send_json({"success": False, "error": "Missing slug or name"}, 400)
                return

            pet_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not pet_dir.startswith(os.path.abspath(PETS_DIR)) or not os.path.exists(pet_dir):
                self._send_json({"success": False, "error": "Pet not found"}, 404)
                return

            manifest_path = os.path.join(pet_dir, "pet.json")
            manifest = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except Exception:
                    manifest = {}

            manifest["displayName"] = new_name
            manifest["description"] = new_desc

            try:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
                return

            try:
                os.utime(SETTINGS_FILE, None)
            except Exception:
                pass

            self._send_json({"success": True})
            return

        if path == "/api/pets/delete":
            slug = safe_slug(body.get("slug"))
            if not slug:
                self._send_json({"success": False, "error": "Missing or invalid slug"}, 400)
                return

            target_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not target_dir.startswith(os.path.abspath(PETS_DIR)):
                self._send_json({"success": False, "error": "Access denied"}, 403)
                return

            cfg = load_config()
            deleted_list = cfg.get("deleted_pets", [])
            if slug not in deleted_list:
                deleted_list.append(slug)
                cfg["deleted_pets"] = deleted_list

            if cfg.get("current_pet") == slug:
                all_pets = [p for p in get_available_pets(PETS_DIR) if p.slug != slug]
                cfg["current_pet"] = all_pets[0].slug if all_pets else ""

            save_config(cfg)

            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)

            _THUMBNAIL_CACHE.pop(slug, None)
            try:
                os.utime(SETTINGS_FILE, None)
            except Exception:
                pass
            self._send_json({"success": True})
            return

        if path == "/api/settings":
            cfg = load_config()
            for k in ("scale", "behavior", "sync_with_antigravity", "sound_enabled", "speech_enabled", "start_with_windows", "shortcuts"):
                if k in body:
                    cfg[k] = body[k]
                    if k == "start_with_windows":
                        try:
                            from config import sync_windows_startup
                            sync_windows_startup(bool(body[k]))
                        except Exception:
                            pass
                    elif k == "shortcuts":
                        try:
                            from config import sync_desktop_shortcut
                            toggle_pet_sc = body[k].get("toggle_pet", "Ctrl+Alt+P") if isinstance(body[k], dict) else "Ctrl+Alt+P"
                            sync_desktop_shortcut(toggle_pet_sc)
                        except Exception:
                            pass
            save_config(cfg)
            try:
                os.utime(SETTINGS_FILE, None)
            except Exception:
                pass
            self._send_json({"success": True, "config": cfg})
            return

        if path == "/api/catalog/download" or path == "/api/catalog/install":
            slug = safe_slug(body.get("slug"))
            if not slug:
                self._send_json({"success": False, "error": "Missing or invalid slug"}, 400)
                return

            done_evt = threading.Event()
            res_holder = {}

            def _cb(success, *args, **kwargs):
                res_holder["success"] = success
                if len(args) >= 2:
                    res_holder["error"] = args[1]
                elif len(args) == 1:
                    res_holder["error"] = args[0]
                else:
                    res_holder["error"] = kwargs.get("err") or kwargs.get("error")
                done_evt.set()

            catalog.download_pet(slug, callback=_cb)
            done_evt.wait(timeout=30.0)

            if res_holder.get("success"):
                _THUMBNAIL_CACHE.pop(slug, None)
                cfg = load_config()
                deleted_pets = cfg.get("deleted_pets", [])
                if slug in deleted_pets:
                    deleted_pets.remove(slug)
                    cfg["deleted_pets"] = deleted_pets
                cfg["current_pet"] = slug
                save_config(cfg)
                try:
                    os.utime(SETTINGS_FILE, None)
                except Exception:
                    pass
                self._send_json({"success": True})
            else:
                self._send_json({"success": False, "error": res_holder.get("error", "Installation timed out")}, 500)
            return

        if path == "/api/pets/import_zip":
            try:
                b64 = body.get("data", "")
                filename = body.get("filename", "custom_pet.zip")
                if "," in b64:
                    b64 = b64.split(",")[1]
                raw_zip = base64.b64decode(b64)
                fallback_name = os.path.splitext(filename)[0]
                result = pet_importer.import_zip_bytes(raw_zip, PETS_DIR, fallback_name)
                
                if result.get("success"):
                    slug = result["slug"]
                    _THUMBNAIL_CACHE.pop(slug, None)
                    cfg = load_config()
                    cfg["current_pet"] = slug
                    save_config(cfg)
                    try:
                        os.utime(SETTINGS_FILE, None)
                    except Exception:
                        pass
                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        if path == "/api/custom/create":
            try:
                name = body.get("name", "Custom Pet").strip()
                desc = body.get("desc", "").strip()
                file_data_url = body.get("fileData", "")
                ext = body.get("ext", ".webp")

                if ext.lower() == ".zip":
                    if "," in file_data_url:
                        b64 = file_data_url.split(",")[1]
                    else:
                        b64 = file_data_url
                    raw_zip = base64.b64decode(b64)
                    result = pet_importer.import_zip_bytes(raw_zip, PETS_DIR, name)
                    if result.get("success"):
                        slug = result["slug"]
                        _THUMBNAIL_CACHE.pop(slug, None)
                        cfg = load_config()
                        cfg["current_pet"] = slug
                        save_config(cfg)
                        try:
                            os.utime(SETTINGS_FILE, None)
                        except Exception:
                            pass
                    self._send_json(result)
                    return

                slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
                if not slug:
                    slug = f"custom-pet-{int(time.time())}"

                target_dir = os.path.join(PETS_DIR, slug)

                if "," in file_data_url:
                    base64_str = file_data_url.split(",")[1]
                else:
                    base64_str = file_data_url

                raw_bytes = base64.b64decode(base64_str)
                result = pet_importer.convert_image_or_gif_to_spritesheet(
                    raw_bytes, ext, target_dir, name, desc
                )

                if result.get("success"):
                    _THUMBNAIL_CACHE.pop(slug, None)
                    cfg = load_config()
                    cfg["current_pet"] = slug
                    save_config(cfg)
                    try:
                        os.utime(SETTINGS_FILE, None)
                    except Exception:
                        pass

                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_hub_background_server(port=54321):
    server = HTTPServer(("127.0.0.1", port), HubHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

def open_hub_app(port=54321):
    import subprocess
    import win32gui
    import win32con

    # 1. Check if Settings window is already open (avoid matching our transparent pet window)
    existing_hwnd = None
    def enum_cb(hwnd, _):
        nonlocal existing_hwnd
        if win32gui.IsWindowVisible(hwnd):
            cls = win32gui.GetClassName(hwnd)
            if cls == "AntigravityPetWindowLayered":
                return True
            title = win32gui.GetWindowText(hwnd)
            if "Antigravity Pet Settings" in title or "Antigravity Pet Hub" in title or f"127.0.0.1:{port}" in title:
                existing_hwnd = hwnd
                return False
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    if existing_hwnd:
        try:
            win32gui.ShowWindow(existing_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(existing_hwnd)
            win32gui.BringWindowToTop(existing_hwnd)
            return
        except Exception:
            pass

    # 2. Open new instance if none was open
    url = f"http://127.0.0.1:{port}"
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if os.path.exists(edge_exe):
        try:
            subprocess.Popen([edge_exe, f"--app={url}", "--window-size=1040,740"])
            return
        except Exception:
            pass
    import webbrowser
    webbrowser.open(url)

if __name__ == "__main__":
    srv = start_hub_background_server(54321)
    print("Hub server running at http://127.0.0.1:54321")
    open_hub_app(54321)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
