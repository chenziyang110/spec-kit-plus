package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func TestDoLargeWorkspaceBaselineDoesNotBlockOperation(t *testing.T) {
	root, input := doFixture(t)
	// Stage missing paths to exercise a real 37,000-path Git workspace without
	// creating thousands of files. Long names reproduce the reported 8 MiB bound.
	blob := strings.TrimSpace(gitRun(t, root, "hash-object", "source.txt"))
	var index bytes.Buffer
	for n := 0; n < 37000; n++ {
		fmt.Fprintf(&index, "100644 %s\tbackground/%s%05d.txt\n", blob, strings.Repeat("long-path-", 13), n)
	}
	command := exec.Command("git", "update-index", "--index-info")
	command.Dir, command.Stdin = root, &index
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("prepare large workspace: %v %s", err, output)
	}
	session, err := doStart(root, input)
	if err != nil {
		t.Fatalf("unrelated workspace changes blocked a small operation: %v", err)
	}
	checkpoint, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))))
	if err != nil {
		t.Fatal(err)
	}
	var stored map[string]json.RawMessage
	if err := json.Unmarshal(checkpoint, &stored); err != nil {
		t.Fatal(err)
	}
	if _, inline := stored["baseline_json"]; inline || len(checkpoint) > 64*1024 {
		t.Fatalf("workspace baseline still bloats the checkpoint: %d bytes", len(checkpoint))
	}
	var ref string
	if err := json.Unmarshal(stored["baseline_ref"], &ref); err != nil {
		t.Fatal(err)
	}
	baselineBytes, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if err != nil {
		t.Fatal(err)
	}
	var baseline runcontrol.WorkspaceBaseline
	if err := json.Unmarshal(baselineBytes, &baseline); err != nil {
		t.Fatal(err)
	}
	if len(baseline.PathDigests) < 37000 || len(baseline.DirtyPaths) < 37000 || len(baselineBytes) <= doSessionSizeLimit {
		t.Fatalf("large baseline lost workspace coverage: paths=%d dirty=%d bytes=%d", len(baseline.PathDigests), len(baseline.DirtyPaths), len(baselineBytes))
	}
	t.Logf("retained %d dirty paths in %d-byte baseline; checkpoint %d bytes", len(baseline.DirtyPaths), len(baselineBytes), len(checkpoint))
	session = doRunFixture(t, root, session)
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if validation := doValidate(root, session, true); validation.Status != "passed" {
		t.Fatalf("unchanged background changes were attributed to the operation: %+v", validation)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"}); err != nil {
		t.Fatal(err)
	}
	after, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
	if err != nil || !bytes.Equal(after, baselineBytes) {
		t.Fatalf("record/finish rewrote the immutable baseline: %v", err)
	}
}

func TestDoBaselineAuditsChangesToInitiallyDirtyBackgroundPaths(t *testing.T) {
	for _, mutation := range []string{"modify", "delete", "restore"} {
		t.Run(mutation, func(t *testing.T) {
			root, input := doFixture(t)
			name := "background.txt"
			if err := os.WriteFile(filepath.Join(root, name), []byte("original"), 0o600); err != nil {
				t.Fatal(err)
			}
			gitRun(t, root, "add", name)
			gitRun(t, root, "-c", "user.name=Do Test", "-c", "user.email=do@example.test", "commit", "-m", "background")
			if err := os.WriteFile(filepath.Join(root, name), []byte("preexisting change"), 0o600); err != nil {
				t.Fatal(err)
			}
			session, err := doStart(root, input)
			if err != nil {
				t.Fatal(err)
			}
			session = doRunFixture(t, root, session)
			if got := doValidate(root, session, true); got.Status != "passed" {
				t.Fatalf("unchanged background should pass: %+v", got)
			}
			switch mutation {
			case "modify":
				err = os.WriteFile(filepath.Join(root, name), []byte("changed again"), 0o600)
			case "delete":
				err = os.Remove(filepath.Join(root, name))
			case "restore":
				gitRun(t, root, "restore", name)
			}
			if err != nil {
				t.Fatal(err)
			}
			loaded, _, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			if got := doValidate(root, loaded, true); got.Status == "passed" || !strings.Contains(strings.Join(got.Blockers, " "), name) {
				t.Fatalf("lost full workspace audit after %s: %+v", mutation, got)
			}
			if err := doReplanRejectRetroactiveScope(root, loaded, nil, []string{"out", name}); err == nil {
				t.Fatal("baseline sidecar allowed retroactive authorization")
			}
		})
	}
}

func TestDoBaselineIntegrityRejectsInvalidBindings(t *testing.T) {
	for _, mutation := range []string{"missing", "changed", "directory", "foreign", "missing-digest", "incomplete", "mixed", "v1-reference", "v2-inline"} {
		t.Run(mutation, func(t *testing.T) {
			root, session := doStartFixture(t)
			_, digest, err := loadDoSession(root, session.ID)
			if err != nil {
				t.Fatal(err)
			}
			checkpointPath := filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID)))
			baselinePath := filepath.Join(root, filepath.FromSlash(session.BaselineRef))
			baseline, err := os.ReadFile(baselinePath)
			if err != nil {
				t.Fatal(err)
			}
			checkpoint, err := os.ReadFile(checkpointPath)
			if err != nil {
				t.Fatal(err)
			}
			var stored map[string]any
			if err := json.Unmarshal(checkpoint, &stored); err != nil {
				t.Fatal(err)
			}
			switch mutation {
			case "missing":
				err = os.Remove(baselinePath)
			case "changed":
				err = os.WriteFile(baselinePath, []byte(`{"head_commit":"changed"}`), 0o600)
			case "directory":
				if err = os.Remove(baselinePath); err == nil {
					err = os.Mkdir(baselinePath, 0o700)
				}
			case "foreign":
				stored["baseline_ref"] = "source.txt"
			case "missing-digest":
				delete(stored, "baseline_sha256")
			case "incomplete":
				invalid := []byte(`{"head_commit":"fixture"}`)
				err = os.WriteFile(baselinePath, invalid, 0o600)
				stored["baseline_sha256"] = doBytesDigest(invalid)
			case "mixed":
				stored["baseline_json"] = string(baseline)
			case "v1-reference":
				stored["schema_version"] = doLegacySessionSchema
			case "v2-inline":
				delete(stored, "baseline_ref")
				delete(stored, "baseline_sha256")
				stored["baseline_json"] = string(baseline)
			}
			if err != nil {
				t.Fatal(err)
			}
			if mutation != "missing" && mutation != "changed" && mutation != "directory" {
				checkpoint, err = json.Marshal(stored)
				if err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(checkpointPath, checkpoint, 0o600); err != nil {
					t.Fatal(err)
				}
			}
			if _, _, err := loadDoSession(root, session.ID); err == nil {
				t.Fatalf("accepted %s baseline binding", mutation)
			}
			if mutation == "missing" || mutation == "changed" || mutation == "directory" {
				session.Revision++
				if err := doWriteSession(root, session, digest, nil); err == nil {
					t.Fatal("stale in-memory session overwrote damaged baseline")
				}
			}
			after, err := os.ReadFile(checkpointPath)
			if err != nil || !bytes.Equal(checkpoint, after) {
				t.Fatalf("rejected baseline changed the checkpoint: %v", err)
			}
		})
	}
}

func TestDoLegacyInlineBaselineRemainsResumable(t *testing.T) {
	root, session := doStartFixture(t)
	baselinePath := filepath.Join(root, filepath.FromSlash(session.BaselineRef))
	baseline, err := os.ReadFile(baselinePath)
	if err != nil {
		t.Fatal(err)
	}
	session.SchemaVersion = doLegacySessionSchema
	session.BaselineJSON = string(baseline)
	session.BaselineRef, session.BaselineSHA256 = "", ""
	checkpoint, err := json.Marshal(session)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID))), checkpoint, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(baselinePath); err != nil {
		t.Fatal(err)
	}
	session, _, err = loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session = doRunFixture(t, root, session)
	session, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := doFinish(root, session, digest, doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"}); err != nil {
		t.Fatal(err)
	}
	loaded, _, err := loadDoSession(root, session.ID)
	if err != nil || loaded.SchemaVersion != doLegacySessionSchema || loaded.BaselineRef != "" || loaded.BaselineJSON != string(baseline) {
		t.Fatalf("legacy baseline changed across resume: %+v %v", loaded, err)
	}
}

func TestDoOversizeStartDoesNotReserveWork(t *testing.T) {
	root, input := doFixture(t)
	input.Context = map[string]string{"oversize": strings.Repeat("x", doSessionSizeLimit)}
	if _, err := doStart(root, input); err == nil || !strings.Contains(err.Error(), "8 MiB") {
		t.Fatalf("expected deterministic checkpoint-size rejection: %v", err)
	}
	view, err := runcontrol.OpenViewForRepository(context.Background(), root)
	if err == nil {
		defer view.Close()
		items, err := view.ListWork(context.Background(), runcontrol.ListWorkParams{})
		if err != nil || len(items) != 0 {
			t.Fatalf("failed start reserved Work ownership: %+v %v", items, err)
		}
	} else if !os.IsNotExist(err) && !strings.Contains(err.Error(), "not found") {
		t.Fatal(err)
	}
	for _, ref := range []string{doSessionRef(input.SessionID), doBaselineRef(input.SessionID)} {
		if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(ref))); !os.IsNotExist(err) {
			t.Fatalf("failed preflight published %s: %v", ref, err)
		}
	}
}

func TestDoBaselineBoundsAndHydratedIntegrity(t *testing.T) {
	root, session := doStartFixture(t)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	session.BaselineJSON += " "
	if err := doWriteSession(root, session, digest, nil); err == nil {
		t.Fatal("changed hydrated baseline passed its immutable binding")
	}
	baselinePath := filepath.Join(root, filepath.FromSlash(session.BaselineRef))
	file, err := os.OpenFile(baselinePath, os.O_WRONLY, 0o600)
	if err != nil {
		t.Fatal(err)
	}
	if err := file.Truncate(doBaselineSizeLimit + 1); err != nil {
		_ = file.Close()
		t.Fatal(err)
	}
	if err := file.Close(); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadDoSession(root, session.ID); err == nil || !strings.Contains(err.Error(), "64 MiB") {
		t.Fatalf("oversized sidecar was not bounded before reading: %v", err)
	}
}

func TestDoBaselineOwnerAndMetricsProjection(t *testing.T) {
	root, session := doStartFixture(t)
	metadata, ok := LookupArtifactType(session.BaselineRef)
	if !ok || metadata.TypeID != "do-baseline" || metadata.Owner != "specify-runtime do start" {
		t.Fatalf("baseline owner is unavailable: %+v", metadata)
	}
	prepared := NewArtifactService(root).Prepare(ArtifactPrepareRequest{Path: session.BaselineRef})
	if prepared.Status != "invalid" || len(prepared.Blockers) == 0 {
		t.Fatal("generic artifact writer acquired the immutable baseline")
	}
	sessions, warnings, err := readDoMetricsSessions(root)
	if err != nil || len(warnings) != 0 || len(sessions) != 1 || sessions[0].BaselineJSON != "" || sessions[0].BaselineRef != session.BaselineRef {
		t.Fatalf("metrics retains audit baseline or loses the session: count=%d warnings=%v err=%v", len(sessions), warnings, err)
	}
}

func TestDoBaselineAndSessionCreationRollBackTogether(t *testing.T) {
	root, input := doFixture(t)
	original := promoteTransactionFile
	t.Cleanup(func() { promoteTransactionFile = original })
	baselinePromoted := false
	promoteTransactionFile = func(target string, content []byte, perm os.FileMode) error {
		if filepath.Base(target) == "baseline.json" {
			baselinePromoted = true
		}
		if filepath.Base(target) == "session.json" {
			return fmt.Errorf("injected session publication failure after baseline promotion")
		}
		return original(target, content, perm)
	}
	if _, err := doStart(root, input); err == nil || !strings.Contains(err.Error(), "injected session publication") || !baselinePromoted {
		t.Fatalf("did not exercise rollback after baseline publication: promoted=%v err=%v", baselinePromoted, err)
	}
	for _, ref := range []string{doSessionRef(input.SessionID), doBaselineRef(input.SessionID)} {
		if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(ref))); !os.IsNotExist(err) {
			t.Fatalf("partial transaction left %s: %v", ref, err)
		}
	}
}

func TestDoBaselineRejectsRedirectedSessionDirectory(t *testing.T) {
	root, session := doStartFixture(t)
	_, digest, err := loadDoSession(root, session.ID)
	if err != nil {
		t.Fatal(err)
	}
	current := filepath.Join(root, filepath.Dir(filepath.FromSlash(doSessionRef(session.ID))))
	outside := filepath.Join(t.TempDir(), "session")
	if err := os.Rename(current, outside); err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS == "windows" {
		if output, err := exec.Command("cmd.exe", "/c", "mklink", "/J", current, outside).CombinedOutput(); err != nil {
			t.Fatalf("create isolated junction: %v %s", err, output)
		}
	} else if err := os.Symlink(outside, current); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadDoSession(root, session.ID); err == nil {
		t.Fatal("loaded baseline through redirected session directory")
	}
	if err := doWriteSession(root, session, digest, nil); err == nil {
		t.Fatal("wrote checkpoint through redirected session directory")
	}
}

func TestDoBaselineOversizePreflight(t *testing.T) {
	// The same serializer used before BeginWork enforces the baseline bound
	// independently of the compact checkpoint. No large Git fixture is needed.
	raw := strings.Repeat(" ", doBaselineSizeLimit+1)
	session := DoSession{SchemaVersion: doSessionSchema, ID: "oversize", BaselineRef: doBaselineRef("oversize"), BaselineJSON: raw, BaselineSHA256: doBytesDigest([]byte(raw))}
	if _, err := doSerializeSession(session); err == nil || !strings.Contains(err.Error(), "64 MiB") {
		t.Fatalf("oversize baseline passed the pre-Work serializer: %v", err)
	}
}
