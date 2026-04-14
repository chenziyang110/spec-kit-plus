# Phase 12: State Surfaces and End-to-End Verification - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the new leader/worker runtime truthful and visible across planning artifacts, generated surfaces, release-facing documentation, and end-to-end verification. It does not redesign Phase 10/11 runtime behavior; it reflects and validates the runtime that now exists.

</domain>

<decisions>
## Implementation Decisions

### Delivery Order
- **D-01:** Implement the “state truth source” first. Planning artifacts and persisted state surfaces must reflect worker outcomes, join points, retry states, and blockers before shipped surfaces or docs are updated.
- **D-02:** After artifact/state truth is in place, align shipped implement surfaces and generated Codex assets to that truth.
- **D-03:** End-to-end verification comes last, after the state surfaces and user-facing guidance have been aligned.

### Planning Artifact Scope
- **D-04:** Phase 12 must expose concrete runtime state in planning artifacts, including worker outcomes, open join points, advanced tasks/phases, and remaining blockers.
- **D-05:** These artifact updates should build on the existing `.planning/STATE.md`, roadmap/requirements/project records, and Codex-team persisted state rather than inventing a separate reporting channel.

### Shipped Surface Alignment
- **D-06:** The shared `implement` template remains the primary source of truth for workflow wording, and generated Codex surfaces must mirror it rather than introducing a separate runtime story.
- **D-07:** User-facing guidance should describe `sp-implement` as a milestone-level orchestration leader with delegated execution, join points, retries, and blocker handling in plain terms.

### Verification Focus
- **D-08:** Regression coverage must fail when planning artifacts, shared template wording, generated Codex skill output, and runtime behavior drift apart.
- **D-09:** End-to-end verification should exercise the real milestone loop expectations that now exist, including delegated batch progression and surfaced blocker/retry truth.

### the agent's Discretion
- Exact file placement for new verification or reporting helpers can follow existing repo conventions as long as the runtime truth is surfaced in existing planning and shipped surfaces.
- The precise phrasing for release-facing docs may vary, but it must remain consistent with the shared template and runtime behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` - Phase 12 goal, success criteria, and plan split (`12-01`, `12-02`)
- `.planning/REQUIREMENTS.md` - `STAT-01`, `STAT-02`, and `STAT-03`
- `.planning/PROJECT.md` - current milestone status, validated requirements, and remaining active scope
- `.planning/STATE.md` - current project state and continuity record

### Prior runtime implementation that Phase 12 must reflect
- `.planning/phases/10-leader-contract-and-milestone-scheduler/10-VERIFICATION.md` - leader-only contract and scheduler truth
- `.planning/phases/11-worker-dispatch-and-failure-convergence/11-01-SUMMARY.md` - batch classification and join-point policy delivered in Phase 11
- `.planning/phases/11-worker-dispatch-and-failure-convergence/11-02-SUMMARY.md` - retry taxonomy and blocker handling delivered in Phase 11
- `.planning/phases/11-worker-dispatch-and-failure-convergence/11-VERIFICATION.md` - verified runtime behavior that Phase 12 must surface and document

### Existing shipped surfaces and docs
- `templates/commands/implement.md` - shared implement contract that user-facing wording must preserve
- `.agents/skills/sp-implement/SKILL.md` - shipped Codex mirror of the implement contract
- `src/specify_cli/integrations/codex/__init__.py` - generated Codex post-processing for `sp-implement`
- `README.md` - release-facing workflow/runtime guidance for this fork

### Existing runtime and state surfaces
- `src/specify_cli/codex_team/runtime_state.py` - persisted runtime objects
- `src/specify_cli/codex_team/manifests.py` - runtime session and dispatch serialization
- `src/specify_cli/codex_team/runtime_bridge.py` - runtime failure and retry state transitions
- `src/specify_cli/codex_team/batch_ops.py` - batch convergence and blocker promotion
- `src/specify_cli/codex_team/session_ops.py` - session lifecycle and monitor summary
- `src/specify_cli/codex_team/state_paths.py` - persisted state layout

### Existing regression tests
- `tests/test_alignment_templates.py` - shared template contract assertions
- `tests/integrations/test_integration_codex.py` - generated Codex skill alignment assertions
- `tests/codex_team/test_auto_dispatch.py` - batch and join-point runtime behavior
- `tests/codex_team/test_manifests.py` - persisted runtime state fields
- `tests/codex_team/test_dispatch_record.py` - runtime failure and retry record behavior
- `tests/contract/test_codex_team_auto_dispatch_cli.py` - Codex team CLI/API contract

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/specify_cli/codex_team/runtime_state.py`, `manifests.py`, `batch_ops.py`, `runtime_bridge.py`, and `session_ops.py` already expose the runtime truth that Phase 12 needs to surface.
- `templates/commands/implement.md` and `.agents/skills/sp-implement/SKILL.md` already encode the leader-only orchestration story and are the natural shipped surfaces to extend.
- Existing planning artifacts (`STATE.md`, `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`) are already the canonical human-readable surfaces and should be evolved rather than replaced.

### Established Patterns
- Phrase-level assertions are preferred over snapshots for template/runtime-contract verification.
- Planning artifacts are updated as phase-delivery records rather than through a separate runtime dashboard.
- Codex-only runtime specifics stay isolated to Codex-facing files, while shared workflow language stays integration-neutral.

### Integration Points
- `STATE.md` and other planning files need to consume the richer runtime truth added in Phase 11.
- Generated Codex skill output and README guidance need to reflect the same runtime story as the shared template.
- End-to-end verification should tie together planning artifacts, shipped surfaces, and runtime behavior rather than checking those layers independently only.

</code_context>

<specifics>
## Specific Ideas

- Do the artifact/state surfacing first so later docs and E2E work have a stable truth source.
- Keep Phase 12 narrowly about reflection and verification; do not use it to redesign runtime mechanics that already shipped in Phases 10-11.
- Treat README and generated surfaces as release-facing truth, not just internal notes.

</specifics>

<deferred>
## Deferred Ideas

- Any broader dashboard or standalone runtime UI remains out of scope.
- Additional integrations beyond the current Codex-centric runtime reporting remain outside this milestone.
- Durable coordination substrate changes remain future work.

</deferred>

---

*Phase: 12-state-surfaces-and-end-to-end-verification*
*Context gathered: 2026-04-14*
