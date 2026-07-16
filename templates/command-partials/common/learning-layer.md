## Project Learning

The CLI is the only agent-facing Learning read surface:

1. Run `{{specify-subcmd:learning start --command <classic-command-name> --format json}}` before deeper non-trivial work.
2. Select summaries by applicability and triggers; use `{{specify-subcmd:learning list --command <classic-command-name> --format json}}` only to filter or page.
3. Execute one matching card's `show_argv`. Do not parse Learning storage.

`start`, `list`, and `show` are read-only. Current repository evidence,
`.specify/memory/constitution.md`, and explicit user direction override stale or
candidate Learning.

At closeout, corrections, retries, route changes, recovery, false leads, hidden
dependencies, validation/tooling/state/cognition gaps, constraints, and near
misses are capture signals. Prefer `{{specify-subcmd:learning capture-auto}}`
from owning state; manual capture includes summary, problem, action, triggers,
success criteria, avoid items, exceptions, and evidence.

- `fast`: skip unless the task escalates.
- `accept`, `analyze`, `ask`, `auto`, `constitution`, `explain`,
  `implement-teams`, `taskstoissues`, and `team`: consume-only; do not violate
  their write boundaries to capture.
- Other non-trivial workflows: consume before deeper work; capture reusable
  signals at closeout or record a no-learning decision.

The `policy` returned by the CLI is authoritative when prompt wording drifts.
