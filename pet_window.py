import os
import sys
import time
import math
import ctypes
from ctypes import wintypes
import threading
import win32gui
import win32con
import win32api

# 1. Ensure Per-Monitor DPI Awareness V2 for razor sharp 1:1 pixel rendering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        pass

from config import load_config, save_config, SETTINGS_FILE, PETS_DIR, CONFIG_DIR, get_asset_path
from pet_loader import PetSpriteSheet, PetDefinition, get_available_pets, rgba_to_premultiplied_bgra
from sound import SoundPlayer
from antigravity_launcher import (
    launch_antigravity, is_antigravity_running,
    toggle_antigravity_window, open_antigravity_new_chat,
    open_antigravity_voice_mode
)
from task_monitor import get_current_task_status
from theme import get_theme_colors
from ui_renderer import (
    draw_pill_dock, draw_ground_shadow,
    draw_custom_menu, draw_speech_bubble, draw_summary_card
)
from hub_server import start_hub_background_server, open_hub_app

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

class SIZE(ctypes.Structure):
    _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', ctypes.c_byte),
        ('BlendFlags', ctypes.c_byte),
        ('SourceConstantAlpha', ctypes.c_byte),
        ('AlphaFormat', ctypes.c_byte)
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3)
    ]

WM_TRAYICON       = win32con.WM_USER + 20
WM_TOGGLE_HOTKEY  = win32con.WM_USER + 50

class AntigravityPetWindow:
    def __init__(self):
        self.cfg = load_config()
        self.sound = SoundPlayer(enabled=self.cfg.get("sound_enabled", True))
        
        self.scale = self.cfg.get("scale", 0.75)
        self.behavior = self.cfg.get("behavior", "zero_g")
        self.sync_with_antigravity = self.cfg.get("sync_with_antigravity", True)
        self.is_visible = True
        self._is_closed = False
        
        # Interactive state
        self.is_hovered = False
        self.last_mouse_move_time = 0.0
        self.hover_dock_btn = None   # 'write', 'voice', 'bell'
        
        # Dynamic task monitoring (Bell only shown when a real task is running!)
        self.has_active_task = False
        self.active_tasks = []
        self.current_task_idx = 0
        self.task_title = ""
        self.task_summary = ""
        self.last_task_check_time = 0.0
        self.summary_rect = (0, 0, 0, 0)
        
        self.show_summary = False
        self.show_menu = False
        self.menu_hover_idx = -1

        # Speech bubble
        self.show_speech = False
        self.speech_text = ""
        self.speech_timeout = 0.0
        
        # Track settings file for live immediate sync
        self._last_settings_mtime = 0
        try:
            if os.path.exists(SETTINGS_FILE):
                self._last_settings_mtime = os.path.getmtime(SETTINGS_FILE)
        except Exception:
            pass

        # Hub Server
        self.hub_server = None
        self.hub_port = 54321
        self._ensure_hub_server()

        # Pets
        self.available_pets = get_available_pets(PETS_DIR)
        self.current_pet_slug = self.cfg.get("current_pet", "makima")
        self.sheet = None
        self._load_current_sheet()

        # Window state
        self.hwnd = None
        self.h_icon = None
        self.class_name = "AntigravityPetWindowLayered"
        
        # Monitor work area
        try:
            h_mon = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
            mon_info = win32api.GetMonitorInfo(h_mon)
            self.work_area = mon_info["Work"]
        except Exception:
            self.work_area = (0, 0, win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1) - 40)

        # Dynamic layout calculation
        self._calc_dimensions()

        saved_x = self.cfg.get("x", -1)
        saved_y = self.cfg.get("y", -1)
        
        if saved_x < 0 or saved_x > self.work_area[2] - 50:
            self.x = self.work_area[2] - self.buffer_w - 40
        else:
            self.x = saved_x
            
        if saved_y < 0 or saved_y > self.work_area[3] - 50:
            self.y = self.work_area[3] - self.buffer_h - 20
        else:
            self.y = saved_y

        self.base_y = self.y
        self.current_y = self.y
        
        # Animation state
        self.current_state = "idle"
        self.current_frame_idx = 0
        self.state_end_time = 0.0
        self.next_frame_time = time.time()
        self.last_sync_check_time = 0.0
        self.last_settings_check_time = 0.0
        self.prev_antigravity_state = is_antigravity_running()

        # Dragging state
        self.is_dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_start_win = (0, 0)
        self.has_moved = False

        # Win32 GDI caching
        self.screen_dc = None
        self.mem_dc = None
        self.h_bitmap = None
        self.old_bitmap = None
        self.p_bits = None

        self._init_window()
        self._start_global_key_hook()

    def _ensure_hub_server(self):
        try:
            self.hub_server = start_hub_background_server(self.hub_port)
        except Exception:
            pass

    def _calc_dimensions(self):
        pet_w = self.sheet.target_w if self.sheet else 144
        pet_h = self.sheet.target_h if self.sheet else 156
        
        # Dock width: 112px when task active (3 buttons), 76px otherwise (2 buttons)
        self.dock_w = 112 if self.has_active_task else 76
        self.dock_h = 30
        self.menu_w = 160
        self.menu_h = 132

        self.buffer_w = max(pet_w + 100, 280)
        self.pet_y = 115
        self.buffer_h = self.pet_y + pet_h + self.dock_h + self.menu_h + 30

        self.pet_x = (self.buffer_w - pet_w) // 2
        self.dock_x = (self.buffer_w - self.dock_w) // 2
        self.dock_y = self.pet_y + pet_h + 4

        self.menu_x = (self.buffer_w - self.menu_w) // 2
        self.menu_y = self.dock_y + self.dock_h + 8

    def _load_current_sheet(self):
        chosen_pet = None
        self.available_pets = get_available_pets(PETS_DIR)
        for p in self.available_pets:
            if p.slug == self.current_pet_slug:
                chosen_pet = p
                break
        if not chosen_pet and self.available_pets:
            chosen_pet = self.available_pets[0]
            self.current_pet_slug = chosen_pet.slug

        if chosen_pet:
            self.sheet = PetSpriteSheet(chosen_pet, scale=self.scale)
        else:
            raise RuntimeError("No pets found in pets directory!")

    def _init_window(self):
        try:
            h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_default:
                user32.SetThreadDesktop(h_default)
        except Exception:
            pass

        wc = win32gui.WNDCLASS()
        wc.lpszClassName = self.class_name
        wc.lpfnWndProc = self._wnd_proc
        # CS_DBLCLKS enables WM_LBUTTONDBLCLK for instant double-click detection
        wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW | win32con.CS_DBLCLKS
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        
        try:
            self.atom = win32gui.RegisterClass(wc)
        except Exception:
            pass

        ex_style = win32con.WS_EX_LAYERED | win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW
        style = win32con.WS_POPUP

        self.hwnd = win32gui.CreateWindowEx(
            ex_style,
            self.class_name,
            "Antigravity Pet",
            style,
            int(self.x), int(self.y), self.buffer_w, self.buffer_h,
            0, 0, 0, None
        )

        self._setup_buffer(self.buffer_w, self.buffer_h)

        # Register official Antigravity logo as system tray icon
        try:
            ico_path = get_asset_path("icon.ico")
            h_icon = 0
            if os.path.exists(ico_path):
                try:
                    h_icon = win32gui.LoadImage(
                        0, ico_path, win32con.IMAGE_ICON, 0, 0,
                        win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                    )
                except Exception:
                    h_icon = 0
            if not h_icon:
                h_icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            
            self.h_icon = h_icon
            nid = (
                self.hwnd,
                1,
                win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                WM_TRAYICON,
                self.h_icon,
                "Antigravity Pet (Ctrl+Alt+P to Show/Hide)"
            )
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except Exception:
            pass

        # 30ms render loop
        user32.SetTimer(self.hwnd, 1, 30, None)

        if self.sync_with_antigravity:
            is_running = is_antigravity_running()
            if not is_running:
                self.hide_pet()
            else:
                self.show_pet()
        else:
            self.show_pet()

        self._render_current_frame()

    def _start_global_key_hook(self):
        """Dedicated background thread polling GetAsyncKeyState so Ctrl+Alt+P works 100% reliably."""
        def _listener():
            VK_CONTROL = 0x11
            VK_MENU    = 0x12 # Alt
            VK_P       = 0x50
            VK_LWIN    = 0x5B
            VK_RWIN    = 0x5C

            was_pressed = False
            while not self._is_closed:
                time.sleep(0.04) # 25Hz check (0.0% CPU)
                try:
                    ctrl = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                    alt  = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                    win  = bool(user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or bool(user32.GetAsyncKeyState(VK_RWIN) & 0x8000)
                    p    = bool(user32.GetAsyncKeyState(VK_P) & 0x8000)

                    is_down = ((ctrl and alt and p) or (win and alt and p))
                    if is_down and not was_pressed:
                        was_pressed = True
                        if self.hwnd:
                            user32.PostMessageW(self.hwnd, WM_TOGGLE_HOTKEY, 0, 0)
                    elif not is_down:
                        was_pressed = False
                except Exception:
                    pass
        t = threading.Thread(target=_listener, daemon=True)
        t.start()

    def _setup_buffer(self, w, h):
        if self.mem_dc:
            gdi32.SelectObject(self.mem_dc, self.old_bitmap)
            gdi32.DeleteObject(self.h_bitmap)
            gdi32.DeleteDC(self.mem_dc)
            user32.ReleaseDC(0, self.screen_dc)

        self.buffer_w = w
        self.buffer_h = h
        self.screen_dc = user32.GetDC(0)
        self.mem_dc = gdi32.CreateCompatibleDC(self.screen_dc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        self.p_bits = ctypes.c_void_p()
        self.h_bitmap = gdi32.CreateDIBSection(
            self.mem_dc, ctypes.byref(bmi), 0, ctypes.byref(self.p_bits), 0, 0
        )
        self.old_bitmap = gdi32.SelectObject(self.mem_dc, self.h_bitmap)

    def show_pet(self):
        self.is_visible = True
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        self._render_current_frame()

    def hide_pet(self):
        self.is_visible = False
        self.show_menu = False
        self.show_summary = False
        self.show_speech = False
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def toggle_visibility(self):
        if self.is_visible:
            self.hide_pet()
        else:
            self.show_pet()
            self.sound.play_wave()

    def open_settings_hub(self):
        """Open the single-instance modern Web-based Pet Gallery Hub."""
        self.show_menu = False
        self._render_current_frame()
        open_hub_app(self.hub_port)

    def change_pet(self, slug: str):
        self.current_pet_slug = slug
        self.cfg["current_pet"] = slug
        save_config(self.cfg)
        self._load_current_sheet()
        self.current_state = "idle"
        self.current_frame_idx = 0
        self._calc_dimensions()
        self._setup_buffer(self.buffer_w, self.buffer_h)
        self.sound.play_wave()
        self._render_current_frame()

    def change_scale(self, new_scale: float):
        self.scale = max(0.3, min(2.0, float(new_scale)))
        self.cfg["scale"] = self.scale
        save_config(self.cfg)
        self._load_current_sheet()
        self._calc_dimensions()
        self._setup_buffer(self.buffer_w, self.buffer_h)
        self._render_current_frame()

    def _show_tray_menu(self):
        """Display native Windows popup menu when right-clicking the system drawer icon."""
        h_menu = win32gui.CreatePopupMenu()
        label_show = "Hide Pet" if self.is_visible else "Show Pet"
        win32gui.AppendMenu(h_menu, win32con.MF_STRING, 101, label_show)
        win32gui.AppendMenu(h_menu, win32con.MF_STRING, 102, "Settings...")
        win32gui.AppendMenu(h_menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(h_menu, win32con.MF_STRING, 103, "Quit Antigravity Pet")

        win32gui.SetForegroundWindow(self.hwnd)
        pos = win32gui.GetCursorPos()
        cmd = win32gui.TrackPopupMenu(
            h_menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            pos[0], pos[1], 0, self.hwnd, None
        )
        win32gui.DestroyMenu(h_menu)

        if cmd == 101:
            self.toggle_visibility()
        elif cmd == 102:
            self.open_settings_hub()
        elif cmd == 103:
            self.quit_app()

    def _on_click_pen_new_conversation(self):
        """Clicking Pen opens a fresh new conversation directly inside Antigravity!"""
        self.sound.play_click()
        self.current_state = "review"
        self.current_frame_idx = 0
        self.state_end_time = time.time() + 1.2
        self._render_current_frame()
        open_antigravity_new_chat(voice_mode=False)

    def _on_click_voice_conversation(self):
        """Clicking Voice triggers Antigravity's native Voice Mode."""
        self.sound.play_wave()
        self.current_state = "waving"
        self.current_frame_idx = 0
        self.state_end_time = time.time() + 1.2
        self.show_speech = False
        self.speech_text = None
        self._render_current_frame()
        open_antigravity_voice_mode()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        try:
            return self._wnd_proc_inner(hwnd, msg, wparam, lparam)
        except Exception:
            import traceback
            traceback.print_exc()
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _wnd_proc_inner(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_LBUTTONDBLCLK:
            # DOUBLE CLICK ON PET: Instantly Toggle Antigravity (Restore / Minimize)
            self.sound.play_wave()
            self.current_state = "jumping"
            self.current_frame_idx = 0
            self.state_end_time = time.time() + 0.8
            self._render_current_frame()
            toggle_antigravity_window()
            return 0

        elif msg == win32con.WM_LBUTTONDOWN:
            mouse_x = win32api.LOWORD(lparam)
            mouse_y = win32api.HIWORD(lparam)

            # 1. Check Context Menu click if open
            if self.show_menu:
                mx0 = self.menu_x
                my0 = self.menu_y
                mx1 = mx0 + self.menu_w
                my1 = my0 + self.menu_h
                if mx0 <= mouse_x <= mx1 and my0 <= mouse_y <= my1:
                    rel_y = mouse_y - my0 - 6
                    if 0 <= rel_y < 120:
                        idx = rel_y // 30
                        if idx == 0:    # Settings
                            self.open_settings_hub()
                        elif idx == 1 or idx == 3:  # Hide Pet / Exit to Tray
                            self.hide_pet()
                        elif idx == 2:  # Switch Pet
                            self.available_pets = get_available_pets(PETS_DIR)
                            curr_idx = 0
                            for i, p in enumerate(self.available_pets):
                                if p.slug == self.current_pet_slug:
                                    curr_idx = i
                                    break
                            next_idx = (curr_idx + 1) % len(self.available_pets)
                            self.change_pet(self.available_pets[next_idx].slug)
                            self.show_menu = False
                        return 0
                else:
                    self.show_menu = False
                    self._render_current_frame()
                    return 0

            # 1.5. Check Summary Card click if open (to cycle tasks)
            if self.show_summary and self.has_active_task:
                sx0, sy0, sx1, sy1 = self.summary_rect
                if sx0 <= mouse_x <= sx1 and sy0 <= mouse_y <= sy1:
                    if len(self.active_tasks) > 1:
                        self.current_task_idx = (self.current_task_idx + 1) % len(self.active_tasks)
                        curr = self.active_tasks[self.current_task_idx]
                        self.task_title = curr["title"]
                        self.task_summary = curr["summary"]
                        self.sound.play_click()
                        self._render_current_frame()
                    return 0

            # 2. Check Pill Dock buttons (when visible on hover)
            if self.is_hovered:
                if (self.dock_x <= mouse_x <= self.dock_x + self.dock_w and
                    self.dock_y <= mouse_y <= self.dock_y + self.dock_h):
                    rel_x = mouse_x - self.dock_x
                    sec_w = self.dock_w // 3 if self.has_active_task else self.dock_w // 2
                    
                    if rel_x < sec_w:
                        # Clicked Pen icon: Open NEW conversation directly in Antigravity!
                        self._on_click_pen_new_conversation()
                    elif rel_x < sec_w * 2:
                        # Clicked Voice icon: Trigger voice conversation in Antigravity!
                        self._on_click_voice_conversation()
                    elif self.has_active_task:
                        # Clicked Bell icon: Toggle real-time running task summary
                        self.sound.play_click()
                        self.show_summary = not self.show_summary
                        if self.show_summary:
                            if self.current_task_idx >= len(self.active_tasks):
                                self.current_task_idx = 0
                            if self.active_tasks:
                                self.task_title = self.active_tasks[self.current_task_idx]["title"]
                                self.task_summary = self.active_tasks[self.current_task_idx]["summary"]
                        self._render_current_frame()
                    return 0

            # 3. Otherwise: Start dragging Pet
            self.show_menu = False
            self.show_summary = False
            self.is_dragging = True
            self.has_moved = False
            self.drag_start_mouse = win32gui.GetCursorPos()
            self.drag_start_win = (self.x, self.base_y)
            win32gui.SetCapture(hwnd)
            self.current_state = "jumping"
            self.current_frame_idx = 0
            self._render_current_frame()
            return 0

        elif msg == win32con.WM_MOUSEMOVE:
            mouse_x = win32api.LOWORD(lparam)
            mouse_y = win32api.HIWORD(lparam)
            self.is_hovered = True
            self.last_mouse_move_time = time.time()

            if self.is_dragging:
                cur = win32gui.GetCursorPos()
                dx = cur[0] - self.drag_start_mouse[0]
                dy = cur[1] - self.drag_start_mouse[1]
                if abs(dx) > 4 or abs(dy) > 4:
                    self.has_moved = True
                new_x = self.drag_start_win[0] + dx
                new_y = self.drag_start_win[1] + dy
                if new_x != self.x or new_y != self.base_y:
                    self.x = new_x
                    self.base_y = new_y
                    self.current_y = self.base_y
                    # Hardware position update via user32.SetWindowPos (0.0% CPU, no bitmap re-render, exception-safe)
                    user32.SetWindowPos(
                        self.hwnd,
                        0,
                        int(self.x),
                        int(self.current_y),
                        0, 0,
                        0x0001 | 0x0004 | 0x0010  # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                    )
                return 0

            # Hover detection for Pill Dock
            hover = None
            if self.is_hovered:
                if (self.dock_x <= mouse_x <= self.dock_x + self.dock_w and
                    self.dock_y <= mouse_y <= self.dock_y + self.dock_h):
                    rel_x = mouse_x - self.dock_x
                    sec_w = self.dock_w // 3 if self.has_active_task else self.dock_w // 2
                    if rel_x < sec_w:
                        hover = "write"
                    elif rel_x < sec_w * 2:
                        hover = "voice"
                    elif self.has_active_task:
                        hover = "bell"

            # Hover detection for custom menu
            menu_idx = -1
            if self.show_menu:
                mx0 = self.menu_x
                my0 = self.menu_y
                mx1 = mx0 + self.menu_w
                my1 = my0 + self.menu_h
                if mx0 <= mouse_x <= mx1 and my0 <= mouse_y <= my1:
                    rel_y = mouse_y - my0 - 6
                    if 0 <= rel_y < 120:
                        menu_idx = rel_y // 30

            if hover != self.hover_dock_btn or menu_idx != self.menu_hover_idx:
                self.hover_dock_btn = hover
                self.menu_hover_idx = menu_idx
                self._render_current_frame()

            return 0

        elif msg == win32con.WM_LBUTTONUP:
            if self.is_dragging:
                win32gui.ReleaseCapture()
                self.is_dragging = False
                if not self.has_moved:
                    # Single click on pet mascot opens Antigravity
                    self.sound.play_click()
                    launch_antigravity()
                else:
                    self.sound.play_drop()
                    self.current_state = "idle"
                    self.current_frame_idx = 0
                    self.cfg["x"] = self.x
                    self.cfg["y"] = self.base_y
                    save_config(self.cfg)
                    self._render_current_frame()
            return 0

        elif msg == win32con.WM_RBUTTONUP:
            self.show_menu = not self.show_menu
            self._render_current_frame()
            return 0

        elif msg == WM_TOGGLE_HOTKEY:
            self.toggle_visibility()
            return 0

        elif msg == WM_TRAYICON:
            if lparam in (win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK):
                self.toggle_visibility()
            elif lparam == win32con.WM_RBUTTONUP:
                self._show_tray_menu()
            return 0

        elif msg == win32con.WM_TIMER:
            self._on_tick()
            return 0

        elif msg == win32con.WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _on_tick(self):
        now = time.time()

        # Hover timeout check: if mouse left the window area for > 0.8s, hide dock & show shadow
        if self.is_hovered and not self.show_menu and not self.show_summary:
            if now - self.last_mouse_move_time > 0.8:
                cur = win32gui.GetCursorPos()
                rx = cur[0] - self.x
                ry = cur[1] - self.current_y
                if not (0 <= rx <= self.buffer_w and 0 <= ry <= self.buffer_h):
                    self.is_hovered = False
                    self._render_current_frame()

        # Speech bubble timeout
        if self.show_speech and self.speech_timeout > 0:
            if now > self.speech_timeout:
                self.show_speech = False
                self.speech_timeout = 0
                self._render_current_frame()

        # Real-time task monitoring: check every 0.8s if real tasks are actively running
        if now - self.last_task_check_time > 0.8:
            self.last_task_check_time = now
            is_active, title, summary, tasks = get_current_task_status()
            
            state_changed = (is_active != self.has_active_task) or (len(tasks) != len(self.active_tasks))
            self.has_active_task = is_active
            self.active_tasks = tasks

            if not is_active:
                if self.show_summary:
                    self.show_summary = False
                    state_changed = True
                self.current_task_idx = 0
                self.task_title = ""
                self.task_summary = ""
                self.summary_rect = (0, 0, 0, 0)
            else:
                if self.current_task_idx >= len(tasks):
                    self.current_task_idx = 0
                if tasks:
                    curr_task = tasks[self.current_task_idx]
                    new_title = curr_task["title"]
                    new_summary = curr_task["summary"]
                    if new_title != self.task_title or new_summary != self.task_summary:
                        self.task_title = new_title
                        self.task_summary = new_summary
                        state_changed = True

            if state_changed:
                self._calc_dimensions()
                self._render_current_frame()

        # 1. Antigravity Process Sync check
        if now - self.last_sync_check_time > 1.2:
            self.last_sync_check_time = now
            running = is_antigravity_running()

            if self.sync_with_antigravity:
                if running != self.prev_antigravity_state:
                    self.prev_antigravity_state = running
                    if running:
                        self.show_pet()
                    else:
                        self.hide_pet()
                        return

        # 2. Real-time Live Settings Sync with settings.json
        if now - self.last_settings_check_time > 0.3:
            self.last_settings_check_time = now
            try:
                if os.path.exists(SETTINGS_FILE):
                    mtime = os.path.getmtime(SETTINGS_FILE)
                    if mtime > self._last_settings_mtime:
                        self._last_settings_mtime = mtime
                        fresh_cfg = load_config()
                        
                        new_pet = fresh_cfg.get("current_pet")
                        if new_pet and new_pet != self.current_pet_slug:
                            self.change_pet(new_pet)

                        new_scale = fresh_cfg.get("scale")
                        if new_scale and abs(float(new_scale) - self.scale) > 0.01:
                            self.change_scale(new_scale)

                        new_beh = fresh_cfg.get("behavior")
                        if new_beh and new_beh != self.behavior:
                            self.behavior = new_beh

                        new_sound = fresh_cfg.get("sound_enabled")
                        if new_sound is not None and new_sound != self.sound.enabled:
                            self.sound.enabled = new_sound

                        new_sync = fresh_cfg.get("sync_with_antigravity")
                        if new_sync is not None and new_sync != self.sync_with_antigravity:
                            self.sync_with_antigravity = new_sync

                        self.cfg = fresh_cfg
                        self._render_current_frame()
            except Exception:
                pass

        if not self.is_visible:
            return

        # State timeout (e.g. after jumping or waving)
        if self.current_state != "idle" and self.state_end_time > 0:
            if now > self.state_end_time and not self.is_dragging:
                self.current_state = "idle"
                self.current_frame_idx = 0
                self.state_end_time = 0

        # STILL ON IDLE:
        # Only animate movements when mouse is hovered or pet is being dragged!
        # When idle without hover/drag, keep completely still (frame 0) to avoid distraction.
        if self.is_hovered or self.is_dragging:
            # Advance frames when interacting
            if now >= self.next_frame_time:
                self.current_frame_idx += 1
                delay_ms = self.sheet.get_delay(self.current_state, self.current_frame_idx)
                self.next_frame_time = now + (delay_ms / 1000.0)
                self._render_current_frame()
        else:
            # Still pose: locked at frame 0 and base_y
            if self.current_frame_idx != 0 or self.current_y != self.base_y:
                self.current_frame_idx = 0
                self.current_y = self.base_y
                self._render_current_frame()

    def _render_current_frame(self):
        if not self.hwnd or not self.sheet or not self.is_visible:
            return

        try:
            from PIL import Image

            canvas = Image.new("RGBA", (self.buffer_w, self.buffer_h), (0, 0, 0, 0))

            # 1. Ground Shadow under pet feet when dock is hidden
            pet_w = self.sheet.target_w
            pet_h = self.sheet.target_h
            if not self.is_hovered and not self.show_menu and not self.show_summary and not self.is_dragging:
                shadow_img = draw_ground_shadow(w=int(pet_w * 0.7), h=12)
                sw, sh = shadow_img.size
                sx = (self.buffer_w - sw) // 2
                sy = self.pet_y + pet_h - 4
                canvas.paste(shadow_img, (sx, sy), shadow_img)

            # 2. Draw Pet Mascot (Frame 0 when idle/unhovered for distraction-free stillness)
            pet_img = self.sheet.get_frame(self.current_state, self.current_frame_idx)
            canvas.paste(pet_img, (self.pet_x, self.pet_y), pet_img)

            # 3. Floating Action Dock (only shown when mouse hovered and NOT dragging)
            if (self.is_hovered or self.show_menu) and not self.is_dragging:
                dock_img = draw_pill_dock(
                    self.dock_w, self.dock_h,
                    hover_btn=self.hover_dock_btn,
                    has_active_task=self.has_active_task,
                    num_tasks=len(self.active_tasks)
                )
                canvas.paste(dock_img, (self.dock_x, self.dock_y), dock_img)

            # 4. Speech Bubble above pet (when reacting)
            if self.show_speech and self.speech_text:
                speech_img, spw, sph = draw_speech_bubble(self.speech_text)
                sp_x = (self.buffer_w - spw) // 2
                sp_y = max(2, self.pet_y - sph - 4)
                canvas.paste(speech_img, (sp_x, sp_y), speech_img)

            # 5. Real-Time Conversation Summary Card (when bell clicked and task running)
            elif self.show_summary and self.has_active_task:
                summary_img, sw, sh = draw_summary_card(
                    title=self.task_title or "Antigravity 2.0 • Active Task",
                    summary=self.task_summary or "Running Antigravity task in progress...",
                    task_idx=self.current_task_idx,
                    total_tasks=len(self.active_tasks),
                    max_w=260
                )
                sx = (self.buffer_w - sw) // 2
                sy = max(2, self.pet_y - sh - 4)
                self.summary_rect = (sx, sy, sx + sw, sy + sh)
                canvas.paste(summary_img, (sx, sy), summary_img)
            else:
                self.summary_rect = (0, 0, 0, 0)

            # 6. Context Menu below the pet & dock
            if self.show_menu:
                menu_img, mw, mh = draw_custom_menu(self.menu_w, hover_idx=self.menu_hover_idx)
                canvas.paste(menu_img, (self.menu_x, self.menu_y), menu_img)

            # Convert to premultiplied BGRA bytes
            bgra_bytes = rgba_to_premultiplied_bgra(canvas)

            ctypes.memmove(self.p_bits, bgra_bytes, len(bgra_bytes))

            pt_dst = POINT(int(self.x), int(self.current_y))
            sz = SIZE(self.buffer_w, self.buffer_h)
            pt_src = POINT(0, 0)
            blend = BLENDFUNCTION(0, 0, 255, 1)

            user32.UpdateLayeredWindow(
                self.hwnd,
                self.screen_dc,
                ctypes.byref(pt_dst),
                ctypes.byref(sz),
                self.mem_dc,
                ctypes.byref(pt_src),
                0,
                ctypes.byref(blend),
                2 # ULW_ALPHA
            )
        except Exception:
            pass

    def quit_app(self):
        """Clean full application exit."""
        self._is_closed = True
        try:
            nid = (self.hwnd, 1)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        except Exception:
            pass
        try:
            user32.KillTimer(self.hwnd, 1)
            win32gui.DestroyWindow(self.hwnd)
        except Exception:
            pass
        user32.PostQuitMessage(0)
        os._exit(0)
