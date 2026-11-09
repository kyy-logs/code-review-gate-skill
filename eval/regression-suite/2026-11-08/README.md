# code-review 行为回归集（2026-11-08）

这是模型回归集的 v0 案例清单，不是全量测试套件。

## 包含

6 个行为/对照案例：

- `spring-ai-alibaba-869`
- `spring-ai-alibaba-903`
- `dbeaver-38915`
- `x04`
- `c04`（修复对照）
- `dbeaver-37564`

另有 1 个 **clean control 缺失**。c04 是“A 已修复、B 仍存在”的修复对照，不等于完全无 finding 的干净对照。

## 当前证据状态

| 案例 | 状态 |
|---|---|
| 869 / 903 | 历史结果仍为严格 0/3；使用旧 skill，不能复用为当前版本结论 |
| dbeaver-38915 | snapshot-only 分支目标 2 命中 medium；common/完整分支曾只到 unverified |
| x04 | 窄搜索规则证据 A high / B medium；common-only 版本曾丢失 A |
| c04 | snapshot-only 分支 A 不重报、B 命中 |
| dbeaver-37564 | 窄搜索规则证据资源泄漏命中；目标 1 仍是已知缺口 |
| clean-control | **缺失，待补** |

`SUITE.json` 保存了每个案例的来源运行、目标检查路径和输入文件哈希。

## 使用规则

- 每次运行必须冻结自己的 skill tree hash；
- 不把历史运行的输出当成当前版本结论；
- 模型输出不按文字相似度断言，按目标检查判定；
- 目标外 finding 单独记录，用来观察误报；
- 关键案例发布前建议至少 2/3 命中；
- 耗时单独记录，不作为硬失败阈值。

详细流程见 `PROTOCOL.md`。

## 下一步

1. 补一个真正的 clean control；
2. 在同一个冻结 skill 上跑这 6 个案例，形成第一版可复用 baseline；
3. 再用 `eval-baseline.py` 记录 tree hash 和可复用运行。
