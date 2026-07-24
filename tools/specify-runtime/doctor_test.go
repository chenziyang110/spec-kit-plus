package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDiagnoseProjectRuntimeAcceptsProjectLocalDigestBinding(t *testing.T) {
	root := t.TempDir()
	entrypoint := filepath.Join(root, filepath.FromSlash(stringsWithoutDotSlash(normalizedRuntimeEntrypoint())))
	if err := os.MkdirAll(filepath.Dir(entrypoint), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(entrypoint, []byte("runtime"), 0o755); err != nil {
		t.Fatal(err)
	}
	digest, err := doctorFileSHA256(entrypoint)
	if err != nil {
		t.Fatal(err)
	}
	config := map[string]any{
		"runtime_launcher": map[string]any{
			"command": projectRuntimeRelativeEntrypoint(),
			"argv":    []string{projectRuntimeRelativeEntrypoint()},
		},
		"runtime_launcher_binding": map[string]any{
			"runtime_binary_sha256": digest,
			"runtime_entrypoint":    projectRuntimeRelativeEntrypoint(),
		},
	}
	raw, err := json.Marshal(config)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", "config.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}

	env := diagnoseProjectRuntime(root)
	if env.Status != "ok" {
		t.Fatalf("doctor status = %q, blockers=%#v", env.Status, env.Blockers)
	}
	if env.Data["runtime_binary_sha256"] != digest {
		t.Fatalf("doctor digest = %#v, want %q", env.Data["runtime_binary_sha256"], digest)
	}
}

func TestDiagnoseProjectRuntimeRejectsAbsoluteLauncher(t *testing.T) {
	root := t.TempDir()
	entrypoint := filepath.Join(root, filepath.FromSlash(stringsWithoutDotSlash(normalizedRuntimeEntrypoint())))
	if err := os.MkdirAll(filepath.Dir(entrypoint), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(entrypoint, []byte("runtime"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := map[string]any{
		"runtime_launcher": map[string]any{
			"argv": []string{entrypoint},
		},
		"runtime_launcher_binding": map[string]any{},
	}
	raw, err := json.Marshal(config)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", "config.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}

	env := diagnoseProjectRuntime(root)
	if env.Status != "blocked" || env.Data["error_code"] != "nonlocal-runtime-launcher" {
		t.Fatalf("doctor result = %#v, want nonlocal-runtime-launcher block", env)
	}
}

func stringsWithoutDotSlash(value string) string {
	if len(value) >= 2 && value[0] == '.' && (value[1] == '/' || value[1] == '\\') {
		return value[2:]
	}
	return value
}
