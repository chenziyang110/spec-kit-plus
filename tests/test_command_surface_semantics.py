import os
from pathlib import Path
import subprocess
import sys

from specify_cli.agents import CommandRegistrar
from specify_cli.integrations.base import IntegrationBase

from .template_utils import read_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_init_generated_codex_skill_includes_invocation_note_and_projected_handoff(tmp_path: Path):
    target = tmp_path / "codex-projection"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT / "src"), env["PYTHONPATH"]]
        if env.get("PYTHONPATH")
        else [str(PROJECT_ROOT / "src")]
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path\n"
                "from typer.testing import CliRunner\n"
                "from specify_cli import app\n"
                "import sys\n"
                "target = Path(sys.argv[1])\n"
                "result = CliRunner().invoke(app, ['init', str(target), '--ai', 'codex', '--no-git', '--ignore-agent-tools', '--script', 'sh'])\n"
                "assert result.exit_code == 0, result.output\n"
                "print((target / '.codex' / 'skills' / 'sp-specify' / 'SKILL.md').read_text(encoding='utf-8'))\n"
            ),
            str(target),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    content = result.stdout

    assert "## Invocation Syntax" in content
    assert "`$sp-plan`-style syntax" in content
    assert "- **Default handoff**: /sp.plan" in content
    assert "recommend /sp.clarify" in content
    assert "through /sp.deep-research" in content
    assert "readiness for the next phase (`$sp-plan` for the mainline" in content
    assert "`next_command: /sp.plan`" in content

    passive = read_template("templates/passive-skills/python-testing/SKILL.md")
    assert "## Invocation Syntax" not in passive


def test_apply_skill_invocation_conventions_projects_user_facing_examples_by_agent():
    body = (
        "- Run /sp-plan next.\n"
        "- State token remains `next_command: /sp.plan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)
    kimi = CommandRegistrar.apply_skill_invocation_conventions("kimi", body)
    claude = CommandRegistrar.apply_skill_invocation_conventions("claude", body)

    assert "## Invocation Syntax" in codex
    assert "## Invocation Syntax" in kimi
    assert "## Invocation Syntax" in claude
    assert "canonical workflow-state identifiers and handoff values" in codex
    assert "canonical workflow-state identifiers and handoff values" in kimi
    assert "canonical workflow-state identifiers and handoff values" in claude
    assert "do not rewrite them to this integration's invocation syntax" in codex
    assert "do not rewrite them to this integration's invocation syntax" in kimi
    assert "do not rewrite them to this integration's invocation syntax" in claude
    assert "- Run $sp-plan next." in codex
    assert "- Run /skill:sp-plan next." in kimi
    assert "- Run /sp-plan next." in claude
    assert "`next_command: /sp.plan`" in codex
    assert "`next_command: /sp.plan`" in kimi
    assert "`next_command: /sp.plan`" in claude


def test_apply_skill_invocation_conventions_preserves_hyphenated_canonical_state_tokens():
    body = (
        "- **Default handoff**: /sp-test-scan\n"
        "- State token remains `next_command: /sp-test-scan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)

    assert "- **Default handoff**: $sp-test-scan" in codex
    assert "`next_command: /sp-test-scan`" in codex


def test_apply_skill_invocation_conventions_supports_agy_surface():
    body = "- Run /sp-plan next.\n"

    agy = CommandRegistrar.apply_skill_invocation_conventions("agy", body)

    assert "## Invocation Syntax" in agy
    assert "- Run $sp-plan next." in agy


def test_invoke_placeholder_projects_codex_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "codex",
        "sh",
    )

    assert rendered.endswith("Run $sp-plan next.")


def test_invoke_placeholder_projects_kimi_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:test-scan}} next.",
        "kimi",
        "sh",
    )

    assert rendered.endswith("Run /skill:sp-test-scan next.")


def test_invoke_placeholder_projects_markdown_command_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:tasks}} next.",
        "opencode",
        "sh",
    )

    assert rendered.endswith("Run /sp.tasks next.")


def test_invoke_placeholder_does_not_rewrite_canonical_tokens():
    rendered = CommandRegistrar.render_invocation_placeholders(
        "codex",
        "Run {{invoke:plan}} next; keep `/sp.plan` and `/sp-test-scan` unchanged.",
    )

    assert "Run $sp-plan next" in rendered
    assert "`/sp.plan`" in rendered
    assert "`/sp-test-scan`" in rendered


def test_workflow_routing_passive_skill_uses_placeholder_for_user_invocation_examples():
    routing = read_template("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    map_gate = read_template("templates/passive-skills/spec-kit-project-map-gate/SKILL.md")
    subagents = read_template("templates/passive-skills/subagent-driven-development/SKILL.md")
    parallel = read_template("templates/passive-skills/dispatching-parallel-agents/SKILL.md")

    assert "{{invoke:specify}}" in routing
    assert "{{invoke:map-scan}} -> {{invoke:map-build}}" in routing
    assert "Use `/sp-specify`" not in routing
    assert "Use `/sp-plan`" not in routing

    assert "{{invoke:map-scan}} -> {{invoke:map-build}}" in map_gate
    assert "use `/sp-map-scan -> /sp-map-build`" not in map_gate

    assert "{{invoke:tasks}}" in subagents
    assert "{{invoke:implement}}" in subagents
    assert "`sp-teams` only when Codex work needs durable team state" in subagents

    assert "{{invoke:quick}}" in parallel
    assert "{{invoke:implement}}" in parallel
    assert "Use `sp-teams` only when Codex work needs durable team state" in parallel


def test_readme_does_not_teach_specify_branch_as_a_real_command() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "specify branch" not in readme


def test_upgrade_guide_uses_current_runtime_repair_language() -> None:
    content = (PROJECT_ROOT / "docs" / "upgrade.md").read_text(encoding="utf-8").lower()

    assert "specify check" in content
    assert "specify integration repair" in content
    assert "/speckit." not in content


def test_specify_template_points_feature_creation_to_sp_specify_and_generated_script() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "specify.md").read_text(
        encoding="utf-8"
    )
    lowered = content.lower()

    assert "sp-specify" in content
    assert "generated create-feature script" in lowered
    assert "specify branch" not in lowered


def test_quickstart_uses_current_feature_creation_and_repair_guidance() -> None:
    content = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "generated create-feature script" in lowered
    assert "specify check" in lowered
    assert "specify integration repair" in lowered
    assert "specify branch" not in lowered


def test_learning_surfaces_do_not_reference_removed_origin_artifact_option() -> None:
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()
    learning_skill = (
        PROJECT_ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-learning"
        / "SKILL.md"
    ).read_text(encoding="utf-8").lower()

    assert "--origin-artifact" not in quickstart
    assert "--origin-artifact" not in learning_skill
    assert "review-learning --command <command-name> --terminal-status <status>" in learning_skill
