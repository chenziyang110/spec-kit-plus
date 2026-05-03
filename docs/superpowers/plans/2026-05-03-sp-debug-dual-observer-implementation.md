# sp-debug Dual Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-debug` from a single observer-framing stage into a dual-observer workflow with a `Causal Map Agent`, an `Investigation Contract Agent`, stronger family-coverage gates, and explicit adjacent-risk closeout requirements.

**Architecture:** Implement this in five slices. First, extend debug session state and persistence with a durable `causal_map` surface while preserving current `observer_framing` and `investigation_contract` compatibility. Second, split the current single think-subagent surface into two focused prompt/parser surfaces: one for causal-map generation and one for contract generation. Third, rework `GatheringNode` into a two-step Stage `1A/1B` handshake and only mark observer framing complete once both subagents have produced valid outputs. Fourth, tighten investigation, fixing, and verification gates so family coverage, contrarian consumption, and adjacent-risk checks are required before closeout. Fifth, align generated `sp-debug` guidance, CLI rendering, and tests so the runtime and generated skill surface tell the same story.

**Tech Stack:** Python 3.13+, Pydantic, Pydantic-Graph, Typer, pytest, Markdown/YAML templates

---

## File Structure

### Runtime state and persistence

- `src/specify_cli/debug/schema.py`
  Owns `DebugGraphState`, `causal_map` models, dual-observer stage flags, and prompt handoff fields.
- `src/specify_cli/debug/persistence.py`
  Owns markdown serialization and resume-safe round-tripping for `causal_map`, `observer_framing`, `transition_memo`, and `investigation_contract`.

### Subagent prompt surfaces

- `src/specify_cli/debug/think_agent.py`
  Owns the Stage `1A` causal-map prompt builder and parser.
- `src/specify_cli/debug/contract_agent.py`
  Owns the Stage `1B` contract-planner prompt builder and parser.
- `templates/worker-prompts/debug-thinker.md`
  Owns the `Causal Map Agent` contract.
- `templates/worker-prompts/debug-contract-planner.md`
  Owns the `Investigation Contract Agent` contract.

### State machine behavior

- `src/specify_cli/debug/graph.py`
  Owns dual-observer orchestration, framing gates, contract-driven investigation readiness, root-cause escalation, and related-risk closeout behavior.

### User-visible workflow surfaces

- `templates/commands/debug.md`
  Owns the generated `sp-debug` workflow contract and stage naming shipped downstream.
- `templates/debug.md`
  Owns the canonical `.planning/debug/[slug].md` structure and section rules.
- `src/specify_cli/debug/cli.py`
  Owns checkpoint rendering for `causal_map`, contract status, and adjacent-risk status.
- `src/specify_cli/integrations/base.py`
  Owns injected integration guidance for generated `sp-debug` skills, including the second subagent handoff.

### Verification

- `tests/test_debug_persistence.py`
- `tests/test_debug_think_agent.py`
- `tests/test_debug_graph.py`
- `tests/test_debug_graph_nodes.py`
- `tests/test_debug_cli.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_extension_skills.py`
- `tests/integrations/test_integration_codex.py`

Extend these existing tests in place. Do not create a parallel “v2” test suite.

---

### Task 1: Add durable `causal_map` state and persistence

**Files:**
- Modify: `src/specify_cli/debug/schema.py`
- Modify: `src/specify_cli/debug/persistence.py`
- Test: `tests/test_debug_persistence.py`

- [ ] **Step 1: Write the failing persistence test for `causal_map` round-trip**

Add this test near the existing persistence round-trip coverage in `tests/test_debug_persistence.py`:

```python
def test_persistence_round_trips_causal_map_fields(tmp_path):
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="queue stuck after slot release")
    state.causal_map_completed = True
    state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
    state.causal_map.closed_loop_path = [
        "job release event",
        "scheduler admission decision",
        "slot ownership update",
        "queue projection refresh",
        "UI queue badge render",
    ]
    state.causal_map.break_edges = [
        "slot ownership update -> queue projection refresh",
    ]
    state.causal_map.bypass_paths = [
        "snapshot cache serves stale queue count after ownership update",
    ]
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        {
            "candidate_id": "cand-slot-ownership",
            "family": "truth_owner_logic",
            "candidate": "Scheduler does not clear slot ownership on release",
            "why_it_fits": "Queue stays blocked after release",
            "map_evidence": "Scheduler owns slot allocation truth",
            "falsifier": "Ownership set is empty before the UI refresh begins",
            "break_edge": "scheduler admission decision -> slot ownership update",
            "bypass_path": "stale ownership cache",
            "recommended_first_probe": "Inspect ownership set immediately after release",
        }
    ]
    state.causal_map.adjacent_risk_targets = [
        {
            "target": "release-retry-loop",
            "reason": "Same ownership path governs retry admission",
            "family": "truth_owner_logic",
            "scope": "nearest-neighbor",
            "falsifier": "Retry path bypasses slot ownership state",
        }
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.causal_map_completed is True
    assert restored.causal_map.symptom_anchor == "UI queue badge remains non-zero"
    assert restored.causal_map.closed_loop_path[1] == "scheduler admission decision"
    assert restored.causal_map.candidates[0].candidate_id == "cand-slot-ownership"
    assert restored.causal_map.candidates[0].falsifier == "Ownership set is empty before the UI refresh begins"
    assert restored.causal_map.adjacent_risk_targets[0].target == "release-retry-loop"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_persistence_round_trips_causal_map_fields -q
```

Expected: FAIL because `DebugGraphState` does not yet expose `causal_map` or `causal_map_completed`.

- [ ] **Step 3: Add the `causal_map` models and state fields**

Update `src/specify_cli/debug/schema.py` by inserting these exact models below `InvestigationContractState`:

```python
class CausalMapCandidate(BaseModel):
    candidate_id: str
    family: str
    candidate: str
    why_it_fits: Optional[str] = None
    map_evidence: Optional[str] = None
    falsifier: Optional[str] = None
    break_edge: Optional[str] = None
    bypass_path: Optional[str] = None
    recommended_first_probe: Optional[str] = None


class CausalMapRiskTarget(BaseModel):
    target: str
    reason: str
    family: str
    scope: str = "nearest-neighbor"
    falsifier: Optional[str] = None


class CausalMapState(BaseModel):
    symptom_anchor: Optional[str] = None
    closed_loop_path: List[str] = Field(default_factory=list)
    break_edges: List[str] = Field(default_factory=list)
    bypass_paths: List[str] = Field(default_factory=list)
    family_coverage: List[str] = Field(default_factory=list)
    candidates: List[CausalMapCandidate] = Field(default_factory=list)
    adjacent_risk_targets: List[CausalMapRiskTarget] = Field(default_factory=list)
```

Then add these fields to `DebugGraphState` immediately above `observer_mode`:

```python
    causal_map_completed: bool = False
    contract_generation_completed: bool = False
```

And add these payload fields near the other structured state:

```python
    causal_map: CausalMapState = Field(default_factory=CausalMapState)
    contract_subagent_prompt: Optional[str] = None
```

Do not remove `observer_framing_completed`, `observer_framing`, or `investigation_contract` in this task.

- [ ] **Step 4: Persist the new section in markdown saves and loads**

Update `src/specify_cli/debug/persistence.py` in the same style as `Observer Framing` and `Investigation Contract`. Add a `### Causal Map` section that renders:

```python
    lines.extend(["", "### Causal Map"])
    if state.causal_map.symptom_anchor:
        lines.append(f"- Symptom anchor: {state.causal_map.symptom_anchor}")
    if state.causal_map.closed_loop_path:
        lines.append("- Closed loop path:")
        for item in state.causal_map.closed_loop_path:
            lines.append(f"  - {item}")
    if state.causal_map.break_edges:
        lines.append("- Break edges:")
        for item in state.causal_map.break_edges:
            lines.append(f"  - {item}")
    if state.causal_map.bypass_paths:
        lines.append("- Bypass paths:")
        for item in state.causal_map.bypass_paths:
            lines.append(f"  - {item}")
```

Also add JSON section persistence entries for `"Causal Map"` and load support:

```python
            ("Causal Map", state.causal_map.model_dump(mode="json")),
```

and

```python
                "causal_map": sections.get("Causal Map") or {},
```

plus frontmatter load/save for `causal_map_completed` and `contract_generation_completed`.

- [ ] **Step 5: Run the targeted persistence tests**

Run:

```bash
uv run pytest tests/test_debug_persistence.py::test_persistence_round_trips_causal_map_fields -q
uv run pytest tests/test_debug_persistence.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py tests/test_debug_persistence.py
git commit -m "feat: add debug causal map state"
```

---

### Task 2: Split the single observer prompt into two focused subagent surfaces

**Files:**
- Modify: `src/specify_cli/debug/think_agent.py`
- Create: `src/specify_cli/debug/contract_agent.py`
- Modify: `templates/worker-prompts/debug-thinker.md`
- Create: `templates/worker-prompts/debug-contract-planner.md`
- Modify: `tests/test_debug_think_agent.py`
- Create: `tests/test_debug_contract_agent.py`

- [ ] **Step 1: Add the failing causal-map prompt/parser tests**

In `tests/test_debug_think_agent.py`, add these two tests:

```python
def test_build_think_subagent_prompt_requires_family_coverage_output() -> None:
    state = DebugGraphState(
        slug="test-session",
        trigger="queue badge remains non-zero after slot release",
        diagnostic_profile="scheduler-admission",
    )
    state.symptoms.expected = "queue badge resets to zero"
    state.symptoms.actual = "queue badge remains non-zero"

    prompt = build_think_subagent_prompt(state)

    assert "family_coverage" in prompt
    assert "falsifier" in prompt
    assert "adjacent_risk_targets" in prompt
    assert "closed_loop_path" in prompt


def test_parse_think_subagent_result_extracts_causal_map() -> None:
    raw = """Scheduler ownership looks stale after release.

---
observer_mode: "full"
causal_map:
  symptom_anchor: "UI queue badge remains non-zero"
  closed_loop_path:
    - "job release event"
    - "scheduler admission decision"
  family_coverage:
    - "truth_owner_logic"
    - "cache_snapshot"
  candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      candidate: "Scheduler does not clear slot ownership on release"
      falsifier: "Ownership set is empty before projection refresh"
"""

    data = parse_think_subagent_result(raw)

    assert data["causal_map"]["symptom_anchor"] == "UI queue badge remains non-zero"
    assert data["causal_map"]["family_coverage"] == ["truth_owner_logic", "cache_snapshot"]
    assert data["causal_map"]["candidates"][0]["candidate_id"] == "cand-slot-ownership"
```

- [ ] **Step 2: Add the failing contract-planner tests**

Create `tests/test_debug_contract_agent.py` with this content:

```python
from specify_cli.debug.contract_agent import (
    build_contract_subagent_prompt,
    parse_contract_subagent_result,
)
from specify_cli.debug.schema import DebugGraphState


def test_build_contract_subagent_prompt_includes_causal_map_inputs() -> None:
    state = DebugGraphState(slug="test-session", trigger="queue badge remains non-zero")
    state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        {
            "candidate_id": "cand-slot-ownership",
            "family": "truth_owner_logic",
            "candidate": "Scheduler does not clear slot ownership on release",
        }
    ]

    prompt = build_contract_subagent_prompt(state)

    assert "cand-slot-ownership" in prompt
    assert "contrarian_candidate" in prompt
    assert "candidate_queue" in prompt
    assert "fix_gate_conditions" in prompt


def test_parse_contract_subagent_result_extracts_investigation_contract() -> None:
    raw = """Use slot ownership as the first probe.

---
observer_framing:
  summary: "Queue badge is downstream of slot ownership truth"
  contrarian_candidate: "Projection layer renders stale queue counts"
transition_memo:
  first_candidate_to_test: "cand-slot-ownership"
  why_first: "It decides the shared truth"
  evidence_unlock:
    - "reproduction"
    - "logs"
investigation_contract:
  primary_candidate_id: "cand-slot-ownership"
  investigation_mode: "normal"
  escalation_reason: null
  candidate_queue:
    - candidate_id: "cand-slot-ownership"
      candidate: "Scheduler does not clear slot ownership on release"
      family: "truth_owner_logic"
      status: "pending"
  related_risk_targets:
    - target: "release-retry-loop"
      reason: "Retry admission also depends on slot ownership"
      scope: "nearest-neighbor"
      status: "pending"
"""

    data = parse_contract_subagent_result(raw)

    assert data["investigation_contract"]["primary_candidate_id"] == "cand-slot-ownership"
    assert data["transition_memo"]["first_candidate_to_test"] == "cand-slot-ownership"
    assert data["observer_framing"]["contrarian_candidate"] == "Projection layer renders stale queue counts"
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run:

```bash
uv run pytest tests/test_debug_think_agent.py::test_build_think_subagent_prompt_requires_family_coverage_output -q
uv run pytest tests/test_debug_contract_agent.py -q
```

Expected: FAIL because the current prompt does not emit `causal_map` requirements and `contract_agent.py` does not exist.

- [ ] **Step 4: Rework the Stage `1A` prompt and parser**

Update `templates/worker-prompts/debug-thinker.md` so the YAML contract emits `causal_map` instead of `investigation_contract`. Replace the output example block with:

```markdown
---
observer_mode: "full"
causal_map:
  symptom_anchor: "where the symptom first appears"
  closed_loop_path:
    - "input event"
    - "control decision"
    - "truth owner update"
    - "projection refresh"
    - "external observation"
  break_edges:
    - "truth owner update -> projection refresh"
  bypass_paths:
    - "snapshot cache serves stale projection"
  family_coverage:
    - "truth_owner_logic"
    - "cache_snapshot"
    - "projection_render"
  candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      candidate: "Scheduler does not clear slot ownership on release"
      why_it_fits: "Queue remains blocked after release"
      map_evidence: "Scheduler owns slot allocation truth"
      falsifier: "Ownership set is empty before projection refresh"
      break_edge: "scheduler admission decision -> slot ownership update"
      bypass_path: "stale ownership cache"
      recommended_first_probe: "Inspect ownership set immediately after release"
  adjacent_risk_targets:
    - target: "release-retry-loop"
      reason: "Retry admission also depends on slot ownership"
      family: "truth_owner_logic"
      scope: "nearest-neighbor"
      falsifier: "Retry admission bypasses slot ownership state"
```

Then update `src/specify_cli/debug/think_agent.py` so the prompt builder asserts these fields and the parser still returns the post-`---` mapping unchanged.

- [ ] **Step 5: Add the second planner surface**

Create `src/specify_cli/debug/contract_agent.py` with this implementation:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import DebugGraphState


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "templates"
    / "worker-prompts"
    / "debug-contract-planner.md"
)


def build_contract_subagent_prompt(state: DebugGraphState) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    causal_map = state.causal_map.model_dump(mode="json")
    observer = state.observer_framing.model_dump(mode="json")
    payload = yaml.safe_dump(
        {
            "trigger": state.trigger,
            "diagnostic_profile": state.diagnostic_profile or "general",
            "causal_map": causal_map,
            "observer_framing": observer,
        },
        allow_unicode=True,
        sort_keys=False,
    )
    return template.replace("{CAUSAL_MAP_PAYLOAD}", payload)


def parse_contract_subagent_result(raw_text: str) -> dict[str, Any]:
    separator = "\n---\n"
    if separator not in raw_text:
        return {}
    _, _, yaml_block = raw_text.partition(separator)
    if not yaml_block.strip():
        return {}
    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
```

Create `templates/worker-prompts/debug-contract-planner.md` with this exact scaffold:

```markdown
# Contract Planner — Investigation Contract

You are the second-stage debug planner. You do not widen the hypothesis space. You convert the causal map into a runtime investigation contract.

## Hard Constraints

- Do not invent new families unless the causal map is internally inconsistent.
- Keep the `primary_candidate` and `contrarian_candidate` in different families.
- Produce a minimal contract by default.
- Escalate to `root_cause` only when the supplied causal map already implies a high-complexity issue.

## Input

```yaml
{CAUSAL_MAP_PAYLOAD}
```

## Required Output

Return free text followed by `---` and a YAML block containing:

- `observer_framing.summary`
- `observer_framing.primary_suspected_loop`
- `observer_framing.suspected_owning_layer`
- `observer_framing.suspected_truth_owner`
- `observer_framing.recommended_first_probe`
- `observer_framing.contrarian_candidate`
- `transition_memo.first_candidate_to_test`
- `transition_memo.why_first`
- `transition_memo.evidence_unlock`
- `transition_memo.carry_forward_notes`
- `investigation_contract.primary_candidate_id`
- `investigation_contract.investigation_mode`
- `investigation_contract.escalation_reason`
- `investigation_contract.candidate_queue`
- `investigation_contract.related_risk_targets`
- `investigation_contract.causal_coverage_state`
```

- [ ] **Step 6: Run the focused prompt/parser tests**

Run:

```bash
uv run pytest tests/test_debug_think_agent.py -q
uv run pytest tests/test_debug_contract_agent.py -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/debug/think_agent.py src/specify_cli/debug/contract_agent.py templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md tests/test_debug_think_agent.py tests/test_debug_contract_agent.py
git commit -m "feat: split debug dual observer prompt surfaces"
```

---

### Task 3: Orchestrate Stage `1A/1B` in `GatheringNode`

**Files:**
- Modify: `src/specify_cli/debug/graph.py`
- Modify: `tests/test_debug_graph.py`
- Modify: `tests/test_debug_graph_nodes.py`

- [ ] **Step 1: Add the failing graph tests for the second handoff**

In `tests/test_debug_graph.py`, add:

```python
@pytest.mark.asyncio
async def test_gathering_requests_contract_subagent_after_causal_map() -> None:
    state = DebugGraphState(trigger="queue stuck", slug="test-slug")
    state.causal_map_completed = True
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        {
            "candidate_id": "cand-slot-ownership",
            "family": "truth_owner_logic",
            "candidate": "Scheduler does not clear slot ownership on release",
        }
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert state.contract_subagent_prompt is not None
    assert "contract subagent" in (state.current_focus.next_action or "").lower()
```

In `tests/test_debug_graph_nodes.py`, add:

```python
@pytest.mark.asyncio
async def test_gathering_blocks_until_dual_observer_is_complete() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.causal_map_completed = True
    state.contract_generation_completed = False
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.candidates = [
        {
            "candidate_id": "cand-slot-ownership",
            "family": "truth_owner_logic",
            "candidate": "Scheduler does not clear slot ownership on release",
        }
    ]

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert state.observer_framing_completed is False
    assert state.contract_subagent_prompt is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run pytest tests/test_debug_graph.py::test_gathering_requests_contract_subagent_after_causal_map -q
uv run pytest tests/test_debug_graph_nodes.py::test_gathering_blocks_until_dual_observer_is_complete -q
```

Expected: FAIL because `GatheringNode` only knows about the current single think-subagent handshake.

- [ ] **Step 3: Add the second handshake to `GatheringNode`**

Update `src/specify_cli/debug/graph.py` imports:

```python
from .contract_agent import build_contract_subagent_prompt
```

Then replace the current single observer block in `GatheringNode.run()` with:

```python
        if not ctx.state.causal_map_completed:
            prompt = build_think_subagent_prompt(ctx.state)
            ctx.state.think_subagent_prompt = prompt
            return _await_input(
                ctx.state,
                "Causal map needed. Spawn a think subagent with think_subagent_prompt. "
                "Wait for its structured result, then populate causal_map, observer_mode, "
                "and any observer summary fields it returned. Set causal_map_completed=True and continue.",
            )

        if not ctx.state.contract_generation_completed:
            prompt = build_contract_subagent_prompt(ctx.state)
            ctx.state.contract_subagent_prompt = prompt
            return _await_input(
                ctx.state,
                "Investigation contract needed. Spawn a contract subagent with contract_subagent_prompt. "
                "Wait for its structured result, then populate observer_framing, transition_memo, and "
                "investigation_contract. Set contract_generation_completed=True and continue.",
            )

        ctx.state.observer_framing_completed = True
```

- [ ] **Step 4: Tighten the framing gate to require family coverage**

Extend `_framing_gate_gaps(state)` in `src/specify_cli/debug/graph.py` so it checks:

```python
    family_count = len(set(state.causal_map.family_coverage))
    minimum_family_count = 2 if state.observer_mode == "compressed" else 3
    if family_count < minimum_family_count:
        gaps.append(
            f"Causal map must cover at least {minimum_family_count} distinct failure families before investigation."
        )
    if not state.causal_map.candidates:
        gaps.append("Causal map must include candidate entries before contract generation can pass.")
    if not state.causal_map.adjacent_risk_targets:
        gaps.append("Causal map must identify at least one adjacent risk target before investigation.")
```

Do not remove the existing observer-framing checks in this step.

- [ ] **Step 5: Run the focused graph tests**

Run:

```bash
uv run pytest tests/test_debug_graph.py -q
uv run pytest tests/test_debug_graph_nodes.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: orchestrate dual observer gathering flow"
```

---

### Task 4: Make investigation, fixing, and verification consume the contract

**Files:**
- Modify: `src/specify_cli/debug/graph.py`
- Modify: `tests/test_debug_graph.py`
- Modify: `tests/test_debug_graph_nodes.py`

- [ ] **Step 1: Add the failing contract-consumption tests**

In `tests/test_debug_graph_nodes.py`, add:

```python
@pytest.mark.asyncio
async def test_fixing_blocks_until_contrarian_candidate_is_resolved() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.resolution.root_cause = {
        "summary": "Scheduler does not clear slot ownership on release",
        "owning_layer": "scheduler",
        "broken_control_state": "slot ownership set",
        "failure_mechanism": "release path leaves ownership set dirty",
        "loop_break": "truth owner update -> projection refresh",
        "decisive_signal": "ownership set remains non-empty after release",
    }
    state.investigation_contract.primary_candidate_id = "cand-slot-ownership"
    state.investigation_contract.candidate_queue = [
        {
            "candidate_id": "cand-slot-ownership",
            "candidate": "Scheduler does not clear slot ownership on release",
            "family": "truth_owner_logic",
            "status": "confirmed",
        },
        {
            "candidate_id": "cand-stale-projection",
            "candidate": "Projection layer renders stale queue counts",
            "family": "projection_render",
            "status": "pending",
        },
    ]
    state.investigation_contract.related_risk_targets = [
        {
            "target": "release-retry-loop",
            "reason": "Retry admission also depends on slot ownership",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]

    result = await InvestigatingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "competing candidate" in (state.current_focus.next_action or "").lower()
```

Also add:

```python
@pytest.mark.asyncio
async def test_verifying_blocks_until_adjacent_risk_target_checked(monkeypatch) -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.reproduction_command = "pytest tests/test_debug_graph.py::test_gathering_to_investigating -q"
    state.resolution.fix = "clear slot ownership on release"
    state.resolution.root_cause = {
        "summary": "Scheduler does not clear slot ownership on release",
        "owning_layer": "scheduler",
        "broken_control_state": "slot ownership set",
        "failure_mechanism": "release path leaves ownership set dirty",
        "loop_break": "truth owner update -> projection refresh",
        "decisive_signal": "ownership set remains non-empty after release",
    }
    state.investigation_contract.related_risk_targets = [
        {
            "target": "release-retry-loop",
            "reason": "Retry admission also depends on slot ownership",
            "scope": "nearest-neighbor",
            "status": "pending",
        }
    ]

    monkeypatch.setattr(
        "specify_cli.debug.graph.run_verification_commands",
        lambda commands, runner, stop_on_failure: [],
    )
    monkeypatch.setattr(
        "specify_cli.debug.graph.verification_passed",
        lambda results: True,
    )

    result = await VerifyingNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "related-risk review is incomplete" in (state.current_focus.next_action or "").lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run pytest tests/test_debug_graph_nodes.py::test_fixing_blocks_until_contrarian_candidate_is_resolved -q
uv run pytest tests/test_debug_graph_nodes.py::test_verifying_blocks_until_adjacent_risk_target_checked -q
```

Expected: FAIL because current readiness logic does not require an explicit contrarian disposition or a checked adjacent-risk target before closeout.

- [ ] **Step 3: Add explicit contract-readiness helpers**

In `src/specify_cli/debug/graph.py`, add these helpers near the other readiness helpers:

```python
def _minimum_contract_gaps(state: DebugGraphState) -> list[str]:
    gaps: list[str] = []
    contract = state.investigation_contract
    if not contract.primary_candidate_id:
        gaps.append("Set investigation_contract.primary_candidate_id before entering fixing.")
    if len(contract.candidate_queue) < 2:
        gaps.append("Keep at least a primary candidate and one contrarian candidate in the candidate queue.")
    families = {
        candidate.family
        for candidate in contract.candidate_queue
        if getattr(candidate, "family", None)
    }
    if len(families) < 2:
        gaps.append("Candidate queue must span at least two failure families before fixing.")
    if not contract.related_risk_targets:
        gaps.append("Record at least one adjacent risk target before fixing.")
    return gaps


def _contrarian_resolution_gaps(state: DebugGraphState) -> list[str]:
    gaps: list[str] = []
    queue = state.investigation_contract.candidate_queue
    if len(queue) < 2:
        return gaps
    non_primary = [
        candidate
        for candidate in queue
        if candidate.candidate_id != state.investigation_contract.primary_candidate_id
    ]
    if not any(candidate.status in {CandidateStatus.RULED_OUT, CandidateStatus.DEPRIORITIZED} for candidate in non_primary):
        gaps.append("At least one non-primary competing candidate must be ruled out or deprioritized before fixing.")
    return gaps
```

- [ ] **Step 4: Consume the helpers in investigation and fixing**

In `InvestigatingNode.run()`, before `return FixingNode()`, insert:

```python
            contract_gaps = _minimum_contract_gaps(ctx.state)
            contract_gaps.extend(_contrarian_resolution_gaps(ctx.state))
            if contract_gaps:
                return _await_input(
                    ctx.state,
                    _format_checklist(
                        "Root cause exists, but the investigation contract is not yet sufficient to enter fixing.",
                        contract_gaps,
                        intro="Resolve these contract gaps before moving into fixing:",
                    ),
                )
```

In `_sync_root_cause_mode(state)`, make sure contract mode escalates with repeated failures:

```python
    if state.resolution.agent_fail_count >= 2:
        state.investigation_contract.investigation_mode = InvestigationMode.ROOT_CAUSE
        if not state.investigation_contract.escalation_reason:
            state.investigation_contract.escalation_reason = "two verification failures"
```

- [ ] **Step 5: Run the graph regression suite**

Run:

```bash
uv run pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: enforce dual observer contract gates"
```

---

### Task 5: Align CLI output and generated `sp-debug` surfaces

**Files:**
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `templates/debug.md`
- Modify: `templates/commands/debug.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/test_debug_cli.py`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add the failing CLI test for `Causal Map` rendering**

In `tests/test_debug_cli.py`, add:

```python
def test_debug_checkpoint_renders_causal_map_section(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.INVESTIGATING
        state.causal_map_completed = True
        state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
        state.causal_map.family_coverage = [
            "truth_owner_logic",
            "cache_snapshot",
            "projection_render",
        ]
        state.causal_map.break_edges = [
            "slot ownership update -> queue projection refresh",
        ]
        state.causal_map.adjacent_risk_targets = [
            {
                "target": "release-retry-loop",
                "reason": "Retry admission also depends on slot ownership",
                "family": "truth_owner_logic",
                "scope": "nearest-neighbor",
                "falsifier": "Retry admission bypasses slot ownership state",
            }
        ]
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "dual-observer")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "queue badge remains non-zero"])

    assert result.exit_code == 0
    assert "causal map" in result.stdout.lower()
    assert "family coverage" in result.stdout.lower()
    assert "release-retry-loop" in result.stdout.lower()
```

- [ ] **Step 2: Run the CLI test to verify it fails**

Run:

```bash
uv run pytest tests/test_debug_cli.py::test_debug_checkpoint_renders_causal_map_section -q
```

Expected: FAIL because the current CLI does not print a `Causal Map` section.

- [ ] **Step 3: Render the new section in `debug cli`**

In `src/specify_cli/debug/cli.py`, add a helper above the existing `Observer Framing` printer:

```python
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
            console.print(f"  - {target.target} ({target.scope})")
```

Then call `_print_causal_map_summary(state)` immediately before `_print_observer_framing_summary(state)`.

- [ ] **Step 4: Update the generated debug contract and session template**

In `templates/commands/debug.md`, add these exact phrases:

```markdown
- **Stage 1A: Causal Map**: The first subagent builds a family-spanning causal map before contract generation begins.
- **Stage 1B: Investigation Contract**: The second subagent converts the causal map into the minimum contract the investigator must consume.
- **Family coverage is the quality bar**: Observer framing is not complete until the causal map spans enough failure families and each family includes a falsifier.
```

In `templates/debug.md`, add a new `## Causal Map` section directly before `## Observer Framing`:

```markdown
## Causal Map

symptom_anchor: [where the symptom first appears]
closed_loop_path:
  - [input event]
  - [control decision]
  - [truth owner update]
  - [projection refresh]
  - [external observation]
break_edges:
  - [where the loop most likely breaks]
bypass_paths:
  - [cache or projection bypass]
family_coverage:
  - [truth_owner_logic | cache_snapshot | projection_render]
candidates:
  - candidate_id: [stable candidate id]
    family: [failure family]
    candidate: [concise hypothesis]
    falsifier: [key disconfirming signal]
adjacent_risk_targets:
  - target: [nearest-neighbor risk]
    reason: [why it is related]
    family: [failure family]
    scope: [nearest-neighbor | broader-family]
    falsifier: [what would disconfirm the risk]
```

- [ ] **Step 5: Update generated integration guidance**

In `src/specify_cli/integrations/base.py`, extend the existing `sp-debug` guidance block with:

```python
            "- If Gathering returns `think_subagent_prompt`, use it for the causal-map subagent and do not improvise the contract yet.\n"
            "- If Gathering returns `contract_subagent_prompt`, use it for the contract-planner subagent and feed its result back into observer_framing, transition_memo, and investigation_contract.\n"
            "- Treat the causal-map output as Stage 1A and the contract-planner output as Stage 1B. Investigation starts only after both stages are complete.\n"
```

- [ ] **Step 6: Run the surface-alignment tests**

Run:

```bash
uv run pytest tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/specify_cli/debug/cli.py templates/debug.md templates/commands/debug.md src/specify_cli/integrations/base.py tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: align debug surfaces with dual observer workflow"
```

---

### Task 6: Run the full debug regression and ship the feature branch cleanly

**Files:**
- Verify only: debug runtime, templates, and integration tests touched above

- [ ] **Step 1: Run the focused debug suite**

Run:

```bash
uv run pytest tests/test_debug_persistence.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_cli.py tests/test_debug_template_guidance.py -q
```

Expected: PASS

- [ ] **Step 2: Run the generated-surface regression**

Run:

```bash
uv run pytest tests/test_extension_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS

- [ ] **Step 3: Review the final diff**

Run:

```bash
git diff --stat HEAD~5..HEAD
git diff -- src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py src/specify_cli/debug/think_agent.py src/specify_cli/debug/contract_agent.py src/specify_cli/debug/graph.py src/specify_cli/debug/cli.py templates/debug.md templates/commands/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md src/specify_cli/integrations/base.py
```

Expected: Only dual-observer runtime, template, and integration-guidance changes.

- [ ] **Step 4: Create the final integration commit**

```bash
git add src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py src/specify_cli/debug/think_agent.py src/specify_cli/debug/contract_agent.py src/specify_cli/debug/graph.py src/specify_cli/debug/cli.py templates/debug.md templates/commands/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md src/specify_cli/integrations/base.py tests/test_debug_persistence.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_cli.py tests/test_debug_template_guidance.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: implement sp-debug dual observer workflow"
```
