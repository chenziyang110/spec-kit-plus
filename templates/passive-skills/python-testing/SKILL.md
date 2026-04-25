---
name: python-testing
description: |
  Use ONLY when user explicitly requests Python test code, pytest configuration,
  test failure diagnosis, or coverage improvement for Python projects.

  Triggers: "write test", "pytest", "unit test python", "coverage python",
  "flaky test python", "mock python", "test fixture", "parametrize", "factory boy",
  "freezegun", "pytest-asyncio", "pytest-cov".

  Do NOT activate for: general Python coding without test context, linting (flake8/ruff),
  type checking (mypy), or non-test package management (pip install general).
origin: ECC
---

# Python Testing (Agent Skill)

Agent-focused testing workflow for modern Python (3.10+) using pytest, the industry-standard test framework.

## When to Use

- Writing new Python tests or fixing existing tests
- Designing unit/integration test coverage for Python components
- Adding test coverage, CI gating, or regression protection
- Configuring pytest workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing async code, CLI tools, or web frameworks

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Python projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (no DI, global mutable state, hard-coded external calls, no interfaces)
- **No test framework** is detected in the project (no `pytest.ini`, `pyproject.toml` test config, `conftest.py`)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or components
- A **required test dependency** (`pytest`, `pytest-asyncio`, `pytest-cov`) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer dependency injection and fixtures over global state.
- **Test layout**: `tests/unit`, `tests/integration`, `tests/conftest.py`, `tests/testdata/`.
- **Fixtures**: pytest's dependency injection mechanism for setup/teardown.
- **Parametrization**: `@pytest.mark.parametrize` for testing multiple inputs.
- **CI signal**: run subset first, then full suite with `--tb=short -x`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Python version (3.10+) and test framework (pytest preferred).
2. Check for existing test files (`tests/`, `*_test.py`, `test_*.py`) to infer naming conventions.
3. Analyze the code under test: identify public API surface, side effects, I/O boundaries (DB, HTTP, filesystem), and async/await usage.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / value objects**: unit tests only, no mocks needed. Use `pytest.mark.parametrize` for multiple cases.
- **External dependencies (DB, HTTP, filesystem)**: use `unittest.mock`, `pytest.monkeypatch`, or `responses`/`pytest-httpx`; prefer `tmp_path` for filesystem.
- **Async code**: use `pytest-asyncio` with `@pytest.mark.asyncio` and `asyncio_mode = auto`.
- **Web frameworks (Django/FastAPI/Flask)**: use framework-specific test clients (`django.test.Client`, `TestClient`).

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem, network)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable at code boundary (DI, interface, parameter injection)?
  → Yes → Mock at boundary (unittest.mock, monkeypatch, responses)
  → No  → Q3

Q3: Needs real behavior verification (SQL, transactions)?
  → Yes → Integration test (Django TestCase, FastAPI TestClient, testcontainers)
  → No  → Use fake/stub (in-memory repo, tmp_path files)

Q4: Async code (asyncio)?
  → Yes → @pytest.mark.asyncio + asyncio_mode = auto
  → No  → Synchronous test sufficient

Q5: Web/browser rendering?
  → Yes → Django LiveServerTestCase, Playwright, Selenium
  → No  → Standard unit test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output.
2. **Boundary values**: empty string, zero, `None`, max length, empty collection.
3. **Error cases**: invalid types, exceptions (`pytest.raises`), permission errors, timeout scenarios.
4. **State & concurrency**: shared mutable state, race conditions, cache invalidation.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Integration / E2E
- [ ] Framework: pytest (with asyncio/monkeypatch if needed)
- [ ] Mocking: Yes/No — tools used
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
pytest -x --tb=short -v <file_path>
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `pytest --cov=src --cov-report=term-missing`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests parse without syntax errors (`pytest --collect-only`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are reset between tests (use `yield` fixtures or `clear` in `setup_method`).
- [ ] No `time.sleep` used for synchronization (use `freezegun` or `asyncio.sleep`).
- [ ] Flaky test guardrails applied (isolation, determinism, `tmp_path`).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```python
# tests/test_add.py
def add(a: int, b: int) -> int:  # Provided by production code.
    ...

def test_adds_two_numbers():  # RED
    assert add(2, 3) == 5

# src/add.py
def add(a: int, b: int) -> int:  # GREEN
    return a + b

# REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (pytest)

```python
# tests/test_calculator.py

def add(a: int, b: int) -> int:  # Provided by production code.
    ...

class TestCalculator:
    def test_adds_two_numbers(self):
        assert add(2, 3) == 5
```

### Fixtures (pytest)

```python
# tests/conftest.py
import pytest
from typing import Optional

class User:
    def __init__(self, name: str):
        self.name = name

class UserStore:
    def __init__(self):
        self._users: list[User] = []

    def seed(self, users: list[User]) -> None:
        self._users.extend(users)

    def find(self, name: str) -> Optional[User]:
        return next((u for u in self._users if u.name == name), None)

@pytest.fixture
def user_store():
    store = UserStore()
    store.seed([User("alice"), User("bob")])
    return store

# tests/test_user_store.py
def test_finds_existing_user(user_store):
    user = user_store.find("alice")
    assert user is not None
    assert user.name == "alice"
```

### Mocking (pytest + monkeypatch / unittest.mock)

```python
# tests/test_notifier.py
from unittest.mock import Mock

class Service:
    def __init__(self, notifier):
        self._notifier = notifier

    def publish(self, message: str):
        self._notifier.send(message)

def test_sends_notifications():
    notifier = Mock()
    service = Service(notifier)

    service.publish("hello")

    notifier.send.assert_called_once_with("hello")
```

### Async Test (pytest-asyncio)

```python
# tests/test_api.py
import pytest

async def fetch_user(user_id: str) -> dict:
    return {"name": "alice"}

@pytest.mark.asyncio
async def test_fetches_user_data():
    user = await fetch_user("1")
    assert user["name"] == "alice"

@pytest.mark.asyncio
async def test_handles_errors():
    with pytest.raises(ValueError):
        raise ValueError("invalid id")
```

### Parametrized Test

```python
# tests/test_math.py
import pytest

def add(a: int, b: int) -> int:
    return a + b

@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
    (100, 200, 300),
])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

### Exception Testing

```python
# tests/test_validation.py
import pytest

def validate_age(age: int) -> None:
    if age < 0:
        raise ValueError("age must be non-negative")

def test_raises_on_negative_age():
    with pytest.raises(ValueError, match="must be non-negative"):
        validate_age(-1)
```

## Pytest Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    asyncio: marks tests as async
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "asyncio: marks tests as async",
]
```

```bash
pytest                       # run all tests
pytest -v                    # verbose
pytest -x                    # stop on first failure
pytest --tb=short            # shorter traceback
pytest -k "test_add"         # run tests matching expression
pytest -m "not slow"         # run all except slow tests
pytest --coverage            # with coverage (pytest-cov>=6.0)
```

### Async Configuration (pytest 8.0+)

pytest-asyncio changed its default mode in pytest 8.0. Explicitly set the mode to avoid deprecation warnings:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Parallel Execution (pytest-xdist)

```bash
# Install: pip install pytest-xdist>=3.6
pytest -n auto          # use all CPU cores
pytest -n 4             # use 4 workers
pytest -n auto --dist loadgroup  # group related tests
```

## Running Tests

```bash
pytest
pytest tests/test_calculator.py
pytest tests/test_calculator.py::test_add
pytest -x --tb=short -v
pytest --junitxml=report.xml
pytest --coverage --coverage-report=html
```

## Debugging Failures

1. Re-run with `-x --tb=long -v` for maximum detail on the first failure.
2. Use `--pdb` to drop into debugger on failure.
3. Add `assert 0, repr(variable)` for quick inspection.
4. Use `-k` filter to run only the failing test.
5. Expand to full suite once the root cause is fixed.

## Coverage

```bash
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=xml --cov-report=html
```

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.coverage.report]
show_missing = true
fail_under = 80
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
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install pytest>=8.3 pytest-cov>=6.0 pytest-xdist>=3.6
      - run: pytest -n auto --cov=src --cov-report=xml --junitxml=report.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: report.xml }
```

## Flaky Tests Guardrails

- Never use `time.sleep` for synchronization; use `await asyncio.sleep(0)` or `pytest-timeout`.
- Make temp directories unique per test using `tmp_path` fixture.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use `freezegun` for time-dependent code.
- Use `pytest-repeat` with `--count 10` to reproduce flakiness.

### Test Data Generation (factory-boy)

```python
# tests/factories.py
import factory
from myapp.models import User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    name = factory.Faker("name")
    email = factory.Faker("email")
    age = factory.Faker("random_int", min=18, max=90)

# tests/test_user_service.py
def test_creates_user():
    user = UserFactory()  # generates fake but deterministic data
    assert user.name is not None
    assert user.age >= 18
```

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```python
# tests/test_validator.py
import pytest

@pytest.mark.parametrize("input,expected_error", [
    ("", ValueError),                     # empty string
    (None, TypeError),                    # null boundary
    ("a" * 10001, ValueError),            # length overflow
    ("<script>alert(1)</script>", ValueError),  # security boundary
])
def test_validate_input_boundary(input, expected_error):
    with pytest.raises(expected_error):
        validate_input(input)
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```python
# tests/test_calculator.py
def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        divide(10, 0)

def test_parse_int_rejects_non_numeric():
    with pytest.raises(ValueError):
        parse_int("not-a-number")
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```python
# tests/test_connection.py
def test_connection_state_transitions():
    conn = Connection()
    assert conn.state == "closed"
    conn.open()
    assert conn.state == "open"
    conn.close()
    assert conn.state == "closed"
    # Idempotency check
    conn.close()
    assert conn.state == "closed"
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `pytest` assertion introspection with clear variable names.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Ensure `pytest.raises` for exceptions, test `None`/empty/zero inputs.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at architectural boundaries (I/O, external services), not internal collaborators.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful (e.g., `assert response` without checking content). *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long, complex test methods with no clear arrange/act/assert structure. *Fix: Follow AAA (Arrange-Act-Assert), use descriptive test names.*
- **Flaky Test**: Non-deterministic results from time, order, or network dependencies. *Fix: Use `freezegun`, `tmp_path`, fixed seeds, fixture isolation.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Use fixtures for setup/teardown instead of `setup_method`/`teardown_method`
- Use `tmp_path` fixture for temporary files
- Separate unit vs integration tests in markers or directory structure
- Use `parametrize` to cover edge cases
- Use `pytest.approx()` for floating-point comparisons
- Prefer `assert` over `self.assertEqual` (pytest style)

### DON'T

- Don't depend on real time, network, or external services in unit tests
- Don't use `time.sleep` for synchronization
- Don't use global state that leaks between tests
- Don't test implementation details (private methods prefixed with `_`)
- Don't write overly large test functions — test one behavior per test

### Common Pitfalls

- **Leaking fixture state** → Use `yield` fixtures with teardown after yield.
- **Relying on real time** → Use `freezegun` or pass a clock dependency.
- **Flaky async tests** → Use `pytest-asyncio` with `@pytest.mark.asyncio`.
- **Global state pollution** → Reset singletons and module-level state in fixtures.
- **Over-mocking** → Prefer integration tests for core logic; mock only external boundaries.
- **Missing coverage config** → Add `--cov` with fail-under in CI.
- **Slow test suite** → Mark slow tests with `@pytest.mark.slow` and separate in CI.

## Optional Appendix: Property-Based Testing

Only use if the project already supports Hypothesis.

- **Hypothesis**: property-based testing for Python.

```python
from hypothesis import given, strategies as st

def add(a: int, b: int) -> int:
    return a + b

@given(a=st.integers(), b=st.integers())
def test_add_is_commutative(a, b):
    assert add(a, b) == add(b, a)
```

## Alternatives to pytest

- **unittest**: built-in, xUnit-style, compatible with pytest runner.
- **nose2**: plugin-based successor to nose.
- **doctest**: embedded tests in docstrings, best for simple validation.
