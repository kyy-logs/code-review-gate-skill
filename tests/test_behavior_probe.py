"""Offline integration of behavior-review with the installed review pipeline.

These fixtures exercise records and gates, not the model's defect recall.
Run with CODE_REVIEW_TEST_BASH set to a Bash executable for shell checks.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/code-review-gate'
PROBES = ('behavior-review', 'test-coverage', 'repo-guard', 'impact-analysis')


class BehaviorFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='behavior-probe-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.review = self.root / 'docs/work/active/example'
        (self.review / 'probes').mkdir(parents=True)
        self.skill = self.root / 'skill'
        (self.skill / 'references').mkdir(parents=True)
        self.registry = self.skill / 'references/probes.yaml'
        shutil.copyfile(SKILL / 'references/probes.yaml', self.registry)
        shutil.copyfile(SKILL / 'assets/code-review.md', self.review / 'code-review.md')
        self.records = {
            name: dict(probe=name, status='passed', duration=1, findings=[])
            for name in PROBES
        }
        self.write_records()

    def write_records(self):
        for name, record in self.records.items():
            (self.review / 'probes' / (name + '.json')).write_text(
                json.dumps(record), encoding='utf-8')

    def add_high(self):
        self.records['behavior-review'].update(status='failed', findings=[{
            'id': 'behavior-review-1', 'probe': 'behavior-review', 'severity': 'high',
            'status': 'open', 'location': 'src/Parser.java:17',
            'summary': 'Priority parsing overwrites the visibility flag',
            'evidence': 'With priority set and visibility omitted, fall-through writes false; '
                        'the parser contract requires visibility to retain its default.'
        }])
        self.write_records()

    def helper(self, *args):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(SKILL / 'scripts/sync-results.py'),
            '--review-dir', str(self.review), '--registry', str(self.registry), *args
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def summary(self, *args):
        result = self.helper(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)


class BehaviorRecordsTests(BehaviorFixture, unittest.TestCase):
    def test_clean_four_probe_records_have_no_invented_findings(self):
        result = self.summary()
        self.assertEqual([p['name'] for p in result['probes']], list(PROBES))
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['reconcile'], dict(total=0, done=0, pending=0))

    def test_missing_behavior_record_is_not_accepted_as_zero(self):
        (self.review / 'probes/behavior-review.json').unlink()
        result = self.helper('--probes')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('behavior-review.json', result.stderr)

    def test_malformed_behavior_records_cannot_be_synchronized(self):
        path = self.review / 'probes/behavior-review.json'
        for raw in ('{invalid', '{"probe":"behavior-review","status":"passed"}',
                    '{"probe":"behavior-review","status":"passed","findings":null}'):
            with self.subTest(raw=raw):
                path.write_text(raw, encoding='utf-8')
                result = self.helper('--probes')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')

    def test_rule_probe_error_preserves_behavior_finding_and_other_records(self):
        self.add_high()
        self.records['repo-guard'].update(status='error', reason='Selected rules are unreadable')
        self.write_records()
        result = self.summary()
        self.assertEqual(len(result['probes']), 4)
        self.assertEqual(result['findings'][0]['id'], 'behavior-review-1')
        self.assertEqual(result['reconcile'], dict(total=1, done=0, pending=1))

    def test_report_renders_behavior_finding_and_preserves_narrative(self):
        self.add_high()
        path = self.review / 'code-review.md'
        path.write_text(path.read_text(encoding='utf-8') + '\nSupplement for behavior-review-1.\n',
                        encoding='utf-8')
        result = self.helper('--write-report')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = path.read_text(encoding='utf-8')
        self.assertIn('behavior-review', report)
        self.assertIn('behavior-review-1', report)
        self.assertIn('total=1 / done=0 / pending=1', report)
        self.assertTrue(report.endswith('Supplement for behavior-review-1.\n'))
        self.assertEqual(self.helper('--check-report').returncode, 0)
        path.write_text(report.replace('behavior-review-1', 'behavior-review-9'), encoding='utf-8')
        self.assertNotEqual(self.helper('--check-report').returncode, 0)

    def test_legacy_reviewer_region_requires_removal(self):
        path = self.review / 'code-review.md'
        legacy = path.read_text(encoding='utf-8') + (
            chr(10) + '<!-- code-review:reviewer:start -->' + chr(10) + 'old verdict' + chr(10)
            + '<!-- code-review:reviewer:end -->' + chr(10))
        path.write_text(legacy, encoding='utf-8')
        result = self.helper('--write-report')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('旧版 Reviewer', result.stderr)
        self.assertEqual(path.read_text(encoding='utf-8'), legacy)

    def test_historical_three_probe_run_still_uses_its_frozen_registry(self):
        configuration = yaml.safe_load(self.registry.read_text(encoding='utf-8'))
        configuration['probes'] = [p for p in configuration['probes'] if p['name'] != 'behavior-review']
        self.registry.write_text(yaml.safe_dump(configuration), encoding='utf-8')
        (self.review / 'probes/behavior-review.json').unlink()
        result = self.summary()
        self.assertEqual(len(result['probes']), 3)
        self.assertEqual(result['reconcile'], dict(total=0, done=0, pending=0))

@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Set CODE_REVIEW_TEST_BASH for Bash checks')
class BehaviorGateTests(BehaviorFixture, unittest.TestCase):
    def command(self, *args):
        env = dict(os.environ, CODE_REVIEW_SKILL_DIR=str(self.skill), CODE_REVIEW_PYTHON=sys.executable)
        return subprocess.run([
            os.environ['CODE_REVIEW_TEST_BASH'], str(SKILL / 'scripts/collect-metrics'), *args
        ], cwd=self.root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)

    def render(self):
        result = self.command('render-report', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.command('verify-report', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)

    def events(self):
        path = self.root / 'docs/work/workflow-events.log'
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def test_clean_four_probe_run_syncs_and_passes_gate(self):
        self.render()
        result = self.command('sync', 'example', '--probes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('behavior-review status=passed required=true', result.stdout)
        result = self.command('gate-pass', 'example', 'code-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('\tcode-review\tgate-pass\t', self.events())

    def test_open_behavior_high_blocks_gate(self):
        self.add_high()
        self.render()
        result = self.command('gate-pass', 'example', 'code-review')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_behavior_execution_error_blocks_gate_without_any_findings(self):
        self.records['behavior-review'].update(status='error', reason='Target source is unreadable')
        self.write_records()
        self.render()
        result = self.command('gate-pass', 'example', 'code-review')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('required', result.stderr)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_missing_behavior_record_does_not_write_success_metrics(self):
        (self.review / 'probes/behavior-review.json').unlink()
        result = self.command('sync', 'example', '--probes')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('\tmetric:probe\t', self.events())
        result = self.command('gate-pass', 'example', 'code-review')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

if __name__ == '__main__':
    unittest.main()
