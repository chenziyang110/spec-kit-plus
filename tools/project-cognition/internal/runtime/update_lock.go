package runtime

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const (
	updateLockRetryInterval = 25 * time.Millisecond
	updateLockWait          = 30 * time.Second
)

// AcquireUpdateLock serializes DB-plus-status publication across processes.
// The operating-system lock is released automatically when a process exits,
// so a crashed updater cannot leave a stale ownership directory behind.
func AcquireUpdateLock(paths Paths) (func(), error) {
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return nil, fmt.Errorf("create project cognition runtime directory: %w", err)
	}
	lockPath := filepath.Join(paths.RuntimeDir, ".update.lock")
	file, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open project cognition update lock: %w", err)
	}

	deadline := time.Now().Add(updateLockWait)
	for {
		acquired, lockErr := tryUpdateFileLock(file)
		if lockErr != nil {
			_ = file.Close()
			return nil, fmt.Errorf("acquire project cognition update lock: %w", lockErr)
		}
		if acquired {
			var releaseOnce sync.Once
			return func() {
				releaseOnce.Do(func() {
					_ = unlockUpdateFile(file)
					_ = file.Close()
				})
			}, nil
		}
		if time.Now().After(deadline) {
			_ = file.Close()
			return nil, fmt.Errorf("timed out waiting for another project cognition update")
		}
		time.Sleep(updateLockRetryInterval)
	}
}
