from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROUTINE_HOOK_FRAGMENTS = (
    "{{specify-subcmd:hook preflight",
    "{{specify-subcmd:hook validate-state",
    "{{specify-subcmd:hook validate-artifacts",
    "{{specify-subcmd:hook validate-session-state",
    "{{specify-subcmd:hook validate-packet",
    "{{specify-subcmd:hook validate-result",
    "{{specify-subcmd:hook checkpoint",
    "{{specify-subcmd:hook monitor-context",
    "{{specify-subcmd:hook workflow-policy",
    "{{specify-subcmd:hook build-compaction",
    "{{specify-subcmd:hook render-statusline",
    "{{specify-subcmd:hook validate-read-path",
    "{{specify-subcmd:hook validate-prompt",
    "{{specify-subcmd:hook signal-learning",
    "{{specify-subcmd:hook review-learning",
    "{{specify-subcmd:hook capture-learning",
    "{{specify-subcmd:hook inject-learning",
    "{{specify-subcmd:hook mark-dirty",
    "{{specify-subcmd:hook complete-refresh",
    "specify hook preflight",
    "specify hook validate-state",
    "specify hook validate-artifacts",
    "specify hook checkpoint",
    "specify hook monitor-context",
    "specify hook workflow-policy",
    "specify hook build-compaction",
    "specify hook render-statusline",
    "specify hook validate-read-path",
    "specify hook validate-prompt",
    "specify hook validate-session-state",
    "specify hook validate-packet",
    "specify hook validate-result",
    "specify hook signal-learning",
    "specify hook review-learning",
    "specify hook capture-learning",
    "specify hook inject-learning",
    "specify hook mark-dirty",
    "specify hook complete-refresh",
)

CORE_WORKFLOW_TEMPLATES = (
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/analyze.md",
    "templates/commands/deep-research.md",
    "templates/commands/constitution.md",
    "templates/commands/implement.md",
    "templates/commands/quick.md",
    "templates/commands/debug.md",
    "templates/commands/fast.md",
    "templates/commands/clarify.md",
    "templates/commands/checklist.md",
    "templates/commands/map-scan.md",
    "templates/commands/map-build.md",
    "templates/commands/test-scan.md",
    "templates/commands/test-build.md",
)

PLANNING_TEMPLATE_EXPECTED_FRAGMENTS = {
    "templates/commands/specify.md": (
        "workflow-state.md",
        "spec.md",
        "alignment.md",
        "context.md",
    ),
    "templates/commands/plan.md": ("workflow-state.md", "plan.md"),
    "templates/commands/tasks.md": ("workflow-state.md", "tasks.md"),
    "templates/commands/analyze.md": ("workflow-state.md",),
    "templates/commands/deep-research.md": ("workflow-state.md", "deep-research.md"),
    "templates/commands/constitution.md": ("workflow-state.md", ".specify/memory/constitution.md"),
}

EXECUTION_TEMPLATE_EXPECTED_FRAGMENTS = {
    "templates/commands/implement.md": (
        "WorkerTaskPacket",
        "WorkerTaskResult",
        "structured handoff",
        "{{specify-subcmd:project-cognition complete-refresh --format json}}",
        '{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}',
    ),
    "templates/commands/quick.md": (
        "STATUS.md",
        "WorkerTaskPacket",
        "structured handoff",
        "{{specify-subcmd:project-cognition complete-refresh --format json}}",
        '{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}',
    ),
    "templates/commands/debug.md": (
        "debug session",
        "evidence",
        "{{specify-subcmd:project-cognition complete-refresh --format json}}",
        '{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}',
    ),
}


def _assert_no_routine_hook_choreography(path: str) -> None:
    content = read_template(path)
    for fragment in ROUTINE_HOOK_FRAGMENTS:
        assert fragment not in content, f"{path} still instructs routine hook choreography: {fragment}"


def test_command_templates_do_not_instruct_routine_hook_choreography() -> None:
    for path in CORE_WORKFLOW_TEMPLATES:
        _assert_no_routine_hook_choreography(path)


def test_planning_templates_preserve_state_and_artifact_outcome_requirements() -> None:
    for path, expected_fragments in PLANNING_TEMPLATE_EXPECTED_FRAGMENTS.items():
        content = read_template(path)
        lowered = content.lower()

        for fragment in expected_fragments:
            assert fragment in content, f"{path} must preserve durable output fragment: {fragment}"
        assert "state" in lowered, f"{path} must mention durable state outcomes"
        if path != "templates/commands/constitution.md":
            assert "artifact" in lowered, f"{path} must mention artifact outcomes"


def test_execution_templates_preserve_contract_outcomes_without_hook_commands() -> None:
    for path, expected_fragments in EXECUTION_TEMPLATE_EXPECTED_FRAGMENTS.items():
        content = read_template(path)

        for fragment in expected_fragments:
            assert fragment in content, f"{path} must preserve execution contract fragment: {fragment}"
        _assert_no_routine_hook_choreography(path)
