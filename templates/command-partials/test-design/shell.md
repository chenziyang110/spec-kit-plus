{{spec-kit-include: ../common/user-input.md}}

## Objective

Generate a professional, evidence-backed Test Universe, test-case catalog,
test-data/material manifest, coverage matrix, and explicit gap register for the
current project or planned feature. The defensible completion target is complete
against a frozen declared scope, not mathematically exhaustive testing.

## Intent and Mode Routing

Run or emulate the project-cognition intake before broad live reads:

```text
{{specify-subcmd:specify-runtime cognition compass --intent test_design --query "$ARGUMENTS" --format json}}
```

Treat its routes, owners, consumers, verification hints, and minimal live reads
as advisory candidates only. Verify selected claims against current source and
approved workflow artifacts. Infer exactly one mode, then confirm it when the
active state or user request leaves a material ambiguity:

- `project-baseline`: create the repository-wide baseline at `.specify/test-design/`.
- `feature`: after a completed Plan and before Tasks, create `<FEATURE_DIR>/test-design/`.
- `incremental-update`: preserve stable IDs while reevaluating an existing root against changed source, contract, risk, or evidence fingerprints.
- `audit`: independently inspect an existing catalog and its coverage/material contracts without expanding scope silently.

`project-baseline` and `feature` initialize new roots only. `incremental-update`
and `audit` require the existing runtime revision and reopen through
`test-design init --expected-revision <revision>`; audit must preserve the exact
frozen boundary, while incremental update records only the explicit delta.

## Frozen Input Boundary

Before initialization, identify:

- the natural-language query and selected project or feature root;
- authoritative source refs and current revision/fingerprint evidence;
- included paths and explicit excluded paths;
- applicable risk dimensions, including functional, negative, boundary, state,
  permission, concurrency, recovery, compatibility, security, performance,
  accessibility, operations, and other project-specific dimensions;
- existing test, fixture, harness, evidence, regression, and test-material routes;
- known human-owned inputs and prohibited sensitive-data sources.

The runtime-generated source fingerprint freezes this boundary. Later source,
scope, contract, or risk changes make validation stale and require an
`incremental-update`; they do not permit a worker or Leader to patch the
fingerprint manually.

## Artifact Boundary

The runtime owns every canonical JSON artifact and deterministic Markdown view.
Workers write no canonical files. The Leader interacts only through
`specify-runtime test-design` lifecycle commands and uses runtime validation as
the completion authority.

This is a planning-only workflow. Safe workflow-local samples and generation
recipes are planning evidence, not executable repository fixtures. Product
source, test source, migrations, build/runtime configuration, repository fixture
directories, and production data remain outside the write boundary.

The Leader registers accepted textual evidence with `specify-runtime evidence
register` and accepted external/binary material with `specify-runtime evidence
import`, both under scope `test-design` with source and provenance metadata.
External feasibility, normative-oracle, or disposable-proof gaps route to
`sp-deep-research`; its evidence and Planning Handoff become resume inputs.
