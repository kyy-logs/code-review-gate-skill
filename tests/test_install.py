"""Install host skill layouts without overwriting user configuration."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SKILL = ROOT / "skills" / "code-review"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="code-review-install-")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "consumer project"
        self.project.mkdir()
        self.environment = dict(os.environ, CODE_REVIEW_PYTHON=sys.executable)
        self.environment.pop("CODE_REVIEW_SKILL_DIR", None)

    def install(self, *args, project=None):
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(INSTALLER), "--project",
             str(project or self.project), *args],
            cwd=ROOT, env=self.environment, capture_output=True, text=True,
            encoding="utf-8", timeout=30)

    def test_zh_language_installs_code_review_zh(self):
        result = self.install("--agent", "codex", "--lang", "zh-CN")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".agents/skills/code-review-zh/SKILL.md").is_file())
        self.assertFalse((self.project / ".agents/skills/code-review").exists())

    def test_both_hosts_honor_language(self):
        result = self.install("--agent", "both", "--lang", "zh-CN")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/code-review-zh/SKILL.md").is_file())
        self.assertTrue((self.project / ".agents/skills/code-review-zh/SKILL.md").is_file())
        self.assertFalse((self.project / ".claude/skills/code-review").exists())
        self.assertFalse((self.project / ".agents/skills/code-review").exists())

    def test_other_language_blocks_install_even_with_force(self):
        other = self.project / ".agents/skills/code-review-zh"
        other.mkdir(parents=True)
        (other / "custom.txt").write_text("keep me\n", encoding="utf-8")
        for extra in ((), ("--force",)):
            with self.subTest(extra=extra):
                result = self.install("--agent", "codex", *extra)
                self.assertEqual(result.returncode, 2)
                self.assertIn("another language", result.stderr)
                self.assertEqual((other / "custom.txt").read_text(encoding="utf-8"), "keep me\n")
        self.assertFalse((self.project / ".agents/skills/code-review").exists())

    def test_invalid_language_writes_nothing(self):
        result = self.install("--agent", "codex", "--lang", "zh")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / ".agents").exists())

    def test_claude_installation_installs_skill_only(self):
        result = self.install("--agent", "claude-code")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/code-review/SKILL.md").is_file())
        self.assertFalse((self.project / ".claude/agents").exists())
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".agents").exists())

    def test_codex_installation_installs_skill_only(self):
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".agents/skills/code-review/SKILL.md").is_file())
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".claude").exists())

    def test_both_hosts_install_together(self):
        result = self.install("--agent", "both")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".claude/skills/code-review/SKILL.md").is_file())
        self.assertTrue((self.project / ".agents/skills/code-review/SKILL.md").is_file())
        self.assertFalse((self.project / ".claude/agents").exists())
        self.assertFalse((self.project / ".codex").exists())

    def test_repeat_install_is_a_noop(self):
        self.assertEqual(self.install("--agent", "codex").returncode, 0)
        skill = self.project / ".agents/skills/code-review/SKILL.md"
        before = (skill.stat().st_mtime_ns, skill.read_bytes())
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        after = (skill.stat().st_mtime_ns, skill.read_bytes())
        self.assertEqual(before, after)
        self.assertIn("unchanged .agents/skills/code-review", result.stdout)

    def test_existing_skill_directory_is_protected(self):
        skill = self.project / ".agents/skills/code-review"
        skill.mkdir(parents=True)
        (skill / "custom.txt").write_text("user file\n", encoding="utf-8")
        result = self.install("--agent", "codex")
        self.assertEqual(result.returncode, 2)
        self.assertIn(".agents/skills/code-review", result.stderr)
        self.assertEqual((skill / "custom.txt").read_text(encoding="utf-8"), "user file\n")
        self.assertFalse((self.project / ".claude").exists())

    def test_force_backs_up_existing_skill_directory(self):
        skill = self.project / ".agents/skills/code-review"
        skill.mkdir(parents=True)
        (skill / "custom.txt").write_text("user file\n", encoding="utf-8")
        result = self.install("--agent", "codex", "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((skill / "SKILL.md").is_file())
        backups = list(skill.parent.glob("code-review.bak.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "custom.txt").read_text(encoding="utf-8"), "user file\n")

    def test_dry_run_writes_nothing(self):
        result = self.install("--agent", "both", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would create .claude/skills/code-review", result.stdout)
        self.assertIn("would create .agents/skills/code-review", result.stdout)
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".codex").exists())

    def test_json_output_and_config_toml_untouched(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('model = "keep-me"\n', encoding="utf-8")
        result = self.install("--agent", "codex", "--json", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["actions"]), 1)
        self.assertEqual(config.read_text(encoding="utf-8"), 'model = "keep-me"\n')

    @unittest.skipUnless(os.environ.get("CODE_REVIEW_TEST_BASH"), "Bash is required")
    def test_shell_wrapper_delegates_to_python(self):
        result = subprocess.run(
            [os.environ["CODE_REVIEW_TEST_BASH"], str(ROOT / "scripts/install"),
             "--agent", "codex", "--project", str(self.project)],
            cwd=ROOT, env=self.environment, capture_output=True, text=True,
            encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.project / ".agents/skills/code-review/SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
