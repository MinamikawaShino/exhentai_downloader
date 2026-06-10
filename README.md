[简体中文](README.zh-cn.md) | [繁體中文](README.zh-tw.md) | [日本語](README.ja.md) | [Русский](README.ru.md)
---


# ExHentai Gallery Downloader

> ⚠️ **This program is AI-written.**
>
> This tool was created solely for the author's purpose of downloading ExHentai's original archive files for personal appreciation and local archival. **Please ensure you have enough GP (Gallery Points) before batch downloading** — the script only downloads the original archive and will not download archives of other resolutions. Thank you!

ExHentai / e-hentai gallery archive automated downloader with CLI and GUI modes.

[简体中文](README.zh-cn.md) | [繁體中文](README.zh-tw.md) | [日本語](README.jp.md) | [Русский](README.ru.md)

## Known Issues

- **CJK (Chinese/Japanese/Korean) character display may have issues** — some characters may appear inconsistent in size or weight, which affects aesthetics. This is a limitation of the current GUI font handling.

## Features

- **Browser hijacking**: connects to an existing Chrome session via remote debugging protocol; user manually handles CloudFlare, then automation takes over
- **Resume support**: HTTP Range requests for interrupted download recovery
- **Auto retry**: 3 retries with exponential backoff on failure
- **Local library dedup**: SQLite-indexed local manga directories, auto-skips already downloaded galleries
- **Queue persistence**: saves progress on interrupt, restores on restart
- **Failure logging**: records failed URLs with reasons, one-click retry
- **Gallery metadata**: saves title, artist, tags, category to SQLite
- **ZIP integrity check**: optional CRC verification after download
- **Auto extract**: optionally unzips archives to a subdirectory named after the gallery title
- **Custom extract directory**: choose where archives are extracted (default: same as download directory)
- **Delete after extract**: optionally remove the ZIP file after successful extraction
- **Download speed/ETA**: real-time speed and estimated time remaining
- **Desktop notifications**: notifies on task completion
- **i18n**: English, 简体中文, 繁體中文, 日本語, Русский
- **GUI**: dark-themed CustomTkinter desktop application

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.9+ |
| Browser automation | Selenium WebDriver (Chrome) |
| HTTP | requests |
| GUI | customtkinter |
| Database | SQLite3 |
| Config | JSON |

## Project Structure

```
exhentai_downloader/
├── data/                       # Persistent data
│   └── library.db              # Local library index + metadata (SQLite)
├── downloads/                  # Default download directory
├── log/
│   ├── failed_downloads.txt    # Failed download records
│   └── pending_queue.txt       # Crash recovery queue
├── src/
│   ├── main.py                 # Unified entry point
│   ├── cli.py                  # CLI implementation
│   ├── downloader_core.py      # Core download engine
│   ├── config.py               # Configuration management
│   ├── i18n/                   # Internationalization
│   │   ├── en.py               # English
│   │   ├── zh_cn.py            # Simplified Chinese
│   │   ├── zh_tw.py            # Traditional Chinese
│   │   ├── ja.py               # Japanese
│   │   └── ru.py               # Russian
│   ├── utils/                  # Utilities
│   │   ├── filename.py         # Filename sanitization
│   │   ├── integrity.py        # ZIP integrity & extraction
│   │   ├── logging_utils.py    # Queue & failure persistence
│   │   ├── metadata_scraper.py # Gallery metadata extraction
│   │   └── notifications.py   # Desktop notifications
│   ├── db/                     # Database layer
│   │   ├── library.py          # Library index operations
│   │   └── metadata.py         # Gallery metadata storage
│   └── ui/                     # GUI components
│       ├── app.py              # Main application window
│       ├── task_tab.py         # Task management tab
│       ├── settings_tab.py     # Settings tab
│       └── widgets.py          # Shared widgets & utilities
├── run.py                        # Entry point launcher
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## Requirements

- Python 3.9+
- Google Chrome browser
- An e-hentai / ExHentai account

## Installation

```bash
git clone <repo-url>
cd exhentai_downloader

pip install -r requirements.txt
```

## Usage

### GUI Mode (recommended)

```bash
python run.py
# or
python -m src.main
# or
python run.py --gui
```

1. In the **Settings** tab, configure:
   - **Download Directory**: where ZIP archives are saved
   - **Extract Directory**: where archives are extracted (leave empty = same as download directory; each gallery extracts into a subfolder named after its title)
   - **Library Paths**: add existing manga directories (for dedup), click rescan
   - **Chrome Browser**: set Chrome path and user data directory
   - **Language**: choose UI language
   - **Options**: toggle ZIP integrity check, auto-extract, delete ZIP after extraction, notifications
2. Click **Launch Browser**, manually login to e-hentai in the opened Chrome
3. Click **Connect Browser**
4. In the **Tasks** tab, paste gallery URLs (one per line), click **Add URL**
5. Click **Start Download**

### CLI Mode

```bash
python run.py --cli
# or with options:
python run.py --cli --language en --download-dir ./downloads --extract --extract-dir ./extracted --delete-after-extract
```

CLI Options:

| Option | Description |
|--------|-------------|
| `-l, --language` | UI language: `en`, `zh_cn`, `zh_tw`, `ja`, `ru` |
| `-d, --download-dir` | Download directory |
| `--extract` | Auto-extract ZIP after download |
| `--extract-dir` | Extract directory (default: same as download directory) |
| `--delete-after-extract` | Delete ZIP after extraction |
| `--no-notify` | Disable desktop notifications |
| `--no-integrity` | Skip ZIP integrity check |

## Workflow

```
Input gallery URL -> Navigate page -> Extract title -> Dedup check
    -> Click Archive Download -> Get download link -> Resume download -> Done
    -> [Optional: Integrity check, Auto extract, Delete ZIP, Metadata save]
```

## Notes

- Chrome must be launched with `--remote-debugging-port=9222` (GUI can launch it for you)
- Manual e-hentai login + CloudFlare bypass must be done once in the browser
- Downloaded archives are ZIP format, saved as `GalleryTitle.zip`
- When auto-extract is enabled, archives extract into `ExtractDir/GalleryTitle/`
<<<<<<< HEAD
=======

---

## Deduplication Logic
- **Same Folder Rule**: Images within the *same* subfolder are NEVER considered duplicates of each other, even if their hashes match.
- **Cross-Folder Rule**: Only when comparing across *different* folders, the newest folder retains the files, and old image copies in other folders are deleted.
- **Folder Overlap**: If the overlap ratio of identical images between two folders exceeds the configured threshold (default 50%), the folder with the oldest modification date is deleted.
- **Ad Image Removal**: Deletes advertisement images by comparing the *last 6 images* (sorted by name) across folders. If the overlap exceeds the threshold (default 50%), the oldest folder is deleted. You can customize this threshold in the settings.
>>>>>>> ac50f8d (新增库管理功能，改进GUI体验)
