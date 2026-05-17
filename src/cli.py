import os
import sys
import signal
from collections import deque

from .downloader_core import ExHentaiDownloader
from .i18n import t, set_language, available_languages
from .config import load_config
from .db.library import get_library_paths, get_all_library_names
from .utils.logging_utils import save_queue, load_failed_urls
from .utils.integrity import verify_zip_integrity, extract_zip
from .utils.metadata_scraper import scrape_gallery_metadata
from .db.metadata import save_gallery_metadata

shutdown_requested = False


def signal_handler(sig, frame):
    global shutdown_requested
    print(f"\n{t('status.interrupted')}")
    shutdown_requested = True


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


class CLIDownloader:
    def __init__(self, config: dict):
        self.config = config
        self.downloader = None
        self._progress_start = 0
        self._last_bytes = 0
        self._last_time = 0

    def run(self, urls: list):
        self.downloader = ExHentaiDownloader(
            download_dir=self.config["download_dir"],
            library_paths=get_library_paths(),
            chrome_debug_port=self.config["chrome_port"],
            skip_page_threshold=self.config.get("skip_page_threshold", 5),
            download_threads=self.config.get("download_threads", 2),
        )
        self.downloader.set_callback(self._on_event)
        self.downloader.set_urls(urls)

        print("\n" + "=" * 55)
        print("Waiting for browser...")
        print("1. Open Chrome with --remote-debugging-port=9222")
        print("2. Login to e-hentai.org and pass CloudFlare")
        print("3. Press Enter to begin")
        print("=" * 55)
        input()

        try:
            self.downloader.connect_browser()
            print("Browser connected! Starting tasks...")
        except Exception as e:
            print(f"Connection failed! Error: {e}")
            return

        self._scan_libraries()
        self.downloader.run()
        self.downloader.disconnect_browser()

    def _scan_libraries(self):
        paths = get_library_paths()
        if paths:
            print(t("status.scanning_dirs"))
            self.downloader.scan_libraries()
            names = get_all_library_names()
            print(t("lib.total", count=len(names)))

    def _on_event(self, event_type: str, data: dict):
        if event_type == "log":
            print(data.get("message", ""))
        elif event_type == "progress":
            if data.get("done"):
                self._handle_download_complete(data)
            else:
                self._handle_progress(data)
        elif event_type == "task_update":
            self._handle_task_update(data)
        elif event_type == "status":
            print(data.get("message", ""))
        elif event_type == "finished":
            self._handle_finished(data)

    def _handle_progress(self, data: dict):
        total = data.get("total", 1) or 1
        cur = data.get("current", 0)
        fname = data.get("filename", "")

        now = __import__("time").time()
        if self._last_time > 0:
            dt = now - self._last_time
            db = cur - self._last_bytes
            if dt > 0.5 and db > 0:
                speed = db / dt
                if cur < total:
                    eta_seconds = int((total - cur) / speed)
                    eta = format_time(eta_seconds)
                else:
                    eta = "0s"
                bar_len = 30
                done = int(bar_len * cur / total)
                bar = "=" * done + " " * (bar_len - done)
                print(f"\r[{bar}] {int(cur / total * 100)}%  "
                      f"{format_size(speed)}/s  ETA: {eta}  "
                      f"{fname}", end="", flush=True)
                self._last_bytes = cur
                self._last_time = now
                return
        self._last_bytes = cur
        self._last_time = now

    def _handle_download_complete(self, data: dict):
        fname = data.get("filename", "")
        print(f"\n{t('download.complete', filename=fname)}")
        self._last_bytes = 0
        self._last_time = 0

        fullpath = os.path.join(self.config["download_dir"], fname)

        if self.config.get("integrity_check") and os.path.exists(fullpath):
            if verify_zip_integrity(fullpath):
                print(t("download.integrity_check", filename=fname))
            else:
                print(t("download.integrity_fail", filename=fname))

        if self.config.get("auto_extract") and os.path.exists(fullpath):
            extract_dir = self.config.get("extract_dir", "").strip()
            if extract_dir:
                title = os.path.splitext(fname)[0]
                extract_to = os.path.join(extract_dir, title)
            else:
                extract_to = None
            print(t("download.auto_extract", filename=fname))
            if extract_zip(fullpath, extract_to):
                print(t("download.extract_done", filename=fname))
                if self.config.get("delete_after_extract"):
                    try:
                        os.remove(fullpath)
                        print(t("download.deleted_zip", filename=fname))
                    except Exception:
                        pass

        if self.downloader and self.downloader.driver:
            try:
                meta = scrape_gallery_metadata(self.downloader.driver)
                url = getattr(self.downloader, '_current_url', '')
                if url:
                    save_gallery_metadata(url=url, **meta)
                    print(t("meta.saved", title=meta.get("title", fname)))
            except Exception:
                pass

    def _handle_task_update(self, data: dict):
        url = data.get("url", "")
        status = data.get("status", "")
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        total = data.get("total", 0)
        label = t(f"status.{status.lower()}")
        if status == "PROCESSING":
            print(f"\n--- [{label}] {url}")
        else:
            print(f"[{label}] {url}")
        print(f"  Progress: {completed + failed + skipped}/{total}  "
              f"OK: {completed}  Fail: {failed}")

    def _handle_finished(self, data: dict):
        total = data.get("total", 0)
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        print(f"\n{t('status.finished', total=total, completed=completed, failed=failed)}")
        if self.config.get("notifications"):
            from .utils.notifications import send_notification
            send_notification(
                t("notify.download_complete"),
                t("notify.all_complete", completed=completed, failed=failed)
            )


def main():
    global shutdown_requested
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

    import argparse
    parser = argparse.ArgumentParser(description="ExHentai Gallery Downloader CLI")
    parser.add_argument("--language", "-l", choices=list(available_languages().keys()),
                        help="Set UI language")
    parser.add_argument("--download-dir", "-d", help="Download directory")
    parser.add_argument("--no-notify", action="store_true", help="Disable notifications")
    parser.add_argument("--no-integrity", action="store_true", help="Skip integrity check")
    parser.add_argument("--extract", action="store_true", help="Auto-extract ZIP after download")
    parser.add_argument("--extract-dir", dest="extract_dir", default=None,
                        help="Extract directory (default: same as download dir)")
    parser.add_argument("--delete-after-extract", action="store_true",
                        help="Delete ZIP after extraction")
    args = parser.parse_args()

    config = load_config()
    if args.language:
        config["language"] = args.language
    if args.download_dir:
        config["download_dir"] = args.download_dir
    if args.no_notify:
        config["notifications"] = False
    if args.no_integrity:
        config["integrity_check"] = False
    if args.extract:
        config["auto_extract"] = True
    if args.extract_dir:
        config["extract_dir"] = args.extract_dir
    if args.delete_after_extract:
        config["delete_after_extract"] = True

    set_language(config.get("language", ""))

    urls = []
    restored = load_queue()
    if restored:
        print(t("queue.restored", count=len(restored)))
        choice = input(t("queue.restore_prompt")).strip().lower()
        if choice != 'n':
            urls = restored

    if not urls:
        print(t("cli.enter_urls"))
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line:
                break
            url = line.strip()
            if url.startswith("http") and url not in urls:
                urls.append(url)

    if not urls:
        return

    cli = CLIDownloader(config)
    try:
        cli.run(urls)
    except Exception as e:
        print(t("download.fatal_error", error=e))
        if not shutdown_requested:
            remaining = [u for u in urls if u != getattr(cli.downloader, '_current_url', '')]
            save_queue(remaining)
    finally:
        if shutdown_requested:
            print(t("status.interrupted"))


if __name__ == "__main__":
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    main()
