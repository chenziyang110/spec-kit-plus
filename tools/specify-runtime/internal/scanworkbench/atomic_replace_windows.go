//go:build windows

package scanworkbench

import (
	"fmt"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

const (
	workbenchMoveFileReplaceExisting = 0x00000001
	workbenchMoveFileWriteThrough    = 0x00000008
)

var (
	workbenchKernel32       = syscall.NewLazyDLL("kernel32.dll")
	workbenchMoveFileExProc = workbenchKernel32.NewProc("MoveFileExW")
)

func replaceWorkbenchFile(source, target string) error {
	sourcePtr, err := syscall.UTF16PtrFromString(source)
	if err != nil {
		return fmt.Errorf("encode source path: %w", err)
	}
	targetPtr, err := syscall.UTF16PtrFromString(target)
	if err != nil {
		return fmt.Errorf("encode target path: %w", err)
	}
	var lastErr error
	// Multi-worker scan-accept can race on Windows file locks; retry briefly
	// before surfacing Access is denied to the leader.
	for attempt := 0; attempt < 8; attempt++ {
		result, _, callErr := workbenchMoveFileExProc.Call(
			uintptr(unsafe.Pointer(sourcePtr)),
			uintptr(unsafe.Pointer(targetPtr)),
			workbenchMoveFileReplaceExisting|workbenchMoveFileWriteThrough,
		)
		if result != 0 {
			return nil
		}
		lastErr = callErr
		message := strings.ToLower(callErr.Error())
		if !strings.Contains(message, "access is denied") &&
			!strings.Contains(message, "being used by another process") &&
			!strings.Contains(message, "sharing violation") {
			break
		}
		time.Sleep(time.Duration(25*(attempt+1)) * time.Millisecond)
	}
	return fmt.Errorf("replace workbench file: %w", lastErr)
}
