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
	artifactRelativePath := ".specify/features/001-runtime/research-evidence/EVD-001.json"

	prepared := service.Prepare(ArtifactPrepareRequest{
		Path: artifactRelativePath,
	})
	if prepared.Status != "ok" {
		t.Fatalf("prepare status = %q, want ok: %#v", prepared.Status, prepared)
	}
	leaseID, ok := prepared.Data["lease_id"].(string)
	if !ok || leaseID == "" {
		t.Fatalf("prepare lease_id = %#v, want non-empty string", prepared.Data["lease_id"])
	}
	if path := prepared.Data["canonical_path"]; path != artifactRelativePath {
		t.Fatalf("prepare canonical_path = %#v", path)
	}
	if prepared.Data["target_exists"] != false || prepared.Data["target_sha256"] != "" {
		t.Fatalf("prepare target snapshot = %#v, want absent target", prepared.Data)
	}

	content := json.RawMessage(`{"schema_version":1,"evidence_id":"EVD-001","claim":"A deterministic runtime"}`)
	submitted := service.Submit(ArtifactSubmitRequest{
		LeaseID: leaseID,
		Content: content,
	})
	if submitted.Status != "ok" {
		t.Fatalf("submit status = %q, want ok: %#v", submitted.Status, submitted)
	}
	artifactPath := filepath.Join(projectRoot, filepath.FromSlash(artifactRelativePath))
	stored, err := os.ReadFile(artifactPath)
	if err != nil {
		t.Fatalf("read canonical artifact: %v", err)
	}
	if !json.Valid(stored) {
		t.Fatalf("canonical artifact is not JSON: %q", stored)
	}

	summary := service.Show(ArtifactShowRequest{
		Path: artifactRelativePath,
		View: "summary",
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
		Path: artifactRelativePath,
		View: "full",
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
	content := "# Feature\n\nstatus: ready\n\n## Requirements\n\n- FR-001\n"

	var submitOut bytes.Buffer
	code = Run([]string{
		"artifact", "submit",
		"--project-root", projectRoot,
		"--lease", leaseID,
		"--content", content,
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

func TestArtifactCLISubmitsInlineContentWithoutTemporaryFile(t *testing.T) {
	projectRoot := t.TempDir()
	var prepareOut, stderr bytes.Buffer
	if code := Run([]string{"artifact", "prepare", "--project-root", projectRoot, "--path", "specs/001-runtime/spec.md"}, &prepareOut, &stderr, "test"); code != 0 {
		t.Fatalf("prepare code = %d stderr=%q stdout=%q", code, stderr.String(), prepareOut.String())
	}
	leaseID := requireObject(t, decodeJSONObject(t, prepareOut.Bytes()), "data")["lease_id"].(string)
	var submitOut bytes.Buffer
	content := "# Feature\n\nstatus: ready\n\n## Requirements\n\n- FR-001\n"
	if code := Run([]string{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--content", content}, &submitOut, &stderr, "test"); code != 0 {
		t.Fatalf("submit code = %d stderr=%q stdout=%q", code, stderr.String(), submitOut.String())
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, "specs", "001-runtime", "spec.md"))
	if err != nil || string(raw) != content {
		t.Fatalf("canonical content = %q err=%v", raw, err)
	}
}

func TestArtifactCLISubmitRequiresExactlyOneContentChannel(t *testing.T) {
	for _, args := range [][]string{
		{"artifact", "submit", "--lease", "lease"},
		{"artifact", "submit", "--lease", "lease", "--content", "x", "--recovery-file", "x.md"},
	} {
		var stdout, stderr bytes.Buffer
		if code := Run(args, &stdout, &stderr, "test"); code == 0 {
			t.Fatalf("Run(%v) succeeded: %s", args, stdout.String())
		}
		if !strings.Contains(stdout.String(), "exactly one") {
			t.Fatalf("Run(%v) = %s, want exact-one guidance", args, stdout.String())
		}
	}
}

func TestArtifactCLIRejectsAgentAuthoredFileSubmissionWithoutClaimingLease(t *testing.T) {
	projectRoot := t.TempDir()
	var prepareOut, stderr bytes.Buffer
	if code := Run([]string{"artifact", "prepare", "--project-root", projectRoot, "--path", "specs/001-runtime/spec.md"}, &prepareOut, &stderr, "test"); code != 0 {
		t.Fatalf("prepare code = %d stderr=%q stdout=%q", code, stderr.String(), prepareOut.String())
	}
	leaseID := requireObject(t, decodeJSONObject(t, prepareOut.Bytes()), "data")["lease_id"].(string)
	temporaryPath := filepath.Join(projectRoot, ".tmp-implementation-handoff-contract.json")
	if err := os.WriteFile(temporaryPath, []byte(`{"oversized":"agent-authored"}`), 0o644); err != nil {
		t.Fatal(err)
	}

	for _, args := range [][]string{
		{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--content-file", temporaryPath},
		{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--recovery-file", temporaryPath},
	} {
		var stdout bytes.Buffer
		if code := Run(args, &stdout, &stderr, "test"); code == 0 {
			t.Fatalf("Run(%v) succeeded: %s", args, stdout.String())
		}
		if !strings.Contains(stdout.String(), "content-file") && !strings.Contains(stdout.String(), "recovery") {
			t.Fatalf("Run(%v) = %s, want file-input rejection", args, stdout.String())
		}
	}

	var submitOut bytes.Buffer
	if code := Run([]string{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--content", "# Inline\n"}, &submitOut, &stderr, "test"); code != 0 {
		t.Fatalf("inline retry code = %d stderr=%q stdout=%q", code, stderr.String(), submitOut.String())
	}
}

func TestArtifactCLIRecoveryFileRequiresJournalBoundAcceptanceBackup(t *testing.T) {
	projectRoot := t.TempDir()
	featurePath := filepath.Join(projectRoot, "specs", "001-runtime")
	if err := os.MkdirAll(featurePath, 0o755); err != nil {
		t.Fatal(err)
	}
	backup := []byte(`{"status":"rejected","source":{},"overall":{},"findings":[{"id":"HAF-001","route":"spx-review","status":"open"}]}` + "\n")
	backupPath := filepath.Join(featurePath, acceptanceRepairBackupFilename)
	if err := os.WriteFile(backupPath, backup, 0o644); err != nil {
		t.Fatal(err)
	}
	journal := map[string]any{
		"version":                       1,
		"phase":                         "acceptance-invalidated",
		"finding_id":                    "HAF-001",
		"route":                         "spx-review",
		"target_stage":                  "review",
		"owning_stage_command":          "spx-review",
		"expected_revision":             7,
		"backup_sha256":                 strings.Repeat("0", 64),
		"invalidated_acceptance_sha256": strings.Repeat("a", 64),
		"acceptance_file":               "human-acceptance.json",
		"backup_file":                   acceptanceRepairBackupFilename,
	}
	journalPath := filepath.Join(featurePath, acceptanceRepairJournalFilename)
	writeRecoveryJournal := func() {
		raw, err := json.MarshalIndent(journal, "", "  ")
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(journalPath, append(raw, '\n'), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	writeRecoveryJournal()

	var prepareOut, stderr bytes.Buffer
	if code := Run([]string{"artifact", "prepare", "--project-root", projectRoot, "--path", "specs/001-runtime/human-acceptance.json"}, &prepareOut, &stderr, "test"); code != 0 {
		t.Fatalf("prepare code = %d stderr=%q stdout=%q", code, stderr.String(), prepareOut.String())
	}
	leaseID := requireObject(t, decodeJSONObject(t, prepareOut.Bytes()), "data")["lease_id"].(string)
	recoveryRef := "specs/001-runtime/" + acceptanceRepairBackupFilename
	var rejectedOut bytes.Buffer
	if code := Run([]string{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--recovery-file", recoveryRef}, &rejectedOut, &stderr, "test"); code == 0 {
		t.Fatalf("mismatched recovery digest succeeded: %s", rejectedOut.String())
	}
	if !strings.Contains(rejectedOut.String(), "digest") {
		t.Fatalf("recovery rejection = %s, want digest blocker", rejectedOut.String())
	}

	digest := sha256.Sum256(backup)
	journal["backup_sha256"] = fmt.Sprintf("%x", digest)
	writeRecoveryJournal()
	var recoveredOut bytes.Buffer
	if code := Run([]string{"artifact", "submit", "--project-root", projectRoot, "--lease", leaseID, "--recovery-file", recoveryRef}, &recoveredOut, &stderr, "test"); code != 0 {
		t.Fatalf("recovery code = %d stderr=%q stdout=%q", code, stderr.String(), recoveredOut.String())
	}
	restored, err := os.ReadFile(filepath.Join(featurePath, "human-acceptance.json"))
	if err != nil || !bytes.Equal(restored, backup) {
		t.Fatalf("restored acceptance = %q err=%v", restored, err)
	}
	recovered := decodeJSONObject(t, recoveredOut.Bytes())
	if requireObject(t, recovered, "data")["input_channel"] != "runtime-recovery-backup" {
		t.Fatalf("recovery envelope = %#v", recovered)
	}
}

func TestArtifactPatchUpdatesOnlyTargetedJSONMarkdownAndFrontmatter(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	jsonPath := "specs/001-runtime/spec-contract.json"
	writeArtifactTestFile(t, projectRoot, jsonPath, `{"status":"draft","nested":{"keep":true}}`)
	jsonLease := service.Prepare(ArtifactPrepareRequest{Path: jsonPath})
	jsonResult := service.Patch(ArtifactPatchRequest{LeaseID: jsonLease.Data["lease_id"].(string), JSONPointer: "/status", Value: "ready"})
	if jsonResult.Status != "ok" {
		t.Fatalf("json patch = %#v", jsonResult)
	}
	jsonRaw, _ := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(jsonPath)))
	if !strings.Contains(string(jsonRaw), `"status": "ready"`) || !strings.Contains(string(jsonRaw), `"keep": true`) {
		t.Fatalf("json patch lost unrelated content: %s", jsonRaw)
	}

	markdownPath := "specs/001-runtime/workflow-state.md"
	writeArtifactTestFile(t, projectRoot, markdownPath, "---\nstatus: draft\nkeep: yes\n---\n\n# State\n\n## Current\n\nold\n\n## Keep\n\nunchanged\n")
	sectionLease := service.Prepare(ArtifactPrepareRequest{Path: markdownPath})
	sectionResult := service.Patch(ArtifactPatchRequest{LeaseID: sectionLease.Data["lease_id"].(string), Section: "Current", Content: "new"})
	if sectionResult.Status != "ok" {
		t.Fatalf("section patch = %#v", sectionResult)
	}
	frontmatterLease := service.Prepare(ArtifactPrepareRequest{Path: markdownPath})
	frontmatterResult := service.Patch(ArtifactPatchRequest{LeaseID: frontmatterLease.Data["lease_id"].(string), Frontmatter: map[string]any{"status": "ready", "confirmed": true}})
	if frontmatterResult.Status != "ok" {
		t.Fatalf("frontmatter patch = %#v", frontmatterResult)
	}
	markdownRaw, _ := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(markdownPath)))
	text := string(markdownRaw)
	for _, want := range []string{"status: \"ready\"", "confirmed: true", "keep: yes", "## Current\n\nnew", "## Keep\n\nunchanged"} {
		if !strings.Contains(text, want) {
			t.Fatalf("markdown patch missing %q:\n%s", want, text)
		}
	}

	ndjsonPath := "specs/001-runtime/clarification/checkpoints.ndjson"
	writeArtifactTestFile(t, projectRoot, ndjsonPath, "{\"id\":1}\n")
	appendLease := service.Prepare(ArtifactPrepareRequest{Path: ndjsonPath})
	appendResult := service.Patch(ArtifactPatchRequest{LeaseID: appendLease.Data["lease_id"].(string), Append: true, AppendJSON: map[string]any{"id": 2}})
	if appendResult.Status != "ok" {
		t.Fatalf("append patch = %#v", appendResult)
	}
	ndjsonRaw, _ := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(ndjsonPath)))
	if string(ndjsonRaw) != "{\"id\":1}\n{\"id\":2}\n" {
		t.Fatalf("ndjson append = %q", ndjsonRaw)
	}
}

func TestArtifactPatchRenamesMarkdownHeadingAndReplacesPreamble(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := ".specify/memory/constitution.md"
	writeArtifactTestFile(t, projectRoot, path, "<!-- old report -->\n\n# [PROJECT_NAME] Constitution\n\n## Core Principles\n\nKeep.\n")

	headingLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	headingResult := service.Patch(ArtifactPatchRequest{
		LeaseID:    headingLease.Data["lease_id"].(string),
		Heading:    "[PROJECT_NAME] Constitution",
		NewHeading: "Demo Constitution",
	})
	if headingResult.Status != "ok" {
		t.Fatalf("heading patch = %#v", headingResult)
	}

	report := "<!--\nSync Impact Report\n- Version: 1.0.0 -> 1.1.0\n-->"
	preambleLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	preambleResult := service.Patch(ArtifactPatchRequest{
		LeaseID:  preambleLease.Data["lease_id"].(string),
		Preamble: &report,
	})
	if preambleResult.Status != "ok" {
		t.Fatalf("preamble patch = %#v", preambleResult)
	}

	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	text := string(raw)
	for _, want := range []string{report, "# Demo Constitution", "## Core Principles\n\nKeep."} {
		if !strings.Contains(text, want) {
			t.Fatalf("Markdown metadata patch missing %q:\n%s", want, text)
		}
	}
	if strings.Contains(text, "old report") || strings.Contains(text, "[PROJECT_NAME]") {
		t.Fatalf("Markdown metadata patch retained stale content:\n%s", text)
	}
}

func TestArtifactPatchCLIHandlesHeadingAndPreambleModes(t *testing.T) {
	projectRoot := t.TempDir()
	path := ".specify/memory/constitution.md"
	writeArtifactTestFile(t, projectRoot, path, "# [PROJECT_NAME] Constitution\n\n## Core Principles\n\nKeep.\n")
	service := NewArtifactService(projectRoot)

	headingLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"artifact", "patch",
		"--project-root", projectRoot,
		"--lease", headingLease.Data["lease_id"].(string),
		"--heading", "[PROJECT_NAME] Constitution",
		"--new-heading", "CLI Demo Constitution",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("heading CLI code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}

	preambleLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{
		"artifact", "patch",
		"--project-root", projectRoot,
		"--lease", preambleLease.Data["lease_id"].(string),
		"--preamble", "<!-- Sync Impact Report -->",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("preamble CLI code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}

	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"<!-- Sync Impact Report -->", "# CLI Demo Constitution", "## Core Principles"} {
		if !strings.Contains(string(raw), want) {
			t.Fatalf("CLI metadata patch missing %q:\n%s", want, raw)
		}
	}
}

func TestScaffoldOwnedArtifactRejectsWholeFileSubmit(t *testing.T) {
	projectRoot := t.TempDir()
	path := "specs/001-runtime/spec-contract.json"
	original := `{"status":"draft"}`
	writeArtifactTestFile(t, projectRoot, path, original)
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	if prepared.Status != "ok" {
		t.Fatalf("prepare scaffold-owned artifact = %#v", prepared)
	}
	result := service.Submit(ArtifactSubmitRequest{
		LeaseID: prepared.Data["lease_id"].(string),
		Content: []byte(`{"status":"ready"}`),
	})
	if result.Status != "invalid" || !strings.Contains(fmt.Sprint(result.Blockers), "artifact scaffold / artifact patch") {
		t.Fatalf("whole-file submit = %#v, want scaffold owner rejection", result)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil || string(raw) != original {
		t.Fatalf("rejected submit changed artifact = %q, %v", raw, err)
	}
}

func TestArtifactPatchRejectsSpecializedArtifacts(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/task-index.json"})
	if prepared.Status != "invalid" || prepared.Data["owner"] != "specify-runtime tasks" {
		t.Fatalf("specialized patch preparation = %#v", prepared)
	}
}

func TestArtifactPatchRejectsJSONLineAppendForNonJSONLineArtifacts(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/workflow-state.md"
	original := "# State\n"
	writeArtifactTestFile(t, projectRoot, path, original)

	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	result := service.Patch(ArtifactPatchRequest{
		LeaseID:    prepared.Data["lease_id"].(string),
		Append:     true,
		AppendJSON: map[string]any{"id": 1},
	})
	if result.Status != "invalid" || !strings.Contains(fmt.Sprint(result.Blockers), "JSONL or NDJSON") {
		t.Fatalf("non-JSONL append = %#v, want invalid extension guidance", result)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != original {
		t.Fatalf("non-JSONL append changed artifact: %q", raw)
	}
}

func TestArtifactPathRegistryRejectsSourceFiles(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	result := service.Prepare(ArtifactPrepareRequest{Path: "src/main.go"})
	if result.Status != "invalid" {
		t.Fatalf("prepare source path = %#v, want invalid", result)
	}
}

func TestArtifactPathRegistryRoutesSpecializedWorkflowStateToItsOwner(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, path := range []string{
		".specify/design/design-state.md",
		".specify/prd/status.json",
	} {
		if result := service.Prepare(ArtifactPrepareRequest{Path: path}); result.Status != "invalid" {
			t.Fatalf("specialized path %q = %#v, want invalid", path, result)
		}
	}
	prdWorkflowState := ".specify/prd-runs/001-scan/workflow-state.md"
	if result := service.Prepare(ArtifactPrepareRequest{Path: prdWorkflowState}); result.Status != "ok" {
		t.Fatalf("CLI-owned PRD workflow state %q = %#v, want generic artifact lease", prdWorkflowState, result)
	}
	if metadata, ok := LookupArtifactType(prdWorkflowState); !ok || !strings.Contains(metadata.Owner, "specify-runtime artifact") {
		t.Fatalf("PRD workflow state owner = %#v, want specify-runtime artifact", metadata)
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

func TestArtifactDeleteArchivesAndRestoreRecoversGenericArtifact(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/spec.md"
	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	submitted := service.Submit(ArtifactSubmitRequest{LeaseID: prepared.Data["lease_id"].(string), Content: []byte("# Spec\n")})
	if submitted.Status != "ok" {
		t.Fatalf("submit = %#v", submitted)
	}

	deleteLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	deleted := service.Delete(ArtifactDeleteRequest{LeaseID: deleteLease.Data["lease_id"].(string)})
	if deleted.Status != "ok" {
		t.Fatalf("delete = %#v, want ok", deleted)
	}
	if _, err := os.Stat(filepath.Join(projectRoot, filepath.FromSlash(path))); !os.IsNotExist(err) {
		t.Fatalf("deleted target still exists: %v", err)
	}
	archiveID := deleted.Data["archive_id"].(string)
	restored := service.Restore(ArtifactRestoreRequest{ArchiveID: archiveID})
	if restored.Status != "ok" {
		t.Fatalf("restore = %#v, want ok", restored)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != "# Spec\n" {
		t.Fatalf("restored content = %q", raw)
	}
	if replay := service.Restore(ArtifactRestoreRequest{ArchiveID: archiveID}); replay.Status != "blocked" {
		t.Fatalf("replayed restore = %#v, want blocked", replay)
	}
}

func TestArtifactDeleteRejectsTargetChangedAfterLease(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/spec.md"
	prepared := service.Prepare(ArtifactPrepareRequest{Path: path})
	if result := service.Submit(ArtifactSubmitRequest{LeaseID: prepared.Data["lease_id"].(string), Content: []byte("# Spec\n")}); result.Status != "ok" {
		t.Fatalf("submit = %#v", result)
	}
	deleteLease := service.Prepare(ArtifactPrepareRequest{Path: path})
	if err := os.WriteFile(filepath.Join(projectRoot, filepath.FromSlash(path)), []byte("# Changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	deleted := service.Delete(ArtifactDeleteRequest{LeaseID: deleteLease.Data["lease_id"].(string)})
	if deleted.Status != "blocked" {
		t.Fatalf("delete changed target = %#v, want blocked", deleted)
	}
	if _, err := os.Stat(filepath.Join(projectRoot, filepath.FromSlash(path))); err != nil {
		t.Fatalf("blocked delete removed target: %v", err)
	}
}

func TestArtifactDeleteAndRestoreCLIUseUnifiedEnvelope(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})
	service.Submit(ArtifactSubmitRequest{LeaseID: prepared.Data["lease_id"].(string), Content: []byte("# Spec\n")})
	deleteLease := service.Prepare(ArtifactPrepareRequest{Path: "specs/001-runtime/spec.md"})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "delete", "--project-root", projectRoot, "--lease", deleteLease.Data["lease_id"].(string), "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("artifact delete code=%d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	requireUnifiedEnvelope(t, payload)
	archiveID := requireObject(t, payload, "data")["archive_id"].(string)

	stdout.Reset()
	code = Run([]string{"artifact", "restore", "--project-root", projectRoot, "--archive", archiveID, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("artifact restore code=%d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	requireUnifiedEnvelope(t, decodeJSONObject(t, stdout.Bytes()))
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

func TestArtifactChecklistCreatesAndAppendsWithoutAgentFileWrites(t *testing.T) {
	projectRoot := t.TempDir()
	writeArtifactTestFile(t, projectRoot, ".specify/templates/artifacts/checklist.md", "# {{title}}\n\n**Purpose**: {{purpose}}\n**Created**: {{created}}\n**Feature**: {{feature}}\n\n{{categories}}\n")
	service := NewArtifactService(projectRoot)
	path := "specs/001-runtime/checklists/security.md"
	first := service.UpsertChecklist(ArtifactChecklistRequest{
		Path: path,
		InputJSON: []byte(`{
			"title":"Security Checklist: Runtime",
			"purpose":"Review requirements quality",
			"feature":"specs/001-runtime/spec.md",
			"categories":[
				{"heading":"Requirement Completeness","items":["Are authentication requirements defined? [Gap]","Are failure modes documented? [Completeness]"]}
			]
		}`),
	})
	if first.Status != "ok" || first.Data["created"] != true || first.Data["first_item_id"] != "CHK001" || first.Data["last_item_id"] != "CHK002" {
		t.Fatalf("first checklist render = %#v", first)
	}
	second := service.UpsertChecklist(ArtifactChecklistRequest{
		Path:      path,
		InputJSON: []byte(`{"categories":[{"heading":"Scenario Coverage","items":["Are recovery requirements specified? [Gap]"]}]}`),
	})
	if second.Status != "ok" || second.Data["created"] != false || second.Data["first_item_id"] != "CHK003" || second.Data["last_item_id"] != "CHK003" {
		t.Fatalf("append checklist render = %#v", second)
	}
	raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(path)))
	if err != nil {
		t.Fatal(err)
	}
	content := string(raw)
	for _, want := range []string{"# Security Checklist: Runtime", "CHK001 Are authentication", "CHK002 Are failure", "CHK003 Are recovery", "## Scenario Coverage"} {
		if !strings.Contains(content, want) {
			t.Fatalf("checklist missing %q:\n%s", want, content)
		}
	}
}

func TestArtifactChecklistRejectsUnregisteredPathsAndAgentAssignedIDs(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, request := range []ArtifactChecklistRequest{
		{Path: "src/checklists/security.md", InputJSON: []byte(`{"categories":[{"heading":"Coverage","items":["Are requirements complete?"]}]}`)},
		{Path: "specs/001-runtime/checklists/security.md", InputJSON: []byte(`{"title":"Security","purpose":"Review","feature":"spec.md","categories":[{"heading":"Coverage","items":["CHK001 Are requirements complete?"]}]}`)},
	} {
		result := service.UpsertChecklist(request)
		if result.Status != "invalid" {
			t.Fatalf("invalid checklist request %#v = %#v", request, result)
		}
	}
}

func TestArtifactChecklistCLIUsesCompactStructuredInput(t *testing.T) {
	projectRoot := t.TempDir()
	writeArtifactTestFile(t, projectRoot, ".specify/templates/artifacts/checklist.md", "# {{title}}\n\n**Purpose**: {{purpose}}\n**Created**: {{created}}\n**Feature**: {{feature}}\n\n{{categories}}\n")
	var stdout, stderr bytes.Buffer
	input := `{"title":"API Checklist","purpose":"Review API requirements","feature":"specs/001-api/spec.md","categories":[{"heading":"Clarity","items":["Are response requirements unambiguous? [Clarity]"]}]}`
	code := Run([]string{"artifact", "checklist", "--project-root", projectRoot, "--path", "specs/001-api/checklists/api.md", "--input-json", input}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("checklist code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if requireObject(t, payload, "data")["canonical_path"] != "specs/001-api/checklists/api.md" {
		t.Fatalf("checklist envelope = %#v", payload)
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

func TestArtifactScaffoldCreatesRegisteredStableWorkflowArtifacts(t *testing.T) {
	tests := []struct {
		kind     string
		template string
		path     string
		contains string
	}{
		{kind: "alignment", template: "alignment-template.md", path: "specs/001-demo/alignment.md", contains: "## Readiness Decision"},
		{kind: "clarification-checkpoints", template: "artifacts/empty.ndjson", path: "specs/001-demo/clarification/checkpoints.ndjson", contains: "\n"},
		{kind: "clarification-evidence-index", template: "artifacts/evidence-index.json", path: ".specify/features/001-demo/clarification/evidence-index.json", contains: `"lanes": []`},
		{kind: "spec-contract", template: "spec-contract-template.json", path: "specs/001-demo/spec-contract.json", contains: `"status": "draft"`},
		{kind: "workflow-state", template: "workflow-state-template.md", path: "specs/001-demo/workflow-state.md", contains: "# Workflow State:"},
		{kind: "constitution", template: "constitution-template.md", path: ".specify/memory/constitution.md", contains: "# [PROJECT_NAME] Constitution"},
		{kind: "data-model", template: "artifacts/data-model.md", path: "specs/001-demo/data-model.md", contains: "## Data Structures and Ownership"},
		{kind: "design-brief", template: "design-brief-template.md", path: ".specify/design/design-brief.md", contains: "status: draft"},
		{kind: "debug-session", template: "artifacts/debug-session.md", path: ".planning/debug/session-a.md", contains: "understanding_confirmed: false"},
		{kind: "deep-research", template: "artifacts/deep-research.md", path: "specs/001-demo/deep-research.md", contains: "## Implementation Chain Evidence"},
		{kind: "deep-research-not-needed", template: "artifacts/deep-research-not-needed.md", path: ".specify/features/001-demo/deep-research.md", contains: "**Status**: Pending"},
		{kind: "design-review", template: "artifacts/design-review.md", path: ".specify/design/review.md", contains: "## Immutable References"},
		{kind: "planning-lane-manifest", template: "artifacts/lane-manifest.json", path: "specs/001-demo/planning/lane-manifest.json", contains: `"command": "plan"`},
		{kind: "quick-plan", template: "artifacts/quick-plan.md", path: ".planning/quick/001-demo/PLAN.md", contains: "## Work Items, Dependencies, and Batches"},
		{kind: "quick-summary", template: "artifacts/quick-summary.md", path: ".planning/quick/001-demo/SUMMARY.md", contains: "## Recovery State"},
		{kind: "quickstart", template: "artifacts/quickstart.md", path: ".specify/features/001-demo/quickstart.md", contains: "## Failure and Recovery"},
		{kind: "references", template: "references-template.md", path: "specs/001-demo/references.md", contains: "## Reference Entries"},
		{kind: "research", template: "research-template.md", path: "specs/001-demo/research.md", contains: "# Research:"},
		{kind: "specify-context", template: "context-template.md", path: ".specify/features/001-demo/context.md", contains: "## Integration Boundaries"},
		{kind: "specify-draft", template: "specify-draft-template.md", path: "specs/001-demo/specify-draft.md", contains: "## Domain Progress Ledger"},
		{kind: "task-generation-lane-manifest", template: "artifacts/lane-manifest.json", path: ".specify/features/001-demo/task-generation/lane-manifest.json", contains: `"command": "tasks"`},
		{kind: "ui-brief", template: "ui-brief-template.md", path: "specs/001-demo/ui-brief.md", contains: "# UI Brief"},
		{kind: "ui-reference-notes", template: "ui-reference-notes-template.md", path: "specs/001-demo/ui-reference-notes.md", contains: "# UI Reference Notes"},
	}
	for _, test := range tests {
		t.Run(test.kind, func(t *testing.T) {
			projectRoot := t.TempDir()
			installScaffoldTemplate(t, projectRoot, test.template)
			result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{Kind: test.kind, Path: test.path})
			if result.Status != "ok" {
				t.Fatalf("scaffold %s = %#v, want ok", test.kind, result)
			}
			raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(test.path)))
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Contains(raw, []byte(test.contains)) {
				t.Fatalf("scaffold %s output does not contain %q", test.kind, test.contains)
			}
		})
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

func TestArtifactScaffoldCLIAcceptsDeprecatedOutAlias(t *testing.T) {
	projectRoot := t.TempDir()
	installScaffoldTemplate(t, projectRoot, "artifacts/quick-status.md")
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"artifact", "scaffold",
		"--project-root", projectRoot,
		"--kind", "quick-status",
		"--out", ".planning/quick/001-demo/STATUS.md",
		"--vars", `{"id":"001","slug":"001-demo","title":"Demo","trigger":"manual"}`,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("artifact scaffold alias code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	compatibility := requireObject(t, data, "compatibility")
	if compatibility["deprecated_option"] != "--out" || compatibility["replacement"] != "--path" {
		t.Fatalf("artifact scaffold compatibility = %#v", compatibility)
	}
}

func TestArtifactScaffoldCLIRejectsUnknownOptionsBeforePathValidation(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"artifact", "scaffold", "--kind", "quick-status", "--ouut", ".planning/quick/001-demo/STATUS.md", "--format", "json",
	}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("artifact scaffold typo code = %d stdout=%q", code, stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if payload["status"] != "usage-error" || !strings.Contains(fmt.Sprint(payload["blockers"]), "unknown option \"--ouut\"") {
		t.Fatalf("artifact scaffold typo payload = %#v", payload)
	}
	if !strings.Contains(fmt.Sprint(payload["blockers"]), "--out") || !strings.Contains(fmt.Sprint(payload["blockers"]), "--path") {
		t.Fatalf("artifact scaffold typo lacks compatibility guidance: %#v", payload)
	}
	if show := requireStringArray(t, payload, "show_argv"); len(show) < 4 || show[1] != "api" || show[2] != "show" || show[3] != "artifact.scaffold" {
		t.Fatalf("artifact scaffold typo show_argv = %#v", show)
	}
	if next := requireStringArray(t, payload, "next_argv"); len(next) < 3 || next[1] != "artifact" || next[2] != "catalog" {
		t.Fatalf("artifact scaffold typo next_argv = %#v", next)
	}
}

func TestArtifactScaffoldCLIReportsMissingPathPrecisely(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "scaffold", "--kind", "quick-status", "--format", "json"}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("artifact scaffold missing path code = %d stdout=%q", code, stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	if payload["status"] != "usage-error" || !strings.Contains(fmt.Sprint(payload["summary"]), "requires --path") {
		t.Fatalf("artifact scaffold missing path payload = %#v", payload)
	}
}

func TestArtifactScaffoldHelpDescribesCanonicalInvocation(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "scaffold", "--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("artifact scaffold help code = %d stderr=%q stdout=%q", code, stderr.String(), stdout.String())
	}
	for _, want := range []string{"--kind <kind>", "--path <project-relative-path>", "--out", "artifact catalog"} {
		if !strings.Contains(stdout.String(), want) {
			t.Fatalf("artifact scaffold help = %q, want %q", stdout.String(), want)
		}
	}
}

func TestArtifactScaffoldCatalogPublishesOnlyImplementedKinds(t *testing.T) {
	result := ArtifactScaffoldCatalog()
	if result.Status != "ok" || len(result.Items) != 25 {
		t.Fatalf("artifact scaffold catalog = %#v, want twenty-five kinds", result)
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
		if strings.TrimSpace(fmt.Sprint(entry["usage"])) == "" {
			t.Fatalf("catalog item has no usage: %#v", entry)
		}
		if len(entry["allowed_paths"].([]string)) == 0 {
			t.Fatalf("catalog item has no allowed paths: %#v", entry)
		}
	}
	for _, kind := range []string{
		"alignment",
		"clarification-checkpoints",
		"clarification-evidence-index",
		"constitution",
		"data-model",
		"debug-session",
		"deep-research",
		"deep-research-not-needed",
		"design-brief",
		"design-review",
		"plan-contract",
		"planning-lane-manifest",
		"quick-plan",
		"quick-status",
		"quick-summary",
		"quickstart",
		"references",
		"research",
		"spec-contract",
		"specify-context",
		"specify-draft",
		"task-generation-lane-manifest",
		"ui-brief",
		"ui-reference-notes",
		"workflow-state",
	} {
		if !kinds[kind] {
			t.Fatalf("catalog kinds = %#v, missing %q", kinds, kind)
		}
	}
	if len(kinds) != 25 {
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

	t.Run("deep research missing semantic anchor", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "artifacts/deep-research.md")
		path := filepath.Join(projectRoot, ".specify", "templates", "artifacts", "deep-research.md")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw = bytes.Replace(raw, []byte("<!-- agent-fill:planning_handoff -->"), nil, 1)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "deep-research",
			Path: "specs/001-demo/deep-research.md",
		})
		if result.Status != "invalid" {
			t.Fatalf("incomplete deep research template = %#v, want invalid", result)
		}
	})

	t.Run("design brief readiness", func(t *testing.T) {
		projectRoot := t.TempDir()
		installScaffoldTemplate(t, projectRoot, "design-brief-template.md")
		path := filepath.Join(projectRoot, ".specify", "templates", "design-brief-template.md")
		raw, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		raw = bytes.Replace(raw, []byte("  status: draft"), []byte("  status: approved"), 1)
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			t.Fatal(err)
		}
		result := NewArtifactService(projectRoot).Scaffold(ArtifactScaffoldRequest{
			Kind: "design-brief",
			Path: ".specify/design/design-brief.md",
		})
		if result.Status != "invalid" {
			t.Fatalf("unsafe design brief template = %#v, want invalid", result)
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
