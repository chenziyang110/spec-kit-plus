# sp-debug 生命周期硬化设计

Date: 2026-05-02
Status: Approved for implementation planning

## Goal

将 `sp-debug` 从“调查加修复”的局部流程，提升为一个证据驱动、可回流、可验收、可恢复的完整缺陷生命周期。

目标是同时解决三个问题：

- 第一阶段 `observer framing` 只有“要求发散”，没有“发散合格”的硬门槛
- 机器验证与用户验收没有被建模为两个不同的闭环
- 用户验收发现还有问题时，流程没有把“原问题没修净”和“修复引入衍生问题”明确区分

## Problem Statement

当前 `sp-debug` 的设计文档、模板约束、运行时状态机之间已经出现分叉：

- 调试模板把 **Human Verification** 写成主流程的一部分
- 运行时状态机目前在 `VerifyingNode` 通过后直接进入 `ResolvedNode`
- `awaiting_human_verify` 主要被实现成“自动验证跑不下去后的人工接管态”，而不是正式验收态
- 第一阶段虽然要求列出多个 `alternative_cause_candidates`，但运行时没有强制“候选数量、候选多样性、候选归档去向”形成完整 contract
- 当前 `fail_count` 同时承载自动验证失败和后续人工反馈的复杂场景，导致复验回流的语义不清晰

结果是：

- 第一阶段容易出现“假发散”：列了多个候选，但其实都在猜同一个 truth owner
- 自动验证通过后会过早收口，绕过真正的人类验收闭环
- 用户说“还有问题”时，系统容易把“原问题没修净”包装成 follow-up，从而错误归档父会话

## Design Principles

- **发散必须可审计**：第一阶段不是“多写几条猜测”，而是建立合格的候选问题空间
- **控制闭环优先于表面症状**：根因、修复、验证都围绕 truth owner、control state、closed loop 建模
- **机器验证和用户验收分层**：自动验证解决“本地证据是否恢复”，用户验收解决“真实使用是否结束”
- **默认保守回流**：只要不能明确证明是新问题或衍生问题，就按“原问题未修净”回到原会话
- **候选必须有归宿**：第一阶段提出的高优先候选，后续必须进入 `confirmed`、`ruled_out`、`still_open_but_deprioritized` 之一
- **恢复优先于便利**：任何 resume 行为都必须保持当前 debug session 作为唯一真相，不允许凭聊天记忆收口

## Proposed Lifecycle

`sp-debug` 的主流程改成 6 个一等阶段：

1. `framing`
2. `investigating`
3. `fixing`
4. `agent_verifying`
5. `human_verifying`
6. `resolved`

### Lifecycle Semantics

#### `framing`

只允许 observer framing。

- 不读源码
- 不读测试
- 不跑 repro
- 不读日志

它的目标不是给出根因结论，而是建立候选问题空间、truth-owner 假设和第一轮证据计划。

#### `investigating`

允许进入 reproduction、logs、code、tests、instrumentation。

它的目标是压缩候选空间，补全：

- truth ownership
- control state
- observation state
- closed loop
- decisive signals
- 替代假设裁决

#### `fixing`

只接受最小根因修复。

`surface-only` 修复不能作为可关闭路径，只能作为被拒绝的修复尝试记录。

#### `agent_verifying`

自动验证阶段。

它回答的问题是：

`当前 fix 是否在可自动验证的边界内恢复了控制闭环？`

#### `human_verifying`

正式用户验收阶段。

它回答的问题是：

`真实使用场景里，这个问题是否真的结束了？`

#### `resolved`

只有同时满足以下条件才允许进入：

- 自动验证通过
- loop restoration proof 已记录
- 用户验收通过
- 没有待处理的 reopen / child follow-up 依赖

## State Transitions

### Main Path

- `framing -> investigating`
  - 前提：framing gate 通过
- `investigating -> fixing`
  - 前提：root-cause gate 通过
- `fixing -> agent_verifying`
  - 前提：fix scope 不是 `surface-only`
- `agent_verifying -> human_verifying`
  - 前提：自动验证通过，且 `loop_restoration_proof` 已记录
- `human_verifying -> resolved`
  - 前提：用户明确确认通过

### Failure / Re-entry Path

- `agent_verifying -> investigating`
  - 前提：自动验证失败
- `human_verifying -> investigating`
  - 前提：用户反馈仍是同一问题，或无法证明是别的问题
- `human_verifying -> child_session`
  - 前提：修复引入衍生问题
- `human_verifying -> new_session`
  - 前提：反馈问题与原问题无关

### Semantic Change

`awaiting_human_verify` 的语义改成主流程正式阶段，不再等价于“自动验证用尽后的人工兜底暂停态”。

运行时上可以保留该字段名以降低迁移成本，但产品语义必须改成：

- agent 已完成当前自动验证责任
- 会话尚未关闭
- 正在等待用户基于真实场景做最终验收或回流分类

## Framing Gate

第一阶段必须从“建议发散”升级为“硬门槛发散”。

### Required Gate Fields

Observer framing 通过前，至少要填完：

- `summary`
- `primary_suspected_loop`
- `suspected_owning_layer`
- `suspected_truth_owner`
- `recommended_first_probe`
- `missing_questions`
- `alternative_cause_candidates`
- `transition_memo.first_candidate_to_test`
- `transition_memo.why_first`
- `transition_memo.evidence_unlock`

### Candidate Count

- `full framing`：至少 3 个候选
- `compressed framing`：至少 2 个候选

### Candidate Diversity

候选不能只是同一猜测的不同表述。

至少满足其一：

- 覆盖至少 2 个不同 `suspected_truth_owner`
- 覆盖至少 2 类不同 `failure_shape`

建议的 `failure_shape` 枚举：

- `truth_owner_logic`
- `control_observation_drift`
- `projection_render`
- `cache_snapshot`
- `boundary_contract`
- `config_flag_env`
- `ordering_concurrency`

### Candidate Payload

每个候选必须包含：

- `candidate`
- `failure_shape`
- `why_it_fits`
- `map_evidence`
- `would_rule_out`
- `recommended_first_probe`

### Contrarian Coverage

除了主候选，还必须记录一个“最强反对候选”。

它必须不是主候选的同义改写，而是来自不同 failure shape 或不同 truth-owner 家族。

### Evidence Lane Coverage

`Suggested Evidence Lanes` 不能只服务于主候选。

至少覆盖前 2 个高价值候选，避免整个调查从一开始就只为最喜欢的那个假设服务。

### Fast-Path Constraint

只有在以下条件同时成立时才允许 `compressed framing`：

- 精确错误位置已知
- repro 明确
- 影响面可证明为单模块、低共享面

即使 fast-path，也不能跳过候选空间，只能降低数量要求。

## Investigation Closure Contract

进入 `investigating` 后，第一阶段的高优先候选不能无声消失。

每个高优先候选最终都必须进入以下三类之一：

- `confirmed`
- `ruled_out`
- `still_open_but_deprioritized`

这要求数据模型不再只保留“当前根因”和“已排除假设”，还要明确记录哪些 framing 候选被压低优先级但尚未完全否定。

## Root-Cause Gate

只有满足以下条件才允许从 `investigating` 进入 `fixing`：

- `resolution.root_cause.summary`
- `resolution.root_cause.owning_layer`
- `resolution.root_cause.broken_control_state`
- `resolution.root_cause.failure_mechanism`
- `resolution.root_cause.loop_break`
- `resolution.root_cause.decisive_signal`
- `truth_ownership` 非空
- `control_state` 非空
- `observation_state` 非空
- `closed_loop` 六段齐全
- `decisive_signals` 非空
- 至少 2 个替代假设被记录为 `considered`
- 只要存在多个候选，就至少 1 个被明确 `ruled_out`
- `root_cause_confidence == confirmed`

## Verification Split

自动验证和用户验收必须拆成两条独立闭环。

### Agent Verification Responsibilities

自动验证负责：

- repro 命令
- 定向测试
- 与改动路径相关的最小验证面
- `loop_restoration_proof`

自动验证不负责：

- 替用户断言“真实环境已修复”
- 因为本地测试通过而提前归档会话

### Human Verification Responsibilities

用户验收负责确认：

- 真实场景是否恢复
- 是否还存在同路径残留问题
- 是否出现修复引入的衍生问题
- 是否另有无关新问题需要单开

## Human Re-entry Classification

用户在 `human_verifying` 阶段反馈“还有问题”时，必须做显式分类。

### `same_issue`

定义：

- 症状本质没变
- 同一 truth owner 仍然失败
- 同一 repro path 仍然失败
- 或没有足够证据证明这是另一个问题

动作：

- reopen 原 session
- 状态回到 `investigating`
- 增加 `human_reopen_count`

### `derived_issue`

定义：

- 原问题主路径可能改善
- 但 fix 引入副作用、邻近回归、链路上的衍生故障

动作：

- 创建 `child session`
- 父会话进入 `waiting_on_child_human_followup`
- 子会话关闭后，父会话必须回到 `human_verifying`
- 父会话不能因为 child 结束而自动 `resolved`

### `unrelated_issue`

定义：

- 用户反馈的是独立新问题
- 与当前 truth owner、repro path、修复影响面没有可验证因果关系

动作：

- 新建独立 session
- 原 session 只有在用户同时确认“原问题已解决”时，才允许继续关闭

### Default Policy

分类策略默认保守：

- 能证明 `derived_issue` 才建 child
- 能证明 `unrelated_issue` 才开新 session
- 其余不确定情况，一律按 `same_issue` reopen 原 session

这条默认规则用于防止把“原问题没修净”伪装成 follow-up。

## Data Model Changes

建议补充或调整以下字段。

### Status / Session Fields

- `status`
  - 明确保留或映射出：`framing | investigating | fixing | agent_verifying | human_verifying | resolved`
- `waiting_on_child_human_followup: bool`
  - 父会话是否正在等待 child 关闭后回到 human verification

### Framing Fields

- `alternative_cause_candidates[*].failure_shape`
- `alternative_cause_candidates[*].recommended_first_probe`
- `contrarian_candidate`
- `framing_gate_passed: bool`

### Candidate Resolution Fields

- `candidate_resolutions`
  - 按候选记录其最终状态：
    - `confirmed`
    - `ruled_out`
    - `still_open_but_deprioritized`

### Verification Fields

- `agent_fail_count`
  - 只记录自动验证失败次数
- `human_reopen_count`
  - 只记录用户验收打回次数
- `human_verification_outcome`
  - `pending | passed | same_issue | derived_issue | unrelated_issue | insufficient_feedback`

现有 `fail_count` 应被迁移或拆分，避免把两种验证闭环混成一个数字。

## Runtime Changes

### Graph Layer

`src/specify_cli/debug/graph.py` 需要做的核心改变：

- `GatheringNode` 只对应 `framing`
- `VerifyingNode` 拆语义：
  - 自动验证成功后进入 `AwaitingHumanNode`
  - 不再直接进入 `ResolvedNode`
- `AwaitingHumanNode` 改成正式 `human_verifying` 阶段
- human-verifying 的反馈处理需要支持：
  - reopen 原会话
  - 标记 child dependency
  - 创建独立新 session

### CLI Layer

`src/specify_cli/debug/cli.py` 需要补强：

- 明确输出当前是在 `agent_verifying` 还是 `human_verifying`
- 当用户在 human verification 反馈问题时，做回流分类
- resume 逻辑优先返回：
  - 待 reopen 的原会话
  - 等 child 归来后待继续 human verification 的父会话

### Persistence Layer

`src/specify_cli/debug/persistence.py` 需要：

- 保存新的验证字段和分类字段
- 在 handoff report 中明确区分：
  - 自动验证结果
  - 用户验收状态
  - 回流分类结果
- 对父子 session 的关闭条件进行更严格提示

## Template Changes

### `templates/commands/debug.md`

需要修改：

- 把 Human Verification 从“文档承诺”变成和运行时一致的一等阶段
- 明确 `same_issue / derived_issue / unrelated_issue` 分类
- 明确 `awaiting_human_verify` 的产品语义
- 明确 framing gate 的数量、多样性、候选归宿要求

### `templates/debug.md`

需要修改：

- frontmatter 和正文结构中加入：
  - `framing_gate_passed`
  - `contrarian_candidate`
  - `candidate_resolutions`
  - `agent_fail_count`
  - `human_reopen_count`
  - `human_verification_outcome`
  - `waiting_on_child_human_followup`

### `templates/worker-prompts/debug-thinker.md`

需要修改：

- 输出每个候选的 `failure_shape`
- 输出 `recommended_first_probe`
- 输出 `contrarian_candidate`
- 强制说明候选必须覆盖至少两个家族，不能只是换说法

## Testing Impact

需要新增或调整的测试类型：

- `framing gate` 测试
  - 候选数量不足时不能进入 investigating
  - 候选多样性不足时不能进入 investigating
- `verification split` 测试
  - 自动验证通过后进入 human verification，而不是 resolved
- `human re-entry` 测试
  - `same_issue` 回到 investigating
  - `derived_issue` 创建 child，并阻止父会话直接 resolved
  - `unrelated_issue` 新开 session，不错误污染父会话
- `persistence` 测试
  - 新字段 round-trip
  - 父子 session 与 reopen 信息能稳定恢复
- `CLI` 测试
  - resume 优先级
  - human verification 状态提示
  - human feedback 分类后的输出

## Migration Strategy

建议按 4 个步骤迁移，避免一次性重写。

### Step 1: 对齐 contract

先更新模板、设计文档、CLI 输出文案和持久化 schema，让产品语义统一。

### Step 2: 拆验证阶段

把 `VerifyingNode -> ResolvedNode` 改成：

- 自动验证通过 -> `AwaitingHumanNode`
- 用户确认通过 -> `ResolvedNode`

### Step 3: 引入 framing hard gate

在 `GatheringNode` 和 think-subagent 结果解析处，补强：

- 候选数量
- 候选多样性
- contrarian coverage
- candidate resolution follow-through

### Step 4: 引入 human re-entry 分类

实现 `same_issue / derived_issue / unrelated_issue` 的分类和回流。

## Out of Scope

本设计暂不覆盖：

- 自动替用户判断真实场景是否已修复
- 多层 child session 的复杂树形批处理
- 跨仓库或跨服务联合 debug session
- 把所有 human feedback 自动 NLP 分类到零误差

## Recommendation

按“先 contract、再验证拆分、再 framing gate、最后 human re-entry”的顺序落地。

原因：

- 当前最危险的问题是“自动验证通过后过早 resolved”
- 其次是“第一阶段假发散”
- 最后才是更细的 child/new 分类自动化

先修主生命周期，再收紧第一阶段质量，最后补回流分类，风险最低，也最容易逐步验证。
