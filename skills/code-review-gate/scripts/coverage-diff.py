#!/usr/bin/env python3
"""Read-only JaCoCo coverage calculation for changed Java lines in mapped source sets."""
import argparse
from decimal import Decimal, ROUND_DOWN
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(project, *args):
    result = subprocess.run(['git', '-C', str(project), *args], capture_output=True)
    require(result.returncode == 0, result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout


def relative_path(value):
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in value,
            f'Expected a project-relative POSIX path: {value}')
    return path


def report_lines(path):
    root = ET.parse(path).getroot()
    require(root.tag == 'report', f'Not a JaCoCo report: {path}')
    sources = {}
    for package in root.iter('package'):
        name = package.attrib['name']
        relative_path(name)
        for source in package.findall('sourcefile'):
            filename = source.attrib['name']
            require(bool(filename) and '/' not in filename, f'Invalid sourcefile name: {filename}')
            relative_path(filename)
            key = (PurePosixPath(name) / filename).as_posix()
            require(key not in sources, f'Ambiguous sourcefile {key} in {path}; use module-specific reports')
            lines = {}
            for row in source.findall('line'):
                nr, missed, covered = (int(row.attrib[key]) for key in ('nr', 'mi', 'ci'))
                require(nr > 0 and missed >= 0 and covered >= 0, f'Invalid line counters in {path}')
                require(nr not in lines, f'Duplicate line {key}:{nr} in {path}')
                lines[nr] = (missed, covered)
            sources[key] = lines
    return sources


def mappings(project, pairs, base, head):
    result = []
    seen = set()
    for source, report in pairs:
        source = relative_path(source)
        report = (project / report).resolve()
        pair = (source, report)
        if pair in seen:
            continue
        for previous, previous_report, _ in result:
            require(source != previous and source not in previous.parents and previous not in source.parents,
                    f'Overlapping source roots: {source}, {previous}')
            require(report != previous_report, f'Use a separate report for each source root: {report}')
        suffix = ':' + source.as_posix() if source.parts else '^{tree}'
        if head:
            try:
                tree = git(project, 'cat-file', '-t', head + suffix).strip()
            except ValueError:
                # A source set may have been deleted entirely by the target.
                tree = git(project, 'cat-file', '-t', base + suffix).strip()
            require(tree == b'tree', f'Source root is not a directory at target: {source}')
        else:
            directory = (project / source).resolve()
            require(project == directory or project in directory.parents, f'Source root escapes project: {source}')
            if not directory.is_dir():
                require(git(project, 'cat-file', '-t', base + suffix).strip() == b'tree',
                        f'Missing source root: {source}')
        result.append((source, report, report_lines(report)))
        seen.add(pair)
    return result


def changed_lines(project, base, head):
    refs = [base] + ([head] if head else [])
    raw = git(project, 'diff', '--name-status', '--no-renames', '-z', *refs, '--')
    fields = raw.split(b'\0')[:-1]
    require(len(fields) % 2 == 0, 'Invalid Git change list')
    paths = {os.fsdecode(fields[i + 1]) for i in range(0, len(fields), 2) if fields[i] != b'D'}
    untracked = set()
    if head is None:
        raw = git(project, 'ls-files', '--others', '--exclude-standard', '-z')
        untracked = {os.fsdecode(path) for path in raw.split(b'\0') if path}
        paths |= untracked
    for path in sorted(paths):
        if not path.endswith('.java'):
            continue
        if path in untracked:
            file = project / path
            require(not file.is_symlink(), f'Untracked source symlink is unsupported: {path}')
            content = file.read_bytes()
            require(b'\0' not in content, f'Binary Java source: {path}')
            lines = set(range(1, len(content.splitlines()) + 1))
        else:
            patch = git(project, 'diff', '--no-renames', '--no-ext-diff', '--no-textconv',
                        '--no-color', '--unified=0', '--inter-hunk-context=0', *refs,
                        '--', ':(literal)' + path)
            require(b'Binary files ' not in patch and b'GIT binary patch' not in patch,
                    f'Binary Java diff: {path}')
            lines = set()
            for match in re.finditer(rb'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', patch, re.M):
                start = int(match[1])
                count = int(match[2]) if match[2] is not None else 1
                lines.update(range(start, start + count))
        yield PurePosixPath(path), lines


def calculate(args):
    require(args.worktree or bool(args.head and args.head.strip()), '--head must not be empty')
    require(args.confirm_report_scope,
            'Confirm report target version, complete mapped source sets, and available line debug information with --confirm-report-scope')
    project = args.project_root.resolve()
    top = Path(os.fsdecode(git(project, 'rev-parse', '--show-toplevel')).strip()).resolve()
    require(top == project, '--project-root must be the Git repository root')
    base = git(project, 'rev-parse', '--verify', args.base + '^{commit}').decode('ascii').strip()
    head = None
    if args.head:
        head = git(project, 'rev-parse', '--verify', args.head + '^{commit}').decode('ascii').strip()
    reports = mappings(project, args.jacoco, base, head)
    covered = total = 0
    uncovered, excluded, per_file = [], [], []
    for path, changed in changed_lines(project, base, head):
        selected = [(source, data) for source, _, data in reports
                    if source == path or source in path.parents]
        if not selected:
            excluded.append(path.as_posix())
            continue
        if not changed:
            continue
        source, data = selected[0]
        key = path.relative_to(source).as_posix()
        require(key in data, f'Missing sourcefile {key} for {source}; cannot infer non-executable code')
        rows = data[key]
        executable = [line for line in sorted(changed) if sum(rows.get(line, (0, 0))) > 0]
        hits = sum(rows[line][1] > 0 for line in executable)
        covered += hits
        total += len(executable)
        uncovered.extend(dict(path=path.as_posix(), line=line) for line in executable if rows[line][1] == 0)
        per_file.append(dict(path=path.as_posix(), covered_lines=hits, executable_lines=len(executable)))
    percent = None
    if total:
        percent = str((Decimal(covered) * 100 / Decimal(total)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
    return dict(status='computed' if total else 'not_applicable', mode='commits' if head else 'worktree',
                base=base, head=head, report_scope='caller_confirmed_not_independently_verified',
                covered_lines=covered, executable_lines=total, percent=percent,
                percent_format='decimal string truncated to 6 places; use counts for exact comparisons',
                files=per_file, uncovered_lines=uncovered, excluded_java_files=excluded,
                reports=[dict(source_root=source.as_posix(), report=str(report)) for source, report, _ in reports])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--base', required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--head')
    target.add_argument('--worktree', action='store_true')
    parser.add_argument('--jacoco', nargs=2, action='append', required=True, metavar=('SOURCE_ROOT', 'REPORT'))
    parser.add_argument('--confirm-report-scope', action='store_true',
                        help='Caller confirms target version, complete source-set coverage, and line debug information')
    args = parser.parse_args()
    try:
        result = calculate(args)
    except (ValueError, OSError, KeyError, ET.ParseError) as error:
        print(json.dumps(dict(status='error', reason=str(error)), ensure_ascii=True))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
