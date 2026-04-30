from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORDINARY_COMMANDS = (
    "analyze",
    "auto",
    "checklist",
    "clarify",
    "constitution",
    "debug",
    "deep-research",
    "explain",
    "fast",
    "implement",
    "map-build",
    "map-scan",
    "plan",
    "quick",
    "research",
    "specify",
    "tasks",
    "taskstoissues",
    "test",
    "test-build",
    "test-scan",
)

TEAM_COMMANDS = ("implement-teams", "team")


def _read_command(name: str) -> str:
    return (PROJECT_ROOT / "templates" / "commands" / f"{name}.md").read_text(encoding="utf-8")


def test_all_ordinary_sp_commands_require_subagents_for_substantive_tasks() -> None:
    for command_name in ORDINARY_COMMANDS:
        content = _read_command(command_name).lower()

        assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in content, command_name
        assert "the leader orchestrates:" in content, command_name
        assert "before dispatch, every subagent lane needs a task contract" in content, command_name
        assert "structured handoff" in content, command_name
        assert "execution_model: subagent-mandatory" in content, command_name
        assert "dispatch_shape: one-subagent | parallel-subagents" in content, command_name
        assert "execution_surface: native-subagents" in content, command_name


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
            assert phrase not in content, f"{command_name}: {phrase}"

    implement_content = _read_command("implement").lower()
    assert "sp-teams" not in implement_content
    assert "managed-team" not in implement_content


def test_mandatory_subagent_templates_block_remaining_leader_path_fallbacks() -> None:
    targeted_commands = (
        "debug",
        "map-build",
        "map-scan",
        "quick",
        "test-build",
        "test-scan",
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
            assert phrase not in content, f"{command_name}: {phrase}"


def test_ordinary_templates_do_not_record_subagent_blocks_as_fallbacks() -> None:
    targeted_commands = (
        "map-build",
        "plan",
        "quick",
        "specify",
        "tasks",
        "test-build",
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
        "leader-inline",
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

    for command_name in ORDINARY_COMMANDS:
        content = _read_command(command_name).lower()

        for phrase in forbidden_phrases:
            assert phrase not in content, f"{command_name}: {phrase}"

    for team_command in TEAM_COMMANDS:
        assert (PROJECT_ROOT / "templates" / "commands" / f"{team_command}.md").exists()


def test_test_build_template_delegates_shared_and_high_risk_serial_lanes() -> None:
    content = _read_command("test-build").lower()

    assert "packetize it as a validated serial subagent lane" in content
    assert "leader owns only the coordination, sequencing, review, and acceptance gate" in content
    assert "the leader owns coordination, review, and acceptance only" in content
    assert "record `subagent-blocked` with the escalation or recovery reason and stop instead of making the edit directly" in content
    assert "record `subagent-blocked` and stop for escalation or recovery" in content

    forbidden_phrases = (
        "treat that work as a leader-owned coordination gate",
        "production-code edits are leader-owned",
        "leader-owned unless the packet explicitly grants a serial lane",
    )
    for phrase in forbidden_phrases:
        assert phrase not in content, phrase


def test_clarify_template_delegates_artifact_update_lanes() -> None:
    content = _read_command("clarify").lower()

    assert "validated artifact-update subagent lane" in content
    assert "packetize the artifact update as a validated subagent lane" in content
    assert "delegate artifact enhancements through a validated subagent lane" in content
    assert "the leader owns coordination, packet validation, user-question decisions, structured-handoff review, acceptance, final status, and state consistency" in content
    assert "if the artifact update lane cannot be safely packetized or delegated, record `subagent-blocked` in `workflow-state.md` with the escalation or recovery reason and stop instead of making the artifact edits" in content

    forbidden_phrases = (
        "can be improved directly from current context",
        "prefer updating the artifacts directly",
        "apply enhancements directly to the artifact set",
        "making the edit directly",
        "leader-authored direct edits",
        "leader-authored artifact edits",
    )
    for phrase in forbidden_phrases:
        assert phrase not in content, phrase


def test_implement_template_does_not_reintroduce_optional_subagent_wording() -> None:
    content = _read_command("implement").lower()

    assert "substantive implementation lanes must be delegated" in content
    assert "leader owns sequencing, review, and acceptance" in content
    assert "for implementation work, prefer subagent execution only when" not in content


def test_fast_and_debug_templates_do_not_frame_fixes_as_direct_leader_implementation() -> None:
    fast_content = _read_command("fast").lower()
    debug_content = _read_command("debug").lower()

    assert "apply the smallest direct change" not in fast_content
    assert "packetize the smallest safe low-risk change" in fast_content
    assert "delegate it through one subagent lane" in fast_content
    assert "a tightly scoped delegated change" in fast_content

    assert "apply the smallest fix that addresses the confirmed root cause" not in debug_content
    assert "packetize the smallest safe fix that addresses the confirmed root cause" in debug_content
    assert "delegate it through a validated subagent lane" in debug_content
    assert "record `subagent-blocked` with the escalation or recovery reason instead of making the fix directly" in debug_content
