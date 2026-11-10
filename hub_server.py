import os
import sys
import json
import time
import base64
import shutil
import urllib.parse
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from PIL import Image

from config import load_config, save_config, SETTINGS_FILE, PETS_DIR, CONFIG_DIR, get_asset_path
from pet_loader import get_available_pets, PetDefinition
from downloader import PetCatalog
import pet_importer

catalog = PetCatalog(PETS_DIR)

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
    <title>Antigravity Pet Hub & Codex Gallery</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <style>
        :root {
            --bg-body: #09090b;
            --bg-card: #18181b;
            --bg-card-hover: #222226;
            --border: #27272a;
            --border-highlight: #38bdf8;
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --badge-bg: rgba(56, 189, 248, 0.15);
            --badge-border: #38bdf8;
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
                --badge-bg: rgba(2, 132, 199, 0.1);
                --badge-border: #0284c7;
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
            padding: 16px 28px;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
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
            font-size: 17px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }

        .brand p {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 1px;
        }

        .tabs {
            display: flex;
            gap: 6px;
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
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn:hover {
            color: var(--text-main);
        }

        .tab-btn.active {
            background: var(--bg-card);
            color: var(--accent);
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }

        main {
            flex: 1;
            padding: 24px 28px;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
            animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .grid-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            gap: 16px;
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
            transition: border 0.2s;
        }

        .search-box input:focus {
            border-color: var(--border-highlight);
        }

        .search-icon {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 14px;
            color: var(--text-muted);
        }

        .pets-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 18px;
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
            transition: all 0.2s ease;
        }

        .pet-card:hover {
            border-color: var(--border-highlight);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.15);
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
            padding: 3px 8px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .pet-preview {
            width: 110px;
            height: 110px;
            margin: 10px 0 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            background: rgba(0,0,0,0.06);
            border-radius: 8px;
            overflow: hidden;
        }

        .pet-preview img {
            max-width: 100%;
            max-height: 100%;
            image-rendering: pixelated;
        }

        .pet-info h3 {
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .pet-info p {
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 14px;
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
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
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

        .btn-outline:hover {
            border-color: var(--border-highlight);
            color: var(--accent);
            background: var(--badge-bg);
        }

        .btn-danger {
            background: transparent;
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.4);
            width: auto;
            padding: 8px 10px;
        }

        .btn-danger:hover {
            background: var(--danger);
            color: #fff;
            border-color: var(--danger);
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
            background: rgba(0,0,0,0.06);
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
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            display: none;
            z-index: 1000;
            font-size: 13px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <img src="/logo.png" alt="Antigravity">
            <div>
                <h1>Antigravity Pet Hub</h1>
                <p>Interactive Desktop Companion & Codex Pets Downloader</p>
            </div>
        </div>
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('installed')">🐾 My Pets</button>
            <button class="tab-btn" onclick="switchTab('gallery')">🌐 Codex Gallery</button>
            <button class="tab-btn" onclick="switchTab('creator')">🛠️ DIY Pet Maker</button>
            <button class="tab-btn" onclick="switchTab('settings')">⚙️ Settings</button>
        </div>
    </header>

    <main>
        <!-- Tab 1: Installed Pets -->
        <div id="tab-installed" class="tab-pane active">
            <div class="grid-header">
                <div>
                    <h2>Installed Pets</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-top:2px;">Select a character to roam your desktop or open Antigravity 2.0</p>
                </div>
            </div>
            <div class="pets-grid" id="installed-grid"></div>
        </div>

        <!-- Tab 2: Online Codex Pets Gallery -->
        <div id="tab-gallery" class="tab-pane">
            <div class="grid-header">
                <div>
                    <h2>Codex Pets Catalog (370+ Mascot Pets)</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-top:2px;">Browse and download free community mascots from codexpets.net</p>
                </div>
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="catalog-search" placeholder="Search pets (e.g. Digimon, Cat, Anya, Robot)..." oninput="filterCatalog()">
                </div>
            </div>
            <div class="pets-grid" id="catalog-grid"></div>
        </div>

        <!-- Tab 3: DIY Pet Maker & Customizer -->
        <div id="tab-creator" class="tab-pane">
            <div class="creator-container">
                <div class="settings-card" style="max-width:none; margin:0;">
                    <h2 style="margin-bottom:6px;">🛠️ Create / Import a Pet</h2>
                    <p style="color:var(--text-muted); font-size:13px; margin-bottom:20px;">Upload an animated GIF, image, spritesheet, or drag & drop a downloaded Codex Pet .ZIP!</p>
                    
                    <div class="drop-zone" id="drop-zone">
                        <div style="font-size:36px; margin-bottom:8px;">📦</div>
                        <h4 style="margin-bottom:4px;" id="drop-title">Drag & Drop Pet .ZIP or Image / GIF Here</h4>
                        <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Supports .zip (Codex pet packages), .gif (animated), .webp, .png, or .jpg</p>
                        <div style="display:inline-flex; gap:10px;">
                            <button type="button" class="btn btn-outline" style="width:auto;" onclick="event.stopPropagation(); document.getElementById('pet-file-input').click();">📁 Browse Image/GIF</button>
                            <button type="button" class="btn btn-outline" style="width:auto;" onclick="event.stopPropagation(); document.getElementById('zip-file-input').click();">📦 Browse .ZIP</button>
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
                    <h3>Character Preview</h3>
                    <div class="creator-img-box">
                        <img id="creator-img-preview" src="" alt="Preview">
                    </div>
                    <h4 id="preview-title" style="margin-bottom:4px;">My Custom Pet</h4>
                    <p id="preview-desc" style="font-size:12px; color:var(--text-muted); margin-bottom:16px;">Ready to create & slice</p>
                    <button class="btn" onclick="saveCustomPet()">✨ Create & Install Pet</button>
                </div>
            </div>
        </div>

        <!-- Tab 4: Settings -->
        <div id="tab-settings" class="tab-pane">
            <div class="settings-card">
                <h2 style="margin-bottom:6px;">Companion Settings</h2>
                <p style="color:var(--text-muted); font-size:13px; margin-bottom:20px;">Configure how your Antigravity pet behaves and interacts in real time.</p>

                <div class="form-group">
                    <label>Pet Scale (Size)</label>
                    <div class="range-container">
                        <input type="range" id="setting-scale" min="40" max="150" step="5" oninput="updateScale(this.value)">
                        <span id="scale-val" style="font-weight:700; width:45px;">75%</span>
                    </div>
                    <p>Immediately scales pet from compact (40%) to large (150%) on screen.</p>
                </div>

                <div class="form-group">
                    <label>Behavior Mode</label>
                    <select id="setting-behavior" class="form-input" onchange="updateBehavior(this.value)">
                        <option value="zero_g">🪐 Zero-G Float (Gentle vertical hover floating)</option>
                        <option value="static">📌 Stay Put (Locked stationary position)</option>
                    </select>
                </div>

                <div class="switch-group">
                    <div>
                        <div style="font-weight:600; font-size:13px;">🔒 Antigravity Auto-Sync</div>
                        <p style="font-size:12px; color:var(--text-muted);">Only show pet when Antigravity 2.0 is running on Windows</p>
                    </div>
                    <input type="checkbox" id="setting-sync" style="width:18px; height:18px; accent-color:var(--accent);" onchange="updateSync(this.checked)">
                </div>

                <div class="switch-group">
                    <div>
                        <div style="font-weight:600; font-size:13px;">🔊 Sound Effects</div>
                        <p style="font-size:12px; color:var(--text-muted);">Play soft system audio chimes on click, jump, and warp launch</p>
                    </div>
                    <input type="checkbox" id="setting-sound" style="width:18px; height:18px; accent-color:var(--accent);" onchange="updateSound(this.checked)">
                </div>

                <div class="form-group" style="margin-top:20px; padding-top:16px; border-top:1px solid var(--border);">
                    <label>Global Show / Hide Shortcuts</label>
                    <div style="display:flex; gap:10px;">
                        <div style="background:var(--bg-body); padding:10px 14px; border-radius:8px; border:1px solid var(--border); font-family:monospace; font-weight:700; color:var(--accent);">
                            Ctrl + Alt + P
                        </div>
                        <div style="background:var(--bg-body); padding:10px 14px; border-radius:8px; border:1px solid var(--border); font-family:monospace; font-weight:700; color:var(--accent);">
                            Win + Alt + P
                        </div>
                    </div>
                    <p>Press either shortcut anywhere in Windows to instantly show or hide the pet.</p>
                </div>
            </div>
        </div>
    </main>

    <div id="toast" class="toast"></div>

    <script>
        let installedPets = [];
        let catalogPets = [];
        let currentPetSlug = 'gigimon';
        let customBase64Data = null;
        let customFileExt = '.webp';

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 2600);
        }

        function switchTab(tabId) {
            const tabMap = {installed: 0, gallery: 1, creator: 2, settings: 3};
            const btnIdx = tabMap[tabId] !== undefined ? tabMap[tabId] : 0;
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach((b, i) => {
                b.classList.toggle('active', i === btnIdx);
            });
            document.querySelectorAll('.tab-pane').forEach(p => {
                p.classList.toggle('active', p.id === 'tab-' + tabId);
            });
        }

        async function loadInstalledPets() {
            try {
                const res = await fetch('/api/pets');
                const data = await res.json();
                installedPets = data.pets;
                currentPetSlug = data.current;
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
                const card = document.createElement('div');
                card.className = `pet-card ${isAct ? 'active-pet' : ''}`;
                card.innerHTML = `
                    ${isAct ? '<span class="badge-active">Active ★</span>' : ''}
                    <div class="pet-preview">
                        <img src="/pet_thumbnail?slug=${p.slug}&t=${Date.now()}" alt="${p.displayName}">
                    </div>
                    <div class="pet-info">
                        <h3>${p.displayName}</h3>
                        <p>${p.description || 'Codex companion for your desktop.'}</p>
                    </div>
                    <div class="card-actions">
                        ${isAct ? 
                            '<button class="btn btn-outline" style="flex:1;" disabled>Currently Active</button>' : 
                            `<button class="btn" style="flex:1;" onclick="activatePet('${p.slug}')">★ Set Active</button>`
                        }
                        ${!isAct && installedPets.length > 1 ? 
                            `<button class="btn btn-danger" title="Delete pet" onclick="deletePet('${p.slug}', '${p.displayName}')">🗑️</button>` : ''
                        }
                    </div>
                `;
                grid.appendChild(card);
            });
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
                    showToast(`Switched active pet to ${slug}! ✨`);
                }
            } catch (e) {
                showToast('Failed to switch pet');
            }
        }

        async function deletePet(slug, displayName) {
            if (!confirm(`Are you sure you want to delete "${displayName || slug}"?`)) {
                return;
            }
            try {
                const res = await fetch('/api/pets/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({slug})
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Deleted ${displayName || slug} ✓`);
                    await loadInstalledPets();
                } else {
                    showToast('Failed to delete: ' + data.error);
                }
            } catch (e) {
                showToast('Delete error');
            }
        }

        async function loadCatalog() {
            try {
                const res = await fetch('/api/catalog');
                catalogPets = await res.json();
                renderCatalogGrid(catalogPets);
            } catch (e) {
                console.error(e);
            }
        }

        function renderCatalogGrid(pets) {
            const grid = document.getElementById('catalog-grid');
            grid.innerHTML = '';
            const installedSlugs = new Set(installedPets.map(p => p.slug));

            pets.slice(0, 60).forEach(p => {
                const isInst = installedSlugs.has(p.slug);
                const card = document.createElement('div');
                card.className = 'pet-card';
                card.innerHTML = `
                    <div class="pet-preview">
                        <img src="https://raw.githubusercontent.com/legeling/awesome-codex-pet/main/pets/${p.slug}/spritesheet.webp" 
                             alt="${p.name}" 
                             onerror="this.src='/pet_thumbnail?slug=gigimon'">
                    </div>
                    <div class="pet-info">
                        <h3>${p.name}</h3>
                        <p>${p.description || p.primary_category || 'Community Codex Pet'}</p>
                    </div>
                    ${isInst ? '<button class="btn btn-outline" disabled>Installed ✓</button>' : `<button class="btn" onclick="downloadPet('${p.slug}')">⬇ Download & Install</button>`}
                `;
                grid.appendChild(card);
            });
        }

        function filterCatalog() {
            const q = document.getElementById('catalog-search').value.toLowerCase().trim();
            if (!q) {
                renderCatalogGrid(catalogPets);
                return;
            }
            const filtered = catalogPets.filter(p => 
                (p.name && p.name.toLowerCase().includes(q)) ||
                (p.slug && p.slug.toLowerCase().includes(q)) ||
                (p.description && p.description.toLowerCase().includes(q)) ||
                (p.primary_category && p.primary_category.toLowerCase().includes(q))
            );
            renderCatalogGrid(filtered);
        }

        async function downloadPet(slug) {
            showToast(`Downloading ${slug}...`);
            try {
                const res = await fetch('/api/catalog/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({slug})
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Successfully installed ${slug}! ✓`);
                    await loadInstalledPets();
                    renderCatalogGrid(catalogPets);
                } else {
                    showToast('Download error: ' + data.error);
                }
            } catch (e) {
                showToast('Failed to download pet');
            }
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
                document.getElementById('setting-sound').checked = cfg.sound_enabled !== false;
            } catch (e) {
                console.error(e);
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
            showToast(`Behavior updated: ${val}`);
        }

        async function updateSync(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sync_with_antigravity: val})
            });
            showToast(`Auto-sync: ${val ? 'ON 🔒' : 'OFF 🔓'}`);
        }

        async function updateSound(val) {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({sound_enabled: val})
            });
            showToast(`Sound: ${val ? 'ON 🔊' : 'Muted 🔇'}`);
        }

        // Setup Drag & Drop handlers on drop-zone
        const dropZone = document.getElementById('drop-zone');
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            }, false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            }, false);
        });

        dropZone.addEventListener('drop', e => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                const file = files[0];
                if (file.name.toLowerCase().endsWith('.zip')) {
                    uploadZipFile(file);
                } else {
                    processImageFile(file);
                }
            }
        });

        function handleImageSelected(event) {
            const file = event.target.files[0];
            if (file) processImageFile(file);
        }

        function handleZipSelected(event) {
            const file = event.target.files[0];
            if (file) uploadZipFile(file);
        }

        function processImageFile(file) {
            const reader = new FileReader();
            customFileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase() || '.webp';
            reader.onload = function(e) {
                customBase64Data = e.target.result;
                document.getElementById('creator-img-preview').src = customBase64Data;
                const name = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
                document.getElementById('creator-name').value = name.charAt(0).toUpperCase() + name.slice(1);
                updateCreatorPreview();
                showToast(`Loaded ${file.name}`);
            };
            reader.readAsDataURL(file);
        }

        async function uploadZipFile(file) {
            showToast(`Extracting & importing ${file.name}...`);
            const reader = new FileReader();
            reader.onload = async function(e) {
                try {
                    const res = await fetch('/api/custom/import_zip', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            zipData: e.target.result,
                            filename: file.name
                        })
                    });
                    const data = await res.json();
                    if (data.success) {
                        showToast(`Successfully installed ${data.name || data.slug}! ✨`);
                        await loadInstalledPets();
                        switchTab('installed');
                    } else {
                        showToast('Zip import error: ' + (data.error || 'Failed'));
                    }
                } catch (err) {
                    console.error('Upload zip error:', err);
                    showToast('Failed to import zip archive');
                }
            };
            reader.readAsDataURL(file);
        }

        function updateCreatorPreview() {
            const n = document.getElementById('creator-name').value || 'My Custom Pet';
            const d = document.getElementById('creator-desc').value || 'Ready to create & slice';
            document.getElementById('preview-title').innerText = n;
            document.getElementById('preview-desc').innerText = d;
        }

        async function saveCustomPet() {
            if (!customBase64Data) {
                showToast('Please choose or drop an image / GIF file first!');
                return;
            }
            const name = document.getElementById('creator-name').value.trim() || 'Custom Pet';
            const desc = document.getElementById('creator-desc').value.trim() || 'Custom desktop companion';

            showToast('Synthesizing 8x9 animation atlas...');
            try {
                const res = await fetch('/api/custom/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: name,
                        desc: desc,
                        fileData: customBase64Data,
                        ext: customFileExt
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Created & activated ${name}! ✨`);
                    await loadInstalledPets();
                    switchTab('installed');
                    document.querySelectorAll('.tab-btn')[0].classList.add('active');
                    document.querySelectorAll('.tab-btn')[2].classList.remove('active');
                } else {
                    showToast('Failed to create pet: ' + data.error);
                }
            } catch (e) {
                showToast('Upload error');
            }
        }

        loadInstalledPets();
        loadCatalog();
        loadSettings();
    </script>
</body>
</html>
"""

class HubHandler(BaseHTTPRequestHandler):
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

    def _send_html(self, html, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
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
            pets = get_available_pets(PETS_DIR)
            pets_data = [
                {
                    "slug": p.slug,
                    "displayName": p.display_name,
                    "description": p.description,
                    "version": p.version
                }
                for p in pets
            ]
            self._send_json({"pets": pets_data, "current": cfg.get("current_pet", "gigimon")})
            return

        if path == "/api/catalog":
            data = catalog.fetch_catalog()
            self._send_json(data)
            return

        if path == "/api/settings":
            self._send_json(load_config())
            return

        if path == "/pet_thumbnail":
            raw_slug = qs.get("slug", ["desk-otter--zihualiu1997"])[0]
            slug = safe_slug(raw_slug)
            pet_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not pet_dir.startswith(os.path.abspath(PETS_DIR)):
                self.send_response(403)
                self.end_headers()
                return

            sheet_path = os.path.join(pet_dir, "spritesheet.webp")
            if not os.path.exists(sheet_path):
                sheet_path = os.path.join(pet_dir, "spritesheet.png")

            if os.path.exists(sheet_path):
                try:
                    im = Image.open(sheet_path)
                    cell_w = im.size[0] // 8
                    cell_h = im.size[1] // (11 if im.size[1] >= 2100 else 9)
                    f0 = im.crop((0, 0, cell_w, cell_h))
                    thumb_path = os.path.join(pet_dir, ".thumb.png")
                    f0.save(thumb_path, format="PNG")
                    with open(thumb_path, "rb") as f:
                        b = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                    return
                except Exception:
                    pass

            self.send_response(404)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        # 1. CSRF Protection: Ensure request is coming from local browser/app
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
        post_data = self.rfile.read(length) if length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8"))
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

        if path == "/api/pets/delete":
            slug = safe_slug(body.get("slug"))
            if not slug:
                self._send_json({"success": False, "error": "Missing or invalid slug"}, 400)
                return

            target_dir = os.path.abspath(os.path.join(PETS_DIR, slug))
            if not target_dir.startswith(os.path.abspath(PETS_DIR)):
                self._send_json({"success": False, "error": "Access denied"}, 403)
                return

            if os.path.exists(target_dir):
                cfg = load_config()
                if cfg.get("current_pet") == slug:
                    all_pets = [p for p in get_available_pets(PETS_DIR) if p.slug != slug]
                    cfg["current_pet"] = all_pets[0].slug if all_pets else "desk-otter--zihualiu1997"
                    save_config(cfg)
                shutil.rmtree(target_dir, ignore_errors=True)
                try:
                    os.utime(SETTINGS_FILE, None)
                except Exception:
                    pass
                self._send_json({"success": True, "active": cfg.get("current_pet")})
            else:
                self._send_json({"success": False, "error": "Pet not found"}, 404)
            return

        if path == "/api/settings":
            cfg = load_config()
            cfg.update(body)
            save_config(cfg)
            try:
                os.utime(SETTINGS_FILE, None)
            except Exception:
                pass
            self._send_json(cfg)
            return

        if path == "/api/catalog/download":
            slug = safe_slug(body.get("slug"))
            if not slug:
                self._send_json({"success": False, "error": "Missing or invalid slug"}, 400)
                return

            done_evt = threading.Event()
            res_holder = {}

            def _cb(success, s, err):
                res_holder["success"] = success
                res_holder["error"] = err
                done_evt.set()

            catalog.download_pet(slug, callback=_cb)
            done_evt.wait(timeout=25)
            self._send_json(res_holder or {"success": False, "error": "Timeout"})
            return

        if path == "/api/custom/import_zip":
            try:
                zip_data_url = body.get("zipData", "")
                filename = body.get("filename", "custom-pet.zip")
                if "," in zip_data_url:
                    b64 = zip_data_url.split(",")[1]
                else:
                    b64 = zip_data_url

                raw_zip = base64.b64decode(b64)
                fallback_name = os.path.splitext(filename)[0]
                result = pet_importer.import_zip_bytes(raw_zip, PETS_DIR, fallback_name)
                
                if result.get("success"):
                    # Automatically activate newly imported pet
                    cfg = load_config()
                    cfg["current_pet"] = result["slug"]
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

                # If ext is zip, route to import_zip
                if ext.lower() == ".zip":
                    if "," in file_data_url:
                        b64 = file_data_url.split(",")[1]
                    else:
                        b64 = file_data_url
                    raw_zip = base64.b64decode(b64)
                    result = pet_importer.import_zip_bytes(raw_zip, PETS_DIR, name)
                    if result.get("success"):
                        cfg = load_config()
                        cfg["current_pet"] = result["slug"]
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
                    # Automatically activate newly created pet
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

    # 1. Check if Antigravity Pet Hub window is already open
    existing_hwnd = None
    def enum_cb(hwnd, _):
        nonlocal existing_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Antigravity Pet Hub" in title:
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
            return
        except Exception:
            pass

    # 2. Open new instance if none was open
    url = f"http://127.0.0.1:{port}"
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if os.path.exists(edge_exe):
        try:
            subprocess.Popen([edge_exe, f"--app={url}", "--window-size=980,720"])
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
