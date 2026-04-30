# MapScanPacket: hooks-execution-orchestration

- lane_id: hooks-execution-orchestration
- mode: read_only
- scope: execution packet/result contracts, hook engine, project-map hooks, learning hooks, orchestration policy/state/review-loop helpers.
- ledger_row_ids: L003, L007, L008

## required_reads

- `src/specify_cli/execution/**`
- `src/specify_cli/hooks/**`
- `src/specify_cli/orchestration/**`
- `tests/execution/**`
- `tests/hooks/**`
- `tests/orchestration/**`
- `src/specify_cli/project_map_status.py`

## excluded_paths

- cache directories

## required_questions

- What is the worker packet contract and result handoff contract?
- Which hooks enforce workflow, artifact, project-map, learning, read-path, prompt, and commit rules?
- How does shared strategy selection choose `single-lane`, `native-multi-agent`, or `sidecar-runtime`?
- What state files and event logs are used by orchestration?

## expected_outputs

- Packet/result contract facts.
- Hook event categories and validation boundaries.
- Orchestration strategy, state, and join-point facts.
- Verification commands and failure modes.

## atlas_targets

- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/root/OPERATIONS.md`
- `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md`
- `.specify/project-map/modules/specify-cli-core/TESTING.md`

## forbidden_actions

- Do not mutate runtime state during read-only packet execution.
- Do not treat hook guidance as enforced if the implementation only exposes helper commands.

## result_handoff_path

`.specify/project-map/worker-results/hooks-execution-orchestration.json`

## join_points

- before final atlas writing
- before reverse coverage validation

## minimum_verification

- `pytest tests/execution tests/hooks tests/orchestration -q`

## blocked_conditions

- Packet schema or hook engine files are unreadable.
- Strategy selection cannot be tied to source code.
