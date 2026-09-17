# Quick shadow command

## Scope

`quick context-shadow` exposes the existing read-only Quick shadow adapter for
explicit diagnostic use. It does not change an installed workflow, start an
executor, claim Work scope, write an artifact, repair a confirmation or approve
a design/product. Capability presence is not release or acceptance evidence.
The command is registered in this development source; no published runtime
binary or installed project was upgraded by that source change.

## Discover before invoking

Use the project-pinned runtime binary with:

```sh
specify-runtime api ensure --capabilities quick.context-shadow --format json
specify-runtime api show quick.context-shadow --format json
specify-runtime api pack --capabilities quick.context-shadow --format json
specify-runtime quick context-shadow --help
```

A runtime that does not advertise `quick.context-shadow` has no such command.
Do not fall back to another workflow or bypass that check. This is an optional
capability: no existing install minimum, Classic/Advanced default or generated
consumer is changed by its introduction.

## Select exactly one existing owner

```sh
specify-runtime quick context-shadow \
  --workspace 2026-09-17-example \
  --item Q1 \
  --project-root /path/to/project \
  --format json
```

`--workspace` is the exact existing directory immediately below
`.planning/quick/`, not a guessed numeric ID, topic match, path or newest task.
The command does not create or enumerate workspaces. `--item` is an exact `Qn`
identifier. `--project-root` defaults to the current directory. On PowerShell,
use one line or PowerShell continuation syntax, not shell backslashes.

Only `--workspace`, `--item`, `--project-root`, `--format json`, and `--help`/`-h`
are accepted, with each option at most once. Options use separate argument
values; `--name=value` is deliberately not supported. Help needs no repository
and runs before any owner reads. Unknown flags are still rejected with help.
There is no JSON/stdin input, output path, repair, write, force, inline or
executor-selection flag. Shell redirection is an operator action, not an
invocation that registers the result as a workflow artifact.

## Interpret the result

An exit-0 result means a diagnostic snapshot was read, not that implementation,
live source behavior, registered design approval or human acceptance passed.

The complete original owner packet stays under `data.report.owner_packet`.
Its context projection is not independently executable. Data and discovery
outputs carry the same `output_contract`, including:

```json
{
  "mode": "shadow-only",
  "side_effect": "read-only",
  "authorizes_execution": false,
  "live_code_verified": false,
  "design_approval_verified": false,
  "acceptance_verified": false,
  "claim_ready": false
}
```

The CLI reads the owner afresh on every invocation, without a new cache.
The adapter's existing double-read drift checks remain in place. References
to other source files and design approvals are still not independently checked.
Unchanged HEAD does not prove an unchanged working tree. Neither repeated reads
nor this command is a filesystem sandbox or transaction against hostile writers.

## Output, failures and recovery

| Exit code | Meaning |
| --- | --- |
| 0 | Help or a complete diagnostic response |
| 2 | Invalid arguments; no owner read performed |
| 10 | Owner blocked/unavailable for this diagnostic, or output exceeded its bound |
| 1 | Internal or output writer error |

The complete JSON envelope, including pinned argv/metadata and its newline,
must fit 128 KiB. Encoding is completed in memory before stdout. On overflow,
a small blocked envelope is returned without `data.report`; no contract is
truncated. A failed serializer never emits its partial buffer. An external
stdout failure returns 1 and may, by the nature of a failing output device,
leave partial bytes at the destination; the CLI does not append a false success.

`next_argv` is empty on every command response. `show_argv` only opens this
command's read-only help. A blocked snapshot is not an instruction to repair,
reconfirm, restart or retry a mutation automatically. Inspect the existing
owner and preserve the original permission and acceptance gates.

## Cancellation and Git query bounds

The production `RunContext` entrypoint passes its context through the Quick
router, diagnostic command, both owner snapshots and every Git identity query.
Each Git subprocess inherits the shorter parent deadline while retaining its
five-second local ceiling and bounded wait. Cancellation is checked before
reads, after owner assembly and after output buffering; a cancelled observation
cannot be emitted as a successful snapshot. Cancellation does not repair state
or authorize another workflow. Errors preserve `context.Canceled` or
`context.DeadlineExceeded` at the Git boundary for callers that inspect causes.

Git identity stdout has a separate 16 KiB ceiling. On overflow the direct child
is cancelled and the result is rejected; stderr is not copied into diagnostic
responses. The bounded writer intentionally does not embed bytes.Buffer, whose
promoted ReaderFrom method could bypass Write when used by io.Copy.

Filesystem calls are synchronous: cancellation is cooperative between those
calls, not a promise to interrupt a stalled filesystem syscall. A cancellation
racing with an external stdout write cannot retract bytes already delivered.
CommandContext's direct-process cancellation and these tests are not a portable
process-tree sandbox or a guarantee against adversarial subprocess descendants.

## Verification before rollout

The command contract tests exercise argument parsing, reader call counts,
non-authority markers, strict discovery consistency, output limits and writer
failures. The production entrypoint tests use `Run`, `shadowTestRepo`, actual
local Git and the existing Quick packet builder. In a prepared complete checkout:

```sh
cd tools/specify-runtime
go test -race -count=1 -run '^TestQuickShadowCLI' .
go test -count=1 ./...
go vet ./...
```

Then run existing Python, wheel/install, Classic/Advanced and native host
regressions. Source additions and supplied tests are not executed-test evidence.
Real Agent measurement, source/approval verification and release checks remain
separate. No generated consumer should switch based only on this diagnostic.


The source suite now contains ten complete-checkout entrypoint tests. Current
selected-source checks are documented in the
[registration checkpoint](../workflow-quality/quick-shadow-registration-2026-09-17.md).
A selected-source smoke check is not a complete runtime integration pass.
Older cumulative and remaining-only patch archives are superseded by the source
registration and must not be stacked on the updated branch.
