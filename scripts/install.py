#!/usr/bin/env python3
"""Install the code-review skill into a project.

The installer is intentionally conservative: it plans every target before
writing, treats identical files as already installed, and refuses to overwrite
different content unless --force is used. --force moves the existing target to
a timestamped .bak sibling first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = {
    "en": REPO / "skills" / "code-review-gate",
    "zh-CN": REPO / "skills" / "code-review-gate-zh",
}
TARGET_NAMES = {"en": "code-review-gate", "zh-CN": "code-review-gate-zh"}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")


def _targets(lang: str) -> dict:
    source = SOURCE_SKILLS[lang]
    name = TARGET_NAMES[lang]
    return {
        "claude-code": (
            ("skill", source, ".claude/skills/" + name, True),
        ),
        "codex": (
            ("skill", source, ".agents/skills/" + name, True),
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_digest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result[path.relative_to(root).as_posix()] = _sha256(path)
    return result


def _state(source: Path, target: Path, is_dir: bool) -> str:
    """Return create, unchanged, replace, or conflict."""
    if not os.path.lexists(target):
        return "create"
    if target.is_symlink():
        return "conflict"
    if is_dir:
        if not target.is_dir():
            return "conflict"
        return "unchanged" if _tree_digest(source) == _tree_digest(target) else "replace"
    if not target.is_file():
        return "conflict"
    return "unchanged" if source.read_bytes() == target.read_bytes() else "replace"


def _backup_path(target: Path) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    candidate = target.with_name(target.name + ".bak." + stamp)
    index = 1
    while os.path.lexists(candidate):
        candidate = target.with_name(target.name + ".bak." + stamp + "." + str(index))
        index += 1
    return candidate


def _agents(value: str) -> list[str]:
    return ["claude-code", "codex"] if value == "both" else [value]


def _plan(project: Path, selected: list[str], force: bool, lang: str) -> tuple[list[dict], list[str]]:
    actions: list[dict] = []
    conflicts: list[str] = []
    targets = _targets(lang)
    other_name = TARGET_NAMES["zh-CN" if lang == "en" else "en"]
    for agent in selected:
        other_root = ".claude/skills" if agent == "claude-code" else ".agents/skills"
        other_relative = other_root + "/" + other_name
        if os.path.lexists(project / other_relative):
            conflicts.append(other_relative + ": another language is already installed")
        for kind, source, relative, is_dir in targets[agent]:
            if not source.exists():
                raise FileNotFoundError("source not found: " + str(source))
            target = project / relative
            current = _state(source, target, is_dir)
            if current in ("conflict", "replace") and not force:
                conflicts.append(relative)
            actions.append({
                "agent": agent,
                "kind": kind,
                "source": source,
                "target": target,
                "relative": relative,
                "is_dir": is_dir,
                "state": current,
                "backup": None,
            })
    return actions, conflicts


def _print_plan(project: Path, actions: list[dict], dry_run: bool, as_json: bool) -> None:
    if as_json:
        payload = {
            "ok": True,
            "project": str(project),
            "dry_run": dry_run,
            "actions": [{
                "agent": action["agent"],
                "kind": action["kind"],
                "target": action["relative"],
                "state": action["state"],
                "backup": (str(action["backup"].relative_to(project))
                           if action["backup"] else None),
            } for action in actions],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return
    print("project: " + str(project))
    for action in actions:
        prefix = "would " if dry_run else ""
        line = "  " + prefix + action["state"] + " " + action["relative"]
        if action["backup"]:
            line += " (backup: " + str(action["backup"].relative_to(project)) + ")"
        print(line)


def _apply(project: Path, actions: list[dict]) -> None:
    for action in actions:
        if action["state"] == "unchanged":
            continue
        target: Path = action["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / (".code-review-install-" + uuid.uuid4().hex)
        try:
            if action["is_dir"]:
                shutil.copytree(action["source"], temporary, ignore=IGNORE)
            else:
                shutil.copy2(action["source"], temporary)
            if os.path.lexists(target):
                backup = _backup_path(target)
                shutil.move(str(target), str(backup))
                action["backup"] = backup
            shutil.move(str(temporary), str(target))
        finally:
            if os.path.lexists(temporary):
                if temporary.is_dir() and not temporary.is_symlink():
                    shutil.rmtree(temporary)
                else:
                    temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the code-review-gate skill.")
    parser.add_argument("--agent", required=True, choices=("claude-code", "codex", "both"),
                        help="host skill layout to install")
    parser.add_argument("--lang", default="en", choices=("en", "zh-CN"),
                        help="skill language to install (default: en)")
    parser.add_argument("--project", default=os.getcwd(), help="target project root (default: cwd)")
    parser.add_argument("--force", action="store_true",
                        help="replace existing different files, keeping a timestamped backup")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print("error: project directory not found: " + str(project), file=sys.stderr)
        return 1

    selected = _agents(args.agent)
    try:
        actions, conflicts = _plan(project, selected, args.force, args.lang)
    except FileNotFoundError as error:
        print("error: " + str(error), file=sys.stderr)
        return 1

    if conflicts:
        payload = {"ok": False, "project": str(project), "conflicts": conflicts}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print("error: refusing to overwrite existing different content:", file=sys.stderr)
            for relative in conflicts:
                print("  " + relative, file=sys.stderr)
            print("re-run with --force to replace and keep a timestamped backup.", file=sys.stderr)
        return 2

    if args.dry_run:
        _print_plan(project, actions, True, args.json)
        return 0

    try:
        _apply(project, actions)
    except OSError as error:
        print("error: installation failed: " + str(error), file=sys.stderr)
        return 1
    _print_plan(project, actions, False, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
