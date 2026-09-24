package main

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestTasksRebindTransactionRejectsChangedFrozenSources(t *testing.T) {
	for _, change := range []string{"edit", "add", "remove"} {
		t.Run(change, func(t *testing.T) {
			fixture := newTaskRebindFixture(t)
			updates, preconditions, verify := prepareTaskRebindSourceTransaction(t, fixture)
			before := snapshotTaskRebindTransactionPaths(t, fixture.root,
				fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
			sourcePath := filepath.Join(fixture.root, "src", "approval.go")
			var changedSource []byte
			switch change {
			case "edit":
				changedSource = []byte("package approval\n// behavior changed after producer verification\n")
				if err := os.WriteFile(sourcePath, changedSource, 0o644); err != nil {
					t.Fatal(err)
				}
			case "add":
				sourcePath = filepath.Join(fixture.root, "src", "new_approval.go")
				changedSource = []byte("package approval\n// newly included source\n")
				if err := os.WriteFile(sourcePath, changedSource, 0o644); err != nil {
					t.Fatal(err)
				}
			case "remove":
				if err := os.Remove(sourcePath); err != nil {
					t.Fatal(err)
				}
			}
			calls := 0
			_, err := applyFileTransactionWithVerification(fixture.root, "tasks.rebind", updates, preconditions, func() error {
				calls++
				return verify()
			})
			if err == nil || !strings.Contains(err.Error(), "source fingerprint changed") || calls != 1 {
				t.Fatalf("%s after capture did not fail the source verification: calls=%d err=%v", change, calls, err)
			}
			after := snapshotTaskRebindTransactionPaths(t, fixture.root,
				fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
			if !reflect.DeepEqual(before, after) {
				t.Fatal("stale sources changed producer/task artifacts, history, transaction staging, or receipts")
			}
			// Verification must preserve the concurrent source change as well.
			if change == "remove" {
				if _, err := os.Stat(sourcePath); !os.IsNotExist(err) {
					t.Fatalf("source verification restored a removed file: %v", err)
				}
			} else if !bytes.Equal(readTaskRebindFile(t, sourcePath), changedSource) {
				t.Fatal("source verification overwrote the concurrent source change")
			}
		})
	}
}

func TestFileTransactionVerificationFailsBeforeStaging(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	updates, preconditions, _ := prepareTaskRebindSourceTransaction(t, fixture)
	before := snapshotTaskRebindTransactionPaths(t, fixture.root,
		fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
	beforeStorage := snapshotTaskRebindTransactionPaths(t, fixture.root,
		".specify/runtime/transactions", ".specify/runtime/receipts")
	var duringVerification map[string][]byte
	calls := 0
	fault := errors.New("source verification could not read its required input")
	_, err := applyFileTransactionWithVerification(fixture.root, "tasks.rebind", updates, preconditions, func() error {
		calls++
		duringVerification = snapshotTaskRebindTransactionPaths(t, fixture.root,
			".specify/runtime/transactions", ".specify/runtime/receipts")
		return fault
	})
	if !errors.Is(err, fault) || calls != 1 {
		t.Fatalf("verification failure was not propagated: calls=%d err=%v", calls, err)
	}
	if !reflect.DeepEqual(beforeStorage, duringVerification) {
		t.Fatal("transaction staging or receipt publication began before verification")
	}
	after := snapshotTaskRebindTransactionPaths(t, fixture.root,
		fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
	if !reflect.DeepEqual(before, after) {
		t.Fatal("verification failure changed output artifacts, history, staging, or receipts")
	}
}

func TestFileTransactionPreconditionFailureSkipsVerification(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	updates, preconditions, _ := prepareTaskRebindSourceTransaction(t, fixture)
	// The frozen producer state sorts after the output artifacts. Its failed
	// guard must prevent verification even when every earlier CAS succeeds.
	statePath := filepath.Join(fixture.feature, "test-design", "test-state.json")
	for i := range preconditions {
		if preconditions[i].Path == statePath {
			preconditions[i].ExpectedSHA256 = strings.Repeat("0", 64)
		}
	}
	before := snapshotTaskRebindTransactionPaths(t, fixture.root,
		fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
	calls := 0
	_, err := applyFileTransactionWithVerification(fixture.root, "tasks.rebind", updates, preconditions, func() error {
		calls++
		return errors.New("verification must not run before successful CAS")
	})
	if err == nil || !strings.Contains(err.Error(), "precondition failed") || !strings.Contains(err.Error(), "test-state.json") || calls != 0 {
		t.Fatalf("failed CAS invoked verification or returned the wrong error: calls=%d err=%v", calls, err)
	}
	after := snapshotTaskRebindTransactionPaths(t, fixture.root,
		fixture.featureRef, ".specify/runtime/transactions", ".specify/runtime/receipts")
	if !reflect.DeepEqual(before, after) {
		t.Fatal("failed CAS changed output artifacts, history, staging, or receipts")
	}
}

func TestTasksRebindTransactionCommitsWithUnchangedFrozenSources(t *testing.T) {
	fixture := newTaskRebindFixture(t)
	updates, preconditions, verify := prepareTaskRebindSourceTransaction(t, fixture)
	before := snapshotTaskRebindTransactionPaths(t, fixture.root, fixture.featureRef)
	calls := 0
	receipt, err := applyFileTransactionWithVerification(fixture.root, "tasks.rebind", updates, preconditions, func() error {
		calls++
		return verify()
	})
	if err != nil || calls != 1 {
		t.Fatalf("unchanged frozen sources should permit publication: calls=%d err=%v", calls, err)
	}
	if receipt.TransactionID == "" || len(receipt.ChangedPaths) != len(updates) {
		t.Fatalf("verified transaction did not return a complete publication receipt: %#v", receipt)
	}
	changed := map[string]bool{}
	for _, update := range updates {
		if !bytes.Equal(readTaskRebindFile(t, update.Path), update.Content) {
			t.Fatalf("verified transaction did not publish %s", update.Path)
		}
		changed[projectRelativeSlash(fixture.root, update.Path)] = true
	}
	after := snapshotTaskRebindTransactionPaths(t, fixture.root, fixture.featureRef)
	for path, content := range before {
		if !changed[path] && !reflect.DeepEqual(content, after[path]) {
			t.Fatalf("verified transaction changed an unrelated producer/lifecycle artifact: %s", path)
		}
	}
	if err := validateTaskControlFreshness(fixture.root, fixture.feature,
		readImplementJSONFile(t, filepath.Join(fixture.feature, "task-index.json"))); err != nil {
		t.Fatalf("verified transaction published stale handoffs: %v", err)
	}
}

// Prepare a real current binding, Markdown, and both downstream handoffs, then
// exercise the transaction boundary directly. Source changes occur after
// preparation; no global hook or production race-injection seam is needed.
func prepareTaskRebindSourceTransaction(t *testing.T, fixture taskRebindFixture) ([]fileTransactionUpdate, []fileTransactionPrecondition, func() error) {
	t.Helper()
	statePath := filepath.Join(fixture.feature, "test-design", "test-state.json")
	frozenRaw := readTaskRebindFile(t, statePath)
	verify, err := taskRebindSourceVerification(fixture.root, frozenRaw)
	if err != nil {
		t.Fatal(err)
	}
	if err := verify(); err != nil {
		t.Fatalf("fixture sources must be current at capture: %v", err)
	}
	indexPath := filepath.Join(fixture.feature, "task-index.json")
	beforeIndex := readTaskRebindFile(t, indexPath)
	index := readImplementJSONFile(t, indexPath)
	if err := taskControlValidateTestDesignBinding(fixture.root, fixture.feature, index, true, true); err != nil {
		t.Fatal(err)
	}
	indexRaw, err := marshalTaskControlJSON(index)
	if err != nil {
		t.Fatal(err)
	}
	updates := []fileTransactionUpdate{{Path: indexPath, Content: indexRaw, Perm: 0o644}}
	preconditions := []fileTransactionPrecondition{
		{Path: indexPath, ExpectedSHA256: taskControlSHA256(beforeIndex)},
		{Path: statePath, ExpectedSHA256: taskControlSHA256(frozenRaw)},
	}
	markdownPath := filepath.Join(fixture.feature, "tasks.md")
	beforeMarkdown := readTaskRebindFile(t, markdownPath)
	title := filepath.Base(fixture.feature)
	if first, _, _ := strings.Cut(string(beforeMarkdown), "\n"); strings.HasPrefix(first, "# Tasks:") {
		title = strings.TrimSpace(strings.TrimPrefix(first, "# Tasks:"))
	}
	markdown, err := renderTaskControlMarkdown(index, title)
	if err != nil {
		t.Fatal(err)
	}
	updates = append(updates, fileTransactionUpdate{Path: markdownPath, Content: []byte(markdown), Perm: 0o644})
	preconditions = append(preconditions, fileTransactionPrecondition{Path: markdownPath, ExpectedSHA256: taskControlSHA256(beforeMarkdown)})
	for _, target := range []string{"tasks", "implement"} {
		path := filepath.Join(fixture.feature, "handoff-to-"+target+".json")
		raw, err := marshalTaskControlJSON(taskControlHandoff(index, indexRaw, target))
		if err != nil {
			t.Fatal(err)
		}
		updates = append(updates, fileTransactionUpdate{Path: path, Content: raw, Perm: 0o644})
		preconditions = append(preconditions, fileTransactionPrecondition{Path: path, ExpectedSHA256: taskControlSHA256(readTaskRebindFile(t, path))})
	}
	historyRaw, err := marshalTaskControlJSON(map[string]any{
		"version": 1, "kind": "tasks.rebind", "reason": "Verify the frozen source at publication.",
		"previous_task_index_sha256": taskControlSHA256(beforeIndex), "previous_task_index": string(beforeIndex),
		"task_index_sha256": taskControlSHA256(indexRaw),
	})
	if err != nil {
		t.Fatal(err)
	}
	historyPath := filepath.Join(fixture.feature, "task-rebind-history", taskControlSHA256(historyRaw)+".json")
	updates = append(updates, fileTransactionUpdate{Path: historyPath, Content: historyRaw, Perm: 0o644})
	preconditions = append(preconditions, fileTransactionPrecondition{Path: historyPath, MustNotExist: true})
	return updates, preconditions, verify
}

// Include directory membership so a callback cannot stage files and clean
// them up later while a failure test only notices unchanged final artifacts.
func snapshotTaskRebindTransactionPaths(t *testing.T, root string, refs ...string) map[string][]byte {
	t.Helper()
	result := map[string][]byte{}
	for _, ref := range refs {
		base := filepath.Join(root, filepath.FromSlash(ref))
		err := filepath.WalkDir(base, func(path string, entry os.DirEntry, walkErr error) error {
			if path == base && os.IsNotExist(walkErr) {
				return nil
			}
			if walkErr != nil {
				return walkErr
			}
			pathRef := projectRelativeSlash(root, path)
			if entry.IsDir() {
				result[pathRef+"/"] = nil
				return nil
			}
			result[pathRef] = readTaskRebindFile(t, path)
			return nil
		})
		if err != nil {
			t.Fatal(err)
		}
	}
	return result
}
