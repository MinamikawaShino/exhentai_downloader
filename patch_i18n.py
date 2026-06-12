import glob

i18n_files = glob.glob("src/i18n/*.py")

translations = {
    "en.py": '    "lib.ad_scan_count": "Ad scan image count:",\n',
    "zh_cn.py": '    "lib.ad_scan_count": "广告图扫描数量:",\n',
    "zh_tw.py": '    "lib.ad_scan_count": "廣告圖掃描數量:",\n',
    "jp.py": '    "lib.ad_scan_count": "広告画像スキャン数:",\n',
    "ru.py": '    "lib.ad_scan_count": "Количество рекламных изображений:",\n',
}

for filepath in i18n_files:
    filename = filepath.split("/")[-1]
    if filename in translations:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # insert after lib.overlap_threshold
        content = content.replace(
            '"lib.overlap_threshold": ',
            translations[filename] + '    "lib.overlap_threshold": '
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
