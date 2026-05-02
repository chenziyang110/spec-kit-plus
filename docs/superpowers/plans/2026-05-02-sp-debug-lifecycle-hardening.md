# sp-debug Lifecycle Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-debug` into a complete lifecycle with hard framing gates, split agent vs human verification, and explicit human re-entry routing for same-issue, derived-issue, and unrelated-issue feedback.

**Architecture:** Implement this in four slices. First, extend the debug session schema and persistence contract so new lifecycle semantics can be stored and resumed safely. Second, rewire the state machine so automated verification hands off into formal human verification instead of resolving immediately, and enforce the new framing gate before investigation begins. Third, update CLI output, templates, and injected integration guidance so runtime behavior, generated skills, and persisted reports say the same thing. Fourth, lock the behavior with focused pytest coverage for graph transitions, persistence round-trips, CLI resume logic, and template guidance.

**Tech Stack:** Python 3.11+, Pydantic, Pydantic-Graph, Typer, pytest, Markdown/YAML templates

---

## File Structure

### Runtime state and persistence

- `src/specify_cli/debug/schema.py`
  Owns debug lifecycle enums, framing candidate structures, verification counters, and the persisted `DebugGraphState` contract.
- `src/specify_cli/debug/persistence.py`
  Owns session markdown serialization, handoff reports, research checkpoints, and resume-target selection.

### Lifecycle and CLI behavior

- `src/specify_cli/debug/graph.py`
  Owns node transitions, framing/readiness gates, verification routing, and failure-loop escalation.
- `src/specify_cli/debug/cli.py`
  Owns user-facing status output, follow-up session creation, resume behavior, and human-verification messaging.

### Prompt and generated workflow surfaces

- `templates/commands/debug.md`
  Owns the product contract for `sp-debug` in generated workflows.
- `templates/debug.md`
  Owns the persisted session template and field documentation.
- `templates/worker-prompts/debug-thinker.md`
  Owns think-subagent framing requirements and output shape.
- `src/specify_cli/integrations/base.py`
  Owns injected runtime guidance added to generated `sp-debug` skills for multiple integrations.

### Verification

- `tests/test_debug_graph.py`
- `tests/test_debug_graph_nodes.py`
- `tests/test_debug_persistence.py`
- `tests/test_debug_cli.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_extension_skills.py`
- `tests/integrations/test_integration_codex.py`

These tests already cover the existing lifecycle. Update them in place rather than creating a second parallel suite.

---

### Task 1: Extend the debug schema for lifecycle hardening

**Files:**
- Modify: `src/specify_cli/debug/schema.py:7-186`
- Test: `tests/test_debug_persistence.py`

- [ ] **Step 1: Write the failing persistence test for new lifecycle fields**

Add a new test near the existing persistence round-trip coverage in `tests/test_debug_persistence.py`:

```python
def test_persistence_round_trips_lifecycle_hardening_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="human verify loop")
    state.status = DebugStatus.AWAITING_HUMAN
    state.waiting_on_child_human_followup = True
    state.framing_gate_passed = True
    state.human_verification_outcome = "derived_issue"
    state.agent_fail_count = 2
    state.human_reopen_count = 1
    state.observer_framing.contrarian_candidate = "Projection layer drops correct source state"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(
            candidate="Scheduler ownership state never released correctly",
            failure_shape="truth_owner_logic",
            recommended_first_probe="Inspect scheduler ownership sets before and after slot release",
        )
    ]
    state.candidate_resolutions = [
        CandidateResolution(
            candidate="Scheduler ownership state never released correctly",
            disposition="confirmed",
        )
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.waiting_on_child_human_followup is True
    assert restored.framing_gate_passed is True
    assert restored.human_verification_outcome == "derived_issue"
    assert restored.agent_fail_count == 2
    assert restored.human_reopen_count == 1
    assert restored.observer_framing.contrarian_candidate == "Projection layer drops correct source state"
    assert restored.observer_framing.alternative_cause_candidates[0].failure_shape == "truth_owner_logic"
    assert restored.observer_framing.alternative_cause_candidates[0].recommended_first_probe.startswith("Inspect scheduler ownership sets")
    assert restored.candidate_resolutions[0].disposition == "confirmed"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_debug_persistence.py::test_persistence_round_trips_lifecycle_hardening_fields -q
```

Expected: FAIL because `DebugGraphState`, `ObserverCauseCandidate`, and persistence parsing do not yet support the new fields.

- [ ] **Step 3: Add the new schema types and fields**

Update `src/specify_cli/debug/schema.py` with these exact structural changes:

```python
class CandidateDisposition(str, Enum):
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
    STILL_OPEN_BUT_DEPRIORITIZED = "still_open_but_deprioritized"


class HumanVerificationOutcome(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    SAME_ISSUE = "same_issue"
    DERIVED_ISSUE = "derived_issue"
    UNRELATED_ISSUE = "unrelated_issue"
    INSUFFICIENT_FEEDBACK = "insufficient_feedback"


class ObserverCauseCandidate(BaseModel):
    candidate: str
    failure_shape: Optional[str] = None
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    would_rule_out: Optional[str] = None
    recommended_first_probe: Optional[str] = None


class CandidateResolution(BaseModel):
    candidate: str
    disposition: CandidateDisposition
    notes: Optional[str] = None


class ObserverFramingState(BaseModel):
    summary: Optional[str] = None
    primary_suspected_loop: Optional[str] = None
    suspected_owning_layer: Optional[str] = None
    suspected_truth_owner: Optional[str] = None
    recommended_first_probe: Optional[str] = None
    contrarian_candidate: Optional[str] = None
    missing_questions: List[str] = Field(default_factory=list)
    alternative_cause_candidates: List[ObserverCauseCandidate] = Field(default_factory=list)
```
```python
class Resolution(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    root_cause: Optional[RootCause] = None
    alternative_hypotheses_considered: List[str] = Field(default_factory=list)
    alternative_hypotheses_ruled_out: List[str] = Field(default_factory=list)
    root_cause_confidence: Optional[str] = None
    fix: Optional[str] = None
    fix_scope: Optional[str] = None
    verification: Optional[str] = None
    validation_results: List[ValidationCheck] = Field(default_factory=list)
    files_changed: List[str] = Field(default_factory=list)
    fail_count: int = 0
    agent_fail_count: int = 0
    human_reopen_count: int = 0
    human_verification_outcome: HumanVerificationOutcome = HumanVerificationOutcome.PENDING
    report: Optional[str] = None
    decisive_signals: List[str] = Field(default_factory=list)
    rejected_surface_fixes: List[str] = Field(default_factory=list)
    loop_restoration_proof: List[str] = Field(default_factory=list)
```
```python
class DebugGraphState(BaseModel):
    slug: str
    status: DebugStatus = DebugStatus.GATHERING
    trigger: str
    parent_slug: Optional[str] = None
    child_slugs: List[str] = Field(default_factory=list)
    resume_after_child: bool = False
    waiting_on_child_human_followup: bool = False
    diagnostic_profile: Optional[str] = None
    observer_mode: Optional[str] = None
    observer_framing_completed: bool = False
    framing_gate_passed: bool = False
    skip_observer_reason: Optional[str] = None
    current_node_id: Optional[str] = None
    ...
    candidate_resolutions: List[CandidateResolution] = Field(default_factory=list)
```

Do not delete `fail_count` yet. Keep it temporarily for backward compatibility while later tasks migrate graph and persistence reads to the split counters.

- [ ] **Step 4: Run the targeted persistence test**

Run:

```bash
python -m pytest tests/test_debug_persistence.py::test_persistence_round_trips_lifecycle_hardening_fields -q
```

Expected: PASS

- [ ] **Step 5: Run the current debug persistence suite**

Run:

```bash
python -m pytest tests/test_debug_persistence.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/schema.py tests/test_debug_persistence.py
git commit -m "feat: extend debug schema for lifecycle hardening"
```

---

### Task 2: Persist and report the new lifecycle fields

**Files:**
- Modify: `src/specify_cli/debug/persistence.py:12-486`
- Test: `tests/test_debug_persistence.py`

- [ ] **Step 1: Write failing handoff-report coverage**

Add this test near the existing handoff report tests in `tests/test_debug_persistence.py`:

```python
def test_handoff_report_includes_split_verification_and_human_outcome(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="human verify loop")
    state.status = DebugStatus.AWAITING_HUMAN
    state.resolution.verification = "success"
    state.resolution.agent_fail_count = 1
    state.resolution.human_reopen_count = 2
    state.resolution.human_verification_outcome = "same_issue"
    state.waiting_on_child_human_followup = True

    report = handler.build_handoff_report(state)

    assert "Agent verification status: success" in report
    assert "Agent verification failures: 1" in report
    assert "Human verification outcome: same_issue" in report
    assert "Human reopen count: 2" in report
    assert "waiting on child human follow-up" in report.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_debug_persistence.py::test_handoff_report_includes_split_verification_and_human_outcome -q
```

Expected: FAIL because the current report only prints `Verification status` and `Failed verification attempts`.

- [ ] **Step 3: Update persistence save/load and report generation**

Apply these concrete changes in `src/specify_cli/debug/persistence.py`:

- In `build_research_checkpoint()`, replace the single failed-attempt line:

```python
f"- Failed verification attempts: {state.resolution.fail_count}",
```

with:

```python
f"- Agent verification failures: {state.resolution.agent_fail_count}",
f"- Human reopen count: {state.resolution.human_reopen_count}",
f"- Human verification outcome: {state.resolution.human_verification_outcome}",
```

- In `build_handoff_report()`, replace:

```python
f"- Verification status: {state.resolution.verification or 'unknown'}",
f"- Failed verification attempts: {state.resolution.fail_count}",
```

with:

```python
f"- Agent verification status: {state.resolution.verification or 'unknown'}",
f"- Agent verification failures: {state.resolution.agent_fail_count}",
f"- Human reopen count: {state.resolution.human_reopen_count}",
f"- Human verification outcome: {state.resolution.human_verification_outcome}",
```

- Add explicit handoff text when waiting on child verification:

```python
if state.waiting_on_child_human_followup:
    lines.append("- Waiting on child human follow-up: true")
```

- In `save()`, persist:

```python
"waiting_on_child_human_followup": state.waiting_on_child_human_followup,
"framing_gate_passed": state.framing_gate_passed,
```

- In `sections`, persist the new `Candidate Resolutions` block:

```python
("Candidate Resolutions", [entry.model_dump(mode="json") for entry in state.candidate_resolutions]),
```

- In `load()`, restore:

```python
"waiting_on_child_human_followup": frontmatter.get("waiting_on_child_human_followup", False),
"framing_gate_passed": frontmatter.get("framing_gate_passed", False),
"candidate_resolutions": sections.get("Candidate Resolutions") or [],
```

- In `load_most_recent_awaiting_human_session()`, keep the same status filter but prefer sessions not blocked by unresolved children:

```python
if state.status == DebugStatus.AWAITING_HUMAN and not state.waiting_on_child_human_followup:
    return state
```

Keep the existing `_parent_resume_ready()` logic, because later CLI tasks will still need parent-return routing after child resolution.

- [ ] **Step 4: Run the two focused persistence tests**

Run:

```bash
python -m pytest tests/test_debug_persistence.py::test_persistence_round_trips_lifecycle_hardening_fields tests/test_debug_persistence.py::test_handoff_report_includes_split_verification_and_human_outcome -q
```

Expected: PASS

- [ ] **Step 5: Run the full persistence suite**

Run:

```bash
python -m pytest tests/test_debug_persistence.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/persistence.py tests/test_debug_persistence.py
git commit -m "feat: persist split verification lifecycle for debug sessions"
```

---

### Task 3: Enforce the framing hard gate in the graph

**Files:**
- Modify: `src/specify_cli/debug/graph.py:1-903`
- Modify: `templates/worker-prompts/debug-thinker.md`
- Test: `tests/test_debug_graph.py`
- Test: `tests/test_debug_think_agent.py`

- [ ] **Step 1: Write the failing framing-gate tests**

Add these tests to `tests/test_debug_graph.py`:

```python
@pytest.mark.asyncio
async def test_gathering_blocks_when_full_framing_has_fewer_than_three_candidates():
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.observer_framing_completed = True
    state.observer_mode = "full"
    state.observer_framing.summary = "Scheduler boundary issue"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "scheduler"
    state.observer_framing.suspected_truth_owner = "scheduler"
    state.observer_framing.recommended_first_probe = "Compare queue and ownership sets"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(candidate="A", failure_shape="truth_owner_logic"),
        ObserverCauseCandidate(candidate="B", failure_shape="truth_owner_logic"),
    ]
    state.transition_memo.first_candidate_to_test = "A"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "at least 3" in (state.current_focus.next_action or "")
```
```python
@pytest.mark.asyncio
async def test_gathering_blocks_when_candidate_diversity_is_fake():
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.observer_framing_completed = True
    state.observer_mode = "full"
    state.observer_framing.summary = "Scheduler boundary issue"
    state.observer_framing.primary_suspected_loop = "scheduler-admission"
    state.observer_framing.suspected_owning_layer = "scheduler"
    state.observer_framing.suspected_truth_owner = "scheduler"
    state.observer_framing.recommended_first_probe = "Compare queue and ownership sets"
    state.observer_framing.contrarian_candidate = "Same family paraphrase"
    state.observer_framing.alternative_cause_candidates = [
        ObserverCauseCandidate(candidate="A", failure_shape="truth_owner_logic"),
        ObserverCauseCandidate(candidate="B", failure_shape="truth_owner_logic"),
        ObserverCauseCandidate(candidate="C", failure_shape="truth_owner_logic"),
    ]
    state.transition_memo.first_candidate_to_test = "A"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "diversity" in (state.current_focus.next_action or "").lower()
```

Add this test to `tests/test_debug_think_agent.py`:

```python
def test_prompt_requires_failure_shape_and_contrarian_candidate() -> None:
    state = DebugGraphState(
        slug="test-session",
        trigger="queue stuck after slot release",
        diagnostic_profile="scheduler-admission",
    )

    prompt = build_think_subagent_prompt(state)

    assert "failure_shape" in prompt
    assert "recommended_first_probe" in prompt
    assert "contrarian_candidate" in prompt
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_debug_graph.py::test_gathering_blocks_when_full_framing_has_fewer_than_three_candidates tests/test_debug_graph.py::test_gathering_blocks_when_candidate_diversity_is_fake tests/test_debug_think_agent.py::test_prompt_requires_failure_shape_and_contrarian_candidate -q
```

Expected: FAIL because the current graph only checks `observer_framing_completed` and the current prompt does not require these fields.

- [ ] **Step 3: Strengthen the thinker prompt and graph gate**

Make these exact changes:

- In `templates/worker-prompts/debug-thinker.md`, change the candidate instructions from:

```markdown
4. Generate at least 3 **alternative cause candidates**. For each:
   - `candidate`
   - `why_it_fits`
   - `map_evidence`
   - `would_rule_out`
```

to:

```markdown
4. Generate at least 3 **alternative cause candidates** for full framing, or at least 2 for compressed framing.
5. The candidates must not be paraphrases of one another. Cover at least 2 different failure families or truth-owner families.
6. For each candidate include:
   - `candidate`
   - `failure_shape`
   - `why_it_fits`
   - `map_evidence`
   - `would_rule_out`
   - `recommended_first_probe`
7. Provide one `contrarian_candidate` that is meaningfully different from the primary candidate.
```

- Update the YAML example to include:

```yaml
contrarian_candidate: "projection layer drops correct source state"
alternative_cause_candidates:
  - candidate: "..."
    failure_shape: "truth_owner_logic"
    why_it_fits: "..."
    map_evidence: "..."
    would_rule_out: "..."
    recommended_first_probe: "..."
```

- In `src/specify_cli/debug/graph.py`, add helper functions directly above `GatheringNode`:

```python
def _framing_gate_count_requirement(state: DebugGraphState) -> int:
    return 2 if state.observer_mode == "compressed" else 3


def _framing_gate_diversity_gaps(state: DebugGraphState) -> list[str]:
    shapes = {candidate.failure_shape for candidate in state.observer_framing.alternative_cause_candidates if candidate.failure_shape}
    if len(shapes) >= 2:
        return []
    return ["candidate diversity across at least 2 failure shapes or truth-owner families"]


def _framing_gate_gaps(state: DebugGraphState) -> list[str]:
    candidates = state.observer_framing.alternative_cause_candidates
    gaps: list[str] = []
    required_count = _framing_gate_count_requirement(state)
    if len(candidates) < required_count:
        gaps.append(f"at least {required_count} alternative cause candidates")
    if not state.observer_framing.contrarian_candidate:
        gaps.append("contrarian candidate")
    for index, candidate in enumerate(candidates, start=1):
        if not candidate.failure_shape:
            gaps.append(f"candidate {index} failure_shape")
        if not candidate.would_rule_out:
            gaps.append(f"candidate {index} would_rule_out")
        if not candidate.recommended_first_probe:
            gaps.append(f"candidate {index} recommended_first_probe")
    gaps.extend(_framing_gate_diversity_gaps(state))
    return gaps
```

- In `GatheringNode.run()`, after the `observer_framing_completed` branch and before symptom gate checks, add:

```python
framing_gaps = _framing_gate_gaps(ctx.state)
if framing_gaps:
    ctx.state.framing_gate_passed = False
    return _await_input(
        ctx.state,
        _format_checklist(
            "Observer framing is complete in form but not yet sufficient to enter investigation.",
            framing_gaps,
            intro="Fill in the missing framing items below before reproduction or code reads:",
        ),
    )
ctx.state.framing_gate_passed = True
```

- [ ] **Step 4: Run the focused tests**

Run:

```bash
python -m pytest tests/test_debug_graph.py::test_gathering_blocks_when_full_framing_has_fewer_than_three_candidates tests/test_debug_graph.py::test_gathering_blocks_when_candidate_diversity_is_fake tests/test_debug_think_agent.py::test_prompt_requires_failure_shape_and_contrarian_candidate -q
```

Expected: PASS

- [ ] **Step 5: Run the existing graph and thinker suites**

Run:

```bash
python -m pytest tests/test_debug_graph.py tests/test_debug_think_agent.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/graph.py templates/worker-prompts/debug-thinker.md tests/test_debug_graph.py tests/test_debug_think_agent.py
git commit -m "feat: enforce hard framing gate for sp-debug"
```

---

### Task 4: Split agent verification from human verification in the graph

**Files:**
- Modify: `src/specify_cli/debug/graph.py:466-920`
- Test: `tests/test_debug_graph.py`
- Test: `tests/test_debug_graph_nodes.py`

- [ ] **Step 1: Write the failing verification-split tests**

Add these tests:

```python
@pytest.mark.asyncio
async def test_verifying_success_routes_to_awaiting_human_not_resolved(monkeypatch):
    import specify_cli.debug.graph as graph_module

    monkeypatch.setattr(
        graph_module,
        "run_verification_commands",
        lambda commands, **_: [
            graph_module.ValidationResult(command=command, status="passed", output="PASS")
            for command in commands
        ],
    )

    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = ["Repro proves the scheduler releases ownership and promotes the next task."]

    result = await VerifyingNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, AwaitingHumanNode)
    assert state.status == DebugStatus.VERIFYING
    assert state.resolution.verification == "success"
```
```python
@pytest.mark.asyncio
async def test_awaiting_human_node_resolves_when_user_already_confirmed():
    state = DebugGraphState(trigger="test bug", slug="test-slug")
    state.status = DebugStatus.AWAITING_HUMAN
    state.resolution.human_verification_outcome = "passed"

    result = await AwaitingHumanNode().run(GraphRunContext(state=state, deps=None))

    assert isinstance(result, ResolvedNode)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_debug_graph.py::test_verifying_success_routes_to_awaiting_human_not_resolved tests/test_debug_graph_nodes.py::test_awaiting_human_node_resolves_when_user_already_confirmed -q
```

Expected: FAIL because the current `VerifyingNode` returns `ResolvedNode()` and `AwaitingHumanNode` always ends with `"Awaiting Human Review"`.

- [ ] **Step 3: Rewire the verification lifecycle**

In `src/specify_cli/debug/graph.py`:

- In `_post_verification_readiness_gaps()`, keep the existing `loop_restoration_proof` requirement.
- In `VerifyingNode.run()`, replace the success tail:

```python
ctx.state.resolution.verification = "success"
return ResolvedNode()
```

with:

```python
ctx.state.resolution.verification = "success"
ctx.state.resolution.human_verification_outcome = "pending"
return AwaitingHumanNode()
```

- In `_handle_failed_verification()`, stop incrementing the legacy field first. Use:

```python
state.resolution.agent_fail_count += 1
state.resolution.fail_count = state.resolution.agent_fail_count
```

- In `AwaitingHumanNode.run()`, prepend the formal human-verification status:

```python
ctx.state.status = DebugStatus.AWAITING_HUMAN
ctx.state.current_node_id = "AwaitingHumanNode"
```

and add this early-return branch before building the report:

```python
if state.resolution.human_verification_outcome == "passed":
    return ResolvedNode()
```

Keep the existing “review the session summary and continue manually” fallback for pending feedback.

- In `run_debug_session()`, keep the persisted-`VerifyingNode` resume guard but ensure it lands in the human-verification node with pending outcome:

```python
state.resolution.human_verification_outcome = "pending"
```

- [ ] **Step 4: Run the focused verification tests**

Run:

```bash
python -m pytest tests/test_debug_graph.py::test_verifying_success_routes_to_awaiting_human_not_resolved tests/test_debug_graph_nodes.py::test_awaiting_human_node_resolves_when_user_already_confirmed -q
```

Expected: PASS

- [ ] **Step 5: Run the full graph suites**

Run:

```bash
python -m pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -q
```

Expected: PASS after updating any existing assertions that still expect `ResolvedNode` directly from `VerifyingNode`.

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: split agent and human verification in sp-debug"
```

---

### Task 5: Add human re-entry classification and resume behavior

**Files:**
- Modify: `src/specify_cli/debug/cli.py:1-389`
- Modify: `src/specify_cli/debug/persistence.py:440-486`
- Test: `tests/test_debug_cli.py`

- [ ] **Step 1: Write the failing CLI classification tests**

Add these tests to `tests/test_debug_cli.py`:

```python
def test_debug_same_issue_feedback_reopens_parent_session(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    handler = MarkdownPersistenceHandler(clean_debug_dir)
    state = DebugGraphState(slug="parent-session", trigger="original issue")
    state.status = DebugStatus.AWAITING_HUMAN
    state.current_node_id = "AwaitingHumanNode"
    state.resolution.human_verification_outcome = "same_issue"
    handler.save(state)

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.INVESTIGATING
        handler.save(state)

    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug"])

    assert result.exit_code == 0
    assert "resuming debug session: parent-session" in result.stdout.lower()
```
```python
def test_debug_awaiting_human_report_mentions_child_wait_state(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.AWAITING_HUMAN
        state.waiting_on_child_human_followup = True
        state.child_slugs = ["child-session"]
        state.resolution.human_verification_outcome = "derived_issue"
        state.resolution.report = "## Awaiting Human Review\n\n- Waiting on child follow-up"
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "parent-session")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "awaiting human review" in result.stdout.lower()
    assert "child-session" in result.stdout.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_debug_cli.py::test_debug_same_issue_feedback_reopens_parent_session tests/test_debug_cli.py::test_debug_awaiting_human_report_mentions_child_wait_state -q
```

Expected: FAIL because the CLI has no notion of same-issue reopen routing or child-wait messaging beyond the older linked-follow-up flow.

- [ ] **Step 3: Update CLI routing and messages**

Apply these targeted changes in `src/specify_cli/debug/cli.py`:

- In `_link_follow_up_session()`, set:

```python
parent_state.waiting_on_child_human_followup = True
parent_state.resolution.human_verification_outcome = "derived_issue"
```

- In `_create_or_link_debug_state()`, keep the current parent-link behavior for explicitly new issue descriptions while the session is awaiting human verification.

- In `_print_session_checkpoint()`, after the current-stage line add:

```python
if state.status == DebugStatus.AWAITING_HUMAN:
    console.print(f"[cyan]Human verification outcome:[/cyan] {state.resolution.human_verification_outcome}")
```

- In `_run_debug()`, expand the `if state.status == DebugStatus.AWAITING_HUMAN:` block:

```python
if state.waiting_on_child_human_followup and state.child_slugs:
    console.print("[yellow]Waiting on child follow-up before closing this parent session.[/yellow]")
    for child_slug in state.child_slugs:
        console.print(f"- linked child: {child_slug}")
```

- In the `elif state.status == DebugStatus.RESOLVED and state.parent_slug:` branch, clear the parent wait state before printing the return hint by loading and updating the parent session:

```python
parent_path = handler.debug_dir / f"{state.parent_slug}.md"
if parent_path.exists():
    parent_state = handler.load(parent_path)
    parent_state.waiting_on_child_human_followup = False
    parent_state.resume_after_child = True
    handler.save(parent_state)
```

- In `src/specify_cli/debug/persistence.py`, keep `load_resume_target()` preferring `_parent_resume_ready()`, because that will now be the main parent-return path after child resolution.

- [ ] **Step 4: Run the focused CLI tests**

Run:

```bash
python -m pytest tests/test_debug_cli.py::test_debug_same_issue_feedback_reopens_parent_session tests/test_debug_cli.py::test_debug_awaiting_human_report_mentions_child_wait_state -q
```

Expected: PASS

- [ ] **Step 5: Run the existing debug CLI suite**

Run:

```bash
python -m pytest tests/test_debug_cli.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/cli.py src/specify_cli/debug/persistence.py tests/test_debug_cli.py
git commit -m "feat: add human re-entry routing for sp-debug"
```

---

### Task 6: Update workflow templates and injected integration guidance

**Files:**
- Modify: `templates/commands/debug.md`
- Modify: `templates/debug.md`
- Modify: `templates/worker-prompts/debug-thinker.md`
- Modify: `src/specify_cli/integrations/base.py:1833-1916`
- Test: `tests/test_debug_template_guidance.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Write the failing template-guidance tests**

Add these assertions:

In `tests/test_debug_template_guidance.py`:

```python
assert "full framing: at least 3 candidates" in content
assert "compressed framing: at least 2 candidates" in content
assert "contrarian candidate" in content
assert "same_issue" in content
assert "derived_issue" in content
assert "unrelated_issue" in content
assert "automatic verification through a formal human verification stage" in content or "human verification is a first-class stage" in content
```

In `tests/test_extension_skills.py`, add to the `sp-debug` body assertions:

```python
assert "same_issue" in debug_lower
assert "derived_issue" in debug_lower
assert "unrelated_issue" in debug_lower
assert "contrarian candidate" in debug_lower
assert "at least 3 alternative cause candidates" in debug_lower
assert "at least 2 for compressed framing" in debug_lower
```

In `tests/integrations/test_integration_codex.py`, add:

```python
assert "same_issue" in content
assert "derived_issue" in content
assert "unrelated_issue" in content
assert "contrarian candidate" in content
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: FAIL because the current generated guidance does not include the new hard-gate and re-entry language.

- [ ] **Step 3: Update the templates and injected guidance**

Make these exact content changes:

- In `templates/commands/debug.md`:
  - In `Session Lifecycle`, replace the old follow-up bullet with explicit classification language:

```markdown
- If the active session is `awaiting_human_verify` and the user reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.
- Default to `same_issue` unless repository evidence proves the other two classes.
- `same_issue` reopens the parent session.
- `derived_issue` creates a linked child session and returns to the parent only after the child resolves.
- `unrelated_issue` creates a separate session and does not auto-close the parent.
```

  - In `Human Verification`, replace:

```markdown
- Once the fix is verified by the agent, request a human confirmation checkpoint.
```

with:

```markdown
- Once the fix is verified by the agent, move into a formal human verification stage instead of resolving immediately.
- The session closes only after explicit human confirmation or an evidence-backed classification into `same_issue`, `derived_issue`, or `unrelated_issue`.
```

  - In `Stage 1: Observer Framing`, add:

```markdown
- Full framing: at least 3 candidates.
- Compressed framing: at least 2 candidates.
- Record a contrarian candidate from a different failure family.
- Candidate diversity must span at least 2 failure-shape or truth-owner families.
```

- In `templates/debug.md`, add field docs for:

```markdown
framing_gate_passed: [true only after candidate count, diversity, contrarian candidate, and transition memo requirements pass]
waiting_on_child_human_followup: [true when a parent session is blocked on a derived child issue]
```

and add new sections/keys for:

```markdown
contrarian_candidate: [strongest materially different alternative candidate]
candidate_resolutions:
  - candidate: [candidate text]
    disposition: confirmed | ruled_out | still_open_but_deprioritized
agent_fail_count: [automatic verification failures only]
human_reopen_count: [human verification reopen count only]
human_verification_outcome: pending | passed | same_issue | derived_issue | unrelated_issue | insufficient_feedback
```

- In `src/specify_cli/integrations/base.py`, update the injected debug guidance bullets around lines `1868-1913` to say:

```python
"- Do not resolve the session directly from successful automated verification. Successful automated verification must hand off into formal human verification.\n"
"- If human feedback reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.\n"
"- Default to `same_issue` unless strong evidence proves the other classes.\n"
"- Keep fixing, agent verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
```

- [ ] **Step 4: Run the focused template and integration tests**

Run:

```bash
python -m pytest tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/commands/debug.md templates/debug.md templates/worker-prompts/debug-thinker.md src/specify_cli/integrations/base.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "docs: align generated debug guidance with lifecycle hardening"
```

---

### Task 7: Run the end-to-end verification set and clean up compatibility edges

**Files:**
- Modify as needed: `tests/test_debug_graph.py`
- Modify as needed: `tests/test_debug_graph_nodes.py`
- Modify as needed: `tests/test_debug_persistence.py`
- Modify as needed: `tests/test_debug_cli.py`

- [ ] **Step 1: Run the full targeted regression set**

Run:

```bash
python -m pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_persistence.py tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS, or a small set of failures caused by renamed verification semantics or new persisted fields.

- [ ] **Step 2: Fix any compatibility-edge assertions**

Only adjust tests and messages needed to align old assumptions with the new lifecycle. Typical safe fixes:

```python
assert isinstance(result, AwaitingHumanNode)
```
instead of:
```python
assert isinstance(result, ResolvedNode)
```

and:

```python
assert "Agent verification status:" in report
assert "Human verification outcome:" in report
```

instead of relying on the older single-field verification wording.

Do not change runtime semantics in this cleanup task unless the failure proves a missing edge in earlier tasks.

- [ ] **Step 3: Re-run the targeted regression set**

Run:

```bash
python -m pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_persistence.py tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 4: Run the broader debug/integration sanity set**

Run:

```bash
python -m pytest tests/test_debug_think_agent.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py -q
```

Expected: PASS, or clearly explained unrelated baseline failures.

- [ ] **Step 5: Commit**

```bash
git add tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_persistence.py tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/test_debug_think_agent.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py
git commit -m "test: lock sp-debug lifecycle hardening behavior"
```

---

## Spec Coverage Check

- Lifecycle rewrite: covered by Tasks 1, 4, and 5.
- Framing hard gate: covered by Task 3.
- Human re-entry classification: covered by Tasks 1, 2, and 5.
- Template/runtime consistency: covered by Task 6.
- Resume/persistence safety: covered by Tasks 1, 2, and 5.

No spec section is intentionally unimplemented in this plan.

## Placeholder Check

- No `TBD`, `TODO`, or deferred pseudo-steps remain.
- Every task includes exact file paths and exact commands.
- Code steps reference concrete field names and branch behavior already present in the repository.

## Type Consistency Check

- New schema names used consistently:
  - `CandidateDisposition`
  - `HumanVerificationOutcome`
  - `CandidateResolution`
  - `waiting_on_child_human_followup`
  - `framing_gate_passed`
  - `agent_fail_count`
  - `human_reopen_count`
- The plan keeps `fail_count` temporarily as a compatibility mirror during migration and then moves assertions to the split counters.

Plan complete and saved to `docs/superpowers/plans/2026-05-02-sp-debug-lifecycle-hardening.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
