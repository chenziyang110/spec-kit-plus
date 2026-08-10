# Test Design Worker Contract

Workers perform bounded, read-only discovery or independent audit. The Leader
retains scope, canonical artifact mutation, lane acceptance, synthesis,
validation, and handoff authority.

Every substantive discovery packet must be executed by a non-Leader worker.
The Leader must not perform discovery serially as a substitute. If no worker is
available, keep the lane pending or yield the active attempt with its auditable
reason, report the blocked stop, and resume at that lane when a worker becomes
available.

## Discovery packet

A discovery packet must include:

- `lane_id`, `attempt_id`, mode, scope root, and frozen source fingerprint;
- assigned obligation IDs, risk dimensions, and exact questions;
- allowed `read_paths` and authoritative source refs;
- required evidence and inspected-path reporting;
- the result schema and stop conditions.

Inspect only packet paths. Do not change source, tests, fixtures, configuration,
canonical test-design artifacts, lane state, or any other repository file. Do
not expand scope, follow an out-of-packet path, or turn an assumption into a
fact. If a needed read is outside the packet, return it as an unknown or gap so
the Leader can re-scope explicitly.

Checkpoint one compact result with these keys:

```json
{
  "lane_id": "LANE-001",
  "attempt_id": "ATTEMPT-001",
  "status": "success|partial|blocked|failed",
  "inspected_paths": [],
  "evidence_refs": [],
  "obligation_results": [],
  "checks": [],
  "candidate_cases": [],
  "data_requirements": [],
  "contradictions": [],
  "unknowns": [],
  "gaps": [],
  "summary": "bounded conclusion"
}
```

Submit it with the lease response's exact `checkpoint_argv_prefix`, which binds
the root, current expected revision, lane, and attempt. Do not reconstruct that
argv from memory or reuse it after another mutation.

Candidate cases state the covered obligation, discriminating scenario,
priority, stage, preconditions, procedure or observation, oracle, evidence
requirement, and material needs. Data requirements propose a `TD-*` kind and
one disposition (`reuse`, `generate`, `search`, `request`, `block`, or `defer`)
with provenance, recipe, request, hygiene, or unblock details as applicable.
`obligation_results` contains exactly one row for every assigned `TO-*`;
`covered` and `not_applicable` cite verified evidence records, while `gap` and
`unknown` cite `GAP-*` rows. Discovery returns empty `checks`; an audit returns
every runtime-required check with status, evidence, affected obligations,
finding refs, and summary.
Separate observed evidence from inference. A worker may return evidence
candidates and provenance, but must never call `evidence register` or `evidence
import`; only the Leader accepts evidence into the content-addressed store.

Execute the lease response's exact `checkpoint_argv_prefix` for a complete or
explicitly partial packet result. Execute its exact `yield_argv_prefix` with
`--reason <reason>` when interrupted, blocked before a useful checkpoint, or
unable to continue safely; never reconstruct either argv. The reason must be
non-empty and sanitized because the runtime persists it in yield history. A worker must not
accept its own result and must never call `lane-accept`, `synthesize`,
`validate`, or `handoff`.

## Independent audit packet

The audit packet uses an `AUDIT-*` lane and includes the frozen denominator,
canonical artifact refs, accepted discovery result refs, and explicit review
questions. It must be assigned after synthesis to a worker that did not author
the package and is distinct from the Leader and every accepted discovery
worker. An independent auditor is always required; if none is available, keep
the audit lane pending or yielded and stop blocked rather than self-auditing.

The auditor checks:

- forward and reverse requirement/capability/scenario/case/data coverage;
- omitted applicable risk dimensions, states, boundaries, permissions,
  failures, recovery, concurrency, compatibility, and operational behavior;
- weak, circular, nondeterministic, or unobservable oracles;
- duplicate cases, infeasible stage or harness assumptions, and evidence that
  cannot be obtained at the named entrypoint;
- UI accessibility, responsive, viewport/state, motion, and visual-comparison
  obligations when applicable;
- unsafe, unavailable, unprovenanced, or incorrectly classified materials;
- exclusions or waivers that hide an in-scope obligation.

Return the normal lane result plus `findings`. Every finding cites affected
refs, severity, evidence, residual risk, recommended disposition, next action,
and observable resolution criteria. An empty finding list means only that this
audit found no omission against the supplied frozen denominator; it is not an
unbounded completeness claim. The Leader independently reviews and accepts or
rejects the audit result.
