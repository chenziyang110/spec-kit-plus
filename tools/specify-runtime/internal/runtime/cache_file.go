package runtime

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// WriteCacheFile publishes a disposable navigation cache, never a state receipt
// or a graph transaction. The parent directory must already exist. Identical
// bytes leave the existing file unchanged; different bytes are prepared in a
// private sibling before using the same platform replacement as status files.
// On Unix readers see an entire old or new file. Other platforms retain the
// existing replacement owner's guarantees and surface any replacement error.
// This is not crash durability, freshness validation, or a hostile-writer sandbox.
func WriteCacheFile(path string, data []byte) error {
	return writeCacheFile(path, data, replaceStatusFile)
}

func writeCacheFile(path string, data []byte, replace func(string, string) error) error {
	mode := os.FileMode(0o600)
	info, err := os.Lstat(path)
	switch {
	case err == nil:
		if !info.Mode().IsRegular() {
			return fmt.Errorf("cache target is not a regular file: %s", path)
		}
		mode = info.Mode().Perm()
		if info.Size() == int64(len(data)) {
			same, err := cacheFileMatches(path, data)
			if err != nil {
				return err
			}
			if same {
				return nil
			}
		}
	case !errors.Is(err, os.ErrNotExist):
		return fmt.Errorf("inspect cache target: %w", err)
	}

	file, err := os.CreateTemp(filepath.Dir(path), ".cognition-cache-*.tmp")
	if err != nil {
		return fmt.Errorf("create temporary cache: %w", err)
	}
	tmp := file.Name()
	defer func() {
		_ = file.Close()
		_ = os.Remove(tmp)
	}()
	if _, err := file.Write(data); err != nil {
		return fmt.Errorf("write temporary cache: %w", err)
	}
	// Keep existing permission bits, but do not widen access for new files or
	// alter the process-wide umask. The temporary file stays private while written.
	if err := file.Chmod(mode); err != nil {
		return fmt.Errorf("set cache permissions: %w", err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("close temporary cache: %w", err)
	}
	// Refuse a newly visible symlink/directory rather than following or removing
	// it. Concurrent cooperating cache publishers still replace regular files.
	if info, err := os.Lstat(path); err == nil {
		if !info.Mode().IsRegular() {
			return fmt.Errorf("cache target became non-regular: %s", path)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return fmt.Errorf("reinspect cache target: %w", err)
	}
	if err := replace(tmp, path); err != nil {
		return fmt.Errorf("publish cache: %w", err)
	}
	return nil
}

// cacheFileMatches uses bounded scratch memory even when a prior cache is large
// or grows concurrently. No process-wide result is retained after this call.
func cacheFileMatches(path string, data []byte) (bool, error) {
	file, err := os.Open(path)
	if err != nil {
		return false, fmt.Errorf("open cache for comparison: %w", err)
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return false, fmt.Errorf("inspect opened cache: %w", err)
	}
	if !info.Mode().IsRegular() {
		return false, fmt.Errorf("opened cache is not a regular file: %s", path)
	}
	if info.Size() != int64(len(data)) {
		return false, nil
	}
	var buffer [32 * 1024]byte
	for offset := 0; offset < len(data); {
		size := min(len(buffer), len(data)-offset)
		n, err := io.ReadFull(file, buffer[:size])
		if errors.Is(err, io.EOF) || errors.Is(err, io.ErrUnexpectedEOF) {
			return false, nil
		}
		if err != nil {
			return false, fmt.Errorf("compare cache bytes: %w", err)
		}
		if !bytes.Equal(buffer[:n], data[offset:offset+n]) {
			return false, nil
		}
		offset += n
	}
	// An external in-place writer is not coordinated by this API. Do not reuse
	// a file whose observed prefix matches but now has extra trailing bytes.
	var extra [1]byte
	n, err := file.Read(extra[:])
	if n > 0 {
		return false, nil
	}
	if err != nil && !errors.Is(err, io.EOF) {
		return false, fmt.Errorf("check cache end: %w", err)
	}
	return err == io.EOF, nil
}
