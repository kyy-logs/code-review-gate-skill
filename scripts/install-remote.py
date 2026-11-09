#!/usr/bin/env python3
"""Download code-review-gate into a temporary checkout and run its installer.

This entry also works via ``python -c``; it does not depend on __file__.
Only the Python standard library and Git are needed to install the files.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REPOSITORY = "https://github.com/kyy-logs/code-review-gate-skill.git"
DEFAULT_REF = "main"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and install the code-review-gate skill.")
    parser.add_argument("--agent", required=True, choices=("claude-code", "codex", "both"))
    parser.add_argument("--lang", default="en", choices=("en", "zh-CN"),
                        help="skill language to install (default: en)")
    parser.add_argument("--project", default=os.getcwd(), help="target project (default: cwd)")
    parser.add_argument("--ref", default=DEFAULT_REF, help="Git branch or tag to download")
    parser.add_argument("--force", action="store_true", help="replace with a timestamped backup")
    parser.add_argument("--dry-run", action="store_true", help="download and plan without installing")
    parser.add_argument("--json", action="store_true", help="machine-readable installer output")
    args = parser.parse_args(argv)

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print("error: project directory not found: " + str(project), file=sys.stderr)
        return 1

    try:
        with tempfile.TemporaryDirectory(prefix="code-review-download-") as temporary:
            checkout = Path(temporary) / "source"
            print("Downloading code-review-gate (" + args.ref + ")...", file=sys.stderr)
            download = subprocess.run(
                ["git", "clone", "--config", "core.autocrlf=false", "--depth", "1",
                 "--single-branch", "--branch", args.ref,
                 "--", REPOSITORY, str(checkout)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            if download.returncode:
                print("error: download failed:\n" + download.stderr, file=sys.stderr)
                return download.returncode

            installer = checkout / "scripts/install.py"
            if not installer.is_file():
                print("error: selected ref has no scripts/install.py", file=sys.stderr)
                return 1
            command = [sys.executable, str(installer), "--agent", args.agent,
                       "--lang", args.lang, "--project", str(project)]
            for flag in ("force", "dry_run", "json"):
                if getattr(args, flag):
                    command.append("--" + flag.replace("_", "-"))
            return subprocess.run(command).returncode
    except (OSError, subprocess.TimeoutExpired) as error:
        print("error: remote installation failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
