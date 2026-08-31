## Fixed Workflow Artifact Boundary

Work Board is the shared ownership boundary. Before artifact writes outside
Fast/Debug/Implement/Quick, reconcile and inspect the board, then register and
claim only the workflow's allowed artifact paths; reuse an existing valid Work
identity or feature-bootstrap reservation rather than creating another owner.
Keep artifact leases and state-owner guards, checkpoint at meaningful events,
and finish Work only after fresh validation and terminal workflow state. The
four execution workflows use their guarded Activity lifecycle instead; do not
invent execution workflow values for artifact-only lanes. All paths belong to
the current worktree; coordination does not authorize branch changes or delivery.

Canonical workflow artifacts are CLI-owned. Read them with `specify-runtime artifact show --path <project-relative-path> --view summary`, using `--json-pointer`, `--section`, and `--limit` before requesting `--view full`. When one step needs multiple reads from the same artifact set and `api list` exposes `artifact.show-many`, prefer one `show-many` request; older runtimes fall back to targeted single `artifact show` calls. Mutate each artifact through the specialized owner named by the artifact registry. Generic `specify-runtime artifact prepare` / `specify-runtime artifact submit` is valid only when `prepare` explicitly grants a lease for an agent-editable type; pass the bounded semantic content inline with `specify-runtime artifact submit --content '<payload>'`. When one semantic checkpoint needs multiple section/frontmatter or JSON-pointer updates on the same artifact and `api list` exposes `artifact.patch-batch`, aggregate the in-memory delta and prefer one `prepare` plus one `artifact patch-batch`; older runtimes fall back to one leased `artifact patch` per target update. Never create a temporary authoring file, directly read or overwrite a canonical artifact, invent an unregistered path, or reuse a lease. `workflow-state.md` is inside this boundary as rich semantic resume/evidence state and is never required-stage authority; CLI-owned `workflow.json` is accessed only through `specify-runtime workflow`. Source code, tests, and other task-scoped implementation files remain normal repository edits.

For `artifact show-many` and `artifact patch-batch`, `--input-json -` reads
JSON from stdin. Prefer a UTF-8 JSON document kept in memory and sent to stdin
for larger payloads, especially on Windows where native command-line length
and quoting can reject long inline argv. Small inline JSON remains valid; the
in-memory content rule does not mean argv-only transport. Do not write a
temporary authoring file or split one semantic checkpoint merely to fit argv.
Keep one prepared lease for one atomic patch-batch, with at most 32 operations
and the runtime's 256 KiB batch-payload bound. Split only when a runtime bound
or a separate semantic/human-confirmation boundary requires it; each later
batch needs a fresh lease and must not be described as one atomic write.
Keep show-many's own query/output limits and use exact public JSON field names,
including `json_pointer`, rather than internal field names.

If one corrected call returns the same `usage-error` or `invalid` summary and blocker, stop value-guessing: do not vary argument values or path syntax again. Inspect `show_argv`, run `specify-runtime api show <capability> --format json`, or use the namespace's supported `--help`, then make one contract-correct retry. An unchanged error after value-only edits means the option may not have been consumed.
