---
description: Use when an existing repository needs to be reverse-extracted into a professional PRD suite grounded in current implementation reality.
workflow_contract:
  when_to_use: Use for an existing repository that needs a professional PRD suite reconstructed from current implementation reality, not for a new idea with no current project surface.
  primary_objective: Produce a delivery-grade PRD suite from an existing project by extracting repository-backed product truth and clearly separating evidence from inference and unknowns.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/coverage-matrix.md`, `.specify/prd-runs/<run-id>/evidence/**`, `.specify/prd-runs/<run-id>/master/master-pack.md`, `.specify/prd-runs/<run-id>/master/exports/**`, and `.specify/prd-runs/<run-id>/exports/prd.md` plus mode-specific exports.'
  default_handoff: Completed PRD suite export. No automatic handoff into implementation planning.
---

# `/sp.prd` Existing Project PRD Suite

## Workflow Contract Summary

This summary is routing metadata only. The full workflow contract is the frontmatter plus the sections below.

- Use `sp-prd` for existing-project reverse PRD extraction.
- Primary truth source: current repository reality, `PROJECT-HANDBOOK.md`, project-map coverage, and cited files.
- Primary terminal state: completed PRD suite export under `.specify/prd-runs/<run-id>/`.
- Default handoff: none. No automatic handoff into implementation planning.

## Objective

[AGENT] Produce a delivery-grade current-state PRD suite from an existing repository.

Extract product truth from code, docs, configuration, tests, routes, UI surfaces, service surfaces, data models, and domain terminology. Build one unified master pack first, then export reader-facing PRD views from that pack.

Every consequential conclusion must be marked as `Evidence`, `Inference`, or `Unknown`.

### Reconstruction Rule

`sp-prd` must reconstruct behavior, not merely inventory repository objects.

The standard is not “artifact found in repository”.
The standard is “artifact explained well enough that another engineer could reconstruct its structure and behavior”.

If the workflow can only name a path, file, endpoint, or module without explaining its internal structure or constraints, mark it as `depth-gap`, not `depth-qualified`.

## Context

`sp-prd` is a peer workflow to `sp-specify`, not a pre-plan requirement. `sp-specify` starts from requested change intent. `sp-prd` starts from current repository reality.

Required context inputs:

- `PROJECT-HANDBOOK.md` as the root navigation artifact.
- `.specify/project-map/index/status.json` and the smallest relevant project-map topics when available.
- `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` when present.
- Current repository evidence from code, docs, tests, routes, UI, API, configuration, data, and deployment surfaces.
- Existing `workflow-state.md` under `.specify/prd-runs/<run-id>/` when resuming an interrupted run.

Create a run workspace under `.specify/prd-runs/<run-id>/` and treat `.specify/prd-runs/<run-id>/workflow-state.md` as the resumable source of truth for phase, project classification, coverage state, open unknowns, blocked surfaces, and export readiness.

Optional control artifacts may also exist under `.specify/prd-runs/<run-id>/`:

- `capability-triage.md` for explicit capability IDs, tiers, and evidence sources
- `depth-policy.md` for tier-by-tier reconstruction expectations
- `quality-check.md` for quality-gate tracking during synthesis and export review

These optional control artifacts strengthen depth-aware execution when present, but they do not replace the required artifact set or the master-pack-first contract.

Classify the project before synthesis as one of:

- `ui` - UI-heavy product, application, site, console, dashboard, or interaction surface.
- `service` - service-heavy API, CLI, backend, automation, library, worker, integration, or platform surface.
- `mixed` - both UI and service surfaces materially shape the product contract.

The classification must include evidence-backed reasoning. It controls which exports are mandatory, not which evidence may be read.

## Process

1. **Route and initialize**
   - Confirm the request is an existing-project reverse-PRD task.
   - If the user only has a new product idea and no current repository surface, route to `sp-specify`.
   - Create or resume `.specify/prd-runs/<run-id>/`.
   - Create or update `.specify/prd-runs/<run-id>/workflow-state.md` before broad repository analysis.

2. **Load brownfield context**
   - Read `PROJECT-HANDBOOK.md` first.
   - Check `.specify/project-map/index/status.json` when present.
   - Use the handbook topic map and project-map routes to choose the smallest relevant atlas documents.
   - If handbook or project-map coverage is missing, stale, or too broad for the project surface, record the gap in `workflow-state.md` before continuing.

3. **Classify project mode**
   - Classify as `ui`, `service`, or `mixed`.
   - Record the evidence used for classification in `.specify/prd-runs/<run-id>/coverage-matrix.md`.
   - Keep mode-specific assumptions visible. Do not silently treat a mixed project as UI-only or service-only.

4. **Capability triage**
   - Identify the repository-backed core value proposition before broad synthesis.
   - Reconstruct capability IDs and assign each one a depth tier: `critical`, `high`, `standard`, or `auxiliary`.
   - Record why each `critical` or `high` capability matters, which sources own it, and which implementation details must be reconstructed before completion can be claimed.
   - Treat cross-cutting behaviors as first-class capabilities even when they span multiple modules or do not align to one UI screen or one service entrypoint.

5. **Targeted evidence harvest**
   - Populate `.specify/prd-runs/<run-id>/evidence/` with notes or files for relevant surfaces.
   - Continue broad surface collection for repository surfaces, UI surfaces, service surfaces, entities and models, workflows, rules, integrations, configuration, permissions, error states, and test/verification clues.
   - For `critical` and `high` capabilities, deepen collection to implementation files, key functions, parsers/serializers, compatibility logic, edge-case handlers, and failure paths.
   - For every `critical` or `high` capability, do not stop at repository object discovery.
   - For each important artifact involved in the capability, capture:
     - where it is
     - what is inside it
     - who reads it
     - who writes it
     - what constraints it must preserve
     - what happens when it fails or receives invalid input
   - Important artifacts include configuration files, schemas, data models, API or CLI contracts, protocol payloads, state machines, normalization or mapping logic, persistence structures, and integration boundaries.
   - Automatically deepen collection for artifacts involving configuration or persistence, protocol or format conversion, compatibility or migration behavior, authentication or authorization boundaries, state transitions, normalization logic, or rollback, retry, failover, and recovery behavior.
   - For any file, interface, schema, or protocol referenced by a `critical` or `high` capability, recording only the path or name is insufficient. Capture structure, fields, format, or contract details.
   - If structure is unknown, mark it explicitly as `Unknown`. If structure is only partially understood, mark it as `depth-gap`.
   - Capture negative-space rules when they materially shape behavior, including read-only fields or sections, values that must remain stable, unsupported transitions, protected history or compatibility anchors, and forbidden overwrite or replacement behavior.
   - When applicable, include at least one concrete example such as a config snippet, schema fragment, request or response sample, state transition example, or failure case example.
   - Label every consequential claim as `Evidence`, `Inference`, or `Unknown`.
   - Use `Evidence` only for claims directly supported by repository files, project docs, runnable behavior, or explicit user input.
   - Use `Inference` for professional conclusions derived from evidence. Include the supporting evidence and confidence.
   - Use `Unknown` when evidence is absent, contradictory, stale, or insufficient. Unknowns must remain visible.

6. **Build depth-aware coverage matrix**
   - Maintain `.specify/prd-runs/<run-id>/coverage-matrix.md`.
   - Track each capability, screen, service entrypoint, data/rule surface, workflow, integration, and export destination.
   - Track each capability's tier, evidence status, depth status, source paths, confidence, and whether the item appears in `master-pack.md` and at least one export.
   - Use depth-aware states such as `surface-covered`, `partially-reconstructed`, `depth-gap`, `blocked-by-unknowns`, and `depth-qualified`.
   - For `critical` and `high` capabilities, include a breakdown covering implementation mechanisms, format or protocol coverage when applicable, edge cases, and traceability.

7. **Synthesize the unified master pack**
   - Write `.specify/prd-runs/<run-id>/master/master-pack.md`.
   - Treat `master/master-pack.md` as the single truth source for all exports.
   - Include product frame, audience and roles, capability inventory, critical capability dossiers, UI or service surface inventory, data and rule model, workflows, integrations, constraints, non-goals, Evidence/Inference/Unknown registry, and coverage/export map.
   - Do not maintain separate export-only facts that are absent from the master pack.

8. **Export PRD views**
   - Always write `.specify/prd-runs/<run-id>/exports/prd.md`.
   - For `ui` and `mixed`, write UI-oriented exports such as `ui-spec.md` and flow or information-architecture views when evidence supports them.
   - For `service` and `mixed`, write service-oriented exports such as `service-spec.md` and capability/API flow views when evidence supports them.
   - Include appendices for data, rules, evidence, unknowns, and internal planning handoff notes when they are needed for a complete suite.

9. **Run quality gates**
   - Run the Capability Triage Gate: block completion if core capabilities and tiers were never made explicit.
   - Run the Critical Depth Gate: a `critical` capability cannot be marked `depth-qualified` until implementation files are traced, core structure or format details are documented, producer and consumer relationships are documented when applicable, key constraints or compatibility rules are documented, failure or boundary behavior is documented, and remaining gaps are explicitly marked as `Unknown` or `depth-gap`.
   - Run the Content Coverage Gate: for each external file, interface, schema, protocol, or persistent structure referenced by a `critical` or `high` capability, path-only coverage is not sufficient; structure or field-level content must be recorded.
   - Run the Producer-Consumer Gate: for each important artifact, identify who produces it, who consumes it, and whether transformation occurs in between.
   - Run the Contradiction Search Gate: actively check for contradictions such as filename or extension vs actual parser, documentation vs implementation behavior, read path vs write path, tests vs runtime logic, and declared schema vs normalized schema.
   - Run the Example Adequacy Gate: each `critical` capability should include at least one concrete example when applicable; otherwise reduce confidence and keep the gap visible.
   - Run the Traceability Gate: block completion if key mechanism claims cannot be traced back to repository evidence.
   - Run the Export Integrity Gate: block completion if exports introduce consequential facts not grounded in `master-pack.md`, or if critical capabilities lack required export landings.
   - Verify every master capability appears in at least one export.
   - Verify every relevant screen or service surface has a documented home.
   - Verify rules and entities are not stranded only in evidence notes.
   - Verify unknowns are retained explicitly where required.
   - Verify no unresolved placeholders or contradictory sections remain in the suite.
   - Record pass/fail status in `workflow-state.md`.

10. **Report completion**
   - Report the run directory, classification, completed exports, unresolved unknowns, inference-heavy areas, and any blocked surfaces.
   - Do not claim implementation-planning readiness unless the user explicitly asks how to consume the PRD suite in later workflows.

## Output Contract

The default artifact set is:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/coverage-matrix.md`
- `.specify/prd-runs/<run-id>/evidence/`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/master/exports/`
- `.specify/prd-runs/<run-id>/exports/prd.md`

Mode-specific exports:

- `ui` projects: include UI-focused exports when UI evidence exists.
- `service` projects: include service-focused exports when service evidence exists.
- `mixed` projects: include both UI-focused and service-focused exports when both surfaces shape the product contract.

`master/master-pack.md` is the unified master pack and the truth source for exports. `exports/prd.md` is the primary reader-facing PRD. Export completeness must be checked against the master pack before final completion.

Each artifact must preserve the Evidence/Inference/Unknown distinction. Unknowns must remain visible rather than being silently filled. Coverage is not complete merely because a capability is mentioned; `critical` capabilities must be depth-qualified before the PRD suite can be marked complete.

## Quality Gates

- **Capability Triage Gate**: block completion if core capabilities and tiers were never made explicit.
- **Critical Depth Gate**: a `critical` capability cannot be marked `depth-qualified` until implementation files are traced, core structure or format details are documented, producer and consumer relationships are documented when applicable, key constraints or compatibility rules are documented, failure or boundary behavior is documented, and remaining gaps are explicitly marked as `Unknown` or `depth-gap`.
- **Content Coverage Gate**: for each external file, interface, schema, protocol, or persistent structure referenced by a `critical` or `high` capability, path-only coverage is not sufficient; structure or field-level content must be recorded.
- **Producer-Consumer Gate**: for each important artifact, identify who produces it, who consumes it, and whether transformation occurs in between.
- **Contradiction Search Gate**: actively check for contradictions such as filename or extension vs actual parser, documentation vs implementation behavior, read path vs write path, tests vs runtime logic, and declared schema vs normalized schema.
- **Example Adequacy Gate**: each `critical` capability should include at least one concrete example when applicable; otherwise reduce confidence and keep the gap visible.
- **Traceability Gate**: block completion if key mechanism claims cannot be traced back to repository evidence.
- **Export Integrity Gate**: block completion if exports introduce consequential facts not grounded in `master-pack.md`, or if critical capabilities lack required export landings.
- **Unknown Visibility Gate**: block completion if missing evidence is narrated as fact instead of preserved as `Unknown` or bounded `Inference`.

## Guardrails

- Do not use `sp-prd` for target-state redesign unless the current-state baseline is explicitly separated from proposed future changes.
- Do not automatically hand off into `sp-plan`, `sp-tasks`, or implementation planning.
- Do not invent product truth to make the PRD look complete.
- Do not collapse repository evidence, professional inference, and unknowns into one unmarked narrative.
- Do not treat path-level traceability as implementation-grade reconstruction.
- Do not mark a capability `depth-qualified` unless the workflow explains what the relevant artifact contains, what constraints it carries, and how it behaves at the boundary.
- Do not collapse contradictions into one clean narrative; preserve conflicting evidence explicitly when repository reality is inconsistent.
- Do not skip `PROJECT-HANDBOOK.md` or project-map routing when they exist.
- Do not treat `exports/prd.md` as the source of truth; it is generated from `master/master-pack.md`.
- Do not claim the PRD suite is complete until export completeness checks pass or unresolved blockers are explicitly reported.
- If evidence is incomplete but export can responsibly continue, preserve `Unknown` and `Inference` labels. If evidence is too thin to support a coherent PRD suite, stop in evidence or coverage phase and record the blocker in `workflow-state.md`.
