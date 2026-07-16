# Analysis gate

Treat artifacts as a chain of obligations rather than a prose comparison:

- specification: observable outcomes, acceptance, constraints, exclusions;
- plan: owners, interfaces, state/error behavior, compatibility, verification;
- tasks: complete coverage, dependency order, isolated writes, join evidence;
- live repository: current owners, consumers, generated surfaces, and test entry
  points.

Use `CRITICAL` for violated project principles or missing baseline truth,
`HIGH` for contradictions, uncovered requirements, unsafe boundaries, or lost
must-preserve behavior, and lower severities for local clarity or maintainability
gaps. A blocking finding must name the highest invalid stage and all downstream
artifacts that become stale.

Keep prior finding IDs when the same evidence and obligation recur. Mark a
finding resolved only from fresh artifact and repository evidence. The visible
report may stay short, but every blocker must appear in the durable gate state.
Do not confuse missing prose with missing behavior coverage, or artifact claims
with proof that the implementation already satisfies them.

Persist a complete blocker bundle in `workflow-state.md`: `gate_status: cleared
| blocked`, incremented `gate_cycle`, `highest_invalid_stage`, `blocker_bundle`,
finding attribution, evidence fingerprint, and exactly one next route. Preserve
IDs across revalidation and clear the gate only after fresh evidence resolves
every blocking row.
