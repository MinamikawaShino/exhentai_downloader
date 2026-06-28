import os
import json

from . import DATA_DIR
from .db.library import get_library_paths

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DEFAULT_CONFIG = {
    "download_dir": os.path.join(os.getcwd(), "downloads"),
    "extract_dir": "",
    "chrome_port": 9222,
    "chrome_path": "",
    "user_data_dir": os.path.join(os.getcwd(), "EhentaiProfile"),
    "library_paths": [],
    "language": "",
    "auto_extract": False,
    "delete_after_extract": False,
    "notifications": True,
    "integrity_check": True,
    "download_threads": 2,
    "scan_threads": 12,
    "white_bg_webp": False,
    "db_enable": True,
    "error_dir": os.path.join(os.getcwd(), "Error"),
    "dedup_dir": os.path.join(os.getcwd(), "Duplicate"),
    "trash_dir": os.path.join(os.getcwd(), "Trash"),
    "theme": "light",
    "scan_corrupt_after_extract": False,
    "dedup_overlap_threshold": 50,
    "skip_page_threshold": 5,
    "webp_to_png_after_extract": False,
}


def _get_chrome_default() -> str:
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return ""


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if not os.path.exists(SETTINGS_FILE):
        if not cfg["chrome_path"]:
            cfg["chrome_path"] = _get_chrome_default()
        return cfg
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        for key in DEFAULT_CONFIG:
            if key in saved:
                cfg[key] = saved[key]
        if "library_paths" in saved and saved["library_paths"]:
            cfg["library_paths"] = list(set(saved["library_paths"]))
        else:
            cfg["library_paths"] = get_library_paths()
    except Exception:
        pass
    if not cfg["chrome_path"]:
        cfg["chrome_path"] = _get_chrome_default()
    if not cfg["user_data_dir"]:
        cfg["user_data_dir"] = os.path.join(os.getcwd(), "EhentaiProfile")
    return cfg


def save_config(cfg: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    to_save = {k: cfg.get(k, DEFAULT_CONFIG.get(k)) for k in DEFAULT_CONFIG}
    to_save["library_paths"] = get_library_paths()
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)
    except Exception:
        pass