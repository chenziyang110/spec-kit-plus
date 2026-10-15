package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// This is a persisted-state shape check, not an acceptance or permission gate.
// Reflect the actual runtime types so newly serialized fields cannot silently
// drift out of the strict schema shipped into generated projects.
func TestQuickConfirmationExecutionSchemaMatchesRuntime(t *testing.T) {
	raw, err := os.ReadFile(filepath.Join("..", "..", "templates", "quick-confirmation-schema.json"))
	if err != nil {
		t.Fatal(err)
	}
	var schema map[string]any
	if err := json.Unmarshal(raw, &schema); err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		name  string
		value any
		path  []string
	}{
		{"execution", quickConfirmationExecution{}, []string{"properties", "execution"}},
		{"work_item_status", quickWorkItemStatus{}, []string{"properties", "execution", "properties", "work_item_status", "items"}},
		{"blocked_dispatch", quickBlockedDispatch{}, []string{"properties", "execution", "properties", "blocked_dispatch"}},
	} {
		t.Run(test.name, func(t *testing.T) {
			node := schema
			for _, key := range test.path {
				node = quickExecutionSchemaObject(t, node, key)
			}
			if node["additionalProperties"] != false {
				t.Fatal("persisted execution objects must reject unknown fields")
			}
			declared := quickExecutionSchemaObject(t, node, "properties")
			typ := reflect.TypeOf(test.value)
			names := map[string]bool{}
			for index := 0; index < typ.NumField(); index++ {
				field := typ.Field(index)
				name := strings.Split(field.Tag.Get("json"), ",")[0]
				if name == "" || name == "-" || !field.IsExported() {
					continue
				}
				names[name] = true
				property, ok := declared[name].(map[string]any)
				if !ok {
					t.Errorf("runtime field %s.%s (%s) is missing from persisted schema", typ.Name(), field.Name, name)
					continue
				}
				kind := field.Type.Kind()
				if kind == reflect.Pointer {
					kind = field.Type.Elem().Kind()
				}
				want := map[reflect.Kind]string{
					reflect.String: "string", reflect.Bool: "boolean",
					reflect.Int:   "integer",
					reflect.Slice: "array", reflect.Struct: "object",
				}[kind]
				if want == "" {
					t.Fatalf("new runtime kind %s needs an explicit schema type check", kind)
				}
				matches := property["type"] == want
				if types, ok := property["type"].([]any); ok {
					for _, candidate := range types {
						matches = matches || candidate == want
					}
				}
				if !matches {
					t.Errorf("%s.%s schema type = %v; need %s", typ.Name(), field.Name, property["type"], want)
				}
			}
			for name := range declared {
				if !names[name] {
					t.Errorf("schema field %q has no serialized runtime field", name)
				}
			}
		})
	}
}

func quickExecutionSchemaObject(t *testing.T, parent map[string]any, key string) map[string]any {
	t.Helper()
	value, ok := parent[key].(map[string]any)
	if !ok {
		t.Fatalf("missing schema object %q", key)
	}
	return value
}
