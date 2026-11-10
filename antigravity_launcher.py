import os
import subprocess
import time
import json
import urllib.request
import asyncio
import ctypes
import win32gui
import win32con
import win32process
import win32api
import psutil

try:
    import websockets
except ImportError:
    websockets = None

LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
DEFAULT_ANTIGRAVITY_PATH = os.path.join(LOCALAPPDATA, "Programs", "Antigravity", "Antigravity.exe") if LOCALAPPDATA else ""
ALT_AGY_PATH = os.path.join(LOCALAPPDATA, "agy", "bin", "agy.exe") if LOCALAPPDATA else ""

user32 = ctypes.windll.user32

def _ensure_desktop_access():
    try:
        h_def = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_def:
            user32.SetThreadDesktop(h_def)
    except Exception:
        pass

def is_antigravity_running():
    """Check if Antigravity desktop app process is currently running."""
    for proc in psutil.process_iter(['name']):
        try:
            name = (proc.info['name'] or '').lower()
            if 'antigravity' in name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def find_antigravity_windows():
    """Find visible or top-level main windows belonging to Antigravity."""
    _ensure_desktop_access()
    matching_hwnds = []
    
    target_pids = set()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = (proc.info['name'] or '').lower()
            if 'antigravity' in name:
                target_pids.add(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def enum_cb(hwnd, _):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid in target_pids:
            cls = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            # Match Electron main window
            if cls == "Chrome_WidgetWin_1" and w > 200 and h > 200:
                matching_hwnds.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
        
    return matching_hwnds

def launch_antigravity(custom_path=None):
    """Bring existing Antigravity window to front or launch a new instance."""
    _ensure_desktop_access()
    windows = find_antigravity_windows()
    if windows:
        hwnd, title = windows[0]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            pass

    path = custom_path or DEFAULT_ANTIGRAVITY_PATH
    if os.path.exists(path):
        try:
            os.startfile(path)
            return True
        except Exception:
            pass
    return False

def toggle_antigravity_window():
    """
    Toggle Antigravity window between Restored (foreground) and Minimized.
    If Antigravity is minimized or not in foreground -> Restores and brings to front.
    If Antigravity is currently in the foreground -> Minimizes it.
    """
    _ensure_desktop_access()
    windows = find_antigravity_windows()
    if windows:
        hwnd, title = windows[0]
        fg = win32gui.GetForegroundWindow()
        is_min = win32gui.IsIconic(hwnd) or not win32gui.IsWindowVisible(hwnd)

        if is_min or fg != hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return "restored"
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return "minimized"
    else:
        launch_antigravity()
        return "launched"

def _trigger_cdp_new_conversation():
    """
    Connects to Antigravity's embedded Chrome DevTools Protocol to directly
    click the 'New Conversation' button and focus the chat input.
    """
    if not websockets:
        return False
    try:
        port_file = os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort")
        if not os.path.exists(port_file):
            return False
        with open(port_file, "r") as f:
            port = f.readline().strip()
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.urlopen(url, timeout=1.5)
        pages = json.loads(req.read().decode('utf-8'))
        target = next((p for p in pages if p.get("type") == "page" and "Antigravity" in p.get("title", "")), None)
        if not target or "webSocketDebuggerUrl" not in target:
            return False
        
        ws_url = target["webSocketDebuggerUrl"]
        
        async def _run():
            async with websockets.connect(ws_url, close_timeout=1.5) as ws:
                script = """
                (() => {
                    const btn = document.querySelector('[data-testid="new-conversation-button"]') ||
                                Array.from(document.querySelectorAll('a, button')).find(x => x.innerText.trim() === 'New Conversation');
                    if (btn) {
                        btn.click();
                        setTimeout(() => {
                            const input = document.querySelector('[aria-label="Message input"]');
                            if (input) input.focus();
                        }, 120);
                        return true;
                    }
                    window.location.href = '/';
                    return true;
                })()
                """
                msg = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": script, "returnByValue": True}}
                await ws.send(json.dumps(msg))
                resp = await ws.recv()
                data = json.loads(resp)
                return bool(data.get("result", {}).get("result", {}).get("value"))
        
        return asyncio.run(_run())
    except Exception:
        return False

def open_antigravity_new_chat(voice_mode=False):
    """
    Brings Antigravity to front and initiates a fresh NEW conversation.
    If voice_mode is True, additionally activates Windows Voice Typing (Win + H).
    """
    _ensure_desktop_access()
    launch_antigravity()
    
    time.sleep(0.12)
    
    # Try CDP direct click for 100% deterministic new conversation
    cdp_success = _trigger_cdp_new_conversation()
    
    if not cdp_success:
        # Fallback keyboard navigation: Ctrl+Shift+L / Ctrl+N
        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        VK_L = 0x4C
        VK_N = 0x4E

        # Send Ctrl + Shift + L
        win32api.keybd_event(VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(VK_SHIFT, 0, 0, 0)
        win32api.keybd_event(VK_L, 0, 0, 0)
        win32api.keybd_event(VK_L, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        time.sleep(0.08)
        # Send Ctrl + N
        win32api.keybd_event(VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(VK_N, 0, 0, 0)
        win32api.keybd_event(VK_N, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

    if voice_mode:
        # Wait a moment for input focus, then trigger Windows Voice Typing (Win + H)
        time.sleep(0.25)
        VK_LWIN = 0x5B
        VK_H = 0x48
        win32api.keybd_event(VK_LWIN, 0, 0, 0)
        win32api.keybd_event(VK_H, 0, 0, 0)
        win32api.keybd_event(VK_H, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)

    return True
