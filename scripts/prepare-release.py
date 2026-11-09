#!/usr/bin/env python3
"""Prepare release documents from a CI-validated main history; never push or tag."""
import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
DOCS = {'NEWS.md', 'README.md', 'README.zh-CN.md'}


def helper(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args],
                                   text=True, encoding='utf-8').strip()


def release_section(news, tag):
    match = re.search(r'^## ' + re.escape(tag) + r' \([^\n]+\)\n.*?(?=^## |\Z)',
                      news, re.M | re.S)
    if not match:
        raise ValueError('missing release notes for ' + tag)
    return match.group(0).strip() + '\n'


def replace_once(text, pattern, replacement):
    text, count = re.subn(pattern, lambda _: replacement, text, flags=re.M)
    if count != 1:
        raise ValueError('missing or ambiguous README release marker: ' + pattern)
    return text


def prepare(repo, validated, notes):
    if not re.fullmatch(r'[0-9a-f]{40,64}', validated):
        raise ValueError('invalid validated commit SHA')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', validated, 'HEAD'], check=True)
    later = set(git(repo, 'diff', '--name-only', validated, 'HEAD', '--').splitlines())
    if later - DOCS:
        raise ValueError('unvalidated changes after successful CI: ' + ', '.join(sorted(later - DOCS)))
    if git(repo, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('tracked worktree changes must be committed first')
    version = (repo / 'VERSION').read_text(encoding='utf-8').strip()
    if not VERSION.fullmatch(version):
        raise ValueError('VERSION must be a stable version such as 0.1.1')
    tag = 'v' + version
    if git(repo, 'tag', '--list', tag):
        target = git(repo, 'rev-parse', tag + '^{commit}')
        subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', target, 'HEAD'], check=True)
        if git(repo, 'show', tag + ':VERSION') != version:
            raise ValueError('existing tag does not match VERSION')
        notes.write_text(release_section(git(repo, 'show', tag + ':NEWS.md'), tag), encoding='utf-8')
        return dict(tag=tag, prepared=False, target=target)
    stable = [tuple(map(int, t[1:].split('.'))) for t in
              git(repo, 'tag', '--merged', 'HEAD', '--list', 'v*').splitlines()
              if VERSION.fullmatch(t[1:])]
    if stable and tuple(map(int, version.split('.'))) <= max(stable):
        raise ValueError('VERSION must increase beyond the latest stable release')

    news_helper, sync_helper = helper('news-update'), helper('sync-news')
    contents = {name: (repo / name).read_text(encoding='utf-8') for name in DOCS}
    date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    block = news_helper.unreleased_block(repo, news_helper.latest_tag(repo), 'HEAD')
    released = block.split('\n', 2)[2].rsplit(news_helper.END, 1)[0].strip()
    section = '## ' + tag + ' (' + date + ')\n\n' + released + '\n'
    empty = (news_helper.START + '\n## Unreleased\n\n'
             '_No user-facing changes since the latest release._\n\n' + news_helper.END)
    news = news_helper.replace_block(contents['NEWS.md'], empty + '\n\n' + section)
    en = replace_once(contents['README.md'], r'The current stable release is `v[0-9.]+`',
                      'The current stable release is `' + tag + '`')
    en = replace_once(en, r'^`v[0-9.]+`(?= is )', '`' + tag + '`')
    en = en.replace('is the first stable release within the scope', 'is a stable release within the scope')
    en = sync_helper.synchronize(en, news)
    zh = replace_once(contents['README.zh-CN.md'], r'当前正式版本为 `v[0-9.]+`',
                      '当前正式版本为 `' + tag + '`')
    zh = replace_once(zh, r'^`v[0-9.]+`(?= 是)', '`' + tag + '`')
    zh = zh.replace('是下述适用范围内的首个正式版本', '是下述适用范围内的正式版本')
    zh = replace_once(zh, r'^## 最新动态\n[\s\S]*?(?=^## 发布状态)',
                      '## 最新动态\n\n### ' + tag + '（' + date + '）\n\n'
                      '本版本更新根据提交记录自动整理，详见 [NEWS](NEWS.md) 和 '
                      '[Release](https://github.com/kyy-logs/code-review-gate-skill/releases/tag/' + tag + ')。\n\n')
    # Validate every document before writing any tracked file.
    for name, text in {'NEWS.md': news, 'README.md': en, 'README.zh-CN.md': zh}.items():
        (repo / name).write_text(text, encoding='utf-8')
    notes.write_text(section, encoding='utf-8')
    return dict(tag=tag, prepared=True, target=git(repo, 'rev-parse', 'HEAD'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--validated-sha', required=True)
    parser.add_argument('--notes', type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = prepare(args.repo.resolve(), args.validated_sha, args.notes.resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print('prepare-release: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(plan))
    return 0


if __name__ == '__main__':
    sys.exit(main())
