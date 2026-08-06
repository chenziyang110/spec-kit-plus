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
	case "workflow-block-input":
		schema = workflowBlockInputSchema()
		capabilityID = "workflow.block"
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
	case "discussion-write-handoff-input":
		schema = discussionWriteHandoffInputSchema()
		capabilityID = "discussion.write-handoff"
	case "implement-result-merge-input":
		schema = implementResultMergeInputSchema()
		capabilityID = "implement.result-merge"
	default:
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown schema %q", schemaID)))
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
		"id":      capabilityID,
		"summary": capabilitySummary(capabilityID),
		"command": command,
	}
	env = NewEnvelope("ok", fmt.Sprintf("Capability %s expanded.", capabilityID))
	switch capabilityID {
	case "workflow.block":
		capability["summary"] = "Record a resumable blocker and novice human action guide."
		capability["input_schema"] = "workflow-block-input"
		capability["side_effect"] = "writes-workflow"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "workflow-block-input", "--format", "json"}
	case "artifact.scaffold":
		capability["input_schema"] = "artifact-scaffold-input"
		capability["side_effect"] = "creates-artifact"
		capability["usage"] = "specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> --vars <json> --format json"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-scaffold-input", "--format", "json"}
		env.NextArgv = []string{"specify-runtime", "artifact", "catalog", "--format", "json"}
	case "artifact.checklist":
		capability["input_schema"] = "artifact-checklist-input"
		capability["side_effect"] = "creates-or-appends-artifact"
		capability["usage"] = "specify-runtime artifact checklist --path <feature-dir>/checklists/<name>.md --input-json <object> --format json"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-checklist-input", "--format", "json"}
	case "artifact.patch":
		capability["input_schema"] = "artifact-patch-input"
		capability["side_effect"] = "patches-artifact"
		capability["usage"] = "specify-runtime artifact patch --lease <id> (--json-pointer <pointer> --value-json <json> | --section <heading> --content <text> | --frontmatter-json <object> | --heading <current> --new-heading <replacement> | --preamble <text> | --append-json <json>)"
		capability["input_contract"] = "--section accepts bare heading text or markdown markers (\"Source Design System\" or \"## Source Design System\"); for Windows path content prefer forward slashes or raw strings so \\a is not treated as a bell escape"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "artifact-patch-input", "--format", "json"}
	case "artifact.submit":
		capability["side_effect"] = "writes-artifact"
		capability["usage"] = "specify-runtime artifact submit --lease <id> --content <inline-payload> --format json"
		capability["file_input"] = "recovery-only: --recovery-file accepts only the runtime-created human acceptance repair backup bound by its sibling journal"
	case "evidence.register":
		capability["side_effect"] = "writes-content-addressed-evidence"
		capability["usage"] = "specify-runtime evidence register (--content <inline-payload> | --object <existing-object-ref>) --scope <scope> [metadata options]"
		capability["input_contract"] = "exactly one of --content or --object; --object must reference an existing .specify/evidence/objects/sha256 object"
	case "evidence.import":
		capability["side_effect"] = "imports-content-addressed-evidence"
		capability["usage"] = "specify-runtime evidence import --file <external-local-path> --scope <scope> [metadata options]"
		capability["file_input"] = "external evidence only; agent-authored structured evidence uses evidence register --content"
	case "hook.extension-plan":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime hook extension-plan --event <event-id> --format json"
		capability["input_contract"] = "the runtime reads and filters .specify/extensions.yml; agents consume only returned actionable hook items"
	case "discussion.bind-consumer":
		capability["side_effect"] = "writes-derived-consumer-handoff"
		capability["usage"] = "specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --input-json <transition-fields> --format json"
		capability["input_contract"] = "semantic_delta, required_refs, blockers, and recovery only via --input-json (inline, @path, or -); runtime binds source contract, review digest, status, and next action; unbound create-feature scaffolds may receive first bind"
	case "discussion.checkpoint":
		capability["side_effect"] = "writes-discussion-state-and-log"
		capability["usage"] = "specify-runtime discussion checkpoint <slug> --input-json <object|@path|-> [--summary <text>] [--phase <phase>] [--user-goal <text>] --format json"
		capability["input_schema"] = "discussion-checkpoint-input"
		capability["input_contract"] = "persists turn_packet semantic fields (user_goal, context_boundary, confirmed_decisions, open_questions, current_recommendation, ...); unknown fields are rejected; --input-json accepts inline, @path, or - (PowerShell should prefer @path/stdin)"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "discussion-checkpoint-input", "--format", "json"}
	case "discussion.write-handoff":
		capability["side_effect"] = "writes-discussion-handoff"
		capability["usage"] = "specify-runtime discussion write-handoff <slug> --input-json <object|@path|-> --format json"
		capability["input_schema"] = "discussion-write-handoff-input"
		capability["input_contract"] = "semantic draft merged into the installed handoff template; roles/evidence/must_preserve are object lists; consumer status ready (not eligible); quality_gate needs self_reviewed_at; --input-json accepts inline, @path, or -"
		env.ShowArgv = []string{"specify-runtime", "api", "schema", "discussion-write-handoff-input", "--format", "json"}
	case "validate.spec":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime validate spec --feature-dir <feature-dir> [--tier light|standard|deep] [--show-passes] --format json"
		capability["input_contract"] = "--feature-dir preferred; --dir is a compatibility alias; conflicting values are rejected; transition.next_action accepts \"/sp.plan\" or {\"command\":\"/sp.plan\"}; change-propagation requires a markdown pipe table"
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
	case "run.create":
		capability["side_effect"] = "writes-run-control"
		capability["usage"] = "specify-runtime run create --run-id <id> --kind <kind> --subject-type <type> --subject-id <id> --target-ref <ref> --intent-sha256 <sha256> [--project-root <path>] --format json"
		capability["input_contract"] = "records control-plane intent only; it does not allocate a workspace or launch an agent"
	case "run.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime run show <run-id> [--project-root <path>] --format json"
	case "run.events":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime run events <run-id> [--project-root <path>] --format json"
	case "run.cancel":
		capability["side_effect"] = "cancels-and-fences-run"
		capability["usage"] = "specify-runtime run cancel <run-id> --expected-revision <revision> --reason <reason> [--project-root <path>] --format json"
		capability["input_contract"] = "requires the exact observed Run revision; cancellation advances the fence before revoking execution authority"
	case "run.launch":
		capability["side_effect"] = "queues-run-routes-workspace-and-runs-tokenized-child"
		capability["usage"] = "specify-runtime run launch --run-id <id> --kind <kind> --subject-type <type> --subject-id <id> --target-ref <ref> --intent-sha256 <sha256> --adapter-id <id> [--workspace-policy auto|primary|isolated] [--project-root <path>] --format json -- <argv...>"
		capability["input_contract"] = "single call queues durable Run intent and requires a literal -- separator; auto routes exactly one non-overlapping modifying Run to the primary workspace only when its checkout is pristine, routes overlaps and idle-but-dirty launches to isolated worktrees, clones overlaps from the primary Run's pre-launch Snapshot, forces child cwd, binds the fenced SPECIFY_RUN_* environment, and atomically records success or failure; interrupted Runs remain recoverable through run supervise"
	case "run.supervise":
		capability["side_effect"] = "routes-workspace-and-runs-tokenized-child"
		capability["usage"] = "specify-runtime run supervise <run-id> --adapter-id <id> [--workspace-policy auto|primary|isolated] [--project-root <path>] --format json -- <argv...>"
		capability["input_contract"] = "requires a literal -- separator and --adapter-id; runtime owns auto routing between one pristine primary workspace owner and isolated overlap or idle-but-dirty worktrees, forces child cwd, binds SPECIFY_RUN_* identity/workspace/fence variables, extends WSLENV for WSL-backed helpers, maintains liveness, releases ownership on every terminal path, and atomically records success or failure. Greenfield/local interactive agents may use create-new-feature + workflow enter + artifact owners without supervise when no host adapter is configured; that path is not a run-control violation for unhosted sessions"
	case "result.list":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime result list [<run-id> | --run-id <id>] [--project-root <path>] --format json"
		capability["input_contract"] = "returns append-only result history for one Run from sealed Result records without mutating execution state"
	case "result.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime result show [<result-id> | --result-id <id>] [--project-root <path>] --format json"
		capability["input_contract"] = "loads one immutable sealed result, its derived identity bindings, and current supersession metadata"
	case "result.reopen":
		capability["side_effect"] = "reopens-sealed-run"
		capability["usage"] = "specify-runtime result reopen <run-id> (--basis-result <result-id> | --basis-result-id <result-id>) --expected-revision <revision> --reason <reason> [--project-root <path>] --format json"
		capability["input_contract"] = "reopens a sealed Run only from its latest sealed Result basis and records deterministic supersession history"
	case "result.depend":
		capability["side_effect"] = "writes-result-dependency"
		capability["usage"] = "specify-runtime result depend <result-id> (--on <result-id> | --upstream-result-id <result-id>) --kind requires|after|conflicts_with --reason <reason> [--project-root <path>] --format json"
		capability["input_contract"] = "records one Result dependency edge in the immutable result graph; runtime validates the dependency kind"
	case "candidate.build":
		capability["side_effect"] = "builds-frozen-candidate"
		capability["usage"] = "specify-runtime candidate build --target-ref <ref> (--result <result-id> | --result-id <result-id>)... [--project-root <path>] --format json"
		capability["input_contract"] = "builds one frozen candidate from multiple results for a single target ref; runtime resolves Result ordering, dependency closure, and immutable candidate bindings"
	case "candidate.show":
		capability["side_effect"] = "read-only"
		capability["usage"] = "specify-runtime candidate show <candidate-id> [--candidate-id <id>] [--project-root <path>] --format json"
		capability["input_contract"] = "loads one immutable candidate, its member Results, manifest digest, hidden ref, and latest Review, Acceptance, Publication, and Sync delivery receipts without mutation"
	case "candidate.review":
		capability["side_effect"] = "writes-candidate-review"
		capability["usage"] = "specify-runtime candidate review <candidate-id> --reviewer <id> [--project-root <path>] --format json -- <literal argv>"
		capability["input_contract"] = "requires at least one literal argv after --; runtime materializes the frozen Candidate review workspace, executes the literal argv, and binds the resulting evidence digest to that exact candidate"
	case "accept.receipt":
		capability["side_effect"] = "writes-candidate-acceptance"
		capability["usage"] = "specify-runtime accept receipt [<candidate-id> | --candidate-id <id>] [(--review-digest <sha256> --decision accepted|rejected --actor <id>) | --input-json <object>] [--project-root <path>] --format json"
		capability["input_contract"] = "records the explicit accept receipt for one frozen Candidate against the latest passing Review digest; runtime binds the human acceptance receipt"
	case "cas.publish":
		capability["side_effect"] = "publishes-accepted-candidate"
		capability["usage"] = "specify-runtime cas publish <candidate-id> --acceptance-digest <sha256> --expected-sha256 <sha256> [--project-root <path>] --format json"
		capability["input_contract"] = "publishes one accepted frozen Candidate under cas protection; runtime verifies the exact acceptance digest, excludes an active primary-workspace owner, and resumes a durable publication journal by observing the protected target ref"
	case "sync.safe":
		capability["side_effect"] = "safe-syncs-primary-worktree"
		capability["usage"] = "specify-runtime sync safe <candidate-id> --publication-digest <sha256> --target-ref <ref> [--project-root <path>] --format json"
		capability["input_contract"] = "performs a separate safe sync only after a successful publication receipt; runtime excludes an active primary-workspace owner, verifies the published Candidate digest and protected worktree state, and can finish a reset whose receipt write was interrupted"
	}
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
			"lease":             nonEmptyString,
			"json_pointer":      nonEmptyString,
			"value":             map[string]any{},
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
			map[string]any{"required": []string{"section", "content"}},
			map[string]any{"required": []string{"frontmatter_patch"}},
			map[string]any{"required": []string{"heading", "new_heading"}},
			map[string]any{"required": []string{"preamble"}},
			map[string]any{"required": []string{"append_value"}},
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
				"task_id":        "T001",
				"status":         "success",
				"changed_files":  []any{"backend/cmd/api/main.go"},
				"validation_results": []any{
					map[string]any{"command": "go test ./...", "status": "passed", "summary": "ok"},
				},
				"blockers": []any{},
			},
		},
	}
}

func discussionCheckpointInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
	stringArray := map[string]any{"type": "array", "items": map[string]any{"type": "string"}}
	return map[string]any{
		"$schema":              "https://json-schema.org/draft/2020-12/schema",
		"$id":                  "specify://schemas/discussion-checkpoint-input/v1",
		"type":                 "object",
		"additionalProperties": false,
		"description":          "Semantic checkpoint payload for specify-runtime discussion checkpoint. Unknown fields are rejected. Pass via --input-json (inline, @path, or -).",
		"properties": map[string]any{
			"summary":                 nonEmptyString,
			"lifecycle_phase":         map[string]any{"type": "string", "enum": []any{"explore", "ground", "decide", "prepare", "review"}},
			"phase":                   map[string]any{"type": "string", "description": "Alias for lifecycle_phase"},
			"user_goal":               nonEmptyString,
			"turn_class":              nonEmptyString,
			"current_decision_frame":  nonEmptyString,
			"confirmed_decisions":     stringArray,
			"changed_recommendations": stringArray,
			"context_boundary":        map[string]any{"type": "object"},
			"verified_fact_refs":      map[string]any{"type": "array"},
			"open_assumptions":        map[string]any{"type": "array"},
			"open_questions":          map[string]any{"type": "array"},
			"current_recommendation":  nonEmptyString,
			"allowed_actions":         stringArray,
			"next_gate":               nonEmptyString,
		},
	}
}

func discussionWriteHandoffInputSchema() map[string]any {
	nonEmptyString := map[string]any{"type": "string", "minLength": 1}
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
	evidenceObject := map[string]any{
		"type":                 "object",
		"additionalProperties": true,
		"required":             []string{"source_type", "evidence_status", "source", "claim"},
		"properties": map[string]any{
			"source_type":     nonEmptyString,
			"evidence_status": nonEmptyString,
			"source":          nonEmptyString,
			"claim":           nonEmptyString,
		},
	}
	mustPreserveObject := map[string]any{
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
		"$id":                  "specify://schemas/discussion-write-handoff-input/v1",
		"type":                 "object",
		"additionalProperties": true,
		"description":          "Semantic draft merged into discussion-handoff-template.json. Runtime owns version/status/digest defaults. Pass via --input-json (inline, @path, or -). On Windows PowerShell prefer @path or stdin.",
		"required":             []string{"handoff_goal"},
		"properties": map[string]any{
			"handoff_goal": nonEmptyString,
			"agent_requirement_contract": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"target_need":               nonEmptyString,
					"constraints":               map[string]any{"type": "array"},
					"success_criteria":          map[string]any{"type": "array"},
					"design_direction":          map[string]any{"type": "array"},
					"optimal_solution_approach": map[string]any{"type": "array"},
					"scope": map[string]any{
						"type": "object",
						"properties": map[string]any{
							"in":       map[string]any{"type": "array"},
							"out":      map[string]any{"type": "array"},
							"deferred": map[string]any{"type": "array"},
						},
					},
				},
			},
			"context_boundary": map[string]any{
				"type": "object",
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
			"source_evidence": map[string]any{"type": "array", "items": evidenceObject},
			"must_preserve":   map[string]any{"type": "array", "minItems": 1, "items": mustPreserveObject},
			"consumer_eligibility": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"sp-specify": consumerEntry,
					"sp-quick":   consumerEntry,
				},
			},
			"recommended_consumer": map[string]any{"type": "string", "enum": []any{"sp-specify", "sp-quick"}},
			"quality_gate": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"status": map[string]any{
						"type":        "string",
						"description": "draft validation accepts self_reviewed when self_reviewed_at is set; write-handoff sets status from self_reviewed_at",
					},
					"self_reviewed_at": nonEmptyString,
					"notes":            nonEmptyString,
				},
			},
			"downstream_instructions": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"settled_decisions":         map[string]any{"type": "array"},
					"preserved_assumptions":     map[string]any{"type": "array"},
					"conflicts_requiring_return": map[string]any{"type": "array"},
					"capability_map":            map[string]any{"type": "array"},
					"dependencies":              map[string]any{"type": "array"},
					"planning_constraints":      map[string]any{"type": "array"},
					"deferred_scope":            map[string]any{"type": "array"},
					"reopen_conditions":         map[string]any{"type": "array"},
				},
			},
			"discussion_decision_digest": map[string]any{"type": "object"},
			"implementation_target":      map[string]any{"type": "object"},
			"blocking_unknowns":          map[string]any{"type": "array"},
			"soft_unknowns":              map[string]any{"type": "array"},
			"coverage_status":            map[string]any{"type": "string", "enum": []any{"complete"}},
			"planning_gate_status":       map[string]any{"type": "string", "enum": []any{"ready"}},
			"hard_unknown_count":         map[string]any{"type": "integer", "const": 0},
			"open_conflict_count":        map[string]any{"type": "integer", "const": 0},
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
