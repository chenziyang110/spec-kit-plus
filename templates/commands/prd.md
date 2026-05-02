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

## Context

`sp-prd` is a peer workflow to `sp-specify`, not a pre-plan requirement. `sp-specify` starts from requested change intent. `sp-prd` starts from current repository reality.

Required context inputs:

- `PROJECT-HANDBOOK.md` as the root navigation artifact.
- `.specify/project-map/index/status.json` and the smallest relevant project-map topics when available.
- `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` when present.
- Current repository evidence from code, docs, tests, routes, UI, API, configuration, data, and deployment surfaces.
- Existing `workflow-state.md` under `.specify/prd-runs/<run-id>/` when resuming an interrupted run.

Create a run workspace under `.specify/prd-runs/<run-id>/` and treat `.specify/prd-runs/<run-id>/workflow-state.md` as the resumable source of truth for phase, project classification, coverage state, open unknowns, blocked surfaces, and export readiness.

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

4. **Harvest evidence**
   - Populate `.specify/prd-runs/<run-id>/evidence/` with notes or files for relevant surfaces.
   - Cover repository surfaces, UI surfaces, service surfaces, entities and models, workflows, rules, integrations, configuration, permissions, error states, and test/verification clues when present.
   - Label every consequential claim as `Evidence`, `Inference`, or `Unknown`.
   - Use `Evidence` only for claims directly supported by repository files, project docs, runnable behavior, or explicit user input.
   - Use `Inference` for professional conclusions derived from evidence. Include the supporting evidence and confidence.
   - Use `Unknown` when evidence is absent, contradictory, stale, or insufficient. Unknowns must remain visible.

5. **Build coverage matrix**
   - Maintain `.specify/prd-runs/<run-id>/coverage-matrix.md`.
   - Track each capability, screen, service entrypoint, data/rule surface, workflow, integration, and export destination.
   - Mark coverage status, source paths, confidence, and whether the item appears in `master-pack.md` and at least one export.

6. **Synthesize the unified master pack**
   - Write `.specify/prd-runs/<run-id>/master/master-pack.md`.
   - Treat `master/master-pack.md` as the single truth source for all exports.
   - Include product overview, audience and roles, capability inventory, UI or service surface inventory, data and rule model, workflows, integrations, constraints, non-goals, Evidence/Inference/Unknown registry, and export map.
   - Do not maintain separate export-only facts that are absent from the master pack.

7. **Export PRD views**
   - Always write `.specify/prd-runs/<run-id>/exports/prd.md`.
   - For `ui` and `mixed`, write UI-oriented exports such as `ui-spec.md` and flow or information-architecture views when evidence supports them.
   - For `service` and `mixed`, write service-oriented exports such as `service-spec.md` and capability/API flow views when evidence supports them.
   - Include appendices for data, rules, evidence, unknowns, and internal planning handoff notes when they are needed for a complete suite.

8. **Run export completeness checks**
   - Verify every master capability appears in at least one export.
   - Verify every relevant screen or service surface has a documented home.
   - Verify rules and entities are not stranded only in evidence notes.
   - Verify unknowns are retained explicitly where required.
   - Verify no unresolved placeholders or contradictory sections remain in the suite.
   - Record pass/fail status in `workflow-state.md`.

9. **Report completion**
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

Each artifact must preserve the Evidence/Inference/Unknown distinction. Unknowns must remain visible rather than being silently filled.

## Guardrails

- Do not use `sp-prd` for target-state redesign unless the current-state baseline is explicitly separated from proposed future changes.
- Do not automatically hand off into `sp-plan`, `sp-tasks`, or implementation planning.
- Do not invent product truth to make the PRD look complete.
- Do not collapse repository evidence, professional inference, and unknowns into one unmarked narrative.
- Do not skip `PROJECT-HANDBOOK.md` or project-map routing when they exist.
- Do not treat `exports/prd.md` as the source of truth; it is generated from `master/master-pack.md`.
- Do not claim the PRD suite is complete until export completeness checks pass or unresolved blockers are explicitly reported.
- If evidence is incomplete but export can responsibly continue, preserve `Unknown` and `Inference` labels. If evidence is too thin to support a coherent PRD suite, stop in evidence or coverage phase and record the blocker in `workflow-state.md`.
