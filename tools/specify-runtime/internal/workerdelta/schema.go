package workerdelta

func InputSchema() map[string]any {
	stringSchema := map[string]any{"type": "string", "minLength": 1}
	identity := map[string]any{}
	for _, field := range []string{"task_ref", "task_id", "packet_id", "attempt_id"} {
		identity[field] = stringSchema
	}
	properties := map[string]any{"schema": map[string]any{"const": Schema}, "version": map[string]any{"type": "integer", "const": 1}, "identity": map[string]any{"type": "object", "additionalProperties": false, "properties": identity}, "recovery": map[string]any{"type": "object", "additionalProperties": false, "properties": map[string]any{"state": map[string]any{"type": "string"}, "actions": map[string]any{"type": "array"}}}}
	for _, field := range Fields {
		properties[field] = map[string]any{"type": "array"}
	}
	properties["changed_paths"] = map[string]any{"type": "array", "items": stringSchema}
	properties["path_changes"] = map[string]any{"type": "array", "items": map[string]any{"oneOf": []any{map[string]any{"type": "object", "additionalProperties": false, "required": []string{"kind", "path"}, "properties": map[string]any{"kind": map[string]any{"enum": []string{"added", "modified", "deleted", "retained", "unknown"}}, "path": stringSchema}}, map[string]any{"type": "object", "additionalProperties": false, "required": []string{"kind", "old_path", "new_path"}, "properties": map[string]any{"kind": map[string]any{"const": "renamed"}, "old_path": stringSchema, "new_path": stringSchema}}}}}
	return map[string]any{"anyOf": []any{map[string]any{"type": "object", "maxProperties": 0}, map[string]any{"type": "object", "additionalProperties": false, "required": []string{"schema", "version"}, "properties": properties}}, "description": "Advisory worker candidate; runtime alone owns submission history, source bindings and acceptance. Retain failure edits and both rename endpoints."}
}
