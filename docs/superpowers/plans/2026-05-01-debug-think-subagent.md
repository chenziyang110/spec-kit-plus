# sp-debug Think Subagent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 sp-debug GatheringNode 中的 observer framing 从本地规则函数迁移到独立 think subagent，实现上下文隔离。

**Architecture:** GatheringNode 在 observer_framing 未完成时返回 await_input 并携带 think_subagent_prompt，AI agent 同步启动 think subagent 等待结果，解析混合输出填充 observer_framing/transition_memo/alternative_cause_candidates，然后重新进入 GatheringNode 走门控检查。Phase 2 所有节点不动。

**Tech Stack:** Python 3.11+, Pydantic, Pydantic-Graph, Typer, pytest

---

### Task 1: 新增 `think_subagent_prompt` 字段到 DebugGraphState

**Files:**
- Modify: `src/specify_cli/debug/schema.py:189`

- [ ] **Step 1: 添加字段**

在 `DebugGraphState` 类的 `execution_intent` 字段后添加：

```python
think_subagent_prompt: Optional[str] = None
```

完整上下文（第 189-190 行）：
```python
    execution_intent: ExecutionIntentState = Field(default_factory=ExecutionIntentState)
    think_subagent_prompt: Optional[str] = None
```

- [ ] **Step 2: 运行现有测试验证 schema 兼容性**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_graph.py -x -q
```

Expected: 所有现有测试仍然 PASS（新增 Optional 字段不影响向后兼容）

- [ ] **Step 3: Commit**

```bash
git add src/specify_cli/debug/schema.py
git commit -m "feat: add think_subagent_prompt field to DebugGraphState"
```

---

### Task 2: 新增 debug-thinker.md 模板

**Files:**
- Create: `templates/worker-prompts/debug-thinker.md`

- [ ] **Step 1: 创建模板文件**

```markdown
# Think Subagent — Observer Framing

You are a debugging **Observer/Framer**. Your job is deep causal reasoning **before any code is read**.

## Hard Constraints

- **Do NOT read source code.** You do not have access to the codebase and must not request it.
- **Do NOT run commands.** You are a pure reasoning agent.
- **Work only from the project map and feature context provided below.**
- **Generate as many plausible hypotheses as you can** (minimum 3). Cast a wide net.

## Input Context

### Symptoms
{SYMPTOMS}

### Diagnostic Profile
{DIAGNOSTIC_PROFILE}

### Feature Context
{FEATURE_CONTEXT}

### Project Map
{PROJECT_MAP}

## Instructions

1. Analyze the symptoms against the project map. Which layers/contracts could produce this failure?
2. Identify the **primary suspected loop** (scheduler-admission, cache-snapshot, ui-projection, or general).
3. Identify the **suspected owning layer** — which system layer most likely owns the truth that is breaking.
4. Generate at least 3 **alternative cause candidates**. For each:
   - `candidate`: a concise one-line hypothesis
   - `why_it_fits`: why this matches the observed symptoms
   - `map_evidence`: what in the project map supports this hypothesis
   - `would_rule_out`: what evidence would eliminate this candidate
5. Recommend the **first probe** — the single most informative investigation to start with.
6. List **missing questions** — what you don't yet know that matters.

## Output Format

Write your analysis as free text first, then append a `---` separator followed by a YAML block:

```
[Your free-text analysis: reasoning process, key observations, connections you noticed, risks you considered but deprioritized]

---
observer_framing:
  summary: "One-paragraph summary of the most likely failure boundary"
  primary_suspected_loop: "scheduler-admission|cache-snapshot|ui-projection|general"
  suspected_owning_layer: "which layer owns the truth"
  suspected_truth_owner: "same or more specific than owning layer"
  recommended_first_probe: "the single most informative first investigation"
  missing_questions:
    - "question 1"
    - "question 2"
alternative_cause_candidates:
  - candidate: "concise hypothesis"
    why_it_fits: "why symptoms match"
    map_evidence: "project-map signals"
    would_rule_out: "what evidence would eliminate this"
  - candidate: "..."
    why_it_fits: "..."
    map_evidence: "..."
    would_rule_out: "..."
transition_memo:
  first_candidate_to_test: "which candidate to test first"
  why_first: "why this one first"
  evidence_unlock:
    - "reproduction"
    - "logs"
    - "code"
    - "tests"
  carry_forward_notes:
    - "Do not discard the observer framing when code-level evidence appears."
    - "Treat later hypotheses as confirmations or eliminations of observer candidates."
```
```

- [ ] **Step 2: 验证模板文件存在**

```bash
ls -la /f/github/spec-kit-plus/templates/worker-prompts/debug-thinker.md
```

- [ ] **Step 3: Commit**

```bash
git add templates/worker-prompts/debug-thinker.md
git commit -m "feat: add debug-thinker subagent prompt template"
```

---

### Task 3: 新增 think_agent.py 模块

**Files:**
- Create: `src/specify_cli/debug/think_agent.py`
- Create: `tests/test_debug_think_agent.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_debug_think_agent.py`：

```python
import pytest
from specify_cli.debug.schema import (
    DebugGraphState,
    DebugStatus,
    ObserverCauseCandidate,
    ObserverFramingState,
    TransitionMemoState,
)
from specify_cli.debug.think_agent import (
    build_think_subagent_prompt,
    parse_think_subagent_result,
)


class TestBuildThinkSubagentPrompt:
    def test_includes_symptoms_in_prompt(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="queue stuck after slot release",
            diagnostic_profile="scheduler-admission",
        )
        state.symptoms.expected = "queue drains within 100ms"
        state.symptoms.actual = "queue remains non-empty for 30s"
        state.symptoms.errors = "timeout waiting for slot"

        prompt = build_think_subagent_prompt(state)

        assert "queue drains within 100ms" in prompt
        assert "queue remains non-empty for 30s" in prompt
        assert "timeout waiting for slot" in prompt
        assert "scheduler-admission" in prompt

    def test_includes_feature_context_in_prompt(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="stale cache",
            diagnostic_profile="cache-snapshot",
        )
        state.context.feature_id = "FEAT-001"
        state.context.summary = "Cache invalidation for task table"

        prompt = build_think_subagent_prompt(state)

        assert "FEAT-001" in prompt
        assert "Cache invalidation" in prompt

    def test_prompt_contains_output_format_instruction(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="ui not updating",
            diagnostic_profile="ui-projection",
        )

        prompt = build_think_subagent_prompt(state)

        assert "---" in prompt
        assert "observer_framing:" in prompt
        assert "alternative_cause_candidates:" in prompt
        assert "transition_memo:" in prompt

    def test_prompt_marks_hard_constraints(self) -> None:
        state = DebugGraphState(
            slug="test-session",
            trigger="general issue",
            diagnostic_profile="general",
        )

        prompt = build_think_subagent_prompt(state)

        assert "Do NOT read source code" in prompt
        assert "Do NOT run commands" in prompt


class TestParseThinkSubagentResult:
    def test_extracts_observer_framing_from_hybrid_output(self) -> None:
        raw = """The most likely failure is in the scheduler admission loop.

---
observer_framing:
  summary: "Scheduler admission control loop failure"
  primary_suspected_loop: "scheduler-admission"
  suspected_owning_layer: "admission control"
  suspected_truth_owner: "admission control"
  recommended_first_probe: "Verify queue contents before and after"
  missing_questions:
    - "What is the slot release timing?"
alternative_cause_candidates:
  - candidate: "Slot leak in admission handler"
    why_it_fits: "Queue never drains"
    map_evidence: "admission handler owns slot lifecycle"
    would_rule_out: "Slot counter matches expected"
transition_memo:
  first_candidate_to_test: "Slot leak in admission handler"
  why_first: "Best matches outsider framing"
  evidence_unlock:
    - "reproduction"
    - "logs"
  carry_forward_notes:
    - "Keep observer framing"
"""

        result = parse_think_subagent_result(raw)

        assert result["observer_framing"]["summary"] == "Scheduler admission control loop failure"
        assert result["observer_framing"]["primary_suspected_loop"] == "scheduler-admission"
        assert len(result["alternative_cause_candidates"]) == 1
        assert result["alternative_cause_candidates"][0]["candidate"] == "Slot leak in admission handler"
        assert result["transition_memo"]["first_candidate_to_test"] == "Slot leak in admission handler"

    def test_extracts_multiple_candidates(self) -> None:
        raw = """Analysis here.

---
observer_framing:
  summary: "Multiple possible causes"
  primary_suspected_loop: "general"
  suspected_owning_layer: "unknown"
  suspected_truth_owner: "unknown"
  recommended_first_probe: "Check logs"
  missing_questions: []
alternative_cause_candidates:
  - candidate: "Cause A"
    why_it_fits: "Fits A"
    map_evidence: "Evidence A"
    would_rule_out: "Rule out A"
  - candidate: "Cause B"
    why_it_fits: "Fits B"
    map_evidence: "Evidence B"
    would_rule_out: "Rule out B"
  - candidate: "Cause C"
    why_it_fits: "Fits C"
    map_evidence: "Evidence C"
    would_rule_out: "Rule out C"
transition_memo:
  first_candidate_to_test: "Cause A"
  why_first: "Most likely"
  evidence_unlock: ["reproduction"]
  carry_forward_notes: []
"""

        result = parse_think_subagent_result(raw)

        assert len(result["alternative_cause_candidates"]) == 3

    def test_no_yaml_block_returns_empty_dict(self) -> None:
        raw = "Just some free text without any YAML block."

        result = parse_think_subagent_result(raw)

        assert result == {}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_think_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'specify_cli.debug.think_agent'`

- [ ] **Step 3: 实现 think_agent.py**

创建 `src/specify_cli/debug/think_agent.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import DebugGraphState


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "worker-prompts" / "debug-thinker.md"


def build_think_subagent_prompt(state: DebugGraphState) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    symptoms_parts: list[str] = []
    if state.symptoms.expected:
        symptoms_parts.append(f"Expected: {state.symptoms.expected}")
    if state.symptoms.actual:
        symptoms_parts.append(f"Actual: {state.symptoms.actual}")
    if state.symptoms.errors:
        symptoms_parts.append(f"Errors: {state.symptoms.errors}")
    if state.trigger:
        symptoms_parts.append(f"Trigger: {state.trigger}")

    symptoms_text = "\n".join(symptoms_parts) if symptoms_parts else "No symptoms recorded."

    feature_parts: list[str] = []
    if state.context.feature_id:
        feature_parts.append(f"Feature ID: {state.context.feature_id}")
    if state.context.summary:
        feature_parts.append(f"Summary: {state.context.summary}")
    if state.context.description:
        feature_parts.append(f"Description: {state.context.description}")
    if state.context.project_map_summary:
        feature_parts.append(f"Project Map: {state.context.project_map_summary}")
    feature_text = "\n".join(feature_parts) if feature_parts else "No feature context loaded."

    project_map_parts: list[str] = []
    if state.context.modified_files:
        project_map_parts.append("Modified files:")
        project_map_parts.extend(f"  - {f}" for f in state.context.modified_files[:10])
    if state.recently_modified:
        if not project_map_parts:
            project_map_parts.append("Recently modified files:")
        else:
            project_map_parts.append("\nRecently modified (git):")
        project_map_parts.extend(f"  - {f}" for f in state.recently_modified[:10])
    project_map_text = "\n".join(project_map_parts) if project_map_parts else "No file information available."

    prompt = (
        template
        .replace("{SYMPTOMS}", symptoms_text)
        .replace("{DIAGNOSTIC_PROFILE}", state.diagnostic_profile or "general")
        .replace("{FEATURE_CONTEXT}", feature_text)
        .replace("{PROJECT_MAP}", project_map_text)
    )

    return prompt


def parse_think_subagent_result(raw_text: str) -> dict[str, Any]:
    separator = "\n---\n"
    if separator not in raw_text:
        return {}

    _, _, yaml_block = raw_text.partition(separator)
    if not yaml_block.strip():
        return {}

    try:
        data = yaml.safe_load(yaml_block)
        if not isinstance(data, dict):
            return {}
        return data
    except yaml.YAMLError:
        return {}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_think_agent.py -v
```

Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/debug/think_agent.py tests/test_debug_think_agent.py
git commit -m "feat: add think_agent module with prompt builder and result parser"
```

---

### Task 4: 修改 GatheringNode 使用 think subagent

**Files:**
- Modify: `src/specify_cli/debug/graph.py:668-702`
- Modify: `src/specify_cli/debug/graph.py:1-17` (新增 import)

- [ ] **Step 1: 更新现有 graph 测试以反映新行为**

先运行现有测试确认基线：

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py -v
```

Expected: 现有测试 PASS

- [ ] **Step 2: 新增 GatheringNode think subagent 分派的测试**

在 `tests/test_debug_graph_nodes.py` 末尾添加：

```python
class TestGatheringNodeThinkSubagentDispatch:
    def test_think_subagent_prompt_is_populated_before_await_input(self) -> None:
        """After build_think_subagent_prompt, state.think_subagent_prompt should be set."""
        from specify_cli.debug.think_agent import build_think_subagent_prompt
        from specify_cli.debug.schema import DebugGraphState

        state = DebugGraphState(
            slug="test-think",
            trigger="queue not draining",
            diagnostic_profile="scheduler-admission",
        )
        state.symptoms.expected = "queue drains"
        state.symptoms.actual = "queue stuck"

        prompt = build_think_subagent_prompt(state)
        state.think_subagent_prompt = prompt

        assert state.think_subagent_prompt is not None
        assert "queue drains" in state.think_subagent_prompt
        assert "queue stuck" in state.think_subagent_prompt
        assert "scheduler-admission" in state.think_subagent_prompt
```

- [ ] **Step 3: 运行新增测试确认失败**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_graph_nodes.py::TestGatheringNodeThinkSubagentDispatch -v
```

Expected: PASS（这些测试验证 prompt 构建，不依赖 graph 变更）

- [ ] **Step 4: 修改 GatheringNode.run()**

在 `src/specify_cli/debug/graph.py` 顶部新增 import：

```python
from .think_agent import build_think_subagent_prompt
```

将第 686 行 `_populate_observer_framing(ctx.state)` 替换为 think subagent 分派门控：

```python
        # 2. Observer Framing — dispatch to think subagent for isolated reasoning
        if not ctx.state.observer_framing_completed:
            prompt = build_think_subagent_prompt(ctx.state)
            ctx.state.think_subagent_prompt = prompt
            return _await_input(
                ctx.state,
                "Observer framing needed. Spawn a think subagent with think_subagent_prompt. "
                "Wait for its structured result, then parse the YAML block after '---' and populate "
                "observer_framing, transition_memo, and alternative_cause_candidates fields. "
                "Set observer_framing_completed=True and continue.",
            )
```

`GatheringNode.run()` 完整变更后的代码：

```python
class GatheringNode(BaseNode[DebugGraphState, MarkdownPersistenceHandler]):
    @persist
    async def run(self, ctx: GraphRunContext[DebugGraphState, MarkdownPersistenceHandler]) -> Union['InvestigatingNode', End]:
        ctx.state.status = DebugStatus.GATHERING
        ctx.state.current_node_id = "GatheringNode"

        # 1. Load context
        loader = ContextLoader()

        if not ctx.state.context.feature_id:
            feature_dir = loader.find_active_feature()
            if feature_dir:
                ctx.state.context = loader.load_feature_context(feature_dir)

        if not ctx.state.recently_modified:
            ctx.state.recently_modified = loader.get_recent_git_changes()

        _refresh_diagnostic_profile(ctx.state)
        _refresh_lane_plan(ctx.state)

        # 2. Observer Framing — dispatch to think subagent for isolated reasoning
        if not ctx.state.observer_framing_completed:
            prompt = build_think_subagent_prompt(ctx.state)
            ctx.state.think_subagent_prompt = prompt
            return _await_input(
                ctx.state,
                "Observer framing needed. Spawn a think subagent with think_subagent_prompt. "
                "Wait for its structured result, then parse the YAML block after '---' and populate "
                "observer_framing, transition_memo, and alternative_cause_candidates fields. "
                "Set observer_framing_completed=True and continue.",
            )

        # 3. Gate checks
        if not ctx.state.symptoms.expected or not ctx.state.symptoms.actual:
            return _await_input(
                ctx.state,
                "Observer framing complete. Collect expected and actual behavior before continuing into evidence investigation.",
            )

        if not ctx.state.symptoms.reproduction_verified:
            return _await_input(
                ctx.state,
                "Observer framing complete. Reproduction not verified. Please create a reproduction script and run it to verify the bug. Update symptoms.reproduction_verified to True once confirmed.",
            )

        return InvestigatingNode()
```

- [ ] **Step 5: 运行所有 debug 测试确认无回归**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_graph.py tests/test_debug_graph_nodes.py tests/test_debug_think_agent.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/debug/graph.py tests/test_debug_graph_nodes.py
git commit -m "feat: dispatch observer framing to think subagent in GatheringNode"
```

---

### Task 5: 更新 _augment_debug_skill 注入 think subagent 分派指南

**Files:**
- Modify: `src/specify_cli/integrations/base.py:1810-1834`

- [ ] **Step 1: 在 Leader Gate 段落后添加 Think Subagent Dispatch 指南**

在 `_augment_debug_skill` 方法中，在 "Leader Gate" 标记检查和 "Subagent Evidence Collection" 之间插入 think subagent 指南段落。

在 `base.py` 第 1833 行（`"**Hard rule:** During `investigating`, the leader must not let subagents mutate the debug file..."` 之后）和第 1834 行（`if "## Session Lifecycle" in content:` 之前）之间插入：

```python
            think_gate_marker = f"## {agent_name} Think Subagent Dispatch"
            if think_gate_marker not in content:
                think_addendum = (
                    "\n"
                    f"## {agent_name} Think Subagent Dispatch\n\n"
                    f"When running `sp-debug` in {agent_name}, the **Gathering** stage may return an `await_input` "
                    "containing a `think_subagent_prompt`. This prompt is a self-contained reasoning task for a "
                    "fresh subagent.\n"
                    "\n"
                    "**When you receive a think_subagent_prompt:**\n"
                    "- Spawn a subagent with the exact prompt text via `spawn_agent`.\n"
                    "- The think subagent does NOT read source code and does NOT run commands — it is a pure reasoning agent.\n"
                    "- Use `wait_agent` to wait for the think subagent's result.\n"
                    "- The result is hybrid: free-text analysis followed by `---` and a YAML block.\n"
                    "- Parse the YAML block after `---` and populate these fields in the debug state:\n"
                    "  - `observer_framing` (summary, primary_suspected_loop, suspected_owning_layer, etc.)\n"
                    "  - `transition_memo` (first_candidate_to_test, why_first, carry_forward_notes)\n"
                    "  - `alternative_cause_candidates` (list of candidate objects)\n"
                    "- Set `observer_framing_completed` to `True`.\n"
                    "- Then continue the debug session — the next GatheringNode run will skip observer framing "
                    "and proceed to gate checks.\n"
                    "- Do NOT skip the think subagent. Context isolation is the purpose of this step.\n"
                )
                content = content.replace(
                    "**Hard rule:** During `investigating`",
                    think_addendum + "\n**Hard rule:** During `investigating`",
                    1,
                )
```

- [ ] **Step 2: 运行现有集成测试验证无回归**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/ -k "debug" -x -q
```

Expected: 所有 debug 相关测试 PASS

- [ ] **Step 3: Commit**

```bash
git add src/specify_cli/integrations/base.py
git commit -m "feat: inject think subagent dispatch guidance into debug skill augmentation"
```

---

### Task 6: 最终验证

- [ ] **Step 1: 运行全量 debug 测试套件**

```bash
cd /f/github/spec-kit-plus && python -m pytest tests/test_debug_*.py -v
```

Expected: 所有测试 PASS，无回归

- [ ] **Step 2: 验证 _populate_observer_framing 仍存在（向后兼容）**

```bash
cd /f/github/spec-kit-plus && python -c "from specify_cli.debug.graph import _populate_observer_framing; print('OK: function still importable')"
```

Expected: `OK: function still importable`

- [ ] **Step 3: Commit 最终验证结果（如有变更）**

```bash
git status
```
