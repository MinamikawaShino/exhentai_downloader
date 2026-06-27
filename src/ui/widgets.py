import tkinter.font as tkfont

import customtkinter as ctk


# ── Apple Design Tokens ──────────────────────────────────────────
# Colors - static accent colors only; CTk handles light/dark base colors

class C:
    PRIMARY = "#0066CC"
    PRIMARY_FOCUS = "#0071E3"
    PRIMARY_ON_DARK = "#2997FF"
    INK = "#1D1D1F"
    BODY = "#1D1D1F"
    BODY_ON_DARK = "#FFFFFF"
    BODY_MUTED = "#CCCCCC"
    INK_MUTED_80 = "#333333"
    INK_MUTED_48 = "#7A7A7A"
    DIVIDER_SOFT = "#F0F0F0"
    HAIRLINE = "#E0E0E0"
    CANVAS = "#FFFFFF"
    CANVAS_PARCHMENT = "#F5F5F7"
    SURFACE_PEARL = "#FAFAFC"
    SURFACE_TILE_1 = "#272729"
    SURFACE_TILE_2 = "#2A2A2C"
    SURFACE_BLACK = "#000000"
    CHIP_TRANSLUCENT = "#D2D2D7"
    ON_PRIMARY = "#FFFFFF"
    ON_DARK = "#FFFFFF"

    SUCCESS = "#34C759"
    SUCCESS_HOVER = "#2DBE4E"
    DANGER = "#FF3B30"
    DANGER_HOVER = "#E0352B"
    WARNING = "#D4A017"


# ── Theme System ──────────────────────────────────────────────────
# CTk handles most colors via set_appearance_mode; we only track accent overrides

_current_theme_name = "light"


def get_theme_name():
    return _current_theme_name


def apply_theme(theme_name: str, root=None):
    global _current_theme_name
    _current_theme_name = theme_name
    if theme_name == "dark":
        ctk.set_appearance_mode("dark")
    else:
        ctk.set_appearance_mode("light")
    if root is not None:
        try:
            if theme_name == "dark":
                root.configure(fg_color="#1C1C1E")
            else:
                root.configure(fg_color=CTK_PARCHMENT)
        except Exception:
            pass
    return _current_theme_name


# CTk reference colors for Apple-style overrides
CTK_CANVAS = "#FFFFFF"
CTK_PARCHMENT = "#F5F5F7"


# Spacing tokens (8px grid)
class S:
    XXS = 4
    XS = 8
    SM = 12
    MD = 17
    LG = 24
    XL = 32
    XXL = 48
    SECTION = 80


# Border radius tokens
class R:
    NONE = 0
    XS = 5
    SM = 8
    MD = 11
    LG = 18
    PILL = 9999


SYSTEM_FONTS = [
    "SF Pro Display", "SF Pro Text",
    "Microsoft YaHei", "Microsoft YaHei UI",
    "Microsoft JhengHei", "Microsoft JhengHei UI",
    "Noto Sans CJK SC", "Segoe UI",
]
MONO_FONTS = ["SF Mono", "Cascadia Code", "Consolas", "Cascadia Mono", "Courier New"]

STATUS_COLORS = {
    "PENDING": (C.INK_MUTED_48, C.INK_MUTED_48),
    "PROCESSING": (C.WARNING, C.WARNING),
    "COMPLETED": (C.SUCCESS, C.SUCCESS_HOVER),
    "FAILED": (C.DANGER, C.DANGER_HOVER),
    "SKIPPED": (C.INK_MUTED_48, C.INK_MUTED_48),
}

STATUS_CN = {}


def _get_available_fonts():
    try:
        return set(tkfont.families())
    except Exception:
        return set()


def _resolve_display_font(available):
    for name in SYSTEM_FONTS:
        if name in available:
            return name
    cjk_aliases = {
        "\u5fae\u8f6f\u96c5\u9ed1": "Microsoft YaHei",
        "\u5b8b\u4f53": "SimSun",
        "\u9ed1\u4f53": "SimHei",
        "\u7b49\u7ebf": "DengXian",
    }
    for cn_name, en_name in cjk_aliases.items():
        if cn_name in available:
            try:
                test = tkfont.Font(family=cn_name, size=12)
                actual = test.actual()["family"]
                del test
                if actual in available:
                    return actual
            except Exception:
                pass
    return "TkDefaultFont"


def pick_font(preferred: list) -> str:
    available = _get_available_fonts()
    for name in preferred:
        if name in available:
            return name
    return "TkDefaultFont"


def setup_fonts():
    available = _get_available_fonts()
    family = _resolve_display_font(available)
    mono = pick_font(MONO_FONTS)
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family=family, size=13)
    text_font = tkfont.nametofont("TkTextFont")
    text_font.configure(family=family, size=13)
    fix_font = tkfont.nametofont("TkFixedFont")
    fix_font.configure(family=mono, size=12)
    return family, mono


class Fonts:
    def __init__(self, family: str, mono_family: str):
        self.hero = ctk.CTkFont(family=family, size=28, weight="bold")
        self.title = ctk.CTkFont(family=family, size=21, weight="bold")
        self.heading = ctk.CTkFont(family=family, size=17, weight="bold")
        self.subheading = ctk.CTkFont(family=family, size=15, weight="bold")
        self.body = ctk.CTkFont(family=family, size=13)
        self.body_strong = ctk.CTkFont(family=family, size=13, weight="bold")
        self.small = ctk.CTkFont(family=family, size=12)
        self.caption = ctk.CTkFont(family=family, size=11)
        self.textbox_body = ctk.CTkFont(family=family, size=13)
        self.textbox_small = ctk.CTkFont(family=family, size=12)
        self.mono_body = (mono_family, 12)
        self.mono_small = (mono_family, 11)


def format_size(b: int | float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def apple_section(parent, title, fonts):
    frame = ctk.CTkFrame(parent, corner_radius=R.LG)
    label = ctk.CTkLabel(frame, text=title, font=fonts.heading)
    label.pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
    return frame


def apple_pill_button(parent, text, command, width=100, color=C.PRIMARY,
                      hover_color=C.PRIMARY_FOCUS, font=None, **kwargs):
    if font is None:
        font = ctk.CTkFont(size=13)
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, fg_color=color, hover_color=hover_color,
        corner_radius=R.PILL, font=font, **kwargs,
    )


def apple_ghost_button(parent, text, command, width=100, font=None,
                      color=None, hover_color=None, **kwargs):
    if font is None:
        font = ctk.CTkFont(size=13)
    if color is not None:
        fg = color
        hv = hover_color if hover_color else ("gray75", "gray30")
        txt_color = C.CANVAS
        border_color = color
    else:
        fg = ("#E8E8E8", "#2D2D2D")
        hv = ("#D0D0D0", "#3D3D3D")
        txt_color = C.PRIMARY
        border_color = C.PRIMARY
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, fg_color=fg, hover_color=hv,
        text_color=txt_color, corner_radius=R.PILL,
        border_width=1, border_color=border_color, font=font, **kwargs,
    )


def apple_danger_button(parent, text, command, width=100, font=None, **kwargs):
    if font is None:
        font = ctk.CTkFont(size=13)
    return ctk.CTkButton(
        parent, text=text, command=command,
        width=width, fg_color=C.DANGER, hover_color=C.DANGER_HOVER,
        corner_radius=R.PILL, font=font, **kwargs,
    )
