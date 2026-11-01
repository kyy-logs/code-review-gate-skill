# 探针输出契约（finding）

本文件统一定义 finding 字段、严重级别、处理状态及探针执行状态，供各探针填写独立 JSON 时使用。
finding 是一条具体问题；`severity` 表示严重程度，finding 的 `status` 表示处理进度，探针状态表示一轮检查的执行结果。

## 1. 单条问题怎么写

| 字段 | 填写要求 | 取值 | 说明 |
|---|---|---|---|
| `id` | 必填 | `<probe>-<序号>` | 全局唯一，序号从 1 开始，**必须稳定** |
| `probe` | 必填 | 探针名 | 探针名取自 `references/probes.yaml` |
| `severity` | 必填 | `high` / `medium` / `low` | 见下方判定表 |
| `status` | 必填 | `open` / `reconciled` / `wontfix` / `false-positive` | 见下方状态机 |
| `location` | 必填 | `path:line` | 定位不到行时写到文件级，并说明原因 |
| `summary` | 必填 | 一句话 | 说**是什么问题**，不是「建议优化」这类空话 |
| `evidence` | 必填 | 具体依据 | 引用规则 ID / 接口契约 / 代码路径 / 测试输出。**没有依据的不算 finding** |
| `repro` | 选填 | 复核命令 | 如 `grep -n 'formatCents' src/…/Calculator.java`、`git show <head>:<path>`。仅限读取证据的命令，不得构建或运行测试 |
| `reconciled_by` | 条件必填 | 处理说明 | `status=reconciled` 时填写：改在哪、为什么这样改 |
| `reconcile_commit` | 选填 | commit id | 有对应处理提交时填写 |

未提供的选填字段及不适用的条件字段可以省略，不必填写空字段。

每个探针将本轮记录保存为独立的 `probes/<探针名>.json`。例如：

```json
{
  "probe": "test-coverage",
  "status": "failed",
  "duration": 12,
  "findings": [{
    "id": "test-coverage-1",
    "probe": "test-coverage",
    "severity": "high",
    "status": "open",
    "location": "src/main/java/com/example/Calculator.java:137",
    "summary": "增量行覆盖率 60%，低于 85% 基线",
    "evidence": "报告与目标版本一致；5 行改动可执行生产代码中覆盖 3 行，3/5 = 60%"
  }]
}
```

`probe`、`status`、`findings` 必填；`duration` 为非负整数秒，可省略，省略记 0。
`skipped` / `error` 须另填非空 `reason`；无问题时显式写 `findings: []`，不虚构空记录。
检查范围、限制和修复建议写入人类报告，机器 JSON 是唯一事实来源，不另抄完整 finding 或手填计数。

## 2. 问题严重程度（severity 判定）

| 级别 | 判据 | 是否进 reconciliation |
|---|---|---|
| `high` | 严重安全规则违规 / 资金或数据正确性问题 / 规范 HIGH 规则违规 / 契约破坏 / 已测量的 diff 行覆盖率低于 85% / 验收项不通过 | **是** |
| `medium` | 可维护性问题、缺测试 | 否（记录即可） |
| `low` | 风格、命名 | 否 |

只接受上述三档；其他级别报错，不自动转换或改写历史记录。


### 行为类问题

**1. 核对依据**

以违反方法契约为由报 `high`，`evidence` 必须包含实际方法的完整签名、对应接口声明（无接口则方法声明）的文件及行号、契约原文短摘。同名重载或相似接口不能代替。
确认无文字契约时，可引用具体代码不变量或测试及位置；不能把未读取视为不存在。
依据未核对或未列出时，最高 `medium`，注明“契约未核对”。

**2. 按已证实的错误定级**

- `high`：可达输入下，API / SPI / 缓存 / 状态机等公共契约边界已出现错误返回、异常或漏失效。源码推演可作证据，不要求端到端运行。
- 最高 `medium`：边界错误尚未证实，仅推测下游可能受影响；或性能问题未测量。

边界错误已证实时，下游 UI / 模板 / 集成层未验证只记入 `evidence`，不因此降级。

**3. 处理契约冲突**

契约、文档或测试存在冲突时，在 `evidence` 列明双方依据。只有适用于目标版本、能解释冲突的证据才能消解冲突；“疑似笔误 / 复制粘贴 / 旧注释”不算证据。
判断依赖未解决冲突的，记为未验证项；如保留为 finding，最高 `medium`，摘要注明“契约待确认”。其他有独立充分证据的问题照常定级。
`unverified` 不是 finding 的 severity 或 status。

### 组合风险与测试缺口

- **组合风险**：多个不同问题相互作用，且有证据证明共同造成更严重后果时，
  按组合后的影响定级，并说明相互作用路径。
- **契约变更与测试缺口**：确认缺少对应测试时，记录测试缺口，不自动升级为 `high`。
  已有证据证明契约变更造成破坏性影响时，按上方 severity 判据定级。
  测试上下文未提供或不完整时，注明“相关测试未验证”，不得据此断言没有测试。

## 3. 问题处理状态

```
open ──┬─→ reconciled      已处理（改了代码 / 补了测试）
       ├─→ wontfix         明确不修（**必须写理由**，且 severity 必须是 medium/low）
       └─→ false-positive  探针误报（**必须写证据**说明为什么不是问题）
```

### 处置后的重跑

high finding 处置后，重新执行对应探针并上报结果，不得直接手工改为 `passed`。
重跑须说明代码或判断依据的变化；执行状态以最新结果为准，历史 finding 及处理记录保留。

## 4. 探针执行结果

`requires` 列出探针所需输入，按本轮提供的材料及默认配置检查。
探针执行状态单独上报，与单条 finding 的处理状态区分：

| 状态 | 含义 |
|---|---|
| `passed` | 相关检查已完成，且无执行错误、无 open high |
| `failed` | 相关检查已完成，无执行错误但发现 open high |
| `skipped` | **按探针约定正常跳过**，例如本轮未提供 `requires` 所需的可选输入；必须写明原因。**不算失败** |
| `error` | 已指定输入的路径不存在、无法读取或解析，或命令 / 工具执行失败。仅 `required=true` 时，与 `failed` 一样计入 `PROBE_REQUIRED_FAILED` |

已指定的覆盖率报告路径读不到时，应记为 `error`。
默认配置指向的资源缺失或损坏同样属于 `error`，不得伪装成正常跳过。
