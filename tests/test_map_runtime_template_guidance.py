import re
from pathlib import Path

from .template_utils import read_command_with_references, read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHARED_COGNITION_PARTIALS = (
    "templates/command-partials/common/context-loading-gradient.md",
    "templates/command-partials/common/planning-context-loading-gradient.md",
)
SHARED_COGNITION_GUIDANCE_SURFACES = (
    *SHARED_COGNITION_PARTIALS,
    "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
)
EPISTEMIC_CONTRACT_TERMS = (
    "epistemic_contract",
    "route_candidate_only",
    "fact_source_of_truth=live_repository",
    "live_verification_required=true",
    "graph_only_claims_allowed=false",
    "unverified_claim_action=withhold",
)
SEMANTIC_WORK_CONTRACT_PARTIAL = (
    "templates/command-partials/common/semantic-work-contract.md"
)
COGNITION_INTAKE_COMMANDS = (
    "discussion.md",
    "specify.md",
    "clarify.md",
    "deep-research.md",
    "plan.md",
    "tasks.md",
    "analyze.md",
    "fast.md",
    "quick.md",
    "implement.md",
    "debug.md",
    "checklist.md",
    "prd-scan.md",
    "map-build.md",
)
OPTIMIZED_PHASE_COMMANDS = ("specify.md", "plan.md", "tasks.md", "implement.md")
ADVANCED_COGNITION_INTAKE_COMMANDS = tuple(
    name for name in COGNITION_INTAKE_COMMANDS if name not in OPTIMIZED_PHASE_COMMANDS
)
SEMANTIC_WORK_CONTRACT_COMMANDS = (
    *COGNITION_INTAKE_COMMANDS,
    "implement-teams.md",
    "map-scan.md",
    "map-update.md",
)
SEMANTIC_WORK_CONTRACT_TERMS = (
    "semantic_work_contract_begin",
    "workcontract v1",
    "semantic-intake",
    "permissiondecision",
    "maximum_without_live_evidence",
    "learningcontract",
    "single unified entrypoint",
    "do not choose debug, implement, plan, or research from the user's raw words",
    "compass-first",
    "semantic-intake escalation",
    "v1.1 audit artifact",
    "workcontract artifact",
    "semantic-intake input/output snapshot",
    "selected/rejected basis",
    "permission upgrade/downgrade reason",
    "action log",
    "semantic-audit-input.json",
    "semantic-audit-output.json",
    "semantic_audit_state",
    "semantic_audit_input_path",
    "semantic_audit_output_path",
    "semantic_audit_resume_status",
    "semantic_audit_resume_validation",
    "semantic_audit_route_fingerprint",
    "semantic_audit_generated_resume_smoke",
    "semantic_audit_stale_reasons",
    "semantic-audit-resume",
    "optional runtime validator",
    "prefer the optional runtime validator",
    "ephemeral resume-validation.json",
    "if the validator returns fresh",
    "if the validator is unavailable",
    "prompt fallback remains valid",
    "does not authorize source edits, final claims, or p3/p4 permission",
    "can_reuse_persisted_claim_readiness",
    "grants_permission",
    "comparison_only_no_source_edit_or_claim_authorization",
    "active-claim-changed",
    "normalized_goal",
    "semantic_intake_ref",
    "selected_concept_ids",
    "rejected_concept_ids",
    "evidence_plan",
    "learning_contract",
    "inspection_plan",
    "target_path",
    "live_evidence_capture",
    "rerank_after_inspect",
    "rerank_assessment",
    "permission_promotion_candidate",
    "candidate_only",
    "route_contradicted",
    "owner_bundle_confidence",
    "owner_miss_expansion",
    "max_radius",
    "source_kind",
    "route_vocabulary",
    "live_source_evidence_required",
    "bounded_source_evidence_required",
    "verification_owner_discovery",
    "verification_owner_missing",
    "verification_results",
    "workflow_authorization",
    "authorized_claims",
    "active_claim_type",
    "authorization_ref",
    "claim_authorizations",
    "verification_evidence_refs",
    "claim_authorization_refs",
    "claim_readiness",
    "claim_type",
    "claim_types",
    "claim_verification_refs",
    "verification_satisfied",
    "claim_candidate",
    "claim_ready",
    "root_cause_claim",
    "verification_owner_match_required",
    "verification_result_failed",
    "verification_result_blocked",
    "verification_result_inconclusive",
    "workflow_authorization_ref_required",
    "claim_type_not_supported",
    "claim_specific_verification_required",
    "claim_authorization_required",
    "claim_authorization_ref_required",
    "claim_authorization_verification_ref_required",
    "active_claim_type_required",
    "active_claim_not_authorized",
    "targeted_test",
    "promotion_blocked",
    "stale_index_downgrade",
    "inspect_ready",
    "inspect_blocked",
    "do not claim root cause, fixed, complete, or release-safe",
    "semantic_work_contract_end",
)


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _compact(text: str) -> str:
    return " ".join(text.split())


def _run_or_emulate_blocks(content: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"Run or emulate:\s*```text\n(?P<body>.*?)\n\s*```", content, re.DOTALL):
        blocks.append(match.group("body"))
    return blocks


def _read_command(name: str) -> str:
    return read_command_with_references(name.removesuffix(".md"))


def test_workflows_use_project_cognition_compass_as_default_intake() -> None:
    workflow_intents = {
        "fast.md": "implement",
        "quick.md": "implement",
        "specify.md": "plan",
        "clarify.md": "plan",
        "deep-research.md": "research",
        "plan.md": "plan",
        "tasks.md": "plan",
        "implement.md": "implement",
        "debug.md": "debug",
        "prd-scan.md": "research",
    }
    readiness_states = ["query_ready", "review", "needs_rebuild", "blocked", "unsupported_runtime"]

    obsolete_primary_input_phrases = [
        "required slices",
        "graph artifacts as primary workflow inputs",
        "graph artifacts as the primary",
        "graph slice artifacts as the primary",
        "status.json`, required slices",
        "status.json`, `slices/change.json`",
        "status.json`, `slices/debug.json`",
        ".specify/project-cognition/status.json`, required slices",
    ]

    for name, intent in workflow_intents.items():
        content = _read_command(name).lower()
        assert "project-cognition compass" in content
        assert f"project-cognition compass --intent {intent}" in content
        assert "minimal_live_reads" in content
        assert "first_pass_paths" in content
        assert "coverage_diagnostics" in content
        if name in OPTIMIZED_PHASE_COMMANDS:
            assert "expansion_ref" in content
            assert "at most one" in content
            assert "context capsule" in content
            assert "project-cognition query --query-plan" not in content
            assert "lexicon -> semantic_intake -> query" not in content
            continue
        assert (
            "lexicon -> semantic_intake -> query" in content
            or "lexicon -> semantic_intake -> project-cognition query" in content
        )
        assert "project-cognition query" in content
        assert "project-cognition query --query-plan" in content
        assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
        assert "--query-plan" in content
        assert "query_plan" in content
        assert "semantic_intake" in content
        assert "facet coverage" in content
        assert "concept_decisions" in content
        assert "lexicon_generation_id" in content
        assert "returned map terms" not in content
        assert "raw user intent plus returned map terms" not in content
        for state in readiness_states:
            assert f"`{state}`" in content, f"{name} missing readiness state {state}"
        assert "`ambiguous`" not in content
        assert "`needs_update`" not in content
        assert "read top-level `minimal_live_reads` first" in content
        assert "then use lane-level `first_pass_paths`" in content
        assert ".specify/project-cognition/graph/nodes.json" not in content
        assert ".specify/project-cognition/graph/edges.json" not in content
        assert ".specify/project-cognition/graph/claims.json" not in content
        assert ".specify/project-cognition/graph/conflicts.json" not in content
        assert ".specify/project-cognition/slices/change.json" not in content
        assert ".specify/project-cognition/slices/debug.json" not in content
        for phrase in obsolete_primary_input_phrases:
            assert phrase not in content, f"{name} contains obsolete runtime input phrase: {phrase}"


def test_cognition_launchers_use_double_brace_generated_forms() -> None:
    for name in ("plan.md", "implement.md", "debug.md", "tasks.md"):
        content = _read_command(name)
        raw_content = _read(f"templates/commands/{name}")
        assert not re.search(r"(?<!\{)\{specify-subcmd:project-cognition compass", raw_content)
        assert "{{specify-subcmd:project-cognition compass" in content


def test_default_runnable_cognition_blocks_only_run_compass() -> None:
    workflow_intents = {
        "fast.md": "implement",
        "quick.md": "implement",
        "specify.md": "plan",
        "clarify.md": "plan",
        "deep-research.md": "research",
        "plan.md": "plan",
        "tasks.md": "plan",
        "implement.md": "implement",
        "debug.md": "debug",
        "prd-scan.md": "research",
    }

    for name, intent in workflow_intents.items():
        content = _read_command(name)
        blocks = _run_or_emulate_blocks(content)
        assert blocks, f"{name} missing Run or emulate fenced block"
        expected = f'{{{{specify-subcmd:project-cognition compass --intent {intent} --query="$ARGUMENTS" --format json}}}}'
        assert any(block.strip() == expected for block in blocks), f"{name} default runnable block must only contain compass"
        for block in blocks:
            assert "project-cognition query" not in block, f"{name} has advanced query in default runnable block"
            assert "semantic_intake" not in block, f"{name} has semantic-intake guidance in default runnable block"


def test_specify_default_intake_does_not_use_old_ready_readiness() -> None:
    content = _read_command("specify.md").lower()
    assert "when cognition reports `ready`, use the returned task-local bundle" not in content
    assert "at most one `project-cognition compass --intent plan` intake" in content
    assert "canonical context capsule lacks a required facet" in content
    assert "`minimal_live_reads`" in content
    assert "`first_pass_paths`" in content
    assert "`coverage_diagnostics`" in content


def test_included_workflow_partials_use_phase_appropriate_runtime_inputs() -> None:
    optimized_partials = [
        "templates/command-partials/plan/shell.md",
        "templates/command-partials/tasks/shell.md",
        "templates/command-partials/implement/shell.md",
    ]
    advanced_partials = [
        "templates/command-partials/debug/shell.md",
        "templates/command-partials/quick/shell.md",
        "templates/command-partials/analyze/shell.md",
        "templates/command-partials/common/navigation-check.md",
    ]

    for path in optimized_partials:
        content = _read(path).lower()
        assert "primary" in content
        assert "required ref" in content or "required_refs" in content
        assert "context capsule" in content or "full upstream" in content or "full plan/spec" in content
        assert "required slices" not in content
        assert "graph artifacts" not in content
        assert "slices/change.json" not in content
        assert "slices/debug.json" not in content

    for path in advanced_partials:
        content = _read(path).lower()
        assert "project-cognition query" in content or "project cognition query" in content
        assert "task-local" in content
        assert "bundle" in content
        assert "readiness" in content
        assert "minimal_live_reads" in content
        assert "required slices" not in content
        assert "graph artifacts" not in content
        assert "slices/change.json" not in content
        assert "slices/debug.json" not in content


def test_shared_project_cognition_partials_require_semantic_intake_contract() -> None:
    required_terms = [
        "alias catalog",
        "semantic_intake",
        "normalized_query",
        "intent_facets",
        "negative_constraints",
        "alias_interpretations",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "facet coverage",
        "do not trust top similarity alone",
    ]
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _read(path).lower()
        for term in required_terms:
            assert term in content, f"{path} missing shared semantic intake term: {term}"


def test_project_cognition_consumers_enforce_machine_readable_epistemic_contract() -> None:
    contract_surfaces = (
        *SHARED_COGNITION_GUIDANCE_SURFACES,
        "templates/command-partials/common/planning-cognition.md",
        "templates/command-partials/common/semantic-work-contract.md",
        "templates/command-partials/ask/shell.md",
    )
    for path in contract_surfaces:
        content = _compact(_read(path).lower())
        for term in EPISTEMIC_CONTRACT_TERMS:
            assert term in content, f"{path} missing epistemic contract term: {term}"


def test_claim_aware_retrieval_contract_propagates_to_agent_consumers() -> None:
    runtime_source = _compact(
        (
            _read("tools/project-cognition/internal/query/query.go")
            + _read("tools/project-cognition/internal/query/compass.go")
            + _read("tools/project-cognition/internal/query/claim_signal.go")
        ).lower()
    )
    for term in (
        'json:"claim_signals,omitempty"',
        'json:"claim_refs,omitempty"',
        '"claim_evidence"',
        'json:"route_confidence"',
        'json:"confidence_scope"',
        'json:"evidence_refs"',
        'json:"live_verification_required"',
    ):
        assert term in runtime_source

    for path in (
        *SHARED_COGNITION_GUIDANCE_SURFACES,
        "templates/command-partials/common/planning-cognition.md",
        "templates/commands/map-build.md",
    ):
        content = _compact(_read(path).lower())
        for term in (
            "claim_refs",
            "claim_signals",
            "claim_evidence",
            "route_confidence",
            "confidence_scope",
        ):
            assert term in content, f"{path} missing claim-aware retrieval term: {term}"
        assert "route candidate" in content
        assert "live verification" in content

    for path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ):
        content = _compact(_read(path).lower())
        for term in (
            "claim_refs",
            "claim_signals",
            "claim_evidence",
            "route_confidence",
            "confidence_scope=route_candidate",
        ):
            assert term in content, f"{path} missing claim-aware retrieval term: {term}"
        assert "source_path" in content and "span" in content
        assert "cannot prove current repository truth" in content
        assert "cannot authorize source changes" in content
        assert "cannot prove current behavior" in content

    integration_source = _compact(_read("src/specify_cli/integrations/base.py").lower())
    for term in EPISTEMIC_CONTRACT_TERMS:
        assert term in integration_source
    assert "carry `epistemic_contract`" in integration_source

    for path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ):
        content = _compact(_read(path).lower())
        for term in EPISTEMIC_CONTRACT_TERMS:
            assert term in content, f"{path} missing epistemic contract term: {term}"


def test_typed_graph_claim_lifecycle_is_separate_from_workflow_final_claims() -> None:
    scan = _compact(_read("templates/commands/map-scan.md").lower())
    for term in (
        "provisional/claims.json",
        "graph_claim_type",
        "requested_state",
        "supporting_evidence_ids",
        "contradicting_evidence_ids",
        "verifications",
    ):
        assert term in scan
    assert "optional" in scan

    build = _compact(_read("templates/commands/map-build.md").lower())
    for term in (
        "schema v3 runtime contract",
        "claims",
        "claim_evidence",
        "claim_verifications",
        "claim_transitions",
        "verified_in_graph_generation",
    ):
        assert term in build
    assert "future semantic tables such as claims" not in build

    update = _compact(_read("templates/commands/map-update.md").lower())
    assert "affected_graph_claims" in update
    assert "changed paths" in update
    assert "mark" in update and "stale" in update
    assert "must not re-promote" in update

    semantic_contract = _compact(_read(SEMANTIC_WORK_CONTRACT_PARTIAL).lower())
    for term in (
        "graph claim namespace",
        "graph_claim_type",
        "verified_in_graph_generation",
        "workflow final claim namespace",
        "claim_readiness.claim_type",
        "cannot set workflow `claim_ready=true`",
        "must not populate `claim_verification_refs`",
    ):
        assert term in semantic_contract

    shared_surfaces = (
        *SHARED_COGNITION_GUIDANCE_SURFACES,
        "templates/command-partials/common/planning-cognition.md",
        "src/specify_cli/integrations/base.py",
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    )
    for path in shared_surfaces:
        content = _compact(_read(path).lower())
        assert "graph claims are indexed assertions" in content, path
        assert "verified_in_graph_generation" in content, path
        assert "cannot set workflow `claim_ready=true`" in content, path


def test_shared_semantic_work_contract_partial_defines_permission_and_learning_gates() -> None:
    content = _compact(_read(SEMANTIC_WORK_CONTRACT_PARTIAL).lower())

    for term in SEMANTIC_WORK_CONTRACT_TERMS:
        assert term in content

    for permission_level in ("p0", "p1", "p2"):
        assert permission_level in content

    for memory_level in ("m0", "m1"):
        assert memory_level in content

    assert "project-cognition semantic-audit" in content
    assert '"semantic_audit_input"' in content
    assert '"semantic_intake_input"' in content
    assert '"semantic_intake_output"' in content
    assert '"route_decision"' in content
    assert '"permission_decision"' in content
    assert '"route_corrections"' in content
    assert '"inspection_plan"' in content
    assert '"steps"' in content
    assert '"live_evidence_capture"' in content
    assert '"rerank_after_inspect"' in content
    assert '"rerank_assessment"' in content
    assert '"permission_promotion_candidate"' in content
    assert '"owner_bundle_confidence"' in content
    assert '"owner_miss_expansion"' in content
    assert '"max_radius"' in content
    assert '"stale_index_downgrade"' in content
    assert "does not authorize source changes" in content
    assert "does not raise permission above p2" in content
    assert "if semantic-audit is unavailable" in content
    assert "manually produce the same semantic_audit_input fields" in content
    assert "do not block on installing a newer runtime solely for semantic-audit" in content
    assert "inspection_plan maps each missing facet or evidence need to a bounded target" in content
    assert "targeted_read only" in content
    assert "capture live_evidence_capture before raising permission" in content
    assert "rerank_after_inspect before any root-cause, fixed, complete, or release-safe claim" in content
    assert "live evidence can create a permission_promotion_candidate only" in content
    assert "candidate_only is not granted permission" in content
    assert "route_contradicted downgrades permission" in content
    assert "owner_bundle_confidence summarizes indexed owner roles" in content
    assert "owner_miss_expansion max_radius is 1" in content
    assert "route vocabulary evidence is not live source evidence" in content
    assert "source_kind" in content
    assert "live_source_evidence_required" in content
    assert "bounded_source_evidence_required" in content
    assert "selected_concept_ids" in content
    assert "rejected_concept_ids" in content
    assert "verification_owner_discovery identifies indexed or missing verification owners" in content
    assert "verification result ingestion" in content
    assert "every selected candidate has an indexed verification owner" in content
    assert "workflow authorization baseline" in content
    assert "claim-specific final claims" in content
    assert "audit state persistence" in content
    assert "persist semantic-audit-input.json and semantic-audit-output.json next to the active workflow state" in content
    assert "resume validation" in content
    assert "compare selected_candidate_ids, active_claim_type, claim_authorization_refs, and claim_verification_refs" in content
    assert "generated resume smoke" in content
    assert "stale-state detection remains prompt-only" in content
    assert "semantic-audit-resume" in content
    assert "optional runtime validator" in content
    assert "prompt fallback remains valid" in content
    assert "does not authorize source edits, final claims, or p3/p4 permission" in content
    assert "semantic-audit-input.json.semantic_audit_input.route_decision" in content
    assert "semantic-audit-output.json.workflow_authorization and semantic-audit-output.json.claim_readiness" in content
    assert "fingerprint mismatches are route-changed" in content
    assert ".specify/templates/examples/semantic-audit-resume/scenarios.md" in content
    assert "semantic audit resume examples" in content
    assert "semantic_audit_generated_resume_smoke" in content
    assert "semantic_audit_stale_reasons" in content
    assert "active-claim-changed" in content
    assert '"semantic_audit_resume_validation"' in content
    assert '"semantic_audit_route_fingerprint"' in content
    assert '"semantic_audit_generated_resume_smoke"' in content
    assert '"semantic_audit_stale_reasons"' in content
    assert '"semantic_audit_state"' in content
    assert '"semantic_audit_input_path"' in content
    assert '"semantic_audit_output_path"' in content
    assert '"semantic_audit_resume_status"' in content
    assert "current generated workflows may mark `fixed_claim`, `completed_claim`, or `release_safe` claim_ready only when" in content
    assert "top-level workflow_authorization has `status: authorized`" in content
    assert "`authorized_claims` contains that claim" in content
    assert "empty verification `claim_type` is legacy-compatible only for `root_cause_claim`" in content
    assert '"workflow_authorization"' in content
    assert '"authorized_claims"' in content
    assert '"authorization_ref"' in content
    assert '"claim_authorizations"' in content
    assert '"verification_evidence_refs"' in content
    assert '"claim_verification_refs"' in content
    assert '"claim_type"' in content
    assert '"claim_types"' in content
    assert "fixed, complete, and release-safe claims additionally require claim-specific passed verification" in content
    assert "verification_path matches an indexed verification owner" in content
    assert "failed verification results block final claims until superseded by a newer matching passed rerun" in content
    assert "blocked verification results block final claims until recovery or rerun produces a newer matching passed result" in content
    assert "skipped or otherwise inconclusive verification results block final claims" in content
    assert "verification_result_failed" in content
    assert "verification_result_blocked" in content
    assert "verification_result_inconclusive" in content
    assert "workflow_authorization.active_claim_type" in content
    assert "multiple authorized claims require explicit active_claim_type" in content
    assert "active_claim_type_required" in content
    assert "active_claim_not_authorized" in content
    assert "without workflow_authorization, claim_status is claim_candidate" in content
    assert "claim_ready remains false" in content
    assert "promotion_blocked true" in content
    assert "targeted_test" in content
    assert "stale_index_downgrade" in content
    assert "semantic-intake --input <work-contract-input.json> --format json` before broader source reads" not in content


def test_semantic_work_contract_is_generated_for_all_project_cognition_workflows() -> None:
    missing = []
    for name in SEMANTIC_WORK_CONTRACT_COMMANDS:
        content = _compact(_read_command(name).lower())
        if not all(term in content for term in SEMANTIC_WORK_CONTRACT_TERMS):
            missing.append(name)

    assert missing == [], f"semantic work contract missing from workflows: {missing}"


def test_semantic_resume_smoke_contract_is_generated_for_all_project_cognition_workflows() -> None:
    required_terms = (
        "generated resume smoke",
        "stale-state detection remains prompt-only",
        "semantic-audit-resume",
        "optional runtime validator",
        "resume-validation.json",
        "resume-validation-route-changed.json",
        "resume-validation-active-claim-changed.json",
        "resume-validation-missing-file.json",
        "resume-validation-claim-ref-mismatch.json",
        "resume-validation-verification-ref-mismatch.json",
        "prefer the optional runtime validator",
        "ephemeral resume-validation.json",
        "if the validator returns fresh",
        "if the validator is unavailable",
        "prompt fallback remains valid",
        "does not authorize source edits, final claims, or p3/p4 permission",
        "validator",
        "can_reuse_persisted_claim_readiness",
        "grants_permission",
        "boundary",
        "semantic-audit-input.json.semantic_audit_input.route_decision",
        "semantic-audit-output.json.workflow_authorization and semantic-audit-output.json.claim_readiness",
        "fingerprint mismatches are route-changed",
        "semantic_audit_generated_resume_smoke",
        "semantic_audit_stale_reasons",
    )
    missing = []
    for name in SEMANTIC_WORK_CONTRACT_COMMANDS:
        content = _compact(_read_command(name).lower())
        missing_terms = [term for term in required_terms if term not in content]
        if missing_terms:
            missing.append(f"{name}: {', '.join(missing_terms)}")

    assert missing == [], f"semantic resume smoke contract missing from workflows: {missing}"


def test_semantic_work_contract_handoff_records_generated_downstream_smoke_boundary() -> None:
    content = _compact(
        _read("docs/design/universal-semantic-work-contract-handoff.md").lower()
    )

    assert "v1.3.7 generated downstream smoke is locally closed" in content
    assert "actual codex init" in content
    assert "generated sp-debug skill" in content
    assert ".specify/templates/workflow-state-template.md" in content
    assert "runtime resume validator remains optional" in content
    assert "v1.3.8 semantic audit resume examples is locally closed" in content
    assert "semantic-audit-resume/scenarios.md" in content
    assert "v1.3.9 runtime resume validator is locally closed" in content
    assert "semantic-audit-resume --input" in content
    assert "optional json comparator" in content
    assert "resume-validation.json" in content
    assert "resume-validation-route-changed.json" in content
    assert "resume-validation-active-claim-changed.json" in content
    assert "resume-validation-missing-file.json" in content
    assert "resume-validation-claim-ref-mismatch.json" in content
    assert "resume-validation-verification-ref-mismatch.json" in content
    assert "prefer the optional runtime validator" in content
    assert "ephemeral resume-validation.json" in content
    assert "if the validator returns fresh" in content
    assert "if the validator is unavailable" in content
    assert "can_reuse_persisted_claim_readiness" in content
    assert "grants_permission: false" in content
    assert "comparison_only_no_source_edit_or_claim_authorization" in content
    assert "v1.3.11 resume validator workflow preference" in content
    assert "v1.3.12 resume validator stale case matrix" in content
    assert "v1.3.13 real downstream resume smoke" in content
    assert "v1.3.14 resume validator test hygiene and release readiness" in content
    assert "v1.3.15 release readiness" in content
    assert "v1.3.15 release readiness is locally closed" in content
    assert "v1.3.16 release publication" in content
    assert "v1.3.16 release publication is locally closed" in content
    assert "no external release was triggered" in content
    assert "next version: v1.3.17 external release trigger" in content
    assert "semantic work contract design-slice label" in content
    assert "not a git release tag" in content
    assert "semver package tag" in content
    assert ".github/workflows/release-trigger.yml" in content
    assert "version matches the tag" in content
    assert "dirty local working tree" in content
    assert "confirm the working tree changes are committed and pushed" in content
    assert "v0.5.14" in content
    assert "released project-cognition binary exposes" in content
    assert "packaged release" in content
    assert "v1.3.17 local preflight is closed" in content
    assert "release-trigger versus release workflow ownership is documented and tested" in content
    assert "remote tag checks found no" in content
    assert "v1.3.17" in content
    assert "remaining work is external release execution" in content
    assert "v1.3.18 claim readiness policy hardening" in content
    assert "verification_result_failed" in content
    assert "verification_result_blocked" in content
    assert "verification_result_inconclusive" in content
    assert "v1.3.19 active claim authorization policy" in content
    assert "workflow_authorization.active_claim_type" in content
    assert "active_claim_type_required" in content
    assert "active_claim_not_authorized" in content
    assert "user-facing guidance docs now document semantic-audit-resume" in content
    assert "tests/test_specify_guidance_docs.py" in content


def test_semantic_work_contract_design_records_verification_outcome_policy() -> None:
    content = _compact(
        _read("docs/design/universal-semantic-work-contract-v1.md").lower()
    )

    assert "verification_results can satisfy claim_readiness" in content
    assert "failed verification results block claim_readiness with verification_result_failed" in content
    assert "blocked verification results block claim_readiness with verification_result_blocked" in content
    assert "skipped or otherwise inconclusive verification results block claim_readiness with verification_result_inconclusive" in content
    assert "workflow_authorization.active_claim_type records the single active final claim" in content
    assert "multiple authorized claims without active_claim_type block claim_readiness with active_claim_type_required" in content
    assert "active claims not listed in authorized_claims block claim_readiness with active_claim_not_authorized" in content


def test_semantic_resume_validator_downstream_adoption_examples_are_documented() -> None:
    content = _compact(_read("templates/examples/semantic-audit-resume/scenarios.md").lower())

    assert "resume-validation.json" in content
    assert "resume-validation-route-changed.json" in content
    assert "resume-validation-active-claim-changed.json" in content
    assert "resume-validation-missing-file.json" in content
    assert "resume-validation-claim-ref-mismatch.json" in content
    assert "resume-validation-verification-ref-mismatch.json" in content
    assert "semantic-audit-input.json" in content
    assert "semantic-audit-output.json" in content
    assert "project-cognition semantic-audit-resume --input resume-validation.json --format json" in content
    assert "semantic_audit_generated_resume_smoke: passed" in content
    assert "semantic_audit_generated_resume_smoke: failed" in content
    assert "can_reuse_persisted_claim_readiness" in content
    assert "grants_permission: false" in content


def test_shared_project_cognition_partials_require_project_language_search_terms() -> None:
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _compact(_read(path).lower())
        assert "project-language search terms" in content, path
        assert "repository_search_terms" in content, path
        assert "derived from the alias catalog" in content, path
        assert "do not search only the raw user words" in content, path
        assert "component names, state names, file names, command names, ui labels, and route names" in content, path
        assert "use these project-language search terms before broad repository search" in content, path


def test_shared_project_cognition_partials_assign_semantic_normalization_to_agent() -> None:
    required_terms = (
        "agent-owned semantic normalization",
        "raw lexicon ranking is only a bootstrap",
        "score=0",
        "mixed-language or cjk text",
        "extract embedded project terms",
    )
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _compact(_read(path).lower())
        for term in required_terms:
            assert term in content, f"{path} missing agent semantic normalization rule: {term}"


def test_shared_cognition_guidance_explains_agent_normalization_diagnostic() -> None:
    required_terms = (
        "agent_normalization",
        "required=true",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
        "not a route decision",
    )

    for path in SHARED_COGNITION_GUIDANCE_SURFACES:
        content = _compact(_read(path).lower())
        for term in required_terms:
            assert term in content, f"{path} missing agent_normalization diagnostic term: {term}"


def test_shared_project_cognition_partials_include_canonical_query_plan_skeleton() -> None:
    required_skeleton_terms = (
        '"raw_query"',
        '"semantic_intake"',
        '"workflow_intent"',
        '"normalized_query"',
        '"intent_facets"',
        '"negative_constraints"',
        '"alias_interpretations"',
        '"open_semantic_questions"',
        '"selected_concepts"',
        '"rejected_concepts"',
        '"concept_decisions"',
        '"covered_facets"',
        '"missing_facets"',
        '"match_sources"',
        '"lexicon_generation_id"',
        '"expanded_queries"',
        '"repository_search_terms"',
        '"paths"',
    )

    for path in SHARED_COGNITION_PARTIALS:
        content = _read(path)
        compact = _compact(content)
        for term in required_skeleton_terms:
            assert term in content, f"{path} missing canonical query-plan skeleton term {term}"
        assert '"alias": "<user term>"' in compact, path
        assert '"meaning": "<project term>"' in compact, path
        assert '"confidence": "medium"' in compact, path
        assert '"alias_interpretations": ["' not in compact, path


def test_cognition_workflows_preserve_shared_intake_sequence() -> None:
    required_terms = (
        "project-cognition compass",
        "minimal_live_reads",
        "first_pass_paths",
        "coverage_diagnostics",
        "lexicon -> semantic_intake -> query",
        "semantic_intake",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "lexicon_generation_id",
        "project-cognition query",
        "--query-plan",
        "repository_search_terms",
        "agent-owned semantic normalization",
        "raw lexicon ranking is only a bootstrap",
    )

    for name in ADVANCED_COGNITION_INTAKE_COMMANDS:
        content = _read_command(name).lower()
        for term in required_terms:
            assert term in content, f"{name} missing shared cognition intake term {term}"

    for name in OPTIMIZED_PHASE_COMMANDS:
        content = _read_command(name).lower()
        for term in (
            "project-cognition compass",
            "minimal_live_reads",
            "first_pass_paths",
            "coverage_diagnostics",
            "expansion_ref",
        ):
            assert term in content, f"{name} missing compact cognition intake term {term}"
        assert "project-cognition query --query-plan" not in content


def test_docs_describe_compass_default_and_advanced_query_path() -> None:
    stale_default_query_phrases = (
        "project cognition query bundle as its default intake",
        "query bundle as its default intake",
        "agent-planned task-local project cognition query bundle",
        "task-local project cognition query bundle before broader",
        "default generated-project route to the alias catalog",
        "default route to the alias catalog",
    )

    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        content = _compact(_read(path).lower())
        assert "project-cognition compass" in content, path
        assert 'project-cognition compass --intent <intent> --query "$arguments" --format json' in content, path
        assert "project-cognition semantic-intake" in content, path
        assert "workcontract v1" in content, path
        assert "v1.1 audit artifact" in content, path
        assert "workcontract artifact" in content, path
        assert "semantic-intake input/output snapshot" in content, path
        assert "selected/rejected basis" in content, path
        assert "permission upgrade/downgrade reason" in content, path
        assert "action log" in content, path
        assert "semantic-intake alone cannot authorize source changes" in content, path
        assert "minimal_live_reads" in content, path
        assert "first_pass_paths" in content, path
        assert "project-cognition lexicon --mode catalog" in content, path
        assert "agent-authored `semantic_intake`" in content, path
        assert "concept_decisions" in content, path
        assert "project-cognition query --query-plan" in content, path
        assert "lexicon -> semantic_intake -> query" in content, path
        assert "final edit scope" in content, path
        for phrase in stale_default_query_phrases:
            assert phrase not in content, f"{path} still contains stale default query wording: {phrase}"

    handbook = _compact(_read("PROJECT-HANDBOOK.md").lower())
    assert 'project-cognition compass --intent debug --query "$arguments" --format json' in handbook


def test_cognition_workflows_preserve_direct_agent_normalization_guidance() -> None:
    required_terms = (
        "agent_normalization",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
    )

    for name in ADVANCED_COGNITION_INTAKE_COMMANDS:
        content = _read_command(name).lower()
        for term in required_terms:
            assert term in content, f"{name} missing direct agent_normalization guidance term: {term}"


def test_map_update_preserves_semantic_intake_classification_without_user_intent_query() -> None:
    content = read_template("templates/commands/map-update.md").lower()

    for term in (
        "shared semantic intake contract",
        "semantic_intake",
        "alias catalog",
        "intent_facets",
        "negative_constraints",
        "alias_interpretations",
        "concept_decisions",
        "covered_facets",
        "missing_facets",
        "match_sources",
        "repository_search_terms",
        "project-language search terms",
        "do not search only the raw user words",
        "do not trust top similarity alone",
    ):
        assert term in content


def test_shared_readiness_review_guidance_uses_minimal_live_reads() -> None:
    for path in (
        *SHARED_COGNITION_PARTIALS,
        "templates/command-partials/common/senior-consequence-analysis-gate.md",
    ):
        content = _compact(_read(path).lower())
        assert "`review`" in content, path
        assert "review" in content and "minimal_live_reads" in content, path
        assert (
            "inspect the returned `minimal_live_reads` before expanding" in content
            or "inspect the returned `minimal_live_reads` before continuing" in content
            or "perform only the returned `minimal_live_reads` before continuing" in content
        ), path


def test_learning_start_hardening_scope_matches_command_templates() -> None:
    commands_with_learning_start: set[str] = set()
    for path in (PROJECT_ROOT / "templates" / "commands").glob("*.md"):
        content = _read_command(path.name)
        for match in re.finditer(r"learning start --command ([a-z-]+) --format json", content):
            commands_with_learning_start.add(match.group(1))

    assert {"debug", "constitution", "map-scan", "map-build"} <= commands_with_learning_start
    assert {"plan", "implement"}.isdisjoint(commands_with_learning_start)
    assert "context capsule" in _read_command("plan.md").lower()
    assert "current task's required refs" in _read_command("implement.md").lower()


def test_semantic_intake_contract_is_not_debug_only() -> None:
    brownfield_workflows = {
        "discussion.md",
        "specify.md",
        "clarify.md",
        "deep-research.md",
        "plan.md",
        "tasks.md",
        "analyze.md",
        "fast.md",
        "quick.md",
        "implement.md",
        "debug.md",
        "checklist.md",
        "prd-scan.md",
        "map-scan.md",
        "map-update.md",
    }
    missing = []
    for name in brownfield_workflows:
        content = _read_command(name).lower()
        if "semantic_intake" not in content or "facet coverage" not in content:
            missing.append(name)

    assert missing == [], f"semantic intake contract must not be limited to sp-debug; missing: {missing}"


def test_map_scan_template_targets_graph_native_runtime() -> None:
    content = _read("templates/commands/map-scan.md")

    assert ".specify/project-cognition/" in content
    assert "evidence" in content.lower()
    assert "provisional nodes" in content.lower()
    assert "candidate edges" in content.lower()
    assert "must not publish final cognition truth" in content.lower()


def test_map_build_template_targets_graph_reconstruction() -> None:
    content = _read("templates/commands/map-build.md")

    assert ".specify/project-cognition/project-cognition.db" in content
    assert "{{specify-subcmd:project-cognition compass" in content
    assert "{{specify-subcmd:project-cognition query" in content
    assert "--query-plan" in content
    assert "raw graph JSON artifacts or slices as runtime truth" in content
    assert "conflict" in content.lower()
    assert "claim" in content.lower()


def test_map_update_template_exists_and_is_incremental() -> None:
    template_path = PROJECT_ROOT / "templates/commands/map-update.md"
    assert template_path.exists(), "map-update command template must exist for incremental cognition runtime maintenance"
    content = _read("templates/commands/map-update.md")

    assert "map-update" in content
    assert "diff" in content.lower()
    assert "user supplement" in content.lower()
    assert "incremental" in content.lower()
    assert "after recording updates, re-evaluate runtime readiness through the shared freshness contract" in content.lower()
    assert "do not report refresh completion when the runtime remains blocked" in content.lower()
    assert "partial_refresh" in content.lower()
    assert "user-supplied scope is authoritative for the touched area unless repository evidence disproves it" in content.lower()
    assert "prefer the smallest update that can truthfully restore readiness" in content.lower()
    assert "git delta intake" in content.lower()
    assert "update-by-default rule" in content.lower()
    assert "ordinary uncertainty is not an update failure" in content.lower()
    assert "partial/low-confidence update" in content.lower()
    assert "known_unknowns" in content
    assert "minimal_live_reads" in content
    assert "do not read or rewrite raw graph json artifacts; they are not runtime truth" in content.lower()
    assert ".specify/project-cognition/project-cognition.db" in content
    assert "do not split small localized updates into parallel scan-style lanes just because subagents are available" in content.lower()
    assert "escalate to `sp-map-scan`, then `sp-map-build` only when no query-backed baseline exists" in content.lower()
    assert "do not escalate merely because the affected closure is uncertain" in content.lower()
    assert "project-cognition validate-build --format json" in content
    assert "must not call" in content.lower()
    assert "needs_rebuild" in content
    assert "complete-refresh" in content


def test_map_update_template_handles_existing_baseline_gaps_without_rebuild() -> None:
    content = _read("templates/commands/map-update.md").lower()

    assert "existing-baseline ordinary gaps" in content
    assert "partial_refresh" in content
    assert "minimal_live_reads" in content
    assert "baseline_identity_invalid" in content
    assert "explicit_rebuild_requested" in content
    assert "path count" in content
    assert (
        "must not route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` "
        "for ordinary path gaps"
    ) in content
