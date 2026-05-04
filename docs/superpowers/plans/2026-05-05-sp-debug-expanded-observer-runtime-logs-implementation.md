# sp-debug Expanded Observer Runtime Logs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an optional expanded observer layer for `sp-debug` plus runtime-log investigation gates so complex runtime bugs widen candidate coverage first and cannot move into fixes without sufficient log evidence or explicit observability escalation.

**Architecture:** Land the feature in vertical slices. First lock the new contract into prompt/template tests so the expanded observer and runtime-log rules are explicit. Then extend debug state and persistence so the new observer/log structures have durable storage and CLI/handoff visibility. After the data model exists, wire the graph/runtime logic for suggestion, user confirmation, runtime-profile classification, and log-readiness gates. Finish by updating worker prompts, user-facing command guidance, and the debug CLI checkpoint output, then run the full targeted debug test matrix.

**Tech Stack:** Python 3.13, Typer CLI, Pydantic models, pytest, Markdown workflow templates, worker prompt templates, Spec Kit debug runtime state machine.

---

## Context

Read before editing:

- [2026-05-05-sp-debug-expanded-observer-runtime-logs-design.md](/F:/github/spec-kit-plus/docs/superpowers/specs/2026-05-05-sp-debug-expanded-observer-runtime-logs-design.md)
- [debug.md](/F:/github/spec-kit-plus/templates/commands/debug.md)
- [debug-thinker.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-thinker.md)
- [debug-contract-planner.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-contract-planner.md)
- [schema.py](/F:/github/spec-kit-plus/src/specify_cli/debug/schema.py)
- [graph.py](/F:/github/spec-kit-plus/src/specify_cli/debug/graph.py)
- [persistence.py](/F:/github/spec-kit-plus/src/specify_cli/debug/persistence.py)
- [cli.py](/F:/github/spec-kit-plus/src/specify_cli/debug/cli.py)
- [think_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/think_agent.py)
- [contract_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/contract_agent.py)
- [test_alignment_templates.py](/F:/github/spec-kit-plus/tests/test_alignment_templates.py)
- [test_debug_template_guidance.py](/F:/github/spec-kit-plus/tests/test_debug_template_guidance.py)
- [test_debug_think_agent.py](/F:/github/spec-kit-plus/tests/test_debug_think_agent.py)
- [test_debug_contract_agent.py](/F:/github/spec-kit-plus/tests/test_debug_contract_agent.py)
- [test_debug_persistence.py](/F:/github/spec-kit-plus/tests/test_debug_persistence.py)
- [test_debug_graph.py](/F:/github/spec-kit-plus/tests/test_debug_graph.py)
- [test_debug_graph_nodes.py](/F:/github/spec-kit-plus/tests/test_debug_graph_nodes.py)
- [test_debug_cli.py](/F:/github/spec-kit-plus/tests/test_debug_cli.py)

Keep these constraints in mind while implementing:

- `standard observer` remains mandatory; do not introduce a skip path that bypasses observer framing entirely.
- `expanded observer` is optional and user-confirmed; it is suggested by the runtime, not enabled by a new required global flag.
- `expanded observer` does not read logs, source code, or tests. It only widens candidates and emits a structured log investigation plan.
- Runtime-log evidence rules apply only to runtime bug investigation flow, not to all debug sessions indiscriminately.
- The implementation must preserve current `full`/`compressed` observer semantics and existing lifecycle-hardening behavior unless the new design explicitly changes them.
- Do not touch unrelated untracked files in the worktree.

## File Structure

Modify:

- [debug.md](/F:/github/spec-kit-plus/templates/commands/debug.md) - add expanded-observer suggestion rules, runtime-profile/log-readiness contract language, and log-insufficiency fix gates.
- [debug-thinker.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-thinker.md) - widen candidate generation, add two-layer scoring output, add project runtime profiling, and emit a log investigation plan while preserving no-log/no-code constraints.
- [debug-contract-planner.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-contract-planner.md) - consume the expanded observer payload and preserve top-candidate/log-plan information in the investigation contract output.
- [schema.py](/F:/github/spec-kit-plus/src/specify_cli/debug/schema.py) - add expanded observer state, runtime profile enums/fields, log-readiness state, score containers, and user log request packet structures.
- [think_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/think_agent.py) - ensure prompt-building and parsing support the richer expanded observer payload.
- [contract_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/contract_agent.py) - pass expanded observer fields into the contract-planner payload and parse any new structured output.
- [graph.py](/F:/github/spec-kit-plus/src/specify_cli/debug/graph.py) - classify runtime bug shape, suggest expanded observer, store user decision, gate fixing on runtime log sufficiency, and generate a user log request packet when needed.
- [persistence.py](/F:/github/spec-kit-plus/src/specify_cli/debug/persistence.py) - persist new fields, render them in session files, research checkpoints, and handoff reports.
- [cli.py](/F:/github/spec-kit-plus/src/specify_cli/debug/cli.py) - surface expanded observer state, runtime profile, top candidates, log readiness, and log-plan summary in checkpoint output.
- [test_alignment_templates.py](/F:/github/spec-kit-plus/tests/test_alignment_templates.py) - lock the shared debug template and prompt contract changes.
- [test_debug_template_guidance.py](/F:/github/spec-kit-plus/tests/test_debug_template_guidance.py) - assert the new command-level workflow guidance.
- [test_debug_think_agent.py](/F:/github/spec-kit-plus/tests/test_debug_think_agent.py) - cover prompt content/parsing for expanded observer outputs.
- [test_debug_contract_agent.py](/F:/github/spec-kit-plus/tests/test_debug_contract_agent.py) - cover contract-planner payloads that include expanded observer/log-plan data.
- [test_debug_persistence.py](/F:/github/spec-kit-plus/tests/test_debug_persistence.py) - round-trip and handoff coverage for new state fields.
- [test_debug_graph.py](/F:/github/spec-kit-plus/tests/test_debug_graph.py) - cover high-level suggestion and runtime-log gate behavior.
- [test_debug_graph_nodes.py](/F:/github/spec-kit-plus/tests/test_debug_graph_nodes.py) - cover node-level transitions, especially blocking when logs are insufficient.
- [test_debug_cli.py](/F:/github/spec-kit-plus/tests/test_debug_cli.py) - cover checkpoint rendering for expanded observer/log investigation state.

## Naming Rules

Keep these names stable across schema, persistence, prompts, and tests:

- `observer_expansion_status`
- `observer_expansion_reason`
- `project_runtime_profile`
- `symptom_shape`
- `log_readiness`
- `expanded_observer`
- `dimension_scan`
- `candidate_board`
- `top_candidates`
- `log_investigation_plan`
- `user_request_packet`

Use these status values consistently:

- `observer_expansion_status`: `not_applicable`, `suggested`, `user_declined`, `enabled`, `completed`
- `symptom_shape`: `exact_error`, `phenomenon_only`
- `log_readiness`: `unknown`, `sufficient_existing_logs`, `insufficient_need_instrumentation`, `user_must_provide_logs`

Use these project runtime profiles consistently:

- `frontend/web-ui`
- `backend/api-service`
- `full-stack/web-app`
- `worker/queue/cron`
- `cli/automation`
- `data-pipeline/integration`

Do not invent alternate spellings like `runtime_profile`, `expanded_observer_status`, `needs_more_logs`, or `fullstack-web`. Keep wording stable for prompt parsing and tests.

---

### Task 1: Lock the expanded observer and runtime-log contract into template tests first

**Files:**
- Modify: [test_alignment_templates.py](/F:/github/spec-kit-plus/tests/test_alignment_templates.py)
- Modify: [test_debug_template_guidance.py](/F:/github/spec-kit-plus/tests/test_debug_template_guidance.py)

- [ ] **Step 1: Add shared template assertions for expanded observer and runtime-log gates**

Add assertions like these to `tests/test_alignment_templates.py`:

```python
def test_debug_template_declares_expanded_observer_and_runtime_log_contract() -> None:
    content = _read("templates/commands/debug.md")

    assert "expanded observer" in content.lower()
    assert "runtime bug" in content.lower()
    assert "log_readiness" in content
    assert "user_request_packet" in content
    assert "logs are a first-class evidence source" in content.lower()
    assert "logs不足时禁止空猜修复".lower() not in content.lower()  # prose stays English in templates
    assert "do not enter `fixing`" in content.lower() or "cannot enter `fixing`" in content.lower()


def test_debug_thinker_prompt_requires_two_layer_scoring_and_log_plan() -> None:
    content = _read("templates/worker-prompts/debug-thinker.md")

    assert "minimum 3" in content.lower() or "at least 3" in content.lower()
    assert "likelihood" in content
    assert "impact_radius" in content
    assert "falsifiability" in content
    assert "log_observability" in content
    assert "cross_layer_span" in content
    assert "indirect_causality_risk" in content
    assert "evidence_gap" in content
    assert "investigation_cost" in content
    assert "log_investigation_plan" in content
    assert "must not inspect logs" in content.lower()
```

- [ ] **Step 2: Add command-guidance tests for suggestion and refusal behavior**

Add assertions like these to `tests/test_debug_template_guidance.py`:

```python
def test_debug_template_guidance_explains_optional_expanded_observer() -> None:
    content = Path("templates/commands/debug.md").read_text(encoding="utf-8")

    assert "suggest expanded observer" in content.lower()
    assert "user confirms" in content.lower() or "user can decline" in content.lower()
    assert "standard observer" in content.lower()


def test_debug_template_guidance_requires_runtime_log_escalation_before_fixing() -> None:
    content = Path("templates/commands/debug.md").read_text(encoding="utf-8")

    assert "existing logs" in content.lower()
    assert "instrumentation" in content.lower()
    assert "user_request_packet" in content
    assert "runtime bug" in content.lower()
```

- [ ] **Step 3: Run the template guidance tests to verify RED**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: FAIL because the current debug command and thinker prompt do not yet encode the expanded observer and runtime-log contract.

- [ ] **Step 4: Commit the RED tests**

Run:

```bash
git add tests/test_alignment_templates.py tests/test_debug_template_guidance.py
git commit -m "test: lock expanded debug observer contract"
```

### Task 2: Expand the worker prompts and command template contract

**Files:**
- Modify: [debug.md](/F:/github/spec-kit-plus/templates/commands/debug.md)
- Modify: [debug-thinker.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-thinker.md)
- Modify: [debug-contract-planner.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-contract-planner.md)

- [ ] **Step 1: Update `debug-thinker.md` to emit runtime profile, layered scores, and a log plan**

Add or revise sections so `templates/worker-prompts/debug-thinker.md` requires output like:

```yaml
observer_mode: "full"
project_runtime_profile: "full-stack/web-app"
symptom_shape: "phenomenon_only"
candidate_board:
  - candidate_id: "cand-cache-drift"
    dimension_origin: "cache_queue_async_layer"
    family: "cache_snapshot"
    candidate: "Stale snapshot survives the authoritative update"
    why_it_fits: "UI symptom can be downstream of healthy backend truth"
    indirect_path: "backend truth owner -> snapshot cache -> UI projection"
    surface_vs_truth_owner_note: "Likely downstream projection symptom, not primary truth owner"
    light_scores:
      likelihood: 4
      impact_radius: 4
      falsifiability: 3
      log_observability: 5
top_candidates:
  - candidate_id: "cand-cache-drift"
    engineering_scores:
      cross_layer_span: 5
      indirect_causality_risk: 5
      evidence_gap: 3
      investigation_cost: 2
    investigation_priority: 1
    recommended_log_probe: "Compare server truth-owner logs with cache refresh logs"
log_investigation_plan:
  existing_log_targets:
    - "application logs around the reproduction window"
  candidate_signal_map:
    - candidate_id: "cand-cache-drift"
      signals:
        - "truth owner updated before cache refresh"
```

Also keep these hard constraints in the prompt:

```markdown
- Do NOT read source code.
- Do NOT run commands.
- Do NOT inspect logs or runtime output.
- The log investigation plan is a plan for later stages, not an instruction to read logs now.
```

- [ ] **Step 2: Update `debug-contract-planner.md` to consume expanded observer artifacts**

Revise the prompt so the contract-planner is instructed to preserve and route:

```markdown
- `project_runtime_profile`
- `symptom_shape`
- `top_candidates`
- `log_investigation_plan`
- which candidates appear to be surface-layer symptoms vs likely truth-owner breaks
```

Require the planner to name a primary candidate and contrarian candidate without discarding the log investigation plan:

```yaml
investigation_contract:
  primary_candidate_id: "cand-cache-drift"
  candidate_queue:
    - candidate_id: "cand-cache-drift"
      evidence_needed:
        - "application truth-owner logs"
        - "cache refresh logs"
```

- [ ] **Step 3: Update `debug.md` to explain suggestion flow and runtime-log fix gates**

Add contract language to `templates/commands/debug.md` that explicitly states:

```markdown
- When the issue is a runtime bug with cross-layer or phenomenon-only symptoms, suggest `expanded observer` before evidence collection.
- `expanded observer` is optional and user-confirmed.
- `expanded observer` does not inspect logs; it produces a widened candidate board and `log_investigation_plan`.
- During runtime investigation, evaluate existing logs before fixing.
- If `log_readiness` is insufficient, do not enter `fixing`; add instrumentation, rerun reproduction, or generate a `user_request_packet`.
```

- [ ] **Step 4: Run the template tests to verify GREEN**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the prompt/template slice**

Run:

```bash
git add templates/commands/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md tests/test_alignment_templates.py tests/test_debug_template_guidance.py
git commit -m "feat: define expanded debug observer contract"
```

### Task 3: Add schema models and parser coverage for expanded observer data

**Files:**
- Modify: [schema.py](/F:/github/spec-kit-plus/src/specify_cli/debug/schema.py)
- Modify: [think_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/think_agent.py)
- Modify: [contract_agent.py](/F:/github/spec-kit-plus/src/specify_cli/debug/contract_agent.py)
- Modify: [test_debug_think_agent.py](/F:/github/spec-kit-plus/tests/test_debug_think_agent.py)
- Modify: [test_debug_contract_agent.py](/F:/github/spec-kit-plus/tests/test_debug_contract_agent.py)

- [ ] **Step 1: Write failing parser tests for new thinker and contract payloads**

Add tests like these:

```python
def test_parse_think_subagent_result_reads_expanded_observer_fields() -> None:
    raw = """analysis
---
observer_mode: "full"
project_runtime_profile: "full-stack/web-app"
symptom_shape: "phenomenon_only"
log_readiness: "unknown"
top_candidates:
  - candidate_id: "cand-cache"
    investigation_priority: 1
log_investigation_plan:
  existing_log_targets:
    - "application.log"
"""

    parsed = parse_think_subagent_result(raw)

    assert parsed["project_runtime_profile"] == "full-stack/web-app"
    assert parsed["symptom_shape"] == "phenomenon_only"
    assert parsed["log_investigation_plan"]["existing_log_targets"] == ["application.log"]
```

```python
def test_build_contract_subagent_prompt_includes_expanded_observer_payload() -> None:
    state = DebugGraphState(slug="session", trigger="runtime drift")
    state.project_runtime_profile = "full-stack/web-app"
    state.symptom_shape = "phenomenon_only"
    state.expanded_observer.log_investigation_plan.existing_log_targets = ["application.log"]

    prompt = build_contract_subagent_prompt(state)

    assert "project_runtime_profile" in prompt
    assert "phenomenon_only" in prompt
    assert "application.log" in prompt
```

- [ ] **Step 2: Add the new schema types and state fields**

Extend `src/specify_cli/debug/schema.py` with focused models similar to:

```python
class LightScoreState(BaseModel):
    likelihood: int | None = None
    impact_radius: int | None = None
    falsifiability: int | None = None
    log_observability: int | None = None


class EngineeringScoreState(BaseModel):
    cross_layer_span: int | None = None
    indirect_causality_risk: int | None = None
    evidence_gap: int | None = None
    investigation_cost: int | None = None
```

```python
class UserLogRequestPacket(BaseModel):
    target_source: list[str] = Field(default_factory=list)
    time_window: str | None = None
    keywords_or_fields: list[str] = Field(default_factory=list)
    why_this_matters: list[str] = Field(default_factory=list)
    expected_signal_examples: list[str] = Field(default_factory=list)
```

```python
class ExpandedObserverState(BaseModel):
    dimension_scan: dict[str, str] = Field(default_factory=dict)
    candidate_board: list[ExpandedObserverCandidate] = Field(default_factory=list)
    top_candidates: list[ExpandedObserverTopCandidate] = Field(default_factory=list)
    log_investigation_plan: LogInvestigationPlan = Field(default_factory=LogInvestigationPlan)
```

Then add fields on `DebugGraphState`:

```python
observer_expansion_status: str = "not_applicable"
observer_expansion_reason: str | None = None
project_runtime_profile: str | None = None
symptom_shape: str | None = None
log_readiness: str = "unknown"
expanded_observer: ExpandedObserverState = Field(default_factory=ExpandedObserverState)
```

- [ ] **Step 3: Update prompt builders/parsers to round-trip the new payload**

In `think_agent.py` and `contract_agent.py`, make sure the YAML payload includes and parses:

```python
{
    "project_runtime_profile": state.project_runtime_profile,
    "symptom_shape": state.symptom_shape,
    "log_readiness": state.log_readiness,
    "expanded_observer": state.expanded_observer.model_dump(mode="json"),
}
```

Do not overwrite existing causal-map or observer-framing payload fields; append the new state alongside them.

- [ ] **Step 4: Run the parser tests to verify GREEN**

Run:

```powershell
pytest tests/test_debug_think_agent.py tests/test_debug_contract_agent.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the schema/parser slice**

Run:

```bash
git add src/specify_cli/debug/schema.py src/specify_cli/debug/think_agent.py src/specify_cli/debug/contract_agent.py tests/test_debug_think_agent.py tests/test_debug_contract_agent.py
git commit -m "feat: add expanded observer debug schema"
```

### Task 4: Persist and report the new expanded observer and log-plan state

**Files:**
- Modify: [persistence.py](/F:/github/spec-kit-plus/src/specify_cli/debug/persistence.py)
- Modify: [test_debug_persistence.py](/F:/github/spec-kit-plus/tests/test_debug_persistence.py)

- [ ] **Step 1: Add failing persistence tests for the new state**

Add tests like these:

```python
def test_persistence_round_trips_expanded_observer_runtime_log_fields(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="runtime drift")
    state.observer_expansion_status = "enabled"
    state.observer_expansion_reason = "runtime_cross_layer_symptom"
    state.project_runtime_profile = "full-stack/web-app"
    state.symptom_shape = "phenomenon_only"
    state.log_readiness = "insufficient_need_instrumentation"
    state.expanded_observer.log_investigation_plan.existing_log_targets = ["application.log"]

    handler.save(state)
    restored = handler.load(tmp_path / "session.md")

    assert restored.observer_expansion_status == "enabled"
    assert restored.project_runtime_profile == "full-stack/web-app"
    assert restored.log_readiness == "insufficient_need_instrumentation"
    assert restored.expanded_observer.log_investigation_plan.existing_log_targets == ["application.log"]
```

```python
def test_handoff_report_includes_log_readiness_and_user_request_packet(tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="runtime drift")
    state.log_readiness = "user_must_provide_logs"
    state.expanded_observer.log_investigation_plan.user_request_packet.target_source = ["browser console"]

    report = handler.build_handoff_report(state)

    assert "Log readiness" in report
    assert "user_must_provide_logs" in report
    assert "browser console" in report
```

- [ ] **Step 2: Persist new fields in session markdown and reports**

Update `src/specify_cli/debug/persistence.py` so it saves and loads the new state, and renders sections like:

```markdown
### Expanded Observer
- Expansion status: enabled
- Expansion reason: runtime_cross_layer_symptom
- Project runtime profile: full-stack/web-app
- Symptom shape: phenomenon_only
- Log readiness: insufficient_need_instrumentation
```

And:

```markdown
### Log Investigation Plan
- Existing log targets:
  - application.log
- Missing observability:
  - cache refresh boundary does not emit a structured transition log
- User request packet:
  - target source: browser console
```

- [ ] **Step 3: Run the persistence tests to verify GREEN**

Run:

```powershell
pytest tests/test_debug_persistence.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit the persistence slice**

Run:

```bash
git add src/specify_cli/debug/persistence.py tests/test_debug_persistence.py
git commit -m "feat: persist expanded debug observer state"
```

### Task 5: Implement graph/runtime suggestion logic and log-readiness gates

**Files:**
- Modify: [graph.py](/F:/github/spec-kit-plus/src/specify_cli/debug/graph.py)
- Modify: [test_debug_graph.py](/F:/github/spec-kit-plus/tests/test_debug_graph.py)
- Modify: [test_debug_graph_nodes.py](/F:/github/spec-kit-plus/tests/test_debug_graph_nodes.py)

- [ ] **Step 1: Write failing graph tests for suggestion and blocking behavior**

Add tests like these:

```python
def test_runtime_bug_with_phenomenon_symptom_suggests_expanded_observer() -> None:
    state = DebugGraphState(slug="session", trigger="UI shows stale status after successful backend action")
    state.symptoms.actual = "UI remains stale until refresh"

    _classify_runtime_debug_shape(state)

    assert state.project_runtime_profile == "full-stack/web-app"
    assert state.symptom_shape == "phenomenon_only"
    assert state.observer_expansion_status == "suggested"
```

```python
def test_runtime_fixing_is_blocked_when_log_readiness_is_insufficient() -> None:
    state = DebugGraphState(slug="session", trigger="runtime drift")
    state.log_readiness = "insufficient_need_instrumentation"
    state.current_focus.hypothesis = "stale cache refresh"

    message = _runtime_log_gate_message(state)

    assert "instrumentation" in message.lower()
    assert "user_request_packet" in message
```

- [ ] **Step 2: Add focused helpers for runtime profile classification and observer suggestion**

In `src/specify_cli/debug/graph.py`, add helpers like:

```python
def _classify_runtime_debug_shape(state: DebugGraphState) -> None:
    text = " ".join(
        part.lower()
        for part in [state.trigger, state.symptoms.actual, state.symptoms.errors]
        if part
    )
    if any(token in text for token in ("ui", "frontend", "browser", "api", "database", "cache")):
        state.project_runtime_profile = "full-stack/web-app"
    elif any(token in text for token in ("worker", "queue", "cron", "job")):
        state.project_runtime_profile = "worker/queue/cron"
    else:
        state.project_runtime_profile = "backend/api-service"

    state.symptom_shape = "exact_error" if "traceback" in text or "line " in text else "phenomenon_only"
```

```python
def _maybe_suggest_expanded_observer(state: DebugGraphState) -> None:
    if state.symptom_shape == "phenomenon_only":
        state.observer_expansion_status = "suggested"
        state.observer_expansion_reason = "runtime_cross_layer_symptom"
```

Keep these helpers additive; do not regress the existing `_strong_low_level_evidence_present()` or current profile logic.

- [ ] **Step 3: Add runtime log gate logic before fixing**

Add a focused gate/checklist helper such as:

```python
def _runtime_log_gate_gaps(state: DebugGraphState) -> list[str]:
    if state.log_readiness == "sufficient_existing_logs":
        return []
    if state.log_readiness == "insufficient_need_instrumentation":
        return ["Add instrumentation and rerun reproduction before fixing."]
    if state.log_readiness == "user_must_provide_logs":
        return ["Generate a user_request_packet and wait for the requested logs before fixing."]
    return ["Assess existing logs before fixing this runtime bug."]
```

Use that helper to block `FixingNode` entry for runtime bugs until log readiness is sufficient or an explicit observability escalation path is recorded.

- [ ] **Step 4: Populate a default user log request packet when logs are inaccessible**

When the runtime decides logs are needed but unavailable, populate fields like:

```python
state.expanded_observer.log_investigation_plan.user_request_packet.target_source = [
    "application logs around the reproduction window",
]
state.expanded_observer.log_investigation_plan.user_request_packet.time_window = "30 seconds before and after reproduction"
state.expanded_observer.log_investigation_plan.user_request_packet.keywords_or_fields = [
    "request id",
    "status transition",
    "cache refresh",
]
```

The exact packet can be profile-sensitive, but it must never be empty when `log_readiness == "user_must_provide_logs"`.

- [ ] **Step 5: Run the graph tests to verify GREEN**

Run:

```powershell
pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the graph/runtime slice**

Run:

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: gate runtime debug fixes on log readiness"
```

### Task 6: Expose expanded observer and log state in the debug CLI

**Files:**
- Modify: [cli.py](/F:/github/spec-kit-plus/src/specify_cli/debug/cli.py)
- Modify: [test_debug_cli.py](/F:/github/spec-kit-plus/tests/test_debug_cli.py)

- [ ] **Step 1: Add failing CLI tests for checkpoint output**

Add tests like these:

```python
def test_print_session_checkpoint_shows_expanded_observer_and_log_readiness(capsys, tmp_path: Path) -> None:
    handler = MarkdownPersistenceHandler(tmp_path)
    state = DebugGraphState(slug="session", trigger="runtime drift")
    state.observer_expansion_status = "enabled"
    state.project_runtime_profile = "full-stack/web-app"
    state.log_readiness = "insufficient_need_instrumentation"
    state.expanded_observer.log_investigation_plan.existing_log_targets = ["application.log"]

    _print_session_checkpoint(state, handler)
    output = capsys.readouterr().out

    assert "Expanded Observer" in output
    assert "full-stack/web-app" in output
    assert "insufficient_need_instrumentation" in output
    assert "application.log" in output
```

- [ ] **Step 2: Render the new state in CLI checkpoint summaries**

Extend `src/specify_cli/debug/cli.py` with a focused helper such as:

```python
def _print_expanded_observer_summary(state: DebugGraphState) -> None:
    if state.observer_expansion_status == "not_applicable":
        return
    console.print("[bold]Expanded Observer[/bold]")
    console.print(f"- Status: {state.observer_expansion_status}")
    if state.project_runtime_profile:
        console.print(f"- Runtime profile: {state.project_runtime_profile}")
    console.print(f"- Log readiness: {state.log_readiness}")
```

Also print:

- top candidate IDs and priorities
- existing log targets
- whether a user log request packet is required

- [ ] **Step 3: Run the CLI tests to verify GREEN**

Run:

```powershell
pytest tests/test_debug_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit the CLI slice**

Run:

```bash
git add src/specify_cli/debug/cli.py tests/test_debug_cli.py
git commit -m "feat: show expanded debug observer in cli"
```

### Task 7: Run the focused debug regression suite and reconcile any drift

**Files:**
- Modify only files required by test failures from previous tasks.

- [ ] **Step 1: Run the focused debug regression suite**

Run:

```powershell
pytest `
  tests/test_alignment_templates.py `
  tests/test_debug_template_guidance.py `
  tests/test_debug_think_agent.py `
  tests/test_debug_contract_agent.py `
  tests/test_debug_persistence.py `
  tests/test_debug_graph.py `
  tests/test_debug_graph_nodes.py `
  tests/test_debug_cli.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the broader debug suite for confidence**

Run:

```powershell
pytest tests/test_debug_*.py -q
```

Expected: PASS.

- [ ] **Step 3: Review the diff for unintended contract drift**

Run:

```powershell
git diff -- templates/commands/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md src/specify_cli/debug tests
```

Expected: Only expanded observer and runtime-log contract changes, with no unrelated workflow regressions.

- [ ] **Step 4: Commit the final reconciliation changes**

Run:

```bash
git add templates/commands/debug.md templates/worker-prompts/debug-thinker.md templates/worker-prompts/debug-contract-planner.md src/specify_cli/debug tests
git commit -m "test: verify expanded debug observer runtime"
```

## Self-Review

Spec coverage check:

- Expanded observer remains optional and user-confirmed: covered by Tasks 1, 2, 5, and 6.
- Expanded observer does not read logs and only produces widened candidates plus log plan: covered by Tasks 2 and 3.
- Runtime bug flow must treat logs as first-class evidence and gate fixing on log sufficiency: covered by Tasks 2 and 5.
- Project runtime profiles and layered scoring: covered by Tasks 2 and 3.
- Persistence, handoff, and CLI visibility: covered by Tasks 4 and 6.
- Regression coverage across templates/runtime/tests: covered by Tasks 1 through 7.

Placeholder scan:

- No `TBD`, `TODO`, or “similar to previous task” shortcuts remain.
- Every test step includes exact files and commands.

Type consistency check:

- The plan consistently uses `observer_expansion_status`, `project_runtime_profile`, `symptom_shape`, `log_readiness`, `expanded_observer`, and `user_request_packet`.
- Runtime profile strings and log-readiness values match the approved design spec.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-05-sp-debug-expanded-observer-runtime-logs-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
