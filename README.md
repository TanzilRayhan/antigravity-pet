# 🪐 Antigravity Desktop Pet

<p align="center">
  <img src="logo.png" width="96" height="96" alt="Antigravity Pet Logo" />
</p>

<p align="center">
  <strong>An ultra-low-latency, zero-CPU interactive desktop companion for Google Antigravity 2.0.</strong><br>
  Built with native Win32 layered hardware composition, full <a href="https://codexpets.net/">Codex Pets</a> compatibility, and real-time task progress monitoring.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?logo=windows" alt="Platform: Windows" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Architecture-x64-informational" alt="x64" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT" />
</p>

> [!NOTE]
> **Disclaimer:** Antigravity Desktop Pet is an independent, community-driven open-source companion project. It is not affiliated with, maintained by, or endorsed by Google, Google DeepMind, or OpenAI. All product names, logos, and brands are property of their respective owners.

---

## ✨ Features & Highlights

- **⚡ Zero-CPU Hardware Translation:**
  Dragging the pet across multi-monitor setups uses native Win32 hardware window translation (`user32.SetWindowPos`), completely bypassing software re-rendering. Even with 1000 Hz gaming mice, CPU usage remains at **0.0%** and CPU temperatures stay cool (50–60°C).

- **🧘 Distraction-Free Stillness on Idle:**
  When you are coding or working, the mascot remains perfectly calm and stationary (frame 0 with a soft feathered ground shadow). Expressive animations, jumps, and reactions activate **only when you hover or drag**.

- **🪄 Floating Action Dock (Revealed on Hover):**
  - **`[ ✎ ]` New Conversation:** Brings Antigravity 2.0 to front and initiates a fresh, new conversation session directly inside the canvas.
  - **`[ ||| ]` Voice Conversation:** Opens a new conversation, focuses the message input, and automatically triggers **Windows Voice Dictation** (`Win + H`) so you can speak hands-free.
  - **`[ 🔔 ]` Live Task Bell (Hidden when Idle):** Automatically appears with a glowing emerald indicator only when an Antigravity task is actively executing. Click it to read a real-time prompt summary parsed live from the active session transcript!

- **🖱️ Double-Click Pet to Restore / Minimize:**
  Double-clicking the pet mascot acts as an instant shortcut: restores Antigravity if minimized or in the background, and minimizes Antigravity if already focused in the foreground.

- **🔒 Antigravity Process Auto-Sync:**
  The pet companion automatically wakes up and appears when Antigravity 2.0 launches, and quietly hides itself when Antigravity closes so your screen is never cluttered.

- **⌨️ Global Show / Hide Hotkeys:**
  Press **`Ctrl + Alt + P`** or **`Win + Alt + P`** from any application or full-screen game to toggle the pet on and off on demand.

- **🐾 10+ Pre-Installed Companions:**
  Preloaded with high-resolution pixel art and vector characters:
  - **Gigimon** & **Guilmon** (Digimon digital monsters)
  - **Makima** (Chainsaw Man chibi companion)
  - **Agumon** (Classic dinosaur companion)
  - **Behemoth** (Fantasy creature companion)
  - **Chud Codex** (Grimdark sci-fi chibi)
  - **Claude** (Orange blocky AI companion)
  - **CodeNoNo** (Floating cyber robot with cyan screen face)
  - **Codex Orb** (Rainbow-rimmed floating eye)
  - **Desk Otter** (Spectacled coding mascot)

- **🌐 In-App Pet Hub & Downloader:**
  Includes a local web dashboard (`http://127.0.0.1:54321`) to browse and 1-click download 370+ pets from [CodexPets.net](https://codexpets.net/) or drag-and-drop custom ZIP files / GIFs.

- **📦 Standalone Portable Executable:**
  Packaged as a standalone single `AntigravityPet.exe` with zero installation and zero Python runtime required.

---

## 🎮 Controls & Shortcuts

| Action | Shortcut / Trigger | Behavior |
| :--- | :--- | :--- |
| **Restore / Minimize App** | **Double-Click Pet** | Restores Antigravity to foreground or minimizes it |
| **Global Toggle** | **`Ctrl + Alt + P`** or **`Win + Alt + P`** | Instantly show / hide pet across any window |
| **Move Mascot** | **Left-Click & Drag** | Drag pet anywhere across multiple displays (0% CPU) |
| **New Conversation** | **Hover $\rightarrow$ Click `[ ✎ ]`** | Opens brand new conversation in Antigravity |
| **Voice Mode** | **Hover $\rightarrow$ Click `[ \|\|\| ]`** | Starts new chat & activates Voice Dictation (`Win + H`) |
| **View Active Task** | **Hover $\rightarrow$ Click `[ 🔔 ]`** | Displays real-time task prompt bubble (when active) |
| **Quick Menu** | **Right-Click Mascot** | Settings, Hide Mini, Switch Pet, Exit |
| **System Tray** | **Taskbar Notification Area** | Tray icon to toggle, configure, or quit the companion |

---

## 🚀 Quick Start

### Option A: Portable Standalone Executable (Recommended)

1. Download the latest **`AntigravityPet-v2.0-Portable.zip`** or **`AntigravityPet.exe`** from [Releases](https://github.com/TanzilRayhan/antigravity-pet/releases).
2. Extract the archive and double-click **`AntigravityPet.exe`**.
3. *(Optional)* Run `Create-Desktop-Shortcut.bat` or `Enable-Run-On-Startup.bat` for one-click launch!

### Option B: Run from Source (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TanzilRayhan/antigravity-pet.git
   cd antigravity-pet
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the pet:**
   ```bash
   python main.py
   ```

---

## 🛠️ Architecture & Performance

```mermaid
flowchart TD
    User["Mouse / Keyboard Interaction"] --> PetWin["AntigravityPetWindow (Layered Win32 HWND)"]
    PetWin -->|"Drag Event"| HWMove["user32.SetWindowPos (0% CPU / DWM Compositor)"]
    PetWin -->|"Frame Tick (8 FPS)"| FastAlpha["ImageChops (Compiled C Premultiplied Alpha)"]
    PetWin -->|"Double Click"| Launcher["antigravity_launcher.py (Toggle Window)"]
    PetWin -->|"Click Pen / Voice"| CDP["Chrome DevTools Protocol (New Conversation Trigger)"]
    PetWin -->|"1.0s Polling"| TaskMon["task_monitor.py (Transcript Status)"]
    TaskMon -->|"Active Task"| Dock["Dynamic Dock (Pill reveals Bell with live summary)"]
    TaskMon -->|"Idle"| CompactDock["Compact Dock (Bell Hidden)"]
    PetWin -->|"Right Click -> Settings"| HubServer["hub_server.py (Web Hub at :54321)"]
```

### Key Performance Innovations:
- **Compiled C Alpha Multiplication:** Uses Pillow's C-accelerated `ImageChops.multiply` for 32-bit BGRA premultiplication, taking **~1.5 ms** per frame instead of 25 ms pure Python bytecode loops.
- **Hardware-composited layered windows:** Leverages Windows Desktop Window Manager (DWM) surfaces to move layered windows with hardware acceleration, preventing CPU voltage/temperature spikes on modern high-boost CPUs (e.g. AMD Ryzen 9000 Zen 5).
- **Direct Chrome DevTools Protocol (CDP) Bridge:** Communicates deterministically with Antigravity's active runtime port (`DevToolsActivePort`) to click UI elements and focus chat inputs instantly.

---

## 🎨 Adding Custom Pets

You can add custom pets in three easy ways:

1. **In-App Downloader:** Right-click pet $\rightarrow$ **Settings** $\rightarrow$ **Browse Gallery** $\rightarrow$ click **Download** on any companion from the 370+ CodexPets library.
2. **ZIP / GIF Import:** In **Settings** $\rightarrow$ **Custom Pet Creator**, drag and drop any `.zip` or `.gif` file to convert and install automatically.
3. **Manual Folder:** Drop any standard Codex Pet folder (containing `pet.json` and `pet.png`) directly into the `pets/` directory.

### Codex Pet Format Support:
Supports both **V1** (8 columns $\times$ 9 rows, 192 $\times$ 208 px) and **V2** (8 columns $\times$ 11 rows) sprite sheets with complete state mappings (`idle`, `running`, `jumping`, `waving`, `waiting`, `review`, `failed`).

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 💖 Acknowledgements & Community

- Built with pair programming on **Google Antigravity 2.0**.
- Inspired by the [Codex Desktop Pet](https://codexpets.net/) and the [awesome-codex-pet](https://github.com/legeling/awesome-codex-pet) community catalog.
