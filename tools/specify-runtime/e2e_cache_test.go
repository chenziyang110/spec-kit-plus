package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"testing"
)

func e2eCacheFixture(t *testing.T) (*e2eService, e2eRef, e2eRef) {
	t.Helper()
	service := &e2eService{projectRoot: t.TempDir(), runID: "cache", rootRef: ".planning/e2e/cache"}
	service.resetReadRequest()
	payload := []byte("original immutable evidence")
	digest := fileContentSHA256(payload)
	blob := e2eRef{Ref: service.rootRef + "/blobs/" + digest + ".bin", SHA256: digest}
	e2eTestFile(t, service.projectRoot, blob.Ref, string(payload))
	value := e2eSubmission{SchemaVersion: "e2e-worker-result-v1", Outcome: "pass", WorkerResultInput: json.RawMessage(`{"status":"success"}`), WorkerResult: map[string]any{"nested": []any{map[string]any{"value": "original"}}}, Evidence: []e2eBinding{{Path: "evidence.txt", SHA256: digest, ArchiveRef: blob.Ref}}}
	ref, raw, err := service.snapshot(value)
	if err != nil {
		t.Fatal(err)
	}
	e2eTestFile(t, service.projectRoot, ref.Ref, string(raw))
	return service, ref, blob
}

func TestE2ECacheImmutableReuseAndCallerIsolation(t *testing.T) {
	service, ref, blob := e2eCacheFixture(t)
	var first e2eSubmission
	if err := service.readSnapshot(ref, &first); err != nil {
		t.Fatal(err)
	}
	before := service.immutable.reads
	originalInput := string(first.WorkerResultInput)
	if before != 2 || len(service.immutable.entries[blob].raw) != 0 {
		t.Fatal("snapshot and shared archive were not read once or large archive bytes were retained")
	}
	first.Evidence[0].Path = "poisoned"
	first.WorkerResult["nested"].([]any)[0].(map[string]any)["value"] = "poisoned"
	first.WorkerResultInput[0] = '!'
	var next e2eSubmission
	if err := service.readSnapshot(ref, &next); err != nil {
		t.Fatal(err)
	}
	if next.Evidence[0].Path != "evidence.txt" || next.WorkerResult["nested"].([]any)[0].(map[string]any)["value"] != "original" || string(next.WorkerResultInput) != originalInput {
		t.Fatalf("caller mutation escaped into the typed snapshot cache: %#v", next)
	}
	var firstMap, secondMap map[string]any
	if err := service.readSnapshot(ref, &firstMap); err != nil {
		t.Fatal(err)
	}
	firstMap["worker_result"].(map[string]any)["nested"].([]any)[0].(map[string]any)["value"] = "poisoned map"
	if err := service.readSnapshot(ref, &secondMap); err != nil {
		t.Fatal(err)
	}
	if secondMap["worker_result"].(map[string]any)["nested"].([]any)[0].(map[string]any)["value"] != "original" || service.immutable.reads != before || service.immutable.hits != 6 {
		t.Fatal("mixed target types reread immutable bytes or exposed cached maps")
	}
	if len(service.immutable.entries[ref].decoded) != 2 || service.observed[ref.Ref] != ref.SHA256 || service.observed[blob.Ref] != blob.SHA256 {
		t.Fatal("typed cache lost exact original commit bindings")
	}
	// A distinct snapshot can share the already verified archive in this request.
	next.WorkerID = "another-attempt"
	other, raw, err := service.snapshot(next)
	if err != nil {
		t.Fatal(err)
	}
	e2eTestFile(t, service.projectRoot, other.Ref, string(raw))
	if err := service.readSnapshot(other, &next); err != nil || service.immutable.reads != before+1 {
		t.Fatalf("shared archive was reread: %v", err)
	}
}

func TestE2ECacheParentHitRechecksIndirectPaths(t *testing.T) {
	for _, kind := range []string{"archive", "contract"} {
		for _, replacement := range []string{"directory", "alias"} {
			t.Run(kind+"/"+replacement, func(t *testing.T) {
				service, parent, child := e2eCacheFixture(t)
				if kind == "contract" {
					root := e2eTestInit(t, "execution")
					started := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker")
					service = &e2eService{projectRoot: root, runID: "run-1", rootRef: ".planning/e2e/run-1"}
					service.resetReadRequest()
					parent = e2eRef{Ref: started["packet_ref"].(string), SHA256: started["packet_sha256"].(string)}
					binding := started["packet"].(map[string]any)["contract_ref"].(map[string]any)
					child = e2eRef{Ref: binding["ref"].(string), SHA256: binding["sha256"].(string)}
				}
				var value map[string]any
				if err := service.readSnapshot(parent, &value); err != nil {
					t.Fatal(err)
				}
				reads := service.immutable.reads
				path := filepath.Join(service.projectRoot, filepath.FromSlash(child.Ref))
				if err := os.Chmod(path, 0o644); err != nil {
					t.Fatal(err)
				}
				if err := os.Remove(path); err != nil {
					t.Fatal(err)
				}
				if replacement == "directory" {
					if err := os.Mkdir(path, 0o755); err != nil {
						t.Fatal(err)
					}
				} else {
					target := filepath.Join(service.projectRoot, "isolated-alias-target")
					if err := os.Mkdir(target, 0o755); err != nil {
						t.Fatal(err)
					}
					if runtime.GOOS == "windows" {
						if output, err := exec.Command("cmd.exe", "/c", "mklink", "/J", path, target).CombinedOutput(); err != nil {
							t.Fatalf("create isolated child junction: %s: %v", output, err)
						}
					} else if err := os.Symlink(target, path); err != nil {
						t.Fatal(err)
					}
					defer os.Remove(path)
				}
				if err := service.readSnapshot(parent, &value); err == nil {
					t.Fatal("cached parent returned an unsafe/nonregular indirect evidence pointer")
				}
				if service.immutable.reads != reads {
					t.Fatal("indirect path check unnecessarily reread immutable bytes")
				}
			})
		}
	}
}

func TestE2ECacheRequestResetAndLiveReadsStayFresh(t *testing.T) {
	service, ref, blob := e2eCacheFixture(t)
	var value e2eSubmission
	if err := service.readSnapshot(ref, &value); err != nil {
		t.Fatal(err)
	}
	e2eTestFile(t, service.projectRoot, "live.txt", "before")
	if _, err := service.readFile("live.txt"); err != nil {
		t.Fatal(err)
	}
	e2eTestFile(t, service.projectRoot, "live.txt", "after")
	if raw, err := service.readFile("live.txt"); err != nil || string(raw) != "after" {
		t.Fatal("mutable bytes were cached")
	}
	e2eTestFile(t, service.projectRoot, blob.Ref, "corrupt between requests")
	service.resetReadRequest()
	if err := service.readSnapshot(ref, &value); err == nil {
		t.Fatal("new request reused an earlier immutable archive verdict")
	}
	if service.immutable.hits != 0 || service.immutable.reads != 2 {
		t.Fatal("reset did not reread snapshot and archive")
	}
	// The public owner entrypoint also resets a reused service, not only helpers.
	root := e2eTestInit(t, "execution")
	started := e2eTestMutation(t, root, "task-start", "--task-id", "S1", "--worker-id", "worker")
	owner := &e2eService{projectRoot: root, runID: "run-1", rootRef: ".planning/e2e/run-1"}
	if env := owner.run("status", nil); env.Status != "ok" {
		t.Fatal(env)
	}
	path := filepath.Join(root, filepath.FromSlash(started["packet_ref"].(string)))
	if err := os.Chmod(path, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("corrupt between public calls"), 0o644); err != nil {
		t.Fatal(err)
	}
	before := e2eViewsTree(t, root)
	if env := owner.run("status", nil); env.Status != "blocked" || !reflect.DeepEqual(before, e2eViewsTree(t, root)) {
		t.Fatal("public request entrypoint reused stale immutable state or mutated it")
	}
}

func TestE2ECacheHitStillChecksPathAndRegularFile(t *testing.T) {
	service, ref, _ := e2eCacheFixture(t)
	var value e2eSubmission
	if err := service.readSnapshot(ref, &value); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(service.projectRoot, filepath.FromSlash(ref.Ref))
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(path, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := service.readSnapshot(ref, &value); err == nil {
		t.Fatal("cache bypassed current regular-file path check")
	}
}

func TestE2ECacheHitRejectsReplacedPathAlias(t *testing.T) {
	for _, kind := range []string{"snapshot", "archive"} {
		t.Run(kind, func(t *testing.T) {
			service, snapshot, blob := e2eCacheFixture(t)
			var value e2eSubmission
			if err := service.readSnapshot(snapshot, &value); err != nil {
				t.Fatal(err)
			}
			ref := snapshot
			if kind == "archive" {
				ref = blob
			}
			parent := filepath.Dir(filepath.Join(service.projectRoot, filepath.FromSlash(ref.Ref)))
			target := parent + "-original"
			if err := os.Rename(parent, target); err != nil {
				t.Fatal(err)
			}
			if runtime.GOOS == "windows" {
				if output, err := exec.Command("cmd.exe", "/c", "mklink", "/J", parent, target).CombinedOutput(); err != nil {
					t.Fatalf("create isolated Windows junction: %s: %v", output, err)
				}
			} else if err := os.Symlink(target, parent); err != nil {
				t.Fatal(err)
			}
			defer os.Remove(parent)
			var err error
			if kind == "snapshot" {
				err = service.readSnapshot(snapshot, &value)
			} else {
				err = service.verifyBlob(blob.Ref, blob.SHA256)
			}
			if err == nil {
				t.Fatal("warm cache bypassed an internal symlink/junction boundary")
			}
		})
	}

}

func TestE2ECacheWarmReadsPreserveAtomicPreconditions(t *testing.T) {
	for _, kind := range []string{"snapshot", "archive", "live"} {
		t.Run(kind, func(t *testing.T) {
			root := e2eTestInit(t, "execution")
			e2eTestStartAndSubmit(t, root, "S1", "pass")
			shown := e2eTestData(t, root, "task-show", "--run-id", "run-1", "--task-id", "S1")
			revision := strconv.Itoa(int(shown["revision"].(float64)))
			packetRef := shown["task"].(map[string]any)["packet"].(map[string]any)["ref"].(string)
			ref := packetRef
			if kind == "archive" {
				raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(ref)))
				if err != nil {
					t.Fatal(err)
				}
				var packet e2ePacket
				if err := e2eDecode(raw, &packet); err != nil {
					t.Fatal(err)
				}
				ref = packet.Inputs[0].ArchiveRef
			} else if kind == "live" {
				ref = "request.md"
			}
			before := e2eViewsTree(t, root)
			var atCommit map[string]string
			service := &e2eService{projectRoot: root, runID: "run-1", rootRef: ".planning/e2e/run-1"}
			service.beforeCommit = func() error {
				if service.immutable.hits == 0 || service.observed[ref] == "" {
					t.Fatal("test did not reach a warm cache with exact commit binding")
				}
				path := filepath.Join(root, filepath.FromSlash(ref))
				if err := os.Chmod(path, 0o644); err != nil {
					return err
				}
				if err := os.WriteFile(path, []byte("changed after cached verification"), 0o644); err != nil {
					return err
				}
				// The mutation lock is held here on Windows. Expected bytes differ
				// only at the deliberately changed existing file; compare the whole
				// tree after the owner releases its lock.
				atCommit = before
				atCommit[filepath.FromSlash(ref)] = fileContentSHA256([]byte("changed after cached verification"))
				return nil
			}
			env := service.run("review-start", []string{"review-start", "--task-id", "S1", "--validator-id", "validator", "--expected-revision", revision})
			if env.Status == "ok" || atCommit == nil || !reflect.DeepEqual(atCommit, e2eViewsTree(t, root)) {
				t.Fatalf("cached verification allowed a partial write after changed %s: %v", kind, env)
			}
		})
	}
}
