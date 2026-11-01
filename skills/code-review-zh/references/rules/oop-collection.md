# OOP 与集合处理规范

## 核心原则

### 不可变性原则

**优先使用不可变数据结构和无副作用操作：**

```java
// 错误：可变操作
public List<User> processUsers(List<User> users) {
    List<User> results = new ArrayList<>();
    for (User user : users) {
        user.setVerified(true);  // 修改原对象！
        results.add(user);
    }
    return results;
}

// 正确：不可变操作（创建新对象）
public List<User> processUsers(List<User> users) {
    return users.stream()
        .map(u -> {
            User copy = new User(u);  // 创建副本
            copy.setVerified(true);
            return copy;
        })
        .collect(Collectors.toList());
}
```

### 防御性编程原则

**所有可能为null的地方都必须进行null检查：**

```java
// 错误：可能NPE
public String getUserName(User user) {
    return user.getName().toUpperCase();
}

// 正确：使用Optional
public String getUserName(User user) {
    return Optional.ofNullable(user)
        .map(User::getName)
        .map(String::toUpperCase)
        .orElse("");
}

// 或使用Objects.equals（推荐用于比较）
public boolean isEqual(User u1, User u2) {
    return Objects.equals(u1, u2);
}
```

## OOP 规范

### 覆写方法

**所有覆写方法必须加@Override注解（MULT-OOP-001）：**

```java
// 正确
@Override
public boolean equals(Object obj) {
    // ...
}

@Override
public String toString() {
    // ...
}
```

### 对象比较

**包装类对象比较必须使用equals（MULT-OOP-003）：**

```java
// 错误：可能比较引用
Integer a = 128;
Integer b = 128;
if (a == b) { }  // false!

// 正确
if (a.equals(b)) { }

// 更安全：使用Objects.equals（推荐）
if (Objects.equals(a, b)) { }
```

**equals用常量或确定有值的对象调用（MULT-OOP-002）：**

```java
// 错误：可能NPE
if (user.getName().equals("admin")) { }

// 正确
if ("admin".equals(user.getName())) { }

// 或使用Objects.equals
if (Objects.equals("admin", user.getName())) { }
```

### POJO类规范

```java
// 正确的POJO类定义
public class UserDTO {
    // 使用包装类型（MULT-OOP-004）
    private Long id;
    private String name;
    private Integer age;
    private Boolean active;  // 不用is前缀（MULT-NAME-008）
    
    // 不要设置默认值（MULT-OOP-006）
    // private Integer status = 0;  // 禁止
    
    // 必须有toString方法（MULT-OOP-011）
    @Override
    public String toString() {
        return "UserDTO{id=" + id + ", name='" + name + "'}";
    }
}
```

### 访问控制

**从严原则：private > protected > default > public（MULT-OOP-121）：**

```java
// 工具类禁止public构造方法
public class StringUtils {
    private StringUtils() {
        throw new UnsupportedOperationException("Utility class");
    }
    
    public static boolean isEmpty(String str) {
        return str == null || str.isEmpty();
    }
}
```

### 序列化规范

**序列化类新增属性时不要修改serialVersionUID（MULT-OOP-007）：**

```java
// 正确
private static final long serialVersionUID = 1L;
```

### 构造方法规范

**构造方法禁止业务逻辑，初始化放init方法（MULT-OOP-008）：**

```java
// 错误：构造方法包含业务逻辑
public UserService() {
    loadConfig();  // 禁止
    initCache();  // 禁止
}

// 正确
public UserService() {
    // 仅初始化必要属性
}

@PostConstruct
public void init() {
    loadConfig();
    initCache();
}
```

## 集合处理规范

### 集合初始化

**指定初始容量避免扩容（MULT-COLL-130）：**

```java
// 正确
List<String> list = new ArrayList<>(expectedSize);
Map<String, Object> map = new HashMap<>(expectedSize);

// 计算公式
int initialCapacity = (int) (expectedSize / 0.75) + 1;
```

### equals/hashCode

**重写equals必须重写hashCode（MULT-COLL-122）：**

```java
// 正确
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    User user = (User) o;
    return Objects.equals(id, user.id);
}

@Override
public int hashCode() {
    return Objects.hash(id);
}
```

### 集合遍历

**禁止在foreach中remove/add（MULT-COLL-123）：**

```java
// 错误：ConcurrentModificationException
for (String item : list) {
    if (condition) {
        list.remove(item);  // 禁止！
    }
}

// 正确：使用Iterator
Iterator<String> iter = list.iterator();
while (iter.hasNext()) {
    String item = iter.next();
    if (condition) {
        iter.remove();
    }
}

// 或使用removeIf（Java 8+）推荐
list.removeIf(item -> condition);
```

### Arrays.asList

**Arrays.asList()返回的集合禁止add/remove/clear（MULT-COLL-125）：**

```java
// 错误
List<String> list = Arrays.asList("a", "b");
list.add("c");  // 抛出UnsupportedOperationException

// 正确：创建新数组
List<String> list = new ArrayList<>(Arrays.asList("a", "b"));
list.add("c");
```

### subList注意事项

**subList是原集合视图，修改原集合导致ConcurrentModificationException（MULT-COLL-126）：**

```java
// 错误
List<String> list = new ArrayList<>(Arrays.asList("a", "b", "c"));
List<String> sub = list.subList(0, 2);
list.add("d");  // 导致sub迭代异常

// 正确：创建独立副本
List<String> sub = new ArrayList<>(list.subList(0, 2));
```

### 集合转数组

```java
// 错误
String[] arr = list.toArray();  // 返回Object[]

// 正确
String[] arr = list.toArray(new String[0]);
```

### Map遍历

```java
// 推荐：使用entrySet（MULT-COLL-131）
for (Map.Entry<String, Object> entry : map.entrySet()) {
    String key = entry.getKey();
    Object value = entry.getValue();
}

// Java 8+：使用forEach
map.forEach((key, value) -> {
    // ...
});
```

### 集合判空

```java
// 错误
if (list.size() == 0) { }

// 正确
if (list.isEmpty()) { }

// 安全判空（推荐）
if (CollectionUtils.isEmpty(list)) { }
```

### ConcurrentHashMap

**ConcurrentHashMap K/V均不允许null（MULT-COLL-129）：**

```java
// 错误
ConcurrentHashMap<String, Object> map = new ConcurrentHashMap<>();
map.put("key", null);  // 禁止

// 正确：使用HashMap（允许null）
Map<String, Object> map = new HashMap<>();
map.put("key", null);
```
