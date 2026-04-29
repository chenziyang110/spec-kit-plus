from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_debug_template_documents_capability_aware_investigation() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "you are not the default evidence worker for every lane" in content
    assert "route, integrate, and decide rather than manually performing every lane sequentially" in content
    assert "stay on the leader path unless the current strategy truly remains `single-agent`" in content
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/project-learnings.md" in content
    assert ".planning/learnings/candidates.md" in content
    assert "specify learning start --command debug --format json" in content
    assert "specify learning capture --command debug" in content
    assert "read `project-handbook.md`" in content
    assert ".specify/project-map/index/status.json" in content
    assert "if the active session is `awaiting_human_verify`" in content
    assert "start a linked follow-up session" in content
    assert "record the parent/child relationship" in content
    assert "return to the parent session to finish the original human verification" in content
    assert "project-map freshness helper" in content
    assert "freshness is `missing` or `stale`" in content
    assert "freshness is `possibly_stale`" in content
    assert "must_refresh_topics" in content
    assert "review_topics" in content
    assert "truth ownership" in content
    assert "read whichever of `architecture.md`, `workflows.md`, `integrations.md`, `testing.md`, and `operations.md` map to the failing area" in content
    assert "if the handbook navigation system is missing" in content
    assert "run `/sp-map-codebase` before root-cause analysis continues" in content
    assert "task-relevant coverage is insufficient" in content
    assert "ownership or placement guidance" in content
    assert "workflow, constraint, integration, or regression-sensitive testing guidance" in content
    assert "capability-aware investigation" in content
    assert "find truth ownership before chasing symptoms" in content
    assert "control state is not observation state" in content
    assert "debug the loop, not just the point" in content
    assert "escalate diagnostics when the loop is still ambiguous" in content
    assert "single-agent" in content
    assert "native-multi-agent" in content
    assert "sidecar-runtime" in content
    assert 'choose_execution_strategy(command_name="debug"' in content
    assert "leader-led" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence-gathering tasks" in content
    assert "existing logs" in content
    assert "observability as insufficient" in content
    assert "diagnostic logging" in content or "instrumentation" in content
    assert "truth ownership map" in content
    assert "control state" in content
    assert "observation state" in content
    assert "closed loop" in content
    assert "execution intent" in content
    assert "success evidence" in content
    assert "decisive signals" in content
    assert "owning_layer" in content
    assert "broken_control_state" in content
    assert "failure_mechanism" in content
    assert "loop_break" in content
    assert "decisive_signal" in content
    assert "rejected surface fixes" in content
    assert "if automated verification or human verification fails repeatedly" in content
    assert ".planning/debug/[slug].research.md" in content
    assert "debug-local research checkpoint" in content
    assert "native delegation surface" in content
    assert "coordinated runtime surface" in content
    assert "verification is truthfully green and no explicit blocker prevents completion" in content
    assert "run `/sp-map-codebase` before moving to `awaiting_human_verify` or `resolved`" in content
    assert "mark `.specify/project-map/index/status.json` dirty" in content
    assert "if you cannot complete that refresh in the current pass" in content
    assert "highest-signal" in content


def test_debug_template_uses_stage_and_protocol_structure() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "## role" in content
    assert "## operating principles" in content
    assert "## session lifecycle" in content
    assert "## investigation protocol" in content
    assert "stage 1: symptom intake" in content
    assert "stage 2: reproduction gate" in content
    assert "stage 3: log review" in content
    assert "required framing before hypothesis" in content
    assert "stage 4: observability assessment" in content
    assert "stage 5: hypothesis formation" in content
    assert "stage 6: experiment loop" in content
    assert "stage 7: root cause confirmation" in content
    assert "## fix and verify protocol" in content
    assert "## checkpoint protocol" in content


def test_debug_template_keeps_shared_guidance_integration_neutral() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "debug.md").read_text(encoding="utf-8").lower()

    assert "spawn_agent" not in content
    assert "wait_agent" not in content
    assert "close_agent" not in content
    assert "specify team" not in content


def test_debug_session_template_captures_control_plane_debugging_fields() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8")

    assert "## Truth Ownership" in content
    assert "## Suggested Evidence Lanes" in content
    assert "## Control State" in content
    assert "## Observation State" in content
    assert "## Closed Loop" in content
    assert "## Execution Intent" in content
    assert "summary:" in content
    assert "owning_layer:" in content
    assert "broken_control_state:" in content
    assert "failure_mechanism:" in content
    assert "loop_break:" in content
    assert "decisive_signal:" in content
    assert "validation_results" in content
    assert "decisive_signals" in content
    assert "rejected_surface_fixes" in content
