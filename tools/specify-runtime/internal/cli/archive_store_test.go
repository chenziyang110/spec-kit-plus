package cli

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestArchiveIncompatibleStoreRefusesRedirectedHistory(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	outside := t.TempDir()
	history := filepath.Join(dir, "history")
	var err error
	if runtime.GOOS == "windows" {
		output, linkErr := exec.Command("cmd.exe", "/c", "mklink", "/J", history, outside).CombinedOutput()
		if linkErr != nil {
			t.Fatalf("create isolated history junction: %v %s", linkErr, output)
		}
	} else if err = os.Symlink(outside, history); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	database, status := []byte("legacy database"), []byte(`{"freshness":"fresh"}`)
	if err := os.WriteFile(paths.DatabasePath, database, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.StatusPath, status, 0o644); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{{"--inspect", "--format", "json"}, {"--expected-sha256", fmt.Sprintf("%x", sha256.Sum256(database)), "--format", "json"}} {
		var stdout, stderr bytes.Buffer
		if code := archiveIncompatibleStoreCommand(args, &stdout, &stderr, paths); code == 0 || !strings.Contains(stdout.String(), "non-symlink") {
			t.Fatalf("redirected archive code=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
		}
		for path, want := range map[string][]byte{paths.DatabasePath: database, paths.StatusPath: status} {
			got, err := os.ReadFile(path)
			if err != nil || !bytes.Equal(got, want) {
				t.Fatalf("refusal changed original %s: %v", path, err)
			}
		}
		entries, err := os.ReadDir(outside)
		if err != nil || len(entries) != 0 {
			t.Fatalf("archive wrote outside project: entries=%v err=%v", entries, err)
		}
	}
}

func TestArchiveIncompatibleStoreRequiresDigestAndMovesExactDatabase(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	databasePath := filepath.Join(runtimeDir, "project-cognition.db")
	content := []byte("legacy-schema-database")
	if err := os.WriteFile(databasePath, content, 0o644); err != nil {
		t.Fatal(err)
	}
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	digest := fmt.Sprintf("%x", sha256.Sum256(content))
	var stdout, stderr bytes.Buffer
	code := Run([]string{"archive-incompatible-store", "--expected-sha256", digest, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("archive code=%d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "archived" || payload["sha256"] != digest {
		t.Fatalf("archive payload = %#v", payload)
	}
	if _, err := os.Stat(databasePath); !os.IsNotExist(err) {
		t.Fatalf("database still exists after archive: %v", err)
	}
	archivePath := filepath.Join(root, filepath.FromSlash(payload["archive_path"].(string)))
	stored, err := os.ReadFile(archivePath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(stored, content) {
		t.Fatalf("archive content = %q", stored)
	}
}

func TestArchiveIncompatibleStoreRejectsStaleDigest(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	databasePath := filepath.Join(runtimeDir, "project-cognition.db")
	if err := os.WriteFile(databasePath, []byte("current"), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"archive-incompatible-store", "--expected-sha256", strings.Repeat("0", 64), "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 || !strings.Contains(stdout.String(), "changed") {
		t.Fatalf("stale digest code=%d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	if _, err := os.Stat(databasePath); err != nil {
		t.Fatalf("stale digest removed database: %v", err)
	}
}

func TestArchiveIncompatibleStoreInspectReturnsGuardedArgvWithoutMutation(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	databasePath := filepath.Join(runtimeDir, "project-cognition.db")
	if err := os.WriteFile(databasePath, []byte("legacy"), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	if code := Run([]string{"archive-incompatible-store", "--inspect", "--format", "json"}, &stdout, &stderr, "test"); code != 0 {
		t.Fatalf("inspect code=%d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	argv, ok := payload["archive_argv"].([]any)
	if payload["status"] != "inspected" || !ok || len(argv) < 7 {
		t.Fatalf("inspect payload = %#v", payload)
	}
	if _, err := os.Stat(databasePath); err != nil {
		t.Fatalf("inspect changed database: %v", err)
	}
}
