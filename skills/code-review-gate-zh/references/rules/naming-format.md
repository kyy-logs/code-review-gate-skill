# 命名与格式规范

## 命名规范

### 基本命名规则

| 类型 | 规则ID | 规范 | 示例 | 禁止示例 |
|------|--------|------|------|---------|
| 类名 | MULT-NAME-003 | UpperCamelCase | `UserDO`, `HtmlUtil`, `OrderService` | `userDo`, `htmlutil` |
| 方法名 | MULT-NAME-004 | lowerCamelCase | `getUserById()`, `calculateTotal()` | `GetUserById()`, `calculate_total()` |
| 常量 | MULT-CONST-005 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` | `maxRetryCount`, `Max_Retry_Count` |
| 包名 | MULT-NAME-009 | 全小写单数 | `com.example.user` | `com.example.Users`, `com.example.userMgmt` |
| 变量 | MULT-NAME-004 | lowerCamelCase | `userName`, `orderList` | `user_name`, `UserName` |
| 数组 | MULT-NAME-007 | `String[] args` | `String[] args` | `String args[]` |

### 特殊命名规则

| 规则ID | 规则 | 说明 | 示例 |
|--------|------|------|------|
| MULT-NAME-006 | 抽象类 | Abstract或Base开头 | `AbstractProcessor`, `BaseServiceImpl` |
| MULT-NAME-006 | 异常类 | Exception结尾 | `UserNotFoundException`, `InvalidParameterException` |
| MULT-NAME-006 | 测试类 | 被测类名+Test | `UserServiceTest`, `OrderControllerTest` |
| MULT-NAME-011 | 接口实现 | Impl后缀 | `UserServiceImpl`, `OrderServiceImpl` |
| MULT-NAME-017 | 领域模型 | DO/DTO/VO/BO后缀 | `UserDO`, `UserDTO`, `UserVO`, `UserBO` |
| MULT-NAME-013 | 枚举类 | Enum后缀 | `StatusEnum`, `TypeEnum` |

### 布尔变量命名

**POJO类中布尔属性禁止使用is前缀（MULT-NAME-008）：**

```java
// 错误：会导致序列化问题
public class User {
    private Boolean isSuccess;  // 禁止！
    private boolean isActive;   // 禁止！
}

// 正确
public class User {
    private Boolean success;
    private boolean active;
    
    // getter方法可以使用is前缀
    public boolean isSuccess() {
        return success;
    }
}
```

### 方法命名约定

| 操作类型 | 规则ID | 命名前缀 | 示例 |
|---------|--------|---------|------|
| 获取单个 | MULT-NAME-014 | get | `getUserById()`, `getOrderByNo()` |
| 获取多个 | MULT-NAME-014 | list | `listUsersByStatus()`, `listOrdersByUser()` |
| 获取统计 | MULT-NAME-014 | count | `countActiveUsers()`, `countOrders()` |
| 插入 | MULT-NAME-014 | save/insert | `saveUser()`, `insertOrder()` |
| 删除 | MULT-NAME-014 | remove/delete | `removeUser()`, `deleteOrder()` |
| 修改 | MULT-NAME-014 | update | `updateUserStatus()`, `updateOrderAmount()` |
| 判断 | - | is/has/can | `isActive()`, `hasPermission()`, `canDelete()` |

### 常量规范

| 规则ID | 规则 | 说明 |
|--------|------|------|
| MULT-CONST-001 | 禁止魔法值 | 不允许未经预定义的常量直接出现 |
| MULT-CONST-002 | long赋值用大写L | `long amount = 2L` (禁止小写l) |
| MULT-CONST-003 | 按功能归类常量 | 不要用一个类维护所有常量 |
| MULT-CONST-004 | 固定范围用enum | 变量值仅在固定范围内变化时用枚举 |

## 代码格式规范

### 缩进与空格

| 规则ID | 规则 | 说明 |
|--------|------|------|
| MULT-FMT-001 | 缩进 | 4个空格，禁止Tab字符 |
| MULT-FMT-002 | 单行长度 | 不超过120字符 |
| MULT-FMT-181 | 运算符空格 | 运算符左右各一个空格：`a + b`, `a == b` |
| MULT-FMT-183 | 逗号空格 | 逗号后一个空格：`func(a, b, c)` |
| MULT-FMT-181 | 括号空格 | if/for/while与括号间一个空格：`if (condition)` |
| MULT-FMT-184 | 文件编码 | UTF-8，换行符Unix格式 |

### 大括号规则

```java
// 正确：左大括号前不换行，后换行
if (condition) {
    doSomething();
} else {
    doOther();
}

// 错误：左大括号前换行
if (condition)
{
    doSomething();
}
```

### 控制语句

**所有控制语句必须使用大括号，即使只有一行（MULT-CTRL-133）：**

```java
// 错误
if (condition) doSomething();

// 正确
if (condition) {
    doSomething();
}
```

**switch必须有default分支（MULT-CTRL-132）：**

```java
switch (status) {
    case Status.ACTIVE:
        return "激活";
    case Status.INACTIVE:
        return "未激活";
    default:
        return "未知";
}
```

**if-else嵌套不超过3层，超过使用卫语句（MULT-CTRL-134）：**

```java
// 错误：嵌套过深
if (user != null) {
    if (user.isActive()) {
        if (user.hasPermission()) {
            // ...
        }
    }
}

// 正确：卫语句
if (user == null) {
    return;
}
if (!user.isActive()) {
    return;
}
if (!user.hasPermission()) {
    return;
}
// 正常逻辑
```

### 单行方法限制

**单个方法总行数不超过80行（MULT-FMT-186）：**

```java
// 正确：方法职责单一，行数可控
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
