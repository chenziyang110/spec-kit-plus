# sp-debug 思考阶段 Subagent 化设计

## 目标

将 sp-debug 第一阶段（GatheringNode 中的 observer framing）从本地规则函数迁移到独立 subagent 执行，实现上下文隔离，让思考推理在不受主对话上下文干扰的环境中完成。

## 核心原则

- **只看项目地图，不碰源码**：subagent 仅基于 feature spec、project-map 文件和症状描述做深度推理
- **尽最大可能猜测**：生成尽可能多的假设候选，每个假设附带 why_it_fits / map_evidence / would_rule_out
- **同步调用**：等待 subagent 返回后才能进入第二阶段调查
- **Phase 2 不受影响**：InvestigatingNode → FixingNode → VerifyingNode 完全不动

## 变更方案

### 架构决策：GatheringNode 内同步调用

改动集中在 `GatheringNode.run()`，不改变状态机拓扑。

### 流程图

```
GatheringNode.run()
  ├─ load context (ContextLoader)           ← 不变
  ├─ _refresh_diagnostic_profile()           ← 不变（纯规则分类，本地执行）
  ├─ _refresh_lane_plan()                    ← 不变
  │
  ├─ [新增] observer_framing 未完成？
  │     └─ _build_think_subagent_prompt()   ← 构建 prompt，存入 state
  │     └─ return await_input("请启动思考 subagent...")  ← 返回分派指令
  │
  ├─ observer_framing 已完成？
  │     └─ gate checks                       ← 不变（expected/actual、repro verified）
  │     └─ return InvestigatingNode()
```

主 agent 收到 await_input 后，用 `think_subagent_prompt` 启动 subagent，等待返回，解析结果填充 `observer_framing`、`transition_memo`、`alternative_cause_candidates`，设 `observer_framing_completed = True`，然后重新进入 GatheringNode。

### 新增文件

#### `src/specify_cli/debug/think_agent.py`

两个函数：

- **`build_think_subagent_prompt(state: DebugGraphState) -> str`**：从 state 提取上下文（feature context、project-map、症状描述、diagnostic profile），渲染 `templates/worker-prompts/debug-thinker.md` 模板，返回 prompt 字符串
- **`parse_think_subagent_result(raw_text: str) -> dict`**：解析 `---` 分隔的混合输出，提取 YAML 结构化区块。给测试和 CLI `--format json` 模式用（实际解析由 AI agent 完成）

#### `templates/worker-prompts/debug-thinker.md`

Subagent 的思考 prompt 模板，包含：

1. **角色定义**：Observer/Framer，不看源码，只基于项目地图做因果推理
2. **输入上下文占位符**：`{{ feature_context }}`、`{{ project_map }}`、`{{ symptoms }}`、`{{ diagnostic_profile }}`
3. **核心指令**：生成至少 3 个假设候选，执行深度因果推理
4. **输出格式规范**：自由分析文本 + `---` + YAML 结构化区块

#### 输出格式

```
[自由分析文本，描述推理过程、关键观察、可能遗漏的问题]

---
observer_framing:
  summary: "..."
  primary_suspected_loop: "scheduler-admission|cache-snapshot|ui-projection|general"
  suspected_owning_layer: "..."
  suspected_truth_owner: "..."
  recommended_first_probe: "..."
  missing_questions: ["...", "..."]
alternative_cause_candidates:
  - candidate: "..."
    why_it_fits: "..."
    map_evidence: "..."
    would_rule_out: "..."
  - candidate: "..."
    ...
transition_memo:
  first_candidate_to_test: "..."
  why_first: "..."
  evidence_unlock: ["reproduction", "logs", "code", "tests"]
  carry_forward_notes: ["..."]
```

### 修改文件

#### `src/specify_cli/debug/graph.py`

`GatheringNode.run()` 变更（约 15 行）：

```python
async def run(self, ctx):
    ctx.state.status = DebugStatus.GATHERING
    ctx.state.current_node_id = "GatheringNode"

    # 1. Load context (不变)
    loader = ContextLoader()
    if not ctx.state.context.feature_id:
        feature_dir = loader.find_active_feature()
        if feature_dir:
            ctx.state.context = loader.load_feature_context(feature_dir)
    if not ctx.state.recently_modified:
        ctx.state.recently_modified = loader.get_recent_git_changes()

    _refresh_diagnostic_profile(ctx.state)
    _refresh_lane_plan(ctx.state)

    # 2. [变更] Observer Framing — 通过 subagent
    if not ctx.state.observer_framing_completed:
        prompt = build_think_subagent_prompt(ctx.state)
        ctx.state.think_subagent_prompt = prompt
        return await_input(
            ctx.state,
            "Observer framing needed. Please spawn a think subagent with "
            "think_subagent_prompt, wait for its structured result, then "
            "populate observer_framing, transition_memo, and "
            "alternative_cause_candidates. Set observer_framing_completed=True "
            "and continue."
        )

    # 3. Gate checks (不变)
    if not ctx.state.symptoms.expected or not ctx.state.symptoms.actual:
        return await_input(...)
    if not ctx.state.symptoms.reproduction_verified:
        return await_input(...)

    return InvestigatingNode()
```

`_populate_observer_framing()` 函数保留但标记为 deprecated（非破坏性保留，用于向后兼容和测试）。

#### `src/specify_cli/debug/schema.py`

新增字段 `think_subagent_prompt: Optional[str] = None` 到 `DebugGraphState`，用于在 await_input 消息中传递 subagent prompt。

### 影响范围

| 层 | 改动 |
|---|---|
| `graph.py` | GatheringNode 约 15 行变更 |
| `schema.py` | 新增 1 个字段 |
| `think_agent.py` | 新增 ~60 行 |
| `debug-thinker.md` | 新增 ~50 行模板 |
| Phase 2 节点 | 不动 |
| 状态机图定义 | 不动 |
| `dispatch.py` | 不动 |
| `cli.py` | 不动 |
| `integrations/base.py` | `_augment_debug_skill()` 新增 think-subagent 分派指南段落 |
| 测试 | 新增 think_agent 单元测试 |

### `_augment_debug_skill()` 补充

在现有 "Leader Gate" 和 "Subagent Evidence Collection" 之间，新增一段 **Think Subagent Dispatch** 指南：

- 当 GatheringNode 返回包含 `think_subagent_prompt` 的 await_input 时，AI agent 必须启动一个 think subagent
- think subagent 不碰源码，只使用项目地图做推理
- AI agent 等待 think subagent 返回后，解析 `---` 分隔的混合输出，填充 `observer_framing` 等字段
- 设 `observer_framing_completed = True` 后重新进入 GatheringNode

## 测试策略

- **`test_think_agent.py`**：测试 prompt 构建包含必要上下文、结果解析正确处理混合格式
- **`test_debug_graph.py`**：验证 GatheringNode 在 observer_framing 未完成时返回 await_input 且包含 think_subagent_prompt
- **`test_debug_graph_nodes.py`**：验证 observer_framing 已完成时直接进入门控检查
