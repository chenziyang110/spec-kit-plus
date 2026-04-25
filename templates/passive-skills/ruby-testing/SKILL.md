---
name: ruby-testing
description: |
  Use ONLY when user explicitly requests Ruby test code, RSpec configuration,
  test failure diagnosis, or coverage improvement for Ruby projects.

  Triggers: "write test ruby", "rspec", "rails test", "factory bot",
  "simplecov", "vcr test", "shared examples", "shoulda matchers".

  Do NOT activate for: general Ruby coding without test context, gem/bundler
  issues, Rails model/controller implementation, or Ruby version management.
origin: ECC
---

# Ruby Testing (Agent Skill)

Agent-focused testing workflow for modern Ruby (3.2+) using RSpec, the dominant BDD-style test framework for Ruby.

## When to Use

- Writing new Ruby tests or fixing existing tests
- Designing unit/integration test coverage for Ruby components
- Adding test coverage, CI gating, or regression protection
- Configuring RSpec workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing Rails apps, gems, or Sinatra services

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Ruby projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (monkey-patched classes, hard-coded HTTP, no dependency injection)
- **No test framework** is detected (no rspec/minitest in Gemfile, no spec/ directory)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or classes
- A **required test dependency** (rspec, rspec-rails, factory_bot) is not installed
- The test would require **secrets, real credentials, or production database access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **BDD style**: `describe` / `context` / `it` blocks for readable specifications.
- **Test layout**: `spec/` directory mirroring `lib/` structure, `spec/spec_helper.rb`.
- **Mocks**: RSpec's built-in `double()`, `allow()`, `expect()`.
- **Factory pattern**: `factory_bot` for test data creation.
- **CI signal**: `bundle exec rspec --format progress --color`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Ruby version (3.2+) and framework (RSpec, Minitest).
2. Check for existing test files (`spec/`, `test/`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, side effects, ActiveRecord interactions, and async patterns.
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks. Use `describe`/`it` with `expect`.
- **External dependencies (DB, HTTP, filesystem)**: use RSpec doubles/mocks; prefer `factory_bot` for data, `VCR` for HTTP recording, `DatabaseCleaner` for DB isolation.
- **Rails applications**: use `type: :request` for API tests, `type: :model` for model tests; use `travel_to` for time freezing.
- **Async code**: Ruby is mostly synchronous; use `have_received` for mock verification.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (DB, HTTP, filesystem)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (DI, service object, HTTP client)?
  → Yes → Mock at boundary (RSpec doubles, VCR cassettes)
  → No  → Q3

Q3: Needs real DB behavior?
  → Yes → DatabaseCleaner + factory_bot + in-memory/test DB
  → No  → Use simple double/stub

Q4: Rails request/controller spec?
  → Yes → type: :request with rspec-rails helpers
  → No  → Q5

Q5: Time-dependent code?
  → Yes → travel_to / Timecop for time freezing
  → No  → Standard describe/it with expect()
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output/response.
2. **Boundary values**: empty arrays, `nil`, empty strings, `0`, `Time.at(0)`.
3. **Error cases**: exceptions (`raise_error`), validation errors, 4xx/5xx responses, nil pointer scenarios.
4. **State & database**: shared mutable state, `let` vs `let!` evaluation order, transaction isolation.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Request / Feature / System
- [ ] Framework: RSpec + factory_bot + VCR (if HTTP)
- [ ] Mocking: Yes/No — doubles / stubs / VCR cassettes
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
bundle exec rspec spec/xxx_spec.rb
bundle exec rspec --tag ~slow
bundle exec rspec --only-failures
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `bundle exec rspec` (with SimpleCov configured in spec_helper.rb)
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests run without parse errors (`bundle exec rspec`).
- [ ] Each `it` block has exactly one logical assertion focus.
- [ ] Mocks are reset between tests (`verify_partial_doubles` enabled).
- [ ] No `sleep` used for synchronization (use `Timecop` or Capybara waiters).
- [ ] Flaky test guardrails applied (`DatabaseCleaner`, `--order random`, deterministic factories).

## TDD Workflow

```ruby
# spec/add_spec.rb
def add(a, b) = nil # stub

RSpec.describe 'add' do
  it 'adds two numbers' do # RED
    expect(add(2, 3)).to eq(5)
  end
end

# lib/add.rb
def add(a, b) = a + b # GREEN

# REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test (RSpec)

```ruby
# spec/calculator_spec.rb
RSpec.describe Calculator do
  describe '.add' do
    it 'adds two numbers' do
      expect(Calculator.add(2, 3)).to eq(5)
    end

    it 'handles negative numbers' do
      expect(Calculator.add(-1, 1)).to eq(0)
    end
  end
end
```

### Subject / Let / Before

```ruby
# spec/user_store_spec.rb
RSpec.describe UserStore do
  subject(:store) { described_class.new }

  before do
    store.seed([User.new('alice'), User.new('bob')])
  end

  describe '#find' do
    it 'returns existing user' do
      user = store.find('alice')
      expect(user).not_to be_nil
      expect(user.name).to eq('alice')
    end

    it 'returns nil for missing user' do
      expect(store.find('charlie')).to be_nil
    end
  end
end
```

### Mocking (RSpec Mocks)

```ruby
# spec/service_spec.rb
RSpec.describe Service do
  it 'sends notifications' do
    notifier = double('Notifier', send: nil)
    service = described_class.new(notifier)

    service.publish('hello')

    expect(notifier).to have_received(:send).with('hello').once
  end
end
```

### Stubs and Message Expectations

```ruby
RSpec.describe PaymentService do
  it 'charges the correct amount' do
    gateway = instance_double('PaymentGateway')
    allow(gateway).to receive(:charge).with(100.0).and_return(true)

    service = described_class.new(gateway)
    result = service.process_order(100.0)

    expect(result).to be true
    expect(gateway).to have_received(:charge).with(100.0)
  end
end
```

### Parametrized Tests

> **Requires:** `gem 'rspec-parameterized'` in your Gemfile.

```ruby
# spec/math_spec.rb
RSpec.describe Math do
  describe '.add' do
    where(:a, :b, :expected) do
      [
        [1, 2, 3],
        [-1, 1, 0],
        [0, 0, 0],
        [100, 200, 300],
      ]
    end

    with_them do
      it 'returns the sum' do
        expect(described_class.add(a, b)).to eq(expected)
      end
    end
  end
end
```

### Shared Examples

```ruby
RSpec.shared_examples 'a notifier' do
  it 'responds to #send' do
    expect(subject).to respond_to(:send)
  end
end

RSpec.describe EmailNotifier do
  it_behaves_like 'a notifier'
end

RSpec.describe SmsNotifier do
  it_behaves_like 'a notifier'
end
```

### Exception Testing

```ruby
RSpec.describe Validator do
  describe '.validate_age' do
    it 'raises on negative age' do
      expect { described_class.validate_age(-1) }
        .to raise_error(ArgumentError, /non-negative/)
    end
  end
end
```

### Controller Test (Rails)

```ruby
# spec/requests/users_spec.rb
RSpec.describe 'Users API', type: :request do
  describe 'GET /users/:id' do
    it 'returns the user' do
      user = User.create!(name: 'alice')

      get "/users/#{user.id}"

      expect(response).to have_http_status(:ok)
      expect(JSON.parse(response.body)['name']).to eq('alice')
    end
  end
end
```

## Gemfile Quickstart

```ruby
# Gemfile
group :test do
  gem 'rspec', '~> 3.13'
  gem 'rspec-rails', '~> 7.0'  # if Rails
  gem 'factory_bot_rails', '~> 6.0' # if Rails
  gem 'faker', '~> 3.0'        # test data generation
  gem 'shoulda-matchers', '~> 6.0' # if Rails, for model matchers
  gem 'database_cleaner-active_record', '~> 2.0' # if Rails
  gem 'simplecov', '~> 0.22', require: false
  gem 'vcr', '~> 6.0'                        # HTTP recording
end
```

## RSpec Configuration

```ruby
# spec/spec_helper.rb
require 'simplecov'
SimpleCov.start

RSpec.configure do |config|
  config.expect_with :rspec do |expectations|
    expectations.include_chain_clauses_in_custom_matcher_descriptions = true
  end

  config.mock_with :rspec do |mocks|
    mocks.verify_partial_doubles = true
  end

  config.shared_context_metadata_behavior = :apply_to_host_groups
  config.filter_run_when_matching :focus
  config.example_status_persistence_file_path = 'spec/examples.txt'
  config.disable_monkey_patching!
  config.profile_examples = 10
  config.order = :random
  Kernel.srand config.seed
end
```

## Running Tests

```bash
bundle exec rspec                         # all specs
bundle exec rspec spec/calculator_spec.rb  # single file
bundle exec rspec spec/calculator_spec.rb:5  # line number
bundle exec rspec --tag slow              # tagged tests
bundle exec rspec --tag ~slow             # exclude slow
bundle exec rspec --only-failures          # rerun failures
bundle exec rspec --next-failure           # one failure at a time
bundle exec rspec --format documentation   # verbose
```

## Coverage

```ruby
# spec/spec_helper.rb (top)
require 'simplecov'
SimpleCov.start 'rails' do # or 'rails' adapter for Rails
  minimum_coverage 90
  maximum_coverage_drop 5
  add_filter '/spec/'
  add_filter '/config/'
end
```

```bash
bundle exec rspec
open coverage/index.html   # view HTML report
```

## Debugging Failures

1. Re-run with `--format documentation` for full output.
2. Use `--only-failures` to focus on failing tests.
3. Add `require 'pry'; binding.pry` in test or code.
4. Use `--seed <seed>` to reproduce randomized order.
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
      - uses: ruby/setup-ruby@v1
        with: { ruby-version: '3.3' }
      - run: bundle install
      - run: bundle exec rspec --format progress --format RspecJunitFormatter --out report.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: test-results, path: report.xml }
```

## Flaky Tests Guardrails

- Never use `sleep(n)` for synchronization; use `Capybara` waiters or `have_selector`.
- Use `DatabaseCleaner` with truncation for test DB isolation.
- Use `Faker::UniqueGenerator` for unique test data.
- Avoid `Time.now` — use `Timecop.freeze` or `travel_to`.
- Run with `--order random` to surface ordering dependencies.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, nil, and just-outside valid ranges.

```ruby
# spec/validator_spec.rb
RSpec.describe Validator do
  describe '.validate' do
    ['', ' ', 'a' * 10001].each do |input|
      it "rejects #{input.inspect}" do
        expect { described_class.validate(input) }.to raise_error(ArgumentError)
      end
    end
  end
end
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```ruby
# spec/calculator_spec.rb
RSpec.describe Calculator do
  describe '.divide' do
    it 'raises on divide by zero' do
      expect { described_class.divide(10, 0) }.to raise_error(ZeroDivisionError)
    end
  end
end
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```ruby
# spec/connection_spec.rb
RSpec.describe Connection do
  describe '#state' do
    it 'transitions through states' do
      conn = described_class.new
      expect(conn.state).to eq(:closed)
      conn.open
      expect(conn.state).to eq(:open)
      conn.close
      expect(conn.state).to eq(:closed)
      # Idempotency
      conn.close
      expect(conn.state).to eq(:closed)
    end
  end
end
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `expect(actual).to eq(expected)` with descriptive `describe`/`context`/`it` nesting.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `nil` values, `expect { ... }.to raise_error(...)`, edge conditions.*
- **Mock Overdose**: Too many doubles hiding integration issues or coupling tests to implementation. *Fix: Use `instance_double` over `double`; mock only at service boundaries.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable expectation.*
- **Obscure Test**: Long `it` blocks with no clear setup/verify structure. *Fix: Follow AAA, use `let`/`let!` for lazy setup, keep expectations focused.*
- **Flaky Test**: Non-deterministic results from DB state, time, or external services. *Fix: Use `DatabaseCleaner`, `travel_to`, `VCR.use_cassette`, `--order random`.*

## Best Practices

### DO

- Use `let` and `subject` for lazy-evaluated test values
- Use `described_class` instead of hardcoded class names
- Keep specs focused — one `it` block per behavior
- Use `context` blocks for different scenarios
- Use `factory_bot` for test data (Rails)
- Use `shoulda-matchers` for concise model validations/associations

### DON'T

- Don't use `sleep` for synchronization
- Don't use `before(:all)` for mutable state (leaks between tests)
- Don't write overly nested `context` blocks
- Don't use `should` syntax (old style) — use `expect`
- Don't use `subject` when a named `let` is clearer
- Don't test private methods directly

### Common Pitfalls

- **Flaky DB state** → Use `DatabaseCleaner` with truncation for non-transactional tests.
- **Time-dependent tests** → Use `Timecop` or `travel_to` (Rails).
- **Order-dependent tests** → Use `--order random` with `--seed` in CI.
- **Slow Capybara tests** → Use `:js` tag only when needed; use `:rack_test` as default.
- **Over-mocking** → Prefer real objects for core domain logic.
- **Stale snapshots** → Use `approvals` gem carefully; review snapshot changes in PR.
- **Missing coverage gates** → Add `SimpleCov.minimum_coverage` in CI.

## Optional Appendix: Property-Based Testing

```ruby
# Using rspec_eventually or rspec-given
require 'rantly/rspec_extensions'

RSpec.describe 'add property' do
  it 'is commutative' do
    property_of {
      [integer, integer]
    }.check { |a, b|
      expect(Math.add(a, b)).to eq(Math.add(b, a))
    }
  end
end
```

## Alternatives

- **Minitest**: Ruby's built-in test framework, simpler, faster.
- **Test::Unit**: Classic xUnit style, bundled with Ruby, compatible with RSpec runner.
- **Cucumber**: Gherkin-based BDD for acceptance tests.
