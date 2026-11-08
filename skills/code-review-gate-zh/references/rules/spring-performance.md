# Spring/JPA 与性能优化规范

## Spring/JPA 最佳实践

### 参数验证

```java
// 正确：使用@Valid验证
@PostMapping("/users")
public UserDTO createUser(@Valid @RequestBody UserCreateRequest request) {
    return userService.create(request);
}

@Data
public class UserCreateRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 50, message = "用户名长度2-50")
    private String name;
    
    @Email(message = "邮箱格式不正确")
    private String email;
    
    @Min(value = 0, message = "年龄不能为负")
    private Integer age;
}
```

### 事务管理

```java
// 正确：事务范围明确
@Transactional(rollbackFor = Exception.class)
public void createUser(User user, UserProfile profile) {
    userDao.insert(user);
    profile.setUserId(user.getId());
    profileDao.insert(profile);
}

// 注意：只读操作不加事务或使用只读事务
@Transactional(readOnly = true)
public User getUser(Long id) {
    return userDao.findById(id);
}
```

### N+1查询防护

```java
// 错误：N+1查询
List<User> users = userDao.findAll();
for (User user : users) {
    List<Order> orders = orderDao.findByUserId(user.getId());  // N次查询！
    user.setOrders(orders);
}

// 正确：使用JOIN FETCH
@Query("SELECT u FROM User u LEFT JOIN FETCH u.orders WHERE u.id IN :ids")
List<User> findWithOrders(@Param("ids") List<Long> ids);

// 或使用EntityGraph
@Entity
@NamedEntityGraph(name = "User.withOrders", 
    attributeNodes = @NamedAttributeNode("orders"))
public class User { ... }
```

### 统一异常处理

```java
// 统一异常处理
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException e) {
        return ResponseEntity.badRequest()
            .body(new ErrorResponse(e.getCode(), e.getMessage()));
    }
    
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleOther(Exception e) {
        log.error("Unexpected error", e);
        return ResponseEntity.internalServerError()
            .body(new ErrorResponse("SYSTEM_ERROR", "系统错误"));
    }
}
```

## 性能优化规范

### 服务器配置

| 配置项 | 说明 | 推荐值 |
|-------|------|-------|
| TCP time_wait超时 | 高并发场景调小 | `net.ipv4.tcp_fin_timeout=30` |
| 最大文件句柄数 | Linux默认1024不够 | `ulimit -n 65535` |
| JVM HeapDump | OOM时生成堆转储 | `-XX:+HeapDumpOnOutOfMemoryError` |

### 对象创建

```java
// 错误：循环中创建字符串
String result = "";
for (String item : list) {
    result += item + ",";  // 每次创建新String！
}

// 正确：使用StringBuilder
StringBuilder sb = new StringBuilder();
for (String item : list) {
    if (sb.length() > 0) sb.append(",");
    sb.append(item);
}
String result = sb.toString();

// 或使用String.join
String result = String.join(",", list);
```

### 批量操作

```java
// 错误：循环单条插入
for (User user : users) {
    userDao.insert(user);  // N次IO！
}

// 正确：批量插入
userDao.batchInsert(users);
```
