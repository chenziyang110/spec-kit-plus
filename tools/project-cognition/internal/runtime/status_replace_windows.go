//go:build windows

package runtime

import (
	"fmt"
	"syscall"
	"unsafe"
)

const (
	movefileReplaceExisting = 0x00000001
	movefileWriteThrough    = 0x00000008
)

var (
	modkernel32     = syscall.NewLazyDLL("kernel32.dll")
	procMoveFileExW = modkernel32.NewProc("MoveFileExW")
)

func replaceStatusFile(tmpPath, statusPath string) error {
	existingPath, err := syscall.UTF16PtrFromString(tmpPath)
	if err != nil {
		return fmt.Errorf("encode temp status path: %w", err)
	}
	newPath, err := syscall.UTF16PtrFromString(statusPath)
	if err != nil {
		return fmt.Errorf("encode status path: %w", err)
	}
	ret, _, callErr := procMoveFileExW.Call(
		uintptr(unsafe.Pointer(existingPath)),
		uintptr(unsafe.Pointer(newPath)),
		movefileReplaceExisting|movefileWriteThrough,
	)
	if ret == 0 {
		return fmt.Errorf("replace status: %w", callErr)
	}
	return nil
}
