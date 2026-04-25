---
name: java-testing
description: |
  Use ONLY when user explicitly requests Java test code, JUnit/Mockito/AssertJ configuration,
  test failure diagnosis, or coverage improvement for Java projects.

  Triggers: "write test java", "JUnit", "Mockito", "AssertJ", "coverage java",
  "flaky test java", "Spring Boot test", "Testcontainers", "test slice", "jacoco".

  Do NOT activate for: general Java coding without test context, Maven/Gradle build
  configuration outside test scope, Spring bean wiring, or non-test dependency issues.
origin: ECC
---

# Java Testing (Agent Skill)

Agent-focused testing workflow for modern Java (17+) using JUnit 5 with Mockito, the industry-standard combination for Java testing.

## When to Use

- Writing new Java tests or fixing existing tests
- Designing unit/integration test coverage for Java components
- Adding test coverage, CI gating, or regression protection
- Configuring JUnit 5 / Mockito workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing Spring Boot, REST APIs, or library code

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Java projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (no DI, global state, static method chains, no interfaces)
- **No test framework** is detected in the project (no JUnit/Mockito in pom.xml or build.gradle)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or components
- A **required test dependency** (JUnit, Mockito, AssertJ) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer constructor injection and mocks over global state.
- **Test layout**: `src/test/java/` with same package structure as source, `src/test/resources/`.
- **Mocks vs stubs**: Mockito mocks for behavior verification, stubs for state.
- **Parametrized tests**: `@ParameterizedTest` with `@ValueSource`, `@CsvSource`, `@MethodSource`.
- **CI signal**: run subset first, then full suite with `--fail-if-no-tests`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Java version (17+) and build tool (Maven/Gradle).
2. Check for existing test files (`src/test/java/`) to infer package structure and style (JUnit 5, AssertJ, Mockito).
3. Analyze the code under test: identify public API surface, side effects, Spring annotations, and concurrency.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / value objects**: unit tests only, no mocks needed. Use `@ParameterizedTest` with `@CsvSource`.
- **External dependencies (DB, HTTP, filesystem)**: use Mockito; prefer Testcontainers for real DB integration tests.
- **Spring Boot components**: use Test Slices (`@WebMvcTest`, `@DataJpaTest`, `@RestClientTest`) instead of heavy `@SpringBootTest`.
- **Async code**: use `CompletableFuture` testing or Awaitility for bounded waits.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem, network)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable at code boundary (@Inject/@Autowired, constructor DI, interface)?
  → Yes → Mock at boundary (Mockito @Mock + @InjectMocks)
  → No  → Q3

Q3: Needs real behavior verification (SQL, JPA, transactions)?
  → Yes → @DataJpaTest / Testcontainers (real DB in Docker)
  → No  → Use fake/stub implementation

Q4: Async/concurrent (CompletableFuture, @Async, reactive)?
  → Yes → Awaitility for bounded waits, StepVerifier for reactive
  → No  → Synchronous test sufficient

Q5: Spring MVC/REST controller?
  → Yes → @WebMvcTest with MockMvc (10-100x faster than @SpringBootTest)
  → No  → Standard unit test with JUnit 5
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty collections, `null`, `Optional.empty()`, max integer/string length.
3. **Error cases**: exceptions (`assertThrows`), validation errors, 4xx/5xx responses.
4. **State & concurrency**: mutable shared state, thread-safety, transaction rollback.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / E2E
- [ ] Framework: JUnit 5 + Mockito + AssertJ
- [ ] Mocking: Yes/No — Mockito / Testcontainers
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
# Maven
mvn test -Dtest=ClassName#methodName
# Gradle
./gradlew test --tests "ClassName.methodName"
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `mvn test jacoco:report` / `./gradlew test jacocoTestReport`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile without errors (`mvn test-compile` / `./gradlew compileTestJava`).
- [ ] Each test has exactly one logical assertion focus (use `assertAll` for grouped assertions).
- [ ] Mocks are reset between tests (`@MockitoSettings` or `@BeforeEach`).
- [ ] No `Thread.sleep` used for synchronization (use Awaitility).
- [ ] Flaky test guardrails applied (`@TempDir`, deterministic data, `@Tag` separation).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```java
// src/test/java/com/example/AddTest.java
class AddTest {
    @Test // RED
    void addsTwoNumbers() {
        assertEquals(5, Add.add(2, 3));
    }
}

// src/main/java/com/example/Add.java
public class Add { // GREEN
    public static int add(int a, int b) {
        return a + b;
    }
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (JUnit 5)

```java
// src/test/java/com/example/CalculatorTest.java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    @Test
    void addsTwoNumbers() {
        assertEquals(5, Calculator.add(2, 3));
    }
}
```

### Lifecycle (JUnit 5)

```java
// src/test/java/com/example/UserStoreTest.java
import org.junit.jupiter.api.*;
import java.util.*;

class UserStoreTest {
    private UserStore store;

    @BeforeEach
    void setUp() {
        store = new UserStore();
        store.seed(List.of(new User("alice"), new User("bob")));
    }

    @Test
    void findsExistingUser() {
        Optional<User> user = store.find("alice");
        assertTrue(user.isPresent());
        assertEquals("alice", user.get().name());
    }
}
```

### Mocking (Mockito)

```java
// src/test/java/com/example/NotifierTest.java
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import static org.mockito.Mockito.*;

class NotifierTest {
    @Test
    void sendsNotifications() {
        Notifier notifier = mock(Notifier.class);
        Service service = new Service(notifier);

        service.publish("hello");

        verify(notifier, times(1)).send("hello");
    }
}
```

### Mockito with Annotations

```java
// src/test/java/com/example/OrderServiceTest.java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
    @Mock
    private PaymentGateway paymentGateway;

    @InjectMocks
    private OrderService orderService;

    @Test
    void processesPayment() {
        when(paymentGateway.charge(anyDouble())).thenReturn(true);

        boolean result = orderService.processOrder(100.0);

        assertTrue(result);
        verify(paymentGateway).charge(100.0);
    }
}
```

### Parametrized Test

```java
// src/test/java/com/example/MathTest.java
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import static org.junit.jupiter.api.Assertions.*;

class MathTest {
    @ParameterizedTest
    @CsvSource({
        "1, 2, 3",
        "-1, 1, 0",
        "0, 0, 0",
        "100, 200, 300"
    })
    void addsNumbers(int a, int b, int expected) {
        assertEquals(expected, Math.add(a, b));
    }
}
```

### Exception Testing

```java
// src/test/java/com/example/ValidationTest.java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ValidationTest {
    @Test
    void throwsOnNegativeAge() {
        assertThrows(IllegalArgumentException.class,
            () -> Validator.validateAge(-1));
    }

    @Test
    void throwsWithMessage() {
        Exception ex = assertThrows(IllegalArgumentException.class,
            () -> Validator.validateAge(-1));
        assertTrue(ex.getMessage().contains("non-negative"));
    }
}
```

### AssertJ Fluent Assertions

```java
// src/test/java/com/example/UserTest.java
import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.*;

class UserTest {
    @Test
    void userHasCorrectProperties() {
        User user = new User("alice", "alice@example.com");

        assertThat(user.name()).isEqualTo("alice");
        assertThat(user.email()).endsWith("@example.com");
        assertThat(user.roles()).contains("user");
    }
}
```

## Build Configuration

### Maven

```xml
<!-- pom.xml -->
<dependencies>
    <dependency>
        <groupId>org.junit.jupiter</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>5.12.0</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>5.16.0</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.assertj</groupId>
        <artifactId>assertj-core</artifactId>
        <version>3.27.0</version>
        <scope>test</scope>
    </dependency>
    <!-- Integration testing -->
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>testcontainers</artifactId>
        <version>1.20.0</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.awaitility</groupId>
        <artifactId>awaitility</artifactId>
        <version>4.2.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.5</version>
        </plugin>
    </plugins>
</build>
```

### Gradle

```kotlin
// build.gradle.kts
dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.12.0")
    testImplementation("org.mockito:mockito-core:5.16.0")
    testImplementation("org.assertj:assertj-core:3.27.0")
    testImplementation("org.testcontainers:testcontainers:1.20.0")
    testImplementation("org.awaitility:awaitility:4.2.0")
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "skipped", "failed")
    }
}
```

## Running Tests

```bash
mvn test                           # run all tests
mvn test -Dtest=CalculatorTest     # run single test class
mvn test -Dtest=CalculatorTest#addsTwoNumbers  # run single method
mvn test -Dtest="*Test"            # wildcard pattern
mvn test -pl module-name           # run tests in a module

./gradlew test                     # run all tests
./gradlew test --tests "*CalculatorTest*"  # filter by pattern
./gradlew test --tests "*CalculatorTest.addsTwoNumbers"  # single test
./gradlew test --info              # verbose output
```

## Debugging Failures

1. Re-run the single failing test with `@Tag` filtering or `--tests` pattern.
2. Pass `-X` to Maven or `--stacktrace` to Gradle for full stack traces.
3. Add breakpoints and run with debugger (`mvn test -Dmaven.surefire.debug`).
4. Use `System.out` (captured by surefire by default).
5. Expand to full suite once the root cause is fixed.

## Coverage

### JaCoCo (Maven)

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
```

### JaCoCo (Gradle)

```kotlin
plugins {
    id("jacoco")
}

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}
```

```bash
mvn test jacoco:report
./gradlew test jacocoTestReport
```

## CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { java-version: '21', distribution: 'temurin' }
      - run: mvn test jacoco:report
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: target/surefire-reports/*.xml }
```

## Flaky Tests Guardrails

- Never use `Thread.sleep()` for synchronization; use `awaitility`.
- Make temp directories unique per test with `@TempDir`.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use `java.time.Clock` injection for time-dependent code.
- Use `awaitility` for async assertions with timeout.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```java
// src/test/java/com/example/ValidatorTest.java
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;

class ValidatorTest {
    @ParameterizedTest
    @ValueSource(strings = {"", " ", "a".repeat(10001)})
    void rejectsInvalidInput(String input) {
        assertThrows(IllegalArgumentException.class, () -> validator.validate(input));
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```java
// src/test/java/com/example/CalculatorTest.java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    @Test
    void throwsOnDivideByZero() {
        assertThrows(ArithmeticException.class, () -> calculator.divide(10, 0));
    }
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```java
// src/test/java/com/example/ConnectionTest.java
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ConnectionTest {
    @Test
    void stateTransitionsAreCorrect() {
        Connection conn = new Connection();
        assertEquals(State.CLOSED, conn.getState());
        conn.open();
        assertEquals(State.OPEN, conn.getState());
        conn.close();
        assertEquals(State.CLOSED, conn.getState());
        // Idempotency
        conn.close();
        assertEquals(State.CLOSED, conn.getState());
    }
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `assertAll("description", () -> ...)` or `assertThat(...).as("description").*`.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Ensure `assertThrows` for exceptions, test `null`/empty/out-of-range inputs.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at architectural boundaries (DB, HTTP), not internal collaborators.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long, complex test methods with no clear arrange/act/assert structure. *Fix: Follow AAA (Arrange-Act-Assert), use `@DisplayName` for intent.*
- **Flaky Test**: Non-deterministic results from time, order, or shared state. *Fix: Use `@TempDir`, `Clock.fixed()`, `@TestMethodOrder` to guarantee determinism.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Use constructor injection for testable components
- Use `@Nested` for hierarchical test organization
- Separate unit vs integration tests with `@Tag` or separate source sets
- Use `assertAll()` for grouped assertions
- Use `@TempDir` for temporary files
- Prefer `AssertJ` for fluent, readable assertions

### DON'T

- Don't use `Thread.sleep()` for synchronization
- Don't depend on real time or network in unit tests
- Don't use `PowerMock` — refactor code instead
- Don't mock value objects or simple data classes
- Don't test private methods directly
- Don't write slow tests that depend on Spring context for unit tests

### Common Pitfalls

- **Leaking test state** → Reset mocks with `@MockitoSettings` or `@BeforeEach`.
- **Relying on wall clock** → Inject `Clock` and use `Clock.fixed()`.
- **Flaky async tests** → Use `awaitility` with bounded waits.
- **Heavy Spring context** → Use `@WebMvcTest` or slice tests instead of full context.
- **Over-mocking** → Prefer real implementations for value objects and pure functions.
- **Missing CI coverage gates** → Add JaCoCo with `haltonFailure` and minimum coverage.
- **Slow parametrized tests** → Limit `@MethodSource` to representative cases in CI.

## Optional Appendix: Advanced Testing

### Testcontainers (Integration Tests)

```java
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.*;

@Testcontainers
class DatabaseTest {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Test
    void connectsToDatabase() {
        // postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()
    }
}
```

### ArchUnit (Architecture Tests)

```java
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.*;

@AnalyzeClasses(packages = "com.example")
class ArchitectureTest {
    @ArchTest
    static final ArchRule services_should_not_depend_on_controllers =
        noClasses().that().resideInAPackage("..service..")
            .should().dependOnClassesThat()
            .resideInAPackage("..controller..");
}
```

### Spring Boot Test Slices

Avoid slow `@SpringBootTest` for unit tests. Use targeted slices that only load the relevant Spring context:

```java
// src/test/java/com/example/UserControllerTest.java
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(UserController.class)
class UserControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;

    @Test
    void returnsUser() throws Exception {
        when(userService.findById(1L)).thenReturn(new User("alice"));

        mockMvc.perform(get("/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("alice"));
    }
}
```

| Slice Annotation | Loads | Use For |
|------------------|-------|---------|
| `@WebMvcTest` | Web layer only | Controller tests |
| `@DataJpaTest` | JPA + datasource | Repository tests |
| `@RestClientTest` | REST client + Jackson | `RestTemplate`/`WebClient` tests |
| `@JsonTest` | Jackson/Gson only | JSON serialization tests |
| `@SpringBootTest` | Full context | Integration / E2E tests only |

> **Performance:** Slices typically start 10-100x faster than full `@SpringBootTest`.

## Alternatives to JUnit 5

- **TestNG**: group-based test configuration, less common now.
- **Spock**: Groovy-based, expressive specification syntax.
- **Kotest**: Kotlin-native, property-based testing built in.

### Mutation Testing (PIT)

Mutation testing verifies that your tests actually catch bugs by introducing small code mutations (e.g., changing `+` to `-`, `>` to `>=`) and checking if tests fail. High mutation score = tests catch real bugs.

```xml
<!-- pom.xml: pitest-maven plugin -->
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.17.0</version>
    <configuration>
        <targetClasses>com.example.*</targetClasses>
    </configuration>
</plugin>
```

```bash
mvn org.pitest:pitest-maven:mutationCoverage
# Report: target/pit-reports/index.html
```

> **Target**: ≥80% mutation score for business logic. Focus on uncovered mutations, not just line coverage.
