//go:build windows

package main

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

type preparedDirectoryEntry struct {
	info   os.FileInfo
	digest string
}

type preparedDirectoryState struct {
	sourceParent os.FileInfo
	targetParent os.FileInfo
	entries      map[string]preparedDirectoryEntry
}

type preparedDirectoryPublishOps struct {
	move    func(string, string) error
	now     func() time.Time
	sleep   func(time.Duration)
	timeout time.Duration
}

func publishPreparedTransactionDirectory(source, target string, journal fileTransactionJournal) error {
	return publishPreparedTransactionDirectoryWithOps(source, target, journal, preparedDirectoryPublishOps{
		move: movePreparedDirectory, now: time.Now, sleep: time.Sleep, timeout: time.Second,
	})
}

func cleanupPreparedDirectoryPublicationFailure(string) {
	// A refused retry may have observed a replaced source directory. Preserve
	// its preparation for diagnosis; it is outside active transaction recovery.
}

// A freshly flushed/closed staging tree can temporarily reject its directory
// rename on Windows. Retry only that pre-publication operation, under the
// existing transaction lock, and never overwrite a competing destination.
func publishPreparedTransactionDirectoryWithOps(source, target string, journal fileTransactionJournal, ops preparedDirectoryPublishOps) error {
	if journal.Version != 1 || journal.Phase != "prepared" || len(journal.Entries) == 0 ||
		filepath.Base(source) != journal.TransactionID || filepath.Base(target) != journal.TransactionID ||
		filepath.Base(filepath.Dir(source)) != ".preparing" ||
		!strings.EqualFold(filepath.Dir(filepath.Dir(source)), filepath.Dir(target)) {
		return fmt.Errorf("prepared directory publication requires its exact prepared transaction")
	}
	rawJournal, err := json.MarshalIndent(journal, "", "  ")
	if err != nil {
		return err
	}
	rawJournal = append(rawJournal, '\n')
	if err := requirePreparedTargetAbsent(target); err != nil {
		return err
	}
	expected, err := preparedDirectoryLayout(journal, rawJournal)
	if err != nil {
		return err
	}
	original, err := capturePreparedDirectoryState(source, target, expected)
	if err != nil {
		return err
	}
	deadline := ops.now().Add(ops.timeout)
	delay := 10 * time.Millisecond
	var last error
	for attempt := 1; ; attempt++ {
		if attempt > 1 {
			if !ops.now().Before(deadline) {
				return fmt.Errorf("prepared directory publication retry deadline after %d attempts: %w", attempt-1, last)
			}
			if err := requirePreparedTargetAbsent(target); err != nil {
				return err
			}
			current, err := capturePreparedDirectoryState(source, target, expected)
			if err != nil {
				return err
			}
			if !samePreparedDirectoryState(original, current) {
				return fmt.Errorf("prepared directory identity or staged bytes changed before publication retry")
			}
			if !ops.now().Before(deadline) {
				return fmt.Errorf("prepared directory publication retry deadline after %d attempts: %w", attempt-1, last)
			}
		}
		// The native call also refuses a destination created after the check.
		last = ops.move(source, target)
		if last == nil {
			return nil
		}
		if !errors.Is(last, syscall.ERROR_ACCESS_DENIED) && !errors.Is(last, syscall.Errno(32)) {
			return last
		}
		remaining := deadline.Sub(ops.now())
		if remaining <= 0 {
			return fmt.Errorf("prepared directory publication retry deadline after %d attempts: %w", attempt, last)
		}
		wait := delay
		if wait > remaining {
			wait = remaining
		}
		ops.sleep(wait)
		if delay < 100*time.Millisecond {
			delay *= 2
			if delay > 100*time.Millisecond {
				delay = 100 * time.Millisecond
			}
		}
	}
}

func requirePreparedTargetAbsent(target string) error {
	if _, err := os.Lstat(target); !os.IsNotExist(err) {
		if err != nil {
			return fmt.Errorf("inspect prepared directory destination: %w", err)
		}
		return fmt.Errorf("prepared directory destination already exists")
	}
	return nil
}

type preparedDirectoryLayoutState struct {
	files    map[string]string
	children map[string]map[string]bool
}

func preparedDirectoryLayout(journal fileTransactionJournal, rawJournal []byte) (preparedDirectoryLayoutState, error) {
	layout := preparedDirectoryLayoutState{
		files:    map[string]string{"journal.json": fmt.Sprintf("%x", sha256.Sum256(rawJournal))},
		children: map[string]map[string]bool{".": {"journal.json": true}},
	}
	for _, entry := range journal.Entries {
		path := filepath.FromSlash(entry.Path)
		if path == "." || filepath.IsAbs(path) || filepath.Clean(path) != path || path == ".." || strings.HasPrefix(path, ".."+string(filepath.Separator)) {
			return layout, fmt.Errorf("prepared transaction contains an invalid path")
		}
		if entry.StageRef != filepath.ToSlash(filepath.Join("stage", path)) || (entry.Existed && entry.BackupRef != filepath.ToSlash(filepath.Join("backup", path))) {
			return layout, fmt.Errorf("prepared transaction contains an invalid staged path")
		}
		stage := strings.ToLower(filepath.FromSlash(entry.StageRef))
		if _, exists := layout.files[stage]; exists {
			return layout, fmt.Errorf("prepared transaction contains duplicate Windows staged paths")
		}
		layout.files[stage] = entry.AfterSHA256
		if entry.Existed {
			backup := strings.ToLower(filepath.FromSlash(entry.BackupRef))
			if _, exists := layout.files[backup]; exists {
				return layout, fmt.Errorf("prepared transaction contains duplicate Windows backup paths")
			}
			layout.files[backup] = entry.BeforeSHA256
		}
	}
	for path := range layout.files {
		for path != "." {
			parent := filepath.Dir(path)
			if layout.children[parent] == nil {
				layout.children[parent] = map[string]bool{}
			}
			layout.children[parent][filepath.Base(path)] = true
			path = parent
		}
	}
	return layout, nil
}

func capturePreparedDirectoryState(source, target string, expected preparedDirectoryLayoutState) (preparedDirectoryState, error) {
	state := preparedDirectoryState{entries: map[string]preparedDirectoryEntry{}}
	// Reuse the runtime's reparse-safe path owner for both full paths. The
	// journal then bounds enumeration to exactly the staged files and parents.
	for _, path := range []string{source, target} {
		volumeRoot := filepath.VolumeName(path) + string(filepath.Separator)
		rel, err := filepath.Rel(volumeRoot, path)
		if err != nil {
			return state, err
		}
		if _, err := secureProjectPath(volumeRoot, rel); err != nil {
			return state, err
		}
	}
	var err error
	state.sourceParent, err = readPreparedDirectoryEntry(filepath.Dir(source), nil)
	if err != nil {
		return state, err
	}
	state.targetParent, err = readPreparedDirectoryEntry(filepath.Dir(target), nil)
	if err != nil {
		return state, err
	}
	for rel, children := range expected.children {
		path, err := secureProjectPath(source, rel)
		if err != nil {
			return state, err
		}
		file, err := os.Open(path)
		if err != nil {
			return state, err
		}
		info, statErr := file.Stat()
		var found []os.FileInfo
		if statErr == nil && info.IsDir() {
			found, err = file.Readdir(len(children) + 1)
		} else if statErr == nil {
			err = fmt.Errorf("prepared publication entry must be a directory: %s", rel)
		}
		closeErr := file.Close()
		if statErr != nil {
			return state, statErr
		}
		if err != nil && err != io.EOF {
			return state, err
		}
		if closeErr != nil {
			return state, closeErr
		}
		if len(found) != len(children) {
			return state, fmt.Errorf("prepared directory membership changed: %s", rel)
		}
		for _, child := range found {
			if !children[strings.ToLower(child.Name())] {
				return state, fmt.Errorf("prepared directory contains an unexpected entry: %s", rel)
			}
		}
		state.entries[rel] = preparedDirectoryEntry{info: info}
	}
	for rel, digest := range expected.files {
		path, err := secureProjectPath(source, rel)
		if err != nil {
			return state, err
		}
		hash := sha256.New()
		stable, err := readPreparedDirectoryEntry(path, hash)
		if err != nil {
			return state, err
		}
		actual := fmt.Sprintf("%x", hash.Sum(nil))
		if !stable.Mode().IsRegular() || actual != digest {
			return state, fmt.Errorf("prepared staged file or journal bytes changed: %s", rel)
		}
		state.entries[rel] = preparedDirectoryEntry{info: stable, digest: actual}
	}
	return state, nil
}

// Handle-derived FileInfo eagerly binds Windows file identity. Plain Lstat
// can defer its identity lookup until after a path has already been replaced.
// Close every handle before publication so this guard cannot block the rename.
func readPreparedDirectoryEntry(path string, content io.Writer) (os.FileInfo, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	before, err := file.Stat()
	if err == nil && !before.IsDir() {
		if !before.Mode().IsRegular() {
			err = fmt.Errorf("prepared directory entry must be regular: %s", path)
		} else if content != nil {
			_, err = io.Copy(content, file)
		}
	}
	after, statErr := file.Stat()
	closeErr := file.Close()
	if err != nil {
		return nil, err
	}
	if statErr != nil {
		return nil, statErr
	}
	if closeErr != nil {
		return nil, closeErr
	}
	pathInfo, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !os.SameFile(before, after) || !os.SameFile(after, pathInfo) || before.Mode() != after.Mode() ||
		(!before.IsDir() && (before.Size() != after.Size() || !before.ModTime().Equal(after.ModTime()))) {
		return nil, fmt.Errorf("prepared directory entry changed while reading: %s", path)
	}
	return after, nil
}

func samePreparedDirectoryState(a, b preparedDirectoryState) bool {
	if !os.SameFile(a.sourceParent, b.sourceParent) || !os.SameFile(a.targetParent, b.targetParent) || len(a.entries) != len(b.entries) {
		return false
	}
	for path, first := range a.entries {
		second, ok := b.entries[path]
		if !ok || !os.SameFile(first.info, second.info) || first.info.Mode() != second.info.Mode() || first.digest != second.digest {
			return false
		}
	}
	return true
}

func movePreparedDirectory(source, target string) error {
	sourcePtr, err := syscall.UTF16PtrFromString(source)
	if err != nil {
		return err
	}
	targetPtr, err := syscall.UTF16PtrFromString(target)
	if err != nil {
		return err
	}
	result, _, callErr := moveFileExProc.Call(uintptr(unsafe.Pointer(sourcePtr)), uintptr(unsafe.Pointer(targetPtr)), moveFileWriteThrough)
	if result == 0 {
		return fmt.Errorf("publish prepared directory %q -> %q: %w", source, target, callErr)
	}
	return nil
}
