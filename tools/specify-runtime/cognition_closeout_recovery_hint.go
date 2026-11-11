package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
)

// A persisted intent is the recovery owner. Receipt compatibility must not
// replace it, including while an old successful scope receipt is still present.
func pendingMutationCloseoutIntent(scopeDir, workflow string, excludedIntentIDs ...string) (*closeoutIntent, error) {
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return nil, err
	}
	scope, err := filepath.Rel(paths.Root, scopeDir)
	if err != nil {
		return nil, err
	}
	canonical, err := normalizeMutationWorkflowID(workflow)
	if err != nil {
		return nil, err
	}
	intents, err := listCloseoutIntents(paths)
	if err != nil {
		return nil, err
	}
	for _, intent := range intents {
		if containsCloseoutIntentID(excludedIntentIDs, intent.ID) {
			continue
		}
		if intent.Workflow == canonical && sameFilesystemPath(filepath.FromSlash(intent.Scope), scope) {
			return &intent, nil
		}
	}
	return nil, nil
}

func containsCloseoutIntentID(ids []string, id string) bool {
	for _, candidate := range ids {
		if candidate == id {
			return true
		}
	}
	return false
}

// Shared apply/replay may evaluate its bound receipt just before removing the
// exact intent. Keep that atomic publication path independent of unrelated
// malformed queue entries, as exact replay has always been.
func matchingMutationCloseoutIntent(scopeDir string, receipt *mutationCognitionReceipt) (bool, error) {
	if receipt.IntentID == "" {
		return false, nil
	}
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return false, err
	}
	if _, err := os.Stat(closeoutIntentPath(paths, receipt.IntentID)); os.IsNotExist(err) {
		return false, nil
	} else if err != nil {
		return false, err
	}
	intent, err := loadCloseoutIntent(paths, receipt.IntentID)
	if err != nil {
		return false, err
	}
	scope, err := filepath.Rel(paths.Root, scopeDir)
	if err != nil {
		return false, err
	}
	return intent.Workflow == receipt.Workflow && intent.InputDigest == receipt.IntentDigest && sameFilesystemPath(filepath.FromSlash(intent.Scope), scope), nil
}

// Exact replay has always left unrelated invalid queue records untouched.
// Use its committed update identity to retain that behavior, whether its own
// intent has been pruned or still awaits pruning. Only that exact identity is
// excluded: other intents for the same owner and scope still block closeout.
// This route is never available to a standalone receipt.
func pendingIntentForCommittedMutationReceipt(scopeDir string, receipt *mutationCognitionReceipt) (*closeoutIntent, bool, error) {
	if receipt.IntentID == "" || receipt.UpdateID == "" {
		return nil, false, nil
	}
	paths, err := rt.ResolvePaths(scopeDir)
	if err != nil {
		return nil, false, err
	}
	committed, err := closeoutCommittedUpdate(paths, receipt.IntentID)
	if err != nil || committed != receipt.UpdateID {
		return nil, false, nil
	}
	active, err := closeoutCommitInActiveGeneration(paths, committed)
	if err != nil || !active {
		return nil, false, nil
	}
	scope, err := filepath.Rel(paths.Root, scopeDir)
	if err != nil {
		return nil, true, err
	}
	entries, err := os.ReadDir(filepath.Join(paths.RuntimeDir, "closeout-intents"))
	if os.IsNotExist(err) {
		return nil, true, nil
	}
	if err != nil {
		return nil, true, err
	}
	for _, entry := range entries {
		id := strings.TrimSuffix(entry.Name(), ".json")
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") || !validCloseoutIntentID(id) {
			continue
		}
		if id == receipt.IntentID {
			continue
		}
		intent, err := loadCloseoutIntent(paths, id)
		if err != nil {
			// Only a committed, bound receipt may ignore this other identity.
			// Normal apply and standalone compatibility still inspect/refuse it.
			continue
		}
		if intent.Workflow == receipt.Workflow && sameFilesystemPath(filepath.FromSlash(intent.Scope), scope) {
			return &intent, true, nil
		}
	}
	return nil, true, nil
}

func mutationCognitionRecoveryArgv(scopeDir, workflow string, changedPaths []string) []string {
	paths, err := rt.ResolvePaths(scopeDir)
	if err == nil {
		// A blocked receipt pins an exact intent even if its repair publication
		// has already replaced the original pending file.
		if receipt, loadErr := loadMutationCognitionReceipt(scopeDir); loadErr == nil && receipt != nil && validCloseoutIntentID(receipt.IntentID) {
			_, intentErr := os.Stat(closeoutIntentPath(paths, receipt.IntentID))
			_, repairErr := os.Stat(closeoutRepairPath(paths, receipt.IntentID))
			if intentErr == nil || repairErr == nil {
				return closeoutRecoveryArgv(paths, "inspect", receipt.IntentID, "")
			}
		}
		if intent, intentErr := pendingMutationCloseoutIntent(scopeDir, workflow); intentErr != nil {
			return []string{"specify-runtime", "cognition", "closeout", "inspect", "--project-root", paths.Root, "--format", "json"}
		} else if intent != nil {
			return closeoutRecoveryArgv(paths, "inspect", intent.ID, "")
		}
		if agreement, exists := runtimegate.CheckExisting(paths); exists && agreement.CauseCode == runtimegate.CauseGraphStoreIncompatible {
			return []string{"specify-runtime", "cognition", "archive-incompatible-store", "--inspect", "--format", "json"}
		}
	}
	canonical, canonicalErr := normalizeMutationWorkflowID(workflow)
	if canonicalErr != nil {
		canonical = workflow
	}
	argv := []string{"specify-runtime", "cognition", "closeout-plan", "--workflow", canonical, "--scope-dir", scopeDir, "--scope-mode", "explicit"}
	if err == nil {
		argv = append(argv, "--project-root", paths.Root)
	}
	for _, path := range normalizedCloseoutPaths(changedPaths) {
		argv = append(argv, "--changed-path", path)
	}
	return append(argv, "--format", "json")
}

func mutationCognitionRecoveryText(scopeDir, workflow string, changedPaths []string) string {
	argv := mutationCognitionRecoveryArgv(scopeDir, workflow, changedPaths)
	// Display is advisory; callers that return structured argv preserve it too.
	quoted := make([]string, len(argv))
	for index, arg := range argv {
		if strings.ContainsAny(arg, " \t\n\r\"") {
			quoted[index] = fmt.Sprintf("%q", arg)
		} else {
			quoted[index] = arg
		}
	}
	if len(argv) > 2 && argv[2] == "closeout-plan" {
		return strings.Join(quoted, " ") + "; supply one --changed-path per exact workflow-owned path, complete truthful agent fields, and execute returned apply_argv (which owns the receipt)"
	}
	if len(argv) > 2 && argv[2] == "archive-incompatible-store" {
		return strings.Join(quoted, " ") + ". Run from the project root to inspect the incompatible graph without mutation. Review the returned digest-bound archive_argv before archival, rebuild with the current runtime, and resume this workflow's exact closeout. Quick may use its explicit mark-dirty fallback with a sealed current source binding while graph repair remains outstanding."
	}
	return strings.Join(quoted, " ") + "; consume exact inspect repair_argv/replay_argv; keep the workflow active until its own receipt allows close"
}
