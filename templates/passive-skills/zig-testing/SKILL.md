---
name: zig-testing
description: |
  Use ONLY when user explicitly requests Zig test code, built-in test runner configuration,
  test failure diagnosis, or coverage for Zig projects.

  Triggers: "write test zig", "zig test", "testing.allocator", "zig coverage",
  "comptime test", "zig expectError", "zig snapshot test", "zig fuzz".

  Do NOT activate for: general Zig coding without test context, build.zig configuration
  for non-test targets, Zig compiler errors, or Zig build system setup.
origin: ECC
---

# Zig Testing (Agent Skill)

Agent-focused testing workflow for Zig using the built-in test framework — zero dependencies, first-class language support with `comptime` test discovery.

## When to Use

- Writing new Zig tests or fixing existing tests
- Designing unit/integration test coverage for Zig components
- Adding test coverage, CI gating, or regression protection
- Configuring `zig test` workflows for consistent execution
- Investigating test failures
- Testing system-level or embedded Zig code

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Zig projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (all comptime, no runtime public API, hard-coded system calls)
- **No test blocks** exist in the project and no test step in build.zig
- The request is **ambiguous**: "test my code" or "add tests" without specifying files or functions
- The code requires **external tooling not yet configured** (kcov, zcoverage)
- The test would require **secrets, real credentials, or production system access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **First-class tests**: `test` blocks are language built-ins, discovered by `zig test`.
- **Comptime evaluation**: tests can run at compile time via `comptime`.
- **Test layout**: tests co-located with source using `test` blocks, or in separate `test/` files.
- **No external framework**: everything is built into the Zig compiler.
- **CI signal**: `zig test src/main.zig` with `--test-no-exec` for compile-time checks.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Zig version (0.13+/master) and build configuration (`build.zig`).
2. Check for existing test files (`test` blocks in source, `test/`, `*_test.zig`) to infer style.
3. Analyze the code under test: identify public API surface, allocator usage, `comptime` evaluation, and I/O boundaries.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: co-located `test` blocks in source files, no mocks. Use `testing.expectEqual`.
- **External dependencies (I/O, network)**: use interfaces (structs with function pointers) for dependency injection; write manual test doubles.
- **Allocator-dependent code**: always use `testing.allocator` to detect memory leaks automatically.
- **Comptime code**: use `comptime` test blocks to validate compile-time logic.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (filesystem, network, hardware)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (function pointer struct, comptime interface)?
  → Yes → Manual test double via function pointer injection
  → No  → Q3

Q3: Allocator-dependent code?
  → Yes → Always use testing.allocator for leak detection
  → No  → Standard test block

Q4: Compile-time validation?
  → Yes → comptime test block
  → No  → Q5

Q5: Snapshot/error union testing?
  → Yes → @embedFile for snapshots, expectError for error cases
  → No  → Standard testing.expectEqual
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty slices, `null`, `0`, `std.math.maxInt(T)`, empty strings.
3. **Error cases**: error unions (`error.SomeError`), `catch unreachable` pitfalls, allocation failures.
4. **Memory & safety**: memory leaks (`testing.allocator` + `defer`), slice bounds, integer overflow.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / Comptime
- [ ] Framework: built-in test runner + build.zig
- [ ] Mocking: Yes/No — manual struct-based DI
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
zig test src/main.zig
zig test src/main.zig -- --test-filter "add"
zig build test
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `kcov --exclude-pattern=zig-cache coverage ./zig-out/bin/test`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`zig test src/main.zig`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Allocators are properly deinitialized (`defer store.deinit()`).
- [ ] No `std.time.sleep` used for synchronization (use atomic operations or event loops).
- [ ] Flaky test guardrails applied (`testing.allocator`, deterministic seeds, no real network in unit tests).

## TDD Workflow

```zig
// src/math.zig
fn add(a: i32, b: i32) i32 { @compileError("stub"); } // stub

test "adds two numbers" { // RED
    try testing.expectEqual(add(2, 3), 5);
}

// src/math.zig
fn add(a: i32, b: i32) i32 { return a + b; } // GREEN

// REFACTOR: once tests pass
```

## Code Examples

### Basic Unit Test

```zig
// src/calculator.zig
const std = @import("std");
const testing = std.testing;

fn add(a: i32, b: i32) i32 {
    return a + b;
}

test "adds two numbers" {
    try testing.expectEqual(add(2, 3), 5);
}

test "handles negative numbers" {
    try testing.expectEqual(add(-1, 1), 0);
}
```

### Multiple Test Files

```zig
// test/math_test.zig
const std = @import("std");
const testing = std.testing;
const math = @import("../src/math.zig");

test "add returns correct sum" {
    try testing.expectEqual(math.add(2, 3), 5);
}

test "add handles negatives" {
    try testing.expectEqual(math.add(-1, 1), 0);
}
```

### Allocator Testing

```zig
// src/user_store.zig
const std = @import("std");
const testing = std.testing;
const Allocator = std.mem.Allocator;

const User = struct {
    name: []const u8,
};

const UserStore = struct {
    allocator: Allocator,
    users: std.ArrayList(User),

    fn init(allocator: Allocator) UserStore {
        return .{
            .allocator = allocator,
            .users = std.ArrayList(User).init(allocator),
        };
    }

    fn deinit(self: *UserStore) void {
        self.users.deinit();
    }

    fn seed(self: *UserStore, users: []const User) !void {
        try self.users.appendSlice(users);
    }

    fn find(self: *UserStore, name: []const u8) ?User {
        for (self.users.items) |user| {
            if (std.mem.eql(u8, user.name, name)) return user;
        }
        return null;
    }
};

test "finds existing user" {
    var store = UserStore.init(testing.allocator);
    defer store.deinit();

    try store.seed(&[_]User{
        .{ .name = "alice" },
        .{ .name = "bob" },
    });

    const user = store.find("alice");
    try testing.expect(user != null);
    try testing.expectEqualStrings("alice", user.?.name);
}

test "returns null for missing user" {
    var store = UserStore.init(testing.allocator);
    defer store.deinit();

    try testing.expect(store.find("charlie") == null);
}
```

### Error Testing

```zig
test "expect error" {
    const result = mightFail();
    try testing.expectError(error.SomeError, result);
}

fn mightFail() !void {
    return error.SomeError;
}
```

### Comptime Test

```zig
test "compile-time evaluation" {
    const result = comptime add(2, 3);
    try testing.expectEqual(result, 5);
}
```

### Snapshot / Approvals (Manual)

```zig
test "snapshot test" {
    const output = generateOutput();
    const expected = @embedFile("snapshots/test1.txt");
    try testing.expectEqualSlices(u8, expected, output);
}
```

### Parametrized (Manual Loop)

```zig
test "add parametrized" {
    const cases = [_]struct { a: i32, b: i32, expected: i32 }{
        .{ .a = 1, .b = 2, .expected = 3 },
        .{ .a = -1, .b = 1, .expected = 0 },
        .{ .a = 0, .b = 0, .expected = 0 },
        .{ .a = 100, .b = 200, .expected = 300 },
    };

    for (cases) |c| {
        const result = add(c.a, c.b);
        try testing.expectEqual(c.expected, result);
    }
}
```

## Build.zig Configuration

```zig
// build.zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "myapp",
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    // Test configuration
    const exe_tests = b.addTest(.{
        .root_source_file = .{ .path = "src/main.zig" },
        .target = target,
        .optimize = optimize,
    });

    const test_step = b.step("test", "Run all tests");
    test_step.dependOn(&exe_tests.step);

    // Separate test files
    inline for (&[_][]const u8{
        "test/math_test.zig",
    }) |test_file| {
        const t = b.addTest(.{
            .root_source_file = .{ .path = test_file },
            .target = target,
            .optimize = optimize,
        });
        test_step.dependOn(&t.step);
    }

    b.default_step.dependOn(&exe.step);
    b.installArtifact(exe);
}
```

## Running Tests

```bash
zig test src/main.zig                  # run all test blocks in file
zig test src/math.zig                  # run tests in specific file
zig test src/main.zig -- --test-filter "add"  # filter by name
zig test src/main.zig --test-no-exec   # compile-only check (CI)
zig test src/main.zig -lc              # link against libc if needed
zig build test                         # if build.zig defines test step
```

## Coverage

Zig does not have built-in coverage. Use external tools:

### kcov (Linux/macOS)

```bash
# 1. Install kcov
# Ubuntu: sudo apt install kcov
# macOS: brew install kcov

# 2. Build a test binary (requires build.zig test step to produce executable)
zig build test -Doptimize=Debug

# 3. Run kcov against the test binary
kcov --clean \
     --include-path=src/ \
     --exclude-pattern=zig-cache,test,test_ \
     coverage-report \
     ./zig-out/bin/test

# 4. View the report
# open coverage-report/index.html
```

### zcoverage (community, cross-platform)

```bash
# https://github.com/nicopap/zcoverage
zig build test --summary all
zcoverage ./zig-out/bin/test
```

> **Interpreting results**: kcov shows line and branch coverage per file. Aim for ≥80% line coverage for critical code paths. The report highlights uncovered lines in red — focus on covering error paths and edge cases first.

## Debugging Failures

1. Re-run with `--test-filter` to isolate the failing test.
2. Add `std.debug.print("{any}\n", .{value});` for debug output.
3. Use `testing.allocator` with `--test-filter` for memory leak detection.
4. Use `@import("std").log` for scoped logging.
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
      - uses: goto-bus-stop/setup-zig@v2
        with: { version: '0.13.0' }
      - run: zig build test --summary all
```

## Flaky Tests Guardrails

- Never use `std.time.sleep` for synchronization; use atomic operations or event loops.
- Use `testing.allocator` to detect memory leaks automatically.
- Avoid real network or filesystem dependencies in unit tests.
- Use `std.Random` with a deterministic seed from `testing.random`.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```zig
// src/validator.zig
test "rejects invalid input" {
    try testing.expectError(error.InvalidInput, validateInput(""));
    try testing.expectError(error.InvalidInput, validateInput(" "));
    const long = "a" ** 10001;
    try testing.expectError(error.InvalidInput, validateInput(long));
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```zig
// src/math.zig
test "divide by zero returns error" {
    try testing.expectError(error.DivideByZero, divide(10, 0));
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```zig
// src/connection.zig
test "connection state transitions" {
    var conn = Connection.init(testing.allocator);
    defer conn.deinit();
    try testing.expectEqual(conn.state(), .closed);
    try conn.open();
    try testing.expectEqual(conn.state(), .open);
    try conn.close();
    try testing.expectEqual(conn.state(), .closed);
    // Idempotency
    try conn.close();
    try testing.expectEqual(conn.state(), .closed);
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `testing.expectEqual(expected, actual)` with clear test block names and comments.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `null` pointers, `error` unions with `expectError`, boundary values.*
- **Mock Overdose**: Too many function-pointer fakes hiding integration issues. *Fix: Mock only at I/O boundaries; test real implementations for pure logic.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable `testing.expect*` call.*
- **Obscure Test**: Large test blocks with no clear setup/verify structure. *Fix: Follow AAA, use `defer` for cleanup, keep test blocks focused on single behavior.*
- **Flaky Test**: Non-deterministic results from allocator state or shared mutability. *Fix: Use `testing.allocator` for leak detection, deterministic seeds, avoid shared mutable state.*

## Best Practices

### DO

- Co-locate `test` blocks directly in source files for unit tests
- Use `try testing.expectEqual` / `try testing.expect` for assertions
- Use `testing.allocator` for memory leak detection
- Use `defer` for cleanup in tests
- Separate integration tests in `test/` directory
- Use `@import` to bring in source files for external test files

### DON'T

- Don't use `std.time.sleep` for synchronization
- Don't depend on real time, network, or external services in unit tests
- Don't ignore memory leaks — always use `testing.allocator` for test allocations
- Don't use `@panic` in test helpers — propagate errors with `try`/`!`
- Don't write tests that depend on test execution order

### Common Pitfalls

- **Memory leaks** → Always use `testing.allocator` and ensure `deinit` is called.
- **No isolated allocators** → Pass allocators explicitly rather than using global ones.
- **Flaky file system tests** → Use `std.testing.tmpDir` or `std.fs.cwd().openDir`.
- **Over-reliance on `@embedFile`** → Keep snapshot files under version control.
- **Missing `try` in test assertions** → Always prefix assertion calls with `try`.
- **Slow compile times** → Separate large test files from frequently changed source files.

## Optional: Fuzzing

Zig's test framework can be used for fuzz-like testing with random inputs:

```zig
test "fuzz add" {
    var prng = std.rand.DefaultPrng.init(42);
    const random = prng.random();

    var i: usize = 0;
    while (i < 1000) : (i += 1) {
        const a = random.int(i32);
        const b = random.int(i32);
        const result = add(a, b);
        // property: a + b == b + a
        try testing.expectEqual(result, add(b, a));
    }
}
```

## Optional: Property-Based Testing

Zig supports property-based testing via manual random input generation. Use `std.Random` with a fixed seed for reproducibility:

```zig
const std = @import("std");
const testing = std.testing;

fn add(a: i32, b: i32) i32 { return a + b; }

test "add is commutative (property)" {
    var prng = std.Random.DefaultPrng.init(42);
    const rand = prng.random();
    for (0..1000) |_| {
        const a = rand.int(i32);
        const b = rand.int(i32);
        try testing.expectEqual(add(a, b), add(b, a));
    }
}

test "add identity (property)" {
    var prng = std.Random.DefaultPrng.init(42);
    const rand = prng.random();
    for (0..1000) |_| {
        const a = rand.int(i32);
        try testing.expectEqual(add(a, 0), a);
    }
}
```

> **Best practice**: Use deterministic seeds for reproducibility, run ≥1000 trials, and test mathematical invariants (commutativity, associativity, identity).
