import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_TUI_TEMPLATE_PATHS = (
    "templates/commands/specify.md",
    "templates/commands/clarify.md",
    "templates/commands/spec-extend.md",
    "templates/commands/explain.md",
)
ASCII_CARD_HEADER_RE = re.compile(r"(?m)^\s*\+--")
ASCII_CARD_LINE_RE = re.compile(r"(?m)^\s*\| .+\|\s*$")
ASCII_CARD_FOOTER_RE = re.compile(r"(?m)^\s*\+-{10,}\+?\s*$")


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _extract_step_6_strategy_block(content: str) -> str:
    lowered = content.lower()
    start = lowered.find("6. select an execution strategy for each ready batch before writing code:")
    assert start != -1
    end = lowered.find("\n7. execute implementation following the task plan:", start)
    assert end != -1
    return lowered[start:end]


def _assert_contains_any(text: str, *needles: str) -> None:
    assert any(needle in text for needle in needles), f"Expected one of: {needles}"


def test_specify_template_uses_alignment_first_contract():
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "alignment.md" in content
    assert "aligned: ready for plan" in lowered
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "Task Classification" in content or "task classification" in lowered
    assert "user's current language" in lowered
    assert "Business Goals" in content
    assert "Users & Roles" in content
    assert "Technical Constraints / Assumptions" in content
    assert "Outstanding Questions" in content
    assert "Default to concise clarification turns" in content
    assert "Do not restate the full current understanding after every answer" in content
    assert "Save the full synthesis for the alignment-ready turn" in content
    assert re.search(r"open (question )?blocks?", lowered)
    _assert_contains_any(lowered, "stage header", "stage title")
    _assert_contains_any(lowered, "question header", "question title")
    _assert_contains_any(lowered, "prompt", "question stem")
    _assert_contains_any(lowered, "recommendation", "recommended item", "[ recommended ]")
    _assert_contains_any(lowered, "reply instruction", "reply guidance", "response instruction")
    assert "example" in lowered
    assert "options" in lowered
    assert "question-card format" not in lowered
    assert "boxed card" not in lowered
    assert "Do not repeat the same question" in content
    assert "Ask at most one unanswered high-impact question per message" in content
    assert "each clarification turn should contain at most one short checkpoint" in content
    assert "decompose" in lowered
    assert "first-release scope" in lowered
    assert "mvp scope" not in lowered
    assert "choose_execution_strategy(command_name=\"specify\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "repository and local context analysis" in lowered
    assert "external references and supporting material analysis" in lowered
    assert "ambiguity, risk, and gap analysis" in lowered
    assert "before capability decomposition" in lowered
    assert "before writing `spec.md` and `alignment.md`" in content
    assert "specify team" not in lowered
    assert "Docs/config/process change:" in content
    assert "compatibility/process constraints" in content
    assert "completion criteria" in content
    assert "Task classification changes which requirement dimensions are probed" in content
    assert "planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria" in content
    assert "Make the next question build directly on the user's most recent answer" in content
    assert "rather than resetting to generic prompts" in content
    assert "vague, shallow, or contradictory" in content
    assert "targeted narrowing question, example, or recommendation" in content
    assert "Do not accept long but still ambiguous answers as sufficient." in content
    assert "Do not turn this into a freeform brainstorming workflow." in content
    assert "guided requirement discovery" in lowered
    assert "recommendation and example scaffolding" in lowered
    assert "current-understanding or confirmation gate" in lowered
    assert "confirm or correct the current understanding before `Aligned: ready for plan`" in content
    assert "common docs/config/process-change flows can reach planning-ready alignment inside `sp-specify`" in content
    assert "explicit pre-release check" in lowered
    assert "without needing `/sp.clarify` or `/sp.spec-extend`" in content


def test_primary_tui_templates_avoid_closed_ascii_card_examples():
    for template_path in PRIMARY_TUI_TEMPLATE_PATHS:
        content = _read(template_path)

        assert not ASCII_CARD_HEADER_RE.search(content), (
            f"{template_path} still defines an ASCII card header"
        )
        assert not ASCII_CARD_LINE_RE.search(content), (
            f"{template_path} still defines right-side pipe framing"
        )
        assert not ASCII_CARD_FOOTER_RE.search(content), (
            f"{template_path} still defines an ASCII box closure"
        )


def test_plan_template_requires_alignment_report_before_planning():
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    assert "alignment.md" in content
    assert "Missing alignment report" in content
    assert "Force proceed with known risks" in content
    assert "Input Risks From Alignment" in content
    assert "user's current language" in lowered
    assert "choose_execution_strategy(command_name=\"plan\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "research" in lowered
    assert "data model" in lowered
    assert "contracts" in lowered
    assert "quickstart and validation scenarios" in lowered
    assert "before final constitution and risk re-check" in lowered
    assert "before writing the consolidated implementation plan" in lowered
    assert "specify team" not in lowered
    assert "specify -> clarify -> plan" not in lowered


def test_tasks_template_documents_shared_routing_before_decomposition():
    content = _read("templates/commands/tasks.md")
    lowered = content.lower()

    assert "choose_execution_strategy(command_name=\"tasks\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "story and phase decomposition" in lowered
    assert "dependency graph analysis" in lowered
    assert "write-set and parallel-safety analysis" in lowered
    assert "before writing `tasks.md`" in content
    assert "before emitting canonical parallel batches and join points" in lowered
    assert "specify team" not in lowered


def test_explain_template_documents_conservative_routing_contract():
    content = _read("templates/commands/explain.md")
    lowered = content.lower()

    assert "choose_execution_strategy(command_name=\"explain\"" in content
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "default to `single-agent`" in lowered
    assert "primary artifact reading" in lowered
    assert "supporting artifact cross-check" in lowered
    assert "before rendering the final explanation" in lowered
    assert "specify team" not in lowered


def test_clarify_template_is_compatibility_only():
    content = _read("templates/commands/clarify.md")
    lowered = content.lower()

    assert "recommend" in lowered or "redirect" in lowered or "route" in lowered or "main path" in lowered
    assert "alignment.md" in content
    assert "adding newly provided requirements or constraints" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
    assert "user's current language" in content.lower()


def test_new_analysis_workflow_command_templates_exist():
    command_dir = PROJECT_ROOT / "templates" / "commands"
    template_stems = {path.stem for path in command_dir.glob("*.md")}

    assert "spec-extend" in template_stems
    assert "explain" in template_stems


def test_spec_template_defines_scope_boundaries_without_open_clarification_examples():
    content = _read("templates/spec-template.md")

    assert "## Scope Boundaries" in content
    assert "### In Scope" in content
    assert "### Out of Scope" in content
    assert "[NEEDS CLARIFICATION:" not in content
    assert "coherent first release" in content.lower()
    assert "viable mvp" not in content.lower()


def test_tasks_templates_default_to_phased_delivery_not_mvp():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert "phased delivery" in command_content.lower()
    assert "suggested first release scope" in command_content.lower()
    assert "parallel batch" in command_content.lower()
    assert "join point" in command_content.lower()
    assert "write set" in command_content.lower()
    assert "mvp first" not in command_content.lower()
    assert "suggested mvp scope" not in command_content.lower()

    assert "phased delivery" in template_content.lower()
    assert "first release candidate" in template_content.lower()
    assert "parallel batch" in template_content.lower()
    assert "join point" in template_content.lower()
    assert "write set" in template_content.lower()
    assert "mvp first" not in template_content.lower()
    assert "mvp increment" not in template_content.lower()
    assert "mvp!" not in template_content.lower()


def test_implement_template_supports_capability_aware_parallel_batches():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    step_6 = _extract_step_6_strategy_block(content)

    assert "parallel batches" in lowered
    assert "current agent" in lowered
    assert "ready tasks" in lowered
    assert "join point" in lowered
    assert "shared registration files" in lowered
    assert "execution strategy" in lowered
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "parallel_batches" in lowered
    assert "no-safe-batch" in lowered
    assert "native-supported" in lowered
    assert "native-missing" in lowered
    assert "specify team" not in lowered
    assert "auto-dispatch" not in lowered
    assert "codex runtime rule" not in lowered

    no_safe_batch = step_6.find("parallel_batches <= 0")
    native_supported = step_6.find("native_multi_agent")
    native_missing = step_6.find("sidecar_runtime_supported")
    fallback = step_6.find("fallback")

    assert no_safe_batch != -1
    assert native_supported != -1
    assert native_missing != -1
    assert fallback != -1
    assert no_safe_batch < native_supported < native_missing < fallback


def test_implement_template_defines_leader_only_milestone_scheduler_contract():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()

    assert "invoking runtime acts as the leader" in lowered
    assert "delegated worker lane" in lowered
    assert "next executable phase" in lowered
    assert "shared implement template is the primary source of truth" in lowered


def test_alignment_template_exists():
    content = _read("templates/alignment-template.md")

    assert "# Requirement Alignment Report:" in content
    assert "## Release Decision" in content
    assert "Aligned: ready for plan" in content
    assert "Force proceed with known risks" in content
