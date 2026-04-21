# Codebase Concerns

**Analysis Date:** 2026-04-11

## Tech Debt

**Monolithic CLI entrypoint:**
- Issue: `src/specify_cli/__init__.py` concentrates CLI wiring, project initialization, integration install/switch flows, preset flows, release-adjacent helpers, and Codex team runtime commands in one 3.5k+ line module.
- Files: `src/specify_cli/__init__.py`
- Impact: Small changes have a wide blast radius, review is slow, and rollback behavior is harder to reason about because unrelated responsibilities share state and helper functions.
- Fix approach: Split command groups into focused modules such as `cli_init.py`, `cli_integrations.py`, `cli_presets.py`, and `cli_team.py`, then keep `src/specify_cli/__init__.py` as registration glue only.

**Parallel implementations for extensions and presets:**
- Issue: `src/specify_cli/extensions.py` and `src/specify_cli/presets.py` repeat similar catalog, ZIP-install, manifest, command/skill materialization, and cleanup logic instead of sharing a common package-management layer.
- Files: `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`
- Impact: Fixes to safety checks, rollback, or packaging behavior are easy to land in one path and miss in the other. This is already visible in how ZIP handling differs across modules.
- Fix approach: Extract shared install/uninstall primitives and shared ZIP validation into a common package manager module used by both features.

**Agent-context update logic is heavily duplicated:**
- Issue: The repo maintains a large shared Bash/PowerShell implementation plus many thin per-integration wrappers that delegate to it.
- Files: `scripts/bash/update-agent-context.sh`, `scripts/powershell/update-agent-context.ps1`, `src/specify_cli/integrations/*/scripts/update-context.sh`, `src/specify_cli/integrations/*/scripts/update-context.ps1`
- Impact: Adding or changing agent support requires edits in many places, which increases drift risk and raises the maintenance cost of every new integration.
- Fix approach: Generate thin wrappers from registry metadata or move all routing into a single script that reads integration metadata instead of hard-coding cases.

## Known Bugs

**Extension upgrade path validates ZIP contents inconsistently:**
- Symptoms: Extension install paths in `src/specify_cli/extensions.py` and `src/specify_cli/presets.py` validate archive member paths before extraction, but the upgrade logic in `src/specify_cli/__init__.py` opens `extension.yml` from the ZIP without the same shared validation flow.
- Files: `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, `src/specify_cli/__init__.py`
- Trigger: Running extension upgrade code that processes a downloaded ZIP through the CLI path in `src/specify_cli/__init__.py`.
- Workaround: Prefer the manager install flows in `src/specify_cli/extensions.py` until the CLI upgrade path reuses the same validated extraction routine.

## Security Considerations

**Archive handling safety is not centralized:**
- Risk: ZIP safety checks exist, but they are implemented separately in multiple places. That creates a real chance that one future path skips containment checks or handles nested archives differently.
- Files: `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, `src/specify_cli/__init__.py`
- Current mitigation: `src/specify_cli/extensions.py` and `src/specify_cli/presets.py` validate archive member paths before calling `extractall`.
- Recommendations: Move ZIP inspection and extraction into one helper and require every extension/preset/upgrade code path to use it.

**Broad exception swallowing can hide safety-relevant failures:**
- Risk: Several flows intentionally continue after `except Exception` or `pass`, especially around cleanup, preset installation, cache parsing, hook evaluation, and rollout rollback paths.
- Files: `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, `scripts/bash/common.sh`
- Current mitigation: Some paths print warnings before continuing.
- Recommendations: Replace broad catches with narrower exception types, emit structured warnings with the affected operation, and test the failure paths explicitly.

**Shell and script surface is under-verified in CI:**
- Risk: Critical behavior lives in shell and PowerShell scripts, but CI mainly enforces Markdown lint and Python `ruff` on `src/`. Script regressions and quoting bugs can ship unnoticed.
- Files: `.github/workflows/lint.yml`, `.github/workflows/test.yml`, `scripts/bash/*.sh`, `scripts/powershell/*.ps1`
- Current mitigation: Some behavior is covered indirectly by Python tests and manual testing guidance in `TESTING.md`.
- Recommendations: Add `shellcheck` for `scripts/bash/*.sh`, a PowerShell syntax/lint job for `scripts/powershell/*.ps1`, and broaden Python lint coverage beyond `src/`.

## Performance Bottlenecks

**Large command modules increase edit and test cost:**
- Problem: `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, and `src/specify_cli/presets.py` are all large enough that most changes require loading and mentally parsing hundreds of unrelated lines.
- Files: `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`, `tests/test_extensions.py`, `tests/test_presets.py`
- Cause: Features have accumulated in-place rather than being broken into smaller units with isolated tests.
- Improvement path: Extract feature-local modules and replace giant end-to-end test files with focused suites around smaller public APIs.

**Catalog and package logic remains mostly synchronous:**
- Problem: Network catalog fetch, archive reads, and filesystem copy/remove operations are mostly serialized and implemented inline.
- Files: `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`
- Cause: The current manager design mixes I/O, validation, and rendering in the same call stack.
- Improvement path: Separate pure validation from I/O and make catalog refresh/install phases easier to cache, batch, and test independently.

## Fragile Areas

**Integration install/switch rollback paths:**
- Files: `src/specify_cli/__init__.py`, `src/specify_cli/integrations/base.py`, `src/specify_cli/integrations/manifest.py`
- Why fragile: Setup, teardown, manifest tracking, file copying, and integration metadata updates span several layers. Errors during partial setup rely on best-effort rollback and warning-only logging.
- Safe modification: Change manifest semantics and teardown logic together, then run integration install/switch tests before merging.
- Test coverage: There is strong happy-path coverage in `tests/integrations/`, but rollback and partial-failure coverage is thinner than the main setup surface.

**Codex team runtime backend support:**
- Files: `src/specify_cli/codex_team/runtime_bridge.py`, `src/specify_cli/codex_team/tmux_backend.py`, `src/specify_cli/codex_team/worker_bootstrap.py`, `tests/codex_team/test_tmux_smoke.py`
- Why fragile: Runtime support depends on environment detection, tmux/psmux availability, path handling, and generated worker instructions. Most tests use monkeypatched backends rather than real process orchestration.
- Safe modification: Keep state-format changes, backend detection changes, and CLI messaging changes in separate commits and verify behavior in an actual tmux-compatible environment.
- Test coverage: Unit coverage is present, but real backend integration coverage is minimal.

**Agent support expansion workflow:**
- Files: `AGENTS.md`, `src/specify_cli/integrations/__init__.py`, `src/specify_cli/__init__.py`, `.github/workflows/scripts/create-release-packages.sh`, `scripts/bash/update-agent-context.sh`, `scripts/powershell/update-agent-context.ps1`
- Why fragile: New agent support requires coordinated changes across docs, registry/config, packaging scripts, tests, and context update scripts.
- Safe modification: Use `tests/test_agent_config_consistency.py` as a gate and avoid landing agent additions without packaging and context-script verification.
- Test coverage: Consistency tests exist, but the workflow still depends on many manually synchronized files.

## Scaling Limits

**Agent matrix growth:**
- Current capacity: The repository already supports a large agent/integration matrix with per-agent wrappers, release packaging rules, and tests.
- Limit: Each new agent increases duplicated script paths, release artifacts, and consistency maintenance work faster than the core abstractions shrink it.
- Scaling path: Drive more generation from `INTEGRATION_REGISTRY` and reduce handwritten per-agent packaging/context logic.

**Single-file command surface:**
- Current capacity: Core CLI behavior remains manageable because contributors can still find logic in one place.
- Limit: As more features land in `src/specify_cli/__init__.py`, onboarding and safe review will continue to slow down.
- Scaling path: Split by command domain and expose smaller, typed public interfaces for tests and future contributors.

## Dependencies at Risk

**Runtime dependence on external terminal multiplexers:**
- Risk: Codex team mode depends on `tmux` or `psmux`, which are not Python dependencies and vary by platform.
- Impact: Team-mode features degrade from available to unusable based on local environment rather than package install success.
- Migration plan: Keep the current backend abstraction in `src/specify_cli/codex_team/tmux_backend.py`, but add stronger environment diagnostics and a clearer non-tmux fallback story before expanding the feature set.

## Missing Critical Features

**No centralized failure telemetry or debug artifact capture:**
- Problem: CLI flows print warnings/errors, but failure analysis depends on terminal output and manual reproduction.
- Blocks: Fast diagnosis of customer-reported install, integration, preset, or runtime failures.
- Files: `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`

**No uniform static analysis policy for non-Python assets:**
- Problem: Bash, PowerShell, and generated command-template surfaces are important product code but lack equivalent automated linting gates.
- Blocks: Confident refactors of scaffolding and cross-platform script behavior.
- Files: `.github/workflows/lint.yml`, `.github/workflows/test.yml`, `scripts/bash/*.sh`, `scripts/powershell/*.ps1`, `templates/commands/*.md`

## Test Coverage Gaps

**Rollback and cleanup failure paths:**
- What's not tested: Failure during integration/preset setup followed by partial rollback, cleanup failures, and recovery from corrupted on-disk state.
- Files: `src/specify_cli/__init__.py`, `src/specify_cli/extensions.py`, `src/specify_cli/presets.py`
- Risk: Users can be left with partially installed state that is hard to diagnose or recover from.
- Priority: High

**Real script execution coverage for cross-platform helpers:**
- What's not tested: Full end-to-end behavior of `scripts/bash/update-agent-context.sh` and `scripts/powershell/update-agent-context.ps1` across representative environments.
- Files: `scripts/bash/update-agent-context.sh`, `scripts/powershell/update-agent-context.ps1`
- Risk: Agent-context updates may drift or fail on a platform-specific edge case without CI catching it.
- Priority: High

**Real runtime backend orchestration:**
- What's not tested: Launching actual `tmux`/`psmux`-backed team sessions instead of mocked backend discovery.
- Files: `src/specify_cli/codex_team/runtime_bridge.py`, `src/specify_cli/codex_team/tmux_backend.py`, `tests/codex_team/test_tmux_smoke.py`
- Risk: The runtime abstraction can pass unit tests while still failing in the real shell environment it targets.
- Priority: Medium

---

*Concerns audit: 2026-04-11*
