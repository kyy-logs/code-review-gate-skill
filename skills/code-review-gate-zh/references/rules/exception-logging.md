# 异常处理与日志规范

## 异常处理规范

### 异常捕获

**禁止空catch块（MULT-EXC-001）：**

```java
// 错误：吞掉异常
try {
    doSomething();
} catch (Exception e) {
    // 空块
}

// 正确：至少记录日志
try {
    doSomething();
} catch (Exception e) {
    log.error("Failed to do something", e);
    throw new BusinessException("操作失败", e);
}
```

### 事务回滚

**事务代码catch异常后必须手动回滚（MULT-EXC-002）：**

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

### finally规则

**finally中禁止return（MULT-EXC-003）：**

```java
// 错误
try {
    return 1;
} finally {
    return 2;  // 禁止！会覆盖try中的return
}

// 正确
try {
    return 1;
} finally {
    // 可以执行清理操作，但不能return
}
```

### 资源关闭

**finally块必须关闭资源，JDK7+用try-with-resources（MULT-EXC-004）：**

```java
// 正确
try (InputStream is = new FileInputStream(file);
     OutputStream os = new FileOutputStream(output)) {
    // 使用资源
} catch (IOException e) {
    log.error("IO error", e);
}
```

### 预检查原则

**预检查优于异常捕获（MULT-EXC-005）：**

```java
// 错误
try {
    return user.getName().toUpperCase();
} catch (NullPointerException e) {
    return null;
}

// 正确
if (user != null && user.getName() != null) {
    return user.getName().toUpperCase();
}
return null;
```

### 异常分类

**区分稳定代码和非稳定代码（MULT-EXC-007）：**

```java
// 稳定代码：捕获特定异常
try {
    userDao.insert(user);
} catch (DuplicateKeyException e) {
    log.warn("Duplicate user: {}", user.getId());
    throw new BusinessException("用户已存在");
}

// 非稳定代码：捕获更广泛的异常
try {
    thirdPartyService.call();
} catch (Exception e) {
    log.error("Third party call failed", e);
    throw new ServiceException("第三方服务调用失败", e);
}
```

### 级联调用NPE

**级联调用易NPE，用Optional（MULT-EXC-008）：**

```java
// 错误
String cityName = user.getAddress().getCity().getName();

// 正确
String cityName = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .map(City::getName)
    .orElse("未知");
```

## 日志规范

### 日志框架

**依赖SLF4J门面，禁直接用Log4j/Logback API（MULT-LOG-140）：**

```java
// 错误：直接使用Log4j/Logback
import org.apache.log4j.Logger;

// 正确：使用SLF4J
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

private static final Logger log = LoggerFactory.getLogger(UserService.class);
```

### 日志内容

**异常日志包含现场信息+堆栈（MULT-LOG-141）：**

```java
// 正确
log.error("参数: {}，异常: {}", userId, e.getMessage(), e);

// 或使用占位符
log.error("更新用户失败, userId={}, error={}", userId, e.getMessage(), e);
```

### 条件输出

**trace/debug/info用条件输出或占位符（MULT-LOG-142）：**

```java
// 错误：字符串拼接
log.debug("Processing user: " + userId);

// 正确：占位符
log.debug("Processing user: {}", userId);

// 或条件输出
if (log.isDebugEnabled()) {
    log.debug("Processing user: {}", userId);
}
```

### 敏感数据脱敏

**日志必须脱敏（MULT-SEC-025/026）：**

```java
// 错误：直接打印敏感信息
log.info("User login: phone={}, idCard={}", phone, idCard);

// 正确：脱敏处理
log.info("User login: phone={}, idCard={}", 
    SensitiveDataMasker.maskPhone(phone), 
    SensitiveDataMasker.maskIdCard(idCard));

// 或使用脱敏工具
log.info("User login: {}", SensitiveDataMasker.maskUserInfo(user));
```

### 日志级别

**生产环境禁debug，有选择输出info（MULT-LOG-146）：**

```java
// 错误
log.debug("Detailed info");

// 正确
log.info("Operation info");
log.warn("Warning info");
log.error("Error info", e);
```

### 重复日志

**避免重复打印日志，设置additivity=false（MULT-LOG-143）：**

```xml
<!-- logback.xml -->
<logger name="com.example.service" level="INFO" additivity="false">
    <appender-ref ref="FILE"/>
</logger>
```
