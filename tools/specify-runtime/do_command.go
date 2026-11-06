package main

import (
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
)

// Command input is a prepare-only convenience. It compiles current script
// facts into the existing definition; execution, evidence and Work stay owned
// by the ordinary start/next/record/complete protocol.
type doCommandInput struct {
	Operation      string                           `json:"operation"`
	Cwd            string                           `json:"cwd,omitempty"`
	Argv           []string                         `json:"argv"`
	SourceWrites   []string                         `json:"source_writes,omitempty"`
	ExternalInputs map[string]PlaybookExternalInput `json:"external_inputs,omitempty"`
	Checks         []doCommandCheck                 `json:"checks"`
}

type doCommandCheck struct {
	Cwd          string          `json:"cwd,omitempty"`
	Argv         []string        `json:"argv,omitempty"`
	Kind         string          `json:"kind,omitempty"`
	ResultPath   string          `json:"result_path,omitempty"`
	JSONPointer  string          `json:"json_pointer,omitempty"`
	ExpectedJSON json.RawMessage `json:"expected_json,omitempty"`
	MinCases     int             `json:"min_cases,omitempty"`
}

func doExpandCommand(root string, input doStartInput) (doStartInput, error) {
	command := input.Command
	if command == nil {
		return input, nil
	}
	if input.MethodBinding != nil || !reflect.DeepEqual(input.Definition, PlaybookDefinition{}) || input.Parameters != nil {
		return input, fmt.Errorf("command cannot be combined with definition, method_binding or parameters: pointer=/command")
	}
	if strings.TrimSpace(input.Goal) == "" {
		return input, fmt.Errorf("command input requires the actual operation goal: pointer=/goal")
	}
	cwd := command.Cwd
	if cwd == "" {
		cwd = "."
	}
	scripts, err := playbookActionScriptSources(root, cwd, command.Argv)
	if err != nil {
		return input, err
	}
	if len(scripts) != 1 {
		return input, fmt.Errorf("command requires one fixed project script; use a definition for other operations: pointer=/command/argv")
	}
	if len(command.Checks) == 0 || len(command.Checks) > 64 {
		return input, fmt.Errorf("command requires 1 to 64 explicit output or verification checks: pointer=/command/checks")
	}
	checks := make([]PlaybookCheck, 0, len(command.Checks))
	for i, check := range command.Checks {
		kind := check.Kind
		if kind == "" {
			kind = "exit_code"
		}
		checkCwd := check.Cwd
		if checkCwd == "" {
			checkCwd = cwd
		}
		checks = append(checks, PlaybookCheck{
			ID: fmt.Sprintf("check-%d", i+1), Purpose: "Verify the requested operation result",
			Cwd: checkCwd, Argv: append([]string{}, check.Argv...), DependsOn: []string{"run"},
			Required: true, ExpectedResult: "The declared verification passes",
			Kind: kind, ResultPath: check.ResultPath, JSONPointer: check.JSONPointer,
			ExpectedJSON: check.ExpectedJSON, MinCases: check.MinCases,
		})
	}
	input.Definition = PlaybookDefinition{
		ExternalInputs: command.ExternalInputs,
		Operation:      command.Operation, Target: "project-script", Owner: scripts[0],
		Variant: "default", Title: input.Goal, Goal: input.Goal,
		Aliases: []string{}, LearningRefs: []string{}, Applicability: map[string][]string{},
		SourceFiles: scripts,
		Steps: []PlaybookStep{{ID: "run", Purpose: input.Goal, Cwd: cwd,
			Argv: append([]string{}, command.Argv...), DependsOn: []string{}, Required: true,
			ExpectedResult: "The requested project script succeeds", SideEffect: "local_write",
			SourceWrites: append([]string{}, command.SourceWrites...)}},
		Checks: checks,
	}
	input.Command = nil
	return input, nil
}

func doCommandInputSchema() map[string]any {
	check := doSchemaObject(map[string]any{
		"cwd":         playbookActionSchema(true)["properties"].(map[string]any)["cwd"],
		"argv":        map[string]any{"type": "array", "maxItems": 128, "items": map[string]any{"type": "string", "maxLength": 8192}},
		"kind":        doSchemaEnum("exit_code", "file", "json", "junit"),
		"result_path": playbookSchemaString(512), "json_pointer": map[string]any{"type": "string"},
		"expected_json": map[string]any{}, "min_cases": map[string]any{"type": "integer", "minimum": 1, "maximum": 10000000},
	})
	delete(check, "required") // Requirements are conditional; never publish null.
	check["allOf"] = []any{
		map[string]any{"if": map[string]any{"not": map[string]any{"required": []string{"kind"}}}, "then": map[string]any{"required": []string{"argv"}, "properties": map[string]any{"argv": map[string]any{"minItems": 1}}}},
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"const": "exit_code"}}}, "then": map[string]any{"required": []string{"argv"}, "properties": map[string]any{"argv": map[string]any{"minItems": 1}}}},
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"enum": []string{"file", "json", "junit"}}}}, "then": map[string]any{"required": []string{"result_path"}}},
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"const": "json"}}}, "then": map[string]any{"required": []string{"expected_json"}}},
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"const": "junit"}}}, "then": map[string]any{"required": []string{"min_cases"}}},
	}
	schema := doSchemaObject(map[string]any{
		"operation":       playbookDefinitionInputSchema()["properties"].(map[string]any)["operation"],
		"cwd":             playbookActionSchema(false)["properties"].(map[string]any)["cwd"],
		"argv":            map[string]any{"type": "array", "minItems": 1, "maxItems": 128, "items": map[string]any{"type": "string", "maxLength": 8192}},
		"source_writes":   playbookSchemaStrings(0, 64),
		"external_inputs": doExternalInputSchema(),
		"checks":          map[string]any{"type": "array", "minItems": 1, "maxItems": 64, "items": check},
	}, "operation", "argv", "checks")
	schema["allOf"] = doProtectedDefinitionConditions()
	return schema
}

func doPrepareInputSchema() map[string]any {
	schema := doStartInputSchema()
	schema["properties"].(map[string]any)["command"] = doCommandInputSchema()
	schema["anyOf"] = append(schema["anyOf"].([]any), map[string]any{"required": []string{"command", "goal"}})
	schema["allOf"] = []any{map[string]any{
		"if": map[string]any{"required": []string{"command"}},
		"then": map[string]any{"required": []string{"goal"}, "not": map[string]any{"anyOf": []any{
			map[string]any{"required": []string{"definition"}}, map[string]any{"required": []string{"method_binding"}}, map[string]any{"required": []string{"parameters"}},
		}}},
	}}
	return schema
}
