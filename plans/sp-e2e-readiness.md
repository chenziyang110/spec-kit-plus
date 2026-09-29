# SP E2E implementation readiness

## Implemented in this branch

- Independent Classic and Advanced E2E workflow source templates.
- Shared deterministic constrained t-way planner and source/evidence-bound audit.
- Behavioral helper tests and explicit machine/input/output documentation.
- Test-only ownership and preservation of Test Design, Review, and Accept boundaries.

## Verification performed

The isolated suites ran locally on Linux with Python 3.13.5 and pytest 9.0.2:
57 helper tests and 4 workflow-source contract tests passed (61 total). Python
3.11/3.12 and native Windows/macOS execution were not run. The helper tests
exercise the helper and its CLI with labeled synthetic fixtures. They are not
browser E2E runs, downstream-product verification, installed-profile validation,
a full source-repository test run, or cloud CI evidence.

## Still required before merge

1. Register `e2e` in the shared cognition closeout policy and matching Go owner;
   audit Learning, workflow-name validation, reserved extension names,
   orchestration, and agent argument-hint consumers. Preserve the existing
   Work Board route rather than adding an unsupported Activity enum.
2. Add `spx-e2e` to the Advanced surface map and the explicit expected catalog in
   `tests/test_spx_skill.py`; synchronize profile counts/guidance, README,
   PROJECT-HANDBOOK, and init Start Here. Adding the source directory alone is
   not enough: the current hardcoded expected SPX set does not contain it.
3. Verify the installed helper in isolated Classic and Advanced projects,
   command/skill rendering on supported integrations, exact sidecars/manifests,
   dual-profile coexistence, hooks, and packaged wheel contents. The existing
   `scripts/shared` force-include is not proof of installed availability.
4. Add at least one real sample-application run and trusted runner-report
   adapter, including missing collection, failure, retry, and shard cases.
   The helper deliberately accepts normalized evidence; it does not yet ship
   runner-specific report adapters or execute a product by itself.
5. Run affected source contract, integration, packaging, and Go suites, review
   the final diff, and require genuine CI evidence. Source commits on this
   branch do not authorize a release or changes to repository visibility.

Keep the PR draft until these gates are closed. Do not remove existing tests,
weaken catalog checks, or present the local helper test count as end-to-end
product readiness.
