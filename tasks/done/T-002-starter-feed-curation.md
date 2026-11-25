# T-002: Audit Feedly OPML feeds & curate top 15 starter set

Status: done

## Goal

Probe all feed URLs in the repo's Feedly `subscriptions.opml` (ignoring existing Feedly folder labels), inspect their live health, `ETag`/`Last-Modified` support, posting recency, and content, and produce `starter-feeds.md` recommending the top 15 starter feeds with fresh suggested `labels` so the user can pick their initial `config.yaml` feeds.

## Behavior change

1. Raw 57-feed Feedly OPML dump with outdated/broken URLs and coarse folders → curated `starter-feeds.md` report with a ranked Top 15 starter set (with suggested `labels` and a ready-to-paste `config.yaml` snippet) plus a status appendix of all remaining feeds.
2. Personal Feedly archive not gitignored → `.gitignore` ignores `feedly-*-archive/`, `*.opml`, and `starter-feeds.md` so personal subscriptions stay local.

## Out of scope

- Editing `config.yaml` or ingesting into `data/feeds.db` (user will review `starter-feeds.md` and pick feeds first).
- Changing `src/feedwise/` application code or SQLite schema.
- Building a permanent `import-opml` CLI command (can be a separate task later if needed).

## Data & contract impact

- Files / modules:
  - `starter-feeds.md` (new — generated curation report for user review)
  - `.gitignore` (add `feedly-*-archive/`, `*.opml`, `starter-feeds.md`)
- `config.yaml`, SQLite schema, or Markdown format changes: none.
- Risk: routine (read-only HTTP GET probes against OPML URLs; writes only `starter-feeds.md` and `.gitignore`).
- Rollback path: delete `starter-feeds.md` and revert `.gitignore`.

## Success & acceptance criteria

Observable outcomes that must be true before marking `done`:
- [x] Every feed URL in `feedly-*/subscriptions.opml` (all 57) is probed live with an explicit timeout (`httpx` + `feedparser`), capturing: HTTP status, final redirected URL (if redirected), `ETag` header presence, `Last-Modified` header presence, valid RSS/Atom parse (`bozo` check), entry count, latest entry date, and 2–3 recent entry titles.
- [x] Existing Feedly folder labels (`Tech`, `Misc`, `Data/AI/ML`) are **ignored**; fresh, clean lowercase feed `labels` (2–3 per feed, e.g., `[ai, research]`, `[distributed-systems, engineering]`, `[llm, practical]`) are proposed based on each feed's actual content and style.
- [x] `starter-feeds.md` contains:
  1. **Top 15 Recommended Starter Feeds** table & notes — selected for active/recent publishing, clean RSS/Atom parsing, `ETag`/`Last-Modified` conditional-GET support where available, and strong diversity + signal-to-noise (avoiding dead/stale/broken feeds).
  2. Each Top 15 entry lists: feed title, best URL (preferring clean HTTPS / final redirect target), `ETag` (`yes`/`no`), `Last-Modified` (`yes`/`no`), latest post date, suggested `labels`, and a 1-line reason why it made the top 15.
  3. A **ready-to-copy `feeds:` YAML block** (validated against `AppConfig` schema) for easy pasting into `config.yaml`.
  4. **All Other Feeds** appendix table grouping the remaining feeds (Active, Stale/Slow, Broken/Failed with exact error/status) so the user can swap in any personal favorites.
- [x] Existing unit tests still pass (`uv run pytest tests/ -x --tb=short -q`) and no temporary probe scripts are left behind in `/workspace`.

Verification checks:
- [x] Unit tests: `uv run pytest tests/ -x --tb=short -q`
- [x] Prompt / quality check: Verify every Top 15 feed URL in `starter-feeds.md` returned HTTP 200 with valid parsed entries and suggested `labels` are non-empty lowercase strings.
- [x] Manual check: Inspect `starter-feeds.md` for completeness (all 57 OPML feeds accounted for across Top 15 + Appendix).

## Plan

1. Run a temporary Python probe script (in `/tmp`, cleaned up afterward) using the container's `uv` environment (`httpx` + `feedparser` + `xml.etree.ElementTree`) to fetch all 57 URLs from `feedly-*/subscriptions.opml` concurrently with a clean User-Agent and timeout, recording status, final URL, `ETag`, `Last-Modified`, parse health, entry count, latest date, and sample titles.
2. Analyze the results (ignoring original Feedly folders) to rank the Top 15 highest-signal, active, healthy feeds (preferring `ETag`/`Last-Modified` support and strong topic diversity) and assign clean, consistent `labels`.
3. Write `starter-feeds.md` with the Top 15 table, ready-to-copy `feeds:` YAML snippet (verified to parse under `FeedConfig`), and the full appendix of the remaining feeds.
4. Update `.gitignore` to ignore `feedly-*-archive/`, `*.opml`, and `starter-feeds.md`.
5. Run `uv run pytest tests/ -x --tb=short -q`, clean up `/tmp` probe script, set `Status: in review`, and pre-fill `## Trial record`.

## Open questions (resolve before `approved`)

- None (approve to launch Claude headlessly in `jarvinion-dev`).

## Trial record

Pre-filled by the agent at handoff; finalized when accepted (write `unknown` rather than guessing).
- Agent / model & reviewer: Claude Opus 4.6 (`us.anthropic.claude-opus-4-6-v1` on Bedrock, headless `--effort medium`) & reviewer: Antigravity + human
- Active time / rough cost: 2m 03s wall time (19 turns) / $0.87 reported Bedrock list cost ($0.8697)
- Repair rounds before acceptance: 0
- Review findings that changed code: none
- Follow-ups (new `T-NNN` or `AGENTS.md` rule): Consider a future `T-NNN` for an `import-opml` CLI command; consider adding a Substack-compatible User-Agent or RSS proxy strategy to handle the 10 Substack 403s.
- Defects found after acceptance: unknown
