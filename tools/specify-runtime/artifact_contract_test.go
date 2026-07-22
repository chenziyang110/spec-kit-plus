package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestArtifactPrepareSubmitAndProgressiveShow(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	prepared := service.Prepare(ArtifactPrepareRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
	})
	if prepared.Status != "ok" {
		t.Fatalf("prepare status = %q, want ok: %#v", prepared.Status, prepared)
	}
	leaseID, ok := prepared.Data["lease_id"].(string)
	if !ok || leaseID == "" {
		t.Fatalf("prepare lease_id = %#v, want non-empty string", prepared.Data["lease_id"])
	}
	if path := prepared.Data["canonical_path"]; path != ".specify/features/001-runtime/spec-contract.json" {
		t.Fatalf("prepare canonical_path = %#v", path)
	}
	if prepared.Data["target_exists"] != false || prepared.Data["target_sha256"] != "" {
		t.Fatalf("prepare target snapshot = %#v, want absent target", prepared.Data)
	}

	content := json.RawMessage(`{"schema_version":1,"status":"ready","target_need":"A deterministic runtime"}`)
	submitted := service.Submit(ArtifactSubmitRequest{
		LeaseID: leaseID,
		Content: content,
	})
	if submitted.Status != "ok" {
		t.Fatalf("submit status = %q, want ok: %#v", submitted.Status, submitted)
	}
	artifactPath := filepath.Join(projectRoot, ".specify", "features", "001-runtime", "spec-contract.json")
	stored, err := os.ReadFile(artifactPath)
	if err != nil {
		t.Fatalf("read canonical artifact: %v", err)
	}
	if !json.Valid(stored) {
		t.Fatalf("canonical artifact is not JSON: %q", stored)
	}

	summary := service.Show(ArtifactShowRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
		View:      "summary",
	})
	if summary.Status != "ok" {
		t.Fatalf("summary status = %q, want ok: %#v", summary.Status, summary)
	}
	if _, leaked := summary.Data["content"]; leaked {
		t.Fatalf("summary unexpectedly exposed full content: %#v", summary.Data)
	}
	if summary.ShowArgv[0] != "specify-runtime" {
		t.Fatalf("summary show_argv = %#v, want runtime expansion command", summary.ShowArgv)
	}

	full := service.Show(ArtifactShowRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
		View:      "full",
	})
	if full.Status != "ok" || full.Data["content"] == nil {
		t.Fatalf("full view = %#v, want content", full)
	}
}

func TestArtifactCLIUsesRegisteredProjectRelativePathAndCompactSummary(t *testing.T) {
	projectRoot := t.TempDir()
	var prepareOut, prepareErr bytes.Buffer
	code := Run([]string{
		"artifact", "prepare",
		"--project-root", projectRoot,
		"--path", "specs/001-runtime/spec.md",
	}, &prepareOut, &prepareErr, "test")
	if code != 0 {
		t.Fatalf("prepare code = %d stderr=%q stdout=%q", code, prepareErr.String(), prepareOut.String())
	}
	prepared := decodeJSONObject(t, prepareOut.Bytes())
	leaseID := requireObject(t, prepared, "data")["lease_id"].(string)
	contentPath := filepath.Join(projectRoot, "draft.md")
	if err := os.WriteFile(contentPath, []byte("# Feature\n\nstatus: ready\n\n## Requirements\n\n- FR-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	var submitOut bytes.Buffer
	code = Run([]string{
		"artifact", "submit",
		"--project-root", projectRoot,
		"--lease", leaseID,
		"--content-file", contentPath,
	}, &submitOut, &prepareErr, "test")
	if code != 0 {
		t.Fatalf("submit code = %d stderr=%q stdout=%q", code, prepareErr.String(), submitOut.String())
	}

	var showOut bytes.Buffer
	code = Run([]string{
		"artifact", "show",
		"--project-root", projectRoot,
		"--path", "specs/001-runtime/spec.md",
		"--view", "summary",
	}, &showOut, &prepareErr, "test")
	if code != 0 {
		t.Fatalf("show code = %d stderr=%q stdout=%q", code, prepareErr.String(), showOut.String())
	}
	shown := decodeJSONObject(t, showOut.Bytes())
	data := requireObject(t, shown, "data")
	if data["content"] != nil {
		t.Fatalf("summary leaked content: %#v", data)
	}
	if headings, ok := data["headings"].([]any); !ok || len(headings) == 0 {
		t.Fatalf("summary headings = %#v, want compact markdown outline", data["headings"])
	}
	if digest, ok := data["sha256"].(string); !ok || len(digest) != 64 {
		t.Fatalf("summary sha256 = %#v, want digest", data["sha256"])
	}
}

func TestArtifactPathRegistryRejectsSourceFiles(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	result := service.Prepare(ArtifactPrepareRequest{Path: "src/main.go"})
	if result.Status != "invalid" {
		t.Fatalf("prepare source path = %#v, want invalid", result)
	}
}

func TestArtifactPathRegistryCoversCanonicalWorkflowRootsOnly(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, path := range []string{
		".specify/design/design-state.md",
		".specify/prd/status.json",
		".specify/prd-runs/001-scan/workflow-state.md",
	} {
		if result := service.Prepare(ArtifactPrepareRequest{Path: path}); result.Status != "ok" {
			t.Fatalf("canonical path %q = %#v, want ok", path, result)
		}
	}
	for _, path := range []string{
		".specify/project-cognition/status.json",
		".specify/teams/runtime.json",
		".specify/templates/plan-template.md",
	} {
		if result := service.Prepare(ArtifactPrepareRequest{Path: path}); result.Status != "invalid" {
			t.Fatalf("specialized or immutable path %q = %#v, want invalid", path, result)
		}
	}
}

func TestArtifactLogicalAddressRejectsDotAndWhitespaceSegments(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, featureID := range []string{".", " ", "bad:name"} {
		result := service.Prepare(ArtifactPrepareRequest{FeatureID: featureID, Kind: "spec"})
		if result.Status != "invalid" {
			t.Fatalf("feature id %q = %#v, want invalid", featureID, result)
		}
	}
}

func TestArtifactNewLeaseCanAtomicallyReplaceExistingArtifact(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/spec.md"

	first := service.Prepare(ArtifactPrepareRequest{Path: path})
	firstResult := service.Submit(ArtifactSubmitRequest{
		LeaseID: first.Data["lease_id"].(string),
		Content: []byte("# First\n"),
	})
	if firstResult.Status != "ok" {
		t.Fatalf("first submit = %#v", firstResult)
	}
	second := service.Prepare(ArtifactPrepareRequest{Path: path})
	secondResult := service.Submit(ArtifactSubmitRequest{
		LeaseID: second.Data["lease_id"].(string),
		Content: []byte("# Second\n"),
	})
	if secondResult.Status != "ok" {
		t.Fatalf("replacement submit = %#v", secondResult)
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != "# Second\n" {
		t.Fatalf("stored = %q, want replacement", stored)
	}
}

func TestArtifactConcurrentLeasesRejectStaleSubmit(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/spec.md"

	first := service.Prepare(ArtifactPrepareRequest{Path: path})
	second := service.Prepare(ArtifactPrepareRequest{Path: path})
	if first.Status != "ok" || second.Status != "ok" {
		t.Fatalf("prepare results = %#v %#v, want ok", first, second)
	}

	firstResult := service.Submit(ArtifactSubmitRequest{
		LeaseID: first.Data["lease_id"].(string),
		Content: []byte("# First writer\n"),
	})
	if firstResult.Status != "ok" {
		t.Fatalf("first submit = %#v, want ok", firstResult)
	}
	secondResult := service.Submit(ArtifactSubmitRequest{
		LeaseID: second.Data["lease_id"].(string),
		Content: []byte("# Stale writer\n"),
	})
	if secondResult.Status != "blocked" {
		t.Fatalf("stale submit = %#v, want blocked", secondResult)
	}

	stored, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != "# First writer\n" {
		t.Fatalf("stored = %q, want first writer preserved", stored)
	}
}

func TestArtifactLeaseDetectsExistingTargetChangedAfterPrepare(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/spec.md"
	target := filepath.Join(projectRoot, filepath.FromSlash(path))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("# Original\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v, want ok", prepared)
	}
	wantDigest := fmt.Sprintf("%x", sha256.Sum256([]byte("# Original\n")))
	if prepared.Data["target_exists"] != true || prepared.Data["target_sha256"] != wantDigest {
		t.Fatalf("prepare target snapshot = %#v, want existing digest %s", prepared.Data, wantDigest)
	}
	if err := os.WriteFile(target, []byte("# External update\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	result := service.Submit(ArtifactSubmitRequest{
		LeaseID: prepared.Data["lease_id"].(string),
		Content: []byte("# Lease update\n"),
	})
	if result.Status != "blocked" {
		t.Fatalf("submit after external update = %#v, want blocked", result)
	}
	stored, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if string(stored) != "# External update\n" {
		t.Fatalf("stored = %q, want external update preserved", stored)
	}
}

func TestArtifactInvalidContentConsumesClaimedLease(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec-contract.json"})
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v, want ok", prepared)
	}
	leaseID := prepared.Data["lease_id"].(string)

	invalid := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("{not-json")})
	if invalid.Status != "invalid" {
		t.Fatalf("invalid submit = %#v, want invalid", invalid)
	}
	if optionValue(invalid.NextArgv, "--path", "") != "specs/001-runtime/spec-contract.json" {
		t.Fatalf("invalid submit next argv = %#v, want a fresh prepare command", invalid.NextArgv)
	}
	retried := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte(`{"status":"ready"}`)})
	if retried.Status != "blocked" {
		t.Fatalf("retry invalid-content lease = %#v, want blocked", retried)
	}
}

func TestArtifactStaleTargetConsumesClaimedLease(t *testing.T) {
	projectRoot := t.TempDir()
	target := filepath.Join(projectRoot, "specs", "001-runtime", "spec.md")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("# Original\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	leaseID := prepared.Data["lease_id"].(string)
	if err := os.WriteFile(target, []byte("# External\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	stale := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Proposed\n")})
	if stale.Status != "blocked" || optionValue(stale.NextArgv, "--path", "") != "specs/001-runtime/spec.md" {
		t.Fatalf("stale submit = %#v, want blocked with fresh prepare argv", stale)
	}
	retried := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Reuse\n")})
	if retried.Status != "blocked" {
		t.Fatalf("retry stale lease = %#v, want blocked", retried)
	}
	stored, err := os.ReadFile(target)
	if err != nil || string(stored) != "# External\n" {
		t.Fatalf("stale retry changed target = %q, %v", stored, err)
	}
}

func TestArtifactRegistryRejectsRuntimeOwnedAndHiddenPaths(t *testing.T) {
	tests := []struct {
		name    string
		request ArtifactPrepareRequest
	}{
		{name: "mixed-case workflow path", request: ArtifactPrepareRequest{Path: ".specify/features/001-runtime/WORKFLOW.json"}},
		{name: "canonical workflow kind", request: ArtifactPrepareRequest{FeatureID: "001-runtime", Kind: "workflow"}},
		{name: "terminal acceptance snapshot", request: ArtifactPrepareRequest{Path: ".specify/features/001-runtime/.human-acceptance-terminal.json"}},
		{name: "acceptance repair journal", request: ArtifactPrepareRequest{Path: ".specify/features/001-runtime/.human-acceptance-repair.json"}},
		{name: "generic hidden basename", request: ArtifactPrepareRequest{Path: "specs/001-runtime/.private.json"}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			result := NewArtifactService(t.TempDir()).Prepare(test.request)
			if result.Status != "invalid" {
				t.Fatalf("prepare = %#v, want invalid", result)
			}
		})
	}
}

func TestAtomicWriteSyncFailureLeavesExistingTargetUnchanged(t *testing.T) {
	directory := t.TempDir()
	target := filepath.Join(directory, "state.json")
	if err := os.WriteFile(target, []byte("original\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	priorSync := syncAtomicTempFile
	syncAtomicTempFile = func(*os.File) error { return errors.New("injected temp sync failure") }
	defer func() { syncAtomicTempFile = priorSync }()

	err := atomicWriteFile(target, []byte("replacement\n"), 0o644)
	if err == nil || !strings.Contains(err.Error(), "injected temp sync failure") {
		t.Fatalf("atomic write error = %v, want injected sync failure", err)
	}
	stored, readErr := os.ReadFile(target)
	if readErr != nil || string(stored) != "original\n" {
		t.Fatalf("target after sync failure = %q, %v", stored, readErr)
	}
	matches, globErr := filepath.Glob(filepath.Join(directory, ".state.json.tmp-*"))
	if globErr != nil || len(matches) != 0 {
		t.Fatalf("temporary files after sync failure = %#v, %v", matches, globErr)
	}
}

func TestArtifactLeaseIsSingleUseAndCannotRedirectOutput(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{FeatureID: "001-runtime", Kind: "spec"})
	leaseID := prepared.Data["lease_id"].(string)

	first := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Spec\n")})
	if first.Status != "ok" {
		t.Fatalf("first submit = %#v", first)
	}
	second := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Replayed\n")})
	if second.Status != "blocked" {
		t.Fatalf("replayed submit status = %q, want blocked: %#v", second.Status, second)
	}

	outside := filepath.Join(projectRoot, "redirected.md")
	if _, err := os.Stat(outside); !os.IsNotExist(err) {
		t.Fatalf("artifact service created an unregistered output: %v", err)
	}
}

func TestArtifactConcurrentSubmitClaimsOneLeaseOnce(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	leaseID := prepared.Data["lease_id"].(string)
	const contenders = 16
	start := make(chan struct{})
	results := make(chan Envelope, contenders)
	for index := 0; index < contenders; index++ {
		go func() {
			<-start
			results <- service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# One writer\n")})
		}()
	}
	close(start)
	okCount := 0
	blockedCount := 0
	for index := 0; index < contenders; index++ {
		switch result := <-results; result.Status {
		case "ok":
			okCount++
		case "blocked":
			blockedCount++
		default:
			t.Fatalf("concurrent submit = %#v", result)
		}
	}
	if okCount != 1 || blockedCount != contenders-1 {
		t.Fatalf("concurrent lease results = %d ok, %d blocked", okCount, blockedCount)
	}
}

func TestArtifactCorruptClaimCannotBeRetriedOrWriteTarget(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	leaseID := prepared.Data["lease_id"].(string)
	leasePath, err := service.leasePath(leaseID)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(leasePath, []byte(`{"id":`), 0o644); err != nil {
		t.Fatal(err)
	}
	first := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Unsafe\n")})
	second := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Retry\n")})
	if first.Status != "blocked" || second.Status != "blocked" {
		t.Fatalf("corrupt claim results = %#v %#v, want blocked", first, second)
	}
	if _, err := os.Stat(filepath.Join(projectRoot, "specs", "001-runtime", "spec.md")); !os.IsNotExist(err) {
		t.Fatalf("corrupt lease wrote target: %v", err)
	}
}

func TestArtifactShowRejectsUnknownView(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	submitted := service.Submit(ArtifactSubmitRequest{
		LeaseID: prepared.Data["lease_id"].(string),
		Content: []byte("# Spec\n"),
	})
	if submitted.Status != "ok" {
		t.Fatalf("submit = %#v", submitted)
	}

	shown := service.Show(ArtifactShowRequest{
		Path: "specs/001-runtime/spec.md",
		View: "raw",
	})
	if shown.Status != "invalid" {
		t.Fatalf("unknown view = %#v, want invalid", shown)
	}
}

func TestArtifactPrepareRejectsSymlinkedRegisteredParent(t *testing.T) {
	projectRoot := t.TempDir()
	outside := t.TempDir()
	if err := os.Symlink(outside, filepath.Join(projectRoot, "specs")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	if prepared.Status != "blocked" {
		t.Fatalf("symlinked prepare = %#v, want blocked", prepared)
	}
	if _, err := os.Stat(filepath.Join(outside, "001-runtime", "spec.md")); !os.IsNotExist(err) {
		t.Fatalf("submit escaped the project root: %v", err)
	}
}

func TestArtifactSubmitRechecksParentAfterMkdirAll(t *testing.T) {
	projectRoot := t.TempDir()
	outside := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v, want ok", prepared)
	}

	var hookErr error
	service.afterArtifactMkdirAll = func() {
		parent := filepath.Join(projectRoot, "specs", "001-runtime")
		if err := os.Remove(parent); err != nil {
			hookErr = err
			return
		}
		hookErr = os.Symlink(outside, parent)
	}
	result := service.Submit(ArtifactSubmitRequest{
		LeaseID: prepared.Data["lease_id"].(string),
		Content: []byte("# Escaped after mkdir\n"),
	})
	if hookErr != nil {
		t.Skipf("symlink replacement unavailable: %v", hookErr)
	}
	if result.Status != "blocked" {
		t.Fatalf("submit after parent replacement = %#v, want blocked", result)
	}
	if _, err := os.Stat(filepath.Join(outside, "spec.md")); !os.IsNotExist(err) {
		t.Fatalf("submit escaped through replaced parent: %v", err)
	}
}

func TestArtifactScaffoldCreatesRegisteredQuickStatusFromInstalledTemplate(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
	service := NewArtifactService(projectRoot)

	result := service.Scaffold(ArtifactScaffoldRequest{
		Kind: "quick-status",
		Path: ".planning/quick/001-demo/STATUS.md",
		Variables: map[string]any{
			"id":      "001",
			"slug":    "001-demo",
			"title":   `Demo "quoted"`,
			"trigger": "manual",
		},
	})
	if result.Status != "ok" {
		t.Fatalf("scaffold quick status = %#v, want ok", result)
	}
	if result.Data["canonical_path"] != ".planning/quick/001-demo/STATUS.md" {
		t.Fatalf("scaffold canonical_path = %#v", result.Data["canonical_path"])
	}
	if result.Data["estimated_token_savings"].(int) <= 0 {
		t.Fatalf("scaffold estimated_token_savings = %#v, want positive", result.Data["estimated_token_savings"])
	}
	stored, err := os.ReadFile(filepath.Join(projectRoot, ".planning", "quick", "001-demo", "STATUS.md"))
	if err != nil {
		t.Fatal(err)
	}
	content := string(stored)
	if !bytes.Contains(stored, []byte("status: gathering")) || !bytes.Contains(stored, []byte("understanding_confirmed: false")) {
		t.Fatalf("quick scaffold changed safe defaults: %q", content)
	}
	if !bytes.Contains(stored, []byte(`title: "Demo \"quoted\""`)) {
		t.Fatalf("quick scaffold did not escape YAML scalar: %q", content)
	}

	replayed := service.Scaffold(ArtifactScaffoldRequest{
		Kind: "quick-status",
		Path: ".planning/quick/001-demo/STATUS.md",
	})
	if replayed.Status != "blocked" {
		t.Fatalf("scaffold existing target = %#v, want blocked", replayed)
	}
}

func TestArtifactScaffoldBuildsRegisteredPlanContract(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "plan-contract-template.json")
	service := NewArtifactService(projectRoot)

	result := service.Scaffold(ArtifactScaffoldRequest{
		Kind: "plan-contract",
		Path: "specs/001-demo/plan-contract.json",
		Variables: map[string]any{
			"intent":           "Ship the unified runtime",
			"complexity_level": "standard",
			"acceptance_refs":  []any{"spec.md#FR-001"},
		},
	})
	if result.Status != "ok" {
		t.Fatalf("scaffold plan contract = %#v, want ok", result)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, "specs", "001-demo", "plan-contract.json"))
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatalf("decode plan scaffold: %v", err)
	}
	if payload["status"] != "draft" || payload["intent"] != "Ship the unified runtime" {
		t.Fatalf("plan scaffold payload = %#v", payload)
	}
	transition, ok := payload["transition"].(map[string]any)
	if !ok || transition["status"] != "blocked" {
		t.Fatalf("plan transition = %#v, want blocked", payload["transition"])
	}
}

func TestArtifactScaffoldRejectsUnsafePathsAndVariables(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
	service := NewArtifactService(projectRoot)
	tests := []struct {
		name      string
		request   ArtifactScaffoldRequest
		wantState string
	}{
		{
			name:      "wrong root",
			request:   ArtifactScaffoldRequest{Kind: "quick-status", Path: "specs/001-demo/STATUS.md"},
			wantState: "invalid",
		},
		{
			name: "frontmatter injection",
			request: ArtifactScaffoldRequest{
				Kind:      "quick-status",
				Path:      ".planning/quick/001-demo/STATUS.md",
				Variables: map[string]any{"title": "bad\nstatus: resolved"},
			},
			wantState: "invalid",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			result := service.Scaffold(test.request)
			if result.Status != test.wantState {
				t.Fatalf("scaffold = %#v, want status %q", result, test.wantState)
			}
		})
	}
}

func TestArtifactScaffoldCLIUsesUnifiedEnvelope(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"artifact", "scaffold",
		"--project-root", projectRoot,
		"--kind", "quick-status",
		"--path", ".planning/quick/001-demo/STATUS.md",
		"--vars", `{"id":"001","slug":"001-demo","title":"Demo","trigger":"manual"}`,
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("artifact scaffold code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	requireUnifiedEnvelope(t, payload)
	if payload["status"] != "ok" {
		t.Fatalf("artifact scaffold payload = %#v", payload)
	}
}

func TestArtifactScaffoldCatalogPublishesOnlyImplementedKinds(t *testing.T) {
	result := ArtifactScaffoldCatalog()
	if result.Status != "ok" || len(result.Items) != 2 {
		t.Fatalf("artifact scaffold catalog = %#v, want two kinds", result)
	}
	kinds := map[string]bool{}
	for _, item := range result.Items {
		entry, ok := item.(map[string]any)
		if !ok {
			t.Fatalf("catalog item = %#v, want object", item)
		}
		kinds[entry["kind"].(string)] = true
		if entry["estimated_token_savings"].(int) <= 0 {
			t.Fatalf("catalog item has no savings estimate: %#v", entry)
		}
	}
	if !kinds["plan-contract"] || !kinds["quick-status"] {
		t.Fatalf("catalog kinds = %#v", kinds)
	}
}

func TestArtifactScaffoldRejectsUnsafeInstalledTemplates(t *testing.T) {
	t.Run("quick status readiness", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
		path := filepath.Join(projectRoot, ".specify", "templates", "artifacts", "quick-status.md")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw = bytes.Replace(raw, []byte("status: gathering"), []byte("status: resolved"), 1)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "quick-status",
			Path: ".planning/quick/001-demo/STATUS.md",
		})
		if result.Status != "invalid" {
			t.Fatalf("unsafe quick template = %#v, want invalid", result)
		}
	})

	t.Run("quick status missing anchor", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
		path := filepath.Join(projectRoot, ".specify", "templates", "artifacts", "quick-status.md")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw = bytes.Replace(raw, []byte("<!-- agent-fill:validation -->"), nil, 1)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "quick-status",
			Path: ".planning/quick/001-demo/STATUS.md",
		})
		if result.Status != "invalid" {
			t.Fatalf("incomplete quick template = %#v, want invalid", result)
		}
	})

	t.Run("plan contract readiness", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "plan-contract-template.json")
		path := filepath.Join(projectRoot, ".specify", "templates", "plan-contract-template.json")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		var payload map[string]any
		if err := json.Unmarshal(raw, &payload); err != nil {
			t.Fatal(err)
		}
		payload["status"] = "ready"
		raw, _ = json.Marshal(payload)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "plan-contract",
			Path: "specs/001-demo/plan-contract.json",
		})
		if result.Status != "invalid" {
			t.Fatalf("unsafe plan template = %#v, want invalid", result)
		}
	})

	t.Run("plan contract missing fill target", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "plan-contract-template.json")
		path := filepath.Join(projectRoot, ".specify", "templates", "plan-contract-template.json")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		var payload map[string]any
		if err := json.Unmarshal(raw, &payload); err != nil {
			t.Fatal(err)
		}
		delete(payload, "interface_map")
		raw, _ = json.Marshal(payload)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "plan-contract",
			Path: "specs/001-demo/plan-contract.json",
		})
		if result.Status != "invalid" {
			t.Fatalf("incomplete plan template = %#v, want invalid", result)
		}
	})
}

func TestArtifactScaffoldRejectsUnregisteredAndReadinessVariables(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "plan-contract-template.json")
	service := NewArtifactService(projectRoot)
	tests := []ArtifactScaffoldRequest{
		{
			Kind:      "plan-contract",
			Path:      "specs/001-demo/plan-contract.json",
			Variables: map[string]any{"status": "ready"},
		},
		{
			Kind: "plan-contract",
			Path: "specs/001-demo/plan-contract.json",
			Variables: map[string]any{
				"architecture_decisions": []any{map[string]any{"review_status": "complete"}},
			},
		},
		{
			Kind:      "plan-contract",
			Path:      "specs/001-demo/plan-contract.json",
			Variables: map[string]any{"transition": map[string]any{"status": "blocked"}},
		},
	}
	for index, request := range tests {
		if result := service.Scaffold(request); result.Status != "invalid" {
			t.Fatalf("unsafe variable case %d = %#v, want invalid", index, result)
		}
	}
}

func TestArtifactScaffoldSupportsNestedRegisteredPlanPathAndUnicode(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "plan-contract-template.json")
	result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
		Kind: "plan-contract",
		Path: ".specify/features/001-demo/plan/plan-contract.json",
		Variables: map[string]any{
			"intent": "保留清晰的工作流结构",
		},
	})
	if result.Status != "ok" {
		t.Fatalf("nested plan scaffold = %#v, want ok", result)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, ".specify", "features", "001-demo", "plan", "plan-contract.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(raw, []byte("保留清晰的工作流结构")) {
		t.Fatalf("plan scaffold escaped or lost unicode: %q", raw)
	}
}

func TestArtifactScaffoldRejectsSymlinkedOutputParent(t *testing.T) {
	projectRoot := t.TempDir()
	outside := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
	quickRoot := filepath.Join(projectRoot, ".planning", "quick")
	if err := os.MkdirAll(filepath.Dir(quickRoot), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, quickRoot); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
		Kind: "quick-status",
		Path: ".planning/quick/001-demo/STATUS.md",
	})
	if result.Status != "blocked" {
		t.Fatalf("symlinked scaffold = %#v, want blocked", result)
	}
	if _, err := os.Stat(filepath.Join(outside, "001-demo", "STATUS.md")); !os.IsNotExist(err) {
		t.Fatalf("scaffold escaped project root: %v", err)
	}
}

func installScaffoldTemplate(t *testing.T, projectRoot, relative string) {
	t.Helper()
	source := filepath.Join("..", "..", "templates", filepath.FromSlash(relative))
	raw, err := os.ReadFile(source)
	if err != nil {
		t.Fatalf("read canonical scaffold template %s: %v", source, err)
	}
	target := filepath.Join(projectRoot, ".specify", "templates", filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}
