# sp-debug Causal Investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-debug` into a candidate-driven, root-cause-escalating debug workflow that turns observer framing into an enforceable investigation contract and requires lightweight related-risk scanning before closeout.

**Architecture:** Implement this in five slices. First, extend the debug schema and persistence contract with explicit investigation-contract state so candidate queues, related-risk targets, and coverage gates can survive resumes. Second, rework think-subagent output and GatheringNode contract checks so the first stage emits structured candidate-driven investigation inputs instead of advisory prose. Third, change the graph runtime so InvestigatingNode consumes candidate queues, VerifyingNode escalates into `root_cause` mode after repeated failures, and closeout requires related-risk scan completion. Fourth, align templates, integration guidance, and CLI/session rendering so generated `sp-debug` surfaces and local runtime behavior tell the same story. Fifth, lock the behavior with focused pytest coverage across schema, persistence, graph transitions, think-agent parsing, and generated skill guidance.

**Tech Stack:** Python 3.13+, Pydantic, Pydantic-Graph, Typer, pytest, Markdown/YAML templates

---

## File Structure

### Runtime state and persistence

- `src/specify_cli/debug/schema.py`
  Owns `DebugGraphState`, debug investigation-contract models, candidate status enums, and coverage flags.
- `src/specify_cli/debug/persistence.py`
  Owns debug-session markdown serialization, handoff report rendering, research checkpoints, and resume-safe round-tripping for new investigation fields.

### Think-subagent and state machine behavior

- `src/specify_cli/debug/think_agent.py`
  Owns think-subagent prompt construction and parsing of structured observer framing output.
- `templates/worker-prompts/debug-thinker.md`
  Owns the observer-framing contract the think subagent must emit.
- `src/specify_cli/debug/graph.py`
  Owns node transitions, framing gates, candidate-driven investigation flow, escalation into `root_cause` mode, related-risk gates, and verification behavior.

### User-visible workflow surfaces

- `templates/commands/debug.md`
  Owns the generated `sp-debug` workflow contract and stage guidance shipped into downstream agent surfaces.
- `templates/debug.md`
  Owns the canonical session template and field documentation for `.planning/debug/[slug].md`.
- `src/specify_cli/debug/cli.py`
  Owns user-facing debug checkpoint rendering and should surface candidate/related-risk status when present.
- `src/specify_cli/integrations/base.py`
  Owns injected integration guidance for generated `sp-debug` skills, including think-subagent and investigation-stage instructions.

### Verification

- `tests/test_debug_template_guidance.py`
- `tests/test_debug_persistence.py`
- `tests/test_debug_think_agent.py`
- `tests/test_debug_graph.py`
- `tests/test_debug_graph_nodes.py`
- `tests/test_debug_cli.py`
- `tests/test_extension_skills.py`
- `tests/integrations/test_integration_codex.py`

These tests already cover the current `sp-debug` lifecycle. Extend them in place rather than creating a shadow suite.

---

### Task 1: Add investigation-contract state to the debug schema

**Files:**
- Modify: `src/specify_cli/debug/schema.py`
- Test: `tests/test_debug_persistence.py`

- [ ] **Step 1: Write the failing persistence test for investigation-contract fields**

Add this test near the existing persistence round-trip coverage in `tests/test_debug_persistence.py`:

```python
def test_persistence_round_trips_investigation_contract_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="candidate-driven debug")
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.investigation_mode = "root_cause"
    state.investigation_contract.escalation_reason = "two verification failures"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser boundary truncates final token",
            "family": "truth_owner_logic",
            "status": "active",
            "why_it_fits": "Final token is consistently missing",
            "map_evidence": "Parser owns token boundary truth",
            "would_rule_out": "Raw parser output already includes final token",
            "recommended_first_probe": "Inspect raw parser output before rendering",
            "evidence_needed": ["raw parser output", "boundary indices"],
            "evidence_found": [],
            "related_targets": ["projection-boundary", "verification-repro"],
        }
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Same token family may be dropped after publish",
            "scope": "nearest-neighbor",
            "status": "pending",
            "evidence": [],
        }
    ]
    state.investigation_contract.causal_coverage_state = {
        "competing_candidate_ruled_out": False,
        "truth_owner_confirmed": True,
        "boundary_break_localized": True,
        "related_risk_scan_completed": False,
        "closeout_ready": False,
    }

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.investigation_contract.primary_candidate_id == "cand-parser-boundary"
    assert restored.investigation_contract.investigation_mode == "root_cause"
    assert restored.investigation_contract.escalation_reason == "two verification failures"
    assert restored.investigation_contract.candidate_queue[0].status == "active"
    assert restored.investigation_contract.related_risk_targets[0].status == "pending"
    assert restored.investigation_contract.causal_coverage_state.closeout_ready is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_persistence_round_trips_investigation_contract_fields -q
```

Expected: FAIL because `DebugGraphState` does not yet expose `investigation_contract`.

- [ ] **Step 3: Add the investigation-contract models and fields**

Update `src/specify_cli/debug/schema.py` with these exact new models:

```python
class InvestigationMode(str, Enum):
    NORMAL = "normal"
    ROOT_CAUSE = "root_cause"


class CandidateStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
    DEPRIORITIZED = "deprioritized"


class RelatedRiskStatus(str, Enum):
    PENDING = "pending"
    CHECKED = "checked"
    CLEARED = "cleared"
    NEEDS_FOLLOWUP = "needs_followup"


class InvestigationCandidate(BaseModel):
    candidate_id: str
    candidate: str
    family: str
    status: CandidateStatus = CandidateStatus.PENDING
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    would_rule_out: Optional[str] = None
    recommended_first_probe: Optional[str] = None
    evidence_needed: List[str] = Field(default_factory=list)
    evidence_found: List[str] = Field(default_factory=list)
    related_targets: List[str] = Field(default_factory=list)


class RelatedRiskTarget(BaseModel):
    target: str
    reason: str
    scope: str
    status: RelatedRiskStatus = RelatedRiskStatus.PENDING
    evidence: List[str] = Field(default_factory=list)


class CausalCoverageState(BaseModel):
    competing_candidate_ruled_out: bool = False
    truth_owner_confirmed: bool = False
    boundary_break_localized: bool = False
    related_risk_scan_completed: bool = False
    closeout_ready: bool = False


class InvestigationContractState(BaseModel):
    primary_candidate_id: Optional[str] = None
    candidate_queue: List[InvestigationCandidate] = Field(default_factory=list)
    related_risk_targets: List[RelatedRiskTarget] = Field(default_factory=list)
    investigation_mode: InvestigationMode = InvestigationMode.NORMAL
    escalation_reason: Optional[str] = None
    causal_coverage_state: CausalCoverageState = Field(default_factory=CausalCoverageState)
```

Then add the new field to `DebugGraphState`:

```python
    investigation_contract: InvestigationContractState = Field(default_factory=InvestigationContractState)
```

Do not remove the existing `candidate_resolutions`, `observer_framing`, or `transition_memo` fields in this task. The new contract must layer on top of the current state, not replace it yet.

- [ ] **Step 4: Run the targeted test to verify it passes**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_persistence_round_trips_investigation_contract_fields -q
```

Expected: PASS

- [ ] **Step 5: Run the full persistence test file**

Run:

```bash
uv run pytest tests/test_debug_persistence.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/schema.py tests/test_debug_persistence.py
git commit -m "feat: add debug investigation contract state"
```

---

### Task 2: Persist and report investigation-contract data

**Files:**
- Modify: `src/specify_cli/debug/persistence.py`
- Test: `tests/test_debug_persistence.py`

- [ ] **Step 1: Write the failing handoff-report test for candidate and related-risk rendering**

Add this test near the existing handoff report coverage in `tests/test_debug_persistence.py`:

```python
def test_handoff_report_includes_investigation_contract_sections(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="candidate report")
    state.investigation_contract.primary_candidate_id = "cand-parser-boundary"
    state.investigation_contract.investigation_mode = "root_cause"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-parser-boundary",
            "candidate": "Parser boundary truncates final token",
            "family": "truth_owner_logic",
            "status": "active",
        }
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor token drop risk",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]

    report = handler.build_handoff_report(state)

    assert "Investigation mode: root_cause" in report
    assert "Primary candidate: cand-parser-boundary" in report
    assert "Parser boundary truncates final token" in report
    assert "Related Risk Targets" in report
    assert "projection-boundary" in report
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_handoff_report_includes_investigation_contract_sections -q
```

Expected: FAIL because the report does not yet render investigation-contract details.

- [ ] **Step 3: Serialize, parse, and render the new contract sections**

Update `src/specify_cli/debug/persistence.py` in three places.

Add the new sections to `save()`:

```python
        sections = [
            ("Current Focus", state.current_focus.model_dump(mode="json")),
            ("Symptoms", state.symptoms.model_dump(mode="json")),
            ("Observer Framing", state.observer_framing.model_dump(mode="json")),
            ("Transition Memo", state.transition_memo.model_dump(mode="json")),
            ("Investigation Contract", state.investigation_contract.model_dump(mode="json")),
            ("Suggested Evidence Lanes", [lane.model_dump(mode="json") for lane in state.suggested_evidence_lanes]),
            ...
        ]
```

Add the new section to `load()`:

```python
                "investigation_contract": sections.get("Investigation Contract") or {},
```

Add a rendered report section in `build_handoff_report()`:

```python
    lines.extend(["", "### Investigation Contract"])
    lines.append(f"- Investigation mode: {state.investigation_contract.investigation_mode.value}")
    lines.append(f"- Primary candidate: {state.investigation_contract.primary_candidate_id or 'Not recorded'}")
    if state.investigation_contract.escalation_reason:
        lines.append(f"- Escalation reason: {state.investigation_contract.escalation_reason}")
    if state.investigation_contract.candidate_queue:
        lines.append("- Candidate queue:")
        for candidate in state.investigation_contract.candidate_queue:
            lines.append(
                f"  - {candidate.candidate_id}: {candidate.candidate} "
                f"[{candidate.family}] ({candidate.status.value})"
            )
    else:
        lines.append("- Candidate queue: not recorded")
```

Then add:

```python
    lines.extend(["", "### Related Risk Targets"])
    if state.investigation_contract.related_risk_targets:
        for target in state.investigation_contract.related_risk_targets:
            lines.append(
                f"- {target.target} ({target.scope}, {target.status.value}): {target.reason}"
            )
    else:
        lines.append("- Not recorded")
```

Keep all existing report sections intact. This task extends the current report rather than replacing it.

- [ ] **Step 4: Run the targeted test to verify it passes**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_handoff_report_includes_investigation_contract_sections -q
```

Expected: PASS

- [ ] **Step 5: Run the full persistence suite**

Run:

```bash
uv run pytest tests/test_debug_persistence.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/persistence.py tests/test_debug_persistence.py
git commit -m "feat: persist debug investigation contract"
```

---

### Task 3: Upgrade think-subagent output into investigation-contract input

**Files:**
- Modify: `templates/worker-prompts/debug-thinker.md`
- Modify: `src/specify_cli/debug/think_agent.py`
- Test: `tests/test_debug_think_agent.py`

- [ ] **Step 1: Write the failing parser test for investigation-contract fields**

Add this test to `tests/test_debug_think_agent.py`:

```python
def test_parse_think_subagent_result_extracts_investigation_contract_fields() -> None:
    raw = """Observer analysis.

---
observer_mode: "full"
observer_framing:
  summary: "Parser boundary likely owns the broken truth"
  primary_suspected_loop: "general"
  suspected_owning_layer: "parser"
  suspected_truth_owner: "parser"
  recommended_first_probe: "Inspect raw parser output before render"
  contrarian_candidate: "Projection boundary drops a correct parser result"
  missing_questions: []
alternative_cause_candidates:
  - candidate_id: "cand-parser-boundary"
    candidate: "Parser boundary truncates final token"
    failure_shape: "truth_owner_logic"
    why_it_fits: "Missing final token is stable"
    map_evidence: "Parser owns token boundary truth"
    would_rule_out: "Raw parser output contains final token"
    recommended_first_probe: "Inspect raw parser output before render"
  - candidate_id: "cand-projection-boundary"
    candidate: "Projection boundary drops final token"
    failure_shape: "projection_render"
    why_it_fits: "Rendered output may diverge after publish"
    map_evidence: "Projection is an observation layer"
    would_rule_out: "Published payload already lacks final token"
    recommended_first_probe: "Compare published payload and rendered output"
investigation_contract:
  primary_candidate_id: "cand-parser-boundary"
  investigation_mode: "normal"
  escalation_reason: null
  related_risk_targets:
    - target: "projection-boundary"
      reason: "Nearest-neighbor token family risk"
      scope: "nearest-neighbor"
      status: "pending"
transition_memo:
  first_candidate_to_test: "cand-parser-boundary"
  why_first: "Highest-likelihood truth owner"
  evidence_unlock: ["reproduction", "logs", "code", "tests"]
  carry_forward_notes:
    - "Do not discard the observer framing when code-level evidence appears."
"""

    result = parse_think_subagent_result(raw)

    assert result["alternative_cause_candidates"][0]["candidate_id"] == "cand-parser-boundary"
    assert result["investigation_contract"]["primary_candidate_id"] == "cand-parser-boundary"
    assert result["investigation_contract"]["related_risk_targets"][0]["target"] == "projection-boundary"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_debug_think_agent.py::test_parse_think_subagent_result_extracts_investigation_contract_fields -q
```

Expected: FAIL because the prompt/template contract does not yet define investigation-contract output.

- [ ] **Step 3: Extend the think-subagent prompt contract**

Update `templates/worker-prompts/debug-thinker.md` so the instructions now require:

```text
6. For each candidate include:
   - `candidate_id`: a stable identifier used by the leader runtime
   - `candidate`: a concise one-line hypothesis
   - `failure_shape`: one of ...
```

Add this instruction block after the candidate instructions:

```text
7. Build an `investigation_contract` section that includes:
   - `primary_candidate_id`
   - `investigation_mode` (`normal` unless the symptoms already imply a root-cause escalation)
   - `escalation_reason`
   - `related_risk_targets` (1-3 nearest-neighbor risks to revisit before closeout)
8. Recommend the first probe ...
```

Update the YAML example so it contains:

```yaml
alternative_cause_candidates:
  - candidate_id: "cand-parser-boundary"
    candidate: "..."
    failure_shape: "truth_owner_logic"
    ...
investigation_contract:
  primary_candidate_id: "cand-parser-boundary"
  investigation_mode: "normal"
  escalation_reason: null
  related_risk_targets:
    - target: "projection-boundary"
      reason: "Nearest-neighbor token family risk"
      scope: "nearest-neighbor"
      status: "pending"
```

- [ ] **Step 4: Keep the parser permissive but assert the new keys exist**

In `src/specify_cli/debug/think_agent.py`, leave `parse_think_subagent_result()` as a YAML extractor, but update the prompt-building tests to expect the new sections. Do not add business logic here yet; this task only changes the contract between prompt and caller.

- [ ] **Step 5: Update the think-agent tests**

Add these assertions to the existing prompt-structure tests in `tests/test_debug_think_agent.py`:

```python
    assert "candidate_id" in prompt
    assert "investigation_contract:" in prompt
    assert "related_risk_targets" in prompt
    assert "primary_candidate_id" in prompt
```

- [ ] **Step 6: Run the think-agent tests**

Run:

```bash
uv run pytest tests/test_debug_think_agent.py -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add templates/worker-prompts/debug-thinker.md src/specify_cli/debug/think_agent.py tests/test_debug_think_agent.py
git commit -m "feat: emit debug investigation contract from think subagent"
```

---

### Task 4: Enforce candidate-driven investigation and root-cause escalation in the graph

**Files:**
- Modify: `src/specify_cli/debug/graph.py`
- Test: `tests/test_debug_graph.py`
- Test: `tests/test_debug_graph_nodes.py`

- [ ] **Step 1: Write the failing graph tests for candidate gating and escalation**

Add these tests.

In `tests/test_debug_graph.py`:

```python
@pytest.mark.asyncio
async def test_gathering_blocks_when_transition_candidate_is_missing_from_queue():
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
    state.observer_framing.contrarian_candidate = "UI projection layer is stale"
    state.observer_framing.alternative_cause_candidates = [
        graph_module.ObserverCauseCandidate(candidate="A", failure_shape="truth_owner_logic"),
        graph_module.ObserverCauseCandidate(candidate="B", failure_shape="projection_render"),
        graph_module.ObserverCauseCandidate(candidate="C", failure_shape="config_flag_env"),
    ]
    state.transition_memo.first_candidate_to_test = "cand-missing"
    state.transition_memo.why_first = "best fit"
    state.transition_memo.evidence_unlock = ["reproduction"]
    state.investigation_contract.candidate_queue = [
        {"candidate_id": "cand-a", "candidate": "A", "family": "truth_owner_logic"},
        {"candidate_id": "cand-b", "candidate": "B", "family": "projection_render"},
    ]
    ctx = GraphRunContext(state=state, deps=None)

    result = await GatheringNode().run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "first candidate" in (state.current_focus.next_action or "").lower()
    assert "candidate queue" in (state.current_focus.next_action or "").lower()
```

In `tests/test_debug_graph_nodes.py`:

```python
@pytest.mark.asyncio
async def test_verifying_second_failure_switches_to_root_cause_mode(monkeypatch):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "FAIL")

    state = DebugGraphState(slug="test-session", trigger="hard bug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.resolution.fix = "Normalize display status"
    state.resolution.fail_count = 1
    state.investigation_contract.investigation_mode = "normal"

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert isinstance(result, InvestigatingNode)
    assert state.investigation_contract.investigation_mode.value == "root_cause"
    assert state.investigation_contract.escalation_reason == "two verification failures"
```

And:

```python
@pytest.mark.asyncio
async def test_verifying_blocks_closeout_until_related_risk_scan_completes(monkeypatch):
    monkeypatch.setattr(graph_module, "run_command", lambda _cmd: "PASS")

    state = DebugGraphState(slug="test-session", trigger="hard bug")
    state.symptoms.reproduction_command = "python tests/repro.py"
    state.context.modified_files = ["tests/test_debug_graph_nodes.py"]
    state.resolution.fix_scope = "truth-owner"
    state.resolution.loop_restoration_proof = ["Loop restored end-to-end"]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "projection-boundary",
            "reason": "Nearest-neighbor risk",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]
    state.investigation_contract.causal_coverage_state.related_risk_scan_completed = False

    node = VerifyingNode()
    ctx = GraphRunContext(state=state, deps=None)

    result = await node.run(ctx)

    assert result.data == "Awaiting more debugging input"
    assert "related risk" in (state.current_focus.next_action or "").lower()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
uv run pytest \
  tests/test_debug_graph.py::test_gathering_blocks_when_transition_candidate_is_missing_from_queue \
  tests/test_debug_graph_nodes.py::test_verifying_second_failure_switches_to_root_cause_mode \
  tests/test_debug_graph_nodes.py::test_verifying_blocks_closeout_until_related_risk_scan_completes -q
```

Expected: FAIL because the graph does not yet use `investigation_contract`.

- [ ] **Step 3: Add graph helpers for candidate and related-risk gates**

In `src/specify_cli/debug/graph.py`, add these helper functions near the other gate helpers:

```python
def _candidate_by_id(state: DebugGraphState, candidate_id: str | None):
    if not candidate_id:
        return None
    for candidate in state.investigation_contract.candidate_queue:
        if candidate.candidate_id == candidate_id:
            return candidate
    return None


def _related_risk_scan_gaps(state: DebugGraphState) -> list[str]:
    if state.investigation_contract.causal_coverage_state.related_risk_scan_completed:
        return []
    if state.investigation_contract.related_risk_targets:
        return ["related risk scan completion"]
    return []


def _sync_root_cause_mode(state: DebugGraphState) -> None:
    if state.resolution.agent_fail_count >= 2:
        state.investigation_contract.investigation_mode = InvestigationMode.ROOT_CAUSE
        state.investigation_contract.escalation_reason = "two verification failures"
```

- [ ] **Step 4: Enforce the contract in GatheringNode and InvestigatingNode**

Update `GatheringNode.run()` so after `_framing_gate_gaps()` it also checks:

```python
        first_candidate_id = ctx.state.transition_memo.first_candidate_to_test
        if first_candidate_id and not _candidate_by_id(ctx.state, first_candidate_id):
            return _await_input(
                ctx.state,
                "Observer framing is complete, but the first candidate to test is not present in the candidate queue. "
                "Reconcile transition_memo.first_candidate_to_test with investigation_contract.candidate_queue before continuing.",
            )
```

Update `InvestigatingNode.run()` so it activates the primary candidate when none is active:

```python
        if ctx.state.investigation_contract.primary_candidate_id:
            active = [
                candidate
                for candidate in ctx.state.investigation_contract.candidate_queue
                if candidate.status == CandidateStatus.ACTIVE
            ]
            if not active:
                primary = _candidate_by_id(ctx.state, ctx.state.investigation_contract.primary_candidate_id)
                if primary and primary.status == CandidateStatus.PENDING:
                    primary.status = CandidateStatus.ACTIVE
```

Do not rewrite the whole node in this step. Only introduce the minimum state activation and gate wiring necessary for the new tests.

- [ ] **Step 5: Enforce root-cause mode and related-risk gate in VerifyingNode**

In `_handle_failed_verification()`, after incrementing `agent_fail_count`, call:

```python
        _sync_root_cause_mode(state)
```

In `VerifyingNode.run()`, after `_post_verification_readiness_gaps(state)` and before returning `AwaitingHumanNode()`, add:

```python
        related_risk_gaps = _related_risk_scan_gaps(ctx.state)
        if related_risk_gaps:
            ctx.state.resolution.verification = "success"
            return _await_input(
                ctx.state,
                _format_checklist(
                    "Verification passed, but related-risk review is incomplete.",
                    related_risk_gaps,
                    intro="Finish the nearest-neighbor related-risk scan before closing the session:",
                ),
            )
```

- [ ] **Step 6: Run the targeted graph tests**

Run:

```bash
uv run pytest \
  tests/test_debug_graph.py::test_gathering_blocks_when_transition_candidate_is_missing_from_queue \
  tests/test_debug_graph_nodes.py::test_verifying_second_failure_switches_to_root_cause_mode \
  tests/test_debug_graph_nodes.py::test_verifying_blocks_closeout_until_related_risk_scan_completes -q
```

Expected: PASS

- [ ] **Step 7: Run the debug graph suites**

Run:

```bash
uv run pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -q
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: enforce debug investigation contract in graph"
```

---

### Task 5: Align templates, CLI output, and generated skill guidance

**Files:**
- Modify: `templates/commands/debug.md`
- Modify: `templates/debug.md`
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/test_debug_template_guidance.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Write the failing template-guidance and integration assertions**

Add these assertions to `tests/test_debug_template_guidance.py`:

```python
    assert "investigation contract" in content
    assert "candidate queue" in content
    assert "related risk targets" in content
    assert "root-cause mode" in content
    assert "second stage must consume the candidate queue" in content
```

Add these assertions to `tests/test_debug_template_guidance.py` session-template test:

```python
    assert "## Investigation Contract" in content
    assert "primary_candidate_id:" in content
    assert "candidate_queue:" in content
    assert "related_risk_targets:" in content
    assert "investigation_mode:" in content
```

Add this assertion to `tests/test_extension_skills.py` and `tests/integrations/test_integration_codex.py` where the current `sp-debug` guidance is checked:

```python
    assert "candidate queue" in debug_lower
    assert "root-cause mode" in debug_lower
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run pytest tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: FAIL because the templates and generated integration guidance do not yet mention the new contract.

- [ ] **Step 3: Update the templates**

In `templates/commands/debug.md`, add these exact guidance points:

```markdown
- **Observer framing becomes an investigation contract**: The output of the think subagent is not advisory prose. The second stage must consume the candidate queue, primary candidate, and related risk targets before freeform investigation can continue.
- **Root-cause mode is mandatory after repeated failure**: After two automated verification failures, stop adding point fixes and switch the session into `root_cause mode`.
- **Related-risk review is part of closeout**: Do not close the session until nearest-neighbor related risk targets have been reviewed.
```

In `templates/debug.md`, add a new section before `## Suggested Evidence Lanes`:

```markdown
## Investigation Contract
<!-- OVERWRITE/REFINE - converts observer framing into runtime investigation constraints -->

primary_candidate_id: [candidate id currently driving the next investigation step]
investigation_mode: normal | root_cause
escalation_reason: [why the session entered root_cause mode, if it did]
candidate_queue:
  - candidate_id: [stable candidate id]
    candidate: [concise one-line hypothesis]
    family: [truth_owner_logic | projection_render | ...]
    status: pending | active | confirmed | ruled_out | deprioritized
    evidence_needed:
      - [concrete evidence still required]
    evidence_found:
      - [evidence already collected]
    related_targets:
      - [nearest-neighbor target id]
related_risk_targets:
  - target: [adjacent risk area]
    reason: [why this risk is related]
    scope: [nearest-neighbor | broader-family]
    status: pending | checked | cleared | needs_followup
    evidence:
      - [what was reviewed]
causal_coverage_state:
  competing_candidate_ruled_out: [true|false]
  truth_owner_confirmed: [true|false]
  boundary_break_localized: [true|false]
  related_risk_scan_completed: [true|false]
  closeout_ready: [true|false]
```

- [ ] **Step 4: Surface the new contract in CLI checkpoints and integration guidance**

In `src/specify_cli/debug/cli.py`, add a new helper and call it from `_print_session_checkpoint()`:

```python
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
            console.print(f"  - {candidate.candidate_id}: {candidate.candidate} ({candidate.status.value})")
    if contract.related_risk_targets:
        console.print("- Related risk targets:")
        for target in contract.related_risk_targets:
            console.print(f"  - {target.target} ({target.status.value})")
```

In `src/specify_cli/integrations/base.py`, extend the injected `sp-debug` guidance string with:

```text
- The think-subagent output is an investigation contract, not advisory prose.
- The investigating stage must consume the candidate queue and primary candidate before freeform fixes begin.
- After two automated verification failures, switch the session into root-cause mode and stop layering point fixes.
- Do not close the session until nearest-neighbor related risk targets have been reviewed.
```

- [ ] **Step 5: Run the targeted guidance tests**

Run:

```bash
uv run pytest tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add templates/commands/debug.md templates/debug.md src/specify_cli/debug/cli.py src/specify_cli/integrations/base.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: align debug surfaces with causal investigation contract"
```

---

### Task 6: Run the final verification set

**Files:**
- Modify: none
- Test: `tests/test_debug_persistence.py`
- Test: `tests/test_debug_think_agent.py`
- Test: `tests/test_debug_graph.py`
- Test: `tests/test_debug_graph_nodes.py`
- Test: `tests/test_debug_cli.py`
- Test: `tests/test_debug_template_guidance.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Run the focused debug verification suite**

Run:

```bash
uv run pytest \
  tests/test_debug_persistence.py \
  tests/test_debug_think_agent.py \
  tests/test_debug_graph.py \
  tests/test_debug_graph_nodes.py \
  tests/test_debug_cli.py \
  tests/test_debug_template_guidance.py \
  tests/test_extension_skills.py \
  tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 2: Run the repository diff review**

Run:

```bash
git diff -- src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py src/specify_cli/debug/think_agent.py src/specify_cli/debug/graph.py src/specify_cli/debug/cli.py templates/worker-prompts/debug-thinker.md templates/commands/debug.md templates/debug.md src/specify_cli/integrations/base.py tests/test_debug_persistence.py tests/test_debug_think_agent.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
```

Expected: Only the planned causal-investigation changes appear.

- [ ] **Step 3: Commit the final integration pass**

```bash
git add src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py src/specify_cli/debug/think_agent.py src/specify_cli/debug/graph.py src/specify_cli/debug/cli.py templates/worker-prompts/debug-thinker.md templates/commands/debug.md templates/debug.md src/specify_cli/integrations/base.py tests/test_debug_persistence.py tests/test_debug_think_agent.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: harden sp-debug causal investigation flow"
```

---

## Self-Review

### Spec coverage

- Investigation contract state is covered by Task 1 and Task 2.
- Candidate-driven graph behavior and root-cause escalation are covered by Task 4.
- Related-risk closeout gating is covered by Task 4 and Task 5.
- Prompt, template, CLI, and generated-skill alignment are covered by Task 3 and Task 5.
- Verification and regression coverage are covered by Task 6.

No spec section is left without a corresponding implementation task.

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” placeholders remain.
- Each task includes exact file paths, exact commands, and concrete code snippets.
- The plan does not rely on “similar to previous task” shorthand.

### Type consistency

- Investigation state names are consistent across tasks:
  `InvestigationMode`, `CandidateStatus`, `RelatedRiskStatus`, `InvestigationCandidate`, `RelatedRiskTarget`, `CausalCoverageState`, and `InvestigationContractState`.
- Runtime field names are consistent across schema, persistence, graph, CLI, and templates:
  `primary_candidate_id`, `candidate_queue`, `related_risk_targets`, `investigation_mode`, `escalation_reason`, and `causal_coverage_state`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-03-sp-debug-causal-investigation-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
