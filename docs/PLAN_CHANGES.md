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
