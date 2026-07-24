"""Generated-agent contract for the unified workflow artifact runtime.

These tests intentionally describe the breaking target contract.  They stay RED
until Classic, Advanced, and delegated-worker surfaces route fixed workflow
artifact access through ``specify-runtime``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specify_cli import _install_shared_infra
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


_TEXT_SUFFIXES = {".json", ".md", ".toml", ".yaml", ".yml"}
_NAKED_RUNTIME_COMMAND = re.compile(
    r"\b(?:project-cognition\s+(?:"
    r"build-from-scan|changes|claim-reconcile|closeout-plan|compass|"
    r"complete-refresh|generate-ignore|init-empty|mark-dirty|query|"
    r"record-refresh|scan-(?:accept|checkpoint|lease|prepare|requeue|"
    r"set|status|yield)|semantic-audit-resume|status|update|"
    r"validate-(?:build|scan)"
    r")|spec-lint\s+(?:check|fix|lint|scan|validate))\b",
    re.IGNORECASE,
)
_PYTHON_WORKFLOW_COMMAND = re.compile(
    r"(?<![\w-])specify\s+workflow\s+(?:"
    r"show|enter|next|complete-stage|transition|reopen|block|resolve|closeout"
    r")\b",
    re.IGNORECASE,
)
_SPECIFY_SUBCMD = re.compile(r"\{\{specify-subcmd:(?P<command>[^}]+)}}")
_INLINE_CODE = re.compile(r"`(?P<command>[^`\r\n]+)`")
_RUNTIME_CALL = re.compile(
    r"(?:\bSPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:)?\bspecify-runtime(?:\.exe)?\s+"
    r"(?P<namespace>[a-z][a-z0-9-]*)(?:\s+(?P<verb>[a-z][a-z0-9-]*))?"
    r"(?:\s+(?P<nested_verb>[a-z][a-z0-9-]*))?",
    re.IGNORECASE,
)
_EXECUTABLE_PREFIX = re.compile(
    r"^\s*(?:\$|PS>|Run\s+|Use\s+|Only\s+|Executing:\s+|To execute:\s+|"
    r"SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:|specify-runtime(?:\.exe)?\b|"
    r"uvx\b|python(?:3)?\b|py\b|[A-Za-z]:[\\/]|/(?:Users|home)/)",
    re.IGNORECASE,
)
_NEGATIVE_EXECUTION_CONTEXT = re.compile(
    r"\b(?:do not|don't|never|must not|not required|not executable|"
    r"documentation-only|display-only|literal|example only)\b",
    re.IGNORECASE,
)
_FORBIDDEN_RENDERED_RUNTIME_LAUNCHER = re.compile(
    r"\buvx\s+--from\b|"
    r"\bspecify\s+specify-runtime\b|"
    r"\b(?:python(?:3)?|py)\s+(?:-[A-Za-z]\s+)*-m\s+specify_cli\b|"
    r"\b(?:python(?:3)?|py)\s+[^`\r\n]*(?:specify_cli|specify-runtime)\b|"
    r"(?:[A-Za-z]:[\\/](?:Users|Documents and Settings)[^`\r\n]*specify-runtime(?:\.exe)?\b)|"
    r"(?:/(?:Users|home)/[^`\r\n]*specify-runtime\b)",
    re.IGNORECASE,
)
_CAPABILITY_LITERAL = re.compile(r'"([a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+)"')

_COGNITION_NESTED_VERBS = {
    "claim-reconcile",
    "delta",
}


CLASSIC_ARTIFACT_SURFACES = {
    "specify": ("sp-specify", "spec.md"),
    "plan": ("sp-plan", "plan.md"),
    "tasks": ("sp-tasks", "tasks.md"),
    "implement": ("sp-implement", "implement-tracker.md"),
    "review": ("sp-review", "review-state.json"),
    "accept": ("sp-accept", "human-acceptance.json"),
    "discussion": ("sp-discussion", "discussion-state.json"),
    "quick": ("sp-quick", "status.md"),
    "debug": ("sp-debug", ".planning/debug"),
    "map-scan": ("sp-map-scan", "status.json"),
    "map-build": ("sp-map-build", "project-cognition.db"),
    "map-update": ("sp-map-update", "project-cognition.db"),
}


ADVANCED_ARTIFACT_SURFACES = {
    "specify": ("spx-specify", "spec.md"),
    "plan": ("spx-plan", "plan.md"),
    "tasks": ("spx-tasks", "tasks.md"),
    "implement": ("spx-implement", "implement-tracker.md"),
    "review": ("spx-review", "review-state.json"),
    "accept": ("spx-accept", "human-acceptance.json"),
    "discussion": ("spx-discussion", "discussion write-handoff"),
    "quick": ("spx-quick", "status.md"),
    "debug": ("spx-debug", "debug-session.md"),
    "map-scan": ("spx-map-scan", "scan-prepare"),
    "map-build": ("spx-map-build", "build-from-scan"),
    "map-update": ("spx-map-update", "complete-refresh"),
}


WORKER_ARTIFACT_SURFACES = {
    "specify-observer": ("specify-observer.md", "specify-draft.md"),
    "implementer": ("implementer.md", "delegated result handoff path"),
    "task-reviewer": ("task-reviewer.md", "worker-results/"),
    "quick-worker": ("quick-worker.md", "status.md"),
    "debug-investigator": ("debug-investigator.md", "debug file"),
    "map-scan-worker": ("map-scan-worker.md", "scan-checkpoint"),
}


RUNTIME_ARTIFACT_BOUNDARY = "fixed workflow artifact boundary"
REQUIRED_ARTIFACT_COMMANDS = (
    "specify-runtime artifact show",
    "specify-runtime artifact prepare",
    "specify-runtime artifact submit",
)


def _install_codex_profile(project: Path, profile: str) -> Path:
    integration = get_integration("codex")
    assert integration is not None
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type="sh",
    )
    return integration.skills_dest(project)


@pytest.fixture(scope="module")
def generated_agent_surfaces(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Path]:
    classic_project = tmp_path_factory.mktemp("runtime-classic")
    advanced_project = tmp_path_factory.mktemp("runtime-advanced")
    worker_project = tmp_path_factory.mktemp("runtime-workers")

    classic = _install_codex_profile(classic_project, "classic")
    advanced = _install_codex_profile(advanced_project, "advanced")
    assert _install_shared_infra(worker_project, "sh") is True

    return {
        "classic": classic,
        "advanced": advanced,
        "workers": worker_project / ".specify" / "templates" / "worker-prompts",
    }


def _read_generated_tree(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    )
    assert files, f"expected generated text files under {root}"
    return "\n".join(path.read_text(encoding="utf-8") for path in files).lower()


def _generated_text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    )


def _executable_snippets(content: str) -> list[tuple[int, str]]:
    snippets: list[tuple[int, str]] = []
    in_fence = False
    fence_language = ""
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            if in_fence:
                in_fence = False
                fence_language = ""
            else:
                in_fence = True
                fence_language = stripped[3:].strip().lower()
            continue

        for match in _SPECIFY_SUBCMD.finditer(line):
            command = match.group("command").strip()
            if command:
                snippets.append((line_number, command))

        if _NEGATIVE_EXECUTION_CONTEXT.search(line):
            continue

        for match in _INLINE_CODE.finditer(line):
            command = match.group("command").strip()
            if _EXECUTABLE_PREFIX.search(command):
                snippets.append((line_number, command))

        if in_fence and fence_language in {"", "bash", "sh", "shell", "powershell", "ps1"}:
            if stripped and _EXECUTABLE_PREFIX.search(stripped):
                snippets.append((line_number, stripped))
    return snippets


def _runtime_capability_for_call(command: str) -> str | None:
    match = _RUNTIME_CALL.search(command)
    if match is None:
        return None
    namespace = match.group("namespace").lower()
    verb = (match.group("verb") or "").lower()
    nested_verb = (match.group("nested_verb") or "").lower()
    if not verb:
        return None
    if namespace == "cognition" and verb in _COGNITION_NESTED_VERBS and nested_verb:
        return f"{namespace}.{verb}.{nested_verb}"
    return f"{namespace}.{verb}"


def _declared_runtime_capability_ids() -> set[str]:
    runtime_main = Path(__file__).resolve().parents[2] / "tools" / "specify-runtime" / "main.go"
    content = runtime_main.read_text(encoding="utf-8")
    start = content.index("func defaultCapabilities() []string")
    end = content.index("func defaultCapabilityCards()", start)
    return set(_CAPABILITY_LITERAL.findall(content[start:end]))


def _all_rendered_surface_calls(
    generated_agent_surfaces: dict[str, Path],
) -> list[tuple[str, int, str, str | None]]:
    calls: list[tuple[str, int, str, str | None]] = []
    for surface, root in generated_agent_surfaces.items():
        for path in _generated_text_files(root):
            content = path.read_text(encoding="utf-8")
            relative = f"{surface}:{path.relative_to(root).as_posix()}"
            for line_number, command in _executable_snippets(content):
                capability = _runtime_capability_for_call(command)
                if capability is not None or _FORBIDDEN_RENDERED_RUNTIME_LAUNCHER.search(command):
                    calls.append((relative, line_number, command, capability))
    return calls


def test_agent_facing_source_placeholders_use_only_unified_runtime() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    source_roots = (
        repository_root / "templates",
        repository_root / "src" / "specify_cli" / "integrations",
    )
    violations: list[str] = []
    for source_root in source_roots:
        for path in _generated_text_files(source_root):
            relative = path.relative_to(repository_root).as_posix()
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                for match in _SPECIFY_SUBCMD.finditer(line):
                    command = match.group("command").strip()
                    if command.startswith("specify-runtime") or command.startswith("init "):
                        continue
                    # Native hook adapter documentation still describes the
                    # human/bootstrap Python compatibility surface; generated
                    # sp-* and spx-* workflow calls may not use it.
                    if "/hooks/readme.md" in relative.lower():
                        continue
                    violations.append(f"{relative}:{line_number}: {command}")

    assert not violations, (
        "Agent-facing specify-subcmd placeholders must route through the unified "
        "project runtime only:\n" + "\n".join(violations)
    )


def _runtime_contract_errors(
    root: Path,
    surfaces: dict[str, tuple[str, str]],
    *,
    directories: bool,
) -> list[str]:
    errors: list[str] = []
    for workflow, (relative, artifact_marker) in surfaces.items():
        target = root / relative
        content = (
            _read_generated_tree(target)
            if directories
            else target.read_text(encoding="utf-8").lower()
        )

        assert artifact_marker in content, (
            f"test setup lost the representative {workflow} artifact marker "
            f"{artifact_marker!r} in {target}"
        )
        if "specify-runtime" not in content:
            errors.append(f"{workflow}: missing unified specify-runtime invocation")

        naked_commands = sorted(
            {
                command
                for line in content.splitlines()
                if "specify-runtime" not in line
                for command in _NAKED_RUNTIME_COMMAND.findall(line)
            }
        )
        if naked_commands:
            errors.append(
                f"{workflow}: contains naked legacy runtime command(s): "
                + ", ".join(naked_commands[:3])
            )
    return errors


def test_generated_classic_artifact_workflows_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["classic"],
        CLASSIC_ARTIFACT_SURFACES,
        directories=True,
    )

    assert errors == [], "\n".join(errors)


def test_generated_advanced_artifact_workflows_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["advanced"],
        ADVANCED_ARTIFACT_SURFACES,
        directories=True,
    )

    assert errors == [], "\n".join(errors)


def test_generated_worker_artifact_surfaces_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["workers"],
        WORKER_ARTIFACT_SURFACES,
        directories=False,
    )

    assert errors == [], "\n".join(errors)


def test_every_classic_workflow_has_the_shared_fixed_artifact_boundary(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    classic = generated_agent_surfaces["classic"]
    errors: list[str] = []
    for skill in sorted(classic.glob("sp-*/SKILL.md")):
        content = skill.read_text(encoding="utf-8").lower()
        missing = [command for command in REQUIRED_ARTIFACT_COMMANDS if command not in content]
        if RUNTIME_ARTIFACT_BOUNDARY not in content or missing:
            errors.append(f"{skill.parent.name}: missing boundary commands {missing}")

    assert len(list(classic.glob("sp-*/SKILL.md"))) == 30
    assert errors == [], "\n".join(errors)


def test_every_advanced_workflow_has_the_shared_fixed_artifact_boundary(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    advanced = generated_agent_surfaces["advanced"]
    errors: list[str] = []
    for skill in sorted(advanced.glob("spx-*/SKILL.md")):
        content = skill.read_text(encoding="utf-8").lower()
        missing = [command for command in REQUIRED_ARTIFACT_COMMANDS if command not in content]
        if RUNTIME_ARTIFACT_BOUNDARY not in content or missing:
            errors.append(f"{skill.parent.name}: missing boundary commands {missing}")

    assert len(list(advanced.glob("spx-*/SKILL.md"))) == 31
    assert errors == [], "\n".join(errors)


def test_worker_prompts_name_only_implemented_runtime_artifact_namespaces(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    workers = generated_agent_surfaces["workers"]
    errors: list[str] = []
    for prompt in sorted(workers.glob("*.md")):
        content = prompt.read_text(encoding="utf-8").lower()
        missing = [command for command in REQUIRED_ARTIFACT_COMMANDS if command not in content]
        unsupported = [
            command
            for command in (
                "specify-runtime context",
                "specify-runtime evidence",
                "specify-runtime session",
            )
            if command in content
        ]
        if RUNTIME_ARTIFACT_BOUNDARY not in content or missing or unsupported:
            errors.append(
                f"{prompt.name}: missing boundary commands {missing}; unsupported {unsupported}"
            )

    assert errors == [], "\n".join(errors)


def test_generated_workflows_do_not_name_unimplemented_runtime_namespaces(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    unsupported = (
        "specify-runtime context",
        "specify-runtime evidence",
        "specify-runtime session",
    )
    errors: list[str] = []
    for profile in ("classic", "advanced"):
        root = generated_agent_surfaces[profile]
        content = _read_generated_tree(root).lower()
        for command in unsupported:
            if command in content:
                errors.append(f"{profile}: unsupported namespace {command}")

    assert errors == [], "\n".join(errors)


def test_generated_scaffolds_use_unified_runtime_not_python_control_plane(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    for profile in ("classic", "advanced"):
        content = _read_generated_tree(generated_agent_surfaces[profile]).lower()
        assert "specify-runtime artifact scaffold" in content
        assert "specify artifact scaffold" not in content


def test_generated_phase_control_uses_only_unified_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    required_verbs = (
        "show",
        "transition",
        "complete-stage",
        "block",
        "resolve",
        "closeout",
    )

    for profile in ("classic", "advanced"):
        content = _read_generated_tree(generated_agent_surfaces[profile]).lower()
        assert "workflow-runtime.json" not in content, profile
        assert _PYTHON_WORKFLOW_COMMAND.search(content) is None, profile
        for verb in required_verbs:
            command = re.compile(
                rf"\bspecify-runtime(?:\.exe)?\s+workflow\s+{re.escape(verb)}\b"
            )
            assert command.search(content), f"{profile}: missing workflow {verb}"
        assert "`workflow-state.md` is inside this boundary" in content, profile
        assert "never required-stage authority" in content, profile
        assert "only completed `accept` is terminal" in content, profile
        assert "unresolved blocker" in content, profile


def test_agent_facing_runtime_calls_do_not_embed_uvx_python_or_user_paths(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    offenders = [
        f"{relative}:{line_number}: {command}"
        for relative, line_number, command, _capability in _all_rendered_surface_calls(
            generated_agent_surfaces
        )
        if _FORBIDDEN_RENDERED_RUNTIME_LAUNCHER.search(command)
    ]

    assert offenders == [], "\n".join(offenders[:40])


def test_every_rendered_runtime_namespace_verb_is_declared_by_runtime_api(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    declared = _declared_runtime_capability_ids()
    calls = _all_rendered_surface_calls(generated_agent_surfaces)
    capabilities = sorted({capability for *_prefix, capability in calls if capability})
    missing = [
        f"{capability}: {relative}:{line_number}: {command}"
        for relative, line_number, command, capability in calls
        if capability and capability not in declared
    ]

    assert "artifact.show" in capabilities
    assert "workflow.show" in capabilities
    assert any(capability.startswith("cognition.") for capability in capabilities)
    assert missing == [], "\n".join(missing[:80])
