# Feedwise — Personal RSS Learning Agent

**A personal learning agent that turns your RSS feeds into a 5–15 minute daily habit: triaging signal from noise, bridging unfamiliar concepts to what you already know, and growing a human-owned knowledge base.**

---

## Problem

Keeping up with RSS feeds across multiple domains is a firehose. Standard RSS summarizers and auto-generated AI wikis fail for the same reason: **passive reading feels productive, but without active synthesis nothing sticks**, and an agent that auto-creates hundreds of notes turns into a second unread backlog.

## Core Design Principle

Separate **three distinct jobs** with clear ownership boundaries:

1. **Daily Digest (AI-owned, ephemeral)** — A 5-minute decision surface that separates signal from noise, contrasts new developments against threads you already track, surfaces trending candidate concepts, and resurfaces `learning` notes when feeds mention them again.
2. **Explainers & Follow-up Q&A (AI-owned, regenerable scaffolding)** — Contextual bridges for concepts you don't know yet: anchored to the *triggering article(s)* and connected explicitly to *your existing notes*, with quick depth controls (`Simpler`, `Deeper`, `Compare`) and scoped follow-up Q&A.
3. **Knowledge Notes (Human-owned, AI-assisted)** — Compact Markdown notes where **you** own `## My Notes` (2–3 sentences in your own words, edited in the dashboard or directly in any Markdown editor). The agent never overwrites your prose; it only maintains `Sources`, `Related`, and metadata inside marked blocks.

---

## The Daily Learning Loop

1. **Scan the digest (3–5 min):** Read prioritized topic updates, see resurfaced notes when a `learning` concept shows up in fresh news, and triage candidate concepts with 1-click actions (`Explain`, `Already know`, `Ignore`).
2. **Understand via a contextual explainer (3–5 min):** Open an unfamiliar concept to get:
   - *Why it came up* (triggering feed entries)
   - *30-second intuition* + concrete example
   - *Connections to your notes* (contrasted with 2–3 related notes you already understand)
   - *Common pitfall / boundary condition*
   - *1–2 conceptual check questions*
   - *Iterative refinement:* ask scoped follow-up questions or regenerate (`Simpler` / `Deeper` / `Compare with [[note]]`).
3. **Lock it in (1–2 min):** Write a 2–3 sentence takeaway in the dashboard's `My Understanding` box, optionally click **`Check my note`** for targeted feedback on gaps or nuances, and save as `learning` or `understood`.

Writing that short takeaway directly improves every future digest and explainer because your own `## My Notes` text becomes the grounding context for what you already know.

---

## Architecture

```
                     ┌─────────────┐
                     │  RSS Feeds  │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Ingester   │  fetch + parse + dedup (SQLite)
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │  Processor  │  triage on RSS, tiered full-text fetch,
                     │  & Triager  │  topic classification, candidate concepts
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼─────┐ ┌─────▼──────┐ ┌────▼─────────────┐
       │ Summarizer │ │  Explainer │ │  Note Manager    │
       │  (daily)   │ │  & Coach   │ │  & FTS5 Indexer  │
       └──────┬─────┘ └─────┬──────┘ └────┬─────────────┘
              │             │             │
              └─────────────┼─────────────┘
                            │
                     ┌──────▼──────┐
                     │  Dashboard  │  FastAPI + HTMX learning workspace
                     │  (Web UI)   │  (digest, explain, Q&A, edit notes)
                     └─────────────┘
```

### Components

| Component | Responsibility | Storage |
|---|---|---|
| **Ingester** | Fetches RSS/Atom feeds on schedule. Deduplicates by entry GUID/URL. Handles per-feed errors and backoff without failing the batch. | SQLite (`feeds.db`) |
| **Processor & Triager** | Scores and classifies entries using RSS title + summary against user topics. Fetches full article text only for entries passing relevance (or on-demand when explaining), with graceful fallback on paywalls/errors. Extracts candidate concepts using existing canonical titles/aliases to reduce duplicates. | SQLite (`feeds.db`) |
| **Summarizer** | Generates an idempotent daily digest grouped by topic. Distinguishes new developments from continuations of tracked notes, highlights trending candidate concepts, and resurfaces `learning` notes matched by new entries. | Markdown (`digests/YYYY-MM-DD.md`) |
| **Explainer & Coach** | Runs a bounded, on-demand tool-calling agent (read-only tools: `search_my_notes`, `read_note`, `get_feed_entries`, `fetch_article`, optional `web_search`) to generate contextual explainers grounded in triggering entries and your `## My Notes`. Powers scoped follow-up Q&A, depth regeneration, and `Check my note` feedback. | Markdown (`knowledge/explainers/<slug>.md`) + SQLite (Q&A threads) |
| **Note Manager & Indexer** | Reads/writes `knowledge/<slug>.md` while strictly preserving human-authored sections outside `<!-- auto:start --> ... <!-- auto:end -->`. Maintains an SQLite FTS5 index, alias table, backlinks, and 1-click merge for near-duplicate concepts. | Markdown (`knowledge/<slug>.md`) + SQLite FTS5 |
| **Dashboard** | Primary daily workspace (FastAPI + HTMX): browse digests, triage candidate concepts (`Explain`, `Already know`, `Ignore`, `Merge`), run follow-up Q&A, edit `## My Notes` inline, and browse/search the knowledge graph. Re-syncs external edits made directly to Markdown files on disk. | Reads/writes Markdown + SQLite |

---

## Classification Layers (Feed Labels, Topics, Concepts)

Avoid overloaded "tags" by keeping three distinct layers with clear ownership:

| Layer | Attached to | Vocabulary | Managed by | Purpose |
|---|---|---|---|---|
| **Feed labels** | Feed (`config.yaml`) | Coarse source attributes (`ai`, `research`, `aggregator`) | **User** (optionally suggested once when adding a feed) | Source filtering & soft context prior for triage |
| **Topics** | Entry (SQLite) | Bounded taxonomy (configured `topics` + `Other`) | **Feedwise (`decide()`)** — proposes new topics when `Other` clusters, never silently adds | Grouping the Daily Digest into stable sections |
| **Concepts** | Entry ↔ Concept table (SQLite) | Open, granular technical ideas (`PagedAttention`, `Raft pre-vote`) | **Feedwise (`complete_json()`)** — canonicalized against existing notes/aliases | Surfacing candidate concepts, Explainers, `## Sources`, spaced resurface |

---

## Knowledge Note Format & Ownership

Only concepts you intentionally engage with (save a takeaway, mark `learning`/`understood`, or promote from a digest) become files in `knowledge/`. Candidate concepts remain lightweight rows in SQLite until promoted.

```markdown
---
title: PagedAttention
aliases: [paged-attention]
status: learning          # learning | understood
topics: [LLMs, Systems]
first_seen: 2026-11-23
last_reviewed: 2026-11-23
---

## My Notes
Applies OS virtual-memory paging to LLM KV-caches so attention blocks don't
need contiguous GPU memory, reducing fragmentation under batched serving.

<!-- auto:start -->
## Explainer
- [[explainers/paged-attention]]

## Related
- [[kv-cache]]
- [[virtual-memory]]

## Sources
- [vLLM architecture deep dive](https://example.com/article1) — 2026-11-23
<!-- auto:end -->
```

**Ownership rule:** The agent may only update frontmatter fields (`aliases`, `topics`, `last_seen`) and the block between `<!-- auto:start -->` and `<!-- auto:end -->`. Everything in `## My Notes` (and any custom sections outside the markers) is strictly user-owned—editable via the dashboard or any Markdown editor (Obsidian, VS Code, etc.).

---

## LLM Backend (Provider-Agnostic)

All model calls go through a thin unified `LLMClient` interface supporting four primitives, configured per task in `config.yaml`:

- **`decide()`** — Typed System-1 decisions (`choice`, `boolean`, `score` + calibrated confidence) for high-volume triage, full-text fetch gating, resurface filtering, and concept dedup routing. Backed by Haiku/Ollama via constrained JSON initially, and directly swappable for dedicated decision models (e.g., **Jev**, Gemini Decisions API, or local *LLM-as-Jev*) without changing business logic.
- **`complete()` / `complete_json()`** — Structured extraction and daily digest synthesis.
- **`tools`** — Native tool calling for the bounded on-demand Explainer & Coach loop.

Supported providers:

- **AWS Bedrock (`bedrock`)** — e.g., Claude Haiku 4.5 for fast/cheap triage and extraction, Claude Opus 4.6 / Sonnet for explainers and note coaching.
- **Direct cloud APIs (`anthropic`, `openai`, `gemini`)** — swap in via API keys if preferred.
- **Local LLMs (`ollama` or any OpenAI-compatible local server)** — local inference (`http://localhost:11434` on host or `http://host.docker.internal:11434` in Docker) when privacy or offline use is preferred.

*(Note: Consumer web subscriptions for Claude, ChatGPT, and Gemini are billed separately from developer APIs; Bedrock or API keys are used for reliable programmatic calls.)*

---

## User Configuration

A single `config.yaml` at the project root:

```yaml
feeds:
  - url: https://example.com/feed.xml
    labels: [ai, research]
  - url: https://news.ycombinator.com/rss
    labels: [tech, aggregator]

topics:
  - name: "Distributed Systems"
    keywords: [consensus, replication, sharding, CAP theorem]
  - name: "LLMs"
    keywords: [transformer, fine-tuning, RAG, inference, attention]

schedule:
  ingest: "0 */4 * * *"     # every 4 hours
  digest: "0 6 * * *"       # daily at 6am

learning:
  candidate_min_mentions: 2 # surface candidate concept in digest once seen >= N times
  resurface_after_days: 14  # resurface 'learning' notes when mentioned again

llm:
  providers:
    bedrock:
      region: us-west-2
    anthropic: {}           # uses ANTHROPIC_API_KEY
    openai: {}              # uses OPENAI_API_KEY
    gemini: {}              # uses GEMINI_API_KEY
    ollama:
      base_url: http://localhost:11434

  tasks:
    triage:    { provider: bedrock, model: us.anthropic.claude-haiku-4-5-20251001-v1:0 }
    summarize: { provider: bedrock, model: us.anthropic.claude-haiku-4-5-20251001-v1:0 }
    explain:   { provider: bedrock, model: us.anthropic.claude-opus-4-6-v1 }
    coach:     { provider: bedrock, model: us.anthropic.claude-opus-4-6-v1 }
```

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ (`uv`) | Strong ecosystem for feed parsing, extraction, LLM SDKs, and FastAPI |
| Feed parsing | `feedparser` | Battle-tested across RSS/Atom edge cases |
| Full-text extraction | `trafilatura` | High-quality article extraction with clean fallback when pages fail |
| Storage & search | SQLite (`sqlite3` + FTS5) | Zero-config, single-file, full-text search over entries and notes |
| LLM clients | Thin `LLMClient` over `anthropic[bedrock]`, `openai`, `google-genai`, `httpx` (Ollama) | Swappable per task, zero framework lock-in |
| Scheduler | `APScheduler` or system `cron` / `launchd` | Triggers idempotent ingest and daily digest jobs |
| Dashboard | FastAPI + HTMX | Server-rendered, low JS complexity, fast interactive triage/Q&A/note editing |
| Markdown rendering | `python-markdown` + `[[wikilink]]` resolver | Renders notes and explainers with live backlink navigation |

---

## Key Design Decisions

- **Hybrid execution (deterministic pipeline + bounded on-demand agent):** Scheduled ingest, triage, and daily digests run as deterministic Python pipelines with targeted `decide()` / structured LLM calls (cheap, fast, testable, and safe against prompt injection from untrusted RSS HTML). Only on-demand **Explainer** and **Note Coach** flows run a bounded read-only tool-calling loop (max ~5–6 turns) so you only pay for agentic exploration when actively learning a concept.
- **Tiered full-text extraction:** Classify and triage every entry on RSS title + summary first; fetch full article text only for high-relevance items or on-demand when generating an explainer, falling back cleanly to RSS content on paywalls, JS-only pages, or timeouts.
- **Concept deduplication:** Pass existing canonical note titles and aliases into concept extraction so the LLM reuses established names; surface ambiguous near-duplicates as a 1-click **`Merge A → B`** action in the dashboard rather than silently merging.
- **Delivery:** Pull-based web dashboard by default to encourage an intentional daily review habit without notification fatigue (digest Markdown files remain easy to pipe to email/Slack later if desired).
- **Idempotency:** Ingest deduplicates by GUID/URL; daily digests overwrite only that date's generated file (`digests/YYYY-MM-DD.md`), so re-running after a failure or config tweak is safe.

---

## Milestones

| # | Milestone | Delivers |
|---|---|---|
| 1 | **Ingest + Unified LLM Client** | Config loader, RSS fetch/parse/dedup to SQLite (`T-001`), and provider-agnostic `LLMClient` with `decide()`, `complete()`, `complete_json()`, and tool-calling support (`T-002`: Bedrock + Ollama first; OpenAI/Gemini/decision-model adapters via same interface). |
| 2 | **Triage + Daily Digest** | Topic classification, tiered full-text fetch, candidate concept tracking in SQLite, and idempotent daily Markdown digests. |
| 3 | **Dashboard v1 (Digest + Triage)** | FastAPI + HTMX UI to read daily digests and triage candidate concepts (`Explain` stub, `Already know`, `Ignore`). *Usable daily habit starts here.* |
| 4 | **Explainer, Scoped Q&A & My Notes** | Bounded tool-using Explainer & Coach agent grounded in existing notes, depth refinement + follow-up Q&A, `Check my note` feedback, and marker-safe `knowledge/<slug>.md` editing. |
| 5 | **Knowledge Graph & Spaced Resurface** | Live `[[wikilink]]` & backlink navigation, FTS5 search, 1-click duplicate merge, external-edit resync, and digest resurfacing of `learning` notes. |
