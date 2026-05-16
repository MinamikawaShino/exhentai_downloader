import datetime
from .library import _db_connect


def save_gallery_metadata(url: str, title: str, title_jp: str = "",
                          artist: str = "", category: str = "", tags: str = "",
                          file_count: int = 0, file_size: str = ""):
    conn = _db_connect()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT OR REPLACE INTO gallery_metadata
        (url, title, title_jp, artist, category, tags, file_count, file_size, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (url, title, title_jp, artist, category, tags, file_count, file_size, now))
    conn.commit()
    conn.close()


def get_gallery_metadata(url: str) -> dict | None:
    conn = _db_connect()
    row = conn.execute(
        "SELECT * FROM gallery_metadata WHERE url = ?", (url,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "url": row[0], "title": row[1], "title_jp": row[2],
            "artist": row[3], "category": row[4], "tags": row[5],
            "file_count": row[6], "file_size": row[7], "downloaded_at": row[8],
        }
    return None


def has_metadata(url: str) -> bool:
    conn = _db_connect()
    row = conn.execute(
        "SELECT 1 FROM gallery_metadata WHERE url = ?", (url,)
    ).fetchone()
    conn.close()
    return row is not None
