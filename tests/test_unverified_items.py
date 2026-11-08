"""Offline checks for visible, ungraded review questions; no model calls."""

from copy import deepcopy
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

from test_behavior_probe import BehaviorFixture, ROOT, SKILL


ITEM = {
    'location': 'src/Loader.java:27',
    'summary': 'Cancellation releases the guard while an old worker is still scanning.',
    'reason': 'The state may mean logical cancellation or physical task completion.',
    'needed_evidence': 'Confirm the intended lifecycle contract for the loading flag.',
}


class UnverifiedItemsTests(BehaviorFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.package = SKILL

    def helper(self, *args):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(self.package / 'scripts/sync-results.py'),
            '--review-dir', str(self.review), '--registry', str(self.registry), *args
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def add_item(self, probe='behavior-review', item=None):
        self.records[probe]['unverified_items'] = [deepcopy(ITEM if item is None else item)]
        self.write_records()

    def test_optional_items_preserve_legacy_records_and_counts(self):
        baseline = self.summary()
        self.assertEqual(baseline.get('unverified_items', []), [])
        self.records['behavior-review']['unverified_items'] = []
        self.write_records()
        self.assertEqual(self.summary(), baseline)
        self.add_item()
        self.add_item('impact-analysis')
        result = self.summary()
        self.assertEqual(result['probes'], baseline['probes'])
        self.assertEqual(result['findings'], baseline['findings'])
        self.assertEqual(result['reconcile'], baseline['reconcile'])
        self.assertEqual(result['unverified_items'], [
            dict(probe='behavior-review', **ITEM), dict(probe='impact-analysis', **ITEM)])
        self.assertEqual(self.helper('--events').stdout,
                         self.remove_items_and_events())

    def remove_items_and_events(self):
        for record in self.records.values():
            record.pop('unverified_items', None)
        self.write_records()
        return self.helper('--events').stdout

    def test_invalid_items_fail_without_writing_report(self):
        invalid = [None, 'question', {}, [None], [{}]]
        for key in ITEM:
            bad = deepcopy(ITEM)
            bad.pop(key)
            invalid.append([bad])
            bad = deepcopy(ITEM)
            bad[key] = ' '
            invalid.append([bad])
        invalid += [[dict(ITEM, severity='medium')], [dict(ITEM, unexpected='value')]]
        report = self.review / 'code-review.md'
        before = report.read_bytes()
        for value in invalid:
            with self.subTest(value=value):
                self.records['behavior-review']['unverified_items'] = value
                self.write_records()
                result = self.helper('--write-report')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertEqual(report.read_bytes(), before)

    def test_items_render_beside_findings_in_both_languages(self):
        for locale, heading in (('code-review-gate', 'Pending confirmation'),
                                ('code-review-gate-zh', '待确认')):
            with self.subTest(locale=locale):
                self.package = ROOT / 'skills' / locale
                report = self.review / 'code-review.md'
                shutil.copyfile(self.package / 'assets/code-review.md', report)
                item = dict(ITEM, summary='Guard <worker> | pending\nNot a confirmed defect.')
                self.add_item(item=item)
                record = self.review / 'probes/behavior-review.json'
                raw_record = record.read_bytes()
                result = self.helper('--write-report')
                self.assertEqual(result.returncode, 0, result.stderr)
                rendered = report.read_text(encoding='utf-8')
                self.assertIn(heading, rendered)
                self.assertIn('&lt;worker&gt;', rendered)
                self.assertNotIn('<worker>', rendered)
                for value in (ITEM['location'], ITEM['reason'], ITEM['needed_evidence']):
                    self.assertIn(value, rendered)
                self.assertLess(rendered.index('<!-- code-review:probes:start -->'), rendered.index(ITEM['location']))
                self.assertLess(rendered.index(ITEM['needed_evidence']), rendered.index('<!-- code-review:probes:end -->'))
                self.assertEqual(self.helper('--check-report').returncode, 0)
                self.assertIn('unverified_items: 1', self.helper('--summary').stdout)
                self.assertEqual(record.read_bytes(), raw_record)
                self.assertEqual(self.helper('--write-report').returncode, 0)
                self.assertEqual(report.read_text(encoding='utf-8'), rendered)
                report.write_text(rendered.replace(ITEM['reason'], 'TAMPERED'), encoding='utf-8')
                self.assertNotEqual(self.helper('--check-report').returncode, 0)
                self.records['behavior-review'].pop('unverified_items')
                self.write_records()
                self.assertEqual(self.helper('--write-report').returncode, 0)
                self.assertNotIn(ITEM['needed_evidence'], report.read_text(encoding='utf-8'))

    def test_legacy_report_does_not_need_an_additional_region(self):
        report = self.review / 'code-review.md'
        content = report.read_text(encoding='utf-8')
        content = re.sub(r'<!-- code-review:unverified:start -->.*?<!-- code-review:unverified:end -->',
                         '', content, flags=re.S)
        report.write_text(content, encoding='utf-8')
        self.assertEqual(self.helper('--write-report').returncode, 0)
        self.assertEqual(self.helper('--check-report').returncode, 0)
        before = report.read_bytes()
        self.add_item()
        result = self.helper('--write-report')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(ITEM['needed_evidence'], report.read_text(encoding='utf-8'))
        self.assertNotIn('code-review:unverified', report.read_text(encoding='utf-8'))

    def test_missing_or_duplicate_region_cannot_hide_items(self):
        self.add_item()
        report = self.review / 'code-review.md'
        original = report.read_text(encoding='utf-8')
        marker = '<!-- code-review:probes:end -->'
        for changed in (original.replace(marker, ''), original + '\n' + marker):
            with self.subTest(changed=changed[-100:]):
                report.write_text(changed, encoding='utf-8')
                for action in ('--write-report', '--check-report'):
                    result = self.helper(action)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(report.read_text(encoding='utf-8'), changed)

    def test_pending_question_and_high_render_together_without_changing_grade(self):
        self.add_high()
        self.add_item()
        result = self.helper('--write-report')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = (self.review / 'code-review.md').read_text(encoding='utf-8')
        self.assertIn('#### [high] Priority parsing', report)
        self.assertIn('#### [Pending confirmation] Cancellation releases', report)
        self.assertIn('**blocked**', report)
        summary = self.helper('--summary')
        self.assertIn('findings: high=1 medium=0 low=0', summary.stdout)
        self.assertIn('unverified_items: 1', summary.stdout)

    def test_error_record_retains_items_and_existing_high(self):
        self.add_high()
        self.add_item()
        self.records['behavior-review'].update(status='error', reason='Timed out after saving evidence')
        self.write_records()
        result = self.summary()
        self.assertEqual(result['findings'][0]['severity'], 'high')
        self.assertEqual(result['unverified_items'][0]['summary'], ITEM['summary'])
        self.assertEqual(result['reconcile']['pending'], 1)


@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
class UnverifiedGateTests(BehaviorFixture, unittest.TestCase):
    def test_unverified_items_alone_do_not_block_or_add_findings(self):
        self.records['behavior-review']['unverified_items'] = [deepcopy(ITEM)]
        self.write_records()
        rendered = self.helper('--project-root', str(self.root), '--write-report')
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        env = dict(os.environ, CODE_REVIEW_SKILL_DIR=str(self.skill),
                   CODE_REVIEW_PYTHON=sys.executable)
        result = subprocess.run([
            os.environ['CODE_REVIEW_TEST_BASH'], str(SKILL / 'scripts/collect-metrics'),
            'gate-pass', 'example', 'code-review'
        ], cwd=self.root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = self.summary()
        self.assertEqual(summary['findings'], [])
        self.assertEqual(summary['reconcile']['pending'], 0)


if __name__ == '__main__':
    unittest.main()
