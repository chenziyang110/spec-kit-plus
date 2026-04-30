# sp-deep-research 就绪保障与契约对齐升级设计

**日期**: 2026-05-01
**状态**: Draft
**来源**: 对比 sp-map-scan / sp-map-build 的硬性机制，分析 sp-specify → sp-deep-research → sp-plan 全链路契约

---

## 背景

sp-deep-research 是 sp-specify 与 sp-plan 之间的可行性桥梁。sp-specify 产出 spec 包后，若任一能力链缺乏可信的实现路径，则由 deep-research 协调多子代理并行调研、运行 disposable spike，产出 Planning Handoff 交给 sp-plan。

对比 sp-map-scan 和 sp-map-build，deep-research 在追踪性、证据质量评分、多智能体编排上做得细致，但在**就绪拒绝、反向覆盖验证、预设维度、排除面管理、能力卡片、检查清单化**等方面缺少硬性机制。同时，作为工作流链中的中间环节，它与上游（sp-specify）和下游（sp-plan）的契约存在双向缺口。

本文档定义 22 个改进点，覆盖六大领域：就绪保障、缺口管理、研究覆盖、输出刚性、子代理协议、工作流集成。

---

## 一、就绪保障（原缺失 #1, #2, #6, #11）

### 1.1 就绪拒绝规则（来源：map-build Readiness Refusal Rules）

**现状**: deep-research 仅在 Outline 第 4 步判断"是否需要此门控"，缺少在不满足前置条件时强制中止并输出缺口报告的机制。

**新增**:

在 `deep-research.md` 输出前，执行以下拒绝检查。任一条件触发则**拒绝移交**，输出缺口报告，将 `next_command` 设为 `/sp.clarify` 或标记为 blocked：

- 仍有 CAP 为 `blocked` 且未被用户显式 force-accept
- 任意 CAP 缺少对应的 PH 决策
- 任意 PH 缺少可追溯的证据 ID（EVD / SPK / repo path）
- 任意 TRK 的 subagent 返回了被拒绝的证据包且未重试
- `dispatch_shape: subagent-blocked` 但未记录具体阻塞原因和升级路径

拒绝时输出：

```markdown
## Readiness Refusal Report

| Check | Status | Affected IDs | Missing Evidence |
|-------|--------|-------------|------------------|
| All CAPs have PH | FAIL | CAP-003 | No PH assigned |
| All PHs trace to evidence | FAIL | PH-005 | No EVD/SPK backing |
```

### 1.2 反向覆盖验证（来源：map-build Reverse Coverage Validation）

**现状**: 仅有 Outline 第 12 步 artifact review gate（7 条审查项），没有形式化的矩阵验证。

**新增**:

最终报告前执行覆盖闭合检查矩阵：

- 每个 CAP 必须至少对应一个 PH-ID
- 每个 PH-ID 必须回溯到至少一个证据（EVD / SPK / repo path）
- 每个被标记为 `proven` 的能力不得残留未解决的未知环节
- 每个 `blocked` 的 CAP 必须有明确的阻塞原因和后续步骤
- 检查失败 → 拒绝输出"可规划"结论，缺口写回 `workflow-state.md`

```markdown
## Reverse Coverage Validation

| CAP ID | Has PH? | PH IDs | Has Evidence? | Evidence IDs | Proven/Clean? |
|--------|---------|--------|---------------|-------------|---------------|
| CAP-001 | PASS | PH-001, PH-002 | PASS | EVD-001, SPK-001 | PASS |
| CAP-002 | FAIL | — | — | — | FAIL: No PH assigned |
```

### 1.3 规划就绪检查清单（来源：map-scan Build Readiness Checklist）

**现状**: 没有可逐项审计的完成清单。

**新增**:

在 `deep-research.md` 末尾增加强制检查清单：

```markdown
## Planning Handoff Readiness Checklist

- [ ] 所有 CAP 都有明确退出状态 (proven/constrained/blocked/not-viable)
- [ ] 所有 PH 都有证据来源 (EVD/SPK/repo path)
- [ ] 所有 spike 结果已记录并通过预期
- [ ] 所有残存风险已标记并链接到证据
- [ ] 所有研究排除都有重访条件
- [ ] alignment.md / context.md / references.md / workflow-state.md 已更新
- [ ] Planning Traceability Index 覆盖所有 PH
- [ ] 反向覆盖验证通过
- [ ] 就绪拒绝规则全部 PASS
```

全部通过后才允许推荐 `/sp.plan`。

### 1.4 不可协商的研究语义（来源：map-build Non-Negotiable Build Semantics）

**现状**: Rules 部分已有约束但语言不够强硬。

**新增**:

在 Guardrails 或 Rules 中增加：

- 没有可运行证据（spike 或 repo path trace）的研究通过 = **失败通过**
- 协调者仅凭自身执行、未调度子代理且未记录 `subagent-blocked` = **失败通过**
- 纯文档引用、未读取仓库实际代码路径的可行性结论 = **不足以规划**
- 子代理返回结果无 `paths_read` = **无效证据，必须拒绝**

---

## 二、缺口管理（原缺失 #4, #12, #13）

### 2.1 排除研究区域与重访条件（来源：map-scan excluded buckets）

**现状**: 不研究的部分没有被显式记录。

**新增**:

增加研究排除清单章节：

```markdown
## Research Exclusions

| Excluded Area | Reason | Revisit Condition | Recorded By |
|---------------|--------|-------------------|-------------|
| 性能压测 | 不在本特性范围 | 进入生产部署前 | Coordinator |
| 权限边界 | 由已有 auth module 保证 | auth module 变更时 | TRK-003 |
```

由协调者在合成阶段生成，确保所有未覆盖的面都可见。

### 2.2 差异证据分析（来源：map-build packet evidence vs existing claims）

**现状**: 当 `deep-research.md` 已存在且重新运行时，不做新旧对比。

**新增**:

若 `deep-research.md` 已存在，增加差异分析章节：

```markdown
## Differential Evidence Analysis

| CAP ID | Previous Conclusion | New Evidence | Status Change |
|--------|-------------------|---------------|---------------|
| CAP-001 | proven (EVD-001) | EVD-005 confirms | Unchanged |
| CAP-002 | constrained (EVD-002) | SPK-003 disproves | **OVERTURNED** → blocked |
```

### 2.3 陈旧声明处理（来源：map-build Unknown-Stale / deep_stale）

**现状**: 没有对"曾经证明过但现在可能过时"的能力链的处理。

**新增**:

在退出状态中增加 `stale-needs-revalidation`。当依赖（库、API、平台行为）自上次研究以来发生变化时，相关 CAP 应标记为此状态，并在工作流状态中记录触发变更的依赖和版本。

```markdown
| CAP ID | Previous Status | Staleness Trigger | Action |
|--------|----------------|-------------------|--------|
| CAP-003 | proven (2026-03) | library X v3 → v4 | Revalidate TRK-003 |
```

---

## 三、研究覆盖（原缺失 #3）

### 3.1 预设可行性研究维度清单（来源：map-scan 14 Required Scan Dimensions）

**现状**: 仅依赖 spec 中显式列出的能力去研究。

**新增**:

在构建能力可行性矩阵（Outline 第 5 步）之前，对照以下维度检查是否遗漏横切面：

1. 权限与认证边界
2. 数据量 / 性能包络
3. 错误 / 异常 / 回滚流转
4. 并发 / 一致性
5. 日志 / 可观测性
6. 迁移 / 兼容性
7. 外部依赖 SLO / 失效模式
8. 模板 / 生成代码传播影响
9. 测试可行性（最小可验证路径）
10. 安全 / 密钥 / 敏感数据处理

即使 spec 未提及，每个 CAP 应至少对这些维度做一次"无影响 / 未验证"确认。

---

## 四、输出刚性（原缺失 #5, #9, #10, #20）

### 4.1 能力卡片（来源：map-build Capability Card）

**现状**: Planning Handoff 用 PH-### 扁平列举，缺少固定结构。

**新增**:

对每个 CAP-### 生成 mini 能力卡片，字段：

| Field | Description |
|-------|-------------|
| Purpose | 能力目的 |
| Owner | 归属模块/服务 |
| Truth lives | 实体所在（代码路径/数据表/配置） |
| Entry points | 入口（CLI/API/event/hook） |
| Downstream consumers | 下游消费者 |
| Extend here | 可扩展处 |
| Do not extend here | 不可扩展处 |
| Key contracts | 输入/输出/副作用 |
| Change propagation | 变更影响范围 |
| Minimum verification | 最小验证命令 |
| Failure modes | 已知失败模式 |
| Confidence | Verified / Inferred / Unknown-Stale |

作为 `deep-research.md` 最终输出的一部分。

### 4.2 强制移交溯源索引（加强版）

**现状**: 已有 Planning Traceability Index 但未强制每行有完整证明链。

**新增**:

Planning Traceability Index 改为强制输出，补齐列：

```markdown
| PH ID | CAP ID | TRK ID | Evidence IDs | Evidence Quality | Plan Consumer | Required Plan Action | Mandatory? |
|-------|--------|--------|-------------|-------------------|---------------|----------------------|------------|
| PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | HIGH / blocking | architecture | Use pattern X | mandatory |
| PH-002 | CAP-001 | TRK-002 | EVD-003 | MEDIUM / constraining | data-model | Consider limit Y | optional |
```

新增列：`CAP ID`、`TRK ID`、`Mandatory?`。这确保 sp-plan 可以直接消费并填充 Deep Research Traceability Matrix。

### 4.3 强制冲突解决与矛盾日志

**现状**: 第 9 步提到冲突解决但没有硬性输出。

**新增**:

```markdown
## Contradiction Resolution Log

| Conflict | Evidence A | Evidence B | Resolution | Priority Basis | Suppressed Reason |
|----------|-----------|-----------|------------|----------------|-------------------|
| API version | EVD-002: v3 | EVD-005: v2 | v3 accepted | spike > docs | EVD-005 was outdated doc |
| Unresolved | EVD-007: pattern A | SPK-003: pattern B | **BLOCKED** | — | Contradictory runnable evidence |
```

无法解决的矛盾必须标记为 blocked 并升级。

### 4.4 Planning Handoff 强制性对齐 sp-plan

**现状**: sp-plan step 4 要求 "If deep-research.md exists but lacks a Planning Handoff section → ERROR"，但 deep-research step 4 的 lightweight 模式写 "Not needed"，格式不一致。

**新增**:

即使 gate 判定 Not needed，lightweight 输出的 Planning Handoff 也必须保持结构化格式：

```markdown
## Planning Handoff

- **Handoff IDs**: Not needed
- **Status**: All capabilities have proven implementation chains in repository
- **Recommended approach**: [existing path]
- **Constraints `/sp.plan` must preserve**: [existing boundary]
- **PH items**: None (all capabilities proven)
```

确保 sp-plan 的解析/验证不会因格式不一致而失败。

---

## 五、子代理协议（原缺失 #7, #8, #10, #14）

### 5.1 证据包接收/拒绝协议（来源：map-build packet intake rejection）

**现状**: 定义了子代理证据包需要包含的字段，但未说明不符合时如何处理。

**新增**:

拒绝条件：
- 无 `paths_read`
- `finding` 为空或仅为猜测
- 核心问题未回答
- 违反只读约束（编辑了生产文件）

被拒绝的包记录在 `workflow-state.md` 中，触发重试（最多 1 次）或升级为 `subagent-blocked`。

```markdown
## Evidence Packet Acceptance

| Track | Subagent | Status | Reason if Rejected | Action |
|-------|----------|--------|--------------------|--------|
| TRK-001 | agent-1 | ACCEPTED | — | — |
| TRK-002 | agent-2 | REJECTED | No paths_read | Retry once |
| TRK-003 | agent-3 | REJECTED | Edited source file | BLOCKED, escalate |
```

### 5.2 增强 workflow-state.md 字段覆盖率

**现状**: 现有字段覆盖面不够细粒度。

**新增**字段：

```yaml
active_command: sp-deep-research
phase_mode: research-only
# 新增
track_exit_states:
  TRK-001: enough-to-plan
  TRK-002: blocked
evidence_packet_acceptance:
  accepted: [EVD-001, EVD-002, SPK-001]
  rejected: [{id: EVD-003, reason: "No paths_read"}]
failed_readiness_checks: ["CAP-003 has no PH"]
open_gaps:
  - {id: GAP-001, description: "Performance envelope unverified", severity: medium}
```

### 5.3 子代理结果持久化为独立文件

**现状**: 所有子代理结果折叠进 `deep-research.md` 表格中。

**新增**:

每个子代理证据包持久化为 `FEATURE_DIR/research-evidence/<EVD-###>.json`：

```json
{
  "evidence_id": "EVD-001",
  "track_id": "TRK-001",
  "question": "...",
  "sources_or_repo_evidence": ["path/to/file.ts:42", "https://docs.example.com"],
  "finding": "...",
  "confidence": "high",
  "planning_implications": "...",
  "constraints_for_sp_plan": ["..."],
  "rejected_options": ["..."],
  "residual_risks": ["..."],
  "spike_artifacts": null,
  "evidence_quality": {
    "source_tier": "repo-evidence",
    "reproduced_locally": "yes",
    "recency": "2026-04-28",
    "confidence": "high",
    "plan_impact": "blocking",
    "limitations": "..."
  }
}
```

好处：审计可追溯、压缩恢复后无需重新解析 deep-research.md、sp-plan 可独立引用。

---

## 六、工作流集成（原缺失 #16, #17, #18, #19, #21, #22）

### 6.1 从 spec.md 能力分解显式消费

**现状**: Outline 第 5 步 "Build a capability feasibility matrix" 像是从零开始。

**新增**:

在第 5 步明确：**从 spec.md 的能力分解出发**，每个 spec 中的 capability 对应一个 CAP-###，不要重新发明能力列表。若 spec 中的能力分解不够细，在 deep-research 中拆分并回写 alignment.md。

```markdown
| Spec Capability | CAP ID | Feasibility Status (from alignment.md) | Action |
|-----------------|--------|----------------------------------------|--------|
| User auth flow | CAP-001 | Needed before plan | Research |
| Dashboard export | CAP-002 | Not needed | Skip |
```

### 6.2 读取 alignment.md 可行性状态并优先排序

**现状**: 未明确读取 alignment.md 中 sp-specify 已设置的 feasibility status。

**新增**:

Outline 第 3 步加载上下文时，增加：
- 从 `alignment.md` 读取 Feasibility / Deep Research Gate 状态
- 只对状态为 `Needed before plan` 的能力启动研究轨道
- 状态为 `Not needed` 或 `Completed` 的能力直接跳过
- 状态为 `Blocked` 的能力保留阻塞状态，记录原因

### 6.3 context.md Locked Decisions 作为不可推翻约束

**现状**: 未提及 context.md 的约束作用。

**新增**:

在 Guardrails 中增加：
- `context.md` 中的 Locked Decisions 在 deep-research 期间是**不可推翻的约束**
- 如果研究发现某个 Locked Decision 不可行，标记为 blocked 并升级，**不得静默替换**

### 6.4 区分入口来源：specify 模式 vs clarify 模式

**现状**: 不区分入口来源，行为一致。

**新增**:

读取 `workflow-state.md` 中的 `active_command` 历史判断入口：

- **从 sp-specify 进入**（全新研究）：所有能力从零开始研究
- **从 sp-clarify 进入**（补充研究）：保留已有证据，仅研究新增/变更的能力

在 `deep-research.md` 的 Research Orchestration 章节中记录入口来源：

```markdown
- **Entry source**: sp-specify | sp-clarify
- **Mode**: full-research | supplement-research
- **Preserved evidence**: [list if supplement]
```

### 6.5 PH 条目标记 mandatory/optional/user-decision

**现状**: PH-### 未标记消费优先级。

**新增**:

sp-plan step 6 要求 "Mark any PH-### item not consumed by the plan as deferred, not applicable, or requires user decision"。为支持这一要求，deep-research 的每个 PH 必须预设消费标记：

```markdown
| PH ID | Mandatory? | If not consumed |
|-------|-----------|-----------------|
| PH-001 | mandatory | ERROR in sp-plan |
| PH-002 | optional | can be deferred |
| PH-003 | user-decision | requires user input |
```

---

## 七、保留自身优势（原缺失 #15）

以下 deep-research 已有的优势在升级中必须保留，不被地图技能的同化所削弱：

| 优势 | 说明 |
|------|------|
| 六维证据质量评分 | source tier × reproduced locally × recency × confidence × plan impact × limitations |
| 五态退出状态机 | enough-to-plan / constrained-but-plannable / blocked / not-viable / user-decision-required |
| Pre/Post Extension Hooks | 支持 before_deep_research / after_deep_research 扩展钩子 |
| 三种分级输出模板 | not-needed.md / docs-only-evidence.md / spike-required.md |

---

## 实施优先级

### P0 — 阻塞性（必须首先实施）

| # | 点 | 原因 |
|---|-----|------|
| 1 | 就绪拒绝规则 | 防止带缺口交接 |
| 2 | 反向覆盖验证 | 保证每个 CAP 都有 PH，每个 PH 都有证据 |
| 19 | Planning Handoff 强制对齐 sp-plan | sp-plan 已将此作为 ERROR 条件，不修复会导致断裂 |
| 6 | 规划就绪检查清单 | 可审计的出口标准 |

### P1 — 结构性（应在 P0 后实施）

| # | 点 |
|---|-----|
| 3 | 预设研究维度清单 |
| 4 | 排除研究区域与重访条件 |
| 5 | 能力卡片 |
| 7 | 证据包接收/拒绝协议 |
| 16 | 从 spec.md 能力分解显式消费 |
| 17 | 读取 alignment.md 可行性状态 |
| 20 | Planning Traceability Index 列补全 |

### P2 — 增强性（提升严谨性和可追溯性）

| # | 点 |
|---|-----|
| 8 | workflow-state.md 字段增强 |
| 9 | 强制移交溯源索引 |
| 10 | 冲突解决与矛盾日志 |
| 11 | 不可协商的研究语义 |
| 12 | 差异证据分析 |
| 13 | 陈旧声明处理 |
| 14 | 子代理结果独立持久化 |
| 18 | context.md Locked Decisions 约束 |
| 21 | 区分 specify/clarify 入口 |
| 22 | PH mandatory/optional 标记 |

---

## 不变更项

以下 deep-research 特性保持不变：

- 六维证据质量评分矩阵
- 五态退出状态机
- Pre/Post Extension Hooks 支持
- 三种分级输出模板
- 多子代理并行编排（与地图技能共享此模式）
- 所有 spike 代码隔离在 `FEATURE_DIR/research-spikes/`
- 禁止编辑生产源代码

---

## 相关文件

- `templates/commands/deep-research.md` — 主命令模板
- `templates/command-partials/deep-research/shell.md` — shell partial
- `templates/commands/map-scan.md` — 对照参考（就绪清单、排除桶、扫描维度）
- `templates/commands/map-build.md` — 对照参考（拒绝规则、反向覆盖、能力卡片）
- `templates/commands/specify.md` — 上游（step 13c feasibility gate）
- `templates/commands/plan.md` — 下游（step 4-6 deep-research 消费）
- `templates/commands/clarify.md` — 替代入口（step 7a）
