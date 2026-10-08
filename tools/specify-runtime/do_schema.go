package main

func doSchemaObject(properties map[string]any, required ...string) map[string]any {
	return map[string]any{"type": "object", "additionalProperties": false, "properties": properties, "required": required}
}
func doSchemaString() map[string]any { return map[string]any{"type": "string", "minLength": 1} }
func doSchemaStrings() map[string]any {
	return map[string]any{"type": "array", "items": doSchemaString()}
}
func doSchemaRevision() map[string]any { return map[string]any{"type": "integer", "minimum": 1} }
func doSchemaEnum(values ...string) map[string]any {
	return map[string]any{"type": "string", "enum": values}
}

func doStartInputSchema() map[string]any {
	return doSchemaObject(map[string]any{
		"session_id": map[string]any{"type": "string", "pattern": doIDPattern.String()},
		"goal":       doSchemaString(), "definition": playbookDefinitionInputSchema(),
		"method_binding": doSchemaObject(map[string]any{"id": doSchemaString(), "revision": doSchemaRevision(), "content_digest": map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"}}, "id", "revision", "content_digest"),
		"context":        map[string]any{"type": "object", "additionalProperties": map[string]any{"type": "string"}},
		"source_files":   doSchemaStrings(), "write_scope": doSchemaStrings(), "output_scope": doSchemaStrings(),
		"agent_id": doSchemaString(), "adapter_id": doSchemaString(),
	}, "definition", "agent_id", "adapter_id")
}

func doRecordInputSchema() map[string]any {
	result := doSchemaObject(map[string]any{"path": doSchemaString(), "kind": doSchemaEnum("file", "json", "junit", "log"), "sha256": map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"}}, "path", "kind")
	event := doSchemaObject(map[string]any{
		"attempt_id": map[string]any{"type": "string", "pattern": doIDPattern.String()}, "target_id": doSchemaString(), "kind": doSchemaEnum("step", "check"), "event": doSchemaEnum("started", "completed"),
		"status": doSchemaEnum("passed", "failed", "interrupted"), "evidence_origin": doSchemaEnum("agent_tool_observation"), "tool_call_id": doSchemaString(),
		"argv": doSchemaStrings(), "cwd": doSchemaString(), "started_at": map[string]any{"type": "string", "format": "date-time"}, "finished_at": map[string]any{"type": "string", "format": "date-time"}, "exit_code": map[string]any{"type": "integer"}, "timed_out": map[string]any{"type": "boolean"}, "cancelled": map[string]any{"type": "boolean"}, "summary": map[string]any{"type": "string", "maxLength": 4096}, "result_refs": map[string]any{"type": "array", "items": result, "maxItems": 16},
	}, "attempt_id", "target_id", "kind", "event")
	event["description"] = "Record started before native execution. A later completed record must include actual provenance, argv/cwd, timestamps, exit code where a command ran, and typed evidence. Timeouts/cancellation are interrupted."
	return doSchemaObject(map[string]any{"expected_revision": doSchemaRevision(), "request_id": map[string]any{"type": "string", "pattern": doIDPattern.String()}, "events": map[string]any{"type": "array", "items": event, "minItems": 1, "maxItems": 32}}, "expected_revision", "request_id", "events")
}

func doFinishInputSchema() map[string]any {
	return doSchemaObject(map[string]any{
		"expected_revision": doSchemaRevision(), "knowledge_status": doSchemaEnum("pending", "saved", "not_applicable"),
		"knowledge": doSchemaObject(map[string]any{"path": doSchemaString(), "sha256": map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"}, "method_id": doSchemaString(), "revision": doSchemaRevision()}, "path", "sha256", "method_id", "revision"),
		"blocker":   doSchemaObject(map[string]any{"category": doSchemaString(), "owner": doSchemaEnum("human", "external"), "cause": doSchemaString(), "next_action": doSchemaString(), "unblock_criteria": doSchemaString(), "resume_point": doSchemaString(), "attempted_recovery": doSchemaStrings(), "evidence_refs": doSchemaStrings()}, "category", "owner", "cause", "next_action", "unblock_criteria", "resume_point", "attempted_recovery", "evidence_refs"),
	}, "expected_revision")
}

func doResumeInputSchema() map[string]any {
	replanScope := map[string]any{"type": "array", "items": doSchemaString(), "maxItems": 128, "description": "Optional complete scope. Omission inherits the previous scope; a supplied array must retain every previous exact path and can only add paths before their first mutation."}
	replan := doSchemaObject(map[string]any{
		"request_id": map[string]any{"type": "string", "pattern": doIDPattern.String()},
		"definition": playbookDefinitionInputSchema(), "write_scope": replanScope, "output_scope": replanScope,
	}, "request_id", "definition")
	replan["description"] = "After a genuine failed current-epoch attempt and inspected effects, freeze a changed definition with the same operation identity and goal. Retain all history and rerun every required step/check in the new runtime-owned epoch. Exact request replay is idempotent. Unchanged definitions use ordinary retry."
	return doSchemaObject(map[string]any{"expected_revision": doSchemaRevision(), "attempt_id": doSchemaString(), "work_fence": map[string]any{"type": "integer", "minimum": 1, "description": "Explicit current fence returned by completed Work recovery; Do never claims or resumes Work ownership automatically."}, "recovery": doSchemaObject(map[string]any{"reason": doSchemaString(), "evidence_ref": doSchemaString(), "processes_stopped": map[string]any{"const": true}, "side_effects_inspected": map[string]any{"const": true}}, "reason", "evidence_ref", "processes_stopped", "side_effects_inspected"), "replan": replan}, "expected_revision", "recovery")
}
