package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
	"sort"
	"strconv"
	"strings"
)

// Diagnostics describe rejected JSON, never command arguments or submitted values.
// This is a failure-only shape inspection, not a second schema validator: the
// existing strict decoder and semantic validators remain the admission owners.
type playbookJSONIssue struct {
	InstancePath string `json:"instance_path"`
	Keyword      string `json:"keyword"`
	Message      string `json:"message"`
}

type playbookJSONInputError struct {
	Issues []playbookJSONIssue
	cause  error
}

func (err *playbookJSONInputError) Error() string {
	issue := err.Issues[0]
	return fmt.Sprintf("playbook_json_schema_invalid: pointer=%s: %s", issue.InstancePath, issue.Message)
}

func (err *playbookJSONInputError) Unwrap() error { return err.cause }

func playbookDescribeJSONError(raw []byte, target any, cause error) error {
	var value any
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	issues := []playbookJSONIssue{}
	if decoder.Decode(&value) == nil {
		playbookInspectJSONShape(value, reflect.TypeOf(target), "", &issues)
	}
	if len(issues) == 0 {
		issues = append(issues, playbookJSONIssue{Keyword: "decode", Message: "input cannot be decoded using the published field types and required fields"})
	}
	return &playbookJSONInputError{Issues: issues, cause: cause}
}

func playbookJSONPointer(parent, name string) string {
	return parent + "/" + strings.ReplaceAll(strings.ReplaceAll(name, "~", "~0"), "/", "~1")
}

// Required property names come from the very schemas exposed by api schema.
// Native actions intentionally carry arbitrary JSON arguments/result values.
func playbookJSONRequired(t reflect.Type, object map[string]any) []string {
	var schema map[string]any
	switch t {
	case reflect.TypeOf(PlaybookDefinition{}):
		schema = playbookDefinitionInputSchema()
	case reflect.TypeOf(PlaybookStep{}):
		schema = playbookActionSchema(false)
	case reflect.TypeOf(PlaybookCheck{}):
		schema = playbookActionSchema(true)
	case reflect.TypeOf(PlaybookNativeAction{}):
		return []string{"kind", "tool", "target", "arguments"}
	case reflect.TypeOf(DoNativeObservation{}):
		return []string{"outcome", "result"}
	}
	if schema == nil {
		return nil
	}
	required, _ := schema["required"].([]string)
	required = append([]string{}, required...)
	if (t == reflect.TypeOf(PlaybookStep{}) || t == reflect.TypeOf(PlaybookCheck{})) && object["native_action"] == nil {
		required = append(required, "cwd", "argv")
	}
	return required
}

func playbookInspectJSONShape(value any, t reflect.Type, pointer string, issues *[]playbookJSONIssue) {
	const maxIssues = 12
	if t == nil || len(*issues) >= maxIssues || t == reflect.TypeOf(json.RawMessage{}) {
		return
	}
	for t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	// Optional nulls keep their existing decoder semantics. Required nulls are
	// reported by the owning object's presence check below.
	if value == nil || t.Kind() == reflect.Interface {
		return
	}
	add := func(keyword, message string) {
		if len(*issues) < maxIssues {
			*issues = append(*issues, playbookJSONIssue{InstancePath: pointer, Keyword: keyword, Message: message})
		}
	}
	switch t.Kind() {
	case reflect.Struct:
		object, ok := value.(map[string]any)
		if !ok {
			add("type", "expected an object")
			return
		}
		fields := map[string]reflect.Type{}
		for i := 0; i < t.NumField(); i++ {
			field := t.Field(i)
			if field.PkgPath != "" {
				continue
			}
			name := strings.Split(field.Tag.Get("json"), ",")[0]
			if name == "-" {
				continue
			}
			if name == "" {
				name = field.Name
			}
			fields[name] = field.Type
		}
		for _, name := range playbookJSONRequired(t, object) {
			v, exists := object[name]
			if !exists {
				if len(*issues) < maxIssues {
					*issues = append(*issues, playbookJSONIssue{InstancePath: playbookJSONPointer(pointer, name), Keyword: "required", Message: "required property is missing"})
				}
			} else if v == nil && !(t == reflect.TypeOf(DoNativeObservation{}) && name == "result") && len(*issues) < maxIssues {
				*issues = append(*issues, playbookJSONIssue{InstancePath: playbookJSONPointer(pointer, name), Keyword: "type", Message: "required property must not be null"})
			}
		}
		for _, name := range playbookJSONKeys(object) {
			fieldType, known := fields[name]
			if !known {
				// encoding/json accepts case-insensitive field matches; do not
				// invent an additional rejection when diagnosing another field.
				for fieldName, candidate := range fields {
					if strings.EqualFold(name, fieldName) {
						fieldType, known = candidate, true
						break
					}
				}
			}
			childPath := playbookJSONPointer(pointer, name)
			if !known {
				if len(*issues) < maxIssues {
					*issues = append(*issues, playbookJSONIssue{InstancePath: childPath, Keyword: "additionalProperties", Message: "unknown property; remove it or use a property from the published schema"})
				}
				continue
			}
			playbookInspectJSONShape(object[name], fieldType, childPath, issues)
		}
	case reflect.Map:
		object, ok := value.(map[string]any)
		if !ok {
			add("type", "expected an object")
			return
		}
		for _, name := range playbookJSONKeys(object) {
			playbookInspectJSONShape(object[name], t.Elem(), playbookJSONPointer(pointer, name), issues)
		}
	case reflect.Slice, reflect.Array:
		array, ok := value.([]any)
		if !ok {
			add("type", "expected an array")
			return
		}
		for i, item := range array {
			playbookInspectJSONShape(item, t.Elem(), playbookJSONPointer(pointer, strconv.Itoa(i)), issues)
			if len(*issues) >= maxIssues {
				break
			}
		}
	case reflect.String:
		if _, ok := value.(string); !ok {
			add("type", "expected a string")
		}
	case reflect.Bool:
		if _, ok := value.(bool); !ok {
			add("type", "expected a boolean")
		}
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		number, ok := value.(json.Number)
		if !ok {
			add("type", "expected an integer")
		} else if _, err := strconv.ParseInt(string(number), 10, t.Bits()); err != nil {
			add("type", "expected an integer within the supported range")
		}
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		number, ok := value.(json.Number)
		if !ok {
			add("type", "expected a nonnegative integer")
		} else if _, err := strconv.ParseUint(string(number), 10, t.Bits()); err != nil {
			add("type", "expected a nonnegative integer within the supported range")
		}
	}
}

func playbookJSONKeys(object map[string]any) []string {
	keys := make([]string, 0, len(object))
	for name := range object {
		keys = append(keys, name)
	}
	sort.Strings(keys)
	return keys
}
