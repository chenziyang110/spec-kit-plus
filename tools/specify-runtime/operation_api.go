package main

// Operation commands are a separate state protocol. They deliberately do not
// inherit feature-workflow stage transitions or a shell execution facade.
type operationAPIContract struct {
	usage      string
	sideEffect string
	schema     string
	input      string
}

var operationAPIContracts = map[string]operationAPIContract{
	"learning.applicability.v1":        {usage: "specify-runtime learning start|list|show [--context component=<source-directory>] [--context constraint_file=<source-path>] [--context counterevidence_file=<current-evidence-path>] --format json", sideEffect: "read-only", schema: "learning-applicability-input", input: "Versioned applicability over existing Learning owners; this capability is not a new subcommand. Capture/capture-auto optionally bind --component, repeated --source-file and --constraint-file, --evidence-kind failure|recovery|correction|constraint, and optional --counterevidence-file. The runtime derives source hashes and sizes. Source files must lie inside the declared component; references must be safe project-relative current files. Reads require the exact live component context, preserve missing legacy bindings as degraded, and reject wrong components, changed source/constraints, counterevidence and catalog lifecycle conflicts. Facet rank and recurrence never override rejection. Start/list/show do not confirm or promote; promotion remains explicit. Byte bindings establish consistency, not author identity, observed recovery, semantic truth or task benefit."},
	"cognition.scope-availability.v2":  {usage: "specify-runtime cognition check|status|doctor --task-packet <project-relative-current-packet> [--availability-json <previous-binding>] --format json", sideEffect: "read-only", schema: "cognition-scope-availability-input", input: "Contract version 2 binds the complete fixed-point owner/dependency/current evidence proof for both task and debt, including every live byte relied on for disjointness. Version 1 bindings must be discarded and reassessed. Derive exact canonical native read_scope/write_scope or Python PacketScope from current packet bytes; Quick packets without explicit typed read dependencies remain degraded. Retain global debt and require current source/evidence hashes, complete typed closure and lifecycle summaries, navigation snapshot and status. This is advisory consistency, never source truth, write authority, workflow claim_ready, Review or human Accept."},
	"cognition.closeout.binding.begin": {usage: "specify-runtime cognition closeout binding begin --workflow <sp-*> --scope-dir <exact> --input-json <object|-> --format json", sideEffect: "writes-runtime-source-binding", schema: "cognition-closeout-binding-begin-input", input: "Use an existing native Work id. Runtime derives its current fence/task/attempt, confirmed product scope, actual owned delta and canonical accepted outputs. Capture before fresh verification; supplied mechanical hashes/accepted-output lists are refused."},
	"cognition.closeout.binding.seal":  {usage: "specify-runtime cognition closeout binding seal --workflow <sp-*> --scope-dir <exact> --input-json <object|-> --format json", sideEffect: "writes-immutable-observation-binding", schema: "cognition-closeout-binding-seal-input", input: "Use exact generated binding_id and fresh validation observations with started_at/finished_at; source/dependency/accepted output changes refuse sealing. Runtime records observations, not tool execution or semantic truth."},
	"cognition.closeout.binding.check": {usage: "specify-runtime cognition closeout binding check --workflow <sp-*> --scope-dir <exact> --input-json <object|-> --format json", sideEffect: "read-only", input: "Use only exact binding_id. Check current native owner, source bytes, dependency bytes, accepted-output versions and transitive parent proofs; stale affected descendants are refused without deleting unaffected evidence."},
	"do.scoped-recovery.v1":            {usage: "specify-runtime do resume <session-id> --input-json <object|-> --format json", sideEffect: "capability-marker", schema: "do-resume-input", input: "Versions public-script source binding, exact audited external_changes, and transitive verified epoch retention over the existing do and playbook owners; no separate command."},
	"do.prepare":                       {usage: "specify-runtime do prepare --input-json <object|-> [--project-root <path>] --format json", sideEffect: "read-only", schema: "do-prepare-input", input: "For first use of an existing project script, supply command:{operation,argv,checks} plus goal, identity and scopes; cwd defaults to '.'. Runtime derives method boilerplate and binds the script, without executing it. Explicit verification checks remain required. Otherwise resolve a bound method and parameters. Return canonical start_input without creating Work or session state; start rechecks facts. Input failures include field diagnostics and schema_argv; correct all independent mistakes together. Save reusable methods only after verified execution."},
	"do.next":                          {usage: "specify-runtime do next <session-id> [--project-root <path>] --format json", sideEffect: "read-only", input: "Return ready frozen tool actions, started_input and completion fact requirements. Recheck dependencies before returning a packet; record started before the real tool call. Each packet revision is optimistic and may require refreshing."},
	"do.complete":                      {usage: "specify-runtime do complete <session-id> --input-json <object|-> [--project-root <path>] --format json", sideEffect: "writes-verified-session-method-and-work-closeout", schema: "do-complete-input", input: "Use expected_revision and truthful change_summary. Reuse existing finish and playbook owners to validate, persist the exact method template and usage receipt, then close knowledge. A knowledge failure leaves passed execution pending for retry without rerunning tools; replay never adds a success sample."},
	"playbook.metrics":                 {usage: "specify-runtime playbook metrics --id <playbook-id> [--context-json <object>] [--parameters-json <object>] [--project-root <path>] --format json", sideEffect: "read-only", schema: "playbook-metrics-input", input: "Project actual sessions, including failed/interrupted attempts, into bound task/instance/environment/verification/source groups. Report scan cost, missing data and noncomparable history. Tool durations are not agent end-to-end performance."},
	"do.start": {
		usage:      "specify-runtime do start --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "creates-do-session-and-work-ownership", schema: "do-start-input",
		input: "Freeze the exact ordered definition, required checks, source/output/write scopes and optional method revision before native execution. Reusing an explicit session_id with identical inputs returns the same session. Runtime records and validates observations; it never executes the operation.",
	},
	"do.record": {
		usage:      "specify-runtime do record <session-id> --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-do-session-and-evidence", schema: "do-record-input",
		input: "Use expected_revision and request_id. Record started before invoking a native tool; checkpoint terminal observations with exact step/attempt ids, argv, cwd, tool identity and observed results. An interrupted or unknown attempt requires explicit observation before retry.",
	},
	"do.validate": {
		usage:      "specify-runtime do validate <session-id> [--project-root <path>] --format json",
		sideEffect: "read-only",
		input:      "Revalidate frozen required steps/checks, current source/output hashes and source-mutation closeout. Successful agent-tool observations are not represented as independent runtime execution proof.",
	},
	"do.finish": {
		usage:      "specify-runtime do finish <session-id> --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-do-session-and-work-closeout", schema: "do-finish-input",
		input: "Use expected_revision; identical state/receipt replay is idempotent. Runtime derives execution_outcome separately from knowledge_status. Persist an already verified method through playbook.update, then close knowledge without rerunning the completed operation.",
	},
	"do.resume": {
		usage:      "specify-runtime do resume <session-id> [--input-json <object|->] [--project-root <path>] --format json",
		sideEffect: "read-only-without-input-otherwise-writes-do-recovery", schema: "do-resume-input",
		input: "Read-only without input. Failed/interrupted effects require exact typed recovery evidence. Replan defaults to genuine failed attempt; mode unstarted changes only unattempted actions without fabricating recovery. external_changes records evidence-backed exact unrelated paths without claiming their ownership or excluding operation inputs. retain_verified retains original eligible process results through a verified immutable epoch chain after source/output/dependency rechecks; required closure and exact checks cannot weaken. All other actions rerun. Native/source/external effects never carry. Exact replay is idempotent.",
	},
	"do.show": {
		usage:      "specify-runtime do show (<session-id> [--section <method|definition|definitions|definition:epoch|attempts|attempt:id|metrics>]|--active [--adapter-id <adapter-id>]) [--project-root <path>] --format json",
		sideEffect: "read-only",
		input:      "Read a compact explicit session, expanding only a selected definition or attempt section. --active resolves live Work Board bindings, optionally within an explicit adapter identity, and returns an ambiguity blocker for multiple sessions; it never chooses the newest directory.",
	},
	"playbook.find": {
		usage:      "specify-runtime playbook find [--query <text>] [--operation <operation>] [--target <target>] [--context-json <object>] [--parameters-json <object>] [--rank relevance|observed] [--limit <1..20>] [--cursor <n>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-find-input",
		input: "Return bounded method cards, aliases and applicability/drift status. Use operation/target flags and explicit context for applicability filtering; expand only selected candidates. The schema documents the query fields, which are passed using the documented flags.",
	},
	"playbook.show": {
		usage:      "specify-runtime playbook show --id <playbook-id> [--section <summary|steps|checks|evidence|recovery|all>] [--revision <n>|--proposal-digest <sha256>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-show-input",
		input: "Expand selected ordered sections from one method with revision, digest and source drift. A historic success does not satisfy the current DoSession's validation obligations.",
	},
	"playbook.update": {
		usage:      "specify-runtime playbook update --input-json <object|-> [--project-root <path>] --format json",
		sideEffect: "writes-playbook-revision-or-proposal", schema: "playbook-update-input",
		input: "Compare-and-swap base_digest; bind the exact definition digest and previous method revision to a passed DoSession. Unverified behavior remains a proposal. Repeated unchanged success records bounded usage without creating another content revision.",
	},
	"playbook.validate": {
		usage:      "specify-runtime playbook validate (--id <playbook-id>|--input-json <definition|->) [--context-json <object>] [--project-root <path>] --format json",
		sideEffect: "read-only", schema: "playbook-validate-input",
		input: "Validate structural integrity and current applicability/source fingerprints without silently repairing the method or blessing it for native execution.",
	},
}

func applyOperationAPIContract(id string, capability map[string]any, env *Envelope) {
	contract, ok := operationAPIContracts[id]
	if !ok {
		return
	}
	capability["usage"] = contract.usage
	if id == "learning.applicability.v1" {
		capability["command"] = []string{"specify-runtime", "learning", "start"}
		capability["output_contract"] = "Consume applicability.version=learning-applicability.v1, state, applicable and reason_codes consistently across start/list/show and candidate notes. Only applicable=true with current live component/source/constraint checks permits considering reuse; graph freshness is separate. Legacy/context-missing records degrade. Rejected records never produce positive promotion readiness; confirmation notes retain rejected state/reasons. Reads preserve lifecycle bytes and modification times. Genuine reusable signals and independent task verification are still required."
	}
	if id == "cognition.scope-availability.v2" {
		capability["command"] = []string{"specify-runtime", "cognition", "check"}
		capability["output_contract"] = "Inspect scope_ready/availability and binding contract_version=2. proof_paths binds all live sources used for task or disjoint-debt proofs; every byte is reread before a ready response. Global freshness/debt remain in global_status; no check writes them fresh. Old v1 bindings are incompatible; source/proof/dependency/claim/navigation/status drift rejects reuse. Hashes prove current consistency only and never semantic truth. Unknown or incomplete proof remains conservative with live evidence fallback."
	}
	capability["side_effect"] = contract.sideEffect
	capability["input_contract"] = contract.input
	if contract.schema != "" {
		capability["input_schema"] = contract.schema
		env.ShowArgv = []string{"specify-runtime", "api", "schema", contract.schema, "--format", "json"}
	}
}

// This describes capture flags, not a JSON submission endpoint or lifecycle write.
func learningApplicabilityInputSchema() map[string]any {
	paths := func(required bool) map[string]any {
		result := map[string]any{"type": "array", "maxItems": 32, "uniqueItems": true, "items": map[string]any{"type": "string", "minLength": 1}}
		if required {
			result["minItems"] = 1
		}
		return result
	}
	return map[string]any{
		"type": "object", "additionalProperties": false,
		"description": "Explicit applicability inputs mapped to existing Learning capture/capture-auto flags. This is not a JSON submission endpoint; the runtime derives source hashes and byte sizes. start/list/show take the corresponding exact --context component/constraint_file/counterevidence_file values and remain read-only.",
		"required":    []string{"component", "sources", "constraints", "evidence_kind"},
		"properties": map[string]any{
			"component":       map[string]any{"type": "string", "minLength": 1, "description": "--component: project-relative existing source directory"},
			"sources":         paths(true),
			"constraints":     paths(true),
			"counterevidence": paths(false),
			"evidence_kind":   map[string]any{"enum": []string{"failure", "recovery", "correction", "constraint"}},
		},
	}
}

func scopeAvailabilityInputSchema() map[string]any {
	return map[string]any{"type": "object", "additionalProperties": false, "required": []string{"task_packet"}, "properties": map[string]any{
		"task_packet": map[string]any{"type": "string", "minLength": 1, "description": "Pass via --task-packet: exact project-relative current compiled native or Python task packet; no glob, private storage or traversal."},
		"availability_binding": map[string]any{"type": "object", "additionalProperties": false, "required": []string{"contract_version", "project_root", "task_packet_path", "task_packet_sha256", "source_digest", "navigation_snapshot", "status_digest"}, "description": "Optional exact previous binding, passed inline with --availability-json; old contracts or changed source/packet/status/graph bytes refuse reuse.", "properties": map[string]any{
			"contract_version": map[string]any{"const": 2}, "project_root": map[string]any{"type": "string"}, "task_packet_path": map[string]any{"type": "string"}, "task_packet_sha256": map[string]any{"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "source_digest": map[string]any{"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "status_digest": map[string]any{"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "navigation_snapshot": map[string]any{"type": "object", "required": []string{"generation_id", "digest"}, "properties": map[string]any{"generation_id": map[string]any{"type": "string"}, "digest": map[string]any{"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}}},
		}},
	}}
}
