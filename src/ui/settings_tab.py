import os
import json
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk

from .. import DATA_DIR
from ..i18n import t, set_language, available_languages
from ..db.library import (
    scan_path_to_db, get_library_paths, get_all_library_names,
    get_library_path_counts, remove_library_path,
)
from ..config import load_config, DEFAULT_CONFIG


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

    def _gather_values(self):
        return {
            "lang_var": self.lang_var.get(),
            "download_dir": self.download_dir_var.get(),
            "extract_dir": self.extract_dir_var.get(),
            "chrome_path": self.chrome_path_var.get(),
            "user_data_dir": self.user_data_dir_var.get(),
            "chrome_port": self.chrome_port_var.get(),
            "auto_extract": self.auto_extract_var.get(),
            "delete_after_extract": self.delete_after_extract_var.get(),
            "integrity": self.integrity_var.get(),
            "notify": self.notify_var.get(),
        }

    def _restore_values(self, vals):
        self.lang_var.set(vals.get("lang_var", ""))
        self.download_dir_var.set(vals.get("download_dir", ""))
        self.extract_dir_var.set(vals.get("extract_dir", ""))
        self.chrome_path_var.set(vals.get("chrome_path", ""))
        self.user_data_dir_var.set(vals.get("user_data_dir", ""))
        self.chrome_port_var.set(vals.get("chrome_port", 9222))
        self.auto_extract_var.set(vals.get("auto_extract", False))
        self.delete_after_extract_var.set(vals.get("delete_after_extract", False))
        self.integrity_var.set(vals.get("integrity", True))
        self.notify_var.set(vals.get("notify", True))

    def _build(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        f0 = ctk.CTkFrame(parent)
        f0.grid(row=0, column=0, sticky="ew", padx=4, pady=(8, 4))
        ctk.CTkLabel(f0, text=t("settings.language"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=12, pady=(10, 2))
        lang_row = ctk.CTkFrame(f0, fg_color="transparent")
        lang_row.pack(fill="x", padx=12, pady=(2, 10))
        langs = available_languages()
        self.lang_var = tk.StringVar(value="")
        self.lang_menu = ctk.CTkOptionMenu(
            lang_row, values=list(langs.values()),
            variable=self.lang_var, command=self._on_lang_change)
        self.lang_menu.pack(side="left")
        ctk.CTkLabel(lang_row, text=" ", width=10).pack(side="left")

        options_row = ctk.CTkFrame(f0, fg_color="transparent")
        options_row.pack(fill="x", padx=12, pady=(0, 10))
        self.auto_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.auto_extract"),
                        variable=self.auto_extract_var,
                        command=self._save_options).pack(side="left", padx=(0, 12))
        self.delete_after_extract_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_row, text=t("settings.delete_after_extract"),
                        variable=self.delete_after_extract_var,
                        command=self._save_options).pack(side="left", padx=(0, 12))
        self.integrity_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_row, text=t("settings.integrity_check"),
                        variable=self.integrity_var,
                        command=self._save_options).pack(side="left", padx=(0, 12))
        self.notify_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(options_row, text=t("settings.notifications"),
                        variable=self.notify_var,
                        command=self._save_options).pack(side="left")

        # Download dir
        f1 = ctk.CTkFrame(parent)
        f1.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(f1, text=t("settings.download_dir"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=12, pady=(10, 2))
        row1 = ctk.CTkFrame(f1, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(2, 10))
        self.download_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        ctk.CTkEntry(row1, textvariable=self.download_dir_var).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(row1, text=t("settings.browse"), width=60,
                      command=self._browse_download_dir).pack(side="left")

        # Extract dir
        f1b = ctk.CTkFrame(parent)
        f1b.grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkLabel(f1b, text=t("settings.extract_dir"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=12, pady=(10, 2))
        extract_row = ctk.CTkFrame(f1b, fg_color="transparent")
        extract_row.pack(fill="x", padx=12, pady=(2, 10))
        self.extract_dir_var = tk.StringVar(value="")
        ctk.CTkEntry(extract_row, textvariable=self.extract_dir_var).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(extract_row, text=t("settings.browse"), width=60,
                      command=self._browse_extract_dir).pack(side="left")
        ctk.CTkLabel(f1b, text=t("settings.extract_dir_hint"),
                     text_color="gray50", font=self.app.fonts.small).pack(anchor="w", padx=12, pady=(0, 6))

        # Library paths
        f2 = ctk.CTkFrame(parent)
        f2.grid(row=3, column=0, sticky="nsew", padx=4, pady=4)
        parent.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(f2, text=t("settings.library_paths"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=12, pady=(10, 4))

        self.lib_list = ctk.CTkScrollableFrame(f2, height=120)
        self.lib_list.pack(fill="both", expand=True, padx=10, pady=(2, 4))

        lib_btns = ctk.CTkFrame(f2, fg_color="transparent")
        lib_btns.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkButton(lib_btns, text=t("settings.add_path"), width=100,
                      command=self._add_library_path).pack(side="left", padx=(0, 4))
        ctk.CTkButton(lib_btns, text=t("settings.rescan"), width=110, fg_color="gray40",
                      command=self._rescan_libraries).pack(side="left")
        self._lib_count_label = ctk.CTkLabel(lib_btns, text="", text_color="gray50")
        self._lib_count_label.pack(side="right")

        # Chrome
        f4 = ctk.CTkFrame(parent)
        f4.grid(row=4, column=0, sticky="ew", padx=4, pady=(4, 8))
        ctk.CTkLabel(f4, text=t("settings.chrome"),
                     font=self.app.fonts.heading).pack(anchor="w", padx=12, pady=(10, 4))

        chrome_row = ctk.CTkFrame(f4, fg_color="transparent")
        chrome_row.pack(fill="x", padx=12, pady=(0, 2))
        ctk.CTkLabel(chrome_row, text=t("settings.chrome_path"), width=60).pack(side="left", padx=(0, 4))
        self.chrome_path_var = tk.StringVar()
        ctk.CTkEntry(chrome_row, textvariable=self.chrome_path_var).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(chrome_row, text=t("settings.browse"), width=50,
                      command=self._browse_chrome_path).pack(side="left")

        udd_row = ctk.CTkFrame(f4, fg_color="transparent")
        udd_row.pack(fill="x", padx=12, pady=(2, 2))
        ctk.CTkLabel(udd_row, text=t("settings.user_data_dir"), width=60).pack(side="left", padx=(0, 4))
        self.user_data_dir_var = tk.StringVar()
        ctk.CTkEntry(udd_row, textvariable=self.user_data_dir_var).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(udd_row, text=t("settings.browse"), width=50,
                      command=self._browse_user_data_dir).pack(side="left")

        port_row = ctk.CTkFrame(f4, fg_color="transparent")
        port_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(port_row, text=t("settings.port")).pack(side="left", padx=(0, 4))
        self.chrome_port_var = tk.IntVar(value=9222)
        ctk.CTkEntry(port_row, textvariable=self.chrome_port_var, width=60).pack(side="left", padx=(0, 8))
        ctk.CTkButton(port_row, text=t("settings.launch_browser"), width=100, fg_color="#2ECC71",
                      hover_color="#27AE60", command=self._launch_browser).pack(side="left", padx=(0, 6))
        self._connect_btn = ctk.CTkButton(port_row, text=t("settings.connect_browser"), width=100,
                                          command=self._connect_browser)
        self._connect_btn.pack(side="left")

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
        self.notify_var.set(config.get("notifications", True))
        self._refresh_library_listbox()
        self._update_lang_menu()

    def _update_lang_menu(self):
        from ..i18n import get_language
        cur = get_language()
        langs = available_languages()
        display_map = {k: v for k, v in langs.items()}
        self.lang_menu.configure(values=list(langs.values()))
        self.lang_var.set(display_map.get(cur, langs.get("en", "English")))

    def _on_lang_change(self, display_name: str):
        old_home = t("tab.home")
        old_settings = t("tab.settings")
        langs = available_languages()
        reverse = {v: k for k, v in langs.items()}
        lang_code = reverse.get(display_name, "en")
        set_language(lang_code)
        self._save_options()
        self.app.refresh_language(old_home, old_settings)

    def get_download_dir(self) -> str:
        return self.download_dir_var.get().strip()

    def get_chrome_port(self) -> int:
        return self.chrome_port_var.get()

    def get_connect_btn(self):
        return self._connect_btn

    def _refresh_library_listbox(self):
        for w in self._lib_widgets.values():
            w.destroy()
        self._lib_widgets.clear()
        counts = get_library_path_counts()
        for path, count in counts.items():
            row = ctk.CTkFrame(self.lib_list, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=path, anchor="w",
                         font=self.app.fonts.body, text_color="gray80").pack(
                side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=str(count), anchor="e",
                         font=self.app.fonts.body, text_color="gray50").pack(
                side="right", padx=(0, 8))
            btn = ctk.CTkButton(row, text="X", width=28, height=22, fg_color="transparent",
                                border_width=1, text_color="#E74C3C",
                                command=lambda p=path: self._remove_library_path(p))
            btn.pack(side="right", padx=2)
            self._lib_widgets[path] = row
        self._update_lib_count()

    def _update_lib_count(self):
        names = get_all_library_names()
        paths = get_library_paths()
        self._lib_count_label.configure(
            text=t("lib.dir_count", dirs=len(paths), items=len(names)))

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
        f = filedialog.askopenfilename(
            title="chrome.exe",
            filetypes=[("chrome.exe", "chrome.exe"), ("exe files", "*.exe")])
        if f:
            self.chrome_path_var.set(f)
            self._save_options()

    def _browse_user_data_dir(self):
        d = filedialog.askdirectory(title="User Data Dir")
        if d:
            self.user_data_dir_var.set(d)
            self._save_options()

    def _launch_browser(self):
        chrome_exe = self.chrome_path_var.get().strip()
        port = self.chrome_port_var.get()
        user_data = self.user_data_dir_var.get().strip()
        if not chrome_exe or not os.path.exists(chrome_exe):
            messagebox.showerror(t("chrome.launch_fail"),
                                 t("chrome.not_found", path=chrome_exe))
            return
        if not user_data:
            messagebox.showwarning("", t("chrome.no_user_data"))
            return
        cmd = [
            chrome_exe,
            f"--remote-debugging-port={port}",
            f'--user-data-dir={user_data}',
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ]
        try:
            subprocess.Popen(cmd)
            self.app.log(t("chrome.launched", port=port, user_data=user_data))
            self.app.set_status(t("chrome.login_prompt"))
        except Exception as e:
            messagebox.showerror(t("chrome.launch_fail"), str(e))

    def _add_library_path(self):
        d = filedialog.askdirectory(title="Library")
        if not d:
            return
        self.app.log(t("lib.scanning", path=d))
        n = scan_path_to_db(d)
        self.app.log(t("lib.scan_done", count=n))
        self._refresh_library_listbox()
        self._save_options()

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

    def _save_options(self):
        import json
        os.makedirs(DATA_DIR, exist_ok=True)
        langs = available_languages()
        reverse = {v: k for k, v in langs.items()}
        lang_code = reverse.get(self.lang_var.get(), "")
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
            "library_paths": get_library_paths(),
        }
        with open(os.path.join(DATA_DIR, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    def _connect_browser(self):
        self.app.connect_browser()