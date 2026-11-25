# T-003: Unified LLMClient (Bedrock + Ollama, `decide()`, `complete()`, `complete_json()`, `tools`)

Status: draft

## Goal

Implement Feedwise's thin, provider-agnostic `LLMClient` layer supporting `decide()`, `complete()`, `complete_json()`, and tool calling—with AWS Bedrock and Ollama adapters routed per task from `config.yaml`—completing Milestone 1.

## Behavior change

1. No LLM integration → `src/feedwise/llm/` defines a unified `LLMClient` protocol with typed models for text completion, strict Pydantic JSON output, System-1 typed decisions (`choice` / `boolean` / `score` + confidence), and single-turn tool calls.
2. No provider adapters → `BedrockClient` (`anthropic[bedrock]`, works with `us-west-2` Haiku 4.5 / Opus 4.6) and `OllamaClient` (`httpx` against `/api/chat` with explicit timeout) both implement `LLMClient`.
3. No task-based routing → `client_for_task(config, task_name)` resolves `config.llm.tasks[task_name]` to the configured provider + model, failing fast on unknown tasks or unconfigured providers.
4. No connectivity check → `feedwise llm-check [--config PATH] [--task NAME]` runs a minimal `complete()` + `decide()` smoke test against the configured backend.

## Out of scope

- OpenAI, direct Anthropic API, Google Gemini, and Jev adapters (cleanly pluggable behind the same `LLMClient` interface in a later task).
- Triage, concept-extraction, digest, explainer, or coaching prompts (Milestone 2 / Milestone 4).
- Multi-turn agent execution loop (Milestone 4 builds on `complete_with_tools()`).
- Changes to SQLite schema (`data/feeds.db`) or `ingest.py`.

## Data & contract impact

- Files / modules:
  - `pyproject.toml` (add `anthropic[bedrock]>=0.45`)
  - `src/feedwise/llm/{__init__.py,types.py,base.py,bedrock.py,ollama.py,router.py}`
  - `src/feedwise/cli.py` (add `llm-check` subcommand)
  - `tests/test_llm.py` (offline tests mocking Bedrock SDK and Ollama `httpx.MockTransport`)
- `config.yaml`, SQLite schema, or Markdown format changes: none (uses existing `llm.providers` and `llm.tasks` sections in `AppConfig`).
- Risk: routine (new module + dependency; no durable DB or Markdown note changes).
- Rollback path: revert commit and run `uv sync`.

## Success & acceptance criteria

Observable outcomes that must be true before marking `done`:
- [ ] `LLMClient` protocol exposes four typed operations:
  - `complete(prompt, *, system=None, max_tokens=1024) -> LLMResponse`
  - `complete_json(prompt, response_model: type[T], *, system=None, max_tokens=1024) -> T` — validates strictly against `response_model` and raises `LLMOutputError` on invalid JSON or schema mismatch (never silently falls back).
  - `decide(state, questions: list[DecisionQuestion], *, system=None) -> dict[str, DecisionResult]` — supports `choice` (must be one of the declared `options`), `boolean` (`bool`), and `score` (`0.0 <= float <= 1.0`), each returning a `confidence` (`0.0 <= float <= 1.0`). Raises `LLMOutputError` if the model returns an out-of-range value or unlisted choice.
  - `complete_with_tools(messages, tools: list[ToolDef], *, system=None, max_tokens=1024) -> LLMResponse` — returns text and/or typed `ToolCall(id, name, arguments)` items.
- [ ] `BedrockClient` and `OllamaClient` both implement all four methods, track token usage (`input_tokens`, `output_tokens` when available), enforce explicit HTTP/API timeouts, and wrap provider failures in `LLMError`.
- [ ] `client_for_task(config, task_name)` resolves configured tasks (`triage`, `summarize`, `explain`, `coach`) and raises a clear `ValueError` if the task is missing or its provider is unconfigured/unsupported.
- [ ] `feedwise llm-check --config config.yaml --task triage` prints provider, model, response preview, decision output, and token usage (exits non-zero cleanly on config/provider error).
- [ ] All unit tests run completely offline (mocking Bedrock SDK calls and Ollama HTTP transport; zero live API calls in `pytest`).

Verification checks:
- [ ] Unit tests (offline): `uv run pytest tests/ -x --tb=short -q`
- [ ] Prompt / quality check: N/A (domain prompts start in Milestone 2; `decide()` wrapper prompt is checked via live smoke test below)
- [ ] Manual check (inside `jarvinion-dev`):
  1. Run `uv run feedwise llm-check --config config.yaml --task triage` and verify Bedrock Haiku 4.5 in `us-west-2` succeeds for both `complete()` and `decide()`.

## Plan

1. Add `anthropic[bedrock]` dependency to `pyproject.toml` and run `uv sync`.
2. Create `src/feedwise/llm/types.py` and `base.py` defining `LLMError`, `LLMOutputError`, `LLMResponse`, `Usage`, `ToolDef`, `ToolCall`, `DecisionQuestion` (`choice`/`boolean`/`score`), `DecisionResult`, and the `LLMClient` protocol (plus shared `decide()` validation helper).
3. Implement `src/feedwise/llm/bedrock.py` using `anthropic.AnthropicBedrock` (native tool use + structured JSON / `decide()` validation).
4. Implement `src/feedwise/llm/ollama.py` using `httpx.Client` against Ollama's `/api/chat` endpoint (JSON format / tool calling / explicit timeout).
5. Implement `src/feedwise/llm/router.py` (`client_for_task`) and wire `feedwise llm-check` in `src/feedwise/cli.py`.
6. Write comprehensive offline tests in `tests/test_llm.py` covering both adapters, invalid JSON / out-of-enum choice rejection, tool-call parsing, router errors, and `llm-check` CLI.
7. Run `uv run pytest tests/ -x --tb=short -q` and the manual `llm-check` smoke test against Bedrock Haiku 4.5 inside `jarvinion-dev`.

## Open questions (resolve before `approved`)

- Should `T-003` focus strictly on `LLMClient` (Bedrock + Ollama) as drafted above, and keep `feedwise feeds` / `feedwise entries` view commands as a separate small `T-004`? *(Recommended: yes — keeps each task one clean logical change.)*

## Trial record

Pre-filled by the agent at handoff; finalized when accepted (write `unknown` rather than guessing).
- Agent / model & reviewer:
- Active time / rough cost:
- Repair rounds before acceptance:
- Review findings that changed code:
- Follow-ups (new `T-NNN` or `AGENTS.md` rule):
- Defects found after acceptance:
