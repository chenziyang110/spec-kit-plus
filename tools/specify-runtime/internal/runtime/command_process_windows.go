//go:build windows

package runtime

import (
	"errors"
	"fmt"
	"os/exec"
	"unsafe"

	"golang.org/x/sys/windows"
)

const commandProcessTreeTerminationExitCode = 137

type windowsCommandProcessTree struct {
	jobHandle     windows.Handle
	processHandle windows.Handle
}

func newCommandProcessTreePlatform() commandProcessTreePlatform {
	return &windowsCommandProcessTree{}
}

func (tree *windowsCommandProcessTree) configure(*exec.Cmd) error {
	return nil
}

func (tree *windowsCommandProcessTree) afterStart(command *exec.Cmd) error {
	if command.Process == nil {
		return errors.New("started command is missing process metadata")
	}
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
		uint32(command.Process.Pid),
	)
	if err != nil {
		_ = windows.CloseHandle(jobHandle)
		return fmt.Errorf("open child process %d: %w", command.Process.Pid, err)
	}
	if err := windows.AssignProcessToJobObject(jobHandle, processHandle); err != nil {
		_ = windows.TerminateProcess(processHandle, commandProcessTreeTerminationExitCode)
		_ = windows.CloseHandle(processHandle)
		_ = windows.CloseHandle(jobHandle)
		return fmt.Errorf("assign child process %d to job object: %w", command.Process.Pid, err)
	}
	tree.jobHandle = jobHandle
	tree.processHandle = processHandle
	return nil
}

func (tree *windowsCommandProcessTree) terminate() error {
	if tree.jobHandle != 0 {
		return windows.TerminateJobObject(tree.jobHandle, commandProcessTreeTerminationExitCode)
	}
	if tree.processHandle != 0 {
		return windows.TerminateProcess(tree.processHandle, commandProcessTreeTerminationExitCode)
	}
	return nil
}

func (tree *windowsCommandProcessTree) close() error {
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
	return closeErr
}
