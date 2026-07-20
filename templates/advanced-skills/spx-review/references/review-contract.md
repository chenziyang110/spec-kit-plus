# System Review contract

## Readiness and owned state

Review starts only after implementation closeout has produced a trusted
`implementation-handoff.json` and the CLI runtime permits the `implement` to
`review` transition. The handoff identifies the implementation fingerprint,
official entrypoints, and required system Review scenarios. Reject a missing,
ambiguous, or stale handoff; do not infer completion from task checkboxes.

`review prepare` compiles or freshness-checks the resumable
`review-state.json`. The installed template/schema and runtime are authoritative
for stable fields. Review owns that state, `review-evidence/**`, Review result
records, bounded source/test repairs, and Review-owned rich workflow-state
fields. It must not silently rewrite specification, plan, tasks, task lifecycle
acceptance, or CLI-owned `workflow-runtime.json`.

On resume, validate the persisted source revision, handoff digest, current
implementation/configuration fingerprint, scenario cursor, finding status, and
evidence paths before reusing any result. If the handoff changed, a Review
repair changed covered source, or another actor changed the product after
validation, mark prior approval stale and rerun every affected scenario. The
final reviewed fingerprint covers the integrated source/configuration snapshot
after all Review repairs; it is the input trust boundary for human acceptance.
Use `{{specify-subcmd:review resume-audit --feature-dir <feature-dir> --format json}}`
to recover the exact cursor and freshness gaps; do not infer them from prose.

## Mandatory scenario matrix

The leader compiles the Review Universe from authoritative acceptance and
design/architecture obligations, handoff scenarios, changed consumer surfaces,
runtime-discovered controls/registrations, and affected shared paths. Use
independent coverage discovery before reading the supplied matrix when
practical, then reconcile the two views. The deterministic scenarios from the
handoff are the minimum, never a reason to ignore an observable gap discovered
at the real entrypoint. Cover:

- installation/build/startup through each official entrypoint and its ready or
  health signal;
- required user journeys, navigation, routes, commands, and state transitions;
- every relevant button, link, menu, form, shortcut, or CLI action and its
  observable result;
- UI/command to handler/controller, service/provider, persistence or external
  dependency, and feedback wiring where applicable;
- registration and consumption of routes, handlers, providers, factories,
  adapters, jobs, commands, generated clients, and configuration;
- persistence/reload plus relevant empty, error, permission, and unavailable
  states;
- blocking browser console, network, process, application-log, and runtime
  diagnostics;
- affected shared-surface regression and the integrated final journey.

For UI scenarios, evidence uses only canonical kinds
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, with
`evidence_scope: integrated`, plus visual comparison or explicit human review.
Use stable real content and the required viewport/state matrix. Isolated task
evidence may guide Review but cannot close a system scenario.

Coverage closes only at zero uncovered obligations and surfaces after all
packets joined. A worker cannot declare coverage complete; the leader owns the
universe, dispositions, joins, and final coverage verdict.

## Findings and repair routing

Record a finding with its scenario, classification, severity/blocking status,
expected and observed results, sanitized evidence, suspected ownership, and
revalidation scope. Never convert a failed observation into a pass by weakening
the expectation.

- Every approved-scope defect remains in Review regardless of repair size.
  Missing code, a task omission, incomplete tests, broken wiring, and
  registration/configuration defects are not upstream truth gaps; decompose
  them into bounded Fix packets and add regression protection.
- An unknown root cause or intermittent mechanism remains in Review. Preserve
  the failed scenario, dispatch a read-only diagnostic packet, and let the
  leader accept the diagnosis before compiling the Fix wave. Review remains the
  stage owner throughout diagnosis, repair, and revalidation.
- Only a proven upstream truth gap is a handoff-and-stop boundary: missing or
  contradictory requirement truth routes to `$spx-specify`; missing or
  contradictory design truth routes to `$spx-design`; architecture truth that
  must change before any conforming fix routes to `$spx-plan`.
- Human-only system, account, device, protected CI, or visual judgment: retain a
  blocked Review with the full Human Action Guide and exact resume point.

For a proven truth gap, use the runtime-provided reopen argv when present.
Otherwise use `workflow reopen` with current revision, compact reason,
sanitized evidence, and the complete invalidated-artifact set. The upstream
workflow never declares Review passed; return to the reopened Review owner for
scenario revalidation.

## Revalidation and approval

After the audit join, use a separate Fix wave for accepted findings. After each
repair, run an independent revalidation wave over the exact failed step, its
complete user journey, every scenario sharing the changed dependency, and the
smallest credible regression set. A repair author must not verify its own
finding; use the leader or a different read-only subagent. Recapture stale
UI/runtime evidence. After all findings appear resolved, restart from a clean
supported state and run the final integrated matrix.

`review validate` may approve only when:

- the Review Universe has zero uncovered obligations/surfaces and all packets joined;
- every required scenario is `pass`;
- no blocking finding remains open or merely asserted resolved;
- required evidence exists, is integrated, and matches the current snapshot;
- startup/readiness and material runtime diagnostics pass;
- each repair has fresh revalidation evidence;
- the final source fingerprint is current.

After the final integrated validation, copy the deterministic
`current_fingerprint` into `final.reviewed_snapshot_sha256`, then set
`status: approved`. Do not approve from an earlier digest.

`review closeout` prepares or refreshes the final implementation summary and
human-acceptance handoff, but it does not transition phase state itself. Execute
only its returned revision-bound completion argv. The separately invoked
`$spx-accept` claims the next stage and owns the human verdict.
