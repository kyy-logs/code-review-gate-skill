# 单元测试与工程结构规范

## 单元测试规范

### AIR原则

**单元测试必须遵守AIR原则（MULT-GEN-203）：**

| 原则 | 说明 |
|------|------|
| A - Automatic | 全自动执行，无需人工干预 |
| I - Independent | 测试用例之间独立，不能互相调用或依赖 |
| R - Repeatable | 可重复执行，结果稳定一致 |

### 测试规范

```java
// 正确的单元测试（MULT-GEN-204）
@Test
public void testGetUserById() {
    // Given: 准备测试数据
    Long userId = 1L;
    User expectedUser = new User(userId, "test");
    when(userDao.findById(userId)).thenReturn(expectedUser);
    
    // When: 执行被测方法
    User actualUser = userService.getUserById(userId);
    
    // Then: 验证结果
    assertNotNull(actualUser);
    assertEquals(expectedUser.getName(), actualUser.getName());
}
```

### BCDE原则

| 原则 | 说明 |
|------|------|
| B - Border | 边界值测试（循环边界、数值边界） |
| C - Correct | 正确的输入得到预期结果 |
| D - Design | 与设计文档结合编写测试 |
| E - Error | 错误输入预期错误输出 |

### 测试覆盖率（MULT-GEN-208）

- 语句覆盖率 >= 70%
- 核心模块语句覆盖率 = 100%
- 分支覆盖率 >= 80%

### 测试禁忌

```java
// 错误：使用System.out验证（MULT-GEN-204）
@Test
public void testBad() {
    User user = userService.getUserById(1L);
    System.out.println(user.getName());  // 禁止！
}

// 正确：使用assert验证
@Test
public void testGood() {
    User user = userService.getUserById(1L);
    assertNotNull(user);
    assertEquals("expected", user.getName());
}

// 错误：测试用例互相依赖（MULT-GEN-205）
@Test
public void testA() {
    // 设置静态变量
    TestContext.value = 1;
}

@Test
public void testB() {
    // 依赖testA的结果
    assertEquals(1, TestContext.value);  // 禁止！
}
```

## 工程结构规范

### 应用分层

**标准分层架构（MULT-GEN-193）：**

```
开放接口层 → 终端显示层 → Web层 → Service层 → Manager层 → DAO层
```

| 层级 | 职责 | 说明 |
|------|------|------|
| 开放接口层 | 封装Service暴露RPC/HTTP接口 | 网关安全控制、流量控制 |
| 终端显示层 | 模板渲染执行显示 | velocity、JS、JSP、移动端 |
| Web层 | 访问控制转发、基本参数校验 | 不复用业务简单处理 |
| Service层 | 具体业务逻辑 | 业务封装、组合调用 |
| Manager层 | 通用业务处理、第三方预处理 | Service通用能力下沉（缓存、中间件）、多DAO组合复用 |
| DAO层 | 数据交互 | MySQL、Oracle、Hbase等 |

### 异常处理分层（MULT-GEN-194）

| 层级 | 异常处理方式 |
|------|-------------|
| DAO层 | catch → throw DAOException，不打日志 |
| Service层 | 必须记录日志到磁盘，带参数信息 |
| Manager层 | 同机如DAO，独立部署如Service |
| Web层 | 不继续抛，跳转友好错误页面 |
| 接口层 | 转换为错误码+错误信息 |

### 领域模型规约（MULT-GEN-195）

| 模型 | 说明 | 使用场景 |
|------|------|---------|
| DO | 数据库表结构对应对象 | DAO层向上传输 |
| DTO | 数据传输对象 | Service/Manager对外传输 |
| BO | 业务对象 | Service层业务逻辑封装 |
| Query | 查询请求对象 | 各层接收查询参数，超2参数禁用Map |
| VO | 显示层对象 | Web向模板引擎传输 |

### 二方库依赖规范（MULT-GEN-196/197/198）

**GAV格式规范：**

| 规范 | 说明 | 示例 |
|------|------|------|
| GroupID | com.{公司/BU}.业务线.[子业务线] | `com.example.order` |
| ArtifactID | 产品线名-模块名 | `passenger-order-api` |
| Version | 主版本.次版本.修订号 | `1.0.0` |

**版本号规则：**

| 版本类型 | 说明 |
|---------|------|
| 主版本 | 不兼容的API修改 |
| 次版本 | 向下兼容的功能新增 |
| 修订号 | 向下兼容的问题修复 |

**依赖规则：**

```xml
<!-- 错误：依赖SNAPSHOT版本 -->
<dependency>
    <version>1.0.0-SNAPSHOT</version>  <!-- 禁止！ -->
</dependency>

<!-- 正确：依赖正式版本 -->
<dependency>
    <version>1.0.0</version>
</dependency>

<!-- 正确：统一版本变量 -->
<dependency>
    <version>${spring.version}</version>
</dependency>
```

### 设计规约（MULT-GEN-199/200/201/202）

| 规则 | 说明 |
|------|------|
| 存储方案评审 | 存储方案和数据结构需评审并沉淀文档 |
| 状态图表达 | 业务对象状态超过3个用状态图表达 |
| 单一职责 | 类设计符合单一职责原则 |
| 组合优于继承 | 优先聚合/组合，谨慎继承 |
