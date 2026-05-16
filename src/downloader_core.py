import os
import time
import socket
import threading
from collections import deque
from enum import Enum, auto

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .i18n import t
from .db.library import scan_path_to_db, get_all_library_names, get_library_paths
from .utils.filename import sanitize_filename, normalize_for_comparison
from .utils.logging_utils import log_failure, save_queue

MAX_DOWNLOAD_RETRIES = 3
RETRY_BACKOFF_BASE = 5
_USER_CANCELLED = "user_cancelled"


class TaskStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


def _check_port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


class ExHentaiDownloader:
    def __init__(self, download_dir, library_paths, chrome_debug_port=9222):
        self.download_dir = download_dir
        self.library_paths = list(library_paths) if library_paths else []
        self.chrome_debug_port = chrome_debug_port

        self.driver = None
        self._shutdown_flag = threading.Event()
        self._task_queue = deque()
        self._local_library = set()
        self.callback = None
        self._current_url = None
        self._last_progress_emit = 0
        self._last_progress_bytes = 0

    def set_callback(self, callback):
        self.callback = callback

    def _emit(self, event_type, **data):
        if self.callback:
            try:
                self.callback(event_type, data)
            except Exception:
                pass

    def set_urls(self, urls):
        self._task_queue = deque(urls)

    def add_urls(self, urls):
        existing = set(self._task_queue)
        for u in urls:
            if u not in existing:
                self._task_queue.append(u)
                existing.add(u)

    def get_queue(self):
        return list(self._task_queue)

    def request_shutdown(self):
        self._shutdown_flag.set()

    def is_shutdown(self):
        return self._shutdown_flag.is_set()

    def connect_browser(self):
        t0 = time.time()
        if not _check_port_open("127.0.0.1", self.chrome_debug_port):
            raise RuntimeError(
                t("chrome.port_not_open", port=self.chrome_debug_port)
            )
        self._emit("log", message=f"[DEBUG] Port reachable ({time.time() - t0:.1f}s)")

        t1 = time.time()
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.chrome_debug_port}")
        self._emit("log", message=f"[DEBUG] ChromeOptions ready ({time.time() - t1:.1f}s)")

        t2 = time.time()
        service = Service()
        service.creation_flags = 0x08000000
        self.driver = webdriver.Chrome(service=service, options=options)
        self._emit("log", message=f"[DEBUG] webdriver.Chrome created ({time.time() - t2:.1f}s)")

        t3 = time.time()
        self.driver.set_page_load_timeout(30)
        try:
            self.driver.get("about:blank")
            self._emit("log", message=f"[DEBUG] about:blank ({time.time() - t3:.1f}s)")
        except Exception:
            pass

        self._emit("log", message=f"[DEBUG] Total connection time: {time.time() - t0:.1f}s")
        return True

    def disconnect_browser(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def scan_libraries(self):
        total = 0
        for path in self.library_paths:
            n = scan_path_to_db(path)
            total += n
            self._emit("log", message=t("lib.scanning", path=path))
            self._emit("log", message=t("lib.scan_done", count=n))
        self._local_library = get_all_library_names()
        return len(self._local_library)

    def run(self):
        self._shutdown_flag.clear()
        self._emit("status", message=t("status.scanning"))

        if not self._local_library:
            self._local_library = get_all_library_names()

        self._emit("status", message=t("status.library_loaded", count=len(self._local_library)))

        if self.library_paths:
            self._emit("log", message=t("status.scanning_dirs"))
            self.scan_libraries()
            self._emit("log", message=t("lib.total", count=len(self._local_library)))

        completed = 0
        failed = 0

        while self._task_queue:
            if self._shutdown_flag.is_set():
                remaining = list(self._task_queue)
                if self._current_url:
                    remaining.insert(0, self._current_url)
                save_queue(remaining)
                self._emit("status", message=t("status.interrupted"))
                total = len(self._task_queue) + completed + failed + (1 if self._current_url else 0)
                self._emit("finished", total=total, completed=completed, failed=failed)
                return

            url = self._task_queue.popleft()
            self._current_url = url
            total = len(self._task_queue) + completed + failed + 1
            self._emit("task_update", url=url, status=TaskStatus.PROCESSING.name,
                       completed=completed, failed=failed, total=total)

            result = self._process_one(url)

            total = len(self._task_queue) + completed + failed
            if result == "completed":
                completed += 1
                total += 1
                self._emit("task_update", url=url, status=TaskStatus.COMPLETED.name,
                           completed=completed, failed=failed, total=total)
            elif result == "skipped":
                self._emit("task_update", url=url, status=TaskStatus.SKIPPED.name,
                           completed=completed, failed=failed, total=total)
            else:
                failed += 1
                total += 1
                self._emit("task_update", url=url, status=TaskStatus.FAILED.name,
                           completed=completed, failed=failed, total=total)

            if self._shutdown_flag.is_set():
                remaining = list(self._task_queue)
                if self._current_url:
                    remaining.insert(0, self._current_url)
                save_queue(remaining)
                self._emit("finished", total=total, completed=completed, failed=failed)
                return

        self._emit("finished", total=completed + failed, completed=completed, failed=failed)

    def _process_one(self, url):
        self._emit("log", message=t("download.processing", url=url))
        main_window = None
        try:
            for nav_attempt in range(3):
                if self._shutdown_flag.is_set():
                    return "failed"
                try:
                    self.driver.get(url)
                    break
                except Exception:
                    if nav_attempt < 2:
                        time.sleep(2)
                    else:
                        raise

            main_window = self.driver.current_window_handle

            if self._shutdown_flag.is_set():
                return "failed"

            title = self._wait_for_title()
            if title is None:
                return "failed"

            safe_title = sanitize_filename(title)
            safe_filename_zip = os.path.join(self.download_dir, safe_title + ".zip")

            if os.path.exists(safe_filename_zip):
                self._emit("log", message=t("download.file_exists", title=safe_title))
                return "skipped"
            if normalize_for_comparison(safe_title) in self._local_library:
                self._emit("log", message=t("download.in_library", title=safe_title))
                return "skipped"

            if self._shutdown_flag.is_set():
                return "failed"

            self._emit("log", message=t("download.gallery_title", title=safe_title))

            archive_link = self._find_archive_link()
            if archive_link is None:
                log_failure(url, t("download.no_archive"))
                return "failed"

            new_window_found = self._click_and_wait_for_window(archive_link, main_window)
            if not new_window_found:
                log_failure(url, t("download.no_window"))
                return "failed"

            for w in self.driver.window_handles:
                if w != main_window:
                    self.driver.switch_to.window(w)
                    break

            download_url = self._get_download_url(main_window)
            if not download_url:
                log_failure(url, t("download.link_fail"))
                self._close_extra_tab(main_window)
                return "failed"

            if self._shutdown_flag.is_set():
                self._close_extra_tab(main_window)
                return "failed"

            self._emit("log", message=t("download.getting_link"))

            real_user_agent = self.driver.execute_script("return navigator.userAgent;")
            selenium_cookies = self.driver.get_cookies()
            requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

            success, error = self._download_file(
                download_url, safe_filename_zip, requests_cookies, real_user_agent)

            self._close_extra_tab(main_window)

            if not success and error != _USER_CANCELLED:
                log_failure(url, t("download.failed_http", filename=safe_title, error=error))
                return "failed"

            self._emit("file_completed", url=url, filepath=safe_filename_zip, title=safe_title)
            return "completed"

        except Exception as e:
            self._emit("log", message=t("download.fatal_error", error=e))
            log_failure(url, t("download.fatal_error", error=e))
            self._cleanup_windows(main_window)
            return "failed"

    def _wait_for_title(self):
        for title_attempt in range(3):
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "gn")))
                gj = self.driver.find_element(By.ID, "gj")
                title = gj.text.strip()
                if not title:
                    title = self.driver.find_element(By.ID, "gn").text.strip()
                return title
            except Exception:
                if title_attempt < 2:
                    self._emit("log", message=t("download.title_load_fail", attempt=title_attempt + 1))
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except Exception:
                        time.sleep(3)
                else:
                    self._emit("log", message=t("download.title_fail"))
                    log_failure(self._current_url, t("download.title_fail"))
                    return None
        return None

    def _find_archive_link(self):
        try:
            return self.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Archive Download')]")
        except NoSuchElementException:
            self._emit("log", message=t("download.no_archive"))
            return None

    def _click_and_wait_for_window(self, archive_link, main_window):
        try:
            archive_link.click()
        except Exception:
            pass

        for win_attempt in range(3):
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: len(d.window_handles) > 1)
                return True
            except TimeoutException:
                if win_attempt < 2:
                    self._emit("log", message=t("download.window_timeout", attempt=win_attempt + 1))
                    try:
                        self.driver.switch_to.window(main_window)
                        archive_link = self.driver.find_element(
                            By.XPATH, "//a[contains(text(), 'Archive Download')]")
                        archive_link.click()
                    except Exception:
                        pass
                    time.sleep(2)
        return False

    def _get_download_url(self, main_window):
        for attempt in range(3):
            if self._shutdown_flag.is_set():
                return None
            try:
                if attempt > 0:
                    self.driver.refresh()
                    time.sleep(2)
                try:
                    cancel_btn = self.driver.find_element(
                        By.XPATH,
                        "//form/div/input[@name='invalidate_session' and @value='Cancel Archive']")
                    cancel_btn.click()
                    time.sleep(2)
                except Exception:
                    pass

                try:
                    final_link_elem = self.driver.find_element(
                        By.LINK_TEXT, "Click Here To Start Downloading")
                    return final_link_elem.get_attribute('href')
                except Exception:
                    try:
                        download_button = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//input[@value='Download Original Archive']")))
                    except Exception:
                        download_button = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located(
                                (By.XPATH,
                                 "//input[@type='submit' and contains(@value, 'Download')]")))

                    download_button.click()
                    final_link_elem = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located(
                            (By.LINK_TEXT, "Click Here To Start Downloading")))
                    return final_link_elem.get_attribute('href')
            except Exception:
                if attempt < 2:
                    time.sleep(10)
        return None

    def _close_extra_tab(self, main_window):
        try:
            self.driver.close()
            self.driver.switch_to.window(main_window)
        except Exception:
            pass

    def _cleanup_windows(self, main_window):
        if not main_window:
            return
        try:
            for w in list(self.driver.window_handles):
                if w != main_window:
                    try:
                        self.driver.switch_to.window(w)
                        self.driver.close()
                    except Exception:
                        pass
            self.driver.switch_to.window(main_window)
        except Exception:
            pass

    def _download_file(self, url, filename, cookies, user_agent):
        for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
            if self._shutdown_flag.is_set():
                return False, _USER_CANCELLED
            success, error = self._download_attempt(url, filename, cookies, user_agent)
            if success:
                return True, None
            if error == _USER_CANCELLED:
                return False, error
            if attempt < MAX_DOWNLOAD_RETRIES:
                wait = RETRY_BACKOFF_BASE * attempt
                self._emit("log", message=t("download.retry", attempt=attempt, max=MAX_DOWNLOAD_RETRIES, wait=wait))
                for _ in range(wait):
                    if self._shutdown_flag.is_set():
                        return False, _USER_CANCELLED
                    time.sleep(1)
            else:
                self._emit("log", message=t("download.max_retries", max=MAX_DOWNLOAD_RETRIES))
                return False, error
        return False, error

    def _download_attempt(self, url, filename, cookies, user_agent):
        fname = os.path.basename(filename)
        headers = {'User-Agent': user_agent} if user_agent else {}
        part_filename = filename + ".part"
        downloaded = 0

        if os.path.exists(part_filename):
            downloaded = os.path.getsize(part_filename)
            if downloaded > 0:
                headers['Range'] = f'bytes={downloaded}-'
                self._emit("log", message=t("download.resuming", size=downloaded))

        try:
            with requests.get(url, stream=True, cookies=cookies, headers=headers,
                              timeout=(30, 180)) as r:
                r.raise_for_status()

                if r.status_code == 206:
                    cr = r.headers.get('content-range', '')
                    if '/' in cr:
                        total_length = int(cr.rsplit('/', 1)[1])
                    else:
                        total_length = downloaded + int(r.headers.get('content-length', 0))
                    mode = 'ab'
                else:
                    total_length = r.headers.get('content-length')
                    if total_length is not None:
                        total_length = int(total_length)
                    mode = 'wb'
                    downloaded = 0

                with open(part_filename, mode) as f:
                    if total_length is None:
                        f.write(r.content)
                    else:
                        dl = downloaded
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                now = time.time()
                                if now - self._last_progress_emit > 0.15:
                                    speed = 0
                                    if self._last_progress_bytes > 0 and now > self._last_progress_emit:
                                        speed = int((dl - self._last_progress_bytes) / (now - self._last_progress_emit))
                                    self._emit("progress", filename=fname,
                                               current=dl, total=total_length,
                                               speed_bytes=speed)
                                    self._last_progress_emit = now
                                    self._last_progress_bytes = dl
                            if self._shutdown_flag.is_set():
                                f.flush()
                                self._emit("log", message=t("download.saved_progress"))
                                return False, _USER_CANCELLED

                os.replace(part_filename, filename)
                self._emit("progress", filename=fname, current=total_length or 0,
                           total=total_length or 1, done=True)
                self._emit("log", message=t("download.complete", filename=fname))
                return True, None

        except requests.exceptions.HTTPError as e:
            self._emit("log", message=t("download.failed_http", filename=fname, error=e))
            if os.path.exists(part_filename):
                if os.path.getsize(part_filename) == 0:
                    os.remove(part_filename)
                else:
                    self._emit("log", message=t("download.part_kept", filename=fname))
            return False, e
        except Exception as e:
            self._emit("log", message=t("download.interrupted", filename=fname, error=e))
            if os.path.exists(part_filename):
                if os.path.getsize(part_filename) == 0:
                    os.remove(part_filename)
                else:
                    self._emit("log", message=t("download.part_kept", filename=fname))
            return False, e