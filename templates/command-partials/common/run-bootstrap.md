## Run Bootstrap

Run Control owns process-tree launch and resume boundaries for workflow work.
Use `specify-runtime run create` only to record control-plane intent only for a new
run. Use `specify-runtime run show` to confirm the active run identity before
reusing it. Launch repository work only through `specify-runtime run supervise`
so the runtime forces child cwd, binds the managed workspace, and records the
attempt outcome. `specify-runtime run integrate` is reserved for a frozen
immutable candidate after delivery gating; `review` and `accept` must not call
direct integration or mutate the frozen candidate binding.
