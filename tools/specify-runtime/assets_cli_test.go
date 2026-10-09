package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func runAssetCLITest(t *testing.T, root string, args ...string) (int, Envelope) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	full := append([]string{"assets"}, args...)
	full = append(full, "--project-root", root, "--format", "json")
	code := Run(full, &stdout, &stderr, "test-assets")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("expected one JSON envelope, code=%d stdout=%s stderr=%s: %v", code, &stdout, &stderr, err)
	}
	return code, env
}

func TestAssetCLIPathsAndOwnership(t *testing.T) {
	root := t.TempDir()
	code, env := runAssetCLITest(t, root, "route", "--purpose", "guide", "--slug", "release-guide")
	if code != 0 || env.Data["action"] != "create-new" || env.Data["path"] != "docs/guides/release-guide.md" {
		t.Fatalf("unexpected routed destination: code=%d %+v", code, env)
	}
	if entries, err := os.ReadDir(root); err != nil || len(entries) != 0 {
		t.Fatalf("routing must not create files or workflows: %v %v", entries, err)
	}
	code, env = runAssetCLITest(t, root, "check", "--path-only", "--path", "docs/guides/release-guide.md", "--path", "assets/release-preview.png")
	if code != 0 || env.Data["path_only"] != true || env.Data["content_checked"] != float64(0) {
		t.Fatalf("path-only check made a false content claim: code=%d %+v", code, env)
	}
	code, env = runAssetCLITest(t, root, "route", "--path", "specs/2026-10-08-assets/spec.md")
	if code == 0 || env.Data["action"] != "owner-required" {
		t.Fatalf("workflow ownership was bypassed: code=%d %+v", code, env)
	}
}

func TestAssetCLIStrictSelectorsAndJSON(t *testing.T) {
	root := t.TempDir()
	cases := [][]string{
		{"check", "--from-ref", "HEAD"},
		{"check", "--to-ref", "HEAD"},
		{"check", "--unknown", "x"},
		{"check", "unexpected.md"},
		{"route", "--purpose", "guide", "--purpose", "report", "--slug", "guide"},
		{"migrate", "plan", "--input-json", `null`},
		{"migrate", "plan", "--input-json", `{"moves":[],"moves":[]}`},
		{"migrate", "plan", "--input-json", `{"moves":[],"unknown":true}`},
		{"migrate", "plan", "--input-json", `{"moves":[]} {}`},
		{"migrate", "apply", "--input-json", `{"plan":{}}`},
		{"catalog", "find", "--input-json", `{"operation":"put"}`},
		{"catalog", "find", "--input-json", `{"query":"x"}`, "--query", "y"},
	}
	for _, args := range cases {
		t.Run(strings.Join(args[:min(2, len(args))], "-")+"/"+strings.Join(args[2:], " "), func(t *testing.T) {
			if code, env := runAssetCLITest(t, root, args...); code == 0 {
				t.Fatalf("ambiguous/invalid request accepted: %+v", env)
			}
		})
	}
	if entries, err := os.ReadDir(root); err != nil || len(entries) != 0 {
		t.Fatalf("invalid requests must not write project state: %v %v", entries, err)
	}
}

func TestAssetCLIFileInputAndDisabledAdapter(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "catalog-input.json"), []byte(`{"query":"logo","enabled":false}`), 0600); err != nil {
		t.Fatal(err)
	}
	code, env := runAssetCLITest(t, root, "catalog", "find", "--input-json", "@catalog-input.json")
	if code != 0 || env.Data["adapter_status"] != "disabled" || env.Data["executed"] != false {
		t.Fatalf("disabled adapter was not a truthful no-op: code=%d %+v", code, env)
	}
	code, env = runAssetCLITest(t, root, "catalog", "find", "--query", "--help")
	if code != 0 || env.Data["adapter_status"] != "disabled" {
		t.Fatalf("literal query was interpreted as CLI help: code=%d %+v", code, env)
	}
	if code, env := runAssetCLITest(t, root, "catalog", "find", "--input-json", "@../outside.json"); code == 0 {
		t.Fatalf("outside input path accepted: %+v", env)
	}
	if _, err := os.Stat(filepath.Join(root, ".assets")); !os.IsNotExist(err) {
		t.Fatalf("disabled adapter bootstrapped AssetKit: %v", err)
	}
}

func TestAssetCLICapabilityDiscoveryAndTimeouts(t *testing.T) {
	for _, id := range []string{"assets.route", "assets.explain", "assets.check", "assets.migrate.plan", "assets.migrate.apply", "assets.catalog.find", "assets.catalog.get", "assets.catalog.put", "assets.catalog.check"} {
		if !containsCapability(defaultCapabilities(), id) {
			t.Fatalf("capability missing from handshake: %s", id)
		}
		var stdout bytes.Buffer
		if code := Run([]string{"api", "show", id, "--format", "json"}, &stdout, &bytes.Buffer{}, "test-assets"); code != 0 {
			t.Fatalf("api show %s failed: %s", id, &stdout)
		}
		if strings.Contains(stdout.String(), "inspect the command-specific help") || !strings.Contains(stdout.String(), "input_contract") {
			t.Fatalf("capability has only fallback documentation: %s", &stdout)
		}
	}
	if !isShortRuntimeQuery([]string{"assets", "check"}) || !isShortRuntimeQuery([]string{"assets", "migrate", "plan"}) {
		t.Fatal("read-only assets commands should use the bounded query budget")
	}
	if isShortRuntimeQuery([]string{"assets", "migrate", "apply"}) || isShortRuntimeQuery([]string{"assets", "catalog", "put"}) {
		t.Fatal("mutating assets commands must not inherit the generic catalog query timeout")
	}
}
