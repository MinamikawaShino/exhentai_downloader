import sqlite3
from pathlib import Path

from .. import DATA_DIR

_DB_DEFAULT = Path(DATA_DIR) / "imgchk.db"


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = str(Path(db_path) if db_path else _DB_DEFAULT)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self._connect()
            conn.close()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def _init_tables(self, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                file_size INTEGER NOT NULL,
                file_mtime REAL NOT NULL,
                scan_status TEXT NOT NULL,
                error_reason TEXT,
                engine TEXT,
                scanned_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duplicate_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                original_path TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                kept_path TEXT NOT NULL,
                file_size INTEGER,
                status TEXT DEFAULT 'moved',
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_path ON scan_cache(file_path)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON scan_cache(file_hash) WHERE file_hash IS NOT NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dup_status ON duplicate_records(status)")

    def load_cache_map(self, source_dir: str) -> dict:
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        prefix = source_dir.replace("\\", "/") + "/"
        cur.execute(
            "SELECT file_path, file_size, file_mtime FROM scan_cache "
            "WHERE scan_status = 'normal' AND file_path LIKE ?",
            (prefix + "%",)
        )
        rows = cur.fetchall()
        conn.close()
        return {row[0]: (row[1], row[2]) for row in rows}

    def insert_scan_cache(self, entries: list[tuple]):
        if not entries:
            return
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute("BEGIN")
        cur.executemany("""
            INSERT INTO scan_cache
                (file_path, file_hash, file_size, file_mtime, scan_status, error_reason, engine)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                file_size = excluded.file_size,
                file_mtime = excluded.file_mtime,
                scan_status = excluded.scan_status,
                error_reason = excluded.error_reason,
                engine = excluded.engine,
                scanned_at = datetime('now','localtime')
        """, entries)
        conn.commit()
        conn.close()

    def insert_duplicates(self, entries: list[tuple]):
        if not entries:
            return
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute("BEGIN")
        cur.executemany("""
            INSERT INTO duplicate_records
                (file_hash, original_path, stored_path, kept_path, file_size)
            VALUES (?,?,?,?,?)
        """, entries)
        conn.commit()
        conn.close()

    def load_duplicates(self, status="moved") -> list[dict]:
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute(
            "SELECT id, file_hash, original_path, stored_path, "
            "kept_path, file_size, status "
            "FROM duplicate_records WHERE status = ? ORDER BY id",
            (status,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{
            "id": r[0], "hash": r[1], "original_path": r[2],
            "stored_path": r[3], "kept_path": r[4],
            "file_size": r[5], "status": r[6],
        } for r in rows]

    def update_duplicate_status(self, record_ids: list[int], new_status: str):
        if not record_ids:
            return
        conn = self._connect()
        cur = conn.cursor()
        for rid in record_ids:
            cur.execute(
                "UPDATE duplicate_records SET status = ? WHERE id = ?",
                (new_status, rid)
            )
        conn.commit()
        conn.close()

    def delete_duplicate_records(self, record_ids: list[int]):
        if not record_ids:
            return
        conn = self._connect()
        cur = conn.cursor()
        for rid in record_ids:
            cur.execute("DELETE FROM duplicate_records WHERE id = ?", (rid,))
        conn.commit()
        conn.close()

    def count_cache(self) -> int:
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM scan_cache")
        count = cur.fetchone()[0]
        conn.close()
        return count

    def clear_scan_cache(self):
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute("DELETE FROM scan_cache")
        conn.commit()
        conn.close()

    def clear_duplicate_records(self):
        conn = self._connect()
        cur = conn.cursor()
        self._init_tables(cur)
        conn.commit()
        cur.execute("DELETE FROM duplicate_records")
        conn.commit()
        conn.close()