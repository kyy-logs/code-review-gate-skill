"""Structural consistency checks for the bilingual skill packages."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / 'scripts/check-skill-locales.py'


class SkillLocaleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='skill-locales-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(ROOT / 'skills/code-review', self.root / 'skills/code-review')
        shutil.copytree(ROOT / 'skills/code-review-zh', self.root / 'skills/code-review-zh')

    def check(self):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(CHECK), '--root', str(self.root)
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_actual_package_structure_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_required_probe_mismatch_fails(self):
        path = self.root / 'skills/code-review-zh/references/probes.yaml'
        text = path.read_text(encoding='utf-8').replace('required: false', 'required: true', 1)
        path.write_text(text, encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('required', result.stdout + result.stderr)

    def test_missing_rule_file_fails(self):
        (self.root / 'skills/code-review-zh/references/rules/security.md').unlink()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('security.md', result.stdout + result.stderr)

    def test_english_rule_index_has_no_legacy_chinese_marker(self):
        text = (ROOT / 'skills/code-review/references/rules/index.md').read_text(encoding='utf-8')
        self.assertNotIn('检测模式', text)
        self.assertNotIn('规则ID', text)

    def test_rule_pattern_mismatch_fails(self):
        path = self.root / 'skills/code-review-zh/references/rules/baseline-java.md'
        text = path.read_text(encoding='utf-8').replace(
            'Statement[^;]*execute(Query|Update)?', 'changed-pattern', 1)
        path.write_text(text, encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rule contract', result.stdout + result.stderr)

    def test_report_marker_order_mismatch_fails(self):
        path = self.root / 'skills/code-review-zh/assets/code-review.md'
        text = path.read_text(encoding='utf-8')
        text = text.replace('code-review:probes:start', '@@TMP@@')
        text = text.replace('code-review:gate:start', 'code-review:probes:start')
        text = text.replace('@@TMP@@', 'code-review:gate:start')
        path.write_text(text, encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('marker', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
