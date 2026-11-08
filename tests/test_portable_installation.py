"""Run copied release files from a separate consumer project."""

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
SOURCE = ROOT / 'skills/code-review-gate'
ZH_SOURCE = ROOT / 'skills/code-review-gate-zh'


class PortableInstallationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='review-release-')
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / 'consumer project'
        self.project.mkdir()
        self.review = self.project / 'docs/work/active/example'
        (self.review / 'probes').mkdir(parents=True)
        self.environment = dict(os.environ, CODE_REVIEW_PYTHON=sys.executable)
        self.environment.pop('CODE_REVIEW_SKILL_DIR', None)
        self.environment.pop('CODE_REVIEW_RULES_DIR', None)

    def install(self, relative, source=SOURCE):
        self.skill = self.project / relative
        shutil.copytree(source, self.skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        registry = yaml.safe_load((self.skill / 'references/probes.yaml').read_text(encoding='utf-8'))
        self.records = {p['name']: dict(probe=p['name'], status='passed', findings=[]) for p in registry['probes']}
        shutil.copyfile(self.skill / 'assets/code-review.md', self.review / 'code-review.md')
        self.write_records()

    def write_records(self):
        for name, record in self.records.items():
            (self.review / 'probes' / (name + '.json')).write_text(json.dumps(record), encoding='utf-8')

    def run_python(self, *args):
        return subprocess.run([sys.executable, '-X', 'utf8', str(self.skill / 'scripts/sync-results.py'),
                               '--review-dir', str(self.review), '--registry',
                               str(self.skill / 'references/probes.yaml'), *args], cwd=self.project,
                              env=self.environment, capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_python_pipeline_works_after_copying_to_each_install_location(self):
        for location in ('.claude/skills/code-review-gate', 'custom skill directory/code-review'):
            with self.subTest(location=location):
                self.install(location)
                before = {p: p.read_bytes() for p in self.review.rglob('*.json')}
                for action in ('--write-report', '--check-report'):
                    result = self.run_python(action)
                    self.assertEqual(result.returncode, 0, result.stderr)
                result = self.run_python()
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = json.loads(result.stdout)
                self.assertEqual(len(summary['probes']), 4)
                self.assertEqual(summary['reconcile'], dict(total=0, done=0, pending=0))
                self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_bilingual_packages_work_after_copying(self):
        for source, name, heading in (
            (SOURCE, 'code-review-gate', 'Review summary (from JSON)'),
            (ZH_SOURCE, 'code-review-gate-zh', '审查摘要（来自 JSON）'),
        ):
            for location in ('.claude/skills/' + name, 'custom ' + name):
                with self.subTest(source=name, location=location):
                    self.install(location, source=source)
                    self.assertEqual(self.run_python('--write-report').returncode, 0)
                    summary = self.run_python('--summary')
                    self.assertEqual(summary.returncode, 0, summary.stderr)
                    self.assertIn(heading, summary.stdout)

    @unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
    def test_shell_pipeline_resolves_installed_files_and_project_rules(self):
        self.install('.claude/skills/code-review-gate')
        for args in (['git', 'init', '--quiet'],
                     ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                      '-c', 'user.name=Release Test', '-c', 'user.email=release-test@example.invalid',
                      'commit', '--quiet', '--allow-empty', '-m', 'Installation fixture']):
            result = subprocess.run(args, cwd=self.project, env=self.environment,
                                    capture_output=True, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)

        def command(script, *args):
            return subprocess.run([os.environ['CODE_REVIEW_TEST_BASH'], str(self.skill / 'scripts' / script), *args],
                                  cwd=self.project, env=self.environment, capture_output=True,
                                  text=True, encoding='utf-8', timeout=30)

        for args in (('render-report', 'example'), ('verify-report', 'example'),
                     ('sync', 'example', '--probes'), ('gate-pass', 'example', 'code-review')):
            result = command('collect-metrics', *args)
            self.assertEqual(result.returncode, 0, result.stderr)

        self.records['behavior-review'].update(status='failed', findings=[dict(
            id='behavior-review-1', probe='behavior-review', severity='high', status='open',
            location='src/Parser.java:7', summary='Changed parsing breaks the caller contract',
            evidence='A valid input now fails at the public parser boundary.')])
        self.write_records()
        self.assertEqual(command('collect-metrics', 'render-report', 'example').returncode, 0)
        self.assertNotEqual(command('collect-metrics', 'gate-pass', 'example', 'code-review').returncode, 0)

        rules = self.project / '.code-review/rules'
        rules.mkdir(parents=True)
        (rules / 'custom.md').write_text('### PROJECT-001 [HIGH] Project rule\n\n**检测模式**: `projectSpecificPattern`\n', encoding='utf-8')
        result = command('rule-grep', '--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PROJECT-001', result.stdout)
        self.assertNotIn('SEC-001', result.stdout)


if __name__ == '__main__':
    unittest.main()
