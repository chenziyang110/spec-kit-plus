# Runtime Context Compiler

## Goal

Reduce agent context loading by compiling a task-specific context packet instead of requiring every workflow to read the complete knowledge surface.

## Design principle

The model should reason about product intent and implementation choices.
The runtime should own deterministic context assembly:

- workflow state
- permissions
- active task contract
- acceptance requirements
- relevant references
- execution boundaries

## Input

A compiler request contains:

```json
{
  "task_id": "...",
  "workflow": "quick",
  "intent": "...",
  "changed_scope": [],
  "risk": "low|medium|high"
}
```

## Output

The compiler emits a bounded context packet:

```json
{
  "goal": "",
  "constraints": [],
  "required_skills": [],
  "relevant_artifacts": [],
  "acceptance": [],
  "forbidden_actions": [],
  "runtime_state_ref": ""
}
```

## Rules

- The packet is a derived view, not a new source of truth.
- Permissions come from runtime state, never from generated context.
- Missing evidence stays missing.
- Context reduction cannot remove security, ownership, or acceptance checks.
- Full state inspection remains available for reconciliation.

## Migration path

1. Introduce packet schema.
2. Add runtime compiler command.
3. Migrate Quick first.
4. Measure context reduction.
5. Expand to other workflows.
