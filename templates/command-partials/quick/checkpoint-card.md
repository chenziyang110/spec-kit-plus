Use the runtime-owned Quick Delivery Checkpoint. Stage the complete structured
decision through `specify-runtime quick checkpoint-stage`, then render the
deterministic decision view. Do not hand-author freeform prose or reconstruct a
partial field list from memory.

The machine contract remains complete, but its default human view is a readable
decision summary. Do not use a dense table. Do not print the raw digest in the default human view;
`confirmation_digest` remains available in the runtime
envelope, `confirmation.json`, and confirmation command.

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
specify-runtime quick item-start <quick-id> --item Qn [--current-work-id <work-id> --current-work-fence <fence>] --format json
specify-runtime quick item-accept <quick-id> --item Qn --evidence '<acceptance proof>' --format json
specify-runtime quick item-status <quick-id> --format json
```

Managed Runs omit the bracketed item-start options because
`SPECIFY_WORK_ID` and `SPECIFY_WORK_FENCE` are inherited. Unhosted execution
passes both values from its `work begin` receipt; item-start claims the complete
Q write scope before dispatch.

`confirmation_digest` covers decision fields only. Delivery Map, waves, batches,
subagents, file splits, and test order never enter the digest. Updating only the
execution shape uses `checkpoint-stage --delivery-only` after confirmation and
must not reopen user approval.

## Confirmation modes

1. **New prompt Quick**: stage the full decision, show `--view decision`, wait
   for one confirmation, then `checkpoint-confirm`.
2. **Discussion handoff with no semantic delta**: stage with
   `source.kind=discussion`, `semantic_delta=false`, and the handoff
   `review_digest`. Runtime marks state `inherited`; show the binding summary and
   continue without asking again.
3. **Semantic delta only**: stage with `source.kind=delta`,
   `source.semantic_delta=true`, `source.delta_summary`, and
   `source.changed_decision_fields` containing the
   exact changed decision paths (for example `scope.include`,
   `items.Q2.acceptance`, or `ui_confirmation.target_experience`). Runtime keeps
   the complete decision for digest validation but renders only the named
   fields plus necessary row context. The field list is display metadata and
   never enters `confirmation_digest`. Confirm the new digest.
4. **Execution-only rearrange**: after confirmation, adjust
   waves/batches/subagents with `--delivery-only`. Never re-confirm.

## Default human decision view

The runtime decision view uses headings and bullets so it wraps cleanly in chat,
terminals, narrow windows, and assistive technology. It still exposes every
digest-protected deliverable, dependency, and acceptance criterion; readability
must not become blind confirmation.

```markdown
## 请确认本次修改

[one-sentence goal]

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
  - 验收：[independent acceptance]
- **Q2 · [deliverable]**
  - 验收：[independent acceptance]
  - 前置：Q1

### 需要重新确认的情况

- [reconfirmation trigger]

回复：**确认** / **修改范围** / **修改 Qn 验收** / **修改界面方向**
```

For inherited or already confirmed decisions, replace the reply with a compact
confirmation-state sentence. For delta mode, name the delta immediately after
the state and avoid replaying unchanged prose unless it is needed to understand
the change.

## Delivery Map and Pulse

Do not place the Delivery Map between a staged decision and its reply prompt.
Show `--view delivery` after confirmation, on explicit request for execution
detail, or immediately for inherited confirmation. During execution, prefer
`--view pulse` over vague "Waiting for agents" text. The map and pulse are
awareness surfaces only and never require approval.

## UI Confirmation

When the task affects a user-visible UI surface, keep
`decision.ui_confirmation` independent in machine state but fold its readable
proposal into the same human decision card under `### 界面方向`. Do not append a
second dense table or a second reply prompt. When Quick will bind or replace a
registered `UD-*` change, stage the exact five-field design binding before
confirmation so `confirmation_digest` protects it.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

## User reply surface

Reply with `confirm`/`确认` to approve the staged Decision Checkpoint and any
present UI direction. Precise corrections should re-stage only the named
decision fields, for example `修改 Q3 验收 ...`, `修改范围 ...`,
`revise: order ...`, or `revise: UI ...`, then confirm the new digest.
