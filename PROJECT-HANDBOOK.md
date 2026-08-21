# Project Handbook

**Last Updated:** 2026-08-17
**Purpose:** Root navigation artifact for this repository.

## System Summary

`spec-kit-plus` packages two deliberately separate command planes. The Python `specify` CLI initializes and repairs projects, installs agent integrations, packages assets, and retains explicitly human/operator or compatibility helpers. Generated `sp-*` and `spx-*` workflows use the project-local Go `specify-runtime` binary as their only workflow control plane for artifact reads, writes, transitions, validation, handoffs, Learning, cognition, and Codex durable-team state. Python workflow implementations may remain as tests or compatibility adapters, but generated agents must not call them.

The repository has four mapped runtime modules:

- `specify-cli-core`: Python bootstrap/operator CLI, integration registry, packaging, compatibility adapters, testing/eval helpers, and legacy execution contracts that are not the generated agent control plane.
- `specify-runtime`: Go-native agent workflow runtime, artifact registry and transactional mutation layer, workflow state machine, task/packet/result lifecycle, cognition, Learning, validation, review/acceptance, PRD, discussion, design, and durable-team state surfaces.
- `templates-generated-surfaces`: workflow command templates, command partials, advanced-model skills, passive skills, project-map compatibility/export templates, scripts, and worker prompts that are copied or transformed into downstream projects.
- `agent-teams-engine`: bundled optional Node/TypeScript plus Rust runtime assets for Codex team coordination.

Project cognition compass, query, and expansion responses carry an `epistemic_contract` with `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. This contract cannot authorize source changes and cannot prove current behavior; agents must carry it into downstream state, withhold unverified claims, and let contradictory live evidence override the route candidate.

Graph claims are indexed assertions. Their lifecycle is `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale`; even `verified_in_graph_generation` is scoped to the active graph generation and is not current repository truth. Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; bounded live evidence, matching workflow verification, and explicit final-claim authorization remain separate requirements.

Schema v5 adds revision-bound, expiring reconciliation to the auditable live feedback loop and current evidence basis while preserving superseded claim evidence as history. Decisive claim-specific bounded reads provide an in-memory semantic intent to `specify-runtime cognition claim-reconcile prepare --input-json '<intent-json>' --format json`; never create an intent file. The runtime owns every integrity field and returns a prepared packet path plus structured `apply_argv`. Execute that argv through `specify-runtime cognition claim-reconcile apply --input <prepared_packet_path> --format json`, then rerun Compass once on ready. This remains route-candidate evidence and cannot authorize a workflow final claim. Schema v5 does not migrate schema v4 or older databases.

## System Boundaries

This repository owns the human/operator `specify` CLI, the agent-facing `specify-runtime` CLI, bundled templates/scripts, supported-agent integration adapters, project-map compatibility/export templates, extension/preset managers, and optional Codex team runtime packaging. It coordinates with external agent CLIs, Git, uv/pip packaging, Node/npm, Cargo/Rust, optional MCP dependencies, tmux/psmux, and GitHub Actions. It does not own upstream agent CLI behavior, external MCP server implementations, terminal multiplexers, or the user's global `specify` installation.

## Design Governance Foundation v1.0

This section is an **architecture constraint declaration**, not a changelog.
It freezes the minimum quality contract for AI-generated design artifacts in
spec-kit-plus.

### Overview

spec-kit-plus is not only a design-artifact generator. The Design Governance
Foundation defines whether an AI design artifact is **implementation-ready**:

- derived from explicit design intent (taste intake)
- iterated against explicit user feedback without arbitrary option branching
- validated through machine-checkable rules
- recoverable when validation fails
- protected against regression through golden artifacts

Preview rounds are freeform and single-concept. The Agent probes live image
generation, image inspection, and image editing capabilities independently;
it never infers them from an integration name. Generation-capable sessions use
an image-primary board bound to its exact generate/edit prompt and adjacent
machine manifest. Other sessions use the self-contained HTML-primary canvas
(chrome only in the scaffold). Inspection availability determines whether the
Agent may make a visual-quality claim or the user owns visual critique. The
Agent asks one high-impact question at a time, recommends a grounded default,
authors the current concept, and iterates it in immutable rounds until explicit
user approval. Fixed specimen grids must not constrain visual imagination;
governance lives in the machine manifest, ready lint, approval/handoff sidecars,
diagnostics, and golden artifacts.

The shared **UI Professional Skill** pack applies progressive disclosure before
concept authoring. A compact catalog routes the request to exactly one domain,
zero-or-one visual style, and zero-to-two specialists; only those references are
loaded. The route is persisted for the immutable round, while material
ambiguity asks one high-impact question. Approved references and registered
design truth take precedence, and image-primary and HTML-primary keep separate
prompt contracts. Web routes also persist a compact
`mature_web_ui_resource_ids` shortlist. The component gate inspects installed
libraries and live components first, selects at most one mature primary system,
adds headless or specialist support only for an exact gap, and retrieves
official Agent Skills, MCP, or LLM docs only for shortlisted candidates. Its
bounded local scan records the live asset inventory without network or writes;
deterministic reason codes explain the primary/supporting choice, and routed
smoothness acceptance IDs bind to the existing usability and integrated Review
evidence contract.

Live product UI is the default style authority. Feature, component, and partial
functional-page work uses `inherit-existing`, exact live source refs, protected
`global-shell`/`shared-components`, no style-delta surfaces, and no style skill.
Only explicit user authorization for one exact complete-page visual overhaul
permits `page-overhaul-authorized`; shell, shared components, and sibling pages
remain protected. The structured authority is carried unchanged through Design,
UI brief, Spec/Plan, Tasks, worker packets, and Review.

Formal routing distinguishes design-first from post-Specify work. Design-first
continues through Specify. When a planning-ready feature spec exists before
Design and its requirements/scope/acceptance remain unchanged, a
`formal-post-specify` receipt binds the registered Design to the unchanged
source-spec digest and Plan verifies it with `specify-runtime design adoption`.
The normal route is `specify -> design -> plan`; it does not run a second
Specify. Only a genuine requirements change reopens Specify.

Product evolution after v1.0 should prefer real-project stress tests of this
contract over stacking more ready-gate conditions.

### Governance pipeline

```text
Intent
  → Taste Intake
  → Direction Strategy
  → Live Visual Capability Route
  → Manifest
  → Structural Validation
  → Semantic Validation
  → Visual Quality Validation
  → Diagnostic Recovery
  → Implementation
```

### Validation layers

Every new governance rule must declare a layer and a recovery class before it
ships. If it cannot answer the questions below, it is not ready for the
governance surface.

#### Structural

**Question:** Can this artifact be correctly understood?

Examples: schema validity, required fields, artifact shape, parseability.

**Recovery:** Fix structure. Do **not** regenerate design intent.

#### Semantic

**Question:** Does this artifact represent real project design intent?

Examples: scaffold leakage, unresolved taste decisions, template-derived
reasoning, placeholder families.

**Recovery:** Redo intake and design reasoning. Do **not** only retune colors.

#### Quality

**Question:** Are design directions materially different and implementation-ready?

Examples: insufficient dial divergence, identical visual fingerprints,
metadata-only differentiation.

**Recovery:** Modify render-driving visual systems (typography, geometry,
density tokens, elevation, motion, modes). Do **not** only rename metadata.

### Diagnostic contract

Every governance failure must provide:

- diagnostic code
- validation layer (`structural` | `semantic` | `quality`)
- reason (`why`)
- recovery guidance
- agent action constraints

Failures guide correction; they do not only block execution. Source of truth:
`templates/design-diagnostic-contract.json`. Fingerprint rule contract:
`templates/visual-fingerprint-rule.json` and
`templates/design-library/visual-fingerprint-spec.md` (versioned; comparable
only when version and dimensions match).

### Golden Artifact Set

The Golden Artifact Set is the **regression source of truth**, not ordinary
unit-test junk data. Location: `tests/fixtures/design-preview/`.

It contains valid and invalid design-preview artifacts, expected ready-lint
outcomes, and expected diagnostic contracts. Regeneration uses
`scripts/generate-design-preview-golden-set.py` only when governance rules
intentionally change.

**Correct evolution path**

1. Explain why the design standard must change.
2. Update the Golden Set (or introduce an explicit version path).
3. Pass regression.

**Forbidden evolution path**

1. Rule fails on CI.
2. Weaken the rule solely to make existing artifacts pass.
3. Green CI without a standards rationale.

### Rule admission checklist

Before adding or tightening a ready-level condition, answer all of:

1. Layer: structural, semantic, or quality?
2. Recovery: what must the agent change, and what must it **not** change?
3. Diagnostic: code, why, recovery, agent_action present in the contract?
4. Golden case: is there a valid or invalid fixture that locks the intent?

If any answer is missing, the rule does not enter governance.

### Version policy (v1.0 freeze)

v1.0 freezes:

- validation layer taxonomy (structural / semantic / quality)
- diagnostic recovery model
- golden artifact concept as regression truth
- fingerprint validation principle (render payload, not labels alone)
- non-weakening policy for gates under green-CI pressure

Future changes must preserve compatibility or introduce an **explicit**
version migration path (for example fingerprint rule v2, golden_spec_version).
Do not silently expand ready conditions as the default growth mode.

### Out of foundation scope (future)

Agent repair loops may sit on top of this foundation only when they:

1. read diagnostic contracts for bounded fix scope
2. re-run ready lint
3. remain accountable to the Golden Set (fail before fix, pass after fix,
   no cheat-path substitution)

Automatic repair without golden accountability is not part of v1.0.

### Source surfaces

| Concern | Location |
| --- | --- |
| Workflow entry | `sp-design` / `$spx-design`, design brief, design CLI |
| Ready lint / fingerprint | `src/specify_cli/design.py` |
| Diagnostic recovery | `templates/design-diagnostic-contract.json` |
| Fingerprint rule | `templates/visual-fingerprint-rule.json` |
| Fingerprint human spec | `templates/design-library/visual-fingerprint-spec.md` |
| Golden Set | `tests/fixtures/design-preview/**` |
| Golden harness | `tests/test_design_artifact_golden_set.py` |

## Design Governance Foundation v2.0 — Change Scope And Consumption

Foundation v1.0 continues to govern preview quality. Foundation v2.0 changes
the ownership model: `DESIGN.md` is a deliverable for one bounded UI change,
not an evergreen project-wide authority.

- Start a change with `specify-runtime design change UD-####`; its canonical
  contract is `.specify/design/changes/<UD-ID>/DESIGN.md` and its brief,
  previews, approval, immutable handoff, review, and exported
  `design-contract.json` remain in the same workspace.
- Refine registered truth with
  `specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID>`. The runtime
  pins `iteration_of`, `basis_sha256`, the exact baseline ref, and `supersedes`
  while leaving the source immutable. Requested scope must remain active on the
  source; an excluded subtree iterates from its active successor instead.
- `.specify/design/index.json` is metadata-only discovery state. It records
  change identity, scope, relationships, status, canonical path, and the
  registered document SHA-256; it does not merge UI rules or choose a latest
  design for consumers.
- `specify-runtime design register <change-local-DESIGN.md>` is the consumption
  boundary. It requires `specify-runtime design lint <change-local-DESIGN.md>
  --level ready`, pins the exact bytes, rejects mutation of an approved record,
  and rejects overlapping active scopes unless the new change explicitly
  declares `supersedes`. It records only intersecting parent scope as
  `superseded_scopes`; the parent remains active outside those exclusions.
- `specify-runtime design resolve --scope <exact-surface>` is discovery only.
  It can return composite parent/successor coverage, which must be split into
  independently bound consumer units because current binding artifacts are
  singular. Each unit owns one exact scope and one binding file. Before replacement, use
  `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID>`, then run the
  read-only `specify-runtime design impact <consumer-ref> --change
  <CANDIDATE-UD-ID> --scope <exact-surface> --mode <formal|quick>
  --expected-change <CURRENT-UD-ID|none>`. The preview reports affected
  `DS-*`/`DH-*` IDs, `preserved_bindings`, `invalidated_bindings`, and
  `reconcile_from`. After the
  owning workflow updates and hashes `spec-contract.json` or the independent
  `ui_design_binding` block in Quick `STATUS.md`, use
  `specify-runtime design adopt ... --expected-change
  <CURRENT-UD-ID|none>` to append the compare-and-swap receipt. The owning
  workflow reconciles only the receipt's affected stages and Review scope;
  completed implementation and unaffected evidence remain valid, and the
  design runtime does not rewrite consumer artifacts.
- Quick adoption additionally requires sibling `confirmation.json` state
  `confirmed|inherited` and `STATUS.md` frontmatter
  `understanding_confirmed: true`. Before confirmation, exact `scope` plus the
  four registered fields are staged as confirmation-protected
  `decision.ui_confirmation.design_binding`; afterward, the independent
  top-level `ui_design_binding` adoption copy is patched in STATUS. The two
  copies must exact-match, and the decision copy remains in `confirmation.json`
  rather than being manually written into the runtime-managed STATUS
  projection.
  A successful Quick replacement retires unstarted affected packets, stops
  in-progress affected packets at a safe boundary, preserves completed work,
  creates a corrective work item for drift, and recaptures only affected Review
  evidence.
- Specify, Quick, Plan, Tasks, worker packets, Review, and Acceptance pin one
  registered `UD-*` identity, path, digest, and selected `DS-*`/`DH-*` rows.
  They never resolve “latest” and never silently retarget active work.
- Durable invariants that should apply to future unrelated changes belong in
  project rules. The change contract itself remains immutable history.
- A pre-existing root `DESIGN.md` is a read-only legacy baseline. Init no longer
  creates it, and design workflows never overwrite it. Migration creates a new
  `UD-*` change that may cite the legacy file in `baseline_refs`.
- External screenshots, mockups, URLs, and code references still use Classic's
  `ui-reference-artifact` lane and `ui-reference-notes.md`; fidelity defaults
  to `approximate`, and an unavailable comparison remains
  `pending-human-review`.

ADR-0001 (`docs/adr/0001-change-scoped-ui-design-contracts.md`) is the decision
record for this ownership model. ADR-0002
(`docs/adr/0002-scope-aware-ui-design-iteration.md`) defines successor lineage,
partial supersession, resolution, semantic diff, and explicit adoption.

## High-Value Capabilities

- **Classic SKILL invocation boundary**: Passive model invocation is allowed only
  for `sp-discussion`, `sp-quick`, `sp-debug`, and `sp-fast`. Every other Classic
  `sp-*` SKILL is user-invoked only: routing may recommend its projected command,
  but must stop until the user invokes it. An already user-invoked workflow may
  resume without requiring the command name on every turn.
- **Project initialization and generated agent surfaces**: `specify init` resolves `--ai` or `--integration`, installs command/skill/workflow files, copies scripts/templates, and records integration manifests. Read `src/specify_cli/__init__.py`, `src/specify_cli/integrations/**`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Generated-project repair and compatibility diagnostics**: `specify check` now surfaces broken project launchers, stale generated runtime assets, and Claude personal workflow skills (`sp-*` / `spx-*`) that shadow same-named project-installed skills. Claude shadowing is a repairable block because personal scope wins over project scope; init/install and SessionStart warn immediately, while `specify integration repair` preserves the personal files and returns a human recovery tutorial instead of mutating state outside the project. Read `src/specify_cli/__init__.py`, `src/specify_cli/launcher.py`, `src/specify_cli/integrations/base.py`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- **Project Learning lifecycle**: Agents consume Learning only through read-only CLI progressive disclosure: `learning start` returns relevant compact cards, `learning list` filters/pages summaries, and `learning show` expands one selected agent-oriented record. `capture` / `capture-auto` create or merge every reusable candidate; `learning start` protects mature knowledge with a 15-card stable quota and up to 5 candidate cards, while ranking candidates by context, assessed value, recurrence, and novelty and diversifying repeated families when enough exist. The bound controls disclosure, not storage. `promote` explicitly confirms a candidate before any separate project-rule promotion, so reads never mutate lifecycle state. Classic commands share the Learning partial/passive skill, every Advanced skill receives `_shared/project-learning.md`, and SPX names normalize to the same Classic namespace. Confirmed, index, detail, and candidate files remain runtime implementation surfaces rather than normal agent reads.
- **Project Learning assessment and policy**: Start/list/show may include an optional backward-compatible `assessment` with independent learning-value tier/reasons, content sensitivity/risk/redaction labels, and `capture-safe|capture-sanitized|defer|ignore` decision/reason. Sensitivity is never an eligibility veto: reusable sensitive lessons are abstracted and captured, while high-value evidence is deferred only when sanitization removes all reusable meaning. Canonical labels cover credentials, email, private keys, machine paths, personal identifiers, business identifiers, and organization-sensitive terms. `.specify/config.json.project_learning` accepts only four literal detector lists (at most 64 distinct 1..128-character entries each) plus `deferred_review_days=1..365`; arbitrary regex is forbidden. Invalid policy warns on built-in-protected reads, while mutation or assessment commands (including dry-run) fail closed.
- **Project Learning review and observability**: `capture-auto --dry-run` returns a sanitized assessment without writes. Runtime-native `learning review` records `none|captured|auto-captured|deferred|manual-capture-needed`; deferred and manual-capture-needed require rationale and remain pending until a matching durable candidate, confirmed learning, or project rule exists. Captured decisions succeed only after that match is verified, while `none` is blocked by matching pending work. Read-only `learning status` reports aggregate pending/due/age buckets only, without rationale, Learning refs, recurrence keys, or timestamps. `learning metrics` reports aggregate totals, decisions, value/risk tiers, reason/label counts, derived confirmation rate, and in-memory age buckets. Persistent metrics never contain age buckets, evidence, Learning refs, paths, rationale, or timestamps. Neither read surface mutates aging or increments metrics.
- **UI design-change handoff**: Governed by **Design Governance Foundation v1.0** for artifact quality and **Foundation v2.0** for ownership and consumption. `sp-design` / `$spx-design` routes one prompt to `create/refine/audit`, uses `specify-runtime design change` for a new bounded `UD-*` workspace, and uses `specify-runtime design iterate` for a digest-pinned successor whose requested scope is still active on the source; a root `DESIGN.md`, when present, is only a read-only legacy baseline. Reference synthesis remains an input strategy for create/refine. Visual create/refine uses durable taste intake, one high-impact question at a time, one professionally authored concept per immutable review round, feedback-led iteration, ready lint, explicit user approval, byte-bound approval, immutable handoff, stable `DS-*` decisions, and stable `DH-*` implementation contracts. Existing-product local UI records exact `style_authority: inherit-existing`; only explicit exact complete-page overhaul authorization permits a bounded style delta, never across protected shell/shared components. `specify-runtime design register` pins the approved document digest and partial `superseded_scopes` in metadata-only `.specify/design/index.json`. `specify-runtime design resolve` discovers exact-scope candidates only; current binding artifacts are singular, so composite coverage becomes independently bound consumer units. `specify-runtime design diff` records the semantic delta, read-only `specify-runtime design impact` CAS-checks one exact consumer and reports `preserved_bindings`, `invalidated_bindings`, and `reconcile_from`, and `specify-runtime design adopt` appends the same impact-bound expected-change receipt after the owning binding file changes. `sp-specify` and `sp-quick` select an exact registered change; later approvals never silently retarget active work. Design-first formal adoption rebinds `spec-contract.json` through Specify. A late design overlay with unchanged requirements uses `formal-post-specify`, preserves source-spec bytes, and returns directly to Plan after `specify-runtime design adoption` verification; only a requirements change reopens Specify. Quick stages exact `decision.ui_confirmation.design_binding`, confirms or inherits it in `confirmation.json`, then patches the exact-matching independent top-level `ui_design_binding` adoption copy in `STATUS.md`; the runtime rejects drift between those copies, retires only unstarted affected packets through the Quick owner, preserves completed work, and routes drift to a corrective work item. Feature `ui-brief.md`, Plan, Tasks, worker packets, Review, and Acceptance carry the exact change ref/hash, style authority, and selected immutable rows instead of copying a global design system or resolving “latest”. External UI references still use the CLI-owned reference/evidence lanes, optional `ui-target.html` remains feature-local, and completion requires real-entrypoint evidence plus a bound `spec-kit-visual-comparison-v1` report; unavailable comparison remains `pending-human-review`.
- **Agent-native phase pipeline**: At handoff, `sp-discussion` presents both routes and their eligibility, explains any blocker, gives a complexity-informed recommendation among eligible routes from delivery complexity and consequence profile, and requires the user's final choice before emitting one confirmed Agent-only JSON requirement contract. For bounded, well-understood delivery it recommends `sp-quick`; for high ambiguity/complexity, interacting systems, architecture/data migration/security/compliance/rollout concerns, broad acceptance obligations, or durable traceability it recommends `sp-specify`. Size alone is not a hard routing ceiling, and either eligible user choice wins. Quick binds the contract into task-local `STATUS.md`; the formal path compiles it into `spec-contract.json`, conditionally enters `sp-deep-research` only when its feasibility gate selects unproven capabilities, then continues through `sp-plan` (`plan-contract.json`), optional `sp-test-design` / `spx-test-design`, `sp-tasks` (`task-index.json` plus per-task lifecycle records), `sp-implement` (`implementation-handoff.json`), mandatory `sp-review` / `spx-review` (`review-state.json`), and finally human `sp-accept` (`human-acceptance.json`). Test Design is an independent producer and does not require a completed Plan: a project, feature, Plan, Quick task, Tasks graph, or Review may select it. It treats current code, tests, configuration, official contracts, and live evidence as factual authority while Project Cognition only navigates, then coordinates bounded read-only discovery plus an independent audit. The runtime publishes a complete-against-frozen-scope case/data/gap package and typed pointer-only projections for Plan, Quick, Tasks, and Review. Those consumers verify and read projections without modifying canonical Test Design; Implement receives only the verified task-packet TC/TD subset, and Review uses Test Design as an oracle rather than PASS evidence. Executable tests and fixtures remain owned by Tasks and Implement.
- **Deep Research feasibility gate**: `sp-deep-research` / `spx-deep-research` is neither generic web research nor architecture planning. `specify-runtime deep-research` binds the current spec digest and selected `CAP-*` set, owns revisioned track preparation/leases/submission, validates repository, primary external, and disposable-spike provenance, records Leader accept/reject decisions and one retry under `research/rejections/`, synthesizes contradictions and reverse coverage, requires a separate audit identity, then publishes and verifies an exact `research/handoff-to-plan.json` digest. `deep-research.md` is derived only. Generic artifact, evidence, and result channels cannot mutate the package. The gate never edits production source/tests and does not choose the final Plan architecture.
- **Post-implementation system review and human acceptance**: `implement closeout` prepares the Review handoff, not human acceptance. Review owns `review-state.json`, `review-results/`, and integrated `review-evidence/`; its closeout refreshes `implementation-summary.md`, preserves `human_acceptance_obligations` and `human_acceptance_scenarios` in the Review-to-Accept handoff, and prepares a fingerprinted `human-acceptance.json` projection bound to the approved reviewed snapshot and Review-owned runtime targets; it does not prefill human PASS. Acceptance requires zero uncovered required human obligations, does not repeat System Review, and cannot edit source. The Accept Agent safely starts or checks those immutable targets (`source`, `build`, `deployment`, or `device`), records only session readiness/action fields, prepares isolated test data, positions the start state, and assists with diagnostics, while the human performs each new-or-changed requirement journey and supplies structured confirmations plus the final verdict. Accept does not diagnose: every failed observation first goes to the Review Leader, who owns diagnosis, an independent Fix, and independent revalidation and may return upstream only after proving a requirement, design, or architecture truth gap. Any repair creates a new Review cycle and resets every human scenario; changed code/config, reviewed snapshot, or runtime target identity invalidates prior Review and acceptance evidence.
- **Cross-profile blocked exits**: Every generated Classic `sp-*` command and Advanced `spx-*` skill uses the shared workflow-blocker schema and compact human view. A blocked exit records workflow/stage, category, owner, exact cause, sanitized evidence, attempted recovery, affected scope, next action, unblock criteria, and resume point. Agent-capable repair and available fallbacks must not be delegated to the user. Genuine human boundaries add a self-contained Human Action Guide with prerequisites, safety, numbered UI/command steps, expected result and failure branch per step, independent verification, sanitized evidence to return, and the exact resume action. Protected CI guidance binds repository, branch, commit, pipeline/job, authorization, terminal status, and pipeline URL/ID; pending UI review binds the real entrypoint, viewport/state matrix, approved references, decision criteria, captures, and repair notes.
- **Adaptive planning dispatch**: `sp-plan` and `sp-tasks` use `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`. Delegate only when expected critical-path gain exceeds handoff cost; no safe packetization is a blocker for heavy work, not a reason to shrink scope. Native lifecycle discovery requires only the integration's exposed dispatch and join surfaces; accepted terminal results need no separate cleanup call. Classic and Advanced native planning/task lanes use stage-owned `result submit`, while `sp-teams submit-result` is reserved for explicitly selected durable-team execution.
- **Debug workflow confirmation**: The full `sp-debug` branch performs one Debug Understanding Checkpoint before substantive investigation. Its main table contains reporter-owned problem facts, expected behavior, occurrence conditions, investigation boundary, fix authority, assumptions to correct, and reconfirmation triggers; agent hypotheses and evidence sequencing stay outside the approval table. Applicable UI symptoms add an independent target-baseline card, with one reply for both and no speculative repair approval.
- **Quick workflow contract**: `sp-quick` / `$spx-quick` is a resumable direct-delivery workflow, not a small-task-only lane. Use it when the requested outcome is clear enough to implement without first creating a formal specification, including larger multi-capability, architecture, migration, compatibility, rollout, or acceptance-heavy work. One workspace may own an ordered `Q1`/`Q2`/... work-item ledger, dependencies, per-item acceptance, multiple lanes or batches, consequence tracking, and final validation; task size or consequence breadth alone must not force a handoff to `sp-specify` / `$spx-specify`, which remains a separate formal specification path chosen explicitly.
- **Quick/Debug context-direct preflight**: Before any tool call, `sp-quick` and `sp-debug` assess only evidence already present in the current conversation context. They offer a user choice between **context-direct** change/fix and the full workflow only when that evidence names the exact owner, consumers, consequence boundary, and verification entrypoint; Debug additionally requires a reproduced signal and proven failure mechanism with no competing hypothesis. Unknowns show no menu. Large, cross-cutting, multi-item, acceptance-heavy, or resumable work always uses full Quick, while an unproven cause always uses full Debug. Context-direct creates no Quick/Debug workflow state and skips entry Learning and Project Cognition navigation, but keeps RED/reproduction, fresh verification, diff review, side-effect gates, and exact-changed-path Project Cognition closeout.
- **Quick workflow confirmation**: Raw quick requests that enter the full Quick branch stage one runtime-owned Decision Checkpoint (`specify-runtime quick checkpoint-stage` / `checkpoint-confirm` / `checkpoint-show`) for the user-owned overall outcome, visible result, scope, ordered `Q1`/`Q2` work items and deliverable-level dependencies, acceptance for every item, recommended approach, assumptions/risks, overall completion evidence, and reconfirmation triggers. `confirmation_digest` covers decision fields only. Delivery Map waves, subagents, file splits, and test order are agent-owned projections and never require user approval. Applicable UI work adds an independent implementation-proposal card and one reply confirms both. A confirmed discussion contract with no quick-stage semantic delta is inherited and does not repeat confirmation; show binding summary plus Delivery Map/Pulse instead.
- **sp-* compact quality standard**: Before adding, modifying, or compressing any `sp-*` workflow prompt, handoff shape, state artifact, task packet, or validation closeout contract, use `docs/workflow-quality/README.md`. A candidate optimization must show quality retention of at least 98% and whole-chain cost reduction; do not shorten prompts by moving ambiguity or interpretation burden downstream.
- **User-confirmed product scope**: Generated workflows preserve the user's complete user-confirmed scope. Workflow routing may choose the lightest safe command surface, but `sp-plan` and `sp-tasks` must not convert the user's product intent into a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`. Scope reduction requires user confirmation, including when a named constraint forces a scope decision. Complexity alone is not a valid reason to shrink scope, defer ordinary work, or block; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
- **Command-surface minimization**: Command-surface minimization must not delete capability. When upstream discussion or specification text includes a new/create/scaffold/authoring operation, `sp-specify`, `sp-plan`, and `sp-tasks` must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact. Manual copy steps and template-only docs are support material, not a replacement for the confirmed operation unless the user selected that narrower entry point.
- **Agent-facing CLI runtime**: Every `sp-*`, `spx-*`, and delegated-worker CLI operation runs through the project-local `.specify/bin/specify-runtime` (`.exe` on Windows). Negotiate this unified Go control plane with `specify-runtime api handshake --format json` and list its compact capabilities with `specify-runtime api list --format json`; Python `specify` remains human-only for bootstrap, init, upgrade, repair, and legacy operator maintenance. Required phase order lives only in CLI-owned `FEATURE_DIR/workflow.json`; rich `workflow-state.md` remains workflow-owned evidence, resume, analysis, and Learning state. An active owner validates and closes its artifacts with `specify-runtime workflow complete-stage`; the destination owner then executes the exact returned `specify-runtime workflow transition --to <stage>` argv. Evidence-backed `specify-runtime workflow reopen` handles an invalidated earlier or same completed non-accept stage. A persisted blocker cannot be replaced; `specify-runtime workflow resolve` requires sanitized resolution evidence, restores the same owner, and retains the full blocker audit. Only completed `accept` is terminal. The runtime refuses skips/stale writes without mutation and uses exit code `10` for a detailed resumable blocker. Do not make agents rebuild command parameters, phase state, or human recovery tutorials from prompt prose.
- **Semantic `sp-specify` traceability**: `sp-specify` preserves intent through `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and a minimal compatibility `brainstorming/handoff-to-specify.json`. `alignment.md` is the semantic traceability surface for `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts`; no upstream capability-like signal should disappear between discussion and spec.
- **Evidence-backed project Q&A**: Use `sp-ask` for read-only project questions before choosing an action workflow. It can use project cognition to navigate, but it answers from live evidence and does not create state, handoffs, tests, builds, or source edits. Same-topic follow-ups reuse the prior evidence set when it still applies; localized, mixed-language, CJK, colloquial, or project-slang terms are normalized into project vocabulary; complex answers separate proven facts from evidence-derived inferences and unknowns. It is independent from `sp-discussion`, does not create `.specify/ask/`, does not run package managers or project CLI commands by default, and has no `specify ask` Typer helper in v1.
- **Pre-spec discussion**: Use `discussion` before `specify` or `quick` when product direction, trade-offs, or context boundaries are not yet stable. Human-visible replies remain human-first and adaptive; compact typed state stays backstage. After explicit handoff request, boundary lock, self-review, and confirmation, `sp-discussion` writes exactly one Agent-only `handoff-to-specify.json` requirement contract. It has no Markdown companion or reviewer-guide artifact. The contract preserves target need, scope, constraints, success criteria, design direction, evidence refs, target boundary, decision digest, Must-Preserve/Consequence refs, consumer eligibility, and recovery. Downstream consumers query supporting discussion artifacts through targeted `specify-runtime artifact show` calls only when a named evidence ref is stale, missing, or contradictory.
- **Discussion cadence**: Continue by default, do not ask for continuation, and ask only when user judgment is genuinely required and no safe default exists.
- **Agent-native discussion state**: Human frontstage replies are written from the human's point of view with adaptive headings; agent backstage uses a compact typed `DiscussionTurnPacket`. Canonical state is `discussion-state.json`, Markdown is a derived compatibility view, and `discussion-log.jsonl` contains semantic checkpoints. Lifecycle is `explore -> ground -> decide -> prepare -> review -> ready -> consumed|closed`; UI, blockers, evidence, persistence mode, and confirmation are orthogonal. Checkpoints are meaning-driven rather than turn-count-driven. The handoff itself is JSON-only, and user confirmation plus downstream consumption bind to a stable `review_digest`.
- **Discussion downstream continuation**: The confirmed `recommended_consumer` controls the next path. `sp-quick` binds the contract and digest into task-local status for direct delivery; `sp-specify` enters compile mode for a formal spec-first path. Both reuse confirmed decisions and evidence and avoid duplicate review when `semantic_delta` is empty.
- **Discussion unified frontstage replies**: All `sp-discussion` visible replies use the same flexible contract. For readiness summary, include locked direction, reason, blocked decisions, evidence gaps, downstream planning inputs to preserve, default discussion action, and override path; do not split the work into P0/P1/P2, migration phases, release batches, task packets, or ordered implementation steps because Quick task-local planning owns them when Quick is selected, while `sp-plan`, `sp-tasks`, and `sp-implement` own them on the formal path. For pre-handoff readiness, include likely verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path without creating a separate assessment artifact. For draft handoff review, include recommended route, scope to approve, excluded scope, readiness checks, package paths, digest, and allowed review decisions. Bind approval to that digest with `discussion confirm-handoff` before marking ready. Do not require fixed headings, fixed cards, or a template ID selection step.
- **Discussion fallback language**: When the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, `sp-discussion` records that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. It must not turn that into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.
- **Discussion handoff repair ownership**: In `sp-discussion`, resubmit the corrected compact semantic input through `specify-runtime discussion write-handoff`; the CLI alone repairs canonical JSON and recomputes its digest. Then confirm that exact revision through `discussion confirm-handoff`. Do not edit the handoff, recompute its digest manually, or render/compare a Markdown copy.
- **Discussion next-step content**: When `sp-discussion` recommends a default next step, the same reply should include the first-pass content for that step, such as a draft, option board, readiness checklist, handoff assessment checklist, evidence plan, or field-by-field responsibility audit table. Do not make the user ask for "next" just to see the content the workflow already recommended.
- **Discussion decision digest**: `sp-specify` preserves selected direction, relevant rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and must-not-dilute constraints through `decision_digest_ref`. `sp-quick` carries the same digest into `STATUS.md`; when no quick-stage semantic delta exists, it reuses the confirmed digest instead of repeating the checkpoint.
- **Existing-project PRD extraction**: `sp-prd-scan -> sp-prd-build` is the canonical heavy reconstruction PRD lane for reverse-extracting repository-first current-state product documentation from code, docs, tests, routes, UI/API surfaces, and atlas evidence. Substantive scans are subagent-mandatory, critical claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. The ten growing JSON ledgers/contracts are maintained one semantic row at a time through `specify-runtime prd-scan record-upsert|record-remove|record-show|record-list`; the runtime owns envelopes, ordering, optimistic digests, atomic writes, and freshness invalidation, so agents never reserialize those full files. `specify-runtime prd-build scaffold` atomically expands all missing master/export boilerplate from installed templates, after which agents patch only semantic sections instead of reconstructing or replacing large documents. `sp-prd-build` compiles from the scan package into the expanded reconstruction archive; `exports/README.md` is the package navigation entry, `exports/prd.md` remains the primary reader-facing PRD, and `sp-prd-build` must not reread the repository. PRD initialization, freshness sealing, status, and semantic readiness are owned by `specify-runtime`; the human `specify prd*` commands and retained shell wrappers are adapters to that Go runtime, while `scripts/shared/prd-state.py` is inactive legacy compatibility data. `sp-prd` is deprecated compatibility-only routing into that pair, which remains a peer workflow path to `sp-specify` with no automatic planning handoff.
- **Concurrent Run control**: `tools/specify-runtime/internal/runcontrol/` is the repository-shared authority for independent `sp-*` and `spx-*` executions. Host adapters use `specify-runtime run launch ... -- <agent argv>` to queue and start a Run in one call; `run supervise` starts a replacement Attempt for an already queued or interrupted Run. Both accept either a compiled packet receipt through `--work-packet-file <path> --work-packet-sha256 <sha256>` or optional manual `--work-agent-id`, `--work-task-ref`, `--work-summary`, and `--work-intents-json` metadata. Packet bytes are digest-verified before parsing. Under the default `auto` workspace policy, exactly one non-overlapping modifying Run owns the primary workspace when its checkout is pristine; every overlap and every idle-but-dirty launch receives an isolated worktree. Overlaps clone the primary Run's pre-launch Snapshot. The supervisor forces child cwd, exports the fenced Run/Attempt/Workspace and `SPECIFY_WORK_ID`/`SPECIFY_WORK_FENCE` bindings, maintains leases, releases primary ownership on success, failure, cancellation, interruption, and stale recovery, and quarantines interrupted generations. Successful execution seals an immutable Result. Delivery then uses `specify-runtime result show -> specify-runtime candidate build -> candidate review -> accept receipt -> cas publish`, with `sync safe` as a separate guarded primary-workspace update. Publish and sync exclude an active primary owner, accept only the exact sealed primary Result as accounted local state, reject and preserve every additional index/worktree change, and reconcile durable publication/sync receipts after interruption. Review repair creates a new Run, Result, and Candidate; agents never merge worktrees or mutate Run-control storage directly.
- **Shared Work Board**: The same repository-shared `run-control.sqlite` stores durable `work_items` and `write_intents` for ordinary and durable-team modifying agents. Managed `run launch|supervise` reconciles expired work, registers the task before child launch, renews its lease without overwriting child-authored scope revisions, completes it on success, retains it as blocked after a nonzero exit, and conservatively interrupts cancellation. Unhosted agents use `specify-runtime board reconcile`, inspect ownership through `board show|owner`, register planned writes through `work begin`, and atomically expand scope with `work scope-add` before touching new paths. Confirmed same-path and ancestor/descendant overlaps block with the current owner identified. `work checkpoint` renews the lease; `work finish|abandon` releases scope while retaining history. Expired clean scope is released, while matching dirty paths or an unavailable worker worktree become an explicit recovery hold; only a new-fence `work resume` or explicit abandon clears ownership. After a confirmed computer/session shutdown, exact-fence `work interrupt` inspects the old workspace and creates the same conservative recovery boundary immediately; it must not interrupt an owner that may still be live. Feature scaffolding first runs a read-only script dry run, then uses one `board feature-bootstrap` call to register the exact `.specify/features/<id>` create intent and receive branch policy before any write. Managed children always remain on their allocated private/current ref. Unhosted `keep-current` avoids branch creation; idle `default` preserves the historical public-branch behavior. The real script replays the dry-run feature id, and an existing feature directory requires explicit resume. The board is a CLI projection and is never edited directly.
- **Enriched task contract generation**: `sp-tasks` produces the minimum executable task contract in light mode and enriched subagent-ready task contracts in standard/heavy mode when downstream delegated implementation needs packets. UI/TUI/CLI/API/runtime-visible work must include User-Observable Path Coverage and packet fields such as `consumer_surfaces` plus `required_evidence: real_entrypoint_evidence` when synthetic-only proof would miss the real entrypoint.
- **Tasks/implement default contract**: `sp-tasks` must run an implementation-readiness self-audit before handoff. Clean completion writes `next_command: /sp.implement`, `gate_status: cleared`, and `highest_invalid_stage: none`; `sp-analyze` remains an optional diagnostic and legacy revalidation route only when explicitly invoked or recorded in existing state. If `analyze` is run, it should finish a complete blocker bundle before choosing the next command. repeated `tasks -> analyze -> tasks` loops are abnormal; only use `analyze` again when explicitly required by legacy or diagnostic state. Missing upstream truth routes directly to `specify`, `plan`, or `deep-research`.
- **Event-triggered implement review**: `sp-implement` validates the task-graph revision at entry and reviews only on drift, parallel joins, write-scope change, validation failure, worker concern, obligation conflict, real-entrypoint gaps, or review-window limits. One task lifecycle record carries result, validation, review verdict, blockers, and recovery. Mandatory protected-CI, remote-system, and human evidence gaps remain structured blocked tasks; `external-evidence-checkpoint` permits only a non-final local commit needed to obtain that evidence and does not accept the task, resolve the tracker, authorize push/CI, or weaken final closeout. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts remain upstream truth.
- **Spec quality gate**: `specify-runtime validate spec` mechanically validates the current `sp-specify -> sp-plan` artifact contract plus tiered quality checks before `sp-plan`. Validation, project cognition, and Agent workflow state ship in the same Go binary. Read `templates/spec-quality-gate.md`.
- **Fixed workflow artifact boundary**: Every generated Classic `sp-*` command, Advanced `spx-*` skill, and worker prompt routes canonical artifact reads through `specify-runtime artifact show --path <project-relative-path> --view summary`; `--view full` is an explicit expansion. Authorized writes use a single-use lease from `artifact prepare` and finish through `artifact submit`. `specify-runtime artifact catalog` publishes the deterministic registry, including the `plan-contract` and `quick-status` scaffold kinds, while `specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> --vars <compact-json>` creates stable boilerplate create-only for contracts, workflow state, design briefs, Plan's generic `research.md`, UI briefs, and Quick/Debug state and returns only the semantic fill targets the agent owns. The Deep Research package, evidence packets, rejection history, and derived projection are specialized runtime-only outputs and are never scaffolded, submitted, or patched through the generic artifact channel. The runtime validates registered workflow roots, safe readiness defaults, and content types and performs atomic replacement; agents never overwrite canonical artifact paths directly. Source and test edits remain normal task-scoped repository writes.
- **Brownfield cognition lifecycle**: Generated projects query `specify-runtime cognition status --format json` and use `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default advisory navigation intake; status and database files are runtime implementation details. The compass packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` and compact `claim_refs`, `coverage_diagnostics`, and `expansion_ref`; these are first evidence routes, not final edit scope. `route_confidence` is valid only within `confidence_scope=route_candidate`; advanced query `claim_signals` and `expand --section claim_evidence` add bounded evidence refs with `source_path` and `span`, but require live verification and cannot prove current repository truth. When explicit concept decisions are needed, use `specify-runtime cognition lexicon --mode catalog` -> Agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan`. The current query contract is `claim_retrieval_contract_version=2` and `candidate_universe_version=2`; carry the latter from lexicon into every explicit query plan. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed. Facet coverage gates selection; similarity and route vocabulary are not repository truth. `specify-runtime cognition semantic-intake` and optional `specify-runtime cognition semantic-audit` remain WorkContract routing and replay surfaces and cannot authorize source changes or final claims. Schema v5 is current-only and adds revision-bound auditable reconciliation through `claim_reconciliations` plus current/superseded `claim_evidence` bases. The current runtime does not migrate schema v4 or older databases. Never move, remove, archive, or replace the store directly; run `specify-runtime cognition archive-incompatible-store --inspect --format json` and execute its hash-guarded `archive_argv` before `sp-map-scan -> sp-map-build`. Optional `provisional/claims.json` uses `graph_claim_type`, evidence references, and compiler-derived lifecycle state. Map points, code proves: even `verified_in_graph_generation` is not current repository truth and cannot set workflow `claim_ready=true`. Workflow-owned mutation closeout is not external map maintenance: source-changing workflows run planner-first project cognition update for their changed paths and affected surfaces; structured update returns `affected_graph_claims` and marks only related claims stale. Only exact claim-specific bounded evidence may then use `specify-runtime cognition claim-reconcile prepare`, followed by the returned `apply_argv` through `specify-runtime cognition claim-reconcile apply`; generic verification cannot re-promote claims. `sp-map-update` remains the external/manual entrypoint. Use `map-scan -> map-build` only for first/missing/unusable baselines and documented rebuild triggers. A first brownfield baseline is complete only after `specify-runtime cognition validate-scan --format json` and `specify-runtime cognition validate-build --format json` pass. Build creates `path_index` only from `nodes[].paths`; coverage rows are accounting, not index sources. Agent commands use only the relative project `runtime_launcher` at `.specify/bin/specify-runtime` (`.exe` on Windows); `SPECIFY_RUNTIME_BIN` and PATH are human bootstrap/repair seeds only. `specify-runtime doctor --format json` diagnoses the binding and returns a human-owned bootstrap boundary when repair is required. Root `.cognitionignore` and `.specify/project-cognition/.cognitionignore` exclude paths from cognition graph evidence, route indexes, and `minimal_live_reads`.
- **Compass recovery contract**: `recommended_next_action` is an object, not a string. Consumers route by `action_id`, never by readiness alone: `needs_rebuild` can accompany a resumable action such as `complete_scan_packets`. Only `action_id=project_cognition.rebuild` carries exact `rebuild_reasons[]` plus canonical profile routes (`spx-map-rebuild` for Advanced, `sp-map-scan -> sp-map-build` for Classic). Non-workflow actions may carry exact `argv`; `project_cognition.repair_status` invokes deterministic `repair-status` only after graph-store invariants validate. Agents must not guess a cause, patch graph metadata, or derive a workflow from legacy runtime status strings.
- **Advanced cognition rebuild cost routing**: `spx-map-scan` owns canonical scan-set preparation, context-budgeted low-cost worker packets, packet acceptance, and scan validation, then stops. `scan-prepare` deducts inherited/instruction/reasoning/tool/result reserves from model capacity; an oversized packet cannot be leased without an explicit sufficient `--worker-capacity-tokens`. Workers checkpoint cumulative completed paths and yield before exhaustion. If a worker stops, the leader recovers its generation-scoped active attempt from `scan-status`, calls `scan-requeue`, and assigns only the exact remaining paths. An identical preparation digest resumes the current workbench. `validate-scan` seals the accepted generation, current source bytes, and canonical artifacts and refreshes dependency-safe path-scope cache bundles keyed by source SHA-256, effective policy, scan contract, and graph schema. Later scans replay hits with fresh generation-bound packet/attempt/receipt identity and dispatch only invalidated scopes; `--full-rebuild` is the explicit cache bypass. `spx-map-build` consumes the frozen scan and performs deterministic graph construction, publication, build validation, and representative Compass proof without a second model-driven repository scan. A matching receipt/compiler/schema fingerprint reuses the ready active generation instead of importing a duplicate, but still requires build validation. `spx-map-rebuild` is only their optional orchestrator. This advanced-profile policy does not change the classic `sp-map-scan -> sp-map-build` prompt contract.
- **Advanced workflow compilation**: The advanced profile is command-equivalent and prompt-optimized. It has no hard word or token ceiling: compression removes repetition, tutorials, and stable boilerplate only after every Classic stage input, triggered output, state owner, resume transition, blocker/recovery rule, side-effect gate, and final-claim gate remains represented. `templates/advanced-skills/_shared/surface-map.json` maps every classic command one-to-one into an independent `spx-*` skill and keeps lifecycle ownership, read/write boundaries, resumable stops, and explicit external side effects separate. Advanced prompts remove repeated cognition tutorials, fixed role chains, mandatory delegation where unnecessary, long examples, and model-authored stable boilerplate; they reuse shared canonical schemas, validators, lifecycle state, deterministic renderers, and project-cognition. Advanced installs do not copy the classic passive prompt bundle. As an explicit cost-routing exception, they also install the original Classic `sp-map-scan`, `sp-map-build`, and `sp-map-update` skills with their command-reference sidecars through the unchanged Classic renderer so lower-cost models can run that contract. `spx-implement-teams` selects the supported Codex or Claude durable-team backend and refuses unsupported integrations; `spx-team` remains Codex-only.
- **Refresh outcomes**: Recorded refresh and ready refresh are different outcomes. `partial_refresh` means update metadata was recorded but shared readiness still failed; follow `recommended_next_action` and keep support drift (`support_drift`) distinct from runtime-truth staleness.
- **Mutation closeout control plane**: Source-changing Classic and Advanced workflows pass an explicit receipt scope plus exact owned paths to `cognition closeout-plan`, fill only Agent-owned evidence, and execute returned `apply_argv`. `cognition closeout apply` owns update, validation, eligible finalization, and receipt; missing passing verification stops before mutation. It separates `scope_result_state` from project-wide freshness, so `scope_ready` may close successful current paths while unrelated global debt remains visible.
- **Claim-aware route ranking**: Compass performs a bounded rerank only after `match_score` establishes repository-backed candidate eligibility. `claim_ranking.adjustment` is capped at `+1` for fresh supported or graph-generation-verified claims, `-1` for stale, and `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. A selected `stale_claim_signal` or `contradicted_claim_signal` keeps the packet `usable_with_review` and returns `reconcile_claims_with_minimal_live_reads` plus a lane-specific live repository action.
- **Semantic cognition handoff**: `specify-runtime cognition semantic-intake` is the WorkContract v1 unified semantic candidate entrypoint; semantic-intake alone cannot authorize source changes or final claims. When escalation influences routing, optional `specify-runtime cognition semantic-audit` creates a v1.1 audit artifact as a replayable WorkContract artifact with the semantic-intake input/output snapshot, selected/rejected basis, permission upgrade/downgrade reason, and action log. The advanced path is `lexicon -> semantic_intake -> query` and requires Agent-authored `semantic_intake` plus explicit `concept_decisions`.
- **Semantic audit resume and claim readiness**: When a workflow resumes from persisted semantic audit state, `specify-runtime cognition semantic-audit-resume --input-json '<resume-validation-json>' --format json` accepts the validation object in memory and is only a comparison helper for the CLI-persisted audit input/output pair and workflow state. Never create a resume-validation file. It does not authorize source changes or final claims, and does not grant P3/P4. Multiple `authorized_claims` require one explicit `active_claim_type`; otherwise claim readiness remains blocked. Failed, blocked, skipped, or inconclusive verification results keep claim readiness blocked with `verification_result_failed`, `verification_result_blocked`, or `verification_result_inconclusive` until a newer matching passed rerun supersedes them.
- **Semantic audit persistence**: `specify-runtime cognition semantic-audit --input-json '<semantic-audit-input-json>' --persist-dir <WORKFLOW_STATE_DIR> --format json` atomically owns `semantic-audit-input.json` and `semantic-audit-output.json`. Agents submit only compact semantic input and may inspect the pair through `artifact show`; generic prepare/submit/patch and direct file writes are not valid for either artifact.
- **Visual comparison ownership**: `specify-runtime evidence visual-compare` accepts compact observed matrix/evidence input and atomically owns `visual-comparison-<Txxx>.json`. Approved preview/manifest/handoff values, exact `DS-*`/`DH-*` coverage, tolerance, deviations, path, and digest come from the CLI-owned task contract rather than agent-authored boilerplate.
- **Planner-first cognition closeout control plane**: Every source-changing `sp-*` workflow calls `specify-runtime cognition closeout-plan --workflow <registry-owned canonical id>` with the exact `--scope-dir`, `--scope-mode explicit`, and one `--changed-path` per workflow-owned path. Renames own both old and new endpoints, and both must remain in `boundary.workflow_owned_paths`. The planner refuses to infer that boundary from the whole repository and returns a structured `apply_argv`; agents fill only its returned `unknown_path_dispositions`, semantic disposition, `verification_evidence`, and `generated_surface_notes` fields in memory, while `update_argv` remains one of the display-only command templates for compatibility/debug only. `update_mode=delta_session` exposes `delta_append_draft.argv_prefix`; `update_mode=inline_json` carries a bounded inline payload. Shared `specify-runtime cognition closeout apply` rejects absent or failed verification evidence before mutation, owns update -> validate-build -> eligible complete-refresh -> bound receipt, and reports `scope_result_state`/`scope_partial_reasons` separately from global outcome/freshness/debt. Clean closeout requires `status=ok`, `readiness=query_ready`, a current bound update ID, and a matching receipt. A `scope_ready` receipt may close the accepted current workflow without erasing unrelated project-wide debt; global `ready`/`no_op` still requires current finalization and receipt binding.
- **Closeout known unknown scope**: Closeout agents should use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If unrelated dirty or untracked working-tree paths were excluded by explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as blocking `known_unknowns`.
- **Delegated execution contracts**: `src/specify_cli/execution/`, `src/specify_cli/hooks/`, and `src/specify_cli/orchestration/` define packet/result schemas, quality hooks, adaptive and mandatory dispatch selection, and state surfaces.
- **Codex team runtime**: `src/specify_cli/codex_team/`, `src/specify_cli/mcp/`, and `extensions/agent-teams/engine/` provide optional Codex team orchestration, state, MCP facade, and bundled engine assets.
- **Testing and verification**: Python pytest layers, integration/template contract tests, Codex-team tests, and engine build checks protect generated behavior.

- **Deterministic cognition proposal publication**: Before SQLite publication, `build-from-scan` adapts the accepted legacy-compatible scan package into a versioned proposal and runs the deterministic cognition proposal compiler. Compiler conflicts block before any graph-store mutation, and compiled graph material remains advisory route candidates rather than repository facts.

## How To Read This Project

- Start here for orientation.
- The runtime atlas now resolves to two workflow handbooks.
- Read `DEBUG-HANDBOOK.md` for `sp-debug` and `BUILD-HANDBOOK.md` for the major non-debug workflows.
- **First stop for any task**: use the project cognition routes described here. Repo-local `.specify/` state is not committed source-of-truth for this repository.
- Treat `specify-runtime cognition status`, the task-local compass packet, and conditional query/expand responses as the advisory project cognition index and advisory navigation inputs. Status and database files are runtime implementation details. Map points, code proves: live repository evidence remains authoritative.
- For generated projects, query readiness with `specify-runtime cognition status --format json` and consume the task-local `specify-runtime cognition compass` packet before broad brownfield work; never read `.specify/project-cognition/status.json` directly.
- Treat project cognition as an advisory navigation index. Code, tests, scripts, configuration, and authoritative docs are the evidence sources.
- Use `.cognitionignore` or `.specify/project-cognition/.cognitionignore` to exclude vendored, generated, archived, or nested-reference projects from project cognition. The rules are gitignore-compatible and affect `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence. `sp-map-scan` runs `specify-runtime cognition generate-ignore --format json` before inventory; when it returns `review_required=true`, review the returned `suggested_patterns`, then activate the approved all/subset through `specify-runtime cognition confirm-ignore` rather than opening runtime storage. A created starter with no suggestions returns `review_required=false` and needs no confirmation. Chat confirmation alone is not an active rule.
- After the ignore gate is clear, scan workflows resolve their temporary agent-facing file list with `specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json`. Default stdout contains only the file-list path and count, and the handoff file contains only `files`; do not replace this with broad ad hoc repository enumeration.
- Project cognition serves code understanding, change, and verification rather than mirroring every readable file at equal depth. After the ignore and `scan-set` gates, `scan-formats` inventories every repository-specific format cohort using detected format/family, path kind, top-level directory, and Git state, returning aggregate counts and at most three representatives. The Agent proposes one complete cohort-level policy, `scan-policy-stage` validates exact coverage, and the user confirms the exact proposal digest before `scan-policy-confirm` activates it. Confirmed decisions remain reusable for content or membership drift inside the same stable cohort; newly observed cohorts require another exact review/confirmation. `scan-prepare` rejects missing, tampered, incomplete, unresolved, or newly uncovered policy state and freezes the current inventory plus confirmed policy into the workbench. Repeated preparation resumes an identical digest or replays validated content/policy/contract-matched path-scope bundles and queues only invalidated scopes. This supports deliberate inclusion of custom code formats without unconfirmed path-level filtering. Ordinary untracked source stays eligible, while untracked `.gitignore` matches, local runtime vendor/data/log payloads, and generated agent/workflow artifacts default to inventory-only `P3`; `--include-gitignored` remains a reviewed pre-policy input. Runtime worker recommendations are capped at four and remain bounded by the platform's available agent slots.
- Empty projects initialized by `specify init` run `specify-runtime cognition init-empty` after pinning the binary. When there is no business code yet, this creates `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` with baseline kind `baseline_kind=greenfield_empty`; greenfield flows do not require map-scan -> map-build solely because the graph has no paths. Projects with existing code still use map-scan -> map-build when a full first brownfield cognition baseline is needed for a first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- When referencing another local directory, run `specify-runtime cognition discover --root <path> --format json`. Use that directory's cognition only when the CLI response reports `reference_readiness=ready`, `freshness=fresh`, and `graph_ready=true`; otherwise fall back to minimal live reads. Do not probe its status/database files. Do not treat legacy `.specify/project-map/**` outputs as current truth.
- Supporting project-map outputs are support-only or reference-only compatibility/export surfaces.
- The refresh workbench still contains `map-scan` / `map-build` scan packets and refresh workbench artifacts for rebuilding the handbooks.
- `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths`; `coverage.json` is coverage accounting, not a path-index source.
- Legacy project-map artifacts may still exist in old projects, but there is no Python runtime alias and new workflows should not call or require `.specify/project-map/**`.
- Fall back to live code reads only when cognition coverage is missing, stale, too broad, or marked low confidence.
- If changed paths are missing from project cognition `path_index`, let `sp-map-update` classify the gap first when the user requested map maintenance or a separate map-maintenance pass is required. Source-changing `sp-*` workflows run planner-first project cognition update for their own changed paths and affected surfaces during closeout. Uncertain closure is recorded by planner-first closeout or `map-update` as partial/low-confidence facts when needed. Adoptable paths get provisional coverage, uncertain paths return `minimal_live_reads`, and ordinary existing-baseline gaps remain external/manual `sp-map-update` work.
- `sp-debug` should use `specify-runtime cognition compass --intent debug --query "$ARGUMENTS" --format json` as its default intake. `specify-runtime cognition query --query-plan` remains available for advanced precision escalation when compass coverage is missing, ambiguous, stale, or contradicted by evidence, and the deeper Stage 1A/1B observer-contract flow remains available for the same evidence conflicts.
- The advanced CLI tool's `agent_normalization` field is agent semantic guidance, not a route decision; it is a CLI tool reminder to normalize project vocabulary rather than an autonomous routing authority.
- Use `map-update` for ordinary existing-baseline gaps and operator-requested localized maintenance; blocked references continue from live evidence. Use map-scan -> map-build only for brownfield first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself. A `ready` or `no_op` update must be followed by `specify-runtime cognition validate-build`; only `status=ok` with `readiness=query_ready` creates the receipt bound to the latest update ID, outcome, and active generation, after which `specify-runtime cognition complete-refresh` may finalize freshness. Until then, the runtime gate withholds Compass/query as `update_finalization_pending`. `specify-runtime cognition record-refresh` is compatibility-only when that matching receipt already exists; it is not a bypass. Preserve `partial_refresh`, `needs_rebuild`, `blocked`, and `recorded` without finalization.
- Preserve the state vocabulary: `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, and `possibly_stale` are machine freshness states; `recommended_next_action` is the public operator guidance.

## Project Cognition Routes

For generated projects, use project cognition first:

- `specify-runtime cognition status --format json` — runtime-owned freshness, coverage, stale paths, and synchronization metadata; do not read its storage file directly
- `specify-runtime cognition compass|query|expand` — canonical graph-store access; do not read or write the database directly
- `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` — default brownfield navigation intake returning readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` and compact `claim_refs`, `coverage_diagnostics`, and `expansion_ref`; `route_confidence` is scoped by `confidence_scope=route_candidate`, advanced query `claim_signals` and `expand --section claim_evidence` expose bounded `source_path`/`span` refs, and every graph claim still requires live verification because it cannot prove current repository truth
- `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan` (`lexicon -> semantic_intake -> query`) — advanced path when compass is draft-like, localized, missing coverage, or needs explicit concept decisions
- Precision `query` is an exact binding consumer, never a natural-language search endpoint. Page `lexicon --mode catalog` through `catalog_page.next_offset`, copy current `concept_id` values or exact paths into the plan, carry the same `lexicon_generation_id`, and require `resolution_state=resolved_exact`; treat binding failures as explicit recovery states rather than null results.
- `specify-runtime cognition changes --format json` - Git-native change plan for `sp-map-update`; reports `summary.included`, `summary.ignored`, `summary.known`, `summary.unknown`, `ignored_paths`, `unknown_paths`, top-level `next_action`, and per-change `recommended_action` before incremental update recording
- The advanced alias catalog path carries facet coverage details: `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `candidate_universe_version`, and `active_generation_id`.
- Pass query plans as one structured argv value with `specify-runtime cognition query --query-plan '<inline-json>'`; use the integration's native argument API when shell quoting is brittle, and never create a query-plan file. The query plan accepts `path_hints`/`reason` as aliases for `paths`/`selection_reason`.

The cognition model should help answer:

- which workflow-specific cognition slice owns the current task
- which graph-backed concept candidates, alias interpretations, paths, and affected surfaces must be read before source work begins
- which propagation risks and verification routes matter before changing code
- what remains unknown and therefore needs live repository confirmation
- whether the factual freshness state is runtime staleness, support drift, or a partial refresh that still blocks readiness

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. `sp-map-build` and the project cognition runtime provide the evidence layer, but the Senior Consequence Analysis Gate turns those facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, `implement`, and `quick`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass. `fast` upgrades when the gate triggers; `quick` tracks consequences and acceptance locally instead of handing off solely because the task is large or consequence-heavy; `debug` traces the dependency loop and rejects surface-only fixes.

`fast` keeps the bounded direct-delivery skeleton without Quick's durable
workspace or worker lanes: consume-only Learning runs before Project Cognition,
the leader performs all edits directly, targeted verification proves the local
change, and the same leader performs one Lightweight Review. It creates no
worker packet or review subagent and does not claim the independent system
Review contract.

## Shared Surfaces

- `src/specify_cli/__init__.py`: top-level Typer app, command registration, init flow, project-map/hook/learning/testing/eval/team helper commands.
- `src/specify_cli/agent_api.py`, `src/specify_cli/command_catalog.py`, and `src/specify_cli/workflow_runtime.py`: compact Agent API negotiation, live progressive CLI discovery, mandatory stage/revision gates, and structured blocker recovery.
- `src/specify_cli/launcher.py`: persisted project launcher binding, generated-project compatibility diagnostics, and runtime launcher helpers.
- `tools/specify-runtime/internal/runcontrol/` and `tools/specify-runtime/run.go`: shared Run authority, automatic primary-or-isolated workspace allocation, pre-launch Snapshots, forced-cwd supervision, fencing/recovery, immutable Result sealing, multi-Result Candidate review, human acceptance receipts, CAS publication, and guarded primary-workspace synchronization.
- `src/specify_cli/integrations/base.py` and `src/specify_cli/integrations/__init__.py`: integration registry, shared generation bases, template processing, passive skill installation, manifest behavior.
- `templates/`: command templates, command partials, opt-in `advanced-skills`, passive skills, project-map/testing templates, worker prompts, constitution/spec/plan/tasks artifacts.
- `scripts/bash/` and `scripts/powershell/`: generated helper layer and freshness/context-update scripts.
- `src/specify_cli/execution/`, `src/specify_cli/hooks/`, `src/specify_cli/orchestration/`: packet/result schemas, workflow hooks, adaptive plan/tasks dispatch plus mandatory-subagent dispatch/state/review helpers.
- `src/specify_cli/codex_team/` and `extensions/agent-teams/engine/`: optional Codex team runtime and bundled engine.
- `tools/specify-runtime/`: unified Go Agent runtime, spec quality gate, project cognition engine, install scripts, and CI cross-compilation workflow.

## Risky Coordination Points

- Editing `src/specify_cli/__init__.py` can change CLI help, routing, init behavior, hook surfaces, and tests across many areas.
- Editing `templates/commands/`, `templates/command-partials/`, `templates/advanced-skills/`, or `templates/passive-skills/` changes generated downstream behavior for multiple agents. Advanced skills are installed only by the `advanced` workflow profile; classic command and passive skill output must remain unchanged.
- Advanced-profile references must originate under `templates/advanced-skills/`; never import, include, or copy classic `templates/command-references/` into an `spx-*` installation. Add a dedicated advanced reference only for a stable runtime, artifact, or lower-tier worker contract that does not belong in the short leader prompt.
- Editing `src/specify_cli/integrations/base.py` affects most generated integrations.
- Editing `tools/specify-runtime/`, `src/specify_cli/specify_runtime.py`, or freshness scripts affects brownfield workflow gating.
- Editing Codex team installer/runtime files can affect `.codex/config.toml`, `.specify/teams/*`, worker state, MCP behavior, and engine packaging.

## Change-Propagation Hotspots

- Agent registration metadata propagates into CLI help, integration generation tests, README guidance, generated file paths, and tool checks.
- Generated runtime compatibility rules propagate into `specify check`, integration install/switch/repair flows, generated `.specify/config.json`, generated hook/settings assets, and generated shared scripts.
- Template wording propagates into every generated agent surface and template assertion tests.
- Run authority, managed-workspace environment bindings, Candidate/Result semantics, and target integration locks propagate into runtime capabilities, workflow feature resolution, launcher diagnostics, generated documentation, and cross-integration tests.
- Adaptive and mandatory dispatch vocabulary propagates into orchestration tests, generated workflow tests, integration tests, README/quickstart guidance, context scripts, and project-map docs.
- Workflow-handbook guidance now propagates from `templates/project-handbook-template.md`, workflow command templates, packet context helpers, and handbook-validation rules into initialized projects, map refresh helpers, and tests.
- Packet/result schema changes propagate into execution helpers, hooks, Codex team runtime, generated workflow prompts, and contract tests.
- Project cognition freshness changes propagate into the Go runtime, Python external-tool bridge, Bash/PowerShell scripts, hook commands, and brownfield gates.
- Engine packaging changes propagate through `pyproject.toml` force-includes, `extensions/agent-teams/engine/`, Codex team installer/runtime tests, and release artifacts.

## Change Impact Guide

- Change CLI command wiring or init behavior: read `root/ARCHITECTURE.md`, `root/WORKFLOWS.md`, and `modules/specify-cli-core/OVERVIEW.md`.
- Change an integration adapter: read `root/INTEGRATIONS.md`, `root/CONVENTIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.
- Change workflow templates or passive skills: read `root/WORKFLOWS.md`, `modules/templates-generated-surfaces/WORKFLOWS.md`, and template tests. For `sp-prd-scan -> sp-prd-build`, preserve the heavy reconstruction contract: repository-first current-state PRD extraction, subagent-mandatory substantive scans, `L4 Reconstruction-Ready` critical claims, `config-contracts.json` in the contract surface, `sp-prd-build` as scan-package compilation rather than a second repository scan, `sp-prd` compatibility-only routing, and no automatic planning handoff.
- Change hooks, packets, orchestration, or Codex team runtime: read `root/ARCHITECTURE.md`, `root/OPERATIONS.md`, and relevant module docs.
- Change packaging, CI, devcontainer, extension, or preset surfaces: read `root/STRUCTURE.md`, `root/INTEGRATIONS.md`, and `root/OPERATIONS.md`.
- Change launcher binding, generated runtime compatibility, or generated-project repair flows: read `root/OPERATIONS.md`, `root/INTEGRATIONS.md`, and `modules/specify-cli-core/ARCHITECTURE.md`.

## Verification Entry Points

- Focused runtime regression: `cd tools/specify-runtime && go test ./... && cd ../.. && pytest tests/test_specify_runtime.py tests/test_project_cognition_runtime_install.py tests/test_project_map_freshness_scripts.py tests/contract/test_hook_cli_surface.py -q`
- Full Python regression: `uv run --extra test pytest -q -n auto`
- Integration surface: `pytest tests/integrations -q`
- Hooks/execution/orchestration: `pytest tests/hooks tests/execution tests/orchestration -q`
- Codex team runtime: `pytest tests/codex_team tests/contract/test_codex_team_cli_surface.py tests/test_teams_mcp_server.py -q`
- Unified runtime: `cd tools/specify-runtime && go test ./... && go vet ./... && go build -o /dev/null .`
- Packaging sanity: `uv build`
- Bundled engine sanity: `npm --prefix extensions/agent-teams/engine run build`

## Known Unknowns

- External agent CLIs can change behavior outside this repository; adapter claims should be verified against upstream docs when external surfaces change.
- The Rust crates under `extensions/agent-teams/engine/crates/` were sampled for this atlas; run a targeted Rust packet before changing Rust runtime semantics.
- The global `specify` executable on a developer machine may lag this checkout. Prefer `PYTHONPATH=src; python -m specify_cli ...` or an editable install when validating local source behavior.

## Low-Confidence Areas

- `agent-teams-engine` Rust internals: Inferred from manifests, representative source, and tests rather than exhaustive source tracing.
- Release packaging beyond GitHub release creation: sampled from workflow files and `pyproject.toml`, but publishing details should be rechecked before changing distribution automation.
- Historical `.planning/**` artifacts are useful context but not always current product truth; `.planning/STATE.md` is the current planning status source.

## Atlas Views

- `templates/project-map/index/atlas-index.json`: machine-readable atlas summary and next-read routes for generated projects.
- `templates/project-map/index/modules.json`: module registry, owned roots, and module doc paths for generated projects.
- `templates/project-map/index/relations.json`: cross-module dependencies and shared-surface expansion routes for generated projects.
- Generated-project `specify-runtime cognition status` response plus the task-local `specify-runtime cognition compass` packet: freshness, module coverage, stale paths, and refresh metadata.
- `root/ARCHITECTURE.md`: cross-module architecture, contracts, dependency graph, capability cards.
- `root/STRUCTURE.md`: directory ownership, critical file families, placement rules.
- `root/CONVENTIONS.md`: naming, generated-surface, state, compatibility, and review conventions.
- `root/INTEGRATIONS.md`: supported agent adapters, external tool boundaries, MCP/runtime seams, security boundaries.
- `root/WORKFLOWS.md`: user and maintainer flows, state transitions, map/test/implement/debug behavior.
- `root/TESTING.md`: test layers, verification matrix, command selection.
- `root/OPERATIONS.md`: build, install, freshness, runtime state, recovery, troubleshooting.

## Where To Read Next

- Add or change workflow behavior: `root/WORKFLOWS.md`, then `modules/templates-generated-surfaces/WORKFLOWS.md`.
- Add or change an agent integration: `root/INTEGRATIONS.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change CLI internals: `modules/specify-cli-core/OVERVIEW.md`, then `modules/specify-cli-core/ARCHITECTURE.md`.
- Change Codex team runtime or bundled engine: `modules/agent-teams-engine/OVERVIEW.md`, then `root/OPERATIONS.md`.
- Diagnose test failures: `root/TESTING.md`, then the module `TESTING.md` for the affected area.
- Change design governance quality (taste, ready lint, diagnostics, golden artifacts): **Design Governance Foundation v1.0** in this handbook first, then `tests/fixtures/design-preview/README.md` and the rule admission checklist. Change design ownership, lifecycle, or consumer binding: **Foundation v2.0** and ADR-0001 first.

## Topic Map

- `specify-runtime cognition status --format json` - default generated-project runtime-owned status, freshness, coverage, stale paths, and synchronization metadata
- `specify-runtime cognition compass|query|expand` - canonical graph-store access without direct database reads
- `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` bundle - default generated-project route to readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; agents use those paths as first evidence, not final edit scope
- `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan` (`lexicon -> semantic_intake -> query`) - advanced route when compass needs explicit concept decisions or coverage escalation
- `specify-runtime cognition changes --format json` - Git-native change plan for `sp-map-update`; reports `summary.included`, `summary.ignored`, `summary.known`, `summary.unknown`, `ignored_paths`, `unknown_paths`, top-level `next_action`, and per-change `recommended_action` before incremental update recording
- `DEBUG-HANDBOOK.md` - compatibility/export debug view
- `BUILD-HANDBOOK.md` - compatibility/export build/change view
- `templates/project-map/**` is retained only for legacy compatibility review and must not be installed or required by new generated projects.

## Update Triggers

- CLI command registration, generated workflow names, integration directories, packet/result schemas, hook events, testing workflow state, project-map compatibility/export rules, extension/preset schemas, packaging force-includes, or Codex team runtime installation assumptions change.

## Recent Structural Changes

- `sp-test-design` is the Classic independent Test Design producer and `spx-test-design` is its Advanced peer; neither requires a completed Plan.
- The runtime atlas is being rewritten around `specify-runtime cognition status`, default `specify-runtime cognition compass` navigation packets, conditional `query`/`expand` responses, and advanced agent-planned `specify-runtime cognition lexicon --mode catalog` -> `semantic_intake` -> `specify-runtime cognition query --query-plan` task-local bundles.
- Ordinary `sp-*` workflows should treat project cognition consumption as advisory navigation before source-level work.
- Supporting handbook artifacts remain available as compatibility/export surfaces, but are no longer the primary evidence path.
