package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const executionGuardSchema = "execution-guard-v1"
const executionCompletionSchema = "execution-completion-v1"

func executionAnnounce(args []string, stdout io.Writer) int {
	parsed, err := parseCoordinationCommandArgs(args, 0,
		"--project-root", "--activity-id", "--work-id", "--parent-work-id",
		"--task-ref", "--workflow", "--subject-id", "--item-id", "--source-ref",
		"--summary", "--agent-id", "--adapter-id", "--workspace-root", "--next-action",
		"--lease-seconds", "--planned-write-scope-json", "--resources-json", "--format",
		"--work-packet-file", "--work-packet-sha256",
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := applyExecutionPacketOptions(&parsed); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	for _, required := range []string{"--workflow", "--subject-id", "--summary", "--agent-id", "--adapter-id"} {
		if strings.TrimSpace(parsed.option(required, "")) == "" {
			return writeEnvelope(stdout, executionControlUsageEnvelope("execution announce requires "+required))
		}
	}
	plannedScope, err := parseStringListJSON(parsed.option("--planned-write-scope-json", "[]"), "--planned-write-scope-json")
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	resources, err := parseExecutionResourceSpecsJSON(parsed.option("--resources-json", "[]"), runcontrol.IntentCandidate)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if _, err := workLeaseUntil(parsed); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	projectRoot := parsed.option("--project-root", ".")
	repository, err := runcontrol.ResolveRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("resolve execution repository", err))
	}
	workspaceRoot, err := resolveWorkBoardWorkspace(ctx, repository, parsed.option("--workspace-root", repository.Root))
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("resolve execution workspace", err))
	}
	baseline, err := runcontrol.CaptureWorkspaceBaseline(ctx, workspaceRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("capture execution baseline", err))
	}
	baseline.WorkerPacket = parsed.packet
	if strings.EqualFold(parsed.option("--workflow", ""), string(runcontrol.ExecutionWorkflowImplement)) {
		controlPlane, controlErr := captureExecutionWorkflowControlPlaneBinding(workspaceRoot, parsed)
		if controlErr != nil {
			return writeEnvelope(stdout, executionControlErrorEnvelope("capture workflow control-plane baseline", controlErr))
		}
		baseline.WorkflowControlPlane = controlPlane
	}
	baselineJSON, err := runcontrol.EncodeWorkspaceBaseline(baseline)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("encode execution baseline", err))
	}
	writes := make([]runcontrol.WriteIntentSpec, 0, len(plannedScope))
	for _, path := range plannedScope {
		writes = append(writes, runcontrol.WriteIntentSpec{
			Path: path, Operation: runcontrol.WriteModify,
			Reason: "announced planned write scope", Confidence: runcontrol.IntentCandidate,
		})
	}
	store, err := runcontrol.OpenRepository(ctx, repository)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control store", err))
	}
	// Start the lease at the actual registration boundary. Git baseline capture
	// and first-open schema work can be material in a large or cold repository.
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	registration, operationErr := store.AnnounceExecution(ctx, runcontrol.AnnounceExecutionParams{
		ActivityID:          parsed.option("--activity-id", ""),
		WorkID:              parsed.option("--work-id", ""),
		ParentWorkID:        parsed.option("--parent-work-id", ""),
		TaskRef:             parsed.option("--task-ref", ""),
		Workflow:            runcontrol.ExecutionWorkflow(strings.ToLower(strings.TrimSpace(parsed.option("--workflow", "")))),
		SubjectID:           parsed.option("--subject-id", ""),
		ItemID:              parsed.option("--item-id", ""),
		SourceRef:           parsed.option("--source-ref", ""),
		Summary:             parsed.option("--summary", ""),
		AgentID:             parsed.option("--agent-id", ""),
		AdapterID:           parsed.option("--adapter-id", ""),
		WorkspaceRoot:       workspaceRoot,
		BaseCommit:          baseline.HeadCommit,
		NextAction:          parsed.option("--next-action", ""),
		LeaseUntil:          leaseUntil,
		BaselineJSON:        baselineJSON,
		PlannedWriteIntents: writes,
		Resources:           resources,
	})
	closeErr := store.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("announce execution activity", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control store", closeErr))
	}
	env := NewEnvelope("ok", "execution activity announced before claim")
	env.Data["execution_activity"] = executionRegistrationDTO(registration)
	env.ShowArgv = executionShowArgv(registration.Activity.ActivityID, projectRoot)
	env.NextArgv = []string{"specify-runtime", "execution", "overview", "--current-work-id", registration.Work.WorkID, "--project-root", projectRoot, "--format", "json"}
	return writeEnvelope(stdout, env)
}

func captureExecutionWorkflowControlPlaneBinding(workspaceRoot string, parsed parsedCoordinationCommand) (*runcontrol.WorkflowControlPlaneBinding, error) {
	featureRef := ""
	if parsed.packet != nil {
		packetRef := filepath.ToSlash(parsed.packet.Path)
		featureRef = filepath.ToSlash(filepath.Dir(filepath.Dir(filepath.Dir(filepath.FromSlash(packetRef)))))
	} else {
		var err error
		featureRef, err = manualImplementFeatureRef(parsed)
		if err != nil {
			return nil, err
		}
	}
	workflowRef := filepath.ToSlash(filepath.Join(filepath.FromSlash(featureRef), "workflow.json"))
	binding := &runcontrol.WorkflowControlPlaneBinding{FeatureRef: featureRef, WorkflowRef: workflowRef}
	raw, err := secureProjectReadFile(workspaceRoot, workflowRef)
	if os.IsNotExist(err) {
		return binding, nil
	}
	if err != nil {
		return nil, err
	}
	service := NewWorkflowService(workspaceRoot)
	feature, err := service.resolveFeature(featureRef, "")
	if err != nil {
		return nil, err
	}
	state, err := service.readState(feature)
	if err != nil {
		return nil, err
	}
	if state.Stage != "implement" || state.Status != "active" {
		return nil, fmt.Errorf("workflow control-plane baseline must be active implement, found %s/%s", state.Stage, state.Status)
	}
	binding.StateSHA256 = fileContentSHA256(raw)
	binding.Revision = state.Revision
	receipt, receiptRaw, receiptRef, receiptErr := readWorkflowMutationReceipt(workspaceRoot, featureRef)
	if receiptErr == nil {
		if receipt.WorkflowSHA256 != binding.StateSHA256 || receipt.Revision != binding.Revision || receipt.Stage != state.Stage || receipt.Status != state.Status {
			return nil, fmt.Errorf("workflow mutation receipt does not match the baseline state")
		}
		binding.ReceiptRef = receiptRef
		binding.ReceiptSHA256 = fileContentSHA256(receiptRaw)
	} else if !os.IsNotExist(receiptErr) {
		return nil, receiptErr
	}
	return binding, nil
}

func manualImplementFeatureRef(parsed parsedCoordinationCommand) (string, error) {
	subjectID := strings.TrimSpace(parsed.option("--subject-id", ""))
	if !safeSegment(subjectID) {
		return "", fmt.Errorf("manual implement execution requires a safe feature subject id")
	}
	canonical := filepath.ToSlash(filepath.Join(".specify", "features", subjectID))
	sourceRef := filepath.ToSlash(strings.Trim(strings.TrimSpace(parsed.option("--source-ref", "")), "/"))
	if sourceRef == "" {
		return canonical, nil
	}
	if featureRef, ok := implementFeatureRefFromSourceRef(subjectID, sourceRef); ok {
		return featureRef, nil
	}
	return "", fmt.Errorf("manual implement --source-ref must be the matching feature task-index.json under .specify/features, .specify/specs, or specs")
}

func implementFeatureRefFromSourceRef(subjectID, sourceRef string) (string, bool) {
	subjectID = strings.TrimSpace(subjectID)
	if !safeSegment(subjectID) {
		return "", false
	}
	sourceRef = filepath.ToSlash(strings.Trim(strings.TrimSpace(sourceRef), "/"))
	for _, root := range []string{filepath.ToSlash(filepath.Join(".specify", "features")), filepath.ToSlash(filepath.Join(".specify", "specs")), "specs"} {
		featureRef := filepath.ToSlash(filepath.Join(filepath.FromSlash(root), subjectID))
		expectedSource := featureRef + "/task-index.json"
		if strings.EqualFold(sourceRef, expectedSource) {
			return featureRef, true
		}
	}
	return "", false
}

// applyExecutionPacketOptions keeps compiled task identity and scope bound to
// the exact packet receipt without launching or allocating an execution process.
func applyExecutionPacketOptions(parsed *parsedCoordinationCommand) error {
	packetPath, hasPath := parsed.options["--work-packet-file"]
	packetDigest, hasDigest := parsed.options["--work-packet-sha256"]
	if !hasPath && !hasDigest {
		return nil
	}
	if !hasPath || !hasDigest {
		return errors.New("--work-packet-file and --work-packet-sha256 must be supplied together")
	}
	if parsed.option("--workflow", "") != "implement" {
		return errors.New("compiled worker task packets require --workflow implement")
	}
	for _, field := range []string{"--subject-id", "--item-id", "--task-ref", "--summary", "--planned-write-scope-json"} {
		if _, supplied := parsed.options[field]; supplied {
			return fmt.Errorf("--work-packet-file cannot be combined with %s", field)
		}
	}
	packet, err := workParamsFromTaskPacket(parsed.option("--project-root", "."), packetPath, packetDigest)
	if err != nil {
		return err
	}
	if !safeSegment(packet.FeatureID) || !safeSegment(packet.TaskID) {
		return errors.New("--work-packet-file requires safe feature_id and task_id path segments")
	}
	paths := make([]string, 0, len(packet.WriteIntents))
	for _, intent := range packet.WriteIntents {
		paths = append(paths, intent.Path)
	}
	encoded, err := json.Marshal(paths)
	if err != nil {
		return fmt.Errorf("encode compiled write scope: %w", err)
	}
	parsed.options["--subject-id"] = packet.FeatureID
	parsed.options["--item-id"] = packet.TaskID
	parsed.options["--task-ref"] = packet.TaskRef
	parsed.options["--summary"] = packet.Summary
	parsed.options["--planned-write-scope-json"] = string(encoded)
	parsed.packet = &runcontrol.WorkerPacketBinding{Path: packet.Path, SHA256: packetDigest, WriteScope: paths}
	return nil
}

func executionShow(args []string, stdout io.Writer) int {
	parsed, err := parseCoordinationCommandArgs(args, 1, "--project-root", "--format")
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, parsed.option("--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control view", err))
	}
	registration, operationErr := view.GetExecutionActivity(ctx, strings.TrimSpace(parsed.positionals[0]))
	closeErr := view.Close()
	if operationErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("show execution activity", operationErr))
	}
	if closeErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control view", closeErr))
	}
	env := NewEnvelope("ok", "execution activity loaded")
	env.Data["execution_activity"] = executionRegistrationDTO(registration)
	env.ShowArgv = executionShowArgv(registration.Activity.ActivityID, parsed.option("--project-root", "."))
	return writeEnvelope(stdout, env)
}

func executionCheckpoint(args []string, stdout io.Writer) int {
	parsed, err := parseCoordinationCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence", "--phase",
		"--next-action", "--observed-paths-json", "--lease-seconds", "--reason", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	leaseUntil, err := workLeaseUntil(parsed)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	observedPaths, err := parseStringListJSON(
		parsed.option("--observed-paths-json", "[]"),
		"--observed-paths-json",
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	phase := runcontrol.ExecutionPhase(strings.ToLower(strings.TrimSpace(parsed.option("--phase", ""))))
	nextAction := strings.TrimSpace(parsed.option("--next-action", ""))
	if phase == "" || nextAction == "" {
		return writeEnvelope(stdout, executionControlUsageEnvelope("execution checkpoint requires --phase and --next-action"))
	}
	activityID := strings.TrimSpace(parsed.positionals[0])
	projectRoot := parsed.option("--project-root", ".")
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control store", err))
	}
	checkpointed, operationErr := store.CheckpointExecution(ctx, runcontrol.CheckpointExecutionParams{
		ActivityID:           activityID,
		ExpectedWorkRevision: revision,
		Fence:                fence,
		TargetPhase:          phase,
		NextAction:           nextAction,
		ObservedPaths:        observedPaths,
		LeaseUntil:           leaseUntil,
		Reason:               parsed.option("--reason", ""),
	})
	closeErr := store.Close()
	if operationErr != nil {
		env := executionControlErrorEnvelope("checkpoint execution", operationErr)
		env.ShowArgv = executionShowArgv(activityID, projectRoot)
		return writeEnvelope(stdout, env)
	}
	if closeErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control store", closeErr))
	}
	dto := executionRegistrationDTO(checkpointed.ExecutionRegistration)
	dto["coordination_revision"] = checkpointed.CoordinationRevision
	env := NewEnvelope("ok", "execution lifecycle checkpoint recorded")
	env.Data["execution_activity"] = dto
	env.ShowArgv = executionShowArgv(activityID, projectRoot)
	return writeEnvelope(stdout, env)
}

func executionGuard(args []string, stdout io.Writer) int {
	parsed, err := parseCoordinationCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence",
		"--expected-overview-revision", "--expected-overview-sha256",
		"--write-scope-json", "--resources-json", "--scope-amendments-json", "--reason", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	workRevision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	overviewRevision, err := nonNegativeExecutionOption(parsed, "--expected-overview-revision")
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	overviewSHA256 := strings.TrimSpace(parsed.option("--expected-overview-sha256", ""))
	if len(overviewSHA256) != 64 {
		return writeEnvelope(stdout, executionControlUsageEnvelope("execution guard requires --expected-overview-sha256"))
	}
	writeScope, err := parseStringListJSON(parsed.option("--write-scope-json", "[]"), "--write-scope-json")
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	resources, err := parseExecutionResourceSpecsJSON(parsed.option("--resources-json", "[]"), runcontrol.IntentConfirmed)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	amendments, err := parseExecutionScopeAmendmentSpecsJSON(
		parsed.option("--scope-amendments-json", "[]"), parsed.option("--reason", "execution scope amendment"),
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	activityID := strings.TrimSpace(parsed.positionals[0])
	projectRoot := parsed.option("--project-root", ".")
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control view", err))
	}
	registration, registrationErr := view.GetExecutionActivity(ctx, activityID)
	closeViewErr := view.Close()
	if registrationErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("load execution activity before guard", registrationErr))
	}
	if closeViewErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control view", closeViewErr))
	}
	if err := verifyExecutionPacketFile(registration); err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("verify execution packet before guard", err))
	}
	if len(amendments) > 0 {
		changedPaths, deltaErr := runcontrol.InspectWorkspaceDelta(ctx, registration.Work.WorkspaceRoot, registration.Activity.BaselineJSON)
		if deltaErr != nil {
			return writeEnvelope(stdout, executionControlErrorEnvelope("inspect scope amendment timing", deltaErr))
		}
		for index := range amendments {
			for _, changedPath := range changedPaths {
				overlaps, overlapErr := runcontrol.WritePathsOverlap(amendments[index].Path, changedPath)
				if overlapErr != nil {
					return writeEnvelope(stdout, executionControlUsageEnvelope(overlapErr.Error()))
				}
				if overlaps {
					amendments[index].LateDiscovery = true
					break
				}
			}
		}
	}
	currentWorkID := registration.Work.WorkID
	currentOverview, err := buildExecutionOverview(projectRoot, currentWorkID)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("refresh execution overview before guard", err))
	}
	currentRevision := executionInt64(currentOverview.Data["coordination_revision"])
	currentSHA256 := stringValue(currentOverview.Data["snapshot_sha256"])
	if currentRevision != overviewRevision || currentSHA256 != overviewSHA256 {
		env := executionControlErrorEnvelope("guard execution", fmt.Errorf(
			"%w: current overview is revision %d with digest %s",
			runcontrol.ErrExecutionSnapshotStale, currentRevision, currentSHA256,
		))
		env.ShowArgv = []string{"specify-runtime", "execution", "overview", "--current-work-id", currentWorkID, "--project-root", projectRoot, "--format", "json"}
		return writeEnvelope(stdout, env)
	}
	if currentOverview.Status == "blocked" {
		env := NewEnvelope("blocked", "execution overview has unresolved blockers")
		env.Blockers = append(env.Blockers, currentOverview.Blockers...)
		env.Data["overview_sha256"] = currentSHA256
		env.ShowArgv = currentOverview.ShowArgv
		return writeEnvelope(stdout, env)
	}
	writes := make([]runcontrol.WriteIntentSpec, 0, len(writeScope))
	for _, path := range writeScope {
		writes = append(writes, runcontrol.WriteIntentSpec{
			Path: path, Operation: runcontrol.WriteModify,
			Reason: parsed.option("--reason", "execution guard"), Confidence: runcontrol.IntentConfirmed,
		})
	}
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control store", err))
	}
	guarded, operationErr := store.GuardExecution(ctx, runcontrol.GuardExecutionParams{
		ActivityID:                   activityID,
		ExpectedWorkRevision:         workRevision,
		Fence:                        fence,
		ExpectedCoordinationRevision: overviewRevision,
		OverviewSHA256:               overviewSHA256,
		WriteIntents:                 writes,
		Resources:                    resources,
		ScopeAmendments:              amendments,
		Reason:                       parsed.option("--reason", "execution guarded before write"),
	})
	closeErr := store.Close()
	if operationErr != nil {
		env := executionControlErrorEnvelope("guard execution", operationErr)
		env.ShowArgv = []string{"specify-runtime", "execution", "overview", "--current-work-id", currentWorkID, "--project-root", projectRoot, "--format", "json"}
		return writeEnvelope(stdout, env)
	}
	if closeErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control store", closeErr))
	}
	env := NewEnvelope("ok", "execution guard atomically claimed write and semantic scope")
	env.Data["execution_guard"] = executionGuardDTO(guarded)
	env.ShowArgv = executionShowArgv(activityID, projectRoot)
	return writeEnvelope(stdout, env)
}

func executionComplete(args []string, stdout io.Writer) int {
	parsed, err := parseCoordinationCommandArgs(args, 1,
		"--project-root", "--expected-revision", "--fence",
		"--validation-json", "--reason", "--format",
	)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	revision, fence, err := workRevisionAndFence(parsed)
	if err != nil {
		return writeEnvelope(stdout, executionControlUsageEnvelope(err.Error()))
	}
	if strings.TrimSpace(parsed.option("--reason", "")) == "" || strings.TrimSpace(parsed.option("--validation-json", "")) == "" {
		return writeEnvelope(stdout, executionControlUsageEnvelope("execution complete requires --reason and --validation-json"))
	}
	activityID := strings.TrimSpace(parsed.positionals[0])
	projectRoot := parsed.option("--project-root", ".")
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("open execution control store", err))
	}
	if _, err := store.ReconcileRepositoryWork(ctx, time.Now().UTC()); err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlErrorEnvelope("reconcile execution authority", err))
	}
	registration, err := store.GetExecutionActivity(ctx, activityID)
	if err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlErrorEnvelope("load execution activity", err))
	}
	if err := verifyExecutionPacketFile(registration); err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlErrorEnvelope("verify execution packet before completion", err))
	}
	executionRoot := registration.Work.WorkspaceRoot
	releaseWorkflowLock := func() {}
	if registration.Activity.Workflow == runcontrol.ExecutionWorkflowImplement {
		var lockEnvelope Envelope
		var locked bool
		releaseWorkflowLock, lockEnvelope, locked = acquireExecutionWorkflowControlPlaneLock(executionRoot, registration)
		if !locked {
			_ = store.Close()
			return writeEnvelope(stdout, lockEnvelope)
		}
		defer releaseWorkflowLock()
	}
	if blocker, blocked := executionTaskCompletionBlock(executionRoot, registration); blocked {
		_ = store.Close()
		env := NewEnvelope("blocked", "workflow task is not terminal")
		env.Blockers = append(env.Blockers, blocker)
		env.ShowArgv = executionShowArgv(activityID, projectRoot)
		return writeEnvelope(stdout, env)
	}
	changedPaths, err := runcontrol.InspectWorkspaceDelta(ctx, registration.Work.WorkspaceRoot, registration.Activity.BaselineJSON)
	if err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlErrorEnvelope("inspect actual execution changes", err))
	}
	if env, blocked := executionWorkflowControlPlaneCompletionBlock(executionRoot, registration, changedPaths); blocked {
		_ = store.Close()
		return writeEnvelope(stdout, env)
	}
	controlPlaneFiles, err := captureExecutionWorkflowControlPlaneExpectations(executionRoot, registration)
	if err != nil {
		_ = store.Close()
		return writeEnvelope(stdout, executionControlErrorEnvelope("pin workflow control-plane completion state", err))
	}
	completed, operationErr := store.CompleteExecution(ctx, runcontrol.CompleteExecutionParams{
		ActivityID:           activityID,
		ExpectedWorkRevision: revision,
		Fence:                fence,
		ChangedPaths:         changedPaths,
		ControlPlaneFiles:    controlPlaneFiles,
		ValidationJSON:       parsed.option("--validation-json", ""),
		Reason:               parsed.option("--reason", ""),
	})
	closeErr := store.Close()
	if operationErr != nil {
		env := executionControlErrorEnvelope("complete execution", operationErr)
		bindExecutionScopeAuditRecovery(&env, operationErr, registration, projectRoot)
		bindExecutionControlPlaneDriftRecovery(&env, operationErr, registration, projectRoot)
		env.ShowArgv = executionShowArgv(activityID, projectRoot)
		return writeEnvelope(stdout, env)
	}
	if closeErr != nil {
		return writeEnvelope(stdout, executionControlErrorEnvelope("close execution control store", closeErr))
	}
	env := NewEnvelope("ok", "execution completed with actual-change audit")
	env.Data["execution_completion"] = executionCompletionDTO(completed)
	env.ShowArgv = executionShowArgv(activityID, projectRoot)
	return writeEnvelope(stdout, env)
}

func acquireExecutionWorkflowControlPlaneLock(projectRoot string, registration runcontrol.ExecutionRegistration) (func(), Envelope, bool) {
	binding, _, ok := executionWorkflowControlPlaneBaseline(registration)
	if !ok {
		return func() {}, Envelope{}, true
	}
	service := NewWorkflowService(projectRoot)
	feature, err := service.resolveFeature(binding.FeatureRef, registration.Activity.SubjectID)
	if err != nil {
		return nil, executionControlErrorEnvelope("resolve workflow control-plane lock", err), false
	}
	return service.acquireWorkflowLock(feature)
}

func captureExecutionWorkflowControlPlaneExpectations(projectRoot string, registration runcontrol.ExecutionRegistration) ([]runcontrol.ExecutionFileDigestExpectation, error) {
	if registration.Activity.Workflow != runcontrol.ExecutionWorkflowImplement {
		return nil, nil
	}
	binding, _, ok := executionWorkflowControlPlaneBaseline(registration)
	if !ok {
		return nil, nil
	}
	paths := []string{binding.WorkflowRef, workflowMutationReceiptRef(binding.FeatureRef)}
	expectations := make([]runcontrol.ExecutionFileDigestExpectation, 0, len(paths))
	for _, ref := range paths {
		raw, err := secureProjectReadFile(projectRoot, ref)
		digest := "missing"
		if err == nil {
			digest = fileContentSHA256(raw)
		} else if !os.IsNotExist(err) {
			return nil, err
		}
		expectations = append(expectations, runcontrol.ExecutionFileDigestExpectation{Path: ref, SHA256: digest})
	}
	return expectations, nil
}

func executionWorkflowControlPlaneCompletionBlock(projectRoot string, registration runcontrol.ExecutionRegistration, changedPaths []string) (Envelope, bool) {
	if registration.Activity.Workflow != runcontrol.ExecutionWorkflowImplement {
		return Envelope{}, false
	}
	binding, captured, ok := executionWorkflowControlPlaneBaseline(registration)
	if !ok {
		return Envelope{}, false
	}
	changed := false
	for _, path := range changedPaths {
		if strings.EqualFold(filepath.ToSlash(path), binding.WorkflowRef) {
			changed = true
			break
		}
	}
	workflowRaw, readErr := secureProjectReadFile(projectRoot, binding.WorkflowRef)
	if readErr == nil && captured && fileContentSHA256(workflowRaw) == binding.StateSHA256 {
		return Envelope{}, false
	}
	if readErr != nil && os.IsNotExist(readErr) && captured && binding.StateSHA256 == "" && !changed {
		return Envelope{}, false
	}
	if !captured && !changed {
		return Envelope{}, false
	}
	stateEnvelope := NewWorkflowService(projectRoot).Show(WorkflowShowRequest{FeatureDir: binding.FeatureRef})
	validState := readErr == nil && stateEnvelope.Status == "ok" &&
		strings.EqualFold(anyString(stateEnvelope.Data["feature_id"]), registration.Activity.SubjectID) &&
		strings.EqualFold(anyString(stateEnvelope.Data["stage"]), "implement") &&
		strings.EqualFold(anyString(stateEnvelope.Data["status"]), "active")
	if validState {
		receipt, receiptRaw, receiptRef, receiptErr := readWorkflowMutationReceipt(projectRoot, binding.FeatureRef)
		workflowSHA256 := fileContentSHA256(workflowRaw)
		validReceipt := receiptErr == nil && receiptRef == workflowMutationReceiptRef(binding.FeatureRef) &&
			receipt.WorkflowRef == binding.WorkflowRef && receipt.WorkflowSHA256 == workflowSHA256 &&
			receipt.Revision == intFromAny(stateEnvelope.Data["revision"]) && receipt.Stage == "implement" && receipt.Status == "active"
		if captured {
			validReceipt = validReceipt && receipt.Revision > binding.Revision &&
				fileContentSHA256(receiptRaw) != binding.ReceiptSHA256
		}
		if validReceipt {
			return Envelope{}, false
		}
	}
	code := "workflow_control_plane_invalid"
	stateErrorCode := strings.ToLower(strings.TrimSpace(anyString(stateEnvelope.Data["error_code"])))
	if stateEnvelope.Status == "blocked" && stateErrorCode != "invalid-workflow-runtime" {
		code = "workflow_control_plane_blocked"
	}
	env := NewEnvelope("blocked", "runtime-owned workflow control-plane state is not valid for execution completion")
	env.Data["error_code"] = code
	env.Data["owner"] = "agent"
	env.Data["human_action_required"] = false
	env.Data["workflow_ref"] = binding.WorkflowRef
	env.Data["workflow_status"] = stateEnvelope.Status
	env.Data["resolution_action"] = map[string]any{
		"kind": "repair-or-resolve-workflow-control-plane", "owner": "agent", "human_action_required": false,
		"show_argv": stateEnvelope.ShowArgv, "next_action": "use the specialized specify-runtime workflow action, then retry the same execution completion",
		"unblock_criteria": "workflow show returns stage implement with status active and a matching runtime mutation receipt",
	}
	env.Blockers = []any{map[string]any{
		"code": code, "owner": "agent", "human_action_required": false,
		"workflow_ref": binding.WorkflowRef, "workflow_status": stateEnvelope.Status, "details": stateEnvelope.Blockers,
	}}
	env.ShowArgv = stateEnvelope.ShowArgv
	return env, true
}

func executionWorkflowControlPlaneRefs(registration runcontrol.ExecutionRegistration) (string, string, bool) {
	binding, _, ok := executionWorkflowControlPlaneBaseline(registration)
	if !ok {
		return "", "", false
	}
	return binding.FeatureRef, binding.WorkflowRef, true
}

func executionWorkflowControlPlaneBaseline(registration runcontrol.ExecutionRegistration) (runcontrol.WorkflowControlPlaneBinding, bool, bool) {
	var baseline runcontrol.WorkspaceBaseline
	if json.Unmarshal([]byte(registration.Activity.BaselineJSON), &baseline) != nil {
		return runcontrol.WorkflowControlPlaneBinding{}, false, false
	}
	if baseline.WorkflowControlPlane != nil {
		binding := *baseline.WorkflowControlPlane
		binding.FeatureRef = filepath.ToSlash(strings.Trim(strings.TrimSpace(binding.FeatureRef), "/"))
		binding.WorkflowRef = filepath.ToSlash(strings.Trim(strings.TrimSpace(binding.WorkflowRef), "/"))
		if binding.FeatureRef == "" || binding.WorkflowRef != binding.FeatureRef+"/workflow.json" {
			return runcontrol.WorkflowControlPlaneBinding{}, false, false
		}
		return binding, true, true
	}
	featureRef := ""
	if baseline.WorkerPacket != nil {
		packetRef := filepath.ToSlash(baseline.WorkerPacket.Path)
		featureRef = filepath.ToSlash(filepath.Dir(filepath.Dir(filepath.Dir(filepath.FromSlash(packetRef)))))
	} else if persistedFeatureRef, found := implementFeatureRefFromSourceRef(registration.Activity.SubjectID, registration.Activity.SourceRef); found {
		featureRef = persistedFeatureRef
	} else if safeSegment(registration.Activity.SubjectID) {
		featureRef = filepath.ToSlash(filepath.Join(".specify", "features", registration.Activity.SubjectID))
	}
	if featureRef == "." || featureRef == "" {
		return runcontrol.WorkflowControlPlaneBinding{}, false, false
	}
	return runcontrol.WorkflowControlPlaneBinding{
		FeatureRef:  featureRef,
		WorkflowRef: filepath.ToSlash(filepath.Join(filepath.FromSlash(featureRef), "workflow.json")),
	}, false, true
}

func executionWorkflowControlPlaneChangedPaths(registration runcontrol.ExecutionRegistration, changedPaths []string) []string {
	_, workflowRef, ok := executionWorkflowControlPlaneRefs(registration)
	if !ok {
		return []string{}
	}
	for _, path := range changedPaths {
		if strings.EqualFold(filepath.ToSlash(path), workflowRef) {
			return []string{workflowRef}
		}
	}
	return []string{}
}

func bindExecutionScopeAuditRecovery(env *Envelope, err error, registration runcontrol.ExecutionRegistration, projectRoot string) {
	if env == nil {
		return
	}
	var scopeAudit *runcontrol.ExecutionScopeAuditError
	if !errors.As(err, &scopeAudit) || len(scopeAudit.UnclaimedPaths) == 0 {
		return
	}
	packetBound := false
	var baseline runcontrol.WorkspaceBaseline
	if json.Unmarshal([]byte(registration.Activity.BaselineJSON), &baseline) == nil && baseline.WorkerPacket != nil {
		packetBound = true
	}
	env.Data["error_code"] = "unclaimed_changed_paths"
	env.Data["resolution_action"] = map[string]any{
		"kind":                  "refresh-overview-and-guard-scope",
		"owner":                 "agent",
		"human_action_required": false,
		"activity_id":           registration.Activity.ActivityID,
		"work_id":               registration.Work.WorkID,
		"unclaimed_paths":       stringsToAny(scopeAudit.UnclaimedPaths),
		"packet_bound":          packetBound,
		"overview_argv": []string{
			"specify-runtime", "execution", "overview", "--current-work-id", registration.Work.WorkID,
			"--project-root", projectRoot, "--format", "json",
		},
		"guard_argv_prefix": []string{
			"specify-runtime", "execution", "guard", registration.Activity.ActivityID,
			"--expected-revision", fmt.Sprint(registration.Work.Revision), "--fence", fmt.Sprint(registration.Work.Fence),
			"--project-root", projectRoot,
		},
		"next_action":      "prove whether each path is causally required; then refresh overview and reuse execution guard with the complete scope. Packet-bound recovery also supplies --scope-amendments-json and requires independent scope-drift-review evidence before retrying completion",
		"unblock_criteria": "every actual changed path is covered by the same Activity's confirmed scope and any packet amendment is independently reviewed",
	}
}

func bindExecutionControlPlaneDriftRecovery(env *Envelope, err error, registration runcontrol.ExecutionRegistration, projectRoot string) {
	if env == nil {
		return
	}
	var drift *runcontrol.ExecutionControlPlaneDriftError
	if !errors.As(err, &drift) || len(drift.Paths) == 0 {
		return
	}
	env.Status = "blocked"
	env.Summary = "workflow control-plane state changed during execution completion"
	env.Data["error_code"] = "workflow_control_plane_changed_during_completion"
	env.Data["owner"] = "agent"
	env.Data["human_action_required"] = false
	env.Data["drifted_paths"] = stringsToAny(drift.Paths)
	env.Data["resolution_action"] = map[string]any{
		"kind":                  "refresh-workflow-and-retry-completion",
		"owner":                 "agent",
		"human_action_required": false,
		"next_action":           "inspect the current workflow state, finish or resolve the runtime-owned mutation, then retry the same Activity completion",
		"unblock_criteria":      "workflow state and mutation receipt remain unchanged through the atomic execution completion boundary",
	}
	env.Blockers = []any{map[string]any{
		"code": "workflow_control_plane_changed_during_completion", "owner": "agent",
		"human_action_required": false, "paths": stringsToAny(drift.Paths),
	}}
	env.ShowArgv = executionShowArgv(registration.Activity.ActivityID, projectRoot)
}

func executionTaskCompletionBlock(projectRoot string, registration runcontrol.ExecutionRegistration) (map[string]any, bool) {
	activity := registration.Activity
	switch activity.Workflow {
	case runcontrol.ExecutionWorkflowQuick:
		return executionQuickTaskCompletionBlock(projectRoot, activity)
	case runcontrol.ExecutionWorkflowImplement:
		return executionImplementTaskCompletionBlock(projectRoot, registration)
	default:
		return nil, false
	}
}

func executionQuickTaskCompletionBlock(projectRoot string, activity runcontrol.ExecutionActivity) (map[string]any, bool) {
	service := quickService{projectRoot: projectRoot}
	root, err := service.root()
	if err != nil {
		return executionTaskSourceBlock(activity, "task_source_unavailable", activity.SourceRef, err), true
	}
	tasks, err := service.scan(root)
	if err != nil {
		return executionTaskSourceBlock(activity, "task_source_unavailable", activity.SourceRef, err), true
	}
	task, err := matchQuickTask(tasks, activity.SubjectID)
	if err != nil {
		code := "task_source_unavailable"
		if strings.Contains(err.Error(), "not found") {
			code = "task_source_missing"
		}
		return executionTaskSourceBlock(activity, code, activity.SourceRef, err), true
	}
	if isQuickUnfinished(task) {
		return map[string]any{
			"code": "task_not_terminal", "workflow": activity.Workflow,
			"subject_id": activity.SubjectID, "item_id": activity.ItemID,
			"task_status": strings.ToLower(stringValue(task["status"])),
			"source_ref": filepath.ToSlash(filepath.Join(
				".planning", "quick", stringValue(task["workspace"]), "STATUS.md",
			)),
		}, true
	}
	return nil, false
}

func executionImplementTaskCompletionBlock(projectRoot string, registration runcontrol.ExecutionRegistration) (map[string]any, bool) {
	activity := registration.Activity
	featureRef, _, ok := executionWorkflowControlPlaneRefs(registration)
	if !ok {
		featureRef = filepath.ToSlash(filepath.Join(".specify", "features", activity.SubjectID))
	}
	sourceRef := filepath.ToSlash(filepath.Join(filepath.FromSlash(featureRef), "task-index.json"))
	raw, err := secureProjectReadFile(projectRoot, sourceRef)
	if err != nil {
		code := "task_source_unavailable"
		if errors.Is(err, os.ErrNotExist) {
			code = "task_source_missing"
		}
		return executionTaskSourceBlock(activity, code, sourceRef, err), true
	}
	var index map[string]any
	if err := json.Unmarshal(raw, &index); err != nil || index == nil {
		if err == nil {
			err = fmt.Errorf("task index is not an object")
		}
		return executionTaskSourceBlock(activity, "task_source_unavailable", sourceRef, err), true
	}
	rawTasks, ok := index["tasks"].([]any)
	if !ok {
		return executionTaskSourceBlock(
			activity, "task_source_unavailable", sourceRef, fmt.Errorf("tasks must be an array"),
		), true
	}
	targetID := strings.ToUpper(strings.TrimSpace(activity.ItemID))
	found := false
	for _, rawTask := range rawTasks {
		task, ok := rawTask.(map[string]any)
		if !ok {
			continue
		}
		taskID := strings.ToUpper(strings.TrimSpace(anyString(firstImplementTaskValue(task["id"], task["task_id"]))))
		if targetID != "" && taskID != targetID {
			continue
		}
		found = true
		status := taskControlStatus(task)
		if !implementTaskTerminalStatuses[status] {
			return map[string]any{
				"code": "task_not_terminal", "workflow": activity.Workflow,
				"subject_id": activity.SubjectID, "item_id": taskID,
				"task_status": status, "source_ref": sourceRef + "#/tasks/" + taskID,
			}, true
		}
	}
	if !found {
		return executionTaskSourceBlock(
			activity, "task_source_missing", sourceRef,
			fmt.Errorf("implement task %q is absent from the task index", activity.ItemID),
		), true
	}
	return nil, false
}

func executionTaskSourceBlock(
	activity runcontrol.ExecutionActivity,
	code string,
	sourceRef string,
	err error,
) map[string]any {
	return map[string]any{
		"code": code, "workflow": activity.Workflow,
		"subject_id": activity.SubjectID, "item_id": activity.ItemID,
		"source_ref": strings.TrimSpace(sourceRef), "reason": err.Error(),
	}
}

func parseExecutionResourceSpecsJSON(raw string, defaultConfidence runcontrol.WriteIntentConfidence) ([]runcontrol.ExecutionResourceIntentSpec, error) {
	var rows []map[string]any
	if err := json.Unmarshal([]byte(strings.TrimSpace(raw)), &rows); err != nil {
		return nil, fmt.Errorf("--resources-json must be an array of resource objects: %w", err)
	}
	resources := make([]runcontrol.ExecutionResourceIntentSpec, 0, len(rows))
	for index, row := range rows {
		resourceType := strings.TrimSpace(anyString(firstImplementTaskValue(row["type"], row["resource_type"])))
		resourceKey := strings.TrimSpace(anyString(firstImplementTaskValue(row["key"], row["resource_key"])))
		if resourceType == "" || resourceKey == "" {
			return nil, fmt.Errorf("--resources-json entry %d requires type and key", index)
		}
		confidence := runcontrol.WriteIntentConfidence(strings.TrimSpace(anyString(row["confidence"])))
		if confidence == "" {
			confidence = defaultConfidence
		}
		mode := runcontrol.ResourceClaimMode(strings.TrimSpace(anyString(row["mode"])))
		if mode == "" {
			mode = runcontrol.ResourceClaimExclusive
		}
		resources = append(resources, runcontrol.ExecutionResourceIntentSpec{
			ResourceType: runcontrol.ResourceType(resourceType),
			ResourceKey:  resourceKey,
			Mode:         mode,
			Confidence:   confidence,
			Reason:       strings.TrimSpace(anyString(row["reason"])),
		})
	}
	return resources, nil
}

func parseExecutionScopeAmendmentSpecsJSON(raw, fallbackReason string) ([]runcontrol.ExecutionScopeAmendmentSpec, error) {
	var rows []map[string]any
	if err := json.Unmarshal([]byte(strings.TrimSpace(raw)), &rows); err != nil {
		return nil, fmt.Errorf("--scope-amendments-json must be an array of objects: %w", err)
	}
	result := make([]runcontrol.ExecutionScopeAmendmentSpec, 0, len(rows))
	for index, row := range rows {
		for key := range row {
			if key != "path" && key != "operation" && key != "reason" {
				return nil, fmt.Errorf("--scope-amendments-json entry %d contains unsupported field %q", index, key)
			}
		}
		path := strings.TrimSpace(anyString(row["path"]))
		reason := strings.TrimSpace(anyString(row["reason"]))
		if reason == "" {
			reason = strings.TrimSpace(fallbackReason)
		}
		if path == "" || reason == "" {
			return nil, fmt.Errorf("--scope-amendments-json entry %d requires path and reason", index)
		}
		operation := runcontrol.WriteOperation(strings.TrimSpace(anyString(row["operation"])))
		if operation == "" {
			operation = runcontrol.WriteModify
		}
		result = append(result, runcontrol.ExecutionScopeAmendmentSpec{
			Path: path, Operation: operation, Reason: reason,
		})
	}
	return result, nil
}

func executionRegistrationDTO(registration runcontrol.ExecutionRegistration) map[string]any {
	planned, confirmed := make([]string, 0), make([]string, 0)
	for _, intent := range registration.WriteIntents {
		if intent.Status != runcontrol.WriteIntentActive && intent.Status != runcontrol.WriteIntentRecovery {
			continue
		}
		if intent.Confidence == runcontrol.IntentConfirmed {
			confirmed = append(confirmed, intent.Path)
		} else {
			planned = append(planned, intent.Path)
		}
	}
	dto := map[string]any{
		"activity_id":               registration.Activity.ActivityID,
		"activity_revision":         registration.Activity.Revision,
		"work_id":                   registration.Work.WorkID,
		"work_revision":             registration.Work.Revision,
		"fence":                     registration.Work.Fence,
		"work_status":               registration.Work.Status,
		"workflow":                  registration.Activity.Workflow,
		"subject_id":                registration.Activity.SubjectID,
		"item_id":                   registration.Activity.ItemID,
		"task_ref":                  registration.Activity.TaskRef,
		"source_ref":                registration.Activity.SourceRef,
		"title":                     registration.Activity.Title,
		"phase":                     registration.Activity.Phase,
		"next_action":               registration.Work.NextAction,
		"planned_write_scope":       stringsToAny(uniqueSortedExecutionOverviewStrings(planned)),
		"confirmed_write_scope":     stringsToAny(uniqueSortedExecutionOverviewStrings(confirmed)),
		"semantic_resources":        executionResourceDTOs(registration.Resources),
		"guarded_overview_revision": registration.Activity.GuardedOverviewRevision,
		"guarded_overview_sha256":   registration.Activity.GuardedOverviewSHA256,
		"completion_sha256":         registration.Activity.CompletionSHA256,
	}
	var baseline runcontrol.WorkspaceBaseline
	if json.Unmarshal([]byte(registration.Activity.BaselineJSON), &baseline) == nil && baseline.WorkerPacket != nil {
		dto["worker_packet"] = baseline.WorkerPacket
		dto["scope_amendments"] = baseline.ScopeAmendments
	}
	return dto
}

func executionGuardDTO(guarded runcontrol.GuardedExecution) map[string]any {
	dto := executionRegistrationDTO(guarded.ExecutionRegistration)
	return map[string]any{
		"schema":                    executionGuardSchema,
		"activity_id":               dto["activity_id"],
		"work_id":                   dto["work_id"],
		"work_revision":             dto["work_revision"],
		"fence":                     dto["fence"],
		"task_ref":                  dto["task_ref"],
		"phase":                     dto["phase"],
		"write_scope":               dto["confirmed_write_scope"],
		"semantic_resources":        dto["semantic_resources"],
		"scope_amendments":          dto["scope_amendments"],
		"guarded_overview_revision": dto["guarded_overview_revision"],
		"guarded_overview_sha256":   dto["guarded_overview_sha256"],
		"coordination_revision":     guarded.CoordinationRevision,
	}
}

func executionCompletionDTO(completed runcontrol.CompletedExecution) map[string]any {
	controlPlanePaths := executionWorkflowControlPlaneChangedPaths(completed.ExecutionRegistration, completed.ChangedPaths)
	dto := map[string]any{
		"schema":                       executionCompletionSchema,
		"activity_id":                  completed.Activity.ActivityID,
		"work_id":                      completed.Work.WorkID,
		"work_revision":                completed.Work.Revision,
		"fence":                        completed.Work.Fence,
		"phase":                        completed.Activity.Phase,
		"work_status":                  completed.Work.Status,
		"actual_changed_paths":         stringsToAny(completed.ChangedPaths),
		"completion_sha256":            completed.Activity.CompletionSHA256,
		"coordination_revision":        completed.CoordinationRevision,
		"workflow_control_plane_paths": stringsToAny(controlPlanePaths),
		"workflow_audit_preserved":     false,
	}
	if len(controlPlanePaths) > 0 {
		featureRef, _, ok := executionWorkflowControlPlaneRefs(completed.ExecutionRegistration)
		if ok {
			_, receiptRaw, receiptRef, err := readWorkflowMutationReceipt(completed.Work.WorkspaceRoot, featureRef)
			if err == nil {
				dto["workflow_mutation_receipt_ref"] = receiptRef
				dto["workflow_mutation_receipt_sha256"] = fileContentSHA256(receiptRaw)
				dto["workflow_audit_preserved"] = true
			}
		}
	}
	return dto
}

func executionResourceDTOs(resources []runcontrol.ExecutionResourceIntent) []any {
	result := make([]any, 0, len(resources))
	for _, resource := range resources {
		result = append(result, map[string]any{
			"type": resource.ResourceType, "key": resource.ResourceKey,
			"mode": resource.Mode, "confidence": resource.Confidence,
			"status": resource.Status,
		})
	}
	return result
}

func executionControlErrorEnvelope(action string, err error) Envelope {
	env := NewEnvelope("error", action+" failed")
	env.Blockers = append(env.Blockers, err.Error())
	if bindRunControlStoreAccess(&env, err) {
		return env
	}
	var resourceConflict *runcontrol.ExecutionResourceConflictError
	var taskConflict *runcontrol.ExecutionTaskConflictError
	var scopeAudit *runcontrol.ExecutionScopeAuditError
	var writeConflict *runcontrol.WorkIntentConflictError
	switch {
	case errors.Is(err, runcontrol.ErrExecutionSnapshotStale):
		env.Status = "blocked"
		env.Blockers = []any{map[string]any{"code": "overview_stale", "reason": err.Error()}}
	case errors.As(err, &resourceConflict):
		env.Status = "blocked"
		env.Blockers = []any{}
		for _, conflict := range resourceConflict.Conflicts {
			env.Blockers = append(env.Blockers, map[string]any{
				"code":              "semantic_resource_conflict",
				"resource_type":     conflict.ResourceType,
				"resource_key":      conflict.ResourceKey,
				"owner_activity_id": conflict.OwnerActivityID,
				"owner_work_id":     conflict.OwnerWorkID,
			})
		}
	case errors.As(err, &taskConflict):
		env.Status = "blocked"
		env.Blockers = []any{map[string]any{
			"code": "duplicate_task_owner", "task_ref": taskConflict.TaskRef,
			"owner_activity_id": taskConflict.OwnerActivityID,
			"owner_work_id":     taskConflict.OwnerWorkID,
		}}
	case errors.As(err, &scopeAudit):
		env.Status = "blocked"
		env.Blockers = []any{map[string]any{
			"code": "unclaimed_changed_paths", "paths": stringsToAny(scopeAudit.UnclaimedPaths),
		}}
	case errors.As(err, &writeConflict):
		env.Status = "blocked"
		env.Blockers = []any{map[string]any{"code": "write_scope_conflict", "reason": err.Error()}}
	case errors.Is(err, runcontrol.ErrExecutionCompletionGate),
		errors.Is(err, runcontrol.ErrExecutionGuardRequired),
		errors.Is(err, runcontrol.ErrRevisionConflict),
		errors.Is(err, runcontrol.ErrStaleFence),
		errors.Is(err, runcontrol.ErrInvalidTransition):
		env.Status = "blocked"
	}
	return env
}

func executionControlUsageEnvelope(message string) Envelope {
	env := NewEnvelope("usage-error", message)
	env.ShowArgv = []string{"specify-runtime", "execution", "help"}
	return env
}

func executionShowArgv(activityID, projectRoot string) []string {
	return []string{"specify-runtime", "execution", "show", activityID, "--project-root", projectRoot, "--format", "json"}
}

func nonNegativeExecutionOption(parsed parsedCoordinationCommand, name string) (int64, error) {
	raw := strings.TrimSpace(parsed.option(name, ""))
	value, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || value < 0 {
		return 0, fmt.Errorf("%s must be a non-negative integer", name)
	}
	return value, nil
}

func executionInt64(value any) int64 {
	switch typed := value.(type) {
	case int64:
		return typed
	case int:
		return int64(typed)
	case float64:
		return int64(typed)
	case json.Number:
		parsed, _ := typed.Int64()
		return parsed
	default:
		parsed, _ := strconv.ParseInt(strings.TrimSpace(fmt.Sprint(value)), 10, 64)
		return parsed
	}
}
