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

    bundled_pets = os.path.join(BUNDLE_DIR, "pets")
    if os.path.exists(bundled_pets) and os.path.abspath(bundled_pets) != os.path.abspath(PETS_DIR):
        for item in os.listdir(bundled_pets):
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

DEFAULT_CONFIG = {
    "current_pet": "desk-otter--zihualiu1997", # Default to open-source community mascot
    "scale": 1.0,                              # 1.0 = sharp native 1:1 pixel rendering
    "behavior": "zero_g",                      # "zero_g", "roam", "static"
    "sound_enabled": True,
    "speech_enabled": True,
    "sync_with_antigravity": True,             # Only show pet when Antigravity is active
    "x": -1,                                   # -1 for smart bottom-right placement above taskbar
    "y": -1,
    "antigravity_path": os.path.join(
        os.environ.get("LOCALAPPDATA", r"C:\AppData\Local"),
        "Programs", "Antigravity", "Antigravity.exe"
    ),
    "always_on_top": True,
    "click_action": "launch_antigravity"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(cfg)
                return merged
        except Exception as e:
            print(f"Error loading config: {e}")
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")
