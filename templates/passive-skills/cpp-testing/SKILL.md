---
name: cpp-testing
description: |
  Use ONLY when user explicitly requests C++ test code, GoogleTest/Catch2/CTest configuration,
  test failure diagnosis, or coverage/sanitizer for C++ projects.

  Triggers: "write test cpp", "gtest", "GoogleTest", "catch2", "doctest",
  "C++ coverage", "sanitizer", "ubsan", "asan", "C++ mock".

  Do NOT activate for: general C++ coding without test context, CMake build
  configuration, C++ template/compile errors, or header-only library setup.
origin: ECC
---

# C++ Testing (Agent Skill)

Agent-focused testing workflow for modern C++ (C++17/20) using GoogleTest/GoogleMock with CMake/CTest.

## When to Use

- Writing new C++ tests or fixing existing tests
- Designing unit/integration test coverage for C++ components
- Adding test coverage, CI gating, or regression protection
- Configuring CMake/CTest workflows for consistent execution
- Investigating test failures or flaky behavior
- Enabling sanitizers for memory/race diagnostics

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-C++ projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (global state, hard-coded I/O, no virtual/interface boundaries)
- **No test framework** is detected in CMakeLists.txt (no GTest/Catch2/CTest)
- The request is **ambiguous**: "test my code" or "add tests" without specifying files or classes
- A **required test dependency** (GTest, Catch2) is not declared in CMake
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer dependency injection and fakes over global state.
- **Test layout**: `tests/unit`, `tests/integration`, `tests/testdata`.
- **Mocks vs fakes**: mock for interactions, fake for stateful behavior.
- **CTest discovery**: use `gtest_discover_tests()` for stable test discovery.
- **CI signal**: run subset first, then full suite with `--output-on-failure`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the C++ standard (17/20/23) and build tool (CMake preferred).
2. Check for existing test files (`tests/`, `*_test.cpp`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, memory management patterns, and concurrency.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage/sanitizers, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / value objects**: unit tests only, no mocks needed. Use `TEST`/`TEST_F`.
- **External dependencies (I/O, network)**: use GoogleMock (`EXPECT_CALL`) or fakes for stateful behavior.
- **Memory-critical code**: enable AddressSanitizer (ASan) and UndefinedBehaviorSanitizer (UBSan) in CI.
- **Concurrent code**: use ThreadSanitizer (TSan); avoid sleeps, use condition variables/latches.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (filesystem, network, hardware)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (virtual interface, template parameter, function pointer)?
  → Yes → Mock at boundary (GoogleMock EXPECT_CALL, MOCK_METHOD)
  → No  → Q3

Q3: Needs real behavior (memory, concurrency)?
  → Yes → Integration test + ASan/UBSan/TSan in CI
  → No  → Use fake/test double

Q4: Memory-critical / UB risk?
  → Yes → Enable AddressSanitizer + UndefinedBehaviorSanitizer
  → No  → Standard TEST/TEST_F

Q5: Concurrency test?
  → Yes → ThreadSanitizer + deterministic thread scheduling
  → No  → Standard unit test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty containers, `nullptr`, `std::nullopt`, max container size, numeric limits.
3. **Error cases**: exceptions, error codes, invalid arguments, resource exhaustion.
4. **Memory & concurrency**: memory leaks (use `testing::internal::Leakable` pattern), data races, RAII correctness.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration
- [ ] Framework: GoogleTest + GoogleMock + CMake/CTest
- [ ] Mocking: Yes/No — GoogleMock / fakes
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
ctest --test-dir build --output-on-failure
./build/example_tests --gtest_filter=TestSuite.TestName
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `cmake -S . -B build-cov -DENABLE_COVERAGE=ON && cmake --build build-cov && ctest --test-dir build-cov`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile without errors (`cmake --build build`).
- [ ] Each test has exactly one logical assertion focus (use `ASSERT_*` for preconditions, `EXPECT_*` for checks).
- [ ] Mocks are reset between tests (reconstruct fixtures in `SetUp`).
- [ ] No `sleep` used for synchronization (use condition variables or latches).
- [ ] Flaky test guardrails applied (unique temp dirs, deterministic seeds, ASan/UBSan in CI).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```cpp
// tests/add_test.cpp
#include <gtest/gtest.h>

int Add(int a, int b); // Provided by production code.

TEST(AddTest, AddsTwoNumbers) { // RED
  EXPECT_EQ(Add(2, 3), 5);
}

// src/add.cpp
int Add(int a, int b) { // GREEN
  return a + b;
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (gtest)

```cpp
// tests/calculator_test.cpp
#include <gtest/gtest.h>

int Add(int a, int b); // Provided by production code.

TEST(CalculatorTest, AddsTwoNumbers) {
    EXPECT_EQ(Add(2, 3), 5);
}
```

### Fixture (gtest)

```cpp
// tests/user_store_test.cpp
// Pseudocode stub: replace UserStore/User with project types.
#include <gtest/gtest.h>
#include <memory>
#include <optional>
#include <string>

struct User { std::string name; };
class UserStore {
public:
    explicit UserStore(std::string /*path*/) {}
    void Seed(std::initializer_list<User> /*users*/) {}
    std::optional<User> Find(const std::string &/*name*/) { return User{"alice"}; }
};

class UserStoreTest : public ::testing::Test {
protected:
    void SetUp() override {
        store = std::make_unique<UserStore>(":memory:");
        store->Seed({{"alice"}, {"bob"}});
    }

    std::unique_ptr<UserStore> store;
};

TEST_F(UserStoreTest, FindsExistingUser) {
    auto user = store->Find("alice");
    ASSERT_TRUE(user.has_value());
    EXPECT_EQ(user->name, "alice");
}
```

### Mock (gmock)

```cpp
// tests/notifier_test.cpp
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <string>

class Notifier {
public:
    virtual ~Notifier() = default;
    virtual void Send(const std::string &message) = 0;
};

class MockNotifier : public Notifier {
public:
    MOCK_METHOD(void, Send, (const std::string &message), (override));
};

class Service {
public:
    explicit Service(Notifier &notifier) : notifier_(notifier) {}
    void Publish(const std::string &message) { notifier_.Send(message); }

private:
    Notifier &notifier_;
};

TEST(ServiceTest, SendsNotifications) {
    MockNotifier notifier;
    Service service(notifier);

    EXPECT_CALL(notifier, Send("hello")).Times(1);
    service.Publish("hello");
}
```

### CMake/CTest Quickstart

```cmake
# CMakeLists.txt (excerpt)
cmake_minimum_required(VERSION 3.20)
project(example LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
# Prefer project-locked versions. If using a tag, use a pinned version per project policy.
set(GTEST_VERSION v1.15.2) # Latest stable as of 2025; verify at github.com/google/googletest
FetchContent_Declare(
  googletest
  # Google Test framework (official repository)
  URL https://github.com/google/googletest/archive/refs/tags/${GTEST_VERSION}.zip
)
FetchContent_MakeAvailable(googletest)

add_executable(example_tests
  tests/calculator_test.cpp
  src/calculator.cpp
)
target_link_libraries(example_tests GTest::gtest GTest::gmock GTest::gtest_main)

enable_testing()
include(GoogleTest)
gtest_discover_tests(example_tests)
```

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Running Tests

```bash
ctest --test-dir build --output-on-failure
ctest --test-dir build -R ClampTest
ctest --test-dir build -R "UserStoreTest.*" --output-on-failure
```

```bash
./build/example_tests --gtest_filter=ClampTest.*
./build/example_tests --gtest_filter=UserStoreTest.FindsExistingUser
```

## Debugging Failures

1. Re-run the single failing test with gtest filter.
2. Add scoped logging around the failing assertion.
3. Re-run with sanitizers enabled.
4. Expand to full suite once the root cause is fixed.

## Coverage

Prefer target-level settings instead of global flags.

```cmake
option(ENABLE_COVERAGE "Enable coverage flags" OFF)

if(ENABLE_COVERAGE)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    target_compile_options(example_tests PRIVATE --coverage)
    target_link_options(example_tests PRIVATE --coverage)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(example_tests PRIVATE -fprofile-instr-generate -fcoverage-mapping)
    target_link_options(example_tests PRIVATE -fprofile-instr-generate)
  endif()
endif()
```

GCC + gcov + lcov:

```bash
cmake -S . -B build-cov -DENABLE_COVERAGE=ON
cmake --build build-cov -j
ctest --test-dir build-cov
lcov --capture --directory build-cov --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage.info
genhtml coverage.info --output-directory coverage
```

Clang + llvm-cov:

```bash
cmake -S . -B build-llvm -DENABLE_COVERAGE=ON -DCMAKE_CXX_COMPILER=clang++
cmake --build build-llvm -j
LLVM_PROFILE_FILE="build-llvm/default.profraw" ctest --test-dir build-llvm
llvm-profdata merge -sparse build-llvm/default.profraw -o build-llvm/default.profdata
llvm-cov report build-llvm/example_tests -instr-profile=build-llvm/default.profdata
```

## Sanitizers

```cmake
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
option(ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)
option(ENABLE_TSAN "Enable ThreadSanitizer" OFF)

if(ENABLE_ASAN)
  add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address)
endif()
if(ENABLE_UBSAN)
  add_compile_options(-fsanitize=undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=undefined)
endif()
if(ENABLE_TSAN)
  add_compile_options(-fsanitize=thread)
  add_link_options(-fsanitize=thread)
endif()
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
      - run: cmake -B build -DCMAKE_BUILD_TYPE=Debug
      - run: cmake --build build
      - run: cd build && ctest --output-on-failure
```

## Flaky Tests Guardrails

- Never use `sleep` for synchronization; use condition variables or latches.
- Make temp directories unique per test and always clean them.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use deterministic seeds for randomized inputs.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```cpp
// tests/validator_test.cpp
#include <gtest/gtest.h>
#include <string>

TEST(ValidatorTest, RejectsInvalidInput) {
    EXPECT_THROW(validator.validate(""), std::invalid_argument);
    EXPECT_THROW(validator.validate(" "), std::invalid_argument);
    EXPECT_THROW(validator.validate(std::string(10001, 'a')), std::invalid_argument);
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```cpp
// tests/calculator_test.cpp
#include <gtest/gtest.h>

TEST(CalculatorTest, ThrowsOnDivideByZero) {
    EXPECT_THROW(calculator.divide(10, 0), std::runtime_error);
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```cpp
// tests/connection_test.cpp
#include <gtest/gtest.h>

TEST(ConnectionTest, StateTransitionsAreCorrect) {
    Connection conn;
    EXPECT_EQ(conn.state(), State::CLOSED);
    conn.open();
    EXPECT_EQ(conn.state(), State::OPEN);
    conn.close();
    EXPECT_EQ(conn.state(), State::CLOSED);
    // Idempotency
    conn.close();
    EXPECT_EQ(conn.state(), State::CLOSED);
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `EXPECT_EQ(val1, val2) << "context message"` or `ASSERT_*` for critical checks.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test invalid inputs, edge values, `EXPECT_THROW` for exceptions.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at interface/virtual boundaries; prefer fakes for stateful behavior.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long test cases with no clear fixture/test split. *Fix: Use `TEST_F` for shared setup, keep individual `TEST` methods short.*
- **Flaky Test**: Non-deterministic results from memory, threads, or unsanitized UB. *Fix: Enable ASan/UBSan/TSan in CI; use deterministic inputs; avoid shared mutable state.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Prefer dependency injection over globals
- Use `ASSERT_*` for preconditions, `EXPECT_*` for multiple checks
- Separate unit vs integration tests in CTest labels or directories
- Run sanitizers in CI for memory and race detection

### DON'T

- Don't depend on real time or network in unit tests
- Don't use sleeps as synchronization when a condition variable can be used
- Don't over-mock simple value objects
- Don't use brittle string matching for non-critical logs

### Common Pitfalls

- **Using fixed temp paths** → Generate unique temp directories per test and clean them.
- **Relying on wall clock time** → Inject a clock or use fake time sources.
- **Flaky concurrency tests** → Use condition variables/latches and bounded waits.
- **Hidden global state** → Reset global state in fixtures or remove globals.
- **Over-mocking** → Prefer fakes for stateful behavior and only mock interactions.
- **Missing sanitizer runs** → Add ASan/UBSan/TSan builds in CI.
- **Coverage on debug-only builds** → Ensure coverage targets use consistent flags.

## Optional Appendix: Fuzzing / Property Testing

Only use if the project already supports LLVM/libFuzzer or a property-testing library.

- **libFuzzer**: best for pure functions with minimal I/O.
- **RapidCheck**: property-based tests to validate invariants.

Minimal libFuzzer harness (pseudocode: replace ParseConfig):

```cpp
#include <cstddef>
#include <cstdint>
#include <string>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    std::string input(reinterpret_cast<const char *>(data), size);
    // ParseConfig(input); // project function
    return 0;
}
```

### Mutation Testing (Mull)

```bash
# Mull: LLVM-based mutation testing for C/C++
# https://github.com/mull-project/mull
mull-cxx -test-framework=GoogleTest -compilation-database-path=build/compile_commands.json
# Report: mutation score per function with killed/survived mutants
```

> Mutation testing introduces code changes (e.g., `+` → `-`, removing `const`) to verify tests detect them. **Target ≥80% mutation score** for critical code paths.

## Alternatives to GoogleTest

- **Catch2** (v3.7.x): header-only, expressive matchers
- **doctest** (v2.4.x): lightweight, minimal compile overhead
