#!/usr/bin/env python3
"""Install one global Antigravity (AGY) harness while preserving unmanaged user assets."""

import argparse
import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Optional, Tuple


AGENTS = ("explorer", "planner", "coder", "tester", "reviewer", "documenter")
SKILLS = ("plan", "work", "review", "release", "setup", "orchestrator", "pr-walkthrough")
SAFETY_HOOKS = ("block-destructive", "protect-secrets")
HOOK_GROUP_NAME = "agy-harness-safety"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(path: Path) -> None:
    for parent in (path.parent,) + tuple(path.parents):
        if parent.is_symlink() and parent not in (
            Path("/var"),
            Path("/tmp"),
            Path("/etc"),
        ):
            raise ValueError("refusing symlinked installation directory: {}".format(parent))
        if parent.exists() and not parent.is_dir():
            raise ValueError("installation parent is not a directory: {}".format(parent))


def exact_file_match(path: Path, source: Path) -> bool:
    return path.is_file() and not path.is_symlink() and digest(path) == digest(source)


def exact_skill_dir_match(path: Path, source: Path) -> bool:
    if not path.is_dir() or path.is_symlink() or not source.is_dir() or source.is_symlink():
        return False

    def collect_tree(root: Path) -> Optional[Dict[Path, Path]]:
        entries: Dict[Path, Path] = {}
        stack = [root]
        while stack:
            current = stack.pop()
            for child in current.iterdir():
                if child.is_symlink():
                    return None
                rel = child.relative_to(root)
                if child.is_dir():
                    entries[rel] = child
                    stack.append(child)
                elif child.is_file():
                    entries[rel] = child
                else:
                    return None
        return entries

    path_entries = collect_tree(path)
    source_entries = collect_tree(source)
    if path_entries is None or source_entries is None:
        return False
    if set(path_entries) != set(source_entries):
        return False
    for rel, source_entry in source_entries.items():
        path_entry = path_entries[rel]
        if source_entry.is_dir():
            if not path_entry.is_dir():
                return False
        elif not exact_file_match(path_entry, source_entry):
            return False
    return True


def managed_destination(destination: Path, source: Path, kind: str) -> bool:
    if destination.is_symlink():
        return destination.resolve(strict=False) == source.resolve(strict=False)
    if kind == "skill":
        return exact_skill_dir_match(destination, source)
    return exact_file_match(destination, source)


def harness_hook_spec(root: Path) -> dict:
    raw = json.loads((root / ".agents/hooks.json").read_text())
    if not isinstance(raw, dict) or HOOK_GROUP_NAME not in raw:
        raise ValueError("missing {} entry in .agents/hooks.json".format(HOOK_GROUP_NAME))
    return raw[HOOK_GROUP_NAME]


def rendered_hooks_config(
    existing: dict,
    safety_spec: Optional[dict],
) -> str:
    if not isinstance(existing, dict):
        raise ValueError("hooks.json must be a JSON object")
    result = copy.deepcopy(existing)
    if safety_spec is not None:
        result[HOOK_GROUP_NAME] = copy.deepcopy(safety_spec)
    else:
        result.pop(HOOK_GROUP_NAME, None)
    return json.dumps(result, indent=2, ensure_ascii=False) + "\n"


def atomic_write(path: Path, content: str) -> bool:
    if path.exists() and path.read_text() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".harness-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def content_would_change(path: Path, content: str) -> bool:
    return not path.exists() or path.read_text() != content


def install(
    root: Path,
    global_root: Path,
    workspace: Optional[Path] = None,
    dry_run: bool = False,
) -> dict:
    root = root.resolve(strict=True)
    global_root = global_root.absolute()
    workspace = workspace.resolve(strict=True) if workspace is not None else None
    safety_spec = harness_hook_spec(root)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    global_backup = global_root / "harness-backups" / stamp
    workspace_backup = (
        workspace / ".agents/harness-backups" / stamp if workspace else None
    )

    link_actions: List[Tuple[Path, Path, Optional[Path]]] = []
    remove_actions: List[Tuple[Path, Path]] = []
    backups: List[str] = []

    targets = []
    for name in AGENTS:
        targets.append(
            (
                root / ".agents/agents" / "{}.md".format(name),
                global_root / "agents" / "{}.md".format(name),
                "file",
            )
        )
    for name in SKILLS:
        targets.append(
            (
                root / ".agents/skills" / name,
                global_root / "skills" / name,
                "skill",
            )
        )
    for name in SAFETY_HOOKS:
        targets.append(
            (
                root / ".agents/hooks" / "{}.sh".format(name),
                global_root / "hooks" / "{}.sh".format(name),
                "file",
            )
        )

    for source, destination, kind in targets:
        if not source.exists():
            raise ValueError("missing source asset: {}".format(source))
        validate_parent(destination)
        if destination.is_symlink() and destination.resolve(strict=False) == source:
            continue
        backup = None
        if destination.exists() or destination.is_symlink():
            if not managed_destination(destination, source, kind):
                raise ValueError("unmanaged collision (not overwritten): {}".format(destination))
            backup = global_backup / destination.relative_to(global_root)
        link_actions.append((source, destination, backup))

    workspace_hooks_json = None
    workspace_hooks_rendered = None
    if workspace is not None and workspace != root:
        workspace_agents = workspace / ".agents"
        cleanup = []
        for name in AGENTS:
            cleanup.append(
                (
                    workspace_agents / "agents" / "{}.md".format(name),
                    root / ".agents/agents" / "{}.md".format(name),
                    "file",
                )
            )
        for name in SKILLS:
            cleanup.append(
                (
                    workspace_agents / "skills" / name,
                    root / ".agents/skills" / name,
                    "skill",
                )
            )
        for name in SAFETY_HOOKS:
            cleanup.append(
                (
                    workspace_agents / "hooks" / "{}.sh".format(name),
                    root / ".agents/hooks" / "{}.sh".format(name),
                    "file",
                )
            )

        for destination, source, kind in cleanup:
            validate_parent(destination)
            if not (destination.exists() or destination.is_symlink()):
                continue
            if managed_destination(destination, source, kind) and (
                destination.resolve(strict=False) != source.resolve(strict=False)
            ):
                remove_actions.append(
                    (
                        destination,
                        workspace_backup / destination.relative_to(workspace_agents),
                    )
                )

        workspace_hooks_json = workspace_agents / "hooks.json"
        validate_parent(workspace_hooks_json)
        if workspace_hooks_json.exists():
            if workspace_hooks_json.is_symlink():
                raise ValueError("refusing symlinked hooks.json file: {}".format(workspace_hooks_json))
            existing_ws = json.loads(workspace_hooks_json.read_text())
            if HOOK_GROUP_NAME in existing_ws:
                workspace_hooks_rendered = rendered_hooks_config(existing_ws, None)

    global_hooks_json = global_root / "hooks.json"
    validate_parent(global_hooks_json)
    if global_hooks_json.is_symlink():
        raise ValueError("refusing symlinked hooks.json file: {}".format(global_hooks_json))
    existing_global = (
        json.loads(global_hooks_json.read_text()) if global_hooks_json.exists() else {}
    )
    global_hooks_rendered = rendered_hooks_config(existing_global, safety_spec)

    hooks_config_updated = int(content_would_change(global_hooks_json, global_hooks_rendered))
    if workspace_hooks_json is not None and workspace_hooks_rendered is not None:
        hooks_config_updated += int(
            content_would_change(workspace_hooks_json, workspace_hooks_rendered)
        )

    planned_backups = [
        str(backup)
        for _, _, backup in link_actions
        if backup is not None
    ] + [str(backup) for _, backup in remove_actions]

    if not dry_run:
        for source, destination, backup in link_actions:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if backup is not None:
                backup.parent.mkdir(parents=True, exist_ok=True)
                destination.rename(backup)
                backups.append(str(backup))
            destination.symlink_to(source, target_is_directory=source.is_dir())

        for destination, backup in remove_actions:
            backup.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(backup)
            backups.append(str(backup))

        atomic_write(global_hooks_json, global_hooks_rendered)
        if workspace_hooks_json is not None and workspace_hooks_rendered is not None:
            atomic_write(workspace_hooks_json, workspace_hooks_rendered)

    return {
        "dry_run": dry_run,
        "links_updated": len(link_actions),
        "managed_duplicates_removed": len(remove_actions),
        "hooks_config_updated": hooks_config_updated,
        "backups": backups,
        "planned_backups": planned_backups,
        "note": "Start a new Antigravity session (agy / App / IDE) to load updated agents, skills, and hooks.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--global-root",
        type=Path,
        default=Path.home() / ".gemini/config",
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = install(
            Path(__file__).resolve().parents[1],
            args.global_root,
            args.workspace,
            args.dry_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("Install failed: {}".format(error), file=os.sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
