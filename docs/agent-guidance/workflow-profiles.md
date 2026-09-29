# Workflow Profiles

Read before changing workflow profiles, installation membership, invocation,
shared workflow contracts, or their tests. These are source-repository product
maintenance requirements, not an instruction to run a generated workflow.
Code paths below are relative to the repository root.

For UI-bearing changes, also read [UI Workflows](ui-workflows.md).

## Workflow Profile Contract: Classic vs Advanced

`classic` and `advanced` are separate prompt products over shared Specify
runtime contracts. Treat the selected profile as an explicit maintenance
boundary; do not infer it from whichever generated directory happens to be
present in a test project.

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
- Classic and Advanced share one blocked-exit semantic contract. Every blocked
  stop must identify workflow/stage, category, owner, exact cause, sanitized
  evidence, attempted recovery, affected scope, next action, observable unblock
  criteria, and exact resume point. Keep agent-capable repair agent-owned. When
  a genuine human boundary exists, provide a self-contained tutorial with
  prerequisites, safety warnings, numbered UI/command steps, expected result
  and failure branch per step, independent verification, sanitized evidence to
  return, and the exact resume action. Protected CI and pending visual review
  must name their concrete repository/branch/commit/job or real-entrypoint/
  viewport/state/reference targets; “run CI” or “ask a human” is insufficient.
- Advanced does **not** install the Classic passive-skill prompt bundle.
  Essential safety and execution gates belong in the owning SPX skill, a
  profile-local Advanced reference, or shared deterministic runtime.
- `sp-test-design` / `spx-test-design` is an optional planning-only lane after
  Plan and before Tasks, or an independent project-baseline lane. It owns a
  frozen test universe, professional case/data/gap package, bounded read-only
  leader/subagent discovery, independent audit, and pointer-only Tasks handoff;
  it never claims absolute completeness or implements executable test assets.
- **Intentional map exception:** every Advanced install also generates the
  original Classic `sp-map-scan`, `sp-map-build`, and `sp-map-update` skills,
  including their Classic command-reference sidecars, through the unchanged
  Classic renderer. These coexist with `spx-map-scan`, `spx-map-build`,
  `spx-map-update`, and `spx-map-rebuild` so lower-cost models can run the
  explicit Classic map workflow. Do not treat these three `sp-*` directories as
  accidental profile leakage, and do not copy their prompts into
  `templates/advanced-skills/**`.
- Use `spx-map-*` when an advanced leader owns boundaries, acceptance, and
  escalation while delegating bounded scan packets to lower-cost workers. Use
  the installed Classic `sp-map-*` companions when a lower-cost model should
  run the whole more-explicit map workflow.

### Source-of-Truth and Change Routing

- A Classic prompt change starts in the Classic surfaces. An Advanced prompt
  change starts in `templates/advanced-skills/**`, including the owning
  `SKILL.md`, triggered `references/**`, deterministic `assets/**`,
  `agents/openai.yaml`, and `_shared/surface-map.json` when topology or ownership
  changes.
- Never implement an Advanced optimization by shortening or weakening Classic.
  Never implement a Classic compatibility fix by pasting the full Classic
  prompt into SPX. Preserve two prompt profiles and one shared runtime wherever
  possible.
- Shared CLI commands, schemas, state machines, validators, launchers, artifact
  formats, project-cognition behavior, and installation semantics are not
  profile forks. Evaluate changes to those surfaces against both profiles and
  all supported integrations.
- Classic `map-scan`, `map-build`, or `map-update` changes automatically affect
  the three Advanced-installed Classic companions because they use the same
  renderer. Separately assess the corresponding `spx-map-*` skill for semantic
  alignment; SPX wording may stay shorter, but scan/build/update ownership and
  runtime contracts must not drift.
- Generated downstream paths such as `.codex/skills/**`, `.claude/skills/**`,
  or `.agents/skills/**` are verification outputs, not source-of-truth edits.
  Fix generators/templates here, then regenerate the downstream fixture or
  test project.

### Required Regression Shape

- For a skills-based integration, Classic-only init installs the expected
  Classic `sp-*` surfaces and passive skills; no `spx-*` skills are installed.
- For a skills-based integration, Advanced-only init installs the complete
  `spx-*` catalog plus exactly the three Classic map companions; unrelated
  Classic `sp-*` workflow skills and the Classic passive bundle are absent.
- Dual install: running init twice with different profiles preserves both
  catalogs, manifests, and profile metadata without overwriting user-modified
  files.
- The three Advanced-installed Classic map companions must remain byte-equivalent
  to the same integration's Classic-profile generation in the same project.
- For Advanced changes, run `tests/test_spx_skill.py`, the relevant
  `tests/integrations/**` suites, packaging/manifest tests, and the
  `skill-creator` validator for every SPX skill. For Classic changes, run the
  affected command/partial/reference, integration-rendering, hook, and artifact
  contract suites. For shared runtime changes, run both sets.
- Keep `README.md`, `PROJECT-HANDBOOK.md`, init's `Start Here` output, and this
  profile contract synchronized whenever profile membership, invocation names,
  or routing guidance changes.

## Current Workflow Guidance

When describing the generated user workflow, teach the current mainline as:

```text
specify -> plan
```

Treat focused repair of an existing specification as part of `sp-specify`; do not introduce a separate Clarify stage.
Treat `sp-deep-research` as the optional runtime-enforced feasibility and planning handoff gate when the requirements are clear but one or more capabilities still need coordinated research, external evidence, an implementation-chain proof, or a disposable demo before planning. It binds the exact spec digest and capability set, owns bounded track leases and result acceptance/rejection, validates provenance and coverage, requires an independent audit, and publishes a digest/revision-bound handoff that `sp-plan` verifies. `deep-research.md` is derived; generic artifact/evidence/result channels must not write the package. It does not own requirement discovery, final architecture, executable tests, or production implementation, and it is not required for minor adjustments to existing, already-proven capabilities.

After task generation, teach the mandatory delivery chain as `tasks -> implement -> review -> accept`. `sp-review` / `spx-review` starts the integrated product from official entrypoints, repairs bounded implementation and wiring defects, and produces fresh system evidence before human acceptance; do not route ordinary implementation completion directly to accept.
