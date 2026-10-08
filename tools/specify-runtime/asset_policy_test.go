package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func assetTestWrite(t *testing.T, root, relative, content string) {
	t.Helper()
	absolute := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(absolute), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(absolute, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestAssetPolicyDefaultsAreReadOnly(t *testing.T) {
	root := t.TempDir()
	policy, err := NewAssetService(root).LoadPolicy("")
	if err != nil {
		t.Fatal(err)
	}
	if policy.SchemaVersion != 1 || policy.PolicyPath != "builtin" || policy.TemporaryRoot != ".specify/tmp/assets" {
		t.Fatalf("unexpected defaults: %#v", policy)
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("loading defaults created files: %v", entries)
	}
	if _, err := NewAssetService(root).LoadPolicy("missing-policy.json"); err == nil {
		t.Fatal("an explicitly missing policy must not use defaults")
	}
}

func TestAssetPolicyRejectsInvalidContracts(t *testing.T) {
	cases := []string{
		`{"schema_version":2}`,
		`{"schema_version":1,"schema_version":1}`,
		`{"schema_version":1,"unknown":true}`,
		`{"schema_version":1} {"schema_version":1}`,
		`{"schema_version":1,"roots":{"guide":"../outside"}}`,
		`{"schema_version":1,"roots":{"guide":".specify/features"}}`,
		`{"schema_version":1,"roots":{"guide":"src/docs"}}`,
		`{"schema_version":1,"roots":{"guide":"docs/manual","report":"docs/manual"}}`,
		`{"schema_version":1,"temporary_root":".assets/tmp"}`,
		`{"schema_version":1,"temporary_root":"assets"}`,
		`{"schema_version":1,"temporary_root":"src/temporary"}`,
		`{"schema_version":1,"temporary_retention":"forever"}`,
		`{"schema_version":1,"fixed_names":["../plan.md"]}`,
	}
	for _, raw := range cases {
		t.Run(raw, func(t *testing.T) {
			if _, err := decodeAssetPolicy([]byte(raw), assetDefaultPolicyPath); err == nil {
				t.Fatalf("invalid policy accepted: %s", raw)
			}
		})
	}
}

func TestAssetPolicyRespectsNativeAndOwnedPaths(t *testing.T) {
	root := t.TempDir()
	service := NewAssetService(root)
	policy, _ := service.LoadPolicy("")
	cases := []struct {
		path, kind                      string
		protected, temporary, compliant bool
	}{
		{".specify/features/2026-10-08-test/spec.md", "workflow-artifact", true, false, true},
		{".specify/features/2026-10-08-test/unknown-note.md", "protected", true, false, true},
		{".SPECIFY/features/test/note.md", "protected", true, false, true},
		{".specify/runtime/asset-governance/session.json", "protected", true, false, true},
		{".assets/records/catalog.md", "protected", true, false, true},
		{"templates/future/Bad_Name.md", "source", false, false, true},
		{"tests/fixtures/UPPER Case.svg", "source", false, false, true},
		{"src/assets/ApplicationLogo.svg", "source", false, false, true},
		{"docs/examples/fixtures/Expected.json", "source", false, false, true},
		{"docs/README.md", "document", false, false, true},
		{"README.zh-CN.md", "document", false, false, true},
		{"AGENTS.md", "configuration", true, false, true},
		{assetDefaultPolicyPath, "configuration", true, false, true},
		{"package.json", "other", false, false, true},
		{"docs/guides/start-here.md", "document", false, false, true},
		{"assets/site-logo.png", "media", false, false, true},
		{"report.md", "document", false, false, false},
		{"final_report.json", "document", false, false, false},
		{"summary.txt", "document", false, false, false},
		{"loose/report.md", "document", false, false, false},
		{"docs/Bad_Name.md", "document", false, false, false},
		{".specify/tmp/assets/task/worker/check-output.json", "temporary", false, true, true},
		{".specify/tmp/assets/task/check-output.json", "temporary", false, true, false},
		{"node_modules/demo/README.md", "cache", true, false, true},
	}
	for _, testcase := range cases {
		t.Run(testcase.path, func(t *testing.T) {
			classification, err := service.ClassifyPath(testcase.path, policy)
			if err != nil {
				t.Fatal(err)
			}
			if classification.Kind != testcase.kind || classification.Protected != testcase.protected || classification.Temporary != testcase.temporary || classification.Compliant != testcase.compliant {
				t.Fatalf("wrong classification: %#v", classification)
			}
		})
	}
}

func TestAssetPolicyExplicitExtensionsDoNotBypassOwners(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, assetDefaultPolicyPath, `{"schema_version":1,"roots":{"report":"project-records"},"fixed_names":["LEGACY.md"],"allowed_root_files":["report.md"],"protected_roots":["contracts"]}`)
	service := NewAssetService(root)
	policy, err := service.LoadPolicy("")
	if err != nil {
		t.Fatal(err)
	}
	for _, relative := range []string{"report.md", "docs/LEGACY.md", "project-records/check.md"} {
		classification, err := service.ClassifyPath(relative, policy)
		if err != nil || !classification.Compliant {
			t.Fatalf("explicit convention not recognized: %s %#v %v", relative, classification, err)
		}
	}
	classification, err := service.ClassifyPath("contracts/custom.md", policy)
	if err != nil || !classification.Protected {
		t.Fatalf("custom protected root lost: %#v %v", classification, err)
	}
	classification, err = service.ClassifyPath(".specify/unknown.md", policy)
	if err != nil || !classification.Protected {
		t.Fatalf("built-in protection was replaced by custom roots: %#v %v", classification, err)
	}
}

func TestAssetPathBoundariesAndCaseConflicts(t *testing.T) {
	root := t.TempDir()
	service := NewAssetService(root)
	policy, _ := service.LoadPolicy("")
	for _, relative := range []string{"../outside.md", "docs/../../outside.md", "/tmp/out.md", `C:\out.md`, `docs\out.md`, "docs/a\n.md", "assets/con.png", "assets/file.", "docs/space /file.md"} {
		if _, err := service.ClassifyPath(relative, policy); err == nil {
			t.Fatalf("unsafe path accepted: %q", relative)
		}
	}
	assetTestWrite(t, root, "docs/Existing.md", "content")
	classification, err := service.ClassifyPath("docs/existing.md", policy)
	if err != nil || classification.Compliant || !assetHasIssue(classification.Issues, "case-conflict") {
		t.Fatalf("case conflict missed: %#v %v", classification, err)
	}
	if runtime.GOOS != "windows" {
		outside := t.TempDir()
		if err := os.Symlink(outside, filepath.Join(root, "linked")); err != nil {
			t.Fatal(err)
		}
		if _, err := service.ClassifyPath("linked/private.md", policy); err == nil || !strings.Contains(err.Error(), "symlink") {
			t.Fatalf("symlink boundary not blocked: %v", err)
		}
		if err := os.Symlink(filepath.Join(outside, "policy.json"), filepath.Join(root, assetDefaultPolicyPath)); err != nil {
			t.Fatal(err)
		}
		if _, err := service.LoadPolicy(""); err == nil {
			t.Fatal("symlink policy accepted")
		}
	}
}

func TestAssetPolicyNestedRootsUseMostSpecificPurpose(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, assetDefaultPolicyPath, `{"schema_version":1,"roots":{"guide":"docs","decision":"docs/adr","architecture":"docs/architecture","reference":"docs/reference","report":"docs/reports","asset":"docs/assets"}}`)
	service := NewAssetService(root)
	policy, err := service.LoadPolicy("")
	if err != nil {
		t.Fatal(err)
	}
	cases := map[string]string{"docs/start.md": "guide", "docs/adr/0001-choice.md": "decision", "docs/architecture/runtime.md": "architecture", "docs/reference/api.md": "reference", "docs/reports/test-results.json": "report", "docs/assets/diagram.svg": "asset"}
	for repeat := 0; repeat < 20; repeat++ {
		for relative, purpose := range cases {
			classification, err := service.ClassifyPath(relative, policy)
			if err != nil || classification.Purpose != purpose || !classification.Compliant {
				t.Fatalf("nested route chose wrong owner: %s %#v %v", relative, classification, err)
			}
		}
	}
	policy, err = decodeAssetPolicy([]byte(`{"schema_version":1,"roots":{"guide":"docs/design"}}`), assetDefaultPolicyPath)
	if err != nil {
		t.Fatal(err)
	}
	classification, err := service.ClassifyPath("docs/design/contributing.md", policy)
	if err != nil || classification.Purpose != "guide" {
		t.Fatalf("explicit root did not override same-length built-in alias: %#v %v", classification, err)
	}
}

func assetHasIssue(issues []AssetIssue, code string) bool {
	for _, issue := range issues {
		if issue.Code == code {
			return true
		}
	}
	return false
}
