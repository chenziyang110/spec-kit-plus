---
name: c-testing
description: |
  Use ONLY when user explicitly requests C test code, CMocka/Unity configuration,
  test failure diagnosis, or coverage/Valgrind for C projects.

  Triggers: "write test c", "cmocka", "unity test c", "C coverage", "valgrind",
  "C unit test", "function pointer di", "C mock".

  Do NOT activate for: general C coding without test context, Makefile/CMake build
  errors, C compiler/linker issues, or embedded build system configuration.
origin: ECC
---

# C Testing (Agent Skill)

Agent-focused testing workflow for modern C (C11/C17) using CMocka, the most widely used unit testing framework for C with mock support.

## When to Use

- Writing new C tests or fixing existing tests
- Designing unit/integration test coverage for C components
- Adding test coverage, CI gating, or regression protection
- Configuring CMocka/CTest workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing embedded systems, kernel modules, or system libraries

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-C projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (global state, hard-coded I/O, no function-pointer DI, no mock boundaries)
- **No test framework** is detected in CMakeLists.txt (no cmocka/Unity/CTest)
- The request is **ambiguous**: "test my code" or "add tests" without specifying files or functions
- A **required test dependency** (cmocka, Unity, Criterion) is not declared
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer dependency injection (function pointers) and mocks over global state.
- **Test layout**: `tests/unit`, `tests/integration`, `tests/testdata`, `tests/mocks/`.
- **CMocka**: assertion macros, mock framework, setup/teardown callbacks.
- **CTest discovery**: `add_test()` with CMake for consistent test execution.
- **CI signal**: `ctest --output-on-failure --schedule-random`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the C standard (C11/C17) and build tool (CMake/Make).
2. Check for existing test files (`tests/`, `*_test.c`) to infer naming conventions and style (CMocka, Unity, Criterion).
3. Analyze the code under test: identify public API surface, memory allocation patterns, pointer usage, and I/O boundaries.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage/sanitizers, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks. Use CMocka `cmocka_unit_test` or Unity `RUN_TEST`.
- **External dependencies (I/O, network, hardware)**: use function pointer structs for dependency injection; use CMocka `expect_*` for mock verification.
- **Memory-critical code**: enable AddressSanitizer (`-fsanitize=address`) and Valgrind (`memcheck`) in CI.
- **Embedded systems**: use Unity (single-header, minimal footprint) instead of CMocka.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (filesystem, network, hardware registers)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (function pointer DI struct)?
  → Yes → Mock via function pointer injection (CMocka expect_*)
  → No  → Q3

Q3: Embedded / minimal footprint?
  → Yes → Unity (single header, no external deps)
  → No  → CMocka with CMake/CTest

Q4: Memory safety critical?
  → Yes → Valgrind memcheck + AddressSanitizer in CI
  → No  → Standard cmocka_unit_test

Q5: Fuzzing needed?
  → Yes → libFuzzer harness with LLVM sanitizer coverage
  → No  → Standard unit test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty strings, `NULL`, `0`, `SIZE_MAX`, `INT_MAX`, empty arrays.
3. **Error cases**: error return codes, `errno` values, `NULL` pointer dereference guards, allocation failures.
4. **Memory & safety**: buffer overflows, use-after-free, memory leaks, uninitialized reads.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration
- [ ] Framework: CMocka (or Unity for embedded) + CMake/CTest
- [ ] Mocking: Yes/No — function pointer DI / CMocka expect
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
ctest --test-dir build --output-on-failure
./build/example_tests
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `cmake -S . -B build-cov -DENABLE_COVERAGE=ON && cmake --build build-cov && ctest --test-dir build-cov && gcov src/*.c`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile without warnings (`cmake --build build`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are restored after tests (reset function pointers to real implementations).
- [ ] No `sleep()` used for synchronization (use condition variables or semaphores).
- [ ] Flaky test guardrails applied (unique temp dirs, deterministic seeds, ASan/UBSan/Valgrind in CI).

## TDD Workflow

```c
// tests/add_test.c
int add(int a, int b); // Provided by production code.

static void test_add(void **state) { // RED
    (void)state;
    assert_int_equal(add(2, 3), 5);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_add),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}

// src/add.c
int add(int a, int b) { return a + b; } // GREEN

// REFACTOR: once tests pass
```

## Code Examples

### Basic Unit Test (CMocka)

```c
// tests/calculator_test.c
#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <cmocka.h>

int add(int a, int b); // Provided by production code.

static void test_add_positive(void **state) {
    (void)state;
    assert_int_equal(add(2, 3), 5);
}

static void test_add_negative(void **state) {
    (void)state;
    assert_int_equal(add(-1, 1), 0);
}

static void test_add_zero(void **state) {
    (void)state;
    assert_int_equal(add(0, 0), 0);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(test_add_positive),
        cmocka_unit_test(test_add_negative),
        cmocka_unit_test(test_add_zero),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
```

### Setup / Teardown

```c
// tests/user_store_test.c
#include <cmocka.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char name[64];
} User;

typedef struct {
    User *users;
    size_t count;
    size_t capacity;
} UserStore;

static int setup(void **state) {
    UserStore *store = calloc(1, sizeof(UserStore));
    store->capacity = 10;
    store->users = calloc(store->capacity, sizeof(User));
    store->users[0] = (User){ .name = "alice" };
    store->users[1] = (User){ .name = "bob" };
    store->count = 2;
    *state = store;
    return 0;
}

static int teardown(void **state) {
    UserStore *store = *state;
    free(store->users);
    free(store);
    return 0;
}

static void test_find_existing_user(void **state) {
    UserStore *store = *state;
    // ... find and assert
    assert_non_null(store);
}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test_setup_teardown(
            test_find_existing_user, setup, teardown),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
```

### Mocking (CMocka)

```c
// tests/notifier_test.c
#include <cmocka.h>
#include <stdbool.h>

typedef bool (*NotifierSend)(const char *message);
static NotifierSend mock_notifier_send = NULL;

// The function that will be called by production code
bool notifier_send(const char *message) {
    if (mock_notifier_send) {
        return mock_notifier_send(message);
    }
    return false;
}

// Mock control function
static bool mock_send_ok(const char *message) {
    check_expected(message);
    return true;
}

static void test_service_publishes(void **state) {
    (void)state;
    mock_notifier_send = mock_send_ok;
    expect_string(mock_send_ok, message, "hello");

    service_publish("hello");

    mock_notifier_send = NULL;
}
```

### CMocka Assertions

```c
assert_int_equal(a, b);       // a == b
assert_int_not_equal(a, b);   // a != b
assert_null(ptr);             // ptr == NULL
assert_non_null(ptr);         // ptr != NULL
assert_string_equal(a, b);    // strcmp(a, b) == 0
assert_string_not_equal(a, b);
assert_memory_equal(a, b, size);
assert_in_range(val, min, max);
assert_not_in_range(val, min, max);
assert_true(expr);
assert_false(expr);
assert_return_code(rc, error); // rc >= 0
```

### Unity (Lightweight Alternative)

```c
// tests/calculator_test.c
#include "unity.h"

void setUp(void) {}
void tearDown(void) {}

void test_add_positive(void) {
    TEST_ASSERT_EQUAL_INT32(5, add(2, 3));
}

void test_add_negative(void) {
    TEST_ASSERT_EQUAL_INT32(0, add(-1, 1));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_add_positive);
    RUN_TEST(test_add_negative);
    return UNITY_END();
}
```

## CMake/CTest Quickstart

```cmake
# CMakeLists.txt (excerpt)
cmake_minimum_required(VERSION 3.20)
project(example C)

set(CMAKE_C_STANDARD 17)

include(FetchContent)
FetchContent_Declare(
  cmocka
  GIT_REPOSITORY https://gitlab.com/cmocka/cmocka.git
  GIT_TAG cmocka-1.1.7
)
FetchContent_MakeAvailable(cmocka)

add_executable(example_tests
  tests/calculator_test.c
  src/calculator.c
)
target_link_libraries(example_tests cmocka)
target_include_directories(example_tests PRIVATE
  ${cmocka_SOURCE_DIR}/include
  src
)

enable_testing()
add_test(NAME calculator_test COMMAND example_tests)
```

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

## Running Tests

```bash
ctest --test-dir build --output-on-failure

# Direct execution
./build/example_tests
./build/example_tests 2>&1 | ./build/example_tests -v
```

## Coverage

```cmake
option(ENABLE_COVERAGE "Enable coverage flags" OFF)

if(ENABLE_COVERAGE)
  if(CMAKE_C_COMPILER_ID MATCHES "GNU")
    target_compile_options(example_tests PRIVATE --coverage)
    target_link_options(example_tests PRIVATE --coverage)
  elseif(CMAKE_C_COMPILER_ID MATCHES "Clang")
    target_compile_options(example_tests PRIVATE -fprofile-instr-generate -fcoverage-mapping)
    target_link_options(example_tests PRIVATE -fprofile-instr-generate)
  endif()
endif()
```

```bash
# GCC + gcov
cmake -S . -B build-cov -DENABLE_COVERAGE=ON
cmake --build build-cov
ctest --test-dir build-cov
gcov src/calculator.c
```

## Memory & Thread Safety (Valgrind / Sanitizers)

```bash
# Valgrind — memory leaks and invalid accesses
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./build/example_tests

# Helgrind — thread race detection
valgrind --tool=helgrind ./build/example_tests

# AddressSanitizer (compile-time, faster than Valgrind)
cmake -S . -B build-asan -DCMAKE_C_FLAGS="-fsanitize=address -fno-omit-frame-pointer" -DCMAKE_LINKER_FLAGS="-fsanitize=address"
cmake --build build-asan
ctest --test-dir build-asan
```

## Debugging Failures

1. Re-run the single failing test by executing the binary directly.
2. Add `-v` or `--verbose` flag for CMocka verbose output.
3. Use GDB: `gdb --args ./build/example_tests`.
4. Add `cm_print_errors()` for CMocka mock error details.
5. Expand to full suite once root cause is fixed.

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
      - run: sudo apt install -y cmake valgrind
      - run: cmake -B build -DCMAKE_BUILD_TYPE=Debug
      - run: cmake --build build
      - run: cd build && ctest --output-on-failure
```

## Flaky Tests Guardrails

- Never use `sleep()` for synchronization; use condition variables or semaphores.
- Make temp directories unique with `mkdtemp()` and clean them.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use deterministic seeds with `srand(42)` for randomized inputs.
- Mock external library calls via function pointer replacement.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, NULL, and just-outside valid ranges.

```c
// tests/validator_test.c
static void test_rejects_invalid_input(void **state) {
    (void)state;
    assert_int_equal(validate_input(""), -1);
    assert_int_equal(validate_input(" "), -1);
    assert_int_equal(validate_input("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"), -1);
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```c
// tests/calculator_test.c
static void test_divide_by_zero(void **state) {
    (void)state;
    int result;
    assert_int_equal(divide(10, 0, &result), ERROR_DIV_ZERO);
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```c
// tests/connection_test.c
static void test_connection_state_transitions(void **state) {
    (void)state;
    Connection *conn = connection_new();
    assert_int_equal(connection_state(conn), STATE_CLOSED);
    connection_open(conn);
    assert_int_equal(connection_state(conn), STATE_OPEN);
    connection_close(conn);
    assert_int_equal(connection_state(conn), STATE_CLOSED);
    // Idempotency
    connection_close(conn);
    assert_int_equal(connection_state(conn), STATE_CLOSED);
    connection_free(conn);
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `assert_int_equal(val1, val2)` with descriptive test function names.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `NULL` pointers, negative values, buffer overflow boundary conditions.*
- **Mock Overdose**: Too many function-pointer mocks hiding integration issues. *Fix: Mock only at I/O and hardware boundaries; test real implementations for pure logic.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long test functions with no clear setup/test split. *Fix: Use `cmocka_unit_test_setup_teardown` for resource management.*
- **Flaky Test**: Non-deterministic results from memory corruption or shared state. *Fix: Use `mkdtemp()` for unique temp dirs, Valgrind/ASan in CI, deterministic inputs.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Use function pointer structs for dependency injection in C
- Use `cmocka_unit_test_setup_teardown` for proper resource cleanup
- Separate unit vs integration tests in CTest labels or directory structure
- Run with AddressSanitizer and UndefinedBehaviorSanitizer in CI
- Use `assert_return_code` for system call return value checks

### DON'T

- Don't use `sleep()` for synchronization
- Don't depend on real time or network in unit tests
- Don't use global mutable state that leaks between tests
- Don't test static functions directly — test through public API
- Don't use `#ifdef TEST` hacks in production code — use DI instead
- Don't ignore return values of system calls in tests

### Common Pitfalls

- **Global state pollution** → Reset module-level globals in setup/teardown.
- **Fixed temp paths** → Use `mkdtemp()` + `rmdir()` per test.
- **Relying on wall clock** → Inject time via function pointer or macro.
- **Missing mock cleanup** → Always restore real implementations after mock tests.
- **Memory leaks** → Use AddressSanitizer in CI (`-fsanitize=address`).
- **Undefined behavior** → Use UBSan (`-fsanitize=undefined`) in CI.
- **Missing coverage targets** → Add gcov/lcov to CI pipeline.

## Optional: Fuzzing

### libFuzzer (Clang)

```c
// tests/fuzz_add.c
#include <stddef.h>
#include <stdint.h>

int add(int a, int b);

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < sizeof(int) * 2) return 0;
    int a = *(const int *)data;
    int b = *(const int *)(data + sizeof(int));
    add(a, b); // just ensure no crash
    return 0;
}
```

## Optional: Property-Based Testing

Property-based testing verifies invariants across randomly generated inputs. In C, use the `theft` library for combinatorial property testing:

```c
// tests/test_add_property.c
#include "theft.h"

struct add_args { int a; int b; };

enum theft_alloc_res alloc_add(struct theft *t, void *env, void **output) {
    struct add_args *args = malloc(sizeof(*args));
    args->a = theft_random_int(t);
    args->b = theft_random_int(t);
    *output = args;
    return THEFT_ALLOC_OK;
}

static theft_trial_res prop_add_commutative(struct theft *t, void *arg) {
    struct add_args *args = arg;
    assert_int_equal(add(args->a, args->b), add(args->b, args->a));
    return THEFT_TRIAL_PASS;
}
```

> **Build**: Compile with `-ltheft`. Run 1000+ random trials per property. Target invariants: commutativity (`a+b == b+a`), associativity, identity (`a+0 == a`).

## Alternatives

- **Unity** (v2.6.x): Extremely lightweight, single header, ideal for embedded systems.
- **Criterion** (v2.4.x): Modern, cross-platform, with parameterized tests and benchmarks.
- **greatest**: Minimalist, single-header test framework.
