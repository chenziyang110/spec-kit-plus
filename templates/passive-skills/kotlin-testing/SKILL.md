---
name: kotlin-testing
description: |
  Use ONLY when user explicitly requests Kotlin test code, Kotest/MockK configuration,
  test failure diagnosis, or coverage improvement for Kotlin projects.

  Triggers: "write test kotlin", "kotest", "mockk", "coroutine test",
  "kotlin coverage", "runTest", "property testing kotlin", "ActivityScenario".

  Do NOT activate for: general Kotlin coding without test context, Gradle build
  errors, Kotlin multiplatform setup, or Android UI implementation without test needs.
origin: ECC
---

# Kotlin Testing (Agent Skill)

Agent-focused testing workflow for modern Kotlin using Kotest, the most feature-rich Kotlin-native test framework, with MockK for mocking.

## When to Use

- Writing new Kotlin tests or fixing existing tests
- Designing unit/integration test coverage for Kotlin components
- Adding test coverage, CI gating, or regression protection
- Configuring Kotest/MockK workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing Android, Ktor, Spring Boot, or Kotlin Multiplatform

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Kotlin projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (object singletons everywhere, no DI, hard-coded network calls in ViewModels)
- **No test framework** is detected (no Kotest/MockK in build.gradle.kts, no test source set)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or classes
- A **required test dependency** (Kotest, MockK, kotlinx-coroutines-test) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Kotest styles**: `FunSpec`, `StringSpec`, `DescribeSpec`, `BehaviorSpec`, etc.
- **Property testing**: built-in property-based testing via `forAll`.
- **Test layout**: `src/test/kotlin/` mirroring source package structure.
- **Mocks**: `MockK` with Kotlin-friendly DSL for mocks, spies, and co-routines.
- **CI signal**: `./gradlew test` with `--info` output.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Kotlin version (2.0+) and build tool (Gradle).
2. Check for existing test files (`src/test/kotlin/`) to infer style (Kotest, JUnit 5, MockK).
3. Analyze the code under test: identify public API surface, coroutines (`suspend` functions), side effects, and Android/Ktor/Spring context.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / value objects**: unit tests only, no mocks needed. Use Kotest `FunSpec` or JUnit 5 `@Test`.
- **External dependencies (DB, HTTP, filesystem)**: use **MockK** for Kotlin-friendly mocking; prefer `kotlinx-coroutines-test` for coroutine testing.
- **Android components**: use `ActivityScenario` for UI tests; use `UnconfinedTestDispatcher` / `StandardTestDispatcher` for coroutine tests.
- **Async / coroutine code**: use `runTest { }` from `kotlinx-coroutines-test`; never use `runBlocking` in tests.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem, network)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (interface, DI, Koin/Kodein)?
  → Yes → Mock at boundary (MockK mockk<T>, coEvery/coVerify)
  → No  → Q3

Q3: Coroutine/suspend function?
  → Yes → runTest { } with StandardTestDispatcher
  → No  → Q4

Q4: Android component (Activity, ViewModel)?
  → Yes → ActivityScenario + StandardTestDispatcher
  → No  → Q5

Q5: Property-based needed?
  → Yes → Kotest forAll / checkAll
  → No  → Standard FunSpec/DescribeSpec
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty lists, `null`, empty strings, `Int.MAX_VALUE`, `LocalDate.MIN`.
3. **Error cases**: exceptions (`shouldThrow`), validation errors, cancellation exceptions, timeout scenarios.
4. **Concurrency**: coroutine leaks, flow emission ordering, shared mutable state in `MutableStateFlow`.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / Android UI
- [ ] Framework: Kotest + MockK (or JUnit 5 + MockK for mixed projects)
- [ ] Mocking: Yes/No — MockK / fakes
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
./gradlew test --tests "*ClassName*"
./gradlew test --info
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `./gradlew test jacocoTestReport`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`./gradlew test`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are cleared between tests (`clearAllMocks()` in `afterTest`).
- [ ] No `Thread.sleep` used in coroutine tests (use `runTest` with `advanceTimeBy`).
- [ ] Flaky test guardrails applied (deterministic data, no real network in unit tests).

## TDD Workflow

```kotlin
// src/test/kotlin/com/example/AddTest.kt
fun add(a: Int, b: Int): Int = TODO() // stub

class AddTest : FunSpec({
    test("adds two numbers") { // RED
        add(2, 3) shouldBe 5
    }
})

// src/main/kotlin/com/example/Math.kt
fun add(a: Int, b: Int): Int = a + b // GREEN

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (Kotest FunSpec)

```kotlin
import io.kotest.core.spec.style.FunSpec
import io.kotest.matchers.shouldBe

class CalculatorTest : FunSpec({
    test("adds two numbers") {
        Calculator.add(2, 3) shouldBe 5
    }

    test("handles negative numbers") {
        Calculator.add(-1, 1) shouldBe 0
    }
})
```

### DescribeSpec (BDD Style)

```kotlin
import io.kotest.core.spec.style.DescribeSpec
import io.kotest.matchers.shouldBe
import io.kotest.matchers.shouldNotBe

class UserStoreTest : DescribeSpec({
    lateinit var store: UserStore

    beforeTest {
        store = UserStore()
        store.seed(listOf(User("alice"), User("bob")))
    }

    describe("find user") {
        it("should return existing user") {
            val user = store.find("alice")
            user shouldNotBe null
            user?.name shouldBe "alice"
        }

        it("should return null for missing user") {
            store.find("charlie") shouldBe null
        }
    }
})
```

### Mocking (MockK)

```kotlin
import io.mockk.*
import io.kotest.core.spec.style.FunSpec
import io.kotest.matchers.shouldBe

interface Notifier {
    fun send(message: String)
}

class Service(private val notifier: Notifier) {
    fun publish(message: String) = notifier.send(message)
}

class ServiceTest : FunSpec({
    test("sends notifications") {
        val notifier = mockk<Notifier>()
        every { notifier.send("hello") } just Runs
        val service = Service(notifier)

        service.publish("hello")

        verify(exactly = 1) { notifier.send("hello") }
    }
})
```

### Coroutine Test

```kotlin
import io.kotest.core.spec.style.FunSpec
import io.kotest.matchers.shouldBe
import io.kotest.assertions.timing.eventually
import kotlin.time.Duration.Companion.seconds

class ApiTest : FunSpec({
    test("fetches user data") {
        eventually(5.seconds) {
            val user = fetchUser("1")
            user.name shouldBe "alice"
        }
    }
})
```

### Property-Based Testing (Kotest)

```kotlin
import io.kotest.core.spec.style.FunSpec
import io.kotest.property.Arb
import io.kotest.property.arbitrary.int
import io.kotest.property.forAll
import io.kotest.matchers.shouldBe

class MathPropertyTest : FunSpec({
    test("add is commutative") {
        forAll(Arb.int(), Arb.int()) { a, b ->
            Math.add(a, b) == Math.add(b, a)
        }
    }
})
```

### StringSpec (Simple Tests)

```kotlin
import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.string.shouldContain

class ValidationTest : StringSpec({
    "should reject negative age" {
        shouldThrow<IllegalArgumentException> {
            Validator.validateAge(-1)
        }.message shouldContain "non-negative"
    }
})
```

### Data-Driven Test

```kotlin
import io.kotest.core.spec.style.FunSpec
import io.kotest.matchers.shouldBe
import io.kotest.datatest.withData

class MathParamTest : FunSpec({
    context("add function") {
        withData(
            nameFn = { "${it.a} + ${it.b} = ${it.expected}" },
            TestCase(1, 2, 3),
            TestCase(-1, 1, 0),
            TestCase(0, 0, 0),
            TestCase(100, 200, 300),
        ) { (a, b, expected) ->
            Math.add(a, b) shouldBe expected
        }
    }
}) {
    data class TestCase(val a: Int, val b: Int, val expected: Int)
}
```

## Build Configuration (Gradle)

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.0.0"
}

dependencies {
    testImplementation("io.kotest:kotest-runner-junit5:5.9.0")
    testImplementation("io.kotest:kotest-assertions-core:5.9.0")
    testImplementation("io.kotest:kotest-property:5.9.0")
    testImplementation("io.kotest:kotest-framework-datatest:5.9.0")
    testImplementation("io.mockk:mockk:1.13.12")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.10.0")
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
./gradlew test                         # all tests
./gradlew test --tests "*CalculatorTest*"
./gradlew test --info                  # verbose output
./gradlew test --continuous            # watch mode
./gradlew test -Dkotest.tags="Integration"
```

## Coverage

```kotlin
// build.gradle.kts — JaCoCo
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
      - run: ./gradlew test jacocoTestReport
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: '**/test-results/**/*.xml' }
```

## Flaky Tests Guardrails

- Never use `Thread.sleep()` in coroutine tests; use `kotlinx.coroutines.test`.
- Use `UnconfinedTestDispatcher` or `StandardTestDispatcher` for controlled coroutine scope.
- Make temp files unique with `createTempFile()` / `createTempDir()`.
- Mock `kotlinx.datetime.Clock` for time-dependent code.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```kotlin
// src/test/kotlin/com/example/ValidatorTest.kt
class ValidatorTest : FunSpec({
    context("input validation") {
        withData(
            nameFn = { "rejects ${it.name}" },
            TestCase("", "empty"),
            TestCase(" ", "whitespace"),
            TestCase("a".repeat(10001), "too long")
        ) { (input, _) ->
            shouldThrow<IllegalArgumentException> { validator.validate(input) }
        }
    }
}) {
    data class TestCase(val input: String, val name: String)
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```kotlin
class CalculatorTest : FunSpec({
    test("throws on divide by zero") {
        shouldThrow<ArithmeticException> { calculator.divide(10, 0) }
    }
})
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```kotlin
class ConnectionTest : FunSpec({
    test("state transitions are correct") {
        val conn = Connection()
        conn.state shouldBe State.CLOSED
        conn.open()
        conn.state shouldBe State.OPEN
        conn.close()
        conn.state shouldBe State.CLOSED
        // Idempotency
        conn.close()
        conn.state shouldBe State.CLOSED
    }
})
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use Kotest `"value" shouldBe expected` with descriptive test names.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `null` values, exceptions with `shouldThrow<>`, edge inputs.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at architectural boundaries (repositories, services); use `relaxed = true` only when needed.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long test functions with no clear arrange/act/assert structure. *Fix: Follow AAA, choose a consistent spec style (FunSpec/DescribeSpec), keep tests focused.*
- **Flaky Test**: Non-deterministic results from coroutines, time, or shared state. *Fix: Use `runTest { }` with `UnconfinedTestDispatcher`, `clearAllMocks()` between tests.*

## Best Practices

### DO

- Use Kotest style specs that match your team's preference (FunSpec for simple, DescribeSpec for BDD)
- Use `shouldBe`, `shouldNotBe`, `shouldThrow` from Kotest matchers
- Use coroutine test dispatchers instead of `runBlocking`
- Use property-based testing for invariant validation
- Use `withData` for readable parametrized tests

### DON'T

- Don't use `Thread.sleep()` for synchronization in coroutine tests
- Don't mix JUnit 4 and Kotest annotations
- Don't mock value objects or data classes
- Don't use `runBlocking` in tests — use coroutine test dispatchers
- Don't over-use `io.mockk.every` for simple return values

### Common Pitfalls

- **Coroutine leaks** → Always use `runTest` from `kotlinx-coroutines-test`.
- **Flaky time-based tests** → Use `TestDispatcher` with `advanceTimeBy()`.
- **MockK leaks** → Use `clearAllMocks()` in `afterProject` or `afterTest`.
- **Android instrumentation** → Use `@MediumTest` / `@LargeTest` annotations.

### Android Testing (ActivityScenario + Espresso)

```kotlin
// app/src/androidTest/kotlin/LoginActivityTest.kt
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LoginActivityTest {

    @Test
    fun testSuccessfulLogin() {
        val scenario = ActivityScenario.launch(LoginActivity::class.java)

        onView(withId(R.id.emailInput))
            .perform(typeText("user@example.com"))
        onView(withId(R.id.passwordInput))
            .perform(typeText("password123"))
        onView(withId(R.id.loginButton))
            .perform(click())
        onView(withId(R.id.welcomeText))
            .check(matches(withText("Welcome!")))

        scenario.close()
    }
}
```

> **build.gradle.kts dependencies**: Add `androidx.test:core-ktx:1.6.x`, `androidx.test.espresso:espresso-core:3.6.x`, `androidx.test:runner:1.6.x` for androidTest source set.

## Mutation Testing (PIT)

```kotlin
// build.gradle.kts
plugins {
    id("info.solidsoft.pitest") version "1.15.0"
}

pitest {
    targetClasses.set(listOf("com.example.*"))
    mutators.set(listOf("STRONGER"))
    outputFormats.set(listOf("HTML"))
}
```

```bash
./gradlew pitest
# Report: build/reports/pitest/index.html
```

> Mutation testing verifies tests catch bugs by introducing code mutations (e.g., `+` → `-`). **Target ≥80% mutation score** for business logic.

## Alternatives

- **JUnit 5 + MockK**: Simpler setup, JUnit-compatible, good for mixed Java/Kotlin projects.
- **Spek**: Structure-based testing with `@Describe` / `@It` annotations.
- **Turbine**: Kotlin Flow testing.
