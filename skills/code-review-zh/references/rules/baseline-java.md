# 公共基线（Java）

最小可用规则集，覆盖安全、并发、异常三类高频问题。
按项目实际技术栈增删；替换本文件不会影响 `SKILL.md` 的编排逻辑。

## 安全

### SEC-001 [HIGH] SQL 字符串拼接

SQL 必须使用参数绑定，禁止把用户输入拼进语句。

**检测模式**（任一命中即违规）:
- `Statement[^;]*execute(Query|Update)?\s*\(\s*["'][^"']*["']\s*\+`
- `create(Query|NativeQuery)\s*\(\s*["'][^"']*["']\s*\+`
- `["'][^"']*(SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\+`

### SEC-002 [HIGH] 硬编码凭证

密码、密钥、Token 不得写在源码里。

**检测模式**:
- `(password|passwd|secret|token|apiKey|accessKey|privateKey)\s*=\s*"[^"]{6,}"`

### SEC-003 [HIGH] XSS 危险渲染

禁止把不可信内容直接交给 HTML 渲染。

**检测模式**:
- `v-html|dangerouslySetInnerHTML|innerHTML\s*=`

### SEC-004 [HIGH] 命令执行

调用系统命令前必须确认参数不来自用户输入。

**检测模式**:
- `Runtime\.getRuntime\(\)\.exec\s*\(|new\s+ProcessBuilder\s*\(`

### AUTH-001 [HIGH] 越权查询

按业务 ID 查询用户数据时，必须同时带上当前用户或租户条件。

**检测模式**: 无（人工判断：查询条件里是否只有 orderId / id，没有 userId / tenantId）

## 日志与数据

### LOG-001 [HIGH] 日志打印敏感字段

身份证、手机号、银行卡、密码、Token 不得明文进日志。

**检测模式**:
- `log(ger)?\.(info|debug|warn|error)\([^)]*(idCard|idNo|phone|mobile|bankCard|password|token)`

## 并发与异常

### CONC-001 [HIGH] 共享 SimpleDateFormat

`SimpleDateFormat` 不是线程安全的，不得作为静态共享实例。

**检测模式**:
- `static\s+(final\s+)?SimpleDateFormat`

### CONC-002 [MEDIUM] 线程池未显式设界

使用 `Executors` 工厂方法容易产生无界队列或无限线程。

**检测模式**:
- `Executors\.(newCachedThreadPool|newFixedThreadPool)\s*\(`

### ERR-001 [HIGH] 空 catch 吞异常

空的 catch 块会静默失败，必须至少记录或重新抛出。

**检测模式**:
- `catch\s*\([^)]*\)\s*\{\s*\}`
