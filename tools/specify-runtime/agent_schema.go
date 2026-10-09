package main

import (
	"fmt"
	"io"
	"strings"
)

func runAPISchema(args []string, stdout io.Writer) int {
	schemaID, env, ok := apiObjectID(args, "schema")
	if !ok {
		return writeEnvelope(stdout, env)
	}
	var schema map[string]any
	var capabilityID string
	switch schemaID {
	case "do-start-input":
		schema = doStartInputSchema()
		capabilityID = "do.start"
	case "do-record-input":
		schema = doRecordInputSchema()
		capabilityID = "do.record"
	case "do-finish-input":
		schema = doFinishInputSchema()
		capabilityID = "do.finish"
	case "do-resume-input":
		schema = doResumeInputSchema()
		capabilityID = "do.resume"
	case "playbook-definition-input":
		schema = playbookDefinitionInputSchema()
		capabilityID = "playbook.update"
	case "playbook-update-input":
		schema = playbookUpdateInputSchema()
		capabilityID = "playbook.update"
	case "playbook-find-input":
		schema = playbookFindInputSchema()
		capabilityID = "playbook.find"
	case "playbook-show-input":
		schema = playbookShowInputSchema()
		capabilityID = "playbook.show"
	case "playbook-validate-input":
		schema = playbookValidateInputSchema()
		capabilityID = "playbook.validate"
	case "workflow-block-input":
		schema = workflowBlockInputSchema()
		capabilityID = "workflow.block"
	case "workflow-reconcile-blocker-input":
		schema = workflowReconcileBlockerInputSchema()
		capabilityID = "workflow.reconcile-blocker"
	case "source-continuity-adapter-plan-input":
		schema = sourceContinuityAdapterPlanInputSchema()
		capabilityID = "evidence.source-continuity-adapter-plan"
	case "source-continuity-adapter-probe-input":
		schema = sourceContinuityAdapterProbeInputJSONSchema()
		capabilityID = "evidence.source-continuity-adapter-probe"
	case "source-continuity-tool-inventory-input":
		schema = sourceContinuityToolInventoryInputJSONSchema()
		capabilityID = "evidence.source-continuity-adapter-bridge"
	case "artifact-show-many-input":
		schema = artifactShowManyInputSchema()
		capabilityID = "artifact.show-many"
	case "artifact-patch-batch-input":
		schema = artifactPatchBatchInputSchema()
		capabilityID = "artifact.patch-batch"
	case "artifact-scaffold-input":
		schema = artifactScaffoldInputSchema()
		capabilityID = "artifact.scaffold"
	case "artifact-checklist-input":
		schema = artifactChecklistInputSchema()
		capabilityID = "artifact.checklist"
	case "artifact-patch-input":
		schema = artifactPatchInputSchema()
		capabilityID = "artifact.patch"
	case "discussion-checkpoint-input":
		schema = discussionCheckpointInputSchema()
		capabilityID = "discussion.checkpoint"
	case "discussion-import-material-input":
		schema = discussionImportMaterialInputSchema()
		capabilityID = "discussion.import-material"
	case "discussion-write-handoff-input":
		schema = discussionWriteHandoffInputSchema()
		capabilityID = "discussion.write-handoff"
	case "implement-result-merge-input":
		schema = implementResultMergeInputSchema()
		capabilityID = "implement.result-merge"
	case "tasks-rebind-updates-input":
		schema = tasksRebindUpdatesInputSchema()
		capabilityID = "tasks.rebind"
	case "deep-research-track-prepare-input":
		schema = deepResearchTrackPrepareInputSchema()
		capabilityID = "deep-research.track-prepare"
	case "deep-research-track-submit-result":
		schema = deepResearchTrackSubmitResultSchema()
		capabilityID = "deep-research.track-submit"
	case "deep-research-synthesis-input":
		schema = deepResearchSynthesisInputSchema()
		capabilityID = "deep-research.synthesize"
	case "deep-research-audit-input":
		schema = deepResearchAuditInputSchema()
		capabilityID = "deep-research.audit-accept"
	case "deep-research-not-needed-input":
		schema = deepResearchNotNeededInputSchema()
		capabilityID = "deep-research.not-needed"
	default:
		schema, capabilityID, ok = e2ePayloadSchema(schemaID)
		if !ok {
			return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown schema %q", schemaID)))
		}
	}
	env = NewEnvelope("ok", fmt.Sprintf("Schema %s expanded.", schemaID))
	env.Data["schema_id"] = schemaID
	env.Data["schema_version"] = 1
	env.Data["schema"] = schema
	env.ShowArgv = []string{"specify-runtime", "api", "show", capabilityID, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runAPIShow(args []string, stdout io.Writer) int {
	capabilityID, env, ok := apiObjectID(args, "capability")
	if !ok {
		return writeEnvelope(stdout, env)
	}
	if !containsCapability(defaultCapabilities(), capabilityID) {
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown capability %q", capabilityID)))
	}
	parts := strings.Split(capabilityID, ".")
	command := append([]string{"specify-runtime"}, parts...)
	capability := map[string]any{
		"id":             capabilityID,
		"summary":        capabilitySummary(capabilityID),
		"command":        command,
		"usage":          strings.Join(command, " ") + " --help",
		"side_effect":    "may-write",
		"input_contract": "inspect the command-specific help before invoking; pass only documented arguments and request the JSON envelope when supported",
	}
	bindAssetCapability(capabilityID, capability)
	env = NewEnvelope("ok", fmt.Sprintf("Capability %s expanded.", capabilityID))
	applyOperationAPIContract(capabilityID, capability, &env)
	switch capabilityID {
	case "learning.capture-auto":
		capability["side_effect"] = "writes-project-learning-for-new-signals"
		capability["usage"] = "specify-runtime learning capture-auto --command <workflow> [--feature-dir <path>|--workspace <path>|--session-file <path>|--session-id <do-id>] [--dry-run] [--project-root <path>] --format json"
		capability["input_contract"] = "sp-do requires an exact --session-id. Only currently verified recovery can generate an automatic Do lesson; ordinary success is no-op. Before writing Do-linked lessons, finish execution with knowledge pending; Learning claims its exact metadata files on that Work. Snapshot replay is idempotent and promotion remains explicit."
	case "api.ensure":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime api ensure (--capabilities <csv> | --requires-json <object|@path|->) [--project-root <path>] --format json"
		capability["input_contract"] = "accept exactly one capability selector: a compact CSV list or a JSON object with capabilities[]. Returns present and missing ids, capability_set_sha256, and compact runtime identity; duplicate or empty ids are rejected"
	case "api.pack":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime api pack (--capabilities <csv> | --requires-json <object|@path|->) [--include-schema] [--project-root <path>] --format json"
		capability["input_contract"] = "accepts exactly one bounded unique capability selector and returns compact usage, side_effect, input_contract, and schema_ref or embedded schema per selected capability; oversized or unknown requests are rejected"
	case "workflow.block":
		capability["summary"] = "Record a resumable blocker and novice human action guide."
		capability["input_schema"] = "workflow-block-input"
		capability["side_effect"] = "writes-workflow"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "workflow-block-input", "--format", "json"}
	case "workflow.ensure":
		capability["side_effect"] = "shows-or-creates-workflow"
		capability["usage"] = "specify-runtime workflow ensure --feature-dir <feature-dir> [--command <discussion|specify>] [--summary <text>] --format json"
		capability["input_contract"] = "returns the current typed workflow state when it already exists; otherwise creates the initial state idempotently without advancing an existing revision"
	case "workflow.resolve":
		capability["side_effect"] = "writes-workflow"
		capability["usage"] = "specify-runtime workflow resolve --feature-dir <feature-dir> --expected-revision <revision> --resolution-evidence <sanitized-evidence> [--resolution-evidence <sanitized-evidence> ...] [--summary <text>] [--reopen-to <specify|plan|tasks|implement|review> --reopen-reason <reason> --reopen-evidence <sanitized-evidence> [--reopen-evidence <sanitized-evidence> ...] --invalidated-artifacts <artifact> [--invalidated-artifacts <artifact> ...]] --format json"
		capability["input_contract"] = "resolution evidence is always required; reopen-to, reopen-reason, reopen-evidence, and invalidated-artifacts are all-or-none and may name only a strict earlier stage permitted by normal reopen ownership; on success the runtime atomically preserves the blocker audit, records its resolution, and reopens that stage"
	case "workflow.reconcile-blocker":
		capability["input_schema"] = "workflow-reconcile-blocker-input"
		capability["side_effect"] = "reconciles-persisted-workflow-blocker"
		capability["usage"] = "specify-runtime workflow reconcile-blocker --input-json <object|@path|-> [--feature-dir <feature-dir>] --format json"
		capability["input_contract"] = "requires a current blocked revision, one or more evidence-backed resolved_subcauses, and a complete remaining cause/evidence/scope/recovery contract. It keeps the same owner/category and blocked status, appends reconciliation audit, removes stale text from the current blocker, and returns workflow.resolve when no blocker remains"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "workflow-reconcile-blocker-input", "--format", "json"}
	case "tasks.rebind":
		capability["input_schema"] = "tasks-rebind-updates-input"
		capability["side_effect"] = "rebinds-task-package"
		capability["usage"] = tasksRebindUsage
		capability["input_contract"] = "requires the current version-2 task-index SHA-256, workflow revision (0 only when workflow.json is absent), verified current Test Design handoff SHA-256, and a non-empty reason; a present workflow must be in tasks or implement. Optional task-updates-json accepts inline JSON, project-contained @path, or stdin and is keyed by existing pending/ready task IDs with only test_case_refs, test_data_refs, and non-empty ui_contract. The runtime validates all-and-only case/data coverage, refreshes pending UI against the exact adopted Plan/registered Design, preserves accepted/deferred task, lifecycle, and result bytes, refuses unresolved started work, and atomically refreshes task projections, downstream handoffs, pending packets, and an immutable audit under compare-and-swap guards. Missing or stale upstream truth must be repaired by its producer; rebind never grants approval or weakens readiness."
		capability["output_contract"] = tasksRebindOutputContract
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "tasks-rebind-updates-input", "--format", "json"}
	case "deep-research.init":
		capability["side_effect"] = "creates-deep-research-workspace"
		capability["usage"] = "specify-runtime deep-research init --feature-dir <feature-dir> --leader-id <leader-id> --mode <repo-only|external-enabled|external-blocked> [--expected-revision <revision>] --format json"
		capability["input_contract"] = "requires an unchanged planning-ready spec with feasibility_gate.required; when workflow.json exists it must be specify/completed. Draft, active or blocked Specify, invalid workflow, and non-enterable stages fail closed to the typed Specify owner action before research state is created; the commit holds the workflow lock and pins source-spec/workflow bytes as transaction preconditions"
	case "deep-research.status":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime deep-research status --feature-dir <feature-dir> --format json"
		capability["input_contract"] = "returns lifecycle phase, revision, track counts, source freshness, and next action; a source that is no longer planning-ready or whose Specify workflow is blocked returns the typed Specify owner and resolution action without advertising Plan"
	case "deep-research.validate":
		capability["side_effect"] = "validates-deep-research-package"
		capability["usage"] = "specify-runtime deep-research validate --feature-dir <feature-dir> --expected-revision <revision> --format json"
		capability["input_contract"] = "requires accepted independent audit, canonical package closure, unchanged planning-ready source, and a Plan-enterable workflow; a blocked Specify source preserves the research revision and returns to its owner, while the source-bound commit uses the workflow lock plus exact spec/workflow preconditions"
	case "deep-research.publish":
		capability["side_effect"] = "publishes-deep-research-plan-handoff"
		capability["usage"] = "specify-runtime deep-research publish --feature-dir <feature-dir> --expected-revision <revision> --format json"
		capability["input_contract"] = "publishes /sp.plan only from validated research whose source remains planning-ready and whose workflow can enter Plan; blocked or non-enterable Specify truth returns the exact owner recovery without replacing the source blocker, and concurrent upstream drift rolls back through the workflow lock plus exact spec/workflow transaction preconditions"
	case "deep-research.verify-handoff":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime deep-research verify-handoff --feature-dir <feature-dir> [--handoff-ref <ref>] [--expected-sha256 <sha256>] --format json"
		capability["input_contract"] = "revalidates the published handoff, every artifact digest, the unchanged planning-ready source, and its workflow; blocked Specify or any non-enterable workflow state invalidates /sp.plan and returns the source owner route"
	case "deep-research.track-prepare":
		capability["input_schema"] = "deep-research-track-prepare-input"
		capability["side_effect"] = "writes-deep-research-tracks"
		capability["usage"] = "specify-runtime deep-research track-prepare --feature-dir <feature-dir> --expected-revision <revision> --input-json <object|@path|-> --format json"
		capability["input_contract"] = "freezes one or more bounded tracks with exact capability coverage, read paths, questions, source classes, spike requirement, and completion signal; --input-json accepts inline, project-contained @path, or stdin"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "deep-research-track-prepare-input", "--format", "json"}
	case "deep-research.track-submit":
		capability["input_schema"] = "deep-research-track-submit-result"
		capability["side_effect"] = "writes-deep-research-result-and-evidence"
		capability["usage"] = "specify-runtime deep-research track-submit --feature-dir <feature-dir> --expected-revision <revision> --track-id <TRK-ID> --attempt-id <ATTEMPT-ID> --result-json <object|@path|-> --format json"
		capability["input_contract"] = "the result payload is a complete or blocked track result; complete results bind findings, evidence quality, paths read, spikes, constraints, risks, and contradictions, while blocked results carry non-empty blockers; --result-json accepts inline, project-contained @path, or stdin"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "deep-research-track-submit-result", "--format", "json"}
	case "deep-research.synthesize":
		capability["input_schema"] = "deep-research-synthesis-input"
		capability["side_effect"] = "writes-deep-research-synthesis"
		capability["usage"] = "specify-runtime deep-research synthesize --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --input-json <object|@path|-> --format json"
		capability["input_contract"] = "closes every selected capability, planning handoff, evidence disposition, accepted spike, and contradiction before recommending /sp.plan; --input-json accepts inline, project-contained @path, or stdin"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "deep-research-synthesis-input", "--format", "json"}
	case "deep-research.audit-accept":
		capability["input_schema"] = "deep-research-audit-input"
		capability["side_effect"] = "writes-deep-research-audit"
		capability["usage"] = "specify-runtime deep-research audit-accept --feature-dir <feature-dir> --expected-revision <revision> --auditor-id <auditor-id> --input-json <object|@path|-> --format json"
		capability["input_contract"] = "binds the prepared audit request digest, accepted or rejected verdict, all required audit checks, and optional typed findings; --input-json accepts inline, project-contained @path, or stdin"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "deep-research-audit-input", "--format", "json"}
	case "deep-research.not-needed":
		capability["input_schema"] = "deep-research-not-needed-input"
		capability["side_effect"] = "publishes-deep-research-not-needed-handoff"
		capability["usage"] = "specify-runtime deep-research not-needed --feature-dir <feature-dir> --leader-id <leader-id> --input-json <object|@path|-> --format json"
		capability["input_contract"] = "requires one evidence-backed not-needed disposition for every selected feasibility capability and refuses publication unless the source specification and workflow can enter Plan; publication holds the workflow lock and pins exact spec/workflow bytes; --input-json accepts inline, project-contained @path, or stdin"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "deep-research-not-needed-input", "--format", "json"}
	case "test-design.status":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime test-design status [--feature-dir <feature-dir>] --format json"
		capability["input_contract"] = "returns phase, revision, blockers, freshness, and next action; blocked or stale agent-owned state includes recovery_action and an executable exact base_argv, while genuine human_action_required state preserves the same post-evidence action without an executable next_argv"
	case "test-design.recover":
		capability["side_effect"] = "writes-test-design"
		capability["usage"] = "specify-runtime test-design recover [--feature-dir <feature-dir>] --mode <audit|incremental-update> --expected-revision <revision> --format json"
		capability["input_contract"] = "reads the existing runtime-owned frozen boundary and leader identity, then CAS-reenters the same root without inline input-json; audit preserves the boundary and incremental-update refreshes its fingerprint"
	case "test-design.handoff":
		capability["side_effect"] = "writes-test-design"
		capability["usage"] = "specify-runtime test-design handoff --feature-dir <feature-dir> --expected-revision <revision> --format json"
		capability["input_contract"] = "writes the Tasks compatibility pointer and returns publish in next_argv; publication and projection verification must complete before Tasks is returned"
	case "test-design.projection-build":
		capability["side_effect"] = "writes-test-design-projection"
		capability["usage"] = "specify-runtime test-design projection-build [--feature-dir <feature-dir>] --consumer <plan|quick|tasks|review> --basis-ref <project-relative-ref> [--obligation-ids <csv>] --format json"
		capability["input_contract"] = "builds a pointer-only consumer projection and returns its exact projection-verify next_argv; the producer never asks an agent or user to reconstruct verification flags"
	case "test-design.projection-verify":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime test-design projection-verify [--feature-dir <feature-dir>] --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json"
		capability["input_contract"] = "fails closed on source, publication, basis, selection, or digest drift; success returns the selected consumer in next_argv so the orchestrator resumes the original path"
	case "artifact.scaffold":
		capability["input_schema"] = "artifact-scaffold-input"
		capability["side_effect"] = "creates-artifact"
		capability["usage"] = "specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> --vars <json> --format json"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-scaffold-input", "--format", "json"}
		env.NextArgv = []string{"specify-runtime", "artifact", "catalog", "--format", "json"}
	case "artifact.checklist":
		capability["input_schema"] = "artifact-checklist-input"
		capability["side_effect"] = "creates-or-appends-artifact"
		capability["usage"] = "specify-runtime artifact checklist --path <feature-dir>/checklists/<name>.md --input-json <object|@path|-> --format json"
		capability["input_contract"] = "--input-json accepts inline JSON, @path, or - (stdin). Schema: title, purpose, feature, categories[{heading,items[]}]."
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-checklist-input", "--format", "json"}
	case "artifact.patch":
		capability["input_schema"] = "artifact-patch-input"
		capability["side_effect"] = "patches-artifact"
		capability["usage"] = "specify-runtime artifact patch --lease <id> (--json-pointer <pointer> --value-json <json|@path|-> [--value-json-pointer <source-pointer>] | --frontmatter-pointer <pointer> --value-json <json|@path|-> [--value-json-pointer <source-pointer>] | --section <heading> --content <text|@path|-> | --frontmatter-json <object|@path|-> | --heading <current> --new-heading <replacement> | --preamble <text|@path|-> | --append-json <json|@path|->)"
		capability["input_contract"] = "--section accepts bare heading text or markdown markers (\"Source Design Change\" or \"## Source Design Change\"); --frontmatter-pointer replaces an existing nested YAML mapping field and --value-json-pointer selects a subtree from the JSON input; large or Windows-sensitive payloads may be passed as @project-relative-path or - for stdin, with project-root containment and symlink/reparse rejection; prefix literal text beginning with @ as @@"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-patch-input", "--format", "json"}
	case "artifact.patch-batch":
		capability["input_schema"] = "artifact-patch-batch-input"
		capability["side_effect"] = "patches-artifact"
		capability["usage"] = "specify-runtime artifact patch-batch --lease <id> --input-json <object|@path|-> [--project-root <path>] --format json"
		capability["input_contract"] = "input-json must be an object with operations[]. Each operation is exactly one of {json_pointer,value}, {section,content}, or {frontmatter}. One lease covers 1..32 operations and writes only when the entire batch validates without target conflicts. For large or Windows payloads, stream UTF-8 JSON from memory through --input-json - rather than putting the payload in argv or creating an authoring file; the complete input remains limited to 256 KiB."
		capability["max_input_bytes"] = maxArtifactBatchInputBytes
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-patch-batch-input", "--format", "json"}
	case "artifact.submit":
		capability["side_effect"] = "writes-artifact"
		capability["usage"] = "specify-runtime artifact submit --lease <id> --content <inline-payload|@path|-> --format json"
		capability["input_contract"] = "large or Windows-sensitive content may use a project-contained @path or - for stdin; prefix literal text beginning with @ as @@"
		capability["file_input"] = "--content @path accepts only project-contained regular files; --recovery-file remains reserved for the runtime-created human acceptance repair backup bound by its sibling journal"
	case "artifact.show-many":
		capability["input_schema"] = "artifact-show-many-input"
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime artifact show-many --input-json <object|@path|-> [--project-root <path>] --format json"
		capability["input_contract"] = "input-json must be an object with queries[] ArtifactShowRequest entries. Each query may select feature/kind or path plus optional view, json_pointer, section, and limit. The batch accepts 1..16 queries and returns per-query status in one bounded envelope."
		capability["max_input_bytes"] = maxArtifactBatchInputBytes
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-show-many-input", "--format", "json"}
	case "evidence.register":
		capability["side_effect"] = "writes-content-addressed-evidence"
		capability["usage"] = "specify-runtime evidence register (--content <inline-payload|@path|-> | --object <existing-object-ref>) --scope <scope> [metadata options]"
		capability["input_contract"] = "exactly one of --content or --object; large content may use a project-contained @path or - for stdin and literal text beginning with @ uses @@; --object must reference an existing .specify/evidence/objects/sha256 object"
	case "evidence.import":
		capability["side_effect"] = "imports-content-addressed-evidence"
		capability["usage"] = "specify-runtime evidence import --file <external-local-path> --scope <scope> [metadata options]"
		capability["file_input"] = "external evidence only; agent-authored structured evidence uses evidence register --content with small inline text, project-contained @path, or stdin -"
	case "hook.extension-plan":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime hook extension-plan --event <event-id> --format json"
		capability["input_contract"] = "the runtime reads and filters .specify/extensions.yml; agents consume only returned actionable hook items"
	case "discussion.resolve":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime discussion resolve --intent continue|sp-specify|sp-quick [--slug <slug>] --format json"
		capability["input_contract"] = "resolves one canonical discussion lineage; multiple candidates return blocked/ambiguous and require an explicit slug; focus bindings carry discussion_slug and state_sha256, while consumer bindings also carry source_contract, review_digest, and recommended_consumer"
	case "discussion.bind-consumer":
		capability["side_effect"] = "writes-derived-consumer-handoff"
		capability["usage"] = "specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <resolved-review-digest> [--intake] --input-json <transition-fields> --format json"
		capability["input_contract"] = "semantic_delta, required_refs, blockers, and recovery only via --input-json (inline, @path, or -); runtime binds source contract, review digest, recommended consumer, state digest, status, and next action; --review-digest is always required from discussion resolve; unbound create-feature scaffolds may receive first bind; --intake pins a complete confirmed source as pending before Spec compilation and cannot replace foreign bindings or downgrade ready; default binding requires complete compiled Spec coverage, then mark-consumed requires a ready pointer"
	case "discussion.checkpoint":
		capability["side_effect"] = "writes-discussion-state-and-log"
		capability["usage"] = "specify-runtime discussion checkpoint <slug> --expected-state-sha256 <resolved-state-sha256> --input-json <object|@path|-> [--summary <text>] [--phase <phase>] [--user-goal <text>] --format json"
		capability["input_schema"] = "discussion-checkpoint-input"
		capability["input_contract"] = "persists canonical turn_packet v2 semantic fields including requirements_snapshot, implementation_target, source_evidence, source_materials, unknowns/conflicts, downstream_instructions, discussion_decision_digest, must_preserve, truth/evidence/confidence, design_context, and artifact_refs; source_evidence may cite material_id and source_materials receive protected material_digest; unknown fields are rejected; --expected-state-sha256 comes from discussion resolve; execute the exact project-local launcher without drive-letter reconstruction; on PowerShell prefer in-memory stdin with --input-json - instead of placing a here-string after the flag; invalid input returns show_argv for the schema and stale state returns a slug-bound next_argv for resolve"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "discussion-checkpoint-input", "--format", "json"}
	case "discussion.import-material":
		capability["side_effect"] = "writes-discussion-source-snapshot-and-state"
		capability["usage"] = "specify-runtime discussion import-material <slug> --expected-state-sha256 <sha256> --input-json <object|@path|-> --format json"
		capability["input_schema"] = "discussion-import-material-input"
		capability["input_contract"] = "reads the complete local UTF-8 text as untrusted data; preserves original locator/version, hashes immutable snapshot, derives <=2000-rune units; no URL fetch or conversion; changed source resets delivery/extraction while retaining prior version and requirements; requires exact state CAS"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "discussion-import-material-input", "--format", "json"}
	case "discussion.read-material":
		capability["side_effect"] = "writes-first-delivery-receipt-or-replays-read-only"
		capability["usage"] = "specify-runtime discussion read-material <slug> --material-id MAT-001 --unit-id <content-bound-unit-id> [--expected-state-sha256 <sha256>] --format json"
		capability["input_contract"] = "verifies the complete bound snapshot; first delivery also checks any still-present live source and requires exact state CAS plus a writable phase; already-delivered units replay the immutable snapshot read-only even when implementation later changes the original source, including after confirmation, consumption, closure or exact archive relocation, with replayed=true and no state/log/digest changes; optional replay CAS must match when supplied; returns compact reading_progress, full UTF-8 text and its original receipt; delivery is not proof of semantic understanding"
	case "discussion.write-handoff":
		capability["side_effect"] = "writes-discussion-handoff"
		capability["usage"] = "specify-runtime discussion write-handoff <slug> --expected-state-sha256 <resolved-state-sha256> --input-json <object|@path|-> --format json"
		capability["input_schema"] = "discussion-write-handoff-input"
		capability["input_contract"] = "requires latest_checkpoint.snapshot_sha256 to match the current canonical semantic snapshot; runtime derives and overwrites agent_requirement_contract, implementation_target, source_evidence/source_materials, unknown/conflict counts, downstream_instructions, decision digest, must_preserve, context boundary, and discussion_snapshot_digest from checkpoint state; input supplies only handoff_goal, consumer_eligibility/recommended_consumer, and quality_gate self-review hints; consumer status ready (not eligible); --expected-state-sha256 comes from discussion resolve; --input-json accepts inline, @path, or -"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "discussion-write-handoff-input", "--format", "json"}
	case "validate.spec":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime validate spec --feature-dir <feature-dir> [--tier light|standard|deep] [--show-passes] --format json"
		capability["input_contract"] = "--feature-dir preferred; --dir is a compatibility alias; conflicting values are rejected; without design_gate the planning-ready transition.next_action must be \"/sp.plan\" or {\"command\":\"/sp.plan\"}; when spec-contract.json design_gate.decision=required the planning-ready transition.next_action must route to \"/sp.design\" and return_target stays /sp.plan; change-propagation requires a markdown pipe table"
	case "artifact.prepare":
		capability["side_effect"] = "creates-lease"
		capability["usage"] = "specify-runtime artifact prepare --path <project-relative-path> --format json"
		capability["input_contract"] = "returns lease_id for submit/patch/delete; no --operation flag"
	case "review.target-bind":
		capability["side_effect"] = "writes-review-target-and-derived-identity"
		capability["usage"] = "specify-runtime review target-bind --feature-dir <feature-dir> --input-json <compact-target> --format json"
		capability["input_contract"] = "agent supplies id, mode, official entrypoint, environment/instance/configuration, optional build or deployment identity, test-data refs, ready-evidence refs, and Review scenario ids; runtime derives ready status, current snapshot, identity path and bytes, byte digest, and final runtime-target digest atomically"
	case "cognition.semantic-audit":
		capability["side_effect"] = "optional-atomic-audit-persistence"
		capability["usage"] = "specify-runtime cognition semantic-audit --input-json <semantic-audit-input> [--persist-dir <workflow-state-dir>] --format json"
		capability["input_contract"] = "with --persist-dir, runtime writes registered semantic-audit-input.json and semantic-audit-output.json together; agents must not recreate, submit, or patch either canonical file"
	case "evidence.visual-compare":
		capability["side_effect"] = "writes-derived-visual-comparison-report"
		capability["usage"] = "specify-runtime evidence visual-compare --feature-dir <feature-dir> --task-id <Txxx> --input-json <observed-comparison> --format json"
		capability["input_contract"] = "agent supplies entrypoint, implementation revision, typed evidence refs, matrix observations, explicit passing verdict, and reviewer; runtime derives approved design and handoff bindings, exact decision coverage, tolerance, deviations, canonical path, and byte digest from task-index.json"
	case "evidence.smoothness-manifest":
		capability["side_effect"] = "writes-derived-smoothness-manifest"
		capability["usage"] = "specify-runtime evidence smoothness-manifest --feature-dir <feature-dir> --task-id <Txxx> --format json"
		capability["input_contract"] = "runtime derives the exact smoothness acceptance ids, official entrypoint, interaction scenarios, viewport matrix, and performance budgets from the current task-index.json; stale task bindings are rejected"
	case "evidence.smoothness-validate":
		capability["side_effect"] = "writes-derived-smoothness-report"
		capability["usage"] = "specify-runtime evidence smoothness-validate --feature-dir <feature-dir> --task-id <Txxx> --manifest <manifest-ref> --input-json <observed-smoothness> --format json"
		capability["input_contract"] = "agent supplies one passing observation per expected smoothness id plus measured performance metrics; runtime enforces exact coverage and task-bound budgets, then returns the canonical report ref and byte digest"
	case "evidence.source-continuity-manifest":
		capability["side_effect"] = "writes-derived-source-continuity-manifest"
		capability["usage"] = "specify-runtime evidence source-continuity-manifest (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --format json"
		capability["input_contract"] = "derives the exact surface/action/asset universe from the immutable source_continuity contract and binds either the current task-index digest or the digest-protected Quick decision. Formal target snapshots use current expected_write_scope with legacy write_scope only as fallback; Quick uses the confirmed item write_scope. Both exclude runtime-owned workflow roots and Source Continuity outputs encountered during product traversal, stay byte-stable when product sources are unchanged, and change when an in-scope product source changes. Explicit runtime-owned scopes are invalid."
	case "evidence.source-continuity-adapter-catalog":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime evidence source-continuity-adapter-catalog --format json"
		capability["input_contract"] = "returns the embedded technology-neutral provider packs, their capabilities/actions/evidence/policies, and a deterministic registry_sha256; it does not inspect the project or install tools"
	case "evidence.source-continuity-adapter-bridge":
		capability["input_schema"] = "source-continuity-tool-inventory-input"
		capability["side_effect"] = "writes-tool-inventory-probe-and-plan"
		capability["usage"] = "specify-runtime evidence source-continuity-adapter-bridge (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --manifest <manifest-ref> --input-json <live-tool-inventory> --format json"
		capability["input_contract"] = "agent or host reports only current tool refs, generic detection signals, roles, execution mode, and availability; runtime maps signals to providers, derives visual capability availability, and atomically writes the inventory report, probe, and Plan"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "source-continuity-tool-inventory-input", "--format", "json"}
	case "evidence.source-continuity-adapter-probe":
		capability["input_schema"] = "source-continuity-adapter-probe-input"
		capability["side_effect"] = "writes-derived-source-continuity-adapter-probe-and-plan"
		capability["usage"] = "specify-runtime evidence source-continuity-adapter-probe (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --manifest <manifest-ref> --input-json <available-tool-bindings> --format json"
		capability["input_contract"] = "agent declares only observed provider ids, symbolic tool refs, roles, execution mode, and availability; runtime owns capabilities, actions, evidence kinds, write/network policy, deterministic lane selection, gap recovery, probe report, and Adapter Plan"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "source-continuity-adapter-probe-input", "--format", "json"}
	case "evidence.source-continuity-adapter-plan":
		capability["input_schema"] = "source-continuity-adapter-plan-input"
		capability["side_effect"] = "writes-derived-source-continuity-adapter-plan"
		capability["usage"] = "specify-runtime evidence source-continuity-adapter-plan (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --manifest <manifest-ref> --input-json <adapter-plan-input> --format json"
		capability["input_contract"] = "composes one or more generic adapters across all source/target capability lanes; descriptors expose only symbolic tool refs, declared permissions, typed evidence, and the bounded action enum; command, argv, env, install, unresolved gaps, and uncovered lanes are rejected"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "source-continuity-adapter-plan-input", "--format", "json"}
	case "evidence.source-continuity-adapter-execution":
		capability["side_effect"] = "writes-derived-adapter-execution-manifest"
		capability["usage"] = "specify-runtime evidence source-continuity-adapter-execution (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --manifest <manifest-ref> --adapter-plan <plan-ref> --adapter-plan-sha256 <sha256> --format json"
		capability["input_contract"] = "runtime validates the manifest/Plan/registry/probe/inventory chain and compiles one packet per selected adapter with only symbolic tool_ref, bounded actions, exact lanes and business binding ids, typed evidence requirements, permissions, preconditions, and stop conditions; no command/argv/env/script/install fields are emitted"
	case "evidence.source-continuity-validate":
		capability["side_effect"] = "writes-derived-source-continuity-report"
		capability["usage"] = "specify-runtime evidence source-continuity-validate (--feature-dir <feature-dir> --task-id <Txxx> | --quick-id <quick-id> --item-id <Qn>) --manifest <manifest-ref> --input-json <observed-source-continuity> --format json"
		capability["input_contract"] = "accepts adapter-owned observations only; requires exact discovery and target coverage, matched business outcomes/side effects/final states, source+target evidence, and semantic/provenance/render asset fidelity"
	case "design.change":
		capability["side_effect"] = "creates-design-change-workspace-and-index-record"
		capability["usage"] = "specify-runtime design change <UD-ID> --title <title> [--type greenfield|preserve|overhaul|extension] --scope <surface>... [--profiles <csv>] [--baseline-ref <ref>]... [--supersedes <UD-ID>]... --format json"
		capability["input_contract"] = "creates .specify/design/changes/<UD-ID>/design-change.md plus local working surfaces and a draft metadata-only index record; scopes are stable path-like identifiers"
	case "design.import":
		capability["side_effect"] = "imports-external-image-into-draft-design-round"
		capability["usage"] = "specify-runtime design import <external-image-path> --change <UD-ID> --round <positive-integer> [--notes <text>] --format json"
		capability["input_contract"] = "the source must be a regular PNG, JPEG, or WEBP file no larger than 32 MiB; the named change must be an existing draft. Image-round import also requires the current runtime-owned .generation.json sidecar to still match the adjacent manifest, prompt, canonical draft design-change digest, and any available input-image digests before bytes are copied atomically to .specify/design/changes/<UD-ID>/previews/round-NN.<ext>. Omit --change/--round only for legacy URL/path reference recording."
		capability["file_input"] = "external generated image only; approval still requires the adjacent manifest and exact prompt"
	case "design.prompt":
		capability["summary"] = "Persist the exact professional image prompt and generation sidecar for one draft image-primary round."
		capability["side_effect"] = "writes-runtime-owned-image-prompt-and-generation-sidecar"
		capability["usage"] = "specify-runtime design prompt <round.manifest.json|round.png|round.jpg|round.jpeg|round.webp> --content <inline|@path|-> --format json"
		capability["input_contract"] = "create-only specialized producer for one canonical draft .specify/design/changes/<UD-ID>/previews/round-* workspace. --content persists the exact professional ImageGen prompt; use stdin - for large agent-authored prompts, while @path accepts only an existing project-contained regular file. Runtime validates the adjacent image-primary manifest plus canonical draft design-change, atomically writes round-NN.prompt.md and round-NN.generation.json, returns their paths and SHA-256 receipts, treats identical replay as idempotent, and rejects different or partial existing bytes. inherit-existing requires edit-source input_images coverage for protected surfaces and records their digests."
		capability["file_input"] = "--content @path accepts only an existing project-contained regular UTF-8 file without symlink or reparse traversal; prefer stdin - for agent-authored prompts"
	case "design.iterate":
		capability["side_effect"] = "creates-digest-pinned-successor-workspace"
		capability["usage"] = "specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID> --title <title> [--type preserve|overhaul|extension] [--scope <surface>]... [--profiles <csv>] --format json"
		capability["input_contract"] = "source must be registered and byte-intact; successor scopes must be within the source; omitted scope inherits only a fully active source; the runtime pins iteration_of, basis_sha256, baseline ref, and supersedes without mutating the source"
	case "design.resolve":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime design resolve --scope <surface> --format json"
		capability["input_contract"] = "scope must be one exact stable path-like surface identifier from a design contract, such as web:orders/list or cli:search, not a prose product description. Returns active immutable candidates after scope-specific supersession; multiple candidates are a composite discovery result that must be split and explicitly adopted, never an implicit latest binding. Missing registry is read-only empty discovery; malformed or unreadable existing registry remains blocked. No candidate, missing registry, or discovery result ever waives required UI approval and registration."
	case "design.diff":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime design diff <FROM-UD-ID> <TO-UD-ID> --format json"
		capability["input_contract"] = "both changes must be registered and byte-intact; returns lineage plus semantic scope, stable DS decision, DH handoff-contract, and section deltas"
	case "design.impact":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime design impact <consumer-ref> --change <UD-ID> --scope <surface> --mode formal|formal-post-specify|quick --expected-change <UD-ID|none> --format json"
		capability["input_contract"] = "candidate must be active for the exact scope and expected-change must match the current receipt; formal-post-specify preserves the unchanged planning-ready source spec and reconciles from Plan; returns impact classes, affected DS/DH IDs, preserved_bindings, invalidated_bindings, reconcile_from, and reconciliation actions without rewriting consumer artifacts"
	case "design.register":
		capability["side_effect"] = "registers-immutable-design-change"
		capability["usage"] = "specify-runtime design register .specify/design/changes/<UD-ID>/design-change.md --format json"
		capability["input_contract"] = "requires an approved change-local contract whose ID, path, scope, and supersedes relationships match index.json; overlapping approved scopes must be explicitly superseded; registration binds the exact SHA-256 and subtracts only intersecting scopes from prior changes"
	case "design.approve":
		capability["side_effect"] = "freezes-immutable-visual-round-and-handoff"
		capability["usage"] = "specify-runtime design approve <round.html|round.png|round.jpg|round.jpeg|round.webp> --direction direction-main [--manifest <round.manifest.json> --prompt <round.prompt.md> --image-inspection available|unavailable --image-editing available|unavailable] --format json"
		capability["input_contract"] = "HTML uses its embedded ready manifest; image-primary approval requires adjacent manifest and exact generation/edit prompt plus independently probed inspection/editing capability values. Both routes byte-bind one current concept, manifest, selected-direction handoff, and explicit user approval. A non-consumable direction checkpoint on the same round blocks approval; contract completion must produce a new round."
	case "design.direction-confirm":
		capability["side_effect"] = "writes-non-consumable-direction-checkpoint"
		capability["usage"] = "specify-runtime design direction-confirm <change-local-round.html|png|jpg|jpeg|webp> --direction direction-main [--manifest <round.manifest.json> --prompt <round.prompt.md> --image-inspection available|unavailable --image-editing available|unavailable] --format json"
		capability["input_contract"] = "requires the canonical previews/round-* path inside one indexed draft .specify/design/changes/<UD-ID> workspace and a current runtime-owned .concept.json receipt from concept-level preview-lint before writing non-consumable .direction.json. Concept receipt drift, missing prompt, or mismatched manifest/capability route blocks direction confirmation. Identical replay is idempotent, drift is rejected, index.json is unchanged, and the checkpoint cannot satisfy approve, register, Plan, Implement, or Quick consumption."
	case "design.preview-lint":
		capability["side_effect"] = "writes-concept-receipt-on-concept-pass"
		capability["usage"] = "specify-runtime design preview-lint <round.html|round.png|round.jpg|round.jpeg|round.webp> --level structural|concept|ready [--inspection-json <object|@path|->] --format json"
		capability["input_contract"] = "concept is preview-only and validates one authored candidate, selected visual profiles, minimum specimens/critical states, reduced/high-contrast direction feasibility, and at least one selected-profile stress target while deferring complete DH matrices and acceptance. A passing concept run writes runtime-owned round-NN.concept.json; image-primary concept lint may also bind --inspection-json <object|@path|-> when actual inspection is available. ready retains the full immutable manifest, prompt, capability, approval, and handoff requirements."
	case "design.adopt":
		capability["side_effect"] = "appends-cas-guarded-consumer-adoption"
		capability["usage"] = "specify-runtime design adopt <consumer-ref> --change <UD-ID> --scope <surface> --mode formal|formal-post-specify|quick --binding-ref <path> --binding-sha256 <sha256> --expected-change <UD-ID|none> --format json"
		capability["input_contract"] = "formal and quick require a consumer artifact already containing the exact design binding; formal-post-specify instead byte-binds one unchanged planning-ready source spec and returns to Plan without rewriting it or rerunning Specify; expected-change is a compare-and-swap guard; adoption appends history and never rewrites the consumer"
	case "design.adoption":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime design adoption <feature-ref> --scope <surface> --binding-ref <source-spec-contract.json> --binding-sha256 <sha256> [--expected-change <UD-ID>] --format json"
		capability["input_contract"] = "verifies that the current formal-post-specify receipt still names an active immutable design change and the exact unchanged planning-ready source spec bytes; Plan consumes this proof directly and must not rerun Specify unless requirements changed"
	case "implement.result-merge":
		capability["side_effect"] = "writes-task-lifecycle-and-worker-result"
		capability["usage"] = "specify-runtime implement result-merge --feature-dir <feature-dir> --task-id <Txxx> --result-json <object|@path|-> --format json"
		capability["input_schema"] = "implement-result-merge-input"
		capability["input_contract"] = "Leader-only. Worker returns inline JSON; do not hand-author worker-results/*.json. Field validation_results (array) is required for status success; each entry needs command + status passed|failed|skipped. Worker status is success|blocked|failed (not DONE). Prefer --result-json @path or Python json.dumps argv over PowerShell ConvertTo-Json. evidence register is optional and does not replace validation_results."
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "implement-result-merge-input", "--format", "json"}
	case "implement.task-reopen":
		capability["side_effect"] = "revision-guarded-task-recovery"
		capability["usage"] = "specify-runtime implement task-reopen --feature-dir <feature-dir> --task-id <Txxx> --expected-task-revision <revision> --expected-workflow-revision <revision> --reason <reason> --evidence <evidence> --format json"
		capability["input_contract"] = "only a non-acceptance-ready implemented task may reopen; the runtime atomically archives the old lifecycle/result, preserves sibling state, and resets only the named task to ready"
	case "prd-scan.record-upsert":
		capability["side_effect"] = "writes-one-prd-record"
		capability["usage"] = "specify-runtime prd-scan record-upsert <run-id> --surface <surface> --expected-sha256 <sha> --input-json <record> --format json"
		capability["input_contract"] = "agent supplies one semantic record with a stable id; runtime owns the registered outer document, optimistic digest check, deterministic ordering, atomic write, and status invalidation"
	case "prd-scan.record-remove":
		capability["side_effect"] = "removes-one-prd-record"
		capability["usage"] = "specify-runtime prd-scan record-remove <run-id> --surface <surface> --record-id <id> --expected-sha256 <sha> --format json"
	case "prd-scan.record-show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime prd-scan record-show <run-id> --surface <surface> --record-id <id> --format json"
	case "prd-scan.record-list":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime prd-scan record-list <run-id> --surface <surface> [--limit <n>] --format json"
	case "prd-build.scaffold":
		capability["side_effect"] = "creates-missing-prd-build-documents"
		capability["usage"] = "specify-runtime prd-build scaffold <run-id> --format json"
		capability["input_contract"] = "runtime verifies the sealed scan, derives project/run/classification values, expands installed PRD templates, preserves existing outputs on resume, and creates all missing build documents atomically; agents patch only semantic sections"
	case "artifact.catalog":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime artifact catalog --format json"
	case "execution.control":
		capability["side_effect"] = "writes-unified-execution-lifecycle"
		capability["command"] = []string{"specify-runtime", "execution"}
		capability["usage"] = "specify-runtime execution announce ...; execution checkpoint ...; execution overview ...; execution guard ...; execution complete ..."
		capability["input_contract"] = "Fast, Debug, Implement, and Quick share one durable Activity per Work. Announce candidate file scope and semantic resources before mutation; checkpoint selected progress; guard the complete confirmed scope against the exact overview revision and SHA-256; checkpoint validating; complete only with terminal task state, passing evidence, and an actual Git-delta audit. Guard and completion are atomic, recovery retains actionable state, and registered Activities cannot bypass these gates through legacy Work claim, checkpoint, or finish commands."
		env.ShowArgv = []string{"specify-runtime", "execution", "help"}
	case "execution.announce":
		capability["side_effect"] = "announces-activity-and-candidate-authority"
		capability["usage"] = "specify-runtime execution announce --workflow <fast|debug|implement|quick> (--subject-id <id> --summary <text> | --work-packet-file <worker-packet.json> --work-packet-sha256 <sha256>) --agent-id <id> --adapter-id <id> [--activity-id <id>] [--work-id <id>] [--task-ref <ref>] [--item-id <id>] [--source-ref <path>] [--planned-write-scope-json <array>] [--resources-json <array>] [--lease-seconds <seconds>] [--project-root <path>] --format json"
		capability["input_contract"] = "creates one Activity and one-to-one Work atomically before mutation, captures the actual Git baseline, and advertises candidate file scope plus semantic resources without granting write authority. Implement announcements also bind the exact feature workflow.json state and its latest runtime mutation receipt when present. Manual legacy .specify/specs or specs roots identify their exact task index through --source-ref; omission selects canonical .specify/features. For implement, --work-packet-file plus --work-packet-sha256 verifies the exact compiled bytes against the canonical packet-compile receipt sha256 and current compiler output before deriving feature_id, task_id, task_ref, objective and planned_write_scope. Product write scope accepts exact future files, exact directories, or a final /** bounded subtree; filename globs are invalid, companion test/migration/fixture/generated writes must be declared, and validation commands do not grant write authority. The planned scope is the union of product write_scope and compiler-owned bookkeeping_write_scope, which includes exact feature workflow.json so official workflow block/resolve/reopen/complete mutations stay separately audited without becoming product drift; agents never hand-edit that path or add it through scope amendments. Guard the full returned set. The exact packet path, digest and original scope stay pinned for the activity; planned changes require recompilation/new announcement, while only execution guard's audited scope-amendment mode may append a later causal product companion path. Packet mode cannot be mixed with manual subject-id, item-id, task-ref, summary or planned-write-scope-json. Only execution guard grants write authority"
	case "execution.checkpoint":
		capability["side_effect"] = "advances-activity-and-renews-work"
		capability["usage"] = "specify-runtime execution checkpoint <activity-id> --expected-revision <work-revision> --fence <fence> --phase <selected|executing|validating|blocked> --next-action <text> --lease-seconds <seconds> [--observed-paths-json <array>] [--reason <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "atomically advances the lifecycle and updates the paired Work lease, heartbeat, next action, observed paths, reason, and revisions; terminal and interruption phases remain owned by their dedicated boundaries"
	case "execution.guard":
		capability["side_effect"] = "atomically-claims-execution-authority"
		capability["usage"] = "specify-runtime execution guard <activity-id> --expected-revision <work-revision> --fence <fence> --expected-overview-revision <revision> --expected-overview-sha256 <sha256> --write-scope-json <array> --resources-json <array> [--scope-amendments-json <array>] --reason <text> [--project-root <path>] --format json"
		capability["input_contract"] = "rebuilds and byte-compares the current overview, then in one transaction rejects duplicate task, file, or semantic ownership conflicts or promotes the entire confirmed set and advances selected -> claimed -> executing without partial authority. Packet scope recovery stays inside this existing guard authority: optional scope amendments require concrete causally necessary paths and reasons, preserve the original packet path/digest/write_scope, append audit state, and remain agent-owned. The runtime marks late discovery from the actual Git delta; any amendment requires independent passing scope-drift-review evidence before completion"
	case "execution.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime execution show <activity-id> [--project-root <path>] --format json"
		capability["input_contract"] = "returns the paired Activity and Work revisions, fence, lifecycle phase, candidate or confirmed write scope, semantic resources, guard binding, and completion digest"
	case "execution.complete":
		capability["side_effect"] = "audits-and-releases-execution-authority"
		capability["usage"] = "specify-runtime execution complete <activity-id> --expected-revision <work-revision> --fence <fence> --validation-json <array> --reason <text> [--project-root <path>] --format json"
		capability["input_contract"] = "requires terminal Quick/Implement task state when registered, a live fence, and passing validation; derives actual changed paths from the announced Git baseline and accepts changed workflow.json only when it is the active Implement stage and matches a newer specify-runtime workflow mutation receipt. This applies to compiled packets and manual Implement Activities across canonical and legacy feature roots; valid-shaped hand edits, malformed state, or unresolved blockers fail closed with agent-owned workflow recovery while the same Activity remains resumable. Completion holds the workflow mutation lock and rechecks the exact workflow/receipt digests inside the completion transaction before authority release; drift keeps the Activity and Work active for an agent-owned retry. Every other path outside confirmed scope is rejected. Success reports workflow_control_plane_paths, workflow_mutation_receipt_ref, workflow_mutation_receipt_sha256, and workflow_audit_preserved; the completion digest binds those control-plane file expectations before all file and semantic authority is released atomically"
	case "execution.overview":
		capability["side_effect"] = "reconciles-work-board"
		capability["usage"] = "specify-runtime execution overview [--current-work-id <work-id>] [--project-root <path>] --format json"
		capability["input_contract"] = "returns one execution-overview-v1 snapshot joining open Quick and Implement task state with registered execution activities and every live or recovery-held Work identity; activities correlate task, Work, planned scope, and confirmed scope; duplicate owners, invalid current identity, and an executing task whose planned scope is not covered by confirmed Work scope block; executing tasks without Work, recovery holds, unreadable task sources, and cross-workflow planned-scope overlap warn; other open untracked tasks remain visible context; current-work-id defaults to SPECIFY_WORK_ID"
	case "quick.preflight":
		capability["side_effect"] = "reconciles-work-board-and-refreshes-derived-quick-index"
		capability["usage"] = "specify-runtime quick preflight [<quick-id>] [--current-work-id <work-id>] [--project-root <path>] --format json"
		capability["input_contract"] = "Quick-scoped compatibility view for legacy fields and signals; global Fast, Debug, Implement, and Quick coordination uses execution.overview. Returns one quick-coordination-v1 snapshot joining unfinished STATUS.md tasks to live or recovery-held Work Board items through canonical task_ref quick:<id>[#Qn]; confirmed Work Board path overlap and an unbound same-Quick owner are hard blockers, while untracked Quick tasks, board-only work, and unfinished Quick scope overlap are advisory attention signals; current-work-id defaults to SPECIFY_WORK_ID and self identity is never inferred from task_ref alone"
	case "quick.item-start":
		capability["side_effect"] = "claims-work-scope-and-starts-quick-item"
		capability["usage"] = "specify-runtime quick item-start <quick-id> --item Qn [--current-work-id <work-id>] [--current-work-fence <fence>] [--project-root <path>] --format json"
		capability["input_contract"] = "requires an active Work identity whose exact task_ref is quick:<id> or quick:<id>#Qn; current-work-id and current-work-fence default to SPECIFY_WORK_ID and SPECIFY_WORK_FENCE; atomically claims a modifying item's complete normalized write_scope all-or-none before changing the item to in_progress or writing its packet, and returns a work_claim receipt; an explicitly scope-empty verification item returns claim_state not_required, while any later changed-files result remains invalid; a conflict, missing identity, foreign task_ref, stale fence, or inactive Work blocks without mutating Quick execution state"
	case "implement.task-start":
		capability["side_effect"] = "claims-work-scope-and-starts-implementation-task"
		capability["usage"] = "specify-runtime implement task-start --feature-dir <feature-dir> --task-id <Txxx> --execution-mode leader-direct|delegated|managed-team [--packet-ref <ref>] [--current-work-id <work-id>] [--current-work-fence <fence>] --format json"
		capability["input_contract"] = "requires an active fenced Work identity whose task_ref is implement:<feature-id> or <feature-id>#<task-id>; atomically claims expected_write_scope all-or-none and returns work_claim before changing the task lifecycle to in_progress. Scope entries are exact future files, exact directories, or final /** bounded subtrees; companion test/migration/fixture/generated writes are explicit and validation commands grant no write authority. A legacy task with no expected scope reuses the current Work's confirmed scope, while a genuinely no-write task returns claim_state not_required; missing identity, foreign task_ref, stale fence, inactive Work, or scope conflict blocks without lifecycle mutation"
	case "board.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime board show [--status active|blocked|interrupted|completed|abandoned] [--project-root <path>] --format json"
		capability["input_contract"] = "reads the repository-shared Work Board projection from the primary worktree's writable .specify/runtime/run-control store; before its one-time automatic migration, a missing canonical store may be read from the legacy Git-common location without writing there. Writer commands migrate a consistent snapshot and preserve the legacy database. Local store setup or migration failures stay typed agent-owned recovery rather than becoming a user decision; defaults to active, blocked, and interrupted work while explicit --status selects retained history; run board reconcile first when expired leases may exist, and never edit either SQLite database directly"
	case "board.owner":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime board owner <project-relative-path> [--project-root <path>] --format json"
		capability["input_contract"] = "returns active or recovery-hold confirmed write owners whose normalized scope is the same path, an ancestor, or a descendant; candidate intents remain advisory"
	case "board.reconcile":
		capability["side_effect"] = "writes-work-board-recovery-state"
		capability["usage"] = "specify-runtime board reconcile [--project-root <path>] --format json"
		capability["input_contract"] = "inspects only expired active or blocked work; clean declared scopes are released, while dirty or unavailable workspaces become interrupted recovery holds that require explicit work resume or work abandon"
	case "board.branch-policy":
		capability["side_effect"] = "reconciles-expired-work-and-selects-feature-branch-policy"
		capability["usage"] = "specify-runtime board branch-policy [--current-work-id <id>] [--project-root <path>] --format json"
		capability["input_contract"] = "returns keep-current when any other unexpired active or blocked task, or interrupted dirty recovery hold, exists in the shared Git repository; otherwise returns default so create-new-feature preserves its historical branch behavior; current-work-id defaults to SPECIFY_WORK_ID"
	case "board.feature-bootstrap":
		capability["side_effect"] = "registers-feature-work-and-selects-branch-policy"
		capability["usage"] = "specify-runtime board feature-bootstrap --feature-id <id> --feature-dir <path> --summary <text> --agent-id <id> --adapter-id <id> [--work-id <id>] [--workspace-root <path>] [--lease-seconds <seconds>] [--project-root <path>] --format json"
		capability["input_contract"] = "after a read-only create-new-feature dry run, atomically exposes one feature bootstrap to other agents before writes: feature-dir must be the exact project-local .specify/features/<feature-id> path, the confirmed create intent is conflict-checked, and the response returns both the registered Work identity/fence and feature_branch_policy; do not query branch-policy or call work begin separately"
	case "work.begin":
		capability["side_effect"] = "registers-work-and-write-intents"
		capability["usage"] = "specify-runtime work begin --summary <text> --agent-id <id> --adapter-id <id> [--work-id <id>] [--workspace-root <path>] [--intents-json <array>] [--lease-seconds <seconds>] [--project-root <path>] --format json"
		capability["input_contract"] = "register before modifying files; workspace-root must belong to the same Git common directory; confirmed path intents are conflict-checked atomically, while candidate intents advertise likely scope without blocking"
	case "work.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime work show <work-id> [--project-root <path>] --format json"
		capability["input_contract"] = "returns current revision, fence, lease, recovery state, observed paths, and retained write-intent history for one work item"
	case "work.claim":
		capability["side_effect"] = "claims-complete-workflow-write-scope"
		capability["usage"] = "specify-runtime work claim --current-work-id <work-id> --current-work-fence <fence> --task-ref <exact-task-ref> --write-scope-json <array> [--reason <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "shared Fast, Debug, Implement, and Quick claim-before-write gate: requires the active fenced Work identity and exact task_ref, normalizes and claims the complete confirmed scope all-or-none before source writes, and returns a work_claim receipt; missing identity, foreign task_ref, stale fence, inactive Work, empty scope, or conflict blocks without a partial claim"
	case "work.scope-add":
		capability["side_effect"] = "adds-conflict-checked-write-intent"
		capability["usage"] = "specify-runtime work scope-add <work-id> --expected-revision <revision> --fence <fence> --path <project-relative-path> [--operation create|modify|delete|rename] [--confidence candidate|confirmed] [--reason <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "declare scope before touching a newly discovered file; revision and fence are compare-and-swap guards, an existing own candidate is promoted in place after conflict checking, and a confirmed same/ancestor/descendant owner returns a blocked conflict instead of stealing scope"
	case "work.checkpoint":
		capability["side_effect"] = "renews-work-lease-and-checkpoint"
		capability["usage"] = "specify-runtime work checkpoint <work-id> --expected-revision <revision> --fence <fence> [--lease-seconds <seconds>] [--next-action <text>] [--observed-paths-json <array>] [--project-root <path>] --format json"
		capability["input_contract"] = "renews live ownership with optimistic revision and fence checks and records a compact restart point plus paths actually observed as changed"
	case "work.block":
		capability["side_effect"] = "blocks-work-while-retaining-scope"
		capability["usage"] = "specify-runtime work block <work-id> --expected-revision <revision> --fence <fence> --reason <text> [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "records a resumable blocker and retains confirmed write ownership until finish, abandon, or stale reconciliation"
	case "work.finish":
		capability["side_effect"] = "completes-work-and-releases-scope"
		capability["usage"] = "specify-runtime work finish <work-id> --expected-revision <revision> --fence <fence> --reason <text> [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "marks work completed and releases active or recovery write ownership while retaining the board record and intent history"
	case "work.unblock":
		capability["side_effect"] = "resumes-live-blocked-work"
		capability["usage"] = "specify-runtime work unblock <work-id> --expected-revision <revision> --fence <fence> --reason <text> [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "revision- and fence-bound blocked -> active transition for the same live owner/session; preserves the current owner, fence, workspace, declared write intents, and semantic resources without interruption or broad workspace recovery inspection; interrupted work still uses work resume"
	case "work.abandon":
		capability["side_effect"] = "abandons-work-and-releases-scope"
		capability["usage"] = "specify-runtime work abandon <work-id> --expected-revision <revision> --fence <fence> --reason <text> [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "explicitly retires active, blocked, or interrupted work and releases all held scope; use after inspecting dirty recovery state and deciding the old task will not resume"
	case "work.interrupt":
		capability["side_effect"] = "fences-live-work-for-explicit-recovery"
		capability["usage"] = "specify-runtime work interrupt <work-id> --expected-revision <revision> --fence <fence> --reason <text> [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "use only after confirming the recorded owner session has ended, such as after a computer restart; exact revision and fence are required, the recorded workspace is inspected immediately, matching dirty paths retain a recovery hold, unavailable workspace inspection preserves every declared scope, and work resume then acquires a new fence"
	case "work.resume":
		capability["side_effect"] = "resumes-interrupted-work-under-new-fence"
		capability["usage"] = "specify-runtime work resume <work-id> --expected-revision <revision> --agent-id <id> --adapter-id <id> [--workspace-root <path>] [--lease-seconds <seconds>] [--next-action <text>] [--project-root <path>] --format json"
		capability["input_contract"] = "explicitly reclaims interrupted intents after atomic conflict checks, clears recovery holds, and advances the fence; defaults to the interrupted worktree, while an unavailable worktree blocks until an inspected same-repository replacement is passed with --workspace-root or the work is abandoned"
	}
	if descriptor, ok := e2eCapabilityDescriptor(capabilityID); ok {
		for key, value := range descriptor {
			capability[key] = value
		}
		if schemaID, ok := descriptor["input_schema"].(string); ok {
			env.ShowArgv = []string{"specify-runtime", "api", "schema", schemaID, "--format", "json"}
		}
	}
	addQuickPackOutputContract(capabilityID, capability, capability)
	env.Data["capability"] = capability
	return writeEnvelope(stdout, env)
}

func apiObjectID(args []string, kind string) (string, Envelope, bool) {
	if len(args) == 0 {
		return "", NewEnvelope("usage-error", "missing "+kind+" id"), false
	}
	if args[0] == "--id" {
		if len(args) < 2 || strings.HasPrefix(args[1], "--") {
			return "", NewEnvelope("usage-error", "--id requires a "+kind+" id"), false
		}
		return strings.TrimSpace(args[1]), Envelope{}, true
	}
	if strings.HasPrefix(args[0], "--") {
		env := NewEnvelope("usage-error", fmt.Sprintf("unknown %s selector %q", kind, args[0]))
		env.Blockers = append(env.Blockers, "pass the id positionally or use --id <id>")
		return "", env, false
	}
	return strings.TrimSpace(args[0]), Envelope{}, true
}

func containsCapability(capabilities []string, want string) bool {
	for _, capability := range capabilities {
		if capability == want {
			return true
		}
	}
	return false
}

func deepResearchTrackPrepareInputSchema() map[string]any {
	track := deepResearchSchemaObject(
		[]string{"track_id", "title", "capability_refs", "read_paths", "questions", "source_classes", "requires_spike", "completion_signal"},
		map[string]any{
			"track_id":          deepResearchSchemaString("^TRK-[0-9]{3,}$"),
			"title":             deepResearchSchemaString(""),
			"capability_refs":   deepResearchSchemaStringArray("^CAP-[0-9]{3,}$", 1),
			"read_paths":        deepResearchSchemaStringArray("", 1),
			"questions":         deepResearchSchemaStringArray("", 1),
			"source_classes":    map[string]any{"type": "array", "minItems": 1, "uniqueItems": true, "items": map[string]any{"type": "string", "enum": []string{"repository", "primary_external", "secondary_external", "experiment"}}},
			"requires_spike":    map[string]any{"type": "boolean"},
			"completion_signal": deepResearchSchemaString(""),
		},
	)
	return deepResearchSchemaRoot("deep-research-track-prepare-input", []string{"tracks"}, map[string]any{
		"tracks": map[string]any{"type": "array", "minItems": 1, "items": track},
	})
}

func deepResearchTrackSubmitResultSchema() map[string]any {
	quality := deepResearchSchemaObject(
		[]string{"authority", "independence", "recency", "limitations"},
		map[string]any{
			"authority":    map[string]any{"type": "string", "enum": []string{"repository", "primary", "secondary", "experiment"}},
			"independence": map[string]any{"type": "string", "enum": []string{"direct", "independent", "corroborated", "single-source"}},
			"recency":      map[string]any{"type": "string", "enum": []string{"current", "dated", "unknown"}},
			"limitations":  deepResearchSchemaStringArray("", 0),
		},
	)
	evidence := deepResearchSchemaObject(
		[]string{"evidence_id", "source_type", "source_ref", "claim", "capability_refs", "quality"},
		map[string]any{
			"evidence_id":     deepResearchSchemaString("^EVD-[0-9]{3,}$"),
			"source_type":     map[string]any{"type": "string", "enum": []string{"repository", "primary_external", "secondary_external", "experiment"}},
			"source_ref":      deepResearchSchemaString(""),
			"source_title":    deepResearchSchemaString(""),
			"retrieved_on":    map[string]any{"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
			"claim":           deepResearchSchemaString(""),
			"capability_refs": deepResearchSchemaStringArray("^CAP-[0-9]{3,}$", 1),
			"quality":         quality,
		},
	)
	finding := deepResearchSchemaObject(
		[]string{"finding_id", "kind", "summary", "capability_refs", "evidence_refs", "spike_refs"},
		map[string]any{
			"finding_id":      deepResearchSchemaString("^FND-[0-9]{3,}$"),
			"kind":            map[string]any{"type": "string", "enum": []string{"fact", "inference", "recommendation"}},
			"summary":         deepResearchSchemaString(""),
			"capability_refs": deepResearchSchemaStringArray("^CAP-[0-9]{3,}$", 1),
			"evidence_refs":   deepResearchSchemaStringArray("^EVD-[0-9]{3,}$", 1),
			"spike_refs":      deepResearchSchemaStringArray("", 0),
		},
	)
	contradiction := deepResearchSchemaObject(
		[]string{"contradiction_id", "summary", "evidence_refs"},
		map[string]any{
			"contradiction_id": deepResearchSchemaString("^CON-[0-9]{3,}$"),
			"summary":          deepResearchSchemaString(""),
			"evidence_refs":    deepResearchSchemaStringArray("^EVD-[0-9]{3,}$", 1),
		},
	)
	schema := deepResearchSchemaRoot("deep-research-track-submit-result", []string{"protocol", "status", "paths_read"}, map[string]any{
		"protocol":       map[string]any{"const": deepResearchTrackProtocol},
		"status":         map[string]any{"type": "string", "enum": []string{"complete", "blocked"}},
		"paths_read":     deepResearchSchemaStringArray("", 1),
		"findings":       map[string]any{"type": "array", "items": finding},
		"evidence":       map[string]any{"type": "array", "items": evidence},
		"spike_refs":     deepResearchSchemaStringArray("", 0),
		"constraints":    deepResearchSchemaStringArray("", 0),
		"risks":          deepResearchSchemaStringArray("", 0),
		"contradictions": map[string]any{"type": "array", "items": contradiction},
		"blockers":       deepResearchSchemaStringArray("", 0),
	})
	schema["allOf"] = []any{
		map[string]any{"if": map[string]any{"properties": map[string]any{"status": map[string]any{"const": "complete"}}}, "then": map[string]any{"required": []string{"findings", "evidence"}, "properties": map[string]any{"findings": map[string]any{"minItems": 1}, "evidence": map[string]any{"minItems": 1}}}},
		map[string]any{"if": map[string]any{"properties": map[string]any{"status": map[string]any{"const": "blocked"}}}, "then": map[string]any{"required": []string{"blockers"}, "properties": map[string]any{"blockers": map[string]any{"minItems": 1}}}},
	}
	return schema
}

func deepResearchSynthesisInputSchema() map[string]any {
	capabilityDisposition := deepResearchSchemaObject([]string{"capability_ref", "disposition", "reason_refs"}, map[string]any{
		"capability_ref": deepResearchSchemaString("^CAP-[0-9]{3,}$"),
		"disposition":    map[string]any{"type": "string", "enum": []string{"plannable", "constrained_but_plannable"}},
		"reason_refs":    deepResearchSchemaStringArray("", 1),
	})
	planningHandoff := deepResearchSchemaObject([]string{"handoff_id", "capability_refs", "status", "decision", "evidence_refs", "spike_refs", "constraints", "risks", "rejected_options", "validation"}, map[string]any{
		"handoff_id":       deepResearchSchemaString("^PH-[0-9]{3,}$"),
		"capability_refs":  deepResearchSchemaStringArray("^CAP-[0-9]{3,}$", 1),
		"status":           map[string]any{"type": "string", "enum": []string{"mandatory", "optional", "user-decision"}},
		"decision":         deepResearchSchemaString(""),
		"evidence_refs":    deepResearchSchemaStringArray("^EVD-[0-9]{3,}$", 0),
		"spike_refs":       deepResearchSchemaStringArray("", 0),
		"constraints":      deepResearchSchemaStringArray("", 0),
		"risks":            deepResearchSchemaStringArray("", 0),
		"rejected_options": deepResearchSchemaStringArray("", 0),
		"validation":       deepResearchSchemaStringArray("", 1),
	})
	evidenceDisposition := deepResearchSchemaObject([]string{"evidence_ref", "disposition", "handoff_refs", "reason"}, map[string]any{
		"evidence_ref": deepResearchSchemaString("^EVD-[0-9]{3,}$"),
		"disposition":  map[string]any{"type": "string", "enum": []string{"consumed", "deferred", "excluded"}},
		"handoff_refs": deepResearchSchemaStringArray("^PH-[0-9]{3,}$", 0),
		"reason":       deepResearchSchemaString(""),
	})
	contradictionResolution := deepResearchSchemaObject([]string{"contradiction_id", "resolution", "evidence_refs"}, map[string]any{
		"contradiction_id": deepResearchSchemaString("^CON-[0-9]{3,}$"),
		"resolution":       deepResearchSchemaString(""),
		"evidence_refs":    deepResearchSchemaStringArray("^EVD-[0-9]{3,}$", 1),
	})
	return deepResearchSchemaRoot("deep-research-synthesis-input", []string{"capability_dispositions", "planning_handoffs", "evidence_dispositions", "contradiction_resolutions", "recommended_next_command"}, map[string]any{
		"capability_dispositions":   map[string]any{"type": "array", "minItems": 1, "items": capabilityDisposition},
		"planning_handoffs":         map[string]any{"type": "array", "minItems": 1, "items": planningHandoff},
		"evidence_dispositions":     map[string]any{"type": "array", "items": evidenceDisposition},
		"contradiction_resolutions": map[string]any{"type": "array", "items": contradictionResolution},
		"recommended_next_command":  map[string]any{"const": "/sp.plan"},
	})
}

func deepResearchAuditInputSchema() map[string]any {
	check := deepResearchSchemaObject([]string{"check_id", "status", "evidence_refs"}, map[string]any{
		"check_id":      map[string]any{"type": "string", "enum": append([]string(nil), deepResearchAuditCheckIDs...)},
		"status":        map[string]any{"type": "string", "enum": []string{"pass", "fail"}},
		"evidence_refs": deepResearchSchemaStringArray("", 0),
	})
	finding := deepResearchSchemaObject([]string{"severity", "summary"}, map[string]any{
		"severity": map[string]any{"type": "string", "enum": []string{"low", "medium", "high", "blocking"}},
		"summary":  deepResearchSchemaString(""),
	})
	return deepResearchSchemaRoot("deep-research-audit-input", []string{"schema_version", "audit_request_sha256", "status", "checks", "findings"}, map[string]any{
		"schema_version":       map[string]any{"const": deepResearchAuditV1},
		"audit_request_sha256": deepResearchSchemaString("^[0-9a-f]{64}$"),
		"status":               map[string]any{"type": "string", "enum": []string{"accepted", "rejected"}},
		"checks":               map[string]any{"type": "array", "minItems": len(deepResearchAuditCheckIDs), "maxItems": len(deepResearchAuditCheckIDs), "items": check},
		"findings":             map[string]any{"type": "array", "items": finding},
	})
}

func deepResearchNotNeededInputSchema() map[string]any {
	disposition := deepResearchSchemaObject([]string{"capability_ref", "reason", "evidence_refs"}, map[string]any{
		"capability_ref": deepResearchSchemaString("^CAP-[0-9]{3,}$"),
		"reason":         deepResearchSchemaString(""),
		"evidence_refs":  deepResearchSchemaStringArray("", 1),
	})
	return deepResearchSchemaRoot("deep-research-not-needed-input", []string{"capability_dispositions"}, map[string]any{
		"capability_dispositions": map[string]any{"type": "array", "minItems": 1, "items": disposition},
	})
}

func deepResearchSchemaRoot(id string, required []string, properties map[string]any) map[string]any {
	return map[string]any{
		"$schema": "https://json-schema.org/draft/2020-12/schema",
		"$id":     "specify://schemas/" + id + "/v1", "type": "object",
		"additionalProperties": false, "required": required, "properties": properties,
	}
}

func deepResearchSchemaObject(required []string, properties map[string]any) map[string]any {
	return map[string]any{"type": "object", "additionalProperties": false, "required": required, "properties": properties}
}

func deepResearchSchemaString(pattern string) map[string]any {
	schema := map[string]any{"type": "string", "minLength": 1}
	if pattern != "" {
		schema["pattern"] = pattern
	}
	return schema
}

func deepResearchSchemaStringArray(pattern string, minItems int) map[string]any {
	return map[string]any{
		"type": "array", "minItems": minItems, "uniqueItems": true,
		"items": deepResearchSchemaString(pattern),
	}
}

func artifactScaffoldInputSchema() map[string]any {
	nonEmptyString := func() map[string]any {
		return map[string]any{"type": "string", "minLength": 1}
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/artifact-scaffold-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"kind", "path"},
		"properties": map[string]any{
			"kind": nonEmptyString(),
			"path": nonEmptyString(),
			"vars": map[string]any{"type": "object"},
		},
		"x-compatibility-aliases": map[string]any{"out": "path"},
	}
}

func artifactChecklistInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/artifact-checklist-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"categories"},
		"properties": map[string]any{
			"title":   nonEmptyString,
			"purpose": nonEmptyString,
			"feature": nonEmptyString,
			"categories": map[string]any{
				"type":     "array",
				"minItems": 1,
				"maxItems": 40,
				"items": map[string]any{
					"type":                 "object",
					"additionalProperties": false,
					"required":             []string{"heading", "items"},
					"properties": map[string]any{
						"heading": nonEmptyString,
						"items":   map[string]any{"type": "array", "minItems": 1, "items": nonEmptyString},
					},
				},
			},
		},
		"allOf": []any{map[string]any{
			"description": "title, purpose, and feature are required when the target does not yet exist",
		}},
	}
}

func artifactPatchInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/artifact-patch-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"lease"},
		"properties": map[string]any{
			"lease":               nonEmptyString,
			"json_pointer":        nonEmptyString,
			"frontmatter_pointer": nonEmptyString,
			"value":               map[string]any{},
			"value_json_pointer":  nonEmptyString,
			"section": map[string]any{
				"type":        "string",
				"minLength":   1,
				"description": "Markdown heading text. Bare titles and optional #/## markers both match (case-insensitive).",
			},
			"content": map[string]any{
				"type":        "string",
				"description": "Replacement section body without the heading line. On Windows, prefer / path separators or raw strings so \\a is not a bell escape.",
			},
			"frontmatter_patch": map[string]any{"type": "object", "minProperties": 1},
			"heading":           nonEmptyString,
			"new_heading":       nonEmptyString,
			"preamble":          map[string]any{"type": "string"},
			"append_value":      map[string]any{},
		},
		"oneOf": []any{
			map[string]any{"required": []string{"json_pointer", "value"}},
			map[string]any{"required": []string{"frontmatter_pointer", "value"}},
			map[string]any{"required": []string{"section", "content"}},
			map[string]any{"required": []string{"frontmatter_patch"}},
			map[string]any{"required": []string{"heading", "new_heading"}},
			map[string]any{"required": []string{"preamble"}},
			map[string]any{"required": []string{"append_value"}},
		},
	}
}

func sourceContinuityAdapterPlanInputSchema() map[string]any {
	stringArray := func(values []any, minItems int) map[string]any {
		return map[string]any{
			"type": "array", "minItems": minItems, "uniqueItems": true,
			"items": map[string]any{"type": "string", "enum": values},
		}
	}
	capabilities := []any{"surface-enumeration", "action-execution", "side-effect-observation", "asset-inspection", "visual-capture"}
	actions := []any{"enumerate-surfaces", "enumerate-actions", "enumerate-assets", "activate-action", "observe-side-effects", "capture-structure", "capture-visual", "capture-runtime", "prepare-isolated-test-data"}
	evidenceKinds := []any{"structure_snapshot", "visual_capture", "runtime_diagnostics"}
	adapter := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required": []string{
			"id", "version", "roles", "capabilities", "actions", "evidence_kinds",
			"execution_mode", "tool_ref", "write_policy", "network_policy",
		},
		"properties": map[string]any{
			"id":             map[string]any{"type": "string", "pattern": `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`},
			"version":        map[string]any{"type": "string", "minLength": 1},
			"roles":          stringArray([]any{"source", "target"}, 1),
			"capabilities":   stringArray(capabilities, 1),
			"actions":        stringArray(actions, 1),
			"evidence_kinds": stringArray(evidenceKinds, 1),
			"execution_mode": map[string]any{"type": "string", "enum": []any{"runtime-managed", "agent-tool", "app-connector", "external-runner", "manual-attested"}},
			"tool_ref":       map[string]any{"type": "string", "pattern": `^[a-z][a-z0-9+.-]*://\S+$`},
			"write_policy":   map[string]any{"type": "string", "enum": []any{"read-only", "evidence-store-only", "isolated-test-data"}},
			"network_policy": map[string]any{"type": "string", "enum": []any{"denied", "declared-read-only"}},
		},
	}
	assignment := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"side", "capability", "adapter_id", "selection_reason"},
		"properties": map[string]any{
			"side":             map[string]any{"type": "string", "enum": []any{"source", "target"}},
			"capability":       map[string]any{"type": "string", "enum": capabilities},
			"adapter_id":       map[string]any{"type": "string", "pattern": `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`},
			"selection_reason": map[string]any{"type": "string", "minLength": 1},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/source-continuity-adapter-plan-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"schema", "adapters", "assignments", "unresolved_gaps"},
		"properties": map[string]any{
			"schema":          map[string]any{"const": sourceContinuityAdapterInputSchema},
			"adapters":        map[string]any{"type": "array", "minItems": 1, "items": adapter},
			"assignments":     map[string]any{"type": "array", "minItems": 10, "maxItems": 10, "items": assignment},
			"unresolved_gaps": map[string]any{"type": "array", "maxItems": 0},
		},
	}
}

func sourceContinuityAdapterProbeInputJSONSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	binding := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"id", "provider_ids", "roles", "tool_ref", "execution_mode", "available", "unavailable_reason"},
		"properties": map[string]any{
			"id": map[string]any{"type": "string", "minLength": 1, "maxLength": 128},
			"provider_ids": map[string]any{
				"type": "array", "minItems": 1, "maxItems": 3, "uniqueItems": true,
				"items": nonEmptyString,
			},
			"roles": map[string]any{
				"type": "array", "minItems": 1, "uniqueItems": true,
				"items": map[string]any{"type": "string", "enum": []any{"source", "target"}},
			},
			"tool_ref":           map[string]any{"type": "string", "maxLength": 512, "pattern": `^[a-z][a-z0-9+.-]*://\S+$`},
			"execution_mode":     map[string]any{"type": "string", "enum": []any{"runtime-managed", "agent-tool", "app-connector", "external-runner", "manual-attested"}},
			"available":          map[string]any{"type": "boolean"},
			"unavailable_reason": map[string]any{"type": "string", "enum": []any{"", "tool-missing", "permission-denied", "source-unavailable", "unsupported-mode", "manual-attestation-unavailable"}},
		},
	}
	policy := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"allow_manual_attested", "preferred_binding_ids"},
		"properties": map[string]any{
			"allow_manual_attested": map[string]any{"type": "boolean"},
			"preferred_binding_ids": map[string]any{
				"type": "array", "maxItems": 32, "uniqueItems": true, "items": nonEmptyString,
			},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/source-continuity-adapter-probe-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"schema", "bindings", "policy"},
		"properties": map[string]any{
			"schema":   map[string]any{"const": sourceContinuityAdapterProbeInputSchema},
			"bindings": map[string]any{"type": "array", "minItems": 1, "maxItems": 32, "items": binding},
			"policy":   policy,
		},
	}
}

func sourceContinuityToolInventoryInputJSONSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	signals := stringsToAny(sourceContinuityToolInventorySignalStrings())
	tool := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"id", "tool_ref", "signals", "roles", "execution_mode", "available", "unavailable_reason"},
		"properties": map[string]any{
			"id":       map[string]any{"type": "string", "minLength": 1, "maxLength": 128},
			"tool_ref": map[string]any{"type": "string", "maxLength": 512, "pattern": `^[a-z][a-z0-9+.-]*://\S+$`},
			"signals": map[string]any{
				"type": "array", "minItems": 1, "maxItems": 32, "uniqueItems": true,
				"items": map[string]any{"type": "string", "enum": signals},
			},
			"roles": map[string]any{
				"type": "array", "minItems": 1, "maxItems": 2, "uniqueItems": true,
				"items": map[string]any{"type": "string", "enum": []any{"source", "target"}},
			},
			"execution_mode":     map[string]any{"type": "string", "enum": []any{"runtime-managed", "agent-tool", "app-connector", "external-runner", "manual-attested"}},
			"available":          map[string]any{"type": "boolean"},
			"unavailable_reason": map[string]any{"type": "string", "enum": []any{"", "tool-missing", "permission-denied", "source-unavailable", "unsupported-mode", "manual-attestation-unavailable"}},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/source-continuity-tool-inventory-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"schema", "source", "tools", "policy"},
		"properties": map[string]any{
			"schema": map[string]any{"const": sourceContinuityToolInventoryInputSchema},
			"source": map[string]any{
				"type":                 "object",
				"additionalProperties": false,
				"required":             []string{"kind", "captured_by", "freshness"},
				"properties": map[string]any{
					"kind":        map[string]any{"const": "live-session"},
					"captured_by": map[string]any{"type": "string", "enum": []any{"agent-observation", "runtime-api", "host-connector"}},
					"freshness":   map[string]any{"const": "current"},
				},
			},
			"tools": map[string]any{"type": "array", "minItems": 1, "maxItems": 32, "items": tool},
			"policy": map[string]any{
				"type":                 "object",
				"additionalProperties": false,
				"required":             []string{"allow_manual_attested", "preferred_tool_ids"},
				"properties": map[string]any{
					"allow_manual_attested": map[string]any{"type": "boolean"},
					"preferred_tool_ids": map[string]any{
						"type": "array", "maxItems": 32, "uniqueItems": true, "items": nonEmptyString,
					},
				},
			},
		},
	}
}

func artifactShowManyInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	showRequest := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"properties": map[string]any{
			"feature":      nonEmptyString,
			"kind":         nonEmptyString,
			"path":         nonEmptyString,
			"view":         map[string]any{"type": "string", "enum": []any{"summary", "full"}},
			"json_pointer": nonEmptyString,
			"section":      nonEmptyString,
			"limit":        map[string]any{"type": "integer", "minimum": 1},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/artifact-show-many-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"queries"},
		"properties": map[string]any{
			"queries": map[string]any{
				"type":     "array",
				"minItems": 1,
				"maxItems": maxArtifactShowManyQueries,
				"items":    showRequest,
			},
		},
	}
}

func artifactPatchBatchInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	operation := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"properties": map[string]any{
			"json_pointer": nonEmptyString,
			"value":        map[string]any{},
			"section":      nonEmptyString,
			"content":      map[string]any{"type": "string"},
			"frontmatter":  map[string]any{"type": "object", "minProperties": 1},
		},
		"oneOf": []any{
			map[string]any{"required": []string{"json_pointer", "value"}},
			map[string]any{"required": []string{"section", "content"}},
			map[string]any{"required": []string{"frontmatter"}},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/artifact-patch-batch-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"operations"},
		"properties": map[string]any{
			"operations": map[string]any{
				"type":     "array",
				"minItems": 1,
				"maxItems": maxArtifactPatchBatchOperations,
				"items":    operation,
			},
		},
	}
}

func implementResultMergeInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	validationEntry := map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"command", "status"},
		"properties": map[string]any{
			"command": nonEmptyString,
			"cmd":     nonEmptyString,
			"check":   nonEmptyString,
			"kind":    map[string]any{"type": "string", "description": "Alias accepted as command when command is absent"},
			"status": map[string]any{
				"type":        "string",
				"enum":        []any{"passed", "failed", "skipped", "pass", "success", "fail", "interrupted"},
				"description": "Normalized to passed|failed|skipped; acceptance-ready success requires every entry passed",
			},
			"summary": nonEmptyString,
			"output":  map[string]any{"type": "string"},
			"details": map[string]any{"type": "string"},
			"message": map[string]any{"type": "string"},
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/implement-result-merge-input/v1",
		"type":                 "object",
		"additionalProperties": true,
		"description":          "WorkerTaskResult for specify-runtime implement result-merge --result-json. Leader merges; workers must not write worker-results/ themselves.",
		"required":             []string{"status"},
		"properties": map[string]any{
			"task_id": map[string]any{"type": "string", "pattern": "^T\\d+$", "description": "Optional when --task-id is supplied; must match when present"},
			"status": map[string]any{
				"type":        "string",
				"enum":        []any{"success", "blocked", "failed", "succeeded", "completed", "done", "pass", "error"},
				"description": "Canonical: success|blocked|failed. DONE/done normalize to success. pending is rejected.",
			},
			"changed_files": map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
			"changedFiles":  map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
			"validation_results": map[string]any{
				"type":        "array",
				"description": "Required non-empty for acceptance-ready success; at least one and every entry must be status passed. Not replaced by evidence register.",
				"items":       validationEntry,
			},
			"validationResults":          map[string]any{"type": "array", "items": validationEntry},
			"blockers":                   map[string]any{"type": "array", "items": map[string]any{"type": "string"}, "description": "Required non-empty when status is blocked; must be empty for success"},
			"suggested_recovery_actions": map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
			"summary":                    map[string]any{"type": "string"},
			"ui_verification":            map[string]any{"type": "object"},
			"obligation_evidence":        map[string]any{"type": "array"},
		},
		"examples": []any{
			map[string]any{
				"task_id":       "T001",
				"status":        "success",
				"changed_files": []any{"backend/cmd/api/main.go"},
				"validation_results": []any{
					map[string]any{"command": "go test ./...", "status": "passed", "summary": "ok"},
				},
				"blockers": []any{},
			},
		},
	}
}

func discussionImportMaterialInputSchema() map[string]any {
	properties := map[string]any{}
	for _, field := range []string{"path", "locator", "material_type", "summary", "version_ref"} {
		properties[field] = discussionJSONNonEmptyStringSchema()
	}
	for field, limit := range map[string]int{"locator": 2048, "material_type": 128, "summary": 1000, "version_ref": 512} {
		properties[field].(map[string]any)["maxLength"] = limit
	}
	properties["id"] = map[string]any{"type": "string", "pattern": "^MAT-[0-9]{3,}$"}
	properties["sensitivity"] = map[string]any{"type": "string", "enum": []any{"safe", "sanitized", "restricted"}}
	return map[string]any{"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "specify://schemas/discussion-import-material-input/v1", "type": "object", "additionalProperties": false, "required": []string{"id", "path", "locator", "material_type", "summary", "sensitivity"}, "properties": properties}
}

func discussionSourceRequirementSchema() map[string]any {
	properties := map[string]any{}
	for _, field := range []string{"statement", "acceptance_hint", "reason", "decision_source", "reopen_condition", "duplicate_of"} {
		properties[field] = discussionJSONNonEmptyStringSchema()
	}
	properties["id"] = map[string]any{"type": "string", "pattern": "^REQ-[0-9]{3,}$"}
	properties["disposition"] = map[string]any{"type": "string", "enum": []any{"in_scope", "context", "duplicate", "deferred", "out_of_scope", "unresolved"}}
	properties["source_refs"] = map[string]any{"type": "array", "minItems": 1, "items": map[string]any{"type": "object", "required": []string{"material_id", "unit_id", "locator"}, "properties": map[string]any{"material_id": map[string]any{"type": "string", "pattern": "^MAT-[0-9]{3,}$"}, "unit_id": map[string]any{"type": "string", "pattern": "^U[0-9]{4,}-[a-f0-9]{12}$"}, "locator": discussionJSONNonEmptyStringSchema()}}}
	conditions := []any{}
	requiredByDisposition := map[string][]string{"in_scope": {"acceptance_hint"}, "context": {"reason"}, "unresolved": {"reason"}, "duplicate": {"reason", "duplicate_of"}, "deferred": {"reason", "decision_source", "reopen_condition"}, "out_of_scope": {"reason", "decision_source", "reopen_condition"}}
	for _, disposition := range []string{"in_scope", "context", "unresolved", "duplicate", "deferred", "out_of_scope"} {
		required := requiredByDisposition[disposition]
		conditions = append(conditions, map[string]any{"if": map[string]any{"properties": map[string]any{"disposition": map[string]any{"const": disposition}}}, "then": map[string]any{"required": required}})
	}
	return map[string]any{"type": "object", "required": []string{"id", "statement", "source_refs", "disposition"}, "properties": properties, "allOf": conditions}
}

func discussionCheckpointInputSchema() map[string]any {
	nonEmptyString := discussionJSONNonEmptyStringSchema()
	stringArray := discussionJSONStringArraySchema(0)
	materialObject := discussionSourceMaterialSchema(false)
	evidenceObject := discussionSourceEvidenceSchema()
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/discussion-checkpoint-input/v2",
		"type":                 "object",
		"additionalProperties": false,
		"description":          "Semantic checkpoint payload for specify-runtime discussion checkpoint. Unknown fields are rejected. Pass via --input-json (inline, @path, or -).",
		"properties": map[string]any{
			"summary":                    nonEmptyString,
			"lifecycle_phase":            map[string]any{"type": "string", "enum": []any{"explore", "ground", "decide", "prepare", "review"}},
			"phase":                      map[string]any{"type": "string", "description": "Alias for lifecycle_phase"},
			"user_goal":                  nonEmptyString,
			"turn_class":                 nonEmptyString,
			"current_decision_frame":     nonEmptyString,
			"requirements_snapshot":      discussionRequirementsSnapshotSchema(false),
			"implementation_target":      discussionImplementationTargetSchema(),
			"source_evidence":            map[string]any{"type": "array", "items": evidenceObject},
			"source_materials":           map[string]any{"type": "array", "items": materialObject},
			"blocking_unknowns":          map[string]any{"type": "array"},
			"soft_unknowns":              map[string]any{"type": "array"},
			"conflicts":                  map[string]any{"type": "array"},
			"downstream_instructions":    discussionDownstreamInstructionsSchema(false),
			"discussion_decision_digest": map[string]any{"type": "object"},
			"must_preserve":              map[string]any{"type": "array", "items": discussionMustPreserveSchema()},
			"truth_pass_status":          map[string]any{"type": "string", "enum": []any{"not-needed", "needed", "in-progress", "complete", "blocked"}},
			"verified_project_facts":     stringArray,
			"evidence_checked":           stringArray,
			"advice_confidence": map[string]any{"oneOf": []any{
				map[string]any{"type": "string", "enum": []any{"high", "medium", "low", "blocked", "none"}},
				map[string]any{"type": "object", "required": []string{"level", "reason"}, "properties": map[string]any{
					"level":  map[string]any{"type": "string", "enum": []any{"high", "medium", "low", "blocked", "none"}},
					"reason": nonEmptyString,
				}},
			}},
			"discussion_compass_status": map[string]any{"type": "string", "enum": []any{"missing", "current", "stale"}},
			"next_discussion_paths":     stringArray,
			"ui_discussion_status":      map[string]any{"type": "string", "enum": []any{"not_applicable", "offered", "accepted", "skipped", "completed", "deferred"}},
			"design_context":            map[string]any{"type": "object"},
			"artifact_refs":             stringArray,
			"topic_ownership":           discussionTopicOwnershipSchema(),
			"confirmed_decisions":       stringArray,
			"changed_recommendations":   stringArray,
			"context_boundary":          map[string]any{"type": "object"},
			"verified_fact_refs":        map[string]any{"type": "array"},
			"open_assumptions":          map[string]any{"type": "array"},
			"open_questions":            map[string]any{"type": "array"},
			"current_recommendation":    nonEmptyString,
			"allowed_actions":           stringArray,
			"next_gate":                 nonEmptyString,
		},
	}
}

func discussionWriteHandoffInputSchema() map[string]any {
	nonEmptyString := discussionJSONNonEmptyStringSchema()
	roleObject := map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"role", "scope", "evidence_source", "notes"},
		"properties": map[string]any{
			"role":            nonEmptyString,
			"scope":           nonEmptyString,
			"evidence_source": nonEmptyString,
			"notes":           nonEmptyString,
		},
	}
	consumerEntry := map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"status"},
		"properties": map[string]any{
			"status": map[string]any{
				"type":        "string",
				"enum":        []any{"ready", "blocked"},
				"description": "draft/ready validation requires at least one consumer with status ready (eligible is not accepted)",
			},
			"reason": nonEmptyString,
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/discussion-write-handoff-input/v2",
		"type":                 "object",
		"additionalProperties": true,
		"description":          "Discussion handoff control input. Runtime requires a current semantic checkpoint and derives/overwrites state-owned requirement, material, evidence, unknown, conflict, downstream, decision, and digest fields from discussion-state.json. Pass via --input-json (inline, @path, or -). On Windows PowerShell prefer @path or stdin.",
		"required":             []string{"handoff_goal", "consumer_eligibility", "recommended_consumer", "quality_gate"},
		"properties": map[string]any{
			"handoff_goal":               nonEmptyString,
			"agent_requirement_contract": map[string]any{"type": "object", "readOnly": true, "description": "Ignored/overwritten from checkpoint requirements_snapshot."},
			"source_evidence":            map[string]any{"type": "array", "readOnly": true, "description": "Ignored/overwritten from checkpoint; use discussion checkpoint for material_id evidence links."},
			"source_materials":           map[string]any{"type": "array", "readOnly": true, "description": "Ignored/overwritten from checkpoint; runtime protects material_digest."},
			"implementation_target":      map[string]any{"type": "object", "readOnly": true, "description": "Ignored/overwritten from checkpoint."},
			"blocking_unknowns":          map[string]any{"type": "array", "readOnly": true},
			"soft_unknowns":              map[string]any{"type": "array", "readOnly": true},
			"conflicts":                  map[string]any{"type": "array", "readOnly": true},
			"downstream_instructions":    map[string]any{"type": "object", "readOnly": true},
			"discussion_decision_digest": map[string]any{"type": "object", "readOnly": true},
			"must_preserve":              map[string]any{"type": "array", "readOnly": true},
			"context_boundary": map[string]any{
				"type":        "object",
				"readOnly":    true,
				"description": "Ignored/overwritten from checkpoint; validation requires locked boundary in canonical state.",
				"properties": map[string]any{
					"status": map[string]any{"type": "string", "enum": []any{"locked"}, "description": "validation requires locked"},
					"current_project_roles": map[string]any{
						"type":  "array",
						"items": roleObject,
					},
					"target_project_roles": map[string]any{
						"type":  "array",
						"items": roleObject,
					},
					"current_project_root": nonEmptyString,
					"target_project_root":  nonEmptyString,
				},
			},
			"consumer_eligibility": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"sp-specify": consumerEntry,
					"sp-quick":   consumerEntry,
				},
			},
			"recommended_consumer": map[string]any{"type": "string", "enum": []any{"sp-specify", "sp-quick"}},
			"quality_gate": map[string]any{
				"type":     "object",
				"required": []string{"self_reviewed_at"},
				"properties": map[string]any{
					"status": map[string]any{
						"type":        "string",
						"description": "draft validation accepts self_reviewed when self_reviewed_at is set; write-handoff sets status from self_reviewed_at",
					},
					"self_reviewed_at": nonEmptyString,
					"notes":            nonEmptyString,
				},
			},
			"topic_ownership":      discussionTopicOwnershipSchema(),
			"coverage_status":      map[string]any{"type": "string", "readOnly": true, "description": "Derived by runtime from canonical content."},
			"planning_gate_status": map[string]any{"type": "string", "readOnly": true, "description": "Derived by runtime from canonical content."},
			"hard_unknown_count":   map[string]any{"type": "integer", "readOnly": true, "description": "Derived from unresolved blocking_unknowns."},
			"open_conflict_count":  map[string]any{"type": "integer", "readOnly": true, "description": "Derived from unresolved conflicts and conflicts_requiring_return."},
		},
	}
}

func discussionJSONNonEmptyStringSchema() map[string]any {
	return map[string]any{"type": "string", "minLength": 1}
}

func discussionJSONStringArraySchema(minItems int) map[string]any {
	schema := map[string]any{
		"type":  "array",
		"items": discussionJSONNonEmptyStringSchema(),
	}
	if minItems > 0 {
		schema["minItems"] = minItems
	}
	return schema
}

func discussionRequirementsSnapshotSchema(ready bool) map[string]any {
	minItems := 0
	if ready {
		minItems = 1
	}
	array := discussionJSONStringArraySchema(minItems)
	scopeIn := discussionJSONStringArraySchema(minItems)
	stringArray := discussionJSONStringArraySchema(0)
	return map[string]any{
		"type": "object",
		"required": []string{
			"target_need",
			"actors",
			"scenarios",
			"constraints",
			"success_criteria",
			"design_direction",
			"optimal_solution_approach",
			"non_goals",
			"scope",
		},
		"properties": map[string]any{
			"target_need":               discussionJSONNonEmptyStringSchema(),
			"actors":                    array,
			"scenarios":                 array,
			"constraints":               stringArray,
			"success_criteria":          array,
			"design_direction":          stringArray,
			"optimal_solution_approach": array,
			"non_goals":                 stringArray,
			"scope": map[string]any{
				"type":     "object",
				"required": []string{"in", "out", "deferred"},
				"properties": map[string]any{
					"in":       scopeIn,
					"out":      stringArray,
					"deferred": stringArray,
				},
			},
			"source_requirements": map[string]any{"type": "array", "items": discussionSourceRequirementSchema()},
		},
		"additionalProperties": true,
	}
}

func discussionImplementationTargetSchema() map[string]any {
	return map[string]any{
		"type": "object",
		"properties": map[string]any{
			"actual_project":                  map[string]any{"type": []any{"string", "null"}},
			"target_root":                     map[string]any{"type": []any{"string", "null"}},
			"target_paths":                    map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
			"required_target_paths_to_verify": map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
		},
		"additionalProperties": true,
	}
}

func discussionSourceEvidenceSchema() map[string]any {
	nonEmptyString := discussionJSONNonEmptyStringSchema()
	return map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"source_type", "evidence_status", "source", "claim"},
		"properties": map[string]any{
			"source_type":     nonEmptyString,
			"evidence_status": map[string]any{"type": "string", "enum": []any{"verified", "proven", "confirmed", "inferred", "assumption", "stale-advisory", "missing", "conflict"}},
			"source":          nonEmptyString,
			"claim":           nonEmptyString,
			"material_id":     map[string]any{"type": "string", "pattern": "^MAT-[0-9]{3,}$"},
		},
	}
}

func discussionSourceMaterialSchema(includeDigest bool) map[string]any {
	required := []string{"id", "material_type", "locator", "summary", "inspection_status", "claims", "coverage_gaps", "sensitivity"}
	if includeDigest {
		required = append(required, "material_digest")
	}
	properties := map[string]any{
		"id":                map[string]any{"type": "string", "pattern": "^MAT-[0-9]{3,}$"},
		"material_type":     map[string]any{"type": "string", "minLength": 1},
		"locator":           map[string]any{"type": "string", "minLength": 1},
		"summary":           map[string]any{"type": "string", "minLength": 1},
		"inspection_status": map[string]any{"type": "string", "enum": []any{"pending", "inspected", "partial", "unavailable", "stale", "conflict"}},
		"claims":            map[string]any{"type": "array", "items": discussionJSONNonEmptyStringSchema()},
		"coverage_gaps":     map[string]any{"type": "array", "items": map[string]any{"type": "string"}},
		"sensitivity":       map[string]any{"type": "string", "enum": []any{"safe", "sanitized", "restricted"}},
		"content_sha256":    map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"},
		"version_ref":       map[string]any{"type": "string"},
		"material_digest":   map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$", "readOnly": !includeDigest},
		"reading":           map[string]any{"type": "object", "readOnly": true, "description": "Runtime import/read evidence: version, content_sha256, snapshot_ref, source_path, units and delivered_unit_ids. Checkpoint cannot author, alter or delete it."},
		"version_history":   map[string]any{"type": "array", "readOnly": true},
		"unit_dispositions": map[string]any{"type": "array", "items": map[string]any{"type": "object", "required": []string{"unit_id", "requirement_ids", "disposition"}, "properties": map[string]any{"unit_id": discussionJSONNonEmptyStringSchema(), "requirement_ids": discussionJSONStringArraySchema(0), "disposition": map[string]any{"enum": []any{"requirements", "context"}}, "reason": discussionJSONNonEmptyStringSchema()}}},
	}
	return map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             required,
		"properties":           properties,
	}
}

func discussionDownstreamInstructionsSchema(requireAll bool) map[string]any {
	fields := []string{"settled_decisions", "preserved_assumptions", "conflicts_requiring_return", "capability_map", "dependencies", "planning_constraints", "deferred_scope", "reopen_conditions"}
	required := []string{}
	if requireAll {
		required = fields
	}
	properties := map[string]any{}
	for _, field := range fields {
		properties[field] = map[string]any{"type": "array"}
	}
	return map[string]any{"type": "object", "required": required, "properties": properties, "additionalProperties": false}
}

func discussionMustPreserveSchema() map[string]any {
	nonEmptyString := discussionJSONNonEmptyStringSchema()
	return map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"id", "type", "claim", "source", "downstream_requirement", "blocking_level", "owner", "latest_resolve_phase", "status"},
		"properties": map[string]any{
			"id":                     nonEmptyString,
			"type":                   nonEmptyString,
			"claim":                  nonEmptyString,
			"source":                 nonEmptyString,
			"downstream_requirement": nonEmptyString,
			"blocking_level":         nonEmptyString,
			"owner":                  nonEmptyString,
			"latest_resolve_phase":   nonEmptyString,
			"status":                 nonEmptyString,
		},
	}
}

func discussionTopicOwnershipSchema() map[string]any {
	nonEmptyString := discussionJSONNonEmptyStringSchema()
	routedTopic := map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"topic", "route"},
		"properties": map[string]any{
			"topic":         nonEmptyString,
			"route":         map[string]any{"type": "string", "enum": []any{"continue_current", "branch_new", "link_existing", "defer"}},
			"target_slug":   map[string]any{"type": []any{"string", "null"}, "minLength": 1},
			"source_digest": map[string]any{"type": []any{"string", "null"}},
		},
		"allOf": []any{
			map[string]any{
				"if": map[string]any{
					"properties": map[string]any{
						"route": map[string]any{"enum": []any{"branch_new", "link_existing"}},
					},
				},
				"then": map[string]any{
					"required": []string{"target_slug"},
					"properties": map[string]any{
						"target_slug": map[string]any{"type": "string", "minLength": 1},
					},
				},
			},
		},
	}
	return map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"owned_scope", "routed_topics"},
		"properties": map[string]any{
			"owner_slug": nonEmptyString,
			"anchor":     nonEmptyString,
			"owned_scope": map[string]any{
				"type":     "array",
				"minItems": 1,
				"items":    nonEmptyString,
			},
			"routed_topics": map[string]any{
				"type":  "array",
				"items": routedTopic,
			},
		},
	}
}

func workflowBlockInputSchema() map[string]any {
	nonEmptyString := func() map[string]any {
		return map[string]any{"type": "string", "minLength": 1}
	}
	nonEmptyStringArray := func() map[string]any {
		return map[string]any{
			"type":     "array",
			"minItems": 1,
			"items":    nonEmptyString(),
		}
	}
	recoveryAttempt := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"action", "result"},
		"properties": map[string]any{
			"action": nonEmptyString(),
			"result": nonEmptyString(),
		},
	}
	humanStep := map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"required":             []string{"order", "title", "action", "expected_result", "if_failed"},
		"properties": map[string]any{
			"order":           map[string]any{"type": "integer", "minimum": 1},
			"title":           nonEmptyString(),
			"action":          nonEmptyString(),
			"command":         map[string]any{"type": []string{"string", "null"}},
			"expected_result": nonEmptyString(),
			"if_failed":       nonEmptyString(),
		},
	}
	humanAction := map[string]any{
		"type":                 []string{"object", "null"},
		"additionalProperties": false,
		"properties": map[string]any{
			"goal":               nonEmptyString(),
			"why_human":          nonEmptyString(),
			"prerequisites":      nonEmptyStringArray(),
			"safety_notes":       nonEmptyStringArray(),
			"steps":              map[string]any{"type": "array", "minItems": 1, "items": humanStep},
			"verification":       nonEmptyStringArray(),
			"evidence_to_return": nonEmptyStringArray(),
		},
	}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/workflow-block-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required": []string{
			"feature_dir",
			"expected_revision",
			"category",
			"owner",
			"cause",
			"evidence",
			"attempted_recovery",
			"affected_scope",
			"exact_next_action",
			"unblock_criteria",
		},
		"properties": map[string]any{
			"feature_dir":       nonEmptyString(),
			"expected_revision": map[string]any{"type": "integer", "minimum": 0},
			"category": map[string]any{"enum": []string{
				"workflow-validation",
				"artifact-or-state",
				"technical-failure",
				"dependency-or-service",
				"delegation",
				"project-cognition",
				"credentials-or-permission",
				"external-system",
				"external-write-authorization",
				"human-decision",
				"human-review",
				"timeout",
				"conflict-or-drift",
			}},
			"owner": map[string]any{"enum": []string{
				"agent",
				"user",
				"maintainer",
				"external-system",
			}},
			"cause":                 nonEmptyString(),
			"evidence":              nonEmptyStringArray(),
			"attempted_recovery":    map[string]any{"type": "array", "items": recoveryAttempt},
			"affected_scope":        nonEmptyStringArray(),
			"exact_next_action":     nonEmptyString(),
			"unblock_criteria":      nonEmptyString(),
			"human_action":          humanAction,
			"human_action_required": map[string]any{"type": []string{"boolean", "null"}},
		},
		"allOf": []any{
			map[string]any{
				"if": map[string]any{
					"properties": map[string]any{"human_action_required": map[string]any{"const": false}},
					"required":   []string{"human_action_required"},
				},
				"then": map[string]any{
					"properties": map[string]any{"human_action": map[string]any{"type": "null"}},
				},
			},
			map[string]any{
				"if": map[string]any{
					"properties": map[string]any{"owner": map[string]any{"enum": []string{"user", "maintainer"}}},
					"required":   []string{"owner"},
				},
				"then": map[string]any{
					"properties": map[string]any{"human_action_required": map[string]any{"enum": []any{true, nil}}},
				},
			},
		},
	}
}

func workflowReconcileBlockerInputSchema() map[string]any {
	nonEmpty := map[string]any{"type": "string", "minLength": 1}
	nonEmptyList := map[string]any{"type": "array", "minItems": 1, "uniqueItems": true, "items": nonEmpty}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/workflow-reconcile-blocker-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"required": []string{
			"feature_dir", "expected_revision", "resolved_subcauses", "remaining_cause",
			"remaining_evidence", "remaining_scope", "exact_next_action", "unblock_criteria",
		},
		"properties": map[string]any{
			"feature_dir":        nonEmpty,
			"expected_revision":  map[string]any{"type": "integer", "minimum": 1},
			"resolved_subcauses": nonEmptyList,
			"remaining_cause":    nonEmpty,
			"remaining_evidence": nonEmptyList,
			"remaining_scope":    nonEmptyList,
			"exact_next_action":  nonEmpty,
			"unblock_criteria":   nonEmpty,
		},
	}
}
