# Naming and formatting guidelines

## Naming conventions

### Basic naming rules
**Detection mode**: semantic

| Type | Rule ID | Convention | Example | Forbidden example |
|------|--------|------|------|---------|
| Class name | MULT-NAME-003 | UpperCamelCase | `UserDO`, `HtmlUtil`, `OrderService` | `userDo`, `htmlutil` |
| Method name | MULT-NAME-004 | lowerCamelCase | `getUserById()`, `calculateTotal()` | `GetUserById()`, `calculate_total()` |
| Constant | MULT-CONST-005 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` | `maxRetryCount`, `Max_Retry_Count` |
| Package name | MULT-NAME-009 | all lowercase, singular | `com.example.user` | `com.example.Users`, `com.example.userMgmt` |
| Variable | MULT-NAME-004 | lowerCamelCase | `userName`, `orderList` | `user_name`, `UserName` |
| Array | MULT-NAME-007 | `String[] args` | `String[] args` | `String args[]` |

### Special naming rules
**Detection mode**: semantic

| Rule ID | Rule | Description | Example |
|--------|------|------|------|
| MULT-NAME-006 | Abstract class | Must start with Abstract or Base | `AbstractProcessor`, `BaseServiceImpl` |
| MULT-NAME-006 | Exception class | Must end with Exception | `UserNotFoundException`, `InvalidParameterException` |
| MULT-NAME-006 | Test class | Name of the class under test + Test | `UserServiceTest`, `OrderControllerTest` |
| MULT-NAME-011 | Interface implementation | Impl suffix | `UserServiceImpl`, `OrderServiceImpl` |
| MULT-NAME-017 | Domain model | DO/DTO/VO/BO suffix | `UserDO`, `UserDTO`, `UserVO`, `UserBO` |
| MULT-NAME-013 | Enum class | Enum suffix | `StatusEnum`, `TypeEnum` |

### Boolean variable naming
**Detection mode**: semantic

**Boolean properties in POJOs must not use the is prefix (MULT-NAME-008):**

```java
// Wrong: causes serialization problems
public class User {
    private Boolean isSuccess;  // Forbidden!
    private boolean isActive;   // Forbidden!
}

// Correct
public class User {
    private Boolean success;
    private boolean active;
    
    // getter methods may use the is prefix
    public boolean isSuccess() {
        return success;
    }
}
```

### Method naming conventions
**Detection mode**: semantic

| Operation | Rule ID | Naming prefix | Example |
|---------|--------|---------|------|
| Get one | MULT-NAME-014 | get | `getUserById()`, `getOrderByNo()` |
| Get many | MULT-NAME-014 | list | `listUsersByStatus()`, `listOrdersByUser()` |
| Get count | MULT-NAME-014 | count | `countActiveUsers()`, `countOrders()` |
| Insert | MULT-NAME-014 | save/insert | `saveUser()`, `insertOrder()` |
| Delete | MULT-NAME-014 | remove/delete | `removeUser()`, `deleteOrder()` |
| Update | MULT-NAME-014 | update | `updateUserStatus()`, `updateOrderAmount()` |
| Predicate | - | is/has/can | `isActive()`, `hasPermission()`, `canDelete()` |

### Constant conventions
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| MULT-CONST-001 | No magic values | Undefined constants must not appear directly |
| MULT-CONST-002 | Use uppercase L for long literals | `long amount = 2L` (lowercase l is forbidden) |
| MULT-CONST-003 | Group constants by function | Do not keep all constants in one class |
| MULT-CONST-004 | Use enum for fixed ranges | Use an enum when a variable's value changes only within a fixed range |

## Code formatting conventions

### Indentation and spacing
**Detection mode**: semantic

| Rule ID | Rule | Description |
|--------|------|------|
| MULT-FMT-001 | Indentation | 4 spaces; tab characters are forbidden |
| MULT-FMT-002 | Line length | No more than 120 characters |
| MULT-FMT-181 | Operator spacing | One space on each side: `a + b`, `a == b` |
| MULT-FMT-183 | Comma spacing | One space after a comma: `func(a, b, c)` |
| MULT-FMT-181 | Parenthesis spacing | One space between if/for/while and the parenthesis: `if (condition)` |
| MULT-FMT-184 | File encoding | UTF-8, Unix line endings |

### Brace rules
**Detection mode**: semantic

```java
// Correct: opening brace on the same line, body on the next line
if (condition) {
    doSomething();
} else {
    doOther();
}

// Wrong: opening brace on a new line
if (condition)
{
    doSomething();
}
```

### Control statements
**Detection mode**: semantic

**All control statements must use braces, even for a single line (MULT-CTRL-133):**

```java
// Wrong
if (condition) doSomething();

// Correct
if (condition) {
    doSomething();
}
```

**switch must have a default branch (MULT-CTRL-132):**

```java
switch (status) {
    case Status.ACTIVE:
        return "active";
    case Status.INACTIVE:
        return "inactive";
    default:
        return "unknown";
}
```

**if-else nesting must not exceed 3 levels; use guard clauses beyond that (MULT-CTRL-134):**

```java
// Wrong: nesting too deep
if (user != null) {
    if (user.isActive()) {
        if (user.hasPermission()) {
            // ...
        }
    }
}

// Correct: guard clauses
if (user == null) {
    return;
}
if (!user.isActive()) {
    return;
}
if (!user.hasPermission()) {
    return;
}
// Normal logic
```

### Method length limit
**Detection mode**: semantic

**A single method must not exceed 80 lines in total (MULT-FMT-186):**

```java
// Correct: single responsibility, manageable length
public UserDTO convertToDTO(UserDO userDO) {
    if (userDO == null) {
        return null;
    }
    UserDTO dto = new UserDTO();
    dto.setId(userDO.getId());
    dto.setName(userDO.getName());
    dto.setStatus(userDO.getStatus());
    return dto;
}
```
