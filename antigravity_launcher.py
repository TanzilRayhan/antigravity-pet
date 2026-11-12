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
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
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

def _get_cdp_ws_url():
    """Locate the active Antigravity main window CDP websocket debugger URL."""
    if not websockets:
        return None
    try:
        port_file = os.path.expandvars(r"%APPDATA%\Antigravity\DevToolsActivePort")
        if not os.path.exists(port_file):
            return None
        with open(port_file, "r") as f:
            port = f.readline().strip()
        url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.urlopen(url, timeout=1.5)
        pages = json.loads(req.read().decode('utf-8'))
        # Pick the primary Antigravity web UI page (excluding data: splash and iframes)
        for p in pages:
            u = p.get("url", "")
            if p.get("type") == "page" and ("127.0.0.1" in u or "localhost" in u) and not u.startswith("data:"):
                return p.get("webSocketDebuggerUrl")
        # Fallback to any page target
        for p in pages:
            if p.get("type") == "page" and "webSocketDebuggerUrl" in p:
                return p.get("webSocketDebuggerUrl")
        return None
    except Exception:
        return None

def _trigger_cdp_new_conversation():
    """
    Connects to Antigravity's embedded Chrome DevTools Protocol to directly
    open a brand new conversation and focus the chat input.
    """
    ws_url = _get_cdp_ws_url()
    if not ws_url:
        return False
    try:
        async def _run():
            async with websockets.connect(ws_url, close_timeout=2.0) as ws:
                script = """
                (() => {
                    const clickEl = (el) => {
                        if (!el) return false;
                        const opts = { bubbles: true, cancelable: true, view: window };
                        el.dispatchEvent(new PointerEvent('pointerdown', opts));
                        el.dispatchEvent(new MouseEvent('mousedown', opts));
                        el.dispatchEvent(new PointerEvent('pointerup', opts));
                        el.dispatchEvent(new MouseEvent('mouseup', opts));
                        el.dispatchEvent(new MouseEvent('click', opts));
                        
                        const propsKey = Object.keys(el).find(k => k.startsWith('__reactProps$'));
                        const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
                        if (propsKey && el[propsKey] && typeof el[propsKey].onClick === 'function') {
                            el[propsKey].onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        } else if (fiberKey && el[fiberKey] && el[fiberKey].memoizedProps && typeof el[fiberKey].memoizedProps.onClick === 'function') {
                            el[fiberKey].memoizedProps.onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        }
                        if (typeof el.click === 'function') el.click();
                        return true;
                    };

                    const btn = document.querySelector('[data-testid="app-icon-new-conversation-button"]') ||
                                document.querySelector('button[aria-label="New Conversation"]') ||
                                document.querySelector('[data-testid="new-conversation-button"]') ||
                                Array.from(document.querySelectorAll('button, a')).find(x => (x.innerText || '').trim() === 'New Conversation');

                    if (btn) {
                        clickEl(btn);
                        const r = btn.getBoundingClientRect();
                        return { success: true, coords: (r.width > 0 && r.height > 0) ? { x: r.left + r.width/2, y: r.top + r.height/2 } : null };
                    }

                    // Direct navigation fallback to fresh conversation URL
                    const proj = new URLSearchParams(window.location.search).get('project');
                    window.location.href = proj ? `/?project=${proj}` : '/';
                    return { success: true, navigated: true };
                })()
                """
                msg = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": script, "returnByValue": True}}
                await ws.send(json.dumps(msg))
                resp = await ws.recv()
                data = json.loads(resp)
                val = data.get("result", {}).get("result", {}).get("value") or {}
                
                if val.get('coords'):
                    c = val['coords']
                    await ws.send(json.dumps({'id': 2, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mousePressed', 'x': c['x'], 'y': c['y'], 'button': 'left', 'clickCount': 1}}))
                    await ws.recv()
                    await ws.send(json.dumps({'id': 3, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mouseReleased', 'x': c['x'], 'y': c['y'], 'button': 'left', 'clickCount': 1}}))
                    await ws.recv()

                # Focus prompt input
                await asyncio.sleep(0.12)
                focus_script = """
                (() => {
                    const input = document.querySelector('[aria-label="Message input"]') ||
                                  document.querySelector('textarea') ||
                                  document.querySelector('[contenteditable="true"]');
                    if (input) {
                        input.focus();
                        return true;
                    }
                    return false;
                })()
                """
                await ws.send(json.dumps({"id": 4, "method": "Runtime.evaluate", "params": {"expression": focus_script, "returnByValue": True}}))
                await ws.recv()

                return bool(val.get("success"))
        
        return asyncio.run(_run())
    except Exception:
        return False

def _trigger_cdp_voice_mode():
    """
    Connects to Antigravity's embedded Chrome DevTools Protocol to directly
    open a brand NEW conversation and activate native Voice Mode (Gemini Live).
    """
    ws_url = _get_cdp_ws_url()
    if not ws_url:
        return False
    try:
        async def _run():
            async with websockets.connect(ws_url, close_timeout=3.0) as ws:
                # Step 1: Open New Conversation first
                script_new = """
                (() => {
                    const clickEl = (el) => {
                        if (!el) return false;
                        const opts = { bubbles: true, cancelable: true, view: window };
                        el.dispatchEvent(new PointerEvent('pointerdown', opts));
                        el.dispatchEvent(new MouseEvent('mousedown', opts));
                        el.dispatchEvent(new PointerEvent('pointerup', opts));
                        el.dispatchEvent(new MouseEvent('mouseup', opts));
                        el.dispatchEvent(new MouseEvent('click', opts));
                        
                        const propsKey = Object.keys(el).find(k => k.startsWith('__reactProps$'));
                        const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
                        if (propsKey && el[propsKey] && typeof el[propsKey].onClick === 'function') {
                            el[propsKey].onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        } else if (fiberKey && el[fiberKey] && el[fiberKey].memoizedProps && typeof el[fiberKey].memoizedProps.onClick === 'function') {
                            el[fiberKey].memoizedProps.onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        }
                        if (typeof el.click === 'function') el.click();
                        return true;
                    };

                    const btn = document.querySelector('[data-testid="app-icon-new-conversation-button"]') ||
                                document.querySelector('button[aria-label="New Conversation"]') ||
                                document.querySelector('[data-testid="new-conversation-button"]');
                    if (btn) {
                        clickEl(btn);
                        return true;
                    }
                    return false;
                })()
                """
                await ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': script_new, 'returnByValue': True}}))
                await ws.recv()

                await asyncio.sleep(0.25)

                # Step 2: Trigger Voice Mode
                script_voice = """
                (() => {
                    const clickEl = (el) => {
                        if (!el) return false;
                        const opts = { bubbles: true, cancelable: true, view: window };
                        el.dispatchEvent(new PointerEvent('pointerdown', opts));
                        el.dispatchEvent(new MouseEvent('mousedown', opts));
                        el.dispatchEvent(new PointerEvent('pointerup', opts));
                        el.dispatchEvent(new MouseEvent('mouseup', opts));
                        el.dispatchEvent(new MouseEvent('click', opts));
                        
                        const propsKey = Object.keys(el).find(k => k.startsWith('__reactProps$'));
                        const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber$'));
                        if (propsKey && el[propsKey] && typeof el[propsKey].onClick === 'function') {
                            el[propsKey].onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        } else if (fiberKey && el[fiberKey] && el[fiberKey].memoizedProps && typeof el[fiberKey].memoizedProps.onClick === 'function') {
                            el[fiberKey].memoizedProps.onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        }
                        if (typeof el.click === 'function') el.click();
                        return true;
                    };

                    // Check if Voice Picker Modal ("Use Fola") is open
                    const pickerUse = document.querySelector('[data-testid="voice-picker-use"]');
                    if (pickerUse) {
                        clickEl(pickerUse);
                        return { action: 'confirmed_picker' };
                    }

                    const vBtn = document.querySelector('[data-testid="voice-start-button"]') ||
                                 document.querySelector('[aria-label="Start Voice mode"]');
                    if (vBtn) {
                        // Fiber traversal to invoke onStart() directly
                        const fk = Object.keys(vBtn).find(x => x.startsWith('__reactFiber$'));
                        let fiber = vBtn[fk];
                        while (fiber) {
                            if (fiber.memoizedProps && typeof fiber.memoizedProps.onStart === 'function') {
                                try {
                                    fiber.memoizedProps.onStart();
                                    return { action: 'called_onstart' };
                                } catch (e) {}
                            }
                            fiber = fiber.return;
                        }

                        // Props onClick fallback
                        const pk = Object.keys(vBtn).find(x => x.startsWith('__reactProps$'));
                        if (pk && vBtn[pk] && typeof vBtn[pk].onClick === 'function') {
                            vBtn[pk].onClick({ preventDefault: () => {}, stopPropagation: () => {} });
                        }
                        clickEl(vBtn);
                        const r = vBtn.getBoundingClientRect();
                        return { action: 'clicked_button', coords: (r.width > 0 && r.height > 0) ? { x: r.left + r.width/2, y: r.top + r.height/2 } : null };
                    }
                    return { action: 'not_found' };
                })()
                """
                await ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': script_voice, 'returnByValue': True}}))
                resp2 = await ws.recv()
                data2 = json.loads(resp2)
                v_res = data2.get("result", {}).get("result", {}).get("value") or {}
                
                if v_res.get('coords'):
                    c = v_res['coords']
                    await ws.send(json.dumps({'id': 3, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mousePressed', 'x': c['x'], 'y': c['y'], 'button': 'left', 'clickCount': 1}}))
                    await ws.recv()
                    await ws.send(json.dumps({'id': 4, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mouseReleased', 'x': c['x'], 'y': c['y'], 'button': 'left', 'clickCount': 1}}))
                    await ws.recv()

                # Step 3: Check if Voice Picker Modal appeared ("Use Fola") and confirm it
                await asyncio.sleep(0.3)
                confirm_script = """
                (() => {
                    const pickerUse = document.querySelector('[data-testid="voice-picker-use"]');
                    if (pickerUse) {
                        const opts = { bubbles: true, cancelable: true, view: window };
                        pickerUse.dispatchEvent(new MouseEvent('click', opts));
                        pickerUse.click();
                        return true;
                    }
                    return false;
                })()
                """
                await ws.send(json.dumps({'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': confirm_script, 'returnByValue': True}}))
                await ws.recv()

                return True
        
        return asyncio.run(_run())
    except Exception:
        return False

def open_antigravity_voice_mode():
    """
    Brings Antigravity to front and activates Antigravity's native Voice Mode (Gemini Live).
    """
    _ensure_desktop_access()
    launch_antigravity()
    time.sleep(0.12)
    return _trigger_cdp_voice_mode()

def open_antigravity_new_chat(voice_mode=False):
    """
    Brings Antigravity to front and initiates a fresh NEW conversation.
    If voice_mode is True, activates Antigravity's native Voice Mode (Gemini Live).
    """
    if voice_mode:
        return open_antigravity_voice_mode()

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

    return True
