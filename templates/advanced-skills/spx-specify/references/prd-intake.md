# PRD intake lane

Use this only when the user supplies an existing PRD or asks to discover and
compile product requirements from source documents or a repository-first
product. Keep source material read-only and record concrete source references
for material requirements.

Extract outcomes, actors, scope, constraints, acceptance, dependencies, and
open decisions; separate explicit source claims from inference. Reconcile
duplicates and contradictions instead of concatenating prose. Ask only about
conflicts that change the product contract.

Choose the output by intent:

- When a supplied PRD is input to one feature, compile the accepted result into
  the canonical spec contract and compact spec view used by ordinary
  `spx-specify`.
- When the user requests current-state repository reconstruction, create a
  durable `.specify/prd-runs/<run-id>/` package. Preserve scan/build separation:
  the build pass consumes accepted scan artifacts and must not reread the
  repository.

For repository-scale reconstruction, let project cognition define bounded
evidence routes. Prefer lower-cost capable workers for disjoint source/UI/API/
test lanes; the advanced leader owns boundary, contradiction resolution, and
acceptance rather than bulk reading. Each lane returns concrete source refs,
observed behavior, confidence, gaps, and product implications. Compile only
accepted lane results and do not reread the repository during the build pass.

The reconstruction package must retain the classic product surface, using the
installed deterministic templates under `.specify/templates/prd/`:

- `workflow-state.md`, `master/master-pack.md`, and the accepted scan package;
- machine-readable capability, UI, service, flow, data, integration, runtime,
  configuration, protocol, state-machine, error, verification, risk, and
  reconstruction indexes, including `config-contracts.json`;
- `exports/README.md` as navigation entry and `exports/prd.md` as the primary
  reader-facing PRD;
- the supporting UI, service, flows/IA, data-rules, integration, runtime,
  `config-contracts.md`, protocol, state-machine, error-semantics,
  verification-surface, reconstruction-risk, and internal-brief exports when
  their source evidence exists.

Critical reconstruction claims target L4 evidence: a future implementer can
identify the owner, consumer, behavior, state/edge cases, configuration or
protocol rules, and a real verification route without reopening a broad scan.
Keep unknowns explicit. PRD reconstruction is a peer output workflow and does
not automatically continue to `spx-plan`.
