# E2E condition-level coverage (scenario book v2)

The operation inventory and fourteen analysis dimensions tell the model where
to look. They are not the denominator of concrete test conditions. A single
scenario tagged `input_boundaries` must not imply that below, at and above a
limit were all tested. Version 2 adds a source-bound condition ledger before
scenarios are selected, without requiring a browser or executable test source.

## Ownership

The model discovers operations, assumptions, variants and correct expected
outcomes from the actual product contract. The helper expands declared boundary
points and checks references, missing variants, step/oracle bindings and observed
coverage. It does not invent semantics, attest perception, find every feature,
compute t-way combinations, or replace Test Design, Review or human acceptance.
Native runner audits remain additional gates when those runners are selected.

## Commands

In generated projects, from the project root:

```text
python .specify/scripts/shared/e2e_scenarios.py schema --schema-version 2
python .specify/scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json --require-v2
```

A source checkout uses `scripts/shared/` instead of `.specify/scripts/shared/`.
`schema` without a version retains the v1 schema for existing tooling. New
Classic and Advanced workflow instructions explicitly select v2 and require it
at every book gate. An old installed helper rejecting these flags is a concrete
installation compatibility blocker, not permission to remove the flags or
fabricate results. Preserve user-edited helpers while repairing the installation.

## Condition families

A v2 book keeps all existing book fields and adds `conditions`. Each condition
has `id`, `operation`, `dimension`, `kind`, `title`, `source_refs` and
`requirements`. References must resolve to the book's hashed sources, operations
and requirements, and the dimension must be applicable to that operation.

For `partition`, `state`, `rule`, `sequence` and `example`, add a nonempty
`variants` array. Every variant has a stable `id`, an `input` description and an
`expected` outcome. Describe an empty input explicitly, for example "submit an
empty name"; these are scenario instructions, not executable data or commands.
A state family can enumerate allowed and rejected transitions. A rule family
can enumerate permission/conflict outcomes. A sequence family can enumerate
ordered interaction paths. Enumeration must come from test analysis; naming a
family does not infer its missing members or all possible permutations.

A `boundary` instead uses `boundary: {limit, unit, expectations}`. The discrete
integer limit must be between -10^12 and 10^12 and have an explicit unit.
`expectations` supplies `below`, `at` and `above`. All three points are derived
as L-1/L/L+1. Fractional thresholds need explicit variants at meaningful domain
increments; do not silently round them into this discrete-boundary contract.

For the disposable desktop sample only, whose contract explicitly limits names
to 32 Unicode code points, one condition could be:

```json
{
  "id": "NAME-LENGTH",
  "operation": "rename",
  "dimension": "input_boundaries",
  "kind": "boundary",
  "title": "Sample filename length, not an operating-system rule",
  "source_refs": ["tests/e2e_samples/desktop_rename.py"],
  "requirements": ["REN-LENGTH"],
  "boundary": {
    "limit": 32,
    "unit": "Unicode code points",
    "expectations": {
      "below": "Accept a valid 31-point name without altering file content",
      "at": "Accept a valid 32-point name without altering file content",
      "above": "Reject a 33-point name without changing files"
    }
  }
}
```

This is an illustrative fragment, not a complete book or executed test result.
Bind the source hash and requirement in the full book. The helper generates
quantities, not suitable filename strings. The model must choose actual input,
verify the unit and contract, and design independent persistence checks.
Unknown limits or outcomes remain discovery gaps; do not invent universal rules.

## Bind every variant to concrete work

Each v2 scenario adds `condition_bindings`. A binding has `condition`, `variant`,
ordered `step_ids` and `oracle_ids`, all referring to that scenario's real steps
and oracles. At least one bound oracle's assertion must exactly equal the
variant's expected outcome. Keep supporting independent-effect oracles too.
The condition's requirements must be included in the scenario's requirements.

```json
{
  "condition": "NAME-LENGTH",
  "variant": "at",
  "step_ids": ["enter-32-point-name", "confirm-name"],
  "oracle_ids": ["at-limit-outcome", "content-preserved"]
}
```

Sibling variants require distinct bound stimulus steps and oracle IDs. Shared
setup need not be bound as a variant stimulus. A longer scenario may test several
variants with distinct actions and observations, but cannot relabel one confirm
step as below, at and above. Different condition families may share a scenario
when it genuinely exercises their conjunction; semantic review remains required.

Every applicable dimension needs a condition family. The existing selected
`event x checkpoint` obligations already provide the denominator for external
mutation/event order when events exist. Ordered paths without external events
still need explicit sequence families. A scenario's declared dimension without
a condition binding or actual perturbation binding remains a design gap.

`derive` returns stable `COND-*` identities, concrete variant descriptions and
linked scenario IDs alongside `TIME-*` obligations. IDs are stable under
reordering; the whole-book digest invalidates evidence when meaning changes.
The helper caps condition expansion at 10,000 obligations and fails rather than
silently sampling. Partition large work explicitly while retaining cross-feature
and high-risk combinations.

## Execution accounting

The trace schema remains version 1; its `book_sha256` must bind the complete v2
book. Existing source/evidence hashes, full step/oracle observations, channel
checks, all attempts and cleanup checks still apply. v2 audit additionally
reports `condition_coverage` and `timing_coverage`, each with total, passed and
missing obligations. Only cleanly passed scenarios credit coverage. A failed,
blocked, skipped, not-run or flaky scenario never becomes clean evidence.

An overlapping passing scenario can cover an obligation, but does not erase a
failed scenario: whole-run completion still requires every declared scenario to
pass and zero design/discovery gaps. Missing cases remain in the denominator.
Screenshots do not replace independent filesystem/API/storage evidence. Visual
observations cannot override a failing native runner audit or claim t-way coverage.

Exit 0 from `derive` means obligations were derived; inspect its gaps. Exit 0
from `check` means declared design readiness, not execution. `audit` requires
consistent complete evidence against that declared book. Exit 1 from check/audit
means gaps, and exit 2 means invalid/stale input or incompatible schema. All
claims retain the qualification that local consistency is not attestation.

## Legacy migration

v1 books and `schemas()` remain readable unchanged for explicit historical
inspection. `--require-v2` refuses them rather than implying condition coverage.
Do not edit an old run in place or just change its version number. Preserve the
original, author and review its conditions, bind concrete scenario steps/oracles,
then run fresh evidence against the new digest. Previously unknown semantics
stay open until resolved through authoritative product evidence.

See [scenario design](sp-e2e-scenarios.md) for the rename candidate inventory and
[readiness](../plans/sp-e2e-readiness.md) for verification limits. This document
is not a release or installed-profile verification claim.
