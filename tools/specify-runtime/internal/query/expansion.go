package query

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

const (
	defaultExpansionSection              = "related_paths"
	expansionRecommendedActionRerun      = "rerun_project_cognition_compass"
	expansionRefStaleBehavior            = "expand rejects non-current contracts as incompatible_expansion, rejects identity corruption as invalid_expansion, and returns stale_expansion only when the current active generation no longer matches"
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
	ClaimRetrievalContractVersion int                             `json:"claim_retrieval_contract_version"`
	ActiveGenerationID            string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion      int                             `json:"candidate_universe_version"`
	QueryFingerprint              string                          `json:"query_fingerprint"`
	Sections                      map[string]ExpansionSectionMeta `json:"sections"`
	SectionPayloads               map[string]any                  `json:"section_payloads"`
	CreatedAt                     string                          `json:"created_at"`
}

type ExpandInput struct {
	ID      string
	Section string
}

type ExpandPayload struct {
	EpistemicContract             EpistemicContract               `json:"epistemic_contract"`
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
}

func writeExpansionBundle(paths rt.Paths, bundle ExpansionBundle) (ExpansionRef, error) {
	if bundle.ClaimRetrievalContractVersion != ClaimRetrievalContractVersion {
		return ExpansionRef{}, fmt.Errorf("claim retrieval contract version %d is unsupported; current runtime requires %d", bundle.ClaimRetrievalContractVersion, ClaimRetrievalContractVersion)
	}
	if bundle.CandidateUniverseVersion != CandidateUniverseVersion {
		return ExpansionRef{}, fmt.Errorf("candidate universe version %d is unsupported; current runtime requires %d", bundle.CandidateUniverseVersion, CandidateUniverseVersion)
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
	if err := os.MkdirAll(filepath.Dir(bundlePath), 0o755); err != nil {
		return ExpansionRef{}, fmt.Errorf("create expansion bundle dir: %w", err)
	}
	data, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return ExpansionRef{}, fmt.Errorf("encode expansion bundle: %w", err)
	}
	if err := os.WriteFile(bundlePath, append(data, '\n'), 0o644); err != nil {
		return ExpansionRef{}, fmt.Errorf("write expansion bundle: %w", err)
	}
	return ExpansionRef{
		ID:                            bundle.ID,
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
	requestedID := strings.TrimSpace(input.ID)
	bundlePath, err := expansionBundlePath(paths, requestedID)
	if err != nil {
		return missingExpansionPayload(status, requestedID, section), nil
	}
	data, err := os.ReadFile(bundlePath)
	if errors.Is(err, os.ErrNotExist) {
		return missingExpansionPayload(status, requestedID, section), nil
	}
	if err != nil {
		return ExpandPayload{}, fmt.Errorf("read expansion bundle: %w", err)
	}
	var bundle ExpansionBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		return ExpandPayload{}, fmt.Errorf("decode expansion bundle: %w", err)
	}
	if expansionBundleIncompatible(bundle) {
		return incompatibleExpansionPayload(requestedID), nil
	}
	if expansionBundleInvalid(bundle, requestedID) {
		return invalidExpansionPayload(requestedID), nil
	}
	available := expansionSectionMeta(bundle.SectionPayloads)
	if bundle.ActiveGenerationID != status.ActiveGenerationID {
		return staleExpansionPayload(bundle, available), nil
	}
	payload, ok := bundle.SectionPayloads[section]
	if !ok {
		return ExpandPayload{
			EpistemicContract:             NewEpistemicContract(),
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
	return ExpandPayload{
		EpistemicContract:             NewEpistemicContract(),
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
	return bundle.ClaimRetrievalContractVersion != ClaimRetrievalContractVersion ||
		bundle.CandidateUniverseVersion != CandidateUniverseVersion
}

func expansionBundleInvalid(bundle ExpansionBundle, requestedID string) bool {
	requestedID = strings.TrimSpace(requestedID)
	if strings.TrimSpace(bundle.QueryFingerprint) == "" {
		return true
	}
	if bundle.ID != requestedID {
		return true
	}
	return bundle.ID != expansionBundleID(bundle)
}

func expansionBundleID(bundle ExpansionBundle) string {
	material := fmt.Sprintf("%s\x00%s\x00%d\x00%d", bundle.QueryFingerprint, bundle.ActiveGenerationID, bundle.ClaimRetrievalContractVersion, bundle.CandidateUniverseVersion)
	sum := sha256.Sum256([]byte(material))
	return fmt.Sprintf("exp-%x", sum[:12])
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
		return 1
	}
}
