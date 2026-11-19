package main

import (
	"context"
	"fmt"
	"maps"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

const quickCognitionJoinUsage = "specify-runtime quick cognition-join <id> --binding-id <item-binding> --work-id <work-id> --fence <current-fence> --format json"
const quickDerivedIndexRef = ".planning/quick/index.json"

func isQuickDerivedIndex(path, scope string) bool {
	return strings.HasPrefix(scope, ".planning/quick/") && sameFilesystemPath(path, quickDerivedIndexRef)
}

// Older bindings sometimes included the derived management index as a source.
// It changes during Quick status and close. Continue to check the Work claim,
// receipt digest and any explicit dependency on it independently.
func excludeQuickDerivedIndex(binding closeoutBinding) closeoutBinding {
	if binding.Workflow != "sp-quick" {
		return binding
	}
	filter := func(path string) bool { return isQuickDerivedIndex(path, binding.Scope) }
	binding.WriteScope = slices.DeleteFunc(slices.Clone(binding.WriteScope), filter)
	binding.OwnedDelta = slices.DeleteFunc(slices.Clone(binding.OwnedDelta), filter)
	for path := range binding.Source {
		if filter(path) {
			binding.Source = maps.Clone(binding.Source)
			delete(binding.Source, path)
		}
	}
	return binding
}

// The item binding and the graph receipt remain the original evidence. This
// projection binds them to the complete confirmed Quick scope when it has only
// one accepted item. It confers no Work claims or new validation observations.
type quickJoinedCloseoutBinding struct {
	ItemID        string `json:"item_id"`
	ItemBindingID string `json:"item_binding_id"`
	ReceiptSHA256 string `json:"receipt_sha256"`
}

// Derive the full-task basis from an item receipt after the caller checks its
// current native Work, source, dependencies, worker results and graph update.
func (service quickService) deriveQuickJoinedBinding(workspacePath string, receipt *mutationCognitionReceipt) (*quickJoinedCloseoutBinding, error) {
	if receipt == nil || receipt.Workflow != "sp-quick" || receipt.StrongBinding == nil {
		return nil, fmt.Errorf("a current Quick item closeout receipt is required")
	}
	proof := receipt.StrongBinding
	if proof.ItemID == "" || proof.ActivityID == "" || proof.PacketSHA256 != "" || proof.SealedAt == "" {
		return nil, fmt.Errorf("recovery requires a sealed manual Quick item Activity binding")
	}
	if closeoutBindingDigest(*proof) != proof.Digest {
		return nil, fmt.Errorf("the embedded item binding differs from its recorded digest")
	}
	if receipt.IntentID == "" || receipt.UpdateID == "" || !equalCloseoutPaths(receipt.ChangedPaths, proof.OwnedDelta) {
		return nil, fmt.Errorf("the recorded graph update must cover the item binding's exact source delta")
	}
	sourceBasis := excludeQuickDerivedIndex(*proof)
	doc, err := service.loadConfirmation(workspacePath)
	if err != nil {
		return nil, err
	}
	if len(doc.Decision.Items) != 1 || doc.Decision.Items[0].ID != proof.ItemID {
		return nil, fmt.Errorf("item binding does not cover the complete Quick task; use joined Quick Work for multiple items")
	}
	if err := service.validateCloseAgainstConfirmation(workspacePath, "resolved"); err != nil {
		return nil, err
	}
	// For the sole item, its accepted output and dependency closure are also
	// the full task's. The regular joined binding additionally snapshots each
	// item's write scope as a dependency, so require the existing validated
	// source snapshot to cover that exact scope.
	productScope := []string{}
	for _, ref := range doc.Decision.Items[0].WriteScope {
		if isQuickDerivedIndex(ref, receipt.Scope) {
			continue
		}
		if closeoutBindingProductPath(ref, receipt.Scope) {
			productScope = append(productScope, ref)
		}
		if _, covered := proof.Source[ref]; !covered {
			if _, covered := proof.Dependencies[ref]; !covered {
				return nil, fmt.Errorf("joined prerequisite %s was not observed in the source or dependency snapshot", ref)
			}
		}
	}
	if len(productScope) == 0 || !equalCloseoutPaths(productScope, sourceBasis.WriteScope) {
		return nil, fmt.Errorf("item binding write scope differs from the complete confirmed Quick product scope")
	}
	basis := *receipt
	basis.QuickJoinedBinding = nil
	return &quickJoinedCloseoutBinding{
		ItemID:        proof.ItemID,
		ItemBindingID: proof.ID,
		ReceiptSHA256: fileContentSHA256(canonicalCloseoutBindingJSON(basis)),
	}, nil
}

func verifyQuickJoinWork(root string, proof *closeoutBinding, allowCompleted bool) error {
	ctx := context.Background()
	view, err := runcontrol.OpenViewForRepository(ctx, root)
	if err != nil {
		return err
	}
	defer view.Close()
	registration, err := view.GetExecutionActivity(ctx, proof.ActivityID)
	if err != nil {
		return err
	}
	work, activity := registration.Work, registration.Activity
	if work.WorkID != proof.WorkID || work.Fence != proof.WorkFence || work.RecoveryHold ||
		work.ParentWorkID != "" || activity.Workflow != runcontrol.ExecutionWorkflowQuick ||
		activity.ItemID != proof.ItemID || activity.GuardedOverviewSHA256 == "" {
		return fmt.Errorf("recovery requires the same current, guarded manual Work")
	}
	if allowCompleted && work.Status == runcontrol.WorkCompleted && activity.Phase == runcontrol.ExecutionPhaseCompleted {
		return nil
	}
	if work.Status != runcontrol.WorkActive || work.LeaseUntilMS <= time.Now().UnixMilli() {
		return fmt.Errorf("recovery requires an active Work lease")
	}
	// Reuse the normal completion auditor to confirm the exact receipt write
	// is inside claims already held by the same Work.
	return runcontrol.AuditExecutionScope(registration, []string{proof.Scope + "/" + mutationCognitionReceiptFileName})
}

func quickCognitionJoinArgv(projectRoot, quickID string, proof *closeoutBinding) []string {
	return []string{
		"specify-runtime", "quick", "cognition-join", quickID, "--project-root", projectRoot,
		"--binding-id", proof.ID, "--work-id", proof.WorkID, "--fence", strconv.FormatInt(proof.WorkFence, 10), "--format", "json",
	}
}

func (service quickService) runCognitionJoin(quickID string, args []string) (Envelope, error) {
	bindingID := strings.TrimSpace(optionValue(args, "--binding-id", ""))
	workID := strings.TrimSpace(optionValue(args, "--work-id", ""))
	fence, err := strconv.ParseInt(optionValue(args, "--fence", ""), 10, 64)
	if quickID == "" || !validCloseoutBindingID(bindingID) || workID == "" || err != nil || fence < 1 {
		return Envelope{}, fmt.Errorf("cognition-join requires the exact item binding and current Work identity; %s", quickCognitionJoinUsage)
	}
	root, err := service.root()
	if err != nil {
		return Envelope{}, err
	}
	tasks, err := service.scan(root)
	if err != nil {
		return Envelope{}, err
	}
	task, err := matchQuickTask(tasks, quickID)
	if err != nil {
		return Envelope{}, err
	}
	if task["archived"] == true || !isQuickUnfinished(task) {
		return Envelope{}, fmt.Errorf("cognition-join requires an active Quick task")
	}
	workspace := stringValue(task["workspace_path"])
	paths, err := rt.ResolvePaths(workspace)
	if err != nil {
		return Envelope{}, err
	}
	scope, err := filepath.Rel(paths.Root, workspace)
	if err != nil {
		return Envelope{}, err
	}
	if _, err := secureProjectPath(paths.Root, filepath.ToSlash(filepath.Join(scope, mutationCognitionReceiptFileName))); err != nil {
		return Envelope{}, err
	}
	release, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return Envelope{}, err
	}
	defer release()

	receipt, err := service.loadCognitionCloseout(workspace)
	if err != nil {
		return Envelope{}, err
	}
	if receipt == nil || receipt.StrongBinding == nil || receipt.StrongBinding.ID != bindingID ||
		receipt.StrongBinding.WorkID != workID || receipt.StrongBinding.WorkFence != fence {
		return Envelope{}, fmt.Errorf("the exact Quick item receipt or Work fence changed; inspect quick status again")
	}
	if allowed, reason := mutationCognitionReceiptGateReason(workspace, receipt); !allowed {
		return Envelope{}, fmt.Errorf("item closeout evidence is not current: %s", reason)
	}
	if intent, err := pendingMutationCloseoutIntent(workspace, "sp-quick"); err != nil {
		return Envelope{}, err
	} else if intent != nil {
		return Envelope{}, fmt.Errorf("recover durable closeout intent %s before Quick join; %s", intent.ID, mutationCognitionRecoveryText(workspace, "sp-quick", receipt.ChangedPaths))
	}
	joined, err := service.deriveQuickJoinedBinding(workspace, receipt)
	if err != nil {
		return Envelope{}, err
	}
	if err := verifyQuickJoinWork(paths.Root, receipt.StrongBinding, false); err != nil {
		return Envelope{}, err
	}
	if receipt.QuickJoinedBinding == nil || *receipt.QuickJoinedBinding != *joined {
		receipt.QuickJoinedBinding = joined
		if _, err := writeMutationCognitionReceipt(workspace, *receipt); err != nil {
			return Envelope{}, err
		}
	}
	env := NewEnvelope("ok", "Quick joined closeout binding recovered from current item evidence")
	gate := service.cognitionCloseoutStatus(workspace)
	env.Data["cognition_closeout"] = gate
	if gate["allowed_close"] == true {
		env.NextArgv = []string{"specify-runtime", "quick", "close", stringValue(task["id"]), "resolved", "--project-root", paths.Root, "--format", "json"}
	} else {
		env.Status = "blocked"
		env.Summary = "Quick closeout evidence changed during join recovery"
		env.ShowArgv = []string{"specify-runtime", "quick", "status", stringValue(task["id"]), "--project-root", paths.Root, "--format", "json"}
	}
	return env, nil
}

// Shared apply may successfully persist item-scoped index evidence. Its public
// eligibility must still match the Quick workflow's terminal gate.
func projectQuickCloseoutApply(env *Envelope, workspacePath string) {
	if env.Data["workflow"] != "sp-quick" {
		return
	}
	receipt, err := loadMutationCognitionReceipt(workspacePath)
	if err != nil || receipt == nil {
		env.Data["allowed_close"] = false
		return
	}
	// A completed shared apply already revalidated the native joined proof.
	// Only item receipts require the additional Quick eligibility check.
	if receipt.StrongBinding == nil {
		return
	}
	if receipt.StrongBinding.ItemID == "" {
		env.Data["binding_scope"] = "joined"
		if summary, ok := env.Data["receipt"].(map[string]any); ok {
			summary["binding_scope"] = "joined"
		}
		return
	}
	paths, err := rt.ResolvePaths(workspacePath)
	if err != nil {
		env.Data["allowed_close"] = false
		return
	}
	gate := (quickService{projectRoot: paths.Root}).cognitionCloseoutStatus(workspacePath)
	for _, name := range []string{"allowed_close", "binding_scope", "binding_item_id", "blocked_reason", "recommended_next_action"} {
		if value, ok := gate[name]; ok {
			env.Data[name] = value
			if receipt, ok := env.Data["receipt"].(map[string]any); ok {
				receipt[name] = value
			}
		}
	}
	if gate["blocked_reason"] == "terminal_scope_requires_joined_binding" {
		env.NextArgv, _ = gate["next_argv"].([]string)
	}
}
