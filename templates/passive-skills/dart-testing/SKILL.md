---
name: dart-testing
description: |
  Use ONLY when user explicitly requests Dart/Flutter test code, flutter_test/mockito configuration,
  test failure diagnosis, or coverage improvement for Dart/Flutter projects.

  Triggers: "write test dart", "flutter test", "mockito dart", "bloc test",
  "widget test", "flutter coverage", "golden test", "mocktail", "patrol".

  Do NOT activate for: general Dart/Flutter coding without test context, pub get/build
  errors, Flutter widget implementation, or state management without test needs.
origin: ECC
---

# Dart/Flutter Testing (Agent Skill)

Agent-focused testing workflow for Dart/Flutter using the built-in `test` package, `flutter_test` for widgets, and `mockito` for mocking.

## When to Use

- Writing new Dart/Flutter tests or fixing existing tests
- Designing unit/integration/widget test coverage for Dart/Flutter apps
- Adding test coverage, CI gating, or regression protection
- Configuring test workflows for consistent execution
- Investigating test failures or flaky behavior
- Testing Flutter UI, business logic, or package libraries

### When NOT to Use

- Implementing new product features without test changes
- Large-scale refactors unrelated to test coverage or failures
- Performance tuning without test regressions to validate
- Non-Dart/Flutter projects or non-test tasks

### Stop Conditions — When to ASK instead of generating

Before generating any test code, STOP and ask the user if:
- The code under test has **zero testability** (no DI, hard-coded HTTP, widget logic embedded in build methods)
- **No test framework** is detected (no `test`/`flutter_test` in pubspec.yaml dev_dependencies)
- The request is **ambiguous**: "test my app" or "add tests" without specifying files or widgets
- A **required test dependency** (mockito, mocktail, bloc_test) is not installed
- The test would require **secrets, real credentials, or production API access**

## Core Concepts

- **TDD loop**: red → green → refactor (tests first, minimal fix, then cleanups).
- **Three tiers**: unit tests (fastest), widget tests (medium), integration tests (slowest).
- **Test layout**: `test/` directory mirroring `lib/` structure, `test/test_helpers/`.
- **Mocks**: `mockito` with `build_runner` for code-generated mock classes.
- **Stream testing**: `expectLater()` for async stream assertions.
- **CI signal**: `flutter test --machine` or `dart test --reporter json`.

## Agent Execution Protocol

When this skill is activated, follow this exact execution sequence:

### Phase 1: Context Analysis
Before writing any test code:
1. Identify the Dart/Flutter SDK version and test framework (`test`, `flutter_test`).
2. Check for existing test files (`test/`) to infer naming conventions and style.
3. Analyze the code under test: identify public API surface, `Stream`/`Future` usage, widget tree, and state management (BLoC, Riverpod, etc.).
4. Determine request type: (a) new tests, (b) fixing broken tests, (c) coverage improvement, (d) flaky test diagnosis.

### Phase 2: Strategy Selection
Based on Phase 1, select the appropriate strategy:
- **Pure functions / utilities**: unit tests only, no mocks. Use `group()`/`test()` with `expect`.
- **External dependencies (HTTP, DB)**: use `MockClient` from `http/testing.dart` or `mockito`/`mocktail`.
- **Flutter widgets**: use `testWidgets()` with `tester.pumpWidget()`; use `find.byKey()` for discovery.
- **State management (BLoC)**: use `blocTest()` from `bloc_test` package for state emission testing.
- **Async code**: use `async` test blocks with `expectLater()` for Streams.

### Decision Tree (Complex Scenarios)

```text
Q1: External I/O (HTTP, DB, platform channels)?
  → Yes → Q2
  → No  → Pure unit test, no mocks needed

Q2: Mockable (interface, abstract class, MockClient)?
  → Yes → Mock at boundary (mockito @GenerateMocks, mocktail)
  → No  → Q3

Q3: Widget rendering?
  → Yes → widgetTest + tester.pumpWidget() + find.byKey()
  → No  → Q4

Q4: State management (BLoC/Cubit)?
  → Yes → blocTest() with expectStates/expectIsar
  → No  → Standard group()/test() with expect()

Q5: End-to-end / native automation?
  → Yes → IntegrationTest / patrol
  → No  → Standard unit test
```

### Phase 3: Test Case Design
Apply systematic test design before coding:
1. **Happy path**: normal input → expected output/widget state.
2. **Boundary values**: empty lists, `null`, `0`, empty strings, `DateTime(0)`.
3. **Error cases**: exceptions (`throwsA`), `Future.error`, widget not found (`findsNothing`).
4. **State & interaction**: user taps, form validation, loading/error/success widget states.

### Phase 4: Code Generation
Output tests in this exact structure:
```
#### Test Strategy Summary
- [ ] Scope: Unit / Widget / Integration
- [ ] Framework: test / flutter_test + mockito/mocktail + bloc_test (if BLoC)
- [ ] Mocking: Yes/No — mockito / mocktail / MockClient
- [ ] Edge cases covered: <list>

#### Generated Test Code
<file_path>
<code>

#### Running Commands
```bash
dart test test/xxx_test.dart
flutter test test/widget/xxx_test.dart
flutter test --coverage
```

#### Coverage Impact (if applicable)
- Estimated coverage change: <X%>
- Command to verify: `flutter test --coverage && genhtml coverage/lcov.info -o coverage/html`
```

### Phase 5: Verification Checklist
Before completing, verify:
- [ ] Tests run without errors (`dart test` / `flutter test`).
- [ ] Each test has exactly one logical assertion focus.
- [ ] Mocks are reset between tests (reconstruct in `setUp`).
- [ ] No `Future.delayed` used for synchronization (use `tester.pumpAndSettle()`).
- [ ] Flaky test guardrails applied (`tester.pumpAndSettle()`, unique test data, golden file reviews).

## TDD Workflow

```dart
// test/add_test.dart
int add(int a, int b) => throw UnimplementedError(); // stub

void main() {
  test('adds two numbers', () { // RED
    expect(add(2, 3), equals(5));
  });
}

// lib/add.dart
int add(int a, int b) => a + b; // GREEN

// REFACTOR: simplify/rename once tests pass
```

## Code Examples

### Basic Unit Test

```dart
// test/calculator_test.dart
import 'package:test/test.dart';

void main() {
  group('Calculator', () {
    test('adds two numbers', () {
      expect(Calculator.add(2, 3), equals(5));
    });

    test('handles negative numbers', () {
      expect(Calculator.add(-1, 1), equals(0));
    });
  });
}
```

### Setup / Teardown

```dart
// test/user_store_test.dart
import 'package:test/test.dart';

void main() {
  late UserStore store;

  setUp(() {
    store = UserStore();
    store.seed([User('alice'), User('bob')]);
  });

  tearDown(() {
    store.dispose();
  });

  group('find', () {
    test('returns existing user', () {
      final user = store.find('alice');

      expect(user, isNotNull);
      expect(user!.name, equals('alice'));
    });

    test('returns null for missing user', () {
      expect(store.find('charlie'), isNull);
    });
  });
}
```

### Mocking (mockito)

```dart
// test/notifier_test.dart
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:test/test.dart';

import 'notifier_test.mocks.dart';

@GenerateMocks([Notifier])
void main() {
  test('sends notifications', () {
    final notifier = MockNotifier();
    final service = Service(notifier);

    service.publish('hello');

    verify(notifier.send('hello')).called(1);
  });
}
```

```dart
// notifier.dart
abstract class Notifier {
  void send(String message);
}
```

```dart
// notifier_test.mocks.dart (generated by build_runner)
```

### Async Test

```dart
// test/api_test.dart
void main() {
  test('fetches user data', () async {
    final user = await fetchUser('1');
    expect(user.name, equals('alice'));
  });

  test('handles errors', () async {
    expect(
      () => fetchUser('invalid'),
      throwsA(isA<Exception>()),
    );
  });
}
```

### Stream Test

```dart
// test/stream_test.dart
void main() {
  test('emits values in order', () {
    final controller = StreamController<int>();

    expectLater(
      controller.stream,
      emitsInOrder([1, 2, 3, emitsDone]),
    );

    controller.add(1);
    controller.add(2);
    controller.add(3);
    controller.close();
  });
}
```

### Flutter Widget Test

```dart
// test/widget/login_button_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:my_app/widgets/login_button.dart';

void main() {
  testWidgets('shows login button', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: LoginButton(),
    ));

    expect(find.text('Login'), findsOneWidget);
  });

  testWidgets('triggers onPressed callback', (tester) async {
    var pressed = false;

    await tester.pumpWidget(MaterialApp(
      home: LoginButton(onPressed: () => pressed = true),
    ));

    await tester.tap(find.text('Login'));
    expect(pressed, isTrue);
  });
}
```

### BLoC State Testing (bloc_test)

```dart
// test/counter_bloc_test.dart
import 'package:bloc_test/bloc_test.dart';
import 'package:test/test.dart';

void main() {
  blocTest<CounterBloc, int>(
    'emits [1] when Increment is added',
    build: () => CounterBloc(),
    act: (bloc) => bloc.add(Increment()),
    expect: () => [1],
  );

  blocTest<CounterBloc, int>(
    'emits [1, 0] when Increment then Decrement is added',
    build: () => CounterBloc(),
    act: (bloc) => bloc
      ..add(Increment())
      ..add(Decrement()),
    expect: () => [1, 0],
  );
}
```

### Flutter Integration Test

```dart
// test_driver/app_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('full app flow', (tester) async {
    await tester.pumpWidget(const MyApp());

    // Wait for splash screen
    await tester.pumpAndSettle();

    // Navigate to login
    await tester.tap(find.text('Get Started'));
    await tester.pumpAndSettle();

    expect(find.text('Welcome'), findsOneWidget);
  });
}
```

### Data-Driven Test

```dart
void main() {
  final cases = [
    (a: 1, b: 2, expected: 3),
    (a: -1, b: 1, expected: 0),
    (a: 0, b: 0, expected: 0),
    (a: 100, b: 200, expected: 300),
  ];

  for (final (a, b, expected) in cases) {
    test('add($a, $b) = $expected', () {
      expect(Calculator.add(a, b), equals(expected));
    });
  }
}
```

## Pubspec Quickstart

```yaml
# pubspec.yaml
dev_dependencies:
  test: ^1.25.0
  flutter_test:
    sdk: flutter
  mockito: ^5.4.0
  build_runner: ^2.4.0
  mocktail: ^1.0.0
  bloc_test: ^9.0.0
  integration_test:
    sdk: flutter
  flutter_lints: ^4.0.0
```

## Running Tests

```bash
dart test                                    # pure Dart package
dart test test/calculator_test.dart           # single file
dart test --name "adds two numbers"           # match name
dart test --reporter expanded                 # verbose

flutter test                                  # all Flutter tests
flutter test test/widget/login_button_test.dart  # single file
flutter test --name "Login"                   # match name
flutter test --coverage                       # with coverage
flutter test --update-goldens                 # update golden files
flutter test --integration-test               # integration tests
flutter drive --driver=test_driver/integration_test.dart
```

## Coverage

```bash
flutter test --coverage
# generates coverage/lcov.info

# Install lcov tools (if available)
genhtml coverage/lcov.info -o coverage/html
```

```yaml
# pubspec.yaml — coverage threshold (using very_good_analysis)
dev_dependencies:
  very_good_analysis: ^6.0.0
```

```bash
# Using very_good_cli
very_good test --coverage --min-coverage 80
```

## Debugging Failures

1. Re-run with `--reporter expanded` for full output.
2. Use `debugPrint = (String msg, {int? wrapWidth}) => print(msg);` to capture Flutter print.
3. Use `tester.binding.setSurfaceSize(Size(width, height))` for specific screen sizes.
4. Use `--update-goldens` when golden files intentionally changed.
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
      - uses: subosito/flutter-action@v2
        with: { flutter-version: '3.24.x' }
      - run: flutter pub get
      - run: flutter test --coverage
      - run: flutter test --machine > report.json
```

## Flaky Tests Guardrails

- Never use `Future.delayed` for synchronization; use `tester.pump()` / `tester.pumpAndSettle()`.
- Use `FakeAsync` for time-dependent Dart code (from `package:fake_async`).
- Make test data unique with `DateTime.now().millisecondsSinceEpoch.toString()`.
- Avoid real network — use `MockClient` (from `package:http/testing.dart`).
- Reset `shared_preferences` and similar singletons between tests.

## Test Case Design Patterns

Apply these systematic patterns before writing test code to ensure robust coverage beyond the happy path.

### 1. Boundary Value Analysis
Test at the edges of valid input domains: empty, zero, maximum, null, and just-outside valid ranges.

```dart
// test/validator_test.dart
import 'package:test/test.dart';

void main() {
  group('validateInput', () {
    ['', ' ', 'a' * 10001].forEach((input) {
      test('rejects ${input.runtimeType}', () {
        expect(() => validateInput(input), throwsA(isA<ArgumentError>()));
      });
    });
  });
}
```

### 2. Negative / Error Case Testing
Verify the system behaves correctly under invalid or unexpected conditions.

```dart
// test/calculator_test.dart
void main() {
  test('throws on divide by zero', () {
    expect(() => divide(10, 0), throwsA(isA<Exception>()));
  });
}
```

### 3. State-Based Testing
For objects with internal state, verify transitions between states are correct and irreversible where expected.

```dart
// test/connection_test.dart
void main() {
  test('transitions through connection states', () {
    final conn = Connection();
    expect(conn.state, ConnectionState.closed);
    conn.open();
    expect(conn.state, ConnectionState.open);
    conn.close();
    expect(conn.state, ConnectionState.closed);
    // Idempotency
    conn.close();
    expect(conn.state, ConnectionState.closed);
  });
}
```

## Common Test Smells to Avoid

- **Assertion Roulette**: Many assertions without descriptive messages, making failure diagnosis ambiguous. *Fix: Use `expect(value, reason: 'description')` for each assertion.*
- **Happy Path Bias**: Only testing successful scenarios, leaving error paths uncovered. *Fix: Test `null` values, exceptions with `throwsA<Exception>()`, empty collections.*
- **Mock Overdose**: Too many mocks hiding integration issues or coupling tests to implementation. *Fix: Mock only at boundary interfaces (repositories, HTTP clients); prefer `mocktail` for simplicity.*
- **The Free Ride**: Tests that execute code but assert nothing meaningful. *Fix: Every test must have at least one specific, falsifiable assertion.*
- **Obscure Test**: Long widget tests with no clear setup/verify structure. *Fix: Follow AAA, use `pumpWidget()` in setUp, keep test cases focused on single behavior.*
- **Flaky Test**: Non-deterministic results from async, timers, or golden files. *Fix: Use `tester.pumpAndSettle()`, `FakeAsync`, avoid real time in widget tests.*

## Best Practices

### DO

- Follow the test pyramid: many unit, some widget, few integration tests
- Use `group()` for logical test organization
- Use `setUp()` / `tearDown()` for consistent test state
- Use `tester.pumpWidget()` for widget rendering
- Use `tester.pumpAndSettle()` to wait for animations
- Use `find.byKey()` (preferred) or `find.text()` for widget discovery
- Use `golden` file tests for visual regression (with `--update-goldens` in CI)

### DON'T

- Don't use `Future.delayed` for synchronization in tests
- Don't depend on real time or network in unit/widget tests
- Don't test private methods starting with `_`
- Don't use `await tester.pump()` after every widget change — use `pumpAndSettle()` when needed
- Don't hardcode golden file paths — use `matchesGoldenFile('goldens/...')`

### Common Pitfalls

- **Flaky widget tests** → Use `tester.pumpAndSettle()` instead of arbitrary `pump(Duration)` calls.
- **Mock generation** → Run `dart run build_runner build` after adding `@GenerateMocks`.
- **Async gaps** → Use `runAsync` for real async calls in widget tests.
- **Golden file bloat** → Keep goldens small; review golden changes in PR.
- **Over-mocking** → Prefer real implementations for pure Dart business logic.
- **Expired goldens** → Run `flutter test --update-goldens` when UI intentionally changes.
- **Slow integration tests** → Test critical paths only; keep unit/widget test coverage high.

## Optional: Property-Based Testing

```dart
import 'package:checks/checks.dart';

void main() {
  test('add is commutative', () {
    final add = Math.add<int>;
    check(add(2, 3)).equals(add(3, 2));
  });
}
```

## Alternatives

- **flutter_test**: built-in, always available for Flutter projects.
- **mocktail**: no code generation needed, works without build_runner.
- **patrol**: advanced integration + native automation for Flutter.