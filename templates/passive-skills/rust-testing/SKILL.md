---
name: rust-testing
description: |
  Use ONLY when user explicitly requests Rust test code, cargo-test/rstest/mockall configuration,
  test failure diagnosis, or coverage improvement for Rust projects.

  Triggers: "write test rust", "cargo test", "rstest", "mockall", "rust coverage",
  "cargo nextest", "cargo-llvm-cov", "proptest", "insta snapshot", "should_panic".

  Do NOT activate for: general Rust coding without test context, borrow checker issues,
  cargo build errors, or crate dependency resolution outside test scope.
origin: ECC
---

# Rust Testing (Agent Skill)

Agent-focused testing workflow for modern Rust (edition 2021+) using the built-in test framework with `rstest` for fixtures and parametrization.

## When to Use

- Writing new Rust tests or fixing existing tests
- Designing unit/integration test coverage for Rust components
- Adding test coverage, CI gating, or regression protection
- Configuring `cargo test` workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing async code, proc macros, or FFI boundaries

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Rust projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (pub(crate) only internals, unsafe blocks without safe wrappers, hard-coded file/network)
- **No test dependencies** exist in Cargo.toml dev-dependencies (rstest, mockall, tokio test-util)
- The request is **ambiguous**: "test my crate" or "add tests" without specifying modules
- A **required test dependency** (rstest, mockall, proptest) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Module tests**: `#[cfg(test)] mod tests { ... }` co-located in source files.
- **Integration tests**: `tests/` directory for black-box testing.
- **Test layout**: `src/` for unit tests (inline), `tests/` for integration, `tests/common/` for shared helpers.
- **Doc tests**: `/// ``` ... ``` ` for documentation-as-tests.
- **CI signal**: `cargo test --all-targets --all-features` followed by `cargo test --doc`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Rust edition (2021+) and workspace structure (`Cargo.toml`).
2. Check for existing test files (`#[cfg(test)]` blocks, `tests/*.rs`) to infer style.
3. Analyze the code under test: identify public API surface, `unsafe` blocks, async (`async`/`.await`), and FFI boundaries.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: inline `#[cfg(test)] mod tests` with `assert_eq!`, no mocks.
- **Trait-based dependencies**: use `mockall` (`#[automock]`) or hand-written test doubles.
- **Async code**: use `#[tokio::test]` or `tokio::test` with controlled runtime.
- **Integration tests**: place in `tests/` directory for black-box testing.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (filesystem, network, DB)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable via trait/interface?
  → Yes → Mock at trait boundary (mockall #[automock])
  → No  → Q3

Q3: Needs real behavior (async runtime, Docker)?
  → Yes → Integration test (tests/ directory, tokio runtime)
  → No  → Hand-written test double

Q4: Async (tokio, async-std)?
  → Yes → #[tokio::test] with controlled runtime
  → No  → Synchronous #[test] sufficient

Q5: Snapshot/approval testing?
  → Yes → insta::assert_snapshot! / assert_debug_snapshot!
  → No  → Standard assert_eq!/assert!
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty `Vec`, `None`, `0`, `usize::MAX`, empty strings, `NonZero*` types.
3. **Error cases**: `Result::Err`, `Option::None`, panics (`#[should_panic]`), `unsafe` precondition violations.
4. **Memory & concurrency**: ownership/borrowing edge cases, `Send`/`Sync` bounds, deadlock scenarios.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / Doc Test
- [ ] Framework: built-in test + rstest + mockall (if needed)
- [ ] Mocking: Yes/No — mockall / manual trait impls
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
cargo test --all-targets --all-features
cargo nextest run  # recommended parallel runner
cargo test --doc
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `cargo llvm-cov --html`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`cargo test`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are reset between tests (reconstruct in `setup` or use `rstest` fixtures).
- [ ] No `thread::sleep` used for synchronization (use channels or `tokio::time::timeout`).
- [ ] Flaky test guardrails applied (`testing.allocator`, deterministic seeds, `--test-threads=1` check).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```rust
// src/lib.rs
pub fn add(a: i32, b: i32) -> i32 { todo!() } // stub for RED

#[cfg(test)]
mod tests {
    use super::*;

    #[test] // RED
    fn adds_two_numbers() {
        assert_eq!(add(2, 3), 5);
    }
}

// src/lib.rs
pub fn add(a: i32, b: i32) -> i32 { // GREEN
    a + b
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test

```rust
// src/lib.rs
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adds_two_numbers() {
        assert_eq!(add(2, 3), 5);
    }
}
```

### Test Fixtures (rstest)

```rust
// src/lib.rs
use rstest::rstest;

#[derive(Debug, PartialEq)]
struct User {
    name: String,
}

struct UserStore {
    users: Vec<User>,
}

impl UserStore {
    fn new() -> Self {
        Self { users: Vec::new() }
    }

    fn seed(&mut self, users: Vec<User>) {
        self.users.extend(users);
    }

    fn find(&self, name: &str) -> Option<&User> {
        self.users.iter().find(|u| u.name == name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rstest::*;

    #[fixture]
    fn user_store() -> UserStore {
        let mut store = UserStore::new();
        store.seed(vec![
            User { name: "alice".into() },
            User { name: "bob".into() },
        ]);
        store
    }

    #[rstest]
    fn finds_existing_user(user_store: UserStore) {
        let user = user_store.find("alice");
        assert!(user.is_some());
        assert_eq!(user.unwrap().name, "alice");
    }
}
```

### Parametrized Tests (rstest)

```rust
// src/lib.rs
use rstest::rstest;

#[rstest]
#[case(1, 2, 3)]
#[case(-1, 1, 0)]
#[case(0, 0, 0)]
#[case(100, 200, 300)]
fn test_add(#[case] a: i32, #[case] b: i32, #[case] expected: i32) {
    assert_eq!(add(a, b), expected);
}
```

### Mocking (mockall)

```rust
// src/lib.rs
#[cfg(test)]
use mockall::automock;

#[cfg_attr(test, automock)]
pub trait Notifier {
    fn send(&self, message: &str);
}

pub struct Service<T: Notifier> {
    notifier: T,
}

impl<T: Notifier> Service<T> {
    pub fn new(notifier: T) -> Self {
        Self { notifier }
    }

    pub fn publish(&self, message: &str) {
        self.notifier.send(message);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sends_notifications() {
        let mut mock = MockNotifier::new();
        mock.expect_send()
            .with(predicate::eq("hello"))
            .times(1)
            .return_const(());

        let service = Service::new(mock);
        service.publish("hello");
    }
}

// Cargo.toml
// [dev-dependencies]
// mockall = "0.13"
```

### Async Test (tokio-test)

```rust
// src/lib.rs
async fn fetch_user(id: &str) -> Result<User, Error> {
    Ok(User { name: "alice".into() })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_fetch_user() {
        let user = fetch_user("1").await.unwrap();
        assert_eq!(user.name, "alice");
    }
}
```

### Doc Test

```rust
/// Adds two numbers together.
///
/// ```
/// use my_crate::add;
///
/// assert_eq!(add(2, 3), 5);
/// ```
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

### Integration Test

```rust
// tests/integration_test.rs
use my_crate::add;

#[test]
fn integration_add() {
    assert_eq!(add(2, 3), 5);
}
```

### Result-Based Test

```rust
#[test]
fn returns_result() -> Result<(), String> {
    if 2 + 2 == 4 {
        Ok(())
    } else {
        Err("math broke".into())
    }
}
```

### Test for Panics

```rust
#[test]
#[should_panic(expected = "age must be non-negative")]
fn test_negative_age() {
    validate_age(-1);
}
```

## Cargo.toml Quickstart

```toml
[dev-dependencies]
rstest = "0.25"
mockall = "0.13"
tokio = { version = "1", features = ["test-util", "macros"] }
pretty_assertions = "1"    # readable assertion diffs
proptest = "1"             # property-based testing
```

## Running Tests

```bash
cargo test                             # all tests
cargo test -- --nocapture              # show stdout
cargo test test_add                    # run tests matching filter
cargo test tests::test_add            # fully qualified name
cargo test --test integration_test     # single integration file
cargo test --doc                      # run doc tests only
cargo test --all-features             # test with all features
cargo test -p my_crate                # test specific package
cargo nextest run                     # Install: cargo install cargo-nextest@0.9
cargo nextest run --workspace         # all workspace packages
cargo nextest run --retries 3         # retry flaky tests automatically
```

## Coverage

```bash
# Install: cargo install cargo-tarpaulin@0.31
cargo tarpaulin --ignore-tests
cargo tarpaulin --out Html --output-dir coverage
```

```bash
# LLVM coverage (nightly)
RUSTFLAGS="-C instrument-coverage" cargo test
llvm-profdata merge -sparse default.profdata -o coverage.profdata
llvm-cov report --instr-profile=coverage.profdata --object target/debug/my_crate
```

```bash
# cargo-llvm-cov (recommended)
# Install: cargo install cargo-llvm-cov@0.6
cargo llvm-cov --html
cargo llvm-cov --lcov --output-path lcov.info  # for Codecov/coveralls
```

## Debugging Failures

1. Re-run with `--nocapture` to see stdout/stderr from tests.
2. Use `RUST_BACKTRACE=1` or `RUST_BACKTRACE=full` for stack traces.
3. Use `dbg!()` macro for quick variable inspection.
4. Use `cargo test -- --test-threads=1` to isolate concurrency issues.
5. Expand to full suite once the root cause is fixed.

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
      - run: rustup update stable
      - run: cargo install cargo-nextest cargo-llvm-cov
      - run: cargo nextest run --workspace
      - run: cargo llvm-cov --html
```

## Flaky Tests Guardrails

- Never use `std::thread::sleep` for synchronization; use `tokio::time::timeout`.
- Make temp directories unique with `tempfile::TempDir`.
- Avoid real time, network, or external services in unit tests.
- Use deterministic seeds for randomized inputs.
- Run tests with `--test-threads=1` to check for concurrency issues.
- Use `#[cfg(not(miri))]` to skip tests that don't work under Miri.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, None, and just-outside valid ranges.

```rust
// src/lib.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[rstest]
    #[case("")]
    #[case(" ")]
    #[case(&"a".repeat(10001))]
    fn rejects_invalid_input(#[case] input: &str) {
        assert!(validate_input(input).is_err());
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```rust
#[test]
fn divide_by_zero_returns_error() {
    assert_eq!(divide(10, 0), Err(DivideError::Zero));
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```rust
#[test]
fn connection_state_transitions() {
    let mut conn = Connection::new();
    assert_eq!(conn.state(), State::Closed);
    conn.open().unwrap();
    assert_eq!(conn.state(), State::Open);
    conn.close().unwrap();
    assert_eq!(conn.state(), State::Closed);
    // Idempotency
    conn.close().unwrap();
    assert_eq!(conn.state(), State::Closed);
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without context, making failure diagnosis ambiguous. *Fix: Use `assert_eq!(actual, expected, "context: {variable}")` with descriptive messages.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `Err(...)` variants, `None` values, `unwrap_err()`, `#[should_panic]`.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at trait boundaries; prefer real implementations for pure logic.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Complex test functions with no clear arrange/act/assert structure. *Fix: Follow AAA, separate fixture setup with `#[fixture]` (rstest).*
- **Flaky Test**: Non-deterministic results from concurrency, IO, or allocator state. *Fix: Use `testing.allocator`, `--test-threads=1` for isolation, proptest for exhaustive input testing.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Co-locate unit tests in `#[cfg(test)] mod tests` within source files
- Use `rstest` for fixtures and parametrized tests
- Use `assert_eq!`, `assert_ne!`, `assert!` with descriptive messages
- Write doc tests for public API documentation
- Separate integration tests in `tests/` directory
- Use `pretty_assertions` for readable assertion diffs

### DON'T

- Don't use `thread::sleep` for synchronization
- Don't depend on real time or network in unit tests
- Don't test private implementation details through public API
- Don't use `unwrap` in tests — use `expect("message")` for context
- Don't write overly large test functions — test one behavior per test
- Don't ignore test helper duplication — share via `tests/common/mod.rs`

### Common Pitfalls

- **Using sleep for sync** → Use channels, `tokio::sync`, or `condvar`.
- **Global mutable state** → Use `std::sync::OnceLock` or test-local setup.
- **Flaky async tests** → Use `#[tokio::test]` with controlled runtime.
- **Leaking env vars** → Use `temp_env::with_var` for scoped env var changes.
- **Over-mocking** → Prefer real implementations for domain logic.
- **Slow compile times** → Keep test code behind `#[cfg(test)]` to avoid bloat.
- **Missing property tests** → Use `proptest` for invariant validation.
- **Brittle doc tests** → Run `cargo test --doc` in CI separately.

### Snapshot Testing (insta)

```rust
// src/lib.rs
#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_snapshot;

    #[test]
    fn output_matches_snapshot() {
        let output = generate_html();
        assert_snapshot!(output);
    }
}
```

```bash
cargo test          # creates new snapshots
cargo insta review  # interactively approve/reject changes
cargo insta accept  # accept all pending snapshots
```

Add to `Cargo.toml`:
```toml
[dev-dependencies]
insta = "1.42"
```

## Optional Appendix: Property-Based Testing

### proptest

```rust
use proptest::prelude::*;

fn add(a: i32, b: i32) -> i32 { a + b }

proptest! {
    #[test]
    fn add_is_commutative(a in any::<i32>(), b in any::<i32>()) {
        assert_eq!(add(a, b), add(b, a));
    }
}
```

### Mutation Testing (cargo-mutants)

```bash
# Install: cargo install cargo-mutants
cargo mutants                # run mutation testing
cargo mutants -- --package my_crate
# Report: terminal output with mutant survival rate
```

> Mutation testing introduces code mutations (e.g., `+` → `-`, `&&` → `||`) and checks if tests catch them. A mutant that survives indicates a gap in test coverage. **Target ≤20% mutant survival rate.**

## Alternatives

- **Built-in `#[test]`**: sufficient for most unit tests.
- **cargo-nextest**: faster parallel test runner with better failure output.
- **cucumber_rust**: BDD/Gherkin-style tests for Rust.
