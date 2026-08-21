# Analysis gate

Treat artifacts as a chain of obligations rather than a prose comparison:

- specification: observable outcomes, acceptance, constraints, exclusions;
- plan: owners, interfaces, state/error behavior, compatibility, verification;
- tasks: complete coverage, dependency order, isolated writes, join evidence;
- live repository: current owners, consumers, generated surfaces, and test entry
  points.

When UI applies, the obligation chain also includes exact
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, component interaction/data rows, and
responsive stretch/overflow rows. A downstream `required_states`-only shape or
a populated pointer-happy-path-only plan/task set is a continuity defect, not a
harmless summarization.

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

The selected repair route must also name the required-stage runtime target and
every artifact made stale. Specify and deep-research invalidate `specify`; plan
invalidates `plan`; task decomposition invalidates `tasks`. Use the CLI reopen
operation only after the full finding set is known so one deterministic backward
transition covers the complete invalidation scope.

Patch the complete blocker bundle into `workflow-state.md` through a leased `specify-runtime artifact patch`: `gate_status: cleared
| blocked`, incremented `gate_cycle`, `highest_invalid_stage`, `blocker_bundle`,
finding attribution, evidence fingerprint, and exactly one next route. Preserve
IDs across revalidation and clear the gate only after fresh evidence resolves
every blocking row.

## Professional UI contract continuity

For UI-bearing scope, Analyze checks exact continuity, contradictions,
ownership, and task coverage across `surface_catalog`, `scenario_matrix`,
`interaction_matrix`, `editing_matrix`, `data_state_matrix`, `accessibility_matrix`,
`navigation_matrix`, `content_matrix`, `motion_contract`, and
`usability_validation`, including component governance.
Prioritize risk-based gaps rather than an unbounded Cartesian product; stay
read-only and never reinterpret required target-user review.
