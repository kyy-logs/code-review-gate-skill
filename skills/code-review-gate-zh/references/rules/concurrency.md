# 并发处理规范

## 线程池创建

**禁止使用Executors创建线程池（MULT-CONC-001）：**

```java
// 错误：可能导致OOM
ExecutorService executor = Executors.newFixedThreadPool(10);

// 正确：明确设置所有参数
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,  // corePoolSize
    20,  // maximumPoolSize
    60L, // keepAliveTime
    TimeUnit.SECONDS,
    new LinkedBlockingQueue<>(1000),
    new ThreadFactoryBuilder().setNameFormat("worker-%d").build(),
    new ThreadPoolExecutor.CallerRunsPolicy()
);
```

## SimpleDateFormat线程安全

```java
// 错误：线程不安全
private static final SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");

// 正确方案1：ThreadLocal
private static final ThreadLocal<SimpleDateFormat> sdf = 
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// 正确方案2：使用Java 8 DateTimeFormatter（推荐）
private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
```

## 锁顺序

**多资源加锁必须保持一致顺序，防止死锁（MULT-CONC-002）：**

```java
// 错误：可能导致死锁
public void transfer(Account from, Account to, int amount) {
    synchronized (from) {
        synchronized (to) {
            from.debit(amount);
            to.credit(amount);
        }
    }
}

// 正确：按固定顺序加锁
public void transfer(Account from, Account to, int amount) {
    Account first = from.getId() < to.getId() ? from : to;
    Account second = from.getId() < to.getId() ? to : from;
    synchronized (first) {
        synchronized (second) {
            from.debit(amount);
            to.credit(amount);
        }
    }
}
```

## 并发修改

**并发修改同一记录必须加锁或乐观锁（MULT-CONC-003）：**

```java
// 乐观锁方案
@Update("UPDATE account SET balance = #{balance}, version = version + 1 WHERE id = #{id} AND version = #{version}")
int updateWithVersion(Account account);

// 重试逻辑（不少于3次）
int retry = 0;
while (retry < 3) {
    Account account = accountDao.getById(id);
    int updated = accountDao.updateWithVersion(account);
    if (updated > 0) {
        break;
    }
    retry++;
}
```

## TOCTOU防护

**Check-Then-Act操作必须原子化（MULT-CONC-012）：**

```java
// 错误：非原子操作
if (account.getBalance() >= amount) {  // Check
    account.debit(amount);  // Act - 余额可能已变化！
}

// 正确：使用数据库乐观锁或分布式锁
@Update("UPDATE account SET balance = balance - #{amount} WHERE id = #{id} AND balance >= #{amount}")
int debitWithCheck(@Param("id") Long id, @Param("amount") Long amount);
```

## 高并发优化

**高并发避免用"等于"判断作为中断/退出条件（MULT-CONC-004）：**

```java
// 错误：可能无限循环
while (count == 0) {
    // 可能永远不退出
}

// 正确：使用区间判断
while (count > 0) {
    // 有明确退出条件
}
```

## 单例模式线程安全

**单例对象需保证线程安全（MULT-CONC-005）：**

```java
// 双重检查锁（需要volatile）
public class Singleton {
    private static volatile Singleton instance;
    
    private Singleton() { }
    
    public static Singleton getInstance() {
        if (instance == null) {
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

## 线程资源

**线程资源必须通过线程池提供，禁止显式创建线程（MULT-CONC-007）：**

```java
// 错误
new Thread(new Runnable() {
    @Override
    public void run() { }
}).start();

// 正确
executor.execute(() -> {
    // ...
});
```

## Random多线程

**避免Random多线程使用，JDK7+用ThreadLocalRandom（MULT-CONC-011）：**

```java
// 错误
Random random = new Random();
int value = random.nextInt(100);

// 正确
int value = ThreadLocalRandom.current().nextInt(100);
```
