# 子代理就绪任务契约 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升级 sp-plan/sp-tasks/sp-implement 的命令模板和共享模板，使得 sp-tasks 产出的每个 task 自带 agent 指派、上下文导航、读写范围声明、可执行验证命令和失败升级策略，sp-implement 在分发前自动校验 task 契约完整性。

**Architecture:** 改动集中在模板层（command partials 和 shared templates），辅以 packet_schema.py 的字段扩展和 delegation.py 的校验函数。核心逻辑是"sp-plan 产出可锚定的文档 → sp-tasks 产出子代理就绪的 task → sp-implement 校验后分发"。

**Tech Stack:** Python (specify_cli), Markdown templates

---

### Task 0: 升级 plan shell.md — 锚定标题要求

**Files:**
- Modify: `templates/command-partials/plan/shell.md:29-31`

- [ ] **Step 1: 在 Guardrails 中追加锚定标题要求**

在现有 Guardrails 列表末尾添加最后一条规则。找到文件中 `## Guardrails` 部分最后的规则，在其后追加：

```markdown
- Use anchorable section headings (`## Section Name`) in all output artifacts so that downstream task generation can produce precise `file#section` context pointers.
```

- [ ] **Step 2: 运行模板对齐测试确认不破坏现有约定**

```bash
pytest tests/test_alignment_templates.py -q
```

- [ ] **Step 3: 提交**

```bash
git add templates/command-partials/plan/shell.md
git commit -m "feat: add anchorable heading guardrail to sp-plan output contract"
```

---

### Task 1: 升级 tasks shell.md — 子代理就绪任务格式

**Files:**
- Modify: `templates/command-partials/tasks/shell.md`

- [ ] **Step 1: 在 Output Contract 区域追加 enriched task 格式要求**

在 `templates/command-partials/tasks/shell.md` 的 `## Output Contract` 节中，现有内容之后追加：

```markdown
- Every task MUST carry the enriched subagent-ready contract fields:
  - **agent**: Role from the agent-teams pool (security-reviewer, test-engineer, style-reviewer, performance-reviewer, quality-reviewer, api-reviewer, debugger, code-simplifier, build-fixer, executor).
  - **depends_on**: Explicit task IDs with brief descriptions.
  - **parallel_safe**: `true` when write sets are fully isolated and no shared-state conflicts exist.
  - **Context navigation table**: Precise `file#section` pointers to plan.md, data-model.md, contracts/, and reference implementations — do not duplicate content, only point to it.
  - **Scope boundaries**: `write_scope` (exact output files), `read_scope` (read-only dependencies), `forbidden` (paths the worker must not touch).
  - **Expected outputs**: Concrete file list the worker must produce.
  - **Anti-goals**: Behaviors the worker must not perform (e.g., "do not introduce new dependencies").
  - **Acceptance criteria**: Verifiable, objective conditions.
  - **Verify commands**: Runnable shell commands the worker can execute to self-validate.
  - **Handoff format**: Structured fields `status`, `changed_files`, `validation_output`, `concerns`, `recovery_hints`.
  - **Failure handling**: `retry_max` (default 2) and `escalation` role (default debugger).
- Every task must pass independent-executability check before being written: a single subagent reading only the task body plus the pointed-to context can complete it without asking the leader for clarification.
```

- [ ] **Step 2: 运行 guidance 测试确认格式被正确传播**

```bash
pytest tests/test_specify_guidance_docs.py -q -k "tasks"
```

- [ ] **Step 3: 提交**

```bash
git add templates/command-partials/tasks/shell.md
git commit -m "feat: require enriched subagent-ready task contract fields in sp-tasks output"
```

---

### Task 2: 升级 tasks-template.md — 增加子代理契约字段

**Files:**
- Modify: `templates/tasks-template.md`

- [ ] **Step 1: 在 Task Shaping Rules 区段增加 enriched field 生成规则**

在 `## Task Shaping Rules` 节末尾（第 36 行 `- Stop decomposition...` 之后）追加：

```markdown
- Every task written into this template MUST include the enriched subagent contract fields defined in the `sp-tasks` output contract.
- Before finalizing a task, confirm the independent-executability gate: one subagent, reading only this task body plus the pointed-to context, can complete the work without asking the leader for clarification.
```

- [ ] **Step 2: 在 Format 区段增加 agent 字段说明**

在 `## Format: [ID] [P?] [Story] Description` 节末尾追加：

```markdown
- **Agent**: Role from the agent-teams pool assigned to this task (security-reviewer, test-engineer, style-reviewer, performance-reviewer, quality-reviewer, api-reviewer, debugger, code-simplifier, build-fixer, executor). Write as `[Agent: <role>]` immediately after the Story label.
```

- [ ] **Step 3: 更新 task 示例格式**

把现有的 task 示例从：
```text
- [ ] T014 [P] [US1] Create [Entity1] model in src/models/[entity1].py
```

更新为：
```text
- [ ] T014 [P] [US1] [Agent: test-engineer] Create [Entity1] model in src/models/[entity1].py
```

对所有示例 task 做同样的更新。同时在模板底部增加一个完整 enriched task 的参考示例，包含上下文导航表、范围边界、验证命令和交付格式。

- [ ] **Step 4: 运行模板测试确认**

```bash
pytest tests/test_alignment_templates.py -q
```

- [ ] **Step 5: 提交**

```bash
git add templates/tasks-template.md
git commit -m "feat: add enriched subagent contract fields to tasks template format"
```

---

### Task 3: 升级 implement.md — 预分发校验层

**Files:**
- Modify: `templates/commands/implement.md`

- [ ] **Step 1: 在 Orchestration Model 与 Pre-Execution Checks 之间插入新节**

在 `## Orchestration Model` 结尾（`### Integrity Rules` 最后一条之后）和 `## Pre-Execution Checks` 之间插入新节：

```markdown
## Pre-Dispatch Validation

Before dispatching any subagent, the leader MUST validate each task contract:

### Required Checks (BLOCK on failure)

1. **agent_exists**: Confirm the task's `agent` role exists in the agent-teams role pool: security-reviewer, test-engineer, style-reviewer, performance-reviewer, quality-reviewer, api-reviewer, debugger, code-simplifier, build-fixer, executor. If missing, auto-correct to the closest matching role or `executor`.

2. **deps_acyclic**: Confirm `depends_on` does not form a cycle. Walk the dependency chain; if a cycle is detected, stop and require tasks.md correction before dispatch.

### Advisory Checks (WARN but continue)

3. **scope_paths_exist**: Confirm each path in `write_scope` and `read_scope` exists in the repository or will be created by this task. Missing paths that are not created by earlier tasks should be flagged.

4. **context_nav_valid**: Spot-check context navigation pointers — verify the pointed-to files exist and the referenced sections are present. Missing pointers should be noted but do not block dispatch.

5. **forbidden_safe**: Verify that `forbidden` includes `.env`, credential files, secrets directories, and other sensitive paths. If missing, auto-append the default forbidden patterns before dispatch.

### Parallel Safety Check

6. **write_set_isolation**: For any two tasks in the same parallel batch, confirm their `write_scope` sets have zero overlap. Tasks with overlapping write sets MUST be serialized even if both are marked `[P]`.

### Validation Output

After checks complete, record results in `implement-tracker.md`:
- `pre_dispatch_validation`: pass | warnings | blocked
- `validation_warnings`: [list of advisory warnings]
- `auto_corrections`: [list of fields auto-corrected]
```

- [ ] **Step 2: 在 Outline Step 5（Parse tasks.md）后增加校验步骤**

在 Step 5（Parse tasks.md structure and extract...）末尾，追加：

```markdown
   - **REQUIRED**: Run pre-dispatch validation (see Pre-Dispatch Validation section) on every task in the current ready batch before compiling WorkerTaskPacket.
   - **IF VALIDATION BLOCKS**: Record the blocking issue in `implement-tracker.md` under `blockers`, set `next_action` to the required fix, and stop the batch.
   - **IF VALIDATION WARNS**: Record warnings in `implement-tracker.md` and continue dispatch.
```

- [ ] **Step 3: 在 Step 6（Select subagent dispatch）中追加 agent 路由规则**

在 Step 6 的 decision order 之前追加：

```markdown
   - **Agent routing**: When a task specifies an `agent` role, dispatch to that role's subagent type. When no agent is specified, default to a general executor lane. Do not route security-sensitive tasks to general-purpose agents when a matching specialist exists.
```

- [ ] **Step 4: 运行 implement 模板测试**

```bash
pytest tests/test_specify_guidance_docs.py -q -k "implement"
```

- [ ] **Step 5: 提交**

```bash
git add templates/commands/implement.md
git commit -m "feat: add pre-dispatch validation and agent routing to sp-implement contract"
```

---

### Task 4: 扩展 WorkerTaskPacket — 增加可选子代理字段

**Files:**
- Modify: `src/specify_cli/execution/packet_schema.py`

- [ ] **Step 1: 在 WorkerTaskPacket dataclass 中增加可选字段**

在 `WorkerTaskPacket` 类的现有字段之后（`packet_version` 之前），添加：

```python
    # Subagent-ready task contract fields (optional — populated when tasks.md is enriched)
    agent_role: str = ""
    context_nav: list[dict[str, str]] = field(default_factory=list)
    anti_goals: list[str] = field(default_factory=list)
    verify_commands: list[str] = field(default_factory=list)
    escalation_role: str = "debugger"
    retry_max: int = 2
```

- [ ] **Step 2: 更新 `worker_task_packet_from_json` 以正确解析新字段**

新字段都是简单类型或默认值，现有的 `_filter_dataclass_payload` 模式已经能处理。确认 `worker_task_packet_payload` 中的 `asdict(packet)` 能正确序列化。

- [ ] **Step 3: 运行现有 packet 测试确认向后兼容**

```bash
pytest tests/codex_team/test_codex_guidance_routing.py -q
pytest tests/contract/test_codex_team_generated_assets.py -q
```

- [ ] **Step 4: 提交**

```bash
git add src/specify_cli/execution/packet_schema.py
git commit -m "feat: add optional subagent contract fields to WorkerTaskPacket"
```

---

### Task 5: 在 delegation.py 中增加 task contract 校验函数

**Files:**
- Modify: `src/specify_cli/orchestration/delegation.py`

- [ ] **Step 1: 增加 `validate_task_contract` 函数**

在文件末尾（`describe_delegation_surface` 函数之后）添加：

```python
from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TaskContractValidation:
    """Result of validating a single task contract before dispatch."""
    task_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_corrections: dict[str, str] = field(default_factory=dict)


KNOWN_AGENT_ROLES = frozenset({
    "security-reviewer",
    "test-engineer",
    "style-reviewer",
    "performance-reviewer",
    "quality-reviewer",
    "api-reviewer",
    "debugger",
    "code-simplifier",
    "build-fixer",
    "git-master",
    "executor",
})


def validate_task_contract(
    *,
    task_id: str,
    agent: str,
    write_scope: list[str] | None = None,
    depends_on: list[str] | None = None,
    project_root: str = ".",
) -> TaskContractValidation:
    """Validate a task contract has the minimum fields for safe subagent dispatch."""
    errors: list[str] = []
    warnings: list[str] = []
    corrections: dict[str, str] = {}

    # 1. agent_exists
    resolved_agent = agent.strip().lower() if agent else ""
    if not resolved_agent:
        corrections["agent"] = "executor"
        resolved_agent = "executor"
    elif resolved_agent not in KNOWN_AGENT_ROLES:
        warnings.append(f"agent '{agent}' not in known role pool, using 'executor'")
        corrections["agent"] = "executor"
        resolved_agent = "executor"

    # 2. deps_acyclic — simple self-reference check (full cycle detection needs task graph)
    if depends_on:
        for dep in depends_on:
            if dep.strip() == task_id.strip():
                errors.append(f"task {task_id} depends on itself")
                break

    # 3. forbidden_safe — ensure sensitive paths are covered
    write_paths = write_scope or []
    sensitive_patterns = {".env", "credentials", "secrets", "secret", ".key", ".pem"}
    for path in write_paths:
        path_lower = path.lower()
        for pattern in sensitive_patterns:
            if pattern in path_lower:
                warnings.append(
                    f"write_scope includes potentially sensitive path '{path}'"
                )
                break

    valid = len(errors) == 0
    return TaskContractValidation(
        task_id=task_id,
        valid=valid,
        errors=errors,
        warnings=warnings,
        auto_corrections=corrections,
    )


def validate_batch_isolation(
    tasks: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Check a batch of tasks for write-set isolation. Returns list of conflicts."""
    conflicts: list[dict[str, object]] = []
    for i, task_a in enumerate(tasks):
        write_a = set(
            str(p) for p in (task_a.get("write_scope") or [])
        )
        if not write_a:
            continue
        for j in range(i + 1, len(tasks)):
            task_b = tasks[j]
            write_b = set(
                str(p) for p in (task_b.get("write_scope") or [])
            )
            overlap = write_a & write_b
            if overlap:
                conflicts.append({
                    "task_a": str(task_a.get("task_id", i)),
                    "task_b": str(task_b.get("task_id", j)),
                    "overlapping_paths": sorted(overlap),
                })
    return conflicts
```

- [ ] **Step 2: 运行现有 orchestration 测试确认不破坏**

```bash
pytest tests/orchestration/ -q
```

- [ ] **Step 3: 提交**

```bash
git add src/specify_cli/orchestration/delegation.py
git commit -m "feat: add task contract validation and batch isolation check helpers"
```

---

### Task 6: 文档更新

**Files:**
- Modify: `AGENTS.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `.specify/project-map/root/WORKFLOWS.md`

- [ ] **Step 1: 更新 AGENTS.md 的工作流路由节**

在 AGENTS.md 中更新 `sp-tasks` 的描述，反映其现在产出 enriched task contract。搜索 `sp-tasks` 的相关行，确保描述与新的子代理就绪格式一致。

- [ ] **Step 2: 更新 PROJECT-HANDBOOK.md**

在 PROJECT-HANDBOOK.md 中更新 task generation 相关描述，增加 enriched contract 的说明。

- [ ] **Step 3: 更新 project-map WORKFLOWS.md**

在 `.specify/project-map/root/WORKFLOWS.md` 中的 `sp-tasks` 描述中增加 enriched task fields 的说明。

- [ ] **Step 4: 提交**

```bash
git add AGENTS.md PROJECT-HANDBOOK.md .specify/project-map/root/WORKFLOWS.md
git commit -m "docs: update workflow docs for subagent-ready task contracts"
```

---

### Task 7: 测试升级

**Files:**
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_alignment_templates.py`
- Create: `tests/orchestration/test_task_contract_validation.py`

- [ ] **Step 1: 在 test_specify_guidance_docs.py 中增加 enriched task field 断言**

在现有的 tasks.md 模板测试中，增加对 enriched fields 的检测：

```python
def test_tasks_template_requires_enriched_fields():
    """tasks shell.md must require agent, scope, context nav, verify commands, and handoff format."""
    tasks_shell = (TEMPLATES_DIR / "command-partials" / "tasks" / "shell.md").read_text()
    required_fields = [
        "agent",
        "write_scope",
        "read_scope",
        "forbidden",
        "context nav",
        "verify",
        "handoff",
        "escalation",
    ]
    for field in required_fields:
        assert field.lower() in tasks_shell.lower(), f"Missing required field: {field}"
```

- [ ] **Step 2: 在 test_alignment_templates.py 中增加 plan 锚定标题断言**

```python
def test_plan_shell_requires_anchorable_headings():
    """plan shell.md must require anchorable section headings."""
    plan_shell = (TEMPLATES_DIR / "command-partials" / "plan" / "shell.md").read_text()
    assert "anchorable" in plan_shell.lower()
```

- [ ] **Step 3: 创建 test_task_contract_validation.py**

```python
"""Tests for task contract validation helpers."""

import pytest
from specify_cli.orchestration.delegation import (
    validate_task_contract,
    validate_batch_isolation,
    KNOWN_AGENT_ROLES,
)


class TestValidateTaskContract:
    def test_valid_contract_passes(self):
        result = validate_task_contract(
            task_id="T001",
            agent="security-reviewer",
            write_scope=["src/auth/middleware.ts"],
        )
        assert result.valid
        assert len(result.errors) == 0

    def test_empty_agent_auto_corrects_to_executor(self):
        result = validate_task_contract(
            task_id="T001",
            agent="",
        )
        assert result.valid
        assert result.auto_corrections.get("agent") == "executor"

    def test_unknown_agent_warns(self):
        result = validate_task_contract(
            task_id="T001",
            agent="nonexistent-role",
        )
        assert result.valid  # warning, not error
        assert len(result.warnings) >= 1

    def test_self_dependency_errors(self):
        result = validate_task_contract(
            task_id="T001",
            agent="executor",
            depends_on=["T001"],
        )
        assert not result.valid
        assert any("itself" in e for e in result.errors)

    def test_sensitive_path_in_write_scope_warns(self):
        result = validate_task_contract(
            task_id="T001",
            agent="executor",
            write_scope=["src/.env"],
        )
        assert len(result.warnings) >= 1

    def test_known_roles_include_all_required(self):
        required = {"security-reviewer", "test-engineer", "debugger", "executor"}
        assert required.issubset(KNOWN_AGENT_ROLES)


class TestValidateBatchIsolation:
    def test_isolated_write_sets_no_conflicts(self):
        tasks = [
            {"task_id": "T1", "write_scope": ["src/a.ts"]},
            {"task_id": "T2", "write_scope": ["src/b.ts"]},
        ]
        assert validate_batch_isolation(tasks) == []

    def test_overlapping_write_sets_conflict(self):
        tasks = [
            {"task_id": "T1", "write_scope": ["src/shared.ts"]},
            {"task_id": "T2", "write_scope": ["src/shared.ts"]},
        ]
        conflicts = validate_batch_isolation(tasks)
        assert len(conflicts) == 1
        assert "src/shared.ts" in conflicts[0]["overlapping_paths"]

    def test_empty_write_sets_skipped(self):
        tasks = [
            {"task_id": "T1", "write_scope": []},
            {"task_id": "T2", "write_scope": []},
        ]
        assert validate_batch_isolation(tasks) == []
```

- [ ] **Step 4: 运行全部测试确认**

```bash
pytest tests/orchestration/test_task_contract_validation.py -q
pytest tests/test_specify_guidance_docs.py -q -k "tasks"
pytest tests/test_alignment_templates.py -q
```

- [ ] **Step 5: 提交**

```bash
git add tests/test_specify_guidance_docs.py tests/test_alignment_templates.py tests/orchestration/test_task_contract_validation.py
git commit -m "test: add subagent-ready task contract validation coverage"
```

---

### Task 8: 端到端验证

**Files:**
- (验证运行，不修改文件)

- [ ] **Step 1: 运行完整相关测试套件**

```bash
pytest tests/test_specify_guidance_docs.py tests/test_alignment_templates.py tests/orchestration/ tests/codex_team/test_codex_guidance_routing.py tests/contract/test_codex_team_generated_assets.py -q
```

- [ ] **Step 2: 检查 template diff 确保无意外变更**

```bash
git diff main -- templates/
```

审阅所有模板变更，确认：
- `plan/shell.md` 只新增了一条 guardrail
- `tasks/shell.md` 新增了 enriched field 要求
- `tasks-template.md` 新增了 agent 字段和 enriched contract 规则
- `implement.md` 新增了 Pre-Dispatch Validation 节

- [ ] **Step 3: 最终提交（如有多余变更需要 squash）**

```bash
git log --oneline main..HEAD
```

---

## 快速验证入口

```bash
# 模板层
pytest tests/test_specify_guidance_docs.py tests/test_alignment_templates.py -q

# 代码层
pytest tests/orchestration/test_task_contract_validation.py tests/orchestration/ tests/codex_team/ tests/contract/ -q

# 集成层
pytest tests/integrations/ -q -k "claude"

# 完整
pytest -q
```
