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
