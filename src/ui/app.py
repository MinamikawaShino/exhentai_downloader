import os
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ..downloader_core import ExHentaiDownloader
from ..i18n import t, set_language, get_language
from ..config import load_config
from ..db.library import get_library_paths
from ..utils.notifications import send_notification
from ..utils.integrity import verify_zip_integrity, extract_zip
from ..utils.metadata_scraper import scrape_gallery_metadata
from ..db.metadata import save_gallery_metadata

from .widgets import setup_fonts, Fonts
from .task_tab import TaskTab
from .settings_tab import SettingsTab


class App:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self._font_family, self._mono_family = setup_fonts()
        self.fonts = Fonts(self._font_family, self._mono_family)
        self.root.title(t("app.title"))
        self.root.geometry("1020x800")
        self.root.minsize(960, 680)

        self.downloader = None
        self._worker_thread = None
        self._browser_connected = False
        self._connecting = False
        self._pending_urls = []
        self._running = False
        self._config = load_config()

        set_language(self._config.get("language", ""))

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._settings_tab.load()
        self.root.after(100, self._delayed_load)

    def _delayed_load(self):
        pass

    def _build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        self._title_label = ctk.CTkLabel(title_frame, text=t("app.title"),
                     font=self.fonts.title)
        self._title_label.pack(side="left")
        self._browser_indicator = ctk.CTkLabel(
            title_frame, text="● " + t("app.not_connected"),
            text_color="gray50", font=self.fonts.subheading)
        self._browser_indicator.pack(side="right", padx=8)

        self._tabview = ctk.CTkTabview(self.root)
        self._tabview.grid(row=1, column=0, sticky="nsew", padx=12, pady=(2, 8))
        self._tabview.add(t("tab.home"))
        self._tabview.add(t("tab.settings"))
        self._tabview.set(t("tab.home"))

        self._task_tab = TaskTab(self._tabview.tab(t("tab.home")), self)
        self._settings_tab = SettingsTab(self._tabview.tab(t("tab.settings")), self)

        status_frame = ctk.CTkFrame(self.root, fg_color="transparent", height=28)
        status_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
        self.status_var = tk.StringVar(value=t("status.ready"))
        ctk.CTkLabel(status_frame, textvariable=self.status_var,
                     text_color="gray60", font=self.fonts.body).pack(side="left")

    def log(self, message: str):
        self._task_tab.log(message)

    def set_status(self, msg: str):
        self.status_var.set(msg)

    def connect_browser(self):
        if self._browser_connected:
            return
        if self._connecting:
            return
        dl_dir = self._settings_tab.get_download_dir()
        if not dl_dir:
            messagebox.showwarning("", t("config.no_download_dir"))
            return
        os.makedirs(dl_dir, exist_ok=True)

        self._connecting = True
        connect_btn = self._settings_tab.get_connect_btn()
        connect_btn.configure(state="disabled", text="...")
        self._task_tab.set_browser_connecting()
        self._browser_indicator.configure(
            text="● " + t("app.connecting"), text_color="#D4A017")
        self.log(t("app.connecting"))

        def _do_connect():
            try:
                dler = ExHentaiDownloader(
                    download_dir=dl_dir,
                    library_paths=get_library_paths(),
                    chrome_debug_port=self._settings_tab.get_chrome_port(),
                )
                dler.set_callback(self._on_event)
                dler.connect_browser()
                self.root.after(0, self._on_connect_success, dler)
            except Exception as e:
                self.root.after(0, self._on_connect_error, e)

        threading.Thread(target=_do_connect, daemon=True).start()

    def _on_connect_success(self, dler):
        self.downloader = dler
        self._browser_connected = True
        self._connecting = False
        self._browser_indicator.configure(
            text="● " + t("app.connected"), text_color="#2ECC71")
        connect_btn = self._settings_tab.get_connect_btn()
        connect_btn.configure(state="disabled", text=t("settings.connected_btn"))
        self._task_tab.set_browser_connected()
        self.log(t("chrome.connect_success"))
        if self._pending_urls:
            self.downloader.add_urls(self._pending_urls)
            self.log(t("queue.loaded", count=len(self._pending_urls)))
            self._pending_urls.clear()
        self._task_tab.refresh_task_list()
        self._task_tab._update_stats()
        self._settings_tab._save_options()
        if self.downloader.get_queue():
            self.start_download()

    def _on_connect_error(self, e):
        self._connecting = False
        self._browser_indicator.configure(
            text="● " + t("app.not_connected"), text_color="gray50")
        connect_btn = self._settings_tab.get_connect_btn()
        connect_btn.configure(state="normal", text=t("settings.connect_browser"))
        self._task_tab.set_browser_disconnected()
        self.downloader = None
        self._pending_urls.clear()
        self.log(t("chrome.connection_fail", error=e))
        messagebox.showerror(t("chrome.connect_fail"), str(e))

    def start_download(self):
        if not self.downloader or not self._browser_connected:
            messagebox.showwarning("", t("task.connect_first"))
            return
        if not self.downloader.get_queue():
            messagebox.showwarning("", t("task.queue_empty"))
            return
        self._running = True
        self._task_tab.set_running(True)
        self._worker_thread = threading.Thread(
            target=self.downloader.run, daemon=True)
        self._worker_thread.start()
        self.log("=== " + t("task.start") + " ===")
        self.set_status(t("app.downloading"))

    def stop_download(self):
        if self.downloader:
            self.downloader.request_shutdown()
        self.log(t("app.stopping"))
        self.set_status(t("app.stopping"))

    def _on_event(self, event_type, data):
        self.root.after(0, self._handle_event, event_type, data)

    def _handle_event(self, event_type, data):
        if event_type == "log":
            self._task_tab.log(data.get("message", ""))
        elif event_type == "progress":
            self._task_tab._update_progress(data)
        elif event_type == "task_update":
            url = data.get("url", "")
            status = data.get("status", "")
            completed = data.get("completed", 0)
            failed = data.get("failed", 0)
            total = data.get("total", 0)
            queue_cnt = total - completed - failed
            self._task_tab.update_queue_stats(queue_cnt, completed, failed, total, url)
            self._task_tab.update_task_item(url, status)
            self.set_status(t("task.queue_progress", done=completed + failed, total=total))

            if status == "COMPLETED":
                self._on_task_completed(url)
        elif event_type == "file_completed":
            self._on_file_completed(data)
        elif event_type == "status":
            self._task_tab.log(data.get("message", ""))
        elif event_type == "finished":
            self._on_finished(data)

    def _on_task_completed(self, url):
        if self.downloader and self.downloader.driver:
            try:
                meta = scrape_gallery_metadata(self.downloader.driver)
                save_gallery_metadata(url=url, **meta)
                self.log(t("meta.saved", title=meta.get("title", "")))
            except Exception:
                pass

    def _on_file_completed(self, data):
        filepath = data.get("filepath", "")
        title = data.get("title", "")
        if not filepath or not os.path.exists(filepath):
            return

        config = load_config()
        fname = os.path.basename(filepath)

        if config.get("integrity_check"):
            if verify_zip_integrity(filepath):
                self.log(t("download.integrity_check", filename=fname))
            else:
                self.log(t("download.integrity_fail", filename=fname))

        if config.get("auto_extract"):
            extract_dir = config.get("extract_dir", "").strip()
            if extract_dir:
                extract_to = os.path.join(extract_dir, title)
            else:
                extract_to = os.path.splitext(filepath)[0]

            self.log(t("download.auto_extract", filename=fname))
            if extract_zip(filepath, extract_to):
                self.log(t("download.extract_done", filename=fname))
                if config.get("delete_after_extract"):
                    try:
                        os.remove(filepath)
                        self.log(t("download.deleted_zip", filename=fname))
                    except Exception:
                        pass

    def _on_finished(self, data):
        total = data.get("total", 0)
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        self._running = False
        self._task_tab.set_running(False)
        self._task_tab.reset_progress()
        self._task_tab._stat_labels["queue"].configure(text="0")
        self._task_tab._stat_labels["completed"].configure(text=str(completed))
        self._task_tab._stat_labels["failed"].configure(text=str(failed))
        self._task_tab._stat_labels["current"].configure(text="-")
        self.log(t("status.finished", total=total, completed=completed, failed=failed))
        self.set_status(t("status.ready"))

        if config := load_config():
            if config.get("notifications"):
                send_notification(
                    t("notify.download_complete"),
                    t("notify.all_complete", completed=completed, failed=failed)
                )

    def refresh_language(self, old_tasks=None, old_settings=None):
        self.root.title(t("app.title"))
        self._title_label.configure(text=t("app.title"))
        if self._browser_connected:
            self._browser_indicator.configure(text="● " + t("app.connected"))
        elif self._connecting:
            self._browser_indicator.configure(text="● " + t("app.connecting"))
        else:
            self._browser_indicator.configure(text="● " + t("app.not_connected"))
        if not self._running:
            self.status_var.set(t("status.ready"))

        del_name1 = old_tasks if old_tasks else t("tab.home")
        del_name2 = old_settings if old_settings else t("tab.settings")
        self._tabview.delete(del_name1)
        self._tabview.delete(del_name2)
        self._tabview.add(t("tab.home"))
        self._tabview.add(t("tab.settings"))
        self._tabview.set(t("tab.home"))

        self._task_tab.refresh_language(self._tabview.tab(t("tab.home")))
        self._settings_tab.refresh_language(self._tabview.tab(t("tab.settings")))

    def on_close(self):
        if self.downloader:
            self.downloader.request_shutdown()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3)
        if self.downloader:
            try:
                self.downloader.disconnect_browser()
            except Exception:
                pass
        self._settings_tab._save_options()
        self.root.destroy()

    def run(self):
        self.root.mainloop()