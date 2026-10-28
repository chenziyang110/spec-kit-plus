package changes

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
)

func TestEffectiveChangeStatusPreservesNonDeletionCodes(t *testing.T) {
	for _, code := range []string{"", "M", "MM", "A", "AM", "D", "R", "R100", "RM", "RD", "??", "explicit", "UU"} {
		if got := effectiveChangeStatus(" " + code + " "); got != code {
			t.Fatalf("status %q changed to %q", code, got)
		}
	}
}

func TestStagedThenDeletedPathsAreNotRefreshedOrAdopted(t *testing.T) {
	for _, code := range []string{"MD", "AD"} {
		for _, known := range []bool{false, true} {
			if got := operationFor(code, true, known); got != changemodel.OperationDelete {
				t.Errorf("code=%s known=%v: operation=%s, want delete", code, known, got)
			}
			if got := classify(code, known); got != levelDeletedPath {
				t.Errorf("code=%s known=%v: level=%s, want deleted_path", code, known, got)
			}
		}
	}
}

func TestStagedThenDeletedRealGit(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git unavailable")
	}
	for _, added := range []bool{false, true} {
		name, wantCode := "modified", "MD"
		if added {
			name, wantCode = "added", "AD"
		}
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			run := func(args ...string) []byte {
				t.Helper()
				cmd := exec.Command("git", args...)
				cmd.Dir = root
				out, err := cmd.CombinedOutput()
				if err != nil {
					t.Fatalf("git %q: %v: %s", args, err, out)
				}
				return out
			}
			run("init", "-q")
			run("config", "user.name", "Cognition Test")
			run("config", "user.email", "cognition-test@example.invalid")
			run("config", "commit.gpgsign", "false")
			file := filepath.Join(root, "file.txt")
			if !added {
				if err := os.WriteFile(file, []byte("before\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				run("add", "--", "file.txt")
				run("commit", "-qm", "fixture")
			} else {
				run("commit", "--allow-empty", "-qm", "fixture")
			}
			if err := os.WriteFile(file, []byte("after\n"), 0o600); err != nil {
				t.Fatal(err)
			}
			run("add", "--", "file.txt")
			if err := os.Remove(file); err != nil {
				t.Fatal(err)
			}
			out := string(run("status", "--porcelain=v1", "-z", "--untracked-files=all"))
			if !strings.HasPrefix(out, wantCode+" file.txt\x00") {
				t.Fatalf("status=%q, want %s for staged-then-deleted file", out, wantCode)
			}
			code := out[:2]
			if got := operationFor(code, true, !added); got != changemodel.OperationDelete {
				t.Fatalf("status %s for absent file routed to %s", code, got)
			}
			if got := classify(code, !added); got != levelDeletedPath {
				t.Fatalf("status %s for absent file classified as %s", code, got)
			}
		})
	}
}
