"""Exercise the shipped calculator against fixed Git changes and JaCoCo counters."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'shared/scripts/coverage-diff.py'


class CoverageDiffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coverage-diff-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.source = self.repo / 'src/main/java/demo/Value.java'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('package demo;\nclass Value {\n}\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.source.write_text('package demo;\nclass Value {\n  int value() {\n    int x = 1;\n    return x;\n  }\n}\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'head')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.report = self.root / 'jacoco.xml'
        self.report.write_text('<report><package name="demo"><sourcefile name="Value.java">'
                               '<line nr="4" mi="0" ci="2"/>'
                               '<line nr="5" mi="1" ci="0"/>'
                               '</sourcefile></package></report>', encoding='utf-8')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True, encoding='utf-8')

    def calculate(self, *, target=None, confirm=True, mappings=None):
        command = [sys.executable, '-X', 'utf8', str(SCRIPT), '--project-root', str(self.repo),
                   '--base', self.base] + (target or ['--head', self.head])
        command += mappings or ['--jacoco', 'src/main/java', str(self.report)]
        if confirm:
            command.append('--confirm-report-scope')
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=30)
        return result.returncode, json.loads(result.stdout)

    def test_counts_only_changed_executable_lines_and_preserves_inputs(self):
        before = self.report.read_bytes(), self.source.read_bytes()
        code, result = self.calculate()
        self.assertEqual(code, 0)
        self.assertEqual((result['covered_lines'], result['executable_lines'], result['percent']), (1, 2, '50.000000'))
        self.assertEqual(result['uncovered_lines'], [dict(path='src/main/java/demo/Value.java', line=5)])
        self.assertEqual((self.report.read_bytes(), self.source.read_bytes()), before)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_scope_confirmation_is_required(self):
        code, result = self.calculate(confirm=False)
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'error')

    def test_missing_or_malformed_report_is_error(self):
        for content in (None, '<report>'):
            with self.subTest(content=content):
                if content is None:
                    self.report.unlink()
                else:
                    self.report.write_text(content, encoding='utf-8')
                code, result = self.calculate()
                self.assertEqual((code, result['status']), (1, 'error'))

    def test_missing_sourcefile_is_not_treated_as_non_executable(self):
        self.report.write_text('<report/>', encoding='utf-8')
        code, result = self.calculate()
        self.assertEqual((code, result['status']), (1, 'error'))

    def test_zero_denominator_is_not_applicable(self):
        code, result = self.calculate(target=['--head', self.base])
        self.assertEqual(code, 0)
        self.assertEqual((result['status'], result['percent']), ('not_applicable', None))

    def test_duplicate_mapping_does_not_double_count(self):
        mapping = ['--jacoco', 'src/main/java', str(self.report)]
        code, result = self.calculate(mappings=mapping * 2)
        self.assertEqual(code, 0)
        self.assertEqual((result['covered_lines'], result['executable_lines']), (1, 2))

    def test_worktree_includes_untracked_source(self):
        extra = self.source.with_name('Extra.java')
        extra.write_text('class Extra {}\n', encoding='utf-8')
        code, result = self.calculate(target=['--worktree'])
        self.assertEqual((code, result['status']), (1, 'error'))
        self.assertIn('Extra.java', result['reason'])
