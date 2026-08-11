# Design Intelligence Artifact Lifecycle

Durable DI artifacts live under `.specify/design/**` in generated projects.
Do **not** create a parallel root `.design/` product tree.

This contract defines create / update / consume / validate / archive paths.
It does not invent a new mainline command and does not replace
`specify-runtime design approve` authority.

## Paths

| Kind | Path (generated project) | Owner stages |
|------|--------------------------|--------------|
| Design change index | `.specify/design/index.json` | design change/register; metadata only |
| Registered design change | `.specify/design/changes/<UD-ID>/DESIGN.md` + `design-contract.json` | design approve/export/register |
| Change review workspace | `.specify/design/changes/<UD-ID>/{brief.md,previews/**,review.md}` | design only until registration |
| DesignContext payload | `.specify/design/context/design-context.json` or a change-local referenced projection | discussion → design → explicitly bound consumers |
| Evidence records | `.specify/design/evidence/*.json` or change-local referenced evidence | design reverse-engineering, discussion discovery |
| UI quality gate report | `.specify/design/gate-reports/*.json` | implement / review / accept (optional engine) |
| Legacy auxiliary archive | `.specify/design/archive/<stamp>/` | explicit auxiliary-record supersede only |

## Lifecycle

1. **create** — write a new context/evidence/gate file with schema version and
   required fields; never invent measured truth without sources.
2. **update** — revise in place only while not approval-bound; keep prior
   evidence ids stable when claims survive.
3. **consume** — specify / plan / implement / review / quick / debug pin one
   registered `UD-*` ref/hash plus explicitly referenced context/evidence; never
   resolve "latest" or re-author dials and tokens as chat-only memory.
4. **validate** — structural checks via Design Intelligence schemas:
   - DesignContext v1
   - Design Evidence v1
   - UI Quality Gate Report v1
5. **supersede** — an approved change remains immutable at its canonical path;
   `index.json` records `superseded`/`superseded_by`. Only auxiliary context or
   evidence records may move under `archive/<stamp>` instead of being silently
   overwritten.

## Stage continuity

```text
discussion design_context
  → design Evidence + System Model + registered UD-* change
  → specify UI Requirements / ui-brief
  → plan ui_design_contract / tasks ui_contract
  → implement / review real-entrypoint evidence + optional gate report
```

Prompt contracts remain subordinate to these schemas. Executable gate rules
return structured issues JSON; unavailable visual comparison stays
`pending-human-review`.

## Non-goals

- Screenshot ML critic
- Parallel root product design tree
- Mutable global design authority or implicit latest selection
- Bypassing design approve / export digests
