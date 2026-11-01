# Spring/JPA and performance guidelines

## Spring/JPA best practices

### Parameter validation
**Detection mode**: semantic

```java
// Correct: validate with @Valid
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

### Transaction management
**Detection mode**: semantic

```java
// Correct: explicit transaction scope
@Transactional(rollbackFor = Exception.class)
public void createUser(User user, UserProfile profile) {
    userDao.insert(user);
    profile.setUserId(user.getId());
    profileDao.insert(profile);
}

// Note: read-only operations should not use a transaction, or should use a read-only transaction
@Transactional(readOnly = true)
public User getUser(Long id) {
    return userDao.findById(id);
}
```

### N+1 query prevention
**Detection mode**: semantic

```java
// Wrong: N+1 queries
List<User> users = userDao.findAll();
for (User user : users) {
    List<Order> orders = orderDao.findByUserId(user.getId());  // N queries!
    user.setOrders(orders);
}

// Correct: use JOIN FETCH
@Query("SELECT u FROM User u LEFT JOIN FETCH u.orders WHERE u.id IN :ids")
List<User> findWithOrders(@Param("ids") List<Long> ids);

// Or use EntityGraph
@Entity
@NamedEntityGraph(name = "User.withOrders", 
    attributeNodes = @NamedAttributeNode("orders"))
public class User { ... }
```

### Unified exception handling
**Detection mode**: semantic

```java
// Unified exception handling
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

## Performance guidelines

### Server configuration
**Detection mode**: semantic

| Setting | Description | Recommended value |
|-------|------|-------|
| TCP time_wait timeout | Lower it in high-concurrency scenarios | `net.ipv4.tcp_fin_timeout=30` |
| Maximum file handles | The Linux default of 1024 is insufficient | `ulimit -n 65535` |
| JVM HeapDump | Generate a heap dump on OOM | `-XX:+HeapDumpOnOutOfMemoryError` |

### Object creation
**Detection mode**: semantic

```java
// Wrong: create strings in a loop
String result = "";
for (String item : list) {
    result += item + ",";  // creates a new String each time!
}

// Correct: use StringBuilder
StringBuilder sb = new StringBuilder();
for (String item : list) {
    if (sb.length() > 0) sb.append(",");
    sb.append(item);
}
String result = sb.toString();

// Or use String.join
String result = String.join(",", list);
```

### Batch operations
**Detection mode**: semantic

```java
// Wrong: one insert per iteration
for (User user : users) {
    userDao.insert(user);  // N IOs!
}

// Correct: batch insert
userDao.batchInsert(users);
```
