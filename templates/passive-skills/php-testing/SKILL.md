---
name: php-testing
description: |
  Use ONLY when user explicitly requests PHP test code, PHPUnit/Pest configuration,
  test failure diagnosis, or coverage improvement for PHP projects.

  Triggers: "write test php", "phpunit", "pest php", "laravel test",
  "PHP coverage", "refresh database test", "data provider php".

  Do NOT activate for: general PHP coding without test context, composer autoload
  issues, PHP framework setup, or non-test Laravel/WordPress configuration.
origin: ECC
---

# PHP Testing (Agent Skill)

Agent-focused testing workflow for modern PHP (8.2+) using PHPUnit, the industry-standard test framework for PHP with Mockito-style mocking.

## When to Use

- Writing new PHP tests or fixing existing tests
- Designing unit/integration test coverage for PHP components
- Adding test coverage, CI gating, or regression protection
- Configuring PHPUnit workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing Laravel, Symfony, Slim, or library code

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-PHP projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (static method chains, hard-coded includes, global state in functions)
- **No test framework** is detected (no phpunit.xml, no PHPUnit/Pest in composer.json)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or classes
- A **required test dependency** (phpunit, pest) is not installed via Composer
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Test layout**: `tests/` directory mirroring `src/` structure, `phpunit.xml` config.
- **Naming**: `*Test.php` files with `test*` methods or `#[Test]` attribute.
- **Mocks**: PHPUnit's built-in `createMock()` / `getMockBuilder()` (Mockito-style).
- **Data providers**: `@dataProvider` methods returning iterables of test cases.
- **CI signal**: `vendor/bin/phpunit --display-warnings --log-junit junit.xml`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the PHP version (8.2+) and framework (PHPUnit or Pest).
2. Check for existing test files (`tests/`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, database interactions, and Laravel/Symfony context.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks. Use PHPUnit `TestCase` or Pest `it()`.
- **External dependencies (DB, HTTP, filesystem)**: use PHPUnit mocks (`createMock`) or Laravel `Http::fake()` / `Bus::fake()`; prefer in-memory SQLite for DB tests.
- **Laravel applications**: use `RefreshDatabase` for feature tests, `DatabaseTransactions` for unit tests; use model factories for test data.
- **Async code**: PHP is mostly synchronous; use `expectException` for error paths.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (DI, service container, facade)?
  → Yes → Mock at boundary (createMock, Http::fake(), Bus::fake())
  → No  → Q3

Q3: Needs real DB behavior?
  → Yes → In-memory SQLite + RefreshDatabase / DatabaseTransactions
  → No  → Use simple stub

Q4: Laravel feature test?
  → Yes → RefreshDatabase + factory() + actingAs()
  → No  → Q5

Q5: Modern functional API preferred?
  → Yes → Pest (it(), expect(), dataset())
  → No  → PHPUnit TestCase
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output/response.
2. **Boundary values**: empty arrays, `null`, empty strings, `0`, `PHP_INT_MAX`, empty models.
3. **Error cases**: exceptions (`expectException`), validation errors (`assertSessionHasErrors`), 4xx/5xx responses.
4. **State & database**: transaction isolation, factory states, seeded data conflicts.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Feature / Integration
- [ ] Framework: PHPUnit or Pest + Laravel Testing (if applicable)
- [ ] Mocking: Yes/No — PHPUnit mocks / Laravel fakes
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
vendor/bin/phpunit --filter testMethod tests/ClassTest.php
vendor/bin/phpunit --testsuite Unit
# Or with Pest:
./vendor/bin/pest
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `vendor/bin/phpunit --coverage-html coverage`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests run without parse errors (`vendor/bin/phpunit`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Global state is reset between tests (`setUp()` or `RefreshDatabase`).
- [ ] No `sleep()` used for synchronization.
- [ ] Flaky test guardrails applied (database transactions, deterministic factories, no real HTTP calls).

## TDD Workflow

```php
// tests/MathTest.php
function add(int $a, int $b): int { throw new \Exception(); } // stub

final class MathTest extends TestCase {
    public function testAddsTwoNumbers(): void { // RED
        self::assertSame(5, add(2, 3));
    }
}

// src/Math.php
function add(int $a, int $b): int { return $a + $b; } // GREEN

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test

```php
// tests/CalculatorTest.php
namespace Tests;

use PHPUnit\Framework\TestCase;

final class CalculatorTest extends TestCase
{
    public function testAddsTwoNumbers(): void
    {
        self::assertSame(5, Calculator::add(2, 3));
    }

    public function testHandlesNegativeNumbers(): void
    {
        self::assertSame(0, Calculator::add(-1, 1));
    }
}
```

### Setup / Teardown

```php
// tests/UserStoreTest.php
final class UserStoreTest extends TestCase
{
    private UserStore $store;

    protected function setUp(): void
    {
        $this->store = new UserStore();
        $this->store->seed([new User('alice'), new User('bob')]);
    }

    public function testFindsExistingUser(): void
    {
        $user = $this->store->find('alice');
        self::assertNotNull($user);
        self::assertSame('alice', $user->name);
    }

    protected function tearDown(): void
    {
        unset($this->store);
    }
}
```

### Mocking (PHPUnit)

```php
// tests/NotifierTest.php
final class ServiceTest extends TestCase
{
    public function testSendsNotifications(): void
    {
        $notifier = $this->createMock(Notifier::class);
        $notifier->expects($this->once())
            ->method('send')
            ->with('hello');

        $service = new Service($notifier);
        $service->publish('hello');
    }
}
```

### Stub (Return Values)

```php
final class PaymentTest extends TestCase
{
    public function testChargesCorrectAmount(): void
    {
        $gateway = $this->createMock(PaymentGateway::class);
        $gateway->method('charge')
            ->with(100.0)
            ->willReturn(true);

        $service = new PaymentService($gateway);
        $result = $service->processOrder(100.0);

        self::assertTrue($result);
    }
}
```

### Data Provider

```php
final class MathTest extends TestCase
{
    /** @dataProvider additionProvider */
    public function testAdd(int $a, int $b, int $expected): void
    {
        self::assertSame($expected, Math::add($a, $b));
    }

    public static function additionProvider(): array
    {
        return [
            [1, 2, 3],
            [-1, 1, 0],
            [0, 0, 0],
            [100, 200, 300],
        ];
    }
}
```

### Exception Testing

```php
final class ValidationTest extends TestCase
{
    public function testThrowsOnNegativeAge(): void
    {
        $this->expectException(\InvalidArgumentException::class);
        $this->expectExceptionMessage('must be non-negative');

        Validator::validateAge(-1);
    }
}
```

### Attribute-Based (PHPUnit 10+)

```php
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\Attributes\CoversClass;

#[CoversClass(Calculator::class)]
final class CalculatorTest extends TestCase
{
    #[Test]
    #[DataProvider('additionProvider')]
    public function add(int $a, int $b, int $expected): void
    {
        self::assertSame($expected, Calculator::add($a, $b));
    }
}
```

## Installation

```bash
composer require --dev phpunit/phpunit:^11
```

## PHPUnit Configuration

```xml
<!-- phpunit.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<phpunit
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
    bootstrap="vendor/autoload.php"
    colors="true"
    cacheDirectory=".phpunit.cache"
>
    <testsuites>
        <testsuite name="Unit">
            <directory>tests/Unit</directory>
        </testsuite>
        <testsuite name="Feature">
            <directory>tests/Feature</directory>
        </testsuite>
    </testsuites>

    <source>
        <include>
            <directory>src</directory>
        </include>
    </source>

    <coverage>
        <report>
            <html outputDirectory="coverage"/>
            <clover outputFile="coverage.xml"/>
        </report>
    </coverage>
</phpunit>
```

## Running Tests

```bash
vendor/bin/phpunit                        # all tests
vendor/bin/phpunit tests/CalculatorTest.php  # single file
vendor/bin/phpunit --filter "testAdd"     # match method name
vendor/bin/phpunit --testsuite Unit       # specific suite
vendor/bin/phpunit --display-warnings     # show warnings
vendor/bin/phpunit --log-junit junit.xml  # CI output
```

## Coverage

```bash
vendor/bin/phpunit --coverage-html coverage
vendor/bin/phpunit --coverage-clover coverage.xml
vendor/bin/phpunit --coverage-text        # terminal report
```

```xml
<!-- phpunit.xml — coverage thresholds -->
<coverage>
    <report>
        <html outputDirectory="coverage"/>
    </report>
</coverage>
```

## Debugging Failures

1. Re-run with `--filter` to isolate the failing test.
2. Add `--display-warnings` for PHP deprecation warnings.
3. Use `var_dump()` (output is shown by default in PHPUnit).
4. Use `--process-isolation` to isolate side effects between tests.
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
      - uses: shivammathur/setup-php@v2
        with: { php-version: '8.3', coverage: xdebug }
      - run: composer install
      - run: vendor/bin/phpunit --coverage-clover=coverage.xml --log-junit=report.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: report.xml }
```

## Flaky Tests Guardrails

- Never use `sleep()` for synchronization.
- Use `Faker\Factory::create()->unique()` for unique test data.
- Reset global state between tests with `setUp()`.
- Use `DatabaseTransactions` trait in Laravel for DB isolation.
- Avoid real HTTP calls — use `Http::fake()` in Laravel or `GuzzleHttp\Handler\MockHandler`.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```php
// tests/ValidatorTest.php
final class ValidatorTest extends TestCase
{
    /** @dataProvider invalidInputProvider */
    public function testRejectsInvalidInput(string $input): void
    {
        $this->expectException(\InvalidArgumentException::class);
        Validator::validate($input);
    }

    public static function invalidInputProvider(): array
    {
        return [[''], [' '], [str_repeat('a', 10001)]];
    }
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```php
// tests/CalculatorTest.php
final class CalculatorTest extends TestCase
{
    public function testThrowsOnDivideByZero(): void
    {
        $this->expectException(\DivisionByZeroError::class);
        Calculator::divide(10, 0);
    }
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```php
// tests/ConnectionTest.php
final class ConnectionTest extends TestCase
{
    public function testStateTransitions(): void
    {
        $conn = new Connection();
        $this->assertSame(State::Closed, $conn->state());
        $conn->open();
        $this->assertSame(State::Open, $conn->state());
        $conn->close();
        $this->assertSame(State::Closed, $conn->state());
        // Idempotency
        $conn->close();
        $this->assertSame(State::Closed, $conn->state());
    }
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `$this->assertSame($expected, $actual, 'should calculate sum')` with descriptive messages.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `expectException()` cases, null/empty/zero inputs, invalid types.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at architectural boundaries (HTTP, queue, filesystem); use `RefreshDatabase` for DB.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long test methods with no clear arrange/act/assert structure. *Fix: Follow AAA, use `#[CoversClass]` attribute, keep test names descriptive.*
- **Flaky Test**: Non-deterministic results from database state or external services. *Fix: Use `DatabaseTransactions`, `Carbon::setTestNow()`, `Http::fake()` for HTTP isolation.*

## Best Practices

### DO

- Use `self::assert*` over `$this->assert*` for consistency
- Use `@dataProvider` or `#[DataProvider]` for multiple test cases
- Use `setUp()` for shared state initialization
- Use `@covers` / `#[CoversClass]` to document which class is tested
- Use strict typing (`declare(strict_types=1)`) in test files
- Use `assertSame` instead of `assertEquals` for type-safe comparisons

### DON'T

- Don't extend `TestCase` with custom base classes that add global state
- Don't use `sleep()` for synchronization
- Don't depend on real databases or external APIs in unit tests
- Don't test private or protected methods directly — test through public API
- Don't use `@depends` for test ordering when possible
- Don't mock `EntityManagerInterface` or similar — use in-memory DB instead

### Common Pitfalls

- **Global state pollution** → Reset singletons and static properties in `setUp()`.
- **Flaky DB tests** → Use transactions rollback or `RefreshDatabase` (Laravel).
- **Time-dependent tests** → Use `Carbon::setTestNow()` (Laravel/Carbon).
- **Slow tests** → Use `@group slow` and exclude from default suite.
- **Over-mocking** → Prefer in-memory implementations for domain logic.
- **Missing type checks** → Add `strict_types=1` and run with `--display-warnings`.
- **Coverage threshold** → Use `@requires PHP` to skip on incompatible versions.

## Optional: Laravel Feature Tests

```php
// tests/Feature/UserApiTest.php
namespace Tests\Feature;

use Tests\TestCase;

final class UserApiTest extends TestCase
{
    public function testCanGetUser(): void
    {
        $user = User::factory()->create(['name' => 'alice']);

        $response = $this->getJson("/api/users/{$user->id}");

        $response->assertOk();
        $response->assertJson(['name' => 'alice']);
    }
}
```

## Pest (Modern PHP Testing)

Pest is a rapidly growing testing framework built on top of PHPUnit with an elegant, function-based API. Many Laravel and modern PHP projects now use Pest as the default.

### Basic Test

```php
// tests/CalculatorTest.php
it('adds two numbers', function () {
    expect(Calculator::add(2, 3))->toBe(5);
});
```

### Dataset (Parametrized)

```php
// tests/MathTest.php
it('adds numbers correctly', function (int $a, int $b, int $expected) {
    expect(Math::add($a, $b))->toBe($expected);
})->with([
    [1, 2, 3],
    [-1, 1, 0],
    [0, 0, 0],
    [100, 200, 300],
]);
```

### Exception Testing

```php
// tests/ValidationTest.php
it('throws on negative age', function () {
    expect(fn () => Validator::validateAge(-1))
        ->toThrow(\InvalidArgumentException::class, 'non-negative');
});
```

### Laravel Feature Test

```php
// tests/Feature/UserApiTest.php
it('can get user', function () {
    $user = User::factory()->create(['name' => 'alice']);

    $response = $this->getJson("/api/users/{$user->id}");

    $response->assertOk()
             ->assertJson(['name' => 'alice']);
});
```

### Running Pest

```bash
./vendor/bin/pest                        # all tests
./vendor/bin/pest tests/CalculatorTest.php
./vendor/bin/pest --filter="adds two numbers"
./vendor/bin/pest --coverage --min=80
```

### PHPUnit → Pest Migration

```bash
composer require pestphp/pest:^3 --dev
./vendor/bin/pest --init                   # creates Pest.php config
# Rename TestCase classes to plain functions
# Replace $this->assert* with expect()->to*()
```

## Optional: Property-Based Testing

```bash
composer require --dev giorgiosironi/eris:^0.15
```

```php
use Eris\Generator;
use Eris\TestTrait;
use PHPUnit\Framework\TestCase;

final class CalculatorPropertyTest extends TestCase
{
    use TestTrait;

    public function testAdditionIsCommutative(): void
    {
        $this
            ->forAll(
                Generator\int(),
                Generator\int()
            )
            ->then(function (int $a, int $b) {
                self::assertSame(
                    Calculator::add($a, $b),
                    Calculator::add($b, $a)
                );
            });
    }
}
```

> Run with: `vendor/bin/phpunit tests/CalculatorPropertyTest.php`. Eris generates hundreds of random inputs per property to uncover edge cases. Target mathematical invariants (commutativity, associativity, identity).

## Alternatives

- **Pest**: Modern, elegant wrapper around PHPUnit with function-based API.
- **Codeception**: BDD-style with acceptance, functional, and unit testing.
- **Behat**: Gherkin-based BDD framework.
