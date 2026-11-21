# Plans — agy-code-harness

## Phase 1: Initial Antigravity Harness Port (Done)

- **Scope**: Port `claude-code-harness` to Antigravity customization conventions (`.agents/agents`, `.agents/skills`, `.agents/hooks`, `.agents/hooks.json`, `scripts/install.py`).
- **Acceptance criteria**:
  - `python3 -m unittest discover -s tests -v` passes.
  - `bash .agents/hooks/tests/run-tests.sh` passes.
  - `scripts/install.py` installs idempotently into `~/.gemini/config` without clobbering existing `hooks.json` entries.

## Phase 2: Add `pr-walkthrough` Skill & Multi-File Skill Installer Support

- **Scope**:
  - **Skill & Progressive Disclosure**:
    - Add `.agents/skills/pr-walkthrough/SKILL.md` (concise, `<= 60` lines) with `name: pr-walkthrough` and `description` containing explicit `Use ...; do not ...` trigger boundaries (human reviewer mental-model walkthrough of a GitHub PR or local branch diff; do not edit files, replace `review` verdicts, approve/merge PRs, or post PR comments unless explicitly requested).
    - Default output to a read-only Antigravity Markdown Artifact; allow `gh pr comment` **only** on explicit user request (using repo-relative/PR links rather than local `file://` paths).
    - Add `.agents/skills/pr-walkthrough/references/walkthrough-template.md` containing the full template:
      1. **TL;DR & Risk/Effort Header**: 3-line summary (`Problem` / `Solution` / `Impact`), Review Effort (`1-5`), Merge Risk (`Low` / `Medium` / `High` / `Critical`), and Scope stats.
      2. **Visual Flow / Architecture Diagram (Mermaid)**: `sequenceDiagram` or `flowchart LR` from entry point → modified functions → DB/API/state boundaries, highlighting changed elements and enforcing quoted node labels without raw HTML tags.
      3. **Guided Tour**: Ordered `Data Contracts/Interfaces → Core Logic → Integration/API/UI → Tests`, with per-function `Before → After` summaries and clickable `file:line` links.
      4. **Review Hotspots (Risk-Tagged)**: `🔴` Critical/High-Risk (logic, security, concurrency, state transitions), `🟡` Design Trade-offs/Assumptions, and `🟢` Skippable Boilerplate/Mechanical/Generated (grouped or collapsed in `<details>`).
      5. **Verification & Uncovered Gaps**: Observed/executed checks vs unverified or uncovered blind spots.
  - **Installer (`scripts/install.py`)**:
    - Add `"pr-walkthrough"` to `SKILLS`.
    - Update `exact_skill_dir_match(path, source)` to perform recursive, non-symlink tree and SHA-256 `digest` comparison so multi-file skill directories (including subdirectories like `references/`) match exact copies and refuse modified, missing, extra, or symlinked entries as unmanaged collisions before any mutation.
  - **Tests (`tests/test_contracts.py`, `tests/test_install.py`)**:
    - Update `SKILLS` in `tests/test_contracts.py`; assert `pr-walkthrough/references/walkthrough-template.md` exists, is referenced by `SKILL.md` (`<= 60` lines), scan `.agents/skills/*/references/*.md` for retired-runtime exclusions, and keep `"pr-walkthrough"` aligned with doc checks.
    - Update `links_updated` assertions from `14` to `15` in `tests/test_install.py`, verify symlinked `references/walkthrough-template.md` resolution, and add tests for exact multi-file skill cleanup plus collision refusals (modified nested file, missing nested file, extra file, symlinked subdirectory).
  - **Docs**:
    - Update `README.md` (staying `<= 110` lines), `README.en.md`, `HARNESS.md` (staying `<= 150` lines), and `CHANGELOG.md` to reflect 7 skills and the `pr-walkthrough` role/output boundary.
- **Non-goals**:
  - Adding new subagents to `AGENTS` or changing `review` / `orchestrator` / `release` contracts or hooks.
  - Automatic GitHub PR polling, auto-commenting, approving, or merging.
  - Partial/fuzzy merging of modified files inside installed skill directories in `scripts/install.py`.
- **Acceptance criteria**:
  - `.agents/skills/pr-walkthrough/SKILL.md` (`<= 60` lines, frontmatter has `"Use"` and `"do not"`) and `.agents/skills/pr-walkthrough/references/walkthrough-template.md` exist and cover all required sections and output-mode guards.
  - `scripts/install.py` includes `"pr-walkthrough"` in `SKILLS` and `exact_skill_dir_match` passes both positive multi-file match and negative collision tests.
  - `README.md` (`<= 110` lines), `README.en.md`, `HARNESS.md` (`<= 150` lines), and `CHANGELOG.md` document the 7 skills and `pr-walkthrough`.
  - `python3 -m unittest discover -s tests -v` passes with all contract and install tests green.
  - `bash .agents/hooks/tests/run-tests.sh` passes with 0 failures.
  - `python3 scripts/install.py --dry-run` exits 0 without errors.
