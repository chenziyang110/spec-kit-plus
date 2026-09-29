    "plan": "Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.",
    "test-design": "Use when a project or planned feature needs an evidence-backed test universe, professional test-case catalog, test-data/material pack, explicit gaps, and a pointer-only handoff before task generation.",
    "tasks": "Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation; clean task packages hand off directly to implement.",
    "implement": "Use when tasks.md exists and workflow state records /sp.implement for the tracked implementation workflow.",
@app.command("test-design", help=SKILL_DESCRIPTIONS["test-design"])
def test_design_command() -> None:
    """Workflow entrypoint surface for planning-only test design."""
    _workflow_entrypoint_surface_only("test-design")


@discussion_app.callback(invoke_without_command=True)
def discussion_command(ctx: typer.Context) -> None:
            ("quick", "resumable direct delivery at any size"),
            ("specify", "requirements and acceptance"),
            ("test-design", "optional test universe and data pack before tasks"),
            ("tasks", "dependency-aware execution task graph"),
            ("taskstoissues", "explicit GitHub issue export"),
    steps_lines.append(
        f"   - [cyan]{_display_cmd('test-design')}[/] - Optionally compile a complete-against-scope test universe, professional cases, and test-data/material pack after [cyan]{_display_cmd('plan')}[/] and before [cyan]{_display_cmd('tasks')}[/]"
    )
    steps_lines.append(
        f"   - [cyan]{_display_cmd('checklist')}[/] - Optional requirements-quality checklist aid after [cyan]{_display_cmd('plan')}[/]"
    )
            f"○ [cyan]{_display_cmd('test-design')}[/] [bright_black](optional after plan)[/bright_black] - Compile an evidence-backed test universe, professional case catalog, data/material decisions, gaps, and a pointer-only handoff before [cyan]{_display_cmd('tasks')}[/]",
            f"○ [cyan]{_display_cmd('analyze')}[/] [bright_black](optional diagnostic / legacy revalidation)[/bright_black] - Cross-artifact consistency & alignment report, including boundary guardrail drift when explicitly requested or recorded in existing state",
            f"○ [cyan]{_display_cmd('explain')}[/] [bright_black](optional)[/bright_black] - Explain the current spec, plan, task, implement, or project cognition/runtime artifact in plain language before moving forward",
