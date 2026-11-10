import sys
import os

# Redirect null stdout/stderr for pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import argparse
import ctypes
from ctypes import wintypes
import win32gui
import win32con

# Set DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ensure_environment
from pet_window import AntigravityPetWindow
from hub_server import start_hub_background_server, open_hub_app

def main():
    ensure_environment()
    parser = argparse.ArgumentParser(description="Antigravity Desktop Pet Companion")
    parser.add_argument("--manager", action="store_true", help="Open Pet Hub & Codex Gallery")
    parser.add_argument("--pet", type=str, default=None, help="Initial pet slug (e.g. gigimon, guilmon, ordis, antigrav)")
    parser.add_argument("--scale", type=float, default=None, help="Pet scale factor (0.4 - 1.5)")
    args = parser.parse_args()

    if args.manager:
        start_hub_background_server(54321)
        open_hub_app(54321)
        return

    print("=" * 60)
    print("Starting Antigravity Desktop Pet Companion...")
    print("   * Pill Dock: [ ✎ Write | ||| Voice | 🔔 Tasks ]")
    print("   * Context Menu: Settings, Hide Mini, Switch Pet, Exit")
    print("   * Global Hotkey: Ctrl + Alt + P or Win + Alt + P")
    print("=" * 60)

    pet_window = AntigravityPetWindow()

    if args.pet:
        pet_window.change_pet(args.pet)
    if args.scale:
        pet_window.change_scale(args.scale)

    # Windows message loop
    try:
        win32gui.PumpMessages()
    except (KeyboardInterrupt, SystemExit):
        pass

def _log_crash():
    import traceback
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log"), "a", encoding="utf-8") as f:
        traceback.print_exc(file=f)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log_crash()
        raise
