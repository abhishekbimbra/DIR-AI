# Plan changes

Every deviation from the development plans is recorded here with a reason.

## CP0

- **Pins live in `pyproject.toml`, pytest config in `pytest.ini`.**
  The plan names `pyproject.toml` for pins and `pytest.ini` for pytest options;
  tool configuration (ruff, mypy) is kept in `pyproject.toml` to avoid a second
  config file.
- **`scripts/gate.py n` tags only with `--tag`.**
  The plan says the gate script tags. Requiring an explicit flag avoids tagging
  a dirty or partially reviewed tree by accident.
- **`langchain-classic` is pinned during the transition.**
  The legacy ReAct CLI imports it. It is removed when CP6 replaces the loop.
- **The literal `dir_ai/{ui,controller,agent,middleware,tools}` directory was
  deleted.** It was empty and untracked.

## CP1

- **Windows drive and UNC paths are rejected on every platform.**
  The plan asks for Windows path tests skipped off Windows. Rejecting them
  everywhere is stricter and keeps a Linux checkout from ever treating
  `C:\...` or `\\server\...` as a relative filename.
- **Paths over 4096 characters or with a component over 255 bytes are
  rejected up front.** This turns a later `OSError` into a clear sandbox error
  and avoids leaking platform-specific failure details.

## CP3

- **The synchronous LangChain tool registry stays as a transitional adapter,
  but every call now routes through `ToolExecutor`.** The CP6 loop calls the
  executor directly; CP6 removes `get_tools()` from the agent path entirely.
- **`ApprovalKind` includes `read` in addition to write/edit/command.** The
  policy needs a kind to prompt for under `ask-all`; reads are free under
  `auto-read` and `read-only`.
- **CLI deny-with-note syntax is `n: reason`.** This keeps the interactive
  prompt single-line while still carrying feedback to the agent.
