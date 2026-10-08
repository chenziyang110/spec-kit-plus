# Do Source Mutation

Trigger: read only when DO changed retained source, scripts, tests, or
configuration, or must recover that mutation's cognition closeout.

Preserved Contract: source-changing DO uses the existing canonical cognition
planner, shared apply, intent recovery, and receipt-bound finalization. An
output-only operation does not acquire this source mutation obligation.

Apply the shared contract below before `do finish`. Its `<feature-or-scope>`
and `<scope>` placeholders mean the existing session directory
`.specify/do/sessions/<id>`; use the runtime-returned ID and preserve its Work
ownership. This is a session scope, not a fabricated feature. Append exact
`--changed-path` values for retained source changes, including both rename
endpoints. Output-only paths and method/session metadata do not enter that
source scope. Failed or interrupted execution retains the source obligation.
Run the planner with the project root as the native tool's working directory;
its CLI does not accept `--project-root`. Preserve the returned apply argv.

Execute structured `apply_argv`, follow durable intent recovery when needed,
and keep the resulting scope receipt for `do validate`. Do not invent direct
updates or a second receipt. An entry map-status assertion cannot satisfy this
source-mutation gate.

{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
