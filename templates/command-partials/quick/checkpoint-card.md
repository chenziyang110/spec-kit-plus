Use the runtime-owned Quick Delivery Checkpoint surface. Do not hand-author a
freeform two-column approval table for multi-item work. Stage structured input
through `specify-runtime quick checkpoint-stage`, then show the deterministic
views. Freeform prose, bullet-only confirmations, or partial field lists are not
sufficient.

## What the user confirms

Only user-owned product decisions:

- final goal and user-visible result
- include / exclude / defer scope
- stable `Q1`, `Q2`, ... deliverables
- product-level dependencies between deliverables
- independent acceptance criteria per deliverable
- risk decisions (compatibility, migration, security, authority)
- UI goals and boundaries when UI applies
- reconfirmation trigger

Do **not** ask the user to approve:

- subagent count or model choice
- file split or write choreography
- batch / wave ordering beyond deliverable dependencies
- test command order
- worker packet internals

Those remain agent-owned in the Delivery Map.

## Runtime commands

```text
specify-runtime quick checkpoint-stage <quick-id> --input-json '<quick-confirmation-v1 decision+delivery>' --format json
specify-runtime quick checkpoint-confirm <quick-id> --digest <confirmation_digest> --format json
specify-runtime quick checkpoint-show <quick-id> --view decision --format json
specify-runtime quick checkpoint-show <quick-id> --view delivery --format json
specify-runtime quick checkpoint-show <quick-id> --view pulse --format json
specify-runtime quick packet-compile <quick-id> --item Qn --format json
specify-runtime quick item-start <quick-id> --item Qn --format json
specify-runtime quick item-accept <quick-id> --item Qn --evidence '<acceptance proof>' --format json
specify-runtime quick item-status <quick-id> --format json
```

`confirmation_digest` covers decision fields only. Delivery Map, waves, batches,
subagents, and test order never enter the digest. Updating only execution shape
uses `checkpoint-stage --delivery-only` after confirmation and must not reopen
user approval.

## Confirmation modes

1. **New prompt Quick**: stage a full Decision Checkpoint, show `--view decision`, wait for one confirmation, then `checkpoint-confirm`.
2. **Discussion handoff with no semantic delta**: stage with `source.kind=discussion`, `semantic_delta=false`, and the handoff `review_digest`. Runtime marks state `inherited`. Show a short binding summary plus Delivery Map / Pulse. Do not ask the user to re-confirm.
3. **Semantic delta only**: stage with `confirmation_mode=delta` / `semantic_delta=true` and a delta summary. Show only changed decision rows. Confirm the delta.
4. **Execution-only rearrange**: after confirmation, adjust waves/batches/subagents with `--delivery-only`. Never re-confirm.

## Decision Checkpoint shape

Present the runtime `decision` view. It must read like:

```markdown
## Quick Delivery Checkpoint

来源：discussion/prompt-authoring-modes
绑定状态：已继承确认
语义变化：无
处理方式：无需重复确认，直接进入执行

目标：[final goal]
可见结果：[user-visible result]
范围：包含 [include]；排除 [exclude]

 ID     交付结果              依赖          独立验收门槛
━━━━━  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Q1     [deliverable]         —             [acceptance]
─────  ────────────────────  ────────────  ───────────────────────────
 Q2     [deliverable]         Q1            [acceptance]
```

For a brand-new prompt request, the binding status is `待确认` and the reply
prompt is required. For inherited discussion handoffs with no semantic delta,
omit the reply prompt.

## Delivery Map shape

Immediately after the Decision Checkpoint (or inheritance summary), present the
runtime `delivery` view for awareness only:

```markdown
## Delivery Map

W1
└─ Q1 [deliverable]

W2
├─ Q2 [deliverable]  ┐
└─ Q3 [deliverable]  ┘ 并行

Join points:
- after Q1 → start W2 (Q1 acceptance evidence)

最终集成门槛：[integration gate]
```

Never ask the user to approve the Delivery Map.

## Pulse shape

During execution, prefer `checkpoint-show --view pulse` over vague
"Waiting for agents" text:

```markdown
## Delivery Pulse

✓ Checkpoint 已继承
→ Q1 metadata-contract 正在执行
⏸ Q2、Q3 等待 Q1
⏸ Q4 等待 Q1、Q2

Join point：Q1 验收证据通过后启动 W2
```

## UI Confirmation

When the task affects a user-visible UI surface, append the independent UI
Confirmation card and include `decision.ui_confirmation` in the staged contract.
One user reply confirms both the main Decision Checkpoint and the UI card.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

## User reply surface

For staged (non-inherited) checkpoints:

```text
确认全部
修改 Q3 验收 ...
把 Q4 改为依赖 Q1、Q2、Q3
将自动翻译加入排除范围
revise: scope ...
revise: order ...
revise: UI ...
```

Reply with `confirm`/`确认` to approve the staged Decision Checkpoint and any
present UI proposal. Precise corrections should re-stage only the changed
decision fields, then confirm the new digest.
