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
)

type ArtifactService struct {
	projectRoot string
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
	FeatureID string
	Kind      string
	Path      string
	View      string
}

type artifactLease struct {
	ID            string `json:"id"`
	CanonicalPath string `json:"canonical_path"`
	Used          bool   `json:"used"`
}

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
	leaseID, err := newLeaseID()
	if err != nil {
		env := NewEnvelope("error", "failed to create artifact lease")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	lease := artifactLease{
		ID:            leaseID,
		CanonicalPath: canonicalPath,
	}
	if err := service.writeLease(lease); err != nil {
		env := NewEnvelope("error", "failed to create artifact lease")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "artifact lease prepared")
	env.Data["lease_id"] = lease.ID
	env.Data["canonical_path"] = canonicalPath
	env.NextArgv = []string{"specify-runtime", "artifact", "submit", "--lease", lease.ID, "--content-file", "<path>"}
	return env
}

func (service *ArtifactService) Submit(request ArtifactSubmitRequest) Envelope {
	lease, claimPath, err := service.claimLease(request.LeaseID)
	if err != nil {
		env := NewEnvelope("blocked", "artifact lease is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	if lease.Used {
		env := NewEnvelope("blocked", "artifact lease has already been used")
		env.Blockers = append(env.Blockers, "prepare a new lease before submitting updated content")
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
	if err := atomicWriteFile(target, content, 0o644); err != nil {
		env := NewEnvelope("error", "failed to write canonical artifact")
		env.Blockers = append(env.Blockers, err.Error())
		return service.finishLease(lease, claimPath, env)
	}
	lease.Used = true
	env := NewEnvelope("ok", "canonical artifact submitted")
	env.Data["canonical_path"] = lease.CanonicalPath
	env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", lease.CanonicalPath, "--view", "summary"}
	return service.finishLease(lease, claimPath, env)
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
	if request.Path != "" {
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--path", canonicalPath, "--view", "full"}
	} else {
		env.ShowArgv = []string{"specify-runtime", "artifact", "show", "--feature", request.FeatureID, "--kind", request.Kind, "--view", "full"}
	}
	if view == "full" {
		env.Data["content"] = string(raw)
	} else {
		addArtifactSummary(env.Data, canonicalPath, raw)
	}
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
	return fmt.Sprintf(".specify/features/%s/%s%s", featureID, kind, extension), nil
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
	"specs/",
}

var registeredRootArtifacts = map[string]bool{
	"DESIGN.md": true,
}

var registeredArtifactExtensions = map[string]bool{
	".json":   true,
	".jsonl":  true,
	".md":     true,
	".ndjson": true,
	".toml":   true,
	".yaml":   true,
	".yml":    true,
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
	if filepath.Base(normalized) == "workflow.json" {
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
	path, err := service.leasePath(leaseID)
	if err != nil {
		return lease, "", err
	}
	claimPath := path + ".claimed"
	if err := os.Rename(path, claimPath); err != nil {
		return lease, "", err
	}
	raw, err := os.ReadFile(claimPath)
	if err != nil {
		return lease, claimPath, err
	}
	if err := json.Unmarshal(raw, &lease); err != nil {
		return lease, claimPath, err
	}
	if lease.ID != leaseID {
		return lease, claimPath, fmt.Errorf("lease id does not match its record")
	}
	canonicalPath, err := registeredArtifactPath(lease.CanonicalPath)
	if err != nil || canonicalPath != lease.CanonicalPath {
		return lease, claimPath, fmt.Errorf("lease canonical path is invalid")
	}
	return lease, claimPath, nil
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
	if err := temp.Close(); err != nil {
		return err
	}
	if err := os.Chmod(tempName, perm); err != nil {
		return err
	}
	return replaceFile(tempName, path)
}
