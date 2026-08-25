# [PROJECT_NAME] Constitution

{{CORE_PRINCIPLES}}

{{CONDITIONAL_GUIDANCE}}

{{ENGINEERING_STANDARDS}}

## Shared Source Structure Standard

### Language-Aware Source File Boundaries

Source files MUST remain cohesive, reviewable, and small enough that a reviewer
can understand their purpose without reconstructing several unrelated concerns.
The project MUST NOT use one universal line limit for every language or artifact;
budgets MUST account for language, framework, and artifact role.

- **Project Rules First**: Repository lint rules or a documented local standard
  MAY set lower or higher thresholds when they explain the relevant language,
  framework, generated-code, or artifact-role constraints. A higher threshold
  MUST NOT be used only to avoid a justified split.
- **Default Review Triggers**: When no stricter project rule exists, review an
  ordinary application or library source file at 400 logical source lines, and
  a structurally verbose or declarative source, test/support file, or
  framework-bound component at 600 logical source lines. Count meaningful code
  or declarations, excluding blank and comment-only lines. These are review
  triggers, not automatic split points.
- **Required Action**: Crossing a trigger requires an explicit cohesion review
  covering responsibilities, change reasons, nesting, coupling, and testability.
  At twice the applicable review trigger, the file MUST be split before
  completion or carry a documented exception that names why splitting would
  reduce clarity, the accountable owner, and a concrete follow-up condition.
- **Structure Beats Counting**: Split below the numeric trigger when a file mixes
  unrelated domain, I/O, presentation, orchestration, or policy concerns, or
  when change hotspots and difficult tests show that it already has more than
  one reason to change.
- **Mechanical Exclusions**: generated, vendored, or machine-produced files,
  lockfiles, immutable snapshots, and tool-required migration/schema artifacts
  MAY be excluded from the numeric budget. They MUST remain clearly identified
  and MUST NOT be hand-expanded to evade the rule.

{{WORKFLOW_AND_QUALITY_GATES}}

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

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
