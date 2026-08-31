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
	store, err := runcontrol.Open(ctx, repository.DatabasePath)
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
		"--write-scope-json", "--resources-json", "--reason", "--format",
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
	if blocker, blocked := executionTaskCompletionBlock(projectRoot, registration.Activity); blocked {
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
	completed, operationErr := store.CompleteExecution(ctx, runcontrol.CompleteExecutionParams{
		ActivityID:           activityID,
		ExpectedWorkRevision: revision,
		Fence:                fence,
		ChangedPaths:         changedPaths,
		ValidationJSON:       parsed.option("--validation-json", ""),
		Reason:               parsed.option("--reason", ""),
	})
	closeErr := store.Close()
	if operationErr != nil {
		env := executionControlErrorEnvelope("complete execution", operationErr)
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

func executionTaskCompletionBlock(projectRoot string, activity runcontrol.ExecutionActivity) (map[string]any, bool) {
	switch activity.Workflow {
	case runcontrol.ExecutionWorkflowQuick:
		return executionQuickTaskCompletionBlock(projectRoot, activity)
	case runcontrol.ExecutionWorkflowImplement:
		return executionImplementTaskCompletionBlock(projectRoot, activity)
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

func executionImplementTaskCompletionBlock(projectRoot string, activity runcontrol.ExecutionActivity) (map[string]any, bool) {
	sourceRef := filepath.ToSlash(filepath.Join(
		".specify", "features", activity.SubjectID, "task-index.json",
	))
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
		"guarded_overview_revision": dto["guarded_overview_revision"],
		"guarded_overview_sha256":   dto["guarded_overview_sha256"],
		"coordination_revision":     guarded.CoordinationRevision,
	}
}

func executionCompletionDTO(completed runcontrol.CompletedExecution) map[string]any {
	return map[string]any{
		"schema":                executionCompletionSchema,
		"activity_id":           completed.Activity.ActivityID,
		"work_id":               completed.Work.WorkID,
		"work_revision":         completed.Work.Revision,
		"fence":                 completed.Work.Fence,
		"phase":                 completed.Activity.Phase,
		"work_status":           completed.Work.Status,
		"actual_changed_paths":  stringsToAny(completed.ChangedPaths),
		"completion_sha256":     completed.Activity.CompletionSHA256,
		"coordination_revision": completed.CoordinationRevision,
	}
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
