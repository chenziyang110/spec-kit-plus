# Templates And Generated Surfaces Workflows

**Last Updated:** 2026-04-30
**Coverage Scope:** generated workflow behavior, state handoffs, and cross-module propagation.
**Primary Evidence:** `worker-results/integrations-generated-surfaces.json`, `docs-planning-operations.json`, `project-map-atlas-state.json`
**Update When:** `sp-*` workflow contracts, passive routing skills, script behavior, or generated state templates change.

## Entry Points and Handoffs

- `specify init` installs this module's assets through integration adapters.
- Generated `sp-*` commands/skills are the downstream user entry points.
- Generated scripts support context updates, project-map freshness, and runtime helpers.
- Map/test workflows write durable state under `.specify/project-map/` and `.specify/testing/`.

## Main Flows

### Subagents-First Execution Guidance

Execution-oriented generated workflows teach a leader + subagents model:

- `execution_model: subagents-first`
- `dispatch_shape: one-subagent | parallel-subagents | leader-inline-fallback`
- `execution_surface: native-subagents | managed-team | leader-inline`

`one-subagent` is valid when one bounded delegated lane is safe and packetized.
`parallel-subagents` is used for independent lanes with isolated write sets.
`managed-team` is reserved for durable team state, explicit join-point tracking,
result files, or lifecycle control beyond one in-session subagent burst.
`leader-inline-fallback` is a recorded exception path, not the default execution
shape.

### Template Generation

1. Shared command template is read from `templates/commands/`.
2. Optional partials and integration-specific addenda are applied.
3. Adapter transforms argument placeholders and frontmatter as needed.
4. Files are written to the integration's target directory.
5. Manifest state records generated files.

### Brownfield Atlas

1. `map-scan` produces coverage ledger and scan packets.
2. `map-build` consumes those packets, reads live repository files, writes worker results, synthesizes atlas docs, and records reverse coverage.
3. Freshness completion happens only after canonical atlas files exist.

### Testing System

1. `test` routes to `test-scan` or `test-build`.
2. `test-scan` produces evidence and risk lanes.
3. `test-build` constructs testing artifacts from approved lanes.

## State Transitions

- Template source -> adapter transform -> generated downstream file -> integration manifest.
- Map scan package -> worker results -> atlas docs -> complete-refresh.
- Test scan artifact -> test build plan -> testing contract/playbook.

## Cross-Module Expansion Triggers

- If a template requires new Python helper behavior, read `specify-cli-core`.
- If Codex team prompts or runtime contracts change, read `agent-teams-engine`.
- If packaging changes, inspect `pyproject.toml` force-includes and packaging tests.

## Failure and Recovery Notes

- If generated commands disagree across agents, inspect shared template first, then adapter-specific transforms.
- If Bash and PowerShell scripts diverge, fix both or document why one shell is intentionally different.
- If a generated map-build prompt allows structural-only docs, update prompt guidance and tests together.
