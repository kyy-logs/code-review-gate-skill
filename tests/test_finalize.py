"""Offline report finalization through the installed shell entry point."""
import os
import unittest

import test_behavior_probe as fixtures


@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
class FinalizeTests(fixtures.BehaviorFixture, unittest.TestCase):
    command = fixtures.BehaviorGateTests.command
    events = fixtures.BehaviorGateTests.events

    def test_finalize_matches_existing_summary_and_is_repeatable(self):
        originals = {p: p.read_bytes() for p in (self.review / 'probes').glob('*.json')}
        result = self.command('finalize', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = self.command('summary', 'example')
        self.assertEqual(expected.returncode, 0, expected.stderr)
        self.assertEqual(result.stdout, expected.stdout)
        report = (self.review / 'code-review.md').read_bytes()
        repeated = self.command('finalize', 'example')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(repeated.stdout, result.stdout)
        self.assertEqual((self.review / 'code-review.md').read_bytes(), report)
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        self.assertEqual(self.events(), '')

    def test_finalize_preserves_blocking_findings_in_summary(self):
        self.add_high()
        result = self.command('finalize', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('behavior-review-1', result.stdout)
        self.assertIn('status: blocked', result.stdout)
        self.assertNotIn('\tgate-pass\t', self.events())

    def test_invalid_json_stops_without_report_update_or_summary(self):
        path = self.review / 'code-review.md'
        original = path.read_bytes()
        (self.review / 'probes/behavior-review.json').write_text('{invalid', encoding='utf-8')
        result = self.command('finalize', 'example')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.events(), '')

    def test_missing_report_marker_stops_without_summary(self):
        path = self.review / 'code-review.md'
        path.write_text('Human notes without generated markers\n', encoding='utf-8')
        original = path.read_bytes()
        result = self.command('finalize', 'example')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.events(), '')
