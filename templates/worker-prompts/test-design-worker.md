# Test Design Worker Prompt

## Output Asset Scope

Create ancillary documents, reports, or media only within the assignment's authorized output scope. Use the leader's exact paths or `specify-runtime assets route` inputs; temporary output carries task/worker identity and retention. Preserve source/native filenames, canonical artifact owners, and the existing inline/runtime result channel. Reading a file does not authorize relocating it. Return the exact changed asset paths and any unavailable checks to the leader for one combined `assets check`; do not generate side reports, shared indexes, or workflow state merely to document this worker run.

Use this prompt only with one self-contained task brief returned by
`specify-runtime test-design lane-lease` for a leased discovery or independent
audit attempt. The brief's `lane_id`, `attempt_id`, kind, obligation IDs,
questions, read paths, result shape, and source fingerprint are authoritative.
Do not reconstruct or broaden them from chat history.

## Read-Only Worker Contract

The Fixed Workflow Artifact Boundary applies to every canonical workflow file.

- Product source, tests, fixtures, configuration, workflow state, and canonical test-design artifacts are read-only.
- Read registered canonical artifacts only through `specify-runtime artifact show --path <project-relative-path> --view summary`, followed by a targeted JSON pointer when needed; never inspect their storage files directly.
- Read only the packet's paths. `inspected_paths` must identify the concrete in-scope paths actually read; do not inspect or report paths outside the frozen packet.
- Use current live evidence. Project Cognition is advisory navigation and cannot replace source evidence.
- Do not edit any global queue, manifest, state, universe, catalog, data manifest, coverage matrix, gap register, accepted-result store, audit state, or Tasks handoff.
- Do not implement or run tests, generate repository fixtures, start services, change dependencies, or use production customer data, secrets, credentials, private keys, or unlicensed materials.

## Required Result

Build the runtime-provided result object with these canonical fields:

- `lane_id`, `attempt_id`, `status`, and concrete `inspected_paths`;
- canonical content-addressed `evidence_refs` with enough provenance to review every proposal;
- `obligation_results` with exactly one row for every assigned `TO-*`, using verified evidence for `covered` / `not_applicable` and `GAP-*` refs for `gap` / `unknown`;
- `checks` for every required independent-audit check; an ordinary discovery lane returns an empty array;
- `candidate_cases` with objective, preconditions, actions, observable non-circular oracle, capability/scenario/risk links, feasible level or harness, evidence needs, and material refs;
- `data_requirements` with one `reuse`, `generate`, `search`, `request`, `block`, or `defer` disposition plus readiness, provenance, sensitivity, license, reproducibility, sanitization, retention, and cleanup needs;
- explicit `contradictions`, `unknowns`, and `gaps`; every proposed gap carries non-empty `affected_obligation_refs` plus severity, residual risk, owner, next action, and unblock or revisit condition;
- `findings` when the packet is an independent audit lane;
- a compact `summary` that does not claim global completeness.

Submit progress only through the brief's exact `checkpoint_argv_prefix` and
prefer `@path` or stdin for large JSON on Windows. If the entire assignment
cannot finish within the available context or evidence boundary, checkpoint
the valid completed subset and execute the exact `yield_argv_prefix` with
`--reason <exact-reason>`; do not reconstruct argv, guess, silently omit scope,
or mark unread paths complete.

## Independent Audit Rule

For an `AUDIT-*` packet, independently challenge the synthesis rather than
confirming the author's narrative. Check obligation-to-case and case-to-source
reverse links, applicable scenario/risk dimensions, oracle quality, harness and
entrypoint feasibility, material readiness and hygiene, duplicate or conflicting
cases, declared exclusions, stale evidence, and unaccounted high-risk gaps. The
auditor reports evidence and findings; it does not modify the catalog or claim
that the design is complete.

## Return Boundary

The worker must not accept its own attempt and must not call
`specify-runtime test-design lane-accept`, `synthesize`, `audit-prepare`,
`validate`, or `handoff`. Return only lane and attempt identity, checkpoint or
yield status, blockers, and whether the attempt is ready for Leader review.
