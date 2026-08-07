# Design Intelligence Artifact Lifecycle

Durable DI artifacts live under `.specify/design/**` in generated projects.
Do **not** create a parallel root `.design/` product tree.

This contract defines create / update / consume / validate / archive paths.
It does not invent a new mainline command and does not replace
`specify-runtime design approve` authority.

## Paths

| Kind | Path (generated project) | Owner stages |
|------|--------------------------|--------------|
| Approved design system | root `DESIGN.md` + `.specify/design/design-system.json` | design approve/export |
| DesignContext payload | `.specify/design/context/design-context.json` | discussion → design → consumers |
| Evidence records | `.specify/design/evidence/*.json` | design reverse-engineering, discussion discovery |
| UI quality gate report | `.specify/design/gate-reports/*.json` | implement / review / accept (optional engine) |
| Archive | `.specify/design/archive/<stamp>/` | explicit supersede only |

## Lifecycle

1. **create** — write a new context/evidence/gate file with schema version and
   required fields; never invent measured truth without sources.
2. **update** — revise in place only while not approval-bound; keep prior
   evidence ids stable when claims survive.
3. **consume** — specify / plan / implement / review / quick / debug read
   approved design + latest validated context/evidence; do not re-author dials
   or tokens as chat-only memory.
4. **validate** — structural checks via Design Intelligence schemas:
   - DesignContext v1
   - Design Evidence v1
   - UI Quality Gate Report v1
5. **archive** — when a new approved design supersedes prior context/evidence,
   move superseded machine records under `archive/<stamp>/` instead of silent
   overwrite of approval digests.

## Stage continuity

```text
discussion design_context
  → design Evidence + System Model + DesignContext
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
- Bypassing design approve / export digests
