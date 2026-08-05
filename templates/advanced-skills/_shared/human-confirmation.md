# Human confirmation

Use one human-facing confirmation before substantive Quick execution or Debug
investigation. Confirm only user-owned product facts, scope, risk, and
authority. Keep technical sequencing and hypotheses in agent-owned state.

## Quick card

Freeform prose, bullet-only confirmations, or partial field lists do not satisfy
this gate. Do not hand-author a two-column approval table for multi-item Quick
work. Stage a `quick-confirmation-v1` contract and render runtime views.

### Runtime owner

```text
specify-runtime quick checkpoint-stage <quick-id> --input-json '<decision+delivery>' --format json
specify-runtime quick checkpoint-confirm <quick-id> --digest <confirmation_digest> --format json
specify-runtime quick checkpoint-show <quick-id> --view decision|delivery|pulse --format json
specify-runtime quick packet-compile <quick-id> --item Qn --format json
specify-runtime quick item-start <quick-id> --item Qn --format json
specify-runtime quick item-accept <quick-id> --item Qn --evidence '<acceptance proof>' --format json
```

`confirmation_digest` hashes decision fields only. Delivery Map, waves,
batches, subagents, file splits, and test order never enter the digest and never
require user approval.

### Decision Checkpoint only confirms

- goal and user-visible result
- include / exclude / defer
- stable `Q1`/`Q2`/... deliverables
- product-level dependencies
- per-item acceptance
- risk and authority decisions
- UI goals/boundaries when applicable
- reconfirmation trigger

### Do not ask the user to approve

- subagent count
- file choreography
- batch/wave construction beyond deliverable dependencies
- test command order
- worker packet internals

### Modes

1. New prompt: full Decision Checkpoint, confirm once.
2. Discussion handoff with no semantic delta: inherit digest, show binding summary + Delivery Map/Pulse, no re-confirm.
3. Semantic delta: show only changed decision rows, confirm the delta.
4. Execution-only rearrange: `checkpoint-stage --delivery-only` after confirmation.

### Decision view shape

```markdown
## Quick Delivery Checkpoint

来源：[prompt|discussion/<slug>]
绑定状态：[待确认|已确认|已继承确认]
语义变化：[无|delta summary]
处理方式：[确认一次|无需重复确认，直接进入执行|只确认变更项]

目标：[goal]
可见结果：[user-visible result]
范围：包含 [include]；排除 [exclude]

 ID     交付结果              依赖          独立验收门槛
━━━━━  ━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Q1     [deliverable]         —             [acceptance]
─────  ────────────────────  ────────────  ───────────────────────────
 Q2     [deliverable]         Q1            [acceptance]
```

### Delivery Map and Pulse

Show Delivery Map after the Decision Checkpoint for awareness only. During
execution, show Pulse with active items, dependency waits, and the next join
point instead of only "Waiting for agents".

Reply with `confirm`/`确认` after a staged Decision Checkpoint and any
applicable UI card, or use precise corrections such as `修改 Q3 验收 ...`,
`revise: scope ...`, `revise: order ...`, or `revise: UI ...`.

## Debug card

```markdown
## Debug Checkpoint

| Decision to confirm | Current understanding |
| --- | --- |
| Reported problem | [user-visible symptom, where it appears, why it matters, and the nearby issue excluded] |
| Expected behavior | [what should happen instead, or the explicit unknown] |
| Occurrence conditions | [environment, inputs, sequence, frequency, reproduction/failing signal, or Unknown: why it matters] |
| Investigation boundary | Include: [investigation boundary]. Exclude: [non-goals]. |
| Fix authority | [Diagnose only, or diagnose and fix after causal evidence; include mutation boundaries] |
| Assumptions to correct | [reporter assumptions or uncertain facts, or None] |
| Reconfirmation trigger | [new defect, boundary, authority, compatibility, migration, side effect, or material risk] |
```

Technical hypotheses belong to the agent. The first evidence action, fix gate,
and progress signal may follow for awareness, not as a request to approve a
hypothesis.

Reply with `confirm`/`确认` after the Debug card and any applicable UI card, or
use `revise: scope ...`, `revise: UI ...`, or another precise correction.

## UI Confirmation

Append this independent card only for a user-visible screen, component, layout,
navigation/interaction flow, visual state, responsive behavior, desktop/mobile
surface, accessibility presentation, TUI layout, or CLI presentation. An
external image is not required. Quick uses it for an implementation proposal;
Debug uses it for a target baseline and must not pre-approve a speculative fix.

Do not present the card when its basis is only
`design_system.status: bootstrap` or when a new/high-visibility direction lacks
an inspectable visual artifact. Route those cases to `$spx-design`. For Quick,
keep multi-surface or acceptance-heavy UI in `$spx-quick` and expand its
task-local plan, viewport/state matrix, batches, and acceptance evidence rather
than routing to `$spx-specify`. Preserve original references with each reference
intent and name real content/image sources.

```markdown
## UI Confirmation

| Decision to confirm | UI proposal or target baseline |
| --- | --- |
| Confirmation purpose | [Quick implementation proposal or Debug target baseline, plus affected surface] |
| User and primary job | [user, context, and single job] |
| Design basis and source material | [approved direction/current entry point/original references with intent/real content and images] |
| Target experience | [visual, content, and interaction thesis plus signature element] |
| Structure and visible change | [hierarchy, layout, components, copy, and visible before-to-after] |
| Interaction, states, and adaptation | [interaction; loading/empty/error/success/disabled/focus; viewport/window; keyboard/accessibility] |
| Design boundaries | Must preserve: [...]. May adapt: [...]. Must not: [...]. |
| Acceptance evidence | [real entry point, viewport/window and state matrix, structure snapshot, visual capture, runtime diagnostics, comparison or human review] |
```

Do not render an incomplete UI Confirmation. Do not add another reply prompt:
when this UI card is present, a single confirmation covers both the main card
and the UI decision. Persist the main confirmation and `ui_confirmation`
separately so a later amendment can change only the affected decision.
