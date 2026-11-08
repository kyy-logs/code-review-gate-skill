# Security guidelines

## HIGH security rules
**Detection mode**: semantic

| Rule ID | Rule | Description | Wrong example | Correct example |
|--------|------|------|---------|---------|
| SEC-101 | SQL parameter binding | String-concatenated SQL is forbidden | `"SELECT * FROM users WHERE id = " + userId` | `"SELECT * FROM users WHERE id = ?"` + PreparedStatement |
| SEC-102 | No hard-coded credentials | API keys / passwords / tokens must not be hard-coded | `String password = "123456"` | `System.getenv("DB_PASSWORD")` |
| SEC-103 | Input validation | All user input must be validated | Use request parameters directly | Use `@Valid` / `@Validated` |
| SEC-104 | Sensitive-data masking | Logs must not print sensitive information | `log.info("user: {}", user)` | `log.info("phone: {}", SensitiveDataMasker.maskPhone(phone))` |
| SEC-105 | CSRF protection | State-changing endpoints must verify CSRF | Direct POST | Add CSRF token verification |
| SEC-106 | Permission checks | All user-data endpoints must enforce authorization | Return data directly | Verify that userId matches |
| SEC-107 | XSS protection | v-html / dangerouslySetInnerHTML are forbidden | `<div v-html="content">` | Use a safe rendering method |

## Authentication and authorization
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| AUTH-101 | Permission checks | All user-data endpoints must enforce authorization and prevent horizontal privilege escalation |
| AUTH-102 | Identity verification | External systems use unified authentication; internal systems use SSO |
| AUTH-103 | Token storage | Must not be placed in URL parameters; use Cookie / POST body |
| AUTH-104 | Cookie security | HttpOnly=true, Secure=true (HTTPS) |
| AUTH-105 | Do not trust the client | Do not use client-supplied userId / roleId directly for authorization |

## Data security
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| DATA-101 | Sensitive-data masking | Phone numbers, ID numbers, bank card numbers, etc. must be masked in displays |
| DATA-102 | Data classification | Decide whether to mask / watermark according to the project's data-classification standard |
| DATA-103 | Number protection | Scenarios involving the real numbers of both parties must use the number-protection service |
| DATA-104 | Query authorization | Do not query by business ID alone; always join userId / tenantId |

## API security
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| API-101 | Replay protection | Platform resources such as SMS and payments must be replay-protected |
| API-102 | Rate limiting | Endpoints with enumerable parameters must be rate-limited to prevent abuse |
| API-103 | Real client IP | Use trusted proxy headers; do not trust X-Forwarded-For directly |
| API-104 | CORS | Access-Control-Allow-Origin must not be `*` |

## Frontend security
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| WEB-101 | XSS protection | v-html and dangerouslySetInnerHTML are forbidden |
| WEB-102 | CSRF protection | Forms / AJAX must verify CSRF |
| WEB-103 | Request methods | Non-query operations must not use GET |

## Key management
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| KEY-101 | Key configuration | No hard-coding; use KMS / a key-management service |
| KEY-102 | Private-key protection | Hard-coding `PRIVATE_KEY = "..."` is forbidden |
