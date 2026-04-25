---
name: go-testing
description: |
  Use ONLY when user explicitly requests Go test code, testing/testify configuration,
  test failure diagnosis, or coverage improvement for Go projects.

  Triggers: "write test go", "go testing", "testify", "uber mock", "go coverage",
  "go benchmark", "table-driven test", "go fuzz", "t.Parallel", "httptest".

  Do NOT activate for: general Go coding without test context, go mod/build errors,
  Go module setup, or Go toolchain installation.
origin: ECC
---

# Go Testing (Agent Skill)

Agent-focused testing workflow for modern Go (1.21+) using the standard `testing` package with `testify` for assertions and mocks.

## When to Use

- Writing new Go tests or fixing existing tests
- Designing unit/integration test coverage for Go components
- Adding test coverage, CI gating, or regression protection
- Configuring Go test workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing HTTP handlers, gRPC services, or CLI tools

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Go projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (package-level globals, no interfaces, hard-coded network calls)
- **No test files** exist in the project and no `_test.go` pattern is used
- The request is **ambiguous**: "test my app" or "add tests" without specifying packages or functions
- A **required test dependency** (testify, mockgen) is not installed via go.mod
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Table-driven tests**: idiomatic Go pattern for testing multiple cases.
- **Test layout**: `_test.go` files co-located with source, `testdata/` for fixtures.
- **Subtests**: `t.Run()` for hierarchical test organization.
- **Testable examples**: `ExampleXxx` functions for documentation-as-tests.
- **CI signal**: run with `-race -count=1 -vet=all` for correctness.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Go version (1.21+) and module structure (`go.mod`).
2. Check for existing test files (`*_test.go`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, goroutine usage, and I/O boundaries.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: table-driven tests (`[]struct{...}`) with `t.Run`, no mocks.
- **External dependencies (DB, HTTP, filesystem)**: use interfaces + manual mocks or Uber Mock (`go.uber.org/mock`); prefer `httptest` for HTTP handlers.
- **Async / goroutine code**: use `sync.WaitGroup` + channels; test with `-race` flag.
- **Benchmarks**: use `BenchmarkXxx` with `testing.B` for performance regression detection.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem, network)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable at code boundary (interface, function parameter)?
  → Yes → Mock at boundary (testify mock, uber mockgen)
  → No  → Q3

Q3: Needs real behavior verification (SQL, Docker services)?
  → Yes → Integration test (dockertest, testcontainers-go)
  → No  → Use fake/stub (in-memory map, bytes.Buffer)

Q4: Concurrent code (goroutines, channels)?
  → Yes → t.Parallel() with sync primitives, -race flag
  → No  → Synchronous test sufficient

Q5: HTTP handler?
  → Yes → httptest.NewServer / httptest.NewRecorder
  → No  → Standard table-driven test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty slices, `nil`, zero values, `math.MaxInt64`, empty strings.
3. **Error cases**: error return values, panics (use `recover` or `assert.Panics`), invalid inputs.
4. **Concurrency**: data races, channel deadlocks, context cancellation.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / Benchmark
- [ ] Framework: testing + testify (optional) + Uber Mock (if needed)
- [ ] Mocking: Yes/No — interfaces / Uber Mock
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
go test -v -race -count=1 ./...
go test -run TestFunctionName ./package
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`go test ./...`).
- [ ] Each subtest has a descriptive name (`t.Run("descriptive name", ...)`).
- [ ] Mocks are reset between tests (reconstruct in `SetupTest` or `beforeEach`).
- [ ] No `time.Sleep` used for synchronization (use `sync.WaitGroup` or channels).
- [ ] Flaky test guardrails applied (`t.TempDir()`, `-count=10` for reproduction).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```go
// add_test.go
func Add(a, b int) int // Provided by production code.

func TestAdd(t *testing.T) { // RED
    got := Add(2, 3)
    want := 5
    if got != want {
        t.Errorf("Add(2, 3) = %d; want %d", got, want)
    }
}

// add.go
func Add(a, b int) int { // GREEN
    return a + b
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test

```go
// calculator_test.go
package main

import "testing"

func TestAdd(t *testing.T) {
    got := Add(2, 3)
    want := 5
    if got != want {
        t.Errorf("Add() = %d; want %d", got, want)
    }
}
```

### Table-Driven Test

```go
// math_test.go
package main

import "testing"

func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, 1, 0},
        {"zeros", 0, 0, 0},
        {"large", 100, 200, 300},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

### Parallel Table-Driven Test

```go
// math_test.go
package main

import "testing"

func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, 1, 0},
        {"zeros", 0, 0, 0},
        {"large", 100, 200, 300},
    }

    for _, tt := range tests {
        tt := tt // capture range variable for parallel execution
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel() // run subtests concurrently
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

> **Warning:** Always reassign the loop variable (`tt := tt`) before `t.Parallel()` to avoid capturing the iteration variable by reference.

### Testify Suite + Assertions

```bash
# Install: go get github.com/stretchr/testify@v1.10.0
```

```go
// user_store_test.go
package main

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/suite"
)

type User struct { Name string }

type UserStore struct {
    users []User
}

func (s *UserStore) Seed(users []User) {
    s.users = append(s.users, users...)
}

func (s *UserStore) Find(name string) *User {
    for _, u := range s.users {
        if u.Name == name {
            return &u
        }
    }
    return nil
}

type UserStoreTestSuite struct {
    suite.Suite
    store *UserStore
}

func (s *UserStoreTestSuite) SetupTest() {
    s.store = &UserStore{}
    s.store.Seed([]User{{"alice"}, {"bob"}})
}

func (s *UserStoreTestSuite) TestFindExistingUser() {
    user := s.store.Find("alice")
    assert.NotNil(s.T(), user)
    assert.Equal(s.T(), "alice", user.Name)
}

func TestUserStoreSuite(t *testing.T) {
    suite.Run(t, new(UserStoreTestSuite))
}
```

### Mocking (testify mock)

```go
// notifier_test.go
package main

import (
    "testing"
    "github.com/stretchr/testify/mock"
    "github.com/stretchr/testify/assert"
)

type Notifier interface {
    Send(message string) error
}

type MockNotifier struct {
    mock.Mock
}

func (m *MockNotifier) Send(message string) error {
    args := m.Called(message)
    return args.Error(0)
}

type Service struct {
    notifier Notifier
}

func (s *Service) Publish(message string) error {
    return s.notifier.Send(message)
}

func TestSendsNotifications(t *testing.T) {
    notifier := new(MockNotifier)
    notifier.On("Send", "hello").Return(nil)

    service := Service{notifier: notifier}
    err := service.Publish("hello")

    assert.NoError(t, err)
    notifier.AssertExpectations(t)
}
```

### HTTP Handler Test

```go
// handler_test.go
package main

import (
    "net/http"
    "net/http/httptest"
    "testing"
)

func TestHelloHandler(t *testing.T) {
    req := httptest.NewRequest(http.MethodGet, "/hello", nil)
    rec := httptest.NewRecorder()

    HelloHandler(rec, req)

    assert.Equal(t, http.StatusOK, rec.Code)
    assert.Equal(t, "Hello, World!", rec.Body.String())
}
```

### Testable Example

```go
// add_test.go
package main

import "fmt"

func ExampleAdd() {
    sum := Add(2, 3)
    fmt.Println(sum)
    // Output: 5
}
```

### Fuzz Test (Go 1.18+)

```go
// add_fuzz_test.go
package main

import "testing"

func FuzzAdd(f *testing.F) {
    f.Add(2, 3)
    f.Add(-1, 1)
    f.Add(0, 0)

    f.Fuzz(func(t *testing.T, a, b int) {
        result := Add(a, b)
        // property: a + b == b + a
    })
}
```

## Running Tests

```bash
go test ./...                          # all packages
go test -v ./...                       # verbose
go test -run TestAdd                   # run matching tests
go test -run "TestAdd/positive"        # run matching subtest
go test -count=1 ./...                 # disable cache
go test -race ./...                    # race detector
go test -bench=. -benchmem             # benchmarks with memory
go test -fuzz=FuzzAdd -fuzztime=10s    # fuzz testing
```

## Coverage

```bash
go test -cover ./...
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out       # per-function coverage
go tool cover -html=coverage.out       # HTML report
```

```bash
# CI with coverage gate
go test -coverprofile=coverage.out -covermode=atomic ./...
go tool cover -func=coverage.out | tail -1 | awk '{print $NF}' | tr -d '%'
```

## Debugging Failures

1. Re-run with `-v -count=1` for uncached verbose output.
2. Use `t.Log()` / `t.Logf()` for debug output (shown with `-v`).
3. Run with `-race` to catch data races.
4. Use `go test -gcflags=-l` to disable inlining for clearer stack traces.
5. Expand to full suite once the root cause is fixed.

## Test Flags and Conventions

```go
// testing.Short for skipping slow tests
func TestIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test in short mode")
    }
}

// Running: go test -short ./...
```

```go
// TestMain for custom setup
func TestMain(m *testing.M) {
    // setup
    code := m.Run()
    // teardown
    os.Exit(code)
}
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
      - uses: actions/setup-go@v5
        with: { go-version: '1.23' }
      - run: go test -v -race -count=1 -coverprofile=coverage.out ./...
      - run: go tool cover -func=coverage.out
```

## Flaky Tests Guardrails

- Never use `time.Sleep` for synchronization; use `sync.WaitGroup` or channels.
- Make temp directories unique with `t.TempDir()`.
- Avoid real time, network, or external services in unit tests.
- Use `clock.NewMock()` from `github.com/benbjohnson/clock` for time-dependent code.
- Run tests with `-count=10` to reproduce flakiness.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, nil, and just-outside valid ranges.

```go
// validator_test.go
func TestValidateInputBoundary(t *testing.T) {
    tests := []struct {
        name  string
        input string
    }{
        {"empty", ""},
        {"whitespace", " "},
        {"too long", strings.Repeat("a", 10001)},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            _, err := ValidateInput(tt.input)
            if err == nil {
                t.Errorf("expected error for %q", tt.input)
            }
        })
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```go
// calculator_test.go
func TestDivideByZero(t *testing.T) {
    _, err := Divide(10, 0)
    if err == nil {
        t.Error("expected error for divide by zero")
    }
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```go
// connection_test.go
func TestConnectionStateTransitions(t *testing.T) {
    conn := NewConnection()
    if conn.State() != Closed {
        t.Errorf("expected closed, got %v", conn.State())
    }
    conn.Open()
    if conn.State() != Open {
        t.Errorf("expected open, got %v", conn.State())
    }
    conn.Close()
    if conn.State() != Closed {
        t.Errorf("expected closed, got %v", conn.State())
    }
    // Idempotency
    conn.Close()
    if conn.State() != Closed {
        t.Errorf("expected closed after double close, got %v", conn.State())
    }
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without context, making failure diagnosis ambiguous. *Fix: Use descriptive `t.Run` subtest names and testify `assert.Equal(t, expected, actual, "context")`.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test non-nil error returns, empty/nil inputs, edge values.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at interface boundaries; prefer real fakes (in-memory store) for collaborators.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long table-driven tests with cryptic names or no descriptive subtest names. *Fix: Use `t.Run("descriptive name")` for each subtest case.*
- **Flaky Test**: Non-deterministic results from goroutines, time, or shared state. *Fix: Use `t.TempDir()`, `-count=10` for reproduction, `-race` for data races.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Use table-driven tests for multiple cases
- Use `t.Helper()` for test helper functions
- Use `t.Cleanup()` for deferred teardown
- Name tests with `TestXxx` and subtests with descriptive names
- Use `testify/assert` for readable assertions
- Run with `-race` in CI

### DON'T

- Don't use `time.Sleep` for synchronization
- Don't depend on real network or external services in unit tests
- Don't write global state that leaks between tests
- Don't test unexported functions directly (except for internal packages)
- Don't use `panic` for test failures — use `t.Error` / `t.Fatal`
- Don't ignore test errors with `_`

### Common Pitfalls

- **Cache masking failures** → Use `-count=1` in CI to disable test caching.
- **Relying on wall clock** → Inject clock interfaces or use `time.Now()` mocking via `clock`.
- **Flaky goroutine tests** → Use `sync.WaitGroup` and channels, not sleeps.
- **Global state pollution** → Reset package-level vars in `TestMain` or `SetupTest`.
- **Over-mocking** → Prefer integration testing for core business logic.
- **Missing race detection** → Add `-race` to CI test runs.
- **Testing internals** → Export only what's needed; test through public API.
- **Orphaned testdata** → Clean up `testdata` directories periodically.

## Optional Appendix: Advanced Testing

### GoMock (Alternative Mocking)

> **Note:** `github.com/golang/mock` has been archived by Google. Use Uber's maintained fork instead.

```bash
go install go.uber.org/mock/mockgen@latest
mockgen -source=notifier.go -destination=mock_notifier.go -package=main
```

### Dockertest (Integration)

```go
import (
    "testing"
    "github.com/ory/dockertest/v3"
)

func TestPostgres(t *testing.T) {
    pool, err := dockertest.NewPool("")
    // ... spin up container, run tests
}
```

### Mutation Testing (gremlins)

```bash
# Install: go install github.com/go-gremlins/gremlins/cmd/gremlins@latest
gremlins unleash                # run all mutation tests
gremlins unleash --tag "unit"   # filter by build tags
# Output: KILLED/MUTATED count per file with survival rate
```

> Mutation testing validates test quality by introducing code changes (e.g., `>` → `>=`, removing early returns). **Target ≥80% kill rate** — surviving mutants indicate missing assertions or untested paths.

## Alternatives

- **Ginkgo + Gomega**: BDD-style testing, more verbose.
- **Gocheck**: older xUnit-style framework, less common in new projects.
- **apitest**: declarative HTTP API testing.
