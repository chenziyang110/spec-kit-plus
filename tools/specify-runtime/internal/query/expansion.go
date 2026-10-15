package query

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const (
	ExpansionContractVersion             = 2
	defaultExpansionSection              = "related_paths"
	expansionRecommendedActionRerun      = "rerun_project_cognition_compass"
	expansionRefStaleBehavior            = "expand rejects non-current contracts as incompatible_expansion, rejects content or identity corruption as invalid_expansion, and returns stale_expansion when graph snapshot or runtime status changes, including same-generation updates"
	expansionStatusOK                    = "ok"
	expansionStatusMissingExpansion      = "missing_expansion"
	expansionStatusIncompatibleExpansion = "incompatible_expansion"
	expansionStatusInvalidExpansion      = "invalid_expansion"
	expansionStatusStaleExpansion        = "stale_expansion"
	expansionStatusMissingSection        = "missing_section"
	expansionCompassStateStaleExpansion  = "stale_expansion"
)

var expansionIDPattern = regexp.MustCompile(`^exp-[A-Za-z0-9._-]+$`)

type ExpansionBundle struct {
	ID                            string                          `json:"id"`
	ExpansionContractVersion      int                             `json:"expansion_contract_version"`
	NavigationSnapshot            store.NavigationSnapshot        `json:"navigation_snapshot"`
	StatusDigest                  string                          `json:"status_digest"`
	RecoveryBasis                 *ExpansionRecoveryBasis         `json:"recovery_basis,omitempty"`
	ClaimRetrievalContractVersion int                             `json:"claim_retrieval_contract_version"`
	ActiveGenerationID            string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion      int                             `json:"candidate_universe_version"`
	QueryFingerprint              string                          `json:"query_fingerprint"`
	Sections                      map[string]ExpansionSectionMeta `json:"sections"`
	SectionPayloads               map[string]any                  `json:"section_payloads"`
	CreatedAt                     string                          `json:"created_at"`
}

// Recovery publishes a new identity while retaining the exact conflicting file.
// The source path and its observed bytes are part of the new content identity.
type ExpansionRecoveryBasis struct {
	PreservedID   string `json:"preserved_id"`
	PreservedPath string `json:"preserved_path"`
	SHA256        string `json:"sha256"`
}

type ExpandInput struct {
	ID      string
	Section string
	Offset  int
}

type ExpandPayload struct {
	EpistemicContract             EpistemicContract               `json:"epistemic_contract"`
	ExpansionContractVersion      int                             `json:"expansion_contract_version"`
	ClaimRetrievalContractVersion int                             `json:"claim_retrieval_contract_version"`
	Status                        string                          `json:"status"`
	Readiness                     string                          `json:"readiness"`
	CompassState                  string                          `json:"compass_state"`
	ID                            string                          `json:"id,omitempty"`
	Section                       string                          `json:"section,omitempty"`
	Data                          any                             `json:"data,omitempty"`
	ActiveGenerationID            string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion      int                             `json:"candidate_universe_version"`
	QueryFingerprint              string                          `json:"query_fingerprint,omitempty"`
	AvailableSections             map[string]ExpansionSectionMeta `json:"available_sections,omitempty"`
	RecommendedNextAction         string                          `json:"recommended_next_action"`
	Errors                        []string                        `json:"errors,omitempty"`
	Warnings                      []string                        `json:"warnings,omitempty"`
	TotalCount                    int                             `json:"total_count,omitempty"`
	ReturnedCount                 int                             `json:"returned_count,omitempty"`
	Offset                        int                             `json:"offset,omitempty"`
	HasMore                       bool                            `json:"has_more,omitempty"`
	NextArgv                      []string                        `json:"next_argv,omitempty"`
}

// A successful claim page must disclose an exact zero denominator and terminal
// false. Other sections/refusals do not carry unrelated paging metadata.
func (payload ExpandPayload) MarshalJSON() ([]byte, error) {
	type plain ExpandPayload
	output := struct {
		plain
		TotalCount    *int  `json:"total_count,omitempty"`
		ReturnedCount *int  `json:"returned_count,omitempty"`
		Offset        *int  `json:"offset,omitempty"`
		HasMore       *bool `json:"has_more,omitempty"`
	}{plain: plain(payload)}
	if payload.Status == expansionStatusOK && payload.Section == "claim_evidence" {
		output.TotalCount, output.ReturnedCount = &payload.TotalCount, &payload.ReturnedCount
		output.Offset, output.HasMore = &payload.Offset, &payload.HasMore
	}
	return json.Marshal(output)
}

func writeExpansionBundle(paths rt.Paths, bundle ExpansionBundle) (ExpansionRef, error) {
	if bundle.ClaimRetrievalContractVersion != ClaimRetrievalContractVersion {
		return ExpansionRef{}, fmt.Errorf("claim retrieval contract version %d is unsupported; current runtime requires %d", bundle.ClaimRetrievalContractVersion, ClaimRetrievalContractVersion)
	}
	if bundle.CandidateUniverseVersion != CandidateUniverseVersion {
		return ExpansionRef{}, fmt.Errorf("candidate universe version %d is unsupported; current runtime requires %d", bundle.CandidateUniverseVersion, CandidateUniverseVersion)
	}
	if bundle.ExpansionContractVersion != ExpansionContractVersion {
		return ExpansionRef{}, fmt.Errorf("expansion contract version %d is unsupported; current runtime requires %d", bundle.ExpansionContractVersion, ExpansionContractVersion)
	}
	if !validNavigationBinding(bundle) || !validExpansionRecoveryBasis(paths, bundle.RecoveryBasis) {
		return ExpansionRef{}, fmt.Errorf("expansion requires a current graph snapshot and status binding")
	}
	if expectedID := expansionBundleID(bundle); bundle.ID != expectedID {
		return ExpansionRef{}, fmt.Errorf("expansion bundle id %q is invalid; current identity is %q", bundle.ID, expectedID)
	}
	bundlePath, err := expansionBundlePath(paths, bundle.ID)
	if err != nil {
		return ExpansionRef{}, err
	}
	if bundle.CreatedAt == "" {
		bundle.CreatedAt = deterministicExpansionCreatedAt(bundle.QueryFingerprint)
	}
	if bundle.SectionPayloads == nil {
		bundle.SectionPayloads = map[string]any{}
	}
	bundle.Sections = expansionSectionMeta(bundle.SectionPayloads)
	if err := checkExpansionPath(paths, bundlePath, true); err != nil {
		return ExpansionRef{}, err
	}
	data, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return ExpansionRef{}, fmt.Errorf("encode expansion bundle: %w", err)
	}
	if err := publishExpansion(bundlePath, append(data, '\n')); err != nil {
		var conflict *expansionContentConflict
		if bundle.RecoveryBasis != nil || !errors.As(err, &conflict) {
			return ExpansionRef{}, fmt.Errorf("write expansion bundle: %w", err)
		}
		relative, relErr := filepath.Rel(paths.Root, bundlePath)
		if relErr != nil {
			return ExpansionRef{}, relErr
		}
		bundle.RecoveryBasis = &ExpansionRecoveryBasis{PreservedID: bundle.ID, PreservedPath: filepath.ToSlash(relative), SHA256: conflict.digest}
		bundle.ID = expansionBundleID(bundle)
		// Exactly one recovery level is allowed. A conflict at this new identity
		// remains an error; never overwrite or build an unbounded alias chain.
		ref, recoveryErr := writeExpansionBundle(paths, bundle)
		if recoveryErr != nil {
			return ExpansionRef{}, recoveryErr
		}
		retained, readErr := readStableExpansion(bundlePath)
		if readErr != nil || expansionBytesDigest(retained) != conflict.digest {
			return ExpansionRef{}, fmt.Errorf("preserved expansion changed during recovery at %s; refusing reference", bundlePath)
		}
		return ref, nil
	}
	return ExpansionRef{
		ID:                            bundle.ID,
		ExpansionContractVersion:      ExpansionContractVersion,
		NavigationDigest:              bundle.NavigationSnapshot.Digest,
		RecoveryBasis:                 bundle.RecoveryBasis,
		ClaimRetrievalContractVersion: bundle.ClaimRetrievalContractVersion,
		ActiveGenerationID:            bundle.ActiveGenerationID,
		CandidateUniverseVersion:      bundle.CandidateUniverseVersion,
		QueryFingerprint:              bundle.QueryFingerprint,
		AvailableSections:             bundle.Sections,
		StaleBehavior:                 expansionRefStaleBehavior,
	}, nil
}

func Expand(paths rt.Paths, input ExpandInput) (ExpandPayload, error) {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return ExpandPayload{}, err
	}
	section := strings.TrimSpace(input.Section)
	if section == "" {
		section = defaultExpansionSection
	}
	if input.Offset < 0 || (input.Offset != 0 && section != "claim_evidence") {
		return ExpandPayload{}, fmt.Errorf("expand offset requires a nonnegative claim_evidence page")
	}
	requestedID := strings.TrimSpace(input.ID)
	bundlePath, err := expansionBundlePath(paths, requestedID)
	if err != nil {
		return missingExpansionPayload(status, requestedID, section), nil
	}
	if err := checkExpansionPath(paths, bundlePath, false); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return missingExpansionPayload(status, requestedID, section), nil
		}
		return invalidExpansionPayload(requestedID), nil
	}
	data, err := readStableExpansion(bundlePath)
	if errors.Is(err, os.ErrNotExist) {
		return missingExpansionPayload(status, requestedID, section), nil
	}
	if err != nil {
		return ExpandPayload{}, fmt.Errorf("read expansion bundle: %w", err)
	}
	var bundle ExpansionBundle
	if !json.Valid(data) {
		return invalidExpansionPayload(requestedID), nil
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := decoder.Decode(&bundle); err != nil {
		return invalidExpansionPayload(requestedID), nil
	}
	if expansionBundleIncompatible(bundle) {
		return incompatibleExpansionPayload(requestedID), nil
	}
	if expansionBundleInvalid(bundle, requestedID) || !validExpansionRecoveryBasis(paths, bundle.RecoveryBasis) {
		return invalidExpansionPayload(requestedID), nil
	}
	available := expansionSectionMeta(bundle.SectionPayloads)
	if bundle.ActiveGenerationID != status.ActiveGenerationID {
		return staleExpansionPayload(bundle, available), nil
	}
	if agreement, exists := runtimegate.CheckExisting(paths); !exists || agreement.Status != "ok" {
		return staleExpansionPayload(bundle, available), nil
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return ExpandPayload{}, err
	}
	defer st.Close()
	read, err := st.BeginNavigationRead(context.Background())
	if err != nil {
		return ExpandPayload{}, err
	}
	defer read.Close()
	if read.Snapshot != bundle.NavigationSnapshot || navigationStatusDigest(status) != bundle.StatusDigest {
		return staleExpansionPayload(bundle, available), nil
	}
	if err := validateNavigationRead(paths, status, read); err != nil {
		return staleExpansionPayload(bundle, available), nil
	}
	payload, ok := bundle.SectionPayloads[section]
	if !ok {
		return ExpandPayload{
			EpistemicContract:             NewEpistemicContract(),
			ExpansionContractVersion:      ExpansionContractVersion,
			ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
			Status:                        expansionStatusMissingSection,
			Readiness:                     status.Readiness,
			CompassState:                  expansionStatusMissingSection,
			ID:                            bundle.ID,
			Section:                       section,
			ActiveGenerationID:            bundle.ActiveGenerationID,
			CandidateUniverseVersion:      CandidateUniverseVersion,
			QueryFingerprint:              bundle.QueryFingerprint,
			AvailableSections:             available,
			RecommendedNextAction:         expansionRecommendedActionRerun,
			Errors:                        []string{"missing_section:" + section},
		}, nil
	}
	totalCount, returnedCount := 0, 0
	hasMore := false
	var nextArgv []string
	if section == "claim_evidence" {
		index, hasIndex := bundle.SectionPayloads["claim_evidence_index"].(map[string]any)
		if !hasIndex {
			return incompatibleExpansionPayload(requestedID), nil
		}
		if hasIndex {
			count, ok := index["total_count"].(json.Number)
			if !ok {
				return invalidExpansionPayload(requestedID), nil
			}
			expectedCount, countErr := count.Int64()
			if countErr != nil || expectedCount < 0 {
				return invalidExpansionPayload(requestedID), nil
			}
			if int64(input.Offset) > expectedCount {
				return ExpandPayload{}, fmt.Errorf("claim evidence offset exceeds total_count")
			}
			values, ok := index["node_ids"].([]any)
			if !ok || len(values) > maxCompassLanes {
				return invalidExpansionPayload(requestedID), nil
			}
			nodeIDs := []string{}
			seen := map[string]bool{}
			for _, id := range values {
				value, ok := id.(string)
				if !ok || value == "" || seen[value] {
					return invalidExpansionPayload(requestedID), nil
				}
				nodeIDs = append(nodeIDs, value)
				seen[value] = true
			}
			page, err := st.ClaimEvidencePageForNodeIDs(context.Background(), nodeIDs, input.Offset, maxExpansionClaimSignals)
			if err != nil {
				return ExpandPayload{}, err
			}
			if int64(page.TotalCount) != expectedCount {
				return invalidExpansionPayload(requestedID), nil
			}
			if err := validateNavigationRead(paths, status, read); err != nil {
				return staleExpansionPayload(bundle, available), nil
			}
			encoded, err := json.Marshal(claimSignals(page.Records, maxExpansionClaimSignals, maxExpansionEvidenceRefs))
			if err != nil {
				return ExpandPayload{}, err
			}
			decoder := json.NewDecoder(bytes.NewReader(encoded))
			decoder.UseNumber()
			if err := decoder.Decode(&payload); err != nil {
				return ExpandPayload{}, err
			}
			totalCount, returnedCount = page.TotalCount, len(page.Records)
			hasMore = input.Offset+returnedCount < totalCount
			if hasMore {
				nextArgv = []string{"specify-runtime", "cognition", "expand", "--id", bundle.ID, "--section", "claim_evidence", "--offset", strconv.Itoa(input.Offset + returnedCount), "--format", "json"}
			}
		}
	}
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
		ExpansionContractVersion:      ExpansionContractVersion,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		Status:                        expansionStatusOK,
		Readiness:                     status.Readiness,
		CompassState:                  compassStateUsableWithReview,
		ID:                            bundle.ID,
		Section:                       section,
		Data:                          payload,
		ActiveGenerationID:            bundle.ActiveGenerationID,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              bundle.QueryFingerprint,
		AvailableSections:             available,
		RecommendedNextAction:         compassRecommendedActionUseReads,
		TotalCount:                    totalCount,
		ReturnedCount:                 returnedCount,
		Offset:                        input.Offset,
		HasMore:                       hasMore,
		NextArgv:                      nextArgv,
	}, nil
}

func expansionBundlePath(paths rt.Paths, id string) (string, error) {
	id = strings.TrimSpace(id)
	if !expansionIDPattern.MatchString(id) {
		return "", fmt.Errorf("invalid expansion id %q", id)
	}
	dir := filepath.Join(paths.RuntimeDir, "workbench", "expansions")
	path := filepath.Join(dir, id+".json")
	absDir, err := filepath.Abs(dir)
	if err != nil {
		return "", err
	}
	absPath, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(absDir, absPath)
	if err != nil {
		return "", err
	}
	if rel == "." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) || rel == ".." || filepath.IsAbs(rel) {
		return "", fmt.Errorf("expansion path escapes runtime dir")
	}
	return path, nil
}

func staleExpansionPayload(bundle ExpansionBundle, available map[string]ExpansionSectionMeta) ExpandPayload {
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
		ExpansionContractVersion:      ExpansionContractVersion,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		Status:                        expansionStatusStaleExpansion,
		Readiness:                     rt.ReviewReadiness,
		CompassState:                  expansionCompassStateStaleExpansion,
		ID:                            bundle.ID,
		ActiveGenerationID:            bundle.ActiveGenerationID,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              bundle.QueryFingerprint,
		AvailableSections:             available,
		RecommendedNextAction:         expansionRecommendedActionRerun,
		Warnings:                      []string{"stale_expansion"},
	}
}

func incompatibleExpansionPayload(id string) ExpandPayload {
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
		ExpansionContractVersion:      ExpansionContractVersion,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		Status:                        expansionStatusIncompatibleExpansion,
		Readiness:                     rt.ReviewReadiness,
		CompassState:                  expansionStatusIncompatibleExpansion,
		ID:                            id,
		RecommendedNextAction:         expansionRecommendedActionRerun,
		Errors:                        []string{expansionStatusIncompatibleExpansion},
	}
}

func invalidExpansionPayload(id string) ExpandPayload {
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
		ExpansionContractVersion:      ExpansionContractVersion,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		Status:                        expansionStatusInvalidExpansion,
		Readiness:                     rt.ReviewReadiness,
		CompassState:                  expansionStatusInvalidExpansion,
		ID:                            id,
		RecommendedNextAction:         expansionRecommendedActionRerun,
		Errors:                        []string{expansionStatusInvalidExpansion},
	}
}

func missingExpansionPayload(status rt.Status, id, section string) ExpandPayload {
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
		ExpansionContractVersion:      ExpansionContractVersion,
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		Status:                        expansionStatusMissingExpansion,
		Readiness:                     status.Readiness,
		CompassState:                  expansionStatusMissingExpansion,
		ID:                            id,
		Section:                       section,
		RecommendedNextAction:         expansionRecommendedActionRerun,
		Errors:                        []string{"missing_expansion"},
	}
}

func expansionBundleIncompatible(bundle ExpansionBundle) bool {
	return bundle.ExpansionContractVersion != ExpansionContractVersion ||
		bundle.ClaimRetrievalContractVersion != ClaimRetrievalContractVersion ||
		bundle.CandidateUniverseVersion != CandidateUniverseVersion
}

func expansionBundleInvalid(bundle ExpansionBundle, requestedID string) bool {
	requestedID = strings.TrimSpace(requestedID)
	if strings.TrimSpace(bundle.QueryFingerprint) == "" || !validNavigationBinding(bundle) {
		return true
	}
	if bundle.ID != requestedID {
		return true
	}
	return bundle.ID != expansionBundleID(bundle)
}

func expansionBundleID(bundle ExpansionBundle) string {
	bundle.ID = ""
	if bundle.CreatedAt == "" {
		bundle.CreatedAt = deterministicExpansionCreatedAt(bundle.QueryFingerprint)
	}
	if bundle.SectionPayloads == nil {
		bundle.SectionPayloads = map[string]any{}
	}
	bundle.Sections = expansionSectionMeta(bundle.SectionPayloads)
	// The writer may hold structs; the reader holds decoded JSON maps. Canonical
	// JSON with preserved numbers makes both representations bind the same data.
	data, err := json.Marshal(bundle)
	if err != nil {
		return ""
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	var canonical any
	if err := decoder.Decode(&canonical); err != nil {
		return ""
	}
	canonicalBundle := canonical.(map[string]any)
	canonicalBundle["sections"] = expansionSectionMeta(canonicalBundle["section_payloads"].(map[string]any))
	data, err = json.Marshal(canonical)
	if err != nil {
		return ""
	}
	sum := sha256.Sum256(data)
	return fmt.Sprintf("exp-%x", sum[:])
}

// IsRuntimeExpansionSnapshot reports whether rel names a query-owned expansion
// snapshot whose content still satisfies the expansion identity contract. It is
// intentionally read-only and permits stale historical bundles, while rejecting
// arbitrary workbench files, wrong IDs, malformed JSON, and content/path drift.
func IsRuntimeExpansionSnapshot(paths rt.Paths, rel string) bool {
	clean := filepath.ToSlash(strings.TrimSpace(rel))
	if !strings.HasPrefix(clean, ".specify/project-cognition/workbench/expansions/") || !strings.HasSuffix(clean, ".json") {
		return false
	}
	id := strings.TrimSuffix(filepath.Base(clean), ".json")
	wantPath, err := expansionBundlePath(paths, id)
	if err != nil {
		return false
	}
	abs, err := filepath.Abs(filepath.Join(paths.Root, filepath.FromSlash(clean)))
	if err != nil {
		return false
	}
	wantAbs, err := filepath.Abs(wantPath)
	if err != nil || abs != wantAbs {
		return false
	}
	raw, err := readStableExpansion(wantAbs)
	if err != nil {
		return false
	}
	var bundle ExpansionBundle
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&bundle); err != nil {
		return false
	}
	return !expansionBundleInvalid(bundle, id) && validExpansionRecoveryBasis(paths, bundle.RecoveryBasis)
}

func validNavigationBinding(bundle ExpansionBundle) bool {
	return bundle.ActiveGenerationID != "" &&
		bundle.NavigationSnapshot.GenerationID == bundle.ActiveGenerationID &&
		validNavigationDigest(bundle.NavigationSnapshot.Digest) && validNavigationDigest(bundle.StatusDigest)
}

func validNavigationDigest(value string) bool {
	return len(value) == len("sha256:")+64 && strings.HasPrefix(value, "sha256:") &&
		strings.Trim(value[len("sha256:"):], "0123456789abcdef") == ""
}

func validExpansionRecoveryBasis(paths rt.Paths, basis *ExpansionRecoveryBasis) bool {
	if basis == nil {
		return true
	}
	path, err := expansionBundlePath(paths, basis.PreservedID)
	if err != nil || !validNavigationDigest(basis.SHA256) {
		return false
	}
	relative, err := filepath.Rel(paths.Root, path)
	return err == nil && basis.PreservedPath == filepath.ToSlash(relative)
}

func expansionBytesDigest(data []byte) string {
	sum := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", sum[:])
}

type expansionContentConflict struct{ digest string }

func (err *expansionContentConflict) Error() string {
	return "existing expansion identity has different content; refusing replacement"
}

// Check the opened file and pathname before/after two byte observations. A
// changing file cannot supply a trustworthy recovery basis or consumable data.
func readStableExpansion(path string) ([]byte, error) {
	before, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !before.Mode().IsRegular() {
		return nil, fmt.Errorf("expansion is not a regular immutable file")
	}
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	data, err := io.ReadAll(file)
	if err != nil {
		return nil, err
	}
	if err := validateExpansionFileRead(path, file, before, data); err != nil {
		return nil, err
	}
	return data, nil
}

func validateExpansionFileRead(path string, file *os.File, before os.FileInfo, data []byte) error {
	if _, err := file.Seek(0, io.SeekStart); err != nil {
		return err
	}
	confirmed, err := io.ReadAll(file)
	if err != nil {
		return err
	}
	after, err := file.Stat()
	if err != nil {
		return err
	}
	current, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !current.Mode().IsRegular() || !os.SameFile(before, after) || !os.SameFile(after, current) ||
		before.Size() != after.Size() || after.Size() != current.Size() ||
		!before.ModTime().Equal(after.ModTime()) || !after.ModTime().Equal(current.ModTime()) ||
		!bytes.Equal(data, confirmed) {
		return fmt.Errorf("expansion changed during read at %s; rerun cognition compass", path)
	}
	return nil
}

func navigationStatusDigest(status rt.Status) string {
	data, _ := json.Marshal(status)
	sum := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", sum[:])
}

func validateNavigationRead(paths rt.Paths, status rt.Status, read *store.NavigationRead) error {
	ctx := context.Background()
	if err := read.Validate(ctx); err != nil {
		return err
	}
	if agreement, exists := runtimegate.CheckExisting(paths); !exists || agreement.Status != "ok" {
		return fmt.Errorf("project cognition agreement changed during navigation; rerun cognition compass")
	}
	// Reopen the current pathname as well as checking the pinned connection:
	// replacing a database cannot leave an old connection silently authoritative.
	current, err := store.OpenExisting(paths)
	if err != nil {
		return err
	}
	defer current.Close()
	snapshot, err := current.ReadNavigationSnapshot(ctx)
	if err != nil {
		return err
	}
	if snapshot != read.Snapshot {
		return fmt.Errorf("project cognition snapshot changed during navigation; rerun cognition compass")
	}
	after, err := rt.ReadStatus(paths)
	if err != nil {
		return err
	}
	if navigationStatusDigest(after) != navigationStatusDigest(status) {
		return fmt.Errorf("project cognition status changed during navigation; rerun cognition compass")
	}
	return read.Validate(ctx)
}

// Publish complete bytes without replacing a previously issued identity. A hard
// link installs the closed, synced temporary file atomically on supported local
// filesystems. Unsupported filesystems fail closed rather than exposing partial
// JSON or falling back to a rename that may overwrite another writer's result.
func publishExpansion(path string, data []byte) error {
	tmp, err := os.CreateTemp(filepath.Dir(path), ".expansion-*.tmp")
	if err != nil {
		return err
	}
	temporaryPath := tmp.Name()
	defer os.Remove(temporaryPath)
	if err := tmp.Chmod(0o644); err != nil {
		_ = tmp.Close()
		return err
	}
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Sync(); err != nil {
		_ = tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	if err := os.Link(temporaryPath, path); err != nil {
		if !errors.Is(err, os.ErrExist) {
			return fmt.Errorf("atomic expansion publication: %w", err)
		}
		existing, readErr := readStableExpansion(path)
		if readErr != nil {
			return readErr
		}
		if !bytes.Equal(existing, data) {
			return &expansionContentConflict{digest: expansionBytesDigest(existing)}
		}
	}
	return nil
}

func checkExpansionPath(paths rt.Paths, target string, create bool) error {
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return err
	}
	relative, err := filepath.Rel(root, target)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) || filepath.IsAbs(relative) {
		return fmt.Errorf("expansion path escapes project")
	}
	parts := strings.Split(relative, string(os.PathSeparator))
	current := root
	for index, part := range parts {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		last := index == len(parts)-1
		if errors.Is(err, os.ErrNotExist) && create {
			if last {
				return nil
			}
			if err := os.Mkdir(current, 0o755); err != nil && !errors.Is(err, os.ErrExist) {
				return err
			}
			info, err = os.Lstat(current)
		}
		if err != nil {
			return err
		}
		if info.Mode()&os.ModeSymlink != 0 || (!last && !info.IsDir()) || (last && !info.Mode().IsRegular()) {
			return fmt.Errorf("expansion path must not contain links or non-regular components")
		}
	}
	return nil
}

func deterministicExpansionCreatedAt(queryFingerprint string) string {
	queryFingerprint = strings.TrimSpace(queryFingerprint)
	if len(queryFingerprint) < 8 {
		return time.Unix(0, 0).UTC().Format(time.RFC3339)
	}
	seconds, err := strconv.ParseInt(queryFingerprint[:8], 16, 64)
	if err != nil {
		return time.Unix(0, 0).UTC().Format(time.RFC3339)
	}
	return time.Unix(seconds, 0).UTC().Format(time.RFC3339)
}

func expansionSectionMeta(payloads map[string]any) map[string]ExpansionSectionMeta {
	meta := map[string]ExpansionSectionMeta{}
	for section, payload := range payloads {
		if strings.TrimSpace(section) == "" {
			continue
		}
		meta[section] = ExpansionSectionMeta{
			State:          "available",
			EstimatedItems: estimatedExpansionItems(payload),
		}
	}
	return meta
}

func estimatedExpansionItems(value any) int {
	switch typed := value.(type) {
	case []string:
		return len(typed)
	case []CoverageDiagnostic:
		return len(typed)
	case []map[string]any:
		return len(typed)
	case []any:
		return len(typed)
	default:
		if value == nil {
			return 0
		}
		kind := reflect.ValueOf(value).Kind()
		if kind == reflect.Slice || kind == reflect.Array {
			return reflect.ValueOf(value).Len()
		}
		return 1
	}
}
