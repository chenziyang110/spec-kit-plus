---
name: swift-testing
description: |
  Use ONLY when user explicitly requests Swift test code, XCTest/Swift Testing configuration,
  test failure diagnosis, or coverage improvement for Swift/Apple-platform projects.

  Triggers: "write test swift", "XCTest", "swift testing", "@Test macro",
  "xcode test", "swift coverage", "XCUITest", "Quick Nimble".

  Do NOT activate for: general Swift coding without test context, SPM/Package.swift
  setup, Xcode project configuration, or SwiftUI/UIKit implementation without test needs.
origin: ECC
---

# Swift Testing (Agent Skill)

Agent-focused testing workflow for modern Swift using XCTest, the official Apple test framework for iOS/macOS/watchOS/tvOS and server-side Swift.

## When to Use

- Writing new Swift tests or fixing existing tests
- Designing unit/integration test coverage for Swift components
- Adding test coverage, CI gating, or regression protection
- Configuring XCTest workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing iOS/macOS UI, REST APIs, or Swift Packages

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Swift projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (tight coupling to UIKit lifecycle, hard-coded UserDefaults, no protocol abstractions)
- **No test target** is configured in Package.swift or Xcode project
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or types
- A **required test dependency** (XCTest, Swift Testing) is not configured in the test target
- The test would require **secrets, real credentials, or production API access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **XCTest**: `XCTestCase` subclasses with `testXxx` methods.
- **Async testing**: `XCTestExpectation` for async code; async/await natively supported.
- **Test layout**: `Tests/` directory at package root, `Sources/` for production code.
- **UI testing**: XCUITest for iOS/macOS UI automation.
- **CI signal**: `xcodebuild test` or `swift test --parallel`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Swift version (5.9+) and test framework (XCTest or Swift Testing).
2. Check for existing test files (`Tests/`, `*Tests.swift`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, `async/await` usage, `@MainActor` requirements, and UI boundaries.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks. Use `XCTestCase` with `XCTAssertEqual` or Swift Testing `@Test`.
- **External dependencies (network, database)**: use protocol-based dependency injection with manual mock structs.
- **Async code**: use `async throws` test methods (Swift 5.5+) or `XCTestExpectation` for legacy callbacks.
- **UI tests**: use XCUITest for iOS/macOS automation; reset app state between tests.
- **Modern projects (Swift 6+)**: prefer Swift Testing framework (`@Test`, `@Suite`, `@Arguments`) over XCTest.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (network, database, filesystem)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable via protocol?
  → Yes → Protocol-based manual mock struct
  → No  → Q3

Q3: Async (async/await, Combine, callbacks)?
  → Yes → async throws test / XCTestExpectation
  → No  → Synchronous test sufficient

Q4: UI interaction (iOS/macOS)?
  → Yes → XCUITest with accessibility identifiers
  → No  → Q5

Q5: Swift 6+ / greenfield project?
  → Yes → Swift Testing (@Test, @Suite, @Arguments)
  → No  → XCTest (XCTAssertEqual, XCTestCase)
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty arrays, `nil`, `0`, `Int.max`, empty strings, `Date.distantPast`.
3. **Error cases**: thrown errors (`throws` / `XCTAssertThrowsError`), `nil` unwrap failures, `Result.failure`.
4. **Concurrency**: `@MainActor` isolation, `Task` cancellation, `Actor` reentrancy.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / UI
- [ ] Framework: XCTest (or Swift Testing for Swift 6+)
- [ ] Mocking: Yes/No — protocol-based manual mocks
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
swift test --filter "ClassName"
swift test --parallel
xcodebuild test -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 16'
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `swift test --enable-code-coverage`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`swift test`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Shared mutable state is reset in `setUp()` / `tearDown()`.
- [ ] No `sleep()` used for synchronization (use `XCTestExpectation` or `async/await`).
- [ ] Flaky test guardrails applied (unique test data, protocol-based DI, `--parallel` stress test).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

```swift
// Tests/AddTests.swift
func add(_ a: Int, _ b: Int) -> Int { fatalError() } // stub

final class AddTests: XCTestCase {
    func testAddsTwoNumbers() { // RED
        XCTAssertEqual(add(2, 3), 5)
    }
}

// Sources/MyLib/Math.swift
func add(_ a: Int, _ b: Int) -> Int { a + b } // GREEN

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test

```swift
import XCTest

final class CalculatorTests: XCTestCase {
    func testAddsTwoNumbers() {
        XCTAssertEqual(Calculator.add(2, 3), 5)
    }

    func testHandlesNegative() {
        XCTAssertEqual(Calculator.add(-1, 1), 0)
    }
}
```

### Setup / Teardown

```swift
final class UserStoreTests: XCTestCase {
    var store: UserStore!

    override func setUp() {
        super.setUp()
        store = UserStore()
        store.seed([User(name: "alice"), User(name: "bob")])
    }

    override func tearDown() {
        store = nil
        super.tearDown()
    }

    func testFindsExistingUser() {
        let user = store.find("alice")
        XCTAssertNotNil(user)
        XCTAssertEqual(user?.name, "alice")
    }
}
```

### Mocking (Manual / Protocol)

```swift
protocol Notifier {
    func send(_ message: String)
}

final class MockNotifier: Notifier {
    var sentMessages: [String] = []

    func send(_ message: String) {
        sentMessages.append(message)
    }
}

final class ServiceTests: XCTestCase {
    func testSendsNotification() {
        let notifier = MockNotifier()
        let service = Service(notifier: notifier)

        service.publish("hello")

        XCTAssertEqual(notifier.sentMessages, ["hello"])
    }
}
```

### Async Test (XCTestExpectation)

```swift
final class ApiTests: XCTestCase {
    func testFetchesUserData() {
        let expectation = XCTestExpectation(description: "fetch user")

        fetchUser(id: "1") { user in
            XCTAssertEqual(user.name, "alice")
            expectation.fulfill()
        }

        wait(for: [expectation], timeout: 2.0)
    }
}
```

### Async/Await Test (Swift 5.5+)

```swift
final class ApiTests: XCTestCase {
    func testFetchesUserData() async throws {
        let user = try await fetchUser(id: "1")
        XCTAssertEqual(user.name, "alice")
    }

    func testHandlesError() async {
        await XCTExpectFailure {
            try? await fetchUser(id: "invalid")
        }
    }
}
```

### Performance Test

```swift
final class PerformanceTests: XCTestCase {
    func testSortingPerformance() {
        let array = (0..<1000).shuffled()
        measure {
            _ = array.sorted()
        }
        // baseline: ~0.001s (adjust per project)
    }
}
```

### Parametrized (Manual Loop)

```swift
final class MathTests: XCTestCase {
    func testAdd() {
        let cases: [(a: Int, b: Int, expected: Int)] = [
            (1, 2, 3),
            (-1, 1, 0),
            (0, 0, 0),
            (100, 200, 300),
        ]
        for (a, b, expected) in cases {
            XCTAssertEqual(Calculator.add(a, b), expected)
        }
    }
}
```

### UI Test (XCUITest)

```swift
final class MyAppUITests: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        continueAfterFailure = false
        app.launch()
    }

    func testLoginButtonExists() {
        let loginButton = app.buttons["Login"]
        XCTAssertTrue(loginButton.exists)
    }

    func testLoginFlow() {
        app.textFields["Email"].tap()
        app.textFields["Email"].typeText("user@example.com")
        app.buttons["Login"].tap()
        XCTAssertTrue(app.staticTexts["Welcome"].waitForExistence(timeout: 5))
    }
}
```

## Swift Testing Framework (Swift 6+)

Apple's modern testing framework is the recommended choice for new Swift 6+ projects. It uses macros for declarative test definition and integrates natively with Swift Package Manager and Xcode 16+.

### Basic Test

```swift
import Testing

@Test("Adds two numbers")
func addTest() {
    #expect(add(2, 3) == 5)
}
```

### Parametrized Test

```swift
import Testing

@Test("Parametrized addition",
    arguments: [(1, 2, 3), (-1, 1, 0), (0, 0, 0), (100, 200, 300)])
func addParametrized(a: Int, b: Int, expected: Int) {
    #expect(add(a, b) == expected)
}
```

### Async Test

```swift
import Testing

@Test("Fetches user data")
func fetchUser() async throws {
    let user = try await fetchUser(id: "1")
    #expect(user.name == "alice")
}
```

### Tagged Tests

```swift
import Testing

@Test(.tags(.integration))
func databaseQuery() async throws {
    // Runs only when explicitly requested via tag filter
}
```

### Running Swift Testing

```bash
swift test                           # discovers @Test automatically
swift test --filter "addTest"
swift test --skip "integration"      # skip tags
```

### Migrating from XCTest

| XCTest | Swift Testing |
|--------|---------------|
| `XCTestCase` | `@Suite` |
| `func testXxx()` | `@Test` |
| `XCTAssertEqual(a, b)` | `#expect(a == b)` |
| `XCTAssertThrowsError` | `#expect(throws: ...) { ... }` |
| `setUp()` | `init()` on `@Suite` |
| `measure { }` | `@Test(.enabled(if: ...))` + manual timing |

## Package.swift Quickstart

```swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MyLibrary",
    products: [
        .library(name: "MyLibrary", targets: ["MyLibrary"]),
    ],
    targets: [
        .target(name: "MyLibrary"),
        .testTarget(
            name: "MyLibraryTests",
            dependencies: ["MyLibrary"]
        ),
    ]
)
```

## Running Tests

```bash
swift test                          # run all tests
swift test --parallel               # parallel execution
swift test --filter "AddTests"      # run specific test class
swift test --filter "testAdd"       # run tests matching pattern
swift test --enable-code-coverage   # with coverage

xcodebuild test \
    -scheme MyApp \
    -destination 'platform=iOS Simulator,name=iPhone 16'
```

## Coverage

```bash
swift test --enable-code-coverage
llvm-cov report \
    .build/debug/MyLibraryPackageTests.xctest/Contents/MacOS/MyLibraryPackageTests \
    --instr-profile=.build/debug/codecov/default.profdata
```

```bash
# Using xccov (Xcode)
xcodebuild -scheme MyApp -destination 'platform=iOS Simulator,name=iPhone 16' \
    -enableCodeCoverage YES test
xcrun xccov view --report --json DerivedData/**/Logs/Test/*.xcresult
```

## CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - run: swift test --enable-code-coverage
      - run: xcrun llvm-cov export -format=lcov .build/debug/*.xctest -instr-profile .build/debug/codecov/default.profdata > coverage.lcov
```

## Flaky Tests Guardrails

- Never use `sleep()` for synchronization; use `XCTestExpectation`.
- Make test data unique per test with UUID-based identifiers.
- Mock network calls using protocol-based dependency injection.
- Use `continueAfterFailure = false` carefully — prefer testing one failure at a time.
- Reset app state between UI tests by launching fresh.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, nil, and just-outside valid ranges.

```swift
// Tests/ValidatorTests.swift
final class ValidatorTests: XCTestCase {
    func testRejectsInvalidInput() {
        XCTAssertThrowsError(try validator.validate("")) { error in
            XCTAssertTrue(error is ValidationError)
        }
        let longInput = String(repeating: "a", count: 10001)
        XCTAssertThrowsError(try validator.validate(longInput))
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```swift
// Tests/CalculatorTests.swift
final class CalculatorTests: XCTestCase {
    func testThrowsOnDivideByZero() {
        XCTAssertThrowsError(try calculator.divide(10, 0))
    }
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```swift
// Tests/ConnectionTests.swift
final class ConnectionTests: XCTestCase {
    func testStateTransitions() {
        let conn = Connection()
        XCTAssertEqual(conn.state, .closed)
        conn.open()
        XCTAssertEqual(conn.state, .open)
        conn.close()
        XCTAssertEqual(conn.state, .closed)
        // Idempotency
        conn.close()
        XCTAssertEqual(conn.state, .closed)
    }
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `XCTAssertEqual(actual, expected, "descriptive message")` or Swift Testing `#expect(actual == expected)`.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `nil` values with `XCTAssertNil`/`XCTAssertNotNil`, `XCTAssertThrowsError` for exceptions.*
- **Mock Overdose**: Too many protocol mocks hiding integration issues. *Fix: Mock only at service boundaries; prefer real implementations for value types.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long `XCTestCase` methods with no clear setup/verify structure. *Fix: Follow AAA, use `setUpWithError()`/`tearDownWithError()`, keep test methods focused.*
- **Flaky Test**: Non-deterministic results from async, UI, or test order. *Fix: Use `XCTestExpectation` with timeouts, `continueAfterFailure = false`, test isolation.*

## Best Practices

### DO

- Use descriptive `testXxx` method names (e.g., `testAdd_WithPositiveNumbers_ReturnsSum`)
- Use `XCTestExpectation` + `wait(for:timeout:)` for async code
- Use `throws` functions to avoid `try?` in tests
- Use `#fileID` / `#line` for helper assertion functions
- Separate unit, integration, and UI tests into separate targets

### DON'T

- Don't use `sleep()` for synchronization
- Don't depend on real network or time in unit tests
- Don't share mutable state between test methods
- Don't test private methods directly — test through public API
- Don't write UI tests that depend on specific screen sizes without layout checks

### Common Pitfalls

- **Flaky async tests** → Always use `XCTestExpectation` with timeout.
- **Shared state** → Reset in `setUp()` / `tearDown()`.
- **Hardcoded delays** → Use `waitForExistence(timeout:)` in UI tests.
- **Network in unit tests** → Mock `URLProtocol` or use protocol-based DI.
- **Slow UI tests** → Mark slow tests with `-[XCUIApplication launch]` per test.
- **Missing coverage gates** → Add `--enable-code-coverage` in CI.

## Optional: Swift Testing Framework (Swift 6+)

The new Swift Testing framework (available in Swift 6+) is the modern alternative:

```swift
import Testing

@Test("Adds two numbers")
func addTest() {
    #expect(add(2, 3) == 5)
}

@Test("Parametrized addition",
    arguments: [(1, 2, 3), (-1, 1, 0), (0, 0, 0)])
func addParametrized(a: Int, b: Int, expected: Int) {
    #expect(add(a, b) == expected)
}
```

## Alternatives

- **Quick + Nimble** (v7.x): BDD-style testing with expressive matchers.
- **Swift Testing**: Apple's new test framework (Swift 6+), modern macro-based API.
