from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _assert_mandatory_subagent_guidance(content: str) -> None:
    lowered = content.lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lowered
    assert "the leader orchestrates:" in lowered
    assert "before dispatch, every subagent lane needs a task contract" in lowered
    assert "structured handoff" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered


def test_map_scan_and_build_templates_require_mandatory_subagent_guidance() -> None:
    _assert_mandatory_subagent_guidance(_read("templates/commands/map-scan.md"))
    _assert_mandatory_subagent_guidance(_read("templates/commands/map-build.md"))


def test_map_scan_template_defines_complete_scan_package_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "sp-map-scan" in content
    assert "sp-map-build" in content
    assert ".specify/project-cognition/workbench/map-scan.md" in content
    assert ".specify/project-cognition/workbench/coverage-ledger.md" in content
    assert ".specify/project-cognition/workbench/coverage-ledger.json" in content
    assert ".specify/project-cognition/workbench/scan-packets/<lane-id>.md" in content
    assert ".specify/project-cognition/workbench/map-state.md" in content
    assert "Project Cognition Workbench State Protocol" in content
    assert "MAP_STATE_FILE=.specify/project-cognition/workbench/map-state.md" in content
    assert ".specify/project-map/" not in content
    assert "MapScanPacket" in content
    assert "`mode: read_only`" in content
    assert "`result_handoff_path`" in content
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
        "provisional nodes, provisional edges, observations, path_index, alias_index, or graph claims"
    ) in content
    assert "`.specify/**` workflow/runtime state is excluded from default source/runtime scan targets" in content
    assert (
        "only read `.specify/**` for workflow operation, validation, migration, or when the requested scan "
        "is explicitly about generated workflow surfaces or spec-kit-plus itself"
    ) in lowered
    assert "project-cognition validate-scan --format json" in content
    assert "validate-scan" in lowered
    assert "may report complete only after" in lowered


def test_map_scan_shell_partial_keeps_specify_out_of_graph_inputs() -> None:
    content = _read("templates/command-partials/map-scan/shell.md")
    lowered = content.lower()

    assert "passive learning files as read-only workflow guidance, not scan evidence" in lowered
    assert "`.specify/**` is workflow/runtime state, not project graph evidence" in content
    assert "must not become scan targets or graph paths" in lowered


def test_map_workflow_templates_use_cognitionignore_for_scan_build_and_update_scope() -> None:
    scan_content = _read("templates/commands/map-scan.md")
    build_content = _read("templates/commands/map-build.md")
    update_content = _read("templates/commands/map-update.md")
    scan_shell = _read("templates/command-partials/map-scan/shell.md")
    build_shell = _read("templates/command-partials/map-build/shell.md")

    for content in (scan_content, build_content, update_content, scan_shell, build_shell):
        assert ".cognitionignore" in content

    assert "gitignore-compatible" in scan_content.lower()
    assert "repository-universe.json" in scan_content
    assert "excluded_paths" in scan_content
    assert "must not appear in coverage rows, evidence rows, provisional nodes, provisional edges, observations, or scan packets" in scan_content
    assert "project-cognition validate-scan --format json" in scan_content

    assert "must reject `.cognitionignore`-excluded paths" in build_content
    assert "must not write `.cognitionignore`-excluded paths" in build_content
    assert "project-cognition validate-build --format json" in build_content

    assert "filter changed paths through `.cognitionignore`" in update_content.lower()
    assert "user-supplied changed paths that match `.cognitionignore`" in update_content.lower()
    assert "minimal_live_reads" in update_content


def test_map_scan_template_prefers_native_subagent_inventory_with_structured_handoffs() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "current-runtime native subagents are the default" in lowered
    assert "choose_subagent_dispatch(command_name=\"map-scan\"" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "native-subagents" in lowered
    assert "validated `mapscanpacket`" in lowered
    assert "raw inventory notes or raw chat summaries are not sufficient" in lowered
    assert "structured handoff" in lowered
    assert "idle subagent output is not an accepted scan result" in lowered
    assert "must wait for every dispatched scan lane" in lowered


def test_map_scan_template_preserves_required_scan_dimensions() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

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


def test_map_build_template_refuses_incomplete_scan_packages() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "sp-map-build" in content
    assert "sp-map-scan" in content
    assert "coverage-ledger.json" in content
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
    assert "complete-refresh" in content
    assert "project-cognition publish-runtime-metadata --format json" in content
    assert "project-cognition validate-build --format json" in content
    assert "validate-build" in lowered
    assert "only after `validate-build`" in lowered or "only after validate-build" in lowered
    assert "DEBUG-HANDBOOK.md" not in content
    assert "BUILD-HANDBOOK.md" not in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/" not in content
    assert "derived-only evidence" in lowered
    assert "required_reads contain only reference-only" in lowered or "reference-only or hard-excluded" in lowered
    assert "`.specify/**` inputs are workbench/control artifacts, not graph evidence rows" in content
    assert "must not write `.specify/**` into `evidence.source_path`, `path_index.path`" in content


def test_map_build_template_requires_reverse_coverage_closure() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    required_phrases = [
        "every `critical` row appears in at least one final handbook target",
        "every `important` row appears in a final handbook target",
        "every scan packet is consumed",
        "every accepted packet result has paths read and confidence",
        "every final handbook target is backed by at least one accepted packet evidence row",
        "no final report claims success for a structural-only refresh",
        "`map_state_file` records accepted packet results",
        "owner, consumer, change propagation, and verification",
        "known unknowns",
        "known-unknowns",
        "excluded bucket has a reason and revisit condition",
        "every critical shared surface can be discovered from the relevant handbook",
        "every key verification entry point can be located from the relevant handbook",
    ]

    for phrase in required_phrases:
        assert phrase in lowered


def test_map_scan_and_build_templates_require_layer1_route_material() -> None:
    scan_content = _read("templates/commands/map-scan.md").lower()
    build_content = _read("templates/commands/map-build.md").lower()

    assert "generate layer 1 retrieval source material" in scan_content
    assert "task route candidates" in scan_content
    assert "symptom route candidates" in scan_content
    assert "shared-surface hotspot candidates" in scan_content
    assert "verification route candidates" in scan_content
    assert "propagation-risk route candidates" in scan_content
    assert "workflow-operational reachability validation" in build_content


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
    assert "concept_candidates" in build_content
    assert "route_pack" in build_content
    assert "graph truth projection" in build_lowered
    assert "evidence-backed route rows" in build_lowered

    assert "patch-in-active-generation" in update_content
    assert "stale retrieval signals" in update_lowered
    assert "selected_concepts" in update_content


def test_map_scan_template_requires_truth_layer_ledgers() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert ".specify/project-cognition/workbench/repository-universe.json" in content
    assert ".specify/project-cognition/workbench/capability-ledger.json" in content
    assert ".specify/project-cognition/workbench/control-ledger.json" in content
    assert "file, entrypoint, branch, and control-node coverage" in lowered
    assert "by capability" in lowered
    assert "by symptom" in lowered


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
