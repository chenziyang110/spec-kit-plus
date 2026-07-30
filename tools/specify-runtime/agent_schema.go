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
		capability["input_contract"] = "inline semantic_delta, required_refs, blockers, and recovery only; runtime binds source contract, review digest, status, and next action"
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
			"section":           nonEmptyString,
			"content":           map[string]any{"type": "string"},
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
