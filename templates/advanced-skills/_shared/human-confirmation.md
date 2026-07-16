# Human confirmation

Use one human-facing confirmation before substantive Quick execution or Debug
investigation. Confirm only user-owned product facts, scope, risk, and
authority. Keep technical sequencing and hypotheses in agent-owned state. Row
labels may be localized, but preserve the table shapes and meanings below.

## Quick card

Freeform prose, bullet-only confirmations, or partial field lists do not satisfy
this gate.

```markdown
## Quick Checkpoint

| Decision to confirm | Current understanding |
| --- | --- |
| Request and outcome | [request/problem, where it appears, why it matters, and intended outcome] |
| User-visible result | [observable result for the user] |
| Scope | Include: [included behavior]. Exclude: [non-goals]. |
| Recommended approach | [user-relevant approach and meaningful trade-off, not implementation choreography] |
| Assumptions and risks | [assumptions, uncertainty, and material risk] |
| Completion evidence | [observable acceptance plus reliable verification evidence] |
| Reconfirmation trigger | [material outcome, boundary, authority, compatibility, migration, or risk change] |
```

Technical execution belongs to the agent. A brief technical summary may follow
for awareness, not as a request to approve technical details.

Reply with `confirm`/`确认` after the Quick card and any applicable UI card, or
use `revise: scope ...`, `revise: UI ...`, or another precise correction.

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
an inspectable visual artifact. Route those cases to `$spx-design`; route
multi-surface or acceptance-heavy UI to `$spx-specify`. Preserve original
references with each reference intent and name real content/image sources.

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
