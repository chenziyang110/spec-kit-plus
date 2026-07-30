//go:build !windows

package scanworkbench

import "os"

func replaceWorkbenchFile(source, target string) error {
	return os.Rename(source, target)
}
