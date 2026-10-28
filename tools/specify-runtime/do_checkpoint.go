package main

import (
	"errors"
	"os"
	"runtime"
	"syscall"
	"time"
)

const doCheckpointReadAttempts = 11
const doCheckpointReadDelay = 10 * time.Millisecond

// A Windows atomic replacement can briefly deny a reader's share mode. Retry
// only those two OS errors, with at most 100 ms of retry waits. Parsing and
// integrity validation remain outside this read boundary and never retry.
func doReadCheckpoint(root, relative string) ([]byte, error) {
	return doReadCheckpointWithRetry(root, relative, runtime.GOOS, os.ReadFile, time.Sleep)
}

func doReadCheckpointWithRetry(root, relative, platform string, readFile func(string) ([]byte, error), pause func(time.Duration)) ([]byte, error) {
	for attempt := 0; ; attempt++ {
		// Resolve the secure path again after every wait. Never keep an old
		// resolved path or return bytes from a different checkpoint.
		target, err := secureProjectPath(root, relative)
		var raw []byte
		if err == nil {
			raw, err = readFile(target)
		}
		if err == nil || platform != "windows" || attempt+1 >= doCheckpointReadAttempts ||
			(!errors.Is(err, syscall.Errno(32)) && !errors.Is(err, syscall.Errno(33))) {
			return raw, err
		}
		pause(doCheckpointReadDelay)
	}
}
