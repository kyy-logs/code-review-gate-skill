# OOP and collection guidelines

## Core principles

### Immutability principle
**Detection mode**: semantic

**Prefer immutable data structures and side-effect-free operations:**

```java
// Wrong: mutable operation
public List<User> processUsers(List<User> users) {
    List<User> results = new ArrayList<>();
    for (User user : users) {
        user.setVerified(true);  // Modifies the original object!
        results.add(user);
    }
    return results;
}

// Correct: immutable operation (create new objects)
public List<User> processUsers(List<User> users) {
    return users.stream()
        .map(u -> {
            User copy = new User(u);  // Create a copy
            copy.setVerified(true);
            return copy;
        })
        .collect(Collectors.toList());
}
```

### Defensive programming principle
**Detection mode**: semantic

**Every place that may be null must be null-checked:**

```java
// Wrong: may throw NPE
public String getUserName(User user) {
    return user.getName().toUpperCase();
}

// Correct: use Optional
public String getUserName(User user) {
    return Optional.ofNullable(user)
        .map(User::getName)
        .map(String::toUpperCase)
        .orElse("");
}

// Or use Objects.equals (recommended for comparisons)
public boolean isEqual(User u1, User u2) {
    return Objects.equals(u1, u2);
}
```

## OOP conventions

### Overridden methods
**Detection mode**: semantic

**All overridden methods must have the @Override annotation (MULT-OOP-001):**

```java
// Correct
@Override
public boolean equals(Object obj) {
    // ...
}

@Override
public String toString() {
    // ...
}
```

### Object comparison
**Detection mode**: semantic

**Wrapper objects must be compared with equals (MULT-OOP-003):**

```java
// Wrong: may compare references
Integer a = 128;
Integer b = 128;
if (a == b) { }  // false!

// Correct
if (a.equals(b)) { }

// Safer: use Objects.equals (recommended)
if (Objects.equals(a, b)) { }
```

**Call equals on a constant or an object known to be non-null (MULT-OOP-002):**

```java
// Wrong: may throw NPE
if (user.getName().equals("admin")) { }

// Correct
if ("admin".equals(user.getName())) { }

// Or use Objects.equals
if (Objects.equals("admin", user.getName())) { }
```

### POJO conventions
**Detection mode**: semantic

```java
// Correct POJO class definition
public class UserDTO {
    // Use wrapper types (MULT-OOP-004)
    private Long id;
    private String name;
    private Integer age;
    private Boolean active;  // Do not use the is prefix (MULT-NAME-008)
    
    // Do not set default values (MULT-OOP-006)
    // private Integer status = 0;  // Forbidden
    
    // Must have a toString method (MULT-OOP-011)
    @Override
    public String toString() {
        return "UserDTO{id=" + id + ", name='" + name + "'}";
    }
}
```

### Access control
**Detection mode**: semantic

**Use the most restrictive access level: private > protected > default > public (MULT-OOP-121):**

```java
// Utility classes must not have public constructors
public class StringUtils {
    private StringUtils() {
        throw new UnsupportedOperationException("Utility class");
    }
    
    public static boolean isEmpty(String str) {
        return str == null || str.isEmpty();
    }
}
```

### Serialization conventions
**Detection mode**: semantic

**Do not change serialVersionUID when adding fields to a serializable class (MULT-OOP-007):**

```java
// Correct
private static final long serialVersionUID = 1L;
```

### Constructor conventions
**Detection mode**: semantic

**Constructors must not contain business logic; put initialization in an init method (MULT-OOP-008):**

```java
// Wrong: constructor contains business logic
public UserService() {
    loadConfig();  // Forbidden
    initCache();  // Forbidden
}

// Correct
public UserService() {
    // Initialize only necessary properties
}

@PostConstruct
public void init() {
    loadConfig();
    initCache();
}
```

## Collection guidelines

### Collection initialization
**Detection mode**: semantic

**Specify the initial capacity to avoid resizing (MULT-COLL-130):**

```java
// Correct
List<String> list = new ArrayList<>(expectedSize);
Map<String, Object> map = new HashMap<>(expectedSize);

// Calculation formula
int initialCapacity = (int) (expectedSize / 0.75) + 1;
```

### equals/hashCode
**Detection mode**: semantic

**Overriding equals requires overriding hashCode (MULT-COLL-122):**

```java
// Correct
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

### Collection iteration
**Detection mode**: semantic

**Do not remove/add inside foreach (MULT-COLL-123):**

```java
// Wrong: ConcurrentModificationException
for (String item : list) {
    if (condition) {
        list.remove(item);  // Forbidden!
    }
}

// Correct: use Iterator
Iterator<String> iter = list.iterator();
while (iter.hasNext()) {
    String item = iter.next();
    if (condition) {
        iter.remove();
    }
}

// Or use removeIf (Java 8+), recommended
list.removeIf(item -> condition);
```

### Arrays.asList
**Detection mode**: semantic

**The collection returned by Arrays.asList() must not be add/remove/clear'd (MULT-COLL-125):**

```java
// Wrong
List<String> list = Arrays.asList("a", "b");
list.add("c");  // throws UnsupportedOperationException

// Correct: create a new list
List<String> list = new ArrayList<>(Arrays.asList("a", "b"));
list.add("c");
```

### subList caveats
**Detection mode**: semantic

**subList is a view of the original collection; modifying the original causes ConcurrentModificationException (MULT-COLL-126):**

```java
// Wrong
List<String> list = new ArrayList<>(Arrays.asList("a", "b", "c"));
List<String> sub = list.subList(0, 2);
list.add("d");  // causes sub iteration to fail

// Correct: create an independent copy
List<String> sub = new ArrayList<>(list.subList(0, 2));
```

### Collection to array
**Detection mode**: semantic

```java
// Wrong
String[] arr = list.toArray();  // returns Object[]

// Correct
String[] arr = list.toArray(new String[0]);
```

### Map iteration
**Detection mode**: semantic

```java
// Recommended: use entrySet (MULT-COLL-131)
for (Map.Entry<String, Object> entry : map.entrySet()) {
    String key = entry.getKey();
    Object value = entry.getValue();
}

// Java 8+: use forEach
map.forEach((key, value) -> {
    // ...
});
```

### Empty collection checks
**Detection mode**: semantic

```java
// Wrong
if (list.size() == 0) { }

// Correct
if (list.isEmpty()) { }

// Safe empty check (recommended)
if (CollectionUtils.isEmpty(list)) { }
```

### ConcurrentHashMap
**Detection mode**: semantic

**ConcurrentHashMap does not allow null keys or values (MULT-COLL-129):**

```java
// Wrong
ConcurrentHashMap<String, Object> map = new ConcurrentHashMap<>();
map.put("key", null);  // Forbidden

// Correct: use HashMap (nulls allowed)
Map<String, Object> map = new HashMap<>();
map.put("key", null);
```
