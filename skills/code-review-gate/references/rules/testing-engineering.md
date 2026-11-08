# Unit testing and project-structure guidelines

## Unit testing guidelines

### AIR principles
**Detection mode**: semantic

**Unit tests must follow the AIR principles (MULT-GEN-203):**

| Principle | Description |
|------|------|
| A - Automatic | Runs fully automatically without human intervention |
| I - Independent | Test cases are independent; they must not call or depend on each other |
| R - Repeatable | Repeatable, with stable and consistent results |

### Test conventions
**Detection mode**: semantic

```java
// Correct unit test (MULT-GEN-204)
@Test
public void testGetUserById() {
    // Given: prepare test data
    Long userId = 1L;
    User expectedUser = new User(userId, "test");
    when(userDao.findById(userId)).thenReturn(expectedUser);
    
    // When: invoke the method under test
    User actualUser = userService.getUserById(userId);
    
    // Then: verify the result
    assertNotNull(actualUser);
    assertEquals(expectedUser.getName(), actualUser.getName());
}
```

### BCDE principles
**Detection mode**: semantic

| Principle | Description |
|------|------|
| B - Border | Boundary-value testing (loop boundaries, numeric boundaries) |
| C - Correct | Correct input produces the expected result |
| D - Design | Write tests together with the design document |
| E - Error | Erroneous input produces the expected error output |

### Test coverage (MULT-GEN-208)
**Detection mode**: semantic

- Statement coverage >= 70%
- Core-module statement coverage = 100%
- Branch coverage >= 80%

### Testing anti-patterns
**Detection mode**: semantic

```java
// Wrong: verify with System.out (MULT-GEN-204)
@Test
public void testBad() {
    User user = userService.getUserById(1L);
    System.out.println(user.getName());  // Forbidden!
}

// Correct: verify with asserts
@Test
public void testGood() {
    User user = userService.getUserById(1L);
    assertNotNull(user);
    assertEquals("expected", user.getName());
}

// Wrong: test cases depend on each other (MULT-GEN-205)
@Test
public void testA() {
    // Set a static variable
    TestContext.value = 1;
}

@Test
public void testB() {
    // Depends on testA's result
    assertEquals(1, TestContext.value);  // Forbidden!
}
```

## Project structure guidelines

### Application layering
**Detection mode**: semantic

**Standard layered architecture (MULT-GEN-193):**

```
Open API layer → Client display layer → Web layer → Service layer → Manager layer → DAO layer
```

| Layer | Responsibility | Description |
|------|------|------|
| Open API layer | Wraps Service and exposes RPC/HTTP interfaces | Gateway security control, traffic control |
| Client display layer | Template rendering and display | velocity, JS, JSP, mobile |
| Web layer | Access control and forwarding, basic parameter validation | No business reuse; keep processing simple |
| Service layer | Concrete business logic | Business encapsulation, composed calls |
| Manager layer | Common business processing, third-party preprocessing | Shared Service capabilities (cache, middleware), composition and reuse of multiple DAOs |
| DAO layer | Data access | MySQL, Oracle, Hbase, etc. |

### Exception handling by layer (MULT-GEN-194)
**Detection mode**: semantic

| Layer | Exception handling |
|------|-------------|
| DAO layer | catch → throw DAOException, no logging |
| Service layer | Must log to disk with parameter information |
| Manager layer | Like DAO when co-located; like Service when independently deployed |
| Web layer | Do not rethrow; redirect to a friendly error page |
| API layer | Convert to an error code + error message |

### Domain model conventions (MULT-GEN-195)
**Detection mode**: semantic

| Model | Description | Use case |
|------|------|---------|
| DO | Object corresponding to a database table | Passed upward by the DAO layer |
| DTO | Data transfer object | Passed outward by Service/Manager |
| BO | Business object | Business-logic encapsulation in the Service layer |
| Query | Query request object | Receives query parameters at each layer; Map is forbidden with more than 2 parameters |
| VO | Display-layer object | Passed from Web to the template engine |

### Internal library dependency conventions (MULT-GEN-196/197/198)
**Detection mode**: semantic

**GAV format conventions:**

| Convention | Description | Example |
|------|------|------|
| GroupID | com.{company/BU}.business-line.[sub-business-line] | `com.example.order` |
| ArtifactID | product-line-name-module-name | `passenger-order-api` |
| Version | major.minor.patch | `1.0.0` |

**Version numbering rules:**

| Version type | Description |
|---------|------|
| Major version | Incompatible API changes |
| Minor version | Backward-compatible feature additions |
| Patch version | Backward-compatible bug fixes |

**Dependency rules:**

```xml
<!-- Wrong: depend on a SNAPSHOT version -->
<dependency>
    <version>1.0.0-SNAPSHOT</version>  <!-- Forbidden! -->
</dependency>

<!-- Correct: depend on a release version -->
<dependency>
    <version>1.0.0</version>
</dependency>

<!-- Correct: use a shared version variable -->
<dependency>
    <version>${spring.version}</version>
</dependency>
```

### Design conventions (MULT-GEN-199/200/201/202)
**Detection mode**: semantic

| Rule | Description |
|------|------|
| Storage design review | Storage designs and data structures must be reviewed and documented |
| State diagrams | Use a state diagram when a business object has more than 3 states |
| Single responsibility | Class design follows the single-responsibility principle |
| Composition over inheritance | Prefer aggregation/composition; use inheritance cautiously |
