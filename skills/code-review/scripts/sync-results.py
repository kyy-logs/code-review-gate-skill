#!/usr/bin/env python3
"""Validate review JSON records, derive metrics, and render a human Markdown report."""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import html
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

import yaml


SEVERITIES = ('high', 'medium', 'low')
STATUSES = ('open', 'reconciled', 'wontfix', 'false-positive')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')
LABELS_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'report-labels.json'
LABEL_KEYS = frozenset({
    'coverage_policy', 'language', 'probe_table_header', 'probe_table_separator',
    'required_yes', 'required_no',
    'status_passed', 'status_failed', 'status_error', 'status_skipped',
    'findings_heading', 'finding_id', 'finding_location', 'finding_status',
    'finding_status_open', 'finding_status_reconciled', 'finding_status_wontfix',
    'finding_status_false_positive', 'finding_status_suffix', 'finding_evidence', 'finding_reconciled_by',
    'no_findings', 'reconcile_line', 'gate_prefix', 'gate_blocked', 'gate_clear',
    'gate_detail', 'gate_footer', 'summary_heading', 'summary_findings',
    'summary_high_ids', 'summary_medium_ids', 'summary_low_ids',
    'summary_reconcile', 'summary_required_failed', 'summary_status',
    'summary_blocked', 'summary_clear', 'summary_none',
    'unverified_status', 'unverified_probe', 'unverified_reason',
    'unverified_needed_evidence', 'summary_unverified',
})

SNAPSHOT_NAME = 'review-snapshot.json'
SNAPSHOT_VERSION = 1
SNAPSHOT_ID = re.compile(r'sha256:[0-9a-f]{64}\Z')
GIT_OID = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?\Z')


class StaleReview(ValueError):
    """The reviewed source no longer matches the recorded snapshot."""


def load_labels():
    data = json.loads(LABELS_PATH.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object)
    require(isinstance(data, dict), 'report labels must be an object')
    require(data.get('language') in ('en', 'zh-CN'), 'unsupported report language')
    missing = LABEL_KEYS - data.keys()
    require(not missing, 'report labels missing keys: ' + ', '.join(sorted(missing)))
    for key in LABEL_KEYS:
        require(isinstance(data[key], str) and data[key].strip(), 'empty report label: ' + key)
    return data


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'重复字段: {key}')
        result[key] = value
    return result


def runtime_config(project, configuration):
    """Resolve project policy once for shell commands and probe handoff."""
    project = Path(project).resolve()
    path = project / '.code-review/config.json'
    data = load_record(path) if path.exists() else {}
    fields(data, (), ('output_dir', 'line_target', 'branch_target'), 'project policy')
    registry_data = yaml.load(Path(configuration).read_text(encoding='utf-8-sig'), Loader=UniqueLoader)
    params = next((p.get('params', {}) for p in registry_data['probes']
                   if p['name'] == 'test-coverage'), {})
    result = {}
    for key, default in (('line_target', 85), ('branch_target', 80)):
        value = data.get(key, params.get(key, default))
        require(type(value) is int and 0 <= value <= 100, key + ' must be an integer from 0 to 100')
        result[key] = value
    output = os.environ.get('CODE_REVIEW_OUTPUT_DIR', data.get('output_dir', 'docs/work'))
    text(output, 'output_dir')
    require(not any(c in output for c in '\t\r\n'), 'invalid output_dir')
    result['output_dir'] = (project / output).resolve().as_posix()
    require(Path(result['output_dir']) != project, 'output_dir must not be the project root')
    return result


def project_relative(project, path):
    try:
        relative = Path(path).resolve().relative_to(Path(project).resolve())
    except ValueError:
        return None
    value = relative.as_posix()
    return None if value in ('', '.') else value


def snapshot_excludes(project, *paths):
    values = {project_relative(project, path) for path in paths if path is not None}
    return sorted(value for value in values if value)


def is_excluded(relative, excludes):
    path = PurePosixPath(relative)
    return any(path == root or root in path.parents for root in map(PurePosixPath, excludes))


def git_run(project, *args):
    result = subprocess.run(['git', '-C', str(project), *args], capture_output=True)
    if result.returncode:
        detail = result.stderr.decode('utf-8', 'replace').strip() or f'exit {result.returncode}'
        raise ValueError(f'git {" ".join(args)} 失败: {detail}')
    return result.stdout


def resolve_commit(project, ref):
    require(isinstance(ref, str) and bool(ref.strip()), 'git ref 必须为非空字符串')
    return git_run(project, 'rev-parse', '--verify', ref + '^{commit}').decode('ascii').strip()


def split_paths(data):
    return [path for path in (os.fsdecode(item) for item in data.split(b'\0')) if path]


def changed_paths(project, base):
    # Disable rename detection: --name-only would report only the destination.
    # An unstaged rename is then "old deleted + new untracked"; once staged it
    # must keep producing the same path set, or unchanged content reports stale.
    return split_paths(git_run(project, 'diff', '--relative', '--name-only', '--no-renames',
                               '-z', base, '--'))


def untracked_paths(project):
    return split_paths(git_run(project, 'ls-files', '--others', '--exclude-standard', '-z'))


def index_entries(project):
    entries = {}
    for item in git_run(project, 'ls-files', '--stage', '-z').split(b'\0'):
        if not item:
            continue
        meta, _, raw = item.partition(b'\t')
        parts = meta.split(b' ')
        if len(parts) >= 2:
            entries[os.fsdecode(raw)] = (parts[0].decode('ascii'), parts[1].decode('ascii'))
    return entries


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def directory_digest(root):
    """Hash a directory tree deterministically without following symlinks."""
    digest = hashlib.sha256(b'directory\0')

    def walk(directory, prefix):
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            if entry.name == '.git':
                continue
            relative = prefix + entry.name
            if entry.is_symlink():
                digest.update(b'L\0' + os.fsencode(relative) + b'\0'
                              + os.fsencode(os.readlink(entry.path)) + b'\0')
            elif entry.is_dir(follow_symlinks=False):
                digest.update(b'D\0' + os.fsencode(relative) + b'\0')
                walk(entry.path, relative + '/')
            elif entry.is_file(follow_symlinks=False):
                digest.update(b'F\0' + os.fsencode(relative) + b'\0'
                              + hash_file(entry.path).encode('ascii') + b'\0')
            else:
                digest.update(b'O\0' + os.fsencode(relative) + b'\0')

    walk(root, '')
    return digest.hexdigest()


def file_digest(project, relative):
    path = Path(project) / relative
    if path.is_symlink():
        return hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    if not path.exists():
        return None
    if path.is_dir():
        # A tracked file can be replaced by a directory in the worktree.
        return directory_digest(path)
    require(path.is_file(), f'不支持的审查输入: {relative}')
    return hash_file(path)


def checkout_gitlink(project, relative):
    path = Path(project) / relative
    # Require the directory itself to be a repository root. Without this, an
    # empty or uninitialized submodule makes git discover the superproject and
    # return its HEAD as if it were the submodule's commit.
    if not path.is_dir() or not (path / '.git').exists():
        return None
    try:
        return git_run(path, 'rev-parse', '--verify', 'HEAD').decode('ascii').strip()
    except (ValueError, OSError):
        return None


def worktree_files(project, base, excludes):
    changed = changed_paths(project, base)
    untracked = set(untracked_paths(project))
    visible = [path for path in sorted(set(changed) | untracked) if not is_excluded(path, excludes)]
    index = index_entries(project)
    files = []
    for relative in visible:
        mode, oid = index.get(relative, (None, None))
        if mode == '160000':
            files.append(dict(path=relative, sha256=None,
                              gitlink=checkout_gitlink(project, relative) or oid))
        elif relative.endswith('/'):
            head = checkout_gitlink(project, relative.rstrip('/'))
            if head is not None:
                files.append(dict(path=relative.rstrip('/'), sha256=None, gitlink=head))
        else:
            files.append(dict(path=relative, sha256=file_digest(project, relative)))
    return files


def canonical_file(item):
    result = dict(path=item['path'], sha256=item['sha256'])
    if 'gitlink' in item:
        result['gitlink'] = item['gitlink']
    return result


def canonical_snapshot(snapshot):
    return dict(
        version=snapshot['version'],
        mode=snapshot['mode'],
        base=snapshot['base'],
        head=snapshot['head'],
        excludes=sorted(snapshot['excludes']),
        files=[canonical_file(item) for item in sorted(snapshot['files'], key=lambda item: item['path'])],
    )


def compute_snapshot_id(snapshot):
    payload = json.dumps(canonical_snapshot(snapshot), sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True)
    return 'sha256:' + hashlib.sha256(payload.encode('utf-8')).hexdigest()


def build_snapshot(project, mode, base_ref=None, head_ref=None, excludes=()):
    require(mode in ('worktree', 'commits'), 'snapshot mode 必须为 worktree 或 commits')
    project = Path(project).resolve()
    if mode == 'worktree':
        base_ref = base_ref or 'HEAD'
        require(head_ref is None, 'worktree 模式不接受 --head')
        base = resolve_commit(project, base_ref)
        head = base
        files = worktree_files(project, base, excludes)
        resolved_head_ref = None
    else:
        require(base_ref is not None, 'commits 模式需要 --base')
        head_ref = head_ref or 'HEAD'
        base = resolve_commit(project, base_ref)
        head = resolve_commit(project, head_ref)
        files = []
        resolved_head_ref = head_ref
    snapshot = dict(
        version=SNAPSHOT_VERSION,
        mode=mode,
        project_root=project.as_posix(),
        base_ref=base_ref,
        head_ref=resolved_head_ref,
        base=base,
        head=head,
        excludes=sorted(excludes),
        files=files,
    )
    snapshot['snapshot_id'] = compute_snapshot_id(snapshot)
    return snapshot


def write_snapshot(directory, snapshot):
    path = Path(directory) / SNAPSHOT_NAME
    descriptor, temporary = tempfile.mkstemp(prefix='.snapshot-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(snapshot, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_snapshot(directory):
    path = Path(directory) / SNAPSHOT_NAME
    require(path.is_file(), f'缺少 {SNAPSHOT_NAME}；请先带 --mode 运行 init 或执行 snapshot')
    data = load_record(path)
    required = ('version', 'snapshot_id', 'mode', 'project_root', 'base_ref', 'head_ref',
                'base', 'head', 'excludes', 'files')
    fields(data, required, (), 'review snapshot')
    require(data['version'] == SNAPSHOT_VERSION, '不支持的 review-snapshot 版本')
    require(data['mode'] in ('worktree', 'commits'), 'review-snapshot mode 非法')
    require(SNAPSHOT_ID.fullmatch(data['snapshot_id']) is not None,
            'snapshot_id 必须为 sha256:<64 hex>')
    for key in ('project_root', 'base_ref', 'base', 'head'):
        text(data[key], f'review snapshot.{key}')
    if data['mode'] == 'worktree':
        require(data['head_ref'] is None, 'worktree 模式的 head_ref 必须为 null')
    else:
        text(data['head_ref'], 'review snapshot.head_ref')
    for key in ('base', 'head'):
        require(GIT_OID.fullmatch(data[key]) is not None, f'review snapshot.{key} 非法')
    require(isinstance(data['excludes'], list), 'review snapshot.excludes 必须为数组')
    for value in data['excludes']:
        text(value, 'review snapshot.excludes')
        pure = PurePosixPath(value)
        require(not pure.is_absolute() and '..' not in pure.parts,
                'review snapshot.excludes 必须为项目相对路径')
    require(isinstance(data['files'], list), 'review snapshot.files 必须为数组')
    if data['mode'] == 'commits':
        require(data['files'] == [], 'commits 模式的 files 必须为空')
    seen = set()
    for item in data['files']:
        fields(item, ('path', 'sha256'), ('gitlink',), 'review snapshot.files')
        text(item['path'], 'review snapshot.files.path')
        pure = PurePosixPath(item['path'])
        require(not pure.is_absolute() and '..' not in pure.parts,
                'review snapshot.files.path 必须为项目相对路径')
        require(item['path'] not in seen, f'review snapshot.files 路径重复: {item["path"]}')
        seen.add(item['path'])
        require(item['sha256'] is None or (isinstance(item['sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', item['sha256']) is not None),
                'review snapshot.files.sha256 非法')
        if 'gitlink' in item:
            require(GIT_OID.fullmatch(item['gitlink']) is not None, 'review snapshot.files.gitlink 非法')
    require(compute_snapshot_id(data) == data['snapshot_id'],
            'review-snapshot 的 snapshot_id 与内容不一致')
    return data


def verify_review_snapshot(directory, project):
    old = read_snapshot(directory)
    project = Path(project).resolve()
    require(Path(old['project_root']).resolve() == project,
            'review-snapshot 的 project_root 与当前项目不一致')
    if old['mode'] == 'commits':
        base = resolve_commit(project, old['base_ref'])
        head = resolve_commit(project, old['head_ref'])
        if base != old['base'] or head != old['head']:
            raise StaleReview(f'审查目标已移动: base {old["base"]} -> {base}, head {old["head"]} -> {head}')
        return old
    base = resolve_commit(project, old['base_ref'])
    if base != old['base']:
        raise StaleReview(f'审查 base 已移动: {old["base"]} -> {base}')
    files = worktree_files(project, old['base'], old['excludes'])
    before = {item['path']: canonical_file(item) for item in old['files']}
    after = {item['path']: canonical_file(item) for item in files}
    changed = [path for path in sorted(set(before) | set(after)) if before.get(path) != after.get(path)]
    if changed:
        shown = ', '.join(changed[:10])
        more = f' 等 {len(changed)} 个文件' if len(changed) > 10 else ''
        raise StaleReview(f'已审查源码发生变化: {shown}{more}')
    return old


def remint_snapshot(directory, project, configuration, mode=None, base=None, head=None):
    directory = Path(directory)
    old = read_snapshot(directory) if (directory / SNAPSHOT_NAME).is_file() else None
    if old is not None:
        mode = mode or old['mode']
        # Inherit refs only when the mode is unchanged; a commits run's head_ref
        # is not valid in worktree mode. After a mode switch, defaults apply.
        if mode == old['mode']:
            # Worktree remint keeps the original base commit so committed fixes stay in scope.
            base = base or (old['base'] if mode == 'worktree' else old['base_ref'])
            head = head or old['head_ref']
        excludes = old['excludes']
    else:
        require(mode is not None, '缺少 --mode；旧 run 重铸快照需要指定 worktree 或 commits')
        policy = runtime_config(project, configuration)
        skill_root = Path(__file__).resolve().parents[1]
        excludes = snapshot_excludes(project, policy['output_dir'], skill_root)
    snapshot = build_snapshot(project, mode, base, head, excludes)
    write_snapshot(directory, snapshot)
    return snapshot


def init_review(project, configuration, slug, mode=None, base=None, head=None):
    require(NAME.fullmatch(slug) is not None and slug not in ('.', '..'), 'invalid slug')
    policy = runtime_config(project, configuration)
    root = Path(policy['output_dir'])
    require(not list((root / 'archive').glob('*/' + slug)), 'slug already archived: ' + slug)
    events = root / 'workflow-events.log'
    if events.exists():
        require(not any(len(row.split('\t')) > 2 and row.split('\t')[2] == slug
                        for row in events.read_text(encoding='utf-8').splitlines()), 'slug already has events: ' + slug)
    directory = root / 'active' / slug
    snapshot = None
    if mode is not None:
        skill_root = Path(__file__).resolve().parents[1]
        excludes = snapshot_excludes(project, policy['output_dir'], skill_root)
        snapshot = build_snapshot(project, mode, base, head, excludes)
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()  # Exclusive creation: a new run must never reuse existing output.
    (directory / 'probes').mkdir()
    template = LABELS_PATH.parent / 'code-review.md'
    content = template.read_text(encoding='utf-8').replace('{line_target}', str(policy['line_target']))
    content = content.replace('{branch_target}', str(policy['branch_target']))
    (directory / 'code-review.md').write_text(content, encoding='utf-8')
    (directory / 'policy.json').write_text(json.dumps(policy, indent=2), encoding='utf-8')
    if snapshot is not None:
        write_snapshot(directory, snapshot)
    result = dict(review_dir=directory.as_posix(), **policy)
    if snapshot is not None:
        result['snapshot_id'] = snapshot['snapshot_id']
    print(json.dumps(result))


class UniqueLoader(yaml.SafeLoader):
    pass


def yaml_mapping(loader, node):
    return unique_object(loader.construct_pairs(node, deep=True))


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, yaml_mapping)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label} 必须为非空字符串')
    return value


def fields(value, required, optional, label):
    require(isinstance(value, dict), f'{label} 必须为对象')
    require(set(required) <= value.keys(), f'{label} 缺少字段: {set(required) - value.keys()}')
    require(value.keys() <= set(required) | set(optional), f'{label} 含未知字段: {value.keys() - set(required) - set(optional)}')


def load_record(path):
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f'非法 JSON 数值: {value}')))


def registry(path):
    data = yaml.load(path.read_text(encoding='utf-8-sig'), Loader=UniqueLoader)
    require(isinstance(data, dict) and isinstance(data.get('probes'), list) and data['probes'], '注册表缺少 probes 清单')
    probes = {}
    for item in data['probes']:
        require(isinstance(item, dict), '探针配置必须为对象')
        name = text(item.get('name'), '探针 name')
        require(NAME.fullmatch(name) is not None and name not in probes, f'非法或重复探针名: {name}')
        require(type(item.get('required')) is bool, f'{name}: required 必须为布尔值')
        probes[name] = item['required']
    return probes


def finding(item, probe):
    required = ('id', 'probe', 'severity', 'status', 'location', 'summary', 'evidence')
    optional = ('repro', 'reconciled_by', 'reconcile_commit')
    fields(item, required, optional, 'finding')
    for key in item:
        text(item[key], f'finding.{key}')
    require(item['probe'] == probe, f"{item['id']}: probe 不匹配")
    pattern = re.escape(probe) + r'-[1-9][0-9]*'
    require(re.fullmatch(pattern, item['id']) is not None, f"非法 finding ID: {item['id']}")
    require(item['severity'] in SEVERITIES, f"{item['id']}: 非法 severity")
    require(item['status'] in STATUSES, f"{item['id']}: 非法 status")
    require(item['status'] != 'wontfix' or item['severity'] in ('medium', 'low'), f"{item['id']}: 严重问题不得 wontfix")
    if item['status'] == 'reconciled':
        text(item.get('reconciled_by'), f"{item['id']}.reconciled_by")
    return deepcopy(item)


def read_probes(directory, configuration):
    probe_dir = directory / 'probes'
    expected = {name + '.json' for name in configuration}
    actual = {p.name for p in probe_dir.glob('*.json')}
    require(actual == expected, f'探针报告清单不匹配: 缺少 {expected - actual}; 未注册 {actual - expected}')
    summaries, findings, unverified_items = [], {}, []
    for name, required in configuration.items():
        block = load_record(probe_dir / (name + '.json'))
        fields(block, ('probe', 'status', 'findings'), ('duration', 'reason', 'unverified_items'), name)
        require(block['probe'] == name, f'{name}: 报告 probe 不匹配')
        require(block['status'] in ('passed', 'failed', 'skipped', 'error'), f'{name}: 非法执行状态')
        duration = block.get('duration', 0)
        require(type(duration) is int and duration >= 0, f'{name}: duration 必须为非负整数秒')
        require(isinstance(block['findings'], list), f'{name}: findings 必须为数组')
        if block['status'] in ('skipped', 'error'):
            text(block.get('reason'), f'{name}.reason')
        elif 'reason' in block:
            text(block['reason'], f'{name}.reason')
        pending_items = block.get('unverified_items', [])
        require(isinstance(pending_items, list), f'{name}: unverified_items 必须为数组')
        for item in pending_items:
            keys = ('location', 'summary', 'reason', 'needed_evidence')
            fields(item, keys, (), f'{name}.unverified_items')
            for key in keys:
                text(item[key], f'{name}.unverified_items.{key}')
            unverified_items.append(dict(probe=name, **deepcopy(item)))
        counts = Counter()
        open_high = 0
        for raw in block['findings']:
            item = finding(raw, name)
            require(item['id'] not in findings, f"重复 finding ID: {item['id']}")
            findings[item['id']] = item
            counts[item['severity']] += 1
            open_high += item['severity'] == 'high' and item['status'] == 'open'
        require(block['status'] != 'skipped' or not block['findings'], f'{name}: skipped 不能带 finding')
        require(block['status'] != 'passed' or not open_high, f'{name}: passed 与 open high 矛盾')
        require(block['status'] != 'failed' or open_high, f'{name}: failed 缺少 open high')
        summaries.append(dict(name=name, required=required, status=block['status'], duration=duration, reason=block.get('reason', ''),
                              **{severity: counts[severity] for severity in SEVERITIES}))
    return summaries, findings, unverified_items


def summarize(directory, configuration, probes_only=False):
    probes, findings, unverified_items = read_probes(directory, registry(configuration))
    reconciliation = None
    if not probes_only:
        severe = [item for item in findings.values() if item['severity'] == 'high']
        done = sum(item['status'] in ('reconciled', 'false-positive') for item in severe)
        reconciliation = dict(total=len(severe), done=done, pending=len(severe) - done)
    return dict(probes=probes, reconcile=reconciliation, findings=list(findings.values()),
                unverified_items=unverified_items)


def markdown(value):
    """Render record text literally, including pipes, newlines, and code fragments."""
    value = html.escape(str(value), quote=False)
    value = re.sub(r'([\\`*_\[\]|#!])', r'\\\1', value)
    return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def render_sections(summary, labels, policy=None):
    rows = [labels['probe_table_header'], labels['probe_table_separator']]
    for p in summary['probes']:
        status = labels['status_' + p['status']]
        rows.append('| ' + ' | '.join(markdown(value) for value in
                    (p['name'], labels['required_yes'] if p['required'] else labels['required_no'],
                     status, p['duration'], p['high'], p['medium'], p['low'], p['reason'])) + ' |')
    rows += ['', labels['findings_heading'], '']
    for item in summary['findings']:
        status = labels['finding_status_' + item['status'].replace('-', '_')]
        title, _, description = item['summary'].replace('\r\n', '\n').replace('\r', '\n').partition('\n')
        rows += [f"#### [{item['severity']}] {markdown(title)}", '']
        if description.strip():
            rows += [markdown(description), '']
        rows += [
                 labels['finding_id'] + markdown(item['id']),
                 labels['finding_location'] + markdown(item['location']),
                 labels['finding_status'] + status + labels['finding_status_suffix'].format(status=item['status'])]
        if item.get('reconciled_by'):
            rows.append(labels['finding_reconciled_by'] + markdown(item['reconciled_by']))
        rows += ['', '<details>', '<summary>' + html.escape(labels['finding_evidence']) + '</summary>', '',
                 markdown(item['evidence']), '', '</details>', '']
    for item in summary['unverified_items']:
        title, _, description = item['summary'].replace('\r\n', '\n').replace('\r', '\n').partition('\n')
        rows += [f"#### [{labels['unverified_status']}] {markdown(title)}", '']
        if description.strip():
            rows += [markdown(description), '']
        rows += [
            labels['unverified_probe'] + markdown(item['probe']),
            labels['finding_location'] + markdown(item['location']),
            labels['unverified_reason'] + markdown(item['reason']),
            labels['unverified_needed_evidence'] + markdown(item['needed_evidence']), '',
        ]
    if not summary['findings'] and not summary['unverified_items']:
        rows.append(labels['no_findings'])
    r = summary['reconcile']
    rows += ['', labels['reconcile_line'].format(**r)]
    failed = [p['name'] for p in summary['probes'] if p['required'] and p['status'] in ('failed', 'error')]
    gate = labels['gate_prefix'] + (labels['gate_blocked'] if r['pending'] or failed else labels['gate_clear'])
    gate += labels['gate_detail'].format(pending=r['pending'], failed=len(failed))
    gate += '\n\n' + labels['gate_footer']
    if policy is not None:
        gate += '\n\n' + labels['coverage_policy'].format(**policy)
    return dict(probes='\n'.join(rows).strip(), gate=gate)


def summary_text(summary, labels):
    """Canonical delivery summary derived only from validated JSON records."""
    findings = summary['findings']
    by_severity = {
        severity: [item['id'] for item in findings if item['severity'] == severity]
        for severity in SEVERITIES
    }
    required_failed = [
        probe['name'] for probe in summary['probes']
        if probe['required'] and probe['status'] in ('failed', 'error')
    ]
    reconcile = summary['reconcile']
    blocked = bool(reconcile['pending'] or required_failed)
    lines = [
        labels['summary_heading'],
        labels['summary_findings'].format(
            **{severity: len(by_severity[severity]) for severity in SEVERITIES}),
        labels['summary_high_ids'] + (', '.join(by_severity['high']) or '-'),
        labels['summary_medium_ids'] + (', '.join(by_severity['medium']) or '-'),
        labels['summary_low_ids'] + (', '.join(by_severity['low']) or '-'),
        labels['summary_unverified'].format(count=len(summary['unverified_items'])),
        labels['summary_reconcile'].format(**reconcile),
        labels['summary_required_failed'] + (', '.join(required_failed) or labels['summary_none']),
        labels['summary_status'] + (labels['summary_blocked'] if blocked else labels['summary_clear']),
    ]
    return '\n'.join(lines)


def update_report(directory, sections, check=False):
    path = directory / 'code-review.md'
    with path.open(encoding='utf-8-sig', newline='') as stream:
        raw = stream.read()
    newline = '\r\n' if '\r\n' in raw else '\n'
    source = raw.replace('\r\n', '\n')
    require(not re.search(r'^```json probe-result\b', source, re.M),
            '原始记录须保存为独立 JSON，最终报告不得嵌入机器记录区块')
    require('<!-- code-review:reviewer:start -->' not in source
            and '<!-- code-review:reviewer:end -->' not in source
            and re.search(r'^```json reviewer-result', source, re.M) is None,
            '报告仍包含旧版 Reviewer 区域；reviewer 功能已移除，请迁移或删除该区域后重新渲染')
    updated = source
    for name, content in sections.items():
        begin, end = f'<!-- code-review:{name}:start -->', f'<!-- code-review:{name}:end -->'
        require(source.count(begin) == source.count(end) == 1, f'{name}: 自动区域标记缺失或重复')
        pattern = re.compile(re.escape(begin) + r'\n.*?\n' + re.escape(end), re.S)
        require(pattern.search(updated) is not None, f'{name}: 自动区域标记顺序错误')
        updated = pattern.sub(lambda _: begin + '\n' + content + '\n' + end, updated, count=1)
    if check:
        require(source == updated, '报告自动区域与原始记录不一致，请重新渲染')
        return
    # Validate all input and all markers before touching the report; replace atomically.
    descriptor, temporary = tempfile.mkstemp(prefix='.code-review-', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            stream.write(updated.replace('\n', newline))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def events(summary):
    rows = []
    for probe in summary['probes']:
        for key in ('status', 'required', 'duration', 'high', 'low', 'medium'):
            value = str(probe[key]).lower() if type(probe[key]) is bool else str(probe[key])
            rows.append('\t'.join((probe['name'], 'metric:probe', key, value)))
    if summary['reconcile'] is not None:
        for key in ('total', 'done'):
            rows.append(f"-\tmetric:reconcile\t{key}\t{summary['reconcile'][key]}")
    return '\n'.join(rows)


def main():
    # Native Windows Python otherwise emits CRLF, which would enter Bash metric values.
    sys.stdout.reconfigure(newline='\n')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--project-root', type=Path)
    parser.add_argument('--runtime-config', action='store_true')
    parser.add_argument('--init-review')
    parser.add_argument('--mode', choices=('worktree', 'commits'))
    parser.add_argument('--base')
    parser.add_argument('--head')
    parser.add_argument('--probes', action='store_true', help='Validate probe reports without claiming reconciliation')
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--events', action='store_true')
    output.add_argument('--has-high', action='store_true')
    output.add_argument('--render', action='store_true', help='Preview generated report sections')
    output.add_argument('--write-report', action='store_true', help='Replace generated report regions only')
    output.add_argument('--check-report', action='store_true', help='Verify every generated field without writing')
    output.add_argument('--summary', action='store_true', help='Print the canonical delivery summary from validated JSON')
    output.add_argument('--snapshot', action='store_true', help='Create or refresh review-snapshot.json')
    output.add_argument('--verify-snapshot', action='store_true', help='Verify the reviewed source still matches review-snapshot.json')
    args = parser.parse_args()
    try:
        if args.runtime_config or args.init_review:
            require(args.project_root is not None, 'project root required')
            if args.init_review:
                init_review(args.project_root, args.registry, args.init_review,
                            args.mode, args.base, args.head)
            else:
                policy = runtime_config(args.project_root, args.registry)
                print('{output_dir}\t{line_target}\t{branch_target}'.format(**policy))
            return 0
        require(args.review_dir is not None, 'review directory required')
        if args.verify_snapshot:
            require(args.project_root is not None, 'project root required')
            snapshot = verify_review_snapshot(args.review_dir, args.project_root)
            print(f'快照校验通过: {snapshot["snapshot_id"]}')
            return 0
        if args.snapshot:
            require(args.project_root is not None, 'project root required')
            snapshot = remint_snapshot(args.review_dir, args.project_root, args.registry,
                                       args.mode, args.base, args.head)
            print(json.dumps(dict(review_dir=args.review_dir.as_posix(),
                                  snapshot_id=snapshot['snapshot_id'])))
            return 0
        labels = load_labels()
        summary = summarize(args.review_dir, args.registry, args.probes)
        if args.render or args.write_report or args.check_report:
            require(not args.probes, '渲染和展示校验需要最终同步结果')
            policy = runtime_config(args.project_root, args.registry) if args.project_root else None
            sections = render_sections(summary, labels, policy)
            if args.write_report or args.check_report:
                update_report(args.review_dir, sections, check=args.check_report)
        if args.summary:
            require(not args.probes, '摘要需要最终同步结果')
    except StaleReview as error:
        print(f'stale-review: {error}', file=sys.stderr)
        return 3
    except (ValueError, TypeError, OSError, yaml.YAMLError) as error:
        print(f'错误: {error}', file=sys.stderr)
        return 1
    if args.write_report or args.check_report:
        print('报告展示校验通过' if args.check_report else '已更新报告自动区域')
    elif args.render:
        print('\n\n'.join(sections.values()))
    elif args.events:
        print(events(summary))
    elif args.has_high:
        print(str(any(p['high'] for p in summary['probes'])).lower())
    elif args.summary:
        print(summary_text(summary, labels))
    else:
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
