package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFileTransactionAbsenceRejectsExistingNodesWithoutReading(t *testing.T) {
	for _, kind := range []string{"directory", "oversize-file"} {
		t.Run(kind, func(t *testing.T) {
			root := t.TempDir()
			gate := filepath.Join(root, "absent")
			if kind == "directory" {
				if err := os.Mkdir(gate, 0o700); err != nil {
					t.Fatal(err)
				}
			} else {
				file, err := os.Create(gate)
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
			}
			target := filepath.Join(root, "output")
			_, err := applyFileTransactionWithPreconditions(root, "test.absence", []fileTransactionUpdate{{Path: target, Content: []byte("output")}}, []fileTransactionPrecondition{{Path: gate, MustNotExist: true}})
			if err == nil || !strings.Contains(err.Error(), "expected the path to be absent") {
				t.Fatalf("existing %s was read or accepted by absence check: %v", kind, err)
			}
			if _, err := os.Stat(target); !os.IsNotExist(err) {
				t.Fatalf("failed absence gate published output: %v", err)
			}
		})
	}
}

func TestFileTransactionRecoversInterruptedPromotion(t *testing.T) {
	for _, existed := range []bool{false, true} {
		for _, promoted := range []bool{false, true} {
			name := "new"
			if existed {
				name = "existing"
			}
			if promoted {
				name += "/after-promotion"
			} else {
				name += "/before-promotion"
			}
			t.Run(name, func(t *testing.T) {
				root := t.TempDir()
				target := filepath.Join(root, "a.txt")
				if existed {
					if err := os.WriteFile(target, []byte("original"), 0o644); err != nil {
						t.Fatal(err)
					}
				}
				originalPromote := promoteTransactionFile
				t.Cleanup(func() { promoteTransactionFile = originalPromote })
				promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
					if promoted {
						if err := atomicWriteFile(path, content, perm); err != nil {
							t.Fatal(err)
						}
					}
					panic("interrupted promotion")
				}
				assertFileTransactionPanic(t, "interrupted promotion", func() {
					_, _ = applyFileTransaction(root, "test.interrupted", []fileTransactionUpdate{{Path: target, Content: []byte("replacement")}})
				})
				promoteTransactionFile = originalPromote
				if _, err := applyFileTransaction(root, "test.next", []fileTransactionUpdate{{Path: filepath.Join(root, "next.txt"), Content: []byte("next")}}); err != nil {
					t.Fatalf("next transaction must recover its predecessor: %v", err)
				}
				actual, err := os.ReadFile(target)
				if existed {
					if err != nil || string(actual) != "original" {
						t.Fatalf("original target not restored: %q, %v", actual, err)
					}
				} else if !os.IsNotExist(err) {
					t.Fatalf("new target survived rollback: %q, %v", actual, err)
				}
			})
		}
	}
}

func TestFileTransactionRetainsFailedRollbackAndCompletedProgress(t *testing.T) {
	for _, failAtCommit := range []bool{false, true} {
		name := "promotion-failure"
		if failAtCommit {
			name = "commit-journal-failure"
		}
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			first, second, third := filepath.Join(root, "a.txt"), filepath.Join(root, "b.txt"), filepath.Join(root, "c.txt")
			for _, path := range []string{first, second} {
				if err := os.WriteFile(path, []byte("original"), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			originalPromote, originalSync := promoteTransactionFile, syncAtomicTempFile
			t.Cleanup(func() { promoteTransactionFile, syncAtomicTempFile = originalPromote, originalSync })
			commitFailures := 0
			promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
				if path == third {
					syncAtomicTempFile = func(file *os.File) error {
						if failAtCommit && strings.HasPrefix(filepath.Base(file.Name()), ".journal.json.tmp-") {
							raw, err := os.ReadFile(file.Name())
							if err != nil {
								return err
							}
							var pending fileTransactionJournal
							if err := json.Unmarshal(raw, &pending); err != nil {
								return err
							}
							if pending.Phase == "committed" {
								commitFailures++
								return errors.New("injected commit journal failure")
							}
						}
						if strings.HasPrefix(filepath.Base(file.Name()), ".b.txt.tmp-") {
							return errors.New("injected rollback sync failure")
						}
						return originalSync(file)
					}
					if !failAtCommit {
						return errors.New("injected promotion failure")
					}
				}
				return atomicWriteFile(path, content, perm)
			}
			_, err := applyFileTransaction(root, "test.rollback-progress", []fileTransactionUpdate{
				{Path: first, Content: []byte("replacement")}, {Path: second, Content: []byte("replacement")}, {Path: third, Content: []byte("replacement")},
			})
			if err == nil || !strings.Contains(err.Error(), "rollback incomplete") {
				t.Fatalf("expected incomplete rollback: %v", err)
			}
			if failAtCommit && (commitFailures != 1 || !strings.Contains(err.Error(), "injected commit journal failure")) {
				t.Fatalf("commit must fail once, then allow rollback progress writes: failures=%d, error=%v", commitFailures, err)
			}
			journalPaths, err := filepath.Glob(filepath.Join(root, ".specify", "runtime", "transactions", "*", "journal.json"))
			if err != nil || len(journalPaths) != 1 {
				t.Fatalf("incomplete rollback must preserve one journal: %v, %v", journalPaths, err)
			}
			raw, err := os.ReadFile(journalPaths[0])
			if err != nil {
				t.Fatal(err)
			}
			var journal fileTransactionJournal
			if err := json.Unmarshal(raw, &journal); err != nil {
				t.Fatal(err)
			}
			if len(journal.Entries) != 3 || journal.Entries[0].Applied || !journal.Entries[1].Applied || journal.Entries[2].Applied {
				t.Fatalf("rollback progress not persisted: %#v", journal.Entries)
			}
			if journal.Version != 1 || journal.Phase != "applying" {
				t.Fatalf("failed rollback must retain a recoverable v1 journal: %#v", journal)
			}
			if actual, err := os.ReadFile(first); err != nil || string(actual) != "original" {
				t.Fatalf("failed rollback of b must not prevent safe recovery of a: %q, %v", actual, err)
			}
			if err := os.WriteFile(first, []byte("later user edit"), 0o644); err != nil {
				t.Fatal(err)
			}
			promoteTransactionFile, syncAtomicTempFile = originalPromote, originalSync
			if _, err := applyFileTransaction(root, "test.next", []fileTransactionUpdate{{Path: third, Content: []byte("next")}}); err != nil {
				t.Fatalf("retry failed: %v", err)
			}
			if actual, _ := os.ReadFile(first); string(actual) != "later user edit" {
				t.Fatalf("retry overwrote an already recovered target: %q", actual)
			}
			if actual, _ := os.ReadFile(second); string(actual) != "original" {
				t.Fatalf("retry did not recover the failed target: %q", actual)
			}
		})
	}
}

func TestFileTransactionRetriesRollbackAfterJournalFailure(t *testing.T) {
	for _, crash := range []bool{false, true} {
		name := "write-error"
		if crash {
			name = "interrupted-write"
		}
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			target := filepath.Join(root, "a.txt")
			if err := os.WriteFile(target, []byte("original"), 0o644); err != nil {
				t.Fatal(err)
			}
			originalPromote, originalSync := promoteTransactionFile, syncAtomicTempFile
			t.Cleanup(func() { promoteTransactionFile, syncAtomicTempFile = originalPromote, originalSync })
			promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
				if err := atomicWriteFile(path, content, perm); err != nil {
					return err
				}
				syncAtomicTempFile = func(file *os.File) error {
					if strings.HasPrefix(filepath.Base(file.Name()), ".journal.json.tmp-") {
						if crash {
							// Process termination closes handles; reproduce that before
							// unwinding so Windows does not retain an artificial lock.
							_ = file.Close()
							panic("interrupted rollback journal")
						}
						return errors.New("injected journal failure")
					}
					return originalSync(file)
				}
				return errors.New("injected post-promotion failure")
			}
			apply := func() {
				_, err := applyFileTransaction(root, "test.rollback-journal", []fileTransactionUpdate{{Path: target, Content: []byte("replacement")}})
				if err == nil || !strings.Contains(err.Error(), "rollback incomplete") {
					t.Fatalf("journal failure must retain the transaction: %v", err)
				}
			}
			if crash {
				assertFileTransactionPanic(t, "interrupted rollback journal", apply)
			} else {
				apply()
			}
			if actual, _ := os.ReadFile(target); string(actual) != "original" {
				t.Fatalf("target must be restored before rollback journal failure: %q", actual)
			}
			promoteTransactionFile, syncAtomicTempFile = originalPromote, originalSync
			if _, err := applyFileTransaction(root, "test.next", []fileTransactionUpdate{{Path: filepath.Join(root, "next.txt"), Content: []byte("next")}}); err != nil {
				t.Fatalf("already restored target must recover idempotently: %v", err)
			}
		})
	}
}

func TestFileTransactionRecoveryPreservesThirdPartyChanges(t *testing.T) {
	for _, existed := range []bool{false, true} {
		name := "new"
		if existed {
			name = "existing"
		}
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			target := filepath.Join(root, "a.txt")
			if existed {
				if err := os.WriteFile(target, []byte("original"), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			originalPromote := promoteTransactionFile
			t.Cleanup(func() { promoteTransactionFile = originalPromote })
			promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
				if err := atomicWriteFile(path, content, perm); err != nil {
					t.Fatal(err)
				}
				panic("interrupted promotion")
			}
			assertFileTransactionPanic(t, "interrupted promotion", func() {
				_, _ = applyFileTransaction(root, "test.interrupted", []fileTransactionUpdate{{Path: target, Content: []byte("replacement")}})
			})
			if err := os.WriteFile(target, []byte("user edit"), 0o644); err != nil {
				t.Fatal(err)
			}
			promoteTransactionFile = originalPromote
			next := filepath.Join(root, "next.txt")
			if _, err := applyFileTransaction(root, "test.next", []fileTransactionUpdate{{Path: next, Content: []byte("next")}}); err == nil {
				t.Fatal("third-party change must block recovery and the next transaction")
			}
			if actual, _ := os.ReadFile(target); string(actual) != "user edit" {
				t.Fatalf("recovery overwrote or deleted user edit: %q", actual)
			}
			if _, err := os.Stat(next); !os.IsNotExist(err) {
				t.Fatalf("blocked recovery admitted a new transaction: %v", err)
			}
		})
	}
}

func assertFileTransactionPanic(t *testing.T, expected string, operation func()) {
	t.Helper()
	defer func() {
		if actual := recover(); actual != expected {
			t.Fatalf("panic = %v, want %q", actual, expected)
		}
	}()
	operation()
}

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

func TestFileTransactionPreparationCrashesDoNotBlockFutureTransactions(t *testing.T) {
	for _, boundary := range []string{"backup", "stage", "journal"} {
		t.Run(boundary, func(t *testing.T) {
			root := t.TempDir()
			target := filepath.Join(root, "existing.json")
			if err := os.WriteFile(target, []byte("original"), 0o644); err != nil {
				t.Fatal(err)
			}
			originalSync := syncAtomicTempFile
			t.Cleanup(func() { syncAtomicTempFile = originalSync })
			syncAtomicTempFile = func(file *os.File) error {
				path := filepath.ToSlash(file.Name())
				matches := strings.Contains(path, "/"+boundary+"/")
				if boundary == "journal" {
					matches = strings.HasPrefix(filepath.Base(path), ".journal.json.tmp-")
				}
				if matches {
					// A terminated process closes its handles. Keep that property
					// when simulating the crash by unwinding on Windows.
					_ = file.Close()
					panic("preparation interrupted")
				}
				return originalSync(file)
			}
			assertFileTransactionPanic(t, "preparation interrupted", func() {
				_, _ = applyFileTransaction(root, "test.preparation-crash", []fileTransactionUpdate{{Path: target, Content: []byte("replacement")}})
			})
			syncAtomicTempFile = originalSync
			if actual, err := os.ReadFile(target); err != nil || string(actual) != "original" {
				t.Fatalf("preparation changed the target: %q, %v", actual, err)
			}
			transactions := filepath.Join(root, ".specify", "runtime", "transactions")
			active, err := filepath.Glob(filepath.Join(transactions, "TX-*"))
			if err != nil || len(active) != 0 {
				t.Fatalf("incomplete preparation became an active transaction: %v, %v", active, err)
			}
			preparing := filepath.Join(transactions, ".preparing")
			abandoned, err := os.ReadDir(preparing)
			if err != nil || len(abandoned) != 1 {
				t.Fatalf("expected one retained preparation: %v, %v", abandoned, err)
			}
			if _, err := applyFileTransaction(root, "test.after-preparation-crash", []fileTransactionUpdate{{Path: filepath.Join(root, "next.json"), Content: []byte("next")}}); err != nil {
				t.Fatalf("interrupted preparation blocked a later transaction: %v", err)
			}
			if _, err := os.Stat(filepath.Join(preparing, abandoned[0].Name())); err != nil {
				t.Fatalf("recovery must preserve abandoned preparation data: %v", err)
			}
		})
	}
}

func TestFileTransactionRecoveryPreservesActiveDirectoryWithMissingJournal(t *testing.T) {
	root := t.TempDir()
	active := filepath.Join(root, ".specify", "runtime", "transactions", "TX-"+strings.Repeat("1", 24))
	if err := os.MkdirAll(active, 0o755); err != nil {
		t.Fatal(err)
	}
	retained := filepath.Join(active, "unknown-recovery-data")
	if err := os.WriteFile(retained, []byte("retain"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err := applyFileTransaction(root, "test.missing-active-journal", []fileTransactionUpdate{{Path: filepath.Join(root, "next.json"), Content: []byte("next")}})
	if err == nil || !strings.Contains(err.Error(), "has no readable journal") {
		t.Fatalf("unknown active transaction must still fail closed: %v", err)
	}
	if actual, err := os.ReadFile(retained); err != nil || string(actual) != "retain" {
		t.Fatalf("unknown active recovery data was altered: %q, %v", actual, err)
	}
}
