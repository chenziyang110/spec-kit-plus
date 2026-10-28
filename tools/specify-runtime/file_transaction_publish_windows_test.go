//go:build windows

package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"
)

func preparedPublishFixture(t *testing.T, atomic bool) (string, string, fileTransactionJournal) {
	t.Helper()
	root := filepath.Join(t.TempDir(), ".specify", "runtime", "transactions")
	source, target := filepath.Join(root, ".preparing", "TX-fixture"), filepath.Join(root, "TX-fixture")
	body := []byte("{\"diagnostic\":true}\n")
	journal := fileTransactionJournal{Version: 1, TransactionID: "TX-fixture", Kind: "test.publish", Phase: "prepared", Entries: []fileTransactionEntry{{Path: ".specify/do/sessions/2026-10-11-diagnostic/session.json", StageRef: "stage/.specify/do/sessions/2026-10-11-diagnostic/session.json", AfterSHA256: fileContentSHA256(body)}}}
	stage := filepath.Join(source, filepath.FromSlash(journal.Entries[0].StageRef))
	if err := os.MkdirAll(filepath.Dir(stage), 0o755); err != nil {
		t.Fatal(err)
	}
	write := os.WriteFile
	if atomic {
		write = atomicWriteFile
	}
	if err := write(stage, body, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := writeFileTransactionJournal(filepath.Join(source, "journal.json"), journal); err != nil {
		t.Fatal(err)
	}
	return source, target, journal
}

func preparedPublishFakeClock(move func(string, string) error, timeout time.Duration) (preparedDirectoryPublishOps, *time.Time) {
	now := time.Date(2026, 10, 11, 0, 0, 0, 0, time.UTC)
	return preparedDirectoryPublishOps{move: move, now: func() time.Time { return now }, sleep: func(wait time.Duration) { now = now.Add(wait) }, timeout: timeout}, &now
}

func TestPreparedTransactionPublishTransientNativeErrorsRecover(t *testing.T) {
	for _, code := range []syscall.Errno{syscall.ERROR_ACCESS_DENIED, 32} {
		t.Run(fmt.Sprint(uint32(code)), func(t *testing.T) {
			source, target, journal := preparedPublishFixture(t, false)
			calls := 0
			ops, _ := preparedPublishFakeClock(func(s, d string) error {
				calls++
				if calls <= 2 {
					return fmt.Errorf("injected native error: %w", code)
				}
				return movePreparedDirectory(s, d)
			}, time.Second)
			if err := publishPreparedTransactionDirectoryWithOps(source, target, journal, ops); err != nil {
				t.Fatal(err)
			}
			if calls < 3 {
				t.Fatalf("transient native error was not retried: %d", calls)
			}
			if _, err := os.Stat(filepath.Join(target, "journal.json")); err != nil {
				t.Fatal(err)
			}
			if _, err := os.Stat(source); !os.IsNotExist(err) {
				t.Fatalf("prepared source still exists: %v", err)
			}
		})
	}
}

func TestPreparedTransactionPublishPermanentErrorExhaustsDeadline(t *testing.T) {
	for _, code := range []syscall.Errno{syscall.ERROR_ACCESS_DENIED, 32} {
		t.Run(fmt.Sprint(uint32(code)), func(t *testing.T) {
			source, target, journal := preparedPublishFixture(t, false)
			calls := 0
			ops, clock := preparedPublishFakeClock(func(string, string) error { calls++; return code }, 25*time.Millisecond)
			start := *clock
			err := publishPreparedTransactionDirectoryWithOps(source, target, journal, ops)
			if err == nil || !errors.Is(err, code) || !strings.Contains(err.Error(), "deadline") || calls != 2 || clock.Sub(start) != 25*time.Millisecond {
				t.Fatalf("permanent native denial did not stop at deadline: calls=%d elapsed=%v error=%v", calls, clock.Sub(start), err)
			}
			if _, err := os.Stat(filepath.Join(source, "journal.json")); err != nil {
				t.Fatal(err)
			}
			if _, err := os.Stat(target); !os.IsNotExist(err) {
				t.Fatalf("deadline published a target: %v", err)
			}
		})
	}
}

func TestPreparedTransactionPublishNativeHandleDenialThenRelease(t *testing.T) {
	source, target, journal := preparedPublishFixture(t, false)
	name, err := syscall.UTF16PtrFromString(source)
	if err != nil {
		t.Fatal(err)
	}
	handle, err := syscall.CreateFile(name, syscall.GENERIC_READ, syscall.FILE_SHARE_READ|syscall.FILE_SHARE_WRITE, nil, syscall.OPEN_EXISTING, syscall.FILE_FLAG_BACKUP_SEMANTICS, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		if handle != syscall.InvalidHandle {
			_ = syscall.CloseHandle(handle)
		}
	}()
	start := time.Now()
	err = publishPreparedTransactionDirectoryWithOps(source, target, journal, preparedDirectoryPublishOps{move: movePreparedDirectory, now: time.Now, sleep: time.Sleep, timeout: 30 * time.Millisecond})
	if err == nil || !errors.Is(err, syscall.Errno(32)) || !strings.Contains(err.Error(), "deadline") || time.Since(start) < 30*time.Millisecond {
		t.Fatalf("actual non-delete-shared handle did not hold publication through deadline: %v", err)
	}
	if err := syscall.CloseHandle(handle); err != nil {
		t.Fatal(err)
	}
	handle = syscall.InvalidHandle
	if err := publishPreparedTransactionDirectory(source, target, journal); err != nil {
		t.Fatalf("release did not recover actual native publication: %v", err)
	}
}

func TestPreparedTransactionPublishRefusesChangedPreparation(t *testing.T) {
	for _, change := range []string{"same-size-mtime-stage", "journal", "source-identity", "extra-file"} {
		t.Run(change, func(t *testing.T) {
			source, target, journal := preparedPublishFixture(t, false)
			calls := 0
			ops, _ := preparedPublishFakeClock(func(string, string) error {
				calls++
				stage := filepath.Join(source, filepath.FromSlash(journal.Entries[0].StageRef))
				switch change {
				case "same-size-mtime-stage":
					info, err := os.Stat(stage)
					if err != nil {
						t.Fatal(err)
					}
					body, err := os.ReadFile(stage)
					if err != nil {
						t.Fatal(err)
					}
					body[0] = ' '
					if err := os.WriteFile(stage, body, 0o644); err != nil {
						t.Fatal(err)
					}
					if err := os.Chtimes(stage, info.ModTime(), info.ModTime()); err != nil {
						t.Fatal(err)
					}
				case "journal":
					if err := os.WriteFile(filepath.Join(source, "journal.json"), []byte("{}\n"), 0o644); err != nil {
						t.Fatal(err)
					}
				case "extra-file":
					if err := os.WriteFile(filepath.Join(source, "other.json"), []byte("{}\n"), 0o644); err != nil {
						t.Fatal(err)
					}
				case "source-identity":
					body, err := os.ReadFile(stage)
					if err != nil {
						t.Fatal(err)
					}
					raw, err := os.ReadFile(filepath.Join(source, "journal.json"))
					if err != nil {
						t.Fatal(err)
					}
					if err := os.RemoveAll(source); err != nil {
						t.Fatal(err)
					}
					if err := os.MkdirAll(filepath.Dir(stage), 0o755); err != nil {
						t.Fatal(err)
					}
					if err := os.WriteFile(stage, body, 0o644); err != nil {
						t.Fatal(err)
					}
					if err := os.WriteFile(filepath.Join(source, "journal.json"), raw, 0o644); err != nil {
						t.Fatal(err)
					}
				}
				return syscall.ERROR_ACCESS_DENIED
			}, time.Second)
			err := publishPreparedTransactionDirectoryWithOps(source, target, journal, ops)
			if err == nil || calls != 1 {
				t.Fatalf("changed preparation was retried: %d %v", calls, err)
			}
			if _, err := os.Stat(target); !os.IsNotExist(err) {
				t.Fatalf("changed preparation was published: %v", err)
			}
		})
	}
}

func TestPreparedTransactionPublishRefusesCompetingTarget(t *testing.T) {
	source, target, journal := preparedPublishFixture(t, false)
	calls := 0
	ops, _ := preparedPublishFakeClock(func(s, d string) error {
		calls++
		if err := os.Mkdir(d, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(d, "other-owner.txt"), []byte("keep"), 0o644); err != nil {
			t.Fatal(err)
		}
		// This is after the absence check, so native no-replace must protect it.
		return movePreparedDirectory(s, d)
	}, time.Second)
	if err := publishPreparedTransactionDirectoryWithOps(source, target, journal, ops); err == nil || calls != 1 {
		t.Fatalf("competing target was retried/overwritten: %d %v", calls, err)
	}
	if raw, err := os.ReadFile(filepath.Join(target, "other-owner.txt")); err != nil || string(raw) != "keep" {
		t.Fatalf("competing target changed: %q %v", raw, err)
	}
	if _, err := os.Stat(filepath.Join(source, "journal.json")); err != nil {
		t.Fatal(err)
	}
}

func TestPreparedTransactionPublishNonRetryErrorAndOrdinaryReplacement(t *testing.T) {
	source, target, journal := preparedPublishFixture(t, false)
	calls := 0
	ops, _ := preparedPublishFakeClock(func(string, string) error { calls++; return syscall.ERROR_PATH_NOT_FOUND }, time.Second)
	if err := publishPreparedTransactionDirectoryWithOps(source, target, journal, ops); !errors.Is(err, syscall.ERROR_PATH_NOT_FOUND) || calls != 1 {
		t.Fatalf("non-recoverable error retried: %d %v", calls, err)
	}
	root := t.TempDir()
	from, to := filepath.Join(root, "source.txt"), filepath.Join(root, "target.txt")
	if err := os.WriteFile(from, []byte("new"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(to, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := replaceFile(from, to); err != nil {
		t.Fatal(err)
	}
	if raw, err := os.ReadFile(to); err != nil || string(raw) != "new" {
		t.Fatalf("ordinary replacement changed: %q %v", raw, err)
	}
}

func TestPreparedTransactionPublishNativePairedSamples(t *testing.T) {
	// Preserve the original 80 x three timing-control denominator. Aggregate
	// PASS does not substitute for the per-operation records below.
	for n := 0; n < 80; n++ {
		for _, profile := range []string{"empty-native", "fresh-atomic-files", "fresh-atomic-files-delay50ms"} {
			if profile == "empty-native" {
				root := t.TempDir()
				source, target := filepath.Join(root, "source"), filepath.Join(root, "target")
				if err := os.Mkdir(source, 0o755); err != nil {
					t.Fatal(err)
				}
				err := movePreparedDirectory(source, target)
				t.Logf("E1_NATIVE_SAMPLE profile=%s iteration=%d outcome=%v", profile, n, err)
				if err != nil {
					t.Error(err)
				}
				continue
			}
			source, target, journal := preparedPublishFixture(t, true)
			if strings.Contains(profile, "delay50ms") {
				time.Sleep(50 * time.Millisecond)
			}
			err := publishPreparedTransactionDirectory(source, target, journal)
			t.Logf("E1_NATIVE_SAMPLE profile=%s iteration=%d outcome=%v", profile, n, err)
			if err != nil {
				t.Error(err)
			}
		}
	}
}

func TestPreparedTransactionPublishWindowsDirectoryCasing(t *testing.T) {
	root := t.TempDir()
	updates := []fileTransactionUpdate{
		{Path: filepath.Join(root, "Docs", "A.txt"), Content: []byte("alpha")},
		{Path: filepath.Join(root, "docs", "B.txt"), Content: []byte("beta")},
	}
	if _, err := applyFileTransaction(root, "test.windows-case", updates); err != nil {
		t.Fatal(err)
	}
	for _, update := range updates {
		raw, err := os.ReadFile(update.Path)
		if err != nil || string(raw) != string(update.Content) {
			t.Fatalf("real transaction outputs differ: %q %v", raw, err)
		}
	}
}

func TestPreparedTransactionPublishRefusesWindowsFileAliases(t *testing.T) {
	root := t.TempDir()
	updates := []fileTransactionUpdate{
		{Path: filepath.Join(root, "Docs", "A.txt"), Content: []byte("alpha")},
		{Path: filepath.Join(root, "docs", "a.txt"), Content: []byte("beta")},
	}
	if _, err := applyFileTransaction(root, "test.windows-file-alias", updates); err == nil || !strings.Contains(err.Error(), "duplicate Windows staged paths") {
		t.Fatalf("two aliased staged files were published: %v", err)
	}
	for _, update := range updates {
		if _, err := os.Stat(update.Path); !os.IsNotExist(err) {
			t.Fatalf("refused aliases changed a project file: %v", err)
		}
	}
}
