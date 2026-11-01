"""Offline checks for generated skill-script copies."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / 'scripts/sync-skill-scripts.py'
SOURCES = ('collect-metrics', 'lib-metrics', 'rule-grep', 'sync-results.py')


class SyncSkillScriptsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='sync-skill-scripts-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.shared = self.root / 'shared/scripts'
        self.shared.mkdir(parents=True)
        for name in SOURCES:
            (self.shared / name).write_text('source ' + name + '\n', encoding='utf-8')
        self.packages = [
            self.root / 'skills/code-review/scripts',
            self.root / 'skills/code-review-zh/scripts',
        ]

    def run_sync(self, *args):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(SYNC), '--root', str(self.root), *args
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_check_fails_before_copies_exist(self):
        result = self.run_sync('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('collect-metrics', result.stdout + result.stderr)

    def test_sync_copies_all_scripts_to_both_packages_and_is_idempotent(self):
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        for package in self.packages:
            self.assertEqual(
                sorted(path.name for path in package.iterdir()),
                sorted(SOURCES),
            )
            for name in SOURCES:
                self.assertEqual(
                    (package / name).read_bytes(),
                    (self.shared / name).read_bytes(),
                )
        before = {p: p.stat().st_mtime_ns for p in self.root.rglob('*') if p.is_file()}
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {p: p.stat().st_mtime_ns for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.run_sync('--check').returncode, 0)

    def test_check_detects_tamper_without_fixing_it(self):
        self.assertEqual(self.run_sync().returncode, 0)
        target = self.packages[1] / 'rule-grep'
        target.write_text('tampered\n', encoding='utf-8')
        result = self.run_sync('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(encoding='utf-8'), 'tampered\n')

    def test_check_rejects_extra_script(self):
        self.assertEqual(self.run_sync().returncode, 0)
        (self.packages[0] / 'extra.py').write_text('extra\n', encoding='utf-8')
        result = self.run_sync('--check')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('extra.py', result.stdout + result.stderr)

    def test_missing_shared_source_fails(self):
        (self.shared / 'lib-metrics').unlink()
        result = self.run_sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('lib-metrics', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
