#!/usr/bin/env python3
"""Validate review JSON records, derive metrics, and render a human Markdown report."""

import argparse
from collections import Counter
from copy import deepcopy
import json
import html
import os
from pathlib import Path
import re
import sys
import tempfile

import yaml


SEVERITIES = ('high', 'medium', 'low')
STATUSES = ('open', 'reconciled', 'wontfix', 'false-positive')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'重复字段: {key}')
        result[key] = value
    return result


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
    summaries, findings = [], {}
    for name, required in configuration.items():
        block = load_record(probe_dir / (name + '.json'))
        fields(block, ('probe', 'status', 'findings'), ('duration', 'reason'), name)
        require(block['probe'] == name, f'{name}: 报告 probe 不匹配')
        require(block['status'] in ('passed', 'failed', 'skipped', 'error'), f'{name}: 非法执行状态')
        duration = block.get('duration', 0)
        require(type(duration) is int and duration >= 0, f'{name}: duration 必须为非负整数秒')
        require(isinstance(block['findings'], list), f'{name}: findings 必须为数组')
        if block['status'] in ('skipped', 'error'):
            text(block.get('reason'), f'{name}.reason')
        elif 'reason' in block:
            text(block['reason'], f'{name}.reason')
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
    return summaries, findings


def summarize(directory, configuration, probes_only=False):
    probes, findings = read_probes(directory, registry(configuration))
    reconciliation = None
    if not probes_only:
        severe = [item for item in findings.values() if item['severity'] == 'high']
        done = sum(item['status'] in ('reconciled', 'false-positive') for item in severe)
        reconciliation = dict(total=len(severe), done=done, pending=len(severe) - done)
    return dict(probes=probes, reconcile=reconciliation, findings=list(findings.values()))


def markdown(value):
    """Render record text literally, including pipes, newlines, and code fragments."""
    value = html.escape(str(value), quote=False)
    value = re.sub(r'([\\`*_\[\]|#!])', r'\\\1', value)
    return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def render_sections(summary):
    rows = ['| 探针 | required | 状态 | 耗时（秒） | high | medium | low | 说明 |',
            '|---|---|---|---|---|---|---|---|']
    for p in summary['probes']:
        status = {'passed': '通过', 'failed': '发现阻塞问题', 'error': '执行错误', 'skipped': '跳过'}[p['status']]
        rows.append('| ' + ' | '.join(markdown(value) for value in
                    (p['name'], '是' if p['required'] else '否', status, p['duration'],
                     p['high'], p['medium'], p['low'], p['reason'])) + ' |')
    rows += ['', '### 问题详情', '']
    for item in summary['findings']:
        rows += [f"#### [{item['severity']}] {markdown(item['summary'])}", '',
                 f"- 问题 ID：{markdown(item['id'])}",
                 f"- 位置：{markdown(item['location'])}",
                 f"- 状态：" + {'open': '待处理', 'reconciled': '已处置', 'wontfix': '明确不修', 'false-positive': '误报'}[item['status']] + f"（{item['status']}）",
                 f"- 原始证据：{markdown(item['evidence'])}"]
        if item.get('reconciled_by'):
            rows.append(f"- 处理说明：{markdown(item['reconciled_by'])}")
        rows.append('')
    if not summary['findings']:
        rows.append('本轮没有记录 finding。')
    r = summary['reconcile']
    rows += ['', f"reconciliation：total={r['total']} / done={r['done']} / pending={r['pending']}"]
    failed = [p['name'] for p in summary['probes'] if p['required'] and p['status'] in ('failed', 'error')]
    gate = '问题与探针状态：' + ('**阻塞**' if r['pending'] or failed else '**无已记录阻塞项**')
    gate += f"。待处理严重问题 {r['pending']} 条；required 探针失败或错误 {len(failed)} 个。"
    gate += '\n\n此结果不代表验收、覆盖率、测试或 CI 等其他条件已全部满足。'
    return dict(probes='\n'.join(rows).strip(), gate=gate)


def summary_text(summary):
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
        '审查摘要（来自 JSON）',
        'findings: high={high} medium={medium} low={low}'.format(
            **{severity: len(by_severity[severity]) for severity in SEVERITIES}),
        'high_ids: ' + (', '.join(by_severity['high']) or '-'),
        'medium_ids: ' + (', '.join(by_severity['medium']) or '-'),
        'low_ids: ' + (', '.join(by_severity['low']) or '-'),
        'reconcile: total={total} done={done} pending={pending}'.format(**reconcile),
        'required_failed: ' + (', '.join(required_failed) or 'none'),
        'status: ' + ('阻塞' if blocked else '无已记录阻塞项'),
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
    parser.add_argument('--review-dir', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--probes', action='store_true', help='Validate probe reports without claiming reconciliation')
    output = parser.add_mutually_exclusive_group()
    output.add_argument('--events', action='store_true')
    output.add_argument('--has-high', action='store_true')
    output.add_argument('--render', action='store_true', help='Preview generated report sections')
    output.add_argument('--write-report', action='store_true', help='Replace generated report regions only')
    output.add_argument('--check-report', action='store_true', help='Verify every generated field without writing')
    output.add_argument('--summary', action='store_true', help='Print the canonical delivery summary from validated JSON')
    args = parser.parse_args()
    try:
        summary = summarize(args.review_dir, args.registry, args.probes)
        if args.render or args.write_report or args.check_report:
            require(not args.probes, '渲染和展示校验需要最终同步结果')
            sections = render_sections(summary)
            if args.write_report or args.check_report:
                update_report(args.review_dir, sections, check=args.check_report)
        if args.summary:
            require(not args.probes, '摘要需要最终同步结果')
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
        print(summary_text(summary))
    else:
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
