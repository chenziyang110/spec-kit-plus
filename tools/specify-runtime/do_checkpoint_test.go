package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"
)

func TestDoCheckpointReadRetriesOnlyWindowsSharingConflicts(t *testing.T) {
	for _, test := range []struct {
		name, platform string
		err            error
		retries        bool
	}{
		{"sharing", "windows", syscall.Errno(32), true},
		{"lock", "windows", syscall.Errno(33), true},
		{"wrapped-sharing", "windows", fmt.Errorf("read checkpoint: %w", &os.PathError{Op: "open", Path: "session.json", Err: syscall.Errno(32)}), true},
		{"access-denied", "windows", syscall.Errno(5), false},
		{"permission", "windows", os.ErrPermission, false},
		{"missing", "windows", os.ErrNotExist, false},
		{"unrelated", "windows", errors.New("corrupt checkpoint"), false},
		{"other-platform", "linux", syscall.Errno(32), false},
	} {
		t.Run(test.name, func(t *testing.T) {
			root := t.TempDir()
			reads, waits := 0, 0
			want := []byte("the next current checkpoint")
			raw, err := doReadCheckpointWithRetry(root, "session.json", test.platform, func(target string) ([]byte, error) {
				reads++
				if target != filepath.Join(root, "session.json") {
					t.Fatalf("unexpected checkpoint path: %s", target)
				}
				if reads < 3 {
					return nil, test.err
				}
				return want, nil
			}, func(delay time.Duration) {
				waits++
				if delay != doCheckpointReadDelay {
					t.Fatalf("unexpected delay: %v", delay)
				}
			})
			if test.retries {
				if err != nil || reads != 3 || waits != 2 || !bytes.Equal(raw, want) {
					t.Fatalf("sharing conflict did not recover: reads=%d waits=%d raw=%q err=%v", reads, waits, raw, err)
				}
			} else if !errors.Is(err, test.err) || reads != 1 || waits != 0 || raw != nil {
				t.Fatalf("nontransient failure retried: reads=%d waits=%d raw=%q err=%v", reads, waits, raw, err)
			}
		})
	}
}

func TestDoCheckpointReadSharingDeadlineIsBounded(t *testing.T) {
	reads, waits := 0, 0
	var waited time.Duration
	_, err := doReadCheckpointWithRetry(t.TempDir(), "session.json", "windows", func(string) ([]byte, error) {
		reads++
		return nil, syscall.Errno(32)
	}, func(delay time.Duration) { waits++; waited += delay })
	if !errors.Is(err, syscall.Errno(32)) || reads != 11 || waits != 10 || waited != 100*time.Millisecond {
		t.Fatalf("sharing conflict exceeded its retry budget: reads=%d waits=%d waited=%v err=%v", reads, waits, waited, err)
	}
}

func TestDoCheckpointReadRechecksSecurePathAfterWait(t *testing.T) {
	root := filepath.Join(t.TempDir(), "project")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatal(err)
	}
	reads, waits := 0, 0
	_, err := doReadCheckpointWithRetry(root, "session.json", "windows", func(string) ([]byte, error) {
		reads++
		return nil, syscall.Errno(32)
	}, func(time.Duration) {
		waits++
		// Remove this empty fixture directory so the next secure resolution
		// fails. A cached path would incorrectly invoke the reader again.
		if err := os.Remove(root); err != nil {
			t.Fatal(err)
		}
	})
	if !errors.Is(err, os.ErrNotExist) || reads != 1 || waits != 1 {
		t.Fatalf("retry bypassed secure path resolution: reads=%d waits=%d err=%v", reads, waits, err)
	}
}

func TestDoCheckpointReadSuccessHasNoRetryOrDelay(t *testing.T) {
	for _, content := range []string{"valid bytes", "{invalid JSON", `{"definition_digest":"wrong"}`} {
		reads, waits := 0, 0
		raw, err := doReadCheckpointWithRetry(t.TempDir(), "session.json", "windows", func(string) ([]byte, error) {
			reads++
			return []byte(content), nil
		}, func(time.Duration) { waits++ })
		if err != nil || reads != 1 || waits != 0 || string(raw) != content {
			t.Fatalf("read boundary interpreted or retried data: reads=%d waits=%d err=%v", reads, waits, err)
		}
	}
}

func TestDoCheckpointLoadStillRejectsCorruptionAndChangedDigest(t *testing.T) {
	for _, test := range []struct{ name, raw, message string }{
		{"json", "{broken", "invalid character"},
		{"digest", `{"schema_version":1,"id":"checkpoint","revision":1,"definition":{},"definition_digest":"changed"}`, "frozen operation definition was changed"},
	} {
		t.Run(test.name, func(t *testing.T) {
			root, definition, _ := doMetricsFixture(t)
			ref := filepath.Join(root, filepath.FromSlash(doSessionRef("checkpoint")))
			if err := os.MkdirAll(filepath.Dir(ref), 0o700); err != nil {
				t.Fatal(err)
			}
			if test.name == "digest" {
				// Keep this fixture compatible if the owner's schema version changes.
				var value map[string]any
				_ = json.Unmarshal([]byte(test.raw), &value)
				value["schema_version"] = doSessionSchema
				value["definition"] = definition
				encoded, _ := json.Marshal(value)
				test.raw = string(encoded)
			}
			before := []byte(test.raw)
			if err := os.WriteFile(ref, before, 0o600); err != nil {
				t.Fatal(err)
			}
			if _, _, err := loadDoSession(root, "checkpoint"); err == nil || !strings.Contains(err.Error(), test.message) {
				t.Fatalf("invalid checkpoint accepted or obscured: %v", err)
			}
			after, err := os.ReadFile(ref)
			if err != nil || doBytesDigest(before) != doBytesDigest(after) {
				t.Fatal("failed read changed checkpoint", err)
			}
		})
	}
}
