import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def installer():
    spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.global_root = Path(self.temporary.name) / "home with spaces" / ".gemini" / "config"
        self.workspace = Path(self.temporary.name) / "workspace"
        self.workspace.mkdir(parents=True)

    def install(self, workspace=True, dry_run=False):
        return installer().install(
            ROOT,
            self.global_root,
            self.workspace if workspace else None,
            dry_run=dry_run,
        )

    def test_global_install_is_idempotent_and_preserves_existing_hooks(self):
        self.global_root.mkdir(parents=True)
        existing_hooks = {
            "orca-status": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "custom-orca-hook"}],
                    }
                ]
            }
        }
        hooks_path = self.global_root / "hooks.json"
        hooks_path.write_text(json.dumps(existing_hooks))

        first = self.install(workspace=False)
        first_bytes = hooks_path.read_bytes()
        second = self.install(workspace=False)

        self.assertEqual(first["links_updated"], 15)
        self.assertEqual(first["hooks_config_updated"], 1)
        self.assertEqual(second["links_updated"], 0)
        self.assertEqual(second["hooks_config_updated"], 0)
        self.assertEqual(first_bytes, hooks_path.read_bytes())

        installed = json.loads(hooks_path.read_text())
        self.assertEqual(installed["orca-status"], existing_hooks["orca-status"])
        self.assertIn("agy-harness-safety", installed)
        self.assertEqual(
            (self.global_root / "agents/reviewer.md").resolve(),
            ROOT / ".agents/agents/reviewer.md",
        )
        self.assertEqual(
            (self.global_root / "skills/review").resolve(),
            ROOT / ".agents/skills/review",
        )
        self.assertEqual(
            (self.global_root / "skills/pr-walkthrough/references/walkthrough-template.md").resolve(),
            ROOT / ".agents/skills/pr-walkthrough/references/walkthrough-template.md",
        )
        self.assertEqual(
            (self.global_root / "hooks/block-destructive.sh").resolve(),
            ROOT / ".agents/hooks/block-destructive.sh",
        )

    def test_exact_workspace_duplicates_are_backed_up_and_workspace_hook_removed(self):
        workspace_agents = self.workspace / ".agents"
        agent = workspace_agents / "agents/coder.md"
        skill = workspace_agents / "skills/review"
        hook = workspace_agents / "hooks/block-destructive.sh"
        ws_hooks_json = workspace_agents / "hooks.json"
        agent.parent.mkdir(parents=True)
        skill.mkdir(parents=True)
        hook.parent.mkdir(parents=True)
        shutil.copy2(ROOT / ".agents/agents/coder.md", agent)
        shutil.copy2(ROOT / ".agents/skills/review/SKILL.md", skill / "SKILL.md")
        shutil.copy2(ROOT / ".agents/hooks/block-destructive.sh", hook)
        ws_hooks_json.write_text(
            json.dumps(
                {
                    "agy-harness-safety": {"PreToolUse": []},
                    "project-lint": {"PostToolUse": []},
                }
            )
        )

        result = self.install()

        self.assertFalse(agent.exists())
        self.assertFalse(skill.exists())
        self.assertFalse(hook.exists())
        self.assertEqual(result["managed_duplicates_removed"], 3)
        self.assertEqual(len(result["backups"]), 3)
        self.assertTrue(all(Path(path).exists() for path in result["backups"]))
        ws_hooks = json.loads(ws_hooks_json.read_text())
        self.assertNotIn("agy-harness-safety", ws_hooks)
        self.assertIn("project-lint", ws_hooks)

    def test_unknown_collision_is_refused_before_any_mutation(self):
        collision = self.global_root / "skills/review"
        collision.mkdir(parents=True)
        (collision / "SKILL.md").write_text("my custom review workflow")

        with self.assertRaises(ValueError):
            self.install(workspace=False)

        self.assertEqual(
            (collision / "SKILL.md").read_text(),
            "my custom review workflow",
        )
        self.assertFalse((self.global_root / "agents/planner.md").exists())

    def test_symlinked_workspace_agents_is_refused_before_mutation(self):
        self.global_root.mkdir(parents=True)
        sentinel = self.global_root / "sentinel.txt"
        sentinel.write_text("keep")
        (self.workspace / ".agents").symlink_to(
            self.global_root,
            target_is_directory=True,
        )

        with self.assertRaises(ValueError):
            self.install()

        self.assertEqual(sentinel.read_text(), "keep")
        self.assertFalse((self.global_root / "agents/planner.md").exists())

    def test_dry_run_reports_without_mutating(self):
        self.global_root.mkdir(parents=True)
        hooks_path = self.global_root / "hooks.json"
        original = '{"custom": {}}\n'
        hooks_path.write_text(original)

        result = self.install(workspace=True, dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["links_updated"], 15)
        self.assertEqual(result["hooks_config_updated"], 1)
        self.assertEqual(result["backups"], [])
        self.assertEqual(hooks_path.read_text(), original)
        self.assertFalse((self.global_root / "agents/planner.md").exists())

    def test_exact_multifile_skill_copy_is_backed_up_and_cleaned(self):
        source = ROOT / ".agents/skills/pr-walkthrough"
        global_copy = self.global_root / "skills/pr-walkthrough"
        workspace_copy = self.workspace / ".agents/skills/pr-walkthrough"
        shutil.copytree(source, global_copy)
        shutil.copytree(source, workspace_copy)

        result = self.install(workspace=True)

        self.assertTrue(global_copy.is_symlink())
        self.assertEqual(
            (global_copy / "references/walkthrough-template.md").resolve(),
            source / "references/walkthrough-template.md",
        )
        self.assertFalse(workspace_copy.exists())
        self.assertEqual(result["managed_duplicates_removed"], 1)
        self.assertEqual(len(result["backups"]), 2)
        self.assertTrue(all(Path(path).exists() for path in result["backups"]))

    def test_multifile_skill_collisions_are_refused_before_any_mutation(self):
        source = ROOT / ".agents/skills/pr-walkthrough"
        cases = ("modified_nested", "missing_nested", "extra_file", "symlinked_subdir")
        for case in cases:
            with self.subTest(case=case):
                case_global = Path(self.temporary.name) / "case-{}".format(case) / ".gemini" / "config"
                collision = case_global / "skills/pr-walkthrough"
                shutil.copytree(source, collision)

                if case == "modified_nested":
                    (collision / "references/walkthrough-template.md").write_text("custom template")
                elif case == "missing_nested":
                    (collision / "references/walkthrough-template.md").unlink()
                elif case == "extra_file":
                    (collision / "references/extra.md").write_text("extra")
                elif case == "symlinked_subdir":
                    shutil.rmtree(collision / "references")
                    (collision / "references").symlink_to(
                        source / "references",
                        target_is_directory=True,
                    )

                with self.assertRaises(ValueError):
                    installer().install(ROOT, case_global, workspace=None, dry_run=False)

                self.assertFalse(collision.is_symlink())
                self.assertFalse((case_global / "agents/planner.md").exists())


if __name__ == "__main__":
    unittest.main()
