# T-001: Project scaffold, config loader, and RSS ingest to SQLite

Status: done

## Goal

Scaffold the `feedwise` Python project and implement `feedwise ingest` so configured RSS/Atom feeds are fetched, deduplicated, and stored reliably in SQLite (`data/feeds.db`).

## Behavior change

1. Docs-only repository → installable Python 3.11+ package (`src/feedwise/`, `pyproject.toml`, `tests/`).
2. No configuration handling → strict Pydantic loader for `config.yaml` (matching `DESIGN.md`), with a committed `config.example.yaml`.
3. No persistence → SQLite store (`data/feeds.db`) tracking feed fetch state (`feeds`) and deduplicated feed items (`entries`).
4. No ingestion command → `feedwise ingest` CLI command that fetches all configured feeds, stores new entries, skips duplicates, and isolates per-feed failures.

## Out of scope

- Unified `LLMClient` and Bedrock/Ollama/API integrations (`T-003`).
- Full-text article scraping (`trafilatura`), topic classification, and concept extraction.
- Daily digest generation, explainers, Knowledge Notes, web dashboard, or cron/APScheduler daemon.

## Data & contract impact

- Files / modules:
  - `pyproject.toml`
  - `config.example.yaml`
  - `.gitignore` (add `config.yaml` if keeping personal feeds local)
  - `src/feedwise/{__init__.py,config.py,db.py,ingest.py,cli.py}`
  - `tests/{test_config.py,test_ingest.py,fixtures/}`
- `config.yaml`, SQLite schema, or Markdown format changes:
  - Establishes initial `config.yaml` schema (`feeds`, `topics`, `schedule`, `learning`, `llm` sections per `DESIGN.md`; sections unused in T-001 still validate cleanly with sensible defaults).
  - Establishes initial SQLite schema in `data/feeds.db` (`PRAGMA user_version = 1`):
    - `feeds(url PRIMARY KEY, title, labels_json, etag, last_modified, last_fetched_at, consecutive_failures, last_error)`
    - `entries(id INTEGER PRIMARY KEY, feed_url, entry_key, title, url, author, published_at, summary, content, fetched_at, UNIQUE(feed_url, entry_key))` + indexes on `fetched_at`, `published_at`, and `url`
- Risk: touches durable data (establishes initial SQLite schema and `config.yaml` contract).
- Rollback path: delete `data/feeds.db` and revert the commit (no existing user data).

## Success & acceptance criteria

Observable outcomes that must be true before marking `done`:
- [x] `config.yaml` validation rejects malformed YAML, missing feed URLs, or unknown top-level keys (`extra="forbid"`) with clear error messages, and `config.example.yaml` validates cleanly.
- [x] RSS 2.0 and Atom feeds parse cleanly into `entries` with normalized UTC ISO-8601 `published_at` (nullable when absent), preserved feed labels, and deterministic `entry_key` (GUID/id first, falling back to normalized link, then content hash).
- [x] Re-running `feedwise ingest` on unchanged feed data inserts `0` duplicate rows and sends conditional GET headers (`ETag` / `If-Modified-Since`) when stored from a prior fetch.
- [x] A failing feed (timeout, HTTP 4xx/5xx, or malformed XML) records `last_error` and increments `consecutive_failures` in `feeds` without aborting ingestion of the remaining healthy feeds; a subsequent successful fetch resets `consecutive_failures` to `0` and clears `last_error`.
- [x] `feedwise ingest` prints a concise per-run summary (feeds fetched, new entries added, skipped duplicates, failed feeds).
- [x] All unit tests run completely offline using local RSS/Atom XML fixtures and mocked HTTP responses.

Verification checks:
- [x] Unit tests (offline): `uv run pytest tests/ -x --tb=short -q`
- [x] Prompt / quality check: N/A (no LLM prompts in T-001)
- [x] Manual check (inside `jarvinion-dev`):
  1. Run `uv run feedwise ingest --config config.example.yaml` against 2 live feeds (e.g., HN RSS + a blog Atom feed) and verify entries appear in `data/feeds.db`.
  2. Run the exact same command a second time and verify `0` new entries are inserted.
  3. Temporarily add an unreachable/invalid feed URL, re-run, and confirm healthy feeds still succeed while the error is recorded in the `feeds` table.

## Plan

1. Initialize `pyproject.toml` (Python 3.11+, `feedparser`, `httpx`, `pydantic`, `pyyaml`, dev dep `pytest`) and `src/feedwise/` package layout with `feedwise` CLI entry point.
2. Implement `config.py` with strict Pydantic models matching `DESIGN.md` and create `config.example.yaml`.
3. Implement `db.py` with idempotent SQLite schema initialization, feed metadata upserts, and deduplicated entry inserts.
4. Implement `ingest.py` using `httpx` (explicit timeout + conditional GET headers + clean User-Agent) piped into `feedparser`, plus per-feed error isolation and summary stats.
5. Wire `cli.py` (`feedwise ingest [--config PATH] [--db PATH]`).
6. Write offline unit tests in `tests/test_config.py` and `tests/test_ingest.py` with RSS 2.0, Atom, 304 Not Modified, duplicate-run, and error-isolation cases.
7. Run automated tests and manual check inside `jarvinion-dev`.

## Open questions (resolve before `approved`)

- ~~Should `config.yaml` be gitignored (keeping only `config.example.yaml` tracked) so your personal feed list stays local?~~ **Resolved:** Yes — add `config.yaml` to `.gitignore` and commit `config.example.yaml`.

## Trial record

Pre-filled by the agent at handoff; finalized when accepted (write `unknown` rather than guessing).
- Agent / model & reviewer: Claude Opus 4.6 (`us.anthropic.claude-opus-4-6-v1` on Bedrock, headless `--effort medium`) & reviewer: Antigravity + human
- Active time / rough cost: 3m 15s agent wall time (2m 10s build + 1m 05s repair, 57 turns total) / $1.65 reported Bedrock list cost ($1.02 build + $0.63 repair)
- Repair rounds before acceptance: 1 (4 code-review findings fixed + 5 tests added)
- Review findings that changed code:
  1. `ingest.py`: check `parsed.bozo and not parsed.entries` so malformed XML/HTML 200 error pages record failure instead of resetting `consecutive_failures`.
  2. `cli.py`: count `feeds_not_modified` as healthy when computing exit code.
  3. `db.py`: set `conn.row_factory` once in `open_db()` instead of mutating inside `get_feed()`; use `INSERT OR IGNORE` in `insert_entry()` so non-duplicate `IntegrityError` (FK violations) are not swallowed.
  4. `ingest.py`: fall back to Atom `updated_parsed` / `updated` when `published` is absent.
  5. `db.py` / `ingest.py`: removed duplicate `entries.labels_json` (kept `feeds.labels_json` as single source of truth), added `feeds.title`, `PRAGMA user_version = 1`, and `entries` indexes on `fetched_at`/`published_at`/`url`.
- Follow-ups (new `T-NNN` or `AGENTS.md` rule): `T-003` (Unified `LLMClient` with `decide()`, `complete()`, `complete_json()`, and `tools`).
- Defects found after acceptance: unknown

## Verification results (2026-11-24)

### Unit tests
```
uv run pytest tests/ -v --tb=short
28 passed in 0.30s
```

### Manual live-feed checks
1. `uv run feedwise ingest --config config.example.yaml --db /tmp/feedwise-test/feeds.db`
   → `Feeds fetched: 2  not modified: 0  failed: 0  | Entries new: 40  skipped: 0`
2. Same command re-run:
   → `Feeds fetched: 0  not modified: 2  failed: 0  | Entries new: 0  skipped: 0`
3. Config with bad URL (`https://this-domain-does-not-exist-feedwise-test.invalid/feed.xml`) + good HN feed:
   → `Feeds fetched: 1  not modified: 0  failed: 1  | Entries new: 20  skipped: 0`
   → Bad feed in DB: `consecutive_failures: 1`, `last_error: [Errno -2] Name or service not known`
