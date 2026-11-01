#!/usr/bin/env python3
"""Check structural consistency between the English and Chinese skill packages.

This verifies machine contracts only: file inventory, frontmatter names, probe
registry fields, rule IDs/levels/patterns, report markers, and label keys. It
does not claim natural-language semantic equivalence.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


PACKAGES = (
    ('en', Path('skills/code-review')),
    ('zh-CN', Path('skills/code-review-zh')),
)
PROBE_FIELDS = ('name', 'file', 'required', 'requires', 'params')
RULE_HEADING = re.compile(r'^### ([A-Za-z][A-Za-z0-9._-]*) \[(HIGH|MEDIUM|LOW)\]', re.M)
MARKER = re.compile(r'<!-- code-review:([A-Za-z0-9_-]+):start -->')
PATTERN = re.compile(r'`([^`]+)`')


def files(root, relative):
    base = root / relative
    result = set()
    for path in base.rglob('*'):
        if not path.is_file():
            continue
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        result.add(path.relative_to(base).as_posix())
    return result


def frontmatter_name(path):
    text = path.read_text(encoding='utf-8-sig')
    match = re.match(r'^---\n(.*?)\n---', text, re.S)
    if not match:
        raise ValueError('missing frontmatter: ' + str(path))
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict) or not isinstance(data.get('name'), str):
        raise ValueError('frontmatter name missing: ' + str(path))
    return data['name']


def probes(path):
    data = yaml.safe_load(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or not isinstance(data.get('probes'), list):
        raise ValueError('invalid probes registry: ' + str(path))
    result = []
    for item in data['probes']:
        if not isinstance(item, dict):
            raise ValueError('invalid probe entry: ' + str(path))
        result.append({field: item.get(field) for field in PROBE_FIELDS})
    return data.get('execution'), result


def rule_contract(path):
    text = path.read_text(encoding='utf-8-sig')
    headings = list(RULE_HEADING.finditer(text))
    result = []
    for index, match in enumerate(headings):
        block = text[match.end():headings[index + 1].start() if index + 1 < len(headings) else len(text)]
        patterns = []
        in_patterns = False
        for line in block.splitlines():
            if line.startswith('**检测模式**') or line.startswith('**Detection pattern**'):
                in_patterns = True
                patterns.extend(PATTERN.findall(line))
                continue
            if in_patterns and line.startswith('**'):
                in_patterns = False
            if in_patterns:
                patterns.extend(PATTERN.findall(line))
        result.append((match.group(1), match.group(2), tuple(patterns)))
    return result


def rule_files(root, relative):
    base = root / relative / 'references/rules'
    return {path.relative_to(base).as_posix(): path for path in base.glob('*.md')}


def markers(path):
    return MARKER.findall(path.read_text(encoding='utf-8-sig'))


def labels(path):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('invalid report labels: ' + str(path))
    return data.get('language'), frozenset(data.keys())


def check(root):
    errors = []
    inventories = {}
    for lang, relative in PACKAGES:
        inventories[lang] = files(root, relative)
    if inventories['en'] != inventories['zh-CN']:
        errors.append('file inventory differs: ' + str(sorted(inventories['en'] ^ inventories['zh-CN'])))

    for lang, relative in PACKAGES:
        package = root / relative
        expected_name = 'code-review-zh' if lang == 'zh-CN' else 'code-review'
        try:
            actual_name = frontmatter_name(package / 'SKILL.md')
            if actual_name != expected_name:
                errors.append(lang + ': frontmatter name is ' + actual_name + ', expected ' + expected_name)
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(lang + ': ' + str(error))

    try:
        en_exec, en_probes = probes(root / PACKAGES[0][1] / 'references/probes.yaml')
        zh_exec, zh_probes = probes(root / PACKAGES[1][1] / 'references/probes.yaml')
        if en_exec != zh_exec:
            errors.append('execution settings differ')
        if en_probes != zh_probes:
            errors.append('probe registry fields differ (name/file/required/requires/params)')
    except (OSError, ValueError, yaml.YAMLError) as error:
        errors.append('probe registry: ' + str(error))

    try:
        en_rules = rule_files(root, PACKAGES[0][1])
        zh_rules = rule_files(root, PACKAGES[1][1])
        if set(en_rules) != set(zh_rules):
            errors.append('rule file inventory differs')
        for name in sorted(set(en_rules) & set(zh_rules)):
            if rule_contract(en_rules[name]) != rule_contract(zh_rules[name]):
                errors.append('rule contract differs: references/rules/' + name)
    except (OSError, ValueError) as error:
        errors.append('rules: ' + str(error))

    try:
        en_markers = markers(root / PACKAGES[0][1] / 'assets/code-review.md')
        zh_markers = markers(root / PACKAGES[1][1] / 'assets/code-review.md')
        if en_markers != zh_markers:
            errors.append('report marker order differs')
    except OSError as error:
        errors.append('report markers: ' + str(error))

    try:
        en_lang, en_keys = labels(root / PACKAGES[0][1] / 'assets/report-labels.json')
        zh_lang, zh_keys = labels(root / PACKAGES[1][1] / 'assets/report-labels.json')
        if en_lang != 'en' or zh_lang != 'zh-CN':
            errors.append('report label languages differ from package languages')
        if en_keys != zh_keys:
            errors.append('report label key sets differ')
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append('report labels: ' + str(error))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = check(args.root.resolve())
    if errors:
        for error in errors:
            print('error: ' + error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
