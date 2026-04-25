---
name: cs-testing
description: |
  Use ONLY when user explicitly requests C# test code, xUnit/NSubstitute configuration,
  test failure diagnosis, or coverage improvement for .NET projects.

  Triggers: "write test c#", "xunit", "NSubstitute", "Bogus", "AutoFixture",
  "dotnet test", "C# coverage", "coverlet", "FluentAssertions", "ASP.NET test".

  Do NOT activate for: general C# coding without test context, NuGet package restore,
  MSBuild/project configuration outside test scope, or .NET runtime issues.
origin: ECC
---

# C# Testing (Agent Skill)

Agent-focused testing workflow for modern C# (.NET 8+) using xUnit.net with NSubstitute (preferred) / Moq (legacy) and FluentAssertions.

## When to Use

- Writing new C# tests or fixing existing tests
- Designing unit/integration test coverage for C# components
- Adding test coverage, CI gating, or regression protection
- Configuring xUnit / NSubstitute / Bogus workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing ASP.NET Core, Blazor, or library code

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-C# projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (static methods everywhere, no DI, hard-coded `new HttpClient()`)
- **No test framework** is detected (no xUnit/NUnit in csproj, no `dotnet test` configuration)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or classes
- A **required test dependency** (xUnit, NSubstitute, FluentAssertions) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer constructor injection and mocks over global state.
- **Test layout**: `tests/UnitTests/`, `tests/IntegrationTests/`, mirror source namespace.
- **Facts vs Theories**: `[Fact]` for single case, `[Theory]` with `[InlineData]` / `[MemberData]`.
- **Mocks vs fakes**: Moq for interaction verification, fakes for stateful behavior.
- **CI signal**: `dotnet test` with `--collect:"XPlat Code Coverage"`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the .NET version (8.0+) and build tool (SDK-style csproj).
2. Check for existing test files (`tests/`, `*Test.cs`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, async/await usage, and DI patterns.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / value objects**: unit tests only, no mocks needed. Use `[Fact]` or `[Theory]`.
- **External dependencies (DB, HTTP, filesystem)**: use **NSubstitute** (preferred) or Moq (legacy only); prefer `WebApplicationFactory` for ASP.NET Core integration tests.
- **Async code**: use `async Task` return type, never `async void`; use `CancellationToken` where applicable.
- **Test data generation**: use `Bogus` for deterministic random data, `AutoFixture` for automating object creation.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem, network)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (interface, constructor DI)?
  → Yes → Mock at boundary (NSubstitute.Substitute.For<T>)
  → No  → Q3

Q3: Needs real behavior (SQL, HTTP pipeline)?
  → Yes → WebApplicationFactory / Testcontainers.DotNet
  → No  → Use fake/stub implementation

Q4: Async (Task, ValueTask, async/await)?
  → Yes → async Task test method, never async void
  → No  → Synchronous [Fact]/[Theory]

Q5: Need test data with specific properties?
  → Yes → Bogus Faker<T> for deterministic random data
  → No  → Standard xUnit test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty collections, `null`, `default(T)`, `string.Empty`, `DateTime.MinValue`.
3. **Error cases**: exceptions (`Assert.Throws`), validation errors, 4xx/5xx responses, timeout scenarios.
4. **State & async**: mutable shared state, `static` field leakage, `Task` cancellation.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / E2E
- [ ] Framework: xUnit + NSubstitute (preferred) / Moq (legacy) + FluentAssertions
- [ ] Mocking: Yes/No — NSubstitute / Moq
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
dotnet test --filter "FullyQualifiedName~ClassName"
dotnet test --logger "console;verbosity=detailed"
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `dotnet test --collect:"XPlat Code Coverage"`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests compile and pass (`dotnet test`).
- [ ] Each test has exactly one logical assertion focus (use `Assert.Multiple` or FluentAssertions chaining).
- [ ] Mocks are reset between tests (reconstruct in constructor or `Dispose`).
- [ ] No `Thread.Sleep` used for synchronization (use `Task.Delay` with `CancellationToken`).
- [ ] Flaky test guardrails applied (`IClassFixture<T>`, deterministic data, no test ordering dependencies).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```csharp
// tests/UnitTests/AddTest.cs
public class AddTest
{
    [Fact] // RED
    public void Adds_Two_Numbers()
    {
        Assert.Equal(5, Add.AddNumbers(2, 3));
    }
}

// src/MyApp/Add.cs
public static class Add { // GREEN
    public static int AddNumbers(int a, int b) => a + b;
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (xUnit)

```csharp
// tests/UnitTests/CalculatorTest.cs
public class CalculatorTest
{
    [Fact]
    public void Adds_Two_Numbers()
    {
        var result = Calculator.Add(2, 3);
        Assert.Equal(5, result);
    }
}
```

### Shared Context (xUnit IClassFixture)

```csharp
// tests/UnitTests/UserStoreTest.cs
public class UserStoreTest : IClassFixture<UserStoreFixture>
{
    private readonly UserStore _store;

    public UserStoreTest(UserStoreFixture fixture)
    {
        _store = fixture.Store;
    }

    [Fact]
    public void Finds_Existing_User()
    {
        var user = _store.Find("alice");
        Assert.NotNull(user);
        Assert.Equal("alice", user.Name);
    }
}

public class UserStoreFixture : IDisposable
{
    public UserStore Store { get; }

    public UserStoreFixture()
    {
        Store = new UserStore();
        Store.Seed([new User("alice"), new User("bob")]);
    }

    public void Dispose() { /* cleanup */ }
}
```

### Mocking (NSubstitute — Recommended)

> **Prefer NSubstitute for new projects.** Moq 4.20+ introduced the controversial SponsorLink feature which raises privacy concerns in the .NET community. NSubstitute offers a cleaner, more discoverable API without external network calls during build.

```csharp
// tests/UnitTests/NotifierTest.cs
using NSubstitute;

public class NotifierTest
{
    [Fact]
    public void Sends_Notifications()
    {
        var notifier = Substitute.For<INotifier>();
        var service = new Service(notifier);

        service.Publish("hello");

        notifier.Received(1).Send("hello");
    }
}
```

### Mocking (Moq — Legacy Only)

> **Use only for existing codebases already committed to Moq.** For greenfield projects, choose NSubstitute.

```csharp
// tests/UnitTests/NotifierTest.cs
using Moq;

public class NotifierTest
{
    [Fact]
    public void Sends_Notifications()
    {
        var notifier = new Mock<INotifier>();
        var service = new Service(notifier.Object);

        service.Publish("hello");

        notifier.Verify(n => n.Send("hello"), Times.Once);
    }
}
```

### Theory (Parametrized Test)

```csharp
// tests/UnitTests/MathTest.cs
public class MathTest
{
    [Theory]
    [InlineData(1, 2, 3)]
    [InlineData(-1, 1, 0)]
    [InlineData(0, 0, 0)]
    [InlineData(100, 200, 300)]
    public void Adds_Numbers(int a, int b, int expected)
    {
        Assert.Equal(expected, Math.Add(a, b));
    }
}
```

### Async Test

```csharp
// tests/UnitTests/ApiTest.cs
public class ApiTest
{
    [Fact]
    public async Task Fetches_User_Data()
    {
        var user = await FetchUser("1");
        Assert.Equal("alice", user.Name);
    }

    [Fact]
    public async Task Handles_Errors()
    {
        await Assert.ThrowsAsync<ArgumentException>(() => FetchUser("invalid"));
    }
}
```

### Exception Testing

```csharp
// tests/UnitTests/ValidationTest.cs
public class ValidationTest
{
    [Fact]
    public void Throws_On_Negative_Age()
    {
        var ex = Assert.Throws<ArgumentException>(() => Validator.ValidateAge(-1));
        Assert.Contains("non-negative", ex.Message);
    }
}
```

### Fluent Assertions

```csharp
// tests/UnitTests/UserTest.cs
using FluentAssertions;

public class UserTest
{
    [Fact]
    public void User_Has_Correct_Properties()
    {
        var user = new User("alice", "alice@example.com");

        user.Name.Should().Be("alice");
        user.Email.Should().EndWith("@example.com");
        user.Roles.Should().Contain("user");
    }
}
```

### ASP.NET Core Controller Test

```csharp
// tests/UnitTests/UsersControllerTest.cs
using Microsoft.AspNetCore.Mvc;
using Moq;

public class UsersControllerTest
{
    [Fact]
    public async Task Get_Returns_User()
    {
        var service = new Mock<IUserService>();
        service.Setup(s => s.GetUser("1"))
            .ReturnsAsync(new User("alice", "alice@example.com"));

        var controller = new UsersController(service.Object);
        var result = await controller.Get("1");

        var okResult = Assert.IsType<OkObjectResult>(result);
        var user = Assert.IsType<User>(okResult.Value);
        Assert.Equal("alice", user.Name);
    }
}
```

## Project Configuration

```xml
<!-- tests/UnitTests/UnitTests.csproj -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="xunit" Version="2.9.0" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.0" />
    <PackageReference Include="NSubstitute" Version="5.3.0" />
    <PackageReference Include="FluentAssertions" Version="8.0.0" />
    <PackageReference Include="Bogus" Version="35.6.0" />
    <PackageReference Include="AutoFixture" Version="5.0.0" />
    <PackageReference Include="coverlet.collector" Version="6.0.0" />
  </ItemGroup>
</Project>
```

## Running Tests

```bash
dotnet test                              # all test projects
dotnet test --filter "Category=Unit"     # filtered by trait
dotnet test --filter "FullyQualifiedName~CalculatorTest"
dotnet test tests/UnitTests              # specific project
dotnet test --logger "console;verbosity=detailed"
dotnet test --collect:"XPlat Code Coverage"
```

## Coverage

```bash
# Using coverlet (built-in)
dotnet test --collect:"XPlat Code Coverage"
dotnet tool install -g dotnet-reportgenerator-globaltool
reportgenerator -reports:"**/TestResults/**/coverage.cobertura.xml" \
    -targetdir:coverage -reporttypes:Html
```

```xml
<!-- Directory.Build.props (project-wide coverage settings) -->
<Project>
  <ItemGroup>
    <PackageReference Include="coverlet.collector" Version="6.0.0">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
    </PackageReference>
  </ItemGroup>
</Project>
```

## Debugging Failures

1. Re-run with `-v d` (detailed verbosity) for full output.
2. Add `Debugger.Launch()` to enter the debugger on failure.
3. Use `ITestOutputHelper` for structured test output.
4. Use `dotnet test --filter` to isolate the failing test.
5. Expand to full suite once the root cause is fixed.

```csharp
public class DebugTest
{
    private readonly ITestOutputHelper _output;

    public DebugTest(ITestOutputHelper output)
    {
        _output = output;
    }

    [Fact]
    public void With_Debug_Output()
    {
        _output.WriteLine("Debug info: {0}", someVariable);
        // ...
    }
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
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: '8.0.x' }
      - run: dotnet test --collect:"XPlat Code Coverage" --logger:"junit;LogFilePath=report.xml"
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: '**/report.xml' }
```

## Flaky Tests Guardrails

- Never use `Thread.Sleep` for synchronization; use `Task.Delay` with `CancellationToken`.
- Make temp directories unique with `Path.GetTempPath()` + `Guid.NewGuid()`.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use `ITestOutputHelper` to capture diagnostics without global state.
- Reset static state in `IClassFixture<T>.Dispose` or constructor.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```csharp
// tests/UnitTests/ValidatorTest.cs
public class ValidatorTest
{
    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData("toolonginputexceedingmaxallowedlength")]
    public void Rejects_Invalid_Input(string input)
    {
        Assert.Throws<ArgumentException>(() => _validator.Validate(input));
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```csharp
// tests/UnitTests/CalculatorTest.cs
public class CalculatorTest
{
    [Fact]
    public void Throws_On_Divide_By_Zero()
    {
        Assert.Throws<DivideByZeroException>(() => _calculator.Divide(10, 0));
    }
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```csharp
// tests/UnitTests/ConnectionTest.cs
public class ConnectionTest
{
    [Fact]
    public void State_Transitions_Are_Correct()
    {
        var conn = new Connection();
        Assert.Equal(State.Closed, conn.State);
        conn.Open();
        Assert.Equal(State.Open, conn.State);
        conn.Close();
        Assert.Equal(State.Closed, conn.State);
        // Idempotency
        conn.Close();
        Assert.Equal(State.Closed, conn.State);
    }
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use FluentAssertions chaining or `Assert.Multiple` with descriptive labels.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `null` values, `ArgumentNullException`, invalid enum values, boundary conditions.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at architectural boundaries (IHttpClientFactory, DbContext); use `WebApplicationFactory` for integration.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long test methods with no clear arrange/act/assert structure. *Fix: Follow AAA, use `IClassFixture<T>` for shared setup, keep test bodies short.*
- **Flaky Test**: Non-deterministic results from time, order, or shared state. *Fix: Use `TimeProvider` (NET 8+), `Bogus` with fixed seeds, `IClassFixture<T>` for isolation.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Use constructor injection for testable components
- Use `[Theory]` with `[InlineData]` for parametrized tests
- Separate unit vs integration tests in separate projects
- Use `FluentAssertions` for readable, chainable assertions
- **Use `NSubstitute` for new projects** — cleaner API, no SponsorLink concerns
- Follow Arrange-Act-Assert pattern with clear spacing
- Use `IClassFixture<T>` for shared test context

### DON'T

- Don't use `Thread.Sleep` for synchronization
- Don't depend on real time, network, or database in unit tests
- Don't test private methods directly — test through public API
- Don't mock value objects, DTOs, or simple data containers
- **Don't choose Moq for new projects** — prefer NSubstitute to avoid SponsorLink
- Don't use `[Fact]` when `[Theory]` is appropriate
- Don't write tests that depend on test execution order

### Common Pitfalls

- **Leaking static state** → Reset static state in constructor or fixture dispose.
- **Relying on real time** → Inject `TimeProvider` (available in .NET 8+) or `ISystemClock`.
- **Flaky async tests** → Use `async Task` return type, never `async void`.
- **Heavy ASP.NET context** → Use `WebApplicationFactory` with in-memory `TestServer`.
- **Over-mocking** → Prefer real implementations for domain logic and value objects.
- **Missing coverage gates** → Add coverlet with minimum coverage thresholds in CI.
- **Slow integration tests** → Mark with `[Trait("Category", "Integration")]` and filter in CI.

## Optional Appendix: Advanced Testing

### Testcontainers (Integration Tests)

```csharp
using Testcontainers.PostgreSql;

public class DatabaseTest : IAsyncLifetime
{
    private readonly PostgreSqlContainer _container =
        new PostgreSqlBuilder().Build();

    public async Task InitializeAsync() => await _container.StartAsync();

    public async Task DisposeAsync() => await _container.DisposeAsync();

    [Fact]
    public async Task Connects_To_Database()
    {
        // use _container.GetConnectionString()
    }
}
```

### Verify (Snapshot Testing)

```csharp
[UsesVerify]
public class SnapshotTest
{
    [Fact]
    public Task Verifies_Output()
    {
        var result = SomeMethod();
        return Verify(result);
    }
}
```

## Alternatives to xUnit

- **NUnit**: `[SetUp]` / `[TearDown]` style, broader assertion library.
- **MSTest**: built-in Visual Studio integration, less feature-rich.
- **SpecFlow**: BDD/Gherkin-style tests for .NET.

### Mutation Testing (Stryker.NET)

```bash
dotnet tool install -g dotnet-stryker
dotnet stryker --solution-path MySolution.sln --project-file=src/MyProject/MyProject.csproj
# Report: StrykerOutput/*/reports/mutation-report.html
```

> Mutation testing introduces small code changes (e.g., `>` → `>=`) to verify tests catch them. **Target ≥80% mutation score** for business logic.
