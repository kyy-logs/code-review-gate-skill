# Exception handling and logging guidelines

## Exception handling

### Exception catching
**Detection mode**: semantic

**Empty catch blocks are forbidden (MULT-EXC-001):**

```java
// Wrong: swallows the exception
try {
    doSomething();
} catch (Exception e) {
    // empty block
}

// Correct: at least log it
try {
    doSomething();
} catch (Exception e) {
    log.error("Failed to do something", e);
    throw new BusinessException("操作失败", e);
}
```

### Transaction rollback
**Detection mode**: semantic

**Catching an exception in transactional code requires a manual rollback (MULT-EXC-002):**

```java
@Transactional(rollbackFor = Exception.class)
public void updateUser(User user) {
    try {
        userDao.update(user);
        userPhoneDao.update(user.getPhone());
    } catch (Exception e) {
        log.error("更新用户失败", e);
        TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
        throw new BusinessException("更新失败");
    }
}
```

### finally rules
**Detection mode**: semantic

**Do not return from finally (MULT-EXC-003):**

```java
// Wrong
try {
    return 1;
} finally {
    return 2;  // Forbidden! Overrides the return in try
}

// Correct
try {
    return 1;
} finally {
    // Cleanup is allowed here, but no return
}
```

### Resource cleanup
**Detection mode**: semantic

**The finally block must close resources; on JDK 7+ use try-with-resources (MULT-EXC-004):**

```java
// Correct
try (InputStream is = new FileInputStream(file);
     OutputStream os = new FileOutputStream(output)) {
    // use the resource
} catch (IOException e) {
    log.error("IO error", e);
}
```

### Pre-check principle
**Detection mode**: semantic

**Pre-checks are better than exception catching (MULT-EXC-005):**

```java
// Wrong
try {
    return user.getName().toUpperCase();
} catch (NullPointerException e) {
    return null;
}

// Correct
if (user != null && user.getName() != null) {
    return user.getName().toUpperCase();
}
return null;
```

### Exception classification
**Detection mode**: semantic

**Distinguish stable code from unstable code (MULT-EXC-007):**

```java
// Stable code: catch a specific exception
try {
    userDao.insert(user);
} catch (DuplicateKeyException e) {
    log.warn("Duplicate user: {}", user.getId());
    throw new BusinessException("用户已存在");
}

// Unstable code: catch a broader exception
try {
    thirdPartyService.call();
} catch (Exception e) {
    log.error("Third party call failed", e);
    throw new ServiceException("第三方服务调用失败", e);
}
```

### Cascading-call NPEs
**Detection mode**: semantic

**Cascading calls are prone to NPEs; use Optional (MULT-EXC-008):**

```java
// Wrong
String cityName = user.getAddress().getCity().getName();

// Correct
String cityName = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .map(City::getName)
    .orElse("未知");
```

## Logging

### Logging framework
**Detection mode**: semantic

**Depend on the SLF4J facade; do not use Log4j/Logback APIs directly (MULT-LOG-140):**

```java
// Wrong: use Log4j/Logback directly
import org.apache.log4j.Logger;

// Correct: use SLF4J
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

private static final Logger log = LoggerFactory.getLogger(UserService.class);
```

### Log content
**Detection mode**: semantic

**Exception logs must include context and the stack trace (MULT-LOG-141):**

```java
// Correct
log.error("参数: {}，异常: {}", userId, e.getMessage(), e);

// Or use placeholders
log.error("更新用户失败, userId={}, error={}", userId, e.getMessage(), e);
```

### Conditional output
**Detection mode**: semantic

**Use conditional output or placeholders for trace/debug/info (MULT-LOG-142):**

```java
// Wrong: string concatenation
log.debug("Processing user: " + userId);

// Correct: placeholder
log.debug("Processing user: {}", userId);

// Or conditional output
if (log.isDebugEnabled()) {
    log.debug("Processing user: {}", userId);
}
```

### Sensitive-data masking
**Detection mode**: semantic

**Logs must be masked (MULT-SEC-025/026):**

```java
// Wrong: log sensitive information directly
log.info("User login: phone={}, idCard={}", phone, idCard);

// Correct: mask it
log.info("User login: phone={}, idCard={}", 
    SensitiveDataMasker.maskPhone(phone), 
    SensitiveDataMasker.maskIdCard(idCard));

// Or use the masking helper
log.info("User login: {}", SensitiveDataMasker.maskUserInfo(user));
```

### Log levels
**Detection mode**: semantic

**Disable debug in production; enable info selectively (MULT-LOG-146):**

```java
// Wrong
log.debug("Detailed info");

// Correct
log.info("Operation info");
log.warn("Warning info");
log.error("Error info", e);
```

### Duplicate logs
**Detection mode**: semantic

**Avoid duplicate log output; set additivity=false (MULT-LOG-143):**

```xml
<!-- logback.xml -->
<logger name="com.example.service" level="INFO" additivity="false">
    <appender-ref ref="FILE"/>
</logger>
```
