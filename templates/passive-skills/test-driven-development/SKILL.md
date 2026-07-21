---
description: "Use for test-first feature, bugfix, or refactoring work. During sp-implement feature batching, defer execution to its workflow-owned validation epochs instead of rerunning tests per task."
---

# Test-Driven Development (Spec Kit Plus)

Write the test first. Watch it fail. Write minimal code to pass.

## Workflow-Owned Validation

When `sp-implement` declares `feature_epochs`, the change-set remains test-first
but the Leader owns execution. Workers may author mapped tests before production
edits, then stop for the combined RED/baseline epoch; implementation workers use
the accepted epoch ref and run only cheap task checks. They return test impact so
the Leader can run one convergence epoch after integration.

The validation epoch budget is shared across Implement and Review. This passive
skill must not start an extra validation epoch for a Txx, join, resume, commit, or
completion claim. Reuse current fingerprint-bound ledger evidence; never reset
or bypass the owning workflow's maximum.

## Integration with sp-* Workflows

- **`sp-implement`**: Group related formal tasks into a coherent change-set.
  Author/select mapped tests before production edits and let the Leader execute
  one combined RED/baseline epoch. Do not require every worker to rerun RED and
  GREEN per task.
- **`sp-debug`**: When diagnosing or fixing a bug, your FIRST step must be to write a failing test that explicitly reproduces the bug. Do not change production code until you have empirically confirmed the failure state.
- **`sp-fast` / `sp-quick`**: Even for small, bounded fixes, write a test first to verify the fix and prevent regressions.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write a change-set before its test contract? Stop and repair the ordering before
continuing.
Violating the letter of the rules is violating the spirit of the rules.

## Red-Green-Refactor

1. **RED**: Write a minimal failing test showing what should happen. In an active
   feature-epoch workflow, the Leader verifies the combined RED state once.
2. **GREEN**: Write the simplest, most minimal production code to pass the test.
   In that workflow, the Leader verifies the integrated change-set once.
3. **REFACTOR**: Clean up duplication and improve structure while keeping the tests green. Do not add new behavior during refactoring.

## Red Flags - STOP and Start Over

- Writing production code before the test.
- "I already manually tested it."
- "The fix is too simple to need a test."
- "I'll add the tests after I get it working."
- Modifying production code in `sp-debug` before reproducing the issue in a test.

If you encounter these red flags, stop, discard the unverified code, and start over with a failing test.
