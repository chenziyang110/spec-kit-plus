# Auto routing contract

Choose the first applicable trustworthy route:

- active durable team batch: `spx-implement-teams`;
- completed independent lane awaiting closeout: `spx-integrate`;
- active implementation lane or ready tracked feature work: `spx-implement`;
- active bounded quick workspace: `spx-quick`;
- active debug session or unknown failure mechanism/regression: `spx-debug`;
- active discussion not yet handoff-ready: `spx-discussion`;
- confirmed ready discussion handoff awaiting consumption: `spx-specify`;
- active PRD reconstruction scan or evidence gap: `spx-prd-scan`;
- reconstruction-ready PRD scan awaiting exports: `spx-prd-build`;
- cognition baseline explicitly requires rebuild: `spx-map-rebuild`;
- scan-ready cognition workbench awaiting publication: `spx-map-build`;
- active or required cognition scan without scan readiness: `spx-map-scan`;
- interrupted or externally changed existing map with no higher active owner:
  `spx-map-update`;
- existing feature has planning-blocking ambiguity or contradictory acceptance:
  `spx-clarify`;
- new feature intent or acceptance is missing or not planning-ready:
  `spx-specify`;
- planning-ready spec has unresolved implementation-chain feasibility:
  `spx-deep-research`;
- planning-ready spec lacks a coherent technical design: `spx-plan`;
- ready plan lacks an executable task graph: `spx-tasks`;
- persisted consistency gate is required or stale: `spx-analyze`;
- ready tasks remain and prerequisites agree: `spx-implement`;
- new request is truly trivial and passes the fast gate: `spx-fast`;
- new bounded non-trivial request needs lightweight state: `spx-quick`;
- workflow-artifact explanation: `spx-explain`;
- other read-only project question: `spx-ask`.

Do not route from a filename alone. Confirm the relevant state contract,
artifact readiness, live diff, and blocker. If a terminal marker conflicts with
missing verification or repository changes, resume the owning workflow rather
than declaring completion.
