import json
import os
import logging
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, filedialog
from tkinter import ttk

import customtkinter as ctk

from .. import DATA_DIR
from ..i18n import t
from ..config import load_config
from ..imgchk.db import Database
from ..imgchk.utils import request_stop, reset_interrupt, is_interrupted
from .widgets import C, S, R, apple_pill_button, apple_ghost_button, apple_danger_button, get_theme_name


class _QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(("log", self.format(record)))


def _format_size(size: int) -> str:
    if not size:
        return "-"
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / (1024 * 1024):.1f}MB"


class LibraryTab:
    def __init__(self, parent, app):
        self.app = app
        self._parent = parent
        self._running = False
        self._restore_running = False
        self._db = None
        self._manifest_data = None
        self._manifest_path = None
        self._id_vars = {}
        self.log_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self._scan_start_time = 0
        self._restore_start_time = 0
        self._build(parent)
        self._poll_queue()

    def refresh_language(self, parent=None):
        vals = self._gather_values()
        for w in self._parent.winfo_children():
            w.destroy()
        if parent is not None:
            self._parent = parent
        self._id_vars = {}
        self._build(self._parent)
        self._restore_values(vals)
        self._poll_queue()

    def _gather_values(self):
        return {
            "source_dir": self.source_var.get(),
            "scan_corrupt": self.scan_corrupt_var.get(),
            "scan_dedup": self.scan_dedup_var.get(),
            "folder_dedup": self.folder_dedup_var.get(),
            "ad_scan": self.ad_scan_var.get(),
            "convert_webp": self.convert_webp_var.get(),
            "white_bg": self.white_bg_var.get(),
            "db_skip": self.db_skip_var.get(),
            "overlap_threshold": self.overlap_threshold_var.get(),
            "ad_scan_count": self.ad_scan_count_var.get(),
        }

    def _restore_values(self, vals):
        self.source_var.set(vals.get("source_dir", ""))
        self.scan_corrupt_var.set(vals.get("scan_corrupt", True))
        self.scan_dedup_var.set(vals.get("scan_dedup", False))
        self.folder_dedup_var.set(vals.get("folder_dedup", False))
        self.ad_scan_var.set(vals.get("ad_scan", False))
        self.convert_webp_var.set(vals.get("convert_webp", False))
        self.white_bg_var.set(vals.get("white_bg", False))
        self.db_skip_var.set(vals.get("db_skip", False))
        self.overlap_threshold_var.set(vals.get("overlap_threshold", 50))
        self.ad_scan_count_var.set(vals.get("ad_scan_count", 6))

    def _get_db(self):
        if self._db is not None:
            return self._db
        cfg = load_config()
        if not cfg.get("db_enable", True):
            return None
        db_path = os.path.join(DATA_DIR, "imgchk.db")
        self._db = Database(db_path)
        return self._db

    def _build(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        f1 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f1.grid(row=0, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f1, text=t("lib.source_dir"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        src_row = ctk.CTkFrame(f1, fg_color="transparent")
        src_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        self.source_var = ctk.StringVar(value="")
        ctk.CTkEntry(src_row, textvariable=self.source_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(src_row, t("settings.browse"), self._browse_source, width=70).pack(side="left")

        opt_frame = ctk.CTkFrame(f1, fg_color="transparent")
        opt_frame.pack(fill="x", padx=S.LG, pady=(S.XS, S.XS))
        self.scan_corrupt_var = ctk.BooleanVar(value=True)
        self.scan_dedup_var = ctk.BooleanVar(value=False)
        self.folder_dedup_var = ctk.BooleanVar(value=False)
        self.ad_scan_var = ctk.BooleanVar(value=False)
        self.convert_webp_var = ctk.BooleanVar(value=False)
        self.white_bg_var = ctk.BooleanVar(value=False)
        self.db_skip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_frame, text=t("lib.scan_corrupt"),
                        variable=self.scan_corrupt_var, corner_radius=R.SM).pack(side="left", padx=(0, S.SM))
        ctk.CTkCheckBox(opt_frame, text=t("lib.scan_dedup"),
                        variable=self.scan_dedup_var, corner_radius=R.SM).pack(side="left", padx=(0, S.SM))
        ctk.CTkCheckBox(opt_frame, text=t("lib.folder_dedup"),
                        variable=self.folder_dedup_var, corner_radius=R.SM).pack(side="left", padx=(0, S.SM))
        ctk.CTkCheckBox(opt_frame, text=t("lib.ad_scan"),
                        variable=self.ad_scan_var, corner_radius=R.SM).pack(side="left")

        opt_frame2 = ctk.CTkFrame(f1, fg_color="transparent")
        opt_frame2.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkCheckBox(opt_frame2, text=t("lib.convert_webp"),
                        variable=self.convert_webp_var, corner_radius=R.SM).pack(side="left", padx=(0, S.SM))
        ctk.CTkCheckBox(opt_frame2, text=t("lib.white_bg"),
                        variable=self.white_bg_var, corner_radius=R.SM).pack(side="left", padx=(0, S.SM))
        ctk.CTkCheckBox(opt_frame2, text=t("lib.db_skip_this"),
                        variable=self.db_skip_var, corner_radius=R.SM).pack(side="left")

        thresh_row = ctk.CTkFrame(f1, fg_color="transparent")
        thresh_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkLabel(thresh_row, text=t("lib.overlap_threshold"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.overlap_threshold_var = ctk.IntVar(value=50)
        ctk.CTkEntry(thresh_row, textvariable=self.overlap_threshold_var, width=60,
                     corner_radius=R.SM).pack(side="left")
        ctk.CTkLabel(thresh_row, text="%",
                     font=self.app.fonts.body).pack(side="left", padx=(S.XXS, 0))

        ctk.CTkLabel(thresh_row, text=t("lib.ad_scan_count"),
                     font=self.app.fonts.body).pack(side="left", padx=(S.LG, S.XS))
        self.ad_scan_count_var = ctk.IntVar(value=6)
        ctk.CTkEntry(thresh_row, textvariable=self.ad_scan_count_var, width=60,
                     corner_radius=R.SM).pack(side="left")

        db_row = ctk.CTkFrame(f1, fg_color="transparent")
        db_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        self._db_info_var = ctk.StringVar(value="")
        ctk.CTkLabel(db_row, textvariable=self._db_info_var,
                     text_color=C.INK_MUTED_48, font=self.app.fonts.caption).pack(side="left")
        apple_ghost_button(db_row, t("lib.clear_dups"), self._clear_dups, width=90).pack(side="right", padx=S.XXS)
        apple_ghost_button(db_row, t("lib.clear_cache"), self._clear_cache, width=90).pack(side="right", padx=S.XS)
        self._update_db_info()

        btn_frame = ctk.CTkFrame(f1, fg_color="transparent")
        btn_frame.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        self._start_btn = apple_pill_button(btn_frame, t("lib.start_scan"), self._start_scan,
                                             width=100, color=C.SUCCESS, hover_color=C.SUCCESS_HOVER)
        self._start_btn.pack(side="left", padx=(0, S.XS))
        self._stop_btn = apple_danger_button(btn_frame, t("lib.stop_scan"), self._stop_scan, width=80)
        self._stop_btn.configure(state="disabled")
        self._stop_btn.pack(side="left")

        prog_outer = ctk.CTkFrame(scroll, corner_radius=R.LG)
        prog_outer.grid(row=1, column=0, sticky="ew", pady=(0, S.SM))
        self.scan_progress_var = ctk.DoubleVar(value=0)
        ctk.CTkProgressBar(prog_outer, variable=self.scan_progress_var, height=6,
                           progress_color=C.PRIMARY, fg_color=C.DIVIDER_SOFT).pack(
            fill="x", padx=S.LG, pady=(S.MD, S.XS))
        self.scan_status_var = ctk.StringVar(value=t("lib.ready"))
        ctk.CTkLabel(prog_outer, textvariable=self.scan_status_var,
                     text_color=C.INK_MUTED_48, font=self.app.fonts.caption).pack(
            anchor="w", padx=S.LG, pady=(0, S.MD))

        log_frame = ctk.CTkFrame(scroll, corner_radius=R.LG)
        log_frame.grid(row=2, column=0, sticky="nsew", pady=(0, S.SM))
        scroll.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(log_frame, text=t("lib.log"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        self.log_text = ctk.CTkTextbox(log_frame, height=100, state="disabled",
                                       font=self.app.fonts.textbox_small,
                                       corner_radius=R.SM)
        self.log_text.pack(fill="both", expand=True, padx=S.LG, pady=(0, S.MD))

        f3 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f3.grid(row=3, column=0, sticky="nsew", pady=(0, S.SM))
        f3.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f3, text=t("lib.data_source"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        src_row2 = ctk.CTkFrame(f3, fg_color="transparent")
        src_row2.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        self.manifest_var = ctk.StringVar(value="")
        ctk.CTkEntry(src_row2, textvariable=self.manifest_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(src_row2, t("lib.load_json"), self._load_manifest, width=80).pack(side="left", padx=(0, S.XS))
        apple_pill_button(src_row2, t("lib.load_db"), self._load_from_db, width=80).pack(side="left")

        act_row = ctk.CTkFrame(f3, fg_color="transparent")
        act_row.pack(fill="x", padx=S.LG, pady=(S.XS, S.XS))
        self._select_all_btn = ctk.CTkButton(act_row, text=t("lib.select_all"), width=70,
                                              corner_radius=R.SM,
                                              command=self._select_all, state="disabled")
        self._select_all_btn.pack(side="left", padx=(0, S.XS))
        self._deselect_btn = ctk.CTkButton(act_row, text=t("lib.deselect_all"), width=70,
                                           corner_radius=R.SM,
                                           command=self._deselect_all, state="disabled")
        self._deselect_btn.pack(side="left", padx=(0, S.XS))
        self._restore_btn = apple_pill_button(act_row, t("lib.restore_selected"), self._restore_selected,
                                               width=90, state="disabled")
        self._restore_btn.pack(side="left", padx=(0, S.XS))
        self._trash_btn = apple_danger_button(act_row, t("lib.trash_selected"), self._trash_selected, width=90)
        self._trash_btn.configure(state="disabled")
        self._trash_btn.pack(side="left", padx=(0, S.XS))
        apple_ghost_button(act_row, t("lib.open_file"), self._open_selected, width=60).pack(side="left")

        self.restore_progress_var = ctk.DoubleVar(value=0)
        ctk.CTkProgressBar(f3, variable=self.restore_progress_var, height=6,
                           progress_color=C.PRIMARY, fg_color=C.DIVIDER_SOFT).pack(
            fill="x", padx=S.LG, pady=(S.XS, S.XS))
        self.restore_status_var = ctk.StringVar(value=t("lib.load_manifest_first"))
        ctk.CTkLabel(f3, textvariable=self.restore_status_var,
                     text_color=C.INK_MUTED_48, font=self.app.fonts.caption).pack(
            anchor="w", padx=S.LG, pady=(0, S.XS))

        self._tree_frame = ctk.CTkFrame(f3, corner_radius=R.SM, height=220)
        self._tree_frame.pack_propagate(False)
        self._tree_frame.pack(fill="both", expand=True, padx=S.LG, pady=(0, S.MD))
        columns = ("id", "hash", "original_path", "file_size", "status")
        self._tree = ttk.Treeview(
            self._tree_frame, columns=columns, show="headings", selectmode="extended",
            height=8, style="Library.Treeview")
        self._tree_scroll_y = ctk.CTkScrollbar(self._tree_frame, orientation="vertical", command=self._tree.yview)
        self._tree_scroll_x = ctk.CTkScrollbar(self._tree_frame, orientation="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=self._tree_scroll_y.set, xscrollcommand=self._tree_scroll_x.set)
        self._tree.heading("id", text="ID")
        self._tree.heading("hash", text="Hash")
        self._tree.heading("original_path", text=t("lib.col_original"))
        self._tree.heading("file_size", text=t("lib.col_size"))
        self._tree.heading("status", text=t("lib.col_status"))
        self._tree.column("id", width=45, anchor="center")
        self._tree.column("hash", width=90, anchor="center")
        self._tree.column("original_path", width=320)
        self._tree.column("file_size", width=70, anchor="e")
        self._tree.column("status", width=65, anchor="center")
        self.refresh_theme()
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._tree_scroll_y.grid(row=0, column=1, sticky="ns")
        self._tree_scroll_x.grid(row=1, column=0, sticky="ew")
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self._tree_frame.grid_columnconfigure(0, weight=1)

    def refresh_theme(self):
        if not hasattr(self, "_tree"):
            return
        dark = get_theme_name() == "dark"
        if dark:
            colors = {
                "frame": "#1C1C1E",
                "bg": "#1F1F21",
                "field": "#1F1F21",
                "fg": "#F5F5F7",
                "heading_bg": "#2C2C2E",
                "heading_fg": "#FFFFFF",
                "selected_bg": "#0A84FF",
                "selected_fg": "#FFFFFF",
                "border": "#3A3A3C",
                "scroll_button": "#48484A",
                "scroll_hover": "#5A5A5C",
            }
        else:
            colors = {
                "frame": "#F2F2F7",
                "bg": "#FFFFFF",
                "field": "#FFFFFF",
                "fg": "#1D1D1F",
                "heading_bg": "#F2F2F7",
                "heading_fg": "#1D1D1F",
                "selected_bg": "#007AFF",
                "selected_fg": "#FFFFFF",
                "border": "#D2D2D7",
                "scroll_button": "#C7C7CC",
                "scroll_hover": "#AEAEB2",
            }

        self._tree_frame.configure(fg_color=colors["frame"])
        if hasattr(self, "_tree_scroll_y"):
            self._tree_scroll_y.configure(
                fg_color=colors["frame"], button_color=colors["scroll_button"],
                button_hover_color=colors["scroll_hover"])
            self._tree_scroll_x.configure(
                fg_color=colors["frame"], button_color=colors["scroll_button"],
                button_hover_color=colors["scroll_hover"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Library.Treeview",
            background=colors["bg"],
            foreground=colors["fg"],
            fieldbackground=colors["field"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            rowheight=28,
            font=(self.app._font_family, 11),
        )
        style.configure(
            "Library.Treeview.Heading",
            background=colors["heading_bg"],
            foreground=colors["heading_fg"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            font=(self.app._font_family, 11, "bold"),
        )
        style.map(
            "Library.Treeview",
            background=[("selected", colors["selected_bg"])],
            foreground=[("selected", colors["selected_fg"])],
        )
        self._tree.configure(style="Library.Treeview")

    def _update_db_info(self):
        db = self._get_db()
        if db:
            try:
                count = db.count_cache()
                self._db_info_var.set(f"imgchk.db ({count} cached)")
            except Exception:
                self._db_info_var.set("imgchk.db")
        else:
            self._db_info_var.set(t("lib.db_not_enabled"))

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _browse_source(self):
        d = filedialog.askdirectory(title=t("lib.source_dir"))
        if d:
            self.source_var.set(d)

    def _browse_manifest(self):
        path = filedialog.askopenfilename(
            title=t("lib.load_json"),
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if path:
            self.manifest_var.set(path)

    def _load_manifest(self):
        path = self.manifest_var.get().strip()
        if not path:
            messagebox.showwarning("", t("lib.select_manifest"))
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._manifest_data = json.load(f)
            self._manifest_path = Path(path)
        except Exception as e:
            messagebox.showerror(t("lib.load_json"), str(e))
            return
        self._populate_tree()

    def _load_from_db(self):
        db = self._get_db()
        if not db:
            messagebox.showwarning("", t("lib.db_not_enabled"))
            return
        try:
            rows = db.load_duplicates("moved")
        except Exception as e:
            messagebox.showerror(t("lib.load_db"), str(e))
            return
        self._manifest_data = {"entries": rows}
        self._manifest_path = None
        self._populate_tree()

    def _populate_tree(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._id_vars.clear()
        if not self._manifest_data:
            return
        for entry in self._manifest_data.get("entries", []):
            if entry.get("status") != "moved":
                continue
            sz = entry.get("file_size", 0)
            size_str = _format_size(sz)
            short_hash = (entry.get("hash") or "")[:12]
            iid = self._tree.insert("", "end", values=(
                entry["id"], short_hash, entry["original_path"], size_str, entry["status"]))
            self._id_vars[iid] = entry

        n = len(self._id_vars)
        st = "normal" if n else "disabled"
        self._select_all_btn.configure(state=st)
        self._deselect_btn.configure(state=st)
        self._restore_btn.configure(state=st)
        self._trash_btn.configure(state=st)
        self.restore_status_var.set(t("lib.loaded_entries", count=n))
        self.restore_progress_var.set(0)

    def _start_scan(self):
        source = self.source_var.get().strip()
        if not source or not Path(source).exists():
            messagebox.showerror("", t("lib.select_source"))
            return
        convert_webp = self.convert_webp_var.get()
        if not (self.scan_corrupt_var.get() or self.scan_dedup_var.get() or
                self.folder_dedup_var.get() or self.ad_scan_var.get() or convert_webp):
            messagebox.showwarning("", t("lib.no_function"))
            return

        reset_interrupt()
        self._running = True
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._clear_log()
        self.scan_progress_var.set(0)
        self._scan_start_time = time.time()
        self.scan_status_var.set(t("lib.scanning_status"))
        self._db = None

        cfg = load_config()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path(DATA_DIR) / "scan_log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"scan_{ts}.log"

        logger = logging.getLogger(f"img_scan_{ts}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        qh = _QueueHandler(self.log_queue)
        qh.setFormatter(fmt)
        logger.addHandler(qh)

        source_dir = Path(source)
        threads = cfg.get("scan_threads", 12)
        white_bg = self.white_bg_var.get()
        do_scan = self.scan_corrupt_var.get()
        do_dedup = self.scan_dedup_var.get()
        do_folder_dedup = self.folder_dedup_var.get()
        do_ad_scan = self.ad_scan_var.get()
        ad_scan_count = max(1, min(100, self.ad_scan_count_var.get()))
        overlap_threshold = max(1, min(100, self.overlap_threshold_var.get())) / 100.0
        db_skip = self.db_skip_var.get()
        db = self._get_db() if not db_skip and cfg.get("db_enable", True) else None

        def progress_cb(current, total):
            self.progress_queue.put(("scan", current, total))

        def worker():
            try:
                if do_scan or convert_webp:
                    from ..imgchk.scanner import scan_directory
                    error_dir = Path(cfg.get("error_dir", str(Path.cwd() / "Error")))
                    error_dir.mkdir(parents=True, exist_ok=True)
                    result = scan_directory(
                        source_dir, error_dir, log_path,
                        threads=threads, convert_webp=convert_webp,
                        white_bg=white_bg, progress_callback=progress_cb,
                        db=db, db_skip=db_skip)
                    self.result_queue.put(("scan", result))

                if (do_dedup or do_folder_dedup or do_ad_scan) and not is_interrupted():
                    reset_interrupt()
                    from ..imgchk.dedup import scan_duplicates, scan_folder_duplicates

                    if do_dedup:
                        dedup_dir = Path(cfg.get("dedup_dir", str(Path.cwd() / "Duplicate")))
                        dedup_dir.mkdir(parents=True, exist_ok=True)
                        manifest_dir = Path(DATA_DIR) / "duplicate_manifest"
                        manifest_dir.mkdir(parents=True, exist_ok=True)
                        dr = scan_duplicates(source_dir, dedup_dir, manifest_dir, threads, logger, db)
                        self.result_queue.put(("dedup", dr))

                    if do_folder_dedup and not is_interrupted():
                        folder_dedup_dir = Path(str(source_dir) + "_Duplicate_Folders")
                        fr = scan_folder_duplicates(source_dir, folder_dedup_dir, overlap_threshold, logger)
                        self.result_queue.put(("folder_dedup", fr))

                    if do_ad_scan and not is_interrupted():
                        reset_interrupt()
                        from ..imgchk.dedup import scan_ad_duplicates
                        ad_dedup_dir = Path(str(source_dir) + "_Ad_Folders")
                        ar = scan_ad_duplicates(source_dir, ad_dedup_dir, overlap_threshold, ad_scan_count, threads, logger)
                        self.result_queue.put(("ad_scan", ar))
            except Exception as e:
                self.result_queue.put(("error", str(e)))
            finally:
                self.app.root.after(0, self._scan_finished)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_scan(self):
        request_stop()

    def _scan_finished(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self.scan_status_var.set(t("lib.scan_complete"))

    def _clear_cache(self):
        db = self._get_db()
        if not db:
            messagebox.showwarning("", t("lib.db_not_enabled"))
            return
        if messagebox.askyesno("", t("lib.clear_cache_confirm")):
            db.clear_scan_cache()
            self.log(t("lib.cache_cleared"))
            self._update_db_info()

    def _clear_dups(self):
        db = self._get_db()
        if not db:
            messagebox.showwarning("", t("lib.db_not_enabled"))
            return
        if messagebox.askyesno("", t("lib.clear_dups_confirm")):
            db.clear_duplicate_records()
            self.log(t("lib.dups_cleared"))

    def _select_all(self):
        self._tree.selection_set(self._tree.get_children())

    def _deselect_all(self):
        self._tree.selection_set(())

    def _restore_selected(self):
        if not self._manifest_data:
            return
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("", t("lib.select_entries"))
            return
        entries = [self._id_vars[iid] for iid in selected if iid in self._id_vars]
        n = len(entries)
        if not messagebox.askyesno("", t("lib.restore_confirm", count=n)):
            return

        self.log(t("lib.restoring", count=n))
        self._restore_running = True
        self._restore_btn.configure(state="disabled")
        self._trash_btn.configure(state="disabled")
        self.restore_progress_var.set(0)
        self._restore_start_time = time.time()

        cfg = load_config()
        db = self._get_db() if cfg.get("db_enable", True) else None
        selected_ids = [e["id"] for e in entries]

        if self._manifest_path:
            manifest_path = self._manifest_path
        else:
            tmp_manifest = Path(DATA_DIR) / "duplicate_manifest" / "_restore_tmp.json"
            tmp_manifest.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_manifest, "w", encoding="utf-8") as f:
                json.dump(self._manifest_data, f, ensure_ascii=False, indent=2)
            manifest_path = tmp_manifest

        log_dir = Path(DATA_DIR) / "scan_log"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger = logging.getLogger(f"img_restore_{ts}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        fh = logging.FileHandler(log_dir / f"restore_{ts}.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        qh = _QueueHandler(self.log_queue)
        qh.setFormatter(fmt)
        logger.addHandler(qh)

        def progress_cb(current, total):
            self.progress_queue.put(("restore", current, total))

        def worker():
            from ..imgchk.dedup import restore_from_manifest
            result = restore_from_manifest(manifest_path, selected_ids, logger, progress_cb)
            if db and result:
                try:
                    db.update_duplicate_status(selected_ids, "restored")
                except Exception:
                    pass
            self.result_queue.put(("restore", result))

        threading.Thread(target=worker, daemon=True).start()

    def _trash_selected(self):
        if not self._manifest_data:
            return
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("", t("lib.select_entries"))
            return
        entries = [self._id_vars[iid] for iid in selected if iid in self._id_vars]
        n = len(entries)
        if not messagebox.askyesno("", t("lib.trash_confirm", count=n)):
            return

        self.log(t("lib.trashing", count=n))
        self._restore_running = True
        self._restore_btn.configure(state="disabled")
        self._trash_btn.configure(state="disabled")
        self.restore_progress_var.set(0)
        self._restore_start_time = time.time()

        cfg = load_config()
        trash_dir = Path(cfg.get("trash_dir", str(Path.cwd() / "Trash")))
        trash_dir.mkdir(parents=True, exist_ok=True)
        db = self._get_db() if cfg.get("db_enable", True) else None

        log_dir = Path(DATA_DIR) / "scan_log"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger = logging.getLogger(f"img_trash_{ts}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        fh = logging.FileHandler(log_dir / f"trash_{ts}.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        qh = _QueueHandler(self.log_queue)
        qh.setFormatter(fmt)
        logger.addHandler(qh)

        def progress_cb(current, total):
            self.progress_queue.put(("restore", current, total))

        def worker():
            from ..imgchk.dedup import move_to_trash
            result = move_to_trash(entries, trash_dir, logger, progress_cb, db)
            self.result_queue.put(("trash", result))

        threading.Thread(target=worker, daemon=True).start()

    def _open_selected(self):
        for iid in self._tree.selection():
            entry = self._id_vars.get(iid)
            if not entry:
                continue
            sp = entry.get("stored_path", "")
            if sp and Path(sp).exists():
                import subprocess
                import sys
                try:
                    if sys.platform == "win32":
                        os.startfile(sp)
                    else:
                        subprocess.run(["xdg-open", sp])
                except Exception:
                    pass

    def _poll_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item[0] == "log":
                    self.log(item[1])
        except queue.Empty:
            pass

        while True:
            try:
                item = self.progress_queue.get_nowait()
                if item[0] == "scan":
                    _, cur, total = item
                    if total > 0:
                        progress = cur / total
                        self.scan_progress_var.set(min(progress, 1))
                        elapsed = time.time() - self._scan_start_time
                        eta = (elapsed / cur) * (total - cur) if cur else 0
                        if eta < 0 or eta == float("inf"):
                            eta_str = "..."
                        elif eta < 60:
                            eta_str = f"{eta:.0f}s"
                        else:
                            m, s = divmod(int(eta), 60)
                            eta_str = f"{m}m{s}s"
                        self.scan_status_var.set(
                            t("lib.scanning_status") + f" {cur}/{total} ETA:{eta_str}")
                elif item[0] == "restore":
                    _, cur, total = item
                    if total > 0:
                        progress = cur / total
                        self.restore_progress_var.set(min(progress, 1))
            except queue.Empty:
                break

        while True:
            try:
                item = self.result_queue.get_nowait()
                kind = item[0]
                if kind == "scan":
                    result = item[1]
                    interrupted = result.get("interrupted", False)
                    s = f"\n{'(Interrupted) ' if interrupted else ''}Scan result: checked {result['total']}/{result['total_found']} images\n"
                    s += f"  Corrupted: {result['corrupted']} | Moved: {result['moved']} | Failed: {result['failed']}\n"
                    if result.get("webp_converted") or result.get("webp_deleted_existing"):
                        s += f"  WebP->PNG: {result['webp_converted']} | Already had PNG: {result['webp_deleted_existing']}\n"
                    if result.get("cached_skipped"):
                        s += f"  Cached skipped: {result['cached_skipped']}\n"
                    self.log(s)
                elif kind == "dedup":
                    result = item[1]
                    if result:
                        s = f"\nDuplicate scan result:\n"
                        s += f"  Groups: {result['total_groups']} | Extra copies: {result['total_duplicates']}\n"
                        s += f"  Moved: {result['moved']} | Failed: {result['failed']}\n"
                        s += f"  Manifest: {result.get('manifest_path', '-')}"
                        self.log(s)
                elif kind == "folder_dedup":
                    result = item[1]
                    if result:
                        s = f"\nFolder dedup: moved {result.get('folders_moved', 0)}, failed {result.get('failed', 0)}"
                        self.log(s)
                elif kind == "ad_scan":
                    result = item[1]
                    if result:
                        s = f"\nAd scan: moved {result.get('folders_moved', 0)}, failed {result.get('failed', 0)}"
                        self.log(s)
                elif kind == "restore":
                    result = item[1]
                    self._restore_running = False
                    self._restore_btn.configure(state="normal")
                    self._trash_btn.configure(state="normal")
                    self.restore_progress_var.set(1)
                    if result:
                        s = f"\nRestore: success {result.get('restored', 0)}, skipped {result.get('skipped', 0)}, failed {result.get('failed', 0)}"
                        self.log(s)
                        self.restore_status_var.set(s.strip())
                elif kind == "trash":
                    result = item[1]
                    self._restore_running = False
                    self._restore_btn.configure(state="normal")
                    self._trash_btn.configure(state="normal")
                    self.restore_progress_var.set(1)
                    if result:
                        s = f"\nTrash: moved {result.get('moved', 0)}, failed {result.get('failed', 0)}"
                        self.log(s)
                        self.restore_status_var.set(s.strip())
                elif kind == "error":
                    self.log(f"\nError: {item[1]}")
            except queue.Empty:
                break

        self.app.root.after(100, self._poll_queue)
