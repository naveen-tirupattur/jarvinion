"""SQLite storage for feeds and entries."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS feeds (
    url                  TEXT PRIMARY KEY,
    title                TEXT,
    labels_json          TEXT NOT NULL DEFAULT '[]',
    etag                 TEXT,
    last_modified        TEXT,
    last_fetched_at      TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error           TEXT
);

CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_url     TEXT NOT NULL REFERENCES feeds(url),
    entry_key    TEXT NOT NULL,
    title        TEXT,
    url          TEXT,
    author       TEXT,
    published_at TEXT,
    summary      TEXT,
    content      TEXT,
    fetched_at   TEXT NOT NULL,
    UNIQUE(feed_url, entry_key)
);

CREATE INDEX IF NOT EXISTS idx_entries_fetched_at ON entries(fetched_at);
CREATE INDEX IF NOT EXISTS idx_entries_published_at ON entries(published_at);
CREATE INDEX IF NOT EXISTS idx_entries_url ON entries(url);
"""


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure schema exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    if current_version > SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(
            f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}"
        )
    conn.executescript(SCHEMA_SQL)
    if current_version < SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return conn


def upsert_feed(conn: sqlite3.Connection, url: str, labels: list[str]) -> None:
    """Insert or update a feed row (preserves fetch state on update)."""
    conn.execute(
        """INSERT INTO feeds (url, labels_json)
           VALUES (?, ?)
           ON CONFLICT(url) DO UPDATE SET labels_json = excluded.labels_json""",
        (url, json.dumps(labels)),
    )


def update_feed_success(
    conn: sqlite3.Connection,
    url: str,
    etag: str | None,
    last_modified: str | None,
    last_fetched_at: str,
    title: str | None = None,
) -> None:
    conn.execute(
        """UPDATE feeds
           SET title = COALESCE(?, title),
               etag = ?, last_modified = ?, last_fetched_at = ?,
               consecutive_failures = 0, last_error = NULL
           WHERE url = ?""",
        (title, etag, last_modified, last_fetched_at, url),
    )


def update_feed_failure(
    conn: sqlite3.Connection, url: str, error: str, last_fetched_at: str
) -> None:
    conn.execute(
        """UPDATE feeds
           SET consecutive_failures = consecutive_failures + 1,
               last_error = ?, last_fetched_at = ?
           WHERE url = ?""",
        (error, last_fetched_at, url),
    )


def insert_entry(
    conn: sqlite3.Connection,
    feed_url: str,
    entry_key: str,
    title: str | None,
    url: str | None,
    author: str | None,
    published_at: str | None,
    summary: str | None,
    content: str | None,
    fetched_at: str,
) -> bool:
    """Insert an entry if it doesn't already exist. Returns True if inserted."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO entries
           (feed_url, entry_key, title, url, author, published_at,
            summary, content, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            feed_url,
            entry_key,
            title,
            url,
            author,
            published_at,
            summary,
            content,
            fetched_at,
        ),
    )
    return cur.rowcount == 1


def get_feed(conn: sqlite3.Connection, url: str) -> dict | None:
    cur = conn.execute("SELECT * FROM feeds WHERE url = ?", (url,))
    row = cur.fetchone()
    return dict(row) if row else None


def count_entries(conn: sqlite3.Connection, feed_url: str | None = None) -> int:
    if feed_url:
        cur = conn.execute(
            "SELECT COUNT(*) FROM entries WHERE feed_url = ?", (feed_url,)
        )
    else:
        cur = conn.execute("SELECT COUNT(*) FROM entries")
    return cur.fetchone()[0]
