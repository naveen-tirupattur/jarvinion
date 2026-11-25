"""Command-line interface for feedwise."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from feedwise.config import load_config
from feedwise.db import open_db
from feedwise.ingest import run_ingest

DEFAULT_CONFIG = "config.yaml"
DEFAULT_DB = "data/feeds.db"


def cmd_ingest(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except Exception as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    if not config.feeds:
        print("No feeds configured.", file=sys.stderr)
        return 1

    conn = open_db(args.db)
    try:
        stats = run_ingest(config, conn)
        print(stats.summary())
        for err in stats.errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        healthy = stats.feeds_ok + stats.feeds_not_modified
        return 1 if healthy == 0 and stats.feeds_failed > 0 else 0
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="feedwise")
    sub = parser.add_subparsers(dest="command")

    ingest_p = sub.add_parser("ingest", help="Fetch and store configured RSS/Atom feeds")
    ingest_p.add_argument("--config", default=DEFAULT_CONFIG, help="Path to config.yaml")
    ingest_p.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "ingest":
        sys.exit(cmd_ingest(args))


if __name__ == "__main__":
    main()
