# Antigravity 2.0 Desktop Pet — Sharing & Distribution Guide

This guide explains how to share, package, and distribute the **Antigravity Desktop Pet Companion** to friends, teammates, or any Windows machine.

---

## 🚀 Quick Summary: Features & Highlights

- **Codex-Style Floating Companion**: Native Windows layered window with per-monitor High-DPI awareness (100% sharp rendering, no pixelation or blur).
- **Interactive Pill Dock**:
  - `[ ✎ Write ]`: Focuses Antigravity prompt or brings Antigravity 2.0 window to the front.
  - `[ ||| Voice ]`: Plays audio chime and triggers voice input mode.
  - `[ 🔔 Tasks ]`: Notification bell with active running indicator dot that toggles a conversation summary chat bubble.
- **Sleek Context Menu (Right-Click)**: Opens **below** the pet (never covers the mascot) with Windows 11 Fluent icons:
  - `⚙ Settings`: Opens the Web App Hub in Edge App mode.
  - `👁 Hide Mini`: Hides pet (toggle back anytime via `Ctrl+Alt+P` or tray icon).
  - `🔄 Switch Pet`: Quickly cycles through installed mascots.
  - `✕ Exit`: Closes the companion cleanly.
- **Web Hub & Codex Gallery (`http://127.0.0.1:54321`)**:
  - **My Pets**: View installed pets, switch active pet instantly, or delete unwanted pets.
  - **Codex Gallery**: Browse and one-click download 370+ community pets from codexpets.net.
  - **DIY Pet Maker**: Drag & drop `.zip` files (from codexpets.net/GitHub) or upload animated GIFs / images to auto-synthesize an 8x9 animation atlas!
  - **Real-Time Settings**: Immediate slider scaling (40% - 150%), Zero-G hover physics, sound toggle, and Antigravity auto-sync.
- **Global Hotkeys**: `Ctrl + Alt + P` and `Win + Alt + P` anywhere in Windows.

---

## 📦 Method 1: Portable Folder Sharing (Recommended)

Share the companion as a clean portable folder.

### Step 1: Package the Folder
1. Open your cloned repository folder:
   ```
   antigravity-pet/
   ```
2. Make sure the folder contains:
   - `main.py`, `pet_window.py`, `ui_renderer.py`, `hub_server.py`, `pet_loader.py`, `pet_importer.py`, `theme.py`, `sound.py`, `config.py`, `antigravity_launcher.py`, `downloader.py`
   - `pets/` folder (with `gigimon`, `guilmon`, `ordis`, `antigrav`)
   - `icon.ico`
   - `run_pet.bat` (Console launcher)
   - `run_pet_hidden.vbs` (Silent background launcher)
   - `install_shortcut.ps1` (Desktop shortcut installer)
   - `install_startup.ps1` (Windows Startup installer)
   - `requirements.txt`
3. Right-click the `antigravity-pet` folder -> **Send to** -> **Compressed (zipped) folder** (e.g. `AntigravityPet-v2.zip`).

### Step 2: Recipient Setup (Takes 30 seconds)
Send `AntigravityPet-v2.zip` to your recipient. They only need:
1. Extract the zip to any folder (e.g. `C:\AntigravityPet` or their Desktop).
2. If they have Python 3.9+ installed:
   Open Command Prompt in that folder and run:
   ```cmd
   pip install -r requirements.txt
   ```
3. Right-click `install_shortcut.ps1` -> **Run with PowerShell** (creates "Antigravity Pet" shortcut on their Desktop).
4. Double-click the desktop shortcut to start!

---

## ⚡ Method 2: Standalone Single `.exe` (Zero Python Needed)

To share with non-developers who don't have Python installed, compile into a single `.exe`:

### Step 1: Install PyInstaller
```powershell
pip install pyinstaller
```

### Step 2: Build the Executable
Run the following build command in the `antigravity-pet` directory:
```powershell
pyinstaller --noconsole --onefile `
  --icon="icon.ico" `
  --name="AntigravityPet" `
  --add-data="pets;pets" `
  --add-data="icon.ico;." `
  --hidden-import="PIL" `
  --hidden-import="win32gui" `
  --hidden-import="win32con" `
  --hidden-import="psutil" `
  main.py
```

### Step 3: Distribute
The single executable is created in `dist\AntigravityPet.exe`.
Anyone can double-click `AntigravityPet.exe` and it will run instantly with zero dependencies!

---

## 🔄 Method 3: Autostart with Windows

To have the pet launch automatically when Windows boots (and stay hidden until Antigravity is opened):

1. Open PowerShell and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "install_startup.ps1"
   ```
2. This creates a startup shortcut in `shell:startup`.
3. To remove from startup:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "remove_startup.ps1"
   ```

---

## 🎨 How Users Add & Customize Pets

1. **Codex Pets Gallery Tab**:
   - Right-click the pet -> click **Settings** (or open `http://127.0.0.1:54321`).
   - Go to the **Codex Gallery** tab.
   - Search for any character (e.g. "Cat", "Digimon", "Anya", "Robot", "Pokemon").
   - Click **Download & Install**. The pet is ready immediately!

2. **Drag & Drop ZIP Import**:
   - Download any pet zip file from [CodexPets.net](https://codexpets.net/) or GitHub.
   - Drag and drop the `.zip` file directly onto the DIY Pet Maker tab.
   - It will automatically unpack, validate, and set the character active!

3. **Convert GIF or Image**:
   - Upload any animated GIF or picture in the **DIY Pet Maker** tab.
   - The built-in converter automatically slices and synthesizes an 8x9 animation grid with idle, walk, jump, and thinking states!
