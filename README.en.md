# Antigravity (AGY) Code Harness

A lightweight personal harness for Google Antigravity (`agy` CLI, Antigravity App, and IDE) that adds a consistent Plan → Work → Review → Release workflow without overriding Antigravity's defaults.

## Components

- 6 custom subagents (`.agents/agents/`): `explorer`, `planner`, `coder`, `tester`, `reviewer`, `documenter`
- 6 skills (`.agents/skills/`): `plan`, `work`, `review`, `release`, `setup`, `orchestrator`
- 2 safety hooks (`.agents/hooks/` + `.agents/hooks.json`): destructive shell command guard and secret-file write guard
- Installer (`scripts/install.py`): symlinks canonical assets into `~/.gemini/config` and safely merges only the `agy-harness-safety` block into `hooks.json`

No lifecycle hook loops, disk retry counters, external `agy -p` phase runners, agent announcement hooks, or post-edit auto-lint hooks. Bounded retries are coordinated in-conversation by `orchestrator` using `send_message`.

## Recommended Flow

Small changes stay in the main conversation. For substantive or risky work:

```text
plan → work → review → release
```

- `plan`: Writes scope, non-goals, and measurable acceptance criteria to `Plans.md`.
- `work`: Implements one approved phase with a focused diff (`tester` is optional).
- `review`: Runs one independent read-only pass across four lenses (spec, security, correctness/maintainability, performance/operability).
- `release`: Prepares docs, commit, push, or PR only on explicit user request.
- `orchestrator`: Coordinates end-to-end work and at most 3 review attempts including the first.

## Subagent Routing

| Role | Model (`model`) | Execution Policy (`commandExecutionPolicy`) | Purpose |
|---|---|---|---|
| planner | `pro` | `off` | Scope, risks, and acceptance criteria |
| reviewer | `pro` | `sandbox` | Independent 4-lens review |
| coder | `inherit` | `sandbox` | Implement one approved phase |
| tester | `inherit` | `sandbox` | Optional independent verification |
| explorer | `flash` | `sandbox` | Read-only codebase discovery |
| documenter | `flash` | `off` | Verified documentation sync |

## Install

```bash
git clone https://github.com/jangheejeong/agy-code-harness.git
cd agy-code-harness
python3 scripts/install.py --dry-run
python3 scripts/install.py
```

## Verify

```bash
python3 -m unittest discover -s tests -v
bash .agents/hooks/tests/run-tests.sh
```
