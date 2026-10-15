## User Input

```text
$ARGUMENTS
```

Consider the user input before proceeding. This workflow is user-invoked only;
natural-language similarity must not select or enter it indirectly. An already
invoked DoSession can resume without repeating the command name every turn.

Use the project-local `specify-runtime` launcher. Inspect the matching runtime
`api show` and returned schema before a structured mutation when its contract
is not already available. Send small JSON inline and larger content on stdin;
never create a temporary authoring file just to transport JSON. The `do` and
`playbook` input contracts accept inline JSON or `-` for stdin, not `@path`.
Do not invoke Python `specify` to
mutate workflow state, or invent unsupported subcommands.

For a new session use `adapter_id="__AGENT__"` and the actual native leader's
`agent_id`. Adapter identity lets hooks distinguish independent CLI work;
multiple active sessions in the same adapter still require an explicit ID.

Before reading methods or creating/resuming state, require the installed runtime's
complete Do contract:

`{{specify-subcmd:specify-runtime api ensure --capabilities do.start,do.record,do.validate,do.finish,do.resume,do.show,playbook.find,playbook.show,playbook.update,playbook.validate,do.prepare,do.next,do.complete,playbook.metrics --format json}}`

Missing capabilities block this invocation until the project-pinned runtime is
repaired or upgraded. Keep existing sessions and methods intact; do not substitute
Python mutation, hand-written state, or another workflow.
