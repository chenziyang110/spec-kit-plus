package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	maxArtifactShowManyQueries      = 16
	maxArtifactShowManyOutputBytes  = 128 * 1024
	artifactShowManyOutputReserve   = 32 * 1024
	maxArtifactPatchBatchOperations = 32
)

type ArtifactShowManyRequest struct {
	Queries []ArtifactShowRequest `json:"queries"`
}

type ArtifactPatchBatchRequest struct {
	LeaseID    string                        `json:"lease_id"`
	Operations []ArtifactPatchBatchOperation `json:"operations"`
}

type ArtifactPatchBatchOperation struct {
	JSONPointer string         `json:"json_pointer,omitempty"`
	Value       any            `json:"value,omitempty"`
	Section     string         `json:"section,omitempty"`
	Content     string         `json:"content,omitempty"`
	Frontmatter map[string]any `json:"frontmatter,omitempty"`
}

var (
	validateArtifactBatchContent = validateArtifactContent
	writeArtifactBatchFile       = atomicWriteFile
)

func (service *ArtifactService) ShowMany(request ArtifactShowManyRequest) Envelope {
	if len(request.Queries) == 0 || len(request.Queries) > maxArtifactShowManyQueries {
		env := NewEnvelope("invalid", "artifact batch read request is invalid")
		env.Blockers = append(env.Blockers, fmt.Sprintf(
			"show-many requires between 1 and %d queries",
			maxArtifactShowManyQueries,
		))
		env.Data["max_queries"] = maxArtifactShowManyQueries
		return env
	}

	env := NewEnvelope("ok", "artifact batch read completed")
	itemBudget := maxArtifactShowManyOutputBytes - artifactShowManyOutputReserve
	itemBytes := 0
	okQueries := 0
	failedQueries := 0
	omittedQueries := 0
	for index, query := range request.Queries {
		shown := service.Show(query)
		item := artifactShowManyItem(index, shown)
		encoded, err := json.Marshal(item)
		if err != nil || itemBytes+len(encoded) > itemBudget {
			item = artifactShowManyOmittedItem(index, query)
			encoded, _ = json.Marshal(item)
			omittedQueries++
			failedQueries++
		} else if shown.Status == "ok" {
			okQueries++
		} else {
			failedQueries++
		}
		itemBytes += len(encoded)
		env.Items = append(env.Items, item)
	}

	env.Data["query_count"] = len(request.Queries)
	env.Data["ok_queries"] = okQueries
	env.Data["failed_queries"] = failedQueries
	env.Data["omitted_queries"] = omittedQueries
	env.Data["max_queries"] = maxArtifactShowManyQueries
	env.Data["max_output_bytes"] = maxArtifactShowManyOutputBytes
	if failedQueries > 0 {
		env.Status = "warn"
		env.Summary = "artifact batch read completed with item failures"
	}

	encoded, err := json.Marshal(env)
	if err == nil && len(encoded) <= maxArtifactShowManyOutputBytes {
		return env
	}

	// This fallback is defensive against unexpectedly large platform error text.
	// It keeps one compact status for every requested query without returning an
	// unbounded model-context payload.
	fallback := NewEnvelope("blocked", "artifact batch output exceeds the bounded agent read limit")
	fallback.Blockers = append(fallback.Blockers, fmt.Sprintf(
		"show-many output exceeds %d bytes; split the query batch or use narrower targeted reads",
		maxArtifactShowManyOutputBytes,
	))
	for index := range request.Queries {
		fallback.Items = append(fallback.Items, artifactShowManyOmittedItem(index, request.Queries[index]))
	}
	fallback.Data["query_count"] = len(request.Queries)
	fallback.Data["ok_queries"] = 0
	fallback.Data["failed_queries"] = len(request.Queries)
	fallback.Data["omitted_queries"] = len(request.Queries)
	fallback.Data["max_queries"] = maxArtifactShowManyQueries
	fallback.Data["max_output_bytes"] = maxArtifactShowManyOutputBytes
	return fallback
}

func artifactShowManyItem(index int, env Envelope) map[string]any {
	item := map[string]any{
		"index":   index,
		"status":  env.Status,
		"summary": env.Summary,
	}
	if len(env.Blockers) > 0 {
		item["blockers"] = env.Blockers
	}
	if len(env.Data) > 0 {
		item["data"] = env.Data
	}
	if len(env.NextArgv) > 0 {
		item["next_argv"] = env.NextArgv
	}
	if len(env.ShowArgv) > 0 {
		item["show_argv"] = env.ShowArgv
	}
	return item
}

func artifactShowManyOmittedItem(index int, request ArtifactShowRequest) map[string]any {
	data := map[string]any{
		"max_total_output_bytes": maxArtifactShowManyOutputBytes,
	}
	if canonicalPath, err := resolveArtifactPath(request.FeatureID, request.Kind, request.Path); err == nil {
		data["canonical_path"] = canonicalPath
	}
	return map[string]any{
		"index":   index,
		"status":  "blocked",
		"summary": "artifact query result omitted by the batch output limit",
		"blockers": []any{
			"split the query batch or use a narrower JSON pointer, Markdown section, or limit",
		},
		"data": data,
	}
}

func (service *ArtifactService) PatchBatch(request ArtifactPatchBatchRequest) Envelope {
	lease, claimPath, err := service.claimLease(request.LeaseID)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		if lease.Used && lease.CanonicalPath != "" {
			env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		}
		return env
	}

	metadata, ok := LookupArtifactType(lease.CanonicalPath)
	if !ok || !artifactTypeAllows(metadata, "patch") {
		env := NewEnvelope("invalid", "workflow artifact is not patchable through the generic CLI")
		if ok {
			env.Blockers = append(env.Blockers, fmt.Sprintf("%s may be changed only through %s", lease.CanonicalPath, metadata.Owner))
			env.Data["owner"] = metadata.Owner
		}
		return service.finishLease(lease, claimPath, env)
	}

	changedTargets, err := validateArtifactPatchBatchRequest(lease.CanonicalPath, request)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("invalid", err))
	}
	target, err := secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("blocked", err))
	}
	lockPath, err := service.artifactLockPath(lease.CanonicalPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("blocked", err))
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("error", err))
	}
	defer release()

	if metadata.TypeID == "ui-design-change-contract" {
		immutable, err := service.registeredDesignChangeImmutable(lease.CanonicalPath)
		if err != nil {
			return service.finishLease(lease, claimPath, artifactPatchBatchError("blocked", err))
		}
		if immutable {
			return service.finishLease(
				lease,
				claimPath,
				artifactPatchBatchError("blocked", fmt.Errorf("registered design change is immutable; create a new UD-* change and declare supersedes")),
			)
		}
	}

	currentExists, currentSHA256, err := snapshotArtifactTarget(target)
	if err != nil || currentExists != lease.TargetExists || currentSHA256 != lease.TargetSHA256 {
		if err == nil {
			err = fmt.Errorf("artifact target changed after lease preparation")
		}
		env := artifactPatchBatchError("blocked", err)
		env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
		return service.finishLease(lease, claimPath, env)
	}
	if !currentExists {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("blocked", fmt.Errorf("patch requires an existing artifact; scaffold or submit it first")))
	}

	raw, err := os.ReadFile(target)
	if err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("error", err))
	}
	updated := append([]byte(nil), raw...)
	for index, operation := range request.Operations {
		updated, err = patchArtifactContent(updated, operation.patchRequest())
		if err != nil {
			return service.finishLease(
				lease,
				claimPath,
				artifactPatchBatchError("invalid", fmt.Errorf("operation %d: %w", index, err)),
			)
		}
	}
	if err := validateArtifactBatchContent(lease.CanonicalPath, updated); err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("invalid", err))
	}
	if err := writeArtifactBatchFile(target, updated, 0o644); err != nil {
		return service.finishLease(lease, claimPath, artifactPatchBatchError("error", err))
	}

	afterDigest := sha256.Sum256(updated)
	env := NewEnvelope("ok", "canonical artifact patched atomically")
	env.Data["canonical_path"] = lease.CanonicalPath
	env.Data["before_sha256"] = lease.TargetSHA256
	env.Data["after_sha256"] = hex.EncodeToString(afterDigest[:])
	env.Data["bytes"] = len(updated)
	env.Data["operation_count"] = len(request.Operations)
	env.Data["changed_targets"] = changedTargets
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
	return service.finishLease(lease, claimPath, env)
}

func artifactPatchBatchError(status string, err error) Envelope {
	env := NewEnvelope(status, "artifact patch batch failed")
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func validateArtifactPatchBatchRequest(canonicalPath string, request ArtifactPatchBatchRequest) ([]map[string]any, error) {
	if len(request.Operations) == 0 || len(request.Operations) > maxArtifactPatchBatchOperations {
		return nil, fmt.Errorf("patch-batch requires between 1 and %d operations", maxArtifactPatchBatchOperations)
	}

	sections := map[string]int{}
	frontmatterKeys := map[string]int{}
	jsonPointers := []artifactBatchJSONPointer{}
	changedTargets := make([]map[string]any, 0, len(request.Operations))
	for index, operation := range request.Operations {
		patch := operation.patchRequest()
		if err := validateArtifactPatchRequest(canonicalPath, patch); err != nil {
			return nil, fmt.Errorf("operation %d: %w", index, err)
		}
		switch {
		case strings.TrimSpace(operation.JSONPointer) != "":
			pointer := artifactBatchJSONPointer{
				index:  index,
				raw:    operation.JSONPointer,
				tokens: artifactBatchPointerTokens(operation.JSONPointer),
			}
			for _, previous := range jsonPointers {
				if artifactBatchPointerConflict(previous.tokens, pointer.tokens) {
					return nil, fmt.Errorf(
						"operation %d target %q conflicts with operation %d target %q",
						index,
						operation.JSONPointer,
						previous.index,
						previous.raw,
					)
				}
			}
			jsonPointers = append(jsonPointers, pointer)
			changedTargets = append(changedTargets, map[string]any{
				"kind":   "json_pointer",
				"target": operation.JSONPointer,
			})
		case strings.TrimSpace(operation.Section) != "":
			target := normalizeMarkdownSectionTarget(operation.Section)
			if previous, exists := sections[target]; exists {
				return nil, fmt.Errorf(
					"operation %d Markdown section target %q conflicts with operation %d",
					index,
					operation.Section,
					previous,
				)
			}
			sections[target] = index
			changedTargets = append(changedTargets, map[string]any{
				"kind":   "section",
				"target": artifactBatchSectionLabel(operation.Section),
			})
		case operation.Frontmatter != nil:
			keys := make([]string, 0, len(operation.Frontmatter))
			for key := range operation.Frontmatter {
				if previous, exists := frontmatterKeys[key]; exists {
					return nil, fmt.Errorf(
						"operation %d frontmatter target %q conflicts with operation %d",
						index,
						key,
						previous,
					)
				}
				frontmatterKeys[key] = index
				keys = append(keys, key)
			}
			sort.Strings(keys)
			changedTargets = append(changedTargets, map[string]any{
				"kind":    "frontmatter",
				"targets": keys,
			})
		}
	}
	return changedTargets, nil
}

func (operation ArtifactPatchBatchOperation) patchRequest() ArtifactPatchRequest {
	return ArtifactPatchRequest{
		JSONPointer: operation.JSONPointer,
		Value:       operation.Value,
		Section:     operation.Section,
		Content:     operation.Content,
		Frontmatter: operation.Frontmatter,
	}
}

type artifactBatchJSONPointer struct {
	index  int
	raw    string
	tokens []string
}

func artifactBatchPointerTokens(pointer string) []string {
	if !strings.HasPrefix(pointer, "/") {
		return []string{pointer}
	}
	parts := strings.Split(pointer[1:], "/")
	for index, part := range parts {
		parts[index] = strings.ReplaceAll(strings.ReplaceAll(part, "~1", "/"), "~0", "~")
	}
	return parts
}

func artifactBatchPointerConflict(left, right []string) bool {
	limit := len(left)
	if len(right) < limit {
		limit = len(right)
	}
	for index := 0; index < limit; index++ {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func artifactBatchSectionLabel(section string) string {
	target := strings.TrimSpace(section)
	for strings.HasPrefix(target, "#") {
		target = strings.TrimSpace(strings.TrimPrefix(target, "#"))
	}
	return target
}
