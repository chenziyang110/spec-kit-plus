package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"
	"unicode/utf8"
)

// AssetKitPolicy enables an already installed, project-local AssetKit adapter.
// It never installs a skill or creates another asset ledger.
type AssetKitPolicy struct {
	Enabled        bool   `json:"enabled,omitempty"`
	Python         string `json:"python,omitempty"`
	TimeoutSeconds int    `json:"timeout_seconds,omitempty"`
	MaxOutputBytes int    `json:"max_output_bytes,omitempty"`
}

type AssetCatalogRequest struct {
	PolicyPath     string `json:"policy_path,omitempty"`
	Operation      string `json:"operation"`
	Enabled        bool   `json:"enabled,omitempty"`
	Python         string `json:"python,omitempty"`
	Query          string `json:"query,omitempty"`
	Reference      string `json:"reference,omitempty"`
	Path           string `json:"path,omitempty"`
	Use            string `json:"use,omitempty"`
	SourceKind     string `json:"source_kind,omitempty"`
	SourceRef      string `json:"source_ref,omitempty"`
	License        string `json:"license,omitempty"`
	ExpectRevision int    `json:"expect_revision,omitempty"`
	Since          string `json:"since,omitempty"`
	TimeoutSeconds int    `json:"timeout_seconds,omitempty"`
	MaxOutputBytes int    `json:"max_output_bytes,omitempty"`
}

// Catalog invokes only the four supported short AssetKit operations. Inputs
// remain individual argv entries; the launcher path is not caller-controlled.
func (s *AssetService) Catalog(request AssetCatalogRequest) Envelope {
	policy, err := s.LoadPolicy(request.PolicyPath)
	if err != nil {
		return assetCatalogFailure("invalid", "policy-invalid", err.Error(), false)
	}
	if !request.Enabled && !policy.AssetKit.Enabled {
		env := NewEnvelope("ok", "AssetKit adapter is disabled; no process was started")
		env.Data["adapter_status"] = "disabled"
		env.Data["executed"] = false
		return env
	}
	root, err := filepath.Abs(s.projectRoot)
	if err != nil {
		return assetCatalogFailure("invalid", "project-invalid", err.Error(), false)
	}
	for _, relative := range []string{".assets/ak.py", ".assets/config.json", ".assets/records", ".assets/cache", ".assets/.lock", ".assets/tmp"} {
		path, pathErr := secureProjectPath(root, relative)
		if pathErr != nil {
			return assetCatalogFailure("blocked", "adapter-unsafe", pathErr.Error(), false)
		}
		if relative != ".assets/ak.py" && relative != ".assets/config.json" && relative != ".assets/records" {
			continue
		}
		info, statErr := os.Stat(path)
		if statErr != nil {
			return assetCatalogFailure("blocked", "adapter-unavailable", fmt.Sprintf("Existing AssetKit project entry is unavailable: %s (%v); installation/bootstrap was not attempted", relative, statErr), false)
		}
		if (relative == ".assets/records" && !info.IsDir()) || (relative != ".assets/records" && !info.Mode().IsRegular()) {
			return assetCatalogFailure("blocked", "adapter-unavailable", "AssetKit entry has an unexpected file type: "+relative, false)
		}
	}
	maxBytes := request.MaxOutputBytes
	if maxBytes == 0 {
		maxBytes = policy.AssetKit.MaxOutputBytes
	}
	if maxBytes == 0 {
		maxBytes = 8192
	}
	seconds := request.TimeoutSeconds
	if seconds == 0 {
		seconds = policy.AssetKit.TimeoutSeconds
	}
	if seconds == 0 {
		seconds = 15
	}
	if maxBytes < 1024 || maxBytes > 65536 || seconds < 1 || seconds > 60 {
		return assetCatalogFailure("invalid", "adapter-limits-invalid", "max_output_bytes must be 1024..65536 and timeout_seconds must be 1..60", false)
	}
	baselineRef := request.Since
	if request.Operation == "check" {
		if len(request.Since) > 256 || !utf8.ValidString(request.Since) {
			return assetCatalogFailure("blocked", "adapter-baseline-invalid", "check requires an explicit Git commit reference of at most 256 bytes", false)
		}
		view := &assetReadView{service: s}
		if err := view.verifyGitRoot(); err != nil {
			return assetCatalogFailure("blocked", "adapter-baseline-invalid", "AssetKit check requires this project's Git worktree: "+err.Error(), false)
		}
		commit, err := view.resolveCommit(request.Since)
		if err != nil {
			return assetCatalogFailure("blocked", "adapter-baseline-invalid", "AssetKit check baseline does not resolve to an existing commit: "+err.Error(), false)
		}
		// Resolve once in the Go boundary. A branch moving before the Python
		// adapter starts cannot silently change the reviewed comparison baseline.
		request.Since = commit
	}
	argv, err := s.assetCatalogArgv(request, policy, maxBytes)
	if err != nil {
		return assetCatalogFailure("blocked", "adapter-request-invalid", err.Error(), false)
	}
	python := strings.TrimSpace(request.Python)
	if python == "" {
		python = strings.TrimSpace(policy.AssetKit.Python)
	}
	if python == "" {
		python = "python3"
	}
	if !filepath.IsAbs(python) && (strings.Contains(python, "/") || strings.Contains(python, string(filepath.Separator))) {
		candidate := filepath.Join(root, filepath.FromSlash(python))
		relative, pathErr := filepath.Rel(root, candidate)
		if pathErr != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			return assetCatalogFailure("blocked", "python-unavailable", "Relative Python paths must remain under the project; use an explicit absolute interpreter path for external environments", false)
		}
		// Virtual-environment interpreters may legitimately be symlinks. This
		// explicit executable choice is separate from asset/ledger path guards.
		python = candidate
	}
	interpreter, err := exec.LookPath(python)
	if err != nil {
		return assetCatalogFailure("blocked", "python-unavailable", fmt.Sprintf("Configured Python executable is unavailable: %s", python), false)
	}
	launcher, err := secureProjectPath(root, ".assets/ak.py")
	if err != nil {
		return assetCatalogFailure("blocked", "adapter-unsafe", err.Error(), false)
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(seconds)*time.Second)
	defer cancel()
	output := &assetCatalogCapture{limit: maxBytes, cancel: cancel}
	cmd := exec.CommandContext(ctx, interpreter, append([]string{"-B", "-S", launcher}, argv...)...)
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "PYTHONDONTWRITEBYTECODE=1", "PYTHONUTF8=1")
	cmd.Stdin = nil
	cmd.Stdout = assetCatalogWriter{capture: output}
	cmd.Stderr = assetCatalogWriter{capture: output, stderr: true}
	// Bound inherited pipe waits as well as the interpreter itself.
	cmd.WaitDelay = 500 * time.Millisecond
	runErr := cmd.Run()
	mutating := request.Operation == "put"
	if runErr != nil && cmd.ProcessState == nil {
		return assetCatalogFailure("blocked", "adapter-start-failed", "AssetKit process could not be started: "+runErr.Error(), false)
	}
	if output.overflow {
		return assetCatalogFailure("blocked", "adapter-output-limit", "AssetKit output exceeded the configured byte limit; the process was stopped", mutating)
	}
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return assetCatalogFailure("blocked", "adapter-timeout", "AssetKit exceeded the configured timeout; inspect its existing ledger before retrying a put", mutating)
	}
	var result map[string]any
	decodeErr := json.Unmarshal(output.stdout.Bytes(), &result)
	if decodeErr != nil || result == nil {
		env := assetCatalogFailure("blocked", "adapter-invalid-output", "AssetKit did not return one valid JSON object", mutating)
		if stderr := strings.TrimSpace(output.stderr.String()); stderr != "" {
			env.Data["adapter_stderr"] = stderr
		}
		return env
	}
	status := "ok"
	if ok, exists := result["ok"].(bool); runErr != nil || !exists || !ok {
		status = "blocked"
	}
	env := NewEnvelope(status, "AssetKit "+request.Operation+" returned a bounded response")
	env.Data["adapter_status"] = "executed"
	env.Data["executed"] = true
	env.Data["operation"] = request.Operation
	env.Data["adapter_result"] = result
	env.Data["data_is_untrusted"] = true
	env.Data["ledger_owner"] = "assetkit"
	env.Data["backend_interoperability"] = "installed-adapter-response-only"
	env.Data["may_update_assetkit_cache"] = true
	if request.Operation == "check" {
		env.Data["baseline_ref"] = baselineRef
		env.Data["baseline_commit"] = request.Since
	}
	if cmd.ProcessState != nil {
		env.Data["backend_exit_code"] = cmd.ProcessState.ExitCode()
	}
	if stderr := strings.TrimSpace(output.stderr.String()); stderr != "" {
		env.Data["adapter_stderr"] = stderr
	}
	if status != "ok" {
		env.Blockers = append(env.Blockers, map[string]any{"code": "adapter-rejected", "message": "AssetKit reported a failure; no automatic retry was attempted"})
		env.Data["mutation_may_have_occurred"] = mutating
	}
	return env
}

func (s *AssetService) assetCatalogArgv(request AssetCatalogRequest, policy AssetPolicy, maxBytes int) ([]string, error) {
	budget := 2048
	if request.Operation == "put" || request.Operation == "check" {
		budget = 1024
	}
	if budget > maxBytes {
		budget = maxBytes
	}
	argv := []string{request.Operation, "--budget=" + strconv.Itoa(budget)}
	bounded := func(value string, limit int) bool {
		return strings.TrimSpace(value) != "" && utf8.ValidString(value) && utf8.RuneCountInString(value) <= limit && !strings.ContainsRune(value, '\x00')
	}
	switch request.Operation {
	case "find":
		if !bounded(request.Query, 200) {
			return nil, fmt.Errorf("find requires a nonempty query of at most 200 characters")
		}
		// AssetKit's Python str.split additionally recognizes the four ASCII
		// information separators as whitespace; preserve its 12-keyword limit.
		terms := strings.FieldsFunc(request.Query, func(value rune) bool {
			return unicode.IsSpace(value) || (value >= 0x1c && value <= 0x1f)
		})
		if len(terms) > 12 {
			return nil, fmt.Errorf("find accepts at most 12 whitespace-separated keywords")
		}
		argv = append(argv, "--", request.Query)
	case "get":
		if !bounded(request.Reference, 1024) {
			return nil, fmt.Errorf("get requires an exact path, id, or short reference")
		}
		argv = append(argv, "--", request.Reference)
	case "put":
		if !bounded(request.Path, 1024) || !bounded(request.Use, 120) {
			return nil, fmt.Errorf("put requires one exact project path and a use of at most 120 characters")
		}
		classification, err := s.ClassifyPath(request.Path, policy)
		if err != nil {
			return nil, err
		}
		if classification.Protected || classification.Temporary || classification.Cache || classification.Kind != "media" || !classification.Compliant {
			return nil, fmt.Errorf("put accepts only compliant, retained ordinary media; %s is %s (protected=%t temporary=%t cache=%t compliant=%t)", request.Path, classification.Kind, classification.Protected, classification.Temporary, classification.Cache, classification.Compliant)
		}
		path, err := secureProjectPath(s.projectRoot, classification.Path)
		if err != nil {
			return nil, err
		}
		info, err := os.Stat(path)
		if err != nil || !info.Mode().IsRegular() {
			return nil, fmt.Errorf("put requires an existing regular media file: %s", request.Path)
		}
		argv = append(argv, "--use="+request.Use)
		if request.ExpectRevision < 0 {
			return nil, fmt.Errorf("expect_revision must be a positive integer when supplied")
		}
		if request.ExpectRevision > 0 {
			argv = append(argv, "--expect-revision="+strconv.Itoa(request.ExpectRevision))
		}
		if request.SourceKind != "" {
			switch request.SourceKind {
			case "unknown", "authored", "generated", "uploaded", "imported":
			default:
				return nil, fmt.Errorf("unsupported source_kind")
			}
			if request.SourceKind != "unknown" && !bounded(request.SourceRef, 1000) {
				return nil, fmt.Errorf("a known source_kind requires a source_ref")
			}
			argv = append(argv, "--source-kind="+request.SourceKind)
		}
		if request.SourceRef != "" {
			if !bounded(request.SourceRef, 1000) {
				return nil, fmt.Errorf("source_ref must contain at most 1000 characters")
			}
			argv = append(argv, "--source-ref="+request.SourceRef)
		}
		if request.License != "" {
			if !bounded(request.License, 160) {
				return nil, fmt.Errorf("license must contain at most 160 characters")
			}
			argv = append(argv, "--license="+request.License)
		}
		argv = append(argv, "--", classification.Path)
	case "check":
		if !bounded(request.Since, 256) || strings.HasPrefix(request.Since, "-") {
			return nil, fmt.Errorf("check requires an explicit real Git baseline in since")
		}
		argv = append(argv, "--since="+request.Since)
	default:
		return nil, fmt.Errorf("operation must be find, get, put, or check")
	}
	return argv, nil
}

func assetCatalogFailure(status, code, message string, mutationPossible bool) Envelope {
	env := NewEnvelope(status, message)
	env.Blockers = append(env.Blockers, map[string]any{"code": code, "message": message})
	env.Data["adapter_status"] = code
	env.Data["executed"] = code == "adapter-output-limit" || code == "adapter-timeout" || code == "adapter-invalid-output"
	env.Data["mutation_may_have_occurred"] = mutationPossible
	return env
}

type assetCatalogCapture struct {
	mu       sync.Mutex
	stdout   bytes.Buffer
	stderr   bytes.Buffer
	limit    int
	used     int
	overflow bool
	cancel   context.CancelFunc
}

type assetCatalogWriter struct {
	capture *assetCatalogCapture
	stderr  bool
}

func (w assetCatalogWriter) Write(payload []byte) (int, error) {
	w.capture.mu.Lock()
	defer w.capture.mu.Unlock()
	count := len(payload)
	remaining := w.capture.limit - w.capture.used
	if count > remaining {
		count = remaining
		w.capture.overflow = true
		w.capture.cancel()
	}
	if w.stderr {
		_, _ = w.capture.stderr.Write(payload[:count])
	} else {
		_, _ = w.capture.stdout.Write(payload[:count])
	}
	w.capture.used += count
	if count != len(payload) {
		return count, io.ErrShortWrite
	}
	return count, nil
}
