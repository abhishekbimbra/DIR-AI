# DIR-AI

A local, sandboxed directory-intelligence coding agent. Python backend first,
Electron desktop frontend second.

The backend is developed against two checkpoint plans:

- Backend plan: CP0 → CP9, then live validation.
- Electron plan: FE0 → FE5, starting only after the backend publishes `cp9-done`.

Both plans live in `plans/` on the development machine (ignored by git). The
committed source of truth for the protocol is `docs/PROTOCOL.md` plus
`docs/schema/`.

## Quick start (WSL/Linux)

```bash
uv sync --all-groups
cp .env.example .env          # add a provider key, or use a local provider
uv run dir-ai --help
uv run dir-ai                 # interactive CLI
```

Local providers need no key:

```bash
DIRAI_PROVIDER=ollama uv run dir-ai
DIRAI_PROVIDER=lmstudio uv run dir-ai
```

## Development

```bash
uv run pytest                 # unit + integration + contract (network blocked)
uv run ruff check .
uv run ruff format --check .
uv run mypy dir_ai
python scripts/gate.py 0      # checkpoint gate (add --tag to tag the gate)
```

Live provider tests are excluded by default and marked `live`:

```bash
uv run pytest -m live
```

## Layout

```
dir_ai/
  config.py        validated settings, env loading
  main.py          CLI entry point
  sandbox.py       path/secret policy (CP1)
  tools/           typed tools behind the sandbox (CP2)
  approval.py      approval protocol and handlers (CP3)
  policy.py        ask-all / auto-read / read-only (CP3)
  events.py        typed, versioned event stream (CP4)
  providers.py     provider factory, errors, retries (CP5)
  agent/           native tool-calling loop (CP6)
  context.py       repo map and project rules (CP8)
  server/          localhost WebSocket protocol (CP9)
tests/
  unit/ integration/ contract/ e2e_fake/ live/ fixtures/
```

## Security invariants

- All file access goes through `dir_ai/sandbox.py`.
- Writes and commands require approval according to the active policy.
- Secrets are never logged, never emitted in events, and never returned to a UI.
- The server binds to `127.0.0.1` and requires a per-launch auth token.

## Status

See `docs/EXECUTION_PROGRESS.md` for the current checkpoint and gate results.
