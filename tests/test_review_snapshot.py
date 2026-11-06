"""Source-freshness checks for the final code-review gate.

These tests exercise snapshot creation, staleness detection, and legacy runs.
They do not test the model's defect recall.
Run with CODE_REVIEW_TEST_BASH set to a Bash executable.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_behavior_probe import PROBES, SKILL


class SnapshotFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='review-snapshot-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'snapshot@example.com')
        self.git('config', 'user.name', 'Snapshot Test')
        (self.root / 'src').mkdir()
        (self.root / 'src/app.py').write_text('one\n', encoding='utf-8')
        (self.root / 'README.md').write_text('readme\n', encoding='utf-8')
        self.git('add', 'src/app.py', 'README.md')
        self.git('commit', '-qm', 'c1')
        self.c1 = self.git('rev-parse', 'HEAD')
        (self.root / 'src/app.py').write_text('one\ntwo\n', encoding='utf-8')
        self.git('commit', '-qam', 'c2')
        self.c2 = self.git('rev-parse', 'HEAD')
        (self.root / 'src/extra.py').write_text('extra A\n', encoding='utf-8')
        self.base_branch = self.git('rev-parse', '--abbrev-ref', 'HEAD')
        self.review = None
        self.snapshot_id = None

    def git_in(self, path, *args):
        result = subprocess.run(['git', '-C', str(path), *args],
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def git(self, *args):
        return self.git_in(self.root, *args)

    def command(self, *args, cwd=None):
        env = dict(os.environ, CODE_REVIEW_SKILL_DIR=str(SKILL), CODE_REVIEW_PYTHON=sys.executable)
        env.pop('CODE_REVIEW_OUTPUT_DIR', None)
        return subprocess.run([os.environ['CODE_REVIEW_TEST_BASH'],
                               str(SKILL / 'scripts/collect-metrics'), *args],
                              cwd=cwd or self.root, env=env, capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def init(self, slug='example', mode='worktree', base=None, head=None, cwd=None):
        args = ['init', slug]
        if mode is not None:
            args += ['--mode', mode]
        if base is not None:
            args += ['--base', base]
        if head is not None:
            args += ['--head', head]
        result = self.command(*args, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.review = Path(data['review_dir'])
        self.snapshot_id = data.get('snapshot_id')
        return data

    def write_records(self):
        for name in PROBES:
            record = dict(probe=name, status='passed', duration=1, findings=[])
            (self.review / 'probes' / (name + '.json')).write_text(
                json.dumps(record), encoding='utf-8')

    def render(self, slug='example', cwd=None):
        for args in (('render-report', slug), ('verify-report', slug)):
            result = self.command(*args, cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)

    def events(self):
        path = self.root / 'docs/work/workflow-events.log'
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def gate_events(self):
        return self.events().count('\tcode-review\tgate-pass\t')

    def gate(self, slug='example', cwd=None):
        return self.command('gate-pass', slug, 'code-review', cwd=cwd)


@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Set CODE_REVIEW_TEST_BASH for Bash checks')
class ReviewSnapshotTests(SnapshotFixture, unittest.TestCase):
    def prepare(self, slug='example', mode='worktree', base=None, head=None):
        self.init(slug, mode=mode, base=base, head=head)
        self.write_records()
        self.render(slug)

    def test_tracked_source_change_blocks_old_records(self):
        self.prepare()
        (self.root / 'src/app.py').write_text('one\ntwo\nthree\n', encoding='utf-8')
        # verify-report is still a pure consistency check.
        self.assertEqual(self.command('verify-report', 'example').returncode, 0)
        result = self.gate()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_untracked_same_name_content_change_blocks_old_records(self):
        self.prepare()
        (self.root / 'src/extra.py').write_text('extra B\n', encoding='utf-8')
        result = self.gate()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_generated_review_artifacts_do_not_invalidate_snapshot(self):
        self.prepare()
        self.assertEqual(self.command('sync', 'example', '--probes').returncode, 0)
        self.assertEqual(self.command('coverage', 'example', '--line', '90').returncode, 0)
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gate_events(), 1)

    def test_commits_mode_ignores_dirty_worktree_but_detects_ref_move(self):
        self.git('branch', 'feature', self.c2)
        self.prepare('commits-demo', mode='commits', base=self.c1, head='feature')
        (self.root / 'README.md').write_text('dirty readme\n', encoding='utf-8')
        result = self.gate('commits-demo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git('checkout', '-q', 'feature')
        (self.root / 'more.txt').write_text('more\n', encoding='utf-8')
        self.git('add', 'more.txt')
        self.git('commit', '-qm', 'c3')
        self.git('checkout', '-q', self.base_branch)
        result = self.gate('commits-demo')
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)
        self.assertEqual(self.gate_events(), 1)

    def test_remint_snapshot_allows_gate_after_re_review(self):
        self.prepare()
        (self.root / 'src/app.py').write_text('one\ntwo\nthree\n', encoding='utf-8')
        self.assertEqual(self.gate().returncode, 3)
        result = self.command('snapshot', 'example')
        self.assertEqual(result.returncode, 0, result.stderr)
        refreshed = json.loads(result.stdout)
        self.assertNotEqual(refreshed['snapshot_id'], self.snapshot_id)
        self.write_records()
        self.render()
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gate_events(), 1)

    def test_legacy_run_without_snapshot_warns_and_passes(self):
        self.init('legacy', mode=None)
        self.write_records()
        self.render('legacy')
        result = self.gate('legacy')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('review-snapshot.json', result.stderr)
        self.assertIn('\tcode-review\tgate-pass\t', self.events())

    def test_removing_an_untracked_reviewed_file_blocks_old_records(self):
        self.prepare()
        (self.root / 'src/extra.py').unlink()
        result = self.gate()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_tampered_snapshot_is_rejected(self):
        self.prepare()
        path = self.review / 'review-snapshot.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['files'][0]['sha256'] = '0' * 64
        path.write_text(json.dumps(data), encoding='utf-8')
        result = self.gate()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('snapshot_id', result.stderr)
        self.assertNotIn('\tcode-review\tgate-pass\t', self.events())

    def test_empty_mode_value_is_rejected(self):
        for slug, args in (
            ('bad-mode', ('init', 'bad-mode', '--mode')),
            ('bad-empty', ('init', 'bad-empty', '--mode', '')),
            ('bad-base', ('init', 'bad-base', '--base', 'HEAD')),
        ):
            with self.subTest(slug=slug):
                result = self.command(*args)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.root / 'docs/work/active' / slug).exists())

    def test_subdirectory_project_root_hashes_tracked_changes(self):
        component = self.root / 'component'
        (component / '.code-review').mkdir(parents=True)
        (component / '.code-review/config.json').write_text('{}', encoding='utf-8')
        (component / 'src').mkdir()
        (component / 'src/app.py').write_text('one\n', encoding='utf-8')
        self.git('add', 'component/src/app.py')
        self.git('commit', '-qm', 'component')
        (component / 'src/app.py').write_text('one\ntwo\n', encoding='utf-8')
        result = self.command('init', 'subroot', '--mode', 'worktree', cwd=component)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.review = Path(data['review_dir'])
        snapshot = json.loads((self.review / 'review-snapshot.json').read_text(encoding='utf-8'))
        entry = next(item for item in snapshot['files'] if item['path'] == 'src/app.py')
        self.assertIsNotNone(entry['sha256'])
        self.write_records()
        self.render('subroot', cwd=component)
        (component / 'src/app.py').write_text('one\ntwo\nthree\n', encoding='utf-8')
        result = self.gate('subroot', cwd=component)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)

    def test_nested_git_repository_is_pinned_without_aborting(self):
        nested = self.root / 'nested'
        nested.mkdir()
        self.git_in(nested, 'init', '-q')
        self.git_in(nested, 'config', 'user.email', 'nested@example.com')
        self.git_in(nested, 'config', 'user.name', 'Nested')
        (nested / 'x.txt').write_text('x\n', encoding='utf-8')
        self.git_in(nested, 'add', 'x.txt')
        self.git_in(nested, 'commit', '-qm', 'nested')
        self.init('nested-demo')
        snapshot = json.loads((self.review / 'review-snapshot.json').read_text(encoding='utf-8'))
        entry = next(item for item in snapshot['files'] if item['path'] == 'nested')
        self.assertIn('gitlink', entry)
        self.write_records()
        self.render('nested-demo')
        (nested / 'x.txt').write_text('y\n', encoding='utf-8')
        self.git_in(nested, 'commit', '-qam', 'nested2')
        result = self.gate('nested-demo')
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)

    def test_commits_mode_detects_base_ref_move(self):
        self.git('branch', 'base-branch', self.c1)
        self.git('branch', 'feature', self.c2)
        self.prepare('commits-base', mode='commits', base='base-branch', head='feature')
        self.git('checkout', '-q', 'base-branch')
        (self.root / 'base-change.txt').write_text('b\n', encoding='utf-8')
        self.git('add', 'base-change.txt')
        self.git('commit', '-qm', 'base move')
        self.git('checkout', '-q', self.base_branch)
        result = self.gate('commits-base')
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('stale-review', result.stderr)


if __name__ == '__main__':
    unittest.main()
