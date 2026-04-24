---
description: "Use when facing multiple independent test failures, bugs, or tasks that can be worked on without shared state. Guides parallelization into the sp-* CLI workflows."
---

# Parallel Execution (Spec Kit Plus)

When you have multiple unrelated failures (e.g., different test files, different subsystems, distinct bugs), investigating them sequentially in a single session wastes time and context.

In Spec Kit Plus, we handle parallel independent domains by scoping our `sp-*` workflows tightly, rather than relying on ad-hoc internal subagents.

## When to Use

- 3+ test files failing with different root causes.
- Multiple subsystems broken independently.
- Each problem can be understood and fixed without context from the others.

## Integration with sp-* Workflows

Instead of a single unstructured AI session trying to fix everything at once:

1. **Identify Independent Domains**: Group the failures or tasks by subsystem. Ensure there is no shared state or overlapping files.
2. **Parallel CLI Invocation**: Advise the user to run multiple parallel instances of the appropriate `sp-*` workflow in separate terminal windows.
   - Example for bugs: Run `specify sp-debug --issue="Fix subsystem A"` in one terminal, and `specify sp-debug --issue="Fix subsystem B"` in another.
   - Example for tasks: Run `specify sp-implement` for independent tasks in separate branches/terminals if supported by the project conventions.
3. **Scope Guarding**: If you are currently inside an `sp-quick` or `sp-debug` session, explicitly refuse to fix out-of-scope independent issues. Instruct the user to open a new `sp-*` session for the unrelated issues.

## Behavioral Rules

- **Do NOT** try to fix multiple independent systems in one `sp-quick` or `sp-debug` run. Scope each run to a single domain.
- **Do NOT** dispatch agents that will modify the same shared state or files concurrently.
- If the failures are related (fixing one might fix the others), keep them in a single sequential `sp-debug` session.

## Red Flags

- "Fix all the failing tests" (Too broad; requires splitting).
- Fixing unrelated bugs in a single `sp-fast` command.
