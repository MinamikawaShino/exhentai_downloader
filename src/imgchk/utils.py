import os
import ctypes
import threading
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from .config import IMAGE_EXTENSIONS, WEBP_EXTENSIONS

_interrupted = False
_print_lock = threading.Lock()
_counter_lock = threading.Lock()
_checked = 0


def is_interrupted() -> bool:
    return _interrupted


def request_stop():
    global _interrupted
    _interrupted = True


def reset_interrupt():
    global _interrupted
    _interrupted = False


def reset_checked():
    global _checked
    _checked = 0


def increment_checked() -> int:
    global _checked
    with _counter_lock:
        _checked += 1
        return _checked


def get_checked() -> int:
    return _checked


def print_lock():
    return _print_lock


def is_image_file(filepath: Path) -> bool:
    return filepath.suffix.lower() in IMAGE_EXTENSIONS


def is_webp_file(filepath: Path) -> bool:
    return filepath.suffix.lower() in WEBP_EXTENSIONS


def resolve_long_path(p: str) -> str:
    if not p:
        return p
    if os.name == "nt":
        p = os.path.abspath(p)
        if p.startswith("\\\\?\\"):
            return p
        if p.startswith("\\\\"):
            return "\\\\?\\UNC\\" + p.lstrip("\\")
        return "\\\\?\\" + p
    return os.path.abspath(p)


def restore_timestamps(filepath: str, ctime: float, atime: float, mtime: float):
    try:
        os.utime(filepath, (atime, mtime))
        if os.name == "nt":
            def ts_to_filetime(ts):
                return int((ts + 11644473600) * 10000000)

            OPEN_EXISTING = 3
            FILE_WRITE_ATTRIBUTES = 256
            FILE_ATTRIBUTE_NORMAL = 128
            handle = ctypes.windll.kernel32.CreateFileW(
                filepath, FILE_WRITE_ATTRIBUTES, 0, None,
                OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
            )
            if handle not in (-1, 0):
                c_ft = wintypes.FILETIME()
                win_ct = ts_to_filetime(ctime)
                c_ft.dwLowDateTime = win_ct & 0xFFFFFFFF
                c_ft.dwHighDateTime = win_ct >> 32
                ctypes.windll.kernel32.SetFileTime(
                    handle, ctypes.byref(c_ft), None, None
                )
                ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        pass


def collect_image_files(source_dir: Path) -> list[Path]:
    files = []
    for root, _dirs, filenames in os.walk(source_dir):
        for filename in filenames:
            filepath = Path(root) / filename
            if is_image_file(filepath) or is_webp_file(filepath):
                files.append(filepath)
    return files


def format_progress(current: int, total: int, width: int = 40) -> str:
    if total == 0:
        pct = 100.0
    else:
        pct = current / total * 100
    filled = int(width * current / total) if total else width
    bar = "█" * filled + "░" * (width - filled)
    return f"|{bar}| {current}/{total} ({pct:5.1f}%)"