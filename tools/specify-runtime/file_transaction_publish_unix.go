//go:build !windows

package main

import "os"

func publishPreparedTransactionDirectory(source, target string, _ fileTransactionJournal) error {
	return replaceFile(source, target)
}

func cleanupPreparedDirectoryPublicationFailure(source string) {
	_ = os.RemoveAll(source)
}
