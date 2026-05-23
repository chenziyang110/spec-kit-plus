//go:build windows

package runtime

import (
	"fmt"
	"syscall"
	"unsafe"
)

const (
	replacefileWriteThrough = 0x00000001
	movefileReplaceExisting = 0x00000001
	movefileWriteThrough    = 0x00000008
)

var (
	modkernel32      = syscall.NewLazyDLL("kernel32.dll")
	procReplaceFileW = modkernel32.NewProc("ReplaceFileW")
	procMoveFileExW  = modkernel32.NewProc("MoveFileExW")
)

func replaceStatusFile(tmpPath, statusPath string) error {
	replacedPath, err := syscall.UTF16PtrFromString(statusPath)
	if err != nil {
		return fmt.Errorf("encode status path: %w", err)
	}
	replacementPath, err := syscall.UTF16PtrFromString(tmpPath)
	if err != nil {
		return fmt.Errorf("encode temp status path: %w", err)
	}
	ret, _, callErr := procReplaceFileW.Call(
		uintptr(unsafe.Pointer(replacedPath)),
		uintptr(unsafe.Pointer(replacementPath)),
		0,
		replacefileWriteThrough,
		0,
		0,
	)
	if ret == 0 {
		if callErr == syscall.ERROR_FILE_NOT_FOUND || callErr == syscall.ERROR_PATH_NOT_FOUND {
			return moveStatusFile(tmpPath, statusPath)
		}
		return fmt.Errorf("replace status: %w", callErr)
	}
	return nil
}

func moveStatusFile(tmpPath, statusPath string) error {
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
