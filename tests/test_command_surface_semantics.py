import os
import re
from pathlib import Path
import subprocess
import sys

import pytest

from specify_cli.agents import CommandRegistrar
from specify_cli.integrations.base import IntegrationBase

from .template_utils import (
    read_command_with_references,
    read_skill_with_references,
    read_template,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASSIVELY_INVOCABLE_CLASSIC_SKILLS = set()


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_managed_block_emitters_match_across_shells() -> None:
    bash = (PROJECT_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(
        encoding="utf-8"
    )
    ps = (
        PROJECT_ROOT / "scripts" / "powershell" / "update-agent-context.ps1"
    ).read_text(encoding="utf-8")

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
        "\n".join(
            s.replace("''", "'")
            for s in re.findall(r"'((?:''|[^'])*)'", ps_match.group("body"))
        )
    )
    assert bash_block == ps_block


def test_classic_workflow_skills_do_not_allow_passive_invocation():
    assert (
        CommandRegistrar.PASSIVELY_INVOCABLE_CLASSIC_SKILLS
        == PASSIVELY_INVOCABLE_CLASSIC_SKILLS
    )

    for skill_name in (
        "sp-debug",
        "sp-discussion",
        "sp-fast",
        "sp-quick",
        "sp-plan",
        "sp-specify",
        "sp-implement",
        "sp-map-update",
    ):
        assert not CommandRegistrar.is_passively_invocable_classic_skill(skill_name)


@pytest.mark.parametrize("agent_name", ("claude", "cursor-agent", "grok", "kimi"))
def test_native_skill_frontmatter_blocks_model_invocation_for_all_workflows(
    agent_name: str,
):
    direct_delivery = CommandRegistrar.build_skill_frontmatter(
        agent_name,
        "sp-quick",
        "Use when direct delivery is appropriate.",
        "templates/commands/quick.md",
    )
    restricted = CommandRegistrar.build_skill_frontmatter(
        agent_name,
        "spx-plan",
        "Use when implementation planning is required.",
        "templates/advanced-skills/spx-plan/SKILL.md",
    )

    assert direct_delivery["disable-model-invocation"] is True
    assert restricted["disable-model-invocation"] is True
    if agent_name in {"claude", "grok"}:
        assert direct_delivery["user-invocable"] is True
        assert restricted["user-invocable"] is True


@pytest.mark.parametrize(
    "agent_name",
    ("agy", "claude", "codex", "cursor-agent", "grok", "kimi", "trae", "vibe", "zcode"),
)
def test_standard_skill_description_requires_explicit_user_invocation(
    agent_name: str,
):
    for skill_name in ("sp-quick", "sp-debug", "sp-plan", "spx-plan"):
        frontmatter = CommandRegistrar.build_skill_frontmatter(
            agent_name,
            skill_name,
            "Use when implementation planning is required.",
            "templates/commands/plan.md",
        )

        assert frontmatter["description"].startswith("User-invoked workflow only:")
        assert "Do not select it automatically." in frontmatter["description"]


def test_passive_workflow_router_is_removed() -> None:
    assert not (
        PROJECT_ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-workflow-routing"
        / "SKILL.md"
    ).exists()


@pytest.mark.parametrize(
    "relative_path",
    (
        "AGENTS.md",
        "PROJECT-HANDBOOK.md",
        "README.md",
        "templates/project-handbook-template.md",
    ),
)
def test_product_guidance_requires_explicit_invocation_for_both_workflow_profiles(
    relative_path: str,
):
    content = read_template(relative_path)
    normalized = " ".join(content.lower().split())

    assert "all `sp-*` and `spx-*` workflow skills are user-invoked only" in normalized
    assert "passive routing may recommend" not in normalized
    assert "recommend the projected invocation" not in normalized
    assert "passive model invocation is allowed only" not in normalized
    assert "passive model invocation has one exact allowlist" not in normalized


@pytest.mark.parametrize(
    "template_path",
    (
        "templates/passive-skills/dispatching-parallel-agents/SKILL.md",
        "templates/passive-skills/project-to-prd/SKILL.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/subagent-driven-development/SKILL.md",
    ),
)
def test_passive_routing_skills_require_manual_entry_for_restricted_workflows(
    template_path: str,
) -> None:
    normalized = " ".join(read_template(template_path).lower().split())

    assert "recommend" in normalized
    assert (
        "user-invoked only" in normalized
        or "explicit user invocation" in normalized
        or "explicitly invokes" in normalized
    )


def test_init_generated_codex_skill_includes_invocation_note_and_projected_handoff(
    tmp_path: Path,
):
    target = tmp_path / "codex-projection"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT / "src"), env["PYTHONPATH"]]
        if env.get("PYTHONPATH")
        else [str(PROJECT_ROOT / "src")]
    )

    subprocess.run(
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
    content = read_skill_with_references(
        target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    )

    assert "## Invocation Syntax" in content
    assert "`$sp-plan`-style syntax" in content
    assert "semantic_delta" in content
    assert "spec-contract.json" in content
    assert "/sp.plan" in content
    assert "/sp.specify" in content
    assert "/sp.deep-research" in content
    assert "Choose exactly one next command" in content
    assert "`next_action`" in content or "next_action" in content

    passive = read_template("templates/passive-skills/python-testing/SKILL.md")
    assert "## Invocation Syntax" not in passive


def test_apply_skill_invocation_conventions_projects_user_facing_examples_by_agent():
    body = "- Run /sp-plan next.\n- State token remains `next_command: /sp.plan`.\n"

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
        "- **Default handoff**: /sp-map-scan\n"
        "- State token remains `next_command: /sp-map-scan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)

    assert "- **Default handoff**: $sp-map-scan" in codex
    assert "`next_command: /sp-map-scan`" in codex


def test_apply_skill_invocation_conventions_supports_agy_surface():
    body = "- Run /sp-plan next.\n"

    agy = CommandRegistrar.apply_skill_invocation_conventions("agy", body)

    assert "## Invocation Syntax" in agy
    assert "- Run $sp-plan next." in agy


def test_apply_skill_invocation_conventions_supports_zcode_surface():
    body = "- Run /sp-plan next.\n- State token remains `next_command: /sp.plan`.\n"

    zcode = CommandRegistrar.apply_skill_invocation_conventions("zcode", body)

    assert "## Invocation Syntax" in zcode
    assert "- Run $sp-plan next." in zcode
    assert "`next_command: /sp.plan`" in zcode


def test_apply_skill_invocation_conventions_supports_grok_surface():
    body = "- Run /sp-plan next.\n- State token remains `next_command: /sp.plan`.\n"

    grok = CommandRegistrar.apply_skill_invocation_conventions("grok", body)

    assert "## Invocation Syntax" in grok
    assert "- Run /sp-plan next." in grok
    assert "`next_command: /sp.plan`" in grok


def test_invoke_placeholder_projects_codex_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "codex",
        "sh",
    )

    assert rendered.endswith("Run $sp-plan next.")


def test_invoke_placeholder_projects_kimi_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:map-scan}} next.",
        "kimi",
        "sh",
    )

    assert rendered.endswith("Run /skill:sp-map-scan next.")


def test_invoke_placeholder_projects_zcode_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "zcode",
        "sh",
    )

    assert rendered.endswith("Run $sp-plan next.")


def test_invoke_placeholder_projects_grok_skill_surface():
    rendered = IntegrationBase.process_template(
        "---\n---\nRun {{invoke:plan}} next.",
        "grok",
        "sh",
    )

    assert rendered.endswith("Run /sp-plan next.")


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
        "Run {{invoke:plan}} next; keep `/sp.plan` and `/sp-map-scan` unchanged.",
    )

    assert "Run $sp-plan next" in rendered
    assert "`/sp.plan`" in rendered
    assert "`/sp-map-scan`" in rendered


def test_remaining_passive_skills_use_placeholder_for_user_invocation_examples():
    cognition_gate = read_template(
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"
    )
    subagents = read_template(
        "templates/passive-skills/subagent-driven-development/SKILL.md"
    )
    parallel = read_template(
        "templates/passive-skills/dispatching-parallel-agents/SKILL.md"
    )

    assert "{{invoke:map-scan}} -> {{invoke:map-build}}" in cognition_gate
    assert "use `/sp-map-scan -> /sp-map-build`" not in cognition_gate

    assert "{{invoke:tasks}}" in subagents
    assert "{{invoke:implement}}" in subagents
    assert "`sp-teams` only when Codex work needs durable team state" in subagents

    assert "{{invoke:quick}}" in parallel
    assert "{{invoke:implement}}" in parallel
    assert "Use `sp-teams` only when Codex work needs durable team state" in parallel


def test_passive_workflow_skills_enforce_real_specify_command_surface() -> None:
    cognition_gate = read_template(
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"
    ).lower()

    for content in (cognition_gate,):
        assert "{{specify-subcmd:specify-runtime api list --format json}}" in content
        assert (
            "generated\ncreate-feature script" in content
            or "generated create-feature script" in content
        )
        assert ".specify/scripts/bash/create-new-feature.sh" in content
        assert ".specify/scripts/powershell/create-new-feature.ps1" in content
        assert "run `specify create-feature`" not in content
        assert "use `specify create-feature`" not in content


def test_readme_does_not_teach_specify_branch_as_a_real_command() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "specify branch" not in readme


def test_command_surfaces_require_help_verification_and_do_not_invent_feature_commands() -> (
    None
):
    surfaces = {
        "README": (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower(),
        "quickstart": (PROJECT_ROOT / "docs" / "quickstart.md")
        .read_text(encoding="utf-8")
        .lower(),
        "specify-template": read_command_with_references("specify").lower(),
        "managed-bash": read_template("scripts/bash/update-agent-context.sh").lower(),
        "managed-powershell": read_template(
            "scripts/powershell/update-agent-context.ps1"
        ).lower(),
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
        "generated create-feature script",
        ".specify/scripts/bash/create-new-feature.sh",
        ".specify/scripts/powershell/create-new-feature.ps1",
    )

    for name, content in surfaces.items():
        for needle in forbidden:
            assert needle not in content, (
                f"{name} still teaches invented command surface: {needle}"
            )
        for needle in required:
            assert needle in content, (
                f"{name} is missing required command-surface guidance: {needle}"
            )
        assert (
            "specify --help" in content
            or "{{specify-cli}} --help" in content
            or "{{specify-subcmd:specify-runtime api list --format json}}" in content
            or "{{specify-runtime-cli}} api list --format json" in content
        ), f"{name} is missing launcher-aware help verification"


def test_upgrade_guide_uses_current_runtime_repair_language() -> None:
    content = (PROJECT_ROOT / "docs" / "upgrade.md").read_text(encoding="utf-8").lower()

    assert "specify check" in content
    assert "specify integration repair" in content
    assert "/speckit." not in content


def test_specify_template_points_feature_creation_to_sp_specify_and_generated_script() -> (
    None
):
    content = read_command_with_references("specify")
    lowered = content.lower()

    assert "sp-specify" in content
    assert "generated create-feature script" in lowered
    assert "run `{script}` from the repo root" in lowered
    assert "if the feature-creation script exits non-zero" in lowered
    assert "lane register" not in lowered
    assert "specify branch" not in lowered


def test_command_templates_do_not_declare_unused_script_frontmatter() -> None:
    commands_dir = PROJECT_ROOT / "templates" / "commands"

    for path in sorted(commands_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        frontmatter, _ = CommandRegistrar.parse_frontmatter(content)
        rendered_body = read_command_with_references(path.stem)
        scripts = frontmatter.get("scripts")
        agent_scripts = frontmatter.get("agent_scripts")

        if scripts:
            assert "{SCRIPT}" in rendered_body, (
                f"{path.name} declares scripts: but never consumes {{SCRIPT}}"
            )
        if agent_scripts:
            assert "{AGENT_SCRIPT}" in rendered_body, (
                f"{path.name} declares agent_scripts: but never consumes {{AGENT_SCRIPT}}"
            )


def test_ask_surface_is_read_only_stateless_and_has_no_specify_helper() -> None:
    command = read_template("templates/commands/ask.md")
    shell = read_template("templates/command-partials/ask/shell.md")
    cognition_gate = read_template(
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"
    )
    combined = "\n".join([command, shell, cognition_gate])
    lowered = combined.lower()

    assert "read-only" in lowered
    assert "do not create `.specify/ask/`" in lowered
    assert "do not write handoff files" in lowered
    assert "do not run tests" in lowered
    assert "do not run builds" in lowered
    assert "do not run package managers" in lowered
    assert "do not launch apps or servers" in lowered
    assert "do not execute project cli commands" in lowered
    assert "do not invoke another `sp-*` workflow automatically" in lowered
    assert "allowed operations are narrow file reads, `rg`" in lowered
    assert "specify-runtime cognition compass --intent ask" in combined
    assert "specify ask" not in lowered
    assert "commits that are already available locally" not in lowered
    assert "commit history" not in lowered
    assert "git log" not in lowered
    assert "git show" not in lowered
    assert "only after you build a semantic intake or query plan" in lowered
    assert (
        "compass output or live evidence is ambiguous or has incomplete coverage"
        in lowered
    )
    assert "stale or localization-sensitive results are examples" in lowered
    assert (
        'specify-runtime cognition query --intent ask --query-plan "<query_plan_json>" --format json'
        in combined
    )
    assert (
        "specify-runtime cognition query --intent ask --query-plan '<inline-json>' --format json"
        in combined
    )
    assert "never create a query-plan file" in lowered
    assert "only after the agent builds a semantic\n  intake or query plan" in combined
    assert (
        "compass output or live evidence is ambiguous\n  or has incomplete coverage"
        in combined
    )
    assert "Stale or localization-sensitive cases are examples" in combined
    assert "still require that ambiguity or incomplete-coverage reason" in combined
    assert "same-topic follow-up" in lowered
    assert "reuse the previous evidence set" in lowered
    assert "one-sentence evidence route" in lowered
    assert "localized, mixed-language, cjk, colloquial, or project-slang" in lowered
    assert "project-language search terms" in lowered
    assert "proven from live evidence" in lowered
    assert "inferred from live evidence" in lowered
    assert "client fields or callsites" in lowered
    assert "interface urls or payload/schema names" in lowered
    assert "whether backend/server/runtime code exists" in lowered


def test_design_command_declares_change_scoped_workflow_contract() -> None:
    content = read_template("templates/commands/design.md")
    raw = (PROJECT_ROOT / "templates" / "commands" / "design.md").read_text(
        encoding="utf-8"
    )

    assert (
        "description: Use when `specify-runtime design` must route one prompt to create, refine, or audit one bounded UI design change"
        in content
    )
    assert "primary_outputs" in content
    assert ".specify/design/changes/<UD-ID>/design-change.md" in content
    assert ".specify/design/index.json" in content
    assert "specify-runtime design change" in content
    assert "specify-runtime design register" in content
    assert "No root design contract participates" in content
    assert "read-only legacy baseline" not in content
    assert "{{spec-kit-include: ../command-partials/design/shell.md}}" in raw


def test_classic_and_advanced_design_contracts_pin_exact_change_identity() -> None:
    classic = read_template("templates/commands/design.md")
    advanced = read_template("templates/advanced-skills/spx-design/SKILL.md")

    for content in (classic, advanced):
        assert ".specify/design/changes/<UD-ID>/design-change.md" in content
        assert ".specify/design/changes/<UD-ID>/design-contract.json" in content
        assert ".specify/design/index.json" in content
        assert "specify-runtime design register" in content
        assert "supersedes" in content
        assert "never silently retarget" in content


def test_classic_and_advanced_design_image_routes_import_external_outputs() -> None:
    classic = "\n".join(
        [
            read_template("templates/command-partials/design/shell.md"),
            read_template(
                "templates/command-references/design/image-generation-studio.md"
            ),
        ]
    ).lower()
    advanced = "\n".join(
        [
            read_template("templates/advanced-skills/spx-design/SKILL.md"),
            read_template(
                "templates/advanced-skills/spx-design/references/image-round.md"
            ),
        ]
    ).lower()

    for content in (classic, advanced):
        assert (
            "specify-runtime design import <saved-image-path> --change <ud-id> "
            "--round nn --format json"
        ) in " ".join(content.split())
        assert "returned change-local path" in content
        assert "never copy" in content
        assert "design approve" in content


def test_classic_and_advanced_design_preflight_uses_exact_capabilities_and_recovery() -> None:
    classic = " ".join(
        read_template("templates/command-partials/design/shell.md").lower().split()
    )
    advanced = " ".join(
        read_template("templates/advanced-skills/spx-design/SKILL.md")
        .lower()
        .split()
    )

    for content in (classic, advanced):
        assert "specify-runtime api list --format json" in content
        assert "specify-runtime design --help" in content
        assert "never guess" in content
        assert "design.status" in content
        assert "design.synthesize" in content
        assert "design handoff" in content
        assert "design validate" in content
        assert "specify-runtime board reconcile" in content
        assert "specify-runtime board show" in content
        assert ".specify/design/changes/<ud-id>" in content
        assert "never claim `.specify/design`" in content
        assert "recovery hold" in content
        assert "show_argv" in content
        assert "resume" in content
        assert "abandon" in content


def test_specify_routes_pending_substantive_ui_through_design_before_plan() -> None:
    classic = " ".join(
        read_template("templates/commands/specify.md").lower().split()
    )
    advanced = " ".join(
        (
            read_template("templates/advanced-skills/spx-specify/SKILL.md")
            + "\n"
            + read_template(
                "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md"
            )
        )
        .lower()
        .split()
    )
    plan_surfaces = " ".join(
        (
            read_template("templates/command-partials/plan/shell.md")
            + "\n"
            + read_template("templates/advanced-skills/spx-plan/SKILL.md")
            + "\n"
            + read_template(
                "templates/advanced-skills/spx-plan/references/planning-contract.md"
            )
        )
        .lower()
        .split()
    )

    for content in (classic, advanced):
        assert "design_gate" in content
        assert "decision=required" in content or "decision: required" in content
        assert "/sp.design" in content
        assert "planning-ready" in content
        assert "formal-post-specify" in content
        assert "do not" in content and "invoke" in content

    assert "design_adoption_binding" in plan_surfaces
    assert "specify-runtime design adoption" in plan_surfaces
    assert "unchanged" in plan_surfaces and "source spec" in plan_surfaces
    assert "missing" in plan_surfaces and "blocks plan" in plan_surfaces


def test_classic_and_advanced_design_workflows_publish_scope_aware_iteration() -> None:
    classic = "\n".join(
        [
            read_template("templates/commands/design.md"),
            read_template("templates/command-references/design/task-router.md"),
            read_template("templates/command-references/design/consumer-contract.md"),
        ]
    ).lower()
    advanced = "\n".join(
        [
            read_template("templates/advanced-skills/spx-design/SKILL.md"),
            read_template(
                "templates/advanced-skills/spx-design/references/task-router.md"
            ),
            read_template(
                "templates/advanced-skills/spx-design/references/design-contract.md"
            ),
            read_template(
                "templates/advanced-skills/spx-design/references/consumer-contract.md"
            ),
        ]
    ).lower()

    for content in (classic, advanced):
        for command in (
            "specify-runtime design iterate",
            "specify-runtime design resolve",
            "specify-runtime design diff",
            "specify-runtime design impact",
            "specify-runtime design adopt",
            "specify-runtime design adoption",
        ):
            assert command in content
        assert "iteration_of" in content
        assert "basis_sha256" in content
        assert "superseded_scopes" in content
        assert "discovery only" in content
        assert "composite" in content
        assert "split" in content
        assert "singular" in content
        assert "independently bound" in content


def test_formal_and_quick_consumers_use_explicit_design_adoption_transactions() -> None:
    formal_surfaces = (
        read_template("templates/commands/specify.md"),
        read_template(
            "templates/advanced-skills/spx-specify/references/ui-and-handoffs.md"
        ),
    )
    quick_surfaces = (
        read_template("templates/command-references/quick/packetized-work.md"),
        read_template("templates/advanced-skills/spx-quick/SKILL.md"),
    )

    for content in formal_surfaces:
        lowered = content.lower()
        assert "specify-runtime design resolve" in lowered
        assert "specify-runtime design diff" in lowered
        assert "specify-runtime design impact" in lowered
        assert "specify-runtime design adopt" in lowered
        assert "--mode formal" in lowered
        assert "--expected-change" in lowered
        assert "--binding-sha256" in lowered
        assert "spec-contract.json" in lowered
        assert "before" in lowered and "adopt" in lowered
        assert "singular" in lowered
        assert "independently bound" in lowered
        assert "preserved_bindings" in lowered
        assert "invalidated_bindings" in lowered
        assert "reconcile_from" in lowered

    for content in quick_surfaces:
        lowered = content.lower()
        assert "specify-runtime design resolve" in lowered
        assert "specify-runtime design diff" in lowered
        assert "specify-runtime design impact" in lowered
        assert "specify-runtime design adopt" in lowered
        assert "--mode quick" in lowered
        assert "--expected-change" in lowered
        assert "--binding-sha256" in lowered
        assert "checkpoint amendment" in lowered
        assert "ui design binding" in lowered
        assert "ui_design_binding" in lowered
        assert "confirmation.json" in lowered
        assert "decision.ui_confirmation.design_binding" in lowered
        assert "confirmation-protected" in lowered or "confirmation_digest" in lowered
        assert "must match" in lowered or "match exactly" in lowered
        assert "confirmed" in lowered and "inherited" in lowered
        assert "runtime-managed" in lowered
        assert "status" in lowered and "projection" in lowered
        assert "retire unstarted" in lowered
        assert "completed work" in lowered and "corrective work item" in lowered
        assert "affected review" in lowered

    classic_quick = quick_surfaces[0].lower()
    advanced_quick = quick_surfaces[1].lower()
    assert "understanding_confirmed: true" in classic_quick
    assert "understanding_confirmed" not in advanced_quick


def test_templates_include_design_quality_sections() -> None:
    assert "## Experience Requirements" in read_template("templates/spec-template.md")
    assert "UI Reference Processing" in read_template("templates/spec-template.md")
    assert "ui-reference-notes.md" in read_template("templates/spec-template.md")
    assert "ui-brief.md" in read_template("templates/spec-template.md")
    assert "## Design Change Adoption" in read_template("templates/plan-template.md")
    assert "Design Quality Coverage" in read_template("templates/tasks-template.md")
    assert (
        "design-system" in read_template("templates/workflow-state-template.md").lower()
    )


def test_generated_codex_sp_specify_skill_exposes_create_feature_command_and_stop_gate(
    tmp_path: Path,
):
    target = tmp_path / "codex-specify-entrypoint"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT / "src"), env["PYTHONPATH"]]
        if env.get("PYTHONPATH")
        else [str(PROJECT_ROOT / "src")]
    )

    subprocess.run(
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
    content = read_skill_with_references(
        target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    ).lower()

    assert ".specify/scripts/bash/create-new-feature.sh" in content
    assert (
        'run `.specify/scripts/bash/create-new-feature.sh "$arguments"` from the repo root'
        in content
    )
    assert "if the feature-creation script exits non-zero" in content
    assert "lane register" not in content


def test_generated_codex_cognition_skill_exposes_create_feature_helper_paths(
    tmp_path: Path,
):
    target = tmp_path / "codex-passive-skill-entrypoint"
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
                "name = 'spec-kit-project-cognition-gate'\n"
                "print(f'## {name}')\n"
                "print((target / '.codex' / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8'))\n"
            ),
            str(target),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    content = result.stdout.lower()

    assert ".specify/scripts/bash/create-new-feature.sh" in content
    assert ".specify/scripts/powershell/create-new-feature.ps1" in content


def test_quickstart_uses_current_feature_creation_and_repair_guidance() -> None:
    content = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    lowered = content.lower()

    assert "generated create-feature script" in lowered
    assert ".specify/scripts/bash/create-new-feature.sh" in lowered
    assert ".specify/scripts/powershell/create-new-feature.ps1" in lowered
    assert "specify check" in lowered
    assert "specify integration repair" in lowered
    assert "specify branch" not in lowered


def test_learning_surfaces_do_not_reference_removed_origin_artifact_option() -> None:
    quickstart = (
        (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()
    )
    learning_skill = (
        (
            PROJECT_ROOT
            / "templates"
            / "passive-skills"
            / "spec-kit-project-learning"
            / "SKILL.md"
        )
        .read_text(encoding="utf-8")
        .lower()
    )

    assert "--origin-artifact" not in quickstart
    assert "--origin-artifact" not in learning_skill
    assert "command shape:" in quickstart
    assert "required options:" in quickstart
    assert "command shape:" in learning_skill
    assert "required options:" in learning_skill
    assert "run `{{specify-subcmd:hook review-learning" not in learning_skill
    assert "run `{{specify-subcmd:hook capture-learning" not in learning_skill


def test_learning_contract_surfaces_do_not_ship_fake_runnable_placeholder_commands() -> (
    None
):
    learning_surface_paths = (
        PROJECT_ROOT / "src" / "specify_cli" / "hooks" / "learning.py",
        PROJECT_ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "learning-layer.md",
        PROJECT_ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-learning"
        / "SKILL.md",
        PROJECT_ROOT / "docs" / "quickstart.md",
    )
    command_template_paths = (
        PROJECT_ROOT / "templates" / "commands" / "analyze.md",
        PROJECT_ROOT / "templates" / "commands" / "checklist.md",
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
    )

    forbidden_fragments = (
        "capture-learning --command analyze ...",
        "capture-learning --command checklist ...",
        "capture-learning --command constitution ...",
        "capture-learning --command deep-research ...",
        "capture-learning --command debug ...",
        "capture-learning --command implement ...",
        "capture-learning --command map-build ...",
        "capture-learning --command map-scan ...",
        "capture-learning --command plan ...",
        "capture-learning --command specify ...",
        "capture-learning --command tasks ...",
        "learning capture --command fast ...",
        "hook review-learning --command quick",
    )

    for path in (*learning_surface_paths, *command_template_paths):
        content = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, (
                f"{path} still contains fake runnable command fragment: {fragment}"
            )


def test_classic_learning_partial_documents_sanitized_bounded_capture() -> None:
    content = read_template(
        "templates/command-partials/common/learning-layer.md"
    ).lower()
    normalized = " ".join(content.split())

    for required in (
        "summary, trigger_signals, and evidence are sanitized agent-facing projections",
        "raw sensitive values must not enter learning storage, registry, or read api",
        "safe project-relative reference or digest",
        "trigger_signals are canonical tags",
        "redaction_labels",
        "personal_identifier",
        "business_identifier",
        "organization_sensitive",
        "[redacted_phone]",
        "[redacted_business_id]",
        "[redacted_org_term]",
        "mature learning protection",
        "bounded candidate slot",
        "a candidate cannot become a rule directly",
        "confirmed learning before explicit project-rule promotion",
        "abstract and retain the reusable lesson",
        "learning value and sensitivity are independent axes",
        "sensitivity alone is never an eligibility veto",
        "capture-safe",
        "capture-sanitized",
        "--dry-run",
        "writes no candidate, registry, review state, or metric",
        "arbitrary regex is forbidden",
        "at most 64 distinct 1..128-character literals",
        "none|captured|auto-captured|deferred|manual-capture-needed",
        "`deferred` and `manual-capture-needed` require rationale",
        "captured decisions succeed only after that match is verified",
        "`none` is blocked while a matching deferred/manual decision remains pending",
        "learning status [--command <workflow>]",
        "status returns only pending/due/age buckets",
        "omits rationale, learning refs, recurrence keys, and timestamps",
        "learning metrics [--command <workflow>]",
        "canonical totals, decisions, value/risk tiers, reason/label counts",
        "derived confirmation rate",
        "do not mutate age or metrics",
    ):
        assert required in normalized


def test_readme_learning_helper_surface_uses_command_shape_and_required_options() -> (
    None
):
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "command shape:" in readme
    assert "required options:" in readme
    assert "specify learning capture --command <workflow> ..." not in readme
    assert "specify hook signal-learning --command <workflow> ..." not in readme
    assert (
        "specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> ..."
        not in readme
    )


def test_upgrade_guide_labels_agent_placeholder_upgrade_command_as_command_shape() -> (
    None
):
    upgrade = (PROJECT_ROOT / "docs" / "upgrade.md").read_text(encoding="utf-8")

    assert "Command shape:" in upgrade
    assert "specify init --here --force --ai <your-agent>" in upgrade


def test_readme_and_quickstart_label_workflow_hook_helper_surfaces_as_command_shapes() -> (
    None
):
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    quickstart = (
        (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()
    )

    assert "specify hook preflight --command <workflow> ..." not in readme
    assert "specify hook validate-state --command <workflow> ..." not in readme
    assert "specify hook workflow-policy --command <workflow> ..." not in readme
    assert "specify hook build-compaction --command <workflow> ..." not in readme
    assert "normal `sp-*` workflow steps should not call `specify hook" in readme
    assert "command shape:" in readme

    assert "use `specify hook preflight --command <workflow> ...`" not in quickstart
    assert (
        "use `specify hook validate-state --command <workflow> ...`" not in quickstart
    )
    assert "use `specify hook checkpoint --command <workflow> ...`" not in quickstart
    assert (
        "use `specify hook monitor-context --command <workflow> ...`" not in quickstart
    )
    assert "normal `sp-*` workflow steps should not call `specify hook" in quickstart
    assert "command shape:" in quickstart


def test_readme_and_quickstart_label_remaining_helper_command_shapes() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    quickstart = (
        (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower()
    )

    assert (
        "specify-runtime implement closeout --feature-dir <feature-dir> --format json"
        in readme
    )
    assert "implementation-summary.md" in readme
    assert "implementation_summary" in readme
    assert "git diff --stat" in readme
    assert "git diff --name-status" in readme
    assert "command shape:" in readme
    assert (
        "specify-runtime result path --command implement --feature-dir <feature-dir> --task-id <task-id>"
        in readme
    )
    assert (
        "specify-runtime result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>"
        in readme
    )
    assert (
        "specify-runtime result path --command debug --session-slug <session-slug> --lane-id <lane-id>"
        in readme
    )
    assert (
        "specify-runtime result path --command <workflow> --request-id <request-id>"
        in readme
    )
    assert (
        "sp-teams submit-result --request-id <request-id> --result-json '<inline-json>'"
        in readme
    )
    assert (
        "specify-runtime result path` emits json directly and does not accept `--format`"
        in readme
    )
    assert "result helper command shapes:" in readme
    assert "specify-runtime quick status <id>" in readme
    assert "quick-task helper command shapes:" in readme
    assert "command shape: `specify-runtime quick status <id>`" in readme
    assert "discussion helper command shapes:" in readme
    assert (
        "command shape: `specify-runtime discussion close <slug> --status completed|abandoned`"
        in readme
    )
    assert (
        "command shape: `specify-runtime discussion mark-consumed <slug> --feature-dir <feature-dir>`"
        in readme
    )
    assert "command shape: `specify hook mark-dirty --reason " not in readme
    assert "command shape: `specify-runtime cognition mark-dirty --reason " in readme
    assert "command shape: `specify project-map mark-dirty --reason " not in readme
    assert "legacy project-map artifacts" in readme
    assert "--origin-command <workflow>" in readme
    assert "--origin-feature-dir <dir>" in readme
    assert "--packet-file <packet-json>" in readme

    assert (
        "specify-runtime implement closeout --feature-dir <feature-dir> --format json"
        in quickstart
    )
    assert (
        "codex runtime-managed result paths require the dispatch request id"
        in quickstart
    )
    assert (
        "specify-runtime result path` emits json directly and does not accept `--format`"
        in quickstart
    )
    assert "implementation-summary.md" in quickstart
    assert "implementation_summary" in quickstart
    assert "git diff --stat" in quickstart
    assert "git diff --name-status" in quickstart
    assert "command shape:" in quickstart
    assert "specify eval create --recurrence-key <key> --summary" in quickstart
    assert "specify eval create --recurrence-key <key> ..." not in quickstart
    assert "quick-task helper command shapes:" in quickstart
    assert "command shape: `specify-runtime quick status <id>`" in quickstart
    assert "discussion helper command shapes:" in quickstart
    assert (
        "command shape: `specify-runtime discussion close <slug> --status completed|abandoned`"
        in quickstart
    )
    assert (
        "command shape: `specify-runtime discussion mark-consumed <slug> --feature-dir <feature-dir>`"
        in quickstart
    )


def test_discussion_workflow_uses_recommendation_first_decision_progression() -> None:
    command = read_command_with_references("discussion").lower()
    shell = read_template("templates/command-partials/discussion/shell.md").lower()
    state_template = read_template("templates/discussion-state-template.md").lower()
    readme = read_template("README.md").lower()
    quickstart = read_template("docs/quickstart.md").lower()
    installation = read_template("docs/installation.md").lower()
    handbook = read_template("PROJECT-HANDBOOK.md").lower()
    handbook_template = read_template("templates/project-handbook-template.md").lower()

    assert "recommendation-first decision progression" in command
    assert "recommendation-first decision progression" in shell
    assert "recommendation-first is not questionless" in command
    assert "recommendation-first is not questionless" in shell
    assert "do not run `sp-discussion` as a permission-first loop" in command
    assert "do not end a turn with a bare open question" in command
    assert "ask only when user judgment is genuinely required" in command
    assert "ask only when user judgment is genuinely required" in shell
    assert "continue by default" in command
    assert "continue by default" in shell
    assert "do not ask for continuation" in command
    assert "do not ask for continuation" in shell
    assert "after recording a user-confirmed decision" in command
    assert "next useful decision with a recommended default" in command
    assert "decision_advancement_mode: recommendation-first" in state_template
    for content in (readme, quickstart, installation, handbook, handbook_template):
        assert "continue by default" in content
        assert "do not ask for continuation" in content
        assert (
            "ask only when user judgment is genuinely required" in content
            or "asks only when user judgment is genuinely required" in content
        )


def test_discussion_helper_uses_active_python_interpreter_with_utf8_contract() -> None:
    cli = (PROJECT_ROOT / "src" / "specify_cli" / "__init__.py").read_text(
        encoding="utf-8"
    )
    bash = (PROJECT_ROOT / "scripts" / "bash" / "discussion-state.sh").read_text(
        encoding="utf-8"
    )
    powershell = (
        PROJECT_ROOT / "scripts" / "powershell" / "discussion-state.ps1"
    ).read_text(encoding="utf-8")
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    discussion_helper = cli.split("def _discussion_helper_script", 1)[1].split(
        "def _run_prd_helper", 1
    )[0]

    assert 'return [sys.executable, "-X", "utf8"], script_path' in discussion_helper
    assert '"scripts" / "shared" / "discussion-state.py"' in discussion_helper
    assert 'env["PYTHONUTF8"] = "1"' in discussion_helper
    assert 'env["PYTHONIOENCODING"] = "utf-8"' in discussion_helper
    assert 'errors="strict"' in discussion_helper
    assert 'errors="replace"' not in discussion_helper
    assert 'PYTHON_BIN="${SPECIFY_PYTHON:-python}"' in bash
    assert '"scripts/shared" = "specify_cli/core_pack/scripts/shared"' in pyproject
    assert 'SHARED_HELPER="$SCRIPT_DIR/../shared/discussion-state.py"' in bash
    assert "$pythonBin = if ($env:SPECIFY_PYTHON)" in powershell


def test_update_agent_context_managed_block_emitters_remain_cross_shell_equivalent() -> (
    None
):
    _assert_managed_block_emitters_match_across_shells()


def test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics() -> (
    None
):
    bash = read_template("scripts/bash/update-agent-context.sh").lower()
    powershell = read_template("scripts/powershell/update-agent-context.ps1").lower()

    for content in (bash, powershell):
        assert "project cognition and project learning are always available" in content
        assert "even without an active `sp-*` workflow" in content
        assert "when existing-system truth matters" in content
        assert "before broad source inspection" in content
        assert (
            "{{specify-runtime-cli}} learning start --command <workflow> --format json"
            in content
        )
        assert "{{specify-runtime-cli}} api list --format json" in content
        assert "python `specify` is human-only" in content
        assert "show_argv" in content
        assert ".specify/memory/learnings/index.md" not in content
        assert "## workflow invocation boundary" in content
        assert "all `sp-*` and `spx-*` workflow skills are user-invoked only" in content
        assert "no passive workflow router is installed" in content
        assert "## workflow recommendations" not in content
        assert "recommend `sp-discussion`" not in content
        assert "generated create-feature script" in content
        assert "prefer durable workflow state and explicit feature paths" in content
        assert "frontstage-only deferred persistence" in content
        assert (
            "do not write discussion files, counters, dirty markers, receipts, or status summaries for every user reply"
            in content
        )
        assert "active discussion turns" in content
        assert "suppress the reminder" in content
        assert "end every discussion reply" not in content
        assert "prompt does not write files by itself" in content
        assert "project cognition freshness truthful" in content
        assert "store reusable lessons through project learning" in content
        assert "1% chance" not in content
        assert "## workflow activation discipline" not in content
        assert "## workflow routing" not in content
        assert "## artifact priority" not in content
        assert "## project cognition usage" not in content
        assert "## map maintenance" not in content
        assert "sp-test-scan" not in content
        assert "sp-test-build" not in content
        assert ("use `" + "project" + "-map complete-refresh`") not in content
        assert ("use `" + "project" + "-map mark-dirty`") not in content
        assert (
            "do not continue under known-stale handbook state without choosing one of those paths"
            not in content
        )
        assert (
            "shared manual override/fallback before later brownfield work continues"
            not in content
        )
        assert "map-level truth" not in content
        assert "possibly_stale" not in content
        assert "must_refresh_topics" not in content
        assert "review_topics" not in content
    assert "project-cognition" in read_template("src/specify_cli/__init__.py").lower()


def test_guidance_docs_document_refresh_readiness_state_vocabulary() -> None:
    readme = read_template("README.md").lower()
    handbook = read_template("PROJECT-HANDBOOK.md").lower()
    handbook_template = read_template("templates/project-handbook-template.md").lower()

    assert "learning start" in readme
    assert "learning list" in readme
    assert "learning show" in readme
    assert "reading never auto-promotes" in readme

    closed_rebuild_policy = " ".join(
        (
            "first/missing/unusable baseline, schema failure, schema v1 or old "
            "broad-schema rebuild-required readiness, zero active-generation path_index "
            "rows, missing or invalid alias_index, explicit_rebuild_requested, or "
            "baseline_identity_invalid"
        ).split()
    )

    for content in (readme, handbook, handbook_template):
        normalized = " ".join(content.replace("`", "").split())
        assert "recorded refresh and ready refresh" in content
        assert "support drift" in content
        assert "support_drift" in content
        assert "partial_refresh" in content
        assert "recommended_next_action" in content
        assert "specify-runtime cognition validate-scan --format json" in content
        assert "specify-runtime cognition validate-build --format json" in content
        assert "first brownfield cognition baseline" in content
        assert closed_rebuild_policy in normalized

    normalized_readme = " ".join(readme.split())
    assert "if the reference is blocked, stale, or incomplete" in normalized_readme
    assert "fall back to minimal live reads" in normalized_readme
    assert "recommend `map-update` for localized stale or weak reference" in readme
    assert "if the reference baseline is missing or unusable" in normalized_readme
    assert "recommend `map-scan -> map-build` only" in normalized_readme
    stale_reference_refresh = (
        "refresh that " + "reference with `map-scan -> map-build` or " + "`map-update`"
    )
    assert stale_reference_refresh not in readme


def test_docs_describe_greenfield_project_cognition_bootstrap() -> None:
    docs = {
        "README.md": read_template("README.md"),
        "PROJECT-HANDBOOK.md": read_template("PROJECT-HANDBOOK.md"),
        "docs/quickstart.md": read_template("docs/quickstart.md"),
        "docs/installation.md": read_template("docs/installation.md"),
    }

    for path, content in docs.items():
        matching_blocks = [
            block
            for block in re.split(r"\n\s*\n", _normalize_newlines(content))
            if "baseline_kind=greenfield_empty" in block
        ]
        assert len(matching_blocks) == 1, path

        block = matching_blocks[0]
        lowered = block.lower()
        normalized = " ".join(block.replace("`", "").split()).lower()

        assert "specify-runtime cognition init-empty" in lowered, path
        assert ".specify/project-cognition/status.json" in lowered, path
        assert ".specify/project-cognition/project-cognition.db" in lowered, path
        assert "baseline_kind=greenfield_empty" in normalized, path
        assert "baseline kind" in normalized, path
        assert "no business code yet" in normalized, path
        assert (
            "do not require map-scan -> map-build solely because the graph has no paths"
            in normalized
        ), path
        assert (
            "projects with existing code still use map-scan -> map-build" in normalized
        ), path
        assert (
            "first missing unusable baseline" in normalized
            or "first/missing/unusable baseline" in normalized
        ), path

        assert "fresh specify init" not in normalized, path
        assert "fresh generated" not in normalized, path
        assert "fresh project" not in normalized, path


def test_classic_auxiliary_artifact_workflows_fail_closed_through_go_gate() -> None:
    expected = {
        "deep-research": "--command deep-research --feature-dir <feature-dir>",
        "analyze": "--command analyze --feature-dir <feature-dir>",
        "constitution": "--command constitution --feature-dir .specify/memory",
    }

    for command, invocation in expected.items():
        content = read_template(f"templates/commands/{command}.md")
        assert "specify-runtime hook validate-artifacts" in content
        assert invocation in content
