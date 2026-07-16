Use this exact Markdown table shape for the user-facing Debug Checkpoint. The
row labels may be localized to the reporter's language when practical, but
preserve the canonical row meanings and the
`| Decision to confirm | Current understanding |` structure. This table is for
user-owned facts and authority. Technical hypotheses belong to the agent and
must not be presented as decisions the user has to validate.

Do not reuse the placeholder text as content. Replace every bracketed item with
session-specific facts. Keep the checkpoint plain text for terminal output; do
not use HTML tags or inline line-break markup.

```markdown
## Debug Checkpoint

| Decision to confirm | Current understanding |
| --- | --- |
| Reported problem | [2-4 concrete sentences: the symptom or regression in user-visible terms, where it appears, why it matters, and the nearby issue this session is not debugging] |
| Expected behavior | [what should happen instead, or the explicit unknown that the investigation must resolve] |
| Occurrence conditions | [known environment, inputs, sequence, frequency, reproduction, failing signal, or Unknown: why it matters] |
| Investigation boundary | Include: [behavior, workflow, state loop, environment, or affected area to investigate]. Exclude: [nearby issue, enhancement, or non-goal]. |
| Fix authority | [Diagnose only, or diagnose and fix after evidence proves the failure mechanism; name any mutation or side-effect boundary] |
| Assumptions to correct | [reporter assumptions or uncertain facts that should be corrected before investigation starts; use None when there are no known assumptions] |
| Reconfirmation trigger | [the exact new defect, boundary, authority, compatibility, migration, external side effect, or material risk change that would require a new user decision] |
```

For a visual, interaction, responsive, accessibility, TUI, or CLI presentation
problem, render the independent UI Confirmation card immediately after the
Debug table. Otherwise omit it completely.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

After the applicable table or tables, add a compact agent investigation summary
for awareness, not as a request to approve a hypothesis. It may state the first
evidence action, fix gate, and progress signal. Those details remain agent-owned
and must not become approval rows or a premature root-cause claim.

Reply with `confirm`/`确认` to approve the checkpoint and, when present, the UI
target baseline in one response. Reply with `revise: scope ...`/`修改：范围 ...`,
`revise: UI ...`/`修改：UI ...`, or another precise correction to revise only
that decision.
