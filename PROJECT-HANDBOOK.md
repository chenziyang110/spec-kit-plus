Graph claims are indexed assertions. Their lifecycle is `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale`; even `verified_in_graph_generation` is scoped to the active graph generation and is not current repository truth. Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; bounded live evidence, matching workflow verification, and explicit final-claim authorization remain separate requirements.

Schema v5 adds revision-bound, expiring reconciliation to the auditable live feedback loop and current evidence basis while preserving superseded claim evidence as history. Decisive claim-specific bounded reads provide an in-memory semantic intent to `specify-runtime cognition claim-reconcile prepare --input-json '<intent-json>' --format json`; never create an intent file. The runtime owns every integrity field and returns a prepared packet path plus structured `apply_argv`. Execute that argv through `specify-runtime cognition claim-reconcile apply --input <prepared_packet_path> --format json`, then rerun Compass once on ready. This remains route-candidate evidence and cannot authorize a workflow final claim. Schema v5 does not migrate schema v4 or older databases.

## Scenario-first E2E ownership

Classic `sp-e2e` and Advanced `spx-e2e` share a scenario-first, platform-neutral
test-analysis and execution contract. They own only scoped test plans, fixtures,
executable tests, adapters and harness configuration; product fixes, feature
state and acceptance stay with their existing owners. Visual client execution
is first-class and does not require a browser runner. External-event/checkpoint
pairs, boundary values and independent durable-effect oracles remain explicit;
missing tools cannot remove a scenario from the denominator.

`e2e_scenarios.py`, `e2e_coverage.py` and the optional native runner are ordinary
test-asset helpers, not Python workflow-state writers. Retained test-asset changes
use canonical `sp-e2e` cognition closeout and Learning through shared runtime
contracts. See [desktop validation](docs/sp-e2e-desktop-sample.md) and
[remaining readiness gates](plans/sp-e2e-readiness.md).

## System Boundaries

This repository owns the human/operator `specify` CLI, the agent-facing `specify-runtime` CLI, bundled templates/scripts, supported-agent integration adapters, project-map compatibility/export templates, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

The Python bootstrap in `src/specify_cli/specify_runtime.py` and both standalone
installers default to public `chenziyang110/spec-kit-plus-releases` assets;
the Python CLI source remains in `chenziyang110/spec-kit-plus`. Python retains
authenticated GitHub CLI/API recovery. The API path uses
existing environment or repository-scoped Git credentials without prompts,
checks asset size/digest, and strips authentication on HTTPS redirects. Mirrors
require explicit configuration. All integrations and both workflow profiles
share this bootstrap and the unchanged runtime capability/provenance checks;
an unreleased CLI contract may still require a cached bundled-source build.
