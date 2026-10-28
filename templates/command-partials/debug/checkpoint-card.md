Use this semantic section shape for the user-facing Debug Checkpoint. Localize
the labels to the reporter's language when practical, but preserve every
meaning below. Do not use a dense two-column table: wrapping makes it difficult
to scan in chat, terminals, narrow windows, and assistive technology.

Present this card after bounded evidence investigation, before any repair write
or fix-worker dispatch. The checkpoint approves a concrete, evidence-backed
repair. Technical hypotheses belong to the agent and must not be presented as
decisions the user has to validate. Do not reuse the placeholder text as content.
Keep the checkpoint plain text for terminal output: use Markdown without HTML
tags or inline line-break markup.

```markdown
## Debug Checkpoint

### 我理解的问题

[2-4 concrete sentences: user-visible symptom, where it appears, expected
behavior, occurrence conditions, impact, and the nearby excluded issue]

### 已发现的问题

[the proven failure mechanism, how it causes the reported symptom, and the
short decisive evidence with inspectable references; distinguish observations
from conclusions and name remaining uncertainty]

### 准备怎么修复

[the concrete change at the owning layer, exact affected scope, what will be
restored, and what the user should observe afterward; include any necessary
regression test, harness, or instrumentation writes in this repair scope]

### 影响与验证

- 影响与风险：[behavior/compatibility/side effects, excluded work, and material
  risk or explicit unknowns]
- 验证方式：[failing reproduction/RED gate, fresh relevant tests, related-risk
  review, and final reporter verification]
- 修复授权：[the exact proposed repair, or Diagnose only with no fix authority;
  preserve separate external or destructive action gates]

### 需要重新确认的情况

[exact new defect, repair, boundary, UI target, authority, compatibility,
migration, external side effect, or material risk change]
```

For a visual, interaction, responsive, accessibility, TUI, or CLI presentation
problem, render the independent UI Confirmation state as the readable interface
direction section immediately after the Debug checkpoint. It is the target
baseline approved together with this evidence-backed repair. During diagnosis,
provisional source-backed observations do not count as UI approval.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

Use `Unknown: reason` for a fact that is still unknown. If the failure mechanism
or repair remains speculative, continue diagnosis instead of requesting repair
approval. If a missing diagnostic harness or persistent instrumentation prevents
decisive evidence, use this same card to explain the proven gap and request only
that bounded diagnostic write; mark the cause and production repair unknown.
That authorization permits no production repair. Return to diagnosis afterward
and obtain the evidence-backed repair confirmation before production changes.

Reply with `confirm`/`确认` to approve the exact repair and, when present, the UI
target baseline in one response. Reply with `revise: scope ...`/`修改：范围 ...`,
`revise: UI ...`/`修改：UI ...`, or another precise correction to revise only
that decision.
