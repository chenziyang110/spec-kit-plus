package main

// This owner records observations, not tool execution or independent semantic
// acceptance. Its digests enforce the exact source/version consistency boundary.
import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/closeout"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
)

const closeoutBindingSchema = "cognition-closeout-binding-v1"

type closeoutBindingInput struct {
	WorkID           string                       `json:"work_id,omitempty"`
	BindingID        string                       `json:"binding_id,omitempty"`
	DependencyRefs   []string                     `json:"dependency_refs,omitempty"`
	ParentBindingIDs []string                     `json:"parent_binding_ids,omitempty"`
	Validation       []closeoutBindingObservation `json:"validation,omitempty"`
}

type closeoutBindingObservation struct {
	Command    string `json:"command"`
	Result     string `json:"result"`
	Artifact   string `json:"artifact,omitempty"`
	StartedAt  string `json:"started_at"`
	FinishedAt string `json:"finished_at"`
}

type closeoutBinding struct {
	Schema                 string                       `json:"schema"`
	ID                     string                       `json:"binding_id"`
	AttemptID              string                       `json:"attempt_id"`
	Workflow               string                       `json:"workflow"`
	Scope                  string                       `json:"scope"`
	WorkID                 string                       `json:"work_id"`
	WorkFence              int64                        `json:"work_fence"`
	TaskRef                string                       `json:"task_ref"`
	ActivityID             string                       `json:"activity_id,omitempty"`
	ItemID                 string                       `json:"item_id,omitempty"`
	PacketSHA256           string                       `json:"packet_sha256,omitempty"`
	OwnerBasis             map[string]any               `json:"owner_basis"`
	WriteScope             []string                     `json:"write_scope"`
	OwnedDelta             []string                     `json:"owned_delta"`
	Source                 map[string]string            `json:"source"`
	DependencyRefs         []string                     `json:"dependency_refs"`
	RequiredDependencyRefs []string                     `json:"required_dependency_refs"`
	Dependencies           map[string]string            `json:"dependencies"`
	AcceptedOutputs        any                          `json:"accepted_outputs"`
	AcceptedOutputSHA256   string                       `json:"accepted_output_sha256"`
	ParentBindingIDs       []string                     `json:"parent_binding_ids"`
	Parents                map[string]string            `json:"parents"`
	Validation             []closeoutBindingObservation `json:"validation"`
	ValidationArtifacts    map[string]string            `json:"validation_artifacts"`
	DoBinding              *DoCognitionBinding          `json:"do_binding,omitempty"`
	StartedAt              string                       `json:"started_at"`
	SealedAt               string                       `json:"sealed_at,omitempty"`
	Digest                 string                       `json:"sha256"`
}

func closeoutBindingDigest(binding closeoutBinding) string {
	binding.Digest = ""
	return fileContentSHA256(canonicalCloseoutBindingJSON(binding))
}

// Native projections contain both structs and JSON maps. Normalize their JSON
// representation before hashing so a persisted/reloaded projection has the same
// digest, without dropping fields or rounding large integer identifiers.
func canonicalCloseoutBindingJSON(value any) []byte {
	raw, err := json.Marshal(value)
	if err != nil {
		return nil
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var normalized any
	if decoder.Decode(&normalized) != nil {
		return nil
	}
	raw, _ = json.Marshal(normalized)
	return raw
}

func closeoutBindingDir(root string) string {
	return filepath.Join(root, ".specify", "runtime", "receipts", "cognition-bindings")
}

func closeoutBindingCurrentPath(root, workflow, scope, work string) string {
	return filepath.Join(closeoutBindingDir(root), "current-"+closeoutIntentDigest(workflow, scope, work)+".json")
}

func validCloseoutBindingID(id string) bool {
	if !strings.HasPrefix(id, "cb-") || len(id) != 35 {
		return false
	}
	_, err := hex.DecodeString(id[3:])
	return err == nil && strings.ToLower(id) == id
}

func loadCloseoutBinding(root, id string) (closeoutBinding, error) {
	var binding closeoutBinding
	if !validCloseoutBindingID(id) {
		return binding, fmt.Errorf("invalid exact binding_id")
	}
	raw, err := secureProjectReadFile(root, ".specify/runtime/receipts/cognition-bindings/"+id+".json")
	if err != nil {
		return binding, err
	}
	if err := json.Unmarshal(raw, &binding); err != nil {
		return binding, err
	}
	if binding.Schema != closeoutBindingSchema || binding.ID != id || binding.Digest != closeoutBindingDigest(binding) {
		return binding, fmt.Errorf("binding identity or mechanical digest changed")
	}
	return binding, nil
}

func closeoutBindingProductPath(path, scope string) bool {
	path = filepath.ToSlash(path)
	for _, prefix := range []string{".git/", ".specify/runtime/", ".specify/project-cognition/", ".planning/learnings/"} {
		if path == strings.TrimSuffix(prefix, "/") || strings.HasPrefix(path, prefix) {
			return false
		}
	}
	if path == mutationCognitionReceiptFileName || strings.HasSuffix(path, "/"+mutationCognitionReceiptFileName) {
		return false
	}
	if scope != "." && (strings.HasPrefix(scope, ".planning/") || strings.HasPrefix(scope, ".specify/features/") || strings.HasPrefix(scope, "specs/")) && (path == scope || strings.HasPrefix(path, scope+"/")) {
		return false
	}
	return true
}

func closeoutBindingSnapshot(root string, refs []string) (map[string]string, error) {
	result := map[string]string{}
	var visit func(string) error
	visit = func(ref string) error {
		abs, err := secureProjectPath(root, ref)
		if err != nil {
			return err
		}
		info, err := os.Lstat(abs)
		if os.IsNotExist(err) {
			result[ref] = "missing"
			return nil
		}
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("binding source is a symlink: %s", ref)
		}
		if info.IsDir() {
			result[ref] = "directory"
			entries, err := os.ReadDir(abs)
			if err != nil {
				return err
			}
			for _, entry := range entries {
				if err := visit(ref + "/" + entry.Name()); err != nil {
					return err
				}
			}
			return nil
		}
		if !info.Mode().IsRegular() {
			return fmt.Errorf("binding source must be regular: %s", ref)
		}
		raw, err := os.ReadFile(abs)
		if err != nil {
			return err
		}
		result[ref] = fmt.Sprintf("file:%s:%o", fileContentSHA256(raw), info.Mode().Perm())
		return nil
	}
	for _, ref := range refs {
		ref = filepath.ToSlash(strings.TrimSpace(ref))
		if ref == "" || ref == "." || filepath.IsAbs(ref) || strings.Contains(ref, "\\") {
			return nil, fmt.Errorf("binding refs require exact project-relative paths")
		}
		if err := visit(ref); err != nil {
			return nil, err
		}
	}
	return result, nil
}

func closeoutBindingNative(root, workflow, scope, workID string) (closeoutBinding, error) {
	binding := closeoutBinding{Schema: closeoutBindingSchema, Workflow: workflow, Scope: scope, WorkID: workID}
	ctx := context.Background()
	store, err := runcontrol.OpenViewForRepository(ctx, root)
	if err != nil {
		return binding, err
	}
	defer store.Close()
	work, intents, err := store.GetWork(ctx, workID)
	if err != nil {
		return binding, err
	}
	if filepath.Clean(work.WorkspaceRoot) != filepath.Clean(root) || work.RecoveryHold || work.Status == runcontrol.WorkAbandoned || work.Status == runcontrol.WorkBlocked || work.Status == runcontrol.WorkInterrupted {
		return binding, fmt.Errorf("binding requires the exact current Work owner without recovery hold")
	}
	binding.WorkFence, binding.TaskRef = work.Fence, work.TaskRef
	activities, err := store.ListExecutionActivities(ctx, runcontrol.ListExecutionActivitiesParams{})
	if err != nil {
		return binding, err
	}
	var activity runcontrol.ExecutionActivity
	registered := false
	for _, row := range activities {
		if row.WorkID == workID {
			activity, registered = row, true
			break
		}
	}
	if registered {
		if "sp-"+string(activity.Workflow) != workflow && !(workflow == "sp-review" && activity.Workflow == runcontrol.ExecutionWorkflowImplement) {
			return binding, fmt.Errorf("binding workflow differs from native Activity")
		}
		if activity.Phase != runcontrol.ExecutionPhaseExecuting && activity.Phase != runcontrol.ExecutionPhaseValidating && activity.Phase != runcontrol.ExecutionPhaseCompleted {
			return binding, fmt.Errorf("binding requires a guarded executing/validating Activity")
		}
		binding.ActivityID, binding.ItemID = activity.ActivityID, activity.ItemID
		registration, err := store.GetExecutionActivity(ctx, activity.ActivityID)
		if err != nil {
			return binding, err
		}
		if activity.Workflow == runcontrol.ExecutionWorkflowImplement {
			feature, _, ok := executionWorkflowControlPlaneRefs(registration)
			if !ok || feature != scope {
				return binding, fmt.Errorf("Implement binding scope differs from native feature owner")
			}
		}
		if activity.Workflow == runcontrol.ExecutionWorkflowQuick {
			service := quickService{projectRoot: root}
			tasks, err := service.scan(filepath.Join(root, ".planning", "quick"))
			if err != nil {
				return binding, err
			}
			task, err := matchQuickTask(tasks, activity.SubjectID)
			if err != nil || scope != ".planning/quick/"+stringValue(task["workspace"]) {
				return binding, fmt.Errorf("Quick binding scope differs from native task owner")
			}
		}
		if activity.Workflow == runcontrol.ExecutionWorkflowFast || activity.Workflow == runcontrol.ExecutionWorkflowDebug {
			expectedScope := "."
			if activity.SourceRef != "" {
				ref := filepath.ToSlash(activity.SourceRef)
				if _, err := secureProjectPath(root, ref); err != nil {
					return binding, err
				}
				expectedScope = filepath.ToSlash(filepath.Dir(filepath.FromSlash(ref)))
				binding.RequiredDependencyRefs = append(binding.RequiredDependencyRefs, ref)
			}
			if scope != expectedScope {
				return binding, fmt.Errorf("binding scope differs from native Activity source owner (%s)", expectedScope)
			}
		}
		var baseline runcontrol.WorkspaceBaseline
		if err := json.Unmarshal([]byte(activity.BaselineJSON), &baseline); err != nil {
			return binding, err
		}
		if baseline.WorkerPacket != nil {
			if err := verifyExecutionPacketFile(registration); err != nil {
				return binding, err
			}
			binding.PacketSHA256 = baseline.WorkerPacket.SHA256
			binding.RequiredDependencyRefs = append(binding.RequiredDependencyRefs, baseline.WorkerPacket.Path)
		}
		binding.OwnedDelta, err = runcontrol.InspectWorkspaceDelta(ctx, root, activity.BaselineJSON)
	} else {
		if workflow != "sp-do" && !strings.HasPrefix(work.TaskRef, strings.TrimPrefix(workflow, "sp-")+":") {
			return binding, fmt.Errorf("Work task_ref does not identify the exact workflow owner")
		}
		binding.OwnedDelta, err = runcontrol.InspectWorkspaceChanges(ctx, root)
		if workflow == "sp-fast" || workflow == "sp-debug" {
			return binding, fmt.Errorf("this workflow requires its native guarded Activity owner")
		}
		if workflow == "sp-implement" {
			feature, resolveErr := NewWorkflowService(root).resolveFeature(scope, "")
			if resolveErr != nil || strings.TrimPrefix(work.TaskRef, "implement:") != feature.ID {
				return binding, fmt.Errorf("binding scope differs from native Implement Work subject")
			}
		}
		if workflow == "sp-review" {
			feature, resolveErr := NewWorkflowService(root).resolveFeature(scope, "")
			if resolveErr != nil || strings.TrimPrefix(work.TaskRef, "review:") != feature.ID {
				return binding, fmt.Errorf("Review binding scope differs from native Work feature owner")
			}
		}
		if workflow == "sp-quick" {
			parts := strings.SplitN(strings.TrimPrefix(work.TaskRef, "quick:"), "#", 2)
			service := quickService{projectRoot: root}
			tasks, scanErr := service.scan(filepath.Join(root, ".planning", "quick"))
			task, matchErr := matchQuickTask(tasks, parts[0])
			if scanErr != nil || matchErr != nil || scope != ".planning/quick/"+stringValue(task["workspace"]) {
				return binding, fmt.Errorf("binding scope differs from native Quick Work subject")
			}
			if len(parts) == 2 {
				binding.ItemID = parts[1]
			}
		}
		if workflow == "sp-e2e" {
			task := strings.TrimPrefix(work.TaskRef, "e2e:")
			parts := strings.SplitN(task, "#", 2)
			if scope != ".planning/e2e/"+parts[0] {
				return binding, fmt.Errorf("E2E binding scope differs from native run owner")
			}
			if len(parts) == 2 {
				binding.ItemID = parts[1]
			}
		}
	}
	if err != nil {
		return binding, err
	}
	for _, intent := range intents {
		if intent.Confidence == runcontrol.IntentConfirmed && (intent.Status == runcontrol.WriteIntentActive || intent.Status == runcontrol.WriteIntentReleased) && closeoutBindingProductPath(intent.Path, scope) {
			binding.WriteScope = append(binding.WriteScope, intent.Path)
		}
	}
	binding.WriteScope = normalizedCloseoutPaths(binding.WriteScope)
	if len(binding.WriteScope) == 0 {
		return binding, fmt.Errorf("binding requires native confirmed product write scope")
	}
	if work.Status == runcontrol.WorkActive && work.LeaseUntilMS <= time.Now().UTC().UnixMilli() {
		return binding, fmt.Errorf("Work lease expired; recover the exact Work before binding")
	}
	baselineJSON := ""
	if registered {
		baselineJSON = activity.BaselineJSON
	}
	renamed, err := runcontrol.InspectWorkspaceRenames(ctx, root, baselineJSON)
	if err != nil {
		return binding, err
	}
	owns := func(path string) bool {
		for _, ref := range binding.WriteScope {
			if path == ref || strings.HasPrefix(path, ref+"/") {
				return true
			}
		}
		return false
	}
	for _, pair := range renamed {
		if owns(pair.Before) != owns(pair.After) {
			return binding, fmt.Errorf("rename crosses native write ownership: both endpoints %s -> %s must belong to the exact Work", pair.Before, pair.After)
		}
	}
	owned := []string{}
	for _, p := range binding.OwnedDelta {
		for _, ref := range binding.WriteScope {
			if p == ref || strings.HasPrefix(p, ref+"/") {
				owned = append(owned, p)
				break
			}
		}
	}
	binding.OwnedDelta = normalizedCloseoutPaths(owned)
	binding.Source, err = closeoutBindingSnapshot(root, binding.WriteScope)
	if err != nil {
		return binding, err
	}
	resultWorkflow := workflow
	selected, required, err := closeoutBindingRequiredOwnerRefs(root, resultWorkflow, scope, binding.ItemID)
	if err != nil {
		return binding, err
	}
	binding.RequiredDependencyRefs = normalizedCloseoutPaths(append(binding.RequiredDependencyRefs, required...))
	binding.OwnerBasis, err = closeoutBindingOwnerBasis(root, resultWorkflow, scope, selected)
	if err != nil {
		return binding, err
	}
	if !registered && (workflow == "sp-implement" || workflow == "sp-quick" || workflow == "sp-e2e") {
		allowed := []string{}
		switch workflow {
		case "sp-implement":
			for id := range selected {
				if binding.ItemID != "" && id != binding.ItemID {
					continue
				}
				row, _ := binding.OwnerBasis[id].(map[string]any)
				allowed = append(allowed, anyStringSlice(row["expected_write_scope"])...)
			}
		case "sp-quick":
			doc, loadErr := (quickService{projectRoot: root}).loadConfirmation(filepath.Join(root, filepath.FromSlash(scope)))
			if loadErr != nil {
				return binding, loadErr
			}
			for _, row := range doc.Decision.Items {
				if selected[row.ID] && (binding.ItemID == "" || binding.ItemID == row.ID) {
					allowed = append(allowed, row.WriteScope...)
				}
			}
		case "sp-e2e":
			service := e2eService{projectRoot: root, rootRef: scope, runID: filepath.Base(filepath.FromSlash(scope)), observed: map[string]string{}, pendingBlobs: map[string][]byte{}}
			state, loadErr := service.readState()
			if loadErr != nil {
				return binding, loadErr
			}
			for _, row := range state.Tasks {
				if selected[row.Contract.ID] && (binding.ItemID == "" || binding.ItemID == row.Contract.ID) {
					allowed = append(allowed, row.Contract.Outputs...)
				}
			}
		}
		for _, path := range binding.OwnedDelta {
			covered := false
			for _, ref := range allowed {
				if path == ref || strings.HasPrefix(path, ref+"/") {
					covered = true
					break
				}
			}
			if !covered {
				return binding, fmt.Errorf("actual source delta %s lies outside the current native task contract", path)
			}
		}
	}
	var merge *workerdelta.Merge
	if resultWorkflow == "sp-implement" || resultWorkflow == "sp-quick" || resultWorkflow == "sp-e2e" {
		merge, err = closeout.CollectWorkerResults(root, resultWorkflow, scope)
	}
	if err != nil {
		return binding, fmt.Errorf("current canonical worker outputs: %w", err)
	}
	accepted := []any{}
	if workflow == "sp-review" {
		accepted, err = closeoutBindingReviewAccepted(root, scope, binding.WriteScope)
		if err != nil {
			return binding, err
		}
	}
	if merge != nil {
		for _, event := range merge.Events {
			if !event.Accepted || len(selected) > 0 && !selected[event.TaskID] {
				continue
			}
			accepted = append(accepted, map[string]any{"task_id": event.TaskID, "attempt_id": event.AttemptID, "sequence": event.Sequence, "result_sha256": event.ResultSHA256, "source_ref": event.SourceRef, "source_sha256": event.SourceSHA256})
		}
	}
	if err := closeoutBindingRequireAcceptedOwners(root, resultWorkflow, scope, selected, accepted); err != nil {
		return binding, err
	}
	binding.AcceptedOutputs = accepted
	raw, _ := json.Marshal(accepted)
	binding.AcceptedOutputSHA256 = fileContentSHA256(raw)
	if workflow == "sp-do" {
		id, err := doCognitionScope(root, scope)
		if err != nil {
			return binding, err
		}
		session, _, err := loadDoSession(root, id)
		if err != nil {
			return binding, err
		}
		if session.WorkID != workID || session.WorkFence != work.Fence {
			return binding, fmt.Errorf("Do session differs from exact Work/fence")
		}
		binding.DoBinding, err = doCurrentCognitionBinding(root, id)
		if err != nil {
			return binding, err
		}
		binding.OwnedDelta = binding.DoBinding.ChangedPaths
	}
	return binding, nil
}

func sameCloseoutBindingJSON(a, b any) bool {
	x := canonicalCloseoutBindingJSON(a)
	y := canonicalCloseoutBindingJSON(b)
	return bytes.Equal(x, y)
}

// Required inputs come from the existing native owners, not from the optional
// caller list. Selected tasks include the transitive accepted producer closure.
func closeoutBindingRequiredOwnerRefs(root, workflow, scope, item string) (map[string]bool, []string, error) {
	selected := map[string]bool{}
	refs := []string{}
	addArtifact := func(ref string) {
		ref = strings.SplitN(filepath.ToSlash(ref), "#", 2)[0]
		if ref == "" || strings.Contains(ref, "://") {
			return
		}
		if _, err := os.Stat(filepath.Join(root, filepath.FromSlash(ref))); err != nil {
			ref = scope + "/" + ref
		}
		refs = append(refs, ref)
	}
	switch workflow {
	case "sp-implement":
		index, err := readImplementJSONMap(filepath.Join(root, filepath.FromSlash(scope), "task-index.json"))
		if os.IsNotExist(err) {
			return nil, nil, fmt.Errorf("legacy Implement evidence requires a current native task-index owner before strong binding")
		}
		if err != nil {
			return nil, nil, err
		}
		rows, _ := index["tasks"].([]any)
		tasks := map[string]map[string]any{}
		for _, raw := range rows {
			task, _ := raw.(map[string]any)
			id := anyString(firstImplementTaskValue(task["id"], task["task_id"]))
			tasks[id] = task
		}
		var visit func(string) error
		visit = func(id string) error {
			if selected[id] {
				return nil
			}
			task := tasks[id]
			if task == nil {
				return fmt.Errorf("required producer %s missing", id)
			}
			selected[id] = true
			for _, ref := range anyStringSlice(task["read_scope"]) {
				refs = append(refs, ref)
			}
			for _, key := range []string{"authoritative_refs", "required_refs", "policy_refs", "test_case_refs", "test_data_refs"} {
				for _, ref := range anyStringSlice(task[key]) {
					addArtifact(ref)
				}
			}
			if id != item {
				refs = append(refs, anyStringSlice(task["expected_write_scope"])...)
			}
			for _, dep := range anyStringSlice(task["dependencies"]) {
				if err := visit(dep); err != nil {
					return err
				}
			}
			return nil
		}
		if item != "" {
			if err := visit(item); err != nil {
				return nil, nil, err
			}
		} else {
			for id := range tasks {
				if err := visit(id); err != nil {
					return nil, nil, err
				}
			}
		}
	case "sp-quick":
		service := quickService{projectRoot: root}
		doc, err := service.loadConfirmation(filepath.Join(root, filepath.FromSlash(scope)))
		if err != nil {
			return nil, nil, err
		}
		var visit func(string) error
		visit = func(id string) error {
			if selected[id] {
				return nil
			}
			task, ok := findQuickItem(doc, id)
			if !ok {
				return fmt.Errorf("required Quick item %s missing", id)
			}
			selected[id] = true
			if id != item {
				refs = append(refs, task.WriteScope...)
			}
			for _, dep := range task.DependsOn {
				if err := visit(dep); err != nil {
					return err
				}
			}
			return nil
		}
		if item != "" {
			if err := visit(item); err != nil {
				return nil, nil, err
			}
		} else {
			for _, task := range doc.Decision.Items {
				if err := visit(task.ID); err != nil {
					return nil, nil, err
				}
			}
		}
	case "sp-e2e":
		service := e2eService{projectRoot: root, rootRef: scope, runID: filepath.Base(filepath.FromSlash(scope)), observed: map[string]string{}, pendingBlobs: map[string][]byte{}}
		state, err := service.readState()
		if err != nil {
			return nil, nil, err
		}
		var visit func(string) error
		visit = func(id string) error {
			if selected[id] {
				return nil
			}
			pos, err := e2eTaskIndex(&state, id)
			if err != nil {
				return err
			}
			task := state.Tasks[pos]
			selected[id] = true
			if err := service.verifyTask(&state, pos); err != nil {
				return fmt.Errorf("current E2E owner %s: %w", id, err)
			}
			refs = append(refs, task.Contract.Inputs...)
			if id != item {
				refs = append(refs, task.Contract.Outputs...)
			}
			for _, dep := range e2eDependencies(&state, task.Contract) {
				if err := visit(dep.TaskID); err != nil {
					return err
				}
			}
			return nil
		}
		if item != "" {
			if err := visit(item); err != nil {
				return nil, nil, err
			}
		} else {
			for _, task := range state.Tasks {
				if err := visit(task.Contract.ID); err != nil {
					return nil, nil, err
				}
			}
		}
	case "sp-review":
		state, err := readJSONObject(filepath.Join(root, filepath.FromSlash(scope), reviewStateFilename))
		if err != nil {
			return nil, nil, err
		}
		refs = append(refs, scope+"/"+implementationHandoffFilename)
		for _, field := range []string{"fix_assignments", "review_assignments"} {
			for _, raw := range listValue(state[field]) {
				row, _ := raw.(map[string]any)
				if row["status"] == "accepted" && row["leader_verdict"] == "accepted" {
					for _, label := range []string{"packet_ref", "result_ref"} {
						if ref := stringField(row, label); ref != "" {
							refs = append(refs, scope+"/"+ref)
						}
					}
				}
			}
		}
	}
	return selected, normalizedCloseoutPaths(refs), nil
}

func closeoutBindingReviewAccepted(root, scope string, writeScope []string) ([]any, error) {
	state, err := readJSONObject(filepath.Join(root, filepath.FromSlash(scope), reviewStateFilename))
	if err != nil {
		return nil, err
	}
	source, _ := state["source"].(map[string]any)
	accepted, allowed := []any{}, []string{}
	for _, raw := range listValue(state["fix_assignments"]) {
		row, _ := raw.(map[string]any)
		if row["status"] != "accepted" || row["leader_verdict"] != "accepted" || row["review_cycle_id"] != source["review_cycle_id"] {
			continue
		}
		for _, label := range []string{"packet", "result"} {
			ref := scope + "/" + stringField(row, label+"_ref")
			data, err := secureProjectReadFile(root, ref)
			if err != nil || fileContentSHA256(data) != stringField(row, label+"_sha256") {
				return nil, fmt.Errorf("accepted Review repair %s current %s bytes unavailable", stringField(row, "id"), label)
			}
		}
		allowed = append(allowed, listStrings(row["allowed_write_paths"])...)
		accepted = append(accepted, row)
	}
	if len(accepted) == 0 {
		return nil, fmt.Errorf("Review source binding requires accepted native repair assignments")
	}
	for _, path := range writeScope {
		covered := false
		for _, ref := range allowed {
			if path == ref || strings.HasPrefix(path, ref+"/") {
				covered = true
				break
			}
		}
		if !covered {
			return nil, fmt.Errorf("Review Work path %s is outside accepted repair scope", path)
		}
	}
	return accepted, nil
}

func closeoutBindingRequireAcceptedOwners(root, workflow, scope string, selected map[string]bool, accepted []any) error {
	current := map[string]bool{}
	for _, raw := range accepted {
		row, _ := raw.(map[string]any)
		current[anyString(row["task_id"])] = true
	}
	if workflow == "sp-implement" {
		index, err := readImplementJSONMap(filepath.Join(root, filepath.FromSlash(scope), "task-index.json"))
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		rows, _ := index["tasks"].([]any)
		for _, raw := range rows {
			task, _ := raw.(map[string]any)
			id := anyString(firstImplementTaskValue(task["id"], task["task_id"]))
			if selected[id] && taskControlStatus(task) == "accepted" && !current[id] {
				return fmt.Errorf("legacy/stale accepted task %s is audit evidence only; submit and accept a current bound result", id)
			}
		}
	}
	if workflow == "sp-quick" {
		doc, err := (quickService{projectRoot: root}).loadConfirmation(filepath.Join(root, filepath.FromSlash(scope)))
		if err != nil {
			return err
		}
		for _, row := range doc.Execution.WorkItemStatus {
			if selected[row.WorkItemID] && row.Status == "accepted" && row.RequiresWorker && !current[row.WorkItemID] {
				return fmt.Errorf("legacy/stale accepted Quick item %s requires a current bound result", row.WorkItemID)
			}
		}
	}
	return nil
}

func closeoutBindingOwnerBasis(root, workflow, scope string, selected map[string]bool) (map[string]any, error) {
	basis := map[string]any{}
	switch workflow {
	case "sp-implement":
		index, err := readImplementJSONMap(filepath.Join(root, filepath.FromSlash(scope), "task-index.json"))
		if os.IsNotExist(err) {
			return basis, nil
		}
		if err != nil {
			return nil, err
		}
		basis["source_revision"] = index["source_revision"]
		rows, _ := index["tasks"].([]any)
		for _, raw := range rows {
			task, _ := raw.(map[string]any)
			id := anyString(firstImplementTaskValue(task["id"], task["task_id"]))
			if selected[id] {
				basis[id] = task
			}
		}
	case "sp-quick":
		doc, err := (quickService{projectRoot: root}).loadConfirmation(filepath.Join(root, filepath.FromSlash(scope)))
		if err != nil {
			return nil, err
		}
		basis["confirmed_decision"] = doc.ConfirmationDigest
		for _, row := range doc.Execution.WorkItemStatus {
			if selected[row.WorkItemID] {
				basis[row.WorkItemID] = row
			}
		}
	case "sp-e2e":
		service := e2eService{projectRoot: root, rootRef: scope, runID: filepath.Base(filepath.FromSlash(scope)), observed: map[string]string{}, pendingBlobs: map[string][]byte{}}
		state, err := service.readState()
		if err != nil {
			return nil, err
		}
		for _, task := range state.Tasks {
			if selected[task.Contract.ID] {
				basis[task.Contract.ID] = map[string]any{"contract_sha256": e2eContractDigest(&state, task.Contract), "packet": task.Packet, "submission": task.Submission, "acceptance": task.Acceptance}
			}
		}
	case "sp-review":
		state, err := readJSONObject(filepath.Join(root, filepath.FromSlash(scope), reviewStateFilename))
		if err != nil {
			return nil, err
		}
		basis["source"] = state["source"]
		basis["fix_assignments"] = state["fix_assignments"]
		basis["review_assignments"] = state["review_assignments"]
	}
	return basis, nil
}

func checkCloseoutBinding(root string, binding closeoutBinding, workflow, scope, workID string, requireSealed bool, seen map[string]bool) error {
	if binding.Workflow != workflow || binding.Scope != scope || workID != "" && binding.WorkID != workID {
		return fmt.Errorf("binding workflow/scope/work does not match current owner")
	}
	if requireSealed && binding.SealedAt == "" {
		return fmt.Errorf("binding is not sealed by fresh validation observations")
	}
	if binding.Digest != closeoutBindingDigest(binding) {
		return fmt.Errorf("binding mechanical fields changed")
	}
	if seen[binding.ID] {
		return fmt.Errorf("binding dependency cycle")
	}
	seen[binding.ID] = true
	defer delete(seen, binding.ID)
	currentRaw, err := os.ReadFile(closeoutBindingCurrentPath(root, workflow, scope, binding.WorkID))
	if err != nil || strings.TrimSpace(string(currentRaw)) != binding.ID {
		return fmt.Errorf("binding attempt was superseded; begin and verify the current attempt")
	}
	current, err := closeoutBindingNative(root, workflow, scope, binding.WorkID)
	if err != nil {
		return err
	}
	for _, row := range []struct {
		name               string
		expected, observed any
	}{
		{"Work fence/task/attempt", []any{binding.WorkFence, binding.TaskRef, binding.ActivityID, binding.ItemID, binding.PacketSHA256}, []any{current.WorkFence, current.TaskRef, current.ActivityID, current.ItemID, current.PacketSHA256}},
		{"native scope", binding.WriteScope, current.WriteScope}, {"native task contract", binding.OwnerBasis, current.OwnerBasis}, {"required dependencies", binding.RequiredDependencyRefs, current.RequiredDependencyRefs}, {"actual owned delta", binding.OwnedDelta, current.OwnedDelta}, {"source bytes", binding.Source, current.Source}, {"accepted output version", binding.AcceptedOutputs, current.AcceptedOutputs}, {"Do session/epoch/source", binding.DoBinding, current.DoBinding},
	} {
		if !sameCloseoutBindingJSON(row.expected, row.observed) {
			return fmt.Errorf("%s changed after validation began", row.name)
		}
	}
	deps, err := closeoutBindingSnapshot(root, binding.DependencyRefs)
	if err != nil {
		return err
	}
	if !sameCloseoutBindingJSON(deps, binding.Dependencies) {
		return fmt.Errorf("dependency bytes changed after validation began")
	}
	refs := []string{}
	for ref := range binding.ValidationArtifacts {
		refs = append(refs, ref)
	}
	sort.Strings(refs)
	artifacts, err := closeoutBindingSnapshot(root, refs)
	if err != nil {
		return err
	}
	if !sameCloseoutBindingJSON(artifacts, binding.ValidationArtifacts) {
		return fmt.Errorf("validation artifact bytes changed")
	}
	for _, id := range binding.ParentBindingIDs {
		parent, err := loadCloseoutBinding(root, id)
		if err != nil {
			return err
		}
		if parent.Digest != binding.Parents[id] {
			return fmt.Errorf("accepted parent version changed")
		}
		if err := checkCloseoutBinding(root, parent, parent.Workflow, parent.Scope, parent.WorkID, true, seen); err != nil {
			return fmt.Errorf("affected parent %s: %w", id, err)
		}
	}
	if requireSealed {
		if err := checkCloseoutNativeVerification(root, binding); err != nil {
			return err
		}
	}
	return nil
}

func beginCloseoutBinding(root, workflow, scope string, input closeoutBindingInput) (closeoutBinding, error) {
	if input.WorkID == "" || input.BindingID != "" || len(input.Validation) > 0 {
		return closeoutBinding{}, fmt.Errorf("begin requires work_id and accepts only dependency_refs/parent_binding_ids; runtime owns all mechanical fields")
	}
	binding, err := closeoutBindingNative(root, workflow, scope, input.WorkID)
	if err != nil {
		return binding, err
	}
	binding.DependencyRefs = normalizedCloseoutPaths(append(binding.RequiredDependencyRefs, input.DependencyRefs...))
	binding.Dependencies, err = closeoutBindingSnapshot(root, binding.DependencyRefs)
	if err != nil {
		return binding, err
	}
	binding.ParentBindingIDs = sortedUniqueCloseoutStrings(input.ParentBindingIDs)
	binding.Parents = map[string]string{}
	for _, id := range binding.ParentBindingIDs {
		parent, err := loadCloseoutBinding(root, id)
		if err != nil {
			return binding, err
		}
		if err := checkCloseoutBinding(root, parent, parent.Workflow, parent.Scope, parent.WorkID, true, map[string]bool{}); err != nil {
			return binding, err
		}
		binding.Parents[id] = parent.Digest
	}
	identity := make([]byte, 16)
	if _, err := rand.Read(identity); err != nil {
		return binding, err
	}
	binding.ID = "cb-" + hex.EncodeToString(identity)
	binding.AttemptID = binding.ID + fmt.Sprintf("-f%d", binding.WorkFence)
	binding.StartedAt = time.Now().UTC().Format(time.RFC3339Nano)
	binding.Validation = []closeoutBindingObservation{}
	binding.ValidationArtifacts = map[string]string{}
	binding.Digest = closeoutBindingDigest(binding)
	if err := writeScriptJSONFile(filepath.Join(closeoutBindingDir(root), binding.ID+".json"), binding); err != nil {
		return binding, err
	}
	err = writeScriptTextFile(closeoutBindingCurrentPath(root, workflow, scope, binding.WorkID), binding.ID+"\n")
	return binding, err
}

func sealCloseoutBinding(root, workflow, scope string, input closeoutBindingInput) (closeoutBinding, error) {
	binding, err := loadCloseoutBinding(root, input.BindingID)
	if err != nil {
		return binding, err
	}
	if input.WorkID != "" || len(input.DependencyRefs) > 0 || len(input.ParentBindingIDs) > 0 {
		return binding, fmt.Errorf("seal cannot replace native work, scope or dependencies")
	}
	if err := checkCloseoutBinding(root, binding, workflow, scope, "", false, map[string]bool{}); err != nil {
		return binding, err
	}
	if binding.SealedAt != "" {
		if sameCloseoutBindingJSON(binding.Validation, input.Validation) {
			return binding, nil
		}
		return binding, fmt.Errorf("sealed validation is immutable; begin a new attempt")
	}
	if len(input.Validation) == 0 {
		return binding, fmt.Errorf("seal requires fresh passing validation observations")
	}
	started, _ := time.Parse(time.RFC3339Nano, binding.StartedAt)
	refs := []string{}
	passed := false
	for _, row := range input.Validation {
		begin, e1 := time.Parse(time.RFC3339Nano, row.StartedAt)
		end, e2 := time.Parse(time.RFC3339Nano, row.FinishedAt)
		if strings.TrimSpace(row.Command) == "" || e1 != nil || e2 != nil || begin.Before(started) || end.Before(begin) || end.After(time.Now().UTC()) {
			return binding, fmt.Errorf("validation must record this attempt's fresh command and started_at/finished_at observations")
		}
		if row.Result != "passed" && row.Result != "failed" && row.Result != "skipped" {
			return binding, fmt.Errorf("invalid validation observation result")
		}
		if row.Result == "failed" {
			return binding, fmt.Errorf("failed verification cannot seal a passing prerequisite")
		}
		passed = passed || row.Result == "passed"
		if row.Artifact != "" {
			info, err := os.Stat(filepath.Join(root, filepath.FromSlash(row.Artifact)))
			if err != nil || info.ModTime().Before(started) {
				return binding, fmt.Errorf("validation artifact predates this binding; old passing logs cannot be relabelled as fresh verification")
			}
			refs = append(refs, row.Artifact)
		}
	}
	if !passed {
		return binding, fmt.Errorf("no passing verification observation")
	}
	if err := checkCloseoutNativeVerification(root, binding); err != nil {
		return binding, err
	}
	binding.ValidationArtifacts, err = closeoutBindingSnapshot(root, normalizedCloseoutPaths(refs))
	if err != nil {
		return binding, err
	}
	for ref, digest := range binding.ValidationArtifacts {
		if digest == "missing" {
			return binding, fmt.Errorf("validation artifact is unavailable: %s", ref)
		}
	}
	binding.Validation = input.Validation
	binding.SealedAt = time.Now().UTC().Format(time.RFC3339Nano)
	binding.Digest = closeoutBindingDigest(binding)
	if err := checkCloseoutBinding(root, binding, workflow, scope, "", true, map[string]bool{}); err != nil {
		return binding, err
	}
	err = writeScriptJSONFile(filepath.Join(closeoutBindingDir(root), binding.ID+".json"), binding)
	return binding, err
}

func requireStrongCloseoutBinding(root, workflow, scope, id, workID string) (*closeoutBinding, error) {
	if id == "" {
		return nil, fmt.Errorf("missing cognition.closeout.binding.v1 proof; legacy receipts remain audit input; begin before fresh verification, seal observations, and retry the owning closeout")
	}
	binding, err := loadCloseoutBinding(root, id)
	if err != nil {
		return nil, err
	}
	if err := checkCloseoutBinding(root, binding, workflow, scope, workID, true, map[string]bool{}); err != nil {
		return nil, err
	}
	return &binding, nil
}

func activeImplementationCloseoutBinding(root, feature, stage string) (*closeoutBinding, error) {
	workID := strings.TrimSpace(os.Getenv("SPECIFY_WORK_ID"))
	if workID == "" {
		return nil, nil
	}
	scope, err := filepath.Rel(root, feature)
	if err != nil {
		return nil, err
	}
	scope = filepath.ToSlash(scope)
	workflow := "sp-" + stage
	raw, err := os.ReadFile(closeoutBindingCurrentPath(root, workflow, scope, workID))
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	proof, err := loadCloseoutBinding(root, strings.TrimSpace(string(raw)))
	if err != nil {
		return nil, err
	}
	if proof.SealedAt != "" {
		return nil, nil
	}
	if err := checkCloseoutBinding(root, proof, workflow, scope, workID, false, map[string]bool{}); err != nil {
		return nil, err
	}
	return &proof, nil
}

func checkCloseoutNativeVerification(root string, binding closeoutBinding) error {
	if binding.Workflow != "sp-implement" && binding.Workflow != "sp-review" {
		return nil
	}
	feature := filepath.Join(root, filepath.FromSlash(binding.Scope))
	if !featureEpochValidationEnabled(feature) {
		return nil
	}
	status, err := implementValidationBudgetStatus(root, feature)
	if err != nil {
		return err
	}
	purpose := "convergence"
	if binding.Workflow == "sp-review" {
		purpose = "delivery"
	}
	for _, raw := range status["runs"].([]any) {
		run, _ := raw.(map[string]any)
		if run["purpose"] == purpose && run["status"] == "passed" && run["cognition_binding_id"] == binding.ID && run["fingerprint"] == status["current_fingerprint"] {
			return nil
		}
	}
	return fmt.Errorf("current native %s verification must begin after this binding and finish against its runtime source fingerprint; retry the existing logical gate", purpose)
}

func runCognitionCloseoutBindingCLI(args []string, stdout io.Writer) int {
	return runCognitionCloseoutBindingCLIWithInput(args, os.Stdin, stdout)
}
func runCognitionCloseoutBindingCLIWithInput(args []string, stdin io.Reader, stdout io.Writer) int {
	if len(args) == 0 || containsHelpFlag(args) {
		env := NewEnvelope("ok", "source-bound closeout binding usage")
		env.Data["usage"] = "specify-runtime cognition closeout binding <begin|seal|check> --workflow <sp-*> --scope-dir <exact> --input-json <object|-> [--project-root <path>] --format json"
		env.Data["ordering"] = "begin after edits and accepted joins, before fresh verification; seal observations against the unchanged basis; apply --binding-id <id>; owning terminal gate checks the current proof"
		env.Data["evidence_limit"] = "runtime records observations and version consistency; it does not execute agent tools, authenticate agent identity or establish independent semantic truth"
		return writeEnvelope(stdout, env)
	}
	workflow, err := normalizeMutationWorkflowID(optionValue(args, "--workflow", ""))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	_, scope, err := resolveCloseoutApplyScope(paths.Root, optionValue(args, "--scope-dir", ""))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	inputValue := optionValue(args, "--input-json", "")
	if strings.HasPrefix(inputValue, "@") {
		ref := strings.TrimPrefix(inputValue, "@")
		if filepath.IsAbs(ref) {
			relative, relErr := filepath.Rel(paths.Root, ref)
			if relErr != nil {
				return writeEnvelope(stdout, scriptDomainError("cognition", relErr))
			}
			ref = filepath.ToSlash(relative)
		}
		metadata, registered := LookupArtifactType(filepath.ToSlash(ref))
		if !registered || !strings.HasPrefix(metadata.Owner, "specify-runtime ") {
			return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("@path requires an existing registered runtime-owned artifact; use inline JSON or stdin for a new input")))
		}
	}
	raw, err := resolveJSONInputBytesFrom(inputValue, paths.Root, "closeout binding", "--input-json", stdin)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	var input closeoutBindingInput
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&input); err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("binding input rejects mechanical/unknown fields: %w", err)))
	}
	var trailing any
	if decoder.Decode(&trailing) != io.EOF {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("binding input requires one object")))
	}
	var binding closeoutBinding
	if args[0] == "check" {
		if input.WorkID != "" || len(input.Validation) > 0 || len(input.DependencyRefs) > 0 || len(input.ParentBindingIDs) > 0 {
			err = fmt.Errorf("check accepts only exact binding_id")
		} else {
			var ptr *closeoutBinding
			ptr, err = requireStrongCloseoutBinding(paths.Root, workflow, scope, input.BindingID, "")
			if ptr != nil {
				binding = *ptr
			}
		}
	} else {
		// Preserve Do-before-cognition lock ordering. No Learning lock is acquired.
		releaseDo := func() {}
		if workflow == "sp-do" {
			var id string
			id, err = doCognitionScope(paths.Root, scope)
			if err == nil {
				releaseDo, err = doSessionLock(paths.Root, id)
			}
		}
		if err != nil {
			return writeEnvelope(stdout, scriptDomainError("cognition", err))
		}
		defer releaseDo()
		release, lockErr := rt.AcquireUpdateLock(paths)
		if lockErr != nil {
			return writeEnvelope(stdout, scriptDomainError("cognition", lockErr))
		}
		defer release()
		switch args[0] {
		case "begin":
			binding, err = beginCloseoutBinding(paths.Root, workflow, scope, input)
		case "seal":
			binding, err = sealCloseoutBinding(paths.Root, workflow, scope, input)
		default:
			err = fmt.Errorf("unknown binding action %q", args[0])
		}
	}
	if err != nil {
		env := NewEnvelope("blocked", "source-bound closeout proof refused")
		env.Data["error"] = err.Error()
		env.Data["strong_proof"] = false
		env.Data["recovery"] = "repair the native owner/current source, begin a new binding before verification, seal fresh observations, and retry the existing workflow terminal owner"
		return writeEnvelope(stdout, env)
	}
	env := NewEnvelope("ok", "exact closeout binding recorded or checked")
	env.Data["binding"] = binding
	env.Data["strong_proof"] = binding.SealedAt != ""
	env.Data["evidence_origin"] = "agent_tool_observation"
	return writeEnvelope(stdout, env)
}

func closeoutBindingBeginInputSchema() map[string]any {
	return doSchemaObject(map[string]any{"work_id": doSchemaString(), "dependency_refs": doSchemaStrings(), "parent_binding_ids": doSchemaStrings()}, "work_id")
}
func closeoutBindingSealInputSchema() map[string]any {
	observation := doSchemaObject(map[string]any{"command": doSchemaString(), "result": doSchemaEnum("passed", "failed", "skipped"), "artifact": doSchemaString(), "started_at": map[string]any{"type": "string", "format": "date-time"}, "finished_at": map[string]any{"type": "string", "format": "date-time"}}, "command", "result", "started_at", "finished_at")
	return doSchemaObject(map[string]any{"binding_id": doSchemaString(), "validation": map[string]any{"type": "array", "minItems": 1, "items": observation}}, "binding_id", "validation")
}

// Planning only discovers native authority; it never creates Work or proof.
func addCloseoutBindingPlan(payload map[string]any, args []string) {
	if payload["status"] != "ok" {
		return
	}
	workflow, err := normalizeMutationWorkflowID(optionValue(args, "--workflow", ""))
	if err != nil {
		return
	}
	if workflow == "sp-do" {
		payload["binding_capability"] = "cognition.closeout.binding.v1"
		payload["binding_status"] = "existing_do_source_proof"
		payload["binding_ordering"] = "consume the existing native Do session/epoch/definition/source proof through shared apply; do not begin a second verification cycle"
		return
	}
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return
	}
	_, scope, err := resolveCloseoutApplyScope(paths.Root, firstNonEmpty(optionValue(args, "--scope-dir", ""), optionValue(args, "--feature-dir", "")))
	if err != nil {
		return
	}
	view, err := runcontrol.OpenViewForRepository(context.Background(), paths.Root)
	if err != nil {
		payload["binding_status"] = "native_work_required"
		return
	}
	defer view.Close()
	works, err := view.ListWork(context.Background(), runcontrol.ListWorkParams{Statuses: []runcontrol.WorkStatus{runcontrol.WorkActive, runcontrol.WorkCompleted}})
	if err != nil {
		return
	}
	candidates := []string{}
	for _, work := range works {
		if _, err := closeoutBindingNative(paths.Root, workflow, scope, work.WorkID); err == nil {
			candidates = append(candidates, work.WorkID)
		}
	}
	payload["binding_capability"] = "cognition.closeout.binding.v1"
	payload["binding_ordering"] = "begin before the owning fresh verification; seal observations against unchanged bytes; apply with the returned binding_id; terminal owners recheck it"
	if len(candidates) != 1 {
		payload["binding_status"] = "native_work_selection_required"
		payload["binding_work_candidates"] = candidates
		return
	}
	draft := map[string]any{"work_id": candidates[0], "dependency_refs": []string{}, "parent_binding_ids": []string{}}
	raw, _ := json.Marshal(draft)
	payload["binding_status"] = "ready_to_begin_before_verification"
	payload["binding_begin_input"] = draft
	payload["binding_begin_argv"] = []string{"specify-runtime", "cognition", "closeout", "binding", "begin", "--workflow", workflow, "--scope-dir", scope, "--input-json", string(raw), "--project-root", paths.Root, "--format", "json"}
	// The placeholder is an opaque runtime ID, never an agent-authored digest.
	for _, field := range []string{"apply_argv", "registration_apply_argv"} {
		if argv, ok := payload[field].([]any); ok && len(argv) > 0 {
			payload[field] = append(argv, "--binding-id", "<binding_id returned by seal>")
		}
	}
}
