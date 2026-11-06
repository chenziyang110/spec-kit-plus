package main

func playbookSchemaString(maximum int) map[string]any {
	return map[string]any{"type": "string", "minLength": 1, "maxLength": maximum}
}

func playbookSchemaStrings(minimum, maximum int) map[string]any {
	return map[string]any{"type": "array", "minItems": minimum, "maxItems": maximum, "items": playbookSchemaString(512), "uniqueItems": true}
}

func playbookCwdSchema(allowEmpty bool) map[string]any {
	atom := `(?:[^/\\:\x00\r\n]|\{\{param:[a-z][a-z0-9_]{0,47}\}\})`
	first := `(?:[^./\\:\x00\r\n]|\{\{param:[a-z][a-z0-9_]{0,47}\}\})`
	component := `(?:` + first + `|\.` + first + `|\.\.` + atom + `)` + atom + `*`
	pattern := `(?:\.|` + component + `(?:/` + component + `)*)`
	if allowEmpty {
		pattern += `?`
	}
	return map[string]any{
		"type": "string", "maxLength": 512, "pattern": `^` + pattern + `$`,
		"description": "Canonical project-relative working directory: '.' or a path such as 'src/tool', using '/' separators and no absolute, drive, UNC or '.'/'..' path segments. Declared {{param:name}} placeholders resolve before runtime path and symlink checks. Native actions omit cwd or use an empty string.",
	}
}

func playbookActionSchema(check bool) map[string]any {
	properties := map[string]any{
		"native_action": playbookNativeActionSchema(),
		"id":            map[string]any{"type": "string", "pattern": `^[A-Za-z][A-Za-z0-9_-]{0,63}$`},
		"purpose":       playbookSchemaString(2048), "cwd": playbookSchemaString(512),
		"argv":       map[string]any{"type": "array", "maxItems": 128, "items": map[string]any{"type": "string", "maxLength": 8192}},
		"script_ref": playbookSchemaString(512), "depends_on": playbookSchemaStrings(0, 64),
		"required": map[string]any{"type": "boolean"}, "expected_result": playbookSchemaString(2048),
	}
	required := []string{"id", "purpose", "depends_on", "required", "expected_result"}
	schema := map[string]any{"type": "object", "additionalProperties": false, "properties": properties}
	if !check {
		properties["side_effect"] = map[string]any{"enum": []string{"read", "local_write", "external_mutation"}}
		properties["source_writes"] = playbookSchemaStrings(0, 64)
		properties["source_writes"].(map[string]any)["description"] = "Exact project-relative source paths or directories this local_write step may change. Do start requires them inside its Work-authorized write_scope; outputs alone do not need this field. The runtime records before/after source bases and requires fresh downstream checks."
		schema["allOf"] = []any{map[string]any{
			"if":   map[string]any{"required": []string{"source_writes"}, "properties": map[string]any{"source_writes": map[string]any{"minItems": 1}}},
			"then": map[string]any{"properties": map[string]any{"side_effect": map[string]any{"const": "local_write"}}},
		}}
		required = append(required, "side_effect")
	} else {
		properties["kind"] = map[string]any{"enum": []string{"exit_code", "file", "json", "junit", "observation"}}
		properties["result_path"] = playbookSchemaString(512)
		properties["json_pointer"] = map[string]any{"type": "string", "pattern": `^(/.*)?$`, "maxLength": 2048}
		properties["expected_json"] = map[string]any{}
		properties["min_cases"] = map[string]any{"type": "integer", "minimum": 1, "maximum": 10000000}
		required = append(required, "kind")
		schema["allOf"] = []any{
			map[string]any{"if": map[string]any{"properties": map[string]any{"kind": map[string]any{"const": "exit_code"}}}, "then": map[string]any{"required": []string{"argv"}, "properties": map[string]any{"argv": map[string]any{"minItems": 1}}, "not": map[string]any{"anyOf": []any{map[string]any{"required": []string{"native_action"}}, map[string]any{"required": []string{"result_path"}}, map[string]any{"required": []string{"json_pointer"}}, map[string]any{"required": []string{"expected_json"}}, map[string]any{"required": []string{"min_cases"}}}}}},
			map[string]any{"if": map[string]any{"properties": map[string]any{"kind": map[string]any{"enum": []string{"file", "json", "junit"}}}}, "then": map[string]any{"required": []string{"result_path"}}},
			map[string]any{"if": map[string]any{"properties": map[string]any{"kind": map[string]any{"const": "json"}}}, "then": map[string]any{"required": []string{"expected_json"}}},
			map[string]any{"if": map[string]any{"properties": map[string]any{"kind": map[string]any{"const": "junit"}}}, "then": map[string]any{"required": []string{"min_cases"}}},
			map[string]any{"if": map[string]any{"properties": map[string]any{"kind": map[string]any{"const": "observation"}}}, "then": map[string]any{"required": []string{"native_action", "expected_json"}, "properties": map[string]any{"depends_on": map[string]any{"minItems": 1}}, "not": map[string]any{"anyOf": []any{map[string]any{"required": []string{"result_path"}}, map[string]any{"required": []string{"min_cases"}}}}}},
		}
	}
	conditions, _ := schema["allOf"].([]any)
	processFields := map[string]any{"required": []string{"cwd", "argv"}, "properties": map[string]any{"cwd": playbookCwdSchema(false)}}
	if !check {
		processFields["properties"].(map[string]any)["argv"] = map[string]any{"minItems": 1}
	}
	conditions = append(conditions, map[string]any{"if": map[string]any{"required": []string{"native_action"}}, "then": map[string]any{"properties": map[string]any{"cwd": map[string]any{"const": ""}, "argv": map[string]any{"maxItems": 0}}, "not": map[string]any{"required": []string{"script_ref"}}}, "else": processFields})
	schema["allOf"] = conditions
	properties["cwd"] = playbookCwdSchema(true)
	schema["required"] = required
	return schema
}

func playbookDefinitionInputSchema() map[string]any {
	return map[string]any{
		"$schema":     "https://json-schema.org/draft/2020-12/schema",
		"title":       "Playbook definition input",
		"description": "Agent-owned method semantics only. Runtime derives identity, revision, digest, source fingerprints, and verification metadata. Steps stay ordered; matching a prior method never proves a new execution result.",
		"type":        "object", "additionalProperties": false,
		"required": []string{"operation", "target", "owner", "variant", "title", "goal", "aliases", "applicability", "source_files", "steps", "checks", "learning_refs"},
		"properties": map[string]any{
			"task_family": map[string]any{"type": "string", "pattern": `^[a-z][a-z0-9._-]{0,63}$`},
			"parameters":  playbookParameterSchema(),
			"operation":   map[string]any{"enum": []string{"build", "package", "test", "check", "generate", "maintenance", "custom"}},
			"target":      playbookSchemaString(128), "owner": playbookSchemaString(256),
			"variant": map[string]any{"type": "string", "pattern": `^[a-z0-9][a-z0-9._-]{0,63}$`},
			"title":   playbookSchemaString(2048), "goal": playbookSchemaString(2048),
			"aliases": playbookSchemaStrings(0, 32), "learning_refs": playbookSchemaStrings(0, 32),
			"source_files":  playbookSchemaStrings(1, 64),
			"applicability": map[string]any{"type": "object", "maxProperties": 24, "additionalProperties": false, "patternProperties": map[string]any{`^(os|arch|shell|toolchain\.[a-z][a-z0-9_-]{0,31})$`: map[string]any{"type": "array", "minItems": 1, "maxItems": 16, "uniqueItems": true, "items": playbookSchemaString(128)}}},
			"steps":         map[string]any{"type": "array", "minItems": 1, "maxItems": 64, "items": playbookActionSchema(false), "contains": map[string]any{"type": "object", "properties": map[string]any{"required": map[string]any{"const": true}}, "required": []string{"required"}}},
			"checks":        map[string]any{"type": "array", "minItems": 1, "maxItems": 64, "items": playbookActionSchema(true), "contains": map[string]any{"type": "object", "properties": map[string]any{"required": map[string]any{"const": true}}, "required": []string{"required"}}},
		},
	}
}

func playbookDefinitionSchema() map[string]any { return playbookDefinitionInputSchema() }

func playbookUpdateInputSchema() map[string]any {
	return map[string]any{
		"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Playbook update input",
		"type": "object", "additionalProperties": false, "required": []string{"definition", "change_summary"},
		"properties": map[string]any{
			"id":          map[string]any{"type": "string", "pattern": playbookIDPattern.String()},
			"base_digest": map[string]any{"type": "string", "pattern": `^([a-f0-9]{64})?$`},
			"definition":  playbookDefinitionInputSchema(),
			"session_id":  playbookSchemaString(128), "change_summary": playbookSchemaString(2048),
			"proposal_only": map[string]any{"type": "boolean"},
		},
	}
}

func playbookContextInputSchema() map[string]any {
	return map[string]any{"type": "object", "maxProperties": 24, "additionalProperties": false, "patternProperties": map[string]any{playbookContextKeyPattern.String(): playbookSchemaString(128)}}
}

func playbookFindInputSchema() map[string]any {
	return map[string]any{
		"type": "object", "additionalProperties": false,
		"description": "CLI filters are flags; context is one structured --context-json value. OS/arch default to the runtime host and may be supplied as explicit search filters.",
		"properties": map[string]any{
			"query": map[string]any{"type": "string", "maxLength": 2048},
			"rank":  doSchemaEnum("relevance", "observed"), "parameters": map[string]any{"type": "object", "maxProperties": 32, "additionalProperties": playbookSchemaString(4096)},
			"operation": map[string]any{"enum": []string{"build", "package", "test", "check", "generate", "maintenance", "custom"}},
			"target":    playbookSchemaString(128), "context": playbookContextInputSchema(),
			"limit":  map[string]any{"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
			"cursor": map[string]any{"type": "integer", "minimum": 0, "default": 0},
		},
	}
}

func playbookShowInputSchema() map[string]any {
	return map[string]any{"type": "object", "additionalProperties": false, "required": []string{"id"}, "properties": map[string]any{
		"id":              map[string]any{"type": "string", "pattern": playbookIDPattern.String()},
		"section":         map[string]any{"enum": []string{"summary", "steps", "checks", "evidence", "recovery", "all"}, "default": "summary"},
		"revision":        map[string]any{"type": "integer", "minimum": 1, "maximum": 999999},
		"proposal_digest": map[string]any{"type": "string", "pattern": playbookDigestPattern.String()},
	}, "not": map[string]any{"required": []string{"revision", "proposal_digest"}}}
}

func playbookValidateInputSchema() map[string]any { return playbookDefinitionInputSchema() }

func playbookMetricsInputSchema() map[string]any {
	return doSchemaObject(map[string]any{"id": map[string]any{"type": "string", "pattern": playbookIDPattern.String()}, "context": playbookContextInputSchema(), "parameters": map[string]any{"type": "object", "maxProperties": 32, "additionalProperties": playbookSchemaString(4096)}}, "id")
}
