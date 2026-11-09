#!/usr/bin/env python3
"""Print read-only tool checks as JSON; exit 1 when a required check fails."""
import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys


def check_command(name, command=None):
    path = shutil.which(command or name)
    result = dict(path=path, available=False)
    if path is None:
        return dict(result, error='Not found on PATH')
    try:
        process = subprocess.run([path, '--version'], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=5)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(result, error=str(error))
    if process.returncode != 0:
        return dict(result, error='Version check exited ' + str(process.returncode))
    lines = process.stdout.strip().splitlines()
    version = lines[0] if lines else ''
    if name == 'bash':
        match = re.search(r'version (\d+)\.(\d+)', version)
        if match is None or tuple(map(int, match.groups())) < (3, 2):
            return dict(result, version=version, error='Bash 3.2+ required; version not supported or not recognized')
    return dict(path=path, available=True, version=version)


def check_environment(bash=None):
    tools = dict(python=dict(path=sys.executable, version=sys.version.split()[0],
                             available=sys.version_info[:2] >= (3, 9)))
    if not tools['python']['available']:
        tools['python']['error'] = 'Python 3.9+ required'
    for name in ('bash', 'git', 'rg'):
        tools[name] = check_command(name, bash if name == 'bash' else None)
    try:
        yaml = importlib.import_module('yaml')
        tools['pyyaml'] = dict(available=True, version=getattr(yaml, '__version__', 'unknown'))
    except ImportError as error:
        tools['pyyaml'] = dict(available=False, error=str(error))
    errors = [name + ': ' + tool['error'] for name, tool in tools.items()
              if name != 'rg' and not tool['available']]
    warnings = [] if tools['rg']['available'] else ['rg unavailable: ' + tools['rg']['error']]
    result = dict(status='error' if errors else 'ready', tools=tools, errors=errors, warnings=warnings)
    if not tools['rg']['available']:
        result['search_fallback'] = 'Use git grep for tracked files; read untracked files explicitly.'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bash', help='Bash executable to check instead of the first bash on PATH')
    args = parser.parse_args()
    result = check_environment(bash=args.bash)
    print(json.dumps(result))
    return 0 if result['status'] == 'ready' else 1


if __name__ == '__main__':
    sys.exit(main())
