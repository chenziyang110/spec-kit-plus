from pathlib import Path

from .template_utils import read_command_with_references, read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANDATORY_COMMANDS = (
    "analyze",
    "auto",
    "checklist",
    "clarify",
    "constitution",
    "deep-research",
    "explain",
    "map-build",
    "map-scan",
    "quick",
    "research",
    "taskstoissues",
)

ADAPTIVE_COMMANDS = ("plan", "tasks")
COMPLEXITY_BASED_COMMANDS = ("debug",)
READ_ONLY_EVIDENCE_LANE_COMMANDS = ("specify",)
TEAM_COMMANDS = ("implement-teams", "team")


def _read_command(name: str) -> str:
    return read_command_with_references(name)


def test_mandatory_sp_commands_require_subagents_for_substantive_tasks() -> None:
    for command_name in MANDATORY_COMMANDS:
        content = _read_command(command_name).lower()

        assert "execution_model: subagent-mandatory" in content, command_name
        assert "execution_surface: native-subagents" in content, command_name


def test_plan_and_tasks_use_adaptive_execution_instead_of_mandatory_partial() -> None:
    for command_name in ADAPTIVE_COMMANDS:
        content = _read_command(command_name).lower()

        assert "execution_model: adaptive" in content, command_name
        assert "execution_mode: light | standard | heavy" in content, command_name
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content, command_name
        assert "workflow_status: ready | blocked" in content, command_name
        assert "execution_model: subagent-mandatory" not in content, command_name


def test_implement_uses_adaptive_jit_execution() -> None:
    content = _read_command("implement").lower()

    assert "execution_model: adaptive" in content
    assert "leader-direct" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "managed-team" in content
    assert "subagent-blocked" in content
    assert "just in time" in content
    assert "event-triggered review" in content
    assert "execution_model: subagent-mandatory" not in content


def test_debug_uses_complexity_based_execution_instead_of_mandatory_subagents() -> None:
    content = _read_command("debug").lower()

    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "subagent-blocked" in content
    assert "execution_model: subagent-mandatory" not in content


def test_read_only_evidence_lane_commands_use_evidence_dispatch() -> None:
    for command_name in READ_ONLY_EVIDENCE_LANE_COMMANDS:
        content = _read_command(command_name).lower()

        assert "choose_evidence_lane_dispatch" in content, command_name
        assert "lane_mode: read-only-evidence" in content, command_name
        assert "dispatch_shape: one-subagent | parallel-subagents" in content, command_name
        assert "execution_surface: native-subagents" in content, command_name
        assert "never for source edits or artifact writes" in content, command_name
        assert "execution_model: subagent-mandatory" not in content, command_name


def test_team_commands_keep_team_surface_separate() -> None:
    for command_name in TEAM_COMMANDS:
        content = _read_command(command_name).lower()

        assert "team" in content, command_name
        assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" not in content, command_name
        assert "the leader orchestrates:" not in content, command_name
        assert "before dispatch, every subagent lane needs a task contract" not in content, command_name


def test_ordinary_templates_do_not_allow_leader_or_team_fallback_for_subagent_work() -> None:
    forbidden_phrases = (
        "keep the batch on the leader path",
        "keep the lane on the leader path",
        "default to leader explanation",
        "perform the same track decomposition sequentially",
        "run the tracks sequentially",
        "if native subagents are unavailable and a durable team path is supported",
        "fallback reason",
    )

    for command_name in ("implement", "explain", "deep-research"):
        content = _read_command(command_name).lower()

        assert "subagent-blocked" in content, command_name
        for phrase in forbidden_phrases:
            if command_name == "quick" and phrase == "leader-inline":
                continue
            if command_name == "quick" and phrase == "leader-inline":
                continue
            assert phrase not in content, f"{command_name}: {phrase}"

    implement_content = _read_command("implement").lower()
    assert "sp-teams" not in implement_content
    assert "managed-team" in implement_content
    assert "not an ordinary dispatch fallback" in implement_content


def test_mandatory_subagent_templates_block_remaining_leader_path_fallbacks() -> None:
    targeted_commands = (
        "map-build",
        "map-scan",
        "prd-build",
        "prd-scan",
        "quick",
    )
    forbidden_phrases = (
        "keep it leader path",
        "keep the lane on the leader path",
        "keep it on the leader path",
        "keep the lane on leader path",
        "keep the batch on the leader path",
        "keep it leader execution",
        "keep it leader-only",
        "leader path only while",
        "leader path only when",
        "on the leader path before dispatch",
        "on the leader path until",
        "on the leader path and finish compiling",
        "the leader must perform the same packet reads",
        "perform the same packet reads directly",
    )

    for command_name in targeted_commands:
        content = _read_command(command_name).lower()

        assert "subagent-blocked" in content, command_name
        assert "stop for escalation or recovery" in content, command_name
        for phrase in forbidden_phrases:
            if command_name == "quick" and phrase == "leader-inline":
                continue
            assert phrase not in content, f"{command_name}: {phrase}"


def test_ordinary_templates_do_not_record_subagent_blocks_as_fallbacks() -> None:
    targeted_commands = (
        "map-build",
        "plan",
        "quick",
        "specify",
        "tasks",
    )
    forbidden_phrases = (
        "execution fallback",
        "execution_fallback:",
        "record that fallback explicitly",
        "`subagent-blocked` is the last fallback",
        "fallback if any",
        "fallback reason",
        "blanket fallback label",
    )

    for command_name in targeted_commands:
        content = _read_command(command_name).lower()

        for phrase in forbidden_phrases:
            assert phrase not in content, f"{command_name}: {phrase}"


def test_task4_templates_do_not_reintroduce_ordinary_local_leader_framing() -> None:
    forbidden_phrases = (
        "before doing local implementation",
        "local implementation",
        "keep work local",
        "work local",
        "direct repository inspection",
        "direct leader",
        "leader execution",
        "managed-team",
        "sp-teams",
        "only discuss a fallback after dispatch has concretely failed",
        "discuss a fallback",
        "keep the review gate on the leader path",
        "leader path",
        "keep it leader path",
        "keep the lane on the leader path",
        "keep it on the leader path",
        "keep the lane on leader path",
        "keep the batch on the leader path",
        "prefer subagent execution only when",
    )

    for command_name in MANDATORY_COMMANDS:
        content = _read_command(command_name).lower()

        for phrase in forbidden_phrases:
            if command_name == "quick" and phrase == "leader-inline":
                continue
            assert phrase not in content, f"{command_name}: {phrase}"

    for command_name in ADAPTIVE_COMMANDS:
        content = _read_command(command_name).lower()
        assert "leader-inline" in content
        assert "capability_degraded" in content
        assert "subagent-blocked" in content
        assert "managed-team fallback is not part" in content

    for team_command in TEAM_COMMANDS:
        assert (PROJECT_ROOT / "templates" / "commands" / f"{team_command}.md").exists()
    clarify_content = _read_command("clarify").lower()

    assert "validated artifact-update subagent lane" in clarify_content
    assert "packetize the artifact update as a validated subagent lane" in clarify_content
    assert "delegate artifact enhancements through a validated subagent lane" in clarify_content
    assert "the leader owns coordination, packet validation, user-question decisions, structured-handoff review, acceptance, final status, and state consistency" in clarify_content
    assert "if the artifact update lane cannot be safely packetized or delegated, record `subagent-blocked` in `workflow-state.md` with the escalation or recovery reason and stop instead of making the artifact edits" in clarify_content

    forbidden_phrases = (
        "can be improved directly from current context",
        "prefer updating the artifacts directly",
        "apply enhancements directly to the artifact set",
        "making the edit directly",
        "leader-authored direct edits",
        "leader-authored artifact edits",
    )
    for phrase in forbidden_phrases:
        assert phrase not in clarify_content, phrase
    implement_content = _read_command("implement").lower()
    fast_content = _read_command("fast").lower()
    debug_content = _read_command("debug").lower()

    assert "choose leader-direct or delegated execution" in implement_content
    assert "the leader owns tracker truth, execution strategy, join points, blocker handling, and final validation" in implement_content
    assert "compile and validate a workertaskpacket just in time only for delegated work" in implement_content
    assert "event-triggered review" in implement_content
    assert "for implementation work, prefer subagent execution only when" not in implement_content
    assert "apply the smallest direct change" not in fast_content
    assert "the leader performs the change directly" in fast_content
    assert "no subagent dispatch" in fast_content

    assert "apply the minimum code change needed to address the confirmed root cause" in debug_content
    assert "when `execution_model: subagent-assisted`" in debug_content
    assert "delegate it through a validated subagent lane" in debug_content
    assert "when the fix cannot proceed safely" in debug_content
    assert "record `subagent-blocked`" in debug_content


def test_implement_template_requires_original_image_handoff_for_visual_tasks() -> None:
    content = _read_command("implement").lower()
    worker_prompt = read_template("templates/worker-prompts/implementer.md").lower()

    assert "runtime image item/local_image" in content
    assert "leader-authored prose summary is not a substitute" in content
    assert "materialize it to a stable project-relative artifact path" in content
    assert "do not dispatch image-backed ui implementation" in content
    assert "missing image handoff reason" in content
    assert "include every original png, screenshot, mockup, design export, or reference image" in worker_prompt
    assert "do not reduce an original visual reference to prose-only instructions" in worker_prompt
    assert "inspect the original visual input before implementing visual structure" in worker_prompt
    assert "do not implement from a controller summary alone" in worker_prompt
