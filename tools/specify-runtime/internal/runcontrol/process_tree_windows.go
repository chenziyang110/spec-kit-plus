//go:build windows

package runcontrol

import (
	"fmt"
	"os/exec"
	"unsafe"

	"golang.org/x/sys/windows"
)

const processTreeTerminationExitCode = 137

type windowsProcessTree struct {
	jobHandle     windows.Handle
	processHandle windows.Handle
	processID     uint32
}

func newProcessTreePlatform() processTreePlatform {
	return &windowsProcessTree{}
}

func (tree *windowsProcessTree) configure(command *exec.Cmd) error {
	return nil
}

func (tree *windowsProcessTree) afterStart(command *exec.Cmd) error {
	if command.Process == nil {
		return fmt.Errorf("%w: started command is missing process metadata", ErrInvalidArgument)
	}
	processID := uint32(command.Process.Pid)
	jobHandle, err := windows.CreateJobObject(nil, nil)
	if err != nil {
		return fmt.Errorf("create job object: %w", err)
	}

	var limits windows.JOBOBJECT_EXTENDED_LIMIT_INFORMATION
	limits.BasicLimitInformation.LimitFlags |= windows.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
	if _, err := windows.SetInformationJobObject(
		jobHandle,
		windows.JobObjectExtendedLimitInformation,
		uintptr(unsafe.Pointer(&limits)),
		uint32(unsafe.Sizeof(limits)),
	); err != nil {
		_ = windows.CloseHandle(jobHandle)
		return fmt.Errorf("configure job object: %w", err)
	}

	processHandle, err := windows.OpenProcess(
		windows.PROCESS_SET_QUOTA|windows.PROCESS_TERMINATE|windows.PROCESS_QUERY_LIMITED_INFORMATION,
		false,
		processID,
	)
	if err != nil {
		_ = windows.CloseHandle(jobHandle)
		return fmt.Errorf("open child process %d: %w", processID, err)
	}
	if err := windows.AssignProcessToJobObject(jobHandle, processHandle); err != nil {
		_ = windows.TerminateProcess(processHandle, processTreeTerminationExitCode)
		_ = windows.CloseHandle(processHandle)
		_ = windows.CloseHandle(jobHandle)
		return fmt.Errorf("assign child process %d to job object: %w", processID, err)
	}

	tree.jobHandle = jobHandle
	tree.processHandle = processHandle
	tree.processID = processID
	return nil
}

func (tree *windowsProcessTree) terminate() error {
	if tree.jobHandle != 0 {
		if err := windows.TerminateJobObject(tree.jobHandle, processTreeTerminationExitCode); err != nil {
			return err
		}
		return nil
	}
	if tree.processHandle != 0 {
		if err := windows.TerminateProcess(tree.processHandle, processTreeTerminationExitCode); err != nil {
			return err
		}
	}
	return nil
}

func (tree *windowsProcessTree) close() error {
	var closeErr error
	if tree.processHandle != 0 {
		if err := windows.CloseHandle(tree.processHandle); err != nil && closeErr == nil {
			closeErr = err
		}
		tree.processHandle = 0
	}
	if tree.jobHandle != 0 {
		if err := windows.CloseHandle(tree.jobHandle); err != nil && closeErr == nil {
			closeErr = err
		}
		tree.jobHandle = 0
	}
	tree.processID = 0
	return closeErr
}
