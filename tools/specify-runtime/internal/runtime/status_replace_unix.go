//go:build !windows

package runtime

import (
	"fmt"
	"os"
)

func replaceStatusFile(tmpPath, statusPath string) error {
	if err := os.Rename(tmpPath, statusPath); err != nil {
		return fmt.Errorf("replace status: %w", err)
	}
	return nil
}
