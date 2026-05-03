# sp-debug 双层观察者设计

Date: 2026-05-03
Status: Approved for implementation planning

## Goal

将 `sp-debug` 的第一阶段从“观察者写一些候选原因”升级为“双层观察者”系统，让阶段 2 在进入源码、日志、测试、repro 之前，先拿到更强的上帝视角和更硬的调查合同。

这次设计主要解决四个问题：

- 调试发散不够，太快锁定单一原因
- 候选虽然有多个，但仍集中在同一根因家族
- 第一阶段产物没有真正约束第二阶段
- 修复当前症状后，缺少同家族相邻风险复核

## Problem Statement

当前 `sp-debug` 已经具备：

- `observer framing`
- `alternative_cause_candidates`
- `transition_memo`
- `truth ownership`
- `candidate-driven investigation`
- repeated failure 后升级到更强诊断路径的文案和部分状态

但这些能力仍然存在三个断裂：

1. 第一阶段偏“写板书”，不是稳定的调查生产器。
2. 第二阶段虽然已经比早期更结构化，但仍容易退化为“围绕一个顺手假设往前推”。
3. 观察结果缺少“根因家族覆盖率”和“每个家族反证点”的硬标准，导致发散看起来很多，实则质量不高。

结果就是：

- 写出了多个候选，但本质都在猜同一层 truth owner
- 看起来有流程图和分析，但阶段 2 仍然是自由发挥
- 修掉一个点后，系统没有制度化地追问“同家族最近邻问题是否仍然存在”

## Design Principles

- **发散质量优先于候选数量**：10 个同类候选不如 4 个跨 family 的候选。
- **先地图，后合同**：先最大化因果发散，再把高价值候选压成阶段 2 必须消费的合同。
- **流程图是辅产物，不是核心价值**：真正进入阶段 2 的是 `causal map` 和 `investigation contract`，不是一张好看的图。
- **默认有最小纪律，复杂问题自动升级**：所有 debug 会话都要消费最小合同；复杂问题进入强合同和 `root_cause mode`。
- **相邻风险是正式 gate，不是好习惯**：修完当前症状不等于结束，必须至少检查一个最近邻风险目标。

## Options Considered

### Option A: 流程图 Agent

只增加一个负责画闭环流程图的 subagent，帮助定位“问题出在流程的哪一环”。

优点：

- 直观
- 对人类理解友好

不足：

- 只能改善可视化，不足以提升候选发散质量
- 无法天然把阶段 1 结果变成阶段 2 的执行约束

### Option B: 因果地图 Agent

用一个更强的第一阶段 subagent 负责系统闭环、truth owner、断裂边、旁路、相邻风险的发散分析。

优点：

- 能显著提升候选家族覆盖率
- 能把“问题在哪一环”升级成“哪类断裂更像真因”

不足：

- 如果没有额外收口层，阶段 2 仍可能不严格消费这些产物

### Option C: 双层观察者

先用 `Causal Map Agent` 做高质量发散，再用 `Investigation Contract Agent` 把结果压成调查合同。

这是本次选定方案。

原因：

- 同时解决“发散不够”和“阶段 2 不消费”的双重问题
- 保留闭环地图和流程图的上帝视角价值
- 与当前 `sp-debug` 已经存在的 candidate-driven 方向一致

## Selected Model

`sp-debug` 的前半段结构升级为：

`Stage 1A Causal Map -> Stage 1B Investigation Contract -> Stage 2 Evidence Investigation -> Stage 3 Fixing -> Stage 4 Verification`

其中：

- `Stage 1A` 必做
- `Stage 1B` 默认生成最小合同
- 复杂问题会从最小合同升级成强合同

### Activation Policy

默认策略：

- 所有 `sp-debug` 会话都先进入 `Stage 1A Causal Map`
- 所有 `sp-debug` 会话都必须消费一个最小合同
- 只有真正单模块、单错误点、低传播风险的问题，才允许压缩而不是跳过

强合同自动触发条件：

- 连续两轮 verification 失败
- 跨模块、shared state、projection/cache、IPC、边界同步类问题
- 当前 evidence 无法区分两个以上高优先候选
- 已经出现一次明显的 `surface fix` 但问题未收敛

## Stage 1A: Causal Map Agent

`Causal Map Agent` 的职责不是“多写几条猜测”，而是从上帝视角构造问题所处的因果闭环。

### Inputs

- 用户症状描述
- `PROJECT-HANDBOOK.md`
- project map / atlas 路由信息
- 调试上下文中的系统边界和 truth-owner 提示

它仍然遵守 observer framing 的硬约束：

- 不读源码
- 不读测试
- 不读日志
- 不跑 repro

### Outputs

它的核心输出建议包括：

- `symptom_anchor`
  - 用户症状首先出现在哪个观察面
- `closed_loop_path`
  - 输入事件 -> control decision -> truth owner -> projection/cache -> external observation
- `failure_families`
  - 至少覆盖 3 个不同根因家族
- `break_edges`
  - 每个家族最可能断裂的边
- `bypass_paths`
  - 旁路、旧状态泄漏、缓存投影覆盖真值等风险
- `adjacent_risk_targets`
  - 与当前问题同 family、同边界、同投影面的相邻风险
- `falsifiers`
  - 每个 family 的关键反证点

### Success Criteria

第一阶段的成功标准从“尽量多写原因”改成：

- 至少覆盖 3 个不同根因家族
- 每个根因家族都给出 `why_it_fits`
- 每个根因家族都给出关键 `falsifier`
- 至少识别 1 个最近邻 `adjacent_risk_target`

建议的根因家族包括：

- `truth_owner_logic`
- `control_observation_drift`
- `projection_render`
- `cache_snapshot`
- `boundary_contract`
- `config_flag_env`
- `ordering_concurrency`

流程图或 `mermaid` 图可以保留，但它只是 `human-facing secondary artifact`，不是唯一产物。

## Stage 1B: Investigation Contract Agent

`Investigation Contract Agent` 负责收口，不负责再次自由发散。

它只消费 `Causal Map Agent` 的结构化结果，把最有价值的候选变成阶段 2 的执行合同。

### Core Outputs

- `primary_candidate`
  - 当前最优先验证的候选
- `contrarian_candidate`
  - 必须来自不同 family
- `adjacent_risk_target`
  - 至少一个最近邻风险目标
- `candidate_queue`
  - 阶段 2 的最小调查顺序
- `probe_plan`
  - 每个候选最先该拿什么 evidence
- `would_rule_out`
  - 什么 evidence 会打掉该候选
- `family_coverage_report`
  - 当前覆盖了哪些根因家族
- `fix_gate_conditions`
  - 满足哪些最小因果条件后才能进入 fixing

### Contract Levels

#### Minimal Contract

所有 `sp-debug` 默认都必须至少消费：

- `primary_candidate`
- `1` 个不同 family 的 `contrarian_candidate`
- `1` 个 `adjacent_risk_target`

#### Strong Contract

复杂问题或升级条件触发时，合同需要补全：

- 完整 `candidate_queue`
- 更明确的 `family_coverage_report`
- 更严格的 `probe_plan`
- 更细的 `fix_gate_conditions`
- 更广的 `adjacent_risk_targets`

## Stage 2: Contract-Driven Investigation

阶段 2 从“自由调查”改成“合同驱动调查”。

这不禁止探索，但每一步探索都必须挂在合同上，说明自己在消解哪个候选、覆盖哪个 family、排查哪个相邻风险。

### Per-Round Requirements

每一轮 evidence action 都必须记录：

- 当前在验证哪个 `candidate`
- 这轮 evidence 预期解决什么歧义
- evidence 成立会强化谁
- evidence 不成立会打掉谁
- 是否影响 `adjacent_risk_target`

并同步更新：

- `candidate status`
- `family coverage`
- `adjacent risk target status`

## Gate to Fixing

进入 `fixing` 前，最小 gate 建议必须满足：

- `primary_candidate` 已拿到正向 evidence
- `contrarian_candidate` 已被 `ruled_out` 或明确 `deprioritized`
- `truth owner` 已具体化
- `break edge` 已定位到闭环中的具体断裂点
- 至少 `1` 个 `adjacent_risk_target` 已检查

不满足这些条件时，不能只因为“已经有一个看起来像根因的解释”就进入 `fixing`。

## Escalation to Root-Cause Mode

满足任一条件时，自动升级到更强调查模式：

- 连续 `2` 轮 verification 失败
- 已出现一次明显 `surface fix`
- 问题涉及 shared state、projection、cache、IPC、跨模块边界
- 当前仍有 `2` 个以上高优先候选无法区分

升级后新增硬约束：

- 禁止继续“先补一个点再说”
- 必须补 decisive instrumentation / trace / state capture
- 必须刷新 `candidate_queue`
- 必须扩大 `adjacent_risk_targets`
- 验证通过后也不能直接 closeout，先做同 family 最近邻复核

## Verification and Closeout

自动验证通过后，不应只问“当前 repro 和 tests 是否恢复”。

还必须检查：

- 当前 fix 是否只修复了表面症状
- `adjacent_risk_target` 是否完成最小复核
- 当前 family 的最近邻路径是否仍然悬空

只有当合同定义的最小相邻风险复核完成后，才能进入最终 closeout。

## Why This Solves the Four Pain Points

### 1. 太快锁定一个原因

因为阶段 2 默认必须消费 `contrarian_candidate`，系统不能只追主候选。

### 2. 候选不够跨家族

因为阶段 1 的成功标准变成“根因家族覆盖率 + 每个家族的反证点”，而不是单纯数量。

### 3. 阶段 2 不消费阶段 1

因为阶段 2 的每一轮调查动作都必须挂到 `causal map` 和 `investigation contract` 上。

### 4. 修完当前点不查相邻路径

因为 `adjacent_risk_target` 已经成为 fixing 和 closeout 前的正式 gate。

## Non-Goals

这次设计不追求：

- 在第一阶段直接得出根因结论
- 让流程图替代 investigation contract
- 把所有简单 bug 都拖进高成本 `root_cause mode`
- 改变 `sp-debug` 后半段所有既有实现细节

## Implementation Implications

后续实现计划需要至少覆盖：

- debug schema / persistence 新增 `causal map` 与 `investigation contract` 状态
- graph runtime 阻止“未消费合同就进入 fixing”
- 复杂问题自动升级到强合同和 `root_cause mode`
- generated `sp-debug` skill、template、session markdown、CLI summary 对齐新的双层观察者语义
- 针对 family coverage、contrarian consumption、adjacent risk gate、root-cause escalation 的回归测试
