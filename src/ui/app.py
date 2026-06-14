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

from .widgets import setup_fonts, Fonts, C, S, R, apple_pill_button, apply_theme, get_theme_name, CTK_PARCHMENT
from .task_tab import TaskTab
from .settings_tab import SettingsTab
from .library_tab import LibraryTab


class App:
    def __init__(self, language=None):
        self._config = load_config()
        theme_name = self._config.get("theme", "light")
        apply_theme(theme_name)

        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self._font_family, self._mono_family = setup_fonts()
        self.fonts = Fonts(self._font_family, self._mono_family)

        set_language(language if language is not None else self._config.get("language", ""))

        self.root.title(t("app.title"))
        self.root.geometry("1080x820")
        self.root.minsize(960, 680)
        self._apply_theme_to_ui(theme_name)

        self.downloader = None
        self._worker_thread = None
        self._browser_connected = False
        self._connecting = False
        self._pending_urls = []
        self._running = False

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._settings_tab.load()
        self.root.after(100, self._delayed_load)

    def _delayed_load(self):
        pass

    def _theme_palette(self, theme_name=None):
        if (theme_name or get_theme_name()) == "dark":
            return {
                "root": "#1C1C1E",
                "segment_fg": "#2C2C2E",
                "selected": "#3A3A3C",
                "selected_hover": "#48484A",
                "unselected": "#1C1C1E",
                "unselected_hover": "#2C2C2E",
                "text": "#FFFFFF",
            }
        return {
            "root": CTK_PARCHMENT,
            "segment_fg": "#E5E5EA",
            "selected": "#FFFFFF",
            "selected_hover": "#F2F2F7",
            "unselected": "#E5E5EA",
            "unselected_hover": "#D8D8DE",
            "text": "#1D1D1F",
        }

    def _apply_theme_to_ui(self, theme_name=None):
        palette = self._theme_palette(theme_name)
        self.root.configure(fg_color=palette["root"])
        if not hasattr(self, "_tabview"):
            return
        self._tabview.configure(
            fg_color=palette["root"],
            segmented_button_fg_color=palette["segment_fg"],
            segmented_button_selected_color=palette["selected"],
            segmented_button_selected_hover_color=palette["selected_hover"],
            segmented_button_unselected_color=palette["unselected"],
            segmented_button_unselected_hover_color=palette["unselected_hover"],
            text_color=palette["text"],
        )
        for tab_name in (t("tab.home"), t("tab.settings"), t("tab.library")):
            try:
                self._tabview.tab(tab_name).configure(fg_color=palette["root"])
            except Exception:
                pass

    def _build_ui(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(self.root, height=52, corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew")
        title_frame.grid_propagate(False)
        title_frame.grid_columnconfigure(1, weight=1)

        self._title_label = ctk.CTkLabel(title_frame, text=t("app.title"),
                                          font=self.fonts.title)
        self._title_label.grid(row=0, column=0, padx=(S.LG, S.SM), pady=S.SM)

        self._browser_indicator = ctk.CTkLabel(
            title_frame, text="● " + t("app.not_connected"),
            font=self.fonts.small, text_color=C.INK_MUTED_48)
        self._browser_indicator.grid(row=0, column=1, sticky="e", padx=S.LG, pady=S.SM)

        self._tabview = ctk.CTkTabview(self.root, corner_radius=R.LG)
        self._tabview.grid(row=1, column=0, sticky="nsew", padx=S.LG, pady=(S.XS, S.MD))

        self._tabview.add(t("tab.home"))
        self._tabview.add(t("tab.settings"))
        self._tabview.add(t("tab.library"))
        self._tabview.set(t("tab.home"))
        self._apply_theme_to_ui()

        self._task_tab = TaskTab(self._tabview.tab(t("tab.home")), self)
        self._settings_tab = SettingsTab(self._tabview.tab(t("tab.settings")), self)
        self._library_tab = LibraryTab(self._tabview.tab(t("tab.library")), self)

        status_frame = ctk.CTkFrame(self.root, height=28, corner_radius=0)
        status_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.status_var = tk.StringVar(value=t("status.ready"))
        ctk.CTkLabel(status_frame, textvariable=self.status_var,
                     font=self.fonts.caption, text_color=C.INK_MUTED_48).pack(
            side="left", padx=S.LG)

    def log(self, message: str):
        try:
            self._task_tab.log(message)
        except Exception:
            pass

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
        connect_btn = self._task_tab.get_connect_btn()
        launch_btn = self._task_tab.get_launch_btn()
        if connect_btn:
            connect_btn.configure(state="disabled", text="...")
        if launch_btn:
            launch_btn.configure(state="disabled")
        self._task_tab.set_browser_connecting()
        self._browser_indicator.configure(
            text="● " + t("app.connecting"), text_color=C.WARNING)

        def _do_connect():
            try:
                dler = ExHentaiDownloader(
                    download_dir=dl_dir,
                    library_paths=get_library_paths(),
                    chrome_debug_port=self._settings_tab.get_chrome_port(),
                    skip_page_threshold=self._config.get("skip_page_threshold", 5),
                    download_threads=self._config.get("download_threads", 2),
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
            text="● " + t("app.connected"), text_color=C.SUCCESS)
        connect_btn = self._task_tab.get_connect_btn()
        launch_btn = self._task_tab.get_launch_btn()
        if connect_btn:
            connect_btn.configure(state="disabled", text=t("settings.connected_btn"))
        if launch_btn:
            launch_btn.configure(state="disabled")
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
            text="● " + t("app.not_connected"), text_color=C.INK_MUTED_48)
        connect_btn = self._task_tab.get_connect_btn()
        launch_btn = self._task_tab.get_launch_btn()
        if connect_btn:
            connect_btn.configure(state="normal", text=t("settings.connect_browser"))
        if launch_btn:
            launch_btn.configure(state="normal")
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
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        if event_type == "log":
            self._task_tab.log(data.get("message", ""))
        elif event_type == "progress":
            self._task_tab._update_progress(data)
        elif event_type == "task_update":
            url = data.get("url", "")
            status = data.get("status", "")
            completed = data.get("completed", 0)
            failed = data.get("failed", 0)
            skipped = data.get("skipped", 0)
            total = data.get("total", 0)
            queue_cnt = max(total - completed - failed - skipped, 0)
            self._task_tab.update_queue_stats(queue_cnt, completed, failed, total, url, skipped)
            self._task_tab.update_task_item(url, status)
            self.set_status(t("task.queue_progress", done=completed + failed + skipped, total=total))

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

                if config.get("webp_to_png_after_extract"):
                    from ..imgchk.converter import convert_webp_to_png
                    from pathlib import Path
                    white_bg = config.get("white_bg_webp", False)
                    webp_count = 0
                    for root_dir, _, files in os.walk(extract_to):
                        for fname_iter in files:
                            fpath = Path(root_dir) / fname_iter
                            if fpath.suffix.lower() == ".webp":
                                ok, _, _ = convert_webp_to_png(fpath, white_bg)
                                if ok:
                                    webp_count += 1
                    if webp_count > 0:
                        self.log(t("download.webp_converted", count=webp_count))

                if config.get("scan_corrupt_after_extract"):
                    from ..imgchk.checker import is_corrupted_image
                    from pathlib import Path
                    corrupt_count = 0
                    for root_dir, _, files in os.walk(extract_to):
                        for fname_iter in files:
                            fpath = Path(root_dir) / fname_iter
                            if fpath.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}:
                                is_bad, reason = is_corrupted_image(fpath)
                                if is_bad:
                                    corrupt_count += 1
                    if corrupt_count > 0:
                        self.log(t("download.corrupt_found", count=corrupt_count, dir=extract_to))
                        self.log(t("download.corrupt_redownload"))
                        import shutil
                        import os as _os
                        try:
                            shutil.rmtree(extract_to)
                        except Exception:
                            pass
                        try:
                            if _os.path.exists(filepath):
                                _os.remove(filepath)
                        except Exception:
                            pass
                        
                        url = data.get("url", "")
                        if url and self.downloader:
                            self._pending_urls.append(url)
                            self.downloader.add_urls([url])
                            # If queue was empty it might be waiting, task tab needs a refresh
                            self.root.after(1000, self._task_tab.refresh_task_list)
                            if not self._running:
                                self.root.after(1000, self.start_download)
                    else:
                        self.log(t("download.corrupt_none", dir=extract_to))

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
        skipped = data.get("skipped", 0)
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

    def refresh_language(self, old_tasks=None, old_settings=None, old_library=None):
        self.root.title(t("app.title"))
        self._title_label.configure(text=t("app.title"))
        if self._browser_connected:
            self._browser_indicator.configure(text="● " + t("app.connected"), text_color=C.SUCCESS)
        elif self._connecting:
            self._browser_indicator.configure(text="● " + t("app.connecting"), text_color=C.WARNING)
        else:
            self._browser_indicator.configure(text="● " + t("app.not_connected"), text_color=C.INK_MUTED_48)
        if not self._running:
            self.status_var.set(t("status.ready"))

        del_name1 = old_tasks if old_tasks else t("tab.home")
        del_name2 = old_settings if old_settings else t("tab.settings")
        del_name3 = old_library if old_library else t("tab.library")
        self._tabview.delete(del_name1)
        self._tabview.delete(del_name2)
        self._tabview.delete(del_name3)
        self._tabview.add(t("tab.home"))
        self._tabview.add(t("tab.settings"))
        self._tabview.add(t("tab.library"))
        self._tabview.set(t("tab.home"))

        self._task_tab.refresh_language(self._tabview.tab(t("tab.home")))
        self._settings_tab.refresh_language(self._tabview.tab(t("tab.settings")))
        self._library_tab.refresh_language(self._tabview.tab(t("tab.library")))

    def set_theme(self, theme_name: str):
        state = self._capture_ui_state()
        apply_theme(theme_name, self.root)
        self._config["theme"] = theme_name
        if hasattr(self, "_library_tab"):
            self._settings_tab._save_options()
        self._rebuild_ui(state)

    def _capture_ui_state(self):
        state = {"selected_tab": None, "task_url_text": "", "task_log_text": ""}
        try:
            state["selected_tab"] = self._tabview.get()
        except Exception:
            pass
        try:
            state["task_url_text"] = self._task_tab.url_text.get("1.0", "end-1c")
        except Exception:
            pass
        try:
            self._task_tab.log_text.configure(state="normal")
            state["task_log_text"] = self._task_tab.log_text.get("1.0", "end-1c")
            self._task_tab.log_text.configure(state="disabled")
        except Exception:
            pass
        try:
            state["library"] = self._library_tab._gather_values()
        except Exception:
            pass
        return state

    def _restore_ui_state(self, state=None):
        if not state:
            return
        if state.get("task_url_text"):
            try:
                self._task_tab.url_text.delete("1.0", "end")
                self._task_tab.url_text.insert("1.0", state["task_url_text"])
            except Exception:
                pass
        if state.get("task_log_text"):
            try:
                self._task_tab.log_text.configure(state="normal")
                self._task_tab.log_text.insert("1.0", state["task_log_text"])
                self._task_tab.log_text.configure(state="disabled")
            except Exception:
                pass
        if state.get("library"):
            try:
                self._library_tab._restore_values(state["library"])
            except Exception:
                pass
        if self.downloader:
            self._task_tab.refresh_task_list()
        if self._browser_connected:
            self._browser_indicator.configure(text="● " + t("app.connected"), text_color=C.SUCCESS)
            self._task_tab.set_browser_connected()
        elif self._connecting:
            self._browser_indicator.configure(text="● " + t("app.connecting"), text_color=C.WARNING)
            self._task_tab.set_browser_connecting()
        else:
            self._browser_indicator.configure(text="● " + t("app.not_connected"), text_color=C.INK_MUTED_48)
            self._task_tab.set_browser_disconnected()
        if self._running:
            self._task_tab.set_running(True)
            self.set_status(t("app.downloading"))
        elif state.get("selected_tab"):
            try:
                self._tabview.set(state["selected_tab"])
            except Exception:
                pass

    def _rebuild_ui(self, state=None):
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._settings_tab.load()
        self._restore_ui_state(state)
        self.root.after(100, self._delayed_load)

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
        try:
            self._settings_tab._save_options()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()
