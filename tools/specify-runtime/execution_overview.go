package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const executionOverviewSnapshotKind = "execution-overview-v1"

type executionOverviewTask struct {
	Workflow     string
	SubjectID    string
	ItemID       string
	Title        string
	Status       string
	NextAction   string
	SourceRef    string
	PlannedScope []string
}

type executionOverviewActivityAccumulator struct {
	Workflow              string
	SubjectID             string
	ItemID                string
	Title                 string
	TaskStatus            string
	NextAction            string
	SourceRefs            map[string]bool
	WorkIDs               map[string]bool
	TaskPresent           bool
	Current               bool
	PlannedScope          map[string]bool
	ConfirmedScope        map[string]bool
	RegisteredActivityIDs map[string]bool
	LifecyclePhase        string
	ActivityRevision      int64
	SemanticResources     []runcontrol.ExecutionResourceIntent
}

func runExecution(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, executionOverviewUsageEnvelope("missing execution subcommand"))
	}
	if args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		env := NewEnvelope("ok", "execution command help")
		env.Data["commands"] = []string{"announce", "overview", "checkpoint", "guard", "show", "complete"}
		env.Data["announce_usage"] = "specify-runtime execution announce --workflow <fast|debug|implement|quick> (--subject-id <id> --summary <text> | --work-packet-file <worker-packet.json> --work-packet-sha256 <sha256>) --agent-id <id> --adapter-id <id> [--planned-write-scope-json <array>] [--resources-json <array>] [--project-root <path>] --format json"
		env.Data["overview_usage"] = "specify-runtime execution overview [--current-work-id <work-id>] [--project-root <path>] --format json"
		env.Data["guard_usage"] = "specify-runtime execution guard <activity-id> --expected-revision <revision> --fence <fence> --expected-overview-revision <revision> --expected-overview-sha256 <sha256> --write-scope-json <array> --resources-json <array> --reason <text> [--project-root <path>] --format json"
		env.Data["checkpoint_usage"] = "specify-runtime execution checkpoint <activity-id> --expected-revision <revision> --fence <fence> --phase <selected|executing|validating|blocked> --next-action <text> --lease-seconds <seconds> [--observed-paths-json <array>] [--reason <text>] [--project-root <path>] --format json"
		env.Data["complete_usage"] = "specify-runtime execution complete <activity-id> --expected-revision <revision> --fence <fence> --validation-json <array> --reason <text> [--project-root <path>] --format json"
		return writeEnvelope(stdout, env)
	}
	switch args[0] {
	case "announce":
		return executionAnnounce(args[1:], stdout)
	case "guard":
		return executionGuard(args[1:], stdout)
	case "checkpoint":
		return executionCheckpoint(args[1:], stdout)
	case "show":
		return executionShow(args[1:], stdout)
	case "complete":
		return executionComplete(args[1:], stdout)
	case "overview":
		// Continue below.
	default:
		return writeEnvelope(stdout, executionOverviewUsageEnvelope(fmt.Sprintf("unknown execution subcommand %q", args[0])))
	}
	parsed, err := parseCoordinationCommandArgs(args[1:], 0, "--project-root", "--current-work-id", "--since-revision", "--format")
	if err != nil {
		return writeEnvelope(stdout, executionOverviewUsageEnvelope(err.Error()))
	}
	if err := parsed.validateJSONFormat(); err != nil {
		return writeEnvelope(stdout, executionOverviewUsageEnvelope(err.Error()))
	}
	sinceRevision := int64(-1)
	if _, present := parsed.options["--since-revision"]; present {
		sinceRevision, err = nonNegativeExecutionOption(parsed, "--since-revision")
		if err != nil {
			return writeEnvelope(stdout, executionOverviewUsageEnvelope(err.Error()))
		}
	}
	env, err := buildExecutionOverviewWithChanges(
		parsed.option("--project-root", "."),
		parsed.option("--current-work-id", os.Getenv("SPECIFY_WORK_ID")),
		sinceRevision,
	)
	if err != nil {
		return writeEnvelope(stdout, executionOverviewErrorEnvelope(err))
	}
	return writeEnvelope(stdout, env)
}

func buildExecutionOverview(projectRoot, currentWorkID string) (Envelope, error) {
	return buildExecutionOverviewWithChanges(projectRoot, currentWorkID, -1)
}

func buildExecutionOverviewWithChanges(projectRoot, currentWorkID string, sinceRevision int64) (Envelope, error) {
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, projectRoot)
	if err != nil {
		return Envelope{}, fmt.Errorf("open shared execution state: %w", err)
	}
	closed := false
	defer func() {
		if !closed {
			_ = store.Close()
		}
	}()

	now := time.Now().UTC()
	reconciliation, err := store.ReconcileRepositoryWork(ctx, now)
	if err != nil {
		return Envelope{}, fmt.Errorf("reconcile shared Work Board: %w", err)
	}
	workItems, err := store.ListWork(ctx, runcontrol.ListWorkParams{Statuses: []runcontrol.WorkStatus{
		runcontrol.WorkActive,
		runcontrol.WorkBlocked,
		runcontrol.WorkInterrupted,
	}})
	if err != nil {
		return Envelope{}, fmt.Errorf("list shared Work Board: %w", err)
	}
	registeredActivities, err := store.ListExecutionActivities(ctx, runcontrol.ListExecutionActivitiesParams{Phases: []runcontrol.ExecutionPhase{
		runcontrol.ExecutionPhaseAnnounced,
		runcontrol.ExecutionPhaseSelected,
		runcontrol.ExecutionPhaseClaimed,
		runcontrol.ExecutionPhaseExecuting,
		runcontrol.ExecutionPhaseValidating,
		runcontrol.ExecutionPhaseBlocked,
		runcontrol.ExecutionPhaseInterrupted,
	}})
	if err != nil {
		return Envelope{}, fmt.Errorf("list registered execution activities: %w", err)
	}
	registrations := make([]runcontrol.ExecutionRegistration, 0, len(registeredActivities))
	registeredByWork := make(map[string]runcontrol.ExecutionRegistration, len(registeredActivities))
	for _, activity := range registeredActivities {
		registration, getErr := store.GetExecutionActivity(ctx, activity.ActivityID)
		if getErr != nil {
			return Envelope{}, fmt.Errorf("load execution activity %q: %w", activity.ActivityID, getErr)
		}
		registrations = append(registrations, registration)
		registeredByWork[registration.Work.WorkID] = registration
	}

	liveWork := make([]runcontrol.WorkItem, 0, len(workItems))
	intentsByWork := make(map[string][]runcontrol.WriteIntent, len(workItems))
	for _, work := range workItems {
		live := (work.Status == runcontrol.WorkActive || work.Status == runcontrol.WorkBlocked) && work.LeaseUntilMS > now.UnixMilli()
		recoveryHeld := work.Status == runcontrol.WorkInterrupted && work.RecoveryHold
		_, registered := registeredByWork[work.WorkID]
		if !live && !recoveryHeld && !(registered && work.Status == runcontrol.WorkInterrupted) {
			continue
		}
		_, intents, getErr := store.GetWork(ctx, work.WorkID)
		if getErr != nil {
			return Envelope{}, fmt.Errorf("load Work %q: %w", work.WorkID, getErr)
		}
		liveWork = append(liveWork, work)
		intentsByWork[work.WorkID] = intents
	}
	coordinationRevision, err := store.CoordinationRevision(ctx)
	if err != nil {
		return Envelope{}, fmt.Errorf("read execution coordination revision: %w", err)
	}
	changes := []runcontrol.Event{}
	if sinceRevision >= 0 {
		changes, err = store.ListCoordinationChanges(ctx, sinceRevision, 200)
		if err != nil {
			return Envelope{}, fmt.Errorf("list execution coordination changes: %w", err)
		}
	}
	if err := store.Close(); err != nil {
		return Envelope{}, fmt.Errorf("close shared execution state: %w", err)
	}
	closed = true

	signals := make([]map[string]any, 0)
	tasks, taskSignals := scanExecutionOverviewTasks(projectRoot)
	signals = append(signals, taskSignals...)
	activities := make(map[string]*executionOverviewActivityAccumulator)
	quickAliases := map[string]string{}
	implementTaskKeys := map[string][]string{}
	for _, task := range tasks {
		key := executionOverviewActivityKey(task.Workflow, task.SubjectID, task.ItemID)
		activity := ensureExecutionOverviewActivity(activities, key, task.Workflow, task.SubjectID, task.ItemID)
		activity.TaskPresent = true
		activity.Title = task.Title
		activity.TaskStatus = task.Status
		activity.NextAction = task.NextAction
		activity.SourceRefs[task.SourceRef] = true
		for _, path := range task.PlannedScope {
			activity.PlannedScope[path] = true
		}
		if task.Workflow == "quick" {
			quickAliases[task.SubjectID] = task.SubjectID
			if workspace := executionOverviewQuickWorkspace(task.SourceRef); workspace != "" {
				quickAliases[workspace] = task.SubjectID
			}
		}
		if task.Workflow == "implement" {
			implementTaskKeys[task.SubjectID] = append(implementTaskKeys[task.SubjectID], key)
		}
	}
	for featureID := range implementTaskKeys {
		sort.Strings(implementTaskKeys[featureID])
	}
	registeredActivityKeyByWork := make(map[string]string, len(registrations))
	for _, registration := range registrations {
		registered := registration.Activity
		key := executionOverviewActivityKey(string(registered.Workflow), registered.SubjectID, registered.ItemID)
		activity := ensureExecutionOverviewActivity(
			activities,
			key,
			string(registered.Workflow),
			registered.SubjectID,
			registered.ItemID,
		)
		activity.RegisteredActivityIDs[registered.ActivityID] = true
		activity.LifecyclePhase = string(registered.Phase)
		activity.ActivityRevision = registered.Revision
		activity.SemanticResources = append(activity.SemanticResources, registration.Resources...)
		activity.WorkIDs[registration.Work.WorkID] = true
		if activity.Title == "" {
			activity.Title = registered.Title
		}
		if activity.NextAction == "" {
			activity.NextAction = registration.Work.NextAction
		}
		if registration.Work.WorkID == strings.TrimSpace(currentWorkID) {
			activity.Current = true
		}
		for _, intent := range registration.WriteIntents {
			if intent.Status != runcontrol.WriteIntentActive && intent.Status != runcontrol.WriteIntentRecovery {
				continue
			}
			if intent.Confidence == runcontrol.IntentConfirmed {
				activity.ConfirmedScope[intent.Path] = true
			} else {
				activity.PlannedScope[intent.Path] = true
			}
		}
		registeredActivityKeyByWork[registration.Work.WorkID] = key
	}

	workProjections := make([]map[string]any, 0, len(liveWork))
	taskRefOwners := make(map[string][]runcontrol.WorkItem)
	for _, work := range liveWork {
		workflow, subjectID, itemID := parseExecutionOverviewTaskRef(work.TaskRef, quickAliases)
		keys := []string{}
		if registeredKey := registeredActivityKeyByWork[work.WorkID]; registeredKey != "" {
			keys = []string{registeredKey}
			registered := registeredByWork[work.WorkID].Activity
			workflow, subjectID, itemID = string(registered.Workflow), registered.SubjectID, registered.ItemID
		} else {
			keys = executionOverviewKeysForWork(activities, implementTaskKeys, workflow, subjectID, itemID, work.WorkID)
		}
		for _, key := range keys {
			activity := ensureExecutionOverviewActivity(activities, key, workflow, subjectID, itemID)
			activity.WorkIDs[work.WorkID] = true
			if activity.Title == "" {
				activity.Title = work.Summary
			}
			if activity.NextAction == "" {
				activity.NextAction = work.NextAction
			}
			if work.WorkID == strings.TrimSpace(currentWorkID) {
				activity.Current = true
			}
			for _, intent := range intentsByWork[work.WorkID] {
				if intent.Status != runcontrol.WriteIntentActive && intent.Status != runcontrol.WriteIntentRecovery {
					continue
				}
				if intent.Confidence == runcontrol.IntentConfirmed {
					activity.ConfirmedScope[intent.Path] = true
				} else {
					activity.PlannedScope[intent.Path] = true
				}
			}
		}
		if normalizedRef := strings.ToLower(strings.TrimSpace(work.TaskRef)); normalizedRef != "" {
			taskRefOwners[normalizedRef] = append(taskRefOwners[normalizedRef], work)
		}
		workProjections = append(workProjections, executionOverviewWorkProjection(work, intentsByWork[work.WorkID], workflow))
	}

	for taskRef, owners := range taskRefOwners {
		if len(owners) < 2 {
			continue
		}
		ownerIDs := make([]string, 0, len(owners))
		for _, owner := range owners {
			ownerIDs = append(ownerIDs, owner.WorkID)
		}
		sort.Strings(ownerIDs)
		signals = append(signals, executionOverviewSignal("block", "duplicate_task_owner", "multiple live Work identities own the same exact task", map[string]any{
			"task_ref": taskRef,
			"work_ids": stringsToAny(ownerIDs),
		}))
	}

	currentWorkID = strings.TrimSpace(currentWorkID)
	if currentWorkID != "" {
		currentValid := false
		for _, work := range liveWork {
			if work.WorkID == currentWorkID && work.Status == runcontrol.WorkActive && work.LeaseUntilMS > now.UnixMilli() {
				currentValid = true
				break
			}
		}
		if !currentValid {
			signals = append(signals, executionOverviewSignal("block", "current_work_identity_invalid", "current Work identity is missing, inactive, or no longer live", map[string]any{
				"work_id": currentWorkID,
			}))
		}
	}

	for activityID, activity := range activities {
		if !activity.TaskPresent {
			continue
		}
		fields := map[string]any{
			"workflow":   activity.Workflow,
			"subject_id": activity.SubjectID,
			"item_id":    activity.ItemID,
		}
		if len(activity.WorkIDs) == 0 && executionOverviewTaskIsExecuting(activity.Workflow, activity.TaskStatus) {
			signals = append(signals, executionOverviewSignal("warn", "executing_task_untracked", "executing task has no live Work authority", fields))
		} else if len(activity.WorkIDs) == 0 {
			signals = append(signals, executionOverviewSignal("info", "open_task_untracked", "open task is visible without live Work authority", fields))
		} else if executionOverviewTaskIsExecuting(activity.Workflow, activity.TaskStatus) {
			missingPaths := executionOverviewMissingClaimedScope(activity.PlannedScope, activity.ConfirmedScope)
			if len(missingPaths) > 0 {
				signals = append(signals, executionOverviewSignal("block", "executing_task_scope_unclaimed", "executing task is not covered by confirmed Work scope", map[string]any{
					"activity_id":   activityID,
					"workflow":      activity.Workflow,
					"subject_id":    activity.SubjectID,
					"item_id":       activity.ItemID,
					"missing_paths": stringsToAny(missingPaths),
				}))
			}
		}
	}
	plannedActivityIDs := make([]string, 0, len(activities))
	for activityID, activity := range activities {
		if activity.TaskPresent && len(activity.PlannedScope) > 0 {
			plannedActivityIDs = append(plannedActivityIDs, activityID)
		}
	}
	sort.Strings(plannedActivityIDs)
	for leftIndex, leftID := range plannedActivityIDs {
		left := activities[leftID]
		leftPaths := executionOverviewStringSetValues(left.PlannedScope)
		for _, rightID := range plannedActivityIDs[leftIndex+1:] {
			right := activities[rightID]
			rightPaths := executionOverviewStringSetValues(right.PlannedScope)
			leftPath, rightPath, overlaps := executionOverviewFirstScopeOverlap(leftPaths, rightPaths)
			if !overlaps {
				continue
			}
			signals = append(signals, executionOverviewSignal("warn", "planned_scope_overlap", "open tasks declare overlapping planned write scope", map[string]any{
				"left_activity_id":  leftID,
				"left_path":         leftPath,
				"right_activity_id": rightID,
				"right_path":        rightPath,
			}))
		}
	}
	type registeredResourceOwner struct {
		activityID string
		workID     string
		resource   runcontrol.ExecutionResourceIntent
	}
	resourceOwners := make([]registeredResourceOwner, 0)
	for _, registration := range registrations {
		for _, resource := range registration.Resources {
			if resource.Status != runcontrol.WriteIntentActive && resource.Status != runcontrol.WriteIntentRecovery {
				continue
			}
			resourceOwners = append(resourceOwners, registeredResourceOwner{
				activityID: registration.Activity.ActivityID,
				workID:     registration.Work.WorkID,
				resource:   resource,
			})
		}
	}
	sort.Slice(resourceOwners, func(i, j int) bool {
		left := resourceOwners[i]
		right := resourceOwners[j]
		return fmt.Sprint(left.resource.ResourceType, ":", left.resource.ResourceKeyNormalized, ":", left.activityID) <
			fmt.Sprint(right.resource.ResourceType, ":", right.resource.ResourceKeyNormalized, ":", right.activityID)
	})
	seenResourceOverlaps := map[string]bool{}
	for leftIndex, left := range resourceOwners {
		for _, right := range resourceOwners[leftIndex+1:] {
			if left.activityID == right.activityID ||
				left.resource.ResourceType != right.resource.ResourceType ||
				left.resource.ResourceKeyNormalized != right.resource.ResourceKeyNormalized {
				continue
			}
			if left.resource.Confidence == runcontrol.IntentConfirmed &&
				right.resource.Confidence == runcontrol.IntentConfirmed {
				continue
			}
			if left.resource.Mode == runcontrol.ResourceClaimShared &&
				right.resource.Mode == runcontrol.ResourceClaimShared {
				continue
			}
			identity := fmt.Sprint(
				left.resource.ResourceType, ":", left.resource.ResourceKeyNormalized, ":",
				left.activityID, ":", right.activityID,
			)
			if seenResourceOverlaps[identity] {
				continue
			}
			seenResourceOverlaps[identity] = true
			signals = append(signals, executionOverviewSignal(
				"warn",
				"planned_resource_overlap",
				"announced activities may compete for the same semantic resource",
				map[string]any{
					"resource_type":     left.resource.ResourceType,
					"resource_key":      left.resource.ResourceKey,
					"left_activity_id":  left.activityID,
					"left_work_id":      left.workID,
					"left_confidence":   left.resource.Confidence,
					"right_activity_id": right.activityID,
					"right_work_id":     right.workID,
					"right_confidence":  right.resource.Confidence,
				},
			))
		}
	}
	for _, work := range liveWork {
		if work.RecoveryHold {
			signals = append(signals, executionOverviewSignal("warn", "work_recovery_hold", "interrupted Work retains dirty or uninspectable scope", map[string]any{
				"work_id":              work.WorkID,
				"work_revision":        work.Revision,
				"fence":                work.Fence,
				"observed_paths":       stringsToAny(work.ObservedPaths),
				"last_heartbeat_at_ms": work.HeartbeatAtMS,
				"lease_until_ms":       work.LeaseUntilMS,
				"last_reason":          work.LastReason,
				"next_action":          work.NextAction,
				"recovery_action":      "resume_or_abandon_after_inspection",
				"recovery_sha256":      executionRecoverySHA256(work),
			}))
		}
	}
	for _, warning := range reconciliation.InspectionWarnings {
		signals = append(signals, executionOverviewSignal("warn", "work_board_inspection_warning", "expired Work scope was preserved because its workspace could not be inspected", map[string]any{
			"workspace_root": warning.WorkspaceRoot,
			"reason":         warning.Reason,
			"fallback":       warning.Fallback,
		}))
	}

	activityProjections := make([]map[string]any, 0, len(activities))
	workflowSet := map[string]bool{}
	untrackedOpenTasks := 0
	for _, activity := range activities {
		workflowSet[activity.Workflow] = true
		if activity.TaskPresent && len(activity.WorkIDs) == 0 {
			untrackedOpenTasks++
		}
		activityProjections = append(activityProjections, executionOverviewActivityProjection(activity))
	}
	sort.Slice(activityProjections, func(i, j int) bool {
		return stringValue(activityProjections[i]["activity_id"]) < stringValue(activityProjections[j]["activity_id"])
	})
	sort.Slice(workProjections, func(i, j int) bool {
		return stringValue(workProjections[i]["work_id"]) < stringValue(workProjections[j]["work_id"])
	})
	sort.SliceStable(signals, func(i, j int) bool {
		left := executionOverviewSignalRank(stringValue(signals[i]["level"]))
		right := executionOverviewSignalRank(stringValue(signals[j]["level"]))
		if left != right {
			return left < right
		}
		return stringValue(signals[i]["code"])+fmt.Sprint(signals[i]) < stringValue(signals[j]["code"])+fmt.Sprint(signals[j])
	})

	blockerCount, warningCount := 0, 0
	for _, signal := range signals {
		switch stringValue(signal["level"]) {
		case "block":
			blockerCount++
		case "warn":
			warningCount++
		}
	}
	coordinationState := "clear"
	recommendedAction := "proceed"
	if warningCount > 0 {
		coordinationState = "attention"
		recommendedAction = "review_execution_signals"
	}
	if blockerCount > 0 {
		coordinationState = "blocked"
		recommendedAction = "resolve_execution_blockers"
	}
	warnings := make([]map[string]any, 0, len(reconciliation.InspectionWarnings))
	for _, warning := range reconciliation.InspectionWarnings {
		warnings = append(warnings, map[string]any{
			"workspace_root": warning.WorkspaceRoot,
			"reason":         warning.Reason,
			"fallback":       warning.Fallback,
		})
	}
	changeProjections := make([]any, 0, len(changes))
	for _, change := range changes {
		changeProjections = append(changeProjections, map[string]any{
			"revision":           change.EventID,
			"aggregate_type":     change.AggregateType,
			"aggregate_id":       change.AggregateID,
			"aggregate_revision": change.AggregateRevision,
			"event_type":         change.EventType,
			"reason":             change.Reason,
			"created_at_ms":      change.CreatedAtMS,
		})
	}
	data := map[string]any{
		"snapshot_kind":             executionOverviewSnapshotKind,
		"coordination_state":        coordinationState,
		"recommended_action":        recommendedAction,
		"current_work_id":           currentWorkID,
		"workflow_count":            len(workflowSet),
		"execution_count":           len(activityProjections),
		"open_task_count":           len(tasks),
		"live_work_count":           len(workProjections),
		"untracked_open_task_count": untrackedOpenTasks,
		"blocker_count":             blockerCount,
		"warning_count":             warningCount,
		"signal_count":              len(signals),
		"coordination_revision":     coordinationRevision,
		"registered_activity_count": len(registrations),
		"activities":                activityProjections,
		"work_board":                workProjections,
		"signals":                   signals,
		"changes":                   changeProjections,
		"changed_since_revision":    sinceRevision >= 0 && coordinationRevision > sinceRevision,
		"since_revision":            sinceRevision,
		"reconciliation": map[string]any{
			"interrupted_count":   len(reconciliation.Interrupted),
			"inspection_warnings": warnings,
		},
	}
	snapshotPayload := make(map[string]any, len(data))
	for key, value := range data {
		if key == "changes" || key == "changed_since_revision" || key == "since_revision" {
			continue
		}
		snapshotPayload[key] = value
	}
	snapshotJSON, err := json.Marshal(snapshotPayload)
	if err != nil {
		return Envelope{}, fmt.Errorf("encode execution overview snapshot: %w", err)
	}
	snapshotDigest := sha256.Sum256(snapshotJSON)
	data["snapshot_sha256"] = hex.EncodeToString(snapshotDigest[:])
	data["observed_at_ms"] = now.UnixMilli()
	envelopeStatus := "ok"
	envelopeSummary := "shared execution overview loaded"
	if blockerCount > 0 {
		envelopeStatus = "blocked"
		envelopeSummary = "shared execution overview found blocking ownership inconsistencies"
	}
	env := NewEnvelope(envelopeStatus, envelopeSummary)
	env.Data = data
	for _, signal := range signals {
		env.Items = append(env.Items, signal)
		if stringValue(signal["level"]) == "block" {
			env.Blockers = append(env.Blockers, signal)
		}
	}
	env.ShowArgv = []string{"specify-runtime", "execution", "overview"}
	if currentWorkID != "" {
		env.ShowArgv = append(env.ShowArgv, "--current-work-id", currentWorkID)
	}
	if sinceRevision >= 0 {
		env.ShowArgv = append(env.ShowArgv, "--since-revision", fmt.Sprint(sinceRevision))
	}
	env.ShowArgv = append(env.ShowArgv, "--project-root", projectRoot, "--format", "json")
	return env, nil
}

func scanExecutionOverviewTasks(projectRoot string) ([]executionOverviewTask, []map[string]any) {
	tasks := make([]executionOverviewTask, 0)
	signals := make([]map[string]any, 0)
	quickService := quickService{projectRoot: projectRoot}
	quickRoot, err := quickService.root()
	if err != nil {
		signals = append(signals, executionOverviewSourceSignal("quick", ".planning/quick", err))
	} else if quickTasks, scanErr := quickService.scan(quickRoot); scanErr != nil {
		signals = append(signals, executionOverviewSourceSignal("quick", ".planning/quick", scanErr))
	} else {
		for _, task := range quickTasks {
			if !isQuickUnfinished(task) {
				continue
			}
			workspacePath := stringValue(task["workspace_path"])
			scope, _, scopeErr := quickCoordinationWriteScope(workspacePath)
			if scopeErr != nil {
				signals = append(signals, executionOverviewSourceSignal("quick", filepath.ToSlash(filepath.Join(".planning", "quick", stringValue(task["workspace"]), quickConfirmationFileName)), scopeErr))
			}
			tasks = append(tasks, executionOverviewTask{
				Workflow:     "quick",
				SubjectID:    stringValue(task["id"]),
				Title:        stringValue(task["title"]),
				Status:       strings.ToLower(stringValue(task["status"])),
				NextAction:   stringValue(task["next_action"]),
				SourceRef:    filepath.ToSlash(filepath.Join(".planning", "quick", stringValue(task["workspace"]), "STATUS.md")),
				PlannedScope: scope,
			})
		}
	}

	featuresRoot, err := secureProjectPath(projectRoot, ".specify/features")
	if err != nil {
		signals = append(signals, executionOverviewSourceSignal("implement", ".specify/features", err))
		return tasks, signals
	}
	entries, err := os.ReadDir(featuresRoot)
	if os.IsNotExist(err) {
		return tasks, signals
	}
	if err != nil {
		signals = append(signals, executionOverviewSourceSignal("implement", ".specify/features", err))
		return tasks, signals
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		featureID := entry.Name()
		ref := filepath.ToSlash(filepath.Join(".specify", "features", featureID, "task-index.json"))
		raw, readErr := secureProjectReadFile(projectRoot, ref)
		if os.IsNotExist(readErr) {
			continue
		}
		if readErr != nil {
			signals = append(signals, executionOverviewSourceSignal("implement", ref, readErr))
			continue
		}
		var index map[string]any
		if decodeErr := json.Unmarshal(raw, &index); decodeErr != nil || index == nil {
			if decodeErr == nil {
				decodeErr = fmt.Errorf("task index is not an object")
			}
			signals = append(signals, executionOverviewSourceSignal("implement", ref, decodeErr))
			continue
		}
		if value := strings.TrimSpace(anyString(index["feature_id"])); value != "" {
			featureID = value
		}
		rawTasks, ok := index["tasks"].([]any)
		if !ok {
			signals = append(signals, executionOverviewSourceSignal("implement", ref, fmt.Errorf("tasks must be an array")))
			continue
		}
		for _, rawTask := range rawTasks {
			task, ok := rawTask.(map[string]any)
			if !ok {
				continue
			}
			status := taskControlStatus(task)
			if implementTaskTerminalStatuses[status] {
				continue
			}
			itemID := strings.ToUpper(strings.TrimSpace(anyString(firstImplementTaskValue(task["id"], task["task_id"]))))
			if !implementTaskIDRE.MatchString(itemID) {
				continue
			}
			scope := make([]string, 0)
			seenScope := map[string]bool{}
			for _, path := range anyStringSlice(task["expected_write_scope"]) {
				path = quickCoordinationWriteScopePath(path)
				if path == "" || seenScope[path] {
					continue
				}
				seenScope[path] = true
				scope = append(scope, path)
			}
			sort.Strings(scope)
			tasks = append(tasks, executionOverviewTask{
				Workflow:     "implement",
				SubjectID:    featureID,
				ItemID:       itemID,
				Title:        strings.TrimSpace(anyString(task["objective"])),
				Status:       status,
				SourceRef:    ref + "#/tasks/" + itemID,
				PlannedScope: scope,
			})
		}
	}
	sort.Slice(tasks, func(i, j int) bool {
		return executionOverviewActivityKey(tasks[i].Workflow, tasks[i].SubjectID, tasks[i].ItemID) < executionOverviewActivityKey(tasks[j].Workflow, tasks[j].SubjectID, tasks[j].ItemID)
	})
	return tasks, signals
}

func executionOverviewActivityKey(workflow, subjectID, itemID string) string {
	workflow = normalizeExecutionOverviewWorkflow(workflow)
	subjectID = strings.TrimSpace(subjectID)
	itemID = strings.TrimSpace(itemID)
	key := workflow + ":" + subjectID
	if itemID != "" {
		key += "#" + itemID
	}
	return key
}

func ensureExecutionOverviewActivity(activities map[string]*executionOverviewActivityAccumulator, key, workflow, subjectID, itemID string) *executionOverviewActivityAccumulator {
	if activity := activities[key]; activity != nil {
		return activity
	}
	activity := &executionOverviewActivityAccumulator{
		Workflow:              normalizeExecutionOverviewWorkflow(workflow),
		SubjectID:             strings.TrimSpace(subjectID),
		ItemID:                strings.TrimSpace(itemID),
		SourceRefs:            map[string]bool{},
		WorkIDs:               map[string]bool{},
		PlannedScope:          map[string]bool{},
		ConfirmedScope:        map[string]bool{},
		RegisteredActivityIDs: map[string]bool{},
	}
	activities[key] = activity
	return activity
}

func parseExecutionOverviewTaskRef(taskRef string, quickAliases map[string]string) (string, string, string) {
	taskRef = strings.TrimSpace(taskRef)
	lower := strings.ToLower(taskRef)
	for _, workflow := range []string{"fast", "debug", "quick", "implement"} {
		prefix := workflow + ":"
		if !strings.HasPrefix(lower, prefix) {
			continue
		}
		target := strings.TrimSpace(taskRef[len(prefix):])
		itemID := ""
		if marker := strings.LastIndex(target, "#"); marker >= 0 {
			itemID = strings.ToUpper(strings.TrimSpace(target[marker+1:]))
			target = strings.TrimSpace(target[:marker])
		}
		if workflow == "quick" {
			if alias := quickAliases[target]; alias != "" {
				target = alias
			}
			itemID = ""
		}
		return workflow, target, itemID
	}
	if marker := strings.LastIndex(taskRef, "#"); marker > 0 {
		itemID := strings.ToUpper(strings.TrimSpace(taskRef[marker+1:]))
		if implementTaskIDRE.MatchString(itemID) {
			return "implement", strings.TrimSpace(taskRef[:marker]), itemID
		}
	}
	if taskRef == "" {
		return "other", "unbound", ""
	}
	return "other", taskRef, ""
}

func executionOverviewKeysForWork(
	activities map[string]*executionOverviewActivityAccumulator,
	implementTaskKeys map[string][]string,
	workflow, subjectID, itemID, workID string,
) []string {
	if workflow == "implement" && itemID == "" && len(implementTaskKeys[subjectID]) > 0 {
		return append([]string(nil), implementTaskKeys[subjectID]...)
	}
	if subjectID == "" || subjectID == "unbound" {
		subjectID = workID
	}
	key := executionOverviewActivityKey(workflow, subjectID, itemID)
	if _, exists := activities[key]; !exists {
		ensureExecutionOverviewActivity(activities, key, workflow, subjectID, itemID)
	}
	return []string{key}
}

func normalizeExecutionOverviewWorkflow(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	value = strings.ReplaceAll(value, "_", "-")
	value = strings.TrimPrefix(value, "spx-")
	value = strings.TrimPrefix(value, "sp-")
	switch value {
	case "fast", "debug", "implement", "quick":
		return value
	default:
		return "other"
	}
}

func executionOverviewTaskIsExecuting(workflow, status string) bool {
	status = strings.ToLower(strings.TrimSpace(status))
	switch workflow {
	case "quick":
		return status == "executing" || status == "in_progress"
	case "implement":
		return status == "in_progress"
	default:
		return false
	}
}

func executionOverviewActivityProjection(activity *executionOverviewActivityAccumulator) map[string]any {
	trackingState := "untracked"
	hasTask, hasWork := activity.TaskPresent, len(activity.WorkIDs) > 0
	switch {
	case hasTask && hasWork:
		trackingState = "work_tracked"
	case hasTask:
		trackingState = "task_only"
	case hasWork:
		trackingState = "work_only"
	}
	return map[string]any{
		"activity_id":             executionOverviewActivityKey(activity.Workflow, activity.SubjectID, activity.ItemID),
		"workflow":                activity.Workflow,
		"subject_id":              activity.SubjectID,
		"item_id":                 activity.ItemID,
		"title":                   activity.Title,
		"task_status":             activity.TaskStatus,
		"next_action":             activity.NextAction,
		"tracking_state":          trackingState,
		"current":                 activity.Current,
		"task_present":            activity.TaskPresent,
		"source_refs":             executionOverviewSetValues(activity.SourceRefs),
		"work_ids":                executionOverviewSetValues(activity.WorkIDs),
		"planned_write_scope":     executionOverviewSetValues(activity.PlannedScope),
		"confirmed_write_scope":   executionOverviewSetValues(activity.ConfirmedScope),
		"activity_registered":     len(activity.RegisteredActivityIDs) > 0,
		"registered_activity_ids": executionOverviewSetValues(activity.RegisteredActivityIDs),
		"lifecycle_phase":         activity.LifecyclePhase,
		"activity_revision":       activity.ActivityRevision,
		"semantic_resources":      executionOverviewResourceProjections(activity.SemanticResources),
	}
}

func executionOverviewResourceProjections(resources []runcontrol.ExecutionResourceIntent) []any {
	result := make([]map[string]any, 0, len(resources))
	for _, resource := range resources {
		if resource.Status != runcontrol.WriteIntentActive && resource.Status != runcontrol.WriteIntentRecovery {
			continue
		}
		result = append(result, map[string]any{
			"type":        resource.ResourceType,
			"key":         resource.ResourceKey,
			"mode":        resource.Mode,
			"confidence":  resource.Confidence,
			"status":      resource.Status,
			"activity_id": resource.ActivityID,
		})
	}
	sort.Slice(result, func(i, j int) bool {
		return fmt.Sprint(result[i]["type"], ":", result[i]["key"], ":", result[i]["activity_id"]) <
			fmt.Sprint(result[j]["type"], ":", result[j]["key"], ":", result[j]["activity_id"])
	})
	projected := make([]any, 0, len(result))
	for _, resource := range result {
		projected = append(projected, resource)
	}
	return projected
}

func executionOverviewWorkProjection(work runcontrol.WorkItem, intents []runcontrol.WriteIntent, workflow string) map[string]any {
	projectedIntents := make([]map[string]any, 0, len(intents))
	for _, intent := range intents {
		if intent.Status != runcontrol.WriteIntentActive && intent.Status != runcontrol.WriteIntentRecovery {
			continue
		}
		projectedIntents = append(projectedIntents, map[string]any{
			"path":       intent.Path,
			"operation":  intent.Operation,
			"confidence": intent.Confidence,
			"status":     intent.Status,
		})
	}
	sort.Slice(projectedIntents, func(i, j int) bool {
		return stringValue(projectedIntents[i]["path"]) < stringValue(projectedIntents[j]["path"])
	})
	return map[string]any{
		"work_id":         work.WorkID,
		"task_ref":        work.TaskRef,
		"workflow":        workflow,
		"summary":         work.Summary,
		"agent_id":        work.AgentID,
		"adapter_id":      work.AdapterID,
		"status":          work.Status,
		"next_action":     work.NextAction,
		"last_reason":     work.LastReason,
		"revision":        work.Revision,
		"fence":           work.Fence,
		"lease_until_ms":  work.LeaseUntilMS,
		"heartbeat_at_ms": work.HeartbeatAtMS,
		"observed_paths":  stringsToAny(work.ObservedPaths),
		"recovery_hold":   work.RecoveryHold,
		"recovery_action": func() string {
			if work.RecoveryHold {
				return "resume_or_abandon_after_inspection"
			}
			return ""
		}(),
		"recovery_sha256": func() string {
			if work.RecoveryHold {
				return executionRecoverySHA256(work)
			}
			return ""
		}(),
		"write_intents": projectedIntents,
	}
}

func executionRecoverySHA256(work runcontrol.WorkItem) string {
	payload, err := json.Marshal(map[string]any{
		"work_id":              work.WorkID,
		"work_revision":        work.Revision,
		"fence":                work.Fence,
		"status":               work.Status,
		"recovery_hold":        work.RecoveryHold,
		"observed_paths":       uniqueSortedExecutionOverviewStrings(work.ObservedPaths),
		"last_heartbeat_at_ms": work.HeartbeatAtMS,
		"lease_until_ms":       work.LeaseUntilMS,
		"last_reason":          work.LastReason,
		"next_action":          work.NextAction,
	})
	if err != nil {
		return ""
	}
	digest := sha256.Sum256(payload)
	return hex.EncodeToString(digest[:])
}

func executionOverviewSetValues(values map[string]bool) []any {
	return stringsToAny(executionOverviewStringSetValues(values))
}

func executionOverviewStringSetValues(values map[string]bool) []string {
	result := make([]string, 0, len(values))
	for value := range values {
		if strings.TrimSpace(value) != "" {
			result = append(result, value)
		}
	}
	sort.Strings(result)
	return result
}

func executionOverviewFirstScopeOverlap(leftPaths, rightPaths []string) (string, string, bool) {
	for _, leftPath := range leftPaths {
		for _, rightPath := range rightPaths {
			overlaps, err := runcontrol.WritePathsOverlap(leftPath, rightPath)
			if err == nil && overlaps {
				return leftPath, rightPath, true
			}
		}
	}
	return "", "", false
}

func executionOverviewMissingClaimedScope(planned, confirmed map[string]bool) []string {
	missing := make([]string, 0)
	confirmedPaths := executionOverviewStringSetValues(confirmed)
	for _, plannedPath := range executionOverviewStringSetValues(planned) {
		covered := false
		for _, confirmedPath := range confirmedPaths {
			if executionOverviewPathCovers(confirmedPath, plannedPath) {
				covered = true
				break
			}
		}
		if !covered {
			missing = append(missing, plannedPath)
		}
	}
	return missing
}

func executionOverviewPathCovers(ownerPath, requestedPath string) bool {
	normalize := func(value string) string {
		value = strings.Trim(strings.TrimSpace(strings.ReplaceAll(value, `\`, "/")), "/")
		if runtime.GOOS == "windows" {
			value = strings.ToLower(value)
		}
		return value
	}
	ownerPath = normalize(ownerPath)
	requestedPath = normalize(requestedPath)
	return ownerPath != "" && (requestedPath == ownerPath || strings.HasPrefix(requestedPath, ownerPath+"/"))
}

func uniqueSortedExecutionOverviewStrings(values []string) []string {
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}

func executionOverviewQuickWorkspace(sourceRef string) string {
	parts := strings.Split(filepath.ToSlash(sourceRef), "/")
	if len(parts) >= 4 && parts[0] == ".planning" && parts[1] == "quick" {
		return parts[2]
	}
	return ""
}

func executionOverviewSignal(level, code, summary string, fields map[string]any) map[string]any {
	signal := map[string]any{"level": level, "code": code, "summary": summary}
	for key, value := range fields {
		signal[key] = value
	}
	return signal
}

func executionOverviewSourceSignal(workflow, sourceRef string, err error) map[string]any {
	return executionOverviewSignal("warn", "task_source_unavailable", "one task source could not be included in the global execution view", map[string]any{
		"workflow":   workflow,
		"source_ref": sourceRef,
		"reason":     err.Error(),
	})
}

func executionOverviewSignalRank(level string) int {
	switch level {
	case "block":
		return 0
	case "warn":
		return 1
	default:
		return 2
	}
}

func executionOverviewUsageEnvelope(message string) Envelope {
	env := NewEnvelope("usage-error", message)
	env.ShowArgv = []string{"specify-runtime", "execution", "overview", "--format", "json"}
	return env
}

func executionOverviewErrorEnvelope(err error) Envelope {
	env := NewEnvelope("error", "execution overview failed")
	env.Blockers = append(env.Blockers, err.Error())
	env.ShowArgv = []string{"specify-runtime", "execution", "overview", "--format", "json"}
	return env
}
