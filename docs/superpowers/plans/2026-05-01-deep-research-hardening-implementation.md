# sp-deep-research 就绪保障升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 sp-deep-research 补齐 22 个就绪保障、缺口管理、上下游契约对齐的硬性机制，使其与 sp-map-scan / sp-map-build 达到同等的交接严谨度。

**Architecture:** 主要修改 `templates/commands/deep-research.md`（主模板），少量修改 `templates/command-partials/deep-research/shell.md`（partial），新增 `tests/test_deep_research_template_guidance.py`（模板验证测试）。不改动 sp-specify、sp-plan 等其他命令。

**Tech Stack:** Markdown 模板、Python pytest

---

## 文件结构

| 文件 | 职责 | 变更类型 |
|------|------|---------|
| `templates/commands/deep-research.md` | 主命令模板，包含全部工作流逻辑 | 大量修改 |
| `templates/command-partials/deep-research/shell.md` | shell partial（Output Contract、Guardrails、Process） | 少量修改 |
| `tests/test_deep_research_template_guidance.py` | 模板合同验证测试 | 新建 |

---

### Task 1: 新增就绪拒绝规则（P0, #1）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** 在 `## Rules` 之前插入新章节 `## Readiness Refusal Rules`

- [ ] **Step 1: 在 Rules 前插入 Readiness Refusal Rules 章节**

在 `templates/commands/deep-research.md` 中，找到 `## Rules` 行（约第 467 行），在其**之前**插入以下章节：

```markdown
## Readiness Refusal Rules

Before writing final `deep-research.md` and recommending `/sp.plan`, run every
check below. If **any** check fails, refuse handoff, produce a gap report, and
set `next_command` to `/sp.clarify` or mark the phase as blocked.

- [ ] Every CAP has at least one PH-ID assigned
- [ ] Every PH-ID traces to at least one evidence ID (`EVD-###`, `SPK-###`, or live repository path)
- [ ] No CAP remains `blocked` without an explicit user force-accept recorded in `alignment.md`
- [ ] No `proven` CAP still has unresolved unknown links in its implementation chain
- [ ] Every dispatched subagent returned an accepted evidence packet; rejected packets were retried or escalated
- [ ] `dispatch_shape: subagent-blocked` is recorded with a concrete block reason and escalation path
- [ ] Every spike with a defined hypothesis was run and has a captured pass/fail result

When refusal happens, output a gap report inline before the refusal decision:

```markdown
## Readiness Refusal Report

| Check | Status | Affected IDs | Missing / Reason |
|-------|--------|-------------|-------------------|
| All CAPs have PH | FAIL | CAP-003 | No PH assigned |
| All PHs trace to evidence | FAIL | PH-005 | No EVD/SPK/repo path |
| ... | PASS | — | — |

**Decision**: Handoff refused. Next command: `/sp.clarify`
```
```

- [ ] **Step 2: 验证模板解析**

运行 `pytest tests/test_deep_research_template_guidance.py -v`（测试文件稍后创建，此步骤先确认模板语法无错误）

先手动验证：检查插入位置正确、markdown 语法无误、无残留占位符。

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add Readiness Refusal Rules to sp-deep-research"
```

---

### Task 2: 新增反向覆盖验证（P0, #2）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** 在 Outline 第 12 步 artifact review gate 之后（约第 442 行后），作为第 12b 步插入

- [ ] **Step 1: 在 artifact review gate 后插入反向覆盖验证步骤**

在 `12. **Run an artifact review gate**` 步骤结束后、`13. **Write or update WORKFLOW_STATE_FILE**` 之前，插入新步骤：

```markdown
12b. **Run reverse coverage validation**:
    - Prove every CAP has at least one PH-ID.
    - Prove every PH-ID traces back to at least one evidence item (`EVD-###`, `SPK-###`, or live repository path).
    - Prove every `proven` CAP has no remaining unresolved unknown links.
    - Prove every `blocked` CAP has a concrete block reason and next action.
    - Prove every accepted evidence packet was consumed by at least one PH or explicitly deferred.
    - If any check fails, refuse handoff and write gaps back to `workflow-state.md`.

    ```markdown
    ## Reverse Coverage Validation

    | CAP ID | Has PH? | PH IDs | Has Evidence? | Evidence IDs | Proven / Clean? |
    |--------|---------|--------|---------------|-------------|-----------------|
    | CAP-001 | PASS | PH-001, PH-002 | PASS | EVD-001, SPK-001 | PASS |
    | CAP-002 | FAIL | — | — | — | FAIL: No PH assigned |

    **Decision**: [PASS / FAIL — if FAIL, refuse handoff]
    ```
```

- [ ] **Step 2: 更新 Outline 步骤编号**

由于插入 12b，后续步骤 13、14 需要确认编号不受影响（它们在 markdown 中是有序列表，手动编号不影响渲染，但应保持一致）。

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add Reverse Coverage Validation to sp-deep-research"
```

---

### Task 3: 新增规划就绪检查清单（P0, #6）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** 在 `deep-research.md` 输出模板的 `## Next Command` 之前插入 `## Planning Handoff Readiness Checklist`

- [ ] **Step 1: 在 full structure 输出模板中插入检查清单**

找到 full structure 输出模板（约第 298-420 行的 markdown 代码块），在 `## Next Command` 行之前插入：

```markdown
## Planning Handoff Readiness Checklist

- [ ] All CAPs have explicit exit status (`proven` / `constrained` / `blocked` / `not-viable`)
- [ ] All PH items trace to evidence (EVD/SPK/repo path)
- [ ] All spike results recorded with pass/fail outcome
- [ ] All residual risks explicitly linked to evidence IDs
- [ ] All research exclusions have revisit conditions
- [ ] `alignment.md` updated with feasibility result and Planning Gate Recommendation
- [ ] `context.md` updated with implementation-chain evidence, constraints, rejected options
- [ ] `references.md` updated with external sources
- [ ] `workflow-state.md` updated with exit criteria and `next_command`
- [ ] Reverse Coverage Validation passed (all CAP→PH→Evidence chains closed)
- [ ] Readiness Refusal Rules all PASS
```

- [ ] **Step 2: 同样在 lightweight 输出模板中插入简化版**

找到 lightweight 结构（约第 272-296 行），在 `## Next Command` 之前插入：

```markdown
## Planning Handoff Readiness Checklist

- [ ] All capabilities have proven implementation chains in repository
- [ ] `alignment.md` updated with `Not needed` feasibility status
- [ ] `context.md` updated
- [ ] `workflow-state.md` updated with `next_command: /sp.plan`
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add Planning Handoff Readiness Checklist to deep-research output"
```

---

### Task 4: 对齐 Planning Handoff 强制格式 + 不可协商研究语义（P0, #19, #11）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** lightweight 输出模板的 Planning Handoff 部分 + Rules 章节

- [ ] **Step 1: 加固 lightweight Planning Handoff 格式**

在 lightweight 输出模板中，将现有的 Planning Handoff 部分替换为结构化格式：

```markdown
## Planning Handoff

- **Handoff IDs**: Not needed
- **Status**: All capabilities have proven implementation chains in repository
- **Recommended approach**: [Existing implementation path `/sp.plan` should use]
- **Constraints `/sp.plan` must preserve**: [Existing boundary, behavior, or constraint]
- **PH items**: None (all capabilities proven — no research-generated handoff items)
```

这确保了 sp-plan step 4 的 "If deep-research.md exists but lacks a Planning Handoff section → ERROR" 不会因格式不一致而触发。

- [ ] **Step 2: 在 Rules 或 Guardrails 中增加不可协商研究语义**

在 `## Rules` 章节末尾或 shell.md 的 `## Guardrails` 章节增加：

```markdown
- A research pass without runnable evidence (spike result or repo path trace) is a failed pass.
- Coordinator-only execution without subagent dispatch justification and recorded `subagent-blocked` reason is a failed pass.
- Feasibility claims based only on documentation citations without live repository path reads are not sufficient for planning.
- Subagent evidence packets without `paths_read` must be rejected; do not accept or synthesize them.
- A structural-only refresh (reformatting findings without new evidence) is a failed pass.
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: harden Planning Handoff format and add non-negotiable research semantics"
```

---

### Task 5: 上游契约消费 — spec 能力 + alignment 状态 + 预设研究维度（P1, #16, #17, #3）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** Outline 第 3 步 + 第 5 步

- [ ] **Step 1: 在第 3 步加载上下文时增加 alignment.md 可行性状态读取**

在 Outline 第 3 步 "Load current spec package and repository context" 的加载列表中，增加显式说明：

```markdown
   - From `FEATURE_DIR/alignment.md`, extract:
     - `Feasibility / Deep Research Gate` status per capability
     - `Planning Gate Recommendation`
     - Capabilities marked `Needed before plan` → these are the research targets
     - Capabilities marked `Not needed` or `Completed` → skip, do not research
     - Capabilities marked `Blocked` → preserve blocker, record reason, do not research unless unblocked
```

- [ ] **Step 2: 重写第 5 步 — 从 spec.md 能力分解出发**

将 Outline 第 5 步 "Build a capability feasibility matrix" 的开头改为：

```markdown
5. **Build a capability feasibility matrix from the spec's capability decomposition**:
   - Start from the capability list in `spec.md`. Each spec capability maps to one CAP-###.
   - Do not invent new capability names; use the spec's decomposition as the source of truth.
   - If a spec capability is too broad for focused research, split it into sub-capabilities (CAP-001a, CAP-001b) and note the split in `alignment.md`.
   - For each capability, read its feasibility status from `alignment.md` and take action:

   | Alignment Status | Action |
   |-----------------|--------|
   | `Needed before plan` | Create research track, assign TRK-### |
   | `Not needed` | Mark `proven` or `not needed`, skip |
   | `Completed` | Preserve existing evidence, skip |
   | `Blocked` | Record blocker, do not research |

   For each capability or module slice, record:
   - stable capability ID (`CAP-###`) — mapped from spec capability name
   - capability name (from spec.md)
   - desired outcome (from spec.md)
   - current evidence from the repository
   - unknown implementation-chain link
   - research questions
   - independent research track owner when delegation is useful
   - whether a disposable demo is required
   - proof target: what evidence would be enough to plan safely
   - result status: `proven`, `constrained`, `not viable`, `blocked`, or `not needed`

   Before finalizing the matrix, check each CAP against the preset research dimensions.
   At minimum, confirm or mark "not applicable" for:
   - permissions / auth boundary
   - data volume / performance envelope
   - error / exception / rollback flow
   - concurrency / consistency
   - logging / observability
   - migration / compatibility
   - external dependency SLO / failure mode
   - template / generated-code propagation
   - minimum verifiable test path
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: consume spec capabilities, alignment status, and preset research dimensions in deep-research"
```

---

### Task 6: 能力卡片 + 增强溯源索引（P1, #5, #9, #20）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** full structure 输出模板中 `## Planning Handoff` 之后

- [ ] **Step 1: 在 Planning Handoff 后插入 Capability Cards 章节**

在 full structure 输出模板的 `## Planning Handoff` 和 `## Planning Traceability Index` 之间插入：

```markdown
## Capability Cards

For each high-value or planning-critical capability, emit a capability card:

### CAP-001: [Capability Name]

| Field | Detail |
|-------|--------|
| **Purpose** | [What this capability achieves] |
| **Owner** | [Owning module / service / surface] |
| **Truth lives** | [Code path, data table, config, or external service] |
| **Entry points** | [CLI command, API route, event handler, hook] |
| **Downstream consumers** | [What depends on this capability] |
| **Extend here** | [Safe extension points] |
| **Do not extend here** | [Fragile or contract-locked areas] |
| **Key contracts** | [Input shape, output shape, side effects, invariants] |
| **Change propagation** | [What breaks when this changes] |
| **Minimum verification** | [Command or check that proves this works] |
| **Failure modes** | [Known ways this can fail] |
| **Confidence** | [Verified / Inferred / Unknown-Stale] |
```

- [ ] **Step 2: 增强 Planning Traceability Index — 补全 CAP ID 和 TRK ID 列**

将现有 `## Planning Traceability Index` 表格从：

```markdown
| Handoff ID | Plan Consumer | Supported By | Evidence Quality | Required Plan Action |
```

改为：

```markdown
| PH ID | CAP ID | TRK ID | Evidence IDs | Evidence Quality | Plan Consumer | Required Plan Action | Mandatory? |
|-------|--------|--------|-------------|-------------------|---------------|----------------------|------------|
| PH-001 | CAP-001 | TRK-001 | EVD-001, SPK-001 | HIGH / blocking | architecture | Use pattern X | mandatory |
| PH-002 | CAP-001 | TRK-002 | EVD-003 | MEDIUM / constraining | data-model | Consider limit Y | optional |
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add Capability Cards and enhanced Traceability Index with CAP/TRK columns"
```

---

### Task 7: 研究排除清单 + 矛盾解决日志（P1, #4, #10）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** full structure 输出模板 + Outline 第 9 步合成阶段

- [ ] **Step 1: 在输出模板中增加 Research Exclusions 章节**

在 `## Capability Cards` 之后插入：

```markdown
## Research Exclusions

Areas, surfaces, or dimensions intentionally not researched in this pass.

| Excluded Area | Reason | Revisit Condition | Recorded By |
|---------------|--------|-------------------|-------------|
| [e.g. performance profiling] | [Not in feature scope] | [Before production deploy] | [Coordinator / TRK-###] |

Every unverified dimension from the preset research checklist that was marked
"not applicable" or "deferred" must appear here with a revisit condition.
```

- [ ] **Step 2: 在输出模板中增加 Contradiction Resolution Log 章节**

在 `## Synthesis Decisions` 之后插入：

```markdown
## Contradiction Resolution Log

When two or more evidence items produce conflicting findings, record the
resolution. Unresolved contradictions must be marked `BLOCKED` and escalated.

| Conflict | Evidence A | Evidence B | Resolution | Priority Basis | Suppressed Reason |
|----------|-----------|-----------|------------|----------------|-------------------|
| [e.g. API version] | EVD-002: v3 | EVD-005: v2 | v3 accepted | spike > docs | EVD-005 was outdated |
| [unresolved] | EVD-007: pattern A | SPK-003: pattern B | **BLOCKED** | — | Contradictory runnable evidence |
```

- [ ] **Step 3: 在 Outline 第 9 步中增加对矛盾日志的引用**

在 `9. **Synthesize research into planning decisions**:` 的 "Resolve conflicts" 行后增加：

```markdown
   - Record every conflict and its resolution in the `Contradiction Resolution Log`.
   - Unresolved conflicts must be marked `BLOCKED` and escalated; do not hide them.
```

- [ ] **Step 4: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add Research Exclusions and Contradiction Resolution Log to deep-research"
```

---

### Task 8: 证据包接收/拒绝协议（P1, #7）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** `## Multi-Agent Research Orchestration` 章节

- [ ] **Step 1: 在子代理证据包要求后增加接受/拒绝协议**

在 Multi-Agent Research Orchestration 中 `Require every subagent to return an evidence packet with:` 列表之后，增加：

```markdown
- [AGENT] After each subagent returns, apply the evidence packet acceptance protocol:
  - **ACCEPT** when: `paths_read` is non-empty, `finding` is specific and evidence-backed, core question is answered, and no production files were edited.
  - **REJECT** when: `paths_read` is empty or missing, `finding` is empty or only speculative, core question is unanswered, or the subagent edited production source files.
  - Record every acceptance and rejection in `workflow-state.md`.
  - For rejected packets: retry once with clarified instructions. If the retry also fails, mark the track as `blocked`, record `subagent-blocked` with the rejection reason, and escalate.
  - Do not silently ignore or synthesize rejected evidence packets.

  ```markdown
  ## Evidence Packet Acceptance

  | Track | Subagent | Status | Reason if Rejected | Action |
  |-------|----------|--------|--------------------|--------|
  | TRK-001 | agent-1 | ACCEPTED | — | — |
  | TRK-002 | agent-2 | REJECTED | No paths_read | Retry once |
  | TRK-003 | agent-3 | REJECTED | Edited source file | BLOCKED, escalate |
  ```
```

- [ ] **Step 2: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add evidence packet acceptance/rejection protocol to deep-research"
```

---

### Task 9: 增强 workflow-state.md 字段 + 证据独立持久化（P1, #8, #14）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** `## Workflow Phase Lock` 章节 + `## Multi-Agent Research Orchestration` 章节

- [ ] **Step 1: 扩展 Workflow Phase Lock 的持久化字段**

在 `## Workflow Phase Lock` 中 `Set or update the state for this run with at least:` 列表，增加以下字段：

```markdown
  - `track_exit_states`: per TRK-### exit state
  - `evidence_packet_acceptance`: accepted and rejected packet lists with reasons
  - `failed_readiness_checks`: list of check IDs that failed
  - `open_gaps`: gap ID, description, severity, and linked CAP/TRK IDs
  - `entry_source`: `sp-specify` | `sp-clarify` (which command routed here)
  - `research_mode`: `full-research` | `supplement-research`
```

- [ ] **Step 2: 在 Multi-Agent Research Orchestration 中增加证据持久化要求**

在协调者责任描述中增加：

```markdown
- [AGENT] After accepting a subagent evidence packet, persist it as
  `FEATURE_DIR/research-evidence/<EVD-###>.json` with the full evidence packet
  fields plus the evidence quality rubric. This enables:
  - independent audit without re-parsing `deep-research.md`
  - direct citation by `/sp.plan` via evidence ID
  - safe context-compaction recovery
```

- [ ] **Step 3: 在 deep-research.md 输出模板的 Evidence Quality Rubric 表格中增加持久化路径列**

在 `## Evidence Quality Rubric` 表格中增加一列 `Persisted`：

```markdown
| Evidence ID | ... | Persisted |
| --- | ... | --- |
| EVD-001 | ... | `research-evidence/EVD-001.json` |
```

- [ ] **Step 4: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: enhance workflow-state fields and add evidence persistence to deep-research"
```

---

### Task 10: 差异证据分析 + 陈旧声明处理（P2, #12, #13）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** Outline 第 3 步之后插入新步骤 + Traceability and Evidence Quality Contract

- [ ] **Step 1: 在第 3 步后增加差异分析步骤**

在 Outline 第 3 步加载上下文之后、第 4 步之前，插入新步骤：

```markdown
3b. **Detect staleness and prior evidence**:
    - If `FEATURE_DIR/deep-research.md` already exists from a prior run, compare
      new findings against prior conclusions.
    - For each CAP with prior evidence, check whether dependencies (library
      versions, API endpoints, platform behavior) have changed since the last
      research pass.
    - Mark CAPs with potentially stale evidence as `stale-needs-revalidation`
      and prioritize their research tracks.
    - Record staleness triggers (version bumps, deprecation notices, etc.) in
      the track description.

    ```markdown
    ## Differential Evidence Analysis

    | CAP ID | Previous Conclusion | Previous Evidence | New Evidence | Status Change |
    |--------|--------------------|--------------------|--------------|---------------|
    | CAP-001 | proven | EVD-001 | EVD-005 confirms | Unchanged |
    | CAP-002 | constrained | EVD-002 | SPK-003 disproves | **OVERTURNED** → blocked |
    | CAP-003 | proven (2026-03) | EVD-004 | lib X v3→v4 | **STALE** → revalidate |
    ```
```

- [ ] **Step 2: 在 Traceability and Evidence Quality Contract 中增加陈旧状态**

在退出状态列表 `Stop each research track when it reaches one of these exit states:` 中增加：

```markdown
  - `stale-needs-revalidation` — prior evidence may no longer be valid due to dependency or platform changes
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add differential evidence analysis and stale claim handling to deep-research"
```

---

### Task 11: Locked Decisions 约束 + 入口来源区分（P2, #18, #21）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** Guardrails + Outline 第 2 步

- [ ] **Step 1: 在 shell.md 的 Guardrails 中增加 Locked Decisions 约束**

在 `templates/command-partials/deep-research/shell.md` 的 `## Guardrails` 章节末尾增加：

```markdown
- Treat `context.md` Locked Decisions as immutable constraints during research.
  Do not research alternatives that contradict a locked decision unless the
  research explicitly proves the locked decision is infeasible, in which case
  mark the affected CAP as `blocked` and escalate; do not silently replace the
  locked decision.
```

- [ ] **Step 2: 在 Outline 第 2 步增加入口来源记录**

在 `2. **Create or resume the workflow state**` 中，增加入口来源判断：

```markdown
   - Determine entry source:
     - If the prior `active_command` in `workflow-state.md` was `sp-specify` →
       `entry_source: sp-specify`, `research_mode: full-research`
     - If the prior `active_command` was `sp-clarify` →
       `entry_source: sp-clarify`, `research_mode: supplement-research`
     - If undetermined → default to `full-research`
   - In `supplement-research` mode, preserve existing evidence and only research
     newly added or changed capabilities.
   - Record entry source and research mode in `deep-research.md` Research
     Orchestration section.
```

- [ ] **Step 3: Commit**

```bash
git add templates/commands/deep-research.md templates/command-partials/deep-research/shell.md
git commit -m "feat: add Locked Decisions constraint and entry source distinction to deep-research"
```

---

### Task 12: PH 条目标记 mandatory/optional/user-decision（P2, #22）

**Files:**
- Modify: `templates/commands/deep-research.md`

**变更位置:** output template `## Planning Handoff` 章节

- [ ] **Step 1: 在 Planning Handoff 每个 PH 条目中增加消费标记**

在 `## Planning Handoff` 章节末尾增加说明，并要求每个 PH 条目标记消费优先级：

```markdown
- **PH consumption contract**:
  - `mandatory` — `/sp.plan` must consume this PH; omitting it is a plan error.
  - `optional` — `/sp.plan` may defer if the plan does not need it.
  - `user-decision` — `/sp.plan` must ask the user before consuming or deferring.

  Each PH item in the Traceability Index must carry its consumption contract in
  the `Mandatory?` column.

  ```markdown
  | PH ID | ... | Mandatory? | If not consumed |
  |-------|-----|-----------|-----------------|
  | PH-001 | ... | mandatory | ERROR in sp-plan |
  | PH-002 | ... | optional | can be deferred |
  | PH-003 | ... | user-decision | requires user input |
  ```
```

- [ ] **Step 2: Commit**

```bash
git add templates/commands/deep-research.md
git commit -m "feat: add PH consumption contract (mandatory/optional/user-decision) to deep-research"
```

---

### Task 13: 更新 shell.md partial + 最终集成检查（P2）

**Files:**
- Modify: `templates/command-partials/deep-research/shell.md`

- [ ] **Step 1: 更新 shell.md 的 Output Contract**

在 `## Output Contract` 中增加新的持久化输出：

```markdown
- Persist accepted evidence packets as `FEATURE_DIR/research-evidence/<EVD-###>.json`.
```

- [ ] **Step 2: 更新 shell.md 的 Process 列表**

在 `## Process` 列表中，增加对新增步骤的简要引用：

```markdown
- Run reverse coverage validation before handoff: every CAP → PH → Evidence chain must close.
- Run readiness refusal checks; refuse handoff with a gap report when checks fail.
- Run the Planning Handoff Readiness Checklist; do not recommend `/sp.plan` until all items pass.
```

- [ ] **Step 3: 全文件一致性检查**

对照 spec 的 22 个点，逐项确认在模板中已落地：

| # | 检查项 | 落地位位置 |
|---|--------|-----------|
| 1 | 就绪拒绝规则 | Readiness Refusal Rules 章节 |
| 2 | 反向覆盖验证 | Outline step 12b |
| 3 | 预设研究维度 | Outline step 5 |
| 4 | 排除区域+重访 | Research Exclusions 章节 |
| 5 | 能力卡片 | Capability Cards 章节 |
| 6 | 就绪检查清单 | Planning Handoff Readiness Checklist |
| 7 | 证据包接收/拒绝 | Multi-Agent Research Orchestration |
| 8 | workflow-state 字段 | Workflow Phase Lock |
| 9 | 强制溯源索引 | Planning Traceability Index |
| 10 | 矛盾日志 | Contradiction Resolution Log |
| 11 | 不可协商语义 | Rules / Guardrails |
| 12 | 差异证据分析 | Outline step 3b |
| 13 | 陈旧声明 | Traceability contract + step 3b |
| 14 | 证据持久化 | Multi-Agent Research Orchestration |
| 15 | 保留优势 | 不变更 |
| 16 | spec 能力消费 | Outline step 5 |
| 17 | alignment 状态消费 | Outline step 3 |
| 18 | Locked Decisions | shell.md Guardrails |
| 19 | PH 强制格式 | lightweight Planning Handoff |
| 20 | 索引列补全 | Planning Traceability Index |
| 21 | 入口区分 | Outline step 2 |
| 22 | PH 消费标记 | Planning Handoff + Traceability Index |

- [ ] **Step 4: Commit**

```bash
git add templates/command-partials/deep-research/shell.md templates/commands/deep-research.md
git commit -m "feat: update shell.md partial and finalize deep-research integration checks"
```

---

### Task 14: 编写模板合同验证测试 + 全量测试（P3）

**Files:**
- Create: `tests/test_deep_research_template_guidance.py`

- [ ] **Step 1: 编写测试文件**

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def _assert_mandatory_subagent_guidance(content: str) -> None:
    lowered = content.lower()
    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lowered
    assert "the leader orchestrates:" in lowered
    assert "before dispatch, every subagent lane needs a task contract" in lowered
    assert "structured handoff" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered


def test_deep_research_template_requires_mandatory_subagent_guidance() -> None:
    _assert_mandatory_subagent_guidance(_read("templates/commands/deep-research.md"))


def test_deep_research_template_defines_complete_research_contract() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "sp-deep-research" in content
    assert "FEATURE_DIR/deep-research.md" in content
    assert "FEATURE_DIR/research-spikes/" in content
    assert "workflow-state.md" in content
    assert "Workflow Phase Lock" in content
    assert "Multi-Agent Research Orchestration" in content
    assert "Traceability and Evidence Quality Contract" in content
    assert "track" in lowered
    assert "question" in lowered
    assert "finding" in lowered
    assert "confidence: high | medium | low" in lowered
    assert "planning_implications" in lowered
    assert "residual_risks" in lowered
    assert "rejected_options" in lowered
    assert "evidence quality rubric" in lowered
    assert "repo-evidence" in content
    assert "runnable-spike" in content
    assert "enough-to-plan" in content
    assert "constrained-but-plannable" in content
    assert "blocked" in content
    assert "not-viable" in content
    assert "user-decision-required" in content
    assert "Planning Handoff" in content
    assert "PH-###" in content or "PH-001" in content
    assert "CAP-001" in content
    assert "TRK-001" in content
    assert "EVD-001" in content
    assert "SPK-001" in content
    assert "Planning Traceability Index" in content
    assert "Before writing final" in lowered or "readiness refusal" in lowered


def test_deep_research_template_has_readiness_refusal_rules() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "readiness refusal" in lowered
    assert "gap report" in lowered
    assert "refuse handoff" in lowered or "handoff refused" in lowered


def test_deep_research_template_has_reverse_coverage_validation() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "reverse coverage validation" in lowered
    assert "every cap" in lowered and "has at least one ph" in lowered
    assert "every ph" in lowered and "traces" in lowered


def test_deep_research_template_has_readiness_checklist() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "Planning Handoff Readiness Checklist" in content
    assert "All CAPs have explicit exit status" in content or "exit status" in content.lower()
    assert "Reverse Coverage Validation passed" in content or "reverse coverage" in content.lower()
    assert "Readiness Refusal Rules all PASS" in content or "readiness refusal" in content.lower()


def test_deep_research_template_has_capability_cards() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "Capability Card" in content
    assert "Purpose" in content
    assert "Truth lives" in content
    assert "Entry points" in content
    assert "Key contracts" in content
    assert "Change propagation" in content


def test_deep_research_template_has_research_exclusions() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "Research Exclusions" in content
    assert "Revisit Condition" in content


def test_deep_research_template_has_contradiction_resolution_log() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "Contradiction Resolution Log" in content
    assert "Priority Basis" in content


def test_deep_research_template_has_evidence_packet_acceptance() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "evidence packet acceptance" in lowered
    assert "paths_read" in lowered
    assert "accepted" in lowered and "rejected" in lowered


def test_deep_research_template_has_preset_research_dimensions() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "preset research dimension" in lowered or "permissions / auth boundary" in lowered
    assert "performance envelope" in lowered or "data volume" in lowered
    assert "observability" in lowered


def test_deep_research_template_consumes_spec_capabilities() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "spec.md" in lowered
    assert "capability decomposition" in lowered or "spec capability" in lowered


def test_deep_research_template_consumes_alignment_status() -> None:
    content = _read("templates/commands/deep-research.md")
    lowered = content.lower()

    assert "needed before plan" in lowered
    assert "feasibility" in lowered


def test_deep_research_template_has_entry_source_distinction() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "entry_source" in content
    assert "full-research" in content or "supplement-research" in content


def test_deep_research_template_has_ph_consumption_contract() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "mandatory" in content.lower()
    assert "user-decision" in content


def test_deep_research_template_has_differential_evidence_analysis() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "Differential Evidence Analysis" in content
    assert "OVERTURNED" in content


def test_deep_research_template_has_stale_claims_handling() -> None:
    content = _read("templates/commands/deep-research.md")

    assert "stale-needs-revalidation" in content


def test_deep_research_shell_partial_defines_guardrails() -> None:
    content = _read("templates/command-partials/deep-research/shell.md")
    lowered = content.lower()

    assert "guardrails" in lowered
    assert "Do not edit production source files" in content
    assert "Locked Decisions" in content or "locked decision" in lowered
```

- [ ] **Step 2: 运行测试确认通过**

```bash
python -m pytest tests/test_deep_research_template_guidance.py -v
```

预期：17 个测试全部 PASS。

- [ ] **Step 3: 运行全量模板测试确认无回归**

```bash
python -m pytest tests/test_*template*.py tests/test_*guidance*.py -v
```

预期：所有已有测试继续通过，新增测试全部 PASS。

- [ ] **Step 4: Commit**

```bash
git add tests/test_deep_research_template_guidance.py
git commit -m "test: add template contract validation tests for sp-deep-research hardening"
```

---

## 自审

1. **Spec coverage**: 22 个点逐项映射到 Task 1-14，Task 13 Step 3 有完整映射表。
2. **Placeholder scan**: 无 TBD/TODO，无 "add appropriate error handling"，所有步骤有具体代码/内容。
3. **Type consistency**: 所有 ID 系统（CAP/TRK/EVD/SPK/PH）在全部任务中一致使用。

---

## 不变更项

- 六维证据质量评分保留
- 五态退出状态机保留（增加 `stale-needs-revalidation`）
- Pre/Post Extension Hooks 保留
- 三种分级输出模板保留
- 多子代理并行编排保留
- 所有 spike 隔离规则保留
- 禁止编辑源代码规则保留
