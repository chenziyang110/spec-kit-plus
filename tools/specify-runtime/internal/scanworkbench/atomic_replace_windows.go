//go:build windows

package scanworkbench

import (
	"fmt"
	"syscall"
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
	result, _, callErr := workbenchMoveFileExProc.Call(
		uintptr(unsafe.Pointer(sourcePtr)),
		uintptr(unsafe.Pointer(targetPtr)),
		workbenchMoveFileReplaceExisting|workbenchMoveFileWriteThrough,
	)
	if result == 0 {
		return fmt.Errorf("replace workbench file: %w", callErr)
	}
	return nil
}
