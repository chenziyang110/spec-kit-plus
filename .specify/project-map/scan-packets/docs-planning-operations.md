# MapScanPacket: docs-planning-operations

- lane_id: docs-planning-operations
- mode: read_only
- scope: README, docs, planning state, historical milestone artifacts, extension/preset docs, release docs, operator guidance.
- ledger_row_ids: L013, L014, L015

## required_reads

- `README.md`
- `docs/**`
- `.planning/PROJECT.md`
- `.planning/STATE.md`
- `.planning/ROADMAP.md`
- `.planning/MILESTONES.md`
- `.planning/milestones/**`
- `.planning/phases/**`
- `docs/superpowers/specs/2026-04-29-map-scan-build-design.md`
- `docs/superpowers/plans/2026-04-29-map-scan-build-implementation.md`
- `extensions/README.md`
- `extensions/EXTENSION-*.md`
- `presets/README.md`
- `presets/ARCHITECTURE.md`
- `.github/workflows/RELEASE-PROCESS.md`

## excluded_paths

- generated logs
- caches

## required_questions

- What does user-facing guidance teach as current mainline?
- What milestone/planning state is current versus historical?
- Which docs are operational inputs for install, upgrade, extension, preset, and release workflows?
- Which historical planning artifacts should be summarized but not treated as current source of truth?

## expected_outputs

- Documentation and planning-state facts.
- Current/archived milestone interpretation.
- Operations and release guidance facts.

## atlas_targets

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/root/INTEGRATIONS.md`
- `.specify/project-map/root/CONVENTIONS.md`

## forbidden_actions

- Do not promote old planning artifacts to current status unless `.planning/STATE.md` supports it.
- Do not rewrite docs during evidence collection.

## result_handoff_path

`.specify/project-map/worker-results/docs-planning-operations.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/test_specify_guidance_docs.py tests/test_runtime_story_docs.py tests/test_packaging_assets.py -q`

## blocked_conditions

- README or planning state cannot be read.
