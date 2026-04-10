# Tasks: Codex Team Runtime Import

**Input**: Design documents from `/specs/001-codex-team-adapter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, `项目技术文档.md`

**Tests**: This feature explicitly requires contract, integration, and tmux-capable runtime verification. Write the listed tests first, confirm they fail for the expected reasons, then implement.

**Organization**: Tasks are grouped by user story so each story remains independently implementable and testable once the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Task can run in parallel because its write set is isolated, its dependencies are already stable, and it has an independent verification path.
- **[Story]**: User story label from `spec.md` (`[US1]`, `[US2]`, `[US3]`, `[US4]`).
- **Write set rule**: Treat shared CLI surfaces, manifest/state registries, templates, context scripts, and exported command registries as coordination surfaces that cannot be changed in the same parallel batch.

## Phase 1: Setup (Shared Scaffolding)

**Purpose**: Create the source-controlled boundaries that the rest of the feature will fill in.

- [X] T001 Create the Codex team package skeleton in `src/specify_cli/codex_team/__init__.py`, `src/specify_cli/codex_team/commands.py`, `src/specify_cli/codex_team/installer.py`, `src/specify_cli/codex_team/manifests.py`, `src/specify_cli/codex_team/runtime_bridge.py`, and `src/specify_cli/codex_team/state_paths.py`
- [X] T002 Create the Codex team test skeleton in `tests/codex_team/__init__.py`, `tests/codex_team/conftest.py`, `tests/contract/test_codex_team_cli_surface.py`, and `tests/contract/test_codex_team_generated_assets.py`
- [X] T003 [P] Create the vendored runtime boundary and provenance stub in `src/specify_cli/runtime_vendor/__init__.py` and `src/specify_cli/runtime_vendor/README.md`

**Checkpoint**: The repository contains explicit code and test boundaries for the new Codex-only subsystem.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared state, manifest, tmux-validation, and installer primitives that every story depends on.

**CRITICAL**: No user story work should start until this phase is complete.

### Tests for Foundation

**Parallel Batch 2.1**: Independent failing tests for shared helpers
- [X] T004 [P] Add failing state-path and manifest helper coverage in `tests/codex_team/test_state_paths.py` and `tests/codex_team/test_manifests.py`
- [X] T005 [P] Add failing tmux environment-check coverage in `tests/codex_team/test_runtime_bridge.py`
**Join Point 2.1**: Confirm the shared-helper tests fail before implementing state or bridge code.

### Implementation for Foundation

**Parallel Batch 2.2**: Isolated helper implementations with non-overlapping write sets
- [X] T006 [P] Implement runtime-state path helpers in `src/specify_cli/codex_team/state_paths.py`
- [X] T007 [P] Implement Codex team manifest/state serializers in `src/specify_cli/codex_team/manifests.py`
- [X] T008 [P] Implement tmux/runtime environment validation helpers in `src/specify_cli/codex_team/runtime_bridge.py` and `src/specify_cli/runtime_vendor/__init__.py`
**Join Point 2.2**: Resolve imports and freeze the installer-facing helper contracts before wiring feature flows.
- [X] T009 Implement the shared Codex team installer boundary in `src/specify_cli/codex_team/installer.py` and `src/specify_cli/codex_team/__init__.py`
- [X] T010 Wire shared Codex team command stubs into `src/specify_cli/codex_team/commands.py` and `src/specify_cli/__init__.py`

**Checkpoint**: Shared runtime/state/install primitives are available, tested, and ready for user-story work.

---

## Phase 3: User Story 1 - Enable Codex Team Capability by Default (Priority: P1)

**Goal**: Fresh `specify init --ai codex` projects receive a `specify`-owned team surface and Codex-only generated assets without requiring external OMX setup.

**Independent Test**: Run `specify init --ai codex --ignore-agent-tools` in a fresh project and confirm Codex-owned team assets are generated and discoverable, while a fresh non-Codex init does not generate or advertise them.

### Tests for User Story 1

**Parallel Batch US1.1**: Lock the Codex install contract before implementation
- [X] T011 [P] [US1] Add failing generated-asset contract coverage in `tests/contract/test_codex_team_generated_assets.py` and `tests/integrations/test_integration_codex.py`
- [X] T012 [P] [US1] Add failing fresh-init CLI-surface coverage in `tests/contract/test_codex_team_cli_surface.py` and `tests/integrations/test_cli.py`
**Join Point US1.1**: Confirm Codex-only asset and surface assertions fail before changing installer behavior.

### Implementation for User Story 1

**Parallel Batch US1.2**: Independent Codex-surface inputs
- [X] T013 [P] [US1] Add the Codex-facing team skill template in `templates/commands/team.md`
- [X] T014 [P] [US1] Extend Codex integration setup behavior in `src/specify_cli/integrations/codex/__init__.py` and `src/specify_cli/integrations/base.py`
- [X] T015 [P] [US1] Extend agent-context update messaging for the `specify`-owned team surface in `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1`
**Join Point US1.2**: Merge template, integration, and context-surface assumptions before touching the shared init flow.
- [X] T016 [US1] Install Codex-only team assets and manifest entries from `specify init` in `src/specify_cli/__init__.py`, `src/specify_cli/codex_team/installer.py`, and `src/specify_cli/integrations/manifest.py`
- [X] T017 [US1] Expose the `specify`-owned team command/help surface for Codex projects in `src/specify_cli/__init__.py` and `src/specify_cli/codex_team/commands.py`

**Checkpoint**: A fresh Codex project gets the official team surface by default, and non-Codex projects still do not.

---

## Phase 4: User Story 2 - Maintain the Runtime In-Repo and Prove the Runtime Loop (Priority: P2)

**Goal**: The runtime is maintained inside this repository and the first-release tmux loop proves bootstrap, dispatch, state recording, failure signaling, and cleanup.

**Independent Test**: In a tmux-capable environment, execute the quickstart flow and verify the vendored runtime can bootstrap, dispatch a minimal task, record state, surface a failure, and clean up into a terminal state.

### Tests for User Story 2

**Parallel Batch US2.1**: Failing lifecycle coverage
- [X] T018 [P] [US2] Add failing runtime-session and dispatch-record lifecycle coverage in `tests/codex_team/test_runtime_session.py` and `tests/codex_team/test_dispatch_record.py`
- [X] T019 [P] [US2] Add failing tmux smoke coverage for bootstrap, dispatch, failure, and cleanup in `tests/codex_team/test_tmux_smoke.py`
**Join Point US2.1**: Confirm lifecycle and smoke tests fail before importing or orchestrating the runtime.

### Implementation for User Story 2

**Parallel Batch US2.2**: Isolated runtime inputs
- [X] T020 [P] [US2] Import the vendored runtime subtree and provenance metadata into `src/specify_cli/runtime_vendor/` and `src/specify_cli/runtime_vendor/README.md`
- [X] T021 [P] [US2] Implement runtime-session and dispatch-state recording in `src/specify_cli/codex_team/manifests.py`, `src/specify_cli/codex_team/state_paths.py`, and `src/specify_cli/codex_team/runtime_bridge.py`
**Join Point US2.2**: Freeze the vendored runtime layout and persisted state schema before wiring the live command flow.
- [X] T022 [US2] Implement bootstrap, dispatch, failure, and cleanup orchestration in `src/specify_cli/codex_team/runtime_bridge.py` and `src/specify_cli/codex_team/commands.py`
- [X] T023 [US2] Document and surface tmux requirement and unsupported-environment messaging in `src/specify_cli/__init__.py`, `README.md`, and `specs/001-codex-team-adapter/quickstart.md`

**Checkpoint**: The embedded runtime loop is observable, supportable, and verified in a tmux-capable environment.

---

## Phase 5: User Story 3 - Isolate Non-Codex Integrations from the New Capability (Priority: P3)

**Goal**: The Codex team import does not change default behavior, generated assets, or advertised surfaces for non-Codex integrations.

**Independent Test**: Initialize one Codex project and one non-Codex project from the same build and confirm only the Codex project receives the team assets and team surface.

### Tests for User Story 3

**Parallel Batch US3.1**: Lock isolation before widening integration wiring
- [X] T024 [P] [US3] Add failing non-Codex isolation regression coverage in `tests/integrations/test_integration_subcommand.py` and `tests/integrations/test_cli.py`
- [X] T025 [P] [US3] Add failing config/registrar isolation checks in `tests/test_agent_config_consistency.py` and `tests/integrations/test_registry.py`
**Join Point US3.1**: Confirm non-Codex behavior is locked before changing shared registries or install routing.

### Implementation for User Story 3

**Parallel Batch US3.2**: Separate shared gating concerns
- [X] T026 [P] [US3] Gate team asset generation to Codex-only install paths in `src/specify_cli/__init__.py`, `src/specify_cli/integrations/__init__.py`, and `src/specify_cli/codex_team/installer.py`
- [X] T027 [P] [US3] Keep non-Codex command registries and context flows free of Codex-only team-surface leakage in `src/specify_cli/extensions.py`, `scripts/bash/update-agent-context.sh`, and `scripts/powershell/update-agent-context.ps1`
**Join Point US3.2**: Verify install routing and registration logic agree on the Codex-only boundary before updating release guidance.
- [X] T028 [US3] Update release-facing isolation guidance in `README.md`, `项目技术文档.md`, and `specs/001-codex-team-adapter/quickstart.md`

**Checkpoint**: The new capability is clearly and verifiably isolated to Codex.

---

## Phase 6: User Story 4 - Keep Existing Codex Project Upgrades Optional (Priority: P4)

**Goal**: First-release messaging guarantees new Codex projects while keeping existing-project upgrades explicitly optional and non-blocking.

**Independent Test**: Review the CLI/help/docs surfaces and confirm they distinguish the new-project guarantee from any optional upgrade path for existing Codex projects.

### Tests for User Story 4

**Parallel Batch US4.1**: Lock the non-blocking migration promise
- [X] T029 [P] [US4] Add failing optional-upgrade regression coverage in `tests/integrations/test_integration_subcommand.py` and `tests/codex_team/test_upgrade_path.py`
- [X] T030 [P] [US4] Add failing release-scope documentation coverage in `tests/codex_team/test_release_scope_docs.py` and `specs/001-codex-team-adapter/quickstart.md`
**Join Point US4.1**: Confirm the upgrade path remains optional in tests and docs before wiring CLI messaging.

### Implementation for User Story 4

**Parallel Batch US4.2**: Independent upgrade-path inputs
- [X] T031 [P] [US4] Implement optional existing-project upgrade helpers in `src/specify_cli/codex_team/installer.py` and `src/specify_cli/codex_team/commands.py`
- [X] T032 [P] [US4] Document first-release scope versus optional upgrade support in `README.md`, `specs/001-codex-team-adapter/plan.md`, and `specs/001-codex-team-adapter/quickstart.md`
**Join Point US4.2**: Merge upgrade-helper behavior and release-scope language before touching shared CLI messaging.
- [X] T033 [US4] Wire non-blocking upgrade messaging into shared CLI flows in `src/specify_cli/__init__.py` and `src/specify_cli/codex_team/commands.py`

**Checkpoint**: Release scope is explicit, and optional upgrade support cannot be mistaken for a launch blocker.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finalize docs, regression evidence, and cross-story cleanup.

- [X] T034 [P] Update release notes and maintainer guidance in `CHANGELOG.md` and `项目技术文档.md`
- [X] T035 Record verification evidence in `specs/001-codex-team-adapter/quickstart.md` after running `pytest tests/integrations/test_integration_codex.py tests/integrations/test_cli.py tests/integrations/test_integration_subcommand.py tests/test_agent_config_consistency.py tests/codex_team -q`
- [X] T036 Normalize exported surfaces and remove temporary scaffolding in `src/specify_cli/codex_team/__init__.py`, `src/specify_cli/codex_team/commands.py`, and `templates/commands/team.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** has no prerequisites.
- **Phase 2: Foundational** depends on Phase 1 and blocks every user story.
- **Phase 3: US1** depends on Phase 2.
- **Phase 4: US2** depends on Phase 2 and should build on the US1 Codex surface once T017 is complete.
- **Phase 5: US3** depends on Phase 2 and validates the boundary established by US1.
- **Phase 6: US4** depends on Phase 2 and should reuse the surfaced commands/install flow from US1.
- **Phase 7: Polish** depends on all shipped stories being complete.

### User Story Dependencies

- **US1 (P1)**: First story to implement after foundation. Establishes the Codex-only public surface.
- **US2 (P2)**: Depends on the foundational bridge/install primitives and benefits from the surfaced command path from US1.
- **US3 (P3)**: Depends on the Codex surface and installer decisions from US1 so it can prove non-Codex isolation against the real implementation.
- **US4 (P4)**: Depends on US1 because it clarifies migration and upgrade behavior for the surfaced Codex capability; it does not block US2 or US3.

### Dependency Graph

```text
Phase 1 Setup
  -> Phase 2 Foundational
      -> US1 (P1)
      -> US2 (P2)
      -> US3 (P3)
      -> US4 (P4)

US1 -> US3
US1 -> US4
US1 -> US2 (shared surfaced command path)

All shipped stories -> Phase 7 Polish
```

### Parallel Opportunities

- **10 parallel batches** are defined: `2.1`, `2.2`, `US1.1`, `US1.2`, `US2.1`, `US2.2`, `US3.1`, `US3.2`, `US4.1`, `US4.2`.
- **24 tasks** are marked `[P]`.
- **Join points** gate every batch so downstream work only starts after contracts, shared registries, and surfaced commands are synchronized.

---

## Parallel Example: User Story 1

```bash
# Parallel Batch US1.1
Task: "Add failing generated-asset contract coverage in tests/contract/test_codex_team_generated_assets.py and tests/integrations/test_integration_codex.py"
Task: "Add failing fresh-init CLI-surface coverage in tests/contract/test_codex_team_cli_surface.py and tests/integrations/test_cli.py"

# Join Point US1.1
# Confirm both test groups fail for the expected Codex-team surface reasons.

# Parallel Batch US1.2
Task: "Add the Codex-facing team skill template in templates/commands/team.md"
Task: "Extend Codex integration setup behavior in src/specify_cli/integrations/codex/__init__.py and src/specify_cli/integrations/base.py"
Task: "Extend agent-context update messaging in scripts/bash/update-agent-context.sh and scripts/powershell/update-agent-context.ps1"

# Join Point US1.2
# Reconcile template, integration, and context assumptions before editing src/specify_cli/__init__.py.
```

## Parallel Example: User Story 2

```bash
# Parallel Batch US2.1
Task: "Add failing runtime-session and dispatch-record lifecycle coverage in tests/codex_team/test_runtime_session.py and tests/codex_team/test_dispatch_record.py"
Task: "Add failing tmux smoke coverage in tests/codex_team/test_tmux_smoke.py"

# Join Point US2.1
# Confirm lifecycle and tmux smoke failures are reproducible.

# Parallel Batch US2.2
Task: "Import the vendored runtime subtree and provenance metadata into src/specify_cli/runtime_vendor/ and src/specify_cli/runtime_vendor/README.md"
Task: "Implement runtime-session and dispatch-state recording in src/specify_cli/codex_team/manifests.py, src/specify_cli/codex_team/state_paths.py, and src/specify_cli/codex_team/runtime_bridge.py"

# Join Point US2.2
# Freeze the vendored runtime layout and persisted state schema before wiring live orchestration.
```

## Parallel Example: User Story 3

```bash
# Parallel Batch US3.1
Task: "Add failing non-Codex isolation regression coverage in tests/integrations/test_integration_subcommand.py and tests/integrations/test_cli.py"
Task: "Add failing config/registrar isolation checks in tests/test_agent_config_consistency.py and tests/integrations/test_registry.py"

# Join Point US3.1
# Confirm non-Codex surfaces remain locked before shared registry changes.

# Parallel Batch US3.2
Task: "Gate team asset generation to Codex-only install paths in src/specify_cli/__init__.py, src/specify_cli/integrations/__init__.py, and src/specify_cli/codex_team/installer.py"
Task: "Keep non-Codex registries and context flows free of Codex-only leakage in src/specify_cli/extensions.py, scripts/bash/update-agent-context.sh, and scripts/powershell/update-agent-context.ps1"

# Join Point US3.2
# Reconcile install routing and registration behavior before final docs updates.
```

## Parallel Example: User Story 4

```bash
# Parallel Batch US4.1
Task: "Add failing optional-upgrade regression coverage in tests/integrations/test_integration_subcommand.py and tests/codex_team/test_upgrade_path.py"
Task: "Add failing release-scope documentation coverage in tests/codex_team/test_release_scope_docs.py and specs/001-codex-team-adapter/quickstart.md"

# Join Point US4.1
# Confirm the upgrade path stays optional before wiring CLI messaging.

# Parallel Batch US4.2
Task: "Implement optional existing-project upgrade helpers in src/specify_cli/codex_team/installer.py and src/specify_cli/codex_team/commands.py"
Task: "Document first-release scope versus optional upgrade support in README.md, specs/001-codex-team-adapter/plan.md, and specs/001-codex-team-adapter/quickstart.md"

# Join Point US4.2
# Merge upgrade behavior and release-scope language before editing shared CLI messaging.
```

---

## Implementation Strategy

### Phased Delivery

1. Complete Setup and Foundational work.
2. Deliver **US1** to make the Codex-only surface installable and discoverable.
3. Deliver **US2** to prove the embedded runtime loop.
4. Deliver **US3** to lock down non-Codex isolation.
5. Deliver **US4** only after the core release path is stable, because it is explicitly non-blocking.
6. Finish with Polish and verification evidence.

### Priority-Ordered Delivery

- **Release-critical slice**: Phase 1 + Phase 2 + US1 + US2 + US3.
- **Post-core slice**: US4, because the spec makes existing-project upgrade support optional for first release.

### Capability-Aware Parallel Execution

- Start every story with its failing-test batch.
- Only run `[P]` tasks together when their write sets do not overlap.
- Treat `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, `scripts/bash/update-agent-context.sh`, `scripts/powershell/update-agent-context.ps1`, and manifest/state registries as join-point surfaces.
- If only one implementer is available, execute tasks sequentially within each batch but keep the same join-point ordering.

---

## Notes

- All task lines follow the required checklist format.
- Every user story phase includes an explicit goal and independent test.
- The smallest coherent first release is not just US1; it is the Codex-only surfaced install path plus the runtime-loop proof and non-Codex isolation boundary.
