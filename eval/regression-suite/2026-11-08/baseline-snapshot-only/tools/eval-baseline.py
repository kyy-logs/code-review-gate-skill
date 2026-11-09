#!/usr/bin/env python3
"""Freeze a skill version and compare existing runs to it.

Evaluation-only tooling. It does not run models, inspect findings, or change
the runtime skill.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


SKIP_DIRS = {'__pycache__'}
SKIP_SUFFIXES = {'.pyc'}


class BaselineError(Exception):
    pass


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skill_files(skill_dir):
    files = []
    for path in sorted(skill_dir.rglob('*')):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts) or path.suffix in SKIP_SUFFIXES:
            continue
        files.append((path.relative_to(skill_dir).as_posix(), sha256_file(path)))
    return files


def skill_tree_hash(skill_dir):
    digest = hashlib.sha256()
    for relative, file_hash in skill_files(skill_dir):
        digest.update(relative.encode('utf-8') + b'\0')
        digest.update(file_hash.encode('ascii') + b'\n')
    return digest.hexdigest()


def git(repo, *args, check=True, binary=False):
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True, text=not binary, encoding=None if binary else 'utf-8',
        errors=None if binary else 'replace', timeout=120,
    )
    if check and result.returncode != 0:
        detail = result.stderr
        if isinstance(detail, bytes):
            detail = detail.decode('utf-8', 'replace')
        raise BaselineError((detail or '').strip() or 'git command failed')
    return result


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    if isinstance(data, bytes):
        temp.write_bytes(data)
    else:
        with open(temp, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(data)
    os.replace(str(temp), str(path))


def make_manifest(repo, skill_dir, output, force):
    repo = repo.expanduser().resolve()
    skill_dir = skill_dir.expanduser().resolve()
    output = output.expanduser().resolve()
    manifest_path = output / 'MANIFEST.json'
    if manifest_path.exists() and not force:
        raise BaselineError('manifest already exists: %s (pass --force to replace)' % manifest_path)
    if not (repo / '.git').exists():
        raise BaselineError('not a git repository: %s' % repo)
    if not skill_dir.is_dir():
        raise BaselineError('skill directory not found: %s' % skill_dir)
    top = git(repo, 'rev-parse', '--show-toplevel').stdout.strip()
    if Path(top).resolve() != repo:
        raise BaselineError('repo must be the git worktree root: %s' % top)
    branch = git(repo, 'branch', '--show-current').stdout.strip()
    commit = git(repo, 'rev-parse', 'HEAD').stdout.strip()
    status = [line for line in git(repo, 'status', '--porcelain=v1').stdout.splitlines() if line.strip()]
    diff = git(repo, 'diff', '--binary', '--', binary=True).stdout
    files = skill_files(skill_dir)
    skill_md = dict(files).get('SKILL.md')
    manifest = {
        'schema_version': 1,
        'created_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'repo_root': str(repo),
        'branch': branch,
        'commit': commit,
        'dirty': bool(status),
        'git_status': status,
        'uncommitted_diff_sha256': hashlib.sha256(diff).hexdigest(),
        'skill_dir': str(skill_dir),
        'skill_tree_sha256': skill_tree_hash(skill_dir),
        'skill_md_sha256': skill_md,
        'skill_files': [{'path': path, 'sha256': digest} for path, digest in files],
    }
    output.mkdir(parents=True, exist_ok=True)
    write_atomic(output / 'uncommitted.diff', diff)
    write_atomic(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest_path, manifest


def read_manifest(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise BaselineError('cannot read manifest %s: %s' % (path, error))
    if not isinstance(data, dict) or not isinstance(data.get('skill_tree_sha256'), str):
        raise BaselineError('manifest is missing skill_tree_sha256')
    return data


def case_id(run_dir):
    for name in ('EXECUTION.json', 'PREPARATION.json'):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get('case_id'), str):
            return data['case_id']
    return None


def compare(manifest_path, run_dirs, required):
    manifest = read_manifest(manifest_path)
    expected = manifest['skill_tree_sha256']
    reusable, mismatched, unverifiable = [], [], []
    reusable_cases = set()
    for run in run_dirs:
        run = run.expanduser().resolve()
        skill = run / 'frozen-skill'
        if not run.is_dir():
            unverifiable.append({'path': str(run), 'reason': 'run directory not found'})
            continue
        if not skill.is_dir():
            unverifiable.append({'path': str(run), 'reason': 'frozen-skill not found'})
            continue
        actual = skill_tree_hash(skill)
        item = {
            'path': str(run),
            'case_id': case_id(run),
            'skill_tree_sha256': actual,
        }
        if actual == expected:
            reusable.append(item)
            if item['case_id']:
                reusable_cases.add(item['case_id'])
        else:
            mismatched.append(item)
    missing = [name for name in required if name not in reusable_cases]
    return {
        'manifest': str(manifest_path.expanduser().resolve()),
        'expected_skill_tree_sha256': expected,
        'reusable': reusable,
        'mismatched': mismatched,
        'unverifiable': unverifiable,
        'required_missing': missing,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    manifest_parser = sub.add_parser('manifest', help='write a frozen skill manifest')
    manifest_parser.add_argument('--repo', type=Path, default=Path('.'))
    manifest_parser.add_argument('--skill-dir', type=Path, required=True)
    manifest_parser.add_argument('--output', type=Path, required=True)
    manifest_parser.add_argument('--force', action='store_true')

    compare_parser = sub.add_parser('compare', help='compare runs to a manifest')
    compare_parser.add_argument('--manifest', type=Path, required=True)
    compare_parser.add_argument('--runs', type=Path, nargs='+', required=True)
    compare_parser.add_argument('--required', nargs='*', default=[],
                                help='case IDs that must have a reusable run')
    compare_parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == 'manifest':
            path, data = make_manifest(args.repo, args.skill_dir, args.output, args.force)
            print(json.dumps({
                'manifest': str(path),
                'commit': data['commit'],
                'branch': data['branch'],
                'dirty': data['dirty'],
                'skill_tree_sha256': data['skill_tree_sha256'],
                'uncommitted_diff_sha256': data['uncommitted_diff_sha256'],
            }, ensure_ascii=False, indent=2))
            return 0
        result = compare(args.manifest, args.runs, args.required)
        if args.output:
            write_atomic(args.output.expanduser().resolve(), json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['required_missing'] else 0
    except (OSError, BaselineError) as error:
        print('eval-baseline: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
