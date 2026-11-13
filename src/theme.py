import winreg

THEME_COLORS = {
    "dark": {
        "pill_bg": (24, 24, 27, 240),
        "pill_border": (39, 39, 42, 255),
        "pill_hover": (45, 45, 52, 255),
        "divider": (63, 63, 70, 255),
        "icon_color": (244, 244, 245, 255),
        "icon_hover": (56, 189, 248, 255),
        "menu_bg": (24, 24, 27, 250),
        "menu_border": (39, 39, 42, 255),
        "menu_hover": (39, 39, 42, 255),
        "text_primary": (244, 244, 245, 255),
        "text_muted": (161, 161, 170, 255),
        "accent": (56, 189, 248, 255),
        "badge_bg": (15, 23, 42, 240),
        "badge_border": (56, 189, 248, 200),
        "card_bg": (24, 24, 27, 245),
        "shadow": (0, 0, 0, 80)
    },
    "light": {
        "pill_bg": (255, 255, 255, 245),
        "pill_border": (228, 228, 231, 255),
        "pill_hover": (244, 244, 245, 255),
        "divider": (212, 212, 216, 255),
        "icon_color": (24, 24, 27, 255),
        "icon_hover": (2, 132, 199, 255),
        "menu_bg": (255, 255, 255, 250),
        "menu_border": (228, 228, 231, 255),
        "menu_hover": (244, 244, 245, 255),
        "text_primary": (24, 24, 27, 255),
        "text_muted": (113, 113, 122, 255),
        "accent": (2, 132, 199, 255),
        "badge_bg": (240, 249, 255, 245),
        "badge_border": (2, 132, 199, 200),
        "card_bg": (255, 255, 255, 245),
        "shadow": (0, 0, 0, 30)
    }
}

def get_system_theme() -> str:
    """Return 'dark' or 'light' according to Windows theme preference."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if val == 1 else "dark"
    except Exception:
        return "dark"

def get_theme_colors():
    theme = get_system_theme()
    return theme, THEME_COLORS.get(theme, THEME_COLORS["dark"])
