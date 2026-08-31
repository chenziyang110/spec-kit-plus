package runcontrol

import (
	"context"
	"database/sql"
	"fmt"
	"sort"
	"strings"
	"time"
)

// GetExecutionActivityForWork is discovery only. Callers must still verify the
// current guard transactionally before any item-start or source mutation.
func (store *Store) GetExecutionActivityForWork(ctx context.Context, workID string) (ExecutionActivity, bool, error) {
	tx, err := store.db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return ExecutionActivity{}, false, fmt.Errorf("read execution activity for Work: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	activity, found, err := readExecutionActivityByWorkTx(ctx, tx, workID)
	if err != nil {
		return ExecutionActivity{}, false, err
	}
	if err := tx.Commit(); err != nil {
		return ExecutionActivity{}, false, err
	}
	return activity, found, nil
}

// VerifyExecutionWorkClaim validates an existing execution guard for a bounded
// item-start handoff. It never claims, promotes, expands, or releases file or
// semantic scope, and never changes a lease, fence, revision, or event. The
// returned intents are the existing owners that cover the requested paths.
// Packet-bound work must also own every pinned write path, including runtime
// bookkeeping that item-start writes even when absent from the caller's Specs.
// Callers must still use GuardExecution to acquire or expand execution scope.
func (store *Store) VerifyExecutionWorkClaim(ctx context.Context, params ClaimWorkIntentsParams) (WorkItem, []WriteIntent, error) {
	params.WorkID = strings.TrimSpace(params.WorkID)
	if params.WorkID == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, nil, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	specs := make([]normalizedWriteIntentSpec, 0, len(params.Specs))
	seenPaths := make(map[string]bool, len(params.Specs))
	for _, raw := range params.Specs {
		spec, err := normalizeWriteIntentSpec(raw)
		if err != nil {
			return WorkItem{}, nil, err
		}
		if seenPaths[spec.pathKey] {
			return WorkItem{}, nil, fmt.Errorf("%w: duplicate write intent path %q", ErrInvalidArgument, spec.Path)
		}
		seenPaths[spec.pathKey] = true
		specs = append(specs, spec)
	}

	// ReadOnly makes this a deferred SQLite read transaction even though normal
	// Store mutations use immediate transactions for atomic conflict checks.
	tx, err := store.db.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return WorkItem{}, nil, fmt.Errorf("begin execution claim verification: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	if err := requireWorkAuthority(work, params.ExpectedRevision, params.Fence, time.Now().UTC().UnixMilli()); err != nil {
		return WorkItem{}, nil, err
	}
	activity, registered, err := readExecutionActivityByWorkTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	if !registered || work.Status != WorkActive || work.RecoveryHold ||
		activity.Phase != ExecutionPhaseExecuting || !hasExecutionGuard(activity) {
		return WorkItem{}, nil, fmt.Errorf("%w: Work %q has no current executing guard", ErrExecutionGuardRequired, work.WorkID)
	}
	binding, err := executionWorkerPacket(activity.BaselineJSON)
	if err != nil {
		return WorkItem{}, nil, err
	}
	if binding != nil && (strings.TrimSpace(params.PacketRef) != binding.Path || strings.TrimSpace(params.PacketSHA256) != binding.SHA256) {
		return WorkItem{}, nil, fmt.Errorf("%w: Work %q requires its exact worker packet path and sha256", ErrExecutionGuardRequired, work.WorkID)
	}
	paths := make([]string, 0, len(specs))
	for _, spec := range specs {
		paths = append(paths, spec.Path)
	}
	if err := verifyExecutionPacketScope(activity, paths); err != nil {
		return WorkItem{}, nil, err
	}
	requestedCount := len(specs)
	if binding != nil {
		for _, path := range binding.WriteScope {
			spec, err := normalizeWriteIntentSpec(WriteIntentSpec{Path: path})
			if err != nil {
				return WorkItem{}, nil, err
			}
			if !seenPaths[spec.pathKey] {
				seenPaths[spec.pathKey] = true
				specs = append(specs, spec)
			}
		}
	}
	intents, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	covered := make([]WriteIntent, 0, requestedCount)
	seenIntents := make(map[string]bool)
	for index, spec := range specs {
		var owner *WriteIntent
		for i := range intents {
			intent := &intents[i]
			if intent.Status != WriteIntentActive || intent.Confidence != IntentConfirmed {
				continue
			}
			// A held subtree covers its children; a held child cannot authorize
			// its parent or a sibling that happens to share a textual prefix.
			if intent.PathKey == spec.pathKey || strings.HasPrefix(spec.pathKey, strings.TrimSuffix(intent.PathKey, "/")+"/") {
				if owner == nil || len(intent.PathKey) > len(owner.PathKey) {
					owner = intent
				}
			}
		}
		if owner == nil {
			return WorkItem{}, nil, fmt.Errorf("%w: Work %q has no active confirmed scope covering %q", ErrExecutionGuardRequired, work.WorkID, spec.Path)
		}
		if index < requestedCount && !seenIntents[owner.IntentID] {
			seenIntents[owner.IntentID] = true
			covered = append(covered, *owner)
		}
	}
	sort.Slice(covered, func(i, j int) bool { return covered[i].PathKey < covered[j].PathKey })
	if err := tx.Commit(); err != nil {
		return WorkItem{}, nil, fmt.Errorf("finish execution claim verification: %w", err)
	}
	return work, covered, nil
}
