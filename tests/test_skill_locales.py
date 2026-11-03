"""Structural consistency checks for the bilingual skill packages."""

from pathlib import Path
import re
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

    def test_conclusion_first_report_layout_passes(self):
        for name in ('code-review', 'code-review-zh'):
            path = self.root / 'skills' / name / 'assets/code-review.md'
            text = path.read_text(encoding='utf-8')
            gate = re.search(
                r'<!-- code-review:gate:start -->\n.*?\n<!-- code-review:gate:end -->',
                text, re.S,
            ).group(0)
            text = text.replace(gate, '')
            text = text.replace('<!-- code-review:probes:start -->',
                                gate + '\n\n<!-- code-review:probes:start -->')
            path.write_text(text, encoding='utf-8')
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

    def test_table_and_prose_rule_id_changes_fail(self):
        for filename, old_id, new_id in (
            ('security.md', 'SEC-106', 'SEC-999'),
            ('concurrency.md', 'MULT-CONC-001', 'MULT-CONC-999'),
        ):
            with self.subTest(filename=filename):
                path = self.root / 'skills/code-review-zh/references/rules' / filename
                original = path.read_text(encoding='utf-8')
                self.assertIn(old_id, original)
                path.write_text(original.replace(old_id, new_id, 1), encoding='utf-8')
                try:
                    result = self.check()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(filename, result.stdout + result.stderr)
                finally:
                    path.write_text(original, encoding='utf-8')

    def test_missing_prose_rule_reference_fails(self):
        path = self.root / 'skills/code-review-zh/references/rules/naming-format.md'
        original = path.read_text(encoding='utf-8')
        # This ID appears in more than one rule; losing one occurrence must be caught.
        self.assertGreater(original.count('MULT-NAME-006'), 1)
        path.write_text(original.replace('MULT-NAME-006', '', 1), encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('naming-format.md', result.stdout + result.stderr)

    def test_invalid_report_marker_pairs_fail(self):
        for case in ('missing-end', 'duplicate-end', 'end-before-start', 'both-missing-pair'):
            with self.subTest(case=case):
                paths = [self.root / 'skills' / name / 'assets/code-review.md'
                         for name in ('code-review', 'code-review-zh')]
                originals = [path.read_text(encoding='utf-8') for path in paths]
                begin = '<!-- code-review:gate:start -->'
                end = '<!-- code-review:gate:end -->'
                text = originals[1]
                if case == 'missing-end':
                    text = text.replace(end, '')
                elif case == 'duplicate-end':
                    text += '\n' + end
                elif case == 'end-before-start':
                    text = text.replace(end, '').replace(begin, end + '\n' + begin)
                else:
                    for path, original in zip(paths, originals):
                        path.write_text(original.replace(begin, '').replace(end, ''), encoding='utf-8')
                if case != 'both-missing-pair':
                    paths[1].write_text(text, encoding='utf-8')
                try:
                    result = self.check()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('marker', result.stdout + result.stderr)
                finally:
                    for path, original in zip(paths, originals):
                        path.write_text(original, encoding='utf-8')

    def test_duplicate_report_label_key_fails(self):
        path = self.root / 'skills/code-review-zh/assets/report-labels.json'
        original = path.read_text(encoding='utf-8')
        path.write_text(original.replace('{', '{"language": "en",', 1), encoding='utf-8')
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate', result.stdout + result.stderr)

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
