import os
import re
from pathlib import Path
import subprocess
import sys

from specify_cli.agents import CommandRegistrar
from specify_cli.integrations.base import IntegrationBase

from .template_utils import read_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_managed_block_emitters_match_across_shells() -> None:
    bash = (PROJECT_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
    ps = (PROJECT_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")

    bash_match = re.search(
        r"render_speckit_managed_block\(\)\s*\{\s*cat <<'EOF'\n(?P<block>.*?)\nEOF",
        bash,
        flags=re.S,
    )
    ps_match = re.search(
        r"function Get-SpecKitManagedBlock\b.*?@\(\s*(?P<body>.*?)\s*\)\s*-join \$Newline",
        ps,
        flags=re.S,
    )

    assert bash_match is not None
    assert ps_match is not None

    bash_block = _normalize_newlines(bash_match.group("block"))
    ps_block = _normalize_newlines(
        "\n".join(s.replace("''", "'") for s in re.findall(r"'((?:''|[^'])*)'", ps_match.group("body")))
    )
    assert bash_block == ps_block


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


def test_passive_workflow_skills_enforce_real_specify_command_surface() -> None:
    routing = read_template("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()
    map_gate = read_template("templates/passive-skills/spec-kit-project-map-gate/SKILL.md").lower()

    for content in (routing, map_gate):
        assert "specify --help" in content
        assert "generated\ncreate-feature script" in content or "generated create-feature script" in content
        assert "run `specify create-feature`" not in content
        assert "use `specify create-feature`" not in content


def test_readme_does_not_teach_specify_branch_as_a_real_command() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "specify branch" not in readme


def test_command_surfaces_require_help_verification_and_do_not_invent_feature_commands() -> None:
    surfaces = {
        "README": (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower(),
        "quickstart": (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower(),
        "specify-template": (PROJECT_ROOT / "templates" / "commands" / "specify.md").read_text(encoding="utf-8").lower(),
        "agent-template": (PROJECT_ROOT / "templates" / "agent-file-template.md").read_text(encoding="utf-8").lower(),
        "managed-bash": read_template("scripts/bash/update-agent-context.sh").lower(),
        "managed-powershell": read_template("scripts/powershell/update-agent-context.ps1").lower(),
    }

    forbidden = (
        "run `specify create-feature`",
        "use `specify create-feature`",
        "run `specify create feature`",
        "use `specify create feature`",
        "run `specify new-feature`",
        "use `specify new-feature`",
        "run `specify new feature`",
        "use `specify new feature`",
    )
    required = (
        "specify --help",
        "generated create-feature script",
    )

    for name, content in surfaces.items():
        for needle in forbidden:
            assert needle not in content, f"{name} still teaches invented command surface: {needle}"
        for needle in required:
            assert needle in content, f"{name} is missing required command-surface guidance: {needle}"


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
    assert "command shape:" in quickstart
    assert "required options:" in quickstart
    assert "command shape:" in learning_skill
    assert "required options:" in learning_skill
    assert "run `{{specify-subcmd:hook review-learning" not in learning_skill
    assert "run `{{specify-subcmd:hook capture-learning" not in learning_skill


def test_learning_contract_surfaces_do_not_ship_fake_runnable_placeholder_commands() -> None:
    learning_surface_paths = (
        PROJECT_ROOT / "src" / "specify_cli" / "hooks" / "learning.py",
        PROJECT_ROOT / "templates" / "command-partials" / "common" / "learning-layer.md",
        PROJECT_ROOT / "templates" / "passive-skills" / "spec-kit-project-learning" / "SKILL.md",
        PROJECT_ROOT / "docs" / "quickstart.md",
    )
    command_template_paths = (
        PROJECT_ROOT / "templates" / "commands" / "analyze.md",
        PROJECT_ROOT / "templates" / "commands" / "checklist.md",
        PROJECT_ROOT / "templates" / "commands" / "clarify.md",
        PROJECT_ROOT / "templates" / "commands" / "constitution.md",
        PROJECT_ROOT / "templates" / "commands" / "debug.md",
        PROJECT_ROOT / "templates" / "commands" / "deep-research.md",
        PROJECT_ROOT / "templates" / "commands" / "fast.md",
        PROJECT_ROOT / "templates" / "commands" / "implement.md",
        PROJECT_ROOT / "templates" / "commands" / "map-build.md",
        PROJECT_ROOT / "templates" / "commands" / "map-scan.md",
        PROJECT_ROOT / "templates" / "commands" / "plan.md",
        PROJECT_ROOT / "templates" / "commands" / "quick.md",
        PROJECT_ROOT / "templates" / "commands" / "specify.md",
        PROJECT_ROOT / "templates" / "commands" / "tasks.md",
        PROJECT_ROOT / "templates" / "commands" / "test-build.md",
        PROJECT_ROOT / "templates" / "commands" / "test-scan.md",
    )

    forbidden_fragments = (
        "capture-learning --command analyze ...",
        "capture-learning --command checklist ...",
        "capture-learning --command clarify ...",
        "capture-learning --command constitution ...",
        "capture-learning --command deep-research ...",
        "capture-learning --command debug ...",
        "capture-learning --command implement ...",
        "capture-learning --command map-build ...",
        "capture-learning --command map-scan ...",
        "capture-learning --command plan ...",
        "capture-learning --command specify ...",
        "capture-learning --command tasks ...",
        "capture-learning --command test-build ...",
        "capture-learning --command test-scan ...",
        "learning capture --command fast ...",
        "hook review-learning --command quick",
    )

    for path in (*learning_surface_paths, *command_template_paths):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"{path} still contains fake runnable command fragment: {fragment}"


def test_readme_learning_helper_surface_uses_command_shape_and_required_options() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "command shape:" in readme
    assert "required options:" in readme
    assert "specify learning capture --command <workflow> ..." not in readme
    assert "specify hook signal-learning --command <workflow> ..." not in readme
    assert "specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> ..." not in readme


def test_upgrade_guide_labels_agent_placeholder_upgrade_command_as_command_shape() -> None:
    upgrade = (PROJECT_ROOT / "docs" / "upgrade.md").read_text(encoding="utf-8")

    assert "Command shape:" in upgrade
    assert "specify init --here --force --ai <your-agent>" in upgrade


def test_readme_and_quickstart_label_workflow_hook_helper_surfaces_as_command_shapes() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()

    assert "specify hook preflight --command <workflow> ..." not in readme
    assert "specify hook validate-state --command <workflow> ..." not in readme
    assert "specify hook workflow-policy --command <workflow> ..." not in readme
    assert "specify hook build-compaction --command <workflow> ..." not in readme
    assert "command shape:" in readme

    assert "use `specify hook preflight --command <workflow> ...`" not in quickstart
    assert "use `specify hook validate-state --command <workflow> ...`" not in quickstart
    assert "use `specify hook checkpoint --command <workflow> ...`" not in quickstart
    assert "use `specify hook monitor-context --command <workflow> ...`" not in quickstart
    assert "command shape:" in quickstart


def test_readme_and_quickstart_label_remaining_helper_command_shapes() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()

    assert "specify implement closeout --feature-dir <feature-dir> --format json" in readme
    assert "command shape:" in readme
    assert "specify result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>" in readme
    assert "result helper command shapes:" in readme
    assert "specify quick status <id>" in readme
    assert "quick-task helper command shapes:" in readme
    assert "command shape: `specify quick status <id>`" in readme
    assert "command shape: `specify hook mark-dirty --reason " in readme

    assert "specify implement closeout --feature-dir <feature-dir> --format json" in quickstart
    assert "command shape:" in quickstart
    assert "specify eval create --recurrence-key <key> --summary" in quickstart
    assert "specify eval create --recurrence-key <key> ..." not in quickstart
    assert "quick-task helper command shapes:" in quickstart
    assert "command shape: `specify quick status <id>`" in quickstart


def test_update_agent_context_managed_block_emitters_remain_cross_shell_equivalent() -> None:
    _assert_managed_block_emitters_match_across_shells()


def test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics() -> None:
    bash = read_template("scripts/bash/update-agent-context.sh").lower()

    assert "treat `sp-*` names as canonical workflow identities" in bash
    assert "treat the learning layer as workflow-execution infrastructure" in bash
    assert "project-map complete-refresh" in bash
    assert "project-map mark-dirty" in bash
    assert "do not continue under known-stale atlas state without choosing one of those paths" in bash
    assert "structured handoff, result file, or runtime-managed result" in bash
    assert "`sp-teams` only" in bash
    assert "possibly_stale" not in bash
    assert "must_refresh_topics" not in bash
    assert "review_topics" not in bash
