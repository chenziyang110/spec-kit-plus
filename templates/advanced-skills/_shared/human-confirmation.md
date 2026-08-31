# Human confirmation

Use one human-facing confirmation before substantive Quick execution or Debug
investigation. Confirm only user-owned product facts, scope, risk, and
authority. Keep technical sequencing and hypotheses in agent-owned state.

The human surface uses short headings and bullets rather than dense tables. The
machine contract stays complete: concise rendering must not remove a decision
field, change digest ownership, or turn confirmation into approval of hidden
details.

## Quick card

Do not hand-author freeform prose or a partial field list. Stage a
`quick-confirmation-v1` contract and render the runtime Quick Delivery Checkpoint.

### Runtime owner

```text
specify-runtime quick checkpoint-stage <quick-id> --input-json '<decision+delivery>' --format json
specify-runtime quick checkpoint-confirm <quick-id> --digest <confirmation_digest> --format json
specify-runtime quick checkpoint-show <quick-id> --view decision|delivery|pulse --format json
specify-runtime quick packet-compile <quick-id> --item Qn --format json
specify-runtime quick item-start <quick-id> --item Qn [--current-work-id <work-id> --current-work-fence <fence>] --format json
specify-runtime quick item-accept <quick-id> --item Qn --evidence '<acceptance proof>' --format json
```

Pass both item-start options from the exact guarded Work/Activity identity,
or inherit matching `SPECIFY_WORK_ID` and `SPECIFY_WORK_FENCE`. After
announce, selected checkpoint, fresh overview, and execution guard, item-start
confirms the complete Q write scope before dispatch; its `work_claim` receipt
must match that guard. Do not register a duplicate owner.

`confirmation_digest` hashes decision fields only. Delivery Map, waves,
batches, subagents, file splits, and test order never enter the digest and never
require user approval. Do not print the raw digest in the default human view;
read it from the runtime envelope when calling `checkpoint-confirm`.

### Decision Checkpoint only confirms

- goal and user-visible result
- include / exclude / defer scope
- stable `Q1`/`Q2`/... deliverables
- product-level dependencies and per-item acceptance
- risk and authority decisions
- UI goals/boundaries when applicable
- reconfirmation trigger

Do not ask the user to approve subagent count, file choreography, batch/wave
construction beyond deliverable dependencies, test command order, or worker
packet internals.

### Modes

1. New prompt: full Decision Checkpoint, confirm once.
2. Discussion handoff with no semantic delta: inherit the digest, show a binding
   summary, and do not re-confirm.
3. Semantic delta: stage `source.kind=delta`, then supply
   `source.delta_summary` plus exact `source.changed_decision_fields`. Runtime
   retains the complete decision for digest validation, renders only those
   fields plus necessary row context, and confirms the new digest. The display
   field list never enters the digest.
4. Execution-only rearrange: use `checkpoint-stage --delivery-only` after
   confirmation.

### Default decision view

Do not use a dense table. Keep every digest-protected deliverable, dependency,
and independent acceptance criterion visible as readable bullets.

```markdown
## 请确认本次修改

[goal]

### 你会看到

- [user-visible result]

### 本次会做

- [included scope]

### 本次不做

- [excluded scope]

### 后续处理

- [deferred scope, only when present]

### 交付与验收

- **Q1 · [deliverable]**
  - 验收：[per-item acceptance]
- **Q2 · [deliverable]**
  - 验收：[per-item acceptance]
  - 前置：Q1

### 需要重新确认的情况

- [reconfirmation trigger]

回复：**确认** / **修改范围** / **修改 Qn 验收** / **修改界面方向**
```

Do not place the Delivery Map before the reply for a staged decision. Show it
after confirmation, when the user requests execution detail, or immediately for
inherited confirmation. During execution, show Pulse with active items,
dependency waits, and the next join point instead of only "Waiting for agents".

Reply with `confirm`/`确认` after a staged Decision Checkpoint and any applicable
UI direction, or use a precise correction such as `修改 Q3 验收 ...`,
`revise: scope ...`, `revise: order ...`, or `revise: UI ...`.

## Debug card

Use localized headings with the same meanings; technical hypotheses remain
agent-owned.

```markdown
## Debug Checkpoint

### 我理解的问题

[user-visible symptom, location, impact, and nearby excluded issue]

### 应有表现

[what should happen instead, or the explicit unknown]

### 已知条件

- 发生条件：[environment, inputs, sequence, frequency, failing signal, or
  `Unknown: reason`]
- 待纠正假设：[reporter assumptions or uncertain facts, or None]

### 本次调查

- 包含：[investigation boundary]
- 不包含：[non-goals]

### 修复授权

[Diagnose only, or diagnose and fix after causal evidence; include mutation
boundaries]

### 需要重新确认的情况

[new defect, boundary, authority, compatibility, migration, side effect, or
material risk]
```

Technical hypotheses belong to the agent. The first evidence action, fix gate,
and progress signal may follow for awareness, not as a request to approve a
hypothesis.

Keep the checkpoint plain text for terminal output: use Markdown without HTML
tags or inline line-break markup.

Reply with `confirm`/`确认` after the Debug card and any applicable UI direction,
or use `revise: scope ...`, `revise: UI ...`, or another precise correction.

## UI Confirmation

Keep UI Confirmation independent in machine state but render it inside the same
human checkpoint as one `界面方向` section. Use it only for a user-visible
screen, component, layout, interaction flow, visual state, responsive behavior,
accessibility presentation, TUI layout, or CLI presentation. Quick uses an
implementation proposal; Debug uses a target baseline and must not pre-approve
a speculative repair.

Do not present it when the basis is only an unregistered draft or legacy
bootstrap seed, or when a new/high-visibility direction lacks an inspectable
visual artifact. Route those cases to `$spx-design`. Preserve original
references with their reference intent and name real content/image sources.

```markdown
## 界面方向

[Quick implementation proposal or Debug target baseline, plus affected surface]

- **使用者与主要任务**：[user, context, and single job]
- **目标体验**：[visual, content, and interaction thesis plus signature element]
- **可见变化**：[hierarchy, layout, components, copy, and before-to-after]
- **必须保留**：[non-negotiable patterns or behavior]
- **可以调整**：[implementation-flexible details]
- **不得改变**：[visual, content, or interaction regressions]
- **确认依据**：
  - 设计来源：[approved direction/current entry point/original references]
  - 注册设计绑定：[Quick adoption only: exact five-field binding]
  - 交互与适配：[input, focus, feedback, states, recovery, resize, accessibility]
  - 验收方式：[real entry point, risk-based matrix, captures, diagnostics,
    comparison or human review]
```

Do not render an incomplete UI Confirmation and do not add another reply prompt:
a single confirmation covers both the main checkpoint and this UI decision.
Persist the main confirmation and `ui_confirmation` separately so an amendment
can change only affected fields. For Quick adoption, stage the exact five-field
`decision.ui_confirmation.design_binding` before `checkpoint-confirm`; the
decision digest protects the binding the user reviewed.
