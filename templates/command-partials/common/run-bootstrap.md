## Run Bootstrap

Run Control owns process-tree launch and resume boundaries for workflow work.
Use `specify-runtime run create` only to record control-plane intent only for a new
run. Use `specify-runtime run show` to confirm the active run identity before
reusing it. Launch repository work only through `specify-runtime run supervise`
so the runtime forces child cwd, binds the managed workspace, and seals an
immutable Result. With `--workspace-policy auto`, the runtime may route exactly
one non-overlapping modifying Run to the primary workspace only when its checkout
is pristine; every overlap and every idle-but-dirty launch is isolated. Overlaps
inherit the primary Run's pre-launch Snapshot. Never change cwd or select
another Run's workspace yourself.

Inspect Result history with `specify-runtime result list` and
`specify-runtime result show`; record only explicit relationships with
`specify-runtime result depend`, and use `specify-runtime result reopen` rather
than mutating a sealed Result. Delivery is a separate frozen chain:
`specify-runtime candidate build` -> `specify-runtime candidate review` ->
explicit human `specify-runtime accept receipt` ->
`specify-runtime cas publish`. `specify-runtime sync safe` is a separate guarded
primary worktree update. The exact sealed primary Result is accounted state, but
any additional index or worktree change blocks delivery and remains untouched. A Review repair
creates a new Run/Result and therefore a new Candidate; no stage calls direct
integration or mutates an existing Candidate.
