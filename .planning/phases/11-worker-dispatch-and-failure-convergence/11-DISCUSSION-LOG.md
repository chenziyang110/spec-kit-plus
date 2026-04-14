# Phase 11: Worker Dispatch and Failure Convergence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-14
**Phase:** 11-worker-dispatch-and-failure-convergence
**Areas discussed:** Failure policy, Safe cross-phase preparation, Join-point completion, Retry and escalation

---

## Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | 任何一个 worker 失败，就让整个 batch 立即失败，并阻塞后续工作 | |
| 2 | 允许同一里程碑里无关的工作继续，只阻塞依赖这个 join point 的后续工作 | |
| 3 | 混合策略：先区分失败类型，有些可恢复，有些直接阻塞里程碑 | Yes |

**User's choice:** 使用推荐项 `3`
**Notes:** 选择 mixed failure handling，与里程碑目标一致，避免“一刀切”地全停或全放行。

---

## Safe Cross-Phase Preparation

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | 不允许，严格按 phase 顺序推进 | |
| 2 | 只允许有限预备：只读分析、脚手架、文档准备这类低风险工作 | Yes |
| 3 | 允许更宽松的预备：只要写集不冲突，就可以提前做后续 phase 的实现工作 | |

**User's choice:** 使用推荐项 `2`
**Notes:** 保持 roadmap order 为默认契约，只放开低风险预备工作，避免提前实现后续 phase 的核心功能。

---

## Join-Point Completion

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | 只有 batch 里的所有任务都成功完成，join point 才算完成 | |
| 2 | 只要所有任务都进入终态即可，部分成功也记录下来 | |
| 3 | 混合策略：按 batch 类型决定 join point 的完成条件 | Yes |

**User's choice:** 使用推荐项 `3`
**Notes:** join point 规则应和 batch 分类、失败分类联动，而不是所有 batch 都套同一完成标准。

---

## Retry and Escalation

| Option | Description | Selected |
|--------|-------------|----------|
| 1 | 不自动重试，失败后立即升级为 blocker | |
| 2 | 固定重试次数，用完后再阻塞 | |
| 3 | 只对明确的瞬时失败自动重试，其余失败立即升级 | Yes |

**User's choice:** 使用推荐项 `3`
**Notes:** 仅对明确瞬时失败做有限重试；逻辑错误、计划错误、写集冲突等确定性失败直接升级。

---

## the agent's Discretion

- 允许 planner 决定批次分类命名、重试预算数值、以及 blocker 元数据的具体字段名。

## Deferred Ideas

- 将同样的 leader/worker 运行时模型推广到 `debug`
- 更持久化的协调后端或全 DAG 调度
- 更丰富的状态可视化和用户文档对齐（Phase 12）
