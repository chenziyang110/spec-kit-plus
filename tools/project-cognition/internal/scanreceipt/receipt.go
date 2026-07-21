// Package scanreceipt binds a validated v2 scan generation to an exact set of
// canonical artifacts and source bytes. It is an integrity check, not an
// authorization signature against another process running as the same user.
package scanreceipt

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

const (
	WorkbenchProtocol = "map_scan_workbench.v2"
	ReceiptProtocol   = "map_scan_receipt.v2"
	receiptFileName   = "scan-receipt.json"
)

type workbenchIdentity struct {
	Protocol     string           `json:"protocol"`
	GenerationID string           `json:"generation_id"`
	ScanSetPath  string           `json:"scan_set_path"`
	Packets      []map[string]any `json:"packets"`
}

type Receipt struct {
	Protocol       string `json:"protocol"`
	GenerationID   string `json:"generation_id"`
	Readiness      string `json:"readiness"`
	ScanSetDigest  string `json:"scan_set_digest"`
	SourceDigest   string `json:"source_digest"`
	ArtifactDigest string `json:"artifact_digest"`
}

type Fingerprint struct {
	GenerationID   string
	ScanSetDigest  string
	SourceDigest   string
	ArtifactDigest string
}

type scanSetFile struct {
	Files []string `json:"files"`
}

// Create writes a receipt only for a v2 workbench. Legacy scan packages remain
// readable during the protocol rollout and continue to rely on validation.
func Create(paths rt.Paths, readiness string) (Receipt, bool, error) {
	return CreateExpected(paths, readiness, nil)
}

// CreateExpected seals only the exact fingerprint validated by the caller.
// A zero fingerprint is the sentinel for a legacy or absent workbench, so the
// comparison must run before returning required=false for the current state.
func CreateExpected(paths rt.Paths, readiness string, expected *Fingerprint) (Receipt, bool, error) {
	if strings.TrimSpace(readiness) != "scan_ready" {
		return Receipt{}, true, fmt.Errorf("scan receipt requires readiness scan_ready")
	}
	fingerprint, required, err := ComputeFingerprint(paths)
	if err != nil {
		return Receipt{}, required, err
	}
	if expected != nil && *expected != fingerprint {
		return Receipt{}, true, fmt.Errorf("scan artifacts changed while validate-scan was running; retry validation")
	}
	if !required {
		return Receipt{}, false, nil
	}
	receipt := Receipt{
		Protocol: ReceiptProtocol, GenerationID: fingerprint.GenerationID, Readiness: "scan_ready",
		ScanSetDigest: fingerprint.ScanSetDigest, SourceDigest: fingerprint.SourceDigest, ArtifactDigest: fingerprint.ArtifactDigest,
	}
	if err := writeJSONAtomic(filepath.Join(paths.RuntimeDir, receiptFileName), receipt); err != nil {
		return Receipt{}, true, err
	}
	return receipt, true, nil
}

// Verify checks that a v2 receipt still describes the exact canonical scan
// package. It returns required=false for legacy packages.
func Verify(paths rt.Paths) (bool, error) {
	_, required, err := VerifySnapshot(paths)
	return required, err
}

// VerifySnapshot returns the exact receipt that matched the current files so a
// caller can ensure the same snapshot existed before and after loading them.
func VerifySnapshot(paths rt.Paths) (Receipt, bool, error) {
	identity, required, err := readWorkbenchIdentity(paths)
	if err != nil || !required {
		return Receipt{}, required, err
	}
	receiptPath := filepath.Join(paths.RuntimeDir, receiptFileName)
	data, err := os.ReadFile(receiptPath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return Receipt{}, true, fmt.Errorf("scan-receipt.json is required for v2 scan artifacts; run validate-scan before build-from-scan")
		}
		return Receipt{}, true, fmt.Errorf("read scan-receipt.json: %w", err)
	}
	var receipt Receipt
	if err := json.Unmarshal(data, &receipt); err != nil {
		return Receipt{}, true, fmt.Errorf("parse scan-receipt.json: %w", err)
	}
	if receipt.Protocol != ReceiptProtocol || receipt.GenerationID != identity.GenerationID || receipt.Readiness != "scan_ready" {
		return Receipt{}, true, fmt.Errorf("scan-receipt.json identity is stale or incompatible; rerun validate-scan")
	}
	fingerprint, _, err := ComputeFingerprint(paths)
	if err != nil {
		return Receipt{}, true, err
	}
	if receipt.GenerationID != fingerprint.GenerationID || receipt.ScanSetDigest != fingerprint.ScanSetDigest || receipt.SourceDigest != fingerprint.SourceDigest || receipt.ArtifactDigest != fingerprint.ArtifactDigest {
		return Receipt{}, true, fmt.Errorf("scan-receipt.json is stale: canonical scan or source digest changed; rerun validate-scan")
	}
	return receipt, true, nil
}

func ComputeFingerprint(paths rt.Paths) (Fingerprint, bool, error) {
	identity, required, err := readWorkbenchIdentity(paths)
	if err != nil || !required {
		return Fingerprint{}, required, err
	}
	scanSetPath, err := resolveRepositoryPath(paths.Root, identity.ScanSetPath)
	if err != nil {
		return Fingerprint{}, true, fmt.Errorf("resolve canonical scan set: %w", err)
	}
	scanSetDigest, err := digestFile(scanSetPath)
	if err != nil {
		return Fingerprint{}, true, fmt.Errorf("digest canonical scan set: %w", err)
	}
	sourceDigest, err := digestScanSetSources(paths.Root, scanSetPath)
	if err != nil {
		return Fingerprint{}, true, fmt.Errorf("digest canonical scan source files: %w", err)
	}
	artifactDigest, err := canonicalArtifactDigest(paths)
	if err != nil {
		return Fingerprint{}, true, err
	}
	return Fingerprint{
		GenerationID: identity.GenerationID, ScanSetDigest: scanSetDigest,
		SourceDigest: sourceDigest, ArtifactDigest: artifactDigest,
	}, true, nil
}

func readWorkbenchIdentity(paths rt.Paths) (workbenchIdentity, bool, error) {
	queuePath := filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json")
	data, err := os.ReadFile(queuePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			_, receiptErr := os.Lstat(filepath.Join(paths.RuntimeDir, receiptFileName))
			if receiptErr == nil {
				return workbenchIdentity{}, true, fmt.Errorf("workbench/scan-queue.json is missing while scan-receipt.json exists")
			}
			if !errors.Is(receiptErr, os.ErrNotExist) {
				return workbenchIdentity{}, true, fmt.Errorf("inspect scan-receipt.json: %w", receiptErr)
			}
			return workbenchIdentity{}, false, nil
		}
		return workbenchIdentity{}, true, fmt.Errorf("read workbench/scan-queue.json identity: %w", err)
	}
	var identity workbenchIdentity
	if err := json.Unmarshal(data, &identity); err != nil {
		return workbenchIdentity{}, true, fmt.Errorf("parse workbench/scan-queue.json identity: %w", err)
	}
	if strings.TrimSpace(identity.Protocol) == "" && strings.TrimSpace(identity.GenerationID) == "" && strings.TrimSpace(identity.ScanSetPath) == "" && !hasV2Footprints(paths, identity.Packets) {
		return identity, false, nil
	}
	if identity.Protocol != WorkbenchProtocol {
		return identity, true, fmt.Errorf("scan workbench protocol %q is incompatible with %s", identity.Protocol, WorkbenchProtocol)
	}
	if strings.TrimSpace(identity.GenerationID) == "" || strings.TrimSpace(identity.ScanSetPath) == "" {
		return identity, true, fmt.Errorf("v2 scan workbench requires generation_id and scan_set_path")
	}
	return identity, true, nil
}

func hasV2Footprints(paths rt.Paths, packets []map[string]any) bool {
	if _, err := os.Lstat(filepath.Join(paths.RuntimeDir, receiptFileName)); err == nil {
		return true
	}
	for _, packet := range packets {
		for _, key := range []string{"attempt_id", "attempt_number", "checkpoint_path", "checkpoint_sequence", "effective_context_budget_tokens", "oversized"} {
			if _, ok := packet[key]; ok {
				return true
			}
		}
	}
	for _, dir := range []string{
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results"),
		filepath.Join(paths.RuntimeDir, "workbench", "checkpoints"),
	} {
		found := false
		_ = filepath.WalkDir(dir, func(path string, entry os.DirEntry, walkErr error) error {
			if walkErr != nil || entry.IsDir() || !strings.EqualFold(filepath.Ext(entry.Name()), ".json") {
				return nil
			}
			data, err := os.ReadFile(path)
			if err != nil {
				return nil
			}
			var header struct {
				Protocol string `json:"protocol"`
			}
			if json.Unmarshal(data, &header) == nil && header.Protocol == "map_scan_result.v2" {
				found = true
				return filepath.SkipAll
			}
			return nil
		})
		if found {
			return true
		}
	}
	return false
}

func canonicalArtifactDigest(paths rt.Paths) (string, error) {
	files := []string{
		filepath.Join(paths.RuntimeDir, "coverage.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"),
		filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"),
		filepath.Join(paths.RuntimeDir, "provisional", "claims.json"),
	}
	for _, dir := range []string{
		filepath.Join(paths.RuntimeDir, "evidence"),
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results"),
	} {
		if err := rejectSymlinksBelow(paths.RuntimeDir, dir); err != nil {
			return "", err
		}
		entries, err := os.ReadDir(dir)
		if err != nil {
			return "", fmt.Errorf("read canonical scan artifact directory %s: %w", filepath.Base(dir), err)
		}
		for _, entry := range entries {
			if !entry.IsDir() && strings.EqualFold(filepath.Ext(entry.Name()), ".json") {
				path := filepath.Join(dir, entry.Name())
				if err := rejectSymlinksBelow(paths.RuntimeDir, path); err != nil {
					return "", err
				}
				files = append(files, path)
			}
		}
	}
	sort.Strings(files)
	digest := sha256.New()
	for _, path := range files {
		if err := rejectSymlinksBelow(paths.RuntimeDir, path); err != nil {
			return "", err
		}
		rel, err := filepath.Rel(paths.Root, path)
		if err != nil {
			return "", err
		}
		if _, err := io.WriteString(digest, filepath.ToSlash(rel)+"\x00"); err != nil {
			return "", err
		}
		data, err := os.ReadFile(path)
		if err != nil {
			if errors.Is(err, os.ErrNotExist) {
				if _, writeErr := io.WriteString(digest, "<missing>\x00"); writeErr != nil {
					return "", writeErr
				}
				continue
			}
			return "", fmt.Errorf("read canonical scan artifact %s: %w", filepath.ToSlash(rel), err)
		}
		if _, err := digest.Write(data); err != nil {
			return "", err
		}
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil)), nil
}

func rejectSymlinksBelow(root string, target string) error {
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return err
	}
	targetAbs, err := filepath.Abs(target)
	if err != nil {
		return err
	}
	if !pathWithinRoot(rootAbs, targetAbs) {
		return fmt.Errorf("canonical scan artifact is outside the runtime directory")
	}
	rel, err := filepath.Rel(rootAbs, targetAbs)
	if err != nil {
		return err
	}
	current := rootAbs
	components := []string{"."}
	if rel != "." {
		components = strings.Split(rel, string(os.PathSeparator))
	}
	for _, component := range components {
		if component != "." {
			current = filepath.Join(current, component)
		}
		info, err := os.Lstat(current)
		if errors.Is(err, os.ErrNotExist) {
			return nil
		}
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("canonical scan artifact path contains a symbolic link: %s", current)
		}
	}
	return nil
}

func digestScanSetSources(root string, scanSetPath string) (string, error) {
	data, err := os.ReadFile(scanSetPath)
	if err != nil {
		return "", err
	}
	var scanSet scanSetFile
	if err := json.Unmarshal(data, &scanSet); err != nil {
		return "", fmt.Errorf("parse scan set: %w", err)
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	canonical := make([]string, 0, len(scanSet.Files))
	seen := map[string]bool{}
	for _, raw := range scanSet.Files {
		target, err := resolveRepositoryPath(rootAbs, raw)
		if err != nil {
			return "", fmt.Errorf("source path %q: %w", raw, err)
		}
		info, err := os.Stat(target)
		if err != nil {
			return "", fmt.Errorf("stat source path %q: %w", raw, err)
		}
		if !info.Mode().IsRegular() {
			return "", fmt.Errorf("source path %q is not a regular file", raw)
		}
		rel, err := filepath.Rel(rootAbs, target)
		if err != nil {
			return "", err
		}
		rel = filepath.ToSlash(rel)
		if seen[rel] {
			return "", fmt.Errorf("scan set repeats source path %q", rel)
		}
		seen[rel] = true
		canonical = append(canonical, rel)
	}
	sort.Strings(canonical)
	digest := sha256.New()
	for _, rel := range canonical {
		if _, err := io.WriteString(digest, rel+"\x00"); err != nil {
			return "", err
		}
		data, err := os.ReadFile(filepath.Join(rootAbs, filepath.FromSlash(rel)))
		if err != nil {
			return "", fmt.Errorf("read source path %s: %w", rel, err)
		}
		if _, err := digest.Write(data); err != nil {
			return "", err
		}
		if _, err := digest.Write([]byte{0}); err != nil {
			return "", err
		}
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil)), nil
}

func digestFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(digest[:]), nil
}

func resolveRepositoryPath(root string, value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("scan set path is empty")
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	target := filepath.FromSlash(value)
	if !filepath.IsAbs(target) {
		target = filepath.Join(rootAbs, target)
	}
	targetAbs, err := filepath.Abs(target)
	if err != nil {
		return "", err
	}
	if !pathWithinRoot(rootAbs, targetAbs) {
		return "", fmt.Errorf("scan set path is outside the repository")
	}
	resolvedRoot, err := filepath.EvalSymlinks(rootAbs)
	if err != nil {
		return "", fmt.Errorf("resolve repository root: %w", err)
	}
	resolvedTarget, err := filepath.EvalSymlinks(targetAbs)
	if err != nil {
		return "", fmt.Errorf("resolve scan set path: %w", err)
	}
	if !pathWithinRoot(resolvedRoot, resolvedTarget) {
		return "", fmt.Errorf("scan set path resolves outside the repository")
	}
	return targetAbs, nil
}

func pathWithinRoot(root string, target string) bool {
	rel, err := filepath.Rel(root, target)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator)) && !filepath.IsAbs(rel)
}

func writeJSONAtomic(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	temp, err := os.CreateTemp(filepath.Dir(path), ".scan-receipt-*")
	if err != nil {
		return err
	}
	tempPath := temp.Name()
	defer os.Remove(tempPath)
	if _, err := temp.Write(append(data, '\n')); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	if err := os.Remove(path); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	return os.Rename(tempPath, path)
}
