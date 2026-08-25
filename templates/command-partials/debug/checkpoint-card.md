Use this semantic section shape for the user-facing Debug Checkpoint. Localize
the labels to the reporter's language when practical, but preserve every
meaning below. Do not use a dense two-column table: wrapping makes it difficult
to scan in chat, terminals, narrow windows, and assistive technology.

The checkpoint is for user-owned facts and authority. Technical hypotheses belong to the agent
and must not be presented as decisions the user has to
validate. Do not reuse placeholder text as content. Keep terminal output plain
Markdown without HTML tags or inline line-break markup.

```markdown
## Debug Checkpoint

### 我理解的问题

[2-4 concrete sentences: user-visible symptom, where it appears, why it
matters, and the nearby issue this session is not debugging]

### 应有表现

[what should happen instead, or the explicit unknown the investigation must
resolve]

### 已知条件

- 发生条件：[environment, inputs, sequence, frequency, reproduction or failing
  signal; use `Unknown: reason` when necessary]
- 待纠正假设：[reporter assumptions or uncertain facts, or None]

### 本次调查

- 包含：[behavior, workflow, state loop, environment, or affected area]
- 不包含：[nearby issue, enhancement, or non-goal]

### 修复授权

[Diagnose only, or diagnose and fix after evidence proves the failure
mechanism; name mutation and side-effect boundaries]

### 需要重新确认的情况

[exact new defect, boundary, authority, compatibility, migration, external side
effect, or material risk change]
```

For a visual, interaction, responsive, accessibility, TUI, or CLI presentation
problem, render the independent UI Confirmation state as the readable interface
direction section immediately after the Debug checkpoint. It is a target
baseline, not approval of a speculative repair.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

After the applicable section or sections, add a compact agent investigation
summary for awareness, not as a request to approve a hypothesis. It may state
the first evidence action, fix gate, and progress signal; these remain
agent-owned.

Reply with `confirm`/`确认` to approve the checkpoint and, when present, the UI
target baseline in one response. Reply with `revise: scope ...`/`修改：范围 ...`,
`revise: UI ...`/`修改：UI ...`, or another precise correction to revise only
that decision.
