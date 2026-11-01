#!/usr/bin/env python3
"""Synchronize the shared review scripts into both installable skill packages.

Only the four explicitly listed scripts are managed. Unknown files in a package
are never deleted; --check reports them so they can be reviewed manually.
"""

import argparse
import shutil
import sys
from pathlib import Path


SOURCES = (
    'collect-metrics',
    'lib-metrics',
    'rule-grep',
    'sync-results.py',
)
PACKAGES = (
    Path('skills/code-review/scripts'),
    Path('skills/code-review-zh/scripts'),
)


def files_in(directory):
    if not directory.is_dir():
        return {}
    result = {}
    for path in sorted(directory.rglob('*')):
        if not path.is_file():
            continue
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        result[path.name] = path
    return result


def check(root, write=False):
    shared = root / 'shared/scripts'
    errors = []
    for name in SOURCES:
        source = shared / name
        if not source.is_file():
            errors.append('missing shared source: shared/scripts/' + name)
    for relative in PACKAGES:
        package = root / relative
        existing = files_in(package)
        expected = set(SOURCES)
        for name in sorted(expected - set(existing)):
            errors.append('missing generated script: ' + relative.as_posix() + '/' + name)
        for name in sorted(set(existing) - expected):
            errors.append('unexpected generated script: ' + relative.as_posix() + '/' + name)
        for name in sorted(expected & set(existing)):
            source = shared / name
            if source.is_file() and existing[name].read_bytes() != source.read_bytes():
                if write:
                    shutil.copy2(source, existing[name])
                else:
                    errors.append('out-of-date generated script: ' + relative.as_posix() + '/' + name)
    if write:
        for relative in PACKAGES:
            (root / relative).mkdir(parents=True, exist_ok=True)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='verify without writing')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    shared = root / 'shared/scripts'
    for name in SOURCES:
        if not (shared / name).is_file():
            print('error: missing shared source: ' + str(shared / name), file=sys.stderr)
            return 1
    if not args.check:
        for relative in PACKAGES:
            package = root / relative
            package.mkdir(parents=True, exist_ok=True)
            for name in SOURCES:
                source = shared / name
                target = package / name
                if target.is_file() and target.read_bytes() == source.read_bytes():
                    continue
                shutil.copy2(source, target)
    errors = check(root, write=False)
    if errors:
        for error in errors:
            print('error: ' + error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
