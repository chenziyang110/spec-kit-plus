package main

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFileTransactionCommitsMultipleFilesAndWritesCompactReceipt(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, ".specify", "features", "001-demo", "state.json")
	second := filepath.Join(root, ".specify", "features", "001-demo", "state.md")

	receipt, err := applyFileTransaction(root, "test.multi-write", []fileTransactionUpdate{
		{Path: first, Content: []byte("{\"status\":\"ready\"}\n"), Perm: 0o644},
		{Path: second, Content: []byte("# Ready\n"), Perm: 0o644},
	})
	if err != nil {
		t.Fatalf("apply transaction: %v", err)
	}
	if receipt.TransactionID == "" || receipt.ReceiptRef == "" || len(receipt.ChangedPaths) != 2 {
		t.Fatalf("receipt = %#v", receipt)
	}
	if raw, err := os.ReadFile(first); err != nil || string(raw) != "{\"status\":\"ready\"}\n" {
		t.Fatalf("first file = %q, %v", raw, err)
	}
	if raw, err := os.ReadFile(second); err != nil || string(raw) != "# Ready\n" {
		t.Fatalf("second file = %q, %v", raw, err)
	}
	if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(receipt.ReceiptRef))); err != nil {
		t.Fatalf("receipt file missing: %v", err)
	}
}

func TestFileTransactionRollsBackEveryAppliedTargetOnFailure(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, ".specify", "features", "001-demo", "state.json")
	second := filepath.Join(root, ".specify", "features", "001-demo", "state.md")
	if err := os.MkdirAll(filepath.Dir(first), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(first, []byte("old-json\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(second, []byte("old-md\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	originalPromote := promoteTransactionFile
	t.Cleanup(func() { promoteTransactionFile = originalPromote })
	calls := 0
	promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
		calls++
		if calls == 2 {
			return errors.New("injected second promote failure")
		}
		return atomicWriteFile(path, content, perm)
	}

	_, err := applyFileTransaction(root, "test.rollback", []fileTransactionUpdate{
		{Path: first, Content: []byte("new-json\n"), Perm: 0o644},
		{Path: second, Content: []byte("new-md\n"), Perm: 0o644},
	})
	if err == nil {
		t.Fatal("transaction unexpectedly succeeded")
	}
	if raw, _ := os.ReadFile(first); string(raw) != "old-json\n" {
		t.Fatalf("first file was not rolled back: %q", raw)
	}
	if raw, _ := os.ReadFile(second); string(raw) != "old-md\n" {
		t.Fatalf("second file changed despite rollback: %q", raw)
	}
}

func TestFileTransactionChecksDigestAndAbsencePreconditionsBeforeMutation(t *testing.T) {
	root := t.TempDir()
	state := filepath.Join(root, ".specify", "features", "001-demo", "state.json")
	history := filepath.Join(root, ".specify", "features", "001-demo", "history.json")
	if err := os.MkdirAll(filepath.Dir(state), 0o755); err != nil {
		t.Fatal(err)
	}
	original := []byte("{\"revision\":1}\n")
	if err := os.WriteFile(state, original, 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := applyFileTransactionWithPreconditions(root, "test.cas", []fileTransactionUpdate{
		{Path: state, Content: []byte("{\"revision\":2}\n"), Perm: 0o644},
		{Path: history, Content: []byte("{\"revision\":1}\n"), Perm: 0o644},
	}, []fileTransactionPrecondition{
		{Path: state, ExpectedSHA256: strings.Repeat("0", 64)},
		{Path: history, MustNotExist: true},
	})
	if err == nil || !strings.Contains(err.Error(), "precondition failed") {
		t.Fatalf("stale digest precondition should fail: %v", err)
	}
	if raw, _ := os.ReadFile(state); string(raw) != string(original) {
		t.Fatalf("failed precondition mutated state: %q", raw)
	}
	if _, statErr := os.Stat(history); !os.IsNotExist(statErr) {
		t.Fatalf("failed precondition created history: %v", statErr)
	}

	if _, err := applyFileTransactionWithPreconditions(root, "test.cas", []fileTransactionUpdate{
		{Path: state, Content: []byte("{\"revision\":2}\n"), Perm: 0o644},
		{Path: history, Content: []byte("{\"revision\":1}\n"), Perm: 0o644},
	}, []fileTransactionPrecondition{
		{Path: state, ExpectedSHA256: fileContentSHA256(original)},
		{Path: history, MustNotExist: true},
	}); err != nil {
		t.Fatalf("valid preconditions should commit: %v", err)
	}
}
