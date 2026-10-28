# Human confirmation

For Quick, understand the request and explore bounded current-state evidence,
then use one human-facing confirmation of the concrete change before
implementation. For
Debug, investigate evidence first and confirm the concrete repair before
mutation. Confirm user-owned product facts, scope, risk, and authority; causal
proof, technical sequencing, and hypotheses remain agent-owned.

The human surface uses short headings and bullets rather than dense tables. The
machine contract stays complete: concise rendering must not remove a decision
field, change digest ownership, or turn confirmation into approval of hidden
details.

## Quick card

Do not hand-author freeform prose or a partial field list. Stage a
`quick-confirmation-v1` contract and render the runtime Quick Delivery Checkpoint.
For a new raw request, populate meaningful `decision.current_state_evidence`,
`recommended_approach`, `assumptions_and_risks` and `completion_evidence` before
staging. State current findings and selected source/check basis, concrete change
and reason, affected behavior and risks, expected result and verification.
Greenfield absence or uncertainty is explicit; do not invent a bug cause.
For a newly gathered raw request, inspect the staged response's
`confirmation.decision.current_state_evidence` and `views.decision`; require
the complete selected basis in the typed field and readable default human view.
For material amendments, retain supplied `current_state_evidence` in the
returned typed decision and its digest; show that basis in the human delta view
only when `current_state_evidence` is named in `source.changed_decision_fields`.
Otherwise omit the unchanged basis from the delta view. A missing supplied
field or basis missing where it should be visible can mean an incompatible old
runtime silently dropped it. Restore or update the pinned compatible runtime
and re-stage before asking for approval or confirming/executing. Exact
unchanged approved or inherited legacy decisions need no new-field backfill
or duplicate confirmation.

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

- the concrete proposal grounded in current findings and their evidence basis
- goal and user-visible result
- include / exclude / defer scope
- stable `Q1`/`Q2`/... deliverables
- product-level dependencies and per-item acceptance
- risk and authority decisions
- recommended change, assumptions/impact and overall completion evidence
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

### 当前情况与依据

- [current findings and selected source/check refs, or checked absence/unknown]

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

### 方案与完成标准

- **推荐路径**：[concrete change, reason and expected effect]
- **假设或风险**：[affected behavior, compatibility/authority and uncertainty]
- **完成证据**：[observable result and regression verification]

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

Before approval, targeted existing source/log/test/UI reads, safe bounded
checks and read-only evidence workers can prepare this decision. They authorize
no product/test/harness write, persistent instrumentation, Q-item start or
implementation dispatch. Only a real human reply approving the exact staged
proposal followed by `checkpoint-confirm --digest`, or validated unchanged
inheritance, authorizes implementation under its original Q/Work gates.
A generic request, Auto recommendation or hand-patched confirmation boolean
cannot substitute. Reuse exact approved decisions without another confirmation
or new-field backfill; material proposal, selected-basis, scope or risk changes
use reason-first delta confirmation, while agent choreography stays agent-owned.

## Debug card

Use this Debug Understanding Checkpoint after bounded diagnosis has established
a discovered defect, causal evidence, and a concrete repair. There is no early
mandatory confirmation to inspect existing evidence. Ask for a missing fact
only when it blocks safe investigation. Use localized headings with the same
meanings; the user approves the bounded repair, not the technical hypothesis.

```markdown
## Debug Checkpoint

### 我理解的问题

[reported symptom, expected behavior, conditions, impact, and investigation
boundary/non-goals]

### 已发现的问题

[discovered defect, proven failure mechanism, and decisive evidence in plain
language; distinguish facts from remaining uncertainty]

### 准备怎么修复

- 修复：[concrete change and why it prevents the observed failure]
- 范围：[affected owners/behavior and exact mutation boundary]
- 修复后：[expected user-visible result]

### 影响与验证

- 影响与风险：[compatibility, side effects, data/consumer risks, or evidence-backed
  absence of material risk]
- 验证：[original reproduction, automated RED/regression, related risks, and
  applicable real-entrypoint/UI review]
- 授权：[approve this repair, or diagnose only]

### 需要重新确认的情况

[material change to discovered defect/root cause, repair, boundary, expected
result, authority, UI target, compatibility, migration, side effect, or risk]
```

Persist the exact approved decision payload in `checkpoint` with
`confirmation_purpose: evidence-backed-repair`, `discovered_problem`,
`root_cause`, decisive `evidence_refs`, `proposed_fix`, `change_scope`,
`expected_outcome`, `risks`, and `validation_plan`, reporter facts/boundaries,
and any applicable UI decision. Compute `confirmation_digest` as SHA-256 of
canonical JSON with sorted keys, stable array order, and UTF-8, excluding both
`checkpoint.confirmation_digest` and applicable
`ui_confirmation.confirmation_digest` self-fields, plus mutable agent plan/full
evidence log. Persist confirmation only
after the user's reply. On resume, require this concrete payload, purpose, and
matching digest; legacy/generic `understanding_confirmed: true` is insufficient
repair authority. These are agent-owned bindings, not runtime authentication.

Before approval, block product/test/harness changes, persistent instrumentation,
and fix-worker dispatch. If evidence is impossible without bounded diagnostic
changes, use `confirmation_purpose: diagnostic-enablement` in this same card:
explain the observed evidence gap and unknown root cause, precise diagnostic
work, bounds, risks, verification, and cleanup. It approves only that diagnostic
work; return to investigation afterward and obtain `evidence-backed-repair`
approval before product repair. A diagnose-only response never permits a fix.

Material cause/repair/scope/risk/UI changes invalidate approval and require only
a reason-first `## Debug Checkpoint Amendment` with changed decisions and an
`Unchanged` statement. Keep the complete approved payload and new digest in
state; safe bounded diagnosis may continue while repair mutations wait. New
raw evidence or agent hypotheses alone do not require duplicate confirmation
when the approved causal finding and repair remain intact.

Keep the checkpoint plain text for terminal output: use Markdown without HTML
tags or inline line-break markup.

Reply with `confirm`/`确认` to approve the displayed repair (or explicitly named
diagnostic-only work) after the Debug card and any applicable UI direction,
or use `revise: scope ...`, `revise: UI ...`, or another precise correction.

## UI Confirmation

Keep UI Confirmation independent in machine state but render it inside the same
human checkpoint as one `界面方向` section. Use it only for a user-visible
screen, component, layout, interaction flow, visual state, responsive behavior,
accessibility presentation, TUI layout, or CLI presentation. Quick uses an
implementation proposal. Debug investigates against a provisional
existing/source-backed target, then confirms the formal repair target baseline
alongside the evidence-backed repair; it must not pre-approve a speculative
repair or redesign.

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
