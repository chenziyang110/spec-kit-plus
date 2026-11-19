# Do Source Mutation

Trigger: read only when DO changed retained source, scripts, tests, or
configuration, or must recover that mutation's cognition closeout.

Preserved Contract: source-changing DO uses the existing canonical cognition
planner, shared apply, intent recovery, and receipt-bound finalization. An
output-only operation does not acquire this source mutation obligation.

Apply the shared contract below before `do finish`. Its `<feature-or-scope>`
and `<scope>` placeholders mean the existing session directory
`.specify/do/sessions/<id>`. Preserve its Work owner. When `do next` returns
`data.source_closeout`, use its exact `plan_argv` from the project root,
or its `recovery_argv` for an existing intent or store blocker. The binding
covers the actual changed source, including both rename endpoints.
On older runtimes, get those exact paths from `do validate` and append them
as individual `--changed-path` flags. Declared output paths and method/session
metadata stay outside the source delta. Failed or interrupted execution
retains the source obligation.

Execute structured `apply_argv`, follow durable intent recovery when needed,
and consume `data.do_continuation` after successful apply or replay. Supply
a truthful `change_summary` with its `complete_input` and run its
`complete_argv`. Use the same expected revision for explicit finish-pending
when Learning is warranted. Complete and finish revalidate the receipt and
live evidence. On older runtimes, read `do next` for the current input.

{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
