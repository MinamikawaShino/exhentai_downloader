import os
import re
import datetime

from .. import LOG_DIR, ROOT_DIR
from ..i18n import t


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_failure(url: str, message: str):
    ensure_log_dir()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(LOG_DIR, "failed_downloads.txt")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {url} - {message}\n")
    except Exception:
        pass


def save_queue(urls: list):
    ensure_log_dir()
    queue_file = os.path.join(LOG_DIR, "pending_queue.txt")
    with open(queue_file, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + ("\n" if urls else ""))


def load_queue() -> list | None:
    queue_file = os.path.join(LOG_DIR, "pending_queue.txt")
    if not os.path.exists(queue_file):
        return None
    with open(queue_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    if urls:
        os.remove(queue_file)
        return urls
    return None


def load_failed_urls() -> set:
    fail_file = os.path.join(LOG_DIR, "failed_downloads.txt")
    if not os.path.exists(fail_file):
        return set()
    urls = set()
    with open(fail_file, "r", encoding="utf-8") as fh:
        for line in fh:
            m = re.search(r'https://exhentai\.org/g/\d+/[a-f0-9]+/', line)
            if m:
                urls.add(m.group(0))
    return urls
