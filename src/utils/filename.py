import re


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', ' ', filename).strip()


def normalize_for_comparison(s: str) -> str:
    return "".join(s.split()).lower()
