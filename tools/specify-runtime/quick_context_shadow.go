package main

import (
	"bytes"
	stdcontext "context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"unicode/utf8"

	contextpacket "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/context"
)

const quickShadowReadLimit = 128 * 1024

// contextShadow is the compatibility wrapper for the read-only diagnostic.
// Internal callers can supply cancellation through the variant below.
// The public CLI uses the context-aware variant; no executor consumes its report.
// Inputs select one existing workspace/item, never agent-authored state/hashes.
func (service quickService) contextShadow(workspace, itemID string) (contextpacket.QuickShadowReport, error) {
	return service.contextShadowWithContext(stdcontext.Background(), workspace, itemID)
}

// Cancellation is cooperative between bounded reads and inherited by each Git
// child. Ordinary filesystem calls are not made asynchronously or force-killed.
func (service quickService) contextShadowWithContext(ctx stdcontext.Context, workspace, itemID string) (contextpacket.QuickShadowReport, error) {
	if ctx == nil {
		return contextpacket.QuickShadowReport{}, fmt.Errorf("quick_shadow_context_missing")
	}
	report, err := contextpacket.BuildQuickShadow(func() (contextpacket.QuickShadowSource, error) {
		return service.contextShadowSnapshotWithContext(ctx, workspace, itemID)
	})
	if ctx.Err() != nil {
		return contextpacket.QuickShadowReport{}, ctx.Err()
	}
	return report, err
}

func (service quickService) verifyContextShadow(workspace, itemID string, report contextpacket.QuickShadowReport) error {
	return service.verifyContextShadowWithContext(stdcontext.Background(), workspace, itemID, report)
}

func (service quickService) verifyContextShadowWithContext(ctx stdcontext.Context, workspace, itemID string, report contextpacket.QuickShadowReport) error {
	if ctx == nil {
		return fmt.Errorf("quick_shadow_context_missing")
	}
	if err := ctx.Err(); err != nil {
		return err
	}
	err := contextpacket.VerifyQuickShadow(report, func() (contextpacket.QuickShadowSource, error) {
		return service.contextShadowSnapshotWithContext(ctx, workspace, itemID)
	})
	if ctx.Err() != nil {
		return ctx.Err()
	}
	return err
}

func (service quickService) contextShadowSnapshot(workspace, itemID string) (contextpacket.QuickShadowSource, error) {
	return service.contextShadowSnapshotWithContext(stdcontext.Background(), workspace, itemID)
}

func (service quickService) contextShadowSnapshotWithContext(ctx stdcontext.Context, workspace, itemID string) (contextpacket.QuickShadowSource, error) {
	zero := contextpacket.QuickShadowSource{}
	if ctx == nil {
		return zero, fmt.Errorf("quick_shadow_context_missing")
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	if !utf8.ValidString(workspace) || strings.TrimSpace(workspace) != workspace || workspace == "" ||
		workspace == "." || workspace == ".." || strings.ContainsAny(workspace, "/\\:\x00\r\n") ||
		!quickWorkItemIDPattern.MatchString(itemID) {
		return zero, fmt.Errorf("quick_shadow_selection_invalid: select one exact workspace and Qn")
	}
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return zero, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return zero, err
	}
	revision, err := quickShadowRevisionWithContext(ctx, root)
	if err != nil {
		return zero, err
	}
	stateRef := filepath.ToSlash(filepath.Join(".planning", "quick", workspace, quickConfirmationFileName))
	before, err := readQuickShadowStateWithContext(ctx, root, stateRef)
	if err != nil {
		return zero, err
	}
	// Decode captured bytes through the strict shadow boundary, not the
	// unbounded legacy loader. Keep exact dynamic numbers and reject typed-field
	// aliases before they can overwrite confirmation or execution state.
	doc, err := decodeQuickShadowConfirmation(before)
	if err != nil {
		return zero, err
	}
	if doc.Schema != quickConfirmationSchema {
		return zero, fmt.Errorf("quick_shadow_schema_unsupported")
	}
	if doc.Workspace != "" && doc.Workspace != workspace {
		return zero, fmt.Errorf("quick_shadow_workspace_mismatch")
	}
	digest, err := computeQuickConfirmationDigest(doc.Decision)
	if err != nil || digest != doc.ConfirmationDigest {
		return zero, fmt.Errorf("quick_shadow_decision_digest_mismatch")
	}
	if err := validateQuickShadowSelection(&doc, itemID); err != nil {
		return zero, err
	}
	packet, ready, _, err := compileQuickWorkerPacket(&doc, itemID)
	if err != nil {
		return zero, err
	}
	if !ready || len(doc.Execution.Blockers) != 0 {
		return zero, fmt.Errorf("quick_shadow_owner_blocked: resume the existing Quick owner")
	}
	rawPacket, err := json.Marshal(packet)
	if err != nil {
		return zero, err
	}
	after, err := readQuickShadowStateWithContext(ctx, root, stateRef)
	if err != nil {
		return zero, err
	}
	if !bytes.Equal(before, after) {
		return zero, fmt.Errorf("quick_shadow_source_changed: confirmation bytes changed")
	}
	currentRevision, err := quickShadowRevisionWithContext(ctx, root)
	if err != nil {
		return zero, err
	}
	if currentRevision != revision {
		return zero, fmt.Errorf("quick_shadow_source_changed: Git revision changed")
	}
	identityRoot := filepath.Clean(root)
	if runtime.GOOS == "windows" {
		identityRoot = strings.ToLower(identityRoot)
	}
	if err := ctx.Err(); err != nil {
		return zero, err
	}
	return contextpacket.QuickShadowSource{
		ProjectIdentity: quickShadowBytesHash([]byte("quick-shadow-project-v1\x00" + identityRoot)),
		Workspace:       workspace, ItemID: itemID, StatePath: stateRef,
		StateDigest: quickShadowBytesHash(before), SourceRevision: revision, OwnerPacket: rawPacket,
	}, nil
}

// This admits a diagnostic snapshot, not executable work. The legacy packet
// builder treats absent rows as pending but does not reject duplicate rows or
// every blocked/unknown selected status. Never turn that ambiguity into a
// runnable-looking shadow. The owner marks newly unblocked successors ready.
// No source state is changed to make admission pass.
func validateQuickShadowSelection(doc *quickConfirmationDoc, selected string) error {
	ids := make(map[string]bool, len(doc.Decision.Items))
	for _, item := range doc.Decision.Items {
		if !quickWorkItemIDPattern.MatchString(item.ID) || ids[item.ID] {
			return fmt.Errorf("quick_shadow_item_missing_or_ambiguous")
		}
		ids[item.ID] = true
	}
	if !ids[selected] {
		return fmt.Errorf("quick_shadow_item_missing_or_ambiguous")
	}
	seen := make(map[string]bool, len(doc.Execution.WorkItemStatus))
	status := "pending" // Same default as the owning quickStatusMap.
	for _, row := range doc.Execution.WorkItemStatus {
		if !ids[row.WorkItemID] || seen[row.WorkItemID] {
			return fmt.Errorf("quick_shadow_execution_ambiguous: duplicate or unknown item row")
		}
		seen[row.WorkItemID] = true
		if row.WorkItemID == selected {
			status = row.Status
		}
	}
	if status != "pending" && status != "ready" && status != "in_progress" {
		return fmt.Errorf("quick_shadow_owner_blocked: selected item is not pending, ready or in_progress")
	}
	if blocked := doc.Execution.BlockedDispatch; blocked != nil &&
		blocked.Status == "subagent-blocked" && (blocked.ItemID == "" || blocked.ItemID == selected) {
		return fmt.Errorf("quick_shadow_owner_blocked: dispatch requires recovery")
	}
	return nil
}

func readQuickShadowState(root, relative string) ([]byte, error) {
	return readQuickShadowStateWithContext(stdcontext.Background(), root, relative)
}

func readQuickShadowStateWithContext(ctx stdcontext.Context, root, relative string) ([]byte, error) {
	if ctx == nil {
		return nil, fmt.Errorf("quick_shadow_context_missing")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	filename, err := secureProjectPath(root, relative)
	if err != nil {
		return nil, err
	}
	before, err := os.Lstat(filename)
	if err != nil || !before.Mode().IsRegular() || before.Size() > quickShadowReadLimit {
		return nil, fmt.Errorf("quick_shadow_state_invalid: require a bounded regular file")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("quick_shadow_state_unavailable: %w", err)
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() || !os.SameFile(before, info) || info.Size() > quickShadowReadLimit {
		return nil, fmt.Errorf("quick_shadow_state_invalid: require a bounded regular file")
	}
	raw, err := io.ReadAll(io.LimitReader(file, quickShadowReadLimit+1))
	if err != nil || len(raw) > quickShadowReadLimit {
		return nil, fmt.Errorf("quick_shadow_state_invalid: bounded read failed")
	}
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	return raw, nil
}

func quickShadowBytesHash(raw []byte) string {
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}
