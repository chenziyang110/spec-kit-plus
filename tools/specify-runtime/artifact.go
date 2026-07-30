package main

import (
	"bufio"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

type ArtifactService struct {
	projectRoot           string
	afterArtifactMkdirAll func()
}

type ArtifactPrepareRequest struct {
	FeatureID string
	Kind      string
	Path      string
}

type ArtifactSubmitRequest struct {
	LeaseID string
	Content any
}

type ArtifactShowRequest struct {
	FeatureID   string
	Kind        string
	Path        string
	View        string
	JSONPointer string
	Section     string
	Limit       int
}

type artifactLease struct {
	ID            string `json:"id"`
	CanonicalPath string `json:"canonical_path"`
	TargetExists  bool   `json:"target_exists"`
	TargetSHA256  string `json:"target_sha256"`
	Used          bool   `json:"used"`
	CreatedAt     string `json:"created_at,omitempty"`
	ExpiresAt     string `json:"expires_at,omitempty"`
}

const artifactLeaseTTL = 30 * 60

// Expanded reads are agent-facing output. Keep them bounded so a single show
// call cannot accidentally inject a large state file into model context.
const maxArtifactExpandedViewBytes = 128 * 1024

func NewArtifactService(projectRoot string) *ArtifactService {
	return &ArtifactService{projectRoot: projectRoot}
}

func (service *ArtifactService) Prepare(request ArtifactPrepareRequest) Envelope {
	canonicalPath, err := resolveArtifactPath(request.FeatureID, request.Kind, request.Path)
	if err != nil {
		env := NewEnvelope("invalid", "invalid artifact request")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	metadata, ok := LookupArtifactType(canonicalPath)
	if !ok {
		env := NewEnvelope("invalid", "workflow artifact type is not registered")
		env.Blockers = append(env.Blockers, "register the artifact type and its owning CLI before creating or changing this path")
		env.Data["canonical_path"] = canonicalPath
		return env
	}
	if !artifactTypeAllows(metadata, "prepare") || (!artifactTypeAllows(metadata, "submit") && !artifactTypeAllows(metadata, "patch")) {
		env := NewEnvelope("invalid", "workflow artifact is owned by a specialized CLI")
		env.Blockers = append(env.Blockers, fmt.Sprintf("%s may be changed only through %s", canonicalPath, metadata.Owner))
		env.Data["canonical_path"] = canonicalPath
		env.Data["type_id"] = metadata.TypeID
		env.Data["owner"] = metadata.Owner
		env.Data["allowed_operations"] = metadata.Operations
		return env
	}
	target, err := secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	targetExists, targetSHA256, err := snapshotArtifactTarget(target)
	if err != nil {
		env := NewEnvelope("blocked", "artifact target cannot be inspected")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	leaseID, err := newLeaseID()
	if err != nil {
		env := NewEnvelope("error", "failed to create artifact lease")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	lease := artifactLease{
		ID:            leaseID,
		CanonicalPath: canonicalPath,
		TargetExists:  targetExists,
		TargetSHA256:  targetSHA256,
		CreatedAt:     nowUTC().Format(time.RFC3339),
		ExpiresAt:     nowUTC().Add(time.Duration(artifactLeaseTTL) * time.Second).Format(time.RFC3339),
	}
	if err := service.writeLease(lease); err != nil {
		env := NewEnvelope("error", "failed to create artifact lease")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "artifact lease prepared")
	env.Data["lease_id"] = lease.ID
	env.Data["canonical_path"] = canonicalPath
	env.Data["target_exists"] = lease.TargetExists
	env.Data["target_sha256"] = lease.TargetSHA256
	if artifactTypeAllows(metadata, "submit") {
		env.NextArgv = []string{"specify-runtime", "artifact", "submit", "--lease", lease.ID, "--content", "<inline-payload>"}
	} else {
		env.NextArgv = []string{"specify-runtime", "artifact", "patch", "--lease", lease.ID, "<patch-mode>"}
	}
	return env
}

func (service *ArtifactService) Submit(request ArtifactSubmitRequest) Envelope {
	return service.submit(request, false)
}

func (service *ArtifactService) submit(request ArtifactSubmitRequest, allowAcceptanceRecovery bool) Envelope {
	lease, claimPath, err := service.claimLease(request.LeaseID)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		if lease.Used && lease.CanonicalPath != "" {
			env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		}
		return env
	}
	// claimLease durably consumes the lease before any content or target work, so
	// every later exit remains one-use, including validation and stale-target failures.
	metadata, ok := LookupArtifactType(lease.CanonicalPath)
	recoveryAllowed := allowAcceptanceRecovery && ok && metadata.TypeID == "feature-human-acceptance"
	if !ok || (!artifactTypeAllows(metadata, "submit") && !recoveryAllowed) {
		env := NewEnvelope("invalid", "workflow artifact is not generic-submit writable")
		if ok {
			env.Blockers = append(env.Blockers, fmt.Sprintf("%s may be changed only through %s", lease.CanonicalPath, metadata.Owner))
			env.Data["type_id"] = metadata.TypeID
			env.Data["owner"] = metadata.Owner
		} else {
			env.Blockers = append(env.Blockers, "the leased path has no registered workflow artifact owner")
		}
		return service.finishLease(lease, claimPath, env)
	}
	content, err := normalizeArtifactContent(request.Content)
	if err != nil {
		env := NewEnvelope("invalid", "artifact content is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	if err := validateArtifactContent(lease.CanonicalPath, content); err != nil {
		env := NewEnvelope("invalid", "artifact content is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	target, err := secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		env := NewEnvelope("error", "failed to create artifact parent directory")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	if service.afterArtifactMkdirAll != nil {
		service.afterArtifactMkdirAll()
	}
	target, err = secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	lockPath, err := service.artifactLockPath(lease.CanonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lock path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	releaseLock, err := filelock.Acquire(lockPath)
	if err != nil {
		env := NewEnvelope("error", "failed to acquire artifact write lock")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	defer releaseLock()
	target, err = secureProjectPath(service.projectRoot, lease.CanonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	currentExists, currentSHA256, err := snapshotArtifactTarget(target)
	if err != nil {
		env := NewEnvelope("blocked", "artifact target cannot be inspected")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	if currentExists != lease.TargetExists || currentSHA256 != lease.TargetSHA256 {
		env := NewEnvelope("blocked", "artifact target changed after lease preparation")
		env.Blockers = append(env.Blockers, "prepare a new lease from the current canonical artifact before submitting")
		env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
		return service.finishLease(lease, claimPath, env)
	}
	if err := atomicWriteFile(target, content, 0o644); err != nil {
		env := NewEnvelope("error", "failed to write canonical artifact")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	env := NewEnvelope("ok", "canonical artifact submitted")
	env.Data["canonical_path"] = lease.CanonicalPath
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
	return service.finishLease(lease, claimPath, env)
}

func snapshotArtifactTarget(path string) (bool, string, error) {
	raw, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return false, "", nil
	}
	if err != nil {
		return false, "", err
	}
	digest := sha256.Sum256(raw)
	return true, hex.EncodeToString(digest[:]), nil
}

func (service *ArtifactService) artifactLockPath(canonicalPath string) (string, error) {
	digest := sha256.Sum256([]byte(canonicalPath))
	relative := filepath.ToSlash(filepath.Join(
		".specify",
		"runtime",
		"locks",
		"artifacts",
		hex.EncodeToString(digest[:])+".lock",
	))
	path, err := secureProjectPath(service.projectRoot, relative)
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return "", err
	}
	return secureProjectPath(service.projectRoot, relative)
}

func (service *ArtifactService) Show(request ArtifactShowRequest) Envelope {
	view := strings.TrimSpace(request.View)
	if view == "" {
		view = "summary"
	}
	if view != "summary" && view != "full" {
		env := NewEnvelope("invalid", "artifact view is invalid")
		env.Blockers = append(env.Blockers, fmt.Sprintf("unknown view %q; expected summary or full", request.View))
		return env
	}
	canonicalPath, err := resolveArtifactPath(request.FeatureID, request.Kind, request.Path)
	if err != nil {
		env := NewEnvelope("invalid", "invalid artifact request")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	metadata, ok := LookupArtifactType(canonicalPath)
	if !ok || !artifactTypeAllows(metadata, "show") {
		env := NewEnvelope("invalid", "workflow artifact type is not registered for reading")
		env.Blockers = append(env.Blockers, "use artifact registry to discover supported artifact types and owner commands")
		env.Data["canonical_path"] = canonicalPath
		return env
	}
	target, err := secureProjectPath(service.projectRoot, canonicalPath)
	if err != nil {
		env := NewEnvelope("blocked", "artifact path safety check failed")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	raw, err := os.ReadFile(target)
	if err != nil {
		env := NewEnvelope("blocked", "canonical artifact is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "canonical artifact read")
	env.Data["canonical_path"] = canonicalPath
	env.Data["bytes"] = len(raw)
	env.Data["sha256"] = fmt.Sprintf("%x", sha256.Sum256(raw))
	env.Data["lines"] = strings.Count(string(raw), "\n") + 1
	env.Data["type_id"] = metadata.TypeID
	env.Data["owner"] = metadata.Owner
	env.Data["role"] = metadata.Role
	if request.Path != "" {
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "full"}
	} else {
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--feature", request.FeatureID, "--kind", request.Kind, "--view", "full"}
	}
	if hasArtifactQuery(request) {
		queryResult, err := artifactQueryResult(canonicalPath, raw, request)
		if err != nil {
			env := NewEnvelope("invalid", "artifact query is invalid")
			env.Blockers = append(env.Blockers, err.Error())
			return env
		}
		if artifactExpandedOutputBytes(queryResult) > maxArtifactExpandedViewBytes {
			return blockOversizedArtifactRead(env, canonicalPath, request, "query result")
		}
		env.Data["query_result"] = queryResult
		if request.JSONPointer != "" {
			env.Data["json_pointer"] = request.JSONPointer
		}
		if request.Section != "" {
			env.Data["section"] = request.Section
		}
		if request.Limit > 0 {
			env.Data["limit"] = request.Limit
		}
	} else if view == "full" {
		if len(raw) > maxArtifactExpandedViewBytes {
			return blockOversizedArtifactRead(env, canonicalPath, request, "full view")
		}
		env.Data["content"] = string(raw)
	} else {
		addArtifactSummary(env.Data, canonicalPath, raw)
		if len(raw) > maxArtifactExpandedViewBytes {
			env.Data["full_view_requires_targeted_query"] = true
			env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--limit", "50"}
		}
	}
	return env
}

func artifactExpandedOutputBytes(value any) int {
	if text, ok := value.(string); ok {
		return len([]byte(text))
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return maxArtifactExpandedViewBytes + 1
	}
	return len(raw)
}

func blockOversizedArtifactRead(env Envelope, canonicalPath string, request ArtifactShowRequest, outputKind string) Envelope {
	env.Status = "blocked"
	env.Summary = "artifact output exceeds the bounded agent read limit"
	env.Blockers = append(env.Blockers,
		fmt.Sprintf("%s exceeds %d bytes; use summary view and a narrower JSON pointer or Markdown section with --limit", outputKind, maxArtifactExpandedViewBytes),
	)
	env.Data["max_expanded_view_bytes"] = maxArtifactExpandedViewBytes
	delete(env.Data, "content")
	delete(env.Data, "query_result")
	if request.JSONPointer != "" || request.Section != "" {
		next := []string{"specify-runtime", "artifact", "show", "--path", canonicalPath}
		if request.JSONPointer != "" {
			next = append(next, "--json-pointer", request.JSONPointer)
		}
		if request.Section != "" {
			next = append(next, "--section", request.Section)
		}
		next = append(next, "--limit", "25")
		env.NextArgv = next
	} else {
		env.NextArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "summary"}
	}
	env.ShowArgv = append([]string(nil), env.NextArgv...)
	return env
}

func resolveArtifactPath(featureID, kind, requestedPath string) (string, error) {
	if strings.TrimSpace(requestedPath) != "" {
		return registeredArtifactPath(requestedPath)
	}
	return canonicalArtifactPath(featureID, kind)
}

func canonicalArtifactPath(featureID, kind string) (string, error) {
	if !safeSegment(featureID) {
		return "", fmt.Errorf("feature id %q must be a safe path segment", featureID)
	}
	if !safeSegment(kind) {
		return "", fmt.Errorf("artifact kind %q must be a safe path segment", kind)
	}
	extension := ".json"
	if kind == "spec" {
		extension = ".md"
	}
	return registeredArtifactPath(fmt.Sprintf(".specify/features/%s/%s%s", featureID, kind, extension))
}

var registeredArtifactRoots = []string{
	".planning/debug/",
	".planning/quick/",
	".specify/design/",
	".specify/discussions/",
	".specify/features/",
	".specify/memory/",
	".specify/prd/",
	".specify/prd-runs/",
	".specify/teams/",
	".specify/worker-results/",
	"specs/",
}

var registeredRootArtifacts = map[string]bool{
	"DESIGN.md": true,
}

var registeredArtifactExtensions = map[string]bool{
	".css":     true,
	".csv":     true,
	".go":      true,
	".gql":     true,
	".graphql": true,
	".html":    true,
	".js":      true,
	".jsx":     true,
	".json":    true,
	".jsonl":   true,
	".md":      true,
	".ndjson":  true,
	".proto":   true,
	".ps1":     true,
	".py":      true,
	".scss":    true,
	".sh":      true,
	".sql":     true,
	".txt":     true,
	".ts":      true,
	".tsx":     true,
	".toml":    true,
	".xml":     true,
	".yaml":    true,
	".yml":     true,
}

func registeredArtifactPath(requestedPath string) (string, error) {
	trimmed := strings.TrimSpace(requestedPath)
	if trimmed == "" || filepath.IsAbs(trimmed) || filepath.VolumeName(trimmed) != "" {
		return "", fmt.Errorf("artifact path must be project-relative")
	}
	normalized := filepath.ToSlash(filepath.Clean(filepath.FromSlash(trimmed)))
	if normalized == "." || normalized == ".." || strings.HasPrefix(normalized, "../") {
		return "", fmt.Errorf("artifact path must stay inside the project")
	}
	if registeredRootArtifacts[normalized] {
		return normalized, nil
	}
	allowedRoot := false
	for _, root := range registeredArtifactRoots {
		if strings.HasPrefix(normalized, root) && len(normalized) > len(root) {
			allowedRoot = true
			break
		}
	}
	if !allowedRoot {
		return "", fmt.Errorf("artifact path %q is outside registered workflow roots", normalized)
	}
	basename := filepath.Base(normalized)
	if strings.HasPrefix(basename, ".") {
		return "", fmt.Errorf("hidden workflow artifacts are runtime-owned and cannot be registered")
	}
	if strings.EqualFold(basename, "workflow.json") {
		return "", fmt.Errorf("workflow.json is owned by specify-runtime workflow")
	}
	extension := strings.ToLower(filepath.Ext(normalized))
	if !registeredArtifactExtensions[extension] {
		return "", fmt.Errorf("artifact path %q has an unregistered content type", normalized)
	}
	return normalized, nil
}

func safeSegment(value string) bool {
	if value == "" || len(value) > 128 || strings.TrimSpace(value) != value || strings.Contains(value, "..") {
		return false
	}
	for index, char := range value {
		isAlphaNumeric := char >= 'a' && char <= 'z' || char >= 'A' && char <= 'Z' || char >= '0' && char <= '9'
		if isAlphaNumeric || index > 0 && (char == '-' || char == '_' || char == '.') {
			continue
		}
		return false
	}
	return true
}

var nowUTC = func() time.Time {
	return time.Now().UTC()
}

func normalizeArtifactContent(content any) ([]byte, error) {
	switch value := content.(type) {
	case []byte:
		return append([]byte(nil), value...), nil
	case string:
		return []byte(value), nil
	case json.RawMessage:
		if !json.Valid(value) {
			return nil, fmt.Errorf("JSON artifact content is malformed")
		}
		return append([]byte(nil), value...), nil
	default:
		raw, err := json.Marshal(value)
		if err != nil {
			return nil, err
		}
		return raw, nil
	}
}

func validateArtifactContent(canonicalPath string, content []byte) error {
	if len(content) == 0 {
		return fmt.Errorf("artifact content must not be empty")
	}
	switch strings.ToLower(filepath.Ext(canonicalPath)) {
	case ".json":
		if !json.Valid(content) {
			return fmt.Errorf("JSON artifact content is malformed")
		}
	case ".jsonl", ".ndjson":
		scanner := bufio.NewScanner(strings.NewReader(string(content)))
		line := 0
		for scanner.Scan() {
			line++
			raw := strings.TrimSpace(scanner.Text())
			if raw != "" && !json.Valid([]byte(raw)) {
				return fmt.Errorf("JSON line %d is malformed", line)
			}
		}
		if err := scanner.Err(); err != nil {
			return err
		}
	}
	return nil
}

func addArtifactSummary(data map[string]any, canonicalPath string, raw []byte) {
	switch strings.ToLower(filepath.Ext(canonicalPath)) {
	case ".json":
		var payload any
		if err := json.Unmarshal(raw, &payload); err != nil {
			return
		}
		object, ok := payload.(map[string]any)
		if !ok {
			return
		}
		keys := make([]string, 0, len(object))
		for key := range object {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		if len(keys) > 24 {
			keys = keys[:24]
		}
		data["keys"] = keys
		signals := map[string]any{}
		for _, key := range []string{"version", "status", "stage", "revision", "gate_status", "next_command"} {
			if value, exists := object[key]; exists {
				signals[key] = value
			}
		}
		if len(signals) > 0 {
			data["signals"] = signals
		}
	case ".md":
		headings := []string{}
		scanner := bufio.NewScanner(strings.NewReader(string(raw)))
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if strings.HasPrefix(line, "#") {
				headings = append(headings, line)
				if len(headings) == 24 {
					break
				}
			}
		}
		data["headings"] = headings
	}
}

func (service *ArtifactService) leasePath(leaseID string) (string, error) {
	if !safeSegment(leaseID) {
		return "", fmt.Errorf("lease id %q must be a safe path segment", leaseID)
	}
	return secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "runtime", "leases", leaseID+".json")))
}

func (service *ArtifactService) writeLease(lease artifactLease) error {
	path, err := service.leasePath(lease.ID)
	if err != nil {
		return err
	}
	raw, err := json.MarshalIndent(lease, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return atomicWriteFile(path, append(raw, '\n'), 0o644)
}

func (service *ArtifactService) readLease(leaseID string) (artifactLease, error) {
	var lease artifactLease
	path, err := service.leasePath(leaseID)
	if err != nil {
		return lease, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return lease, err
	}
	if err := json.Unmarshal(raw, &lease); err != nil {
		return lease, err
	}
	if lease.ID != leaseID {
		return lease, fmt.Errorf("lease id does not match its record")
	}
	canonicalPath, err := registeredArtifactPath(lease.CanonicalPath)
	if err != nil || canonicalPath != lease.CanonicalPath {
		return lease, fmt.Errorf("lease canonical path is invalid")
	}
	return lease, nil
}

func (service *ArtifactService) claimLease(leaseID string) (artifactLease, string, error) {
	var lease artifactLease
	if _, err := service.leasePath(leaseID); err != nil {
		return lease, "", err
	}
	lockPath, err := secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(
		".specify", "runtime", "locks", "leases", leaseID+".lock",
	)))
	if err != nil {
		return lease, "", err
	}
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return lease, "", err
	}
	lockPath, err = secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(
		".specify", "runtime", "locks", "leases", leaseID+".lock",
	)))
	if err != nil {
		return lease, "", err
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return lease, "", err
	}
	defer release()
	lease, err = service.readLease(leaseID)
	if err != nil {
		return lease, "", err
	}
	if lease.Used {
		return lease, "", fmt.Errorf("artifact lease has already been claimed")
	}
	if lease.ExpiresAt != "" {
		expiresAt, parseErr := time.Parse(time.RFC3339, lease.ExpiresAt)
		if parseErr != nil {
			return lease, "", fmt.Errorf("artifact lease expiry is invalid")
		}
		if !expiresAt.After(nowUTC()) {
			lease.Used = true
			_ = service.writeLease(lease)
			return lease, "", fmt.Errorf("artifact lease has expired; prepare a new lease")
		}
	}
	lease.Used = true
	if err := service.writeLease(lease); err != nil {
		return artifactLease{}, "", fmt.Errorf("persist claimed lease: %w", err)
	}
	return lease, "", nil
}

func (service *ArtifactService) releaseLease(lease artifactLease, claimPath string) error {
	if claimPath == "" {
		return nil
	}
	if lease.ID == "" {
		return nil
	}
	if err := service.writeLease(lease); err != nil {
		return err
	}
	return os.Remove(claimPath)
}

func (service *ArtifactService) finishLease(lease artifactLease, claimPath string, env Envelope) Envelope {
	if lease.Used && env.Status != "ok" && len(env.NextArgv) == 0 && lease.CanonicalPath != "" {
		env.NextArgv = []string{"specify-runtime", "artifact", "prepare", "--path", lease.CanonicalPath}
	}
	if err := service.releaseLease(lease, claimPath); err != nil {
		env.Status = "error"
		env.Summary = "failed to persist artifact lease state"
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func newLeaseID() (string, error) {
	var bytes [16]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		return "", fmt.Errorf("create lease id: %w", err)
	}
	return hex.EncodeToString(bytes[:]), nil
}

var syncAtomicTempFile = func(file *os.File) error {
	return file.Sync()
}

func atomicWriteFile(path string, content []byte, perm os.FileMode) error {
	temp, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".tmp-*")
	if err != nil {
		return err
	}
	tempName := temp.Name()
	defer os.Remove(tempName)
	if _, err := temp.Write(content); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Chmod(perm); err != nil {
		_ = temp.Close()
		return err
	}
	if err := syncAtomicTempFile(temp); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	return replaceFile(tempName, path)
}
