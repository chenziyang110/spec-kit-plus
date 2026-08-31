package update

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/delta"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

// ParseUpdatePayload shares the actual update parser with mutation admission.
// A repair may replace verification only; all other fields keep their semantics.
func ParseUpdatePayload(data []byte, verificationOverride []VerificationEvidence) (PayloadFileInput, error) {
	if verificationOverride != nil {
		if err := validateVerificationEvidence(verificationOverride); err != nil {
			return PayloadFileInput{}, err
		}
		var raw map[string]json.RawMessage
		if err := json.Unmarshal(data, &raw); err != nil || raw == nil {
			return PayloadFileInput{}, fmt.Errorf("update payload must be a JSON object")
		}
		verification, err := json.Marshal(verificationOverride)
		if err != nil {
			return PayloadFileInput{}, err
		}
		delete(raw, "verification_evidence")
		raw["verification"] = verification
		data, err = json.Marshal(raw)
		if err != nil {
			return PayloadFileInput{}, err
		}
	}
	payload, err := parsePayloadInput(data, "update payload")
	if err != nil {
		return PayloadFileInput{}, err
	}
	paths := append([]string{}, payload.ChangedPaths...)
	paths = append(paths, payload.ScopePaths...)
	paths = append(paths, payload.Boundary.WorkflowOwnedPaths...)
	if err := validateChangedPaths(normalizePaths(paths)); err != nil {
		return PayloadFileInput{}, err
	}
	if err := validateVerificationEvidence(payload.Verification); err != nil {
		return PayloadFileInput{}, err
	}
	return payload, nil
}

// ValidateVerificationEvidence checks each input row before normalization can
// discard empty rows or collapse duplicates.
func ValidateVerificationEvidence(values []VerificationEvidence) error {
	return validateVerificationEvidence(values)
}

// ValidateCommitRange uses the same read-only Git resolution as update itself.
func ValidateCommitRange(paths rt.Paths, commitRange string) error {
	_, err := gitDiffPathsFromCommitRange(paths.Root, commitRange)
	return err
}

// ValidateDeltaInput is pure: callers can bind exactly the bundle they checked.
func ValidateDeltaInput(bundle delta.Bundle, verificationOverride []VerificationEvidence) error {
	input := applyDeltaBundleInput(UpdateInput{}, bundle)
	if _, err := normalizePathChanges(input.PathChanges); err != nil {
		return err
	}
	paths := []string{}
	for _, event := range bundle.Events {
		paths = append(paths, event.ChangedPaths...)
		if verificationOverride == nil {
			for _, raw := range event.Verification {
				if strings.HasPrefix(strings.TrimSpace(raw), "{") {
					var evidence VerificationEvidence
					if err := json.Unmarshal([]byte(raw), &evidence); err != nil {
						return fmt.Errorf("invalid delta verification JSON: %w", err)
					}
				}
			}
		}
	}
	if err := validateChangedPaths(normalizePaths(paths)); err != nil {
		return err
	}
	if verificationOverride != nil {
		input.Verification = verificationOverride
	}
	return validateVerificationEvidence(input.Verification)
}
