package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func doPrepareValidationFixture(t *testing.T) (string, doStartInput) {
	t.Helper()
	root, input := doFixture(t)
	input.Definition.Operation = "package"
	input.Definition.Steps[0].SideEffect = "local_write"
	input.Definition.Steps[0].SourceWrites = []string{"source.txt"}
	input.WriteScope = []string{"source.txt"}
	input.Definition.Checks = []PlaybookCheck{{ID: "requiredcheck", Purpose: "check the package command", Cwd: ".", Argv: []string{"git", "--version"}, DependsOn: []string{"run"}, Required: true, ExpectedResult: "exit zero", Kind: "exit_code"}}
	input.Definition = playbookNormalizeDefinition(input.Definition)
	return root, input
}

func doPrepareValidationStdin(t *testing.T, root string, input []byte) (int, Envelope, []byte) {
	t.Helper()
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	previous := os.Stdin
	os.Stdin = reader
	defer func() { os.Stdin = previous; _ = reader.Close(); _ = writer.Close() }()
	written := make(chan error, 1)
	go func() {
		_, err := writer.Write(input)
		if closeErr := writer.Close(); err == nil {
			err = closeErr
		}
		written <- err
	}()
	var stdout bytes.Buffer
	code := runDo([]string{"prepare", "--project-root", root, "--input-json", "-", "--format", "json"}, &stdout)
	_ = reader.Close()
	if err := <-written; err != nil {
		t.Fatal(err)
	}
	var envelope Envelope
	if err := json.Unmarshal(stdout.Bytes(), &envelope); err != nil {
		t.Fatalf("invalid JSON envelope: %v: %s", err, stdout.Bytes())
	}
	return code, envelope, stdout.Bytes()
}

func doPrepareValidationUnchanged(t *testing.T, root string, before map[string]string) {
	t.Helper()
	if after := doFastTree(t, root); !reflect.DeepEqual(before, after) {
		t.Fatalf("prepare wrote project files: %v", doFastTreeChanges(before, after))
	}
	for _, relative := range []string{".specify/do/sessions", ".specify/runtime/run-control"} {
		if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(relative))); !os.IsNotExist(err) {
			t.Fatalf("prepare created session or Work state at %s: %v", relative, err)
		}
	}
}

func TestDoPreparePackageSourceWriterStdinIsReadOnly(t *testing.T) {
	root, input := doPrepareValidationFixture(t)
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	before := doFastTree(t, root)
	code, envelope, output := doPrepareValidationStdin(t, root, raw)
	if code != 0 || envelope.Status != "ok" || envelope.Data["start_input"] == nil {
		t.Fatalf("valid local package definition rejected: %d %s", code, output)
	}
	doPrepareValidationUnchanged(t, root, before)
}

func TestDoPrepareNestedValidationDiagnostics(t *testing.T) {
	const secretValue = "private-input-value-must-not-appear"
	const argvValue = "private-argv-value-must-not-appear"
	for _, test := range []struct {
		name    string
		mutate  func(map[string]any)
		path    string
		keyword string
	}{
		{"step_type", func(def map[string]any) { def["steps"].([]any)[0].(map[string]any)["required"] = secretValue }, "/definition/steps/0/required", "type"},
		{"step_required_null", func(def map[string]any) { def["steps"].([]any)[0].(map[string]any)["required"] = nil }, "/definition/steps/0/required", "type"},
		{"step_unknown_field", func(def map[string]any) { def["steps"].([]any)[0].(map[string]any)["unexpected"] = secretValue }, "/definition/steps/0/unexpected", "additionalProperties"},
		{"step_unknown_escaped_field", func(def map[string]any) {
			def["steps"].([]any)[0].(map[string]any)["unexpected/path~part"] = secretValue
		}, "/definition/steps/0/unexpected~1path~0part", "additionalProperties"},
		{"step_argv_element_type", func(def map[string]any) { def["steps"].([]any)[0].(map[string]any)["argv"] = []any{"git", 42} }, "/definition/steps/0/argv/1", "type"},
		{"native_arguments_null", func(def map[string]any) {
			step := def["steps"].([]any)[0].(map[string]any)
			delete(step, "cwd")
			delete(step, "argv")
			step["native_action"] = map[string]any{"kind": "file", "tool": "test.adapter.write", "target": "source.txt", "arguments": nil}
		}, "/definition/steps/0/native_action/arguments", "type"},
		{"learning_refs_type", func(def map[string]any) { def["learning_refs"] = secretValue }, "/definition/learning_refs", "type"},
		{"learning_refs_null", func(def map[string]any) { def["learning_refs"] = nil }, "/definition/learning_refs", "type"},
		{"learning_refs_missing", func(def map[string]any) { delete(def, "learning_refs") }, "/definition/learning_refs", "required"},
		{"check_cwd_missing", func(def map[string]any) {
			check := def["checks"].([]any)[0].(map[string]any)
			check["kind"], check["result_path"], check["argv"] = "file", "out/package.zip", []any{}
			delete(check, "cwd")
		}, "/definition/checks/0/cwd", "required"},
		{"check_argv_missing", func(def map[string]any) {
			check := def["checks"].([]any)[0].(map[string]any)
			check["kind"], check["result_path"] = "file", "out/package.zip"
			delete(check, "argv")
		}, "/definition/checks/0/argv", "required"},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, input := doPrepareValidationFixture(t)
			raw, err := json.Marshal(input)
			if err != nil {
				t.Fatal(err)
			}
			var payload map[string]any
			if err := json.Unmarshal(raw, &payload); err != nil {
				t.Fatal(err)
			}
			definition := payload["definition"].(map[string]any)
			definition["steps"].([]any)[0].(map[string]any)["argv"] = []any{"git", argvValue}
			test.mutate(definition)
			raw, err = json.Marshal(payload)
			if err != nil {
				t.Fatal(err)
			}
			before := doFastTree(t, root)
			code, envelope, output := doPrepareValidationStdin(t, root, raw)
			if code == 0 || envelope.Status == "ok" {
				t.Fatalf("malformed input accepted: %d %s", code, output)
			}
			doPrepareValidationUnchanged(t, root, before)
			for _, private := range []string{secretValue, argvValue} {
				if bytes.Contains(output, []byte(private)) {
					t.Fatal("diagnostic exposed an input value")
				}
			}
			issues, ok := envelope.Data["validation_errors"].([]any)
			if !ok || len(issues) == 0 {
				t.Fatalf("no machine-readable nested validation errors: %s", output)
			}
			matched := false
			for _, value := range issues {
				issue, ok := value.(map[string]any)
				if !ok {
					t.Fatalf("validation error is not an object: %#v", value)
				}
				message, _ := issue["message"].(string)
				if issue["instance_path"] == test.path && issue["keyword"] == test.keyword && strings.TrimSpace(message) != "" {
					matched = true
				}
			}
			if !matched {
				t.Fatalf("missing %s %s diagnostic: %s", test.path, test.keyword, output)
			}
			if len(envelope.ShowArgv) != 0 || bytes.Contains(output, []byte("inspect the exact session")) {
				t.Fatalf("pre-session validation directed recovery to a nonexistent session: %s", output)
			}
			schemaArgv, _ := json.Marshal(envelope.Data["schema_argv"])
			if !bytes.Contains(schemaArgv, []byte("do-prepare-input")) {
				t.Fatalf("missing prepare schema recovery action: %s", output)
			}
			guidance, _ := json.Marshal(envelope.Blockers)
			if !bytes.Contains(guidance, []byte("input")) && !bytes.Contains(guidance, []byte("prepare")) {
				t.Fatalf("no actionable input repair/resume guidance: %s", guidance)
			}
		})
	}
}

func TestDoPrepareDiagnosticsPreserveActualNullObservation(t *testing.T) {
	var observation DoNativeObservation
	if err := decodePlaybookJSON([]byte(`{"outcome":"passed","result":null}`), &observation); err != nil {
		t.Fatalf("actual null observation rejected: %v", err)
	}
	err := decodePlaybookJSON([]byte(`{"outcome":42,"result":null}`), &observation)
	var inputError *playbookJSONInputError
	if !errors.As(err, &inputError) || len(inputError.Issues) != 1 || inputError.Issues[0].InstancePath != "/outcome" {
		t.Fatalf("valid null was diagnosed instead of the invalid outcome: %v", err)
	}
}

func TestDoPrepareInputDecoderKeepsSupportedVariants(t *testing.T) {
	_, input := doPrepareValidationFixture(t)
	for _, test := range []struct {
		name   string
		mutate func(map[string]any)
		check  func(*testing.T, doStartInput)
	}{
		{"expected_json_null", func(payload map[string]any) {
			check := payload["definition"].(map[string]any)["checks"].([]any)[0].(map[string]any)
			check["kind"], check["result_path"], check["argv"], check["expected_json"] = "json", "out/report.json", []any{}, nil
		}, func(t *testing.T, decoded doStartInput) {
			if string(decoded.Definition.Checks[0].ExpectedJSON) != "null" {
				t.Fatal("lost the intentional JSON null assertion")
			}
		}},
		{"native_action_without_process_fields", func(payload map[string]any) {
			definition := payload["definition"].(map[string]any)
			for _, entry := range []map[string]any{definition["steps"].([]any)[0].(map[string]any), definition["checks"].([]any)[0].(map[string]any)} {
				delete(entry, "cwd")
				delete(entry, "argv")
				entry["native_action"] = map[string]any{"kind": "file", "tool": "test.adapter.read", "target": "source.txt", "arguments": map[string]any{}}
			}
			check := definition["checks"].([]any)[0].(map[string]any)
			check["kind"], check["expected_json"] = "observation", nil
		}, func(t *testing.T, decoded doStartInput) {
			if decoded.Definition.Steps[0].NativeAction == nil || decoded.Definition.Checks[0].NativeAction == nil {
				t.Fatal("native actions were lost during decoding")
			}
		}},
		{"method_binding_without_inline_definition", func(payload map[string]any) {
			delete(payload, "definition")
			payload["method_binding"] = map[string]any{"id": "pb-package-0123456789abcdef", "revision": 1, "content_digest": strings.Repeat("a", 64)}
		}, func(t *testing.T, decoded doStartInput) {
			if decoded.MethodBinding == nil || decoded.Definition.Goal != "" {
				t.Fatal("method-only input was not preserved")
			}
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			raw, err := json.Marshal(input)
			if err != nil {
				t.Fatal(err)
			}
			var payload map[string]any
			if err := json.Unmarshal(raw, &payload); err != nil {
				t.Fatal(err)
			}
			test.mutate(payload)
			raw, err = json.Marshal(payload)
			if err != nil {
				t.Fatal(err)
			}
			var decoded doStartInput
			if err := doReadInput(string(raw), &decoded); err != nil {
				t.Fatalf("diagnostic change rejected supported input: %v", err)
			}
			test.check(t, decoded)
		})
	}
}
