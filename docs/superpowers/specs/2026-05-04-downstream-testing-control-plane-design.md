# Downstream Testing Control Plane Design

## Summary

This design defines the first high-quality downstream testing system for generated Spec Kit Plus projects. The system centers all testing policy, discovery, execution guidance, and workflow reuse under a single control plane at `.specify/testing/*`.

The design goals are:

- Make downstream testing artifacts the single source of truth for `sp-test-scan`, `sp-test-build`, `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`, `sp-fast`, and `sp-quick`
- Ensure a newcomer who adds behavior can immediately see where tests belong, which scenarios to add, and which commands to run
- Support a strong default lane for `small` unit tests, `medium` local API or adapter tests, and `fast smoke` verification without making `large` E2E a first-release dependency
- Prefer contract-driven automation over freeform test generation
- Provide stronger defaults for Python and TypeScript or JavaScript projects while preserving a language-agnostic contract for other stacks

## Problem Statement

The repository already defines `sp-test-scan`, `sp-test-build`, and the downstream `.specify/testing/*` artifact family. It also already routes planning and implementation workflows to consume those artifacts when present. The remaining gap is not workflow existence. The remaining gap is control-plane strength.

Today, the product surface can describe testing artifacts, but the downstream experience still risks these failure modes:

- multiple workflows infer testing rules independently instead of consuming one durable testing contract
- generated testing artifacts overlap in purpose and become duplicative documentation instead of operational truth
- a newcomer can still be told to "add tests" without being told where to put them, which scenario categories matter, or which commands provide the fastest trustworthy validation
- API and adapter work can default to happy-path-only test additions because the scenario matrix is not treated as a binding structure
- testing automation can devolve into low-signal test scaffolding if it is not anchored to scenario matrices, module ownership, and execution commands

This design turns `.specify/testing/*` from a loose artifact bundle into a strict downstream testing control plane.

## Design Principles

### 1. Single control plane

Downstream projects must have one testing source of truth. Workflow commands may read different testing artifacts, but they may not invent independent testing policy once `.specify/testing/*` exists.

### 2. Contract before generation

The system must prefer structured discovery, scenario matrices, lane packets, and module rules before any automated test-building behavior. Automation extends explicit policy; it does not replace it.

### 3. Newcomer-first usability

Every covered module should expose enough local testing guidance that a newcomer can answer these questions without repo archaeology:

- where should the new test go
- what should the test file be named
- which fixture, helper, or factory layer should be reused
- what is the narrowest RED command
- what is the focused module validation command
- what is the full project validation command

### 4. Risk-weighted scope

The first release should strongly support:

- `small` tests for truth-owning logic and behavior contracts
- `medium` tests for local API, CLI, adapter, serializer, storage, and local integration seams
- `fast smoke` validation for very quick confidence after small changes

The first release should not require a comprehensive `large` or E2E platform.

### 5. Strong default enforcement

For covered modules, behavior changes and bug fixes should default to mandatory test updates. The workflow should make exceptions explicit rather than silently optional.

### 6. Extend, do not replace

Generated downstream testing systems should extend or standardize existing project frameworks. They should not casually replace a stable user-owned testing architecture.

## Scope

### In scope

- downstream generated project testing artifacts under `.specify/testing/*`
- workflow contracts for `sp-test-scan` and `sp-test-build`
- downstream consumption rules for `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, `sp-debug`, `sp-fast`, and `sp-quick`
- newcomer test-addition flow
- `fast smoke`, `focused`, and `full` validation tiers
- support expectations for Python and TypeScript or JavaScript first-class defaults
- scenario-matrix expectations for API, adapter, and local integration surfaces

### Out of scope

- building a mandatory first-release E2E platform
- freeform AI test generation without scenario anchors
- synthetic or invented coverage numbers
- replacing downstream user-owned test frameworks when extension is sufficient

## Target User Experience

When a downstream user adds a feature or fixes a bug in a covered module, the workflow experience should converge to this:

1. The active workflow reads `.specify/testing/TESTING_CONTRACT.md` and `.specify/testing/TESTING_PLAYBOOK.md`.
2. The workflow identifies whether the touched module is covered and which layer mix applies.
3. The workflow tells the user or subagent exactly where the new tests belong and which scenario classes must be updated.
4. The workflow requires a failing test first for behavior changes or regressions.
5. The workflow exposes the module's `fast smoke`, `focused`, and `full` validation commands.
6. The workflow leaves durable evidence in `.specify/testing/*` so later runs do not rediscover the same rules.

For brownfield projects with weak or partial test coverage, the system should instead route to a testing-program path:

1. `sp-test-scan` discovers modules, risk tiers, existing test surfaces, gaps, and executable test-building lanes.
2. `sp-test-build` turns that evidence into foundational tests, test helpers, contract documents, and coverage baseline artifacts.
3. Later planning and implementation workflows consume those artifacts directly instead of re-scoping testing policy from scratch.

## Control Plane Architecture

The downstream testing control plane is the directory `.specify/testing/*`. It is not a passive documentation folder. It is the durable policy and execution surface for testing-aware workflows.

The control-plane lifecycle is:

`sp-test-scan -> TEST_BUILD_PLAN -> sp-test-build -> TESTING_CONTRACT / TESTING_PLAYBOOK / COVERAGE_BASELINE -> downstream workflow consumption`

Each workflow has a strict role:

- `sp-test-scan` discovers and structures evidence
- `sp-test-build` executes approved testing-system construction
- `sp-specify` and `sp-plan` consume testing-program and testing-policy inputs
- `sp-tasks` materializes test work as default deliverables
- `sp-implement` enforces RED-first testing and module-local validation behavior
- `sp-debug` enforces repro or regression coverage before resolving a bug
- `sp-fast` and `sp-quick` operate only within already-defined testing lanes, not as independent testing-policy authors

## Artifact Model

### `TEST_SCAN.md`

Purpose:

- human-readable evidence report for current project testing state

Must contain:

- module inventory summary
- language and framework evidence
- risk tiers
- inspected files and public entrypoints
- existing test-surface assessment
- missing scenario categories
- blockers and uncertainties
- recommended `small / medium / large` layer mix by module

Must not become:

- the machine-executable source of test-building lanes
- the durable project testing contract

### `TEST_BUILD_PLAN.md`

Purpose:

- human-readable execution plan for testing-system construction

Must contain:

- wave order
- lane readiness
- lane objectives
- write-set summaries
- validation commands
- done conditions
- shared-surface serialization requirements

Must answer:

- what should be built first
- what can run in parallel
- what requires leader-owned sequencing or review

### `TEST_BUILD_PLAN.json`

Purpose:

- machine-readable lane truth for `sp-test-build`

Must contain:

- executable lanes with `lane_id`, `wave_id`, `module`, `write_set`, `allowed_actions`, `forbidden_actions`, `validation_command`, and `done_condition`

Must be treated as:

- the canonical runtime lane source when present

Must not be treated as:

- optional duplication of the Markdown plan

### `UNIT_TEST_SYSTEM_REQUEST.md`

Purpose:

- brownfield testing-program request surface for later planning and workflow continuation

Must contain:

- current module-by-module testing assessment
- `small / medium / large` philosophy and target mix
- module risk tiers
- scenario matrix
- coverage uplift waves
- CI or presubmit gate policy
- allowed testability refactors
- recommended routing for `sp-specify`, `sp-quick`, or `sp-fast`

This file exists so large testing-system work can enter `sp-specify` and `sp-plan` as a structured program rather than as unstructured user intent.

### `TESTING_CONTRACT.md`

Purpose:

- project-wide testing policy and enforcement surface

Must contain:

- covered-module rules
- mandatory testing triggers
- regression-test requirements for bug fixes
- module-level framework ownership
- coverage policy
- explicit gaps and exceptions
- implementation and planning workflow obligations

This file is the policy anchor that turns testing from recommendation into workflow constraint.

### `TESTING_PLAYBOOK.md`

Purpose:

- operator-facing test execution and test-authoring guide

Must contain:

- environment setup
- install and build commands
- run-all command
- module-level targeted commands
- file-level or name-filter commands when framework support exists
- coverage commands
- CI commands
- where new tests belong
- naming conventions
- fixture or helper reuse guidance
- smallest RED-first command
- focused module validation command
- full project validation command

This file is the newcomer usability anchor.

### `COVERAGE_BASELINE.json`

Purpose:

- machine-readable baseline and threshold surface

Must contain:

- per-module baseline data
- thresholds when known
- unknown measurement state when coverage is not yet reliable
- explicit hotspot or exception tracking when required

Must not contain:

- narrative policy that belongs in `TESTING_CONTRACT.md`

### `testing-state.md`

Purpose:

- resumable testing workflow state

Must contain:

- active command
- scan and build status
- selected modules
- selected language skills
- current wave and lane
- artifact paths
- open gaps
- next command and handoff reason
- latest manual validation evidence

This file remains the state surface, not the policy surface.

## Workflow Responsibilities

### `sp-test-scan`

`sp-test-scan` is the read-only evidence workflow. Its job is to discover and structure testing reality before any test-system construction begins.

It should:

- inventory modules, manifests, frameworks, and commands
- assign risk tiers
- identify truth-owning files and public entrypoints
- classify missing scenarios
- propose layer mix and build lanes
- generate scan and build-plan artifacts
- recommend exactly one next command

It should not:

- write final testing contract or playbook artifacts
- mutate source or test files
- invent executable build policy without evidence

### `sp-test-build`

`sp-test-build` is the testing-system construction workflow. It consumes scan-approved lanes and turns them into durable testing assets and concrete repo changes.

It should:

- execute validated build lanes
- add or refresh tests, fixtures, helpers, and local test config
- record module ownership and commands
- produce `TESTING_CONTRACT.md`, `TESTING_PLAYBOOK.md`, and `COVERAGE_BASELINE.json`
- update `UNIT_TEST_SYSTEM_REQUEST.md` when build evidence changes the long-range testing program
- capture manual validation evidence truthfully

It should not:

- rebuild scan intent from chat memory
- bypass lane packet boundaries
- claim validation without explicit command evidence

### `sp-specify`

When brownfield testing-system work is in play, `sp-specify` should treat `UNIT_TEST_SYSTEM_REQUEST.md` as required input. It should extract priority waves, scenario-matrix expectations, allowed refactors, and CI policy from that file rather than restating testing goals from scratch.

### `sp-plan`

`sp-plan` should consume `TESTING_CONTRACT.md`, `TESTING_PLAYBOOK.md`, and `COVERAGE_BASELINE.json` when present. Testing rules and commands should be copied into planning artifacts as constraints, not left as optional follow-up ideas.

### `sp-tasks`

`sp-tasks` should treat tests as default deliverables for behavior changes, bug fixes, and refactors. When the testing contract exists, task generation should include:

- failing-test tasks
- implementation tasks
- focused validation tasks
- broader validation tasks when required

For API, adapter, or local integration seams, it should also generate `medium` test tasks rather than only unit-only tasks.

### `sp-implement`

`sp-implement` should treat `TESTING_CONTRACT.md` and `TESTING_PLAYBOOK.md` as binding when present. For covered modules it should:

- write or update failing tests first
- confirm RED before implementation
- run the module's focused validation command before accepting the batch
- run broader validation according to project policy before completion

If no reliable automated test surface exists, it should bootstrap the smallest viable test surface or route back to `sp-test-scan`.

### `sp-debug`

`sp-debug` should require repro or regression coverage for covered modules. When a bug touches a covered module:

- write a failing repro or regression test first
- use the project playbook's commands for validation
- refuse to treat the bug as resolved without regression protection unless an explicit exception exists

### `sp-fast` and `sp-quick`

These workflows should operate inside the testing control plane, not outside it.

- `sp-fast` should only handle one tiny harness, command, fixture, or helper repair with obvious verification
- `sp-quick` should only consume one bounded module, one risk tranche, or one coverage wave
- neither workflow should invent testing policy that conflicts with `.specify/testing/*`

## Default Test Layers

### First-release supported layers

The first release should formalize three downstream testing layers:

- `small`
- `medium`
- `fast smoke`

### `small`

`small` tests cover:

- truth-owning logic
- validation logic
- state transitions
- deterministic transformations
- public contract behavior
- boundary and exception handling

These should be the default foundation layer.

### `medium`

`medium` tests cover local integration seams inside the repository, including:

- API handlers
- CLI entrypoints
- serializers and deserializers
- repository or adapter boundaries
- local storage seams
- local process or localhost interactions when kept repository-local

These tests must remain local and controllable. They should not become a disguised E2E platform.

### `fast smoke`

`fast smoke` is a validation tier, not a separate test taxonomy. It provides the smallest trustworthy command that answers, "Did this local behavior still work after the change?"

Every covered module should expose:

- one `fast smoke` command
- one `focused` command
- one `full` validation command

### Deferred `large`

`large` tests remain an extension point in `UNIT_TEST_SYSTEM_REQUEST.md`, but they should not be a first-release hard dependency.

## Scenario Matrix Requirements

The first release should force scenario completeness through a standard minimum matrix for critical covered behavior. For API and adapter-heavy work, the matrix should include at least:

- valid path
- invalid or null path
- boundary-value path
- exception or error path
- local integration seam path

For each scenario row, downstream artifacts should be able to capture:

- module
- layer
- scenario description
- preconditions
- input or trigger
- expected observable outcome
- priority

This keeps API testing from collapsing into happy-path-only coverage.

## Newcomer Test Addition Flow

For a newcomer adding a feature in a covered module, the expected flow is:

1. The active workflow identifies the touched module and confirms module coverage.
2. `TESTING_PLAYBOOK.md` tells the newcomer where the new test belongs.
3. The playbook tells the newcomer which fixture, helper, or factory layer to reuse.
4. The playbook exposes the narrowest RED command for the module.
5. The newcomer adds the failing test against the public behavior or documented boundary.
6. The implementation proceeds only after RED is confirmed.
7. The newcomer runs the module's `focused` command.
8. The workflow or user runs the project's `full` validation command before closeout when required.

This is the minimum downstream experience the system must make obvious.

## Validation Tiers

The downstream system should normalize three verification tiers:

### `fast smoke`

Use when:

- a small behavior or helper changed
- fast local feedback is needed
- the goal is immediate confidence, not final signoff

### `focused`

Use when:

- a covered module changed
- a bug fix touched one local surface
- the current batch needs trustworthy module-level validation

### `full`

Use when:

- final validation is required
- CI equivalence or project-wide test confidence is needed
- the testing contract requires broader coverage checks before completion

The playbook must map these tiers to real repository commands instead of generic placeholders.

## Language Strategy

### Contract is language-agnostic

All downstream projects should receive the same control-plane artifact semantics, regardless of language.

### Strong first-release defaults

Python and TypeScript or JavaScript should receive the strongest first-release defaults because they are the most likely to benefit from immediate module discovery, command mapping, and test skeleton conventions.

These defaults include:

- stronger framework inference
- stronger canonical command detection
- stronger guidance for test file placement
- stronger fixture or helper reuse conventions
- better `fast smoke`, `focused`, and `full` command mapping

### Other stacks

Other stacks should still receive:

- the same artifact family
- the same control-plane semantics
- the same risk, scenario, and routing rules

They may begin with thinner default guidance until framework-specific support expands.

## Automation Strategy

### What automation should do

`sp-test-scan` automation should:

- detect modules, manifests, languages, and frameworks
- infer current test paths and test commands
- infer coverage commands where possible
- assign selected testing skills
- produce scenario seeds and build-lane seeds
- write evidence and machine-readable build plans

`sp-test-build` automation should:

- consume validated lanes
- create or refresh test-system artifacts
- standardize module commands and module guidance
- write or update coverage baseline data
- capture actual validation evidence

### What automation should not do

The system should not:

- generate freeform tests with no scenario anchor
- fabricate coverage numbers
- replace stable downstream frameworks by default
- allow each workflow to copy or mutate testing rules independently

The standard is contract-driven automation, not unconstrained code generation.

## Enforcement Model

The first release should adopt a strong default enforcement model.

For covered modules:

- behavior changes must add or update tests
- bug fixes must add regression coverage
- testing obligations may only be skipped for explicit exceptions such as docs-only work, contract-recorded gaps, or deliberately approved narrow exceptions

The goal is to make testing the default path, not an optional extra.

## Risks

### Risk: artifact overlap

If artifact boundaries remain fuzzy, downstream projects will treat the control plane as duplicative docs instead of actionable truth.

Mitigation:

- keep each artifact's purpose strict and non-overlapping
- keep JSON as runtime truth where applicable
- keep contract and playbook separate

### Risk: over-automation

If the product starts free-generating tests without scenario anchors, the downstream experience will become noisy and low-signal.

Mitigation:

- require scenario matrices
- require module ownership
- require real commands and explicit validation evidence

### Risk: too much first-release scope

If the first release tries to build a full E2E platform, the testing system will become too heavy for common downstream use.

Mitigation:

- formalize `small`, `medium`, and validation tiers first
- defer `large` as an extension surface

### Risk: framework replacement drift

If testing workflows replace downstream framework choices casually, the system will feel invasive and brittle.

Mitigation:

- extend stable existing frameworks whenever possible
- make replacements explicit and evidence-backed

## Open Design Decisions

The design intentionally leaves these as implementation decisions rather than unresolved product ambiguity:

- exact template wording and field expansions for each downstream testing artifact
- exact inventory heuristics for richer Python and TypeScript or JavaScript command detection
- exact thresholds and baseline JSON schema details where measurement support differs by framework
- exact lane-packet and result-handoff shapes beyond the current minimum contract

These are implementation details inside an approved architecture, not missing product decisions.

## Recommended Implementation Direction

Implementation should proceed as a cross-surface product change, not as a template-only edit. The work should at minimum cover:

- `templates/commands/test-scan.md`
- `templates/commands/test-build.md`
- `templates/testing/*`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/debug.md`
- `templates/commands/fast.md`
- `templates/commands/quick.md`
- `src/specify_cli/testing_inventory.py`
- downstream integration rendering and skill-install surfaces where these artifacts ship
- tests covering workflow guidance and downstream artifact semantics

The implementation should preserve the current control-plane direction already visible in the repository and harden it into a coherent downstream testing product surface.
