## Gate Self-Check

At each phase boundary, output an explicit confirmation. This replaces pure declaration with verifiable checkpoints.

### Format

```
[GATE CHECK] Phase: <phase_name>
- Forbidden actions in this phase: <list>
- I confirm I have NOT performed any forbidden action since the last gate.
- Files modified in this phase: <list or "none">
```

### When to emit

- On phase transition (e.g., analysis → specification, specification → handoff)
- Before final reporting
- After any recovery from a false start or route change

### Enforcement

This is a Level 2 enforcement (gate self-check). It does not prevent tool use, but it creates an auditable record. If a gate check cannot be honestly emitted, the phase is not complete.
