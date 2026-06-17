from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assert_tier_roles(content: str) -> None:
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in content
    fast_smoke_index = content.index("fast smoke")
    focused_index = content.index("focused", fast_smoke_index)
    full_index = content.index("full", focused_index)

    fast_smoke_context = content[fast_smoke_index : fast_smoke_index + 180]
    focused_context = content[focused_index : focused_index + 220]
    full_context = content[full_index : full_index + 220]

    assert "cheapest" in fast_smoke_context or "early signal" in fast_smoke_context
    assert "accepting the fix" in focused_context or "acceptance" in focused_context
    assert "regression risk" in full_context or "broader regression" in full_context


def test_debug_template_documents_map_backed_intake_contract() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "complexity-based debug execution" in content
    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "dispatch_reason" in content
    assert "blocked_reason" in content
    assert "use `leader-inline` when the investigation is small, focused, and has a short evidence chain" in content
    assert "use `subagent-assisted` when the investigation has multiple independent evidence lanes" in content
    assert "structured handoff" in content
    assert "project-map first" in content
    assert "map-backed minimum intake" in content
    assert "deep intake is fallback, not the default" in content
    assert "stage 1a: causal map" in content
    assert "stage 1b: investigation contract + log investigation plan" in content
    assert "causal_map_completed" in content
    assert "investigation_contract_completed" in content
    assert "log_investigation_plan_completed" in content
    assert "do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing" in content
    assert "think subagent must not read source files" in content
    assert "think subagent must not inspect logs" in content
    assert "think subagent must not read test files" in content
    assert "the think subagent uses only the user report plus the current system map" in content
    assert "automatically continue into evidence investigation" in content
    assert "hard gate" in content
    assert "skip_observer_reason: map-backed-minimum-intake" in content
    assert "think subagent" in content
    assert "observer_framing_completed" in content
    assert "you may perform focused leader-inline evidence work when the investigation is small and single-lane" in content
    assert "route, integrate, and decide rather than manually performing every lane sequentially" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/index.md" in content
    assert "linked learning detail docs" in content
    assert "learning start --command debug --format json" in content
    assert "manual `learning capture` helper surface" in content
    assert "manual `capture-learning` hook surface" not in content
    assert "debug cognition gate" in content
    assert "pass the cognition gate before" in content
    assert "project-cognition compass --intent debug" in content
    assert "project-cognition query --query-plan" in content
    assert "minimal_live_reads" in content
    assert "debug-handbook.md" not in content
    assert "debug-workflow-contract" not in content
    assert "symptom-to-surface-routing" not in content
    assert "system-topology-for-debug" not in content
    assert "investigation-playbooks" not in content
    assert "verification-and-exit" not in content
    assert "atlas.entry" not in content
    assert "atlas.index.status" not in content
    assert "atlas.index.atlas" not in content
    assert "if the active session is `awaiting_human_verify`" in content
    assert "start a linked follow-up session" in content
    assert "record the parent/child relationship" in content
    assert "return to the parent session to finish the original human verification" in content
    assert "same_issue" in content
    assert "derived_issue" in content
    assert "unrelated_issue" in content
    assert "contrarian candidate" in content
    assert "if cognition freshness is `missing`, continue with live repository evidence when workflow policy allows" in content
    assert "recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance" in content
    assert "if cognition freshness is `stale`, treat map output as advisory" in content
    assert "recommend `{{invoke:map-update}}` as follow-up maintenance only when the user requested cognition repair" in content
    assert "cognition freshness is `support_drift`" in content
    assert "cognition freshness is `partial_refresh`" in content
    assert "do not reflexively route to `{{invoke:map-update}}`" in content
    assert "recommended_next_action" in content
    assert "cognition freshness is `missing` or `stale`" not in content
    assert "cognition freshness is `possibly_stale`" in content
    assert "{{invoke:map-update}}" in content
    assert "truth ownership" in content
    assert "use the debug cognition slice to identify likely truth-owning layers" in content
    assert "recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance" in content
    assert "task-relevant cognition coverage is insufficient" in content
    assert "ownership or placement guidance" in content
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in content
    assert "capability-aware investigation" in content
    assert "find truth ownership before chasing symptoms" in content
    assert "control state is not observation state" in content
    assert "debug the loop, not just the point" in content
    assert "escalate diagnostics when the loop is still ambiguous" in content
    assert "subagent-assisted" in content
    assert "leader-inline" in content
    assert "subagent-blocked" in content
    assert "execution_surface: none" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "native-subagents" in content
    assert "dispatch a subagent only when the evidence-lane contract is complete" in content
    assert "enough context" not in content
    assert 'choose_subagent_dispatch(command_name="debug"' in content
    assert "leader-led" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence-gathering tasks" in content
    assert "existing logs" in content
    assert "logs are a first-class evidence source" in content
    assert "append it to `evidence` with `source_type: log`" in content
    assert "observability as insufficient" in content
    assert "diagnostic logging" in content or "instrumentation" in content
    assert "truth ownership map" in content
    assert "control state" in content
    assert "observation state" in content
    assert "closed loop" in content
    assert "execution intent" in content
    assert "success evidence" in content
    assert "decisive signals" in content
    assert "alternative_hypotheses_considered" in content
    assert "alternative_hypotheses_ruled_out" in content
    assert "investigation contract" in content
    assert "candidate queue" in content
    assert "related risk targets" in content
    assert "root-cause mode" in content
    assert "second stage must consume the candidate queue" in content
    assert "root_cause_confidence" in content
    assert "fix_scope" in content
    assert "loop_restoration_proof" in content
    assert "owning_layer" in content
    assert "broken_control_state" in content
    assert "failure_mechanism" in content
    assert "loop_break" in content
    assert "decisive_signal" in content
    assert "rejected surface fixes" in content
    assert "if automated verification or human verification fails repeatedly" in content
    assert ".planning/debug/[slug].research.md" in content
    assert "debug-local research checkpoint" in content
    assert "dispatches bounded evidence-gathering subagents" in content
    assert "durable team workflow" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "changed_code_paths" in content
    assert "changed_behavior_surfaces" in content
    assert "verification_evidence" in content
    assert "project_cognition_refresh" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "project-cognition delta append" in content
    assert "project-cognition update --delta-session" in content
    assert "project-cognition update --payload-file" in content
    assert "clean closeout keys on `result_state`" in content
    assert "not `update_id`, `last_update_id`, or freshness alone" in content
    assert "legacy recorded-only output" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "dirty only when inline update" in content
    assert "ordinary uncertain closure" in content
    assert "partial/low-confidence facts, known unknowns, and `minimal_live_reads`" in content
    assert "use map-update for ordinary existing-baseline gaps" in content
    assert "use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid" in content
    assert "returned `project-cognition query` bundle and readiness as the truth source" not in content
    assert "returned project cognition compass packet as the default intake source" in content
    assert "use only returned `minimal_live_reads` when needed" in content
    assert "debug session state" in content
    assert "competing truths" in content
    assert "coverage gaps" in content
    assert ".specify/project-map/index/status.json" not in content
    assert "complete-refresh" in content
    assert "project-cognition validate-build --format json" in content
    assert "incremental freshness finalization" in content
    assert "do not run `complete-refresh` as a rebuild finalizer" in content
    assert "{{specify-subcmd:project-cognition mark-dirty --reason \"<reason>\" --format json}}" in content
    assert "write the selected capability or symptom, evidence routes" in content
    assert "highest-signal" in content
    assert "write a failing automated repro test before changing production code" in content
    assert "do not modify production behavior until the red state is proven" in content
    assert "if no reliable automated test surface exists for the failing behavior" in content
    assert "add the missing harness first or route through `/sp-quick` or `/sp-specify`" in content
    assert "senior consequence analysis gate" in content
    assert "dependency loop" in content
    assert "affected objects" in content
    assert "adjacent risk targets" in content
    assert "reject surface-only fixes" in content
    assert "record which plausible causes were considered and which were ruled out" in content
    assert "surface-only" in content
    assert "cannot satisfy the debug contract" in content
    assert "loop restoration proof" in content
    assert "log investigation plan" in content
    assert "logs are a first-class evidence source" in content
    assert "existing logs" in content
    assert "do not enter fixing" in content or "cannot directly enter fixing" in content
    assert "fast-path gate" not in content
    assert "compressed observer framing" not in content
    assert "optional expanded observer" not in content
    assert "user can agree or decline" not in content


def test_debug_template_requires_understanding_checkpoint_before_investigation() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "## debug understanding checkpoint" in content
    assert "symptom understood" in content
    assert "expected behavior" in content
    assert "investigation boundary" in content
    assert "evidence approach" in content
    assert "success signal" in content
    assert "wait for user confirmation" in content
    assert "not a fix-plan approval" in content
    assert "not a root-cause claim" in content
    assert "understanding_confirmed: false" in content
    assert "understanding_confirmed: true" in content
    assert (
        "before reproduction commands, log review, source-code reads, test inspection, evidence collection, "
        "instrumentation, code edits, fix work, or validation commands"
    ) in content
    assert "blocks evidence investigation on resume" in content
    assert "only hand off to map maintenance after confirmation" in content


def test_debug_session_template_tracks_understanding_checkpoint() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8").lower()

    assert "understanding_confirmed" in content
    assert "## debug understanding checkpoint" in content
    assert "confirmed_symptom:" in content
    assert "confirmed_expected_behavior:" in content
    assert "confirmed_investigation_boundary:" in content
    assert "confirmed_evidence_approach:" in content
    assert "confirmed_success_signal:" in content
    assert "confirmation_notes:" in content


def test_debug_template_preserves_blocked_state_and_subagent_boundaries() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "subagent-blocked" in content
    assert "execution_surface: none" in content
    assert "unsafe, unavailable, or unpacketizable" in content
    assert "subagents may collect evidence" in content
    assert "must not update the debug file" in content
    assert "must not declare the root cause final" in content
    assert "must not transition the session state" in content


def test_debug_template_uses_stage_and_protocol_structure() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "## role" in content
    assert "## operating principles" in content
    assert "## session lifecycle" in content
    assert "## investigation protocol" in content
    assert "stage 1a: causal map" in content
    assert "stage 1b: investigation contract + log investigation plan" in content
    assert "stage 2: evidence" in content
    assert "stage 3: fix" in content
    assert "stage 4: verify" in content
    assert "## fix and verify protocol" in content
    assert "## checkpoint protocol" in content


def test_debug_template_keeps_shared_guidance_integration_neutral() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "spawn_agent" not in content
    assert "wait_agent" not in content
    assert "close_agent" not in content
    assert "specify team" not in content


def test_debug_thinker_template_documents_stage_1a_causal_map_outputs() -> None:
    content = read_template("templates/worker-prompts/debug-thinker.md").lower()

    assert "causal_map:" in content
    assert "dimension_scan" in content
    assert "candidate_board" in content
    assert "light_scores" in content
    assert "likelihood" in content
    assert "impact_radius" in content
    assert "falsifiability" in content
    assert "log_observability" in content
    assert "project cognition" in content
    assert "### project map" not in content
    assert "{project_map}" not in content
    assert "log_investigation_plan:" not in content
    assert "observer_mode:" not in content
    assert "expanded_observer:" not in content


def test_debug_session_template_uses_canonical_intake_fields() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "causal_map_completed:" in content
    assert "investigation_contract_completed:" in content
    assert "log_investigation_plan_completed:" in content
    assert "observer_framing_completed:" in content
    assert "legacy_session_needs_reintake:" in content
    assert "execution_model:" in content
    assert "leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape:" in content
    assert "leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface:" in content
    assert "leader-inline | native-subagents | none" in content
    assert "dispatch_reason:" in content
    assert "blocked_reason:" in content
    session_template = content.split("```markdown", 1)[1].split("```", 1)[0]
    frontmatter = session_template.split("---", 2)[1]
    execution_field_order = [
        "legacy_session_needs_reintake:",
        "execution_model:",
        "dispatch_shape:",
        "execution_surface:",
        "dispatch_reason:",
        "blocked_reason:",
        "waiting_on_child_human_followup:",
    ]
    execution_field_offsets = [frontmatter.index(field) for field in execution_field_order]
    assert execution_field_offsets == sorted(execution_field_offsets)
    assert "map-backed or deep canonical intake package is complete" in lowered
    assert "## Observer Framing" in content
    assert "## Transition Memo" in content
    assert "## Truth Ownership" in content
    assert "## Suggested Evidence Lanes" in content
    assert "## Control State" in content
    assert "## Observation State" in content
    assert "## Closed Loop" in content
    assert "## Execution Intent" in content
    assert "## Evidence" in content
    assert "## Investigation Contract" in content
    assert "primary_candidate_id:" in content
    assert "candidate_queue:" in content
    assert "related_risk_targets:" in content
    assert "investigation_mode:" in content
    assert "source_type: log" in content
    assert "source_ref:" in content
    assert "summary:" in content
    assert "owning_layer:" in content
    assert "broken_control_state:" in content
    assert "failure_mechanism:" in content
    assert "loop_break:" in content
    assert "decisive_signal:" in content
    assert "validation_results" in content
    assert "decisive_signals" in content
    assert "rejected_surface_fixes" in content
    assert "alternative_hypotheses_considered" in content
    assert "alternative_hypotheses_ruled_out" in content
    assert "root_cause_confidence:" in content
    assert "fix_scope:" in content
    assert "loop_restoration_proof:" in content
    assert "framing_gate_passed:" in content
    assert "waiting_on_child_human_followup:" in content
    assert "human_verification_outcome:" in content
    assert "## Log Investigation Plan" in content
    assert "## Senior Consequence Analysis" in content
    assert "affected_objects:" in content
    assert "dependency_loop:" in content
    assert "control_state:" in content
    assert "observation_state:" in content
    assert "adjacent_risk_targets:" in content
    assert "surface_only_fixes_rejected:" in content
    assert "no source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`" in lowered
    assert "observer_mode:" not in content
    assert "## Expanded Observer" not in content
