package main

import (
	"context"
	"crypto/sha256"
	"fmt"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

const workScopeClaimSchema = "work-scope-claim-v1"

type currentWorkScopeClaimRequest struct {
	ProjectRoot                          string
	Args                                 []string
	AllowedTaskRef                       []string
	WriteScope                           []string
	Reason                               string
	UseCurrentConfirmedScopeWhenEmpty    bool
	AllowDeclaredNoWriteWhenScopeIsEmpty bool
	AllowExecutionGuardReceipt           bool
	PacketRef                            string
}

// claimCurrentWorkScope is the shared claim-before-write gate used by every
// modifying execution workflow. It validates the caller's fenced Work
// identity and claims the complete normalized scope in one transaction.
func claimCurrentWorkScope(request currentWorkScopeClaimRequest) (map[string]any, error) {
	workID := strings.TrimSpace(optionValue(request.Args, "--current-work-id", os.Getenv("SPECIFY_WORK_ID")))
	fenceValue := strings.TrimSpace(optionValue(request.Args, "--current-work-fence", os.Getenv("SPECIFY_WORK_FENCE")))
	if workID == "" || fenceValue == "" {
		return nil, fmt.Errorf("claim-before-write requires current Work identity: set SPECIFY_WORK_ID and SPECIFY_WORK_FENCE or pass --current-work-id and --current-work-fence")
	}
	fence, err := strconv.ParseInt(fenceValue, 10, 64)
	if err != nil || fence < 1 {
		return nil, fmt.Errorf("claim-before-write requires a positive current Work fence, got %q", fenceValue)
	}

	allowedTaskRefs := make(map[string]struct{}, len(request.AllowedTaskRef))
	for _, raw := range request.AllowedTaskRef {
		if taskRef := strings.TrimSpace(raw); taskRef != "" {
			allowedTaskRefs[taskRef] = struct{}{}
		}
	}
	if len(allowedTaskRefs) == 0 {
		return nil, fmt.Errorf("claim-before-write requires at least one allowed task_ref")
	}

	normalizedScope, err := normalizeWorkClaimScope(request.WriteScope)
	if err != nil {
		return nil, err
	}
	ctx := context.Background()
	store, err := runcontrol.OpenForRepository(ctx, firstNonEmpty(strings.TrimSpace(request.ProjectRoot), "."))
	if err != nil {
		return nil, fmt.Errorf("open shared Work Board for claim-before-write: %w", err)
	}
	defer func() { _ = store.Close() }()
	if _, err := store.ReconcileRepositoryWork(ctx, time.Now().UTC()); err != nil {
		return nil, fmt.Errorf("reconcile shared Work Board for claim-before-write: %w", err)
	}
	work, currentIntents, err := store.GetWork(ctx, workID)
	if err != nil {
		return nil, fmt.Errorf("load current Work identity for claim-before-write: %w", err)
	}
	if work.Fence != fence {
		return nil, fmt.Errorf("current Work fence is stale: work %q holds fence %d, received %d", workID, work.Fence, fence)
	}
	if work.Status != runcontrol.WorkActive {
		return nil, fmt.Errorf("current Work %q is %s; resume or unblock it before claiming write scope", workID, work.Status)
	}
	if _, ok := allowedTaskRefs[strings.TrimSpace(work.TaskRef)]; !ok {
		return nil, fmt.Errorf("current Work task_ref %q does not match allowed task refs %s", work.TaskRef, strings.Join(sortedStringSet(allowedTaskRefs), ", "))
	}
	if len(normalizedScope) == 0 && request.UseCurrentConfirmedScopeWhenEmpty {
		fallbackScope := make([]string, 0, len(currentIntents))
		for _, intent := range currentIntents {
			if intent.Confidence == runcontrol.IntentConfirmed &&
				(intent.Status == runcontrol.WriteIntentActive || intent.Status == runcontrol.WriteIntentRecovery) {
				fallbackScope = append(fallbackScope, intent.Path)
			}
		}
		normalizedScope, err = normalizeWorkClaimScope(fallbackScope)
		if err != nil {
			return nil, err
		}
	}
	reason := strings.TrimSpace(request.Reason)
	if reason == "" {
		reason = "claim-before-write for " + strings.TrimSpace(work.TaskRef)
	}
	specs := make([]runcontrol.WriteIntentSpec, 0, len(normalizedScope))
	for _, path := range normalizedScope {
		specs = append(specs, runcontrol.WriteIntentSpec{
			Path:       path,
			Operation:  runcontrol.WriteModify,
			Reason:     reason,
			Confidence: runcontrol.IntentConfirmed,
		})
	}
	claimParams := runcontrol.ClaimWorkIntentsParams{
		WorkID:           work.WorkID,
		ExpectedRevision: work.Revision,
		Fence:            fence,
		Specs:            specs,
	}
	if request.PacketRef != "" {
		packetPath, err := resolveProjectContainedPath(request.ProjectRoot, request.PacketRef)
		if err != nil {
			return nil, fmt.Errorf("resolve task-start packet: %w", err)
		}
		content, err := os.ReadFile(packetPath)
		if err != nil {
			return nil, fmt.Errorf("read task-start packet: %w", err)
		}
		claimParams.PacketRef = request.PacketRef
		claimParams.PacketSHA256 = fmt.Sprintf("%x", sha256.Sum256(content))
	}
	claimedWork := work
	var claimedIntents []runcontrol.WriteIntent
	verifiedExecution := false
	if request.AllowExecutionGuardReceipt {
		activity, registered, err := store.GetExecutionActivityForWork(ctx, work.WorkID)
		if err != nil {
			return nil, fmt.Errorf("load execution identity before item start: %w", err)
		}
		if registered {
			if err := verifyExecutionPacketFile(runcontrol.ExecutionRegistration{Activity: activity, Work: work}); err != nil {
				return nil, fmt.Errorf("verify current item-start packet: %w", err)
			}
			claimedWork, claimedIntents, err = store.VerifyExecutionWorkClaim(ctx, claimParams)
			if err != nil {
				return nil, fmt.Errorf("verify complete execution scope before item start: %w", err)
			}
			verifiedExecution = true
		}
	}
	// A source-read-only result is an exemption from source mutation, never
	// from a registered Activity's current guard and immutable packet binding.
	if len(normalizedScope) == 0 {
		if request.AllowDeclaredNoWriteWhenScopeIsEmpty {
			return map[string]any{
				"schema":               workScopeClaimSchema,
				"claim_state":          "not_required",
				"work_id":              work.WorkID,
				"work_fence":           work.Fence,
				"work_revision":        work.Revision,
				"task_ref":             work.TaskRef,
				"write_scope":          []string{},
				"claimed_intent_count": 0,
			}, nil
		}
		return nil, fmt.Errorf("claim-before-write requires a non-empty complete write scope")
	}

	if !verifiedExecution {
		claimedWork, claimedIntents, err = store.ClaimWorkIntents(ctx, claimParams)
		if err != nil {
			return nil, fmt.Errorf("claim complete write scope all-or-none: %w", err)
		}
	}
	claimedScope := make([]string, 0, len(claimedIntents))
	for _, intent := range claimedIntents {
		claimedScope = append(claimedScope, intent.Path)
	}
	return map[string]any{
		"schema":               workScopeClaimSchema,
		"claim_state":          "claimed",
		"work_id":              claimedWork.WorkID,
		"work_fence":           claimedWork.Fence,
		"work_revision":        claimedWork.Revision,
		"task_ref":             claimedWork.TaskRef,
		"write_scope":          claimedScope,
		"claimed_intent_count": len(claimedIntents),
	}, nil
}

func normalizeWorkClaimScope(rawScope []string) ([]string, error) {
	seen := make(map[string]struct{}, len(rawScope))
	normalized := make([]string, 0, len(rawScope))
	for _, rawPath := range rawScope {
		path := strings.TrimSpace(strings.ReplaceAll(rawPath, `\`, "/"))
		if strings.HasSuffix(path, "/**") {
			path = strings.TrimSuffix(path, "/**")
		} else if strings.HasSuffix(path, "/*") {
			path = strings.TrimSuffix(path, "/*")
		}
		path = strings.TrimSuffix(path, "/")
		if path == "" {
			return nil, fmt.Errorf("claim-before-write contains a blank write scope path")
		}
		key := path
		if runtime.GOOS == "windows" {
			key = strings.ToLower(key)
		}
		if _, exists := seen[key]; exists {
			continue
		}
		seen[key] = struct{}{}
		normalized = append(normalized, path)
	}
	return normalized, nil
}

func sortedStringSet(values map[string]struct{}) []string {
	result := make([]string, 0, len(values))
	for value := range values {
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}
