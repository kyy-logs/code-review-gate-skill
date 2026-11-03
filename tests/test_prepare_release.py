"""Prepare releases in temporary Git histories without publishing anything."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/prepare-release.py'


class PrepareReleaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='release-test-')
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        for name in ('VERSION', 'NEWS.md', 'README.md', 'README.zh-CN.md'):
            shutil.copyfile(ROOT / name, self.repo / name)
        (self.repo / 'VERSION').write_text('0.1.0\n', encoding='utf-8')
        (self.repo / 'NEWS.md').write_text(
            '# News\n\n<!-- UNRELEASED:START -->\n## Unreleased\n\n'
            '_No changes._\n<!-- UNRELEASED:END -->\n\n'
            '## v0.1.0 (2026-11-03)\n\n- Initial stable release.\n', encoding='utf-8')
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Release test')
        self.git('config', 'user.email', 'release@example.invalid')
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Initial release')
        self.git('tag', 'v0.1.0')
        self.validated = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args],
                                       text=True, encoding='utf-8').strip()

    def bump(self, version='0.1.1'):
        (self.repo / 'VERSION').write_text(version + '\n', encoding='utf-8')
        self.git('add', 'VERSION')
        self.git('commit', '--quiet', '-m', 'feat: clearer reports')
        self.validated = self.git('rev-parse', 'HEAD')

    def prepare(self):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(SCRIPT), '--repo', str(self.repo),
            '--validated-sha', self.validated, '--notes', str(self.repo / 'notes.txt'),
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_new_version_generates_release_docs_without_tagging(self):
        self.bump()
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertTrue(plan['prepared'])
        self.assertEqual(plan['tag'], 'v0.1.1')
        self.assertIn('clearer reports', (self.repo / 'notes.txt').read_text(encoding='utf-8'))
        self.assertIn('## v0.1.1 (', (self.repo / 'NEWS.md').read_text(encoding='utf-8'))
        for name in ('README.md', 'README.zh-CN.md'):
            self.assertIn('`v0.1.1`', (self.repo / name).read_text(encoding='utf-8'))
        self.assertEqual(self.git('tag', '--list', 'v0.1.1'), '')
        self.assertEqual((self.repo / 'VERSION').read_text().strip(), '0.1.1')

    def test_existing_version_is_idempotent_and_has_original_notes(self):
        before = {name: (self.repo / name).read_bytes() for name in
                  ('VERSION', 'NEWS.md', 'README.md', 'README.zh-CN.md')}
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['prepared'])
        self.assertIn('## v0.1.0 (', (self.repo / 'notes.txt').read_text(encoding='utf-8'))
        for name, content in before.items():
            self.assertEqual((self.repo / name).read_bytes(), content)

    def test_unvalidated_code_is_rejected_without_doc_changes(self):
        self.bump()
        before = (self.repo / 'NEWS.md').read_bytes()
        (self.repo / 'code.py').write_text('changed = True\n')
        self.git('add', 'code.py')
        self.git('commit', '--quiet', '-m', 'fix: later code')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unvalidated', result.stderr)
        self.assertEqual((self.repo / 'NEWS.md').read_bytes(), before)

    def test_newer_news_bot_commit_is_allowed(self):
        self.bump()
        p = self.repo / 'NEWS.md'
        p.write_text(p.read_text(encoding='utf-8') + '\n<!-- bot update -->\n', encoding='utf-8')
        self.git('add', 'NEWS.md')
        self.git('commit', '--quiet', '-m', 'docs: update NEWS unreleased block')
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_or_decreasing_version_is_rejected(self):
        for version in ('0.0.9', '0.1.1-beta', '0.01.1', '../bad'):
            with self.subTest(version=version):
                self.bump(version)
                before = (self.repo / 'NEWS.md').read_bytes()
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('VERSION', result.stderr)
                self.assertEqual((self.repo / 'NEWS.md').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
