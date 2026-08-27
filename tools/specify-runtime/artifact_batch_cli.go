package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
)

const maxArtifactBatchInputBytes = 256 * 1024

type artifactPatchBatchInput struct {
	Operations []ArtifactPatchBatchOperation `json:"operations"`
}

func decodeArtifactShowManyCLI(args []string, projectRoot string) (ArtifactShowManyRequest, Envelope, bool) {
	var request ArtifactShowManyRequest
	if !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
		return request, artifactBatchUsageEnvelope("show-many", "artifact show-many requires --input-json"), false
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "artifact show-many")
	if err != nil {
		return request, artifactBatchUsageEnvelope("show-many", err.Error()), false
	}
	if err := decodeStrictArtifactBatchJSON(raw, &request, "artifact show-many"); err != nil {
		return request, artifactBatchUsageEnvelope("show-many", err.Error()), false
	}
	return request, Envelope{}, true
}

func decodeArtifactPatchBatchCLI(args []string, projectRoot string) (ArtifactPatchBatchRequest, Envelope, bool) {
	var request ArtifactPatchBatchRequest
	leaseID := strings.TrimSpace(optionValue(args, "--lease", ""))
	if leaseID == "" || !hasFlag(args, "--input-json") || strings.TrimSpace(optionValue(args, "--input-json", "")) == "" {
		return request, artifactBatchUsageEnvelope("patch-batch", "artifact patch-batch requires --lease and --input-json"), false
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, "artifact patch-batch")
	if err != nil {
		return request, artifactBatchUsageEnvelope("patch-batch", err.Error()), false
	}
	var input artifactPatchBatchInput
	if err := decodeStrictArtifactBatchJSON(raw, &input, "artifact patch-batch"); err != nil {
		return request, artifactBatchUsageEnvelope("patch-batch", err.Error()), false
	}
	request.LeaseID = leaseID
	request.Operations = input.Operations
	return request, Envelope{}, true
}

func decodeStrictArtifactBatchJSON(raw []byte, target any, label string) error {
	if len(raw) == 0 {
		return fmt.Errorf("%s input must not be empty", label)
	}
	if len(raw) > maxArtifactBatchInputBytes {
		return fmt.Errorf("%s input exceeds %d bytes", label, maxArtifactBatchInputBytes)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return fmt.Errorf("%s --input-json is invalid: %w", label, err)
	}
	if err := ensureJSONEOF(decoder); err != nil {
		return fmt.Errorf("%s --input-json must contain exactly one object: %w", label, err)
	}
	return nil
}

func artifactBatchUsageEnvelope(operation, detail string) Envelope {
	env := NewEnvelope("usage-error", detail)
	env.ShowArgv = []string{"specify-runtime", "api", "show", "artifact." + operation, "--format", "json"}
	return env
}
