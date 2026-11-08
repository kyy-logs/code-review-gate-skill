# 安全规范

## HIGH 安全规则

| 规则ID | 规则 | 说明 | 错误示例 | 正确示例 |
|--------|------|------|---------|---------|
| SEC-101 | SQL 参数绑定 | 禁止字符串拼接 SQL | `"SELECT * FROM users WHERE id = " + userId` | `"SELECT * FROM users WHERE id = ?"` + PreparedStatement |
| SEC-102 | 禁止硬编码凭证 | API 密钥 / 密码 / Token 禁止硬编码 | `String password = "123456"` | `System.getenv("DB_PASSWORD")` |
| SEC-103 | 输入验证 | 所有用户输入必须验证 | 直接使用 request 参数 | 使用 `@Valid` / `@Validated` |
| SEC-104 | 敏感数据脱敏 | 日志禁止打印敏感信息 | `log.info("user: {}", user)` | `log.info("phone: {}", SensitiveDataMasker.maskPhone(phone))` |
| SEC-105 | CSRF 保护 | 状态变更接口必须 CSRF 验证 | 直接 POST | 添加 CSRF Token 验证 |
| SEC-106 | 权限校验 | 所有用户数据接口必须权限控制 | 直接返回数据 | 校验 userId 匹配 |
| SEC-107 | XSS 防护 | 禁止 v-html / dangerouslySetInnerHTML | `<div v-html="content">` | 使用安全渲染方式 |

## 认证授权

| 规则ID | 规则 | 说明 |
|--------|------|------|
| AUTH-101 | 权限校验 | 所有用户数据接口必须权限控制，防水平越权 |
| AUTH-102 | 身份验证 | 外部系统接入统一认证，内部系统接入 SSO |
| AUTH-103 | Token 存储 | 禁止放 URL 参数，使用 Cookie / POST body |
| AUTH-104 | Cookie 安全 | HttpOnly=true，Secure=true（HTTPS） |
| AUTH-105 | 禁止信任客户端 | 禁止直接使用客户端传来的 userId / roleId 鉴权 |

## 数据安全

| 规则ID | 规则 | 说明 |
|--------|------|------|
| DATA-101 | 敏感数据脱敏 | 手机号、身份证、银行卡号等必须脱敏展示 |
| DATA-102 | 数据分级 | 按项目数据分级标准决定是否脱敏 / 水印 |
| DATA-103 | 号码保护 | 涉及双方真实号码的场景接入号码保护服务 |
| DATA-104 | 查询鉴权 | 禁止仅用业务 ID 查询，必须联查 userId / tenantId |

## 接口安全

| 规则ID | 规则 | 说明 |
|--------|------|------|
| API-101 | 防重放 | 短信、支付等平台资源必须防重放 |
| API-102 | 限频 | 可遍历参数接口必须限频防刷 |
| API-103 | 获取真实 IP | 使用可信代理头，禁止直接信任 X-Forwarded-For |
| API-104 | CORS | Access-Control-Allow-Origin 禁止 `*` |

## 前端安全

| 规则ID | 规则 | 说明 |
|--------|------|------|
| WEB-101 | XSS 防护 | 禁止 v-html、dangerouslySetInnerHTML |
| WEB-102 | CSRF 防护 | 表单 / AJAX 必须 CSRF 验证 |
| WEB-103 | 请求方法 | 非查询操作禁止 GET 请求 |

## 密钥管理

| 规则ID | 规则 | 说明 |
|--------|------|------|
| KEY-101 | 密钥配置 | 禁止硬编码，接入 KMS / 密钥管理服务 |
| KEY-102 | 私钥保护 | 禁止硬编码 `PRIVATE_KEY = "..."` |
