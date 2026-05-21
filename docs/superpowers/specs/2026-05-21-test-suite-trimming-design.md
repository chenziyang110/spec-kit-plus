# Aggressive Test Suite Trimming Design

## Context

The repository currently collects 3,286 pytest cases. The largest surfaces are integration rendering, presets, extensions, alignment/template guidance, hook CLI behavior, artifact hooks, timestamp/script flows, and Codex team orchestration. The suite has no slow-test markers or default test layering; `pyproject.toml` runs the entire `tests` tree with verbose pytest output.

The requested direction is aggressive deletion of test code, not merely moving tests behind a marker. The desired outcome is a substantially smaller full-suite test set with acceptable coverage loss.

## Goal

Reduce the collected test count by at least 50%, targeting roughly 1,200 to 1,600 collected tests, while preserving the contracts most likely to catch release-breaking regressions.

The optimized suite should act as a product risk net:

- Keep tests that prove user-visible CLI behavior, generated asset shape, integration-specific transformations, hook fail-closed behavior, packaging inclusion, and high-risk pure logic.
- Remove tests that repeatedly lock identical behavior across every agent, assert incidental wording, or enumerate low-value combinations that do not represent distinct failure modes.

## Non-Goals

- Do not add a slow-test marker as the main solution.
- Do not hide tests from default execution while keeping large volumes of low-value test code.
- Do not chase a coverage percentage target.
- Do not refactor production code unless required to remove or simplify tests safely.

## Retained Contracts

### CLI and Generated Assets

Keep coverage for the main `specify` CLI surfaces that users directly invoke:

- `specify init` installs the expected directory structure and command assets.
- Integration install, repair, and upgrade flows keep their visible behavior.
- Packaged templates, command partials, passive skills, worker prompts, scripts, and shared hook assets remain included.
- User-facing failures remain actionable.

### Representative Integration Matrix

Replace exhaustive per-agent deep tests with representative samples:

- Standard Markdown agent: keep one ordinary Markdown integration as the base behavior sample.
- Skills integrations: keep Codex and one IDE skills integration sample.
- TOML integrations: keep one TOML sample.
- Special integrations: keep focused tests for Copilot, Forge, opencode, Codex, and Generic because they have non-standard processing or directory rules.
- Registry coverage should verify every supported integration is registered and has basic metadata, but not rerun full install/render contracts for each one.

### Hook and Runtime Safety

Keep tests for hook/runtime behavior that fails closed or prevents corrupted state:

- Required artifacts are rejected when missing or malformed.
- Dangerous or incomplete workflow states do not pass.
- CLI hook wrappers return machine-readable payloads for key success and failure paths.
- Git-sensitive preflight behavior is covered by a small number of representative cases.

### High-Risk Pure Logic

Keep compact unit coverage for logic-heavy modules where tests are cheap and regressions are subtle:

- Project cognition status/query/validation core behavior.
- Codex team task, result, dispatch, and runtime state models.
- Orchestration and execution packet validation.
- Workflow marker parsing and core path classification.

## Deletion Strategy

### Integration Tests

Current integration tests spend many cases proving the same base integration behavior across many agents. Delete or collapse tests that only differ by agent key when the production path is shared.

Keep:

- Base integration tests for Markdown, skills, and TOML processing.
- One smoke test per integration family proving install output shape.
- Focused tests for agents with special behavior:
  - Copilot companion prompts and VS Code settings.
  - Forge parameter replacement and frontmatter transformation.
  - opencode singular `command` directory.
  - Codex skills and team-related generated assets.
  - Generic custom command directory handling.

Delete:

- Per-agent duplicate assertions for generated command file existence when registry coverage already proves the agent exists.
- Repeated CLI invocation tests that exercise the same `init` branch through every integration.
- Per-agent text assertions that duplicate shared command-template tests.

### Template and Guidance Tests

Template guidance tests should verify durable product contracts, not every sentence.

Keep:

- A small set of tests that verify workflow navigation, required artifacts, state handoffs, and non-negotiable safety language.
- Tests that protect current workflow guidance such as `specify -> plan`, optional `CLARIFY`, and `sp-deep-research` handoff positioning.
- Tests for command frontmatter and shared invocation structure.

Delete:

- Tests that assert incidental wording when the behavior can be represented by one broader contract.
- Multiple tests in the same file that each check a nearby sentence in the same template section.
- Duplicated wording checks across README, quickstart, project handbook, and template files unless each file is a separate product surface with distinct user impact.

### Presets and Extensions

Presets and extensions are large test surfaces. Keep the behavior that proves discovery, validation, installation, and failure handling. Delete low-value permutations.

Keep:

- Happy path install/resolve behavior.
- Validation of malformed or unsafe manifests.
- Conflict handling and user-visible diagnostics.
- A minimal set of CLI entrypoint tests.

Delete:

- Exhaustive permutations that validate the same schema rule through many equivalent examples.
- Repeated assertions of file listings where one representative asset tree is enough.
- Edge combinations that do not map to a documented user contract.

### Hooks and Contract Tests

Hook tests are important, but many can be collapsed around distinct failure modes.

Keep:

- Missing artifact, malformed artifact, unsafe state, and clean pass cases.
- One representative git-backed preflight case for each major category.
- CLI JSON payload shape for key hook and team surfaces.

Delete:

- Duplicated error-message variants where the same validation branch is already covered.
- Equivalent fixture setups that only change non-semantic prose.
- Repeated git initialization scenarios when path classification or state validation is the real behavior under test.

### Script and Cross-Shell Tests

Script tests are expensive because they use subprocesses and sometimes git.

Keep:

- One Bash and one PowerShell smoke path for critical scripts when both shells are product-supported.
- Direct unit tests for shared Python/path logic where available.
- A small number of branch/timestamp scenarios proving the documented naming contract.

Delete:

- Cross-product combinations of timestamp, sequential, dry-run, JSON, no-git, and explicit feature directory when they exercise the same parser branch.
- Redundant PowerShell/Bash parity tests after one parity contract proves the shared behavior.

### Codex Team Tests

Codex team has real state-machine risk, so it should be trimmed more carefully than template wording tests.

Keep:

- State model round trips and invalid transition checks.
- Dispatch/result submission failure handling.
- Runtime backend detection smoke.
- Public team CLI/API JSON surfaces.

Delete:

- Repeated tests that differ only by a minor message or metadata field.
- End-to-end dispatch variants when unit-level state transition tests already cover the branch.
- Redundant mocked backend availability combinations that do not alter user-visible behavior.

## File-Level Work Plan

The implementation should proceed in passes:

1. Collect a baseline with `uv run pytest --collect-only -q`.
2. Trim `tests/integrations/**` first, because it is the largest and most redundant family.
3. Trim high-volume template guidance files, especially tests that assert incidental wording.
4. Trim `tests/test_presets.py` and `tests/test_extensions.py` by preserving documented contracts and deleting equivalent permutations.
5. Trim `tests/contract/**`, `tests/hooks/**`, and cross-shell script tests with extra caution.
6. Trim Codex team tests only after the lower-risk deletions have already met most of the reduction target.
7. Re-run collection after each pass and keep a running count of deleted tests by family.

## Acceptance Criteria

The work is complete when:

- `uv run pytest --collect-only -q` reports between 1,200 and 1,600 collected tests, unless a specific higher count is justified by preserved high-risk coverage.
- `uv run pytest -q` passes on the reduced suite.
- At least one representative test remains for each supported integration family and each special integration behavior listed above.
- Packaging asset coverage remains present.
- Hook fail-closed behavior remains covered for missing, malformed, unsafe, and clean states.
- The final summary lists removed test families and the retained contracts that replace them.

## Residual Risks

- Some downstream integration-specific regressions may no longer be caught before release because not every agent receives deep install/render coverage.
- Wording regressions in docs and templates will be less constrained.
- Rare shell-specific branch combinations may move from automated coverage to manual or release-check confidence.

These risks are accepted by the chosen aggressive deletion strategy. The mitigation is to preserve representative samples and high-risk contracts rather than exhaustive combinations.

## Rollback Strategy

Deleted tests should be removed in coherent commits or clearly described file groups so individual families can be restored if a regression escapes. If the reduced suite misses an important bug, add back a targeted contract test for that failure mode rather than restoring broad matrix coverage.
