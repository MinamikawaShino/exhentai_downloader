import tkinter.font as tkfont

import customtkinter as ctk


SYSTEM_FONTS = [
    "Microsoft YaHei UI", "Microsoft YaHei",
    "Microsoft JhengHei UI", "Microsoft JhengHei",
    "Noto Sans CJK SC", "Segoe UI",
]
MONO_FONTS = ["Cascadia Code", "Consolas", "Cascadia Mono", "Courier New"]

STATUS_COLORS = {
    "PENDING": ("gray50", "gray30"),
    "PROCESSING": ("#D4A017", "#D4A017"),
    "COMPLETED": ("#2ECC71", "#27AE60"),
    "FAILED": ("#E74C3C", "#C0392B"),
    "SKIPPED": ("gray60", "gray45"),
}

STATUS_CN = {}


def _get_available_fonts():
    try:
        return set(tkfont.families())
    except Exception:
        return set()


def _resolve_cjk_font(available):
    cjk_font_map = {
        "Microsoft YaHei UI": "Microsoft YaHei UI",
        "Microsoft YaHei": "Microsoft YaHei",
        "Microsoft JhengHei UI": "Microsoft JhengHei UI",
        "Microsoft JhengHei": "Microsoft JhengHei",
        "Noto Sans CJK SC": "Noto Sans CJK SC",
        "Segoe UI": "Segoe UI",
    }
    for font in SYSTEM_FONTS:
        if font in cjk_font_map and font in available:
            return font
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
    family = _resolve_cjk_font(available)
    mono = pick_font(MONO_FONTS)
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family=family, size=11)
    fix_font = tkfont.nametofont("TkFixedFont")
    fix_font.configure(family=mono, size=10)
    return family, mono


class Fonts:
    def __init__(self, family: str, mono_family: str):
        self.title = ctk.CTkFont(family=family, size=18)
        self.heading = ctk.CTkFont(family=family, size=13)
        self.subheading = ctk.CTkFont(family=family, size=12)
        self.body = ctk.CTkFont(family=family, size=11)
        self.small = ctk.CTkFont(family=family, size=10)
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