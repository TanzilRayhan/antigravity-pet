import sys
import os
import time
import ctypes
from ctypes import wintypes

# 1. Immediately hide any console window so no terminal window flashes
try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    h_con = kernel32.GetConsoleWindow()
    if h_con:
        user32.ShowWindow(h_con, 0)  # SW_HIDE
except Exception:
    pass

# Redirect null stdout/stderr for windowless execution
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
import win32gui
import win32con
import win32process
import psutil

# Set DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(PROJECT_ROOT, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import ensure_environment, CONFIG_DIR
from pet_window import AntigravityPetWindow
from hub_server import start_hub_background_server, open_hub_app

MUTEX_NAME = "Global\\AntigravityPet_SingleInstance_Mutex_v2"
ERROR_ALREADY_EXISTS = 183
WM_PET_ENSURE_SHOW = user32.RegisterWindowMessageW("AntigravityPet_EnsureShowMsg")
WM_PET_SHOW = user32.RegisterWindowMessageW("AntigravityPet_ShowMsg")

def check_recent_exit_marker() -> bool:
    try:
        marker_path = os.path.join(CONFIG_DIR, ".pet_exit_marker")
        if os.path.exists(marker_path):
            with open(marker_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                ts = float(content)
                diff = time.time() - ts
                if 0.0 <= diff < 3.5:
                    return True
    except Exception:
        pass
    return False

def main():
    parser = argparse.ArgumentParser(description="Antigravity Desktop Pet Companion")
    parser.add_argument("--manager", action="store_true", help="Open Pet Hub & Codex Gallery")
    parser.add_argument("--pet", type=str, default=None, help="Initial pet slug (e.g. gigimon, guilmon, ordis, antigrav)")
    parser.add_argument("--scale", type=float, default=None, help="Pet scale factor (0.4 - 1.5)")
    args = parser.parse_args()

    if args.manager:
        start_hub_background_server(54321)
        open_hub_app(54321)
        return

    # Check if this process was launched as a delayed byproduct of the exit shortcut
    if check_recent_exit_marker():
        return

    # 1. Strict single-instance check via Named Mutex
    h_mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # Another instance is already running! Signal it to ensure it is visible and exit immediately.
        user32.PostMessageW(0xFFFF, WM_PET_ENSURE_SHOW, 0, 0)
        try:
            h_win = win32gui.FindWindow("AntigravityPetWindowLayered", None)
            if h_win:
                user32.PostMessageW(h_win, WM_PET_ENSURE_SHOW, 0, 0)
        except Exception:
            pass
        return

    ensure_environment()

    # Ensure interactive Default desktop access
    try:
        h_def = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_def:
            user32.SetThreadDesktop(h_def)
    except Exception:
        pass

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
    finally:
        if h_mutex:
            kernel32.CloseHandle(h_mutex)

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
