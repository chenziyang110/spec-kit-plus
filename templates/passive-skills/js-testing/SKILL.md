---
name: js-testing
description: |
  Use ONLY when user explicitly requests JavaScript/TypeScript test code, Vitest/Jest configuration,
  test failure diagnosis, or coverage improvement for JS/TS projects.

  Triggers: "write test js", "vitest", "jest", "react test", "vue test", "MSW",
  "playwright", "fast-check", "coverage js", "snapshot test", "testing-library".

  Do NOT activate for: general JS/TS coding without test context, build tool configuration
  (Vite/webpack), npm/pnpm/yarn install issues, or TypeScript type-only questions.
origin: ECC
---

# JS/TS Testing (Agent Skill)

Agent-focused testing workflow for modern JavaScript/TypeScript using Vitest, the fastest-growing test framework with native Vite integration.

## When to Use

- Writing new JS/TS tests or fixing existing tests
- Designing unit/integration test coverage for JS/TS components
- Adding test coverage, CI gating, or regression protection
- Configuring Vitest/Jest workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing browser, Node, or isomorphic code

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-JS/TS projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (no module exports, global side-effects, hard-coded fetch/axios)
- **No test framework** is detected in the project (no vitest.config.ts, jest.config, test script in package.json)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or components
- A **required test dependency** (vitest, jest, @testing-library, MSW) is not installed
- The test would require **secrets, real credentials, or production API access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Isolation**: prefer dependency injection and mocks over global state.
- **Test layout**: `src/__tests__/` co-located, or `tests/unit`, `tests/integration`, `tests/fixtures`.
- **Mocks vs fakes**: mock for interactions (`vi.mock`, `vi.spyOn`), fake for stateful behavior.
- **In-source testing**: Vitest supports `.test.ts` co-located with source.
- **CI signal**: run affected tests first, then full suite with `--reporter=junit`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the runtime (Node/Browser) and framework (Vitest preferred, Jest if existing).
2. Check for existing test files (`*.test.ts`, `*.spec.ts`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, HTTP calls, DOM interactions, and async patterns.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks needed. Use `describe`/`it` with `expect`.
- **HTTP / API calls**: use MSW (Mock Service Worker) to intercept network requests; avoid mocking `fetch` directly.
- **React/Vue components**: use Testing Library (`@testing-library/react`, `@testing-library/vue`); test behavior, not implementation.
- **E2E flows**: use Playwright for critical user journeys.
- **Async code**: use `async/await` in tests; use `waitFor` for DOM assertions, `vi.advanceTimersByTime` for timers.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (HTTP, localStorage, IndexedDB, filesystem)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable at boundary (module import, fetch wrapper, axios instance)?
  → Yes → Mock at boundary (vi.mock, MSW, jest.mock)
  → No  → Q3

Q3: Needs real network behavior verification (API contract, error responses)?
  → Yes → MSW handlers with real-like responses
  → No  → Simple mock with hardcoded return values

Q4: Async (Promises/Observables/async-await)?
  → Yes → await/expect().resolves/expect().rejects
  → No  → Synchronous test sufficient

Q5: Browser rendering / user interaction?
  → Yes → Component test (RTL, Vue Test Utils) ⋯ or E2E (Playwright, Cypress)
  → No  → Standard unit test with Vitest/Jest
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output/DOM state.
2. **Boundary values**: empty arrays, `null`, `undefined`, `0`, `NaN`, empty strings.
3. **Error cases**: rejected promises, thrown errors, 4xx/5xx responses, invalid props.
4. **Interaction & state**: user events (click, type), form validation, loading/error/success states.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Component / Integration / E2E
- [ ] Framework: Vitest (or Jest) + Testing Library + MSW (if HTTP)
- [ ] Mocking: Yes/No — vi.mock / MSW / Playwright
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
npx vitest run <file_path>
npx vitest run --coverage
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `npx vitest run --coverage`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests run without parse errors (`npx vitest run`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are reset between tests (`vi.clearAllMocks()` in `beforeEach`).
- [ ] No `setTimeout` used for synchronization (use `waitFor` or `vi.useFakeTimers`).
- [ ] Flaky test guardrails applied (isolation, no real network in unit tests).

## TDD Workflow

Follow the RED → GREEN → REFACTOR loop:

1. **RED**: write a failing test that captures the new behavior
2. **GREEN**: implement the smallest change to pass
3. **REFACTOR**: clean up while tests stay green

```ts
// add.test.ts
import { describe, it, expect } from 'vitest'

function add(a: number, b: number): number // Provided by production code.

describe('add', () => {
  it('adds two numbers', () => { // RED
    expect(add(2, 3)).toBe(5)
  })
})

// src/add.ts
export function add(a: number, b: number): number { // GREEN
  return a + b
}

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (Vitest)

```ts
// calculator.test.ts
import { describe, it, expect } from 'vitest'

function add(a: number, b: number): number // Provided by production code.

describe('Calculator', () => {
  it('adds two numbers', () => {
    expect(add(2, 3)).toBe(5)
  })
})
```

### Setup / Teardown (Vitest)

```ts
// user-store.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest'

interface User { name: string }
class UserStore {
  private users: User[] = []
  seed(users: User[]) { this.users.push(...users) }
  find(name: string): User | undefined {
    return this.users.find(u => u.name === name)
  }
}

describe('UserStore', () => {
  let store: UserStore

  beforeEach(() => {
    store = new UserStore()
    store.seed([{ name: 'alice' }, { name: 'bob' }])
  })

  it('finds existing user', () => {
    const user = store.find('alice')
    expect(user).toBeDefined()
    expect(user!.name).toBe('alice')
  })
})
```

### Mocking (vi.mock / vi.spyOn)

```ts
// notifier.test.ts
import { describe, it, expect, vi } from 'vitest'

interface Notifier {
  send(message: string): void
}

class Service {
  constructor(private notifier: Notifier) {}
  publish(message: string) { this.notifier.send(message) }
}

describe('Service', () => {
  it('sends notifications', () => {
    const notifier: Notifier = { send: vi.fn() }
    const service = new Service(notifier)

    service.publish('hello')

    expect(notifier.send).toHaveBeenCalledWith('hello')
    expect(notifier.send).toHaveBeenCalledTimes(1)
  })
})
```

### Async Test

```ts
// api.test.ts
import { describe, it, expect, vi } from 'vitest'

async function fetchUser(id: string): Promise<{ name: string }> {
  return { name: 'alice' }
}

describe('API', () => {
  it('fetches user data', async () => {
    const user = await fetchUser('1')
    expect(user.name).toBe('alice')
  })

  it('handles errors', async () => {
    await expect(fetchUser('invalid')).rejects.toThrow()
  })
})
```

### Snapshot Testing

```ts
// component.test.tsx
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import Button from './Button'

describe('Button', () => {
  it('renders correctly', () => {
    const { container } = render(<Button label="Click me" />)
    expect(container).toMatchSnapshot()
  })
})
```

## Package.json Quickstart

```jsonc
// package.json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  },
  "devDependencies": {
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "msw": "^2.0.0",
    "fast-check": "^3.0.0"
  }
}
```

## Vitest Configuration

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',  // or 'jsdom' / 'happy-dom' for browser
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**'],
      exclude: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
    },
  },
})
```

```bash
npx vitest                    # watch mode
npx vitest run                # single run
npx vitest run --reporter=junit  # CI output
npx vitest run --coverage     # with coverage
```

## Running Tests

```bash
npx vitest run
npx vitest run src/calculator.test.ts
npx vitest run --reporter=junit --outputFile=test-results.xml
npx vitest related src/calculator.ts
```

## Debugging Failures

1. Re-run the single failing test with `.only()` or `--testNamePattern`.
2. Add `--reporter=verbose` for detailed output.
3. Use `console.log` with `--reporter=verbose` since Vitest captures stdout.
4. Use `--ui` mode for interactive debugging.
5. Expand to full suite once the root cause is fixed.

## Coverage

```bash
npx vitest run --coverage
npx vitest run --coverage --coverage.reporter=lcov
```

```ts
// vitest.config.ts — coverage configuration
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      thresholds: {
        branches: 80,
        functions: 80,
        lines: 80,
        statements: 80,
      },
    },
  },
})
```

## Mocking HTTP with MSW

MSW (Mock Service Worker) is the modern standard for intercepting and mocking HTTP requests in JavaScript/TypeScript tests. Unlike mocking `fetch` directly, MSW operates at the network level, making tests more realistic and easier to maintain.

```ts
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/user/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'alice' })
  }),
]
```

```ts
// tests/mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```ts
// vitest.setup.ts
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './tests/mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

```ts
// tests/api.test.ts
import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from './mocks/server'

describe('fetchUser', () => {
  it('returns user data', async () => {
    const user = await fetchUser('1')
    expect(user.name).toBe('alice')
  })

  it('handles server errors', async () => {
    server.use(
      http.get('/api/user/:id', () => {
        return new HttpResponse(null, { status: 500 })
      })
    )
    await expect(fetchUser('1')).rejects.toThrow('Server error')
  })
})
```

## E2E Testing with Playwright

For critical user journeys, use Playwright instead of unit tests.

```ts
// tests/e2e/login.spec.ts
import { test, expect } from '@playwright/test'

test('user can log in', async ({ page }) => {
  await page.goto('/login')
  await page.fill('[name=email]', 'alice@example.com')
  await page.fill('[name=password]', 'secret')
  await page.click('button[type=submit]')
  await expect(page).toHaveURL('/dashboard')
  await expect(page.locator('h1')).toContainText('Welcome')
})
```

```bash
npx playwright test
npx playwright test --ui
npx playwright test --headed
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
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: npm ci
      - run: npx vitest run --coverage --reporter=junit --outputFile=report.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: report.xml }
```

## Flaky Tests Guardrails

- Never use `setTimeout` for synchronization; use `waitFor` from Testing Library.
- Make temp directories unique per test with `fs.mkdtempSync()`.
- Avoid real time, network, or filesystem dependencies in unit tests.
- Use `vi.useFakeTimers()` for time-dependent code.
- Reset mocks between tests with `vi.clearAllMocks()` or `vi.resetAllMocks()`.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, undefined, and just-outside valid ranges.

```ts
// tests/validator.test.ts
import { describe, it, expect } from 'vitest'

describe('validateInput', () => {
  it.each([
    ['', 'empty string'],
    [null, 'null'],
    [undefined, 'undefined'],
    ['a'.repeat(10001), 'too long'],
    ['<script>alert(1)</script>', 'xss attempt'],
  ])('rejects %s (%s)', (input) => {
    expect(() => validateInput(input)).toThrow()
  })
})
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```ts
// tests/calculator.test.ts
import { describe, it, expect } from 'vitest'

describe('divide', () => {
  it('throws on divide by zero', () => {
    expect(() => divide(10, 0)).toThrow('Division by zero')
  })
})
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```ts
// tests/connection.test.ts
import { describe, it, expect } from 'vitest'

describe('Connection', () => {
  it('transitions through states', () => {
    const conn = new Connection()
    expect(conn.state).toBe('closed')
    conn.open()
    expect(conn.state).toBe('open')
    conn.close()
    expect(conn.state).toBe('closed')
    // Idempotency
    conn.close()
    expect(conn.state).toBe('closed')
  })
})
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `expect(value, 'description').toBe(...)` or descriptive `describe`/`it` blocks.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test rejected promises, `null`/`undefined`/empty inputs, 4xx/5xx responses.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at boundaries (HTTP with MSW, timers with `vi.useFakeTimers()`).*
- **The Free Ride**: Tests that execute code but assert nothing meaningful (e.g., `expect(true).toBe(true)`). *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long, complex test methods with no clear arrange/act/assert structure. *Fix: Follow AAA, avoid testing implementation details (test behavior, not state).*
- **Flaky Test**: Non-deterministic results from async, timers, or DOM. *Fix: Use `waitFor`, `act()`, `vi.useFakeTimers()`, avoid real network in unit tests.*

## Best Practices

### DO

- Keep tests deterministic and isolated
- Prefer dependency injection over globals
- Use `describe` / `it` nesting for readable test structure
- Separate unit vs integration tests in directory structure or config
- Run type checking with `vitest --typecheck`
- Use Testing Library for DOM/component tests (React, Vue, etc.)

### DON'T

- Don't depend on real time or network in unit tests
- Don't use `setTimeout` as synchronization when `waitFor` can be used
- Don't over-mock simple value objects
- Don't snapshot large dynamic objects that change frequently
- Don't test implementation details (private methods, internal state)

### Common Pitfalls

- **Leaking mock state** → Use `beforeEach` with `vi.clearAllMocks()`.
- **Relying on real timers** → Use `vi.useFakeTimers()` with `vi.advanceTimersByTime()`.
- **Flaky async tests** → Use `waitFor` or proper `await` instead of arbitrary timeouts.
- **Global test pollution** → Reset modules with `vi.resetModules()` in `beforeEach`.
- **Over-mocking** → Prefer integration-style tests that use real implementations for core logic.
- **Missing type checks** → Enable `--typecheck` flag in CI.
- **Brittle snapshots** → Keep snapshots small; prefer inline snapshots for critical structure.

## Optional Appendix: Property-Based Testing

Only use if the project already supports fast-check or similar.

- **fast-check**: property-based testing for TypeScript/JavaScript.

```ts
import { describe, it } from 'vitest'
import * as fc from 'fast-check'

function add(a: number, b: number): number { return a + b }

describe('add', () => {
  it('is commutative', () => {
    fc.assert(
      fc.property(fc.integer(), fc.integer(), (a, b) => {
        expect(add(a, b)).toBe(add(b, a))
      })
    )
  })
})
```

## Alternatives to Vitest

- **Jest**: mature, massive ecosystem, slower migration path.
- **Mocha + Chai**: flexible, no built-in mocking, requires more configuration.
- **Node test runner**: built-in since Node 20, minimal setup for simple projects.
