# Plans — agy-code-harness

## Phase 1: Initial Antigravity Harness Port (Done)

- **Scope**: Port `claude-code-harness` to Antigravity customization conventions (`.agents/agents`, `.agents/skills`, `.agents/hooks`, `.agents/hooks.json`, `scripts/install.py`).
- **Acceptance criteria**:
  - `python3 -m unittest discover -s tests -v` passes.
  - `bash .agents/hooks/tests/run-tests.sh` passes.
  - `scripts/install.py` installs idempotently into `~/.gemini/config` without clobbering existing `hooks.json` entries.
