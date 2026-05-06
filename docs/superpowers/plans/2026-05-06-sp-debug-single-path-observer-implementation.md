# sp-debug Single-Path Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `sp-debug`'s multi-branch observer entry with a single mandatory intake contract that always produces `causal map`, `investigation contract`, and `log investigation plan` before evidence collection or fixing.

**Architecture:** Implement the redesign in vertical slices. First lock the new single-path contract into prompt, parser, and graph tests so the old branches cannot silently survive. Then converge the template surfaces and prompt helpers, reshape the schema and persistence layer around the three first-class intake artifacts with legacy-session migration, and finally simplify the graph and CLI/reporting surfaces to match the new contract.

**Tech Stack:** Python 3.13, Typer CLI, Pydantic models, pytest, Markdown workflow templates, YAML-backed debug persistence.

---

## Context

Read these before starting implementation:

- [2026-05-06-sp-debug-single-path-observer-design.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/docs/superpowers/specs/2026-05-06-sp-debug-single-path-observer-design.md)
- [templates/commands/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/commands/debug.md)
- [templates/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/debug.md)
- [templates/worker-prompts/debug-thinker.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-thinker.md)
- [templates/worker-prompts/debug-contract-planner.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-contract-planner.md)
- [src/specify_cli/debug/think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/think_agent.py)
- [src/specify_cli/debug/contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/contract_agent.py)
- [src/specify_cli/debug/schema.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/schema.py)
- [src/specify_cli/debug/graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/graph.py)
- [src/specify_cli/debug/persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/persistence.py)
- [src/specify_cli/debug/cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/cli.py)
- [tests/test_debug_template_guidance.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_template_guidance.py)
- [tests/test_debug_think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_think_agent.py)
- [tests/test_debug_contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_contract_agent.py)
- [tests/test_debug_persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_persistence.py)
- [tests/test_debug_graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph.py)
- [tests/test_debug_graph_nodes.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph_nodes.py)
- [tests/test_debug_cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_cli.py)

Keep these implementation decisions stable across all tasks:

- Fresh sessions must not expose `fast-path`, `compressed observer framing`, or optional/user-declinable expanded observer behavior.
- The canonical intake artifacts are:
  - `causal_map`
  - `investigation_contract`
  - `log_investigation_plan`
- The canonical intake completion fields are:
  - `causal_map_completed`
  - `investigation_contract_completed`
  - `log_investigation_plan_completed`
- `observer_framing_completed` becomes a derived gate, not a shortcut flag.
- Legacy session compatibility uses `read old / normalize to new / block unsafe legacy resume`.

## File Structure

Modify:

- [templates/commands/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/commands/debug.md) - remove early observer branches and document the fixed intake contract.
- [templates/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/debug.md) - replace old frontmatter/sections with canonical intake completion fields and a dedicated `Log Investigation Plan` section.
- [templates/worker-prompts/debug-thinker.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-thinker.md) - emit a single full causal-map package with `dimension_scan` and `candidate_board`.
- [templates/worker-prompts/debug-contract-planner.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-contract-planner.md) - consume the causal map and emit `observer_framing`, `transition_memo`, `investigation_contract`, and `log_investigation_plan`.
- [src/specify_cli/debug/think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/think_agent.py) - keep the prompt builder simple but align parser expectations with the new thinker payload.
- [src/specify_cli/debug/contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/contract_agent.py) - stop passing/expecting `expanded_observer` and align the planner payload with canonical intake artifacts.
- [src/specify_cli/debug/schema.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/schema.py) - promote intake-completion fields, add top-level `log_investigation_plan`, move `dimension_scan` and `candidate_board` under `CausalMapState`, and add a legacy re-intake blocker flag.
- [src/specify_cli/debug/persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/persistence.py) - save/load the canonical intake state, migrate legacy sections, and render reports from the normalized log-plan surface.
- [src/specify_cli/debug/graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/graph.py) - remove fast-path/compressed/expanded-observer branches, enforce the fixed intake gate, and keep repeated-failure escalation in downstream investigation only.
- [src/specify_cli/debug/cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/cli.py) - print the canonical intake state without the old mode/compression/expanded-observer vocabulary.
- [tests/test_debug_template_guidance.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_template_guidance.py) - lock the command and session template contract.
- [tests/test_debug_think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_think_agent.py) - lock thinker prompt and parser output against the new Stage 1A contract.
- [tests/test_debug_contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_contract_agent.py) - lock planner prompt and parser output against the new Stage 1B contract.
- [tests/test_debug_persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_persistence.py) - round-trip the new canonical session shape and legacy-session normalization.
- [tests/test_debug_graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph.py) - lock the fixed intake sequence and downstream escalation semantics.
- [tests/test_debug_graph_nodes.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph_nodes.py) - lock node-level intake gating and legacy re-intake blocking.
- [tests/test_debug_cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_cli.py) - lock checkpoint output against the new intake/report surface.

Do not modify `README.md` or `PROJECT-HANDBOOK.md` in this change. The current repo docs reference `sp-debug` generically but do not describe the old observer-mode branches, so the contract change is fully contained in the workflow/runtime surfaces above.

## Naming Rules

Use these names consistently:

- `causal_map_completed`
- `investigation_contract_completed`
- `log_investigation_plan_completed`
- `observer_framing_completed`
- `legacy_session_needs_reintake`
- `log_investigation_plan`
- `dimension_scan`
- `candidate_board`
- `top_candidates`

Use these status values consistently:

- `investigation_mode`: `normal`, `root_cause`
- `log_readiness`: `unknown`, `sufficient_existing_logs`, `insufficient_need_instrumentation`, `user_must_provide_logs`
- `human_verification_outcome`: `pending`, `passed`, `same_issue`, `derived_issue`, `unrelated_issue`, `insufficient_feedback`

Do not reintroduce these names in fresh-session semantics:

- `observer_mode`
- `skip_observer_reason`
- `observer_expansion_status`
- `observer_expansion_reason`
- `expanded_observer`

---

### Task 1: Lock the new single-path intake contract into prompt and parser tests

**Files:**
- Modify: [tests/test_debug_template_guidance.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_template_guidance.py)
- Modify: [tests/test_debug_think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_think_agent.py)
- Modify: [tests/test_debug_contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_contract_agent.py)

- [ ] **Step 1: Rewrite the template-guidance assertions around the single-path contract**

Replace the old branch-oriented assertions in `tests/test_debug_template_guidance.py` with checks like these:

```python
def test_debug_template_documents_single_path_intake_contract() -> None:
    content = read_template("templates/commands/debug.md").lower()

    assert "stage 1a: causal map" in content
    assert "stage 1b: investigation contract + log investigation plan" in content
    assert "causal_map_completed" in content
    assert "investigation_contract_completed" in content
    assert "log_investigation_plan_completed" in content
    assert "do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing" in content
    assert "fast-path gate" not in content
    assert "compressed observer framing" not in content
    assert "optional expanded observer" not in content
    assert "user can agree or decline" not in content


def test_debug_session_template_uses_canonical_intake_fields() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8")

    assert "investigation_contract_completed:" in content
    assert "log_investigation_plan_completed:" in content
    assert "legacy_session_needs_reintake:" in content
    assert "## Log Investigation Plan" in content
    assert "observer_mode:" not in content
    assert "skip_observer_reason:" not in content
    assert "## Expanded Observer" not in content
```

- [ ] **Step 2: Rewrite the thinker tests around Stage 1A-only output**

Replace the old `expanded_observer` and `observer_mode` expectations in `tests/test_debug_think_agent.py` with tests like these:

```python
def test_prompt_contains_stage_1a_output_shape() -> None:
    state = DebugGraphState(
        slug="test-session",
        trigger="queue badge remains non-zero after slot release",
        diagnostic_profile="scheduler-admission",
    )

    prompt = build_think_subagent_prompt(state)

    assert "causal_map:" in prompt
    assert "dimension_scan:" in prompt
    assert "candidate_board:" in prompt
    assert "log_investigation_plan:" not in prompt
    assert "observer_mode:" not in prompt
    assert "expanded_observer:" not in prompt


def test_parse_think_subagent_result_extracts_dimension_scan_and_candidate_board() -> None:
    raw = """Observer analysis.

---
causal_map:
  symptom_anchor: "UI queue badge remains non-zero"
  closed_loop_path:
    - "job release event"
    - "scheduler admission decision"
  family_coverage:
    - "truth_owner_logic"
    - "projection_render"
    - "cache_snapshot"
  dimension_scan:
    symptom_layer: "UI queue badge"
    truth_owner_or_business_layer: "Scheduler slot ownership"
  candidate_board:
    - candidate_id: "cand-slot-ownership"
      dimension_origin: "truth_owner_or_business_layer"
      family: "truth_owner_logic"
      candidate: "Scheduler does not clear slot ownership on release"
      light_scores:
        likelihood: 4
        impact_radius: 4
        falsifiability: 3
        log_observability: 2
"""

    result = parse_think_subagent_result(raw)

    assert result["causal_map"]["dimension_scan"]["symptom_layer"] == "UI queue badge"
    assert result["causal_map"]["candidate_board"][0]["candidate_id"] == "cand-slot-ownership"
    assert "log_investigation_plan" not in result
```

- [ ] **Step 3: Rewrite the planner tests around Stage 1B output**

Update `tests/test_debug_contract_agent.py` to expect a top-level `log_investigation_plan` and no `expanded_observer` payload:

```python
def test_build_contract_subagent_prompt_uses_canonical_intake_payload() -> None:
    state = DebugGraphState(slug="test-session", trigger="queue badge remains non-zero")
    state.project_runtime_profile = "full-stack/web-app"
    state.symptom_shape = "phenomenon_only"
    state.log_readiness = "unknown"
    state.causal_map.symptom_anchor = "UI queue badge remains non-zero"
    state.causal_map.family_coverage = [
        "truth_owner_logic",
        "cache_snapshot",
        "projection_render",
    ]
    state.causal_map.dimension_scan.truth_owner_or_business_layer = "Scheduler owns slot state"
    state.causal_map.candidate_board = [
        ExpandedObserverCandidateBoardEntry(
            candidate_id="cand-slot-ownership",
            dimension_origin="truth_owner_or_business_layer",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
        )
    ]

    prompt = build_contract_subagent_prompt(state)

    assert "expanded_observer:" not in prompt
    assert "observer_expansion_status" not in prompt
    assert "log_investigation_plan:" in prompt
    assert "candidate_board:" in prompt


def test_parse_contract_subagent_result_extracts_log_plan_top_level() -> None:
    raw = """Use runtime logs before fixing.

---
observer_framing:
  summary: "Queue badge is downstream of scheduler state"
transition_memo:
  first_candidate_to_test: "cand-slot-ownership"
investigation_contract:
  primary_candidate_id: "cand-slot-ownership"
  investigation_mode: "normal"
  candidate_queue:
    - candidate_id: "cand-slot-ownership"
      candidate: "Scheduler does not clear slot ownership on release"
      family: "truth_owner_logic"
      status: "pending"
log_investigation_plan:
  existing_log_targets:
    - "application runtime logs for the failing request window"
  candidate_signal_map:
    - candidate_id: "cand-slot-ownership"
      signals:
        - "release recorded without ownership clear"
"""

    data = parse_contract_subagent_result(raw)

    assert data["investigation_contract"]["primary_candidate_id"] == "cand-slot-ownership"
    assert data["log_investigation_plan"]["existing_log_targets"][0] == "application runtime logs for the failing request window"
```

- [ ] **Step 4: Run the prompt/parser test slice to verify RED**

Run:

```powershell
uv run --extra test pytest tests/test_debug_template_guidance.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py -q
```

Expected: FAIL because the command template, session template, thinker prompt, planner prompt, and helper payloads still expose the old observer-mode and expanded-observer contract.

- [ ] **Step 5: Commit the RED tests**

Run:

```bash
git add tests/test_debug_template_guidance.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py
git commit -m "test: lock sp-debug single-path intake contract"
```

### Task 2: Converge the template and prompt surfaces on the canonical intake artifacts

**Files:**
- Modify: [templates/commands/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/commands/debug.md)
- Modify: [templates/debug.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/debug.md)
- Modify: [templates/worker-prompts/debug-thinker.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-thinker.md)
- Modify: [templates/worker-prompts/debug-contract-planner.md](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/templates/worker-prompts/debug-contract-planner.md)
- Modify: [src/specify_cli/debug/think_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/think_agent.py)
- Modify: [src/specify_cli/debug/contract_agent.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/contract_agent.py)

- [ ] **Step 1: Rewrite `templates/commands/debug.md` to teach one intake path**

Replace the old fast-path, compressed, and optional-expanded-observer wording with a section like this:

```markdown
## Mandatory Intake Contract

All new `sp-debug` sessions follow this fixed intake path:

`Stage 1A Causal Map -> Stage 1B Investigation Contract + Log Investigation Plan -> Evidence Investigation -> Fixing -> Verifying -> Human Verify`

Do not enter reproduction, log review, test inspection, source-code reads, evidence collection, or fixing until the session records all of the following:

- `causal_map_completed: true`
- `investigation_contract_completed: true`
- `log_investigation_plan_completed: true`
- `observer_framing_completed: true`

Repeated failure does not reopen observer-shape choices. It upgrades downstream investigation strength only, including `root_cause` mode and stronger instrumentation requirements.
```

Delete the `Fast-Path Gate` section and any instruction that mentions `compressed observer framing`, `observer_mode`, optional expanded observer, or a user-decline branch.

- [ ] **Step 2: Rewrite `templates/debug.md` to match the canonical session shape**

Update the frontmatter and sections in `templates/debug.md` so they use the new fields and canonical sections:

```markdown
---
slug: [session slug]
status: gathering | investigating | fixing | verifying | awaiting_human_verify | resolved
trigger: "[verbatim user input]"
diagnostic_profile: scheduler-admission | cache-snapshot | ui-projection | general
causal_map_completed: [true only after the Stage 1A causal map is written]
investigation_contract_completed: [true only after the Stage 1B contract planner finishes]
log_investigation_plan_completed: [true only after the Stage 1B log plan is written]
observer_framing_completed: [true only after the canonical intake package is complete]
framing_gate_passed: [true only after family coverage, candidate queue, and related-risk gate checks pass]
legacy_session_needs_reintake: [true only when a resumed legacy session cannot satisfy the new intake contract safely]
waiting_on_child_human_followup: [true when a parent session is blocked on a derived child issue]
atlas_read_completed: [true only after the atlas gate is complete]
current_node_id: [ID of the active graph node]
created: [ISO timestamp]
updated: [ISO timestamp]
---
```

Also add a dedicated `## Log Investigation Plan` section and remove the `## Expanded Observer` section entirely.

- [ ] **Step 3: Rewrite the thinker and planner prompts to match Stage 1A and Stage 1B**

Use these exact output shapes in the prompt examples.

For `templates/worker-prompts/debug-thinker.md`:

```yaml
causal_map:
  symptom_anchor: "UI queue badge remains non-zero"
  closed_loop_path:
    - "job release event"
    - "scheduler admission decision"
    - "slot ownership update"
    - "queue projection refresh"
    - "UI queue badge render"
  break_edges:
    - "slot ownership update -> queue projection refresh"
  family_coverage:
    - "truth_owner_logic"
    - "cache_snapshot"
    - "projection_render"
  dimension_scan:
    symptom_layer: "UI queue badge"
    truth_owner_or_business_layer: "Scheduler slot ownership"
  candidate_board:
    - candidate_id: "cand-slot-ownership"
      dimension_origin: "truth_owner_or_business_layer"
      family: "truth_owner_logic"
      candidate: "Scheduler does not clear slot ownership on release"
      light_scores:
        likelihood: 4
        impact_radius: 4
        falsifiability: 3
        log_observability: 2
```

For `templates/worker-prompts/debug-contract-planner.md`:

```yaml
observer_framing:
  summary: "Queue badge is downstream of scheduler state"
  primary_suspected_loop: "scheduler-admission"
transition_memo:
  first_candidate_to_test: "cand-slot-ownership"
  why_first: "Scheduler slot ownership is the earliest truth owner in the loop."
investigation_contract:
  primary_candidate_id: "cand-slot-ownership"
  investigation_mode: "normal"
  candidate_queue:
    - candidate_id: "cand-slot-ownership"
      candidate: "Scheduler does not clear slot ownership on release"
      family: "truth_owner_logic"
      status: "pending"
  top_candidates:
    - candidate_id: "cand-slot-ownership"
      family: "truth_owner_logic"
      investigation_priority: 1
      recommended_log_probe: "Check release and admission logs in the same request window"
log_investigation_plan:
  existing_log_targets:
    - "application runtime logs for the failing request window"
  candidate_signal_map:
    - candidate_id: "cand-slot-ownership"
      signals:
        - "release recorded without ownership clear"
```

The thinker prompt must no longer mention `observer_mode`, `observer_expansion_status`, `observer_expansion_reason`, or `expanded_observer:`.

- [ ] **Step 4: Align the helper payload builders with the new prompt contract**

Update `src/specify_cli/debug/contract_agent.py` so it passes only canonical data:

```python
def build_contract_subagent_prompt(state: DebugGraphState) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = yaml.safe_dump(
        {
            "trigger": state.trigger,
            "diagnostic_profile": state.diagnostic_profile or "general",
            "project_runtime_profile": _enum_value(state.project_runtime_profile),
            "symptom_shape": _enum_value(state.symptom_shape),
            "log_readiness": _enum_value(state.log_readiness),
            "causal_map": state.causal_map.model_dump(mode="json"),
        },
        allow_unicode=True,
        sort_keys=False,
    )
    return template.replace("{CAUSAL_MAP_PAYLOAD}", payload)
```

Keep `src/specify_cli/debug/think_agent.py` simple: only prompt text and `parse_think_subagent_result()` need alignment with the new YAML shape, not additional runtime logic.

- [ ] **Step 5: Run the prompt/parser slice to verify GREEN**

Run:

```powershell
uv run --extra test pytest tests/test_debug_template_guidance.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the template/prompt slice**

Run:

```bash
git add templates/commands/debug.md templates/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md src/specify_cli/debug/think_agent.py src/specify_cli/debug/contract_agent.py tests/test_debug_template_guidance.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py
git commit -m "feat: define canonical sp-debug intake contract"
```

### Task 3: Reshape the schema and persistence layer around canonical intake artifacts

**Files:**
- Modify: [src/specify_cli/debug/schema.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/schema.py)
- Modify: [src/specify_cli/debug/persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/persistence.py)
- Modify: [tests/test_debug_persistence.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_persistence.py)

- [ ] **Step 1: Add failing persistence tests for the canonical session shape and legacy migration**

Add these tests to `tests/test_debug_persistence.py`:

```python
def test_persistence_round_trips_canonical_intake_state(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="roundtrip")
    state.causal_map_completed = True
    state.investigation_contract_completed = True
    state.log_investigation_plan_completed = True
    state.observer_framing_completed = True
    state.causal_map.dimension_scan.truth_owner_or_business_layer = "Scheduler slot ownership"
    state.causal_map.candidate_board = [
        ExpandedObserverCandidateBoardEntry(
            candidate_id="cand-slot-ownership",
            dimension_origin="truth_owner_or_business_layer",
            family="truth_owner_logic",
            candidate="Scheduler does not clear slot ownership on release",
        )
    ]
    state.log_investigation_plan.existing_log_targets = [
        "application runtime logs for the failing request window"
    ]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.investigation_contract_completed is True
    assert restored.log_investigation_plan_completed is True
    assert restored.causal_map.dimension_scan.truth_owner_or_business_layer == "Scheduler slot ownership"
    assert restored.log_investigation_plan.existing_log_targets == [
        "application runtime logs for the failing request window"
    ]


def test_load_normalizes_legacy_expanded_observer_session(tmp_path: Path) -> None:
    session = tmp_path / "legacy.md"
    session.write_text(
        \"\"\"---
slug: legacy
status: gathering
trigger: "legacy session"
causal_map_completed: true
contract_generation_completed: true
observer_mode: compressed
observer_framing_completed: true
created: "2026-05-06T00:00:00"
updated: "2026-05-06T00:00:00"
---

## Causal Map
symptom_anchor: "UI queue badge remains non-zero"

## Expanded Observer
log_investigation_plan:
  existing_log_targets:
    - "application runtime logs for the failing request window"
\"\"\",
        encoding="utf-8",
    )

    restored = MarkdownPersistenceHandler(tmp_path).load(session)

    assert restored.investigation_contract_completed is True
    assert restored.log_investigation_plan.existing_log_targets == [
        "application runtime logs for the failing request window"
    ]
    assert restored.legacy_session_needs_reintake is True
```

- [ ] **Step 2: Rewrite `DebugGraphState` and `CausalMapState` around the canonical intake model**

Update `src/specify_cli/debug/schema.py` with fields like these:

```python
class CausalMapState(BaseModel):
    symptom_anchor: Optional[str] = None
    closed_loop_path: List[str] = Field(default_factory=list)
    break_edges: List[str] = Field(default_factory=list)
    bypass_paths: List[str] = Field(default_factory=list)
    family_coverage: List[str] = Field(default_factory=list)
    candidates: List[CausalMapCandidate] = Field(default_factory=list)
    adjacent_risk_targets: List[CausalMapRiskTarget] = Field(default_factory=list)
    dimension_scan: ExpandedObserverDimensionScan = Field(default_factory=ExpandedObserverDimensionScan)
    candidate_board: List[ExpandedObserverCandidateBoardEntry] = Field(default_factory=list)


class DebugGraphState(BaseModel):
    slug: str
    status: DebugStatus = DebugStatus.GATHERING
    trigger: str
    diagnostic_profile: Optional[str] = None
    causal_map_completed: bool = False
    investigation_contract_completed: bool = False
    log_investigation_plan_completed: bool = False
    observer_framing_completed: bool = False
    framing_gate_passed: bool = False
    legacy_session_needs_reintake: bool = False
    project_runtime_profile: Optional[ProjectRuntimeProfile] = None
    symptom_shape: Optional[SymptomShape] = None
    log_readiness: Optional[LogReadiness] = None
    log_investigation_plan: LogInvestigationPlanState = Field(default_factory=LogInvestigationPlanState)
```

Remove `observer_mode`, `skip_observer_reason`, `observer_expansion_status`, `observer_expansion_reason`, and `expanded_observer` from fresh-session state.

- [ ] **Step 3: Add a persistence migration helper that reads old fields and writes the new shape**

Add a helper like this to `src/specify_cli/debug/persistence.py`:

```python
def _normalize_legacy_debug_payload(frontmatter: dict[str, Any], sections: dict[str, Any]) -> dict[str, Any]:
    investigation_contract_section = sections.get("Investigation Contract") or {}
    expanded_section = sections.get("Expanded Observer") or {}
    canonical_log_plan = (
        sections.get("Log Investigation Plan")
        or investigation_contract_section.get("log_investigation_plan")
        or expanded_section.get("log_investigation_plan")
        or {}
    )

    legacy_branch_markers = any(
        (
            frontmatter.get("observer_mode"),
            frontmatter.get("skip_observer_reason"),
            frontmatter.get("observer_expansion_status"),
            frontmatter.get("observer_expansion_reason"),
            sections.get("Expanded Observer"),
        )
    )

    return {
        "investigation_contract_completed": frontmatter.get(
            "investigation_contract_completed",
            frontmatter.get("contract_generation_completed", False),
        ),
        "log_investigation_plan_completed": frontmatter.get(
            "log_investigation_plan_completed",
            bool(canonical_log_plan),
        ),
        "log_investigation_plan": canonical_log_plan,
        "legacy_session_needs_reintake": legacy_branch_markers,
    }
```

Use that helper in `load()`, and save the new canonical sections with:

```python
("Log Investigation Plan", state.log_investigation_plan.model_dump(mode="json"))
```

instead of `("Expanded Observer", ...)`.

- [ ] **Step 4: Run the persistence tests to verify GREEN**

Run:

```powershell
uv run --extra test pytest tests/test_debug_persistence.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the schema/persistence slice**

Run:

```bash
git add src/specify_cli/debug/schema.py src/specify_cli/debug/persistence.py tests/test_debug_persistence.py
git commit -m "feat: normalize sp-debug intake state"
```

### Task 4: Remove the observer-branch runtime logic and enforce the fixed intake gate

**Files:**
- Modify: [src/specify_cli/debug/graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/graph.py)
- Modify: [tests/test_debug_graph.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph.py)
- Modify: [tests/test_debug_graph_nodes.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_graph_nodes.py)

- [ ] **Step 1: Add failing graph tests for the fixed intake sequence**

Add tests like these to `tests/test_debug_graph.py` and `tests/test_debug_graph_nodes.py`:

```python
@pytest.mark.asyncio
async def test_gathering_requests_causal_map_before_any_other_intake_artifact() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "Causal map needed" in (state.current_focus.next_action or "")
    assert "observer_mode" not in (state.current_focus.next_action or "")


@pytest.mark.asyncio
async def test_gathering_blocks_until_log_plan_completion() -> None:
    state = DebugGraphState(slug="test", trigger="queue stuck")
    state.symptoms.expected = "queue drains"
    state.symptoms.actual = "queue remains non-empty"
    state.symptoms.reproduction_verified = True
    state.causal_map_completed = True
    state.investigation_contract_completed = True
    state.log_investigation_plan_completed = False

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "log investigation plan" in (state.current_focus.next_action or "").lower()


@pytest.mark.asyncio
async def test_gathering_blocks_unsafe_legacy_resume_until_reintake() -> None:
    state = DebugGraphState(slug="legacy", trigger="legacy session")
    state.legacy_session_needs_reintake = True

    result = await GatheringNode().run(GraphRunContext(state=state, deps=None))

    assert result.data == "Awaiting more debugging input"
    assert "legacy-session-needs-reintake" in (state.current_focus.next_action or "")
```

- [ ] **Step 2: Delete the old front-half branch helpers and add a canonical intake-sync helper**

In `src/specify_cli/debug/graph.py`, remove:

- `_suggest_expanded_observer_if_needed`
- `_expanded_observer_confirmation_needed`
- `_expanded_observer_confirmation_message`
- `_strong_low_level_evidence_present`
- compressed/full framing count branches based on `observer_mode`

Add helpers like these instead:

```python
def _sync_intake_completion(state: DebugGraphState) -> None:
    state.observer_framing_completed = (
        state.causal_map_completed
        and state.investigation_contract_completed
        and state.log_investigation_plan_completed
    )


def _legacy_reintake_message(state: DebugGraphState) -> str:
    return (
        "legacy-session-needs-reintake: this resumed session predates the canonical intake contract.\n"
        "- Re-run Stage 1A causal mapping.\n"
        "- Re-run Stage 1B contract and log-plan generation.\n"
        "- Do not resume evidence collection or fixing until the canonical intake artifacts are rewritten."
    )
```

- [ ] **Step 3: Rewrite `GatheringNode` to enforce the canonical sequence**

Use logic like this inside `GatheringNode.run()`:

```python
if ctx.state.legacy_session_needs_reintake:
    return _await_input(ctx.state, _legacy_reintake_message(ctx.state))

if not ctx.state.causal_map_completed:
    ctx.state.think_subagent_prompt = build_think_subagent_prompt(ctx.state)
    return _await_input(
        ctx.state,
        "Causal map needed. Spawn a think subagent with think_subagent_prompt. "
        "Parse the YAML after '---', populate `causal_map`, set `causal_map_completed=True`, and continue.",
    )

if not ctx.state.investigation_contract_completed or not ctx.state.log_investigation_plan_completed:
    ctx.state.contract_subagent_prompt = build_contract_subagent_prompt(ctx.state)
    return _await_input(
        ctx.state,
        "Investigation contract and log investigation plan needed. Spawn a contract subagent with contract_subagent_prompt. "
        "Populate `observer_framing`, `transition_memo`, `investigation_contract`, and `log_investigation_plan`, then set "
        "`investigation_contract_completed=True` and `log_investigation_plan_completed=True` before continuing.",
    )

_sync_intake_completion(ctx.state)
```

Also update `_framing_gate_gaps()` to require the full counts unconditionally:

```python
required_candidate_count = 3
required_family_count = 3
```

- [ ] **Step 4: Keep repeated-failure escalation in downstream investigation only**

Update `_sync_root_cause_mode()` so the escalation stays in the back half:

```python
def _sync_root_cause_mode(state: DebugGraphState) -> None:
    if state.resolution.agent_fail_count >= 2:
        state.investigation_contract.investigation_mode = InvestigationMode.ROOT_CAUSE
        state.investigation_contract.escalation_reason = "two verification failures"
```

Do not add any code that reopens observer-shape selection after repeated failure.

- [ ] **Step 5: Run the graph tests to verify GREEN**

Run:

```powershell
uv run --extra test pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the graph slice**

Run:

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: enforce canonical sp-debug intake flow"
```

### Task 5: Update CLI/reporting surfaces and run the targeted regression matrix

**Files:**
- Modify: [src/specify_cli/debug/cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/src/specify_cli/debug/cli.py)
- Modify: [tests/test_debug_cli.py](/F:/github/spec-kit-plus/.worktrees/sp-specify-fixed-heavy-discovery/tests/test_debug_cli.py)

- [ ] **Step 1: Add failing CLI assertions for the canonical intake summary**

Update `tests/test_debug_cli.py` with checks like these:

```python
def test_debug_prints_canonical_intake_summary(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.INVESTIGATING
        state.causal_map_completed = True
        state.investigation_contract_completed = True
        state.log_investigation_plan_completed = True
        state.observer_framing_completed = True
        state.project_runtime_profile = "full-stack/web-app"
        state.log_readiness = "unknown"
        state.log_investigation_plan.existing_log_targets = [
            "application runtime logs for the failing request window"
        ]
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "checkpoint-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "log investigation plan" in result.stdout.lower()
    assert "application runtime logs for the failing request window" in result.stdout.lower()
    assert "compression reason" not in result.stdout.lower()
    assert "observer expansion status" not in result.stdout.lower()
```

- [ ] **Step 2: Replace the old CLI mode/expanded-observer summary with canonical intake/report sections**

Update `src/specify_cli/debug/cli.py` so the observer summary prints only canonical information:

```python
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
    if observer.summary:
        console.print(f"- Summary: {observer.summary}")
    if observer.primary_suspected_loop:
        console.print(f"- Primary suspected loop: {observer.primary_suspected_loop}")
    if observer.suspected_owning_layer:
        console.print(f"- Suspected owning layer: {observer.suspected_owning_layer}")
```

Then replace `_print_expanded_observer_summary()` with a canonical log-plan summary:

```python
def _print_log_investigation_plan_summary(state: DebugGraphState) -> None:
    plan = state.log_investigation_plan
    if not any(
        (
            state.project_runtime_profile,
            state.symptom_shape,
            state.log_readiness,
            state.investigation_contract.top_candidates,
            plan.existing_log_targets,
            plan.candidate_signal_map,
            plan.user_request_packet,
        )
    ):
        return

    console.print("[bold]Log Investigation Plan[/bold]")
    if state.project_runtime_profile:
        console.print(f"- Project runtime profile: {state.project_runtime_profile.value}")
    if state.symptom_shape:
        console.print(f"- Symptom shape: {state.symptom_shape.value}")
    if state.log_readiness:
        console.print(f"- Log readiness: {state.log_readiness.value}")
    if plan.existing_log_targets:
        console.print("- Existing log targets:")
        for target in plan.existing_log_targets:
            console.print(f"  - {target}")
```

- [ ] **Step 3: Run the CLI regression slice to verify GREEN**

Run:

```powershell
uv run --extra test pytest tests/test_debug_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Run the full targeted debug regression matrix**

Run:

```powershell
uv run --extra test pytest tests/test_debug_template_guidance.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py tests/test_debug_persistence.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Confirm that repo-level docs do not need follow-up edits**

Run:

```powershell
rg -n "fast-path gate|compressed observer framing|optional expanded observer|observer expansion status" README.md PROJECT-HANDBOOK.md
```

Expected: no matches. If the command prints nothing, keep `README.md` and `PROJECT-HANDBOOK.md` unchanged in this change.

- [ ] **Step 6: Commit the CLI/final verification slice**

Run:

```bash
git add src/specify_cli/debug/cli.py tests/test_debug_cli.py
git commit -m "feat: align sp-debug cli with canonical intake"
```

---

## Self-Review

### Spec Coverage

- Single-path workflow contract: covered by Tasks 1, 2, and 4.
- Canonical intake state model: covered by Task 3.
- Runtime/graph convergence: covered by Task 4.
- Legacy migration policy: covered by Task 3.
- CLI/reporting alignment: covered by Task 5.

No spec sections are currently uncovered.

### Placeholder Scan

- No `TODO`, `TBD`, or "implement later" placeholders remain.
- Every code-changing step includes concrete code blocks.
- Every verification step includes an exact command and expected outcome.

### Type Consistency

- The plan consistently uses `investigation_contract_completed`, not the old `contract_generation_completed`, for fresh-session logic.
- The plan consistently uses `log_investigation_plan` as a top-level artifact.
- The plan consistently treats `observer_framing_completed` as derived from the three intake completion fields.

