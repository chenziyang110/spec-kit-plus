# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This Python consumer/compatibility increment
follows `ce0b897f4edec05111bd31551c66adc3f3759710` on PR #120.

## Current decision

Keep dependency order **#116 -> #119 -> #120** and keep the PR draft.
Selected components have been verified; full runtime, installation, native-host
and release verification remain open. Do not merge, publish, upgrade installed
projects or switch generated consumers based on these component results.

The current change fixes Python runtime response handling and installation-time
compatibility checks. It does not change minimum capabilities, release selection,
workflow defaults, launcher configuration ownership or permissions.

## Implemented work

| Area | Implemented | Still not established |
| --- | --- | --- |
| Quick execution/output | Explicit direct/worker selection, compact output, usage tools | Measured improvements in accepted real deliveries |
| Evaluation | Validated observations, unknown values and fixed fixtures | Actual Agent runs and independent acceptance |
| Context/shadow | Bound compilation, strict state decoding, optional non-authorizing CLI and discovery | Live-source/design approval or an executable replacement contract |
| Runtime reliability | Bounded/cancellable reads, delivery and timeout checks | Rollback, process-tree isolation or whole-platform validation |
| Installation | Independent verified copies and selected legacy-hardlink repair | Complete init, wheel, release download or native-platform validation |
| Python consumer | Exit-aware blockers, unambiguous JSON and single-snapshot compatibility | Executable authenticity, atomic check/use or full launcher integration |
| Evidence | Named tests, host package inventory and complete-log checks | Authenticity of edited logs or execution of unstarted jobs |

The complete owner packet and existing result/review/acceptance gates remain.
Shadow stays optional and non-authorizing. Classic and Advanced retain their
separate prompt products and unchanged installed minimum requirements.

## Latest Python boundary repair

A real child process returning a `blocked` envelope with exit 1 was incorrectly
returned as a normal structured blocker. With the default `check=True`, blocked
and repairable-block envelopes now require exit **10**. Exit 1, contradictory
exit 0, other errors and POSIX signal termination cannot be hidden by a blocker
label. Validation happens before the legacy cognition-data unwrap. Valid exit-10
cognition/non-cognition responses preserve their respective existing shapes.

`check=False` remains an explicit diagnostic opt-out from exit checking, not a
permission grant. It does not opt out of JSON integrity. Normal legacy plain
objects remain supported. Response decoding rejects duplicate decoded keys,
non-finite numbers and malformed UTF-8 instead of replacing or silently choosing
values. Integers stay exact; ordinary decimals retain the existing Python float
type. This is not arbitrary-precision decimal transport or bounded streaming IO.

Binary, exact-release and latest-clean checks previously read capabilities from
one handshake and identity from a second. Controlled alternating responses showed
that two individually incompatible snapshots could combine into an accepted one.
Each check now validates capabilities and identity from **one** observed handshake.
This removes one subprocess per such check, not a measured product speedup.

Handshake error/block statuses and malformed data cannot supply a usable identity.
Legacy flat/nested handshake shapes and legacy protocol/capability field names
remain supported. Malformed capability members are rejected rather than converted
to strings. Retired-command rejection, explicit development-dirty permission,
concrete release pins and clean-release fallback remain enforced. A single
handshake is not authentication of an executable or a lock against later changes.

## Validation actually executed for this increment

Linux amd64, Python 3.13.5, local Go 1.23.2 for the retained native-copy fixture.
The original installer and atomic_io bytes were checked against Git blob IDs.

| Executed scope | Result | Boundary |
| --- | --- | --- |
| Before-fix targeted regressions | All 11 failed as expected | Eight blocker/exit cases and three mixed-snapshot cases |
| New response/handshake cases | 54 passed | Parameterized cases using real isolated Python child processes |
| Retained materialization cases | 28 passed | 25 previous cases and three unchanged legacy test bodies |
| Final combined selected Python run | 82 passed; no failures or skips | Not the whole repository or complete CLI |
| Python compilation and source scope | Passed | Full changed module parsed; six existing functions changed, two helpers added |

Tests count subprocess invocations and prohibit response validation from invoking
installation/retry. They cover actual signal termination on Linux, invalid UTF-8,
duplicate keys, ordinary success/blocker compatibility, dirty/release constraints
and the optional shadow capability. Child interpreters use isolated stdlib-only
startup; no network, credentials, published binaries or paid Agent execution.

The full `specify_runtime.py` and `atomic_io.py` modules load. Local package
initialization and two unselected launcher imports remain poison seams; they are
not used or committed as production replacements. The handshake seam in binary
checks only redirects argv to a real child; it does not fabricate subprocess
results. This is component integration, not full `specify init`, configuration
persistence, concurrent initialization, wheel installation or a built Go runtime.
Earlier 105-case selected Go results are historical and were not rerun here.
Ruff is unavailable locally; no Ruff or complete-CI pass is claimed.

## Remaining acceptance gates

| Gate | Current state | Required evidence |
| --- | --- | --- |
| Full Go runtime, SQLite/Work, API and all named tests | Not validated | Complete clean checkout, prepared dependencies and original full suite |
| Full Python, wheel/init/launcher and installed profiles | Not validated | Existing suites against the same source revision |
| Native Windows/macOS | Not executed here | Actual native logs, not cross-compilation or configuration |
| Cloud CI | Latest inspected baseline failed without returned steps | Accessible failure detail and actual execution; root cause remains unknown |
| Live source and registered design inputs | Not verified by shadow | Existing source/design owners before projection adoption |
| Real Agent quality/cost | Not measured | Comparable runs, real instrumentation and independent acceptance |
| Main/release/distributed consumer | Not performed | Passing gates, separate authorization and consumer verification |

Direct container name resolution for GitHub and Go-proxy hosts still failed at
this checkpoint. There is no prepared complete checkout. No billing diagnosis,
repeated rerun, disabled gate or permission change follows from missing CI steps.
Broader large-file/document restructuring and measured adaptive rollout from the
original review are not implicitly complete. Keep user changes and source private.

## Resume through the existing validation path

In a clean prepared checkout, with a new output directory outside the repository:

```sh
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

For the current Python regression in a complete development environment:

```sh
python -m pytest tests/test_runtime_response_integrity.py tests/test_runtime_materialization_isolation.py
```

Neither a partial reproduction bundle nor a supplied test replaces complete
checkout verification. Existing Go, Python, native/install and release gates
remain required. Do not reapply superseded cumulative patches.

See [CI recovery](../ci-troubleshooting.md),
[command usage](../architecture/quick-shadow-cli.md) and
[runtime maintenance](../agent-guidance/workflow-maintenance.md).
