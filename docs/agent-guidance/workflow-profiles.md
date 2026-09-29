### Installation and Naming

- One `specify init` invocation selects exactly one workflow profile. A user may
  rerun init for the same integration to install the other profile additively;
  this is supported and must preserve both installed profile records.
- **Classic** generates the agent-native `sp-*` command or skill surfaces from
  `templates/commands/**`, `templates/command-partials/**`,
  `templates/command-references/**`, `templates/passive-skills/**`, and
  `templates/worker-prompts/**`. It is the explicit, broadly compatible prompt
  path and retains the full Classic workflow guidance.
- **Advanced** is supported by skills-based integrations and generates the
  independent `spx-*` catalog from `templates/advanced-skills/**`. It is
  command-equivalent and prompt-optimized for advanced models: every Classic
  command has an independent SPX counterpart, while `spx-map-rebuild` is an
  additional convenience orchestrator. The current topology is 29 SPX skills:
  28 one-to-one Classic command counterparts plus `spx-map-rebuild`. Advanced
  keeps command ownership, read/write boundaries, resumable stops, and
  external-side-effect gates; it removes repeated tutorials, fixed role chains,
  unnecessary mandatory delegation, long examples, and model-authored stable
  boilerplate.
- `sp-e2e` / `spx-e2e` is a scenario-first, platform-neutral test-analysis
  and execution lane. Client visual interaction is first-class; native runners
  are optional. Test Design stays read-only input and Review/Accept retain
  ownership. Only retained test-asset mutations use canonical `sp-e2e` closeout.
- Advanced prompt optimization has no hard word or token ceiling. Optimize
  expression, not workflow semantics: every Classic stage input, triggered
  output, state owner, resume transition, blocker/recovery rule, side-effect
  gate, and final-claim gate must remain in the owning SPX skill, a triggered
  Advanced reference, or shared deterministic runtime. Leave implementation
  strategy and judgment to the advanced model only after those contracts are
  preserved.
