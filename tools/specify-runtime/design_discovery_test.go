package main

import (
	"bytes"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestDesignResolveInvalidScopeOffersReadOnlyDiscovery(t *testing.T) {
	for _, scope := range []string{
		"enterprise knowledge workspace across Web, CLI, HTTP API, and Server Jobs",
		"",
		"web:orders/*",
		"/orders",
	} {
		t.Run(scope, func(t *testing.T) {
			root := t.TempDir()
			withCwd(t, root)
			before := snapshotDesignDiscoveryFiles(t, root)
			var stdout bytes.Buffer
			if exit := runDesign([]string{"resolve", "--scope", scope}, &stdout); exit != 2 {
				t.Fatalf("invalid scope must be a usage error: exit=%d output=%s", exit, stdout.String())
			}
			env := decodeEnvelope(t, stdout.Bytes())
			if env.Status != "usage-error" || env.Data["diagnostic_code"] != "invalid-scope" {
				t.Fatalf("missing structured scope diagnostic: %#v", env)
			}
			format, ok := env.Data["scope_format"].(map[string]any)
			if !ok || format["pattern"] != `^[A-Za-z0-9][A-Za-z0-9._:/-]*$` || len(stringList(format["examples"])) < 2 {
				t.Fatalf("missing accepted scope format and examples: %#v", format)
			}
			for _, example := range stringList(format["examples"]) {
				if !designChangeScopeRE.MatchString(example) {
					t.Fatalf("suggested scope %q violates the stable scope format", example)
				}
			}
			if _, claimed := env.Data["candidate_count"]; claimed || len(env.Items) != 0 {
				t.Fatalf("invalid scope must not claim a discovery result: %#v", env)
			}
			assertDesignDiscoveryNextArgv(t, env)
			stdout.Reset()
			if exit := runArtifact(env.NextArgv[2:], &stdout); exit != 0 {
				t.Fatalf("suggested discovery must work without an index: exit=%d output=%s", exit, stdout.String())
			}
			if after := snapshotDesignDiscoveryFiles(t, root); !reflect.DeepEqual(before, after) {
				t.Fatalf("scope diagnostic or suggested discovery wrote project files: before=%v after=%v", before, after)
			}
		})
	}
}

func TestDesignResolveMissingIndexIsReadOnlyNoCandidates(t *testing.T) {
	for _, withDesignDirectory := range []bool{false, true} {
		t.Run(fmt.Sprintf("design-directory=%t", withDesignDirectory), func(t *testing.T) {
			root := t.TempDir()
			withCwd(t, root)
			if withDesignDirectory {
				if err := os.MkdirAll(filepath.Join(root, ".specify", "design"), 0o755); err != nil {
					t.Fatal(err)
				}
			}
			before := snapshotDesignDiscoveryFiles(t, root)
			for attempt := 0; attempt < 2; attempt++ {
				var stdout bytes.Buffer
				if exit := runDesign([]string{"resolve", "--scope", "web:orders"}, &stdout); exit != 0 {
					t.Fatalf("missing registry must be a discovery result: exit=%d output=%s", exit, stdout.String())
				}
				env := decodeEnvelope(t, stdout.Bytes())
				if env.Status != "ok" || len(env.Blockers) != 0 || len(env.Items) != 0 || env.Data["candidate_count"] != float64(0) || env.Data["composite"] != false || env.Data["registry_state"] != "missing" {
					t.Fatalf("missing registry must return explicit zero candidates: %#v", env)
				}
				if !strings.Contains(env.Summary, "no registered UI design candidates") || !strings.Contains(env.Summary, "missing") {
					t.Fatalf("missing registry summary is unclear: %q", env.Summary)
				}
				assertDesignDiscoveryNextArgv(t, env)
			}
			// Only discovery treats absence as no candidates. Registration-dependent
			// readers must still fail, with the underlying absence preserved.
			if _, _, _, err := loadDesignChangeIndex(root); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("strict index loader must preserve missing-registry error: %v", err)
			}
			if _, _, _, err := loadRegisteredDesignChange(root, "UD-0042"); err == nil {
				t.Fatal("missing registry must not fabricate a registered design")
			}
			if after := snapshotDesignDiscoveryFiles(t, root); !reflect.DeepEqual(before, after) {
				t.Fatalf("missing-index discovery wrote project files: before=%v after=%v", before, after)
			}
		})
	}
}

func TestDesignResolveDistinguishesExistingRegistryStates(t *testing.T) {
	for _, tc := range []struct {
		name     string
		content  string
		asDir    bool
		asLink   bool
		state    string
		wantExit int
	}{
		{name: "empty-registry", content: fmt.Sprintf(`{"schema":%q,"changes":[]}`, designChangeIndexSchema), state: "present"},
		{name: "invalid-json", content: "{", state: "malformed", wantExit: 10},
		{name: "null", content: "null", state: "malformed", wantExit: 10},
		{name: "wrong-schema", content: `{"schema":"wrong","changes":[]}`, state: "malformed", wantExit: 10},
		{name: "invalid-changes", content: fmt.Sprintf(`{"schema":%q,"changes":{}}`, designChangeIndexSchema), state: "malformed", wantExit: 10},
		{name: "unreadable-directory", asDir: true, state: "unreadable", wantExit: 10},
		{name: "dangling-index", asLink: true, state: "unreadable", wantExit: 10},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			withCwd(t, root)
			indexPath := filepath.Join(root, ".specify", "design", "index.json")
			if err := os.MkdirAll(filepath.Dir(indexPath), 0o755); err != nil {
				t.Fatal(err)
			}
			if tc.asLink {
				if err := os.Symlink("missing-registry.json", indexPath); err != nil {
					t.Skipf("cannot create symlink on this platform: %v", err)
				}
			} else if tc.asDir {
				if err := os.Mkdir(indexPath, 0o755); err != nil {
					t.Fatal(err)
				}
			} else if err := os.WriteFile(indexPath, []byte(tc.content), 0o644); err != nil {
				t.Fatal(err)
			}
			before := snapshotDesignDiscoveryFiles(t, root)
			var stdout bytes.Buffer
			if exit := runDesign([]string{"resolve", "--scope", "web:orders"}, &stdout); exit != tc.wantExit {
				t.Fatalf("registry state exit=%d, want %d: %s", exit, tc.wantExit, stdout.String())
			}
			env := decodeEnvelope(t, stdout.Bytes())
			if env.Data["registry_state"] != tc.state || env.Data["read_only"] != true || env.Data["requires_explicit_adoption"] != true {
				t.Fatalf("registry diagnostic lost state or adoption boundary: %#v", env)
			}
			if tc.wantExit != 0 {
				if env.Status != "blocked" || len(env.Blockers) == 0 {
					t.Fatalf("existing bad registry must remain blocked: %#v", env)
				}
				if _, claimed := env.Data["candidate_count"]; claimed {
					t.Fatalf("unusable registry must not claim zero candidates: %#v", env)
				}
			} else if env.Data["candidate_count"] != float64(0) || len(env.Items) != 0 {
				t.Fatalf("empty valid registry must have no candidates: %#v", env)
			}
			if after := snapshotDesignDiscoveryFiles(t, root); !reflect.DeepEqual(before, after) {
				t.Fatalf("registry discovery wrote project files: before=%v after=%v", before, after)
			}
		})
	}
}

func TestDesignResolveDiscoveryFindsContractWithoutInferringApproval(t *testing.T) {
	root := t.TempDir()
	withCwd(t, root)
	canonical := ".specify/design/changes/UD-0042/design-change.md"
	path := filepath.Join(root, filepath.FromSlash(canonical))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	content := "---\ndesign_system:\n  status: draft\n  scope:\n    surfaces: [web:orders]\n---\n# Orders design\n"
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	before := snapshotDesignDiscoveryFiles(t, root)
	var stdout bytes.Buffer
	if exit := runDesign([]string{"resolve", "--scope", "orders workspace"}, &stdout); exit != 2 {
		t.Fatalf("prose scope exit=%d output=%s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	assertDesignDiscoveryNextArgv(t, env)
	stdout.Reset()
	if exit := runArtifact(env.NextArgv[2:], &stdout); exit != 0 {
		t.Fatalf("suggested artifact discovery exit=%d output=%s", exit, stdout.String())
	}
	listed := decodeEnvelope(t, stdout.Bytes())
	items, ok := listed.Data["items"].([]any)
	if !ok || len(items) != 1 || items[0].(map[string]any)["canonical_path"] != canonical {
		t.Fatalf("discovery must find the actual contract without an index: %#v", listed)
	}
	stdout.Reset()
	if exit := runArtifact([]string{"show", "--path", canonical, "--view", "full", "--format", "json"}, &stdout); exit != 0 {
		t.Fatalf("contract inspection exit=%d output=%s", exit, stdout.String())
	}
	if shown := decodeEnvelope(t, stdout.Bytes()); shown.Data["content"] != content {
		t.Fatalf("contract inspection must preserve the source scope: %#v", shown)
	}
	stdout.Reset()
	if exit := runDesign([]string{"resolve", "--scope", "web:orders"}, &stdout); exit != 0 {
		t.Fatalf("exact scope discovery exit=%d output=%s", exit, stdout.String())
	}
	resolved := decodeEnvelope(t, stdout.Bytes())
	if len(resolved.Items) != 0 || resolved.Data["registry_state"] != "missing" || resolved.Data["requires_explicit_adoption"] != true {
		t.Fatalf("discovering a contract must not infer registration or adoption: %#v", resolved)
	}
	if after := snapshotDesignDiscoveryFiles(t, root); !reflect.DeepEqual(before, after) {
		t.Fatalf("contract discovery or inspection wrote project files: before=%v after=%v", before, after)
	}
}

func assertDesignDiscoveryNextArgv(t *testing.T, env Envelope) {
	t.Helper()
	root, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"artifact", "list", "--project-root", root, "--path-prefix", ".specify/design/changes/", "--type", "ui-design-change-contract", "--format", "json"}
	if len(env.NextArgv) < 2 || !reflect.DeepEqual(env.NextArgv[1:], want) {
		t.Fatalf("expected executable read-only artifact discovery, got %#v", env.NextArgv)
	}
	if env.Data["read_only"] != true || env.Data["requires_explicit_adoption"] != true {
		t.Fatalf("discovery must preserve read-only and explicit-adoption boundaries: %#v", env.Data)
	}
}

func snapshotDesignDiscoveryFiles(t *testing.T, root string) map[string]string {
	t.Helper()
	snapshot := map[string]string{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		var raw []byte
		if entry.Type()&os.ModeSymlink != 0 {
			target, err := os.Readlink(path)
			if err != nil {
				return err
			}
			raw = []byte(target)
		} else if !entry.IsDir() {
			raw, err = os.ReadFile(path)
			if err != nil {
				return err
			}
		}
		modified := int64(0)
		if !entry.IsDir() {
			modified = info.ModTime().UnixNano()
		}
		// Directory membership catches created paths without depending on
		// delayed Windows directory timestamps from fixture creation.
		snapshot[path] = fmt.Sprintf("%s:%d:%s", info.Mode(), modified, raw)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return snapshot
}
