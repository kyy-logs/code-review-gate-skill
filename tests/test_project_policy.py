"""Consumer-side runtime policy and collision protection."""
import json
import os
import subprocess
import shutil
import sys
import unittest

from test_behavior_probe import BehaviorFixture, SKILL


@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
class ProjectPolicyTests(BehaviorFixture, unittest.TestCase):
    def command(self, *args, **overrides):
        env = dict(os.environ, CODE_REVIEW_PYTHON=sys.executable, **overrides)
        return subprocess.run([env['CODE_REVIEW_TEST_BASH'],
                               str(SKILL / 'scripts/collect-metrics'), *args],
                              cwd=self.root, env=env, capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def policy(self, **values):
        directory = self.root / '.code-review'
        directory.mkdir(exist_ok=True)
        (directory / 'config.json').write_text(json.dumps(values), encoding='utf-8')

    def test_output_root_and_init_do_not_overwrite_an_existing_run(self):
        output = self.root / 'review output'
        self.policy(output_dir=str(output))
        result = self.command('init', 'fresh')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = output / 'active/fresh/code-review.md'
        self.assertTrue(report.is_file())
        report.write_text('existing report', encoding='utf-8')
        self.assertNotEqual(self.command('init', 'fresh').returncode, 0)
        self.assertEqual(report.read_text(encoding='utf-8'), 'existing report')
        self.assertFalse((self.root / 'docs/work/active/fresh').exists())

    def test_custom_output_keeps_the_whole_pipeline_in_the_selected_root(self):
        output = self.root / 'custom output'
        self.policy(line_target=70)
        env = dict(CODE_REVIEW_OUTPUT_DIR=str(output))
        result = self.command('init', 'fresh', **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        directory = output / 'active/fresh'
        shutil.copytree(self.review / 'probes', directory / 'probes', dirs_exist_ok=True)
        self.assertIn('70%', (directory / 'code-review.md').read_text(encoding='utf-8'))
        for args in [('sync', 'fresh'), ('coverage', 'fresh', '--line', '75'),
                     ('render-report', 'fresh'), ('verify-report', 'fresh'),
                     ('summary', 'fresh'), ('gate-pass', 'fresh', 'code-review'),
                     ('archive', 'fresh')]:
            result = self.command(*args, **env)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / 'workflow-events.log').is_file())
        self.assertTrue((output / 'quality-trend.csv').is_file())
        self.assertTrue((directory / 'quality-scorecard.txt').is_file())
        self.assertFalse((self.root / 'docs/work/workflow-events.log').exists())

    def test_archived_and_event_only_slugs_cannot_be_reinitialized(self):
        archived = self.root / 'docs/work/archive/2025/old'
        archived.mkdir(parents=True)
        self.assertNotEqual(self.command('init', 'old').returncode, 0)
        result = self.command('coverage', 'history', '--line', '90')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self.command('init', 'history').returncode, 0)
        self.assertFalse((self.root / 'docs/work/active/history').exists())

    def test_project_threshold_controls_gate_and_scorecard(self):
        self.policy(line_target=70, branch_target=60)
        for args in [('render-report', 'example'), ('coverage', 'example', '--line', '75'),
                     ('gate-pass', 'example', 'code-review'), ('archive', 'example')]:
            result = self.command(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
        card = (self.review / 'quality-scorecard.txt').read_text(encoding='utf-8')
        self.assertIn('COVERAGE_TARGET="70"', card)
        self.policy(line_target=80)
        self.assertEqual(self.command('render-report', 'example').returncode, 0)
        self.assertNotEqual(self.command('gate-pass', 'example', 'code-review').returncode, 0)

    def test_invalid_policy_fails_before_writing_events(self):
        for value in (-1, 101, '70', True):
            self.policy(line_target=value)
            self.assertNotEqual(self.command('coverage', 'example', '--line', '75').returncode, 0)
            self.assertFalse((self.root / 'docs/work/workflow-events.log').exists())

    def test_event_clock_is_numeric_and_iso_formatted(self):
        result = self.command('coverage', 'example', '--line', '90')
        self.assertEqual(result.returncode, 0, result.stderr)
        fields = (self.root / 'docs/work/workflow-events.log').read_text().splitlines()[1].split('\t')
        self.assertGreater(int(fields[0]), 0)
        self.assertRegex(fields[1], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d')
