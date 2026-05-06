# PRD Export Navigation Design

Date: 2026-05-05
Scope: `templates/prd/**`, `templates/commands/prd-build.md`, PRD export validation and tests
Status: Approved for implementation planning

## Summary

This design adds an explicit navigation layer to the PRD export suite produced
by `sp-prd-scan -> sp-prd-build`.

Today the workflow already produces a rich reconstruction archive, but the
reader-facing export package assumes that consumers will infer reading order
from file names alone. That is workable for authors who know the system, but it
is weak for engineering handoff, onboarding, and cross-team review.

The target outcome is a two-layer reader experience:

- `exports/README.md` becomes the package-level navigation entry.
- `exports/prd.md` remains the canonical primary reader-facing PRD.

The result is a PRD suite that is easier to hand to another engineer without
requiring them to guess where to start or which supporting document answers a
specific question.

## Problem Statement

The current PRD export suite is content-rich but navigation-poor.

Observed problems:

- `exports/prd.md` is defined as the primary reader-facing PRD, but it only
  includes a light appendix list rather than an intentional reading map.
- The export directory has no directory-level entrypoint such as `README.md`,
  so a reader opening `exports/` sees many files with no explicit guidance on
  reading order or task-based routing.
- The suite is especially hard to consume during engineering handoff, where the
  first question is usually not "what is the product?" but "where do I look for
  runtime behavior, protocols, risks, or verification?"
- The current workflow contract treats the export set as complete once the
  files exist, even if the package is difficult to navigate as a coherent
  deliverable.

The issue is not missing content. The issue is missing orientation.

## Goals

- Add a package-level navigation document to the PRD export set.
- Preserve `exports/prd.md` as the canonical primary PRD rather than replacing
  it with a directory index.
- Make the suite easier to use for engineering handoff and technical review.
- Route readers by question and task, not just by raw file name.
- Promote navigation to a required part of the export contract rather than an
  optional documentation flourish.

## Non-Goals

- No change to `sp-prd-scan` scope or output responsibilities.
- No new scan artifacts, scan phases, or run lifecycle states.
- No attempt to collapse the full PRD suite back into one giant document.
- No attempt to make `exports/README.md` a second full PRD.
- No Codex-only optimization. This is a shared workflow/product improvement and
  should apply across supported generated integrations.

## Design Principles

### Keep A Single Canonical PRD

`exports/prd.md` remains the canonical primary reader-facing PRD. The new
navigation layer must not create ambiguity about which file is the main product
document.

### Add A Directory-Level On-Ramp

Readers frequently enter through the filesystem rather than through a direct
link to `prd.md`. The export package should therefore include a directory-level
entrypoint that explains how to use the suite before the reader opens specific
topic files.

### Route By Reader Question

The navigation layer should answer questions like:

- "Where do I start?"
- "Which file explains runtime behavior?"
- "Where are state transitions?"
- "How do I verify this system after changes?"

This is more useful than a bare file listing.

### Separate Navigation From Narrative

`exports/README.md` owns package navigation.
`exports/prd.md` owns the main product narrative.
Both should link to related documents, but neither should try to absorb the
other's job.

## Proposed Reader Model

The PRD export suite should use two entry layers.

### Layer 1: Package Navigation Entry

`exports/README.md` is the first-stop document for readers who open the export
directory without prior context.

Its job is to explain:

- what this package contains
- which file is the main PRD
- recommended reading paths for common goals
- what each supporting document is for
- where confidence is strongest and where gaps still exist

### Layer 2: Canonical Main PRD

`exports/prd.md` remains the main reader-facing PRD.

Its job is to explain:

- what the product is today
- who it serves
- its major capabilities and boundaries
- the most important confidence and unknown notes
- where to jump next for deeper technical detail

### Intended Reading Flow

The expected reading flow becomes:

1. Open `exports/README.md` to understand package structure and reading paths.
2. Read `exports/prd.md` to build overall product understanding.
3. Jump into supporting topic documents according to the reader's current goal.

This keeps the export suite legible without flattening it.

## `exports/README.md` Design

The new `exports/README.md` should be a package guide, not a duplicate PRD.

It should contain five required sections.

### 1. What This Package Contains

Purpose:

- identify the package as a PRD reconstruction export suite
- show the project name, run id, and classification
- clearly state that `prd.md` is the primary reader-facing PRD

This section should orient the reader within a few lines.

### 2. Recommended Reading Paths

Purpose:

- give task-oriented reading orders
- reduce trial-and-error document opening

Representative path categories:

- quick engineering handoff
- interface and integration review
- state and failure analysis
- pre-change risk assessment

This section is not a full index. It is a guided starting map.

### 3. Document Map

Purpose:

- explain what each exported file is for
- answer "when should I read this one?"
- show which documents are commonly paired

Recommended format:

- a table with file name, primary question answered, when to read, and related
  documents

This is the most important navigational section in the README.

### 4. Confidence And Gaps

Purpose:

- explain where the reconstruction is strongest
- explain where the reader should still expect inference or unresolved unknowns
- direct readers to the right supporting files for risk or verification work

This section should summarize confidence posture, not dump every unknown.

### 5. Package Usage Notes

Purpose:

- explain the boundaries between `README.md`, `prd.md`, and the supporting
  exports
- explain that `master/master-pack.md` is the internal synthesis truth source,
  not the preferred first reader entry
- prevent misuse of the package as a random pile of markdown files

## `exports/prd.md` Role Adjustment

`exports/prd.md` should remain the primary PRD, but it needs stronger
navigation semantics than the current appendix-only ending.

Three changes are required.

### Add `How To Use This PRD Suite`

This section should appear near the front of the document and explain:

- that `prd.md` is the main reader-facing narrative
- that the suite includes supporting topic documents
- which documents to open for deeper interface, state, verification, config,
  and risk detail

This should be a compact reading map, not a full document index.

### Replace Appendix-Only Navigation With `Related Documents`

The current lightweight appendix navigation should become a more intentional
related-document section.

Each listed document should carry a short description of its purpose, such as:

- `integration-contracts.md` for system boundaries and dependencies
- `state-machines.md` for state transitions and recovery paths
- `verification-surface.md` for change validation and behavior lock checks

This keeps the PRD actionable without turning it into a full directory guide.

### Keep The Main PRD Focused

`prd.md` should not absorb the full `README` document map.

It should continue to prioritize:

- product overview
- users and roles
- scope and boundaries
- capability overview
- critical capability notes
- key flows
- rules, dependencies, and unknowns

The new navigation additions should support this narrative, not overwhelm it.

## Workflow Contract Changes

The package navigation entry must become part of the official `sp-prd-build`
output contract.

Required contract updates:

- add `exports/README.md` to `workflow_contract.primary_outputs` in
  `templates/commands/prd-build.md`
- add `exports/README.md` to the explicit output contract list
- describe `exports/README.md` as the package navigation entry
- preserve `exports/prd.md` as the primary reader-facing PRD

This makes the package navigation layer mandatory rather than implied.

## Validation Changes

Artifact validation must treat the navigation entry as required.

Required validation updates:

- include `exports/README.md` in PRD build required export validation
- fail artifact validation when the PRD export suite lacks the navigation entry

This ensures that future PRD builds cannot silently regress back to a
navigation-poor package while still appearing contract-complete.

## Template Changes

The shared PRD template set should change as follows.

### Add New Template

- `templates/prd/export-readme-template.md`

This template should include placeholders and required structure for:

- package identity
- recommended reading paths
- document map
- confidence and gaps
- usage notes

### Update Existing Template

- `templates/prd/export-prd-template.md`

Required additions:

- a `How To Use This PRD Suite` section
- a richer `Related Documents` section
- clearer positioning of `prd.md` as the main reader-facing PRD

## Documentation Changes

The repository's operator-facing documentation should describe the PRD export
suite as a navigable package rather than only as a fixed list of files.

Update targets:

- `README.md`
- `PROJECT-HANDBOOK.md`

The documentation should make clear that:

- the PRD lane still produces a full topic-based export suite
- `exports/README.md` is the entrypoint for package navigation
- `exports/prd.md` remains the main PRD

## Test Changes

This design should be enforced through template, helper, and contract tests.

At minimum:

- update `tests/test_prd_export_templates.py`
  - assert the new README export template exists
  - assert its required sections are present
  - assert the PRD export template includes its new usage/navigation structure
- update `tests/test_prd_scan_build_template_guidance.py`
  - assert `prd-build` contract outputs include `exports/README.md`
- update PRD helper and contract fixtures that currently model a complete build
  without a navigation entry
- update artifact validation contract tests so missing `exports/README.md`
  blocks successful PRD build validation

## Success Criteria

This design is successful when all of the following are true:

- a reader opening `exports/` knows immediately where to start
- engineering handoff readers can find relevant documents by task or question
  instead of guessing from file names
- `exports/prd.md` remains clearly identifiable as the canonical main PRD
- missing `exports/README.md` causes PRD build validation to fail
- the change is enforced through shared templates and tests rather than
  depending on author discipline

## Risks And Tradeoffs

### Risk: Dual Entry Confusion

Adding `README.md` introduces a second obvious file in the directory.

Mitigation:

- explicitly describe `README.md` as the package guide
- explicitly describe `prd.md` as the primary reader-facing PRD
- keep the README focused on navigation rather than product narrative

### Risk: Over-duplicating Content

If both files become too descriptive, they will drift and waste reader time.

Mitigation:

- `README.md` routes
- `prd.md` narrates
- supporting documents specialize

### Risk: Contract Drift

If only templates change, runtime validation and tests may drift from the new
intended package shape.

Mitigation:

- update workflow contract text
- update artifact validation
- update template and contract tests in the same implementation pass

## Implementation Notes

This is a shared workflow/product improvement. It should be implemented through
the repository's normal source-of-truth surfaces for templates, validation,
tests, and docs rather than as an integration-specific patch.

`sp-prd-scan` remains unchanged. The navigation entry is an export concern owned
by `sp-prd-build`.
