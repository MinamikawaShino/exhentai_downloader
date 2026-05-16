import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ..i18n import t
from ..utils.logging_utils import load_queue, load_failed_urls
from ..config import load_config
from .widgets import STATUS_COLORS, format_size, format_time


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

    def _build(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=3)
        parent.grid_rowconfigure(5, weight=1)

        url_frame = ctk.CTkFrame(parent)
        url_frame.grid(row=0, column=0, sticky="ew", pady=(8, 4))
        url_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(url_frame, text=t("task.url_input"),
                     font=self.app.fonts.subheading).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
        self.url_text = ctk.CTkTextbox(url_frame, height=80,
                                       font=self.app.fonts.mono_body)
        self.url_text.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 4))

        btn_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkButton(btn_row, text=t("task.add_url"), width=90,
                      command=self._add_urls).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text=t("task.load_failed"), width=80, fg_color="gray40",
                      command=self._load_failed).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text=t("task.load_queue"), width=80, fg_color="gray40",
                      command=self._load_queue).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text=t("task.clear"), width=80, fg_color="transparent", border_width=1,
                      command=self._clear_urls).pack(side="left", padx=2)

        # Stats
        stats_frame = ctk.CTkFrame(parent)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        cols = ctk.CTkFrame(stats_frame, fg_color="transparent")
        cols.pack(fill="x", padx=12, pady=8)
        for i, key in enumerate(["queue", "completed", "failed", "current"]):
            ctk.CTkLabel(cols, text=t(f"task.stats.{key}") + ":",
                         text_color="gray50", font=self.app.fonts.body).grid(
                row=0, column=i * 2, sticky="e", padx=(16, 4))
            lbl = ctk.CTkLabel(cols, text="0", font=self.app.fonts.subheading)
            lbl.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 18))
            self._stat_labels[key] = lbl
        cols.grid_columnconfigure(7, weight=1)

        # File progress
        prog_frame = ctk.CTkFrame(parent)
        prog_frame.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.file_label = ctk.CTkLabel(prog_frame, text=t("task.file_progress_ready"),
                                       text_color="gray60", font=self.app.fonts.body)
        self.file_label.pack(side="top", anchor="w", padx=12, pady=(8, 0))
        self.file_progress = ctk.CTkProgressBar(prog_frame, height=8)
        self.file_progress.pack(fill="x", padx=12, pady=(2, 0))
        self.file_progress.set(0)
        self.speed_label = ctk.CTkLabel(prog_frame, text="",
                                        text_color="gray50", font=self.app.fonts.small)
        self.speed_label.pack(side="top", anchor="w", padx=12)

        self.queue_label = ctk.CTkLabel(prog_frame, text=t("task.queue_progress", done=0, total=0),
                                        text_color="gray60", font=self.app.fonts.body)
        self.queue_label.pack(side="top", anchor="w", padx=12)
        self.queue_progress = ctk.CTkProgressBar(prog_frame, height=8)
        self.queue_progress.pack(fill="x", padx=12, pady=(2, 6))
        self.queue_progress.set(0)

        # Task list
        task_frame = ctk.CTkFrame(parent)
        task_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 6))
        task_frame.grid_rowconfigure(0, weight=1)
        task_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(task_frame, text=t("task.task_list"),
                     font=self.app.fonts.subheading).grid(row=0, column=0, sticky="nw", padx=8, pady=(6, 0))
        self.task_scroll = ctk.CTkScrollableFrame(task_frame)
        self.task_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 4))
        self.task_scroll.grid_columnconfigure(0, weight=1)

        # Log
        log_frame = ctk.CTkFrame(parent)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=4)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text=t("task.log"),
                     font=self.app.fonts.subheading).grid(row=0, column=0, sticky="nw", padx=8, pady=(6, 0))
        self.log_text = ctk.CTkTextbox(log_frame, font=self.app.fonts.mono_small, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 4))
        self.log_text.configure(state="disabled")

        # Controls
        ctrl_frame = ctk.CTkFrame(parent)
        ctrl_frame.grid(row=6, column=0, sticky="ew")

        browser_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        browser_row.pack(fill="x", padx=8, pady=(6, 0))
        self._launch_btn = ctk.CTkButton(browser_row, text=t("settings.launch_browser"), width=100,
                                         fg_color="#2ECC71", hover_color="#27AE60",
                                         command=self._launch_browser)
        self._launch_btn.pack(side="left", padx=(0, 6))
        self._connect_btn = ctk.CTkButton(browser_row, text=t("settings.connect_browser"), width=100,
                                          command=self._connect_browser)
        self._connect_btn.pack(side="left")
        self._browser_status = ctk.CTkLabel(browser_row, text="", text_color="gray50",
                                            font=self.app.fonts.body)
        self._browser_status.pack(side="left", padx=12)

        pad = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        pad.pack(fill="x", padx=8, pady=(2, 6))
        self.start_btn = ctk.CTkButton(pad, text=t("task.start"), width=110, fg_color="#2ECC71",
                                       hover_color="#27AE60", command=self._start_download)
        self.start_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ctk.CTkButton(pad, text=t("task.stop"), width=90, fg_color="#E74C3C",
                                      hover_color="#C0392B", state="disabled", command=self._stop_download)
        self.stop_btn.pack(side="left", padx=(0, 6))
        ctk.CTkButton(pad, text=t("task.retry_failed"), width=90, fg_color="gray40",
                      command=self._retry_failed).pack(side="left", padx=2)
        ctk.CTkButton(pad, text=t("task.exit"), width=70, fg_color="transparent", border_width=1,
                      command=self.app.on_close).pack(side="right", padx=2)

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
        self._browser_status.configure(text="● " + t("app.connected"), text_color="#2ECC71")

    def set_browser_connecting(self):
        self._connect_btn.configure(state="disabled", text="...")
        self._launch_btn.configure(state="disabled")
        self._browser_status.configure(text="● " + t("app.connecting"), text_color="#D4A017")

    def set_browser_disconnected(self):
        self._connect_btn.configure(state="normal", text=t("settings.connect_browser"))
        self._launch_btn.configure(state="normal")
        self._browser_status.configure(text="● " + t("app.not_connected"), text_color="gray50")

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
        row = ctk.CTkFrame(self.task_scroll, fg_color="transparent", height=32)
        row.pack(fill="x", pady=2)
        short = url if len(url) <= 70 else url[:67] + "..."
        ctk.CTkLabel(row, text=short, anchor="w",
                     font=self.app.fonts.body).pack(side="left", padx=(6, 10))
        color = STATUS_COLORS.get(status, ("gray50", "gray30"))[0]
        status_text = t(f"status.{status.lower()}")
        lbl = ctk.CTkLabel(row, text=status_text, text_color=color,
                           font=self.app.fonts.body)
        lbl.pack(side="right", padx=6)
        self._task_widgets[url] = (row, lbl)

    def update_task_item(self, url, status):
        if url in self._task_widgets:
            _, lbl = self._task_widgets[url]
            color = STATUS_COLORS.get(status, ("gray50", "gray30"))[0]
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

    def update_queue_stats(self, queue_cnt: int, completed: int, failed: int, total: int, current_url: str = ""):
        self._stat_labels["queue"].configure(text=str(queue_cnt))
        self._stat_labels["completed"].configure(text=str(completed))
        self._stat_labels["failed"].configure(text=str(failed))
        self._stat_labels["current"].configure(text=os.path.basename(current_url) if current_url else "-")
        done = completed + failed
        self.queue_label.configure(text=t("task.queue_progress", done=done, total=total))
        self.queue_progress.set(done / total if total else 0)

    def reset_progress(self):
        self.file_progress.set(0)
        self.file_label.configure(text=t("task.file_progress_ready"))
        self.speed_label.configure(text="")
        self.queue_progress.set(1)
        self.queue_label.configure(text=t("task.queue_progress", done=0, total=0))
