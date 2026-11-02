# 双语 Code Review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本轮只交付计划，不执行下列任务。

**Goal:** 在同一仓库提供可独立安装的英文、中文 code-review skill，保持审查语义、机器协议和门禁行为一致。

**Architecture:** `skills/code-review/` 为默认英文版，`skills/code-review-zh/` 为中文版。四个运行脚本只在 `shared/scripts/` 维护，同步生成到两套安装目录并提交生成文件，使现有按目录安装的方式无需构建即可使用。说明文档和报告文案按语言维护，机器字段与判定逻辑共享。

**Tech Stack:** Python 3.9+、PyYAML、Bash、Git、unittest、GitHub Actions；不增加运行时依赖。

**Spec:** 本文件“设计范围与约定”记录已讨论的双语目录方案及实施边界，是后续任务的设计依据。

## 设计范围与约定

### 当前基线

- 计划分支：`codex/bilingual-skill-plan`，从 `codex/remove-reviewer` 的 `b791cdd` 创建。
- 当前 `skills/code-review/` 是中文版，含 4 个脚本；安装器固定复制该目录。
- `SKILL.md` 有上一轮未提交的交接说明。迁移时两种语言都须保留其语义；本计划不提交或覆盖这处修改。
- 当前 `sync-results.py` 自动报告和摘要固定使用中文；`rule-grep` 从中文检测模式标记抽取规则，并用启发式区分散文与正则。翻译可能改变运行行为，须有离线夹具保护。
- `docs/` 被 `.gitignore` 忽略；计划若需提交，只精确强制添加本文件，不更改整目录忽略策略。

### 目标目录及责任

```text
shared/scripts/                         # 唯一手工维护的运行脚本
  collect-metrics
  lib-metrics
  sync-results.py
  rule-grep
skills/code-review/                     # 英文，name: code-review
  SKILL.md
  references/{output-schema.md,probes.yaml,probes/,rules/}
  assets/{code-review.md,report-labels.json}
  scripts/                              # 同步生成，提交到 Git
skills/code-review-zh/                  # 中文，name: code-review-zh
  SKILL.md
  references/{output-schema.md,probes.yaml,probes/,rules/}
  assets/{code-review.md,report-labels.json}
  scripts/                              # 同步生成，提交到 Git
scripts/sync-skill-scripts.py            # 生成 / 检查脚本副本
scripts/check-skill-locales.py           # 检查双语包的结构与机器约定
scripts/{install.py,install-remote.py,install}
tests/
.github/workflows/skill-validation.yml
```

### Global Constraints

- 不新增 reviewer、探针、跨探针通信、去重、风险分类或自动修复。
- 不在本任务顺带修改覆盖率阈值、duration 缺失语义、定级和 HARD-GATE。
- 保留四探针并行、只读审查、源码版本隔离、检查限制交接与后台任务收尾约束。
- probe 名称、finding ID、JSON 字段、severity/status 枚举、事件键、命令和自动区域标记保持一致；skill 的安装名称允许区分语言。
- 英文 `SKILL.md` 的 `name` 为 `code-review`；中文为 `code-review-zh`。默认分别输出英文、中文报告，引用和代码证据保留原文，不翻译原始 JSON 中的事实。
- `shared/scripts/` 和两套生成脚本字节相同。运行脚本从各自安装目录定位规则和资源，不能依赖仓库的 `shared/`、绝对开发路径或符号链接。
- 默认安装英文；项目内只选一种语言。原安装的覆盖保护、dry-run 和 `--force` 备份语义保留，安装器不自动删除另一语言。
- Python 3.9+、PyYAML、Bash、Git 依赖不变，支持 Windows Git Bash 和 Linux。
- 不自动调用付费模型；结构检查、离线夹具和真实模型评测分别报告，不能将前两者称为召回验证。

### Review Focus

1. 仅复制一个 skill 到含空格、中文的项目路径，删除源仓库后仍能扫描、同步、渲染、校验、输出摘要及执行 gate；任务 1、5 验证。
2. 翻译改变规则抽取或将英文散文误当正则，导致候选丢失；任务 2 验证模式清单、候选及语义检查分流相同。
3. 英文生成文件遗漏或被手工改写，直接目录安装得到旧逻辑；任务 1 的 `--check` 与任务 5 CI 拒绝此状态。
4. 安装语言切换、重复安装或选错语言导致覆盖用户内容；任务 4 验证拒绝冲突、备份及 dry-run 无副作用。
5. 文案本地化改变计数、门禁、转义或报告校验，或自动翻译 finding 证据；任务 2、5 用相同机器记录验证结果不变及篡改仍被拒绝。

## Task 1: 建立共享脚本源和可独立安装的双包

**Files:**
- Create: `shared/scripts/`（迁入现有四个运行脚本）
- Create: `scripts/sync-skill-scripts.py`
- Create: `skills/code-review-zh/`（先完整保存当前中文包）
- Modify: `skills/code-review/scripts/`、`skills/code-review-zh/scripts/`（生成副本）
- Test: `tests/test_sync_skill_scripts.py`

**Interfaces:** `python scripts/sync-skill-scripts.py [--check]`。默认只将四个明确列出的源脚本同步到两个包；`--check` 只读，缺失、多余或内容不同均返回非零并列明路径。不得递归删除不明文件。两套包的脚本清单应严格相等，排除 `__pycache__`、`*.pyc`。

- [ ] 先写离线测试：同步后两目录与共享源逐字节一致；再次同步不改相同文件；单独篡改、删除和添加脚本时 `--check` 失败且不修正文件。
- [ ] 运行 `python -m unittest discover -s tests -p test_sync_skill_scripts.py -v`，确认新增测试因功能缺失失败。
- [ ] 保存完整中文包，迁入共享源并实现同步器；两套生成脚本前都不添加会破坏字节一致性的语言专用头。
- [ ] 同步并运行上述测试及 `python scripts/sync-skill-scripts.py --check`，确认通过；验证现有默认包仍可通过原有离线测试。
- [ ] 单独提交本任务，不提交无关工作区文件。

## Task 2: 让共享运行逻辑支持两种语言

**Files:**
- Modify: `shared/scripts/sync-results.py`、`shared/scripts/rule-grep`
- Create: 两套包的 `assets/report-labels.json`
- Test: `tests/test_localized_runtime.py`
- Modify: `tests/test_behavior_probe.py`、`tests/test_three_severities.py`（保留原断言强度，适配标签加载）

**Interfaces:**
- 两个 `report-labels.json` 使用同一键集合，分别提供 `language`（`en` / `zh-CN`）及自动报告、交付摘要所需固定文案。
- `sync-results.py` 从其所在安装包的 `assets/report-labels.json` 加载文案；只改变展示层，不改变 `summarize`、事件或原始 finding。资源缺失、重复键、非法语言或缺少标签时报错，不默认补齐中文。
- `rule-grep` 同时接受既有 `**检测模式**:` 和英文 `**Detection pattern**:` 标记。新增规则级 `**Detection mode**: semantic`，有此标记的规则转入不可机判说明，不执行其描述；两套内置规则均使用此显式标记表示散文项。未添加新标记的项目自带规则继续保留当前兼容行为。

- [ ] 先写双语夹具：clean / open high / medium / error 产生相同机器计数和阻塞状态，报告固定文案按包语言变化，finding 的 summary/evidence 原样保留。
- [ ] 写规则夹具：英文和中文检测标签能提取同一正则；英文散文明确标为 semantic 后不作为正则运行；既有项目规则保持可用；无效正则仍明确记录，不伪装为通过。
- [ ] 运行 `python -m unittest discover -s tests -p test_localized_runtime.py -v`，确认新增测试先失败。
- [ ] 实现本地化和显式语义分流，更新生成脚本。人类可读错误说明统一使用清晰英文即可，本轮不为所有 Bash 日志建立翻译系统；报告和机器摘要须完整本地化。
- [ ] 重跑上述测试和原有报告完整性测试。缺标签、重复 JSON 键、特殊字符、自动区篡改都须保持失败；不得删除原来的负例来迁就翻译。
- [ ] 单独提交本任务。

## Task 3: 翻译全部执行文档，并建立双语一致性检查

**Files:**
- Modify: `skills/code-review/SKILL.md`、`references/` 全部说明和规则、`assets/code-review.md`
- Modify: `skills/code-review-zh/SKILL.md`、`references/rules/` 中散文项的显式标记
- Create: `scripts/check-skill-locales.py`
- Test: `tests/test_skill_locales.py`

**Interfaces:** `python scripts/check-skill-locales.py` 只读检查以下结构约定：两包文档相对路径清单一致；frontmatter name 与目录匹配；四探针的 name/file/required/requires/params、执行模式和重派上限一致，title 和注释可翻译；规则 ID、规则级别及可执行正则逐项一致；报告自动标记数量和顺序一致。检查器不声称能验证自然语言语义等价。

- [ ] 先写夹具：缺少一份规则、变更 required、丢失规则 ID、改动正则或报告标记都失败；仅翻译说明、title 时通过。执行 `python -m unittest discover -s tests -p test_skill_locales.py -v` 确认先失败。
- [ ] 将默认包完整翻译为英文；中文版保留原语义，name 改为 `code-review-zh`，调用示例与之对应。两份入口都要求子代理按所选包语言交接报告信息。
- [ ] 逐项核对行为检查、契约冲突定级、测试证据不足、规则选择优先级、影响分析深度和全部阻塞条件，不能将翻译变成规则重写。
- [ ] 两套规则中的散文检测项使用任务 2 的 semantic 标记；真正正则保持字节相同，不能把带正则语义的字符串当普通文案翻译。
- [ ] 实现检查器并运行其测试、规则抽取对照和两套 skill validator。英文文件有中文引用或样例不直接判失败，人工确认其是否属于原始证据或合法测试输入。
- [ ] 单独提交本任务。

## Task 4: 为本地及远程安装器增加语言选择

**Files:**
- Modify: `scripts/install.py`、`scripts/install-remote.py`
- Verify: `scripts/install`（当前是透传包装器，不需要则不改）
- Modify: `tests/test_install.py`、`tests/test_install_remote.py`

**Interfaces:** 两个 Python 安装入口增加 `--lang {en,zh-CN}`，默认 `en`。英文源目录及目标末级名为 `code-review`，中文为 `code-review-zh`；宿主根目录仍为 `.agents/skills/` 或 `.claude/skills/`。远程入口将语言值显式透传给固定 ref 的安装器。

- [ ] 先添加测试：两语言 × 两宿主的源/目标匹配，`--agent both` 只安装所选语言，省略语言仍安装 `code-review`，非法语言无写入。
- [ ] 增加冲突用例：目标宿主已经安装另一语言时，拒绝并说明手动选择保留哪个；`--force` 只备份替换同名目标，不绕过另一语言并存检查。检查只针对所选宿主，不改动未选宿主。
- [ ] 覆盖已有中文版以 `code-review` 名称安装的升级：默认英文安装时，内容不同仍拒绝；显式 force 备份后替换，不猜测语言、不静默删除或搬迁旧安装。
- [ ] 为两种语言保留重复安装无写入、含空格项目路径、dry-run、JSON 输出、不修改宿主配置等既有用例。远程测试使用本地 Git 仓库和固定标签，不访问公网。
- [ ] 运行安装器测试确认新增断言先失败，再实现语言映射和参数透传，重跑直至通过。
- [ ] 单独提交本任务。

## Task 5: 接通发布检查、双语说明和离线端到端验证

**Files:**
- Modify: `tests/test_portable_installation.py`、`README.md`、`README.zh-CN.md`、`NEWS.md`
- Create: `.github/workflows/skill-validation.yml`
- Modify: 其他现有测试中确实依赖中文文案或包位置的夹具，不削弱对字段、计数和阻塞的检查。

**Interfaces:** 两套可安装目录必须已经完整提交，`npx skills add` 不负责运行本仓库生成器。CI 的 PR 和 push 检查只读，不自动改文件、提交或 push。现有 NEWS 自动更新流程不另行重构。

- [ ] 将可移植性测试扩展到两语言 × 两宿主；复制完整单包后，在无法访问源码目录的隔离夹具中执行 rule-grep、sync、render-report、verify-report、summary 和 gate-pass。
- [ ] 用同一套 clean/high/error/伪造报告夹具验证两语言：机器 JSON、计数、阻塞一致；原始证据不变；渲染保留人工正文，篡改后 verify/summary/gate 均不放行。
- [ ] CI 执行脚本同步检查、双语结构检查、原有全量 unittest、两套 validator、NEWS preview 检查；使用 Python 3.9 与一个当前项目支持版本的 Linux 矩阵，配备 Bash 和 PyYAML。Windows Git Bash 的实际验证单独记录，未运行不写通过。
- [ ] 更新两份 README 的安装与调用示例：英文 `--skill code-review`，中文 `--skill code-review-zh`；本地/远程 Python 安装示例展示 `--lang`。提醒同项目择一安装，第三方安装器并不受本仓库并存检查约束。
- [ ] 说明维护流程：只改 `shared/scripts/`，运行同步并提交两个生成副本；行为规则修改双语同步，PR 列出对应文件和人工语义复核结果。结构检查不能代替该复核。
- [ ] NEWS 增加双语入口和默认语言变化说明，不在计划阶段指定或擅自发布版本号，不更新召回宣传数字。
- [ ] 完成以下离线检查，按真实输出记录通过、跳过和环境失败；不将 skipped 当作通过：

```bash
python scripts/sync-skill-scripts.py --check
python scripts/check-skill-locales.py
python -m unittest discover -s tests -v
python scripts/sync-news.py --check
git diff --check
```

运行 Bash 用例前按现有测试约定设置 `CODE_REVIEW_TEST_BASH`。Windows 可使用 `E:/git/Git/bin/bash.exe`，解释器可用 `D:/anaconda3/python.exe -X utf8`。两套 validator 使用已安装 skill-creator 的 `scripts/quick_validate.py`，不将维护者机器的绝对路径写进产品。

- [ ] 单独提交本任务，给出全部变更、离线证据与尚未验证的事项；不自动合并、打 tag 或推送。

## Task 6: 双语真实执行对照（独立验收，获准后再运行）

**产物位置:** 忽略目录 `eval/bilingual-skill-runs/<日期>-<标识>/`，不进入发布包。

- [ ] 冻结两套包和相同被审 commit 区间，先选一个已确认缺陷和一个修复对照；执行者不能看到参考答案或历史报告。
- [ ] 使用相同实际模型、配置和四探针编排，每个“语言 × 案例”使用全新上下文；允许英文任务调用中文包、中文任务调用英文包时，报告默认语言仍遵循所选包，不额外做交叉矩阵。
- [ ] 分开记录目标机制命中、修复后停止上报、额外 finding 的证据、定级、未验证项、报告语言、墙钟与各项 token 用量。
- [ ] 将结果写为已知案例定向对照，不计入原盲测，不凭单轮差异宣称某语言更强或更省 token。
- [ ] 出现差异先核对翻译、实际模型和证据读取路径；只修有证据的偏差，不为追求同数值手工改写原始 JSON。

## 完成与验收边界

- 任务 1–5 完成才可称“双语打包和离线运行链路通过”。
- 任务 6 另行获准并完成后，才能报告该批案例的实际语言执行结果；即使通过，也不能称通用召回等价。
- 本计划不执行付费评测、不迁移真实用户安装、不合并 main、不提交或推送产品实现。
