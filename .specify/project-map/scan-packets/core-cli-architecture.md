# MapScanPacket: core-cli-architecture

- lane_id: core-cli-architecture
- mode: read_only
- scope: Python CLI core, command registration, project-map freshness, learning, testing inventory, verification, root packaging metadata.
- ledger_row_ids: L001, L002, L003, L014

## required_reads

- `pyproject.toml`
- `src/specify_cli/__init__.py`
- `src/specify_cli/__main__.py`
- `src/specify_cli/project_map_status.py`
- `src/specify_cli/learnings.py`
- `src/specify_cli/testing_inventory.py`
- `src/specify_cli/verification.py`
- `src/specify_cli/launcher.py`
- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/status.json`

## excluded_paths

- `.venv/**`
- `.pytest_cache/**`
- `.ruff_cache/**`
- `dist/**`

## required_questions

- What is the primary CLI shape and command grouping?
- Which files own the project-map freshness lifecycle?
- Which state surfaces does the CLI read/write?
- Which packaging settings bundle generated assets and runtime assets?
- What changes here require root and module atlas refresh?

## expected_outputs

- CLI capability facts with entry points and owners.
- Project-map freshness state lifecycle and dirty/fresh transitions.
- Packaging and local development invariants.
- Confidence for each accepted fact.

## atlas_targets

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/modules/specify-cli-core/OVERVIEW.md`
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md`

## forbidden_actions

- Do not edit source code.
- Do not infer current behavior from old planning docs without live file evidence.

## result_handoff_path

`.specify/project-map/worker-results/core-cli-architecture.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/test_project_map_status.py tests/test_learning_cli.py tests/test_testing_inventory.py -q`

## blocked_conditions

- CLI entry points cannot be read.
- Project-map status model is missing or does not parse.
