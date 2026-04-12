# spec-kit-plus Constitution

## Core Principles

### I. Specification-First Delivery (NON-NEGOTIABLE)

Work MUST begin from a written spec, plan, or clearly scoped task before
implementation for any change that is not trivial. Requirements, constraints,
edge cases, and acceptance criteria MUST be explicit before code is treated as
ready.

- **Reasoning Before Coding**: When a request changes behavior, update the
  relevant spec, plan, or task artifact first.
- **No Silent Scope Drift**: If implementation reveals new requirements, the
  governing artifact MUST be updated before the change expands.
- **Rationale**: Clear intent reduces rework and keeps implementation aligned
  with user outcomes.

### II. Simplicity and Scope Discipline

Solutions MUST be the smallest change that fully satisfies the current need.

- **Prefer Deletion Over Addition**: Remove dead code, duplicate paths, and
  obsolete configuration before introducing new layers.
- **Reuse Existing Patterns**: Extend established modules, utilities, and
  conventions before inventing new abstractions.
- **No Speculative Complexity**: Do not add dependencies, frameworks, or
  architecture for hypothetical future needs without explicit justification.
- **Rationale**: Small, focused changes are easier to review, test, and
  maintain.

### III. Test-Backed Changes (NON-NEGOTIABLE)

Behavior changes, bug fixes, and critical refactors MUST be protected by tests.

- **TDD Preferred**: When practical, use Red-Green-Refactor and start with a
  failing test or executable check that proves the change is needed.
- **Regression Protection**: Every bug fix MUST add coverage that would have
  caught the bug before the fix.
- **Right-Sized Verification**: Run the smallest relevant test set during
  iteration, then run broader project checks before completion.
- **Pragmatic Exceptions**: Pure documentation, small configuration-only
  changes, throwaway prototypes, and one-off operational edits MAY use lighter
  verification if full TDD does not fit the work.
- **Rationale**: Tests turn expected behavior into executable evidence and
  reduce regressions.

### IV. Security by Default

Changes MUST protect data, permissions, and trust boundaries by default.

- **Validate Inputs**: External inputs, file contents, configuration, and API
  payloads MUST be validated at the boundary.
- **Least Privilege**: New capabilities SHOULD request only the access they
  actually need.
- **No Secret Leakage**: Secrets, tokens, credentials, and personal data MUST
  not be committed to code, logs, or fixtures.
- **Rationale**: Security failures are expensive and often irreversible, so the
  safe path must be the default path.

### V. Reviewable, Reversible Delivery

Every change MUST be easy to understand, review, and revert.

- **Small Diffs**: Prefer narrowly scoped changes with clear intent over large
  mixed-purpose edits.
- **Documentation Sync**: User-facing behavior, operational procedures, and
  architecture notes MUST be updated in the same change when affected.
- **Compatibility Awareness**: Breaking changes MUST be explicit, justified,
  and accompanied by migration guidance.
- **Rationale**: Delivery quality depends on maintainability, not just passing
  builds.

### VI. Evidence Before Completion (NON-NEGOTIABLE)

Completion claims MUST be backed by relevant verification evidence.

- **Required Checks**: Run the relevant lint, typecheck, tests, and static
  analysis before declaring work complete.
- **Read the Output**: Verification is not complete until results have been
  reviewed and any failures addressed.
- **Scope-Matched Proof**: Use lightweight checks for small changes and broader
  validation for risky, cross-cutting, or user-facing work.
- **Rationale**: Reliability comes from evidence, not from confidence.

### VII. No Unrequested Fallbacks

User intent MUST take precedence over agent convenience when the requested
implementation path is explicit.

- **Honor Explicit Technology Choices**: If the user requires a specific
  technology, tool, library, provider, or architecture, implementation MUST
  use that choice unless the user later changes the requirement.
- **Fallbacks Require Consent**: Do not add fallback strategies, substitute a
  different stack, or silently degrade behavior unless fallback behavior is
  explicitly requested.
- **Failure Must Stay Visible**: If the requested approach fails, report the
  failure clearly instead of hiding it behind an automatic fallback.
- **Rationale**: Silent fallback changes product behavior, obscures real
  constraints, and violates the user's stated requirements.

## Conditional Guidance

Apply the following rules when the project or change type makes them relevant.

### Diagnostics and Observability

The system MUST make failures easy to detect, explain, and reproduce.

- **Actionable Errors**: Error messages and logs MUST describe what failed,
  where it failed, and what context is needed to investigate.
- **Log Before Guessing**: When troubleshooting, inspect logs, traces, metrics,
  or other diagnostics before requesting users to reproduce details that the
  system should already capture.
- **Safe Telemetry**: Sensitive data MUST be redacted or avoided in logs and
  diagnostics.
- **Rationale**: Good observability shortens recovery time and improves
  operator confidence.

## Engineering Standards

- **Technical Source of Truth**: Maintain `项目技术文档.md` at the repository
  root as the project architecture reference for structure, dependencies,
  interfaces, and core data flows. If it is missing in an existing codebase,
  generate it before structural work by analyzing the repository and writing
  the document in place, then keep it in sync when architecture, module
  responsibilities, configuration shape, or external interfaces change.
- **Encoding Preservation**: When modifying an existing file, changes MUST
  preserve the file's existing character encoding and BOM behavior unless the
  task explicitly requires an encoding conversion.
- **Documentation Sync**: Update docs when code changes affect structure,
  behavior, interfaces, workflows, or operator expectations.
- **Performance as a Requirement**: Define and verify performance expectations
  when latency, throughput, startup time, or resource usage matter to the user
  outcome.
- **Accessible Interfaces**: User-facing flows SHOULD be understandable,
  testable, and accessible for their target environment.
- **Operational Readiness**: New services, jobs, or automation SHOULD expose
  the configuration, health checks, and runbooks needed to operate them safely.

## Workflow and Quality Gates

- **Spec-Driven Flow**: Significant work SHOULD follow constitution -> specify
  -> plan -> tasks -> implement, unless the change is truly small and
  self-evident.
- **Review Context**: Change summaries MUST call out risks, assumptions, and
  follow-up items when they exist.
- **Branch Hygiene**: Keep changes current with the target branch and avoid
  long-lived, drifting branches.

## Governance

This constitution is the default decision framework for the project. When
lower-level guidance conflicts, this document takes precedence unless an
explicit higher-priority instruction overrides it.

- **Amendment Process**: Changes to this constitution MUST be documented,
  justified, and reviewed by project maintainers.
- **Versioning Policy**: Use semantic versioning for this document: MAJOR for
  breaking governance changes, MINOR for new principles or materially expanded
  guidance, PATCH for clarifications.
- **Compliance Review**: Reviews, plans, and implementation summaries MUST note
  any intentional deviations from the constitution and why they were accepted.
- **Runtime Guidance**: Repository-specific guidance files may add stricter
  rules, but they MUST NOT silently weaken this constitution.

**Version**: 1.1.0 | **Ratified**: 2026-04-10 | **Last Amended**: 2026-04-12
