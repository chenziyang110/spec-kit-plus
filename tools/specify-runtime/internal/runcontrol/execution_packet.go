package runcontrol

import (
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
)

// WorkerPacketBinding is optional immutable metadata in an activity's
// BaselineJSON under "worker_packet". The outer CLI verifies the canonical
// packet, digest, and task index; the store enforces this bound on every claim.
type WorkerPacketBinding struct {
	Path       string   `json:"path"`
	SHA256     string   `json:"sha256"`
	WriteScope []string `json:"write_scope"`
}

// ExecutionScopeAmendmentSpec is the caller's bounded request to extend one
// immutable worker packet through the existing execution guard authority.
type ExecutionScopeAmendmentSpec struct {
	Path          string
	Operation     WriteOperation
	Reason        string
	LateDiscovery bool
}

// ExecutionScopeAmendment is append-only audit state. It never rewrites the
// original packet path, digest, or declared scope.
type ExecutionScopeAmendment struct {
	Path           string         `json:"path"`
	Operation      WriteOperation `json:"operation"`
	Reason         string         `json:"reason"`
	LateDiscovery  bool           `json:"late_discovery"`
	ReviewRequired bool           `json:"review_required"`
	AddedAtMS      int64          `json:"added_at_ms"`
}

func executionWorkerPacket(baselineJSON string) (*WorkerPacketBinding, error) {
	var baseline map[string]json.RawMessage
	if err := json.Unmarshal([]byte(baselineJSON), &baseline); err != nil {
		return nil, fmt.Errorf("%w: invalid execution baseline: %v", ErrInvalidArgument, err)
	}
	raw, present := baseline["worker_packet"]
	if !present {
		return nil, nil
	}
	var binding WorkerPacketBinding
	if err := json.Unmarshal(raw, &binding); err != nil {
		return nil, fmt.Errorf("%w: invalid worker_packet binding: %v", ErrInvalidArgument, err)
	}
	path, _, err := normalizeWorkPath(binding.Path, runtime.GOOS == "windows")
	if err != nil || !validSHA256(binding.SHA256) || binding.WriteScope == nil {
		return nil, fmt.Errorf("%w: worker_packet requires a relative path, sha256, and write_scope array", ErrInvalidArgument)
	}
	binding.Path = path
	for i, scope := range binding.WriteScope {
		// Packet scopes may retain the compiler's bounded subtree notation.
		scope = strings.TrimSpace(strings.ReplaceAll(scope, `\`, "/"))
		scope = strings.TrimSuffix(strings.TrimSuffix(scope, "/**"), "/*")
		path, _, err := normalizeWorkPath(scope, runtime.GOOS == "windows")
		if err != nil {
			return nil, fmt.Errorf("%w: invalid worker_packet write_scope: %v", ErrInvalidArgument, err)
		}
		binding.WriteScope[i] = path
	}
	return &binding, nil
}

func verifyExecutionPacketScope(activity ExecutionActivity, paths []string) error {
	return verifyExecutionPacketScopeWithPending(activity, paths, nil)
}

func verifyExecutionPacketScopeWithPending(activity ExecutionActivity, paths []string, pending []ExecutionScopeAmendmentSpec) error {
	binding, err := executionWorkerPacket(activity.BaselineJSON)
	if err != nil || binding == nil {
		return err
	}
	originalScope := append([]string(nil), binding.WriteScope...)
	amendedPaths := make(map[string]struct{})
	existing, err := executionScopeAmendments(activity.BaselineJSON)
	if err != nil {
		return err
	}
	for _, amendment := range existing {
		_, key, err := normalizeWorkPath(amendment.Path, runtime.GOOS == "windows")
		if err != nil {
			return err
		}
		amendedPaths[key] = struct{}{}
	}
	for _, amendment := range pending {
		_, key, err := normalizeWorkPath(amendment.Path, runtime.GOOS == "windows")
		if err != nil {
			return err
		}
		amendedPaths[key] = struct{}{}
	}
	for _, path := range paths {
		_, requested, err := normalizeWorkPath(path, runtime.GOOS == "windows")
		if err != nil {
			return err
		}
		covered := false
		for _, scope := range originalScope {
			_, held, err := normalizeWorkPath(scope, runtime.GOOS == "windows")
			if err != nil {
				return err
			}
			if requested == held || strings.HasPrefix(requested, held+"/") {
				covered = true
				break
			}
		}
		if _, amended := amendedPaths[requested]; amended {
			covered = true
		}
		if !covered {
			return fmt.Errorf("%w: path %q exceeds worker packet %q write scope", ErrExecutionGuardRequired, path, binding.Path)
		}
	}
	return nil
}

func normalizeExecutionScopeAmendmentSpecs(activity ExecutionActivity, raw []ExecutionScopeAmendmentSpec) ([]ExecutionScopeAmendmentSpec, error) {
	if len(raw) == 0 {
		return nil, nil
	}
	binding, err := executionWorkerPacket(activity.BaselineJSON)
	if err != nil {
		return nil, err
	}
	if binding == nil {
		return nil, fmt.Errorf("%w: scope amendments require an immutable worker packet binding", ErrExecutionGuardRequired)
	}
	existing, err := executionScopeAmendments(activity.BaselineJSON)
	if err != nil {
		return nil, err
	}
	originalScope := append([]string(nil), binding.WriteScope...)
	existingByKey := make(map[string]ExecutionScopeAmendment, len(existing))
	for _, amendment := range existing {
		_, key, err := normalizeWorkPath(amendment.Path, runtime.GOOS == "windows")
		if err != nil {
			return nil, err
		}
		existingByKey[key] = amendment
	}
	seen := make(map[string]struct{}, len(raw))
	normalized := make([]ExecutionScopeAmendmentSpec, 0, len(raw))
	for _, item := range raw {
		item.Path = strings.TrimSpace(strings.ReplaceAll(item.Path, `\`, "/"))
		item.Reason = strings.TrimSpace(item.Reason)
		if item.Path == "" || item.Reason == "" || strings.ContainsAny(item.Path, "*?[]") {
			return nil, fmt.Errorf("%w: packet scope amendments require a concrete repository-relative path and reason", ErrInvalidArgument)
		}
		path, key, err := normalizeWorkPath(item.Path, runtime.GOOS == "windows")
		if err != nil {
			return nil, err
		}
		item.Path = path
		if item.Operation == "" {
			item.Operation = WriteModify
		}
		switch item.Operation {
		case WriteCreate, WriteModify, WriteDelete, WriteRename:
		default:
			return nil, fmt.Errorf("%w: unsupported scope amendment operation %q", ErrInvalidArgument, item.Operation)
		}
		if _, duplicate := seen[key]; duplicate {
			return nil, fmt.Errorf("%w: duplicate scope amendment path %q", ErrInvalidArgument, item.Path)
		}
		seen[key] = struct{}{}
		if recorded, alreadyApplied := existingByKey[key]; alreadyApplied {
			if recorded.Operation != item.Operation {
				return nil, fmt.Errorf("%w: scope amendment path %q was already recorded with a different operation", ErrInvalidArgument, item.Path)
			}
			continue
		}
		alreadyCovered := false
		for _, scope := range originalScope {
			_, held, err := normalizeWorkPath(scope, runtime.GOOS == "windows")
			if err != nil {
				return nil, err
			}
			if key == held || strings.HasPrefix(key, strings.TrimSuffix(held, "/")+"/") {
				alreadyCovered = true
				break
			}
		}
		if alreadyCovered {
			return nil, fmt.Errorf("%w: scope amendment path %q is already covered by the packet", ErrInvalidArgument, item.Path)
		}
		normalized = append(normalized, item)
	}
	return normalized, nil
}

func executionScopeAmendments(baselineJSON string) ([]ExecutionScopeAmendment, error) {
	var baseline WorkspaceBaseline
	if err := json.Unmarshal([]byte(baselineJSON), &baseline); err != nil {
		return nil, fmt.Errorf("%w: invalid execution baseline: %v", ErrInvalidArgument, err)
	}
	seen := make(map[string]struct{}, len(baseline.ScopeAmendments))
	for index := range baseline.ScopeAmendments {
		amendment := &baseline.ScopeAmendments[index]
		amendment.Path = strings.TrimSpace(strings.ReplaceAll(amendment.Path, `\`, "/"))
		amendment.Reason = strings.TrimSpace(amendment.Reason)
		if amendment.Path == "" || amendment.Reason == "" || !amendment.ReviewRequired || amendment.AddedAtMS < 1 || strings.ContainsAny(amendment.Path, "*?[]") {
			return nil, fmt.Errorf("%w: invalid execution scope amendment", ErrInvalidArgument)
		}
		path, key, err := normalizeWorkPath(amendment.Path, runtime.GOOS == "windows")
		if err != nil {
			return nil, err
		}
		amendment.Path = path
		switch amendment.Operation {
		case WriteCreate, WriteModify, WriteDelete, WriteRename:
		default:
			return nil, fmt.Errorf("%w: invalid execution scope amendment operation", ErrInvalidArgument)
		}
		if _, duplicate := seen[key]; duplicate {
			return nil, fmt.Errorf("%w: duplicate execution scope amendment", ErrInvalidArgument)
		}
		seen[key] = struct{}{}
	}
	return baseline.ScopeAmendments, nil
}

func appendExecutionScopeAmendments(baselineJSON string, specs []ExecutionScopeAmendmentSpec, nowMS int64) (string, error) {
	if len(specs) == 0 {
		return baselineJSON, nil
	}
	var baseline WorkspaceBaseline
	if err := json.Unmarshal([]byte(baselineJSON), &baseline); err != nil {
		return "", fmt.Errorf("%w: invalid execution baseline: %v", ErrInvalidArgument, err)
	}
	for _, spec := range specs {
		baseline.ScopeAmendments = append(baseline.ScopeAmendments, ExecutionScopeAmendment{
			Path: spec.Path, Operation: spec.Operation, Reason: spec.Reason,
			LateDiscovery: spec.LateDiscovery, ReviewRequired: true, AddedAtMS: nowMS,
		})
	}
	raw, err := json.Marshal(baseline)
	if err != nil {
		return "", fmt.Errorf("encode execution scope amendments: %w", err)
	}
	return string(raw), nil
}

func requireExecutionScopeAmendmentReview(activity ExecutionActivity, work WorkItem, validationJSON string) error {
	amendments, err := executionScopeAmendments(activity.BaselineJSON)
	if err != nil || len(amendments) == 0 {
		return err
	}
	var evidence []map[string]any
	if err := json.Unmarshal([]byte(validationJSON), &evidence); err != nil {
		return fmt.Errorf("%w: invalid scope amendment validation", ErrExecutionCompletionGate)
	}
	for _, item := range evidence {
		command := strings.ToLower(strings.TrimSpace(fmt.Sprint(item["command"])))
		result := strings.ToLower(strings.TrimSpace(fmt.Sprint(item["result"])))
		reviewer, _ := item["reviewer"].(string)
		reviewer = strings.TrimSpace(reviewer)
		independent, _ := item["independent"].(bool)
		if command == "scope-drift-review" && (result == "passed" || result == "pass" || result == "ok") &&
			independent && reviewer != "" && !strings.EqualFold(reviewer, work.AgentID) {
			return nil
		}
	}
	return fmt.Errorf("%w: packet scope amendments require passing independent scope-drift-review evidence", ErrExecutionCompletionGate)
}

func hasExecutionGuard(activity ExecutionActivity) bool {
	return activity.GuardedOverviewRevision > 0 && validSHA256(activity.GuardedOverviewSHA256)
}
