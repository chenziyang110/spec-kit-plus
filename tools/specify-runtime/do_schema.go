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
	result := doSchemaObject(map[string]any{
		"parameters": map[string]any{"type": "object", "maxProperties": 32, "additionalProperties": playbookSchemaString(4096)},
		"session_id": map[string]any{"type": "string", "pattern": doIDPattern.String()},
		"goal":       doSchemaString(), "definition": playbookDefinitionInputSchema(),
		"method_binding": doSchemaObject(map[string]any{"id": doSchemaString(), "revision": doSchemaRevision(), "content_digest": map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"}}, "id", "revision", "content_digest"),
		"context":        map[string]any{"type": "object", "additionalProperties": map[string]any{"type": "string"}},
		"source_files":   doSchemaStrings(), "write_scope": doSchemaStrings(), "output_scope": doSchemaStrings(),
		"agent_id": doSchemaString(), "adapter_id": doSchemaString(),
	}, "agent_id", "adapter_id")
	result["anyOf"] = []any{map[string]any{"required": []string{"definition"}}, map[string]any{"required": []string{"method_binding"}}}
	return result
}

func doRecordInputSchema() map[string]any {
	result := doSchemaObject(map[string]any{"path": doSchemaString(), "kind": doSchemaEnum("file", "json", "junit", "log"), "sha256": map[string]any{"type": "string", "pattern": "^[a-f0-9]{64}$"}}, "path", "kind")
	event := doSchemaObject(map[string]any{
		"native_action": playbookNativeActionSchema(), "native_observation": doNativeObservationSchema(),
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

func doCompleteInputSchema() map[string]any {
	return doSchemaObject(map[string]any{"expected_revision": doSchemaRevision(), "change_summary": map[string]any{"type": "string", "minLength": 1, "maxLength": 2048}}, "expected_revision", "change_summary")
}

func doResumeInputSchema() map[string]any {
	recovery := doSchemaObject(map[string]any{
		"native_action_settled": map[string]any{"const": true},
		"reason":                doSchemaString(), "evidence_ref": doSchemaString(),
		"evidence_text":     map[string]any{"type": "string", "minLength": 1, "maxLength": doRecoveryTextLimit, "description": "Sanitized native process and side-effect inspection, at most 64 KiB of UTF-8. Runtime atomically snapshots this text inside its already owned session evidence directory; no product/output write scope is needed or expanded."},
		"processes_stopped": map[string]any{"const": true}, "side_effects_inspected": map[string]any{"const": true},
	}, "reason", "side_effects_inspected")
	recovery["anyOf"] = []any{map[string]any{"required": []string{"processes_stopped"}}, map[string]any{"required": []string{"native_action_settled"}}}
	recovery["oneOf"] = []any{map[string]any{"required": []string{"evidence_ref"}}, map[string]any{"required": []string{"evidence_text"}}}
	recovery["description"] = "Provide exactly one evidence source. File evidence_ref must remain inside the original write/output scope; evidence_text is saved by the runtime together with recovery. Evidence digests are runtime-owned."
	replanScope := map[string]any{"type": "array", "items": doSchemaString(), "maxItems": 128, "description": "Optional complete scope. Omission inherits the previous scope; a supplied array must retain every previous exact path and can only add paths before their first mutation."}
	replan := doSchemaObject(map[string]any{
		"mode": doSchemaEnum("failed", "unstarted"), "retain_verified": map[string]any{"type": "boolean", "default": false},
		"request_id": map[string]any{"type": "string", "pattern": doIDPattern.String()},
		"definition": playbookDefinitionInputSchema(), "write_scope": replanScope, "output_scope": replanScope,
	}, "request_id", "definition")
	replan["description"] = "Default failed mode requires genuine failed attempt and inspected effects. Unstarted mode changes only unattempted actions and omits attempt_id/recovery. retain_verified allows original process observations through an unbroken immutable epoch chain with identical actions/source/dependencies and rehashed local results; excludes native/external/source mutation. Required dependency closure and exact outcome checks cannot weaken. History remains immutable; retained results are not new executions."
	paths := doSchemaStrings()
	paths["minItems"], paths["maxItems"], paths["uniqueItems"] = 1, 128, true
	external := doSchemaObject(map[string]any{"paths": paths}, "paths")
	external["description"] = "Inspect exact current unrelated workspace changes using recovery evidence. Runtime binds current bytes and source basis without claiming ownership, widening scope, or changing the baseline. Operation inputs and writes cannot be excluded; later drift requires fresh inspection."
	result := doSchemaObject(map[string]any{"expected_revision": doSchemaRevision(), "attempt_id": doSchemaString(), "work_fence": map[string]any{"type": "integer", "minimum": 1, "description": "Explicit current fence returned by completed Work recovery; Do never claims or resumes Work ownership automatically."}, "recovery": recovery, "replan": replan, "external_changes": external}, "expected_revision")
	result["allOf"] = []any{map[string]any{
		"if":   map[string]any{"required": []string{"external_changes"}},
		"then": map[string]any{"required": []string{"recovery"}, "not": map[string]any{"anyOf": []any{map[string]any{"required": []string{"attempt_id"}}, map[string]any{"required": []string{"replan"}}}}},
	}}
	unstarted := map[string]any{"required": []string{"replan"}, "properties": map[string]any{"replan": map[string]any{"required": []string{"mode"}, "properties": map[string]any{"mode": map[string]any{"const": "unstarted"}}}}}
	result["if"] = unstarted
	result["then"] = map[string]any{"not": map[string]any{"anyOf": []any{map[string]any{"required": []string{"recovery"}}, map[string]any{"required": []string{"attempt_id"}}}}}
	result["else"] = map[string]any{"required": []string{"recovery"}}
	return result
}
