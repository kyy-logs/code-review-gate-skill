"""Offline checks for the read-only environment preflight."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'shared/scripts/check-environment.py'


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('check_environment', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.paths = {name: '/tools with spaces/' + name for name in ('bash', 'git', 'rg')}
        self.versions = {'bash': 'GNU bash, version 3.2.57(1)-release\n',
                         'git': 'git version 2.45.0\n', 'rg': 'ripgrep 14.1.0\n'}
        self.lookup = patch.object(self.module.shutil, 'which', side_effect=self.paths.get)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        self.runner = patch.object(self.module.subprocess, 'run', side_effect=self.run_tool)
        self.run_mock = self.runner.start()
        self.addCleanup(self.runner.stop)
        self.yaml = patch.object(self.module.importlib, 'import_module', return_value=SimpleNamespace(__version__='6.0.2'))
        self.yaml.start()
        self.addCleanup(self.yaml.stop)

    def run_tool(self, args, **kwargs):
        name = next(name for name, path in self.paths.items() if path == args[0])
        return subprocess.CompletedProcess(args, 0, self.versions[name], '')

    def test_supported_environment_returns_paths_and_versions(self):
        result = self.module.check_environment()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['tools']['python']['path'], sys.executable)
        self.assertEqual(result['tools']['bash']['path'], self.paths['bash'])
        self.assertEqual(result['tools']['pyyaml']['version'], '6.0.2')
        for call in self.run_mock.call_args_list:
            self.assertIsInstance(call.args[0], list)
            self.assertFalse(call.kwargs.get('shell', False))
            self.assertGreater(call.kwargs['timeout'], 0)

    def test_missing_rg_is_optional_with_limited_fallback(self):
        del self.paths['rg']
        result = self.module.check_environment()
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['tools']['rg']['available'])
        self.assertTrue(result['warnings'])
        self.assertIn('git grep', result['search_fallback'])
        self.assertIn('untracked', result['search_fallback'])

    def test_explicit_bash_overrides_the_path_lookup(self):
        selected = '/selected Git Bash/bash'
        self.paths['bash'] = selected
        self.run_mock.side_effect = self.run_tool
        with patch.object(self.module.shutil, 'which', side_effect=lambda name: selected if name == selected else self.paths.get(name)):
            result = self.module.check_environment(bash=selected)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['tools']['bash']['path'], selected)

    def test_missing_required_tool_is_an_error(self):
        for name in ('bash', 'git'):
            with self.subTest(tool=name):
                original = self.paths.pop(name)
                result = self.module.check_environment()
                self.assertEqual(result['status'], 'error')
                self.assertFalse(result['tools'][name]['available'])
                self.assertTrue(result['errors'])
                self.paths[name] = original

    def test_missing_pyyaml_is_reported_without_installing(self):
        self.yaml.stop()
        with patch.object(self.module.importlib, 'import_module', side_effect=ModuleNotFoundError('yaml')):
            result = self.module.check_environment()
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['tools']['pyyaml']['available'])

    def test_old_or_unrecognized_bash_is_an_error(self):
        for version in ('GNU bash, version 3.1.0\n', 'unrecognized wrapper output\n'):
            with self.subTest(version=version):
                self.versions['bash'] = version
                self.assertEqual(self.module.check_environment()['status'], 'error')

    def test_unusable_executables_and_timeouts_are_reported(self):
        for error in (OSError('cannot execute'), subprocess.TimeoutExpired(['bash'], 5)):
            with self.subTest(error=error):
                self.run_mock.side_effect = error
                result = self.module.check_environment()
                self.assertEqual(result['status'], 'error')
                self.assertFalse(result['tools']['bash']['available'])
        self.run_mock.side_effect = lambda args, **kwargs: subprocess.CompletedProcess(args, 1, '', 'unavailable')
        self.assertEqual(self.module.check_environment()['status'], 'error')


class EnvironmentCommandTests(unittest.TestCase):
    def test_real_command_prints_json_and_writes_no_project_files(self):
        with tempfile.TemporaryDirectory(prefix='review-preflight-') as directory:
            root = Path(directory)
            (root / 'existing.txt').write_text('preserve', encoding='utf-8')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT)], cwd=root,
                capture_output=True, text=True, encoding='utf-8', timeout=30)
            record = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0 if record['status'] == 'ready' else 1)
            self.assertEqual(record['tools']['python']['path'], sys.executable)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})
            self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
