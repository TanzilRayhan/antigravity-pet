import os
import math
from PIL import Image, ImageDraw, ImageFont
from theme import get_theme_colors

# Load Windows 11 Fluent icons and Segoe UI fonts
def get_font(size: int, bold: bool = False):
    font_names = [
        "SegoeUI-Bold.ttf" if bold else "segoeui.ttf",
        "seguisb.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf"
    ]
    for fn in font_names:
        p = os.path.join(r"C:\Windows\Fonts", fn)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def get_icon_font(size: int):
    for fn in ["SegoeIcons.ttf", "segmdl2.ttf"]:
        p = os.path.join(r"C:\Windows\Fonts", fn)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return get_font(size)

# Official Windows 11 Fluent icon glyph codepoints
ICON_SETTINGS = "\uE713"    # Settings Gear
ICON_HIDE     = "\uED1A"    # Hide / Eye Off
ICON_SWITCH   = "\uE72C"    # Switch / Sync
ICON_EXIT     = "\uE8BB"    # Close / Dismiss
ICON_EDIT     = "\uE70F"    # Edit Pen
ICON_BELL     = "\uEA8F"    # ActionCenter Bell
ICON_MIC      = "\uE720"    # Mic
ICON_UP       = "\uE74A"    # Up Arrow (Send)
ICON_PLUS     = "\uE710"    # Add / Plus

def draw_ground_shadow(w=70, h=12):
    """
    Renders a soft, elegant elliptical ground shadow under the pet when dock is hidden.
    """
    S = 3
    SW, SH = w * S, h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Concentric soft gradient ellipses
    steps = 6
    for i in range(steps, 0, -1):
        ratio = i / steps
        alpha = int(45 * (1.0 - ratio) + 10)
        ew = int(SW * ratio)
        eh = int(SH * ratio)
        ex0 = (SW - ew) // 2
        ey0 = (SH - eh) // 2
        d.ellipse([ex0, ey0, ex0 + ew, ey0 + eh], fill=(0, 0, 0, alpha))

    return img.resize((w, h), Image.Resampling.LANCZOS)

def draw_pill_dock(w=112, h=30, hover_btn=None, has_active_task=True, num_tasks=1):
    """
    Renders the floating action pill dock:
    [ ✎ Write | ||| Voice | 🔔 Tasks ]
    Only shown on hover!
    """
    _, colors = get_theme_colors()
    
    S = 3
    SW, SH = w * S, h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Ambient drop shadow
    d.rounded_rectangle([1*S, 1*S, SW - 1*S, SH - 1*S], radius=15*S, fill=colors["shadow"])
    # Pill surface
    d.rounded_rectangle([0, 0, SW - 2*S, SH - 2*S], radius=14*S, fill=colors["pill_bg"], outline=colors["pill_border"], width=1*S)

    f_icon = get_icon_font(13 * S)

    if has_active_task:
        sec_w = (SW - 2*S) // 3
        sec1_end = sec_w
        sec2_end = sec_w * 2

        if hover_btn == "write":
            d.rounded_rectangle([2*S, 2*S, sec1_end - 1*S, SH - 4*S], radius=12*S, fill=colors["pill_hover"])
        elif hover_btn == "voice":
            d.rounded_rectangle([sec1_end + 1*S, 2*S, sec2_end - 1*S, SH - 4*S], radius=10*S, fill=colors["pill_hover"])
        elif hover_btn == "bell":
            d.rounded_rectangle([sec2_end + 1*S, 2*S, SW - 4*S, SH - 4*S], radius=12*S, fill=colors["pill_hover"])

        d.line([(sec1_end, 7*S), (sec1_end, SH - 9*S)], fill=colors["divider"], width=1*S)
        d.line([(sec2_end, 7*S), (sec2_end, SH - 9*S)], fill=colors["divider"], width=1*S)

        # 1. Write Pen
        w_col = colors["icon_hover"] if hover_btn == "write" else colors["icon_color"]
        c1_x = sec1_end // 2
        try:
            bb = f_icon.getbbox(ICON_EDIT)
            iw, ih = bb[2] - bb[0], bb[3] - bb[1]
            d.text((c1_x - iw//2, (SH - ih)//2 - 1*S), ICON_EDIT, font=f_icon, fill=w_col)
        except Exception:
            d.text((c1_x - 6*S, 6*S), "✎", font=get_font(12*S), fill=w_col)

        # 2. Voice Waveform (3 smooth rounded vertical bars)
        v_col = colors["icon_hover"] if hover_btn == "voice" else colors["icon_color"]
        c2_x = sec1_end + (sec2_end - sec1_end) // 2
        cy = SH // 2
        bw = 2 * S
        d.rounded_rectangle([c2_x - 6*S, cy - 4*S, c2_x - 6*S + bw, cy + 4*S], radius=1*S, fill=v_col)
        d.rounded_rectangle([c2_x - 1*S, cy - 8*S, c2_x - 1*S + bw, cy + 8*S], radius=1*S, fill=v_col)
        d.rounded_rectangle([c2_x + 4*S, cy - 5*S, c2_x + 4*S + bw, cy + 5*S], radius=1*S, fill=v_col)

        # 3. Notification Bell
        b_col = colors["icon_hover"] if hover_btn == "bell" else colors["icon_color"]
        c3_x = sec2_end + (SW - sec2_end) // 2
        try:
            bb = f_icon.getbbox(ICON_BELL)
            iw, ih = bb[2] - bb[0], bb[3] - bb[1]
            d.text((c3_x - iw//2 - 2*S, (SH - ih)//2 - 1*S), ICON_BELL, font=f_icon, fill=b_col)
        except Exception:
            d.text((c3_x - 6*S, 6*S), "🔔", font=get_font(12*S), fill=b_col)

        # Active emerald dot or count badge
        if num_tasks > 1:
            f_num = get_font(7 * S, bold=True)
            bx = c3_x + 3 * S
            by = 3 * S
            d.rounded_rectangle([bx, by, bx + 11*S, by + 9*S], radius=4*S, fill=(34, 197, 94, 255))
            d.text((bx + 2*S + 1, by), str(num_tasks), font=f_num, fill=(255, 255, 255, 255))
        else:
            dot_x = c3_x + 5 * S
            dot_y = 6 * S
            dot_r = 3 * S
            d.ellipse([dot_x - dot_r - 1*S, dot_y - dot_r - 1*S, dot_x + dot_r + 1*S, dot_y + dot_r + 1*S], fill=(34, 197, 94, 90))
            d.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=(34, 197, 94, 255))

    else:
        mid_x = (SW - 2*S) // 2
        if hover_btn == "write":
            d.rounded_rectangle([2*S, 2*S, mid_x - 1*S, SH - 4*S], radius=12*S, fill=colors["pill_hover"])
        elif hover_btn == "voice":
            d.rounded_rectangle([mid_x + 1*S, 2*S, SW - 4*S, SH - 4*S], radius=12*S, fill=colors["pill_hover"])

        d.line([(mid_x, 7*S), (mid_x, SH - 9*S)], fill=colors["divider"], width=1*S)

        # 1. Write
        w_col = colors["icon_hover"] if hover_btn == "write" else colors["icon_color"]
        c1_x = mid_x // 2
        try:
            bb = f_icon.getbbox(ICON_EDIT)
            iw, ih = bb[2] - bb[0], bb[3] - bb[1]
            d.text((c1_x - iw//2, (SH - ih)//2 - 1*S), ICON_EDIT, font=f_icon, fill=w_col)
        except Exception:
            d.text((c1_x - 6*S, 6*S), "✎", font=get_font(12*S), fill=w_col)

        # 2. Waveform
        v_col = colors["icon_hover"] if hover_btn == "voice" else colors["icon_color"]
        c2_x = mid_x + (SW - mid_x) // 2
        cy = SH // 2
        bw = 2 * S
        d.rounded_rectangle([c2_x - 6*S, cy - 4*S, c2_x - 6*S + bw, cy + 4*S], radius=1*S, fill=v_col)
        d.rounded_rectangle([c2_x - 1*S, cy - 8*S, c2_x - 1*S + bw, cy + 8*S], radius=1*S, fill=v_col)
        d.rounded_rectangle([c2_x + 4*S, cy - 5*S, c2_x + 4*S + bw, cy + 5*S], radius=1*S, fill=v_col)

    return img.resize((w, h), Image.Resampling.LANCZOS)

def draw_chat_input_bar(w=260, h=38, text="", is_focused=True, hover_btn=None, cursor_blink=True):
    """
    Renders the exact sleek floating prompt input bar from the user screenshot:
    [ + Start new chat                                     ↑ ]
    """
    _, colors = get_theme_colors()
    
    S = 3
    SW, SH = w * S, h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Ambient drop shadow
    d.rounded_rectangle([2*S, 2*S, SW - 2*S, SH - 2*S], radius=18*S, fill=colors["shadow"])
    # Capsule surface
    d.rounded_rectangle([0, 0, SW - 3*S, SH - 3*S], radius=17*S, fill=colors["pill_bg"], outline=colors["pill_border"], width=1*S)

    f_icon = get_icon_font(12 * S)
    f_text = get_font(11 * S, bold=False)

    # Left: Plus icon (+)
    plus_col = colors["accent"] if hover_btn == "plus" else colors["text_muted"]
    try:
        bb = f_icon.getbbox(ICON_PLUS)
        iw, ih = bb[2] - bb[0], bb[3] - bb[1]
        d.text((12*S, (SH - ih)//2 - 1*S), ICON_PLUS, font=f_icon, fill=plus_col)
    except Exception:
        d.text((12*S, 10*S), "+", font=get_font(13*S, bold=True), fill=plus_col)

    # Center: Text or Placeholder
    tx = 34 * S
    max_text_w = SW - (72 * S)

    if not text:
        placeholder = "Start new chat..."
        d.text((tx, 11*S), placeholder, font=f_text, fill=colors["text_muted"])
    else:
        # User typed text
        display_str = text
        while True:
            bb = f_text.getbbox(display_str)
            if (bb[2] - bb[0]) > max_text_w and len(display_str) > 1:
                display_str = display_str[1:]
            else:
                break
        d.text((tx, 11*S), display_str, font=f_text, fill=colors["text_primary"])
        
        # Blinking cursor
        if is_focused and cursor_blink:
            bb = f_text.getbbox(display_str)
            cx = tx + (bb[2] - bb[0]) + 2*S
            d.line([(cx, 9*S), (cx, SH - 11*S)], fill=colors["accent"], width=2*S)

    # Right: Circular Accent Send Button (↑)
    btn_r = 13 * S
    btn_cx = SW - 22 * S
    btn_cy = SH // 2
    btn_fill = (37, 99, 235, 255) if hover_btn == "send" else (30, 64, 175, 255)
    if not text.strip():
        btn_fill = (45, 55, 72, 200)

    d.ellipse([btn_cx - btn_r, btn_cy - btn_r, btn_cx + btn_r, btn_cy + btn_r], fill=btn_fill)
    
    # Arrow Up icon
    arrow_col = (255, 255, 255, 255)
    try:
        bb = f_icon.getbbox(ICON_UP)
        aw, ah = bb[2] - bb[0], bb[3] - bb[1]
        d.text((btn_cx - aw//2, btn_cy - ah//2 - 1*S), ICON_UP, font=f_icon, fill=arrow_col)
    except Exception:
        d.text((btn_cx - 4*S, btn_cy - 7*S), "↑", font=get_font(11*S, bold=True), fill=arrow_col)

    final_img = img.resize((w, h), Image.Resampling.LANCZOS)
    return final_img, w, h

def draw_custom_menu(w=160, hover_idx=-1):
    """
    Renders the context menu below the pet:
    [ ⚙ Settings   ]
    [ 👁 Hide Mini  ]
    [ 🔄 Switch Pet ]
    [ ✕ Exit       ]
    """
    _, colors = get_theme_colors()
    
    menu_items = [
        (ICON_SETTINGS, "Settings"),
        (ICON_HIDE, "Hide Mini"),
        (ICON_SWITCH, "Switch Pet"),
        (ICON_EXIT, "Exit")
    ]
    item_h = 30
    h = len(menu_items) * item_h + 12

    S = 3
    SW, SH = w * S, h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([2*S, 2*S, SW - 2*S, SH - 2*S], radius=10*S, fill=colors["shadow"])
    d.rounded_rectangle([0, 0, SW - 3*S, SH - 3*S], radius=9*S, fill=colors["menu_bg"], outline=colors["menu_border"], width=1*S)

    f_icon = get_icon_font(13 * S)
    f_text = get_font(12 * S, bold=False)

    for i, (glyph, label) in enumerate(menu_items):
        iy = 6*S + i * item_h * S
        if hover_idx == i:
            d.rounded_rectangle([4*S, iy, SW - 7*S, iy + item_h*S - 2*S], radius=6*S, fill=colors["menu_hover"])

        d.text((12*S, iy + 6*S), glyph, font=f_icon, fill=colors["text_primary"])
        d.text((36*S, iy + 5*S), label, font=f_text, fill=colors["text_primary"])

    final_img = img.resize((w, h), Image.Resampling.LANCZOS)
    return final_img, w, h

def draw_speech_bubble(text="Starting new task...", max_w=240):
    """
    Renders speech bubble above the pet mascot when chatting or reacting.
    """
    _, colors = get_theme_colors()
    f_body = get_font(11, bold=False)

    lines = []
    words = text.split()
    curr_line = ""
    for w in words:
        test_line = (curr_line + " " + w).strip()
        try:
            bbox = f_body.getbbox(test_line)
            w_px = bbox[2] - bbox[0]
        except Exception:
            w_px = len(test_line) * 7
        if w_px > max_w - 24:
            if curr_line:
                lines.append(curr_line)
            curr_line = w
        else:
            curr_line = test_line
    if curr_line:
        lines.append(curr_line)
    lines = lines[:3]

    card_w = max_w
    line_h = 16
    card_h = 18 + len(lines) * line_h + 10

    S = 3
    SW, SH = card_w * S, card_h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([2*S, 2*S, SW - 2*S, SH - 2*S], radius=10*S, fill=colors["shadow"])
    d.rounded_rectangle([0, 0, SW - 3*S, SH - 3*S], radius=9*S, fill=colors["card_bg"], outline=colors["menu_border"], width=1*S)

    # Bottom pointer
    tip_x = (SW - 3*S) // 2
    d.polygon([(tip_x - 5*S, SH - 3*S), (tip_x + 5*S, SH - 3*S), (tip_x, SH - 1)], fill=colors["card_bg"])

    final_img = img.resize((card_w, card_h), Image.Resampling.LANCZOS)
    d1 = ImageDraw.Draw(final_img)

    y = 8
    for l in lines:
        d1.text((12, y), l, font=f_body, fill=colors["text_primary"])
        y += line_h

    return final_img, card_w, card_h

def draw_summary_card(title="Antigravity 2.0 • Active Task", summary="Active coding session in progress...", task_idx=0, total_tasks=1, max_w=260):
    """
    Renders the modern conversation / task summary popup chat bubble when Bell is clicked.
    Supports multi-task navigation (task_idx of total_tasks).
    """
    _, colors = get_theme_colors()

    f_title = get_font(11, bold=True)
    f_badge = get_font(9, bold=True)
    f_body = get_font(11, bold=False)
    f_footer = get_font(9, bold=False)

    lines = []
    words = summary.split()
    curr_line = ""
    for w in words:
        test_line = (curr_line + " " + w).strip()
        try:
            bbox = f_body.getbbox(test_line)
            w_px = bbox[2] - bbox[0]
        except Exception:
            w_px = len(test_line) * 7
        if w_px > max_w - 24:
            if curr_line:
                lines.append(curr_line)
            curr_line = w
        else:
            curr_line = test_line
    if curr_line:
        lines.append(curr_line)
    lines = lines[:4]

    card_w = max_w
    line_h = 16
    has_multi = total_tasks > 1
    footer_h = 20 if has_multi else 0
    card_h = 32 + len(lines) * line_h + 12 + footer_h

    S = 3
    SW, SH = card_w * S, card_h * S
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle([2*S, 2*S, SW - 2*S, SH - 2*S], radius=11*S, fill=colors["shadow"])
    d.rounded_rectangle([0, 0, SW - 3*S, SH - 3*S], radius=10*S, fill=colors["card_bg"], outline=colors["menu_border"], width=1*S)
    d.rounded_rectangle([0, 0, SW - 3*S, 3*S], radius=2*S, fill=colors["accent"])

    tip_x = (SW - 3*S) // 2
    d.polygon([(tip_x - 6*S, SH - 4*S), (tip_x + 6*S, SH - 4*S), (tip_x, SH - 1*S)], fill=colors["card_bg"])

    final_img = img.resize((card_w, card_h), Image.Resampling.LANCZOS)
    d1 = ImageDraw.Draw(final_img)

    d1.text((12, 9), title, font=f_title, fill=colors["accent"])

    if has_multi:
        badge_text = f"‹ {task_idx + 1}/{total_tasks} ›"
        try:
            bb = f_badge.getbbox(badge_text)
            bw = bb[2] - bb[0]
        except Exception:
            bw = len(badge_text) * 6
        bx = card_w - 12 - bw - 8
        by = 8
        d1.rounded_rectangle([bx, by, bx + bw + 8, by + 14], radius=4, fill=(56, 189, 248, 35))
        d1.text((bx + 4, by + 1), badge_text, font=f_badge, fill=colors["accent"])

    d1.line([(12, 27), (card_w - 12, 27)], fill=colors["divider"])

    y = 33
    for l in lines:
        d1.text((12, y), l, font=f_body, fill=colors["text_primary"])
        y += line_h

    if has_multi:
        d1.line([(12, card_h - 22), (card_w - 12, card_h - 22)], fill=colors["divider"])
        footer_text = "Click card to switch task • Bell to close"
        d1.text((12, card_h - 17), footer_text, font=f_footer, fill=colors["text_muted"])

    return final_img, card_w, card_h
