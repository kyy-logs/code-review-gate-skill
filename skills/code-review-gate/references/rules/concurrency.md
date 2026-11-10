# Concurrency guidelines

## Thread pool creation
**Detection mode**: semantic

**Do not create thread pools with Executors (MULT-CONC-001):**

```java
// Wrong: may cause OOM
ExecutorService executor = Executors.newFixedThreadPool(10);

// Correct: set all parameters explicitly
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

## SimpleDateFormat thread safety
**Detection mode**: semantic

```java
// Wrong: not thread-safe
private static final SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");

// Correct option 1: ThreadLocal
private static final ThreadLocal<SimpleDateFormat> sdf = 
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// Correct option 2: use Java 8 DateTimeFormatter (recommended)
private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
```

## Lock ordering
**Detection mode**: semantic

**Locking multiple resources must follow a consistent order to prevent deadlocks (MULT-CONC-002):**

```java
// Wrong: may deadlock
public void transfer(Account from, Account to, int amount) {
    synchronized (from) {
        synchronized (to) {
            from.debit(amount);
            to.credit(amount);
        }
    }
}

// Correct: lock in a fixed order
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

## Concurrent modification
**Detection mode**: semantic

**Concurrent modification of the same record must use a lock or optimistic locking (MULT-CONC-003):**

```java
// Optimistic locking approach
@Update("UPDATE account SET balance = #{balance}, version = version + 1 WHERE id = #{id} AND version = #{version}")
int updateWithVersion(Account account);

// Retry logic (at least 3 times)
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

## TOCTOU protection
**Detection mode**: semantic

**Check-Then-Act operations must be atomic (MULT-CONC-012):**

```java
// Wrong: non-atomic operation
if (account.getBalance() >= amount) {  // Check
    account.debit(amount);  // Act - the balance may have changed!
}

// Correct: use a database optimistic lock or distributed lock
@Update("UPDATE account SET balance = balance - #{amount} WHERE id = #{id} AND balance >= #{amount}")
int debitWithCheck(@Param("id") Long id, @Param("amount") Long amount);
```

## High-concurrency optimization
**Detection mode**: semantic

**In high-concurrency code, do not use equality checks as interruption/exit conditions (MULT-CONC-004):**

```java
// Wrong: equality check may never become true
while (count == 0) {
    // may never exit
}

// Correct: use a range check
while (count > 0) {
    // explicit exit condition
}
```

## Singleton thread safety
**Detection mode**: semantic

**Singleton objects must be thread-safe (MULT-CONC-005):**

```java
// Double-checked locking (requires volatile)
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

## Thread resources
**Detection mode**: semantic

**Thread resources must be provided through thread pools; do not create threads explicitly (MULT-CONC-007):**

```java
// Wrong
new Thread(new Runnable() {
    @Override
    public void run() { }
}).start();

// Correct
executor.execute(() -> {
    // ...
});
```

## Random in multithreaded code
**Detection mode**: semantic

**Avoid sharing Random across threads; on JDK 7+ use ThreadLocalRandom (MULT-CONC-011):**

```java
// Wrong
Random random = new Random();
int value = random.nextInt(100);

// Correct
int value = ThreadLocalRandom.current().nextInt(100);
```
