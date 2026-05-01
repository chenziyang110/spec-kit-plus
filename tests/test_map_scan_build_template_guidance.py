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
    assert ".specify/project-map/map-scan.md" in content
    assert ".specify/project-map/coverage-ledger.md" in content
    assert ".specify/project-map/coverage-ledger.json" in content
    assert ".specify/project-map/scan-packets/<lane-id>.md" in content
    assert ".specify/project-map/map-state.md" in content
    assert "Project Map State Protocol" in content
    assert "MAP_STATE_FILE=.specify/project-map/map-state.md" in content
    assert ".specify/project-map/QUICK-NAV.md" in content
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


def test_map_build_template_refuses_incomplete_scan_packages() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "sp-map-build" in content
    assert "sp-map-scan" in content
    assert "coverage-ledger.json" in content
    assert "scan-packets" in content
    assert "begins with validation, not writing" in lowered
    assert "must not guess and continue" in lowered
    assert "Project Map State Protocol" in content
    assert "Validate Scan Inputs Before Execution" in content
    assert "Compile And Validate MapBuildPacket Inputs" in content
    assert "do not rebuild the scan from chat memory" in lowered
    assert "coverage-ledger.json` as the machine-readable row source" in content
    assert "MapBuildPacket" in content
    assert "raw scan prose or raw Markdown checklist items alone" in content
    assert ".specify/project-map/worker-results/<packet-id>.json" in content
    assert "scan gap report" in lowered
    assert "packet results without paths read" in lowered
    assert "packet results that only summarize without evidence" in lowered
    assert "unresolved critical rows" in lowered
    assert "not a scaffold, migration, or file-moving command" in lowered
    assert "inputs, not evidence" in lowered
    assert "packet evidence intake" in lowered
    assert "structural-only refresh is a failed build" in lowered
    assert "reverse coverage validation" in lowered
    assert "complete-refresh" in content
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/QUICK-NAV.md" in content
    assert ".specify/project-map/index/*.json" in content
    assert ".specify/project-map/root/*.md" in content
    assert ".specify/project-map/modules/<module-id>/*.md" in content


def test_map_build_template_requires_reverse_coverage_closure() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    required_phrases = [
        "every `critical` row appears in at least one final atlas target",
        "every `important` row appears in a final atlas target",
        "every scan packet is consumed",
        "every accepted packet result has paths read and confidence",
        "every final atlas target is backed by at least one accepted packet evidence row",
        "no final report claims success for a structural-only refresh",
        "`map_state_file` records accepted packet results",
        "owner, consumer, change propagation, and verification",
        "known unknowns",
        "low-confidence areas",
        "deep_stale",
        "excluded bucket has a reason and revisit condition",
        "every high-frequency problem type is reachable from layer 1",
        "every critical shared surface can be discovered from layer 1 or atlas indexes",
        "every key verification entry point can be located from layer 1 or module/index metadata",
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
    assert "layer 1 reachability validation" in build_content
