# Environment setup

## WSL / Linux (backend)

1. Python 3.11+ (this repo uses 3.13) and `uv`.
2. Keep the repo on the Linux filesystem, e.g. `~/projects/DIR-AI`, not `/mnt/c`.
3. Install:

   ```bash
   uv sync --all-groups
   cp .env.example .env
   ```

4. Provider keys (`GOOGLE_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`) are only
   needed for live runs. Ollama and LM Studio need no key.
5. Run the gate:

   ```bash
   python scripts/gate.py 0
   ```

### Local model servers from WSL

- Ollama: `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- LM Studio: start the local server, then
  `LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1`
- If LM Studio runs on Windows and the backend in WSL, add to
  `%UserProfile%\.wslconfig`:

  ```ini
  [wsl2]
  networkingMode=mirrored
  ```

  then run `wsl --shutdown` and restart.

## Windows (Electron frontend, after `cp9-done`)

1. Clone the repository with Git (do not copy folders).
2. Node.js 20 LTS or newer with npm or pnpm.
3. Python is needed only for the FE5 packaging checkpoint; the backend ships as
   a bundled executable.
4. The Electron app connects to `ws://127.0.0.1:<port>`; the backend binds only
   to loopback.
5. Verify line endings: `.gitattributes` enforces LF for source files.

## Fake backend

Every regression run uses scripted conversations. The server accepts
`--fake-llm` and never touches a provider or the network in that mode.
