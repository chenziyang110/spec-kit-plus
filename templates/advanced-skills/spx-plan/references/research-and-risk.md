# Research and risk gate

Research only an uncertainty capable of changing architecture, feasibility,
dependency choice, security, operations, or verification. State the decision it
will unlock and stop when evidence is sufficient for that decision.

Prefer live repository evidence and primary technical sources. Treat model
memory as provisional. A disposable spike is appropriate when documentation
cannot prove integration, performance, build, or runtime behavior; keep it out
of production code and record its inputs, commands, environment, output, and
what it established. Do not declare planning ready while a design-changing
research question is unresolved, contradicted, or supported only by an
irreproducible demo.

Require explicit treatment when triggered:

- data/schema migration and rollback;
- auth, secrets, destructive operations, or trust-boundary changes;
- public/API/protocol compatibility;
- generated or mirrored consumers;
- concurrency, caching, lifecycle, or failure recovery;
- UI fidelity or real-entrypoint verification;
- deployment, observability, and operational ownership.

For low-risk local work, omit empty research/risk sections rather than filling
templates with generic prose.
