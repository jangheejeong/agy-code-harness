---
name: pr-walkthrough
description: Build a read-only, human-friendly walkthrough of a GitHub pull request or local branch diff to accelerate code review. Use for PR onboarding, diff explanations, or reviewer guides; do not edit code, replace `review` verdicts, approve/merge PRs, or post PR comments unless explicitly requested.
---

# PR Walkthrough

Produce a low-cognitive-load mental model for a human reviewer without modifying repository files.

1. Gather complete change context:
   - For a GitHub PR: inspect metadata and diff via `gh pr view` and `gh pr diff`.
   - For a local branch: resolve the base branch and inspect `git diff <base>...HEAD` plus any in-scope untracked files.
   - Read surrounding functions, types, and callers—never rely on diff hunks alone.
2. For large multi-module PRs, optionally delegate read-only mapping of untouched callers or module boundaries to `explorer`.
3. Structure the walkthrough using `./references/walkthrough-template.md`:
   - TL;DR (`Problem` / `Solution` / `Impact`), Review Effort (`1–5`), Merge Risk (`Low`/`Medium`/`High`/`Critical`), and Scope stats.
   - Mermaid flow or architecture diagram with quoted node labels, no raw HTML tags, and highlighted changed elements.
   - Guided Tour ordered `Data Contracts/Interfaces → Core Logic → Integration/API/UI → Tests` with per-function `Before → After` summaries and `file:line` links.
   - Risk-tagged Review Hotspots (`🔴`, `🟡`, `🟢` with boilerplate collapsed in `<details>`).
   - Verification results vs. uncovered gaps and manual checks.
4. Default output: write a user-facing Antigravity Markdown Artifact (read-only). Do not edit repository files, approve, or merge PRs.
5. Optional PR comment: run `gh pr comment` **only** when the user explicitly requests posting to GitHub. Before posting, replace every local `file://` URI with a repo-relative path or GitHub PR link.
