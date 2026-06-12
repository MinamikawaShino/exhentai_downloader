import re

with open("src/ui/library_tab.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add to _gather_values
content = content.replace(
    '"overlap_threshold": self.overlap_threshold_var.get(),',
    '"overlap_threshold": self.overlap_threshold_var.get(),\n            "ad_scan_count": self.ad_scan_count_var.get(),'
)

# Add to _restore_values
content = content.replace(
    'self.overlap_threshold_var.set(vals.get("overlap_threshold", 50))',
    'self.overlap_threshold_var.set(vals.get("overlap_threshold", 50))\n        self.ad_scan_count_var.set(vals.get("ad_scan_count", 6))'
)

# Add to UI in _build
ui_code = """        ctk.CTkLabel(thresh_row, text="%",
                     font=self.app.fonts.body).pack(side="left", padx=(S.XXS, 0))

        ctk.CTkLabel(thresh_row, text=t("lib.ad_scan_count"),
                     font=self.app.fonts.body).pack(side="left", padx=(S.LG, S.XS))
        self.ad_scan_count_var = ctk.IntVar(value=6)
        ctk.CTkEntry(thresh_row, textvariable=self.ad_scan_count_var, width=60,
                     corner_radius=R.SM).pack(side="left")"""

content = content.replace(
"""        ctk.CTkLabel(thresh_row, text="%",
                     font=self.app.fonts.body).pack(side="left", padx=(S.XXS, 0))""",
ui_code
)

# Pass ad_scan_count to scan_ad_duplicates
content = content.replace(
    'do_ad_scan = self.ad_scan_var.get()',
    'do_ad_scan = self.ad_scan_var.get()\n        ad_scan_count = max(1, min(100, self.ad_scan_count_var.get()))'
)

content = content.replace(
    'ar = scan_ad_duplicates(source_dir, ad_dedup_dir, overlap_threshold, threads, logger)',
    'ar = scan_ad_duplicates(source_dir, ad_dedup_dir, overlap_threshold, ad_scan_count, threads, logger)'
)

with open("src/ui/library_tab.py", "w", encoding="utf-8") as f:
    f.write(content)
