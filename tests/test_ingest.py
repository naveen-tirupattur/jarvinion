"""Tests for feed ingestion (all offline via mocked HTTP)."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from feedwise.cli import cmd_ingest
from feedwise.config import AppConfig, FeedConfig, load_config
from feedwise.db import count_entries, get_feed, insert_entry, open_db
from feedwise.ingest import IngestStats, ingest_feed, run_ingest

FIXTURES = Path(__file__).parent / "fixtures"


def _make_config(*feed_urls: str, labels: list[str] | None = None) -> AppConfig:
    feeds = [FeedConfig(url=u, labels=labels or []) for u in feed_urls]
    return AppConfig(feeds=feeds)


def _mock_response(
    body: str, status_code: int = 200, headers: dict | None = None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        text=body,
        headers=headers or {},
        request=httpx.Request("GET", "https://example.com"),
    )


class TestRSS2Ingestion:
    def test_rss2_entries_stored(self, db_conn, rss2_xml):
        config = _make_config("https://example.com/feed.xml", labels=["test"])
        stats = IngestStats()
        client = httpx.Client(transport=httpx.MockTransport(lambda req: _mock_response(rss2_xml)))
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        assert stats.feeds_ok == 1
        assert stats.entries_new == 2
        assert stats.entries_skipped == 0
        assert count_entries(db_conn) == 2

    def test_rss2_labels_stored_on_feed(self, db_conn, rss2_xml):
        config = _make_config("https://example.com/feed.xml", labels=["ai", "news"])
        client = httpx.Client(transport=httpx.MockTransport(lambda req: _mock_response(rss2_xml)))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        cur = db_conn.execute(
            """SELECT f.labels_json, f.title
               FROM entries e JOIN feeds f ON f.url = e.feed_url
               LIMIT 1"""
        )
        import json
        row = cur.fetchone()
        assert json.loads(row["labels_json"]) == ["ai", "news"]
        assert row["title"] is not None

        entry_cols = {
            r["name"] for r in db_conn.execute("PRAGMA table_info(entries)").fetchall()
        }
        assert "labels_json" not in entry_cols

    def test_rss2_published_at_normalized(self, db_conn, rss2_xml):
        config = _make_config("https://example.com/feed.xml")
        client = httpx.Client(transport=httpx.MockTransport(lambda req: _mock_response(rss2_xml)))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        cur = db_conn.execute("SELECT published_at FROM entries ORDER BY id")
        rows = cur.fetchall()
        assert rows[0][0] is not None
        assert "2026-11-18" in rows[0][0]


class TestAtomIngestion:
    def test_atom_entries_stored(self, db_conn, atom_xml):
        config = _make_config("https://atom.example.com/feed")
        client = httpx.Client(transport=httpx.MockTransport(lambda req: _mock_response(atom_xml)))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        assert stats.entries_new == 2
        assert count_entries(db_conn) == 2

    def test_atom_content_extracted(self, db_conn, atom_xml):
        config = _make_config("https://atom.example.com/feed")
        client = httpx.Client(transport=httpx.MockTransport(lambda req: _mock_response(atom_xml)))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        cur = db_conn.execute(
            "SELECT content FROM entries WHERE entry_key = 'urn:uuid:entry-1'"
        )
        row = cur.fetchone()
        assert row is not None
        assert "<p>" in row[0]


class TestDeduplication:
    def test_duplicate_run_inserts_zero(self, db_conn, rss2_xml):
        config = _make_config("https://example.com/feed.xml")
        transport = httpx.MockTransport(lambda req: _mock_response(rss2_xml))

        client = httpx.Client(transport=transport)
        with client:
            stats1 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats1)
            assert stats1.entries_new == 2

            stats2 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats2)
            assert stats2.entries_new == 0
            assert stats2.entries_skipped == 2

        assert count_entries(db_conn) == 2

    def test_304_not_modified(self, db_conn, rss2_xml):
        call_count = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(
                    rss2_xml,
                    headers={"ETag": '"abc123"', "Last-Modified": "Mon, 18 Nov 2026 12:00:00 GMT"},
                )
            return _mock_response("", status_code=304)

        config = _make_config("https://example.com/feed.xml")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with client:
            stats1 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats1)
            assert stats1.entries_new == 2

            stats2 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats2)
            assert stats2.feeds_not_modified == 1
            assert stats2.entries_new == 0

    def test_conditional_get_headers_sent(self, db_conn, rss2_xml):
        requests_seen: list[httpx.Request] = []

        def handler(req: httpx.Request) -> httpx.Response:
            requests_seen.append(req)
            if len(requests_seen) == 1:
                return _mock_response(
                    rss2_xml,
                    headers={"ETag": '"etag-val"', "Last-Modified": "Mon, 18 Nov 2026 00:00:00 GMT"},
                )
            return _mock_response("", status_code=304)

        config = _make_config("https://example.com/feed.xml")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with client:
            stats = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats)
            ingest_feed(db_conn, client, config.feeds[0], stats)

        second_req = requests_seen[1]
        assert second_req.headers.get("If-None-Match") == '"etag-val"'
        assert second_req.headers.get("If-Modified-Since") == "Mon, 18 Nov 2026 00:00:00 GMT"


class TestErrorIsolation:
    def test_failing_feed_does_not_block_others(self, db_conn, rss2_xml):
        def handler(req: httpx.Request) -> httpx.Response:
            if "bad" in str(req.url):
                return _mock_response("", status_code=500)
            return _mock_response(rss2_xml)

        config = _make_config(
            "https://example.com/good-feed.xml",
            "https://example.com/bad-feed.xml",
        )
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with client:
            stats = run_ingest.__wrapped__(config, db_conn) if hasattr(run_ingest, '__wrapped__') else _run_ingest_with_client(config, db_conn, client)

        assert stats.feeds_ok == 1
        assert stats.feeds_failed == 1
        assert stats.entries_new == 2

        bad_feed = get_feed(db_conn, "https://example.com/bad-feed.xml")
        assert bad_feed is not None
        assert bad_feed["consecutive_failures"] == 1
        assert bad_feed["last_error"] == "HTTP 500"

    def test_timeout_records_error(self, db_conn):
        def handler(req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("connection timed out")

        config = _make_config("https://example.com/slow-feed.xml")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)

        assert stats.feeds_failed == 1
        feed = get_feed(db_conn, "https://example.com/slow-feed.xml")
        assert feed["consecutive_failures"] == 1
        assert "timed out" in feed["last_error"]

    def test_success_after_failure_resets_counter(self, db_conn, rss2_xml):
        call_count = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response("", status_code=503)
            return _mock_response(rss2_xml)

        config = _make_config("https://example.com/flaky.xml")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with client:
            stats1 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats1)
            assert stats1.feeds_failed == 1

            feed = get_feed(db_conn, "https://example.com/flaky.xml")
            assert feed["consecutive_failures"] == 1

            stats2 = IngestStats()
            ingest_feed(db_conn, client, config.feeds[0], stats2)
            assert stats2.feeds_ok == 1

            feed = get_feed(db_conn, "https://example.com/flaky.xml")
            assert feed["consecutive_failures"] == 0
            assert feed["last_error"] is None


class TestSummaryOutput:
    def test_summary_format(self):
        stats = IngestStats(
            feeds_ok=3, feeds_not_modified=1, feeds_failed=1,
            entries_new=15, entries_skipped=5,
        )
        s = stats.summary()
        assert "3" in s
        assert "15" in s
        assert "5" in s


def _run_ingest_with_client(
    config: AppConfig, db_conn, client: httpx.Client
) -> IngestStats:
    """Helper to run ingest with a pre-built client (for mocked transport)."""
    stats = IngestStats()
    for feed_cfg in config.feeds:
        ingest_feed(db_conn, client, feed_cfg, stats)
    return stats


class TestMalformedFeed:
    def test_malformed_xml_records_failure(self, db_conn):
        malformed = "this is not xml at all {{{"
        config = _make_config("https://example.com/broken.xml")
        client = httpx.Client(
            transport=httpx.MockTransport(lambda req: _mock_response(malformed))
        )
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        assert stats.feeds_failed == 1
        assert stats.feeds_ok == 0
        assert len(stats.errors) == 1
        assert "Malformed feed" in stats.errors[0]
        feed = get_feed(db_conn, "https://example.com/broken.xml")
        assert feed["consecutive_failures"] == 1


class TestExitCode:
    def test_304_only_is_healthy(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "feeds:\n  - url: https://example.com/feed.xml\n"
        )
        db_path = tmp_path / "data" / "feeds.db"
        args = argparse.Namespace(config=str(config_path), db=str(db_path))

        with patch("feedwise.cli.run_ingest") as mock_run:
            mock_run.return_value = IngestStats(
                feeds_ok=0, feeds_not_modified=2, feeds_failed=0
            )
            rc = cmd_ingest(args)
        assert rc == 0

    def test_all_failed_is_error(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "feeds:\n  - url: https://example.com/feed.xml\n"
        )
        db_path = tmp_path / "data" / "feeds.db"
        args = argparse.Namespace(config=str(config_path), db=str(db_path))

        with patch("feedwise.cli.run_ingest") as mock_run:
            mock_run.return_value = IngestStats(
                feeds_ok=0, feeds_not_modified=0, feeds_failed=3,
                errors=["a", "b", "c"],
            )
            rc = cmd_ingest(args)
        assert rc == 1


class TestInsertEntryFKViolation:
    def test_fk_violation_raises_integrity_error(self, db_conn):
        with pytest.raises(sqlite3.IntegrityError):
            insert_entry(
                db_conn,
                feed_url="https://no-such-feed.example.com/rss",
                entry_key="key-1",
                title="Title",
                url="https://example.com",
                author=None,
                published_at=None,
                summary=None,
                content=None,
                fetched_at="2026-01-01T00:00:00+00:00",
            )


class TestSchemaAndFeedTitle:
    def test_schema_version_set(self, db_conn):
        from feedwise.db import SCHEMA_VERSION

        version = db_conn.execute("PRAGMA user_version").fetchone()[0]
        assert version == SCHEMA_VERSION

    def test_feed_title_preserved_on_304(self, db_conn, rss2_xml):
        calls = 0

        def handler(req: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return _mock_response(rss2_xml, headers={"ETag": '"t1"'})
            return _mock_response("", status_code=304)

        config = _make_config("https://example.com/feed.xml")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
            title_after_200 = get_feed(db_conn, "https://example.com/feed.xml")["title"]
            assert title_after_200 is not None
            ingest_feed(db_conn, client, config.feeds[0], stats)
            title_after_304 = get_feed(db_conn, "https://example.com/feed.xml")["title"]
            assert title_after_304 == title_after_200


class TestAtomDateFallback:
    def test_updated_used_when_published_absent(self, db_conn):
        atom_no_published = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test</title>
  <id>urn:uuid:test</id>
  <updated>2026-11-20T10:00:00Z</updated>
  <entry>
    <title>No Published</title>
    <link href="https://example.com/1"/>
    <id>urn:uuid:no-pub-1</id>
    <updated>2026-11-19T08:30:00Z</updated>
    <summary>Entry with only updated, no published.</summary>
  </entry>
</feed>"""
        config = _make_config("https://example.com/atom-nopub")
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda req: _mock_response(atom_no_published)
            )
        )
        stats = IngestStats()
        with client:
            ingest_feed(db_conn, client, config.feeds[0], stats)
        assert stats.entries_new == 1
        cur = db_conn.execute(
            "SELECT published_at FROM entries WHERE entry_key = 'urn:uuid:no-pub-1'"
        )
        row = cur.fetchone()
        assert row is not None
        assert "2026-11-19" in row["published_at"]
