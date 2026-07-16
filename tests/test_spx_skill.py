import json
import os
import re
import tomllib
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import specify_cli
from specify_cli import app
from specify_cli.design import lint_design_file
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import (
    SpecifyLauncherSpec,
    write_project_cognition_launcher_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADVANCED_SKILLS = PROJECT_ROOT / "templates" / "advanced-skills"
SPX_SKILLS = {
    "spx-accept",
    "spx-analyze",
    "spx-ask",
    "spx-auto",
    "spx-checklist",
    "spx-clarify",
    "spx-constitution",
    "spx-debug",
    "spx-deep-research",
    "spx-design",
    "spx-discussion",
    "spx-explain",
    "spx-fast",
    "spx-implement",
    "spx-implement-teams",
    "spx-integrate",
    "spx-map-build",
    "spx-map-rebuild",
    "spx-map-scan",
    "spx-map-update",
    "spx-plan",
    "spx-prd",
    "spx-prd-build",
    "spx-prd-scan",
    "spx-quick",
    "spx-research",
    "spx-specify",
    "spx-tasks",
    "spx-taskstoissues",
    "spx-team",
}
CLASSIC_MAP_COMPANION_SKILLS = {
    "sp-map-build",
    "sp-map-scan",
    "sp-map-update",
}
SKILLS_INTEGRATIONS = (
    "agy",
    "claude",
    "codex",
    "cursor-agent",
    "kimi",
    "trae",
    "vibe",
    "zcode",
)


def _frontmatter(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith("---\n")
    return yaml.safe_load(raw.split("---", 2)[1])


def test_spx_design_asset_passes_the_real_design_linter() -> None:
    diagnostics = lint_design_file(
        ADVANCED_SKILLS / "spx-design" / "assets" / "design-system.md"
    )

    assert diagnostics == []


def test_spx_quick_status_asset_is_readable_by_the_real_quick_helper(
    monkeypatch, tmp_path: Path
) -> None:
    quick_id = "20260714-001"
    workspace = tmp_path / ".planning" / "quick" / f"{quick_id}-parser-contract"
    workspace.mkdir(parents=True)
    content = (ADVANCED_SKILLS / "spx-quick" / "assets" / "status.md").read_text(
        encoding="utf-8"
    )
    for placeholder, value in {
        "{{id}}": quick_id,
        "{{slug}}": "parser-contract",
        "{{title}}": "Parser contract",
        "{{intent}}": "verify the advanced quick template",
    }.items():
        content = content.replace(placeholder, value)
    (workspace / "STATUS.md").write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    task = specify_cli._run_quick_helper("status", quick_id=quick_id)["task"]

    assert task["current_focus"] == "verify the advanced quick template"
    assert task["next_action"] == "establish scope and acceptance"


def _expected_installed_files(skill_name: str) -> set[str]:
    skill_source = ADVANCED_SKILLS / skill_name
    files = {
        path.relative_to(skill_source).as_posix()
        for path in skill_source.rglob("*")
        if path.is_file()
    }
    files.update(
        f"references/{path.name}" for path in (ADVANCED_SKILLS / "_shared").glob("*.md")
    )
    return files


def test_spx_sources_are_independent_and_discoverable() -> None:
    skill_dirs = {
        path.name
        for path in ADVANCED_SKILLS.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }
    assert skill_dirs == SPX_SKILLS
    assert not (ADVANCED_SKILLS / "spx" / "SKILL.md").exists()

    bodies = []
    for skill_name in SPX_SKILLS:
        skill_dir = ADVANCED_SKILLS / skill_name
        skill = skill_dir / "SKILL.md"
        frontmatter = _frontmatter(skill)
        assert frontmatter.keys() == {"name", "description"}
        assert frontmatter["name"] == skill_name
        assert "advanced" in frontmatter["description"].lower()
        body = skill.read_text(encoding="utf-8")
        bodies.append(body)
        assert "references/project-cognition.md" in body
        assert "references/project-learning.md" in body
        for relative in re.findall(
            r"`((?:references|assets)/[^`\s]+\.md)`",
            body,
        ):
            local = skill_dir / relative
            shared = ADVANCED_SKILLS / "_shared" / Path(relative).name
            assert local.is_file() or shared.is_file(), (skill_name, relative)

        openai_yaml = yaml.safe_load(
            (skill_dir / "agents" / "openai.yaml").read_text(encoding="utf-8")
        )
        assert openai_yaml["policy"]["allow_implicit_invocation"] is False
        assert f"${skill_name}" in openai_yaml["interface"]["default_prompt"]

    cognition = ADVANCED_SKILLS / "_shared" / "project-cognition.md"
    assert cognition.exists()
    learning = ADVANCED_SKILLS / "_shared" / "project-learning.md"
    assert learning.exists()
    blocker_resolution = ADVANCED_SKILLS / "_shared" / "blocker-resolution.md"
    assert blocker_resolution.exists()
    assert "references/blocker-resolution.md" in cognition.read_text(encoding="utf-8")

    for source_file in ADVANCED_SKILLS.rglob("*"):
        if not source_file.is_file():
            continue
        content = source_file.read_text(encoding="utf-8").lower()
        assert "templates/command-references" not in content
        assert "{{spec-kit-include:" not in content

    combined = "\n".join([*bodies, cognition.read_text(encoding="utf-8")]).lower()
    for forbidden in (
        "close_agent",
        "subagent-mandatory",
        "claim_retrieval_contract_version",
        "candidate_universe_version",
        "v1.3.",
        "understanding_confirmed",
    ):
        assert forbidden.lower() not in combined


def test_spx_blocked_exit_requires_detailed_human_recovery_only_at_human_boundaries() -> None:
    contract = re.sub(
        r"\s+",
        " ",
        (ADVANCED_SKILLS / "_shared" / "blocker-resolution.md")
        .read_text(encoding="utf-8")
        .lower(),
    )
    for required in (
        "exact cause",
        "sanitized evidence",
        "recovery attempted",
        "unblock criteria",
        "exact resume point",
        "human_action_required: true",
        "expected visible result",
        "safe failure branch",
        "protected ci",
        "visual review",
        "product decision",
        "never ask for secrets",
    ):
        assert required in contract


def test_spx_skills_keep_runtime_reuse_and_safety_boundaries() -> None:
    skills = {
        name: (ADVANCED_SKILLS / name / "SKILL.md").read_text(encoding="utf-8").lower()
        for name in SPX_SKILLS
    }

    assert "read-only" in skills["spx-ask"]
    assert "live repository" in skills["spx-ask"]
    assert "spx-explain" in skills["spx-ask"]

    assert "contextless human" in skills["spx-accept"]
    assert "one current scenario step" in skills["spx-accept"]
    assert "human product acceptance, not code review" in skills["spx-accept"]
    assert "spx-implement" in skills["spx-accept"]
    assert "accept closeout" in skills["spx-accept"]

    assert "exactly one next spx workflow" in skills["spx-auto"]
    assert "create no separate auto state" in skills["spx-auto"]

    assert "design.md" in skills["spx-design"]
    assert "do not edit application source" in skills["spx-design"]

    assert "create-new-feature" in skills["spx-specify"]
    assert "spec-contract-template.json" in skills["spx-specify"]
    assert "do not implement" in skills["spx-specify"]
    assert "spx-clarify" in skills["spx-specify"]
    assert "spx-prd-scan" in skills["spx-specify"]

    assert "do not create a new feature" in skills["spx-clarify"]
    assert "existing" in skills["spx-clarify"]
    assert "do not plan or implement" in skills["spx-clarify"]

    assert ".specify/memory/constitution.md" in skills["spx-constitution"]
    assert "owns the constitution only" in skills["spx-constitution"]

    assert "discussion resume" in skills["spx-discussion"]
    assert "discussion mark-ready" in skills["spx-discussion"]
    assert "do not create feature state" in skills["spx-discussion"]

    assert "remain read-only" in skills["spx-explain"]
    assert "what the artifact\nclaims" in skills["spx-explain"]

    assert "setup-plan" in skills["spx-plan"]
    assert "plan-contract-template.json" in skills["spx-plan"]
    assert "assets/plan.md" in skills["spx-plan"]
    assert "do not create tasks" in skills["spx-plan"]
    assert "spx-deep-research" in skills["spx-plan"]
    assert "spx-tasks" in skills["spx-plan"]
    assert "production source" in skills["spx-plan"]

    assert "deep-research.md" in skills["spx-deep-research"]
    assert "planning handoff" in skills["spx-deep-research"]
    assert "do not implement production" in skills["spx-deep-research"]
    assert "not a separate artifact lifecycle" in skills["spx-research"]

    assert "task-index-template.json" in skills["spx-tasks"]
    assert "dependency" in skills["spx-tasks"]
    assert "do not implement" in skills["spx-tasks"]

    assert "non-destructive gate" in skills["spx-analyze"]
    assert "do not edit `spec.md`" in skills["spx-analyze"]

    assert "requirements or planning decisions" in skills["spx-checklist"]
    assert "checklist completion does not by itself prove" in skills["spx-checklist"]

    assert "external write" in skills["spx-taskstoissues"]
    assert "safe retry boundary" in skills["spx-taskstoissues"]

    assert "check-prerequisites" in skills["spx-implement"]
    assert "run the relevant verification" in skills["spx-implement"]
    assert "delegate only" in skills["spx-implement"]
    assert "spx-integrate" in skills["spx-implement"]

    assert "integration.json" in skills["spx-implement-teams"]
    assert "codex" in skills["spx-implement-teams"]
    assert "claude" in skills["spx-implement-teams"]
    assert "emulate durable state" in skills["spx-implement-teams"]

    assert "only inspects and closes lane state" in skills["spx-integrate"]
    assert "--close" in skills["spx-integrate"]

    assert "codex-only runtime" in skills["spx-team"]
    assert "cleanup" in skills["spx-team"]

    assert "reproduce" in skills["spx-debug"]
    assert "ranked hypotheses" in skills["spx-debug"]
    assert "regression" in skills["spx-debug"]

    assert "leader-direct" in skills["spx-fast"]
    assert "no spec" in skills["spx-fast"]
    assert "spx-quick" in skills["spx-fast"]

    assert ".planning/quick/" in skills["spx-quick"]
    assert "status.md" in skills["spx-quick"]
    assert "summary.md" in skills["spx-quick"]
    assert "spx-specify" in skills["spx-quick"]

    assert "spx-map-scan" in skills["spx-map-rebuild"]
    assert "spx-map-build" in skills["spx-map-rebuild"]
    assert "scan-prepare" not in skills["spx-map-rebuild"]
    assert "build-from-scan" not in skills["spx-map-rebuild"]

    assert "scan-prepare" in skills["spx-map-scan"]
    assert "scan-accept" in skills["spx-map-scan"]
    assert "validate-scan" in skills["spx-map-scan"]
    assert "lowest-cost capable" in skills["spx-map-scan"]
    assert "build-from-scan" in skills["spx-map-scan"]
    assert "do not run" in skills["spx-map-scan"]

    assert "validate-scan" in skills["spx-map-build"]
    assert "build-from-scan" in skills["spx-map-build"]
    assert "validate-build" in skills["spx-map-build"]
    assert "scan-prepare" not in skills["spx-map-build"]
    assert "hand-edit sqlite" in skills["spx-map-build"]
    assert "closeout-plan" in skills["spx-map-update"]

    scan_worker = (
        (ADVANCED_SKILLS / "spx-map-scan" / "references" / "scan-worker.md")
        .read_text(encoding="utf-8")
        .lower()
    )
    for required in (
        "lowest-cost model",
        "assigned_paths",
        "pending-results/<packet-id>.json",
        "nodes[].paths",
        "acceptance: pass",
        "never silently omit",
        "do not run `scan-accept`",
    ):
        assert required in scan_worker

    assert "prd-scan" in skills["spx-prd"]
    assert "prd-build" in skills["spx-prd"]
    assert "read-only" in skills["spx-prd-scan"]
    assert "lowest-cost capable" in skills["spx-prd-scan"]
    assert "do not synthesize the final prd" in skills["spx-prd-scan"]
    assert "only product-fact source" in skills["spx-prd-build"]
    assert "do not crawl or reread the repository" in skills["spx-prd-build"]


def test_spx_core_pipeline_requires_an_explicit_stop_between_stages() -> None:
    skills = {
        name: re.sub(
            r"\s+",
            " ",
            (ADVANCED_SKILLS / name / "SKILL.md").read_text(encoding="utf-8").lower(),
        )
        for name in ("spx-specify", "spx-plan", "spx-tasks")
    }

    for skill in skills.values():
        assert "this invocation authorizes only this workflow stage" in skill

    specify = skills["spx-specify"]
    assert (
        "do not create `plan-contract.json`, `plan.md`, `research.md`, "
        "`data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, or "
        "`task-index.json`"
    ) in specify
    assert "do not invoke `$spx-plan`" in specify

    plan = skills["spx-plan"]
    assert "do not create tasks or task artifacts" in plan
    assert "`tasks.md`" in plan
    assert "`task-index.json`" in plan
    assert "do not invoke `$spx-tasks`" in plan

    tasks = skills["spx-tasks"]
    assert "read `plan-contract.json` first" in tasks
    assert "do not implement or edit production source/tests" in tasks
    assert "do not invoke `$spx-implement`" in tasks

    implement = re.sub(
        r"\s+",
        " ",
        (ADVANCED_SKILLS / "spx-implement" / "SKILL.md")
        .read_text(encoding="utf-8")
        .lower(),
    )
    assert "--require-tasks --include-tasks" in implement
    assert "`$spx-accept`" in implement


def test_spx_preplan_routes_stop_after_the_authorized_stage() -> None:
    skills = {
        name: re.sub(
            r"\s+",
            " ",
            (ADVANCED_SKILLS / name / "SKILL.md").read_text(encoding="utf-8").lower(),
        )
        for name in ("spx-auto", "spx-research", "spx-clarify", "spx-deep-research")
    }

    assert "stop after that workflow returns" in skills["spx-auto"]
    assert "do not invoke a second workflow" in skills["spx-auto"]

    assert "authorizes only the deep-research compatibility route" in skills[
        "spx-research"
    ]
    assert "do not continue to `$spx-plan`" in skills["spx-research"]

    for name in ("spx-clarify", "spx-deep-research"):
        assert "this invocation authorizes only this workflow stage" in skills[name]
        assert "do not invoke `$spx-plan`" in skills[name]

    assert "do not invoke `$spx-deep-research`" in skills["spx-clarify"]
    assert "do not invoke `$spx-clarify`" in skills["spx-deep-research"]


def test_spx_read_only_and_runtime_probe_boundaries_are_explicit() -> None:
    explain_reference = (
        ADVANCED_SKILLS / "spx-explain" / "references" / "artifact-explanation.md"
    ).read_text(encoding="utf-8").lower()
    team = re.sub(
        r"\s+",
        " ",
        (ADVANCED_SKILLS / "spx-team" / "SKILL.md")
        .read_text(encoding="utf-8")
        .lower(),
    )

    assert "--ensure-worktree" not in explain_reference
    assert "inspection and diagnosis authorize only `status` and `doctor`" in team
    assert "never run `live-probe` implicitly" in team
    assert "explicit operator authorization" in team


def test_spx_fast_and_quick_preserve_consequence_escalation_triggers() -> None:
    skills = {
        name: re.sub(
            r"\s+",
            " ",
            (ADVANCED_SKILLS / name / "SKILL.md").read_text(encoding="utf-8").lower(),
        )
        for name in ("spx-fast", "spx-quick")
    }

    for content in skills.values():
        assert "references/consequence-gate.md" in content
        for trigger in (
            "lifecycle operations",
            "running objects",
            "concurrent work",
            "destructive behavior",
            "shared state",
            "downstream consumers",
            "compatibility",
            "security-sensitive behavior",
            "multiple plausible product behaviors",
        ):
            assert trigger in content

    assert "route bounded consequences to `$spx-quick`" in skills["spx-fast"]
    assert "route broader or user-owned consequences to `$spx-specify`" in skills[
        "spx-fast"
    ]
    assert "record bounded consequence obligations in `status.md`" in skills[
        "spx-quick"
    ]
    assert "route unbounded consequences to `$spx-specify`" in skills["spx-quick"]


def test_spx_ui_quality_contract_survives_design_to_implementation() -> None:
    ui_gate = (ADVANCED_SKILLS / "_shared" / "ui-quality-gate.md").read_text(
        encoding="utf-8"
    )
    assert "does not\nrequire an external screenshot" in ui_gate
    assert "status:\nbootstrap" in ui_gate
    assert "real entry point" in ui_gate
    assert "pending-human-review" in ui_gate

    for skill_name in (
        "spx-accept",
        "spx-analyze",
        "spx-auto",
        "spx-debug",
        "spx-design",
        "spx-fast",
        "spx-implement",
        "spx-implement-teams",
        "spx-integrate",
        "spx-plan",
        "spx-quick",
        "spx-specify",
        "spx-tasks",
    ):
        content = (ADVANCED_SKILLS / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "references/ui-quality-gate.md" in content, skill_name

    assert "--level ready" in (ADVANCED_SKILLS / "spx-design" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "substantive\nUI work" in (
        ADVANCED_SKILLS / "spx-specify" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "ui_design_contract" in (
        ADVANCED_SKILLS / "spx-plan" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "assets/ui-task.md" in (
        ADVANCED_SKILLS / "spx-tasks" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "assets/ui-task-index-entry.json" in (
        ADVANCED_SKILLS / "spx-tasks" / "SKILL.md"
    ).read_text(encoding="utf-8")
    ui_task = (ADVANCED_SKILLS / "spx-tasks" / "assets" / "ui-task.md").read_text(
        encoding="utf-8"
    )
    assert "### Scope Boundaries" in ui_task
    assert "### UI Implementation Contract" in ui_task
    assert "required_evidence" in ui_task
    assert "ui_required_evidence" not in ui_task
    ui_task_index = json.loads(
        (
            ADVANCED_SKILLS / "spx-tasks" / "assets" / "ui-task-index-entry.json"
        ).read_text(encoding="utf-8")
    )
    assert set(ui_task_index) == {"ui_contract"}
    assert "contract_version" not in ui_task_index["ui_contract"]
    current_packet = json.loads(
        (PROJECT_ROOT / "templates" / "task-packet-template.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(ui_task_index["ui_contract"]) == set(current_packet["ui_contract"])
    for field in (
        "surface_type",
        "platforms",
        "subject",
        "audience",
        "single_job",
        "visual_thesis",
        "content_thesis",
        "interaction_thesis",
        "signature_element",
        "approved_visual_ref",
        "reference_intents",
        "real_content_plan",
        "image_plan",
    ):
        assert field in ui_task_index["ui_contract"]
    assert ui_task_index["ui_contract"]["required_evidence"] == [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
    assert "visual convergence loop" in (
        ADVANCED_SKILLS / "spx-implement" / "references" / "execution-contract.md"
    ).read_text(encoding="utf-8")
    design_asset = (
        ADVANCED_SKILLS / "spx-design" / "assets" / "design-system.md"
    ).read_text(encoding="utf-8")
    for generic_anchor in ('value: "8px"', 'value: "16px"', 'value: "14px"'):
        assert generic_anchor not in design_asset


def test_spx_shared_project_cognition_contract_is_tool_driven() -> None:
    content = (
        (ADVANCED_SKILLS / "_shared" / "project-cognition.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    for required in (
        "project-cognition compass",
        "minimal_live_reads",
        "first_pass_paths",
        "coverage_diagnostics",
        "expansion_ref",
        "live repository",
        "project-cognition closeout-plan",
        "update_argv",
        "needs_rebuild",
        "spx-map-rebuild",
        "spx-map-update",
    ):
        assert required in content


def test_spx_shared_project_learning_contract_is_cli_progressive_and_read_only() -> None:
    content = (
        (ADVANCED_SKILLS / "_shared" / "project-learning.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    for required in (
        "learning start",
        "learning list",
        "show_argv",
        "read-only",
        "capture-auto",
        "consume-only",
        "trigger signals",
        "never silently promote",
    ):
        assert required in content
    assert ".specify/memory/learnings/index.md" not in content


def test_advanced_profile_installs_spx_with_only_classic_map_companions(
    tmp_path,
) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    manifest = IntegrationManifest("codex", project)

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )

    skills_dir = integration.skills_dest(project)
    installed = {path.parent.name for path in skills_dir.glob("spx-*/SKILL.md")}
    assert installed == SPX_SKILLS

    for skill_name in SPX_SKILLS:
        skill_dir = skills_dir / skill_name
        skill = skill_dir / "SKILL.md"
        assert (skill_dir / "agents" / "openai.yaml").exists()
        assert (skill_dir / "references" / "project-cognition.md").exists()
        assert (skill_dir / "references" / "project-learning.md").exists()
        assert (skill_dir / "references" / "consequence-gate.md").exists()
        assert (skill_dir / "references" / "ui-quality-gate.md").exists()

        frontmatter = _frontmatter(skill)
        assert frontmatter["name"] == skill_name
        assert frontmatter["metadata"]["source"] == (
            f"templates/advanced-skills/{skill_name}/SKILL.md"
        )

        content = skill.read_text(encoding="utf-8")
        assert "Subagent Dispatch Contract" not in content
        assert "Project Cognition Gate" not in content
        assert "{{spec-kit-include:" not in content

        for path in skill_dir.rglob("*"):
            if path.is_file():
                assert path.relative_to(project).as_posix() in manifest.files
            if path.is_file() and path.suffix == ".md":
                installed_content = path.read_text(encoding="utf-8")
                assert "{{specify-subcmd:" not in installed_content

        installed_files = {
            path.relative_to(skill_dir).as_posix()
            for path in skill_dir.rglob("*")
            if path.is_file()
        }
        assert installed_files == _expected_installed_files(skill_name)

    installed_scan_worker = (
        skills_dir / "spx-map-scan" / "references" / "scan-worker.md"
    )
    assert installed_scan_worker.exists()
    assert (
        "lowest-cost model" in installed_scan_worker.read_text(encoding="utf-8").lower()
    )

    assert not (skills_dir / "sp-plan" / "SKILL.md").exists()
    assert not (skills_dir / "tdd-workflow" / "SKILL.md").exists()
    installed_classic = {path.parent.name for path in skills_dir.glob("sp-*/SKILL.md")}
    assert installed_classic == CLASSIC_MAP_COMPANION_SKILLS
    for skill_name in CLASSIC_MAP_COMPANION_SKILLS:
        skill = skills_dir / skill_name / "SKILL.md"
        command_name = skill_name.removeprefix("sp-")
        assert _frontmatter(skill)["metadata"]["source"] == (
            f"templates/commands/{command_name}.md"
        )
        assert "Mandatory Subagent Execution" in skill.read_text(encoding="utf-8")


def test_advanced_local_references_use_the_project_pinned_launcher(tmp_path) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                },
                "project_cognition_launcher": {
                    "command": "C:/tools/project-cognition.exe",
                    "argv": ["C:/tools/project-cognition.exe"],
                },
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("codex", project)

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )

    execution = (
        integration.skills_dest(project)
        / "spx-implement"
        / "references"
        / "execution-contract.md"
    ).read_text(encoding="utf-8")
    teams = (
        integration.skills_dest(project)
        / "spx-implement-teams"
        / "references"
        / "codex-teams.md"
    ).read_text(encoding="utf-8")
    cognition = (
        integration.skills_dest(project)
        / "spx-ask"
        / "references"
        / "project-cognition.md"
    ).read_text(encoding="utf-8")

    assert "python -m specify_cli implement resume-audit" in execution
    assert "python -m specify_cli sp-teams auto-dispatch" in teams
    assert "C:\\tools\\project-cognition.exe" in cognition or (
        "C:/tools/project-cognition.exe" in cognition
    )
    assert "{{specify-subcmd:" not in execution + teams + cognition


def test_fresh_advanced_codex_init_binds_root_discussion_skill_to_source_launcher(
    monkeypatch,
    tmp_path,
) -> None:
    import importlib

    project = tmp_path / "fresh-advanced-project"
    project.mkdir()
    assert not (project / ".specify" / "config.json").exists()
    pinned_command = (
        "uvx --from "
        "git+https://github.com/chenziyang110/spec-kit-plus.git@abc123 specify"
    )
    pinned_launcher = SpecifyLauncherSpec(
        command=pinned_command,
        argv=(
            "uvx",
            "--from",
            "git+https://github.com/chenziyang110/spec-kit-plus.git@abc123",
            "specify",
        ),
    )
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)
    monkeypatch.setattr(
        "specify_cli.launcher.resolve_specify_launcher_spec",
        lambda: pinned_launcher,
    )
    specify_lint = importlib.import_module("specify_cli.lint")
    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr(
        "specify_cli.project_cognition_runtime.ensure_binary",
        lambda: (_ for _ in ()).throw(RuntimeError("offline runtime fixture")),
    )
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        initialized = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "codex",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert initialized.exit_code == 0, initialized.output
    config = json.loads(
        (project / ".specify" / "config.json").read_text(encoding="utf-8")
    )
    assert config["specify_launcher"]["argv"] == list(pinned_launcher.argv)
    discussion = (
        project / ".codex" / "skills" / "spx-discussion" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert f"{pinned_command} discussion list --json" in discussion
    assert f"{pinned_command} discussion init <slug> --json" in discussion
    assert "`specify discussion" not in discussion


def test_advanced_local_references_without_cognition_launcher_use_recovery_contract(
    tmp_path,
) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("codex", project)

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )

    cognition_references = [
        (skill_dir / "references" / "project-cognition.md").read_text(
            encoding="utf-8"
        )
        for skill_dir in integration.skills_dest(project).glob("spx-*")
    ]

    assert cognition_references
    assert len(set(cognition_references)) == 1
    cognition = cognition_references[0]
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" in cognition
    assert "python -m specify_cli check" in cognition
    assert "python -m specify_cli integration repair" in cognition
    assert "specify cognition" in cognition
    assert "do not" in cognition.lower()
    assert "(requires project-cognition" not in cognition
    assert "`project-cognition compass" not in cognition
    assert "{{specify-subcmd:" not in cognition


def test_advanced_runtime_repair_rebinds_unavailable_cognition_references(
    tmp_path,
) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    references = sorted(
        integration.skills_dest(project).glob("spx-*/references/project-cognition.md")
    )
    assert references
    assert all(
        "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE"
        in reference.read_text(encoding="utf-8")
        for reference in references
    )

    binary = project / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_project_cognition_launcher_config(project, binary)

    repaired = integration.repair_runtime_assets(
        project,
        manifest,
        script_type="sh",
    )

    repaired_references = [
        reference.read_text(encoding="utf-8") for reference in references
    ]
    assert set(references).issubset(set(repaired))
    assert len(set(repaired_references)) == 1
    assert all(str(binary) in content for content in repaired_references)
    assert all(
        "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" not in content
        for content in repaired_references
    )


def test_runtime_repair_preserves_user_modified_cognition_guidance(tmp_path) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    reference = (
        integration.skills_dest(project)
        / "spx-implement"
        / "references"
        / "project-cognition.md"
    )
    reference.write_text(
        reference.read_text(encoding="utf-8") + "\nUser-owned recovery note.\n",
        encoding="utf-8",
    )

    binary = project / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_project_cognition_launcher_config(project, binary)

    repaired = integration.repair_runtime_assets(
        project,
        manifest,
        script_type="sh",
    )

    content = reference.read_text(encoding="utf-8")
    assert reference not in repaired
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" in content
    assert "User-owned recovery note." in content


def test_advanced_integration_repair_installs_and_rebinds_missing_cognition_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    import importlib

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)
    specify_lint = importlib.import_module("specify_cli.lint")
    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr(
        "specify_cli.project_cognition_runtime.ensure_binary",
        lambda: (_ for _ in ()).throw(RuntimeError("offline runtime fixture")),
    )
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        initialized = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "codex",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        assert initialized.exit_code == 0, initialized.output
        installed_reference = (
            project
            / ".codex"
            / "skills"
            / "spx-ask"
            / "references"
            / "project-cognition.md"
        )
        assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" in (
            installed_reference.read_text(encoding="utf-8")
        )
        (project / "DESIGN.md").write_text(
            "# Approved project design\n\nDo not replace this contract.\n",
            encoding="utf-8",
        )

        binary = tmp_path / "cache" / "project-cognition"
        binary.parent.mkdir(parents=True)
        binary.write_text("binary", encoding="utf-8")
        monkeypatch.setattr(
            "specify_cli.project_cognition_runtime.ensure_binary", lambda: binary
        )
        repaired = runner.invoke(
            app,
            ["integration", "repair"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert repaired.exit_code == 0, repaired.output
    project_config = json.loads(
        (project / ".specify" / "config.json").read_text(encoding="utf-8")
    )
    assert project_config["project_cognition_launcher"]["argv"] == [str(binary)]
    assert (project / "DESIGN.md").read_text(encoding="utf-8") == (
        "# Approved project design\n\nDo not replace this contract.\n"
    )
    cognition_references = [
        reference.read_text(encoding="utf-8")
        for reference in (project / ".codex" / "skills").glob(
            "spx-*/references/project-cognition.md"
        )
    ]
    assert cognition_references
    assert all(str(binary) in content for content in cognition_references)
    assert all(
        "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" not in content
        for content in cognition_references
    )


def test_classic_missing_cognition_launcher_has_equivalent_recovery_and_rebinds(
    tmp_path,
) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    skills = integration.skills_dest(project)
    implement = skills / "sp-implement" / "SKILL.md"
    implement_content = implement.read_text(encoding="utf-8")
    cognition_gate = (
        skills / "spec-kit-project-cognition-gate" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert (
        "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE:project-cognition compass"
        in implement_content
    )
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" in cognition_gate
    assert "python -m specify_cli check" in cognition_gate
    assert "python -m specify_cli integration repair" in cognition_gate
    assert "specify cognition" in cognition_gate
    assert "do not" in cognition_gate.lower()

    binary = project / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_project_cognition_launcher_config(project, binary)
    repaired = integration.repair_runtime_assets(
        project,
        manifest,
        script_type="sh",
    )

    assert implement in repaired
    repaired_implement = implement.read_text(encoding="utf-8")
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" not in repaired_implement
    assert f"{binary} compass --intent implement" in repaired_implement


def test_markdown_command_integration_installs_and_rebinds_cognition_recovery(
    tmp_path,
) -> None:
    integration = get_integration("qwen")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("qwen", project)

    integration.setup(project, manifest, script_type="sh")

    commands = integration.commands_dest(project)
    implement = (commands / "sp.implement.md").read_text(encoding="utf-8")
    semantic_contract = (
        commands / "references" / "implement" / "semantic-work-contract.md"
    ).read_text(encoding="utf-8")
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE:project-cognition" in implement
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" in semantic_contract
    assert "python -m specify_cli check" in semantic_contract
    assert "python -m specify_cli integration repair" in semantic_contract
    assert "specify cognition" in semantic_contract
    assert "do not" in semantic_contract.lower()

    binary = project / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_project_cognition_launcher_config(project, binary)

    repaired = integration.repair_runtime_assets(
        project,
        manifest,
        script_type="sh",
    )

    implement_path = commands / "sp.implement.md"
    assert implement_path in repaired
    repaired_implement = implement_path.read_text(encoding="utf-8")
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" not in repaired_implement
    assert f"{binary} compass --intent implement" in repaired_implement


def test_toml_command_integration_rebinds_cognition_recovery_as_valid_toml(
    tmp_path,
) -> None:
    integration = get_integration("gemini")
    project = tmp_path / "project"
    config = project / ".specify" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "specify_launcher": {
                    "command": "python -m specify_cli",
                    "argv": ["python", "-m", "specify_cli"],
                }
            }
        ),
        encoding="utf-8",
    )
    manifest = IntegrationManifest("gemini", project)

    integration.setup(project, manifest, script_type="sh")

    implement_path = integration.commands_dest(project) / "sp.implement.toml"
    initial = tomllib.loads(implement_path.read_text(encoding="utf-8"))
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE:project-cognition" in initial["prompt"]

    binary = project / ".specify" / "tools" / "project-cognition.exe"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    write_project_cognition_launcher_config(project, binary)

    repaired = integration.repair_runtime_assets(
        project,
        manifest,
        script_type="sh",
    )

    assert implement_path in repaired
    repaired_payload = tomllib.loads(implement_path.read_text(encoding="utf-8"))
    assert "PROJECT_COGNITION_LAUNCHER_UNAVAILABLE" not in repaired_payload["prompt"]
    assert f"{binary} compass --intent implement" in repaired_payload["prompt"]


def test_advanced_upgrade_prunes_only_unmodified_retired_spx_files(tmp_path) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    skills = integration.skills_dest(project)
    retired = skills / "spx-plan" / "references" / "retired.md"
    customized = skills / "spx-plan" / "references" / "customized-retired.md"
    retired.write_text("managed old reference\n", encoding="utf-8")
    customized.write_text("managed old reference\n", encoding="utf-8")
    manifest.record_existing(retired.relative_to(project))
    manifest.record_existing(customized.relative_to(project))
    customized.write_text("user-customized reference\n", encoding="utf-8")

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )

    assert not retired.exists()
    assert customized.read_text(encoding="utf-8") == "user-customized reference\n"
    assert customized.relative_to(project).as_posix() in manifest.files


def test_advanced_surface_map_covers_classic_commands_and_declared_files() -> None:
    surface_map = json.loads(
        (ADVANCED_SKILLS / "_shared" / "surface-map.json").read_text(encoding="utf-8")
    )
    assert surface_map["schema_version"] == 2
    assert surface_map["design"]["equivalence"] == (
        "command-equivalent, prompt-optimized"
    )
    assert set(surface_map["classic_companion_skills"]) == (
        CLASSIC_MAP_COMPANION_SKILLS
    )
    assert surface_map["skills"].keys() == SPX_SKILLS

    mapped_commands = []
    for skill_name, contract in surface_map["skills"].items():
        mapped_commands.extend(contract["absorbs"])
        declared = {*contract["references"], *contract["assets"]}
        for relative in declared:
            assert (ADVANCED_SKILLS / relative).is_file(), (
                skill_name,
                relative,
            )
        skill_dir = ADVANCED_SKILLS / skill_name
        actual = {
            path.relative_to(ADVANCED_SKILLS).as_posix()
            for directory in ("references", "assets")
            for path in (skill_dir / directory).glob("*")
            if path.is_file()
        }
        assert declared == actual, skill_name

    classic_commands = {
        path.stem for path in (PROJECT_ROOT / "templates" / "commands").glob("*.md")
    }
    assert len(mapped_commands) == len(set(mapped_commands))
    assert set(mapped_commands) == classic_commands
    for command in classic_commands:
        assert surface_map["skills"][f"spx-{command}"]["absorbs"] == [command]
    assert surface_map["skills"]["spx-map-rebuild"]["absorbs"] == []

    for relative in surface_map["shared_references"]:
        assert (ADVANCED_SKILLS / relative).is_file()


def test_advanced_views_do_not_fork_canonical_machine_contracts() -> None:
    forbidden_machine_copies = {
        "spec-contract.json",
        "plan-contract.json",
        "task-index.json",
        "execution-state.json",
        "lifecycle.json",
    }
    assert not {path.name for path in ADVANCED_SKILLS.rglob("*.json")}.intersection(
        forbidden_machine_copies
    )

    for required in (
        "spx-specify/assets/spec.md",
        "spx-plan/assets/plan.md",
        "spx-tasks/assets/tasks.md",
        "spx-checklist/assets/checklist.md",
        "spx-quick/assets/status.md",
        "spx-debug/assets/debug-session.md",
    ):
        assert (ADVANCED_SKILLS / required).is_file()


def test_advanced_map_phases_keep_independent_write_boundaries() -> None:
    scan = (ADVANCED_SKILLS / "spx-map-scan" / "SKILL.md").read_text(encoding="utf-8")
    build = (ADVANCED_SKILLS / "spx-map-build" / "SKILL.md").read_text(encoding="utf-8")
    rebuild = (ADVANCED_SKILLS / "spx-map-rebuild" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for required in ("scan-prepare", "scan-accept", "validate-scan"):
        assert required in scan
    assert "Do not run\n`build-from-scan`" in scan
    assert "validate-build" not in scan

    for required in ("validate-scan", "build-from-scan", "validate-build"):
        assert required in build
    for forbidden in ("scan-set", "scan-prepare", "scan-accept"):
        assert forbidden not in build
    assert "complete-refresh" in build
    assert "Do not ask a model" in build

    assert "$spx-map-scan" in rebuild
    assert "$spx-map-build" in rebuild
    for forbidden in ("scan-prepare", "scan-accept", "build-from-scan"):
        assert forbidden not in rebuild


def test_advanced_source_commands_use_launcher_placeholders() -> None:
    bare_command = re.compile(r"`(?:specify|sp-teams)\s+[^`]+`")
    for path in ADVANCED_SKILLS.rglob("*.md"):
        if "assets" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        assert bare_command.search(content) is None, path

    assert "{{specify-subcmd:implement resume-audit" in (
        ADVANCED_SKILLS / "spx-implement" / "references" / "execution-contract.md"
    ).read_text(encoding="utf-8")
    assert "{{specify-subcmd:sp-teams auto-dispatch" in (
        ADVANCED_SKILLS / "spx-implement-teams" / "references" / "codex-teams.md"
    ).read_text(encoding="utf-8")


def test_classic_profile_keeps_existing_skills_and_does_not_install_spx(
    tmp_path,
) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"
    manifest = IntegrationManifest("codex", project)

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )

    skills_dir = integration.skills_dest(project)
    legacy_plan = skills_dir / "sp-plan" / "SKILL.md"
    assert legacy_plan.exists()
    assert _frontmatter(legacy_plan)["metadata"]["source"] == (
        "templates/commands/plan.md"
    )
    assert not any(skills_dir.glob("spx-*/SKILL.md"))


@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATIONS)
def test_all_skills_integrations_support_the_advanced_profile(
    tmp_path,
    integration_key,
) -> None:
    integration = get_integration(integration_key)
    project = tmp_path / integration_key
    manifest = IntegrationManifest(integration_key, project)

    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )

    skills_dir = integration.skills_dest(project)
    installed = {path.parent.name for path in skills_dir.glob("spx-*/SKILL.md")}
    assert installed == SPX_SKILLS, integration_key
    installed_classic = {path.parent.name for path in skills_dir.glob("sp-*/SKILL.md")}
    assert installed_classic == CLASSIC_MAP_COMPANION_SKILLS, integration_key
    assert not (skills_dir / "sp-plan" / "SKILL.md").exists(), integration_key
    assert not (skills_dir / "spec-kit-workflow-routing" / "SKILL.md").exists(), (
        integration_key
    )

    if integration_key in {"claude", "vibe"}:
        for skill_name in SPX_SKILLS:
            skill = skills_dir / skill_name / "SKILL.md"
            assert _frontmatter(skill)["user-invocable"] is True

    cognition_reference = (
        skills_dir / "spx-ask" / "references" / "project-cognition.md"
    ).read_text(encoding="utf-8")
    expected_handoff = (
        "/skill:spx-map-rebuild"
        if integration_key == "kimi"
        else (
            "$spx-map-rebuild"
            if integration_key in {"agy", "codex", "trae", "zcode"}
            else "/spx-map-rebuild"
        )
    )
    assert expected_handoff in cognition_reference
    if not expected_handoff.startswith("$"):
        assert "$spx-map-rebuild" not in cognition_reference

    invocation_prefix = (
        "/skill:"
        if integration_key == "kimi"
        else "$" if integration_key in {"agy", "codex", "trae", "zcode"} else "/"
    )
    for skill_name, next_skill in (
        ("spx-specify", "spx-plan"),
        ("spx-plan", "spx-tasks"),
        ("spx-tasks", "spx-implement"),
    ):
        installed_skill = re.sub(
            r"\s+",
            " ",
            (skills_dir / skill_name / "SKILL.md")
            .read_text(encoding="utf-8")
            .lower(),
        )
        assert "this invocation authorizes only this workflow stage" in installed_skill
        expected_next = f"{invocation_prefix}{next_skill}"
        assert f"do not invoke `{expected_next}`" in installed_skill


def test_classic_then_advanced_profiles_are_additive_in_the_manifest(tmp_path) -> None:
    integration = get_integration("codex")
    project = tmp_path / "project"

    classic_manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        classic_manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )
    skills_dir = integration.skills_dest(project)
    classic_map_bytes = {
        skill_name: {
            path.relative_to(skills_dir / skill_name).as_posix(): path.read_bytes()
            for path in (skills_dir / skill_name).rglob("*")
            if path.is_file()
        }
        for skill_name in CLASSIC_MAP_COMPANION_SKILLS
    }
    classic_manifest.save()

    advanced_manifest = IntegrationManifest.load("codex", project)
    integration.setup(
        project,
        advanced_manifest,
        parsed_options={"workflow_profile": "advanced"},
        script_type="sh",
    )
    advanced_manifest.save()

    assert (skills_dir / "sp-plan" / "SKILL.md").exists()
    assert (skills_dir / "spx-plan" / "SKILL.md").exists()
    advanced_map_bytes = {
        skill_name: {
            path.relative_to(skills_dir / skill_name).as_posix(): path.read_bytes()
            for path in (skills_dir / skill_name).rglob("*")
            if path.is_file()
        }
        for skill_name in CLASSIC_MAP_COMPANION_SKILLS
    }
    assert advanced_map_bytes == classic_map_bytes

    tracked = IntegrationManifest.load("codex", project).files
    assert ".codex/skills/sp-plan/SKILL.md" in tracked
    assert ".codex/skills/spx-plan/SKILL.md" in tracked


def test_profile_metadata_is_isolated_between_skills_integrations(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        classic = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "claude",
                "--workflow-profile",
                "classic",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        advanced = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "codex",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert classic.exit_code == 0, classic.output
    assert advanced.exit_code == 0, advanced.output
    for skill_name in SPX_SKILLS:
        assert f"${skill_name}" in advanced.output
    for skill_name in CLASSIC_MAP_COMPANION_SKILLS:
        assert f"${skill_name}" in advanced.output
    options = json.loads(
        (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
    )
    assert options["workflow_profiles_by_integration"] == {
        "claude": ["classic"],
        "codex": ["advanced"],
    }
    integration_state = json.loads(
        (project / ".specify" / "integration.json").read_text(encoding="utf-8")
    )
    assert integration_state["integration"] == "codex"
    assert integration_state["workflow_profiles"] == ["advanced"]
    assert not (project / ".codex" / "skills" / "sp-plan").exists()


def test_non_skills_integrations_do_not_install_spx(tmp_path) -> None:
    integration = get_integration("gemini")
    project = tmp_path / "project"
    manifest = IntegrationManifest("gemini", project)

    integration.setup(project, manifest, script_type="sh")

    assert not any(path.name.startswith("spx-") for path in project.rglob("spx-*"))


@pytest.mark.parametrize(
    "profile_order",
    [("advanced", "classic"), ("classic", "advanced")],
)
def test_init_can_install_both_profiles_without_losing_either(
    tmp_path,
    profile_order,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        results = []
        for profile in profile_order:
            results.append(
                runner.invoke(
                    app,
                    [
                        "init",
                        "--here",
                        "--force",
                        "--ai",
                        "codex",
                        "--workflow-profile",
                        profile,
                        "--script",
                        "sh",
                        "--no-git",
                        "--ignore-agent-tools",
                    ],
                    catch_exceptions=False,
                )
            )
    finally:
        os.chdir(old_cwd)

    for result in results:
        assert result.exit_code == 0, result.output

    skills_dir = project / ".codex" / "skills"
    assert (skills_dir / "spx-plan" / "SKILL.md").exists()
    assert (skills_dir / "spx-fast" / "SKILL.md").exists()
    assert (skills_dir / "spx-quick" / "SKILL.md").exists()
    assert (skills_dir / "sp-plan" / "SKILL.md").exists()

    project_config = json.loads(
        (project / ".specify" / "config.json").read_text(encoding="utf-8")
    )
    cognition_binary = project_config["project_cognition_launcher"]["argv"][0]
    installed_cognition = (
        skills_dir / "spx-ask" / "references" / "project-cognition.md"
    ).read_text(encoding="utf-8")
    assert cognition_binary in installed_cognition
    assert "{{specify-subcmd:" not in installed_cognition

    init_options = json.loads(
        (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
    )
    assert init_options["workflow_profile"] == profile_order[-1]
    assert init_options["installed_workflow_profiles"] == list(profile_order)

    manifest = json.loads(
        (project / ".specify" / "integrations" / "codex.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert ".codex/skills/spx-plan/SKILL.md" in manifest["files"]
    assert ".codex/skills/spx-fast/SKILL.md" in manifest["files"]
    assert ".codex/skills/spx-quick/SKILL.md" in manifest["files"]
    assert ".codex/skills/sp-plan/SKILL.md" in manifest["files"]

    integration_state = json.loads(
        (project / ".specify" / "integration.json").read_text(encoding="utf-8")
    )
    assert integration_state["workflow_profiles"] == list(profile_order)
    assert integration_state["team"]["surface"] == "sp-teams"


def test_advanced_only_codex_repair_restores_runtime_without_unrelated_classic_skill(
    tmp_path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        initialized = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "codex",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        missing_reference = (
            project
            / ".codex"
            / "skills"
            / "spx-implement"
            / "references"
            / "execution-contract.md"
        )
        missing_asset = (
            project / ".codex" / "skills" / "spx-quick" / "assets" / "status.md"
        )
        missing_reference.unlink()
        missing_asset.unlink()
        repaired = runner.invoke(
            app,
            ["integration", "repair", "--script", "sh"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert initialized.exit_code == 0, initialized.output
    assert repaired.exit_code == 0, repaired.output
    assert missing_reference.exists()
    assert "{{specify-subcmd:" not in missing_reference.read_text(encoding="utf-8")
    assert missing_asset.exists()
    assert not (project / ".codex" / "skills" / "sp-plan").exists()
    assert not (project / ".codex" / "skills" / "sp-teams").exists()
    for skill_name in CLASSIC_MAP_COMPANION_SKILLS:
        assert (project / ".codex" / "skills" / skill_name / "SKILL.md").exists()

    integration_state = json.loads(
        (project / ".specify" / "integration.json").read_text(encoding="utf-8")
    )
    assert integration_state["workflow_profiles"] == ["advanced"]
    assert integration_state["team"]["surface"] == "sp-teams"
    assert (project / ".specify" / "teams" / "runtime.json").is_file()


def test_uninstall_clears_workflow_profile_metadata(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        initialized = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "codex",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
        uninstalled = runner.invoke(
            app,
            ["integration", "uninstall", "codex", "--force"],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert initialized.exit_code == 0, initialized.output
    assert uninstalled.exit_code == 0, uninstalled.output

    init_options = json.loads(
        (project / ".specify" / "init-options.json").read_text(encoding="utf-8")
    )
    assert "workflow_profile" not in init_options
    assert "installed_workflow_profiles" not in init_options


def test_advanced_profile_is_rejected_for_non_skills_integration(tmp_path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runner = CliRunner()

    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        result = runner.invoke(
            app,
            [
                "init",
                "--here",
                "--force",
                "--ai",
                "gemini",
                "--workflow-profile",
                "advanced",
                "--script",
                "sh",
                "--no-git",
                "--ignore-agent-tools",
            ],
            catch_exceptions=False,
        )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 1
    assert "advanced workflow profile requires a skills-based integration" in (
        result.output.lower()
    )
