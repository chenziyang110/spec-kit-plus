# Auto routing contract

Choose the first applicable trustworthy route:

- active implementation lane or ready tracked feature work: `spx-implement`;
- active bounded quick workspace: `spx-quick`;
- active debug session or unknown failure mechanism/regression: `spx-debug`;
- recoverable discussion handoff or discussion state awaiting specification:
  `spx-specify`;
- cognition baseline explicitly requires rebuild: `spx-map-rebuild`;
- interrupted or externally changed existing map with no higher active owner:
  `spx-map-update`;
- feature intent or acceptance is missing, contradictory, or not planning-ready:
  `spx-specify`;
- planning-ready spec lacks a coherent design or executable tasks: `spx-plan`;
- ready tasks remain and prerequisites agree: `spx-implement`;
- new request is truly trivial and passes the fast gate: `spx-fast`;
- new bounded non-trivial request needs lightweight state: `spx-quick`;
- read-only question: `spx-ask`.

Do not route from a filename alone. Confirm the relevant state contract,
artifact readiness, live diff, and blocker. If a terminal marker conflicts with
missing verification or repository changes, resume the owning workflow rather
than declaring completion.
