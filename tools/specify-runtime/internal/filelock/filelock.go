package filelock

import (
	"fmt"
	"os"
	"sync"
	"time"
)

const (
	retryInterval = 25 * time.Millisecond
	waitTimeout   = 30 * time.Second
)

// Acquire obtains an exclusive operating-system lock for path. The caller must
// create and validate the parent directory before acquiring the lock.
func Acquire(path string) (func(), error) {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open file lock: %w", err)
	}

	deadline := time.Now().Add(waitTimeout)
	for {
		acquired, lockErr := tryLock(file)
		if lockErr != nil {
			_ = file.Close()
			return nil, fmt.Errorf("acquire file lock: %w", lockErr)
		}
		if acquired {
			var releaseOnce sync.Once
			return func() {
				releaseOnce.Do(func() {
					_ = unlock(file)
					_ = file.Close()
				})
			}, nil
		}
		if time.Now().After(deadline) {
			_ = file.Close()
			return nil, fmt.Errorf("timed out waiting for file lock")
		}
		time.Sleep(retryInterval)
	}
}
