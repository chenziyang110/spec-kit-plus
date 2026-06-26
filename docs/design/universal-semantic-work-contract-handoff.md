# Universal Semantic Work Contract Handoff

This handoff is the execution-facing companion to
`docs/design/universal-semantic-work-contract-v1.md`. The design document explains
why the system exists; this file explains what is already in v1, what must be
verified before release, and what the next maintainer should build next.

## Current Local State

Implemented in this working tree:

- `project-cognition semantic-intake --input <file> --format json`
- semantic-intake request validation for `version: 1`, `raw_request`, and agent facets
- project-backed candidate universe with primary, contrast, and rejected candidates
- permission cap: semantic-intake can guide routing but cannot authorize source edits, root-cause claims, fixed claims, completion claims, or release-safe claims
- conservative learning output capped at `M1`
- compass escalation support for CJK, mixed-language, symptom-first, and weak-coverage requests
- shared semantic work contract partial for generated workflows
- runtime compatibility checks for `semantic-intake --input`
- installer and release workflow smoke checks for the new command surface

Added as the v1.1 minimal audit slice in this working tree:

- optional `project-cognition semantic-audit --input <file> --format json`
- replayable `semantic_routing_audit` artifact construction from a WorkContract, semantic-intake input/output snapshots, selected/contrast/rejected candidate IDs, permission decision, action log, and route corrections
- semantic-audit validation that selected candidates exist in the semantic-intake primary candidate universe, contrast candidates exist in contrast candidates, and rejected candidates exist in rejected candidates
- semantic-audit permission cap at the lower of `P2` and the embedded semantic-intake `permission_hint.maximum_without_live_evidence`; it blocks source-change actions, P2-only inspect actions below P2, and final root-cause/fixed/complete/release-safe claims from routing data alone
- shared workflow guidance that treats the v1.1 audit artifact as a replay/debug/learning record, not as permission to edit or claim completion
- workflow-written `semantic_audit_input` schema guidance, including WorkContract fields, semantic-intake input/output snapshots, route decision, permission decision, action log, and route corrections
- semantic-audit input parsing for both the bare runtime request and the workflow artifact wrapper shape
- regression fixtures covering localized CJK, mixed CJK/ASCII, symptom-first wording, workflow-shadow false friends, docs-shadow false friends, and stale-runtime fallback

Added as the v1.2 minimal evidence-guided inspection slice in this working tree:

- `semantic-audit` output now includes `inspection_plan`
- inspection steps map WorkContract evidence needs, semantic-intake missing evidence, and selected-candidate missing facets to bounded `target_path` or unresolved `target_id`
- known owner hints produce `targeted_read` P2 steps; missing owner paths produce `resolve_owner_before_source_read` P1 steps
- runtime-unavailable, stale, insufficient, or permission-below-P2 states produce `inspect_blocked`/`inspect_limited` behavior instead of broad reads
- `live_evidence_capture`, `rerank_after_inspect`, and `stale_index_downgrade` are explicit artifact fields
- shared workflow guidance treats `inspection_plan` as the only P2 live-read plan and blocks root-cause/fixed/complete/release-safe claims until rerank and verification evidence exist
- v1.2.1 hardening: workflow-provided `live_evidence_capture` records can feed `rerank_assessment`; supporting evidence creates only a non-granted `permission_promotion_candidate`, while contradicting evidence downgrades permission to P1 and blocks further targeted inspect/change/final claims
- v1.2.2 hardening: `owner_bundle_confidence` summarizes indexed primary/supporting/truth/verification owner roles for selected candidates, and `owner_miss_expansion` caps unresolved owner expansion at radius 1 with broad reads blocked
- v1.2.3 hardening: only bounded live source evidence with `source_kind: "source"`, a `read_path` from `inspection_plan` or selected owner hints, and explicit support/contradiction flags can affect `rerank_assessment`; route vocabulary or arbitrary broad source evidence stays useful as context but cannot create a permission promotion candidate
- v1.3 minimal verification owner discovery: `verification_owner_discovery` reports indexed or missing verification owners, emits `targeted_test:<path>` command candidates for indexed verification paths, and keeps claim promotion blocked until workflow authorization plus verification results exist
- v1.3.1 verification result ingestion: workflow-provided `verification_results` are normalized and matched against indexed verification owner paths; matched passed results feed `claim_readiness.evidence_trail` and set `verification_satisfied`, but `claim_ready` stays false until `workflow_authorization` is present
- v1.3.1 safety hardening: partial verification ownership remains blocked; every selected candidate must have an indexed verification owner before any passed result can satisfy `claim_readiness`, and later passed reruns can supersede earlier failed attempts for the same indexed owner path
- v1.3.2 workflow authorization gate: workflow-provided `workflow_authorization` can make `claim_readiness.claim_ready` true only for `root_cause_claim`, only after bounded source evidence and matching passed verification results exist for every selected candidate, and only with `status: authorized`, `authorized_claims` containing `root_cause_claim`, and a non-empty `authorization_ref`
- v1.3.3 claim authorization expansion: `fixed_claim`, `completed_claim`, and `release_safe` can become `claim_ready` only with claim-specific passed verification for every selected candidate, top-level `workflow_authorization.status: authorized`, `authorized_claims` containing the claim, and a matching `workflow_authorization.claim_authorizations[]` entry whose `status` is authorized, whose per-claim `authorization_ref` is non-empty, and whose `verification_evidence_refs` cover the matched verification results
- v1.3.3 safety boundary: claim readiness does not grant P3/P4 permission, unblock source edits, or prove broader release safety beyond the named claim; empty verification `claim_type` remains legacy-compatible only for `root_cause_claim`
- v1.3.4 audit state persistence: generated workflow guidance and `workflow-state.md` now carry `semantic_audit_state`, `semantic_audit_input_path`, `semantic_audit_output_path`, `semantic_audit_resume_status`, active claim type, claim readiness status, claim authorization refs, and claim verification refs so resumed workflows can re-read persisted audit files instead of relying on chat memory
- v1.3.5 resume validation: generated workflow guidance and `workflow-state.md` now carry `semantic_audit_resume_validation`, `semantic_audit_route_fingerprint`, and `selected_candidate_ids`; resumed workflows must compare selected candidate IDs, active claim type, claim authorization refs, and claim verification refs against persisted semantic-audit output before trusting claim readiness
- v1.3.6 generated resume smoke: generated workflow guidance and `workflow-state.md` now carry `semantic_audit_generated_resume_smoke` and `semantic_audit_stale_reasons`; resumed workflows must prompt-check persisted audit file presence and route/claim/ref drift before trusting persisted claim readiness, while stale-state detection remains prompt-only in this version
- v1.3.7 generated downstream smoke: actual Codex init coverage verifies the generated sp-debug skill, generated debug command template, and `.specify/templates/workflow-state-template.md` carry the v1.3.6 resume smoke contract in a downstream project
- v1.3.8 semantic audit resume examples: generated projects now receive `.specify/templates/examples/semantic-audit-resume/scenarios.md` with fresh, missing-file, route-changed, active-claim-changed, claim-ref-mismatch, and verification-ref-mismatch examples for prompt-level resume smoke
- v1.3.9 runtime resume validator: `project-cognition semantic-audit-resume --input <resume-validation.json> --format json` is now an optional JSON comparator for persisted audit input/output plus extracted workflow state; prompt fallback remains valid and the validator does not authorize source edits, final claims, or P3/P4 permission

The v1.1 audit command is intentionally optional at this stage. It should not be
added to `REQUIRED_COMMANDS`, install smoke checks, or release smoke checks until
a generated workflow makes the audit artifact mandatory.

Local validation already used for this v1 slice:

```powershell
cd tools/project-cognition
go test ./...
go vet ./...
go build -o $env:TEMP\spec-kit-plus-project-cognition-smoke.exe .

cd ../..
python -m pytest -q
python -m pytest tests/test_release_workflows.py tests/test_project_cognition_runtime_install.py tests/test_map_runtime_template_guidance.py tests/test_launcher.py -q
python -m build --wheel --outdir $env:TEMP\spec-kit-plus-wheel-build
git diff --check
```

Known non-blocking local warning:

- `git diff --check` reports CRLF/LF warnings for `templates/commands/implement-teams.md` and `templates/commands/map-scan.md`; it exits 0 and reports no patch whitespace errors.

## Release Decision Gate

Do not publish directly from this file. Before release, decide the release version
and tag explicitly. At the time this handoff was written:

- latest local tag observed: `v0.5.13`
- package version observed: `0.5.14.dev0`

Release-ready means all of these are true:

- the intended release version/tag is confirmed
- implementation changes are committed
- the release workflow is triggered for that tag
- attached `project-cognition-*` assets are verified after publication
- generated downstream project smoke test confirms the pinned binary exposes `semantic-intake`

Suggested post-release binary verification:

```powershell
$version = "v0.5.14" # replace with the actual confirmed tag
$tmp = Join-Path $env:TEMP "project-cognition-$version.exe"
Invoke-WebRequest -Uri "https://github.com/chenziyang110/spec-kit-plus/releases/download/$version/project-cognition-windows-amd64.exe" -OutFile $tmp
& $tmp --version
& $tmp --help
& $tmp semantic-intake --help
& $tmp compass --help
Remove-Item $tmp
```

Expected:

- `--version` prints the confirmed release tag
- root help lists `semantic-intake`
- `semantic-intake --help` includes `-input`
- `compass --help` includes `-semantic-intake-file` and `-query-plan-file`

## v1 Acceptance Checklist

Use this checklist when reviewing the implementation:

- A colloquial or localized request can be represented as raw request plus agent-extracted facets.
- Empty or underspecified semantic-intake input is rejected before any candidate ranking.
- Unsupported semantic-intake request versions are rejected.
- Empty candidate groups serialize as `[]`, not `null`.
- H5/web environment settings page wording routes ahead of `.env` config when page facets dominate.
- `.env` config routes ahead of the page when startup/config facets dominate.
- workflow/environment false friends are rejected or demoted unless workflow facets are present.
- semantic-intake CLI output can be used by `compass --semantic-intake-file`.
- output options actually control contrast, rejected, owner hint, and verification-prior fields.
- generated workflow prompts use compass-first intake and semantic-intake escalation.
- semantic-intake-only output never authorizes edits or final correctness claims.
- installers and runtime compatibility checks reject older binaries without `semantic-intake --input`.
- release workflow smoke-tests the new project-cognition command surface before asset upload.

## v1.1 Audit Artifact

Goal:

```text
Make every semantic routing decision replayable, debuggable, and learnable without
raising action permission.
```

Minimal runtime slice:

- `semantic-audit` command accepts an explicit JSON request or stdin
- `semantic-audit` accepts either a bare audit request or a workflow-written `{ "semantic_audit_input": ... }` wrapper
- audit output preserves semantic-intake input/output snapshots
- selected, contrast, and rejected candidate basis are replayable by ID
- permission downgrade reasons record when semantic-intake-only evidence is capped at `P2` or a lower semantic-intake permission hint
- action log records intake and follow-up evidence steps without authorizing edits
- route correction fields carry false-match learning candidates at `M1`

Implemented v1.1 workflow/test slice:

- shared semantic work contract partial defines a workflow-written `semantic_audit_input` artifact schema
- generated workflow guidance says to write or carry that artifact before broad live reads when semantic-intake escalation influences routing
- fallback guidance says to manually produce the same fields when `semantic-audit` is unavailable, without blocking on a newer runtime solely for the optional audit command
- tests cover localized CJK request, mixed CJK/ASCII request, symptom-first request, workflow-shadow false friend, docs-shadow false friend, and stale runtime fallback

Do not implement in v1.1:

- automatic source edits from semantic-intake
- canonical learning promotion above `M1`
- final fixed/complete/release-safe claims from routing data alone
- workflow-specific semantic-routing forks
- mandatory install/release smoke dependency on `semantic-audit`

Future v1.1 hardening only if product needs it:

- choose a stable downstream workflow persistence path for `semantic-audit-input.json`
- add generated-project smoke tests that verify the artifact is written at that path
- promote `semantic-audit` from optional to required only after generated workflows depend on that path

## Next Version: v1.2 Evidence-Guided Inspection

Goal:

```text
Turn candidate routing into bounded live evidence collection.
```

Implemented local minimum:

- minimal live-read plan derived from candidate universe, WorkContract evidence needs, and missing facets
- bounded target mapping through candidate owner hints and expansion target IDs
- contradiction handling contract through `rerank_after_inspect`
- stale/runtime fallback downgrade contract through `stale_index_downgrade`
- tests proving route vocabulary produces bounded inspect plans but still blocks edits and final claims

v1.2 is locally closed for this design slice:

- multiple captured bounded live source evidence records can feed rerank while route vocabulary and unbounded broad source records remain excluded
- no P3/P4 permission grant is made from v1.2 evidence; v1.3 discovery still requires verification results and workflow authorization

## Next Version: v1.3 Verification Owner Discovery

Goal:

```text
Discover what verification is needed before P3/P4 claims.
```

Implemented local minimum:

- verification owner hints from the project graph candidate owner bundle
- required verification command candidates for indexed verification owner paths
- explicit `promotion_blocked: true` and final-claim blocking while verification results are missing
- verification result ingestion for workflow-captured targeted verification results
- `claim_readiness` evidence trail that separates inspect-ready, change-ready, and claim-ready states
- workflow authorization gate that can mark `root_cause_claim` ready after bounded source evidence and matching passed verification for every selected candidate
- claim-specific verification and per-claim authorization gates for `fixed_claim`, `completed_claim`, and `release_safe`
- explicit blockers for unsupported claim types, missing workflow authorization, missing authorization references, failed verification, missing verification results, verification owner mismatches, missing claim-specific verification, and incomplete claim authorization

v1.3.6 is locally closed for this design slice:

- `workflow_authorization` is explicit input/output, not inferred from workflow name
- `root_cause_claim` can still use legacy untyped passed verification; `fixed_claim`, `completed_claim`, and `release_safe` require `verification_results[].claim_type` or `claim_types`
- non-root final claims require top-level `workflow_authorization.status: authorized`, `authorized_claims` containing the claim, and `claim_authorizations[]` with `status: authorized`, a non-empty per-claim `authorization_ref`, and `verification_evidence_refs` covering the matched claim-specific verification results
- workflows have a stable default persistence convention: store `semantic-audit-input.json` and `semantic-audit-output.json` next to the active workflow state and record exact paths in the Semantic Audit State section
- resume validation must compare selected candidate IDs, active claim type, claim authorization refs, claim verification refs, and the semantic audit route fingerprint before reusing persisted claim readiness
- generated resume smoke records `semantic_audit_generated_resume_smoke` and `semantic_audit_stale_reasons` so a resumed workflow has an explicit pass/fail marker and reason list before it trusts persisted semantic-audit state
- resume smoke comparison sources are fixed: route fields compare workflow state against `semantic-audit-input.json.semantic_audit_input.route_decision`, while authorization and verification refs compare workflow state against `semantic-audit-output.json.workflow_authorization` and `semantic-audit-output.json.claim_readiness`; fingerprint mismatches are `route-changed`
- v1.3.6 keeps stale-state detection prompt-only; no runtime validator command is required until generated-project failures show prompt-level checks are insufficient
- permission promotion remains non-granted; semantic-audit still does not authorize source edits or release claims

## v1.3.6 Generated Resume Smoke

Goal:

```text
Prove generated workflows preserve and invalidate semantic-audit state across resume.
```

Implemented local minimum:

- shared semantic work contract partial requires generated workflows to run a prompt-level resume smoke before trusting persisted claim readiness
- workflow-state template records `semantic_audit_generated_resume_smoke` with `not-run|passed|failed|not-applicable`
- workflow-state template records `semantic_audit_stale_reasons` with missing-file, route-changed, active-claim-changed, claim-ref-mismatch, and verification-ref-mismatch reasons
- generated workflow template tests verify every project-cognition-backed workflow receives the resume smoke contract through the shared partial
- stale-state detection intentionally remains prompt-only in v1.3.6

## Next Version: v1.3.7 Runtime Resume Validator (Optional)

v1.3.7 generated downstream smoke is locally closed:

- actual Codex init smoke verifies the generated sp-debug skill includes generated resume smoke guidance, deterministic comparison sources, prompt-only stale-state detection, no runtime validator requirement, and claim_ready blocking on smoke failure
- actual Codex init smoke verifies the generated debug command template carries the same semantic work contract as the skill surface
- actual Codex init smoke verifies `.specify/templates/workflow-state-template.md` contains `semantic_audit_generated_resume_smoke`, `semantic_audit_stale_reasons`, and `active-claim-changed`
- runtime resume validator remains optional; the generated downstream smoke currently supports keeping stale-state detection prompt-only

## v1.3.8 Semantic Audit Resume Examples

v1.3.8 semantic audit resume examples is locally closed:

- `.specify/templates/examples/semantic-audit-resume/scenarios.md` documents the expected state result for fresh, missing-file, route-changed, active-claim-changed, claim-ref-mismatch, and verification-ref-mismatch resume smoke cases
- the shared semantic work contract points generated workflows at `.specify/templates/examples/semantic-audit-resume/scenarios.md` when the examples are available
- package tests verify the examples are bundled through the existing `templates/examples` force-include
- Codex init smoke verifies generated downstream projects receive the examples under `.specify/templates/examples/semantic-audit-resume/scenarios.md`
- the examples are prompt-level comparison guides, not a runtime validator

## v1.3.9 Runtime Resume Validator

v1.3.9 runtime resume validator is locally closed:

- `project-cognition semantic-audit-resume --input <resume-validation.json> --format json` accepts extracted workflow state and concrete paths to `semantic-audit-input.json` plus `semantic-audit-output.json`
- the validator compares selected candidate IDs, active claim type, route fingerprint, authorization refs, verification refs, and input/output file-pair route consistency
- output records `validator: semantic-audit-resume`, `semantic_audit_generated_resume_smoke`, `semantic_audit_resume_status`, `semantic_audit_resume_validation`, `semantic_audit_stale_reasons`, `can_reuse_persisted_claim_readiness`, `claim_ready_allowed`, `permission_promotion_granted: false`, `grants_permission: false`, and `boundary: comparison_only_no_source_edit_or_claim_authorization`
- the command is an optional JSON comparator; it does not parse workflow-state.md and does not authorize source edits, final claims, or P3/P4 permission
- prompt fallback remains valid when the command is unavailable, blocked, or unnecessary
- installer, runtime support checks, and release smoke verify `semantic-audit-resume --input`

## v1.3.10 Resume Validator Downstream Adoption

v1.3.10 resume validator downstream adoption is locally closed:

- generated projects now receive concrete validator fixtures under `.specify/templates/examples/semantic-audit-resume/`
- `resume-validation.json` demonstrates a fresh `project-cognition semantic-audit-resume --input resume-validation.json --format json` result with `semantic_audit_generated_resume_smoke: passed`, `semantic_audit_resume_status: fresh`, and `can_reuse_persisted_claim_readiness: true`
- `resume-validation-route-changed.json` demonstrates a stale route result with `semantic_audit_generated_resume_smoke: failed`, `semantic_audit_resume_status: needs-rerun`, and `semantic_audit_stale_reasons: [route-changed]`
- both fixtures reference sibling `semantic-audit-input.json` and `semantic-audit-output.json`; the runtime still reads explicit JSON paths and does not parse workflow-state.md
- Codex init smoke verifies generated downstream projects receive the fresh and route-changed validator fixtures
- packaging tests verify the fixture set is bundled through the existing `templates/examples` force-include and can execute against the local Go runtime when Go is available
- no new workflow-state field was added; `resume-validation.json` remains an example or ephemeral command input until a later version deliberately persists it

## v1.3.11 Resume Validator Workflow Preference

v1.3.11 resume validator workflow preference is locally closed:

- generated workflow contracts now prefer the optional runtime validator when a compatible `project-cognition semantic-audit-resume` command is available
- workflows should build an ephemeral resume-validation.json from current workflow state plus concrete `semantic_audit_input_path` and `semantic_audit_output_path`
- if the validator returns fresh and `can_reuse_persisted_claim_readiness: true`, workflows may reuse persisted claim readiness for the same active claim
- if the validator is unavailable, blocked, or returns stale output, prompt fallback remains valid and final claims remain blocked until `semantic-audit-input.json` is rebuilt
- the preference does not make the runtime mandatory, does not add a persisted workflow-state field, and does not grant P3/P4 permission or source edits

## v1.3.12 Resume Validator Stale Case Matrix

v1.3.12 resume validator stale case matrix is locally closed:

- generated projects now receive executable stale fixtures for active-claim drift, missing audit files, claim authorization ref drift, and claim verification ref drift
- `resume-validation-active-claim-changed.json` demonstrates `semantic_audit_stale_reasons: [active-claim-changed, route-changed]` because the route fingerprint includes `active_claim_type`
- `resume-validation-missing-file.json` demonstrates `semantic_audit_stale_reasons: [missing-file]` while still returning JSON instead of failing the command
- `resume-validation-claim-ref-mismatch.json` demonstrates `semantic_audit_stale_reasons: [claim-ref-mismatch]`
- `resume-validation-verification-ref-mismatch.json` demonstrates `semantic_audit_stale_reasons: [verification-ref-mismatch]`
- packaging tests execute all stale fixtures against the local Go runtime when Go is available
- Codex init smoke verifies generated downstream projects receive the complete fixture matrix

## v1.3.13 Real Downstream Resume Smoke

v1.3.13 real downstream resume smoke is locally closed:

- Codex init smoke now writes workflow-local `semantic-audit-input.json` and workflow-local `semantic-audit-output.json` under a temporary downstream `.planning/debug/h5-env/` state directory
- the smoke constructs fresh and route-changed ephemeral `resume-validation.json` inputs from that workflow-local state instead of using the example fixture paths as validator input
- the local Go runtime validates fresh reuse with `can_reuse_persisted_claim_readiness: true`
- the local Go runtime validates route drift with `semantic_audit_resume_status: needs-rerun`, `semantic_audit_stale_reasons: [route-changed]`, and `can_reuse_persisted_claim_readiness: false`
- prompt fallback remains valid and the validator remains optional; this smoke proves downstream path resolution and resume behavior only

## v1.3.14 Resume Validator Test Hygiene And Release Readiness

v1.3.14 resume validator test hygiene and release readiness is locally closed:

- extract local helpers for running `project-cognition semantic-audit-resume` from Python tests without weakening coverage
- split the real downstream resume validator smoke into its own Codex init test with an explicit Go-toolchain skip when Go is unavailable
- keep long inline resume-validation JSON construction in the smoke because it proves generated workflows can build an ephemeral validator input from workflow state without relying on example fixture paths

## v1.3.15 Release Readiness

v1.3.15 release readiness is locally closed:

- full project-cognition Go tests pass with `go test ./...`
- full project-cognition vet passes with `go vet ./...`
- full Python suite passes with `python -m pytest -q`
- wheel packaging succeeds with `python -m build --wheel`
- `git diff --check` passes; the only output is the existing CRLF normalization warning for `templates/commands/implement-teams.md` and `templates/commands/map-scan.md`
- wheel packaging includes all new semantic-audit-resume fixtures through the existing `templates/examples` force-include

## v1.3.16 Release Publication

v1.3.16 release publication is locally closed:

- release notes now mention the optional `semantic-audit-resume` validator and the generated semantic-audit-resume example matrix
- release workflow smoke now verifies the Linux release binary exposes `semantic-audit-resume --input`
- release workflow smoke now runs the compiled release binary against fresh and route-changed `semantic-audit-resume` fixtures before creating the GitHub release
- no external release was triggered in this local workstream; publishing remains gated on an explicit release instruction
- latest local verification passed with `go test ./...`, `go vet ./...`, `python -m pytest -q` (`2354 passed, 7 skipped`), `python -m build --wheel`, and `git diff --check` with only the known CRLF normalization warnings

## Next Version: v1.3.17 External Release Trigger

Build next only when the user explicitly asks to publish or trigger the external release:

- treat `v1.3.17` as the semantic work contract design-slice label, not a Git release tag
- use the repository's SemVer package tag for release automation; do not look for or publish a `v1.3.17` Git tag for this workstream
- use `.github/workflows/release-trigger.yml` as the preferred release entrypoint so the release tag points at a commit whose `pyproject.toml` version matches the tag
- do not run `.github/workflows/release.yml` directly from a dirty local working tree; `release.yml` checks out the pushed tag or dispatched tag and cannot see uncommitted local changes
- confirm the working tree changes are committed and pushed before triggering release automation
- confirm the intended tag, likely `v0.5.14` if releasing from the current `0.5.14.dev0` development version after `v0.5.13`
- trigger or run the release process that publishes the updated project-cognition binary assets
- verify the released project-cognition binary exposes `semantic-audit-resume --input`
- verify a freshly initialized downstream project receives the semantic-audit-resume example matrix from the packaged release
- keep workflow authorization claim-readiness-only unless a separate permission contract explicitly allows P3/P4 influence
- decide ambiguous multi-claim authorization policy if workflows authorize multiple final claims without selecting a single active claim

v1.3.17 local preflight is closed in this working tree:

- release-trigger versus release workflow ownership is documented and tested
- `v1.3.17` is explicitly documented as a design-slice label, not a Git release tag
- user-facing docs avoid hard-coded stale development version literals such as `0.5.1.dev0`
- remote tag checks found no `v0.5.14` or `v1.3.17` tag at the time of local preflight
- the remaining work is external release execution after the changes are committed, pushed, and an explicit release version/tag is confirmed

## v1.3.18 Claim Readiness Policy Hardening

v1.3.18 claim readiness policy hardening is locally closed for verification
outcomes:

- matched failed verification results now block claim readiness with `verification_result_failed`
- matched blocked verification results now block claim readiness with `verification_result_blocked`
- matched skipped or otherwise inconclusive verification results now block claim readiness with `verification_result_inconclusive`
- a newer matching passed rerun for the same indexed verification owner path and selected candidate can restore verification satisfaction
- a newer matching failed, blocked, skipped, or inconclusive result can block again after an earlier pass
- status-specific blockers explain verification state only; they do not prove root cause, grant P3/P4 permission, authorize source edits, or make final claims
- generated workflow guidance now names the status-specific blockers and requires final claims to stay blocked until a newer matching passed rerun supersedes the failed, blocked, skipped, or inconclusive result

## v1.3.19 Active Claim Authorization Policy

v1.3.19 active claim authorization policy is locally closed:

- `workflow_authorization.active_claim_type` is the runtime input source for the single active final claim
- if `workflow_authorization.authorized_claims` contains multiple final claims and `active_claim_type` is empty, claim readiness stays blocked with `active_claim_type_required`
- if `active_claim_type` is not listed in `authorized_claims`, claim readiness stays blocked with `active_claim_not_authorized`
- single-claim authorization behavior remains backward-compatible
- runtime still does not infer active claims from workflow names such as debug, implement, or plan
- active claim selection affects claim readiness only; it does not grant P3/P4 permission, authorize source edits, or approve release
- user-facing guidance docs now document semantic-audit-resume, active_claim_type, authorized_claims, and verification outcome blockers; `tests/test_specify_guidance_docs.py` locks that release-readiness boundary

Next version: v1.3.20 External Release Execution

Build next only when the user explicitly asks to publish or trigger the external
release:

- confirm the intended SemVer release tag, likely `v0.5.14` from the current development version
- commit and push the current working tree changes
- trigger `.github/workflows/release-trigger.yml` with the confirmed version
- verify the published project-cognition binary exposes `semantic-audit-resume --input`
- verify a freshly initialized downstream project receives the semantic-audit-resume examples and active claim guidance from the packaged release

## Hard Boundaries For Future Maintainers

Preserve these rules across all future versions:

- Workflow name is only an intent hint; it is not a separate semantic router.
- Agent normalization is an input to project-backed routing, not project fact.
- Database candidates are not proof that behavior exists.
- `semantic-intake` never reads live source, edits files, runs tests, or authorizes final claims.
- Permission can only rise with live evidence and verification.
- Learning must stay conditional and reversible until evidence promotes it.
- Prompt changes requiring runtime support must ship with installer, launcher, release, and compatibility checks.
