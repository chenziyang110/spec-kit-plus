Use this exact Markdown table shape for the user-facing Quick Checkpoint. The
row labels may be localized to the user's language when practical, but preserve
the canonical row meanings and the
`| Decision to confirm | Current understanding |` structure. This table is for
user-owned decisions. Technical execution belongs to the agent; freeform prose,
bullet-only confirmations, or partial field lists are not sufficient.

Do not reuse the placeholder text as content. Replace every bracketed item with
task-specific facts. Keep the checkpoint plain text for terminal output; do not
use HTML tags or inline line-break markup.

```markdown
## Quick Checkpoint

| Decision to confirm | Current understanding |
| --- | --- |
| Request and outcome | [2-4 concrete sentences: the request or problem in the user's terms, where it appears, why it matters, and the outcome this quick task should deliver] |
| User-visible result | [what the user will see, do, or rely on differently when the work is complete] |
| Scope | Include: [behaviors, areas, or workflows that are part of this task]. Exclude: [nearby non-goals or behavior that must remain unchanged]. |
| Recommended approach | [the user-relevant approach and any meaningful product trade-off; omit implementation sequencing and internal file choreography] |
| Assumptions and risks | [facts being assumed, known uncertainty, compatibility or migration risk, and the consequence if an assumption is wrong] |
| Completion evidence | [observable acceptance result plus the tests, real entry point, or other evidence the user can rely on] |
| Reconfirmation trigger | [the exact product, scope, authority, compatibility, migration, or risk change that would require a new user decision] |
```

For UI-related work, render the independent UI Confirmation card immediately
after the Quick table. Otherwise omit it completely.

{{spec-kit-include: ../common/ui-confirmation-card.md}}

After the applicable table or tables, the agent may add a short technical
summary for awareness, not as a request to approve technical details. It may
name likely affected surfaces, the first execution action, and the verification
route, but those are agent-owned and must not become additional approval rows.

Reply with `confirm`/`确认` to approve the checkpoint and, when present, the UI
proposal in one response. Reply with `revise: scope ...`/`修改：范围 ...`,
`revise: UI ...`/`修改：UI ...`, or another precise correction to revise only
that decision.
