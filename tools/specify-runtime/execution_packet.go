package main

import (
	"encoding/json"
	"fmt"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

func verifyExecutionPacketFile(registration runcontrol.ExecutionRegistration) error {
	var baseline struct {
		WorkerPacket *runcontrol.WorkerPacketBinding `json:"worker_packet"`
	}
	if err := json.Unmarshal([]byte(registration.Activity.BaselineJSON), &baseline); err != nil {
		return fmt.Errorf("%w: malformed execution baseline", runcontrol.ErrExecutionGuardRequired)
	}
	if baseline.WorkerPacket == nil {
		return nil
	}
	if _, err := workParamsFromTaskPacket(registration.Work.WorkspaceRoot, baseline.WorkerPacket.Path, baseline.WorkerPacket.SHA256); err != nil {
		return fmt.Errorf("%w: compiled packet changed since announcement: %v", runcontrol.ErrExecutionGuardRequired, err)
	}
	return nil
}
