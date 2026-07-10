Use this exact Markdown table shape for the user-facing Quick Checkpoint. The
row labels may be localized to the user's language when practical, but preserve
the canonical row meanings and keep the `| Item | Current understanding |`
table structure. Freeform prose, bullet-only summaries, or partial field lists
are not sufficient.

```markdown
## Quick Checkpoint

| Item | Current understanding |
| --- | --- |
| Issue | [2-4 concrete sentences: the specific problem/request in the user's terms, where it appears, why it matters, and the nearest thing that is not being requested] |
| Target outcome | [the concrete result this quick task should deliver] |
| Boundaries | Will change: [specific areas, files, commands, workflows, or behavior]. Will not change: [specific non-goals]. Escalate if: [condition that no longer fits quick]. |
| Known facts / assumptions | [repository evidence, handoff facts, minimal reads, explicit user constraints, and any safe assumption being made while unknowns remain] |
| Affected surfaces | [implementation, docs, tests, generated assets, state files, CLI/API surfaces, or consumers expected to be touched or checked] |
| Implementation plan | 1. [task-specific first step]; 2. [task-specific second step]; 3. [task-specific third step]; 4. [task-specific fourth step, if needed]; 5. [task-specific verification or closeout step] |
| Next action | [the first implementation, delegation, or preparation action after confirmation] |
| Validation evidence | [tests, commands, manual checks, changed-surface sweep, or other evidence required before closeout] |
| Stop condition | [the exact discovery or risk that will stop quick execution and require a user decision or escalation] |

Reply with `confirm`/`确认` to continue, or `revise: ...`/`修改：...` with corrections.
```
