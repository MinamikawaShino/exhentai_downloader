import os
import sqlite3
import datetime

from .. import DATA_DIR
from ..utils.filename import normalize_for_comparison

DB_FILE = os.path.join(DATA_DIR, "library.db")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def _db_connect():
    _ensure_dirs()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library_items (
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            UNIQUE(path, name)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_library_name ON library_items(name)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS gallery_metadata (
            url TEXT PRIMARY KEY,
            title TEXT,
            title_jp TEXT,
            artist TEXT,
            category TEXT,
            tags TEXT,
            upload_date TEXT,
            file_count INTEGER,
            file_size TEXT,
            downloaded_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_metadata_title ON gallery_metadata(title)")
    conn.commit()
    return conn


def scan_path_to_db(path: str) -> int:
    if not path or not os.path.exists(path):
        return 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _db_connect()
    conn.execute("DELETE FROM library_items WHERE path = ?", (path,))
    count = 0
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                name = entry.name
                if entry.is_file() and name.lower().endswith('.zip'):
                    name = name[:-4]
                if not name.lower().endswith('.part'):
                    normalized = normalize_for_comparison(name)
                    conn.execute(
                        "INSERT OR IGNORE INTO library_items(path, name, scanned_at) VALUES(?, ?, ?)",
                        (path, normalized, now))
                    count += 1
    except Exception:
        pass
    conn.commit()
    conn.close()
    return count


def get_all_library_names() -> set:
    conn = _db_connect()
    rows = conn.execute("SELECT DISTINCT name FROM library_items").fetchall()
    conn.close()
    return {row[0] for row in rows}


def get_library_paths() -> list:
    conn = _db_connect()
    rows = conn.execute("SELECT DISTINCT path FROM library_items ORDER BY path").fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_library_path_counts() -> dict:
    conn = _db_connect()
    rows = conn.execute(
        "SELECT path, COUNT(*) FROM library_items GROUP BY path ORDER BY path"
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def remove_library_path(path: str):
    conn = _db_connect()
    conn.execute("DELETE FROM library_items WHERE path = ?", (path,))
    conn.commit()
    conn.close()
