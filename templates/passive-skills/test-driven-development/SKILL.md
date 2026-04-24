---
description: "Use when implementing any feature, bugfix, or refactoring (especially within sp-implement, sp-debug, sp-fast, or sp-quick). Enforces writing failing tests before production code."
---

# Test-Driven Development (Spec Kit Plus)

Write the test first. Watch it fail. Write minimal code to pass.

## Integration with sp-* Workflows

- **`sp-implement`**: When executing a formal task, your FIRST implementation step must be to write the failing test that proves the task is incomplete or the feature is missing. Only then should you write the code to make it pass.
- **`sp-debug`**: When diagnosing or fixing a bug, your FIRST step must be to write a failing test that explicitly reproduces the bug. Do not change production code until you have empirically confirmed the failure state.
- **`sp-fast` / `sp-quick`**: Even for small, bounded fixes, write a test first to verify the fix and prevent regressions.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.
Violating the letter of the rules is violating the spirit of the rules.

## Red-Green-Refactor

1. **RED**: Write a minimal failing test showing what should happen. Verify that it fails for the correct reason.
2. **GREEN**: Write the simplest, most minimal production code to pass the test. Verify that all tests pass.
3. **REFACTOR**: Clean up duplication and improve structure while keeping the tests green. Do not add new behavior during refactoring.

## Red Flags - STOP and Start Over

- Writing production code before the test.
- "I already manually tested it."
- "The fix is too simple to need a test."
- "I'll add the tests after I get it working."
- Modifying production code in `sp-debug` before reproducing the issue in a test.

If you encounter these red flags, stop, discard the unverified code, and start over with a failing test.
