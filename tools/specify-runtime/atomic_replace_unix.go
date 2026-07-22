//go:build !windows

package main

import (
	"os"
	"path/filepath"
)

func replaceFile(source, target string) error {
	if err := os.Rename(source, target); err != nil {
		return err
	}
	// The rename is the commit point. Sync the directory for durability when the
	// filesystem supports it, but do not report an ordinary pre-commit error after
	// the target has already changed.
	directory, openErr := os.Open(filepath.Dir(target))
	if openErr == nil {
		_ = directory.Sync()
		_ = directory.Close()
	}
	return nil
}
