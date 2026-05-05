import typer
import asyncio
from typing import Optional
from pathlib import Path
from rich.console import Console

from ..cli_output import print_json
from .schema import DebugGraphState, DebugStatus
from .persistence import MarkdownPersistenceHandler
from .dispatch import (
    build_codex_dispatch_plan,
    build_codex_spawn_plan,
    format_dispatch_plan,
    format_spawn_plan,
)
from .utils import generate_slug, get_debug_dir
from .graph import run_debug_session
from ..learnings import capture_auto_learning
from ..project_map_status import inspect_project_map_freshness

console = Console()
debug_app = typer.Typer(help="Systematic debugging engine for Spec Kit Plus.")


def _link_follow_up_session(
    handler: MarkdownPersistenceHandler,
    parent_state: DebugGraphState,
    child_state: DebugGraphState,
) -> None:
    if child_state.slug not in parent_state.child_slugs:
        parent_state.child_slugs.append(child_state.slug)
    parent_state.resume_after_child = True
    parent_state.waiting_on_child_human_followup = True
    parent_state.resolution.human_verification_outcome = "derived_issue"
    parent_state.current_focus.next_action = (
        f"A linked follow-up issue is being investigated in `{child_state.slug}`. "
        "After that session is resolved, return here to finish the original human verification."
    )
    parent_state.resolution.report = handler.build_handoff_report(parent_state)
    handler.save(parent_state)


def _create_or_link_debug_state(
    description: str,
    handler: MarkdownPersistenceHandler,
) -> tuple[DebugGraphState, DebugGraphState | None]:
    slug = generate_slug(description)
    parent_state = handler.load_most_recent_awaiting_human_session()
    state = DebugGraphState(slug=slug, trigger=description)
    if parent_state:
        state.parent_slug = parent_state.slug
        _link_follow_up_session(handler, parent_state, state)
    return state, parent_state


def _project_map_preflight_for_debug() -> None:
    project_root = Path.cwd()
    if not (project_root / ".specify").exists():
        return

    result = inspect_project_map_freshness(project_root)
    freshness = result["freshness"]
    if freshness in {"missing", "stale"}:
        console.print(
            f"[red]Error:[/red] Project-map freshness is {freshness}. Refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` before debug."
        )
        for reason in result.get("reasons", []):
            console.print(f"- {reason}")
        raise typer.Exit(1)

    if freshness == "possibly_stale":
        console.print(
            "[yellow]Warning:[/yellow] Project-map freshness is possibly_stale. Continue only if the investigation is still local."
        )
        for reason in result.get("reasons", []):
            console.print(f"- {reason}")


def _print_root_cause_summary(state: DebugGraphState) -> None:
    root_cause = state.resolution.root_cause
    if not root_cause:
        return

    console.print("[bold]Root Cause Draft[/bold]")
    if root_cause.summary:
        console.print(f"- Summary: {root_cause.summary}")
    if root_cause.owning_layer:
        console.print(f"- Owning layer: {root_cause.owning_layer}")
    if root_cause.broken_control_state:
        console.print(f"- Broken control state: {root_cause.broken_control_state}")
    if root_cause.failure_mechanism:
        console.print(f"- Failure mechanism: {root_cause.failure_mechanism}")
    if root_cause.loop_break:
        console.print(f"- Closed-loop break: {root_cause.loop_break}")
    if root_cause.decisive_signal:
        console.print(f"- Primary decisive signal: {root_cause.decisive_signal}")


def _print_causal_coverage_summary(state: DebugGraphState) -> None:
    resolution = state.resolution
    if not any(
        (
            resolution.alternative_hypotheses_considered,
            resolution.alternative_hypotheses_ruled_out,
            resolution.root_cause_confidence,
        )
    ):
        return

    console.print("[bold]Causal Coverage[/bold]")
    if resolution.alternative_hypotheses_considered:
        console.print("- Alternative hypotheses considered:")
        for item in resolution.alternative_hypotheses_considered:
            console.print(f"  - {item}")
    if resolution.alternative_hypotheses_ruled_out:
        console.print("- Alternatives ruled out:")
        for item in resolution.alternative_hypotheses_ruled_out:
            console.print(f"  - {item}")
    if resolution.root_cause_confidence:
        console.print(f"- Root cause confidence: {resolution.root_cause_confidence}")


def _print_fix_closure_summary(state: DebugGraphState) -> None:
    resolution = state.resolution
    if not any((resolution.fix_scope, resolution.loop_restoration_proof)):
        return

    console.print("[bold]Fix Closure[/bold]")
    if resolution.fix_scope:
        console.print(f"- Fix scope: {resolution.fix_scope}")
    if resolution.loop_restoration_proof:
        console.print("- Loop restoration proof:")
        for item in resolution.loop_restoration_proof:
            console.print(f"  - {item}")


def _print_causal_map_summary(state: DebugGraphState) -> None:
    causal_map = state.causal_map
    if not any(
        (
            causal_map.symptom_anchor,
            causal_map.closed_loop_path,
            causal_map.break_edges,
            causal_map.family_coverage,
            causal_map.adjacent_risk_targets,
        )
    ):
        return

    console.print("[bold]Causal Map[/bold]")
    if causal_map.symptom_anchor:
        console.print(f"- Symptom anchor: {causal_map.symptom_anchor}")
    if causal_map.family_coverage:
        console.print(f"- Family coverage: {', '.join(causal_map.family_coverage)}")
    if causal_map.break_edges:
        console.print("- Break edges:")
        for edge in causal_map.break_edges:
            console.print(f"  - {edge}")
    if causal_map.adjacent_risk_targets:
        console.print("- Adjacent risk targets:")
        for target in causal_map.adjacent_risk_targets:
            target_id = target["target"] if isinstance(target, dict) else target.target
            scope = target["scope"] if isinstance(target, dict) else target.scope
            console.print(f"  - {target_id} ({scope})")


def _print_observer_framing_summary(state: DebugGraphState) -> None:
    observer = state.observer_framing
    if not any(
        (
            observer.summary,
            observer.primary_suspected_loop,
            observer.suspected_owning_layer,
            observer.suspected_truth_owner,
            observer.recommended_first_probe,
            observer.missing_questions,
            observer.alternative_cause_candidates,
        )
    ):
        return

    console.print("[bold]Observer Framing[/bold]")
    if state.observer_mode:
        console.print(f"- Mode: {state.observer_mode}")
    if state.skip_observer_reason:
        console.print(f"- Compression reason: {state.skip_observer_reason}")
    if observer.summary:
        console.print(f"- Summary: {observer.summary}")
    if observer.primary_suspected_loop:
        console.print(f"- Primary suspected loop: {observer.primary_suspected_loop}")
    if observer.suspected_owning_layer:
        console.print(f"- Suspected owning layer: {observer.suspected_owning_layer}")
    if observer.suspected_truth_owner:
        console.print(f"- Suspected truth owner: {observer.suspected_truth_owner}")
    if observer.recommended_first_probe:
        console.print(f"- Recommended first probe: {observer.recommended_first_probe}")
    if observer.missing_questions:
        console.print("- Missing questions:")
        for question in observer.missing_questions:
            console.print(f"  - {question}")
    if observer.alternative_cause_candidates:
        console.print("- Alternative cause candidates:")
        for candidate in observer.alternative_cause_candidates:
            console.print(f"  - {candidate.candidate}")


def _print_transition_memo(state: DebugGraphState) -> None:
    memo = state.transition_memo
    if not any((memo.first_candidate_to_test, memo.why_first, memo.evidence_unlock, memo.carry_forward_notes)):
        return

    console.print("[bold]Transition Memo[/bold]")
    if memo.first_candidate_to_test:
        console.print(f"- First candidate to test: {memo.first_candidate_to_test}")
    if memo.why_first:
        console.print(f"- Why first: {memo.why_first}")
    if memo.evidence_unlock:
        console.print(f"- Evidence unlock: {', '.join(memo.evidence_unlock)}")
    if memo.carry_forward_notes:
        console.print("- Carry forward:")
        for note in memo.carry_forward_notes:
            console.print(f"  - {note}")


def _print_investigation_contract_summary(state: DebugGraphState) -> None:
    contract = state.investigation_contract
    if not any((contract.primary_candidate_id, contract.candidate_queue, contract.related_risk_targets)):
        return

    console.print("[bold]Investigation Contract[/bold]")
    console.print(f"- Mode: {contract.investigation_mode.value}")
    if contract.primary_candidate_id:
        console.print(f"- Primary candidate: {contract.primary_candidate_id}")
    if contract.candidate_queue:
        console.print("- Candidate queue:")
        for candidate in contract.candidate_queue:
            status = candidate["status"] if isinstance(candidate, dict) else candidate.status.value
            candidate_id = candidate["candidate_id"] if isinstance(candidate, dict) else candidate.candidate_id
            text = candidate["candidate"] if isinstance(candidate, dict) else candidate.candidate
            console.print(f"  - {candidate_id}: {text} ({status})")
    if contract.related_risk_targets:
        console.print("- Related risk targets:")
        for target in contract.related_risk_targets:
            target_id = target["target"] if isinstance(target, dict) else target.target
            status = target["status"] if isinstance(target, dict) else target.status.value
            console.print(f"  - {target_id} ({status})")


def _print_expanded_observer_summary(state: DebugGraphState) -> None:
    expanded = state.expanded_observer
    top_candidates = state.investigation_contract.top_candidates or expanded.top_candidates
    contract_log_plan = state.investigation_contract.log_investigation_plan
    expanded_log_plan = expanded.log_investigation_plan

    def _has_log_plan(plan) -> bool:
        return any(
            (
                plan.existing_log_targets,
                plan.candidate_signal_map,
                plan.log_sufficiency_judgment,
                plan.missing_observability,
                plan.instrumentation_targets,
                plan.instrumentation_style,
                plan.user_request_packet,
            )
        )

    log_plan = contract_log_plan if _has_log_plan(contract_log_plan) else expanded_log_plan
    if not any(
        (
            state.observer_expansion_status,
            state.observer_expansion_reason,
            state.project_runtime_profile,
            state.log_readiness,
            top_candidates,
            _has_log_plan(log_plan),
        )
    ):
        return

    console.print("[bold]Expanded Observer[/bold]")
    if state.observer_expansion_status:
        console.print(f"- Observer expansion status: {state.observer_expansion_status.value}")
    if state.observer_expansion_reason:
        console.print(f"- Observer expansion reason: {state.observer_expansion_reason}")
    if state.project_runtime_profile:
        console.print(f"- Project runtime profile: {state.project_runtime_profile.value}")
    if state.log_readiness:
        console.print(f"- Log readiness: {state.log_readiness.value}")

    if top_candidates:
        console.print("- Top candidates:")
        for candidate in top_candidates:
            console.print(
                f"  - {candidate.candidate_id} ({candidate.family}, priority {candidate.investigation_priority})"
            )
            if candidate.recommended_log_probe:
                console.print(f"    Probe: {candidate.recommended_log_probe}")
            scores = candidate.engineering_scores
            score_parts: list[str] = []
            if scores.cross_layer_span is not None:
                score_parts.append(f"cross-layer span: {scores.cross_layer_span}")
            if scores.indirect_causality_risk is not None:
                score_parts.append(
                    f"indirect causality risk: {scores.indirect_causality_risk}"
                )
            if scores.evidence_gap is not None:
                score_parts.append(f"evidence gap: {scores.evidence_gap}")
            if scores.investigation_cost is not None:
                score_parts.append(f"investigation cost: {scores.investigation_cost}")
            if score_parts:
                console.print(f"    Engineering scores: {', '.join(score_parts)}")

    if _has_log_plan(log_plan):
        console.print("[bold]Runtime Log Investigation Plan[/bold]")
        if log_plan.existing_log_targets:
            console.print("- Existing log targets:")
            for target in log_plan.existing_log_targets:
                console.print(f"  - {target}")
        if log_plan.candidate_signal_map:
            console.print("- Candidate signal map:")
            for entry in log_plan.candidate_signal_map:
                signals = ", ".join(entry.signals) if entry.signals else "no signals recorded"
                console.print(f"  - {entry.candidate_id}: {signals}")
        if log_plan.log_sufficiency_judgment:
            console.print(f"- Log sufficiency judgment: {log_plan.log_sufficiency_judgment}")
        if log_plan.missing_observability:
            console.print("- Missing observability:")
            for item in log_plan.missing_observability:
                console.print(f"  - {item}")
        if log_plan.instrumentation_targets:
            console.print("- Instrumentation targets:")
            for item in log_plan.instrumentation_targets:
                console.print(f"  - {item}")
        if log_plan.instrumentation_style:
            console.print("- Instrumentation style:")
            for item in log_plan.instrumentation_style:
                console.print(f"  - {item}")
        if log_plan.user_request_packet:
            console.print("- User log request packet:")
            for packet in log_plan.user_request_packet:
                console.print(f"  - Target source: {packet.target_source}")
                console.print(f"    Time window: {packet.time_window}")
                if packet.keywords_or_fields:
                    console.print(
                        f"    Keywords/fields: {', '.join(packet.keywords_or_fields)}"
                    )
                console.print(f"    Why this matters: {packet.why_this_matters}")
                if packet.expected_signal_examples:
                    console.print(
                        "    Expected signals: "
                        + ", ".join(packet.expected_signal_examples)
                    )


def _missing_root_cause_fields(state: DebugGraphState) -> list[str]:
    root_cause = state.resolution.root_cause
    if not root_cause:
        return [
            "root cause summary",
            "owning layer",
            "broken control state",
            "failure mechanism",
            "closed-loop break",
            "primary decisive signal",
        ]

    missing: list[str] = []
    if not root_cause.summary:
        missing.append("root cause summary")
    if not root_cause.owning_layer:
        missing.append("owning layer")
    if not root_cause.broken_control_state:
        missing.append("broken control state")
    if not root_cause.failure_mechanism:
        missing.append("failure mechanism")
    if not root_cause.loop_break:
        missing.append("closed-loop break")
    if not root_cause.decisive_signal:
        missing.append("primary decisive signal")
    return missing


def _missing_causal_gate_fields(state: DebugGraphState) -> list[str]:
    missing: list[str] = []
    if len(state.observer_framing.alternative_cause_candidates) > 1:
        if len(state.resolution.alternative_hypotheses_considered) < 2:
            missing.append("alternative hypothesis coverage")
        if not state.resolution.alternative_hypotheses_ruled_out:
            missing.append("ruled-out alternative causes")
    if state.resolution.root_cause and state.resolution.root_cause_confidence != "confirmed":
        missing.append("root cause confidence set to confirmed")
    if state.resolution.fix and not state.resolution.fix_scope:
        missing.append("fix scope classification")
    if state.status in {DebugStatus.VERIFYING, DebugStatus.RESOLVED, DebugStatus.AWAITING_HUMAN} and not state.resolution.loop_restoration_proof:
        missing.append("loop restoration proof")
    return missing


def _print_session_checkpoint(state: DebugGraphState, handler: MarkdownPersistenceHandler) -> None:
    session_path = handler.debug_dir / f"{state.slug}.md"
    console.print(f"[cyan]Current stage:[/cyan] {state.status.value}")
    if state.status == DebugStatus.AWAITING_HUMAN:
        console.print(
            f"[cyan]Human verification outcome:[/cyan] {state.resolution.human_verification_outcome}"
        )
    if state.diagnostic_profile:
        console.print(f"[cyan]Diagnostic profile:[/cyan] {state.diagnostic_profile}")
    if state.suggested_evidence_lanes:
        console.print("[bold]Suggested Evidence Lanes[/bold]")
        for lane in state.suggested_evidence_lanes:
            console.print(f"- {lane.name}: {lane.focus}")
        dispatch_plan = build_codex_dispatch_plan(state)
        if dispatch_plan:
            console.print("[bold]Suggested Codex Dispatch[/bold]")
            for task in dispatch_plan:
                console.print(f"- {task.lane_name}: {task.task_summary}")
        spawn_plan = build_codex_spawn_plan(state)
        if spawn_plan:
            console.print("[bold]Suggested Codex Spawn Payloads[/bold]")
            for task in spawn_plan:
                console.print(f"- {task.lane_name}: {task.agent_type} ({task.reasoning_effort})")
    _print_causal_map_summary(state)
    _print_observer_framing_summary(state)
    _print_expanded_observer_summary(state)
    _print_transition_memo(state)
    _print_investigation_contract_summary(state)
    _print_root_cause_summary(state)
    _print_causal_coverage_summary(state)
    _print_fix_closure_summary(state)

    missing_root_fields = _missing_root_cause_fields(state)
    if missing_root_fields and state.resolution.root_cause:
        console.print("[bold]Missing Root Cause Fields[/bold]")
        for field in missing_root_fields:
            console.print(f"- {field}")

    missing_causal_fields = _missing_causal_gate_fields(state)
    if missing_causal_fields:
        console.print("[bold]Missing Causal Gate Fields[/bold]")
        for field in missing_causal_fields:
            console.print(f"- {field}")

    if state.current_focus.next_action:
        console.print("[bold]Next Action[/bold]")
        console.print(state.current_focus.next_action)

    console.print(f"[cyan]Session file:[/cyan] {session_path}")

@debug_app.callback(invoke_without_command=True)
def debug_command(
    ctx: typer.Context,
    description: Optional[str] = typer.Argument(None, help="Brief description of the bug to start a new investigation."),
    dispatch_plan: bool = typer.Option(False, "--dispatch", help="Render the suggested Codex child-agent dispatch plan instead of the standard debug checkpoint."),
    output_format: str = typer.Option("text", "--format", help="Output format for --dispatch: text, json, or spawn-json."),
):
    """
    Start a new debug investigation or resume the most recent one.
    """
    if ctx.invoked_subcommand is not None:
        return

    if dispatch_plan:
        asyncio.run(_run_debug_dispatch(description, output_format))
    else:
        asyncio.run(_run_debug(description))

async def _run_debug(description: Optional[str]):
    _project_map_preflight_for_debug()
    debug_dir = get_debug_dir()
    handler = MarkdownPersistenceHandler(debug_dir)
    
    state: Optional[DebugGraphState] = None
    resumed = False
    resume_reason = "missing"
    
    if description:
        state, parent_state = _create_or_link_debug_state(description, handler)
        if parent_state:
            console.print(
                f"[green]Starting linked follow-up debug session:[/green] {state.slug} "
                f"(parent: {parent_state.slug})"
            )
        else:
            console.print(f"[green]Starting new debug session:[/green] {state.slug}")
    else:
        state, resume_reason = handler.load_resume_target()
        if state:
            resumed = True
            if resume_reason == "parent_after_child":
                console.print(f"[cyan]Returning to parent debug session:[/cyan] {state.slug}")
            else:
                console.print(f"[cyan]Resuming debug session:[/cyan] {state.slug}")
        else:
            console.print("[red]Error:[/red] No description provided and no recent session found to resume.")
            console.print("Usage: specify debug \"description of the bug\"")
            raise typer.Exit(1)
            
    try:
        await run_debug_session(state, handler, resumed=resumed)
        if state.status == DebugStatus.RESOLVED and (Path.cwd() / ".specify").exists():
            session_path = handler.debug_dir / f"{state.slug}.md"
            auto_payload = capture_auto_learning(
                Path.cwd(),
                command_name="debug",
                session_file=session_path,
            )
            if auto_payload["status"] == "captured":
                console.print(
                    f"[cyan]Auto-captured {len(auto_payload['captured'])} debug learning candidate(s).[/cyan]"
                )
        if state.status == DebugStatus.AWAITING_HUMAN:
            session_path = handler.debug_dir / f"{state.slug}.md"
            report = state.resolution.report or "No session summary was generated."
            console.print("[yellow]Awaiting Human Review[/yellow]")
            console.print(report)
            console.print(f"[yellow]Session paused.[/yellow] Continue from: {session_path}")
            if state.waiting_on_child_human_followup and state.child_slugs:
                console.print("[yellow]Waiting on child follow-up before closing this parent session.[/yellow]")
                for child_slug in state.child_slugs:
                    console.print(f"- linked child: {child_slug}")
            if state.parent_slug:
                console.print(
                    f"[yellow]After confirming this follow-up issue, return to parent session:[/yellow] {state.parent_slug}"
                )
        elif state.status == DebugStatus.RESOLVED and state.parent_slug:
            parent_path = handler.debug_dir / f"{state.parent_slug}.md"
            if parent_path.exists():
                parent_state = handler.load(parent_path)
                parent_state.waiting_on_child_human_followup = False
                parent_state.resume_after_child = True
                handler.save(parent_state)
            console.print(
                f"[cyan]Follow-up issue resolved.[/cyan] Return to parent debug session: {state.parent_slug}"
            )
        elif state.status != DebugStatus.RESOLVED:
            _print_session_checkpoint(state, handler)
    except Exception as e:
        console.print(f"[red]Error during debug session:[/red] {e}")
        raise typer.Exit(1)


async def _load_or_create_debug_state(description: Optional[str]) -> tuple[DebugGraphState, MarkdownPersistenceHandler, bool]:
    debug_dir = get_debug_dir()
    handler = MarkdownPersistenceHandler(debug_dir)

    if description:
        state, _ = _create_or_link_debug_state(description, handler)
        return state, handler, False

    state, _ = handler.load_resume_target()
    if state:
        return state, handler, True

    console.print("[red]Error:[/red] No description provided and no recent session found to resume.")
    console.print("Usage: specify debug dispatch \"description of the bug\"")
    raise typer.Exit(1)


async def _run_debug_dispatch(description: Optional[str], output_format: str) -> None:
    _project_map_preflight_for_debug()
    state, handler, resumed = await _load_or_create_debug_state(description)
    await run_debug_session(state, handler, resumed=resumed)

    tasks = build_codex_dispatch_plan(state)
    spawn_tasks = build_codex_spawn_plan(state)
    if output_format.lower() == "json":
        payload = {
            "slug": state.slug,
            "diagnostic_profile": state.diagnostic_profile,
            "tasks": [task.model_dump(mode="json") for task in tasks],
        }
        print_json(payload, indent=2)
        return
    if output_format.lower() == "spawn-json":
        payload = {
            "slug": state.slug,
            "diagnostic_profile": state.diagnostic_profile,
            "spawn_tasks": [task.model_dump(mode="json") for task in spawn_tasks],
        }
        print_json(payload, indent=2)
        return

    console.print(format_dispatch_plan(tasks))
    if spawn_tasks:
        console.print(format_spawn_plan(spawn_tasks))

if __name__ == "__main__":
    debug_app()
