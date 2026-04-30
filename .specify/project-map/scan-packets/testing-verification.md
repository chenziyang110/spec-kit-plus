# MapScanPacket: testing-verification

- lane_id: testing-verification
- mode: read_only
- scope: Python test matrix, engine build/test routes, packaging and template verification entry points.
- ledger_row_ids: L011, L012, L016

## required_reads

- `pyproject.toml`
- `tests/**`
- `extensions/agent-teams/engine/package.json`
- `extensions/agent-teams/engine/src/**/__tests__/**`
- `extensions/agent-teams/engine/tests/**`
- `extensions/agent-teams/engine/crates/**/tests/**`
- `README.md`
- `PROJECT-HANDBOOK.md`

## excluded_paths

- `.pytest_cache/**`
- `.ruff_cache/**`
- `.venv/**`
- `.worktrees/**`
- `dist/**`
- `.tmp-*`

## required_questions

- What are the smallest trustworthy verification commands by change surface?
- Which tests lock template guidance, integration generation, project-map freshness, hooks, execution, orchestration, and Codex runtime?
- Which engine checks are separate from Python pytest?
- Which generated/cached outputs are inventory-only?

## expected_outputs

- Verification entry-point matrix.
- Test-layer ownership and regression-sensitive areas.
- Excluded output/cache buckets with revisit conditions.

## atlas_targets

- `.specify/project-map/root/TESTING.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/root/STRUCTURE.md`
- `.specify/project-map/modules/specify-cli-core/TESTING.md`
- `.specify/project-map/modules/agent-teams-engine/TESTING.md`
- `.specify/project-map/modules/templates-generated-surfaces/TESTING.md`

## forbidden_actions

- Do not mutate tests during packet execution.
- Do not treat cache or generated output as source truth.

## result_handoff_path

`.specify/project-map/worker-results/testing-verification.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/test_map_scan_build_template_guidance.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`
- `pytest -q`
- `npm --prefix extensions/agent-teams/engine run build`

## blocked_conditions

- Python test layout or engine package scripts cannot be read.
