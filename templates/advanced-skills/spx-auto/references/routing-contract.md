# Auto routing contract

For every feature candidate, first run `specify-runtime workflow show`, then `specify-runtime workflow next`.
`FEATURE_DIR/workflow.json` is the primary required-stage phase lock.
Consume its structured `next_argv`: `specify-runtime workflow complete-stage` routes to the
current stage owner, while `specify-runtime workflow transition --to <stage>` routes to that
destination and is passed through exactly. Never reconstruct runtime flags from
prose or infer a successor from Markdown. Active `accept` returning
`specify-runtime workflow closeout` routes to the current accept owner; only completed `accept`
has no successor. `workflow-state.md` remains rich resume/evidence context,
queried only through `specify-runtime artifact show` and mutated only through
leased `specify-runtime artifact patch`; it may add an auxiliary gate but cannot
skip or reverse the runtime stage. Legacy `next_command`/`active_command`
heuristics are fallback only for noncanonical auxiliary state when no runtime
file exists.

A blocked runtime intentionally has no `next_argv`. Preserve its tutorial and
wait for the declared evidence; when available, fill only the required evidence
input in `data.resolution_action` and execute its runtime-owned base argv.
`show_argv` refreshes state but does not resolve it.

When rich state contains evidence that an upstream required stage is invalid,
do not infer a reverse route from its prose alone. Use `specify-runtime workflow reopen` with
the current revision, compact reason, sanitized evidence, and complete
invalidated-artifact set when the record is sufficient. Resume an already active
mapped owner; reactivate the same completed owner through reopen. Otherwise
route to analyze or the current owner to establish a valid reopen decision. A
blocked runtime must first use `specify-runtime workflow resolve` with evidence, and acceptance
findings use `accept route-repair`.

When a managed Run declares a feature subject, verify the current directory is
`SPECIFY_RUN_WORKSPACE` and route only state belonging to that subject. A
recorded upstream gate outranks an implementation tracker or later artifact.
For an unbound read-only invocation, stop on conflicting states or anything
other than exactly one unique safe candidate; report the evidence and smallest
repair instead of guessing.

Discover candidates only through the managed Run subject, `discussion list`,
`quick list`, and bounded `artifact list` queries
for feature, debug, Review, and Acceptance types. Query a selected record with
`workflow show|next` or targeted `artifact show`. Never enumerate or parse the
underlying `.specify/**` or `.planning/**` state directories directly.

Candidate priority applies only within one resolved workflow lineage. A topical
continuation of an already-invoked incomplete discussion is selected before
unrelated feature, Quick, Debug, or task candidates are considered, and stays
in `spx-discussion` until its handoff is ready. A ready discussion can continue
only through its explicitly selected `spx-quick` or `spx-specify` consumer,
never directly through `spx-implement`. A name, slug, title, topic, or keyword
similarity is not binding evidence between workflow roots; require runtime lane
selection or the consumer's durable `source_contract` and `review_digest`. When
feature context is absent, do not enumerate `.specify/features/**`, `tasks.md`,
or `task-index.json` to guess a feature directory. An unconsumed discussion and
an unrelated feature are competing candidates, not priority-ranked stages.

Choose the first applicable trustworthy route:

- new/high-visibility UI direction, redesign, or UI work blocked by missing or
  bootstrap `DESIGN.md`: `spx-design`;
- active durable team batch: `spx-implement-teams`;
- trusted completed system Review whose fresh `human-acceptance.json` is not
  `accepted`: `spx-accept`;
- active Review, or trusted completed implementation whose Review is missing,
  stale, blocked, repairing, or not approved: `spx-review`;
- active implementation lane or ready tracked feature work: `spx-implement`;
- active quick direct-delivery workspace: `spx-quick`;
- active debug session or unknown failure mechanism/regression: `spx-debug`;
- active discussion not yet handoff-ready: `spx-discussion`;
- confirmed ready discussion handoff awaiting its explicitly selected consumer:
  `spx-quick` for direct delivery or `spx-specify` for a formal spec-first path;
- active PRD reconstruction scan or evidence gap: `spx-prd-scan`;
- reconstruction-ready PRD scan awaiting exports: `spx-prd-build`;
- cognition baseline explicitly requires rebuild: `spx-map-rebuild`;
- scan-ready cognition workbench awaiting publication: `spx-map-build`;
- active or required cognition scan without scan readiness: `spx-map-scan`;
- interrupted or externally changed existing map with no higher active owner:
  `spx-map-update`;
- existing feature has planning-blocking ambiguity or contradictory acceptance:
  `spx-clarify`;
- new feature request explicitly asks for a formal specification before
  implementation: `spx-specify`;
- planning-ready spec has unresolved implementation-chain feasibility:
  `spx-deep-research`;
- planning-ready spec lacks a coherent technical design: `spx-plan`;
- ready plan lacks an executable task graph: `spx-tasks`;
- persisted consistency gate is required or stale: `spx-analyze`;
- ready tasks remain and prerequisites agree: `spx-implement`;
- new request is truly trivial and passes the fast gate: `spx-fast`;
- new non-trivial direct-delivery request needs resumable state, regardless of
  size or capability count: `spx-quick`;
- workflow-artifact explanation: `spx-explain`;
- other read-only project question: `spx-ask`.

Do not route from a filename alone. Confirm the relevant state contract,
artifact readiness, live diff, and blocker. If a terminal marker conflicts with
missing verification or repository changes, resume the owning workflow rather
than declaring completion.
