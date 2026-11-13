import os
import sys
import json
import shutil

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = BUNDLE_DIR

CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
SETTINGS_FILE = CONFIG_FILE
PETS_DIR = os.path.join(CONFIG_DIR, "pets")

def get_asset_path(filename: str) -> str:
    """Resolve asset path checking next to exe first, then bundled data."""
    p_local = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(p_local):
        return p_local
    p_bundle = os.path.join(BUNDLE_DIR, filename)
    if os.path.exists(p_bundle):
        return p_bundle
    return p_local

def ensure_environment():
    """Ensure config directories and unpack bundled pets if running for first time."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(PETS_DIR, exist_ok=True)

    cfg = load_config()
    deleted_pets = set(cfg.get("deleted_pets", []))

    bundled_pets = os.path.join(BUNDLE_DIR, "pets")
    if os.path.exists(bundled_pets) and os.path.abspath(bundled_pets) != os.path.abspath(PETS_DIR):
        for item in os.listdir(bundled_pets):
            if item in deleted_pets:
                continue
            s_item = os.path.join(bundled_pets, item)
            d_item = os.path.join(PETS_DIR, item)
            if not os.path.exists(d_item):
                try:
                    if os.path.isdir(s_item):
                        shutil.copytree(s_item, d_item)
                    else:
                        shutil.copy2(s_item, d_item)
                except Exception:
                    pass

    # Ensure desktop and start menu shortcuts are wired with Ctrl+Alt+P hotkey
    try:
        sync_desktop_shortcut()
        if cfg.get("start_with_windows", False):
            sync_windows_startup(True)
        else:
            sync_windows_startup(False)
    except Exception:
        pass

DEFAULT_SHORTCUTS = {
    "toggle_pet": "Ctrl+Alt+P",
    "toggle_visibility": "Ctrl+Alt+H",
    "switch_pet": "Ctrl+Alt+N",
    "toggle_behavior": "Ctrl+Alt+B",
    "open_settings": "Ctrl+Alt+S"
}

DEFAULT_CONFIG = {
    "current_pet": "desk-otter--zihualiu1997", # Default to open-source community mascot
    "scale": 1.0,                              # 1.0 = sharp native 1:1 pixel rendering
    "behavior": "zero_g",                      # "zero_g", "roam", "static"
    "sound_enabled": True,
    "speech_enabled": True,
    "sync_with_antigravity": True,             # Only show pet when Antigravity is active
    "start_with_windows": False,               # Not launched on startup by default (user requests on-demand launch)
    "x": -1,                                   # -1 for smart bottom-right placement above taskbar
    "y": -1,
    "antigravity_path": os.path.join(
        os.environ.get("LOCALAPPDATA", r"C:\AppData\Local"),
        "Programs", "Antigravity", "Antigravity.exe"
    ),
    "always_on_top": True,
    "click_action": "launch_antigravity",
    "shortcuts": dict(DEFAULT_SHORTCUTS)
}

def normalize_wsh_hotkey(s: str) -> str:
    """Normalize a shortcut string for Windows Script Host (WScript.Shell).
    WSH requires no spaces, and typically Ctrl+Alt+Key or Ctrl+Shift+Key.
    Empty string clears the shortcut.
    """
    if not s or not s.strip():
        return ""
    parts = [p.strip() for p in s.replace("+", " ").split()]
    mods = []
    key = None
    for p in parts:
        u = p.upper()
        if u in ("CTRL", "CONTROL"):
            if "Ctrl" not in mods:
                mods.append("Ctrl")
        elif u in ("ALT", "MENU"):
            if "Alt" not in mods:
                mods.append("Alt")
        elif u in ("SHIFT",):
            if "Shift" not in mods:
                mods.append("Shift")
        else:
            key = p.upper()
    if not key:
        return ""
    if not mods:
        mods = ["Ctrl", "Alt"]
    return "+".join(mods + [key])

def sync_windows_startup(enable: bool = False, hotkey: str = None):
    """Register or unregister Antigravity Pet in Windows Startup folder."""
    try:
        import win32com.client
        startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        if not os.path.isdir(startup_dir):
            return
        shortcut_path = os.path.join(startup_dir, "Antigravity Pet.lnk")
        if enable:
            wsh = win32com.client.Dispatch("WScript.Shell")
            sc = wsh.CreateShortcut(shortcut_path)
            if getattr(sys, 'frozen', False):
                sc.TargetPath = sys.executable
                sc.Arguments = ""
                sc.WorkingDirectory = os.path.dirname(sys.executable)
                sc.IconLocation = f"{sys.executable},0"
            else:
                sc.TargetPath = "wscript.exe"
                sc.Arguments = f'"{os.path.join(CONFIG_DIR, "run_pet_hidden.vbs")}"'
                sc.WorkingDirectory = CONFIG_DIR
                sc.IconLocation = f"{os.path.join(CONFIG_DIR, 'icon.ico')},0"
            sc.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
            if hotkey is None:
                hotkey = load_config().get("shortcuts", {}).get("toggle_pet", "Ctrl+Alt+P")
            sc.Hotkey = normalize_wsh_hotkey(hotkey)
            sc.Save()
        else:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
    except Exception:
        pass

def _resolve_pythonw():
    venv_pyw = os.path.join(CONFIG_DIR, ".venv", "Scripts", "pythonw.exe")
    if os.path.exists(venv_pyw):
        return venv_pyw
    hermes_pyw = r"C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
    if os.path.exists(hermes_pyw):
        return hermes_pyw
    which_pyw = shutil.which("pythonw")
    if which_pyw:
        return which_pyw
    return sys.executable

def sync_desktop_shortcut(hotkey: str = None):
    """Ensure Desktop and Start Menu Programs shortcuts have global hotkey configured."""
    try:
        import win32com.client
        wsh = win32com.client.Dispatch("WScript.Shell")

        if getattr(sys, 'frozen', False):
            target_path = sys.executable
            target_args = ""
            work_dir = os.path.dirname(sys.executable)
            icon_loc = f"{sys.executable},0"
        else:
            target_path = "wscript.exe"
            target_args = f'"{os.path.join(CONFIG_DIR, "run_pet_hidden.vbs")}"'
            work_dir = CONFIG_DIR
            icon_loc = f"{os.path.join(CONFIG_DIR, 'icon.ico')},0"

        if hotkey is None:
            hotkey = load_config().get("shortcuts", {}).get("toggle_pet", "Ctrl+Alt+P")
        wsh_hotkey = normalize_wsh_hotkey(hotkey)

        # 1. Desktop shortcut
        desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        if os.path.isdir(desktop_dir):
            shortcut_path = os.path.join(desktop_dir, "Antigravity Pet.lnk")
            sc = wsh.CreateShortcut(shortcut_path)
            sc.TargetPath = target_path
            sc.Arguments = target_args
            sc.WorkingDirectory = work_dir
            sc.IconLocation = icon_loc
            sc.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
            sc.Hotkey = wsh_hotkey
            sc.Save()

        # 2. Start Menu Programs shortcut
        sm_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        if os.path.isdir(sm_dir):
            sm_shortcut_path = os.path.join(sm_dir, "Antigravity Pet.lnk")
            sc_sm = wsh.CreateShortcut(sm_shortcut_path)
            sc_sm.TargetPath = target_path
            sc_sm.Arguments = target_args
            sc_sm.WorkingDirectory = work_dir
            sc_sm.IconLocation = icon_loc
            sc_sm.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
            sc_sm.Hotkey = wsh_hotkey
            sc_sm.Save()

        # 3. Notify Windows Shell
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        except Exception:
            pass
    except Exception:
        pass

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(cfg)
                # Ensure shortcuts dictionary has all defaults populated
                sc = dict(DEFAULT_SHORTCUTS)
                if isinstance(cfg.get("shortcuts"), dict):
                    sc.update(cfg["shortcuts"])
                merged["shortcuts"] = sc
                return merged
        except Exception as e:
            print(f"Error loading config: {e}")
    merged = dict(DEFAULT_CONFIG)
    merged["shortcuts"] = dict(DEFAULT_SHORTCUTS)
    return merged

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")
