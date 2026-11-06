package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"path"
	"reflect"
	"regexp"
	"strings"
)

// Parameters are ordinary nonsecret inputs. Environment secret bindings remain
// separate; expansion substitutes data and never evaluates a shell expression.
type PlaybookParameter struct {
	Kind          string   `json:"kind"`
	Required      bool     `json:"required"`
	Example       string   `json:"example"`
	Default       *string  `json:"default,omitempty"`
	AllowedValues []string `json:"allowed_values,omitempty"`
	Pattern       string   `json:"pattern,omitempty"`
	MaxLength     int      `json:"max_length,omitempty"`
}

func (parameter *PlaybookParameter) UnmarshalJSON(raw []byte) error {
	if err := playbookRequireJSONFields(raw, "kind", "required", "example"); err != nil {
		return err
	}
	type plain PlaybookParameter
	var value plain
	if err := decodePlaybookJSON(raw, &value); err != nil {
		return err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return err
	}
	if rawDefault, present := fields["default"]; present && string(rawDefault) == "null" {
		return fmt.Errorf("playbook_parameter_default_must_be_a_string")
	}
	*parameter = PlaybookParameter(value)
	return nil
}

var playbookParameterName = regexp.MustCompile(`^[a-z][a-z0-9_]{0,47}$`)
var playbookParameterToken = regexp.MustCompile(`\{\{param:([a-z][a-z0-9_]{0,47})\}\}`)

func normalizePlaybookParameters(parameters map[string]PlaybookParameter) map[string]PlaybookParameter {
	if len(parameters) == 0 {
		return nil
	}
	result := make(map[string]PlaybookParameter, len(parameters))
	for name, parameter := range parameters {
		parameter.AllowedValues = uniqueSortedTrimmed(parameter.AllowedValues)
		if parameter.Default != nil {
			value := *parameter.Default
			parameter.Default = &value
		}
		result[name] = parameter
	}
	return result
}

func validatePlaybookParameter(root, name string, parameter PlaybookParameter, value string) error {
	if !playbookParameterName.MatchString(name) || strings.Contains(value, "{{param:") || strings.ContainsAny(value, "\x00\r\n") || strings.TrimSpace(value) != value || value == "" {
		return fmt.Errorf("playbook_parameter_invalid: %s", name)
	}
	maximum := parameter.MaxLength
	if maximum == 0 {
		maximum = 1024
	}
	if maximum < 1 || maximum > 4096 || len(value) > maximum || len(parameter.AllowedValues) > 32 || len(parameter.Pattern) > 512 {
		return fmt.Errorf("playbook_parameter_bounds_invalid: %s", name)
	}
	switch parameter.Kind {
	case "string":
		if parameter.Pattern == "" {
			return fmt.Errorf("playbook_string_parameter_requires_pattern: %s: pointer=%s", name, playbookJSONPointer(playbookJSONPointer("", "parameters"), name)+"/pattern")
		}
	case "enum":
		if len(parameter.AllowedValues) == 0 {
			return fmt.Errorf("playbook_enum_parameter_requires_values: %s", name)
		}
	case "path":
		if _, err := playbookSafePath(root, value, false); err != nil {
			return fmt.Errorf("playbook_parameter_path_invalid: %s: %w", name, err)
		}
		if doWorkflowStatePath(value) {
			return fmt.Errorf("playbook_parameter_path_is_protected: %s", name)
		}
	default:
		return fmt.Errorf("playbook_parameter_kind_invalid: %s", name)
	}
	if len(parameter.AllowedValues) > 0 {
		found := false
		for _, allowed := range parameter.AllowedValues {
			if value == allowed {
				found = true
			}
		}
		if !found {
			return fmt.Errorf("playbook_parameter_value_not_allowed: %s", name)
		}
	}
	if parameter.Pattern != "" {
		pattern, err := regexp.Compile("^(?:" + parameter.Pattern + ")$")
		if err != nil || !pattern.MatchString(value) {
			return fmt.Errorf("playbook_parameter_pattern_mismatch: %s", name)
		}
	}
	return nil
}

func validatePlaybookDefinition(root string, definition PlaybookDefinition) error {
	if definition.TaskFamily != "" && !regexp.MustCompile(`^[a-z][a-z0-9._-]{0,63}$`).MatchString(definition.TaskFamily) {
		return fmt.Errorf("playbook_task_family_invalid")
	}
	if len(definition.Parameters) == 0 {
		_, _, err := resolvePlaybookDefinition(root, definition, nil)
		return err
	}
	if len(definition.Parameters) > 32 {
		return fmt.Errorf("playbook_parameter_count_invalid")
	}
	examples := map[string]string{}
	for name, parameter := range definition.Parameters {
		if err := validatePlaybookParameter(root, name, parameter, parameter.Example); err != nil {
			return err
		}
		if !parameter.Required && parameter.Default == nil {
			return fmt.Errorf("playbook_optional_parameter_requires_default: %s", name)
		}
		if parameter.Default != nil {
			if err := validatePlaybookParameter(root, name, parameter, *parameter.Default); err != nil {
				return err
			}
		}
		examples[name] = parameter.Example
	}
	_, _, err := resolvePlaybookDefinition(root, definition, examples)
	if err == nil {
		err = validatePlaybookSensitiveContent(root, definition)
	}
	return err
}

func resolvePlaybookDefinition(root string, definition PlaybookDefinition, supplied map[string]string) (PlaybookDefinition, map[string]string, error) {
	definition = playbookNormalizeDefinition(definition)
	if len(definition.Parameters) == 0 && len(supplied) == 0 {
		raw, _ := json.Marshal(definition)
		if strings.Contains(string(raw), "{{param:") {
			return PlaybookDefinition{}, nil, fmt.Errorf("playbook_parameter_undeclared")
		}
		return definition, nil, validateResolvedPlaybookDefinition(root, definition)
	}
	bindings := map[string]string{}
	for name := range supplied {
		if _, exists := definition.Parameters[name]; !exists {
			return PlaybookDefinition{}, nil, fmt.Errorf("playbook_parameter_unknown: %s", name)
		}
	}
	for name, parameter := range definition.Parameters {
		value, present := supplied[name]
		if !present && parameter.Default != nil {
			value, present = *parameter.Default, true
		}
		if !present {
			return PlaybookDefinition{}, nil, fmt.Errorf("playbook_parameter_required: %s", name)
		}
		if err := validatePlaybookParameter(root, name, parameter, value); err != nil {
			return PlaybookDefinition{}, nil, err
		}
		bindings[name] = value
	}
	if err := doNativeSensitiveCheck(root, bindings); err != nil {
		return PlaybookDefinition{}, nil, err
	}
	var expansionError error
	expand := func(value string) string {
		return playbookParameterToken.ReplaceAllStringFunc(value, func(token string) string {
			name := playbookParameterToken.FindStringSubmatch(token)[1]
			value, exists := bindings[name]
			if !exists {
				expansionError = fmt.Errorf("playbook_parameter_undeclared: %s", name)
			}
			return value
		})
	}
	expandArgv := func(cwd string, argv []string, parameterizedCwd bool) []string {
		result := append([]string{}, argv...)
		fileScript := playbookPowerShellFileScriptIndex(root, cwd, argv)
		if parameterizedCwd {
			fileScript = -1 // The new -File exception must not parameterize script selection.
		}
		for i, argument := range result {
			if !strings.Contains(argument, "{{param:") {
				continue
			}
			if i == 0 || playbookParameterToken.FindString(argument) != argument {
				expansionError = fmt.Errorf("playbook_parameter_must_be_a_complete_argv_value")
				continue
			}
			if len(argv) > 0 {
				command := strings.TrimSuffix(strings.ToLower(path.Base(strings.ReplaceAll(argv[0], "\\", "/"))), ".exe")
				if command == "sh" || command == "bash" || command == "zsh" || command == "cmd" || ((command == "powershell" || command == "pwsh") && (fileScript < 0 || i <= fileScript)) {
					expansionError = fmt.Errorf("playbook_parameter_shell_command_expansion_forbidden")
					continue
				}
			}
			result[i] = expand(argument)
			if fileScript >= 0 && strings.HasPrefix(result[i], "-") {
				expansionError = fmt.Errorf("playbook_parameter_shell_command_expansion_forbidden")
			}
		}
		return result
	}
	expandJSON := func(raw json.RawMessage) json.RawMessage {
		if len(raw) == 0 {
			return raw
		}
		var value any
		canonical, err := doNativeJSON(raw, false)
		if err != nil {
			expansionError = err
			return raw
		}
		decoder := json.NewDecoder(bytes.NewReader(canonical))
		decoder.UseNumber()
		if err := decoder.Decode(&value); err != nil {
			expansionError = err
			return raw
		}
		var visit func(any) any
		visit = func(value any) any {
			switch typed := value.(type) {
			case string:
				return expand(typed)
			case []any:
				for i := range typed {
					typed[i] = visit(typed[i])
				}
				return typed
			case map[string]any:
				for key, item := range typed {
					if strings.Contains(key, "{{param:") {
						expansionError = fmt.Errorf("playbook_parameter_json_keys_are_fixed")
					}
					typed[key] = visit(item)
				}
				return typed
			default:
				return value
			}
		}
		encoded, err := json.Marshal(visit(value))
		if err != nil {
			expansionError = err
		}
		return encoded
	}
	expandNative := func(action *PlaybookNativeAction) *PlaybookNativeAction {
		if action == nil {
			return nil
		}
		result := *action
		result.Target = expand(result.Target)
		result.Arguments = expandJSON(result.Arguments)
		return &result
	}
	for i := range definition.Steps {
		step := &definition.Steps[i]
		parameterizedCwd := strings.Contains(step.Cwd, "{{param:")
		step.Cwd = expand(step.Cwd)
		step.Argv, step.ExpectedResult = expandArgv(step.Cwd, step.Argv, parameterizedCwd), expand(step.ExpectedResult)
		step.NativeAction = expandNative(step.NativeAction)
		for j := range step.SourceWrites {
			step.SourceWrites[j] = expand(step.SourceWrites[j])
		}
	}
	for i := range definition.Checks {
		check := &definition.Checks[i]
		parameterizedCwd := strings.Contains(check.Cwd, "{{param:")
		check.Cwd = expand(check.Cwd)
		check.Argv, check.ResultPath = expandArgv(check.Cwd, check.Argv, parameterizedCwd), expand(check.ResultPath)
		check.ExpectedResult, check.ExpectedJSON = expand(check.ExpectedResult), expandJSON(check.ExpectedJSON)
		check.NativeAction = expandNative(check.NativeAction)
	}
	definition.Parameters = nil
	if expansionError != nil {
		return PlaybookDefinition{}, nil, expansionError
	}
	raw, err := json.Marshal(definition)
	if err != nil || strings.Contains(string(raw), "{{param:") {
		return PlaybookDefinition{}, nil, fmt.Errorf("playbook_parameter_outside_supported_input_fields")
	}
	if err := validateResolvedPlaybookDefinition(root, definition); err != nil {
		return PlaybookDefinition{}, nil, err
	}
	if len(bindings) == 0 {
		bindings = nil
	}
	return definition, bindings, nil
}

// -File passes later argv as script data. Keep the executable, host options and
// existing project script fixed; -Command and unknown host forms never qualify.
func playbookPowerShellFileScriptIndex(root, cwd string, argv []string) int {
	if len(argv) < 3 {
		return -1
	}
	command := strings.TrimSuffix(strings.ToLower(path.Base(strings.ReplaceAll(argv[0], "\\", "/"))), ".exe")
	if command != "pwsh" && command != "powershell" {
		return -1
	}
	for i := 1; i < len(argv); i++ {
		switch strings.ToLower(argv[i]) {
		case "-nologo", "-noprofile", "-noninteractive", "-sta", "-mta":
		case "-executionpolicy":
			i++
			if i >= len(argv) {
				return -1
			}
			switch strings.ToLower(argv[i]) {
			case "allsigned", "bypass", "default", "remotesigned", "restricted", "undefined", "unrestricted":
			default:
				return -1
			}
		case "-file", "-f":
			if i+1 >= len(argv) {
				return -1
			}
			script := strings.ReplaceAll(argv[i+1], "\\", "/")
			if !strings.EqualFold(path.Ext(script), ".ps1") || strings.HasPrefix(script, "/") || strings.ContainsAny(script, ":$%{}\"'`;|&()*?[]\x00\r\n") {
				return -1
			}
			relative := path.Clean(path.Join(cwd, script))
			if _, err := playbookSafePath(root, relative, false); err != nil {
				return -1
			}
			if _, err := secureProjectReadFile(root, relative); err != nil {
				return -1
			}
			return i + 1
		default:
			return -1
		}
	}
	return -1
}

func doMethodDefinition(session DoSession) PlaybookDefinition {
	if session.TemplateDefinition != nil {
		return *session.TemplateDefinition
	}
	return session.Definition
}
func doMethodDigest(session DoSession) string {
	if session.TemplateDigest != "" {
		return session.TemplateDigest
	}
	return session.DefinitionDigest
}

func doVerifyInstanceBinding(root string, session DoSession) error {
	if session.TemplateDefinition == nil {
		if session.TemplateDigest != "" || len(session.Parameters) != 0 {
			return fmt.Errorf("session_parameter_template_binding_missing")
		}
		return nil
	}
	digest, err := playbookDefinitionDigest(*session.TemplateDefinition)
	if err != nil || digest != session.TemplateDigest {
		return fmt.Errorf("session_template_digest_mismatch")
	}
	resolved, parameters, err := resolvePlaybookDefinition(root, *session.TemplateDefinition, session.Parameters)
	if err != nil {
		return err
	}
	instanceDigest, err := playbookDefinitionDigest(resolved)
	if err != nil || instanceDigest != session.DefinitionDigest || !reflect.DeepEqual(parameters, session.Parameters) {
		return fmt.Errorf("session_instance_does_not_match_template_parameters")
	}
	return nil
}

func playbookParameterSchema() map[string]any {
	parameter := doSchemaObject(map[string]any{
		"kind": doSchemaEnum("string", "enum", "path"), "required": map[string]any{"type": "boolean"}, "example": playbookSchemaString(4096), "default": playbookSchemaString(4096),
		"allowed_values": playbookSchemaStrings(1, 32), "pattern": playbookSchemaString(512), "max_length": map[string]any{"type": "integer", "minimum": 1, "maximum": 4096},
	}, "kind", "required", "example")
	parameter["allOf"] = []any{
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"const": "string"}}}, "then": map[string]any{"required": []string{"pattern"}}},
		map[string]any{"if": map[string]any{"required": []string{"kind"}, "properties": map[string]any{"kind": map[string]any{"const": "enum"}}}, "then": map[string]any{"required": []string{"allowed_values"}}},
		map[string]any{"if": map[string]any{"required": []string{"required"}, "properties": map[string]any{"required": map[string]any{"const": false}}}, "then": map[string]any{"required": []string{"default"}}},
	}
	return map[string]any{"type": "object", "maxProperties": 32, "additionalProperties": false, "patternProperties": map[string]any{playbookParameterName.String(): parameter}, "description": "Nonsecret declared inputs. Use {{param:name}} in complete argv values or supported path/native input fields. PowerShell permits data values only after a fixed project script selected by -File; executable, host options and script paths remain fixed, and shell-expression interpolation is forbidden. Identity, tool names, scripts and dependencies remain fixed. Example values validate structure; they do not prove every parameter combination."}
}

func validatePlaybookVerificationInstance(root string, definition PlaybookDefinition, verification DoPlaybookValidationReceipt) error {
	if len(definition.Parameters) == 0 {
		if verification.InstanceDigest != "" || len(verification.Parameters) != 0 {
			return fmt.Errorf("legacy_method_has_foreign_parameter_verification")
		}
		return nil
	}
	resolved, bindings, err := resolvePlaybookDefinition(root, definition, verification.Parameters)
	if err != nil {
		return err
	}
	digest, err := playbookDefinitionDigest(resolved)
	if err != nil || digest != verification.InstanceDigest || !reflect.DeepEqual(bindings, verification.Parameters) {
		return fmt.Errorf("method_verification_instance_binding_mismatch")
	}
	return nil
}
