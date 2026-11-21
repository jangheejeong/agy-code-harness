import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = {
    "planner": ("pro", "off"),
    "reviewer": ("pro", "sandbox"),
    "coder": ("inherit", "sandbox"),
    "tester": ("inherit", "sandbox"),
    "explorer": ("flash", "sandbox"),
    "documenter": ("flash", "off"),
}
SKILLS = ("plan", "work", "review", "release", "setup", "orchestrator")


def frontmatter(path):
    source = path.read_text()
    header = source.split("---", 2)[1]
    return {
        key: value.strip().strip('"')
        for key, value in re.findall(r"^([A-Za-z0-9_-]+):\s*(.+)$", header, re.M)
    }


class ContractTests(unittest.TestCase):
    def test_agent_model_and_policy_routing(self):
        for name, expected in AGENTS.items():
            with self.subTest(agent=name):
                metadata = frontmatter(ROOT / ".agents/agents" / "{}.md".format(name))
                self.assertEqual(
                    (metadata["model"], metadata["commandExecutionPolicy"]),
                    expected,
                )
                self.assertEqual(metadata["subagent"], "true")
                self.assertEqual(metadata["mainAgent"], "false")
                self.assertNotIn("tools", metadata)

    def test_skills_have_clear_trigger_boundaries(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                metadata = frontmatter(ROOT / ".agents/skills" / name / "SKILL.md")
                description = metadata["description"]
                self.assertIn("Use", description)
                self.assertIn("do not", description)
        release = frontmatter(ROOT / ".agents/skills/release/SKILL.md")
        self.assertIn("explicit user invocation", release["description"])

    def test_review_has_four_lenses_and_one_retry_owner(self):
        reviewer = (ROOT / ".agents/agents/reviewer.md").read_text()
        for lens in (
            "Spec correctness",
            "Security",
            "Correctness and maintainability",
            "Performance and operability",
        ):
            self.assertIn(lens, reviewer)
        review = (ROOT / ".agents/skills/review/SKILL.md").read_text()
        orchestrator = (ROOT / ".agents/skills/orchestrator/SKILL.md").read_text()
        self.assertIn("one read-only pass", review)
        self.assertIn("Only `orchestrator`", review)
        self.assertIn("at most three total attempts", orchestrator)

    def test_only_two_safety_hooks_remain(self):
        hooks = json.loads((ROOT / ".agents/hooks.json").read_text())
        self.assertEqual(set(hooks), {"agy-harness-safety"})
        safety = hooks["agy-harness-safety"]
        self.assertEqual(set(safety), {"PreToolUse"})
        commands = [
            handler["command"]
            for entry in safety["PreToolUse"]
            for handler in entry["hooks"]
        ]
        self.assertEqual(
            commands,
            [
                "./hooks/block-destructive.sh",
                "./hooks/protect-secrets.sh",
            ],
        )

    def test_active_instructions_do_not_reference_claude_or_retired_runtime(self):
        active = [ROOT / ".agents/hooks.json"]
        active.extend(ROOT.glob(".agents/agents/*.md"))
        active.extend(ROOT.glob(".agents/skills/*/SKILL.md"))
        source = "\n".join(path.read_text() for path in active)
        for forbidden in (
            "CLAUDE_PROJECT_DIR",
            "claude -p",
            "record-verdict",
            "enforce-loop",
            "loop-state",
            "HARNESS_RUN_PHASE",
            "run_phase.py",
        ):
            self.assertNotIn(forbidden, source)

    def test_user_docs_are_lean_and_match_the_active_contract(self):
        docs = [ROOT / "README.md", ROOT / "README.en.md", ROOT / "HARNESS.md"]
        source = "\n".join(path.read_text() for path in docs)
        for expected in ("pro", "inherit", "flash", "네 관점", "3", "~/.gemini/config"):
            self.assertIn(expected, source)
        self.assertLessEqual(len((ROOT / "README.md").read_text().splitlines()), 110)
        self.assertLessEqual(len((ROOT / "HARNESS.md").read_text().splitlines()), 150)


if __name__ == "__main__":
    unittest.main()
