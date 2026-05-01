# Command Surface Semantics Design

**Date:** 2026-05-01  
**Status:** Proposed  
**Scope:** Shared workflow templates, generated skills/commands, public docs, and integration projection behavior  
**Primary goal:** Separate canonical workflow-state tokens from user-facing invocation syntax across all integrations without breaking existing state, hooks, or generated assets

## Problem

Spec Kit Plus currently mixes three different concepts in the same text surfaces:

1. internal workflow-state identifiers
2. user-facing invocation syntax
3. integration-specific command or skill projections

That blending is now causing real external usability failures:

- public docs often imply `/sp-*` works everywhere
- skills-backed integrations such as Codex and Kimi still generate `SKILL.md` content that recommends slash-style invocation even when the real surface is `$sp-*` or `/skill:sp-*`
- template authors cannot reliably tell when `/sp.plan` is intended as a state token versus a literal command to type

The result is drift between:

- canonical workflow truth
- generated integration surfaces
- public docs
- extension and preset override chains

This design solves that by formalizing a three-layer command surface model, making the shared template layer the primary source of truth, and projecting user-facing syntax per integration during generation.

## Goals

- Preserve existing canonical workflow-state semantics and compatibility
- Make shared templates unambiguous about internal tokens versus user invocation syntax
- Ensure generated assets for each integration are self-consistent
- Ensure public docs no longer imply one invocation syntax works across all integrations
- Unify `init` generation and extension/preset override behavior under one projection rule
- Add regression coverage so the template layer cannot silently drift back into mixed semantics

## Non-Goals

- Renaming `sp-specify`, `sp-plan`, or other existing workflow names
- Changing `sp-teams` as the Codex runtime product surface
- Migrating historical `workflow-state.md` files or rewriting existing artifacts in user projects
- Replacing slash-prefixed canonical tokens with a new neutral internal token scheme
- Solving every wording inconsistency in one pass across low-signal historical design notes

## Design Summary

Introduce a formal three-layer model:

1. `Canonical workflow token`
2. `User invocation surface`
3. `Integration projection`

The shared template layer must author against those concepts explicitly:

- canonical workflow tokens remain the only valid tokens for state, artifact, hook, validation, and handoff semantics
- user invocation text must never hardcode a universal syntax in shared templates
- integration generation must project invocation syntax from canonical workflow names into the active surface

This preserves compatibility while removing ambiguity for users and template authors.

## Interface Model

### 1. Canonical Workflow Token

Canonical workflow tokens are the internal protocol identifiers for workflow progression and contract enforcement.

Examples:

- `/sp.plan`
- `/sp.tasks`
- `/sp.specify`
- `/sp.deep-research`

These tokens are authoritative in:

- `workflow-state.md`
- `next_command`
- hooks and validators
- learning capture and aggregation
- artifact validation rules
- handoff and escalation contracts
- stateful workflow reports

These tokens are not required to be directly invocable in every integration.

### 2. User Invocation Surface

User invocation surface is the literal syntax a user should type or invoke in the current integration.

Examples:

- Codex: `$sp-plan`
- Claude: `/sp-plan`
- Kimi: `/skill:sp-plan`
- Markdown command integrations: `/sp.plan`

This surface is authoritative in:

- generated next-steps output after `specify init`
- public docs that tell a user what to type
- skill or command text that explicitly instructs the user to run the next workflow
- operator-facing runtime guidance such as `sp-teams`

### 3. Integration Projection

Integration projection is the mapping from canonical workflow concept to the user-facing surface for a specific integration.

Projection examples:

- `plan` -> `$sp-plan` for Codex
- `plan` -> `/sp-plan` for Claude
- `plan` -> `/skill:sp-plan` for Kimi
- `plan` -> `/sp.plan` for Markdown command agents

Projection must be centralized and reusable across:

- `init` generation
- extension-generated skills
- preset-generated skills
- hook-generated user prompts that include explicit command invocations

## Template Authoring Rules

The shared template layer must classify text into one of three categories.

### State or Contract Text

Examples:

- `next_command: /sp.plan`
- `route to /sp.tasks`
- `workflow-state must preserve /sp.deep-research`

Rules:

- use canonical workflow tokens only
- do not project integration syntax
- do not rewrite existing state semantics

Reason:

These strings are consumed by hooks, validators, state readers, tests, and artifact contracts. They must remain stable.

### User Action Text

Examples:

- "Run the next workflow"
- "In chat, invoke the planning step"
- "Recommended next command"

Rules:

- never hardcode `/sp-*` as a supposedly universal user-facing syntax
- always project into the active integration surface
- shared templates should author these with an invocation placeholder, not a literal prefix

Reason:

This is the text users follow directly. If it is wrong, the generated surface is functionally misleading even when state semantics remain correct.

### Mixed Text

Examples:

- a sentence that both explains `next_command` state and tells the user what to type next

Rules:

- split into two statements
- keep the state statement in canonical-token form
- keep the user action statement in projected invocation form

Reason:

Mixed text is the main source of ambiguity and the primary way the current template layer leaks internal protocol syntax into user guidance.

## Projection Mechanism

### Placeholder Strategy

Shared templates should stop embedding universal command syntax in user-action lines.

Instead, use a projection placeholder model at author time, conceptually:

- `{{invoke:plan}}`
- `{{invoke:specify}}`
- `{{invoke:tasks}}`
- `{{invoke:deep-research}}`

The exact placeholder syntax can be implemented in whichever way best fits the current template pipeline, but the semantics must be:

- placeholder means "project this workflow as a user-facing invocation"
- canonical state tokens remain literal where required

### Projection Map

Minimum projection rules:

- Codex: `$sp-<name>`
- Antigravity: `$sp-<name>`
- Claude skills: `/sp-<name>`
- Kimi skills: `/skill:sp-<name>`
- Markdown command integrations: `/sp.<name>`
- TOML command integrations follow the same rendered invocation surface as their command family

Special cases:

- `team` projects to `sp-teams` as the Codex runtime surface
- `implement-teams` remains integration-specific and must preserve current product boundaries

## Code Surface Changes

### Shared Template Layer

Primary focus:

- `templates/commands/**`
- selected `templates/passive-skills/**`

High-priority templates:

- `specify.md`
- `plan.md`
- `tasks.md`
- `auto.md`
- `analyze.md`
- `quick.md`
- `test-scan.md`
- `test-build.md`
- `team.md`
- `implement-teams.md`

High-priority passive skills:

- `spec-kit-workflow-routing`
- `spec-kit-project-map-gate`
- `subagent-driven-development`
- `dispatching-parallel-agents`

### Generation Layer

Primary enforcement points:

- `src/specify_cli/integrations/base.py`
- `src/specify_cli/agents.py`

Requirements:

- `init` generation path and extension/preset generation path must use the same invocation projection rule
- user-facing invocation examples must be projected from one shared helper
- canonical workflow-state strings must not be rewritten when they occur in state or contract contexts

### Public Docs

Primary targets:

- `README.md`
- `docs/quickstart.md`
- `docs/installation.md`

Requirements:

- stop implying that `/sp-*` works across all integrations
- document canonical workflow names separately from invocation syntax
- show integration-specific examples where the user is expected to type a command

## Compatibility Strategy

Adopt a compatibility-preserving strategy:

- keep `/sp.plan`, `/sp.tasks`, `/sp.specify`, and related tokens as the canonical workflow-state layer
- do not migrate historical state files
- do not introduce a second canonical state token scheme
- do not rename existing workflow skills
- do not rename `sp-teams`

This minimizes risk by changing guidance and projection semantics while leaving internal workflow protocol stable.

## Migration Plan

### Phase 1: Rules and Shared Projection

- formalize template authoring rules
- implement or finalize shared projection helper behavior
- ensure `init` and extension/preset chains use the same logic

### Phase 2: High-Risk Template Cleanup

First-pass cleanup targets:

- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/auto.md`
- `templates/commands/analyze.md`
- `templates/commands/quick.md`
- `templates/commands/test-scan.md`
- `templates/commands/test-build.md`

Goal:

- remove user-facing universal `/sp-*` assumptions from the most common and highest-impact generated surfaces

### Phase 3: Passive Skills and Public Docs

- clean workflow-routing and project-map guidance
- update README and quickstart language
- ensure installation docs describe invocation syntax per integration rather than per workflow name alone

### Phase 4: Regression Hardening

- add tests that fail when user-facing invocation text regresses to the wrong surface
- add tests that fail when canonical state tokens are accidentally projected into integration-specific syntax

## Testing Strategy

### Unit Layer

Test the projection rules directly:

- Codex -> `$sp-*`
- Claude -> `/sp-*`
- Kimi -> `/skill:sp-*`
- Markdown command integrations -> `/sp.*`

Edge cases:

- `sp-teams`
- `sp-implement-teams`
- dotted to hyphenated conversion
- canonical-token preservation

### Generated Asset Layer

For `specify init --ai <agent>`:

- generated user-facing guidance must use the correct integration syntax
- generated state and contract content must preserve canonical tokens where required
- the same shared template must yield:
  - stable state semantics
  - different user invocation surfaces per integration

### Documentation Layer

Validate that public docs:

- do not present `/sp-*` as universal user syntax
- explicitly distinguish canonical workflow names from integration-specific invocation syntax

### Regression Layer

Add tests that block:

- user-facing examples in skills-backed assets that still assume universal slash invocation
- accidental rewriting of canonical tokens into integration syntax inside state or contract sections

## Risks

### Risk: Over-Replacement

If projection logic blindly rewrites all `/sp-*` references, it will corrupt state semantics.

Mitigation:

- classify text by intent
- only project user-facing invocation text
- preserve canonical tokens in state and contract contexts

### Risk: Partial Coverage

If only one generation path is updated, `init` and extension/preset behavior will drift again.

Mitigation:

- enforce one shared projection helper
- test both generation paths

### Risk: Template Author Confusion

Without explicit authoring rules, future template edits will reintroduce mixed semantics.

Mitigation:

- document authoring rules in code comments or template guidance
- add regression tests at the shared-template layer

### Risk: Doc Drift

Public docs can drift separately from generated output.

Mitigation:

- include docs in the same design scope
- keep public docs aligned with the model, not with one integration

## Acceptance Criteria

This design is complete only when all of the following are true:

1. Shared templates clearly separate canonical workflow-state tokens from user invocation syntax
2. Generated skills and commands for at least Codex, Claude, Kimi, and one Markdown command integration are self-consistent
3. Public docs no longer imply that `/sp-*` is a universal invocation surface
4. `init` generation and extension/preset generation use the same projection semantics
5. Canonical state semantics remain backward-compatible
6. Regression tests exist for both:
   - wrong user-facing invocation syntax
   - accidental projection of canonical state tokens

## Recommended Implementation Phases

1. Rules and rendering infrastructure
2. High-risk template and public-doc cleanup
3. Test matrix and consistency hardening

## Open Questions

None are required before planning. The compatibility strategy is intentionally conservative:

- keep the canonical token layer
- fix the template layer
- centralize invocation projection

That is sufficient to move into implementation planning without introducing a state migration program.
