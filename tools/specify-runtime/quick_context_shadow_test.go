package main

import (
	"bytes"
	"encoding/json"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	contextpacket "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/context"
)

// These fixtures use real local Git and the existing Quick owner loader and
// packet builder. A synthetic confirmed document is not human acceptance.
func shadowTestGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("Git is required for native shadow adapter tests")
	}
	argv := append([]string{"-C", root, "-c", "user.name=Shadow fixture", "-c", "user.email=shadow@example.invalid",
		"-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.DevNull}, args...)
	cmd := exec.Command("git", argv...)
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		if !strings.HasPrefix(strings.ToUpper(key), "GIT_") {
			cmd.Env = append(cmd.Env, entry)
		}
	}
	cmd.Env = append(cmd.Env, "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL="+os.DevNull, "GIT_TERMINAL_PROMPT=0")
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("fixture git %v: %v: %s", args, err, out)
	}
	return strings.TrimSpace(string(out))
}

func shadowTestDocument() *quickConfirmationDoc {
	return &quickConfirmationDoc{
		Schema: quickConfirmationSchema, Workspace: "2026-09-17-shadow",
		ConfirmationMode: "explicit", ConfirmationState: "confirmed",
		Source: quickConfirmationSource{Kind: "prompt"},
		Decision: quickConfirmationDecision{
			Goal: "修复登录😀", UserVisibleResult: "login succeeds",
			Scope: quickConfirmationScope{Include: []string{"login"}, Exclude: []string{"billing"}, Defer: []string{"redesign"}},
			Items: []quickConfirmationItem{
				{ID: "Q1", Deliverable: "login", Acceptance: "login checks pass", WriteScope: []string{"src/login.go"}},
				{ID: "Q2", Deliverable: "integration", Acceptance: "integration checks pass", WriteScope: []string{"src/integration.go"}, DependsOn: []string{"Q1"}},
			},
			CompletionEvidence: []string{"actual check log"}, ReconfirmationTrigger: "requirements change",
			UIConfirmation: map[string]any{"applicable": false, "preserve": []any{"existing shell"}},
		},
		Execution: quickConfirmationExecution{WorkItemStatus: []quickWorkItemStatus{{WorkItemID: "Q1", Status: "pending"}, {WorkItemID: "Q2", Status: "pending"}}},
	}
}

func shadowTestWrite(t *testing.T, root string, doc *quickConfirmationDoc) string {
	t.Helper()
	digest, err := computeQuickConfirmationDigest(doc.Decision)
	if err != nil {
		t.Fatal(err)
	}
	doc.ConfirmationDigest = digest
	dir := filepath.Join(root, ".planning", "quick", "2026-09-17-shadow")
	if err := os.MkdirAll(dir, 0700); err != nil {
		t.Fatal(err)
	}
	data, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	filename := filepath.Join(dir, quickConfirmationFileName)
	if err := os.WriteFile(filename, data, 0600); err != nil {
		t.Fatal(err)
	}
	return filename
}

func shadowTestRepo(t *testing.T) (quickService, *quickConfirmationDoc) {
	t.Helper()
	root := t.TempDir()
	shadowTestGit(t, root, "init", "-q")
	shadowTestGit(t, root, "commit", "--allow-empty", "-qm", "fixture")
	doc := shadowTestDocument()
	shadowTestWrite(t, root, doc)
	return quickService{projectRoot: root}, doc
}

func shadowTestFiles(t *testing.T, root string) map[string]string {
	t.Helper()
	out := map[string]string{}
	err := filepath.WalkDir(root, func(p string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return nil
		}
		data, err := os.ReadFile(p)
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, p)
		if err != nil {
			return err
		}
		out[filepath.ToSlash(rel)] = quickShadowBytesHash(data)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return out
}

func TestQuickContextShadowUsesRealOwnersWithoutWrites(t *testing.T) {
	service, doc := shadowTestRepo(t)
	before := shadowTestFiles(t, service.projectRoot)
	report, err := service.contextShadow(doc.Workspace, "Q1")
	if err != nil {
		t.Fatal(err)
	}
	loaded, err := service.loadConfirmation(filepath.Join(service.projectRoot, ".planning", "quick", doc.Workspace))
	if err != nil {
		t.Fatal(err)
	}
	owner, ready, _, err := compileQuickWorkerPacket(loaded, "Q1")
	if err != nil || !ready {
		t.Fatal("invalid owner fixture", err)
	}
	expected, _ := json.Marshal(owner)
	if !bytes.Equal(expected, report.OwnerPacket) {
		t.Fatal("complete legacy packet changed in the adapter")
	}
	data, err := os.ReadFile(filepath.Join(service.projectRoot, filepath.FromSlash(report.Projection.RuntimeStateRef)))
	if err != nil {
		t.Fatal(err)
	}
	if report.Projection.StateDigest != quickShadowBytesHash(data) || report.Projection.StateDigest == doc.ConfirmationDigest {
		t.Fatal("raw state identity confused with decision-only digest")
	}
	if report.Projection.SourceRevision != shadowTestGit(t, service.projectRoot, "rev-parse", "HEAD") {
		t.Fatal("wrong source identity")
	}
	if report.AuthorizesExecution || report.LiveCodeVerified || report.Mode != "shadow-only" {
		t.Fatal("diagnostic report invented execution authority")
	}
	if err := service.verifyContextShadow(doc.Workspace, "Q1", report); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(before, shadowTestFiles(t, service.projectRoot)) {
		t.Fatal("read-only adapter changed project or Git files")
	}
}

func TestQuickContextShadowRejectsExecutionOnlyDrift(t *testing.T) {
	for _, change := range []string{"write-scope", "join-point", "timestamp", "source-revision"} {
		t.Run(change, func(t *testing.T) {
			service, doc := shadowTestRepo(t)
			report, err := service.contextShadow(doc.Workspace, "Q1")
			if err != nil {
				t.Fatal(err)
			}
			decisionDigest := doc.ConfirmationDigest
			switch change {
			case "write-scope":
				doc.Decision.Items[0].WriteScope = []string{"src/other.go"}
			case "join-point":
				doc.Execution.JoinPoint = "changed"
			case "timestamp":
				doc.UpdatedAt = "2026-09-17T00:00:00Z"
			case "source-revision":
				shadowTestGit(t, service.projectRoot, "commit", "--allow-empty", "-qm", "new snapshot")
			}
			shadowTestWrite(t, service.projectRoot, doc)
			if doc.ConfirmationDigest != decisionDigest {
				t.Fatal("fixture should keep the decision digest unchanged")
			}
			if service.verifyContextShadow(doc.Workspace, "Q1", report) == nil {
				t.Fatal("stale execution context accepted")
			}
		})
	}
}

func TestQuickContextShadowHonorsDependenciesAndDirectResultContract(t *testing.T) {
	service, doc := shadowTestRepo(t)
	if _, err := service.contextShadow(doc.Workspace, "Q2"); err == nil {
		t.Fatal("unaccepted prerequisite was bypassed")
	}
	doc.Execution.WorkItemStatus[0] = quickWorkItemStatus{WorkItemID: "Q1", Status: "accepted", AcceptanceEvidence: []string{"fixture evidence"}}
	doc.Execution.WorkItemStatus[1] = quickWorkItemStatus{WorkItemID: "Q2", Status: "in_progress", ExecutionMode: quickLeaderDirectMode}
	shadowTestWrite(t, service.projectRoot, doc)
	report, err := service.contextShadow(doc.Workspace, "Q2")
	if err != nil {
		t.Fatal(err)
	}
	var owner map[string]any
	if err := json.Unmarshal(report.OwnerPacket, &owner); err != nil {
		t.Fatal(err)
	}
	if owner["requires_result_submit"] != true || owner["execution_mode"] != quickLeaderDirectMode {
		t.Fatal("direct executor lost its result-submit obligation")
	}
	if _, err := service.contextShadow(doc.Workspace, "Q1"); err == nil {
		t.Fatal("already accepted item projected as runnable")
	}
}

func TestQuickContextShadowRejectsInvalidSelectionAndSources(t *testing.T) {
	mutations := map[string]func(*quickConfirmationDoc){
		"undeclared-status-row": func(d *quickConfirmationDoc) {
			d.Execution.WorkItemStatus = append(d.Execution.WorkItemStatus, quickWorkItemStatus{WorkItemID: "Q99", Status: "pending"})
		},
		"blocked-dispatch": func(d *quickConfirmationDoc) {
			d.Execution.BlockedDispatch = &quickBlockedDispatch{Status: "subagent-blocked", ItemID: "Q1"}
		},
		"staged":         func(d *quickConfirmationDoc) { d.ConfirmationState = "staged" },
		"workspace":      func(d *quickConfirmationDoc) { d.Workspace = "another" },
		"schema":         func(d *quickConfirmationDoc) { d.Schema = "unknown" },
		"global-blocker": func(d *quickConfirmationDoc) { d.Execution.Blockers = []string{"unresolved"} },
		"duplicate-item": func(d *quickConfirmationDoc) { d.Decision.Items = append(d.Decision.Items, d.Decision.Items[0]) },
		"duplicate-status": func(d *quickConfirmationDoc) {
			d.Execution.WorkItemStatus = append(d.Execution.WorkItemStatus, d.Execution.WorkItemStatus[0])
		},
		"blocked-item":   func(d *quickConfirmationDoc) { d.Execution.WorkItemStatus[0].Status = "blocked" },
		"unknown-status": func(d *quickConfirmationDoc) { d.Execution.WorkItemStatus[0].Status = "unexpected" },
		"empty-status":   func(d *quickConfirmationDoc) { d.Execution.WorkItemStatus[0].Status = "" },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			service, doc := shadowTestRepo(t)
			mutate(doc)
			shadowTestWrite(t, service.projectRoot, doc)
			report, err := service.contextShadow("2026-09-17-shadow", "Q1")
			if err == nil || !reflect.DeepEqual(report, contextpacket.QuickShadowReport{}) {
				t.Fatal("invalid source returned a report", err)
			}
		})
	}
	service, _ := shadowTestRepo(t)
	for _, workspace := range []string{"", "..", "../escape", "a/b", "a\\b", "C:drive", " name"} {
		if _, err := service.contextShadow(workspace, "Q1"); err == nil {
			t.Errorf("invalid workspace accepted: %q", workspace)
		}
	}
	for _, id := range []string{"", "Q0", "Q01", "Q2/..", "Q99"} {
		if _, err := service.contextShadow("2026-09-17-shadow", id); err == nil {
			t.Errorf("invalid/missing item accepted: %q", id)
		}
	}
}

func TestQuickContextShadowRejectsTamperedDecisionAndMalformedState(t *testing.T) {
	service, doc := shadowTestRepo(t)
	p := shadowTestWrite(t, service.projectRoot, doc)
	original, _ := os.ReadFile(p)
	cases := [][]byte{
		bytes.Replace(original, []byte("login succeeds"), []byte("changed without confirmation"), 1),
		bytes.Replace(original, []byte(`"goal":`), []byte(`"goal":"conflict","goal":`), 1),
		[]byte("[]"), []byte("null"), []byte("{"), bytes.Repeat([]byte(" "), quickShadowReadLimit+1),
	}
	for i, raw := range cases {
		if err := os.WriteFile(p, raw, 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := service.contextShadow(doc.Workspace, "Q1"); err == nil {
			t.Errorf("invalid state %d accepted", i)
		}
		after, _ := os.ReadFile(p)
		if !bytes.Equal(raw, after) {
			t.Fatal("invalid state evidence was changed")
		}
	}
}

func TestQuickContextShadowIsolatesAmbientGitAndProjectIdentity(t *testing.T) {
	service, doc := shadowTestRepo(t)
	other, _ := shadowTestRepo(t)
	first, err := service.contextShadow(doc.Workspace, "Q1")
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("GIT_DIR", filepath.Join(other.projectRoot, ".git"))
	t.Setenv("GIT_WORK_TREE", other.projectRoot)
	t.Setenv("GIT_CONFIG_COUNT", "1")
	t.Setenv("GIT_CONFIG_KEY_0", "core.bare")
	t.Setenv("GIT_CONFIG_VALUE_0", "true")
	if err := service.verifyContextShadow(doc.Workspace, "Q1", first); err != nil {
		t.Fatal("ambient Git overrides redirected a read", err)
	}
	if other.verifyContextShadow(doc.Workspace, "Q1", first) == nil {
		t.Fatal("another project accepted the report")
	}
}

func TestQuickContextShadowRefusesParentRepositoryAndMissingHead(t *testing.T) {
	service, _ := shadowTestRepo(t)
	subdir := filepath.Join(service.projectRoot, "subproject")
	if err := os.Mkdir(subdir, 0700); err != nil {
		t.Fatal(err)
	}
	if _, err := quickShadowRevision(subdir); err == nil {
		t.Fatal("parent Git root used as subproject identity")
	}
	empty := t.TempDir()
	shadowTestGit(t, empty, "init", "-q")
	if _, err := quickShadowRevision(empty); err == nil {
		t.Fatal("missing HEAD given a fallback identity")
	}
}

func TestQuickContextShadowSupportsLinkedWorktreeWithoutRetargeting(t *testing.T) {
	service, doc := shadowTestRepo(t)
	linked := filepath.Join(t.TempDir(), "linked")
	shadowTestGit(t, service.projectRoot, "worktree", "add", "--detach", linked, "HEAD")
	shadowTestWrite(t, linked, doc)
	other := quickService{projectRoot: linked}
	report, err := other.contextShadow(doc.Workspace, "Q1")
	if err != nil {
		t.Fatal(err)
	}
	if err := other.verifyContextShadow(doc.Workspace, "Q1", report); err != nil {
		t.Fatal(err)
	}
	if service.verifyContextShadow(doc.Workspace, "Q1", report) == nil {
		t.Fatal("same HEAD must not merge worktree identities")
	}
}

func TestQuickContextShadowRejectsSymlinkState(t *testing.T) {
	service, doc := shadowTestRepo(t)
	p := shadowTestWrite(t, service.projectRoot, doc)
	moved := p + ".original"
	if err := os.Rename(p, moved); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(moved, p); err != nil {
		t.Skip("this host does not permit symlink creation")
	}
	if _, err := service.contextShadow(doc.Workspace, "Q1"); err == nil {
		t.Fatal("state read followed a symlink")
	}
}

func TestQuickContextShadowKeepsOwnerDefaultForAbsentRows(t *testing.T) {
	service, doc := shadowTestRepo(t)
	doc.Execution.WorkItemStatus = nil
	shadowTestWrite(t, service.projectRoot, doc)
	if _, err := service.contextShadow(doc.Workspace, "Q1"); err != nil {
		t.Fatal("absent rows must retain the owner's pending default", err)
	}
	if _, err := service.contextShadow(doc.Workspace, "Q2"); err == nil {
		t.Fatal("default pending must not mean accepted prerequisite")
	}
}
