# sp-debug 因果调查闭环设计

Date: 2026-05-03
Status: Approved for implementation planning

## Goal

将 `sp-debug` 从“收到一个症状就修一个点”的局部调试流程，升级为“候选消解 + 根因闭环 + 关联风险复核”的因果调查流程。

这次设计要解决的核心问题不是 think-subagent 写得不够多，而是第一阶段的观察产物没有在第二阶段之后形成强执行约束，导致运行时容易退化成：

- 用户说一个问题，系统只修这个问题
- 缺少对竞争根因的消解
- 缺少对相邻路径、相邻状态面、相邻观察面的举一反三
- 连续失败后仍然继续点状打补丁

## Problem Statement

当前 `sp-debug` 已经具备：

- `observer framing`
- `alternative_cause_candidates`
- `transition_memo`
- `truth ownership`
- `closed loop`
- repeated failure 后的诊断升级文案

但这些能力还没有组合成真正的“调查执行器”。

现状中的主要断裂点：

1. 第一阶段 think-subagent 的输出主要用于通过 observer gate 和写入 session，不是后续阶段必须执行的合同。
2. `InvestigatingNode` 没有显式消费 `first_candidate_to_test`、`contrarian_candidate`、`alternative_cause_candidates` 作为调查顺序和收口约束。
3. `FixingNode` 进入条件更接近“已经写出了一个看起来像根因的说明”，而不是“已经对竞争解释做了足够消解”。
4. `VerifyingNode` 仍然以“当前 repro 和 tests 是否通过”为主要收口条件，对“同类问题是否可能仍在相邻路径中存在”缺少制度化检查。
5. 自动验证连续失败时虽然会提示加 instrumentation，但没有切换到明确的 `root_cause mode`，仍可能继续重复局部修补。

结果就是：

- 第一阶段像“写板书”，第二阶段像“自由发挥”
- session 里看起来有推理，运行时却不受这些推理约束
- 难问题会卡在“改一点 -> 测一下 -> 再改一点”的死循环

## Design Principles

- **观察结果必须可执行**：第一阶段不是说明文，而是后续调查合同。
- **根因优先于症状**：运行时优先解释 truth owner、control state、boundary break，而不是先修外部表现。
- **竞争解释必须有归宿**：高优先候选不能无声消失，必须进入 `confirmed`、`ruled_out` 或 `deprioritized`。
- **复杂问题必须自动升级**：连续验证失败后，不允许继续自由补丁，必须切换到 root-cause mode。
- **举一反三必须制度化**：相关问题扫描不能依赖操作者自觉，要成为 closeout 前的正式 gate。
- **简单问题保留轻量路径**：普通问题允许轻量关联扫描，复杂问题再升级为重度模式。

## User-Facing Outcome

这次改造后，`sp-debug` 的默认行为应当变成：

1. 先把问题归入一个根因家族，而不是立刻修一个点。
2. 明确记录最先验证哪个候选，为什么先验证它。
3. 每轮实验都说明它在消解哪个候选，以及它如何影响其他候选。
4. 没有足够的因果覆盖时，不能进入 fixing。
5. fixing 后不仅要验证当前问题，还要做轻量的相邻风险复核。
6. 连续两轮失败后自动进入 root-cause mode，禁止继续表面修补。

## Proposed Model

### 1. 调查合同层

在现有 `observer_framing` 和 `transition_memo` 之上，引入一层显式“调查合同”。

合同不是替代现有字段，而是把它们组织成运行时必须消费的结构。建议至少包含：

- `primary_candidate_id`
- `candidate_queue`
- `related_risk_targets`
- `investigation_mode`
- `escalation_reason`
- `causal_coverage_state`

其中：

- `primary_candidate_id` 表示当前优先验证的候选解释
- `candidate_queue` 表示待消解的候选根因列表
- `related_risk_targets` 表示与当前根因家族相邻的风险路径或状态面
- `investigation_mode` 取值 `normal | root_cause`
- `escalation_reason` 说明为什么进入 `root_cause`
- `causal_coverage_state` 记录是否满足进入 fixing / closeout 的因果覆盖要求

### 2. 候选驱动调查

`InvestigatingNode` 不再是开放式调查阶段，而是候选驱动阶段。

每轮调查动作必须绑定一个 candidate，并回答：

- 当前在验证哪个 candidate
- 需要什么 evidence 才能推进该 candidate 的判定
- 新 evidence 会让该 candidate 变成 `confirmed`、`ruled_out`，还是 `deprioritized`
- 这个 evidence 会不会改变其他 candidate 的优先级

这意味着第一阶段的 `first_candidate_to_test` 必须真正映射到 `candidate_queue` 里的第一项，而不能只停留在文案里。

### 3. 调查模式分层

`sp-debug` 引入两种运行模式：

- `normal`
- `root_cause`

#### `normal`

面向普通问题，强调速度，但仍保持因果纪律。

流程：

- observer framing
- 生成调查合同
- 验证 `primary_candidate`
- 更新 candidate 状态
- 满足因果 gate 后进入 fixing
- 完成轻量关联扫描后 closeout

#### `root_cause`

面向困难问题和反复失败问题，强调系统性收敛。

流程：

- 重建或刷新 `candidate_queue`
- 明确 truth ownership
- 补 decisive instrumentation
- 执行 boundary trace
- 复核 `related_risk_targets`
- 满足更严格的因果 gate 后才允许 fixing

一旦进入 `root_cause`，默认不自动降级，除非新 evidence 明确表明问题已收敛到单一根因。

## Escalation Rules

任一条件满足时，自动从 `normal` 升级到 `root_cause`：

- 连续两轮验证失败
- 同一 session 出现多个 `rejected_surface_fixes`
- 当前 evidence 无法区分两个以上高优先级 candidate
- 关键边界缺乏 decisive instrumentation

升级后增加三条硬约束：

- 禁止继续追加新的点状 fix
- 必须补充 instrumentation / trace / state capture
- 必须刷新 `candidate_queue` 和 `related_risk_targets`

## State Model Changes

建议在 `src/specify_cli/debug/schema.py` 中新增以下结构。

### Candidate State

每个调查候选建议包含：

- `candidate_id`
- `candidate`
- `family`
- `status`
- `why_it_fits`
- `map_evidence`
- `would_rule_out`
- `recommended_first_probe`
- `evidence_needed`
- `evidence_found`
- `related_targets`

`status` 建议取值：

- `pending`
- `active`
- `confirmed`
- `ruled_out`
- `deprioritized`

### Investigation Contract State

建议新增一个聚合结构，例如 `InvestigationContractState`：

- `primary_candidate_id`
- `candidate_queue`
- `related_risk_targets`
- `investigation_mode`
- `escalation_reason`
- `causal_coverage_state`

### Related Risk Target

每个关联风险目标建议包含：

- `target`
- `reason`
- `scope`
- `status`
- `evidence`

`status` 建议取值：

- `pending`
- `checked`
- `cleared`
- `needs_followup`

### Causal Coverage State

建议至少记录：

- `competing_candidate_ruled_out`
- `truth_owner_confirmed`
- `boundary_break_localized`
- `related_risk_scan_completed`
- `closeout_ready`

## Graph Changes

### GatheringNode

新增合同一致性 gate：

- `transition_memo.first_candidate_to_test` 必须能在 `candidate_queue` 中找到对应项
- `contrarian_candidate` 必须来自不同 family 或不同 truth-owner 家族
- `related_risk_targets` 不能为空，至少要识别最近邻风险面

如果这些条件不满足，observer gate 不通过。

### InvestigatingNode

新增候选执行逻辑：

- 如果没有 active candidate，则激活 `primary_candidate_id`
- 每轮 evidence 必须归属到一个 candidate
- candidate 被更新后，同步刷新 `causal_coverage_state`
- 只有满足 root-cause gate 才能进入 `FixingNode`

### FixingNode

新增因果 gate：

- root cause 指向明确 truth owner
- 至少一个竞争 candidate 被 `ruled_out`
- `closed_loop.break_point` 已具体化
- `related_risk_targets` 已识别并至少完成最小复核计划

不满足则返回 `InvestigatingNode` 或留在当前节点等待补证据。

### VerifyingNode

自动验证通过后，不再只检查 repro 和 tests。

还必须检查：

- 当前修复是否只影响表面症状
- `related_risk_targets` 是否至少完成轻量复核
- 是否存在“当前点恢复，但同家族相邻路径仍悬空”的情况

若上述未满足，不能进入 `awaiting_human_verify`。

## Related Risk Scan

“举一反三”不做成全仓大扫荡，而做成分层复核。

### 轻量关联扫描

在 `normal` 模式中默认执行，范围控制在最近邻：

- 同 truth owner
- 同 boundary
- 同 observation surface

目标是回答：

- 这个根因家族还可能污染哪 1 到 3 个相邻路径
- 当前 fix 是否只修复了一个表面表现

### 重度关联扫描

在 `root_cause` 模式中执行，范围可扩展到：

- 相同 family 的其他模块
- 相同 state boundary 的其他入口
- 相同 observation path 的其他投影视图

目标是回答：

- 问题是否属于可传播的根因家族
- 当前修复是否需要拆成 follow-up lanes 或 follow-up sessions

## Prompt and Template Changes

### `templates/worker-prompts/debug-thinker.md`

think-subagent prompt 需要从“生成多个候选”升级为“生成调查合同输入”。

新增要求：

- 给每个 candidate 一个稳定 `candidate_id`
- 明确 `family`
- 产出 `related_risk_targets`
- 指定 `primary_candidate_id`
- 给出“进入 root-cause mode 时最应该先补哪类 instrumentation”

### `templates/commands/debug.md`

需要把现有文案收紧成：

- 第一阶段输出是后续调查合同，不是建议
- 第二阶段必须按 candidate queue 推进
- 连续失败自动进入 root-cause mode
- closeout 前必须完成相关风险复核

### `templates/debug.md`

session 模板需要新增：

- Investigation Contract
- Candidate Queue
- Related Risk Targets
- Investigation Mode
- Causal Coverage State

## Testing Strategy

测试分四层。

### 1. Template Guidance Tests

确保指导语不会回退成“observer framing 可写可不写”：

- 候选驱动调查
- root-cause mode
- related risk scan
- fixing / closeout causal gates

### 2. Schema and Persistence Tests

确保以下内容可稳定 round-trip：

- `candidate_queue`
- `investigation_mode`
- `related_risk_targets`
- `causal_coverage_state`

### 3. Graph Behavior Tests

重点验证：

- 未完成 candidate 消解时不能进入 fixing
- 连续两轮失败后自动切到 `root_cause`
- 未完成关联扫描时不能进入最终 closeout
- evidence 更新会同步刷新 candidate 状态

### 4. CLI / Session Experience Tests

确保操作者能看到：

- 当前在验证哪个 candidate
- 为什么现在不能继续打补丁
- 哪些竞争解释还未被裁决
- 哪些相邻风险仍待复核

## Rollout Plan

建议分三步落地。

### Step 1

先把调查合同字段和 gate 接进 graph。

目标：

- 第一阶段产物真正约束第二阶段
- `InvestigatingNode` 从自由调查改为候选驱动调查

### Step 2

加入 `root_cause mode` 和自动升级规则。

目标：

- 解决复杂问题卡在点状补丁循环的问题

### Step 3

加入轻量关联扫描和 closeout gate。

目标：

- 把“举一反三”变成默认行为，而不是依赖操作者经验

## Non-Goals

这次设计不做以下事情：

- 不把 `sp-debug` 变成全自动跨仓库根因平台
- 不要求简单问题一开始就做重型系统审计
- 不强制所有 bug 都生成多 session、多 lane 的团队流程
- 不在本设计中引入新的外部依赖或 MCP 前置条件

## Risks and Mitigations

### 风险 1：简单问题变重

缓解：

- 默认分 `normal` 和 `root_cause`
- 轻量关联扫描只看最近邻风险

### 风险 2：状态模型膨胀

缓解：

- 把新增字段聚合在 Investigation Contract 下
- 通过 persistence tests 保证 round-trip 可控

### 风险 3：candidate queue 变成形式主义

缓解：

- 强制 `InvestigatingNode` 和 `FixingNode` 消费 queue
- 不满足因果 gate 不能推进

## Acceptance Criteria

设计落地后，应满足以下验收标准：

1. 第一阶段 think-subagent 的结果能直接驱动第二阶段调查顺序。
2. `sp-debug` 不再允许在未裁决竞争 candidate 的情况下直接进入 fixing。
3. 连续两轮验证失败会自动切换到 `root_cause mode`，阻止继续点状补丁。
4. closeout 前必须完成轻量的相关风险复核。
5. session 文件能清楚回答：
   - 现在在验证哪个候选
   - 哪些候选已被排除
   - 当前根因为何比竞争解释更强
   - 哪些相关路径已经举一反三地检查过

## Next Step

这份设计经用户审阅确认后，下一步应进入实现计划编写，拆成：

- state/schema lane
- graph/runtime lane
- template/prompt lane
- persistence/reporting lane
- test/verification lane
