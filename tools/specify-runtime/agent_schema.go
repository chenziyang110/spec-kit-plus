package main

import (
	"fmt"
	"io"
)

func runAPISchema(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing schema id"))
	}
	schemaID := args[0]
	if schemaID != "workflow-block-input" {
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown schema %q", schemaID)))
	}
	env := NewEnvelope("ok", fmt.Sprintf("Schema %s expanded.", schemaID))
	env.Data["schema_id"] = schemaID
	env.Data["schema_version"] = 1
	env.Data["schema"] = workflowBlockInputSchema()
	env.ShowArgv = []string{"specify-runtime", "api", "show", "workflow.block", "--format", "json"}
	return writeEnvelope(stdout, env)
}

func runAPIShow(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, NewEnvelope("usage-error", "missing capability id"))
	}
	if args[0] != "workflow.block" {
		return writeEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown capability %q", args[0])))
	}
	env := NewEnvelope("ok", "Capability workflow.block expanded.")
	env.Data["capability"] = map[string]any{
		"id":           "workflow.block",
		"summary":      "Record a resumable blocker and novice human action guide.",
		"input_schema": "workflow-block-input",
		"side_effect":  "writes-workflow",
		"command":      []string{"specify-runtime", "workflow", "block"},
	}
	env.ShowArgv = []string{"specify-runtime", "api", "schema", "workflow-block-input", "--format", "json"}
	return writeEnvelope(stdout, env)
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
