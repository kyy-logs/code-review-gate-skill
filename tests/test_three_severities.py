"""Strict three-level findings and gate integration."""
import os
import subprocess
import unittest

import test_behavior_probe as fixtures
from test_behavior_probe import BehaviorFixture


class ThreeSeverityTests(BehaviorFixture, unittest.TestCase):
    def test_three_levels_are_counted_and_only_high_enters_reconciliation(self):
        self.add_high()
        first = self.records['behavior-review']['findings'][0]
        self.records['behavior-review']['findings'] += [
            dict(first, id='behavior-review-2', severity='medium'),
            dict(first, id='behavior-review-3', severity='low'),
        ]
        self.write_records()
        originals = {p: p.read_bytes() for p in self.review.rglob('*.json')}
        result = self.summary()
        self.assertEqual([result['probes'][0][s] for s in ('high', 'medium', 'low')], [1, 1, 1])
        self.assertEqual(result['reconcile'], dict(total=1, done=0, pending=1))
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        self.assertEqual(set(result['probes'][0]) - {'name', 'required', 'status', 'duration', 'reason'}, {'high', 'medium', 'low'})
        rendered = self.helper('--render')
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.assertIn('| high | medium | low |', rendered.stdout)

    def test_unsupported_levels_fail_in_findings(self):
        for severity in ('critical', 'CRITICAL', 'urgent'):
            with self.subTest(severity=severity):
                self.add_high()
                self.records['behavior-review']['findings'][0]['severity'] = severity
                self.write_records()
                self.assertNotEqual(self.helper('--probes').returncode, 0)


    def test_raw_reconciled_high_closes_reconciliation(self):
        self.add_high()
        finding = self.records['behavior-review']['findings'][0]
        finding['status'] = 'reconciled'
        finding['reconciled_by'] = 'Fixed in follow-up'
        self.records['behavior-review']['status'] = 'passed'
        self.write_records()
        result = self.summary()
        self.assertEqual(result['probes'][0]['high'], 1)
        self.assertEqual(result['reconcile'], dict(total=1, done=1, pending=0))
        self.assertEqual(result['findings'][0]['status'], 'reconciled')

@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
class ThreeSeverityGateTests(BehaviorFixture, unittest.TestCase):
    command = fixtures.BehaviorGateTests.command
    render = fixtures.BehaviorGateTests.render
    events = fixtures.BehaviorGateTests.events

    def test_high_still_blocks_and_old_level_does_not_write_success(self):
        self.add_high()
        self.render()
        self.assertNotEqual(self.command('gate-pass', 'example', 'code-review').returncode, 0)
        self.records['behavior-review']['findings'][0]['severity'] = 'critical'
        self.write_records()
        self.assertNotEqual(self.command('sync', 'example').returncode, 0)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_medium_and_low_findings_do_not_block(self):
        self.add_high()
        item = self.records['behavior-review']['findings'][0]
        item['severity'] = 'medium'
        self.records['behavior-review'].update(
            status='passed', findings=[item, dict(item, id='behavior-review-2', severity='low')])
        self.write_records()
        self.render()
        result = self.command('gate-pass', 'example', 'code-review')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_summary_reports_counts_ids_and_blockers_from_json(self):
        self.add_high()
        first = self.records['behavior-review']['findings'][0]
        self.records['behavior-review']['findings'] += [
            dict(first, id='behavior-review-2', severity='medium'),
            dict(first, id='behavior-review-3', severity='low'),
        ]
        self.write_records()
        self.render()
        result = self.command('summary', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('findings: high=1 medium=1 low=1', result.stdout)
        self.assertIn('high_ids: behavior-review-1', result.stdout)
        self.assertIn('medium_ids: behavior-review-2', result.stdout)
        self.assertIn('low_ids: behavior-review-3', result.stdout)
        self.assertIn('reconcile: total=1 done=0 pending=1', result.stdout)
        self.assertIn('status: blocked', result.stdout)

    def test_summary_rejects_tampered_report(self):
        self.add_high()
        self.render()
        report = self.review / 'code-review.md'
        report.write_text(report.read_text(encoding='utf-8').replace(
            'behavior-review-1', 'behavior-review-9'), encoding='utf-8')
        result = self.command('summary', 'example')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Review summary', result.stdout)

    def test_summary_zero_findings_is_explicit(self):
        self.render()
        result = self.command('summary', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('findings: high=0 medium=0 low=0', result.stdout)
        self.assertIn('high_ids: -', result.stdout)
        self.assertIn('status: no recorded blockers', result.stdout)

    def test_security_metrics_and_scorecard_use_three_levels(self):
        self.render()
        result = self.command('security', 'example', '--high', '2', '--medium', '3', '--low', '4')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('high=2 medium=3 low=4', result.stdout)
        self.assertNotIn('critical', self.events().lower())
        result = self.command('archive', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        card = (self.review / 'quality-scorecard.txt').read_text(encoding='utf-8')
        self.assertIn('SECURITY_HIGH="2"', card)
        self.assertIn('SECURITY_MEDIUM="3"', card)
        self.assertIn('SECURITY_LOW="4"', card)
        self.assertNotIn('critical', card.lower())
        self.assertNotIn('critical', (self.root / 'docs/work/quality-trend.csv').read_text().lower())

    def test_unsupported_security_option_is_rejected(self):
        self.assertNotEqual(self.command('security', 'example', '--critical', '1').returncode, 0)
        self.assertEqual(self.events(), '')

    def test_unsupported_historical_metric_is_not_silently_ignored(self):
        self.render()
        events = self.root / 'docs/work/workflow-events.log'
        events.parent.mkdir(parents=True, exist_ok=True)
        old = '0\tdate\texample\t-\t-\tmetric:security\tcritical\t1\n'
        events.write_text(old, encoding='utf-8')
        result = self.command('archive', 'example')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events.read_text(encoding='utf-8'), old)

    def test_unknown_trend_format_is_not_overwritten(self):
        self.render()
        self.assertEqual(self.command('sync', 'example').returncode, 0)
        trend = self.root / 'docs/work/quality-trend.csv'
        trend.write_text('old,format\n1,2\n', encoding='utf-8')
        result = self.command('archive', 'example')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trend.read_text(encoding='utf-8'), 'old,format\n1,2\n')

    def test_rule_package_accepts_only_current_severities(self):
        rules = self.root / 'rules'
        rules.mkdir()
        path = rules / 'security.md'
        for level, success in (('HIGH', True), ('MEDIUM', True), ('LOW', True), ('CRITICAL', False)):
            with self.subTest(level=level):
                path.write_text(f'### SEC-001 [{level}] SQL rule\n\n**检测模式**: `unsafeSql`\n', encoding='utf-8')
                result = subprocess.run(
                    [os.environ['CODE_REVIEW_TEST_BASH'], str(fixtures.SKILL / 'scripts/rule-grep'), '--list'],
                    cwd=self.root, env=dict(os.environ, CODE_REVIEW_RULES_DIR=str(rules)),
                    capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode == 0, success, result.stderr)


if __name__ == '__main__':
    unittest.main()
