package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func assetCatalogTestPython(t *testing.T) string {
	t.Helper()
	for _, name := range []string{"python3", "python"} {
		if binary, err := exec.LookPath(name); err == nil {
			return binary
		}
	}
	t.Skip("fake AssetKit script test requires a Python interpreter; no real AssetKit interoperability is claimed")
	return ""
}

func assetCatalogTestWrite(t *testing.T, root, relative, content string) {
	t.Helper()
	target := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func assetCatalogTestInstall(t *testing.T, root, script string) {
	t.Helper()
	assetCatalogTestWrite(t, root, ".assets/ak.py", script)
	assetCatalogTestWrite(t, root, ".assets/config.json", "{}\n")
	if err := os.MkdirAll(filepath.Join(root, ".assets", "records"), 0o755); err != nil {
		t.Fatal(err)
	}
}

func assetCatalogTestGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("AssetKit baseline validation requires Git")
	}
	command := exec.Command(git, args...)
	command.Dir = root
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("Git fixture %v: %s (%v)", args, output, err)
	}
	return strings.TrimSpace(string(output))
}

func assetCatalogTestBaseline(t *testing.T, root string) string {
	t.Helper()
	assetCatalogTestGit(t, root, "init", "--quiet")
	assetCatalogTestWrite(t, root, "README.md", "# Baseline\n")
	assetCatalogTestGit(t, root, "add", "README.md")
	assetCatalogTestGit(t, root, "-c", "user.name=Asset Test", "-c", "user.email=asset@example.invalid", "commit", "--quiet", "-m", "fixture")
	return assetCatalogTestGit(t, root, "rev-parse", "HEAD")
}

func assetCatalogTestArgv(t *testing.T, envelope Envelope) []string {
	t.Helper()
	result, ok := envelope.Data["adapter_result"].(map[string]any)
	if !ok {
		t.Fatalf("missing adapter result: %+v", envelope)
	}
	values, ok := result["argv"].([]any)
	if !ok {
		t.Fatalf("missing adapter argv: %+v", result)
	}
	argv := make([]string, len(values))
	for index, value := range values {
		argv[index], ok = value.(string)
		if !ok {
			t.Fatalf("non-string argv: %#v", value)
		}
	}
	return argv
}

func TestAssetCatalogDisabledAndMissingInstallationDoNotBootstrap(t *testing.T) {
	root := t.TempDir()
	service := NewAssetService(root)
	result := service.Catalog(AssetCatalogRequest{Operation: "find", Query: "hero"})
	if result.Status != "ok" || result.Data["adapter_status"] != "disabled" || result.Data["executed"] != false {
		t.Fatalf("disabled adapter reported execution: %+v", result)
	}
	result = service.Catalog(AssetCatalogRequest{Enabled: true, Operation: "find", Query: "hero"})
	if result.Status != "blocked" || result.Data["adapter_status"] != "adapter-unavailable" || result.Data["executed"] != false {
		t.Fatalf("missing adapter was not reported accurately: %+v", result)
	}
	entries, err := os.ReadDir(root)
	if err != nil || len(entries) != 0 {
		t.Fatalf("disabled/missing adapter wrote project files: %v (%v)", entries, err)
	}
}

func TestAssetCatalogFakeAdapterReceivesLiteralArgvAndExplicitBaseline(t *testing.T) {
	python := assetCatalogTestPython(t)
	root := t.TempDir()
	baseline := assetCatalogTestBaseline(t, root)
	assetCatalogTestInstall(t, root, "import json, os, sys\nprint(json.dumps({'ok': True, 'argv': sys.argv[1:], 'cwd': os.getcwd()}))\n")
	service := NewAssetService(root)
	query := "--help $(touch unexpected) ; quoted 'resource'"
	result := service.Catalog(AssetCatalogRequest{Enabled: true, Python: python, Operation: "find", Query: query})
	if result.Status != "ok" {
		t.Fatalf("fake find failed: %+v", result)
	}
	if got := assetCatalogTestArgv(t, result); !reflect.DeepEqual(got, []string{"find", "--budget=2048", "--", query}) {
		t.Fatalf("query was reinterpreted: %#v", got)
	}
	if _, err := os.Stat(filepath.Join(root, "unexpected")); !os.IsNotExist(err) {
		t.Fatal("literal shell syntax produced a side effect")
	}
	for _, operation := range []string{"get", "check"} {
		request := AssetCatalogRequest{Enabled: true, Python: python, Operation: operation, Reference: "@abc123", Since: "HEAD"}
		result = service.Catalog(request)
		if result.Status != "ok" {
			t.Fatalf("fake %s failed: %+v", operation, result)
		}
		want := []string{"get", "--budget=2048", "--", "@abc123"}
		if operation == "check" {
			want = []string{"check", "--budget=1024", "--since=" + baseline}
			if result.Data["baseline_ref"] != "HEAD" || result.Data["baseline_commit"] != baseline {
				t.Fatalf("adapter did not expose its pinned baseline: %+v", result)
			}
		}
		if got := assetCatalogTestArgv(t, result); !reflect.DeepEqual(got, want) {
			t.Fatalf("wrong %s argv: %#v", operation, got)
		}
	}
	result = service.Catalog(AssetCatalogRequest{Enabled: true, Python: python, Operation: "check"})
	if result.Status != "blocked" || result.Data["executed"] != false {
		t.Fatalf("missing baseline was accepted: %+v", result)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
		t.Fatal("catalog created a second runtime ledger")
	}
}

func TestAssetCatalogRejectsMissingNonCommitAndForeignGitBaselinesBeforeBackend(t *testing.T) {
	for _, scenario := range []string{"no-git", "missing-ref", "non-commit", "nested-project", "option-like-ref"} {
		t.Run(scenario, func(t *testing.T) {
			root := t.TempDir()
			since := "HEAD"
			if scenario != "no-git" {
				assetCatalogTestBaseline(t, root)
			}
			switch scenario {
			case "missing-ref":
				since = "refs/heads/nonexistent"
			case "non-commit":
				since = "HEAD:README.md"
			case "nested-project":
				root = filepath.Join(root, "child-project")
				if err := os.Mkdir(root, 0o755); err != nil {
					t.Fatal(err)
				}
			case "option-like-ref":
				since = "--help"
			}
			assetCatalogTestInstall(t, root, "import json\nopen('unexpected-backend-execution', 'w').write('executed')\nprint(json.dumps({'ok': True}))\n")
			result := NewAssetService(root).Catalog(AssetCatalogRequest{Enabled: true, Operation: "check", Since: since})
			if result.Status != "blocked" || result.Data["adapter_status"] != "adapter-baseline-invalid" || result.Data["executed"] != false {
				t.Fatalf("invalid baseline reached the backend: %+v", result)
			}
			if _, err := os.Stat(filepath.Join(root, "unexpected-backend-execution")); !os.IsNotExist(err) {
				t.Fatal("invalid baseline executed the fake adapter")
			}
		})
	}
}

func TestAssetCatalogFindMatchesAssetKitCharacterAndKeywordLimits(t *testing.T) {
	python := assetCatalogTestPython(t)
	for _, scenario := range []struct {
		name, query string
		allowed     bool
	}{
		{"unicode-200-characters", strings.Repeat("图", 200), true},
		{"unicode-201-characters", strings.Repeat("图", 201), false},
		{"twelve-keywords", strings.TrimSpace(strings.Repeat("hero ", 12)), true},
		{"thirteen-keywords", strings.TrimSpace(strings.Repeat("hero ", 13)), false},
		{"python-whitespace-twelve", strings.TrimSuffix(strings.Repeat("hero\x1c", 12), "\x1c"), true},
		{"python-whitespace-thirteen", strings.TrimSuffix(strings.Repeat("hero\x1c", 13), "\x1c"), false},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			root := t.TempDir()
			assetCatalogTestInstall(t, root, "import json,sys\nopen('adapter-called', 'w').write('called')\nprint(json.dumps({'ok': True, 'argv': sys.argv[1:]}))\n")
			result := NewAssetService(root).Catalog(AssetCatalogRequest{Enabled: true, Python: python, Operation: "find", Query: scenario.query})
			_, calledErr := os.Stat(filepath.Join(root, "adapter-called"))
			if scenario.allowed {
				if result.Status != "ok" || calledErr != nil {
					t.Fatalf("valid query was rejected: %+v (%v)", result, calledErr)
				}
			} else if result.Status != "blocked" || result.Data["executed"] != false || !os.IsNotExist(calledErr) {
				t.Fatalf("query outside upstream limits reached the adapter: %+v (%v)", result, calledErr)
			}
		})
	}
}

func TestAssetCatalogPolicyOptInAndPutMetadataRemainStructured(t *testing.T) {
	python := assetCatalogTestPython(t)
	root := t.TempDir()
	assetCatalogTestInstall(t, root, "import json, sys\nprint(json.dumps({'ok': True, 'argv': sys.argv[1:]}))\n")
	assetCatalogTestWrite(t, root, "public/hero.png", "image")
	raw, err := json.Marshal(map[string]any{"schema_version": 1, "assetkit": AssetKitPolicy{Enabled: true, Python: python}})
	if err != nil {
		t.Fatal(err)
	}
	assetCatalogTestWrite(t, root, ".asset-policy.json", string(raw))
	result := NewAssetService(root).Catalog(AssetCatalogRequest{Operation: "put", Path: "public/hero.png", Use: "Homepage visual",
		SourceKind: "generated", SourceRef: "--literal-ref;$(noop)", License: "project approval", ExpectRevision: 3})
	if result.Status != "ok" {
		t.Fatalf("policy opt-in put failed: %+v", result)
	}
	want := []string{"put", "--budget=1024", "--use=Homepage visual", "--expect-revision=3", "--source-kind=generated", "--source-ref=--literal-ref;$(noop)", "--license=project approval", "--", "public/hero.png"}
	if got := assetCatalogTestArgv(t, result); !reflect.DeepEqual(got, want) {
		t.Fatalf("put parameters drifted: %#v", got)
	}
}

func TestAssetCatalogPutRejectsOwnedTransientSourceAndUnroutedFilesBeforeExecution(t *testing.T) {
	root := t.TempDir()
	assetCatalogTestInstall(t, root, "raise RuntimeError('must not execute')\n")
	paths := []string{
		".specify/features/2026-10-08-test/spec.md", ".specify/design/changes/change/previews/approved.png",
		".specify/tmp/assets/task/worker/hero.png", "node_modules/lib/hero.png", "templates/hero.png",
		"public/Bad Name.png", "bad.png", "docs/guides/usage.md", "public/missing.png",
	}
	for _, relative := range paths {
		if !strings.Contains(relative, "missing") {
			assetCatalogTestWrite(t, root, relative, "original")
		}
	}
	for _, relative := range paths {
		t.Run(relative, func(t *testing.T) {
			result := NewAssetService(root).Catalog(AssetCatalogRequest{Enabled: true, Operation: "put", Path: relative, Use: "retained output"})
			if result.Status != "blocked" || result.Data["executed"] != false {
				t.Fatalf("unsafe put reached the interpreter: %+v", result)
			}
		})
	}
}

func TestAssetCatalogBoundsTimeoutOutputAndReportsUnknownMutation(t *testing.T) {
	python := assetCatalogTestPython(t)
	for _, scenario := range []struct {
		name, script, expected string
	}{
		{"timeout", "import time\ntime.sleep(10)\n", "adapter-timeout"},
		{"output", "print('x' * 100000)\n", "adapter-output-limit"},
		{"invalid", "print('this is not JSON')\n", "adapter-invalid-output"},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			root := t.TempDir()
			assetCatalogTestInstall(t, root, scenario.script)
			assetCatalogTestWrite(t, root, "public/hero.png", "image")
			// Output/JSON cases exercise their own boundary, independently of
			// interpreter startup under load. Keep the timeout case at one second.
			seconds := 5
			if scenario.name == "timeout" {
				seconds = 1
			}
			started := time.Now()
			result := NewAssetService(root).Catalog(AssetCatalogRequest{Enabled: true, Python: python, Operation: "put", Path: "public/hero.png", Use: "visual", TimeoutSeconds: seconds, MaxOutputBytes: 1024})
			if result.Status != "blocked" || result.Data["adapter_status"] != scenario.expected || result.Data["mutation_may_have_occurred"] != true {
				t.Fatalf("adapter boundary was misreported: %+v", result)
			}
			if time.Since(started) > time.Duration(seconds+3)*time.Second {
				t.Fatal("adapter process was not bounded")
			}
		})
	}
}

func TestAssetCatalogDoesNotPromoteBackendFailureToSuccess(t *testing.T) {
	python := assetCatalogTestPython(t)
	root := t.TempDir()
	assetCatalogTestInstall(t, root, "import json\nprint(json.dumps({'ok': False, 'code': 'REVISION_REQUIRED'}))\n")
	assetCatalogTestWrite(t, root, "public/hero.png", "image")
	result := NewAssetService(root).Catalog(AssetCatalogRequest{Enabled: true, Python: python, Operation: "put", Path: "public/hero.png", Use: "visual"})
	if result.Status != "blocked" || result.Data["mutation_may_have_occurred"] != true {
		t.Fatalf("backend refusal was reported as success: %+v", result)
	}
}

func TestAssetCatalogRejectsSymlinkLauncherAndMissingPython(t *testing.T) {
	root := t.TempDir()
	assetCatalogTestInstall(t, root, "print('{}')\n")
	service := NewAssetService(root)
	result := service.Catalog(AssetCatalogRequest{Enabled: true, Python: filepath.Join(root, "nonexistent-python"), Operation: "find", Query: "hero"})
	if result.Status != "blocked" || result.Data["adapter_status"] != "python-unavailable" {
		t.Fatalf("missing interpreter status is wrong: %+v", result)
	}
	launcher := filepath.Join(root, ".assets", "ak.py")
	if err := os.Remove(launcher); err != nil {
		t.Fatal(err)
	}
	external := filepath.Join(t.TempDir(), "adapter.py")
	if err := os.WriteFile(external, []byte("print('{}')"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, launcher); err != nil {
		t.Skipf("symlink creation unavailable: %v", err)
	}
	result = service.Catalog(AssetCatalogRequest{Enabled: true, Operation: "find", Query: "hero"})
	if result.Status != "blocked" || result.Data["adapter_status"] != "adapter-unsafe" || result.Data["executed"] != false {
		t.Fatalf("symlink launcher was accepted: %+v", result)
	}
}
