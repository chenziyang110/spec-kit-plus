from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _assert_mandatory_subagent_guidance(content: str) -> None:
    lowered = content.lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lowered
    assert "the leader orchestrates:" in lowered
    assert "before dispatch, every subagent lane needs" in lowered
    assert "task contract" in lowered
    assert "structured handoff" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered


def test_map_scan_and_build_templates_require_mandatory_subagent_guidance() -> None:
    scan_content = _read("templates/commands/map-scan.md").lower()
    build_content = _read("templates/commands/map-build.md").lower()

    _assert_mandatory_subagent_guidance(scan_content)
    _assert_mandatory_subagent_guidance(build_content)

    for content in (scan_content, build_content):
        assert "subagent_blocked" in content
        assert "coverage-ledger.json.open_gaps" in content
        assert "map-state.md" in content
        assert "low_risk_open_gap" in content
        assert "unknown` blocks" in content


def test_map_guidance_documents_schema_v5_alias_and_claim_readiness() -> None:
    scan_content = _read("templates/commands/map-scan.md").lower()
    build_content = _read("templates/commands/map-build.md").lower()
    shared_context = _read("templates/command-partials/common/context-loading-gradient.md").lower()
    planning_context = _read("templates/command-partials/common/planning-context-loading-gradient.md").lower()

    for content in (scan_content, build_content, shared_context, planning_context):
        assert "schema v5" in content
        assert "alias_index" in content
        assert "alias catalog" in content
        assert "normalize user input" in content
        assert "run map-scan -> map-build" in content or "run sp-map-scan -> sp-map-build" in content

    assert "claim_evidence" in build_content
    assert "claim_verifications" in build_content
    assert "claim_transitions" in build_content
    assert "conflicts table" not in build_content
    assert "symbol_index" not in build_content


def test_map_scan_template_defines_complete_scan_package_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = " ".join(content.lower().split())

    assert "sp-map-scan" in content
    assert "sp-map-build" in content
    assert ".specify/project-cognition/workbench/map-scan.md" in content
    assert ".specify/project-cognition/workbench/coverage-ledger.md" in content
    assert ".specify/project-cognition/workbench/coverage-ledger.json" in content
    assert ".specify/project-cognition/workbench/scan-queue.json" in content
    assert ".specify/project-cognition/workbench/handoff-ledger.json" in content
    assert ".specify/project-cognition/workbench/scan-packets/<lane-id>.md" in content
    assert ".specify/project-cognition/workbench/worker-results/<packet-id>.json" in content
    assert ".specify/project-cognition/workbench/map-state.md" in content
    assert "Project Cognition Workbench State Protocol" in content
    assert "MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md" in content
    assert ".specify/project-map/" not in content
    assert "MapScanPacket" in content
    assert "`mode: read_only`" in content
    assert "`result_handoff_path`" in content
    assert "worker checkpoints and result handoffs" in lowered
    assert "worker-results/<packet-id>.json" in content
    assert "worker-results/<lane-id>.json" in content
    assert "full project-relevant inventory" in lowered
    assert "nested directories" in lowered
    assert "scan packets are executable read instructions" in lowered
    assert "not final" in lowered
    assert "atlas evidence" in lowered
    assert "must still execute the packet reads" in lowered
    assert "rg --files" in content
    assert "Git-tracked files" in content
    assert "excluded_from_deep_read" in content
    assert "vendor-cache-build-output" in content
    assert "`unknown` is a scan failure" in content
    assert "`inventory`" in content
    assert "`sampled`" in content
    assert "`deep-read`" in content
    assert "`critical`" in content
    assert "`important`" in content
    assert "`low-risk`" in content
    assert "every project-relevant row is categorized" in lowered
    assert "scan-packets/<lane-id>.md" in content
    assert "Coverage Classification" in content
    assert "Criticality Scoring" in content
    assert "even when freshness is `fresh`" in lowered
    assert "git baseline diff" in lowered
    assert "reference-only" in lowered
    assert "live surface" in lowered
    assert "must not become a scan target" in lowered
    assert "`.specify/**` must never enter the project cognition graph" in content
    assert "passive learning files are workflow guidance, not scan evidence" in lowered
    assert (
        "`.specify/memory/**` must not appear in repository-universe, coverage-ledger, evidence rows, "
        "provisional nodes, provisional edges, observations, path_index, or alias_index"
    ) in content
    assert "`.specify/**` workflow/runtime state is excluded from default source/runtime scan targets" in content
    assert (
        "only read `.specify/**` for workflow operation, validation, migration, or when the requested scan "
        "is explicitly about generated workflow surfaces or spec-kit-plus itself"
    ) in lowered
    assert "specify-runtime cognition validate-scan --format json" in content
    assert "validate-scan" in lowered
    assert "may report complete only after" in lowered
    assert "inspect compact `scan-status`" in lowered
    assert "lease a packet" in lowered
    assert "submit packet-local checkpoints" in lowered
    assert "runtime-owned projections" in lowered
    assert "only runtime commands may change them" in lowered
    assert "accepted_nonblocking_gap_paths" in content
    assert "concrete repository file paths enumerated from `repository-universe.json`" in lowered
    assert "globs such as `jzwinrenew/*.cpp`" in lowered
    assert "directory patterns, absolute paths, and summary labels are invalid" in lowered
    assert "a top-level `coverage.json` or `coverage-ledger.json` row is not proof that a path was scanned" in lowered
    assert "included_paths - assigned_paths - accepted_nonblocking_gap_paths" in content
    assert "accepted packet-local path results" in lowered
    assert "runtime-generated packet-local task ledger and result skeleton" in lowered
    assert "do not reproduce a stable json schema in the prompt" in lowered

    assert "current-runtime native subagents are the default" in lowered
    assert "choose_subagent_dispatch(command_name=\"map-scan\"" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "native-subagents" in lowered
    assert "validated `mapscanpacket`" in lowered
    assert "raw inventory notes or raw chat summaries are not sufficient" in lowered
    assert "structured handoff" in lowered
    assert "idle subagent output" in lowered
    assert "not accepted scan results" in lowered
    assert "must wait for every dispatched scan lane" in lowered

    required_phrases = [
        "project shape and stack",
        "architecture overview",
        "directory ownership",
        "module dependency graph",
        "core code elements",
        "entry and api surfaces",
        "data and state flows",
        "user and maintainer workflows",
        "integrations and protocol boundaries",
        "build, release, and runtime",
        "testing and verification",
        "risk, security, observability, and evolution",
        "template and generated-surface propagation",
        "coverage reverse index",
        "layer 1 retrieval inputs",
    ]

    for phrase in required_phrases:
        assert phrase in lowered

    assert "consequence substrate evidence" in lowered
    assert "active/running actors" in lowered
    assert "shared mutable state and destructive-operation surfaces" in lowered
    assert "minimal live reads" in lowered
    scan_shell = _read("templates/command-partials/map-scan/shell.md")
    scan_shell_lowered = scan_shell.lower()
    assert ".cognitionignore" in content
    assert ".cognitionignore" in scan_shell
    assert "specify-runtime cognition generate-ignore --format json" in content
    assert "specify-runtime cognition generate-ignore --format json" in scan_shell
    assert "specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json" in content
    assert "specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json" in scan_shell
    assert "default stdout is compact json" in scan_shell_lowered
    assert "handoff file is a temporary agent-facing scan-set containing only `files`" in scan_shell_lowered
    assert "review `.specify/project-cognition/.cognitionignore`" in scan_shell_lowered
    assert "wait for confirmation" in scan_shell_lowered
    assert "passive learning files as read-only workflow guidance, not scan evidence" in scan_shell_lowered
    assert "`.specify/**` is workflow/runtime state, not project graph evidence" in scan_shell
    assert "must not become scan targets or graph paths" in scan_shell_lowered


def test_passive_subagent_guidance_uses_path_level_gap_outcomes() -> None:
    content = _read("templates/passive-skills/subagent-driven-development/SKILL.md")
    lowered = content.lower()

    assert "evidence lanes" in lowered
    assert "acceptance=fail_gap" in lowered
    assert 'coverage[].outcome="overflow"' in lowered
    assert "return `overflow` or `blocked`" not in lowered
    assert "returns `overflow` or `blocked`" not in lowered


def test_map_build_template_refuses_incomplete_scan_packages() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "sp-map-build" in content
    assert "sp-map-scan" in content
    assert "coverage-ledger.json" in content
    assert ".specify/project-cognition/workbench/scan-queue.json" in content
    assert ".specify/project-cognition/workbench/handoff-ledger.json" in content
    assert "scan-packets" in content
    assert "begins with validation, not writing" in lowered
    assert "must not guess and continue" in lowered
    assert "Project Cognition Workbench State Protocol" in content
    assert "Validate Scan Inputs Before Execution" in content
    assert "Compile And Validate MapBuildPacket Inputs" in content
    assert "do not rebuild the scan from chat memory" in lowered
    assert "coverage-ledger.json` as the machine-readable row source" in content
    assert "MapBuildPacket" in content
    assert "raw scan prose or raw Markdown checklist items alone" in content
    assert ".specify/project-cognition/workbench/worker-results/<packet-id>.json" in content
    assert "scan gap report" in lowered
    assert "packet results without paths read" in lowered
    assert "packet results that only summarize without evidence" in lowered
    assert "unresolved critical rows" in lowered
    assert "not a scaffold, migration, or file-moving command" in lowered
    assert "inputs, not evidence" in lowered or "inputs, not" in lowered
    assert "packet evidence intake" in lowered
    assert "structural-only refresh is a failed build" in lowered
    assert "reverse coverage validation" in lowered
    assert "specify-runtime cognition build-from-scan --format json" in content
    assert "specify-runtime cognition publish-runtime-metadata --format json" not in content
    assert "specify-runtime cognition complete-refresh --format json" not in content
    assert "specify-runtime cognition validate-build --format json" in content
    assert "validate-build" in lowered
    assert "path_index_to_included_ratio" in content
    assert "accepted_nonblocking_gap_paths" in content
    assert "must not set `freshness=fresh`" in lowered
    assert "must not set `readiness=query_ready`" in lowered
    assert "must not set `graph_ready=true`" in lowered
    assert "Freshness=ready" not in content
    assert "manual sql" in lowered
    assert "hand-picked node subsets" in lowered
    assert "build-from-scan" in lowered
    assert "identity reconciliation" in lowered
    assert "DEBUG-HANDBOOK.md" not in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/" not in content
    assert "derived-only evidence" in lowered
    assert "required_reads contain only reference-only" in lowered or "reference-only or hard-excluded" in lowered
    assert "`.specify/**` inputs are workbench/control artifacts, not graph evidence rows" in content
    assert "must not write `.specify/**` into `evidence.source_path`, `path_index.path`" in content
    assert ".cognitionignore" in content
    assert "must reject `.cognitionignore`-excluded paths" in content
    assert "must not write `.cognitionignore`-excluded paths" in content
    build_shell = _read("templates/command-partials/map-build/shell.md")
    assert ".cognitionignore" in build_shell

    required_phrases = [
        "every `critical` row is covered by active runtime path and route indexes",
        "every `important` row is reachable through active runtime path and route indexes",
        "every scan packet is consumed",
        "every accepted packet result has paths read and confidence",
        "every runtime node, edge, observation, path row, and alias row is backed by accepted packet evidence",
        "query bundle and route reachability are validated through runtime query surfaces",
        "no final report claims success for a structural-only refresh",
        "`map_state_file` records accepted packet results",
        "owner, consumer, change propagation, and verification",
        "known unknowns",
        "known-unknowns",
        "excluded bucket has a reason and revisit condition",
        "every critical shared surface can be discovered through runtime query surfaces",
        "every key verification entry point can be located through runtime query surfaces",
    ]

    for phrase in required_phrases:
        assert phrase in lowered
    assert "final handbook target" not in lowered
    assert "workflow-operational reachability validation" in lowered


def test_map_build_exposes_deterministic_proposal_compilation_gate() -> None:
    build = _read("templates/commands/map-build.md")
    shell = _read("templates/command-partials/map-build/shell.md")
    required = [
        "deterministic cognition proposal compiler",
        "before any graph-store mutation",
        "compilation.publication_allowed=false",
        "route candidates rather than repository facts",
    ]
    for phrase in required:
        assert phrase in build
        assert phrase in shell

    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        content = _read(path)
        assert "deterministic cognition proposal compiler" in content
        assert "before sqlite publication" in content.lower()


def test_map_workflow_templates_require_project_concept_lexicon_signals() -> None:
    scan_content = _read("templates/commands/map-scan.md")
    build_content = _read("templates/commands/map-build.md")
    update_content = _read("templates/commands/map-update.md")

    scan_lowered = scan_content.lower()
    build_lowered = build_content.lower()
    update_lowered = update_content.lower()

    assert "Concept Retrieval Signal Evidence" in scan_content
    assert "concept retrieval signals" in scan_lowered
    assert "colloquial user phrases" in scan_lowered
    assert "domain ownership evidence" in scan_lowered

    assert "query_examples" in build_content
    assert "not current readiness requirements" in build_lowered
    assert "concept_candidates" in build_content
    assert "route_pack" in build_content
    assert "graph truth projection" in build_lowered
    assert "evidence-backed route rows" in build_lowered

    assert "patch-in-active-generation" in update_content
    assert "stale retrieval signals" in update_lowered
    assert "selected_concepts" in update_content
    assert ".cognitionignore" in update_content
    assert "filter changed paths through `.cognitionignore`" in update_lowered
    assert "user-supplied changed paths that match `.cognitionignore`" in update_lowered
    assert "minimal_live_reads" in update_content


def test_map_scan_template_requires_truth_layer_ledgers() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert ".specify/project-cognition/workbench/repository-universe.json" in content
    assert ".specify/project-cognition/workbench/capability-ledger.json" in content
    assert ".specify/project-cognition/workbench/control-ledger.json" in content
    assert "file, entrypoint, branch, and control-node coverage" in lowered
    assert "by capability" in lowered
    assert "by symptom" in lowered
    assert "generate layer 1 retrieval source material" in lowered
    assert "task route candidates" in lowered
    assert "symptom route candidates" in lowered
    assert "shared-surface hotspot candidates" in lowered
    assert "verification route candidates" in lowered
    assert "propagation-risk route candidates" in lowered


def test_map_build_template_requires_truth_layer_outputs() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert ".specify/project-cognition/project-cognition.db" in content
    assert "queryable task-oriented cognition bundles" in lowered
    assert "consequence substrate synthesis" in lowered
    assert "lifecycle/state edges" in lowered
    assert "shared-state and destructive-operation edges" in lowered
    assert "minimal_live_reads" in content
    assert "which owners, consumers, state surfaces, generated surfaces, and verification routes are implicated" in lowered
    assert "DEBUG-HANDBOOK.md" not in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "DEBUG-WORKFLOW-CONTRACT" not in content
    assert "BUILD-WORKFLOW-CONTRACT" not in content


def test_map_scan_template_requires_canonical_boundary_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = " ".join(content.lower().split())

    assert "runtime-resolved scan set" in lowered
    assert "do not let the agent freely decide which files to omit" in lowered
    assert "canonical boundary artifact" in lowered
    assert "`.specify/project-cognition/workbench/repository-universe.json`" in content
    assert ".specify/project-cognition/tmp/scan-files.json" in content
    assert "`schema_version`" in content
    assert "`candidate_universe`" in content
    assert "`decision_source`" in content
    assert "`assigned_paths`" in content
    assert "`deep_read`" in content
    assert "`inventory_only`" in content
    assert "disposition is separate from criticality" in lowered
    assert "`criticality`" in content
    assert "excluded paths must not appear in graph-facing `coverage.json` rows" in lowered
    assert "capacity-exhausted" in lowered
    assert "assigned_paths`, queue rows, worker path results, and worker coverage paths" in content
    assert "concrete repository file paths enumerated from `repository-universe.json`" in lowered
    assert "a top-level `coverage.json` or `coverage-ledger.json` row is not proof" in lowered


def test_map_scan_template_requires_packet_ledger_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "runtime-generated packet-local task ledger" in lowered
    assert "paths_read" in content
    assert "non-empty set of concrete completed path results" in lowered
    assert "path outcomes and confidence" in lowered
    assert "paths_read: true" in lowered
    assert "boolean read flags are invalid" in lowered
    assert "existing `evidence_ids`" in lowered
    assert "source_path" in lowered
    assert "accepted packet-local path results" in lowered
    assert "rejected or incomplete attempt blocks packet acceptance" in lowered
    assert "worker results without a matching scan packet are invalid" in lowered
    assert "coverage gate" in lowered
    assert "quality gate" in lowered
    assert "fail_gap" in lowered
    assert "fail_quality" in lowered
    assert "fail_contract" in lowered
    assert "fail_systemic" in lowered
    assert "sampled and inventory_only are not free-form" in lowered
    assert "repository-universe.json" in content
    assert "disposition and criticality together justify" in lowered


def test_map_scan_template_uses_runtime_owned_context_budgeted_dispatch() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = " ".join(content.lower().split())

    for command in (
        "specify-runtime cognition scan-set",
        "specify-runtime cognition scan-prepare",
        "specify-runtime cognition scan-lease",
        "specify-runtime cognition scan-checkpoint",
        "specify-runtime cognition scan-yield",
        "scan-requeue",
        "specify-runtime cognition scan-accept",
        "specify-runtime cognition scan-status",
        "specify-runtime cognition validate-scan",
    ):
        assert command in content

    assert "effective worker context budget" in lowered
    assert "estimated token cost" in lowered
    assert "path count and byte limits are secondary guards" in lowered
    assert "cli-generated self-contained task brief" in lowered
    assert "minimum inherited conversation context" in lowered
    assert "assigned paths minus runtime-accepted terminal paths" in lowered
    assert "dispatch a new subagent for the remaining paths" in lowered
    assert "--worker-capacity-tokens" in content
    assert "active packet and attempt identifiers returned by `scan-status`" in lowered
    assert "natural-language completion claims" in lowered
    assert "only the runtime" in lowered
    assert "global queue, handoff, coverage, evidence, provisional, and status artifacts" in lowered
    assert "must not hand-write" in lowered
    assert "sqlite" in lowered


def test_map_scan_worker_prompt_is_checkpointed_and_packet_local() -> None:
    scan_command = _read("templates/commands/map-scan.md")
    content = _read("templates/worker-prompts/map-scan-worker.md")
    lowered = " ".join(content.lower().split())

    assert ".specify/templates/worker-prompts/map-scan-worker.md" in scan_command
    assert "cli-generated self-contained task brief" in lowered
    assert "minimum inherited conversation context" in lowered
    assert "assigned_paths" in content
    assert "effective context budget" in lowered
    assert "scan-checkpoint" in content
    assert "scan-yield" in content
    assert "before context, tool-output, or result-output capacity is exhausted" in lowered
    assert "packet-local" in lowered
    assert "global queue" in lowered
    assert "status.json" in content
    assert "project-cognition.db" in content
    assert "natural-language summary is not acceptance evidence" in lowered
    assert "the runtime computes the authoritative remaining set" in lowered
    assert "keep worker-authored `acceptance` at `partial`" in lowered
    assert "runtime derives `pass`" in lowered


def test_map_scan_and_build_require_a_receipt_bound_v2_handoff() -> None:
    scan = _read("templates/commands/map-scan.md").lower()
    build = _read("templates/commands/map-build.md").lower()
    spx_scan = _read(
        "templates/advanced-skills/spx-map-scan/references/scan-gates.md"
    ).lower()
    spx_build = _read("templates/advanced-skills/spx-map-build/SKILL.md").lower()

    for content in (scan, build, spx_scan, spx_build):
        assert "scan-receipt.json" in content
        assert "v2" in content
    assert "any later canonical mutation" in scan
    assert "current source-file bytes" in scan
    assert "absent or digest-mismatched" in build


def test_map_scan_template_defines_machine_readable_scan_artifact_schema() -> None:
    content = _read("templates/commands/map-scan.md")

    assert "Machine-Readable Scan Artifact Schema" in content
    assert "nodes.json" in content
    assert "`id`" in content
    assert "`type`" in content
    assert "`title`" in content
    assert "`paths`" in content
    assert "`attrs`" in content
    assert "`kind`" in content
    assert "`label`" in content
    assert "`attrs_json`" in content
    assert "build-from-scan creates path_index rows only from nodes[].paths" in content
    assert "coverage.json does not create path_index rows by itself" in content
    assert "source_node_id" in content
    assert "target_node_id" in content
    assert "observations.json" in content
    assert "string observations are accepted only as compatibility input" in content
    assert "do not maintain separate `rows` and" in content
    assert "`coverage` lists that can drift" in content


def test_map_build_template_rejects_incomplete_boundary_coverage() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "repository-universe.json" in content
    assert "every included path is represented in scan coverage or an accepted gap" in lowered
    assert "excluded paths are represented only by the boundary artifact" in lowered
    assert "not by graph-facing coverage rows" in lowered
    assert "scan gap report" in lowered


def test_map_build_template_routes_back_on_contract_and_systemic_failures() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "repository-universe.json" in content
    assert "scan gap report" in lowered
    assert "contract" in lowered
    assert "systemic" in lowered
    assert "paths_read" in content
    assert "non-empty array of concrete paths" in lowered
    assert "different `source_path`" in lowered
    assert "orphan packet results" in lowered
    assert "non-`pass` packet outcomes" in lowered
    assert "not `true`" in lowered
    assert "not only a local patch" in lowered or "not local patch" in lowered


def test_map_build_template_explains_path_index_source_contract() -> None:
    content = _read("templates/commands/map-build.md")

    assert "Path Index Source Contract" in content
    assert "build-from-scan creates DB path_index rows from nodes.json `paths`" in content
    assert "does not read `attrs_json.path`" in content
    assert "coverage.json rows without matching node paths are recorded as rejected coverage" in content
    assert "active_generation_has_no_path_index_rows" in content


def test_map_update_template_requires_changed_path_accounting() -> None:
    content = _read("templates/commands/map-update.md")
    lowered = content.lower()

    assert "every changed path must be accounted for" in lowered
    assert "ignored with reason" in lowered
    assert "partial with `minimal_live_reads`" in lowered
    assert "provisional `path_index` and `alias_index` coverage" in lowered
    assert "future `specify-runtime cognition compass` and alias-catalog routing" in lowered
    assert "must not write `.cognitionignore`-excluded paths into update records" in lowered
    assert "reserved rebuild reason" in lowered


def test_map_update_template_uses_git_native_changes_and_finalizers() -> None:
    content = _read("templates/commands/map-update.md")
    lowered = content.lower()

    assert "specify-runtime cognition changes --format json" in content
    assert "consume `next_action`" in lowered
    assert "feed `changes[].path`" in lowered
    assert "use the returned `result_state`" in lowered
    assert "must not call `complete-refresh` when `result_state` is `partial_refresh`" in lowered
    assert "specify-runtime cognition complete-refresh --format json" in content
    assert "specify-runtime cognition record-refresh --reason \"map-update\" --format json" in content
