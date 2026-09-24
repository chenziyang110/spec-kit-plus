package main

const tasksRebindUsage = "specify-runtime tasks rebind --feature-dir <feature-dir> --expected-task-index-sha256 <sha256> --expected-workflow-revision <revision> --expected-test-design-handoff-sha256 <sha256> --reason <text> [--task-updates-json <object|@path|->] --format json"

const tasksRebindOutputContract = "On success returns task_count, task_index_sha256, test_design_handoff_sha256, workflow_revision, history_ref, history_sha256, preserved_task_ids, refreshed_ui_task_ids, and the atomic transaction receipt. Successful rebinding preserves prior accepted/deferred evidence; it does not advance workflow state or establish new implementation, Review, or human acceptance evidence."

// This is the optional semantic delta, not a replacement task index. Binding,
// lifecycle, evidence, and transaction fields stay exclusively runtime-owned.
func tasksRebindUpdatesInputSchema() map[string]any {
	refs := map[string]any{
		"type":        "array",
		"uniqueItems": true,
		"items":       map[string]any{"type": "string", "minLength": 1},
		"description": "Exact members of the verified current Test Design handoff; all task unions must consume all and only its refs.",
	}
	return map[string]any{
		"type":                 "object",
		"additionalProperties": false,
		"description":          "Optional updates keyed by existing pending/ready task IDs. Accepted/deferred tasks, started tasks, and runtime-owned bindings cannot be authored here.",
		"patternProperties": map[string]any{
			"^T[0-9]+$": map[string]any{
				"type":                 "object",
				"minProperties":        1,
				"additionalProperties": false,
				"properties": map[string]any{
					"test_case_refs": refs,
					"test_data_refs": refs,
					"ui_contract": map[string]any{
						"type":          "object",
						"minProperties": 1,
						"description":   "Task-local exact subset of the current adopted Plan UI contract; the runtime validates registered Design identity, immutable digests, and full required coverage.",
					},
				},
			},
		},
	}
}
