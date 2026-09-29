## Workflow Profile Contract: Classic vs Advanced

- `classic` and `advanced` are separate prompt products over shared runtime
  contracts. One `specify init` invocation selects one profile; additive
  installation must preserve both profiles, manifests, and user-modified files.
- Classic owns `sp-*` and its passive bundle. Advanced owns `spx-*` and does
  **not** install the Classic passive-skill prompt bundle. The current topology
  is 28 SPX skills: 27 one-to-one Classic command counterparts plus
  `spx-map-rebuild`.
- Advanced intentionally also installs Classic `sp-map-scan`, `sp-map-build`,
  and `sp-map-update` through the unchanged Classic renderer for lower-cost
  models. Keep them byte-equivalent to Classic generation and assess the
  corresponding `spx-map-*` contracts when changing them.
- Advanced prompt optimization has no hard word or token ceiling. Optimize
  expression without dropping inputs, outputs, ownership, resume transitions,
  recovery, side-effect gates, or final-claim gates. Do not weaken Classic to
  optimize Advanced or paste the full Classic prompt into SPX.
