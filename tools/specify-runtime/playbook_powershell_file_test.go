package main

import (
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
	"testing"
)

func TestPlaybookPowerShellFileParametersRemainBoundScriptData(t *testing.T) {
	root, input := playbookFixture(t)
	const script = "scripts/package.ps1"
	if err := os.MkdirAll(filepath.Join(root, "scripts"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(script)), []byte("param([string]$Revision)\nWrite-Output $Revision\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, test := range []struct {
		name, cwd string
		argv      []string
	}{
		{"pwsh", ".", []string{"pwsh", "-File", script, "-Revision", "{{param:revision}}"}},
		{"windows-powershell", ".", []string{"powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Revision", "{{param:revision}}"}},
		{"cwd-relative", "scripts", []string{"pwsh", "-File", "package.ps1", "-Revision", "{{param:revision}}"}},
		{"windows-script-separators", ".", []string{"pwsh", "-File", `.\scripts\package.ps1`, "-Revision", "{{param:revision}}"}},
	} {
		t.Run(test.name, func(t *testing.T) {
			definition := playbookNormalizeDefinition(input.Definition)
			definition.Parameters = map[string]PlaybookParameter{"revision": {Kind: "string", Required: true, Example: "r375", Pattern: `r[0-9]+`}}
			definition.Steps[0].Cwd, definition.Steps[0].Argv = test.cwd, test.argv
			resolved, bindings, err := resolvePlaybookDefinition(root, definition, map[string]string{"revision": "r376"})
			if err != nil {
				t.Fatal(err)
			}
			want := append([]string{}, test.argv...)
			want[len(want)-1] = "r376"
			if !reflect.DeepEqual(resolved.Steps[0].Argv, want) || bindings["revision"] != "r376" {
				t.Fatalf("script data changed: argv=%q bindings=%v", resolved.Steps[0].Argv, bindings)
			}
			fingerprint, err := playbookSourceFingerprint(root, resolved)
			if err != nil || fingerprint[script] == "" {
				t.Fatalf("fixed script was not source-bound: %v, %v", fingerprint, err)
			}
		})
	}
	for _, test := range []struct {
		name, value string
		argv        []string
	}{
		{"executable", "pwsh", []string{"{{param:revision}}", "-File", script}},
		{"script", script, []string{"pwsh", "-File", "{{param:revision}}"}},
		{"host-option", "-NoProfile", []string{"pwsh", "{{param:revision}}", "-File", script}},
		{"host-option-value", "Bypass", []string{"pwsh", "-ExecutionPolicy", "{{param:revision}}", "-File", script}},
		{"command", "r376", []string{"pwsh", "-Command", "{{param:revision}}"}},
		{"encoded-command", "r376", []string{"pwsh", "-EncodedCommand", "{{param:revision}}"}},
		{"command-before-file", "r376", []string{"pwsh", "-Command", "noop", "-File", script, "{{param:revision}}"}},
		{"command-with-args", "r376", []string{"pwsh", "-CommandWithArgs", "noop", "{{param:revision}}"}},
		{"working-directory-option", "r376", []string{"pwsh", "-WorkingDirectory", "scripts", "-File", "package.ps1", "{{param:revision}}"}},
		{"missing-script", "r376", []string{"pwsh", "-File", "scripts/missing.ps1", "{{param:revision}}"}},
		{"external-script", "r376", []string{"pwsh", "-File", "../package.ps1", "{{param:revision}}"}},
		{"dynamic-script", "r376", []string{"pwsh", "-File", "$env:PACKAGE.ps1", "{{param:revision}}"}},
		{"script-option-substitution", "-Command", []string{"pwsh", "-File", script, "{{param:revision}}"}},
		{"embedded-expression", "r376", []string{"pwsh", "-File", script, "$({{param:revision}})"}},
		{"embedded-option", "r376", []string{"pwsh", "-File", script, "-Revision={{param:revision}}"}},
		{"other-shell", "r376", []string{"bash", "-File", script, "{{param:revision}}"}},
	} {
		t.Run("reject-"+test.name, func(t *testing.T) {
			definition := playbookNormalizeDefinition(input.Definition)
			definition.Parameters = map[string]PlaybookParameter{"revision": {Kind: "string", Required: true, Example: "r375", Pattern: `.+`}}
			definition.Steps[0].Argv = test.argv
			_, _, err := resolvePlaybookDefinition(root, definition, map[string]string{"revision": test.value})
			if err == nil || !strings.Contains(err.Error(), "playbook_parameter_") {
				t.Fatalf("unsafe parameter placement accepted: %v", err)
			}
		})
	}
}

func TestPlaybookPowerShellFileParameterCannotRetargetScriptThroughCwd(t *testing.T) {
	root, input := playbookFixture(t)
	if err := os.MkdirAll(filepath.Join(root, "scripts"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "scripts/package.ps1"), []byte("param([string]$Revision)\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	definition := playbookNormalizeDefinition(input.Definition)
	definition.Parameters = map[string]PlaybookParameter{
		"directory": {Kind: "path", Required: true, Example: "scripts"},
		"revision":  {Kind: "string", Required: true, Example: "r376", Pattern: `r[0-9]+`},
	}
	definition.Steps[0].Cwd = "{{param:directory}}"
	definition.Steps[0].Argv = []string{"pwsh", "-File", "package.ps1", "-Revision", "{{param:revision}}"}
	bindings := map[string]string{"directory": "scripts", "revision": "r376"}
	if _, _, err := resolvePlaybookDefinition(root, definition, bindings); err == nil || !strings.Contains(err.Error(), "shell_command_expansion_forbidden") {
		t.Fatalf("parameterized cwd selected a parameterized PowerShell script: %v", err)
	}
	for _, argv := range [][]string{
		{"pwsh", "-File", "package.ps1", "-Revision", "r376"},
		{"tool", "{{param:revision}}"},
	} {
		definition.Steps[0].Argv = argv
		if _, _, err := resolvePlaybookDefinition(root, definition, bindings); err != nil {
			t.Fatalf("existing cwd parameter flow was restricted: %v", err)
		}
	}
}

func TestPlaybookParameterSchemaPublishesRuntimeRequirements(t *testing.T) {
	parameter := playbookParameterSchema()["patternProperties"].(map[string]any)[playbookParameterName.String()].(map[string]any)
	conditions := parameter["allOf"].([]any)
	requirements := map[string]string{}
	for _, item := range conditions {
		condition := item.(map[string]any)
		properties := condition["if"].(map[string]any)["properties"].(map[string]any)
		for field, raw := range properties {
			value := raw.(map[string]any)["const"]
			key := field
			if text, ok := value.(string); ok {
				key += ":" + text
			} else if value != false {
				t.Fatalf("unexpected schema condition: %v", condition)
			}
			requirements[key] = condition["then"].(map[string]any)["required"].([]string)[0]
		}
	}
	if !reflect.DeepEqual(requirements, map[string]string{"kind:string": "pattern", "kind:enum": "allowed_values", "required": "default"}) {
		t.Fatalf("schema omitted parameter requirements: %v", requirements)
	}
	properties := parameter["properties"].(map[string]any)
	if properties["pattern"].(map[string]any)["minLength"] != 1 || properties["allowed_values"].(map[string]any)["minItems"] != 1 {
		t.Fatal("required parameter constraints allow empty values")
	}
	err := validatePlaybookParameter(t.TempDir(), "revision", PlaybookParameter{Kind: "string", Required: true, Example: "r376"}, "r376")
	if err == nil || !strings.Contains(err.Error(), "pointer=/parameters/revision/pattern") {
		t.Fatalf("missing string pattern lacks repair location: %v", err)
	}
	for _, allowEmpty := range []bool{false, true} {
		schema := playbookCwdSchema(allowEmpty)
		pattern, err := regexp.Compile(schema["pattern"].(string))
		if err != nil {
			t.Fatal(err)
		}
		for _, cwd := range []string{".", "src/tool", ".github/tools", "中文/工具", "{{param:directory}}", "out/prefix-{{param:revision}}"} {
			if !pattern.MatchString(cwd) {
				t.Errorf("valid cwd rejected by schema: %q", cwd)
			}
		}
		for _, cwd := range []string{"/absolute", "D:/work/project", `D:\work`, `\\server\share`, "..", "../outside", "src/../tool", "./src", "src/./tool", "src//tool", "src/", "src\ntool"} {
			if pattern.MatchString(cwd) {
				t.Errorf("noncanonical cwd admitted by schema: %q", cwd)
			}
		}
		if pattern.MatchString("") != allowEmpty {
			t.Fatal("native empty cwd exception leaked into process cwd")
		}
	}
}
