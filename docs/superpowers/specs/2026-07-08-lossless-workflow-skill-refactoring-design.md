# Lossless Workflow Skill Refactoring Design

Date: 2026-07-08

## Requirement

Spec Kit Plus will productize the downstream skill compaction pattern in the
upstream generator. The generated workflow skills will be easier for agents to
read and execute, while preserving the current workflow behavior, quality gates,
artifact contracts, state fields, handoff semantics, validation requirements,
and user confirmation points.

This is a lossless prompt refactoring. It is not workflow simplification.

## Scope

The first migration covers the workflow skills that already proved the pattern
downstream:

- `sp-discussion`
- `sp-specify`
- `sp-plan`
- `sp-tasks`
- `sp-implement`
- `sp-quick`
- `sp-debug`

Codex is only one downstream example. The upstream design must apply to all
skills-format integrations that install `sp-*/SKILL.md` workflow skills,
including Codex, Claude, Cursor, Kimi, Antigravity, Trae, and Mistral Vibe.

## Hard Constraints

- Do not change the main workflow order for any migrated skill.
- Do not change workflow behavior, quality expectations, artifact paths,
  file names, JSON fields, state values, command tokens, review gates, or
  blocking conditions.
- Do not hide hard gates only in external references. The main `SKILL.md` must
  keep a visible forced summary and link to the detailed reference.
- Do not treat reference extraction as permission to rewrite, weaken, merge, or
  delete rules.
- Do not reduce context for non-skills integrations. If they cannot consume
  sidecar references safely, their rendered command output must keep an
  equivalent complete contract by using `single-file-inline` reference
  rendering.
- Do not treat downstream projects as source of truth. Downstream generated
  output is an acceptance sample only.
- Do not involve `tools/project-cognition` release work unless this change
  actually modifies project-cognition runtime behavior or distribution
  contracts.

## Design Direction

Use a main-flow skeleton plus lossless references.

The upstream source layout will distinguish the hot execution path from the
detailed contract:

```text
templates/
  commands/
    discussion.md
    specify.md
    plan.md
    tasks.md
    implement.md
    quick.md
    debug.md

  command-references/
    discussion/*.md
    specify/*.md
    plan/*.md
    tasks/*.md
    implement/*.md
    quick/*.md
    debug/*.md
```

The main command template remains the authoritative entry point. It keeps the
workflow identity, applicability, ordered phases, hard gates, stop conditions,
required inputs and outputs, key artifact paths, key state names, and explicit
reference-loading triggers.

Reference files hold the detailed contract: long schemas, field definitions,
checklists, examples, anti-patterns, exception paths, repair loops, subagent
contracts, review windows, validation rubrics, and recovery rules.

Each reference file must start with:

- `Trigger`: when the agent must read it.
- `Purpose`: what decision or behavior it supports.
- `Preserved Contract`: the original behavior or quality contract it preserves.

## Rendering Model

Command references are a new asset model. They must not be represented with the
existing `{{spec-kit-include: ...}}` directive because include directives are
resolved uniformly before the renderer knows whether it is producing a
skills-format sidecar output or a single-file command output.

The renderer must support two explicit render modes for migrated workflows:

- `skills-sidecar`: render the compact main template as `SKILL.md`, preserve
  reference links, and copy `templates/command-references/<workflow>/` into the
  generated skill directory as processed `references/` files.
- `single-file-inline`: render the compact main template and inline the command
  reference files into the command output at a deterministic
  `Reference Contracts` boundary, after normal script, argument, invocation,
  frontmatter, and agent-name substitutions.

Command references must be rendered with the owning command template context in
both modes. They may use renderer tokens only when those tokens can be resolved
from the owning command's frontmatter and agent context. Reference rendering
must apply the same effective substitution surface as the main command:

- `{{spec-kit-include: ...}}` partial expansion for inline partials.
- `{SCRIPT}` and `{AGENT_SCRIPT}` resolution from the owning command template's
  `scripts` and `agent_scripts` frontmatter.
- `{ARGS}` and agent argument placeholder conversion.
- `__AGENT__` replacement.
- `{{invoke:...}}` invocation rendering.
- Existing project-relative path rewrites.

Generated main skills, generated reference sidecars, and inlined non-skills
command output must fail validation if any unresolved renderer token remains,
including `{SCRIPT}`, `{AGENT_SCRIPT}`, `{ARGS}`, `__AGENT__`, or
`{{invoke:...}}`.

Reference discovery is based on the workflow template stem and the
`templates/command-references/<workflow>/` directory. The compact main template
may contain normal Markdown links to `references/*.md`, but those links are
not the source of truth for locating every reference file during installation;
the reference directory is.

The existing `{{spec-kit-include: ...}}` mechanism remains an inline partial
mechanism for shared prompt text. It is not used for sidecar references.

## Reference Reachability

Every generated workflow skill must make all installed sidecar references
discoverable from the hot path.

Required behavior:

- Each migrated workflow installs a generated or maintained
  `references/INDEX.md`.
- The main `SKILL.md` links to `references/INDEX.md` and tells the agent to use
  it when a stage needs detailed contract routing.
- `references/INDEX.md` lists every reference file in that workflow's
  `references/` directory with its `Trigger`, `Purpose`, and preserved-contract
  summary.
- Every reference file must either be directly linked from the main `SKILL.md`
  or listed in `references/INDEX.md`; copied but unreachable reference files
  are invalid.
- The generated index must not replace direct stage-level links for hard gates.
  Hard gates still need a visible summary and relevant reference link in the
  main file.

## Generated Output

For skills-format integrations, each migrated workflow installs:

```text
<skills-dir>/sp-<workflow>/SKILL.md
<skills-dir>/sp-<workflow>/references/*.md
```

The generated main `SKILL.md` will be shorter and easier to follow, but it
must still expose the full workflow spine and hard gates. The generated
`references/` directory must be copied, recorded in the integration manifest,
and managed by install, repair, and uninstall paths.

Integration-specific augmentation must continue to work. Existing Codex,
Cursor, Claude, or other skill appenders must preserve their current runtime,
leader, dispatch, and tool-surface guidance. Long integration-specific appended
sections may be refactored later, but this migration must not weaken or remove
them.

For non-skills integrations, the output must not be only the short skeleton.
The renderer must use `single-file-inline` mode so the command output contains
the equivalent complete single-file command contract. Invocation syntax,
frontmatter, TOML formatting, script placeholders, and agent-specific
substitutions must remain compatible with existing behavior.

## Repair And Uninstall Semantics

Reference sidecars are generated assets, but repair must preserve the existing
policy that user-customized workflow skills are not rewritten.

Required behavior:

- Install records generated reference files in the integration manifest.
- Uninstall removes manifest-owned reference files using the same safety rules
  as other managed generated files.
- Repair may recreate a missing manifest-owned reference file when the matching
  generated workflow skill still exists and the source reference is available.
- Repair must not overwrite an existing `SKILL.md`.
- Repair must not overwrite an existing reference file whose content differs
  from the manifest record or whose ownership cannot be proven.
- Repair must not update manifest hashes in a way that masks a user-modified
  reference as clean generated content.
- When repair cannot prove a sidecar restore is safe, it must skip the file and
  report the skipped managed path instead of rewriting it.

Regression coverage must extend the existing modified-skill preservation tests
to modified reference sidecars.

## Packaging And Distribution

`templates/command-references/` is a packaged core asset surface.

The implementation must update package data and core-pack lookup logic so the
reference tree is available from both a source checkout and an installed
package. Required distribution checks include:

- `pyproject.toml` force-includes `templates/command-references`.
- Runtime lookup searches the packaged core-pack reference directory and the
  source checkout reference directory.
- Shared-infra installation or restore code that depends on command templates
  either mirrors `command-references` into the generated project or explicitly
  resolves references from the packaged core pack.
- Tests prove migrated workflow references are available during `specify init`
  from both source-tree and packaged-core contexts.
- Preset uninstall or restore paths that regenerate a core workflow `SKILL.md`
  must also restore missing generated sidecar references for that workflow when
  safe, while still preserving modified existing sidecars.

## Workflow Split Boundaries

### `sp-discussion`

Main file preserves exploration, context-boundary lock, continue-by-default
behavior, handoff trigger, and user confirmation. References hold Discussion
Compass, Truth Pass, frontstage/backstage rules, handoff JSON fields, handoff
repair, and evidence accounting.

### `sp-specify`

Main file preserves the path from direct requirement or discussion handoff to
the spec package, question cadence, artifact writing, self-review, and user
review gate. References hold handoff validation, semantic traceability, UI
reference lane, artifact schemas, and self-review checklists.

### `sp-plan`

Main file preserves the requirement for a valid spec package, planning phases,
constitution and risk checks, and plan output. References hold research lanes,
data model and contract guidance, complexity tracking, subagent dispatch, and
plan contract fields.

### `sp-tasks`

Main file preserves the requirement for a valid plan, task-generation sequence,
dependencies, parallel batches, and review gate. References hold task packet
schema, parallel safety, Must-Preserve ledger rules, task review, and repair
rules.

### `sp-implement`

Main file preserves tasks-only execution, leader responsibility, RED-first
testing, review windows, and completion conditions. References hold execution
state, worker contracts, join-point review, safe task-layer repair, branch
review, and validation evidence.

### `sp-quick`

Main file preserves small bounded work routing, the Understanding Checkpoint,
confirmation before execution, boundaries, validation, and stop conditions.
References hold quick workspace state, eligible handoff consumption,
packetized work, validation, and closeout.

### `sp-debug`

Main file preserves bug or regression routing, the Debug Checkpoint,
reproduction and evidence before fixes, root-cause gate, and validation.
References hold evidence lanes, hypothesis tracking, fix gate, regression
validation, and debug state.

## Migration Strategy

Use move-first extraction rather than rewrite-first editing.

1. Add the reference distribution capability without changing workflow content.
2. Migrate `sp-discussion` as the pattern sample because it is large and has
   already been compacted downstream.
3. Verify the sample with source coverage checks and generated output checks.
4. Migrate `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-quick`,
   and `sp-debug`.
5. Add non-skills rendering compatibility so single-file command integrations
   retain the complete contract.
6. Run cross-integration generation and regression tests.

## Verification

Verification must prove that structure changed but behavior did not.

Source-level checks:

- Every original H2/H3 section for a migrated workflow maps to the main file or
  a reference file.
- Every migrated workflow has a rule-level coverage ledger or generated source
  map. Heading coverage is not sufficient.
- The coverage ledger maps original gates, numbered steps, bullets, field
  definitions, state values, JSON keys, exception branches, repair paths,
  review gates, validation gates, and examples to either the main file or a
  specific reference file and anchor.
- Hard gates and stop conditions remain present in the main file as visible
  summaries and in references where details are needed.
- Key artifact paths, state fields, JSON fields, command tokens, and review
  gates remain searchable.
- Every reference has `Trigger`, `Purpose`, and `Preserved Contract`.
- Every link from a main `SKILL.md` to a reference resolves.
- Every reference file is reachable from either the main `SKILL.md` or
  `references/INDEX.md`, and the main `SKILL.md` links to the index.
- Source reference files contain only token-free text or renderer tokens that
  are resolvable from the owning command context.
- Generated reference files pass unresolved-token validation for `{SCRIPT}`,
  `{AGENT_SCRIPT}`, `{ARGS}`, `__AGENT__`, and `{{invoke:...}}`.

Generated-output checks:

- Skills-format integrations install `SKILL.md` plus `references/*.md`.
- The skills-format verification matrix covers at least Codex, Claude, Cursor,
  Kimi, Antigravity, Trae, and Mistral Vibe, plus any future integration whose
  registrar extension is `/SKILL.md`.
- Reference files are included in manifests and covered by repair/uninstall.
- Generated reference sidecars are renderer-processed with the owning command
  context and contain no unresolved renderer tokens.
- Each generated workflow skill includes `references/INDEX.md`, and that index
  lists every installed reference sidecar.
- The generated main skill is shorter but still contains the workflow spine and
  hard gates.
- Existing integration-specific appended guidance remains present.
- Passive skills are unaffected.

Non-skills compatibility checks:

- Single-file command integrations retain the full detailed contract through
  `single-file-inline` rendering.
- Non-skills rendering uses the `single-file-inline` reference mode, not
  `skills-sidecar`.
- Frontmatter, TOML formatting, script placeholders, argument placeholders, and
  invocation syntax remain compatible.

Regression checks:

- Existing integration and alignment tests continue to pass.
- New tests cover reference copying, manifest recording, link resolution,
  source coverage, and non-skills complete-contract rendering.
- New tests cover generated reference processing and fail on unresolved
  `{SCRIPT}`, `{AGENT_SCRIPT}`, `{ARGS}`, `__AGENT__`, or `{{invoke:...}}`
  tokens.
- New tests cover bidirectional reachability: main skill to index, index to
  every reference, and direct main-skill links for hard-gate references.
- New tests cover modified sidecar preservation during repair.
- New tests cover package data, core-pack lookup, shared-infra or packaged
  reference resolution, and preset restore behavior for missing sidecars.

## Non-Goals

- No workflow redesign.
- No behavior change.
- No artifact or state schema change.
- No invocation syntax change.
- No project-cognition runtime or release change.
- No downstream project editing as part of the upstream source change.

## Acceptance Criteria

- The seven target workflows use a main-flow skeleton plus lossless references.
- Skills-format integrations generate compact main workflow skills and complete
  sidecar references.
- Non-skills integrations do not lose detailed workflow context.
- All existing workflow behavior, quality gates, state contracts, handoff
  semantics, and validation requirements are preserved.
- Automated checks and review can trace each moved rule, gate, field, branch,
  and validation requirement to the main file or a specific reference file.
- Repair and preset restore preserve user-customized skill trees while safely
  restoring missing generated sidecars when ownership and source availability
  are proven.
