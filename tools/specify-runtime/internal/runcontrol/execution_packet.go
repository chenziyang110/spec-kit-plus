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
	binding, err := executionWorkerPacket(activity.BaselineJSON)
	if err != nil || binding == nil {
		return err
	}
	for _, path := range paths {
		_, requested, err := normalizeWorkPath(path, runtime.GOOS == "windows")
		if err != nil {
			return err
		}
		covered := false
		for _, scope := range binding.WriteScope {
			_, held, err := normalizeWorkPath(scope, runtime.GOOS == "windows")
			if err != nil {
				return err
			}
			if requested == held || strings.HasPrefix(requested, held+"/") {
				covered = true
				break
			}
		}
		if !covered {
			return fmt.Errorf("%w: path %q exceeds worker packet %q write scope", ErrExecutionGuardRequired, path, binding.Path)
		}
	}
	return nil
}

func hasExecutionGuard(activity ExecutionActivity) bool {
	return activity.GuardedOverviewRevision > 0 && validSHA256(activity.GuardedOverviewSHA256)
}
