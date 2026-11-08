# Common baseline (Java)

A minimal usable rule set covering three high-frequency categories: security, concurrency, and exceptions.
Add or remove rules according to the project's actual stack; replacing this file does not affect the orchestration logic in `SKILL.md`.

## Security

### SEC-001 [HIGH] SQL string concatenation

SQL must use parameter binding; user input must never be concatenated into statements.

**Detection pattern** (any hit is a violation):
- `Statement[^;]*execute(Query|Update)?\s*\(\s*["'][^"']*["']\s*\+`
- `create(Query|NativeQuery)\s*\(\s*["'][^"']*["']\s*\+`
- `["'][^"']*(SELECT|INSERT|UPDATE|DELETE)[^"']*["']\s*\+`

### SEC-002 [HIGH] Hard-coded credentials

Passwords, keys, and tokens must not be written in source code.

**Detection pattern**:
- `(password|passwd|secret|token|apiKey|accessKey|privateKey)\s*=\s*"[^"]{6,}"`

### SEC-003 [HIGH] Dangerous XSS rendering

Untrusted content must not be passed directly to HTML rendering.

**Detection pattern**:
- `v-html|dangerouslySetInnerHTML|innerHTML\s*=`

### SEC-004 [HIGH] Command execution

Confirm that arguments do not come from user input before invoking a system command.

**Detection pattern**:
- `Runtime\.getRuntime\(\)\.exec\s*\(|new\s+ProcessBuilder\s*\(`

### AUTH-001 [HIGH] Missing authorization on queries
**Detection mode**: semantic

When querying user data by business ID, include the current user or tenant condition as well.

**Detection pattern**: none (manual check: whether the query condition contains only orderId / id, with no userId / tenantId)

## Logging and data

### LOG-001 [HIGH] Sensitive fields in logs

ID card numbers, phone numbers, bank card numbers, passwords, and tokens must not appear in logs in plaintext.

**Detection pattern**:
- `log(ger)?\.(info|debug|warn|error)\([^)]*(idCard|idNo|phone|mobile|bankCard|password|token)`

## Concurrency and exceptions

### CONC-001 [HIGH] Shared SimpleDateFormat

`SimpleDateFormat` is not thread-safe and must not be used as a static shared instance.

**Detection pattern**:
- `static\s+(final\s+)?SimpleDateFormat`

### CONC-002 [MEDIUM] Thread pool without explicit bounds

`Executors` factory methods can easily create unbounded queues or unlimited threads.

**Detection pattern**:
- `Executors\.(newCachedThreadPool|newFixedThreadPool)\s*\(`

### ERR-001 [HIGH] Empty catch swallows exceptions

An empty catch block fails silently; it must at least log the exception or rethrow it.

**Detection pattern**:
- `catch\s*\([^)]*\)\s*\{\s*\}`
