# 规则包

本索引列出内置规则文件及其用途；加载与检查流程见 [repo-guard 探针](../probes/repo-guard.md)。

## 位置优先级

1. `$CODE_REVIEW_RULES_DIR`
2. 项目根 `.code-review/rules/`
3. skill 内置：`references/rules/`

项目自带规则包会整体替代内置规则包（不是合并）。`bash "$CODE_REVIEW_SKILL_DIR/scripts/rule-grep"` 使用同一套优先级。

## 内置文件

| 文件 | 类型 | 内容 |
|---|---|---|
| `baseline-java.md` | 可机判 / 语义检查 | 9 条基线规则 |
| `concurrency.md` | 散文 | 线程池、SimpleDateFormat、锁顺序 |
| `exception-logging.md` | 散文 | 异常捕获、事务回滚、日志 |
| `naming-format.md` | 散文 | 命名与格式 |
| `oop-collection.md` | 散文 | 不可变、防御性编程、集合 |
| `spring-performance.md` | 散文 | Spring / JPA / 事务 / 性能 |
| `testing-engineering.md` | 散文 | 单元测试规范 |
| `security.md` | 散文 | 安全基线 |

## 规则文件格式

每条规则一个标题，后跟一行可选的 `检测模式`：

```markdown
### SEC-001 [HIGH] SQL 字符串拼接

为什么这条规则重要。

**检测模式**（任一命中即违规）:
- `正则一`
- `正则二`
```

- 标题必须是 `### <规则ID> [<严重级>] <标题>`，严重级取 `HIGH` / `MEDIUM` / `LOW`
- `检测模式` 里的反引号片段会被 `bash "$CODE_REVIEW_SKILL_DIR/scripts/rule-grep"` 抽出来当正则跑
- 没有 `检测模式` 的规则不参与正则扫描
- **规则 ID 是 finding 的 evidence**，没有 ID 的判断不算数

## 约束

- 只写团队自己的规则，不要复制来源不明的内部规范
- 正则尽量窄，宁可漏筛也不要制造大量误报
