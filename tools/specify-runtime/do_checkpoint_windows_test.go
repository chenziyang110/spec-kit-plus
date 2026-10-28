//go:build windows

package main

import (
	"errors"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"testing"
	"time"

	"golang.org/x/sys/windows"
)

func TestDoCheckpointWindowsRecoversActualDeniedSharingHandle(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "checkpoint", definition, context, "pending", 1)
	writeDoMetricsSession(t, root, session)
	path := filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID)))
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	encoded, err := windows.UTF16PtrFromString(path)
	if err != nil {
		t.Fatal(err)
	}
	handle, err := windows.CreateFile(encoded, windows.GENERIC_READ, 0, nil, windows.OPEN_EXISTING, windows.FILE_ATTRIBUTE_NORMAL, 0)
	if err != nil {
		t.Fatal(err)
	}
	var once sync.Once
	var closeErr error
	release := func() { once.Do(func() { closeErr = windows.CloseHandle(handle) }) }
	defer release()
	if _, err := secureProjectReadFile(root, doSessionRef(session.ID)); !errors.Is(err, syscall.Errno(32)) {
		t.Fatalf("fixture did not produce a real sharing violation: %v", err)
	}
	released := make(chan struct{})
	go func() {
		time.Sleep(20 * time.Millisecond)
		release()
		close(released)
	}()
	loaded, digest, loadErr := loadDoSession(root, session.ID)
	<-released
	if closeErr != nil {
		t.Fatal(closeErr)
	}
	if loadErr != nil || loaded.ID != session.ID || digest != doBytesDigest(before) {
		t.Fatalf("actual checkpoint reader did not recover: id=%s digest=%s err=%v", loaded.ID, digest, loadErr)
	}
	after, err := os.ReadFile(path)
	if err != nil || doBytesDigest(after) != doBytesDigest(before) {
		t.Fatal("checkpoint read mutated state", err)
	}
}
