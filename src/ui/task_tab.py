import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ..i18n import t
from ..utils.logging_utils import load_queue, load_failed_urls
from ..config import load_config
from .widgets import STATUS_COLORS, format_size, format_time, C, S, R, apple_pill_button, apple_ghost_button, apple_danger_button


class TaskTab:
    def __init__(self, parent, app):
        self.app = app
        self._task_widgets = {}
        self._stat_labels = {}
        self._parent = parent
        self._build(parent)

    def refresh_language(self, parent=None):
        url_text = self.url_text.get("1.0", "end-1c")
        log_lines = []
        try:
            self.log_text.configure(state="normal")
            log_lines = self.log_text.get("1.0", "end-1c")
        except Exception:
            pass

        for w in self._parent.winfo_children():
            w.destroy()

        if parent is not None:
            self._parent = parent
        self._task_widgets = {}
        self._stat_labels = {}
        self._build(self._parent)

        if url_text:
            self.url_text.insert("1.0", url_text)
        if log_lines:
            self.log_text.configure(state="normal")
            self.log_text.insert("1.0", log_lines)
            self.log_text.configure(state="disabled")

        if self.app.downloader:
            for url in self.app.downloader.get_queue():
                self._add_task_item(url, "PENDING")

    def _gather_values(self):
        return {
            "url_text": self.url_text.get("1.0", "end-1c"),
        }

    def _restore_values(self, vals):
        url_text = vals.get("url_text", "")
        if url_text:
            self.url_text.delete("1.0", "end")
            self.url_text.insert("1.0", url_text)

    def _build(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # URL input + browser + download controls
        url_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        url_frame.grid(row=0, column=0, sticky="ew", pady=(0, S.SM))
        url_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(url_frame, text=t("task.url_input"),
                     font=self.app.fonts.heading).grid(row=0, column=0, sticky="w", padx=S.LG, pady=(S.MD, S.XS))
        self.url_text = ctk.CTkTextbox(url_frame, height=80,
                                       font=self.app.fonts.textbox_body,
                                       corner_radius=R.MD)
        self.url_text.grid(row=1, column=0, sticky="ew", padx=S.LG, pady=(S.XS, S.XS))

        btn_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=S.LG, pady=(0, S.XS))
        apple_pill_button(btn_row, t("task.add_url"), self._add_urls, width=100).pack(side="left", padx=(0, S.XS))
        apple_ghost_button(btn_row, t("task.load_failed"), self._load_failed, width=90).pack(side="left", padx=S.XXS)
        apple_ghost_button(btn_row, t("task.load_queue"), self._load_queue, width=90).pack(side="left", padx=S.XXS)
        apple_danger_button(btn_row, t("task.clear"), self._clear_urls, width=70).pack(side="left", padx=S.XXS)

        # Download controls row
        ctrl_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        ctrl_row.grid(row=3, column=0, sticky="ew", padx=S.LG, pady=(0, S.XS))
        self.start_btn = apple_pill_button(ctrl_row, t("task.start"), self._start_download,
                                            width=100, color=C.SUCCESS, hover_color=C.SUCCESS_HOVER)
        self.start_btn.pack(side="left", padx=(0, S.XS))
        self.stop_btn = apple_danger_button(ctrl_row, t("task.stop"), self._stop_download, width=80)
        self.stop_btn.configure(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, S.XS))
        apple_ghost_button(ctrl_row, t("task.retry_failed"), self._retry_failed, width=90).pack(side="left", padx=S.XS)

        # Browser controls row
        browser_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        browser_row.grid(row=4, column=0, sticky="ew", padx=S.LG, pady=(0, S.MD))
        self._launch_btn = apple_pill_button(browser_row, t("settings.launch_browser"),
                                              self._launch_browser, width=120, color=C.SUCCESS,
                                              hover_color=C.SUCCESS_HOVER)
        self._launch_btn.pack(side="left", padx=(0, S.SM))
        self._connect_btn = apple_pill_button(browser_row, t("settings.connect_browser"),
                                                self._connect_browser, width=120)
        self._connect_btn.pack(side="left")
        self._browser_status = ctk.CTkLabel(browser_row, text="",
                                             font=self.app.fonts.body, text_color=C.INK_MUTED_48)
        self._browser_status.pack(side="left", padx=S.LG)
        apple_danger_button(browser_row, t("task.exit"), self.app.on_close, width=70).pack(side="right")

        # Stats
        stats_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, S.SM))
        cols = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cols.pack(fill="x", padx=S.LG, pady=S.MD)
        for i, key in enumerate(["queue", "completed", "failed", "current"]):
            ctk.CTkLabel(cols, text=t(f"task.stats.{key}") + ":",
                         font=self.app.fonts.caption, text_color=C.INK_MUTED_48).grid(
                row=0, column=i * 2, sticky="e", padx=(S.SM, S.XXS))
            lbl = ctk.CTkLabel(cols, text="0", font=self.app.fonts.heading)
            lbl.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, S.LG))
            self._stat_labels[key] = lbl
        cols.grid_columnconfigure(7, weight=1)

        # Progress
        prog_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        prog_frame.grid(row=2, column=0, sticky="ew", pady=(0, S.SM))
        self.file_label = ctk.CTkLabel(prog_frame, text=t("task.file_progress_ready"),
                                       font=self.app.fonts.body, text_color=C.INK_MUTED_48)
        self.file_label.pack(side="top", anchor="w", padx=S.LG, pady=(S.MD, S.XXS))
        self.file_progress = ctk.CTkProgressBar(prog_frame, height=6,
                                                 progress_color=C.PRIMARY,
                                                 fg_color=C.DIVIDER_SOFT)
        self.file_progress.pack(fill="x", padx=S.LG, pady=(0, S.XXS))
        self.file_progress.set(0)
        self.speed_label = ctk.CTkLabel(prog_frame, text="",
                                        font=self.app.fonts.caption, text_color=C.INK_MUTED_48)
        self.speed_label.pack(side="top", anchor="w", padx=S.LG, pady=(0, S.XS))

        self.queue_label = ctk.CTkLabel(prog_frame, text=t("task.queue_progress", done=0, total=0),
                                        font=self.app.fonts.body, text_color=C.INK_MUTED_48)
        self.queue_label.pack(side="top", anchor="w", padx=S.LG, pady=(0, S.XS))
        self.queue_progress = ctk.CTkProgressBar(prog_frame, height=6,
                                                   progress_color=C.PRIMARY,
                                                   fg_color=C.DIVIDER_SOFT)
        self.queue_progress.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        self.queue_progress.set(0)

        # Task list
        task_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        task_frame.grid(row=3, column=0, sticky="ew", pady=(0, S.SM))
        task_frame.grid_rowconfigure(1, weight=1)
        task_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(task_frame, text=t("task.task_list"),
                     font=self.app.fonts.heading).grid(row=0, column=0, sticky="nw", padx=S.LG, pady=(S.MD, S.XS))
        self.task_scroll = ctk.CTkScrollableFrame(task_frame, height=150)
        self.task_scroll.grid(row=1, column=0, sticky="nsew", padx=S.SM, pady=(0, S.SM))
        self.task_scroll.grid_columnconfigure(0, weight=1)

        # Log
        log_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        log_frame.grid(row=4, column=0, sticky="ew", pady=(0, S.SM))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text=t("task.log"),
                     font=self.app.fonts.heading).grid(row=0, column=0, sticky="nw", padx=S.LG, pady=(S.MD, S.XS))
        self.log_text = ctk.CTkTextbox(log_frame, font=self.app.fonts.textbox_small, wrap="word",
                                       corner_radius=R.MD, height=120)
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=S.LG, pady=(0, S.MD))
        self.log_text.configure(state="disabled")

    def get_connect_btn(self):
        return self._connect_btn

    def get_launch_btn(self):
        return self._launch_btn

    def log(self, message: str):
        print(message, flush=True)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _update_progress(self, data: dict):
        if data.get("done"):
            self.file_progress.set(0)
            self.file_label.configure(text=t("task.file_complete"))
            self.speed_label.configure(text="")
            return
        total = data.get("total", 1) or 1
        cur = data.get("current", 0)
        self.file_progress.set(cur / total)
        sb = data.get("speed_bytes", 0)
        if sb > 0:
            self.speed_label.configure(text=f"{format_size(sb)}/s")
        self.file_label.configure(
            text=t("task.file_downloading",
                   name=data.get("filename", ""),
                   current=format_size(cur),
                   total=format_size(total)))

    def _update_stats(self):
        if self.app.downloader:
            q = len(self.app.downloader.get_queue())
            self._stat_labels["queue"].configure(text=str(q))

    def set_running(self, running: bool):
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def _clear_urls(self):
        self.url_text.delete("1.0", "end")

    def _connect_browser(self):
        self.app.connect_browser()

    def _launch_browser(self):
        self.app._settings_tab._launch_browser()

    def set_browser_connected(self):
        self._connect_btn.configure(state="disabled", text=t("settings.connected_btn"))
        self._launch_btn.configure(state="disabled")
        self._browser_status.configure(text="● " + t("app.connected"), text_color=C.SUCCESS)

    def set_browser_connecting(self):
        self._connect_btn.configure(state="disabled", text="...")
        self._launch_btn.configure(state="disabled")
        self._browser_status.configure(text="● " + t("app.connecting"), text_color=C.WARNING)

    def set_browser_disconnected(self):
        self._connect_btn.configure(state="normal", text=t("settings.connect_browser"))
        self._launch_btn.configure(state="normal")
        self._browser_status.configure(text="● " + t("app.not_connected"), text_color=C.INK_MUTED_48)

    def _add_urls(self):
        text = self.url_text.get("1.0", "end-1c").strip()
        if not text:
            return
        urls = [l.strip() for l in text.splitlines() if l.strip().startswith("http")]
        if not urls:
            return
        if self.app._connecting:
            self.app._pending_urls.extend(urls)
            self.log(t("chrome.connecting"))
            self.url_text.delete("1.0", "end")
            return
        if not self.app.downloader:
            self.app._pending_urls.extend(urls)
            self.app.connect_browser()
            self.url_text.delete("1.0", "end")
            return
        self.app.downloader.add_urls(urls)
        for u in urls:
            if u not in self._task_widgets:
                self._add_task_item(u, "PENDING")
        self.url_text.delete("1.0", "end")
        self.log(t("queue.loaded", count=len(urls)))
        self._update_stats()

    def _load_failed(self):
        urls = load_failed_urls()
        if not urls:
            messagebox.showinfo("", t("task.no_failed"))
            return
        urls_list = list(urls)
        if self.app._connecting:
            self.app._pending_urls.extend(urls_list)
            return
        if not self.app.downloader:
            self.app._pending_urls.extend(urls_list)
            self.app.connect_browser()
            return
        self.app.downloader.add_urls(urls_list)
        for u in urls_list:
            if u not in self._task_widgets:
                self._add_task_item(u, "PENDING")
        self.log(t("queue.loaded", count=len(urls_list)))
        self._update_stats()

    def _load_queue(self):
        urls = load_queue()
        if not urls:
            messagebox.showinfo("", t("task.no_queue"))
            return
        if self.app._connecting:
            self.app._pending_urls.extend(urls)
            return
        if not self.app.downloader:
            self.app._pending_urls.extend(urls)
            self.app.connect_browser()
            return
        self.app.downloader.add_urls(urls)
        for u in urls:
            if u not in self._task_widgets:
                self._add_task_item(u, "PENDING")
        self.log(t("queue.loaded", count=len(urls)))
        self._update_stats()

    def _start_download(self):
        self.app.start_download()

    def _stop_download(self):
        self.app.stop_download()

    def _retry_failed(self):
        urls = load_failed_urls()
        if not urls:
            messagebox.showinfo("", t("task.no_failed"))
            return
        urls_list = list(urls)
        if self.app._connecting:
            self.app._pending_urls.extend(urls_list)
            return
        if not self.app.downloader:
            self.app._pending_urls.extend(urls_list)
            self.app.connect_browser()
            return
        self.app.downloader.add_urls(urls_list)
        for u in urls_list:
            if u not in self._task_widgets:
                self._add_task_item(u, "PENDING")
        self.log(t("queue.loaded", count=len(urls_list)))
        self._update_stats()
        if not self.app._running:
            self._start_download()

    def _add_task_item(self, url, status):
        row = ctk.CTkFrame(self.task_scroll, corner_radius=R.SM, height=36)
        row.pack(fill="x", pady=S.XXS, padx=S.XS)
        row.grid_columnconfigure(0, weight=1)
        short = url if len(url) <= 70 else url[:67] + "..."
        ctk.CTkLabel(row, text=short, anchor="w",
                     font=self.app.fonts.body).grid(row=0, column=0, sticky="w", padx=(S.SM, S.MD), pady=S.XXS)
        color = STATUS_COLORS.get(status, (C.INK_MUTED_48, C.INK_MUTED_48))[0]
        status_text = t(f"status.{status.lower()}")
        lbl = ctk.CTkLabel(row, text=status_text, text_color=color,
                           font=self.app.fonts.body_strong)
        lbl.grid(row=0, column=1, sticky="e", padx=S.SM, pady=S.XXS)
        self._task_widgets[url] = (row, lbl)

    def update_task_item(self, url, status):
        if url in self._task_widgets:
            _, lbl = self._task_widgets[url]
            color = STATUS_COLORS.get(status, (C.INK_MUTED_48, C.INK_MUTED_48))[0]
            status_text = t(f"status.{status.lower()}")
            lbl.configure(text=status_text, text_color=color)
        else:
            self._add_task_item(url, status)

    def refresh_task_list(self):
        for w in self._task_widgets.values():
            w[0].destroy()
        self._task_widgets.clear()
        if self.app.downloader:
            for url in self.app.downloader.get_queue():
                self._add_task_item(url, "PENDING")

    def update_queue_stats(self, queue_cnt: int, completed: int, failed: int, total: int, current_url: str = "", skipped: int = 0):
        self._stat_labels["queue"].configure(text=str(queue_cnt))
        self._stat_labels["completed"].configure(text=str(completed))
        self._stat_labels["failed"].configure(text=str(failed))
        self._stat_labels["current"].configure(text=os.path.basename(current_url) if current_url else "-")
        done = completed + failed + skipped
        self.queue_label.configure(text=t("task.queue_progress", done=done, total=total))
        self.queue_progress.set(done / total if total else 0)

    def reset_progress(self):
        self.file_progress.set(0)
        self.file_label.configure(text=t("task.file_progress_ready"))
        self.speed_label.configure(text="")
        self.queue_progress.set(1)
        self.queue_label.configure(text=t("task.queue_progress", done=0, total=0))
