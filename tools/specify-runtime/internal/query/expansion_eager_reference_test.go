package query

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

// Frozen Expand owner from PR #136 at 01fa1425; only its name changes.
// This full-packet reference preserves IO, validation and nil/error behavior.
func expansionEagerReadReference(paths rt.Paths, input ExpandInput) (ExpandPayload, error) {
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
