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
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
	"unicode/utf8"

	contextpacket "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/context"
)

const quickShadowReadLimit = 128 * 1024

// contextShadow is the runtime-owned, read-only bridge, intentionally not yet
// registered as a public CLI command or consumed by generated workflows.
// Inputs select one existing workspace/item, never agent-authored state/hashes.
func (service quickService) contextShadow(workspace, itemID string) (contextpacket.QuickShadowReport, error) {
	return contextpacket.BuildQuickShadow(func() (contextpacket.QuickShadowSource, error) {
		return service.contextShadowSnapshot(workspace, itemID)
	})
}

func (service quickService) verifyContextShadow(workspace, itemID string, report contextpacket.QuickShadowReport) error {
	return contextpacket.VerifyQuickShadow(report, func() (contextpacket.QuickShadowSource, error) {
		return service.contextShadowSnapshot(workspace, itemID)
	})
}

func (service quickService) contextShadowSnapshot(workspace, itemID string) (contextpacket.QuickShadowSource, error) {
	zero := contextpacket.QuickShadowSource{}
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
	revision, err := quickShadowRevision(root)
	if err != nil {
		return zero, err
	}
	stateRef := filepath.ToSlash(filepath.Join(".planning", "quick", workspace, quickConfirmationFileName))
	before, err := readQuickShadowState(root, stateRef)
	if err != nil {
		return zero, err
	}
	if err := contextpacket.ValidateQuickShadowJSON(before); err != nil {
		return zero, err
	}
	// Decode the bounded captured bytes into the owning Quick type. Calling the
	// legacy loader here would reopen the file with an unbounded os.ReadFile,
	// breaking this diagnostic's read budget if a writer replaces it mid-read.
	var doc quickConfirmationDoc
	if err := json.Unmarshal(before, &doc); err != nil {
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
	after, err := readQuickShadowState(root, stateRef)
	if err != nil || !bytes.Equal(before, after) {
		return zero, fmt.Errorf("quick_shadow_source_changed: confirmation bytes changed")
	}
	currentRevision, err := quickShadowRevision(root)
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
	return contextpacket.QuickShadowSource{
		ProjectIdentity: quickShadowBytesHash([]byte("quick-shadow-project-v1\x00" + identityRoot)),
		Workspace:       workspace, ItemID: itemID, StatePath: stateRef,
		StateDigest: quickShadowBytesHash(before), SourceRevision: revision, OwnerPacket: rawPacket,
	}, nil
}

// This admits a diagnostic snapshot, not executable work. The legacy packet
// builder treats absent rows as pending but does not reject duplicate rows or
// every blocked/unknown selected status. Never turn that ambiguity into a
// runnable-looking shadow. No source state is changed to make admission pass.
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
	if status != "pending" && status != "in_progress" {
		return fmt.Errorf("quick_shadow_owner_blocked: selected item is not pending or in_progress")
	}
	if blocked := doc.Execution.BlockedDispatch; blocked != nil &&
		blocked.Status == "subagent-blocked" && (blocked.ItemID == "" || blocked.ItemID == selected) {
		return fmt.Errorf("quick_shadow_owner_blocked: dispatch requires recovery")
	}
	return nil
}

func readQuickShadowState(root, relative string) ([]byte, error) {
	filename, err := secureProjectPath(root, relative)
	if err != nil {
		return nil, err
	}
	before, err := os.Lstat(filename)
	if err != nil || !before.Mode().IsRegular() || before.Size() > quickShadowReadLimit {
		return nil, fmt.Errorf("quick_shadow_state_invalid: require a bounded regular file")
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
	return raw, nil
}

// A single local read-only Git invocation identifies BOTH the project and HEAD.
// Ambient GIT_DIR/config overrides cannot silently redirect the selected repo.
func quickShadowRevision(root string) (string, error) {
	ctx, cancel := stdcontext.WithTimeout(stdcontext.Background(), 5*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "--no-optional-locks", "-C", root,
		"rev-parse", "--show-toplevel", "--verify", "HEAD")
	cmd.WaitDelay = time.Second
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		if !strings.HasPrefix(strings.ToUpper(key), "GIT_") {
			cmd.Env = append(cmd.Env, entry)
		}
	}
	cmd.Env = append(cmd.Env, "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL="+os.DevNull,
		"GIT_TERMINAL_PROMPT=0", "GIT_NO_LAZY_FETCH=1")
	raw, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("quick_shadow_git_unavailable: require a local Git root with HEAD; no fallback identity")
	}
	lines := strings.Split(strings.TrimSpace(string(raw)), "\n")
	if len(lines) != 2 {
		return "", fmt.Errorf("quick_shadow_git_identity_invalid")
	}
	top, err := filepath.EvalSymlinks(strings.TrimSuffix(lines[0], "\r"))
	if err != nil {
		return "", err
	}
	same := filepath.Clean(top) == filepath.Clean(root)
	if runtime.GOOS == "windows" {
		same = strings.EqualFold(filepath.Clean(top), filepath.Clean(root))
	}
	if !same {
		return "", fmt.Errorf("quick_shadow_git_root_mismatch: do not bind a parent repository")
	}
	revision := strings.TrimSuffix(lines[1], "\r")
	decoded, err := hex.DecodeString(revision)
	if err != nil || (len(decoded) != 20 && len(decoded) != 32) || strings.ToLower(revision) != revision {
		return "", fmt.Errorf("quick_shadow_git_revision_invalid")
	}
	return revision, nil
}

func quickShadowBytesHash(raw []byte) string {
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}
