from pathlib import Path
import re
from typing import Any
from datetime import datetime
import yaml
from .schema import (
    DebugGraphState,
    DebugStatus,
)
from .dispatch import build_codex_dispatch_plan, build_codex_spawn_plan


def debug_research_path(debug_dir: Path, slug: str) -> Path:
    return debug_dir / f"{slug}.research.md"


def build_research_checkpoint(state: DebugGraphState) -> str:
    root_cause = state.resolution.root_cause.display_text() if state.resolution.root_cause else "Not confirmed"
    fix = state.resolution.fix or "No fix recorded"
    profile = state.diagnostic_profile or "Not classified"
    lines = [
        f"# Debug Research: {state.slug}",
        "",
        f"- Trigger: {state.trigger}",
        f"- Diagnostic profile: {profile}",
        f"- Failed verification attempts: {state.resolution.fail_count}",
        f"- Agent verification failures: {state.resolution.agent_fail_count}",
        f"- Human reopen count: {state.resolution.human_reopen_count}",
        f"- Human verification outcome: {state.resolution.human_verification_outcome.value}",
        f"- Current root-cause draft: {root_cause}",
        f"- Latest attempted fix: {fix}",
        "",
        "## Why The Current Loop Is Blocked",
        "",
        "Repeated verification failed without producing a stronger causal explanation.",
        "Do focused research before applying another fix so the next experiment changes the decision quality, not just the code shape.",
        "",
        "## Research Questions",
        "",
        "- Which truth-owning layer or contract is still not directly verified?",
        "- Which environment, dependency, API, or runtime assumption might still be wrong?",
        "- What evidence would falsify the current root-cause draft fastest?",
        "- What observation would prove the next fix restores the full closed loop instead of only the symptom layer?",
        "",
        "## Existing Evidence To Re-check",
        "",
    ]

    if state.evidence:
        for entry in state.evidence[-5:]:
            lines.append(f"- {entry.checked}: {entry.found} -> {entry.implication}")
    else:
        lines.append("- No decisive evidence recorded yet.")

    lines.extend(["", "## Sources To Verify", ""])
    if state.context.modified_files:
        for path in state.context.modified_files[:5]:
            lines.append(f"- {path}")
    elif state.recently_modified:
        for path in state.recently_modified[:5]:
            lines.append(f"- {path}")
    else:
        lines.append("- Add the highest-signal local files, contracts, or docs to inspect next.")

    lines.extend(
        [
            "",
            "## Exit Criteria",
            "",
            "- Replace the current draft with a stronger falsifiable hypothesis, or explicitly reject it.",
            "- Name the exact next experiment and the evidence that will count as pass/fail.",
            "- Do not resume another fix loop until the missing research answers are recorded here or in the debug session.",
        ]
    )
    return "\n".join(lines)


def build_handoff_report(state: DebugGraphState) -> str:
    root_cause = state.resolution.root_cause.display_text() if state.resolution.root_cause else "Not confirmed"
    lines = [
        "## Awaiting Human Review",
        "",
        f"- Trigger: {state.trigger}",
        f"- Diagnostic profile: {state.diagnostic_profile or 'Not classified'}",
        f"- Root cause: {root_cause}",
        f"- Attempted fix: {state.resolution.fix or 'No fix recorded'}",
        f"- Agent verification status: {state.resolution.verification or 'unknown'}",
        f"- Agent verification failures: {state.resolution.agent_fail_count}",
        f"- Human reopen count: {state.resolution.human_reopen_count}",
        f"- Human verification outcome: {state.resolution.human_verification_outcome.value}",
        "",
        "### Eliminated Hypotheses",
    ]

    if state.waiting_on_child_human_followup:
        lines.insert(8, "- Waiting on child human follow-up: true")

    if state.eliminated:
        for entry in state.eliminated:
            lines.append(f"- {entry.hypothesis}: {entry.evidence}")
    else:
        lines.append("- None recorded")

    lines.extend(["", "### Key Evidence"])
    if state.evidence:
        for entry in state.evidence:
            lines.append(
                f"- {entry.checked}: {entry.found} -> {entry.implication}"
            )
    else:
        lines.append("- None recorded")

    lines.extend(["", "### Truth Ownership"])
    if state.truth_ownership:
        for entry in state.truth_ownership:
            owner_line = f"- {entry.layer}: {entry.owns}"
            if entry.evidence:
                owner_line += f" ({entry.evidence})"
            lines.append(owner_line)
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Observer Framing"])
    if state.observer_framing.summary:
        lines.append(f"- Summary: {state.observer_framing.summary}")
    if state.observer_framing.primary_suspected_loop:
        lines.append(f"- Primary suspected loop: {state.observer_framing.primary_suspected_loop}")
    if state.observer_framing.suspected_owning_layer:
        lines.append(f"- Suspected owning layer: {state.observer_framing.suspected_owning_layer}")
    if state.observer_framing.suspected_truth_owner:
        lines.append(f"- Suspected truth owner: {state.observer_framing.suspected_truth_owner}")
    if state.observer_framing.recommended_first_probe:
        lines.append(f"- Recommended first probe: {state.observer_framing.recommended_first_probe}")
    if state.observer_framing.contrarian_candidate:
        lines.append(f"- Contrarian candidate: {state.observer_framing.contrarian_candidate}")
    if state.observer_framing.missing_questions:
        lines.append("- Missing questions:")
        for question in state.observer_framing.missing_questions:
            lines.append(f"  - {question}")
    if state.observer_framing.alternative_cause_candidates:
        lines.append("- Alternative cause candidates:")
        for candidate in state.observer_framing.alternative_cause_candidates:
            lines.append(f"  - {candidate.candidate}")
            if candidate.failure_shape:
                lines.append(f"    - failure shape: {candidate.failure_shape}")
            if candidate.why_it_fits:
                lines.append(f"    - why it fits: {candidate.why_it_fits}")
            if candidate.map_evidence:
                lines.append(f"    - map evidence: {candidate.map_evidence}")
            if candidate.would_rule_out:
                lines.append(f"    - would rule out: {candidate.would_rule_out}")
            if candidate.recommended_first_probe:
                lines.append(f"    - recommended first probe: {candidate.recommended_first_probe}")
    if not any(
        (
            state.observer_framing.summary,
            state.observer_framing.primary_suspected_loop,
            state.observer_framing.suspected_owning_layer,
            state.observer_framing.suspected_truth_owner,
            state.observer_framing.recommended_first_probe,
            state.observer_framing.missing_questions,
            state.observer_framing.alternative_cause_candidates,
        )
    ):
        lines.append("- Not recorded")

    lines.extend(["", "### Transition Memo"])
    if state.transition_memo.first_candidate_to_test:
        lines.append(f"- First candidate to test: {state.transition_memo.first_candidate_to_test}")
    if state.transition_memo.why_first:
        lines.append(f"- Why first: {state.transition_memo.why_first}")
    if state.transition_memo.evidence_unlock:
        lines.append(f"- Evidence unlock: {', '.join(state.transition_memo.evidence_unlock)}")
    if state.transition_memo.carry_forward_notes:
        lines.append("- Carry forward:")
        for note in state.transition_memo.carry_forward_notes:
            lines.append(f"  - {note}")
    if not any(
        (
            state.transition_memo.first_candidate_to_test,
            state.transition_memo.why_first,
            state.transition_memo.evidence_unlock,
            state.transition_memo.carry_forward_notes,
        )
    ):
        lines.append("- Not recorded")

    lines.extend(["", "### Decisive Signals"])
    if state.resolution.decisive_signals:
        for signal in state.resolution.decisive_signals:
            lines.append(f"- {signal}")
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Causal Coverage"])
    if state.resolution.alternative_hypotheses_considered:
        lines.append("- Alternative hypotheses considered:")
        for item in state.resolution.alternative_hypotheses_considered:
            lines.append(f"  - {item}")
    else:
        lines.append("- Alternative hypotheses considered: not recorded")
    if state.resolution.alternative_hypotheses_ruled_out:
        lines.append("- Alternatives ruled out:")
        for item in state.resolution.alternative_hypotheses_ruled_out:
            lines.append(f"  - {item}")
    else:
        lines.append("- Alternatives ruled out: not recorded")
    lines.append(f"- Root cause confidence: {state.resolution.root_cause_confidence or 'Not recorded'}")

    lines.extend(["", "### Candidate Resolutions"])
    if state.candidate_resolutions:
        for entry in state.candidate_resolutions:
            line = f"- {entry.candidate}: {entry.disposition}"
            if entry.notes:
                line += f" ({entry.notes})"
            lines.append(line)
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Suggested Evidence Lanes"])
    if state.suggested_evidence_lanes:
        for lane in state.suggested_evidence_lanes:
            lines.append(f"- {lane.name}: {lane.focus}")
            for item in lane.evidence_to_collect:
                lines.append(f"  - {item}")
            if lane.join_goal:
                lines.append(f"  - join goal: {lane.join_goal}")
    else:
        lines.append("- Not recorded")

    dispatch_plan = build_codex_dispatch_plan(state)
    lines.extend(["", "### Suggested Codex Dispatch"])
    if dispatch_plan:
        for task in dispatch_plan:
            lines.append(f"- {task.lane_name}: {task.task_summary}")
            lines.append(f"  - role: {task.agent_role}")
            lines.append(f"  - prompt: {task.prompt.strip()}")
    else:
        lines.append("- Not recorded")

    spawn_plan = build_codex_spawn_plan(state)
    lines.extend(["", "### Suggested Codex Spawn Payloads"])
    if spawn_plan:
        for task in spawn_plan:
            lines.append(f"- {task.lane_name}: {task.agent_type} ({task.reasoning_effort})")
            lines.append(f"  - message: {task.message.strip()}")
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Root Cause Structure"])
    if state.resolution.root_cause:
        if state.resolution.root_cause.owning_layer:
            lines.append(f"- Owning layer: {state.resolution.root_cause.owning_layer}")
        if state.resolution.root_cause.broken_control_state:
            lines.append(f"- Broken control state: {state.resolution.root_cause.broken_control_state}")
        if state.resolution.root_cause.failure_mechanism:
            lines.append(f"- Failure mechanism: {state.resolution.root_cause.failure_mechanism}")
        if state.resolution.root_cause.loop_break:
            lines.append(f"- Closed-loop break: {state.resolution.root_cause.loop_break}")
        if state.resolution.root_cause.decisive_signal:
            lines.append(f"- Primary decisive signal: {state.resolution.root_cause.decisive_signal}")
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Fix Closure"])
    lines.append(f"- Fix scope: {state.resolution.fix_scope or 'Not recorded'}")
    if state.resolution.loop_restoration_proof:
        lines.append("- Loop restoration proof:")
        for item in state.resolution.loop_restoration_proof:
            lines.append(f"  - {item}")
    else:
        lines.append("- Loop restoration proof: not recorded")

    lines.extend(
        [
            "",
            "### Next Step",
        ]
    )
    if state.parent_slug:
        lines.append(
            f"After resolving this derived issue, return to the parent session `{state.parent_slug}` and finish the original human verification."
        )
    elif state.resolution.fail_count >= 2:
        lines.append(
            f"Repeated verification failed. Review the focused research checkpoint at `.planning/debug/{state.slug}.research.md` before attempting another fix loop."
        )
    elif state.resume_after_child and state.child_slugs:
        lines.append(
            "A linked follow-up issue is in progress or recently completed. Resolve the child session and then return here to close the original human verification."
        )
        for child_slug in state.child_slugs:
            lines.append(f"- linked child: `{child_slug}`")
    else:
        lines.append("Continue the investigation manually from the persisted session file.")
    return "\n".join(lines)

class MarkdownPersistenceHandler:
    def __init__(self, debug_dir: Path):
        self.debug_dir = debug_dir
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, slug: str) -> Path:
        if not slug or Path(slug).name != slug or any(sep in slug for sep in ("/", "\\")):
            raise ValueError("Invalid debug session slug")

        file_path = (self.debug_dir / f"{slug}.md").resolve()
        debug_root = self.debug_dir.resolve()
        if file_path.parent != debug_root:
            raise ValueError("Debug session path escapes debug directory")

        return file_path

    def save(self, state: DebugGraphState):
        file_path = self._session_path(state.slug)
        
        # Frontmatter
        frontmatter = {
            "slug": state.slug,
            "status": state.status.value,
            "trigger": state.trigger,
            "parent_slug": state.parent_slug,
            "child_slugs": state.child_slugs,
            "resume_after_child": state.resume_after_child,
            "waiting_on_child_human_followup": state.waiting_on_child_human_followup,
            "diagnostic_profile": state.diagnostic_profile,
            "observer_mode": state.observer_mode,
            "observer_framing_completed": state.observer_framing_completed,
            "framing_gate_passed": state.framing_gate_passed,
            "skip_observer_reason": state.skip_observer_reason,
            "current_node_id": state.current_node_id,
            "created": state.created.isoformat(),
            "updated": datetime.now().isoformat()
        }
        
        content = "---\n"
        content += yaml.safe_dump(frontmatter, sort_keys=False)
        content += "---\n\n"

        sections = [
            ("Current Focus", state.current_focus.model_dump(mode="json")),
            ("Symptoms", state.symptoms.model_dump(mode="json")),
            ("Observer Framing", state.observer_framing.model_dump(mode="json")),
            ("Transition Memo", state.transition_memo.model_dump(mode="json")),
            ("Suggested Evidence Lanes", [lane.model_dump(mode="json") for lane in state.suggested_evidence_lanes]),
            ("Candidate Resolutions", [entry.model_dump(mode="json") for entry in state.candidate_resolutions]),
            ("Truth Ownership", [entry.model_dump(mode="json") for entry in state.truth_ownership]),
            ("Control State", state.control_state),
            ("Observation State", state.observation_state),
            ("Closed Loop", state.closed_loop.model_dump(mode="json")),
            ("Execution Intent", state.execution_intent.model_dump(mode="json")),
            ("Context", state.context.model_dump(mode="json")),
            ("Recently Modified", state.recently_modified),
            ("Eliminated", [entry.model_dump(mode="json") for entry in state.eliminated]),
            ("Evidence", [entry.model_dump(mode="json") for entry in state.evidence]),
            ("Resolution", state.resolution.model_dump(mode="json")),
        ]

        for title, payload in sections:
            content += f"## {title}\n"
            content += yaml.safe_dump(payload, sort_keys=False).rstrip()
            content += "\n\n"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def build_handoff_report(self, state: DebugGraphState) -> str:
        return build_handoff_report(state)

    def research_path(self, slug: str) -> Path:
        return debug_research_path(self.debug_dir, slug)

    def save_research_checkpoint(self, state: DebugGraphState) -> Path:
        path = self.research_path(state.slug)
        path.write_text(build_research_checkpoint(state), encoding="utf-8")
        return path

    def load(self, path: Path) -> DebugGraphState:
        if not path.exists():
            raise FileNotFoundError(f"Debug session file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse YAML frontmatter without being confused by `---` inside values.
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("Invalid debug session file format: Missing YAML frontmatter")

        try:
            frontmatter_end = lines[1:].index("---") + 1
        except ValueError as exc:
            raise ValueError("Invalid debug session file format: Unterminated YAML frontmatter") from exc

        frontmatter = yaml.safe_load("\n".join(lines[1:frontmatter_end]))
        body = "\n".join(lines[frontmatter_end + 1 :])
        
        # Extract sections using markdown headings and decode each as YAML.
        sections: dict[str, Any] = {}
        
        current_section = None
        current_content = []
        
        for line in body.splitlines():
            match = re.match(r"^##\s+(.*)", line)
            if match:
                if current_section:
                    section_text = "\n".join(current_content).strip()
                    sections[current_section] = yaml.safe_load(section_text) if section_text else None
                current_section = match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            section_text = "\n".join(current_content).strip()
            sections[current_section] = yaml.safe_load(section_text) if section_text else None

        return DebugGraphState.model_validate(
            {
                "slug": frontmatter["slug"],
                "status": frontmatter["status"],
                "trigger": frontmatter["trigger"],
                "parent_slug": frontmatter.get("parent_slug"),
                "child_slugs": frontmatter.get("child_slugs", []),
                "resume_after_child": frontmatter.get("resume_after_child", False),
                "waiting_on_child_human_followup": frontmatter.get("waiting_on_child_human_followup", False),
                "diagnostic_profile": frontmatter.get("diagnostic_profile"),
                "observer_mode": frontmatter.get("observer_mode"),
                "observer_framing_completed": frontmatter.get("observer_framing_completed", False),
                "framing_gate_passed": frontmatter.get("framing_gate_passed", False),
                "skip_observer_reason": frontmatter.get("skip_observer_reason"),
                "current_node_id": frontmatter.get("current_node_id"),
                "created": frontmatter["created"],
                "updated": frontmatter["updated"],
                "current_focus": sections.get("Current Focus") or {},
                "symptoms": sections.get("Symptoms") or {},
                "observer_framing": sections.get("Observer Framing") or {},
                "transition_memo": sections.get("Transition Memo") or {},
                "suggested_evidence_lanes": sections.get("Suggested Evidence Lanes") or [],
                "candidate_resolutions": sections.get("Candidate Resolutions") or [],
                "truth_ownership": sections.get("Truth Ownership") or [],
                "control_state": sections.get("Control State") or [],
                "observation_state": sections.get("Observation State") or [],
                "closed_loop": sections.get("Closed Loop") or {},
                "execution_intent": sections.get("Execution Intent") or {},
                "context": sections.get("Context") or {},
                "recently_modified": sections.get("Recently Modified") or [],
                "eliminated": sections.get("Eliminated") or [],
                "evidence": sections.get("Evidence") or [],
                "resolution": sections.get("Resolution") or {},
            }
        )

    def load_all_sessions(self) -> list[DebugGraphState]:
        if not self.debug_dir.exists():
            return []

        sessions = list(self.debug_dir.glob("*.md"))
        sessions.sort(key=lambda path: path.stat().st_mtime, reverse=True)

        loaded: list[DebugGraphState] = []
        for session_path in sessions:
            try:
                loaded.append(self.load(session_path))
            except Exception:
                continue
        return loaded

    def load_most_recent_awaiting_human_session(self) -> DebugGraphState | None:
        for state in self.load_all_sessions():
            if state.status == DebugStatus.AWAITING_HUMAN and not state.waiting_on_child_human_followup:
                return state
        return None

    def _parent_resume_ready(
        self,
        state: DebugGraphState,
        states_by_slug: dict[str, DebugGraphState],
    ) -> bool:
        if state.status != DebugStatus.AWAITING_HUMAN:
            return False
        if not state.resume_after_child or not state.child_slugs:
            return False

        child_states = [states_by_slug.get(slug) for slug in state.child_slugs]
        if not child_states or any(child is None for child in child_states):
            return False
        return all(child.status == DebugStatus.RESOLVED for child in child_states if child is not None)

    def load_resume_target(self) -> tuple[DebugGraphState | None, str]:
        sessions = self.load_all_sessions()
        if not sessions:
            return None, "missing"

        states_by_slug = {state.slug: state for state in sessions}
        for state in sessions:
            if self._parent_resume_ready(state, states_by_slug):
                return state, "parent_after_child"

        return sessions[0], "most_recent"

    def load_most_recent_session(self) -> DebugGraphState | None:
        """
        Finds and loads the most recently updated debug session from the debug directory.
        """
        state, _ = self.load_resume_target()
        return state
