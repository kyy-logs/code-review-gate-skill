"""Offline tests for bilingual report labels and rule extraction."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / 'skills/code-review'
ZH = ROOT / 'skills/code-review-zh'
PROBES = ('behavior-review', 'test-coverage', 'repo-guard', 'impact-analysis')


class LocalizedRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='localized-runtime-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def prepare(self, package):
        workspace = self.root / (package.name + '-work')
        skill = workspace / 'skill'
        shutil.copytree(package, skill)
        review = workspace / 'docs/work/active/example'
        (review / 'probes').mkdir(parents=True)
        shutil.copyfile(skill / 'assets/code-review.md', review / 'code-review.md')
        finding = {
            'id': 'behavior-review-1',
            'probe': 'behavior-review',
            'severity': 'high',
            'status': 'open',
            'location': 'src/Parser.java:7',
            'summary': '保留原文 summary',
            'evidence': '保留原文 evidence',
        }
        records = {
            'behavior-review': {'probe': 'behavior-review', 'status': 'failed', 'findings': [finding]},
            'test-coverage': {'probe': 'test-coverage', 'status': 'passed', 'findings': []},
            'repo-guard': {'probe': 'repo-guard', 'status': 'passed', 'findings': []},
            'impact-analysis': {'probe': 'impact-analysis', 'status': 'passed', 'findings': []},
        }
        for name, record in records.items():
            (review / 'probes' / (name + '.json')).write_text(
                json.dumps(record, ensure_ascii=False), encoding='utf-8')
        return skill, review

    def run_pipeline(self, skill, review, action):
        return subprocess.run([
            sys.executable, '-X', 'utf8', str(skill / 'scripts/sync-results.py'),
            '--review-dir', str(review), '--registry', str(skill / 'references/probes.yaml'),
            action,
        ], capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_english_and_chinese_labels_change_presentation_not_facts(self):
        en_skill, en_review = self.prepare(EN)
        zh_skill, zh_review = self.prepare(ZH)
        for skill, review, heading, status, status_line in (
            (en_skill, en_review, 'Review summary (from JSON)', 'status: blocked', 'open (open)'),
            (zh_skill, zh_review, '审查摘要（来自 JSON）', 'status: 阻塞', '待处理（open）'),
        ):
            rendered = self.run_pipeline(skill, review, '--write-report')
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            report = (review / 'code-review.md').read_text(encoding='utf-8')
            self.assertIn(heading, self.run_pipeline(skill, review, '--summary').stdout)
            self.assertIn(status, self.run_pipeline(skill, review, '--summary').stdout)
            self.assertIn('保留原文 summary', report)
            self.assertIn('保留原文 evidence', report)
            self.assertIn(status_line, report)

        en_summary = self.run_pipeline(en_skill, en_review, '--summary').stdout
        zh_summary = self.run_pipeline(zh_skill, zh_review, '--summary').stdout
        self.assertIn('findings: high=1 medium=0 low=0', en_summary)
        self.assertIn('findings: high=1 medium=0 low=0', zh_summary)

    def test_missing_label_is_an_error(self):
        skill, review = self.prepare(EN)
        labels_path = skill / 'assets/report-labels.json'
        labels = json.loads(labels_path.read_text(encoding='utf-8'))
        labels.pop('summary_heading')
        labels_path.write_text(json.dumps(labels, ensure_ascii=False), encoding='utf-8')
        result = self.run_pipeline(skill, review, '--summary')
        self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(os.environ.get('CODE_REVIEW_TEST_BASH'), 'Bash is required')
class RuleGrepLocalizationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='rule-grep-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rules = self.root / 'rules'
        self.rules.mkdir()
        (self.rules / 'index.md').write_text('# rules\n', encoding='utf-8')

    def run_grep(self, *args):
        env = dict(os.environ, CODE_REVIEW_RULES_DIR=str(self.rules))
        return subprocess.run([
            os.environ['CODE_REVIEW_TEST_BASH'],
            str(ROOT / 'skills/code-review/scripts/rule-grep'), *args
        ], env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_bilingual_detection_labels_and_semantic_marker(self):
        (self.rules / 'bilingual.md').write_text(
            '### SEC-001 [HIGH] Chinese\n\n'
            '**检测模式**: `foo`\n\n'
            '### SEC-002 [HIGH] English\n\n'
            '**Detection pattern**: `bar`\n\n'
            '### SEM-001 [HIGH] Semantic\n\n'
            '**Detection mode**: semantic\n'
            '**Detection pattern**: `baz`\n',
            encoding='utf-8')
        result = self.run_grep('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('foo', result.stdout)
        self.assertIn('bar', result.stdout)
        self.assertNotIn('baz', result.stdout)

    def test_existing_rules_still_list(self):
        shutil.copytree(ROOT / 'skills/code-review/references/rules', self.rules,
                        dirs_exist_ok=True)
        result = self.run_grep('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SEC-001', result.stdout)


if __name__ == '__main__':
    unittest.main()
