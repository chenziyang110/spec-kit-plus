package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const quickCoordinationSnapshotKind = "quick-coordination-v1"

type quickCoordinationBoardEntry struct {
	work        runcontrol.WorkItem
	intents     []runcontrol.WriteIntent
	linkedQuick string
	projection  map[string]any
}

func (service quickService) runPreflight(quickID string, args []string) (Envelope, error) {
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	if _, err := service.writeIndex(root, tasks); err != nil {
		return Envelope{}, err
	}

	currentQuickID := ""
	if strings.TrimSpace(quickID) != "" {
		current, matchErr := matchQuickTask(tasks, quickID)
		if matchErr != nil {
			return Envelope{}, matchErr
		}
		if !isQuickUnfinished(current) {
			return Envelope{}, fmt.Errorf("quick preflight requires an unfinished task: %s", quickID)
		}
		currentQuickID = stringValue(current["id"])
	}

	unfinished := make([]map[string]any, 0, len(tasks))
	for _, task := range tasks {
		if isQuickUnfinished(task) {
			unfinished = append(unfinished, task)
		}
	}
	sort.Slice(unfinished, func(i, j int) bool {
		return stringValue(unfinished[i]["id"])+stringValue(unfinished[i]["workspace"]) <
			stringValue(unfinished[j]["id"])+stringValue(unfinished[j]["workspace"])
	})

	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, service.projectRoot)
	if err != nil {
		return Envelope{}, fmt.Errorf("open shared Work Board for quick preflight: %w", err)
	}
	now := time.Now().UTC()
	reconciliation, operationErr := store.ReconcileRepositoryWork(ctx, now)
	if operationErr != nil {
		_ = store.Close()
		return Envelope{}, fmt.Errorf("reconcile shared Work Board for quick preflight: %w", operationErr)
	}

	workItems, operationErr := store.ListWork(ctx, runcontrol.ListWorkParams{Statuses: []runcontrol.WorkStatus{
		runcontrol.WorkActive,
		runcontrol.WorkBlocked,
		runcontrol.WorkInterrupted,
	}})
	if operationErr != nil {
		_ = store.Close()
		return Envelope{}, fmt.Errorf("list shared Work Board for quick preflight: %w", operationErr)
	}

	quickAliases := make(map[string]string, len(unfinished)*2)
	for _, task := range unfinished {
		id := stringValue(task["id"])
		quickAliases[id] = id
		quickAliases[stringValue(task["workspace"])] = id
	}
	currentWorkID := strings.TrimSpace(optionValue(args, "--current-work-id", os.Getenv("SPECIFY_WORK_ID")))
	boardEntries := make([]quickCoordinationBoardEntry, 0, len(workItems))
	linkedWorkByQuick := make(map[string][]string)
	for _, work := range workItems {
		live := (work.Status == runcontrol.WorkActive || work.Status == runcontrol.WorkBlocked) && work.LeaseUntilMS > now.UnixMilli()
		recoveryHeld := work.Status == runcontrol.WorkInterrupted && work.RecoveryHold
		if !live && !recoveryHeld {
			continue
		}
		_, intents, getErr := store.GetWork(ctx, work.WorkID)
		if getErr != nil {
			_ = store.Close()
			return Envelope{}, getErr
		}
		linkedQuick := quickCoordinationLinkedQuick(work.TaskRef, quickAliases)
		if linkedQuick != "" {
			linkedWorkByQuick[linkedQuick] = append(linkedWorkByQuick[linkedQuick], work.WorkID)
		}
		boardEntries = append(boardEntries, quickCoordinationBoardEntry{
			work:        work,
			intents:     intents,
			linkedQuick: linkedQuick,
			projection:  quickCoordinationWorkProjection(work, intents, linkedQuick, work.WorkID == currentWorkID),
		})
	}
	sort.Slice(boardEntries, func(i, j int) bool { return boardEntries[i].work.WorkID < boardEntries[j].work.WorkID })
	for quickID := range linkedWorkByQuick {
		sort.Strings(linkedWorkByQuick[quickID])
	}

	quickProjections := make([]map[string]any, 0, len(unfinished))
	quickScopeByID := make(map[string][]string, len(unfinished))
	untrackedQuickCount := 0
	for _, task := range unfinished {
		id := stringValue(task["id"])
		scope, scopeState, scopeErr := quickCoordinationWriteScope(stringValue(task["workspace_path"]))
		quickScopeByID[id] = scope
		workIDs := append([]string(nil), linkedWorkByQuick[id]...)
		tracking := "tracked"
		if len(workIDs) == 0 {
			tracking = "untracked"
			untrackedQuickCount++
		}
		projection := map[string]any{
			"id":                  id,
			"title":               task["title"],
			"status":              task["status"],
			"current_focus":       task["current_focus"],
			"next_action":         task["next_action"],
			"workspace":           task["workspace"],
			"current":             id == currentQuickID,
			"planned_write_scope": scope,
			"scope_state":         scopeState,
			"board_tracking":      tracking,
			"board_work_ids":      workIDs,
		}
		if scopeErr != nil {
			projection["scope_error"] = scopeErr.Error()
		}
		quickProjections = append(quickProjections, projection)
	}

	boardProjections := make([]map[string]any, 0, len(boardEntries))
	boardOnlyWorkCount := 0
	concurrentWorkCount := 0
	for _, entry := range boardEntries {
		boardProjections = append(boardProjections, entry.projection)
		if entry.work.WorkID != currentWorkID {
			concurrentWorkCount++
			if entry.linkedQuick == "" {
				boardOnlyWorkCount++
			}
		}
	}

	signals := make([]map[string]any, 0)
	for _, task := range quickProjections {
		id := stringValue(task["id"])
		if task["board_tracking"] == "untracked" {
			code := "unfinished_quick_untracked"
			summary := "unfinished Quick has no live Work Board registration"
			if id == currentQuickID {
				code = "current_quick_untracked"
				summary = "current Quick must register on the Work Board before source writes"
			}
			signals = append(signals, quickCoordinationSignal("warn", code, summary, map[string]any{"quick_id": id}))
		} else if id != currentQuickID {
			signals = append(signals, quickCoordinationSignal("info", "other_unfinished_quick", "another unfinished Quick is visible", map[string]any{"quick_id": id}))
		}
		if scopeError := strings.TrimSpace(stringValue(task["scope_error"])); scopeError != "" {
			signals = append(signals, quickCoordinationSignal("warn", "quick_scope_unavailable", "Quick planned write scope could not be read", map[string]any{
				"quick_id": id,
				"reason":   scopeError,
			}))
		}
	}
	for _, entry := range boardEntries {
		if entry.work.WorkID == currentWorkID || entry.linkedQuick != "" {
			continue
		}
		signals = append(signals, quickCoordinationSignal("info", "board_only_work", "live Work Board item has no unfinished Quick workspace", map[string]any{
			"work_id":  entry.work.WorkID,
			"task_ref": entry.work.TaskRef,
		}))
	}
	for _, warning := range reconciliation.InspectionWarnings {
		signals = append(signals, quickCoordinationSignal("warn", "work_board_inspection_warning", "expired work scope was preserved because its workspace could not be inspected", map[string]any{
			"workspace_root": warning.WorkspaceRoot,
			"reason":         warning.Reason,
			"fallback":       warning.Fallback,
		}))
	}

	if currentQuickID != "" {
		currentScope := quickScopeByID[currentQuickID]
		for _, task := range quickProjections {
			otherID := stringValue(task["id"])
			if otherID == currentQuickID {
				continue
			}
			if currentPath, otherPath, overlap := quickCoordinationFirstScopeOverlap(currentScope, quickScopeByID[otherID]); overlap {
				signals = append(signals, quickCoordinationSignal("warn", "unfinished_quick_scope_overlap", "unfinished Quick tasks declare overlapping planned write scope", map[string]any{
					"quick_id":         otherID,
					"requested_path":   currentPath,
					"other_quick_path": otherPath,
				}))
			}
		}
	}

	conflicts := make([]map[string]any, 0)
	seenConflicts := map[string]bool{}
	if currentQuickID != "" {
		for _, requestedPath := range quickScopeByID[currentQuickID] {
			owners, findErr := store.FindWorkOwners(ctx, requestedPath)
			if findErr != nil {
				signals = append(signals, quickCoordinationSignal("warn", "quick_scope_invalid", "planned write scope cannot be checked against the Work Board", map[string]any{
					"quick_id": currentQuickID,
					"path":     requestedPath,
					"reason":   findErr.Error(),
				}))
				continue
			}
			for _, owner := range owners {
				if owner.Work.WorkID == currentWorkID {
					continue
				}
				ownerQuick := quickCoordinationLinkedQuick(owner.Work.TaskRef, quickAliases)
				if currentWorkID == "" && ownerQuick == currentQuickID {
					continue
				}
				key := strings.Join([]string{requestedPath, owner.Intent.Path, owner.Work.WorkID}, "\x00")
				if seenConflicts[key] {
					continue
				}
				seenConflicts[key] = true
				conflict := map[string]any{
					"requested_path": requestedPath,
					"owner_path":     owner.Intent.Path,
					"owner_work_id":  owner.Work.WorkID,
					"owner_quick_id": ownerQuick,
					"owner_agent_id": owner.Work.AgentID,
					"owner_summary":  owner.Work.Summary,
					"owner_status":   owner.Work.Status,
					"intent_status":  owner.Intent.Status,
				}
				conflicts = append(conflicts, conflict)
				signals = append(signals, quickCoordinationSignal("block", "write_overlap", "confirmed Work Board owner overlaps the current Quick write scope", conflict))
			}
		}
	}
	if closeErr := store.Close(); closeErr != nil {
		return Envelope{}, fmt.Errorf("close shared Work Board after quick preflight: %w", closeErr)
	}

	coordinationState := "clear"
	recommendedAction := "proceed"
	if len(conflicts) != 0 {
		coordinationState = "blocked"
		recommendedAction = "resolve_write_overlap"
	} else if currentQuickID != "" && len(linkedWorkByQuick[currentQuickID]) == 0 {
		coordinationState = "attention"
		recommendedAction = "register_current_quick_before_writes"
	} else if len(signals) != 0 {
		coordinationState = "attention"
		recommendedAction = "review_concurrent_work_then_proceed"
	}

	otherQuickCount := len(quickProjections)
	if currentQuickID != "" {
		otherQuickCount--
	}
	if otherQuickCount < 0 {
		otherQuickCount = 0
	}
	warnings := make([]map[string]any, 0, len(reconciliation.InspectionWarnings))
	for _, warning := range reconciliation.InspectionWarnings {
		warnings = append(warnings, map[string]any{
			"workspace_root": warning.WorkspaceRoot,
			"reason":         warning.Reason,
			"fallback":       warning.Fallback,
		})
	}
	data := map[string]any{
		"snapshot_kind":                quickCoordinationSnapshotKind,
		"coordination_state":           coordinationState,
		"recommended_action":           recommendedAction,
		"current_quick_id":             currentQuickID,
		"current_work_id":              currentWorkID,
		"unfinished_quick_count":       len(quickProjections),
		"other_unfinished_quick_count": otherQuickCount,
		"live_work_count":              len(boardProjections),
		"concurrent_work_count":        concurrentWorkCount,
		"untracked_quick_count":        untrackedQuickCount,
		"board_only_work_count":        boardOnlyWorkCount,
		"conflict_count":               len(conflicts),
		"quick_tasks":                  quickProjections,
		"work_board":                   boardProjections,
		"conflicts":                    conflicts,
		"signals":                      signals,
		"reconciliation": map[string]any{
			"interrupted_count":   len(reconciliation.Interrupted),
			"inspection_warnings": warnings,
		},
	}
	envelopeStatus := "ok"
	envelopeSummary := "Quick coordination preflight loaded"
	if len(conflicts) != 0 {
		envelopeStatus = "blocked"
		envelopeSummary = "Quick coordination is blocked by confirmed write overlap"
	}
	env := NewEnvelope(envelopeStatus, envelopeSummary)
	env.Data = data
	for _, signal := range signals {
		env.Items = append(env.Items, signal)
		if stringValue(signal["level"]) == "block" {
			env.Blockers = append(env.Blockers, signal)
		}
	}
	env.ShowArgv = []string{"specify-runtime", "quick", "preflight"}
	if currentQuickID != "" {
		env.ShowArgv = append(env.ShowArgv, currentQuickID)
	}
	env.ShowArgv = append(env.ShowArgv, "--project-root", service.projectRoot, "--format", "json")
	return env, nil
}

func quickCoordinationWriteScope(workspacePath string) ([]string, string, error) {
	raw, err := os.ReadFile(filepath.Join(workspacePath, quickConfirmationFileName))
	if os.IsNotExist(err) {
		return []string{}, "not_staged", nil
	}
	if err != nil {
		return []string{}, "unavailable", err
	}
	var doc quickConfirmationDoc
	if err := json.Unmarshal(raw, &doc); err != nil {
		return []string{}, "invalid", fmt.Errorf("decode confirmation.json: %w", err)
	}
	if doc.Schema != quickConfirmationSchema {
		return []string{}, "invalid", fmt.Errorf("unsupported confirmation schema %q", doc.Schema)
	}
	seen := map[string]bool{}
	paths := make([]string, 0)
	for _, item := range doc.Decision.Items {
		for _, path := range item.WriteScope {
			path = quickCoordinationWriteScopePath(path)
			if path == "" || seen[path] {
				continue
			}
			seen[path] = true
			paths = append(paths, path)
		}
	}
	sort.Strings(paths)
	return paths, "available", nil
}

func quickCoordinationWriteScopePath(path string) string {
	path = strings.TrimSpace(strings.ReplaceAll(path, `\`, "/"))
	if strings.HasSuffix(path, "/**") {
		path = strings.TrimSuffix(path, "/**")
	} else if strings.HasSuffix(path, "/*") {
		path = strings.TrimSuffix(path, "/*")
	}
	return strings.TrimSuffix(path, "/")
}

func quickCoordinationLinkedQuick(taskRef string, aliases map[string]string) string {
	taskRef = strings.TrimSpace(taskRef)
	if len(taskRef) < len("quick:") || !strings.EqualFold(taskRef[:len("quick:")], "quick:") {
		return ""
	}
	target := strings.TrimSpace(taskRef[len("quick:"):])
	if item := strings.Index(target, "#"); item >= 0 {
		target = strings.TrimSpace(target[:item])
	}
	return aliases[target]
}

func quickCoordinationWorkProjection(work runcontrol.WorkItem, intents []runcontrol.WriteIntent, linkedQuick string, current bool) map[string]any {
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
	return map[string]any{
		"work_id":       work.WorkID,
		"task_ref":      work.TaskRef,
		"summary":       work.Summary,
		"agent_id":      work.AgentID,
		"status":        work.Status,
		"next_action":   work.NextAction,
		"recovery_hold": work.RecoveryHold,
		"quick_id":      linkedQuick,
		"current":       current,
		"write_intents": projectedIntents,
	}
}

func quickCoordinationFirstScopeOverlap(current, other []string) (string, string, bool) {
	for _, currentPath := range current {
		for _, otherPath := range other {
			overlap, err := runcontrol.WritePathsOverlap(currentPath, otherPath)
			if err == nil && overlap {
				return currentPath, otherPath, true
			}
		}
	}
	return "", "", false
}

func quickCoordinationSignal(level, code, summary string, fields map[string]any) map[string]any {
	signal := map[string]any{"level": level, "code": code, "summary": summary}
	for key, value := range fields {
		signal[key] = value
	}
	return signal
}
