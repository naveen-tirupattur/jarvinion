# AGENTS.md

Feedwise is a personal RSS learning agent (Python 3.11+, SQLite + FTS5, plain Markdown, FastAPI + HTMX). Full architecture and milestones live in `DESIGN.md`.

## Core invariants

- **Ownership boundary:**
  - `digests/YYYY-MM-DD.md` — AI-owned, ephemeral, idempotent per date.
  - `knowledge/explainers/<slug>.md` — AI-owned, regenerable scaffolding.
  - `knowledge/<slug>.md` — `## My Notes` (and anything outside `<!-- auto:start --> ... <!-- auto:end -->`) is **strictly human-owned**. Never overwrite user prose.
- **Hybrid execution model:** Scheduled ingest, triage, and digest generation stay deterministic Python pipelines with targeted `decide()` / structured LLM calls (no autonomous tool loops over untrusted RSS HTML). Only on-demand Explainer and Coach flows use a bounded read-only tool-calling loop.
- **Terminology (avoid "tags"):**
  - **Feed labels** (`labels` in `config.yaml`) — user-owned coarse source attributes on a feed.
  - **Topics** (`topics` in `config.yaml` + `Other`) — bounded taxonomy assigned to entries via `decide()` for digest grouping; propose new topics from `Other` clusters rather than silently adding.
  - **Concepts** — open, granular technical ideas extracted from entries (tracked as candidates in SQLite until promoted to `knowledge/<slug>.md`).

## Commands

Python is managed with `uv` (3.11+).

| Command | Purpose |
|---|---|
| `uv sync` | Install / sync dependencies |
| `uv run pytest tests/ -x --tb=short -q` | Run all tests (offline) |
| `uv run pytest tests/<file> -x --tb=short -q` | Run one test file |
| `uv run feedwise ingest` | Fetch and store configured RSS/Atom feeds |

## Correctness-critical contracts

Extra care, explicit tests, and a stated rollback path are required when changing:
- `config.yaml` Pydantic schema (`extra="forbid"`).
- SQLite schema and migrations in `data/feeds.db`.
- Markdown note frontmatter and `<!-- auto:start --> ... <!-- auto:end -->` markers.

## Working practices

- Run `git status --short` first and leave unrelated local changes alone.
- Work from a task file in `tasks/T-NNN-<slug>.md` (created from `tasks/TEMPLATE.md`). Do not write implementation code until the task's `Status` is `approved`.
- Stay strictly within the task's scope and respect `## Out of scope`. Put follow-up ideas into a new task rather than expanding the current one.
- Prefer targeted changes over refactors. Do not add dependencies without stating why.
- At handoff, summarize files changed, checks run with exact results, anything skipped, and pre-fill `## Trial record` in the task file (write `unknown` rather than guessing). Move the task to `tasks/done/` once merged.

## Conventions

- Pydantic models are strict (`extra="forbid"`) and fail fast on invalid config/data.
- All unit tests must run **completely offline** using local fixtures and mocked HTTP / LLM responses — never hit live feeds or paid LLM APIs in `pytest`.
- Every outbound HTTP call must set an explicit timeout and handle errors per-feed/per-entry without crashing the batch.
- Never commit `.env`, `config.yaml` (commit `config.example.yaml` instead), `data/feeds.db`, credentials, or personal notes in `knowledge/`.
