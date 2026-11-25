"""RSS/Atom feed ingestion pipeline."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time

import feedparser
import httpx

from feedwise.config import AppConfig, FeedConfig
from feedwise.db import (
    insert_entry,
    update_feed_failure,
    update_feed_success,
    upsert_feed,
)

FETCH_TIMEOUT = 30.0
USER_AGENT = "Feedwise/0.1 (+https://github.com/feedwise)"


@dataclass
class IngestStats:
    feeds_ok: int = 0
    feeds_not_modified: int = 0
    feeds_failed: int = 0
    entries_new: int = 0
    entries_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"Feeds fetched: {self.feeds_ok}",
            f"not modified: {self.feeds_not_modified}",
            f"failed: {self.feeds_failed}",
            f"| Entries new: {self.entries_new}",
            f"skipped: {self.entries_skipped}",
        ]
        return "  ".join(parts)


def _normalize_published(
    raw: str | struct_time | None,
) -> str | None:
    """Normalize a published date to UTC ISO-8601 string, or None."""
    if raw is None:
        return None
    if isinstance(raw, struct_time):
        try:
            dt = datetime(*raw[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError):
            return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return None
    return None


def _entry_key(entry: dict) -> str:
    """Deterministic key: GUID/id first, then link, then content hash."""
    guid = entry.get("id") or entry.get("guid")
    if guid:
        return guid.strip()
    link = entry.get("link")
    if link:
        return link.strip()
    content = entry.get("summary", "") + entry.get("title", "")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _best_content(entry: dict) -> str | None:
    """Extract the best content field from a feedparser entry."""
    if "content" in entry and entry["content"]:
        for c in entry["content"]:
            if c.get("value"):
                return c["value"]
    return None


def _fetch_feed(
    client: httpx.Client,
    feed_url: str,
    etag: str | None,
    last_modified: str | None,
) -> httpx.Response:
    headers: dict[str, str] = {"User-Agent": USER_AGENT}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return client.get(feed_url, headers=headers, timeout=FETCH_TIMEOUT, follow_redirects=True)


def ingest_feed(
    conn: sqlite3.Connection,
    client: httpx.Client,
    feed_cfg: FeedConfig,
    stats: IngestStats,
) -> None:
    """Fetch and store a single feed. Updates stats in-place."""
    feed_url = str(feed_cfg.url)
    now_iso = datetime.now(timezone.utc).isoformat()

    upsert_feed(conn, feed_url, feed_cfg.labels)

    from feedwise.db import get_feed

    feed_row = get_feed(conn, feed_url)
    etag = feed_row["etag"] if feed_row else None
    last_modified = feed_row["last_modified"] if feed_row else None

    try:
        resp = _fetch_feed(client, feed_url, etag, last_modified)
    except (httpx.HTTPError, OSError) as exc:
        update_feed_failure(conn, feed_url, str(exc), now_iso)
        conn.commit()
        stats.feeds_failed += 1
        stats.errors.append(f"{feed_url}: {exc}")
        return

    if resp.status_code == 304:
        update_feed_success(conn, feed_url, etag, last_modified, now_iso)
        conn.commit()
        stats.feeds_not_modified += 1
        return

    if resp.status_code >= 400:
        err = f"HTTP {resp.status_code}"
        update_feed_failure(conn, feed_url, err, now_iso)
        conn.commit()
        stats.feeds_failed += 1
        stats.errors.append(f"{feed_url}: {err}")
        return

    parsed = feedparser.parse(resp.text)

    if parsed.bozo and not parsed.entries:
        err = f"Malformed feed: {parsed.bozo_exception}"
        update_feed_failure(conn, feed_url, err, now_iso)
        conn.commit()
        stats.feeds_failed += 1
        stats.errors.append(f"{feed_url}: {err}")
        return

    new_etag = resp.headers.get("ETag")
    new_last_modified = resp.headers.get("Last-Modified")
    feed_title = (parsed.feed.get("title") or "").strip() or None
    update_feed_success(
        conn, feed_url, new_etag, new_last_modified, now_iso, title=feed_title
    )

    for entry in parsed.entries:
        key = _entry_key(entry)
        pub_raw = (
            entry.get("published_parsed")
            or entry.get("published")
            or entry.get("updated_parsed")
            or entry.get("updated")
        )
        published_at = _normalize_published(pub_raw)

        inserted = insert_entry(
            conn,
            feed_url=feed_url,
            entry_key=key,
            title=entry.get("title"),
            url=entry.get("link"),
            author=entry.get("author"),
            published_at=published_at,
            summary=entry.get("summary"),
            content=_best_content(entry),
            fetched_at=now_iso,
        )
        if inserted:
            stats.entries_new += 1
        else:
            stats.entries_skipped += 1

    conn.commit()
    stats.feeds_ok += 1


def run_ingest(config: AppConfig, db_conn: sqlite3.Connection) -> IngestStats:
    """Run the full ingestion pipeline for all configured feeds."""
    stats = IngestStats()
    with httpx.Client() as client:
        for feed_cfg in config.feeds:
            ingest_feed(db_conn, client, feed_cfg, stats)
    return stats
