# MapScanPacket: project-map-atlas-state

- lane_id: project-map-atlas-state
- mode: read_only
- scope: AGENTS rules, existing handbook, project-map state/templates, memory files, atlas freshness scripts and expectations.
- ledger_row_ids: L003, L005, L013, L014

## required_reads

- `AGENTS.md`
- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/status.json`
- `.specify/project-map/status.json`
- `.specify/memory/project-rules.md`
- `.specify/memory/project-learnings.md`
- `templates/project-handbook-template.md`
- `templates/project-map/**`
- `templates/commands/map-scan.md`
- `templates/commands/map-build.md`
- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/project-map-freshness.ps1`
- `tests/test_project_handbook_templates.py`
- `tests/test_project_map_layered_contract.py`
- `tests/test_project_map_status.py`

## excluded_paths

- project-map worker-results generated after this packet starts

## required_questions

- What atlas structure is canonical?
- What made the current atlas stale?
- Which files must exist before complete-refresh can mark the map fresh?
- Which AGENTS rules govern future atlas refreshes?

## expected_outputs

- Canonical atlas shape and freshness facts.
- AGENTS and memory constraints.
- Reverse coverage validation inputs.

## atlas_targets

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/CONVENTIONS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/index/status.json`

## forbidden_actions

- Do not mark project-map fresh before final atlas files exist and reverse coverage is proven.
- Do not drop content outside managed AGENTS blocks.

## result_handoff_path

`.specify/project-map/worker-results/project-map-atlas-state.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py -q`

## blocked_conditions

- Project-map templates or status files cannot be read.
