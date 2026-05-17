import os
import json
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk

from .. import DATA_DIR
from ..i18n import t, set_language, get_language, available_languages
from ..db.library import (
    scan_path_to_db, get_library_paths, get_all_library_names,
    get_library_path_counts, remove_library_path,
)
from ..config import load_config, DEFAULT_CONFIG
from .widgets import C, S, R, apple_pill_button, apple_ghost_button, get_theme_name


class SettingsTab:
    def __init__(self, parent, app):
        self.app = app
        self._lib_widgets = {}
        self._parent = parent
        self._build(parent)

    def refresh_language(self, parent=None):
        vals = self._gather_values()

        for w in self._parent.winfo_children():
            w.destroy()

        if parent is not None:
            self._parent = parent
        self._lib_widgets = {}
        self._build(self._parent)
        self._restore_values(vals)
        self._refresh_library_listbox()
        self._update_lang_menu()
        self._update_theme_menu()

    def _gather_values(self):
        return {
            "lang_var": self.lang_var.get(),
            "theme_var": self.theme_var.get(),
            "download_dir": self.download_dir_var.get(),
            "extract_dir": self.extract_dir_var.get(),
            "chrome_path": self.chrome_path_var.get(),
            "user_data_dir": self.user_data_dir_var.get(),
            "chrome_port": self.chrome_port_var.get(),
            "auto_extract": self.auto_extract_var.get(),
            "delete_after_extract": self.delete_after_extract_var.get(),
            "integrity": self.integrity_var.get(),
            "scan_corrupt_after_extract": self.scan_corrupt_after_extract_var.get(),
            "webp_to_png_after_extract": self.webp_to_png_after_extract_var.get(),
            "dedup_overlap_threshold": self.overlap_threshold_var.get(),
            "notify": self.notify_var.get(),
            "scan_threads": self.scan_threads_var.get(),
            "white_bg_webp": self.white_bg_webp_var.get(),
            "db_enable": self.db_enable_var.get(),
            "error_dir": self.error_dir_var.get(),
            "dedup_dir": self.dedup_dir_var.get(),
            "trash_dir": self.trash_dir_var.get(),
            "skip_page_threshold": self.skip_page_threshold_var.get(),
            "download_threads": self.download_threads_var.get(),
        }

    def _restore_values(self, vals):
        self.lang_var.set(vals.get("lang_var", ""))
        self.theme_var.set(vals.get("theme_var", ""))
        self.download_dir_var.set(vals.get("download_dir", ""))
        self.extract_dir_var.set(vals.get("extract_dir", ""))
        self.chrome_path_var.set(vals.get("chrome_path", ""))
        self.user_data_dir_var.set(vals.get("user_data_dir", ""))
        self.chrome_port_var.set(vals.get("chrome_port", 9222))
        self.auto_extract_var.set(vals.get("auto_extract", False))
        self.delete_after_extract_var.set(vals.get("delete_after_extract", False))
        self.integrity_var.set(vals.get("integrity", True))
        self.scan_corrupt_after_extract_var.set(vals.get("scan_corrupt_after_extract", False))
        self.webp_to_png_after_extract_var.set(vals.get("webp_to_png_after_extract", False))
        self.overlap_threshold_var.set(vals.get("dedup_overlap_threshold", 50))
        self.notify_var.set(vals.get("notify", True))
        self.scan_threads_var.set(vals.get("scan_threads", 12))
        self.white_bg_webp_var.set(vals.get("white_bg_webp", False))
        self.db_enable_var.set(vals.get("db_enable", True))
        self.error_dir_var.set(vals.get("error_dir", ""))
        self.dedup_dir_var.set(vals.get("dedup_dir", ""))
        self.trash_dir_var.set(vals.get("trash_dir", ""))
        self.skip_page_threshold_var.set(vals.get("skip_page_threshold", 5))
        self.download_threads_var.set(vals.get("download_threads", 2))

    def _build(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Language + Theme + Options
        f0 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f0.grid(row=0, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f0, text=t("settings.language"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        lang_row = ctk.CTkFrame(f0, fg_color="transparent")
        lang_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        langs = available_languages()
        self.lang_var = tk.StringVar(value="")
        self.lang_menu = ctk.CTkOptionMenu(
            lang_row, values=list(langs.values()),
            variable=self.lang_var, command=self._on_lang_change,
            corner_radius=R.SM)
        self.lang_menu.pack(side="left")

        ctk.CTkLabel(f0, text=t("settings.theme"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.XS, S.XS))
        theme_row = ctk.CTkFrame(f0, fg_color="transparent")
        theme_row.pack(fill="x", padx=S.LG, pady=(0, S.SM))
        self.theme_var = tk.StringVar(value="")
        theme_display = {"light": t("settings.theme_light"), "dark": t("settings.theme_dark")}
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, values=list(theme_display.values()),
            variable=self.theme_var, command=self._on_theme_change,
            corner_radius=R.SM)
        self.theme_menu.pack(side="left")

        options_row = ctk.CTkFrame(f0, fg_color="transparent")
        options_row.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        self.auto_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.auto_extract"),
                        variable=self.auto_extract_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.delete_after_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.delete_after_extract"),
                        variable=self.delete_after_extract_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.integrity_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_row, text=t("settings.integrity_check"),
                        variable=self.integrity_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.scan_corrupt_after_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.scan_corrupt_after_extract"),
                        variable=self.scan_corrupt_after_extract_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.webp_to_png_after_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.webp_to_png_after_extract"),
                        variable=self.webp_to_png_after_extract_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.notify_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_row, text=t("settings.notifications"),
                        variable=self.notify_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left")

        skip_row = ctk.CTkFrame(f0, fg_color="transparent")
        skip_row.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        ctk.CTkLabel(skip_row, text=t("settings.skip_page_threshold"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.skip_page_threshold_var = tk.IntVar(value=5)
        ctk.CTkEntry(skip_row, textvariable=self.skip_page_threshold_var, width=60,
                     corner_radius=R.SM).pack(side="left")
        ctk.CTkLabel(skip_row, text=t("settings.skip_page_threshold_unit"),
                     font=self.app.fonts.caption, text_color=C.INK_MUTED_48).pack(side="left", padx=(S.XXS, 0))

        # Download directory
        f1 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f1.grid(row=1, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f1, text=t("settings.download_dir"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        row1 = ctk.CTkFrame(f1, fg_color="transparent")
        row1.pack(fill="x", padx=S.LG, pady=(0, S.SM))
        self.download_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        ctk.CTkEntry(row1, textvariable=self.download_dir_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(row1, t("settings.browse"), self._browse_download_dir, width=70).pack(side="left")

        threads_row = ctk.CTkFrame(f1, fg_color="transparent")
        threads_row.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        ctk.CTkLabel(threads_row, text=t("settings.download_threads"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.download_threads_var = tk.IntVar(value=2)
        ctk.CTkEntry(threads_row, textvariable=self.download_threads_var, width=60,
                     corner_radius=R.SM).pack(side="left")

        # Extract directory
        f1b = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f1b.grid(row=2, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f1b, text=t("settings.extract_dir"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))
        extract_row = ctk.CTkFrame(f1b, fg_color="transparent")
        extract_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        self.extract_dir_var = tk.StringVar(value="")
        ctk.CTkEntry(extract_row, textvariable=self.extract_dir_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(extract_row, t("settings.browse"), self._browse_extract_dir, width=70).pack(side="left")
        ctk.CTkLabel(f1b, text=t("settings.extract_dir_hint"),
                     font=self.app.fonts.caption, text_color=C.INK_MUTED_48).pack(anchor="w", padx=S.LG, pady=(0, S.MD))

        # Library paths
        f2 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f2.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, S.SM))
        scroll.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(f2, text=t("settings.library_paths"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))

        self.lib_list = ctk.CTkScrollableFrame(f2, corner_radius=R.SM, height=100)
        self.lib_list.pack(fill="both", expand=True, padx=S.LG, pady=(0, S.XS))

        lib_btns = ctk.CTkFrame(f2, fg_color="transparent")
        lib_btns.pack(fill="x", padx=S.LG, pady=(0, S.MD))
        apple_pill_button(lib_btns, t("settings.add_path"), self._add_library_path, width=100).pack(side="left", padx=(0, S.XS))
        apple_ghost_button(lib_btns, t("settings.rescan"), self._rescan_libraries, width=110).pack(side="left")
        self._lib_count_label = ctk.CTkLabel(lib_btns, text="", font=self.app.fonts.caption, text_color=C.INK_MUTED_48)
        self._lib_count_label.pack(side="right")

        # Chrome Browser section
        f4 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f4.grid(row=4, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f4, text=t("settings.chrome"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))

        chrome_row = ctk.CTkFrame(f4, fg_color="transparent")
        chrome_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkLabel(chrome_row, text=t("settings.chrome_path"), width=80,
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.chrome_path_var = tk.StringVar()
        ctk.CTkEntry(chrome_row, textvariable=self.chrome_path_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(chrome_row, t("settings.browse"), self._browse_chrome_path, width=70).pack(side="left")

        udd_row = ctk.CTkFrame(f4, fg_color="transparent")
        udd_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkLabel(udd_row, text=t("settings.user_data_dir"), width=80,
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.user_data_dir_var = tk.StringVar()
        ctk.CTkEntry(udd_row, textvariable=self.user_data_dir_var,
                     corner_radius=R.SM).pack(
            side="left", fill="x", expand=True, padx=(0, S.XS))
        apple_pill_button(udd_row, t("settings.browse"), self._browse_user_data_dir, width=70).pack(side="left")

        port_row = ctk.CTkFrame(f4, fg_color="transparent")
        port_row.pack(fill="x", padx=S.LG, pady=(S.XS, S.MD))
        ctk.CTkLabel(port_row, text=t("settings.port"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.chrome_port_var = tk.IntVar(value=9222)
        ctk.CTkEntry(port_row, textvariable=self.chrome_port_var, width=60,
                     corner_radius=R.SM).pack(side="left", padx=(0, S.LG))
        self._launch_btn = apple_pill_button(port_row, t("settings.launch_browser"), self._launch_browser,
                                              width=110, color=C.SUCCESS, hover_color=C.SUCCESS_HOVER)
        self._launch_btn.pack(side="left", padx=(0, S.XS))
        self._connect_btn = apple_pill_button(port_row, t("settings.connect_browser"), self._connect_browser, width=110)
        self._connect_btn.pack(side="left")

        # Image Scanning Settings
        f5 = ctk.CTkFrame(scroll, corner_radius=R.LG)
        f5.grid(row=5, column=0, sticky="ew", pady=(0, S.SM))
        ctk.CTkLabel(f5, text=t("settings.scan_section"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=S.LG, pady=(S.MD, S.XS))

        threads_row = ctk.CTkFrame(f5, fg_color="transparent")
        threads_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkLabel(threads_row, text=t("settings.scan_threads"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.scan_threads_var = tk.IntVar(value=12)
        ctk.CTkEntry(threads_row, textvariable=self.scan_threads_var, width=60,
                     corner_radius=R.SM).pack(side="left")

        opts_row = ctk.CTkFrame(f5, fg_color="transparent")
        opts_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        self.white_bg_webp_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_row, text=t("settings.white_bg_webp"),
                        variable=self.white_bg_webp_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left", padx=(0, S.SM))
        self.db_enable_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_row, text=t("settings.db_enable"),
                        variable=self.db_enable_var, corner_radius=R.SM,
                        command=self._save_options).pack(side="left")

        thresh_row = ctk.CTkFrame(f5, fg_color="transparent")
        thresh_row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
        ctk.CTkLabel(thresh_row, text=t("settings.dedup_overlap_threshold"),
                     font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
        self.overlap_threshold_var = tk.IntVar(value=50)
        ctk.CTkEntry(thresh_row, textvariable=self.overlap_threshold_var, width=60,
                     corner_radius=R.SM).pack(side="left")
        ctk.CTkLabel(thresh_row, text="%",
                     font=self.app.fonts.caption).pack(side="left", padx=(S.XXS, 0))

        for label_text, var_name, browse_fn in [
            (t("settings.error_dir"), "error_dir", self._browse_error_dir),
            (t("settings.dedup_dir"), "dedup_dir", self._browse_dup_dir),
            (t("settings.trash_dir"), "trash_dir", self._browse_trash_dir),
        ]:
            row = ctk.CTkFrame(f5, fg_color="transparent")
            row.pack(fill="x", padx=S.LG, pady=(0, S.XS))
            ctk.CTkLabel(row, text=label_text, width=100,
                         font=self.app.fonts.body).pack(side="left", padx=(0, S.XS))
            var = tk.StringVar()
            setattr(self, f"{var_name}_var", var)
            ctk.CTkEntry(row, textvariable=var,
                         corner_radius=R.SM).pack(
                side="left", fill="x", expand=True, padx=(0, S.XS))
            apple_pill_button(row, t("settings.browse"), browse_fn, width=70).pack(side="left")

        ctk.CTkFrame(f5, height=S.SM).pack()

    def load(self):
        config = load_config()
        self.download_dir_var.set(config.get("download_dir", DEFAULT_CONFIG["download_dir"]))
        self.extract_dir_var.set(config.get("extract_dir", ""))
        self.chrome_port_var.set(config.get("chrome_port", 9222))
        self.chrome_path_var.set(config.get("chrome_path", ""))
        self.user_data_dir_var.set(config.get("user_data_dir", ""))
        self.auto_extract_var.set(config.get("auto_extract", False))
        self.delete_after_extract_var.set(config.get("delete_after_extract", False))
        self.integrity_var.set(config.get("integrity_check", True))
        self.scan_corrupt_after_extract_var.set(config.get("scan_corrupt_after_extract", False))
        self.webp_to_png_after_extract_var.set(config.get("webp_to_png_after_extract", False))
        self.notify_var.set(config.get("notifications", True))
        self.scan_threads_var.set(config.get("scan_threads", 12))
        self.white_bg_webp_var.set(config.get("white_bg_webp", False))
        self.db_enable_var.set(config.get("db_enable", True))
        self.error_dir_var.set(config.get("error_dir", ""))
        self.dedup_dir_var.set(config.get("dedup_dir", ""))
        self.trash_dir_var.set(config.get("trash_dir", ""))
        self.overlap_threshold_var.set(config.get("dedup_overlap_threshold", 50))
        self.skip_page_threshold_var.set(config.get("skip_page_threshold", 5))
        self.download_threads_var.set(config.get("download_threads", 2))
        self._refresh_library_listbox()
        self._update_lang_menu()
        self._update_theme_menu()

    def get_download_dir(self) -> str:
        return self.download_dir_var.get().strip()

    def get_chrome_port(self) -> int:
        try:
            return int(self.chrome_port_var.get())
        except (tk.TclError, ValueError):
            return DEFAULT_CONFIG["chrome_port"]

    def _browse_download_dir(self):
        d = filedialog.askdirectory(title=t("settings.download_dir"))
        if d:
            self.download_dir_var.set(d)
            self._save_options()

    def _browse_extract_dir(self):
        d = filedialog.askdirectory(title=t("settings.extract_dir"))
        if d:
            self.extract_dir_var.set(d)
            self._save_options()

    def _browse_chrome_path(self):
        f = filedialog.askopenfilename(title=t("settings.chrome_path"),
                                       filetypes=[("Executable", "*.exe"), ("All", "*.*")])
        if f:
            self.chrome_path_var.set(f)
            self._save_options()

    def _browse_user_data_dir(self):
        d = filedialog.askdirectory(title=t("settings.user_data_dir"))
        if d:
            self.user_data_dir_var.set(d)
            self._save_options()

    def _browse_error_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.error_dir_var.set(d)
            self._save_options()

    def _browse_dup_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.dedup_dir_var.set(d)
            self._save_options()

    def _browse_trash_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.trash_dir_var.set(d)
            self._save_options()

    def _add_library_path(self):
        d = filedialog.askdirectory(title=t("settings.library_paths"))
        if d:
            scan_path_to_db(d)
            self._refresh_library_listbox()
            self._save_options()

    def _launch_browser(self):
        self._save_options()
        cfg = load_config()
        port = cfg.get("chrome_port", 9222)
        chrome_path = cfg.get("chrome_path", "")
        user_data_dir = cfg.get("user_data_dir", "")
        args = []
        if chrome_path:
            args.append(chrome_path)
        else:
            import shutil
            found = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
            if not found:
                self.app.log(t("chrome.launch_fail"))
                return
            args.append(found)
        args.append(f"--remote-debugging-port={port}")
        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")
        args.extend([
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-popup-blocking",
            "--disable-features=CalculateNativeWinOcclusion",
        ])
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.app.log(t("chrome.launched", port=port, user_data=user_data_dir or "default"))
        except Exception as e:
            self.app.log(t("chrome.launch_fail"))

    def _update_lang_menu(self):
        langs = available_languages()
        current = get_language()
        display = langs.get(current, "English")
        self.lang_var.set(display)

    def _update_theme_menu(self):
        theme_name = get_theme_name()
        self.theme_var.set(t("settings.theme_" + theme_name))

    def _refresh_library_listbox(self):
        for w in self.lib_list.winfo_children():
            w.destroy()
        self._lib_widgets = []
        paths = get_library_paths()
        counts = get_library_path_counts()
        for path in paths:
            cnt = counts.get(path, 0)
            row = ctk.CTkFrame(self.lib_list, fg_color="transparent")
            row.pack(fill="x", pady=1)
            label_text = f"{path} ({cnt})" if cnt else path
            ctk.CTkLabel(row, text=label_text, font=self.app.fonts.body).pack(side="left")
            apple_ghost_button(row, "✕", lambda p=path: self._remove_library_path(p),
                               width=28).pack(side="right")
            self._lib_widgets.append(row)
        total = sum(counts.values())
        self._lib_count_label.configure(text=t("settings.total_galleries", count=total) if total else "")

    def _remove_library_path(self, path):
        remove_library_path(path)
        self._refresh_library_listbox()
        self._save_options()
        self.app.log(t("lib.removed", path=path))

    def _rescan_libraries(self):
        paths = get_library_paths()
        if not paths:
            return
        self.app.log(t("lib.rescanning", count=len(paths)))
        total = 0
        for p in paths:
            n = scan_path_to_db(p)
            total += n
            self.app.log(f"  {p}: {n}")
        self.app.log(t("lib.total", count=total))
        self._refresh_library_listbox()

    def _on_lang_change(self, _choice=None):
        langs = available_languages()
        reverse = {v: k for k, v in langs.items()}
        lang_code = reverse.get(self.lang_var.get(), "en")
        set_language(lang_code)
        self._save_options()
        self.app._rebuild_ui()

    def _on_theme_change(self, _choice=None):
        theme_reverse = {t("settings.theme_light"): "light", t("settings.theme_dark"): "dark"}
        theme_name = theme_reverse.get(self.theme_var.get(), "light")
        self.app.set_theme(theme_name)

    def _save_options(self):
        import json
        os.makedirs(DATA_DIR, exist_ok=True)
        langs = available_languages()
        reverse = {v: k for k, v in langs.items()}
        lang_code = reverse.get(self.lang_var.get(), "")
        theme_reverse = {t("settings.theme_light"): "light", t("settings.theme_dark"): "dark"}
        theme_name = theme_reverse.get(self.theme_var.get(), self.app._config.get("theme", "light"))
        s = {
            "download_dir": self.download_dir_var.get(),
            "extract_dir": self.extract_dir_var.get(),
            "chrome_port": self.chrome_port_var.get(),
            "chrome_path": self.chrome_path_var.get(),
            "user_data_dir": self.user_data_dir_var.get(),
            "auto_extract": self.auto_extract_var.get(),
            "delete_after_extract": self.delete_after_extract_var.get(),
            "integrity_check": self.integrity_var.get(),
            "notifications": self.notify_var.get(),
            "language": lang_code,
            "theme": theme_name,
            "library_paths": get_library_paths(),
            "scan_threads": self.scan_threads_var.get(),
            "white_bg_webp": self.white_bg_webp_var.get(),
            "db_enable": self.db_enable_var.get(),
            "error_dir": self.error_dir_var.get(),
            "dedup_dir": self.dedup_dir_var.get(),
            "trash_dir": self.trash_dir_var.get(),
            "scan_corrupt_after_extract": self.scan_corrupt_after_extract_var.get(),
            "webp_to_png_after_extract": self.webp_to_png_after_extract_var.get(),
            "dedup_overlap_threshold": self.overlap_threshold_var.get(),
            "skip_page_threshold": self.skip_page_threshold_var.get(),
            "download_threads": self.download_threads_var.get(),
        }
        with open(os.path.join(DATA_DIR, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    def _connect_browser(self):
        self.app.connect_browser()
