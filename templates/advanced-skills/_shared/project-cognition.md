# Project cognition

Use project cognition as the default navigation layer, not as proof of current
behavior.

## Intake

Run `{{specify-subcmd:project-cognition compass --intent <intent> --query="<request>" --format json}}`,
using the intent named by the active skill. This placeholder resolves to the
project-pinned cognition binary during installation. Consume only what helps
the task: `epistemic_contract`, `minimal_live_reads`, lane `first_pass_paths`,
`coverage_diagnostics`, and `expansion_ref`.

- Read `minimal_live_reads` before broad repository search and use
  `first_pass_paths` to choose the next live evidence.
- Follow `expansion_ref` with
  `{{specify-subcmd:project-cognition expand --ref <expansion-ref> --format json}}`
  only when coverage or contradictory live evidence requires more map detail.
- Escalate to lexicon, agent-authored semantic intake, and a precise
  `{{specify-subcmd:project-cognition query --intent <intent> --query-plan <query-plan-json> --format json}}`
  only for unresolved terminology, multilingual intent, or material coverage
  gaps.
- Treat graph claims as route candidates. The live repository, tests,
  configuration, runtime output, and authoritative docs establish facts.

If readiness says `needs_rebuild`, use `$spx-map-rebuild`. Use
`$spx-map-update` for explicit maintenance, external changes, or recovery of an
interrupted incremental update. For `blocked` or partial results, report the
specific recovery signal and continue from live evidence only when the active
skill's safety boundary permits it. Never use `complete-refresh` to disguise an
incomplete, blocked, or rebuild-required state.

## Closeout after repository changes

After verifying changes to source, runtime, templates, configuration, tests, or
generated behavior, run
`{{specify-subcmd:project-cognition closeout-plan --workflow <canonical-sp-workflow> --intent <intent> --format json}}`.
Fill the returned agent-owned evidence fields, then execute the structured
`update_argv`. If its first token is the bare `project-cognition` name, replace
only that first token with `{{specify-subcmd:project-cognition}}` and preserve
every remaining argv token exactly; command strings marked display-only are not
executable instructions. If the update cannot complete, leave freshness
truthful and report the recovery action.

Specification, plan, task, checklist, research, and other planning-only artifact
changes do not make the code map dirty and do not require cognition closeout.
