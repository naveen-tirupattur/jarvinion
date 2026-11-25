# T-NNN: <short name>

Status: draft | approved | in progress | in review | done | parked

One task per logical change, short enough to read in one sitting.
- Copy to `tasks/T-NNN-<slug>.md` (next unused number across `tasks/` and `tasks/done/`).
- Agree before writing code; move to `tasks/done/` once merged.
- New ideas or follow-ups get their own task rather than expanding scope here.

## Goal

One or two sentences: what you can do afterwards that you cannot do now.

## Behavior change

One line per change (`current → intended`):
1.

## Out of scope

Explicitly list adjacent work we are NOT doing in this task.

-

## Data & contract impact

- Files / modules:
- `config.yaml`, SQLite schema, or Markdown format changes: none | <details>
- Risk: routine | touches durable data (SQLite / Markdown notes / LLM prompts)
- Rollback path: none | <how to revert safely>

## Success & acceptance criteria

Observable outcomes that must be true before marking `done`:
- [ ] <concrete, verifiable outcome 1>
- [ ] <concrete, verifiable outcome 2>

Verification checks:
- [ ] Unit tests (offline / mocked LLMs): `uv run pytest <files> -x --tb=short -q`
- [ ] Prompt / quality check: <sample fixture + pass bar | N/A>
- [ ] Manual check: <CLI or dashboard check>

## Plan

Ordered implementation steps for the agent:
1.

## Open questions (resolve before `approved`)

-

## Trial record

Pre-filled by the agent at handoff; finalized when accepted (write `unknown` rather than guessing).
- Agent / model & reviewer:
- Active time / rough cost:
- Repair rounds before acceptance:
- Review findings that changed code:
- Follow-ups (new `T-NNN` or `AGENTS.md` rule):
- Defects found after acceptance:
