package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"strings"
	"testing"
)

const validDesignForRuntime = `---
design_system:
  schema: spec-kit-design-v1
  name: test-system
  version: 1
  status: approved
  approval:
    status: approved
    direction: direction-a
    review_round: 1
    source_refs:
      - src/app/page.tsx
    visual_refs:
      - .specify/design/previews/round-01.html#direction-a
    preview_sha256: PREVIEW_SHA256
    manifest_sha256: MANIFEST_SHA256
    handoff_ref: .specify/design/previews/round-01.handoff.json
    handoff_sha256: HANDOFF_SHA256
    decision_ids:
      - DS-COLOR-001
      - DS-TYPE-001
      - DS-SPACE-001
      - DS-COMP-001
      - DS-MOTION-001
      - DS-RESP-001
      - DS-CONTENT-001
    handoff_contract_ids:
HANDOFF_CONTRACT_IDS
    capability_profile_ids:
      - web
    specimen_ids:
      - SP-WEB-WORKSPACE-001
      - SP-WEB-CONTROLS-001
      - SP-WEB-COLLECTION-001
  product_context:
    subject: account settings
    audience: account owners
    single_job: update preferences
  direction_contract:
    visual_thesis: compact hierarchy
    content_thesis: real preference values
    interaction_thesis: immediate local feedback
    signature_element: section progress rail
    safe_system_choices:
      - semantic tokens
    creative_risks:
      - compact density
  platforms:
    - web
  capability_profiles:
    - web
  specimens:
    - SP-WEB-WORKSPACE-001
    - SP-WEB-CONTROLS-001
    - SP-WEB-COLLECTION-001
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: app background
      text.primary:
        value: "#111827"
        usage: primary text
    spacing:
      scale.4:
        value: "16px"
        usage: default gap
    radius:
      control:
        value: "6px"
        usage: controls
    typography:
      body.family:
        value: "system-ui"
        usage: body text
    motion:
      duration.fast:
        value: "140ms"
        usage: direct control feedback
      easing.standard:
        value: "cubic-bezier(.2, .8, .2, 1)"
        usage: continuous state change
  color_modes:
    light:
      canvas: "{color.surface.canvas}"
  components:
    button:
      required_states:
        - default
      token_refs:
        background: "{color.surface.canvas}"
        text: "{color.text.primary}"
      decision_refs:
        - DS-COMP-001
  responsive:
    breakpoints:
      compact: "680px"
  content:
    voice_rules:
      - concise and actionable
  decisions:
    - id: DS-COLOR-001
      kind: color
      statement: use accessible semantic color pairs
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: contrast report and visual capture
    - id: DS-TYPE-001
      kind: typography
      statement: preserve compact readable hierarchy
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: resolved font and visual capture
    - id: DS-SPACE-001
      kind: spacing
      statement: preserve the spacing rhythm
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: computed tokens and visual capture
    - id: DS-COMP-001
      kind: component
      statement: preserve component anatomy and states
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: state matrix and structure snapshot
    - id: DS-MOTION-001
      kind: motion
      statement: preserve purposeful feedback and reduced motion
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: runtime capture
    - id: DS-RESP-001
      kind: responsive
      statement: preserve hierarchy across target widths
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: viewport matrix
    - id: DS-CONTENT-001
      kind: content
      statement: preserve representative content density
      source_ref: .specify/design/previews/round-01.html#direction-a
      verification: content evidence and visual capture
  verification:
    required_viewports:
      - "390"
  accessibility:
    contrast_intent: WCAG AA
    focus_visible: required
    keyboard_navigation: required
    reduced_motion: required
---

# Design

## Product Feel

Purposeful and compact.

## Design Direction

Direction A is approved.

## Visual And Interaction Signature

Use the section progress rail.

## Foundations

Use the approved semantic tokens and modes.

## Platforms

Web only.

## Component Rules

Use the tokens.

## Motion Rules

Use purposeful motion and a reduced-motion equivalent.

## Responsive Behavior

Collapse navigation before content.

## Content And Imagery

Use representative content and owned imagery.

## Anti-Patterns

No unrelated styling.

## Design Change Policy

Update this file through sp-design.

## UI QA Checklist

Capture screenshots.

## Reference Fidelity

Bind evidence to the approved preview digest.

## Planned Gaps and Exceptions

None.
`

func TestDesignPreviewApproveFreezesDirectionAndBindsSidecar(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-02.html")

	var scaffoldOut bytes.Buffer
	exit := runDesign([]string{"preview", "--out", preview}, &scaffoldOut)
	if exit != 0 {
		t.Fatalf("preview scaffold exit = %d output=%s", exit, scaffoldOut.String())
	}
	configurePreviewCandidate(t, preview)

	var stdout bytes.Buffer
	exit = runDesign([]string{"approve", preview, "--direction", "direction-c"}, &stdout)
	if exit != 0 {
		t.Fatalf("approve exit = %d output=%s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	approval := env.Data["approval"].(map[string]any)
	if approval["direction_id"] != "direction-c" {
		t.Fatalf("direction_id = %v", approval["direction_id"])
	}
	html := readFile(t, preview)
	if !strings.Contains(html, `data-preview-status="approved"`) || !strings.Contains(html, `data-approved-direction="direction-c"`) {
		t.Fatalf("approved attributes were not written")
	}
	sidecar := strings.TrimSuffix(preview, filepath.Ext(preview)) + ".approval.json"
	if _, err := os.Stat(sidecar); err != nil {
		t.Fatalf("approval sidecar missing: %v", err)
	}
	handoff := strings.TrimSuffix(preview, filepath.Ext(preview)) + ".handoff.json"
	if _, err := os.Stat(handoff); err != nil {
		t.Fatalf("handoff sidecar missing: %v", err)
	}
	if !hexDigestRE.MatchString(fmt.Sprint(approval["handoff_sha256"])) || len(stringList(approval["handoff_contract_ids"])) == 0 {
		t.Fatalf("approval does not bind immutable handoff: %#v", approval)
	}
	if !reflect.DeepEqual(stringList(approval["capability_profile_ids"]), []string{"web"}) || len(stringList(approval["specimen_ids"])) != 3 {
		t.Fatalf("approval does not bind capability profiles and specimens: %#v", approval)
	}
	var handoffPayload map[string]any
	if err := json.Unmarshal([]byte(readFile(t, handoff)), &handoffPayload); err != nil {
		t.Fatal(err)
	}
	direction, _ := handoffPayload["direction"].(map[string]any)
	reproduction, _ := handoffPayload["reproduction"].(map[string]any)
	if handoffPayload["schema"] != designHandoffSchema || direction["id"] != "direction-c" || len(stringList(reproduction["contract_ids"])) == 0 {
		t.Fatalf("handoff does not freeze the selected direction contract: %#v", handoffPayload)
	}
	capabilityModel, _ := reproduction["capability_model"].(map[string]any)
	if !reflect.DeepEqual(stringList(capabilityModel["profile_ids"]), []string{"web"}) {
		t.Fatalf("handoff does not freeze the capability model: %#v", reproduction)
	}
	stdout.Reset()
	exit = runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout)
	if exit != 0 {
		t.Fatalf("approved preview should lint: exit=%d output=%s", exit, stdout.String())
	}

	originalHandoff, err := os.ReadFile(handoff)
	if err != nil {
		t.Fatal(err)
	}
	mutatedHandoff := strings.Replace(string(originalHandoff), `"reproduction_mode": "exact"`, `"reproduction_mode": "platform-adapted"`, 1)
	if err := os.WriteFile(handoff, []byte(mutatedHandoff), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	exit = runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout)
	if exit != 2 {
		t.Fatalf("tampered handoff exit = %d output=%s", exit, stdout.String())
	}
	env = decodeEnvelope(t, stdout.Bytes())
	if !envelopeHasDiagnostic(env, "preview-stale-handoff-binding") || !envelopeHasDiagnostic(env, "preview-stale-handoff-content") {
		t.Fatalf("expected tampered handoff diagnostics, got %#v", env.Items)
	}
	if err := os.WriteFile(handoff, originalHandoff, 0o644); err != nil {
		t.Fatal(err)
	}

	beforeMutation := readFile(t, preview)
	mutated := strings.Replace(beforeMutation, "Direction A freeform canvas", "Direction A changed canvas", 1)
	if mutated == beforeMutation {
		t.Fatal("stale sidecar fixture did not mutate the preview")
	}
	if err := os.WriteFile(preview, []byte(mutated), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	exit = runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout)
	if exit != 2 {
		t.Fatalf("stale sidecar exit = %d output=%s", exit, stdout.String())
	}
	env = decodeEnvelope(t, stdout.Bytes())
	if !envelopeHasDiagnostic(env, "preview-stale-approval-sidecar") {
		t.Fatalf("expected stale sidecar diagnostic, got %#v", env.Items)
	}
}

func TestDesignPreviewApproveRollsBackEveryArtifactWhenPromotionFails(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-03.html")

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview", "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, stdout.String())
	}
	configurePreviewCandidate(t, preview)
	originalPreview := readFile(t, preview)

	originalPromote := promoteTransactionFile
	t.Cleanup(func() { promoteTransactionFile = originalPromote })
	calls := 0
	promoteTransactionFile = func(path string, content []byte, perm os.FileMode) error {
		calls++
		if calls == 2 {
			return fmt.Errorf("injected design approval promote failure")
		}
		return atomicWriteFile(path, content, perm)
	}

	stdout.Reset()
	exit := runDesign([]string{"approve", preview, "--direction", "direction-a"}, &stdout)
	if exit == 0 {
		t.Fatalf("approve unexpectedly succeeded: %s", stdout.String())
	}
	if current := readFile(t, preview); current != originalPreview {
		t.Fatal("preview was not restored after failed approval")
	}
	for _, suffix := range []string{".approval.json", ".handoff.json"} {
		path := strings.TrimSuffix(preview, filepath.Ext(preview)) + suffix
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("partial approval artifact remains at %s: %v", path, err)
		}
	}
}

func TestDesignPreviewManifestRendersDeterministicCandidate(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	manifest := filepath.Join(".specify", "design", "previews", "round-03.manifest.json")
	preview := filepath.Join(".specify", "design", "previews", "round-03.html")
	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-manifest", "--out", manifest}, &stdout); exit != 0 {
		t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
	}
	configured := regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(readFile(t, manifest), "Configured design content")
	if err := os.WriteFile(manifest, []byte(configured), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"preview", "--manifest", manifest, "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview render failed: %d %s", exit, stdout.String())
	}
	content := readFile(t, preview)
	if !strings.Contains(content, `data-preview-status="candidate"`) || !strings.Contains(content, `data-review-round="3"`) {
		t.Fatalf("rendered candidate did not bind round/status")
	}
	if exit := runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout); exit != 0 {
		t.Fatalf("rendered candidate should lint: %d %s", exit, stdout.String())
	}
}

func TestDesignCapabilityProfilesProjectHybridAndRouteNoUI(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	var stdout bytes.Buffer
	if exit := runDesign([]string{"profiles"}, &stdout); exit != 0 {
		t.Fatalf("profiles failed: %d %s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	profiles, _ := env.Data["profiles"].([]any)
	if len(profiles) != 7 {
		t.Fatalf("profile count = %d, want 7", len(profiles))
	}

	manifestPath := filepath.Join(".specify", "design", "previews", "round-12.manifest.json")
	stdout.Reset()
	if exit := runDesign([]string{"preview-manifest", "--profiles", "mobile,cli", "--out", manifestPath}, &stdout); exit != 0 {
		t.Fatalf("hybrid manifest failed: %d %s", exit, stdout.String())
	}
	manifest := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, manifestPath)), &manifest); err != nil {
		t.Fatal(err)
	}
	model, _ := manifest["capability_model"].(map[string]any)
	if !reflect.DeepEqual(stringList(model["profile_ids"]), []string{"mobile", "cli"}) {
		t.Fatalf("profile IDs = %#v", model["profile_ids"])
	}
	specimens, _ := model["specimens"].([]any)
	if len(specimens) != 6 {
		t.Fatalf("specimen count = %d, want 6", len(specimens))
	}
	for _, raw := range manifest["directions"].([]any) {
		direction := raw.(map[string]any)
		if len(stringList(direction["specimen_ids"])) != 6 {
			t.Fatalf("direction specimen coverage = %#v", direction["specimen_ids"])
		}
	}

	noUIPath := filepath.Join(".specify", "design", "previews", "round-13.manifest.json")
	stdout.Reset()
	if exit := runDesign([]string{"preview-manifest", "--profiles", "no-ui", "--out", noUIPath}, &stdout); exit == 0 {
		t.Fatalf("no-ui unexpectedly produced a preview manifest: %s", stdout.String())
	}
	if _, err := os.Stat(noUIPath); !os.IsNotExist(err) {
		t.Fatalf("no-ui manifest should not exist: %v", err)
	}
	if !strings.Contains(stdout.String(), "design_system_status") {
		t.Fatalf("no-ui result lacks explicit route: %s", stdout.String())
	}
}

func TestDesignTemplateLookupUsesGeneratedProjectTemplates(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	template := filepath.Join(".specify", "templates", "design-preview-template.html")
	if err := os.MkdirAll(filepath.Dir(template), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(template, []byte("project template"), 0o644); err != nil {
		t.Fatal(err)
	}

	resolved, err := locateTemplate("design-preview-template.html")
	if err != nil {
		t.Fatal(err)
	}
	want, err := filepath.Abs(template)
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Clean(resolved) != filepath.Clean(want) {
		t.Fatalf("resolved template = %q, want %q", resolved, want)
	}
}

func TestDesignUITargetLintRejectsRemoteRuntimeAndInlineHandlers(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	target := "ui-target.html"
	if exit := runDesign([]string{"ui-target", "--out", target}, &bytes.Buffer{}); exit != 0 {
		t.Fatalf("ui-target scaffold failed: %d", exit)
	}
	content := configureUITargetCandidate(t, target)
	content = strings.Replace(content, `<button type="button" data-width="390"`, `<button type="button" onclick="fetch('/api')" data-width="390"`, 1)
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout bytes.Buffer
	exit := runDesign([]string{"ui-target-lint", target, "--level", "ready"}, &stdout)
	if exit != 2 {
		t.Fatalf("ui-target lint exit = %d output=%s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	if !envelopeHasDiagnostic(env, "ui-target-inline-event-handler") || !envelopeHasDiagnostic(env, "ui-target-forbidden-runtime") {
		t.Fatalf("missing expected diagnostics: %#v", env.Items)
	}
}

func TestDesignExportRendersApprovedDesignAndAllowsLegacyEscapeHatch(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-01.html")
	var scaffoldOut bytes.Buffer
	if exit := runDesign([]string{"preview", "--out", preview}, &scaffoldOut); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, scaffoldOut.String())
	}
	configurePreviewCandidate(t, preview)
	var stdout bytes.Buffer
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-a"}, &stdout); exit != 0 {
		t.Fatalf("approve failed: %d %s", exit, stdout.String())
	}
	approval := decodeEnvelope(t, stdout.Bytes()).Data["approval"].(map[string]any)
	design := strings.ReplaceAll(validDesignForRuntime, "PREVIEW_SHA256", approval["html_sha256"].(string))
	design = strings.ReplaceAll(design, "MANIFEST_SHA256", approval["manifest_sha256"].(string))
	design = strings.ReplaceAll(design, "HANDOFF_SHA256", approval["handoff_sha256"].(string))
	var handoffYAML []string
	for _, id := range stringList(approval["handoff_contract_ids"]) {
		handoffYAML = append(handoffYAML, "      - "+id)
	}
	design = strings.ReplaceAll(design, "HANDOFF_CONTRACT_IDS", strings.Join(handoffYAML, "\n"))
	if err := os.WriteFile("DESIGN.md", []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", "--format", "tailwind"}, &stdout); exit != 0 {
		t.Fatalf("export tailwind failed: %d %s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	content := env.Data["content"].(map[string]any)
	theme := content["theme"].(map[string]any)
	extend := theme["extend"].(map[string]any)
	colors := extend["colors"].(map[string]any)
	if colors["surface-canvas"] != "#ffffff" {
		t.Fatalf("unexpected tailwind color export: %#v", colors)
	}

	legacy := strings.Replace(design, "  status: approved\n", "", 1)
	if err := os.WriteFile("DESIGN.md", []byte(legacy), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", "--format", "json"}, &stdout); exit != 10 {
		t.Fatalf("unapproved export should block, exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", "--format", "json", "--allow-unapproved"}, &stdout); exit != 0 {
		t.Fatalf("legacy export should pass with escape hatch: %d %s", exit, stdout.String())
	}
}

func TestDesignImportWritesReferenceWithoutRootDesign(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	var stdout bytes.Buffer
	exit := runDesign([]string{"import", "https://example.com/style", "--notes", "Dense admin UI with compact tables."}, &stdout)
	if exit != 0 {
		t.Fatalf("import exit=%d output=%s", exit, stdout.String())
	}
	content := readFile(t, filepath.Join(".specify", "design", "references.md"))
	if !strings.Contains(content, "https://example.com/style") || !strings.Contains(content, "Dense admin UI with compact tables.") {
		t.Fatalf("reference content missing source or notes:\n%s", content)
	}
	if _, err := os.Stat("DESIGN.md"); !os.IsNotExist(err) {
		t.Fatalf("import should not create DESIGN.md")
	}
}

func TestDesignChangeScaffoldCreatesChangeLocalContractAndIndex(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	var stdout bytes.Buffer
	exit := runDesign([]string{
		"change",
		"UD-0042",
		"--title", "Orders workspace redesign",
		"--type", "overhaul",
		"--scope", "web:orders/list",
		"--scope", "web:orders/detail",
		"--profiles", "web",
	}, &stdout)
	if exit != 0 {
		t.Fatalf("design change exit=%d output=%s", exit, stdout.String())
	}
	designPath := filepath.Join(".specify", "design", "changes", "UD-0042", "DESIGN.md")
	content := readFile(t, designPath)
	if !strings.Contains(content, "design_change:") || !strings.Contains(content, "schema: spec-kit-ui-design-change-v1") {
		t.Fatalf("change-local contract is missing the new schema:\n%s", content)
	}
	if diagnostics := lintDesignFile(designPath, "structural"); len(diagnostics) != 0 {
		t.Fatalf("change-local contract must pass structural lint: %#v", diagnostics)
	}
	if _, err := os.Stat("DESIGN.md"); !os.IsNotExist(err) {
		t.Fatalf("design change must not create a root DESIGN.md")
	}
	var index map[string]any
	if err := json.Unmarshal([]byte(readFile(t, filepath.Join(".specify", "design", "index.json"))), &index); err != nil {
		t.Fatal(err)
	}
	if index["schema"] != "spec-kit-ui-design-index-v1" {
		t.Fatalf("unexpected design index schema: %#v", index)
	}
	changes, ok := index["changes"].([]any)
	if !ok || len(changes) != 1 || changes[0].(map[string]any)["id"] != "UD-0042" {
		t.Fatalf("unexpected design index changes: %#v", index["changes"])
	}
}

func TestDesignChangeLintRejectsInvalidIterationSource(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	path, err := scaffoldDesignChange(
		"UD-0042",
		"Orders workspace redesign",
		"preserve",
		[]string{"web:orders"},
		[]string{"web"},
		nil,
		nil,
		"",
		"",
	)
	if err != nil {
		t.Fatal(err)
	}
	content := strings.Replace(
		readFile(t, path),
		"iteration_of: null",
		"iteration_of: not-a-change",
		1,
	)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	diagnostics := lintDesignFile(path, "structural")
	for _, diagnostic := range diagnostics {
		if diagnostic.Code == "invalid-design-change-iteration" {
			return
		}
	}
	t.Fatalf("missing invalid-design-change-iteration diagnostic: %#v", diagnostics)
}

func TestDesignRegisterPinsDigestBlocksOverlapAndAppliesSupersedes(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	create := func(id, scope string, supersedes ...string) string {
		t.Helper()
		args := []string{"change", id, "--title", id + " design", "--type", "extension", "--scope", scope, "--profiles", "web"}
		for _, prior := range supersedes {
			args = append(args, "--supersedes", prior)
		}
		var stdout bytes.Buffer
		if exit := runDesign(args, &stdout); exit != 0 {
			t.Fatalf("create %s failed: %d %s", id, exit, stdout.String())
		}
		path := filepath.Join(".specify", "design", "changes", id, "DESIGN.md")
		writeReadyDesignChangeRuntime(t, path, id, []string{scope}, supersedes)
		return path
	}

	first := create("UD-0042", "web:orders")
	var stdout bytes.Buffer
	if exit := runDesign([]string{"register", first}, &stdout); exit != 0 {
		t.Fatalf("register first failed: %d %s", exit, stdout.String())
	}
	firstBytes, err := os.ReadFile(first)
	if err != nil {
		t.Fatal(err)
	}
	wantDigest := fmt.Sprintf("%x", sha256.Sum256(firstBytes))
	index := readDesignChangeIndexRuntime(t)
	firstRecord := designChangeRecordRuntime(t, index, "UD-0042")
	if firstRecord["status"] != "approved" || firstRecord["approval_sha256"] != wantDigest {
		t.Fatalf("first record was not pinned: %#v", firstRecord)
	}

	overlapping := create("UD-0043", "web:orders/list")
	stdout.Reset()
	if exit := runDesign([]string{"register", overlapping}, &stdout); exit == 0 || !strings.Contains(stdout.String(), "overlaps approved design change UD-0042") {
		t.Fatalf("ambiguous overlap must block: exit=%d output=%s", exit, stdout.String())
	}

	replacement := create("UD-0044", "web:orders", "UD-0042")
	stdout.Reset()
	if exit := runDesign([]string{"register", replacement}, &stdout); exit != 0 {
		t.Fatalf("register replacement failed: %d %s", exit, stdout.String())
	}
	index = readDesignChangeIndexRuntime(t)
	firstRecord = designChangeRecordRuntime(t, index, "UD-0042")
	replacementRecord := designChangeRecordRuntime(t, index, "UD-0044")
	if firstRecord["status"] != "superseded" || firstRecord["superseded_by"] != "UD-0044" {
		t.Fatalf("prior change was not superseded: %#v", firstRecord)
	}
	if replacementRecord["status"] != "approved" {
		t.Fatalf("replacement was not approved: %#v", replacementRecord)
	}
}

func TestDesignIterateCreatesDigestPinnedSuccessorWithoutMutatingSource(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	source, sourceDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	sourceBefore := readFile(t, source)

	var stdout bytes.Buffer
	exit := runDesign([]string{
		"iterate", "UD-0042", "UD-0043",
		"--title", "Orders list refinement",
		"--scope", "web:orders/list",
	}, &stdout)
	if exit != 0 {
		t.Fatalf("design iterate exit=%d output=%s", exit, stdout.String())
	}
	if got := readFile(t, source); got != sourceBefore {
		t.Fatalf("design iterate mutated its registered source")
	}

	env := decodeEnvelope(t, stdout.Bytes())
	successor := filepath.FromSlash(env.Data["path"].(string))
	doc, err := parseDesignMarkdown(readFile(t, successor), successor)
	if err != nil {
		t.Fatal(err)
	}
	relationships := doc.DesignSystem["relationships"].(map[string]any)
	if relationships["iteration_of"] != "UD-0042" {
		t.Fatalf("iteration_of = %#v, want UD-0042", relationships["iteration_of"])
	}
	wantBaseline := ".specify/design/changes/UD-0042/DESIGN.md#sha256=" + sourceDigest
	if got := stringList(doc.DesignSystem["baseline_refs"]); !reflect.DeepEqual(got, []string{wantBaseline}) {
		t.Fatalf("baseline_refs = %#v, want exact registered source", got)
	}
	if got := stringList(relationships["supersedes"]); !reflect.DeepEqual(got, []string{"UD-0042"}) {
		t.Fatalf("supersedes = %#v, want source change", got)
	}
	record := designChangeRecordRuntime(t, readDesignChangeIndexRuntime(t), "UD-0043")
	if record["iteration_of"] != "UD-0042" || record["basis_sha256"] != sourceDigest {
		t.Fatalf("successor index record did not pin its source: %#v", record)
	}
}

func TestDesignRegisterPartiallySupersedesOnlyIntersectingScope(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, sourceDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	successor := createDesignIterationRuntime(t, "UD-0042", "UD-0043", "web:orders/list")
	writeReadyDesignIterationRuntime(t, successor, "UD-0043", []string{"web:orders/list"}, "UD-0042", sourceDigest)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"register", successor}, &stdout); exit != 0 {
		t.Fatalf("register partial successor failed: %d %s", exit, stdout.String())
	}
	index := readDesignChangeIndexRuntime(t)
	parent := designChangeRecordRuntime(t, index, "UD-0042")
	if parent["status"] != "approved" {
		t.Fatalf("partial iteration retired the whole parent: %#v", parent)
	}
	wantCovered := []any{map[string]any{"scope": "web:orders/list", "by": "UD-0043"}}
	if !reflect.DeepEqual(parent["superseded_scopes"], wantCovered) {
		t.Fatalf("superseded_scopes = %#v, want %#v", parent["superseded_scopes"], wantCovered)
	}

	if got := resolveDesignIDsRuntime(t, "web:orders/list"); !reflect.DeepEqual(got, []string{"UD-0043"}) {
		t.Fatalf("list resolution = %#v, want only successor", got)
	}
	if got := resolveDesignIDsRuntime(t, "web:orders/detail"); !reflect.DeepEqual(got, []string{"UD-0042"}) {
		t.Fatalf("detail resolution = %#v, want parent", got)
	}
	if got := resolveDesignIDsRuntime(t, "web:orders"); !reflect.DeepEqual(got, []string{"UD-0043", "UD-0042"}) {
		t.Fatalf("broad resolution = %#v, want explicit composite candidates", got)
	}
}

func TestDesignIterateRejectsScopeAlreadySupersededOnSource(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, sourceDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	successor := createDesignIterationRuntime(t, "UD-0042", "UD-0043", "web:orders/list")
	writeReadyDesignIterationRuntime(t, successor, "UD-0043", []string{"web:orders/list"}, "UD-0042", sourceDigest)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"register", successor}, &stdout); exit != 0 {
		t.Fatalf("register partial successor failed: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{
		"iterate", "UD-0042", "UD-0044",
		"--title", "Invalid list iteration",
		"--scope", "web:orders/list/table",
	}, &stdout); exit == 0 || !strings.Contains(stdout.String(), "no longer active") {
		t.Fatalf("superseded source scope must block: exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{
		"iterate", "UD-0042", "UD-0044",
		"--title", "Orders detail refinement",
		"--scope", "web:orders/detail",
	}, &stdout); exit != 0 {
		t.Fatalf("remaining active source scope should iterate: exit=%d output=%s", exit, stdout.String())
	}
}

func TestDesignDiffReportsScopeLineageAndStableDecisionChanges(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, sourceDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	successor := createDesignIterationRuntime(t, "UD-0042", "UD-0043", "web:orders/list")
	writeReadyDesignIterationRuntime(t, successor, "UD-0043", []string{"web:orders/list"}, "UD-0042", sourceDigest)
	updated := strings.Replace(readFile(t, successor), "use accessible semantic color pairs", "use stronger accessible semantic color pairs", 1)
	if err := os.WriteFile(successor, []byte(updated), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout bytes.Buffer
	if exit := runDesign([]string{"register", successor}, &stdout); exit != 0 {
		t.Fatalf("register successor failed: %d %s", exit, stdout.String())
	}

	stdout.Reset()
	if exit := runDesign([]string{"diff", "UD-0042", "UD-0043"}, &stdout); exit != 0 {
		t.Fatalf("design diff failed: %d %s", exit, stdout.String())
	}
	diff := decodeEnvelope(t, stdout.Bytes()).Data["diff"].(map[string]any)
	if diff["schema"] != "spec-kit-ui-design-diff-v1" {
		t.Fatalf("unexpected diff schema: %#v", diff)
	}
	lineage := diff["lineage"].(map[string]any)
	if lineage["direct_iteration"] != true || lineage["supersedes_source"] != true {
		t.Fatalf("diff lineage = %#v, want direct explicit iteration", lineage)
	}
	decisions := diff["decisions"].(map[string]any)
	if !reflect.DeepEqual(stringList(decisions["changed"]), []string{"DS-COLOR-001"}) {
		t.Fatalf("changed decisions = %#v", decisions["changed"])
	}
	if !containsString(stringList(diff["changed_sections"]), "decisions") {
		t.Fatalf("changed sections = %#v, want decisions", diff["changed_sections"])
	}
}

func TestDesignImpactClassesCoverUIDimensionsAndStableContractIDs(t *testing.T) {
	diff := map[string]any{
		"changed_sections": []string{"components", "content", "responsive", "verification"},
		"decisions": map[string]any{
			"added": []string{"DS-COMP-002"}, "removed": []string{},
			"changed": []string{"DS-COMP-001"}, "retained": []string{},
		},
		"handoff_contracts": map[string]any{
			"added": []string{"DH-COMP-002"}, "removed": []string{"DH-COMP-001"}, "retained": []string{},
		},
	}
	want := []string{
		"visual", "interaction", "component", "responsive", "content",
		"verification", "design-decision", "handoff-contract",
	}
	if got := designImpactClasses(diff); !reflect.DeepEqual(got, want) {
		t.Fatalf("impact classes = %#v, want %#v", got, want)
	}
}

func TestDesignAdoptUsesExpectedChangeCASAndPreservesRebindHistory(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	parent, parentDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	parentContract := writeDesignContractRuntime(t, parent)
	bindingRef := ".specify/features/001-orders/spec-contract.json"
	parentBindingDigest := writeDesignBindingRuntime(t, bindingRef, "UD-0042", parentDigest, parentContract)
	approvedContract := readFile(t, parentContract)
	var tamperedContract map[string]any
	if err := json.Unmarshal([]byte(approvedContract), &tamperedContract); err != nil {
		t.Fatal(err)
	}
	tamperedContract["title"] = "tampered export"
	tamperedRaw, err := json.MarshalIndent(tamperedContract, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(parentContract, append(tamperedRaw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	initialAdoption := []string{
		"adopt", "feature:001-orders",
		"--change", "UD-0042",
		"--scope", "web:orders/detail",
		"--mode", "formal",
		"--binding-ref", bindingRef,
		"--binding-sha256", parentBindingDigest,
		"--expected-change", "none",
	}
	if exit := runDesign(initialAdoption, &stdout); exit == 0 || !strings.Contains(stdout.String(), "does not match the registered design") {
		t.Fatalf("tampered design export must block adoption: exit=%d output=%s", exit, stdout.String())
	}
	if err := os.WriteFile(parentContract, []byte(approvedContract), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign(initialAdoption, &stdout); exit != 0 {
		t.Fatalf("initial design adoption failed: %d %s", exit, stdout.String())
	}

	successor := createDesignIterationRuntime(t, "UD-0042", "UD-0043", "web:orders/detail")
	writeReadyDesignIterationRuntime(t, successor, "UD-0043", []string{"web:orders/detail"}, "UD-0042", parentDigest)
	updated := strings.Replace(readFile(t, successor), "use accessible semantic color pairs", "use stronger accessible semantic color pairs", 1)
	if err := os.WriteFile(successor, []byte(updated), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"register", successor}, &stdout); exit != 0 {
		t.Fatalf("register successor failed: %d %s", exit, stdout.String())
	}
	successorDigest := designChangeRecordRuntime(t, readDesignChangeIndexRuntime(t), "UD-0043")["approval_sha256"].(string)
	successorContract := writeDesignContractRuntime(t, successor)
	successorBindingDigest := writeDesignBindingRuntime(t, bindingRef, "UD-0043", successorDigest, successorContract)

	wrongExpected := []string{
		"adopt", "feature:001-orders",
		"--change", "UD-0043",
		"--scope", "web:orders/detail",
		"--mode", "formal",
		"--binding-ref", bindingRef,
		"--binding-sha256", successorBindingDigest,
		"--expected-change", "none",
	}
	stdout.Reset()
	if exit := runDesign(wrongExpected, &stdout); exit == 0 || !strings.Contains(stdout.String(), "expected current change") {
		t.Fatalf("stale adoption CAS must block: exit=%d output=%s", exit, stdout.String())
	}
	indexBeforeImpact := readFile(t, filepath.Join(".specify", "design", "index.json"))
	stdout.Reset()
	if exit := runDesign([]string{
		"impact", "feature:001-orders",
		"--change", "UD-0043",
		"--scope", "web:orders/detail",
		"--mode", "formal",
		"--expected-change", "none",
	}, &stdout); exit == 0 || !strings.Contains(stdout.String(), "expected current change") {
		t.Fatalf("stale impact CAS must block: exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{
		"impact", "feature:001-orders",
		"--change", "UD-0043",
		"--scope", "web:orders/detail",
		"--mode", "formal",
		"--expected-change", "UD-0042",
	}, &stdout); exit != 0 {
		t.Fatalf("design impact failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, filepath.Join(".specify", "design", "index.json")); got != indexBeforeImpact {
		t.Fatal("design impact mutated the design index")
	}
	impact := decodeEnvelope(t, stdout.Bytes()).Data["impact"].(map[string]any)
	if impact["schema"] != "spec-kit-ui-design-impact-v1" || impact["current_change_id"] != "UD-0042" || impact["candidate_change_id"] != "UD-0043" {
		t.Fatalf("impact identity = %#v", impact)
	}
	if !reflect.DeepEqual(stringList(impact["impact_classes"]), []string{"visual", "interaction", "design-decision"}) {
		t.Fatalf("impact classes = %#v", impact["impact_classes"])
	}
	if !reflect.DeepEqual(stringList(impact["affected_decision_ids"]), []string{"DS-COLOR-001"}) || len(stringList(impact["affected_handoff_contract_ids"])) != 0 {
		t.Fatalf("stable contract impact = DS %#v DH %#v", impact["affected_decision_ids"], impact["affected_handoff_contract_ids"])
	}
	if !reflect.DeepEqual(stringList(impact["changed_sections"]), []string{"decisions"}) || impact["reconcile_from"] != "plan" {
		t.Fatalf("impact reconciliation boundary = %#v", impact)
	}
	if !reflect.DeepEqual(stringList(impact["preserved_bindings"]), []string{"feature.ui_brief", "implementation.completed_work", "review.unaffected_scope_evidence"}) {
		t.Fatalf("preserved bindings = %#v", impact["preserved_bindings"])
	}
	if !reflect.DeepEqual(stringList(impact["invalidated_bindings"]), []string{"plan.ui_design_contract", "tasks.ui_contracts", "review.affected_scope_evidence"}) {
		t.Fatalf("invalidated bindings = %#v", impact["invalidated_bindings"])
	}
	if !reflect.DeepEqual(stringList(impact["reconciliation_actions"]), []string{"recompile_plan_ui_design_contract", "recompile_task_ui_contracts", "recapture_affected_review_evidence"}) || !hexDigestRE.MatchString(fmt.Sprint(impact["impact_sha256"])) {
		t.Fatalf("impact actions/digest = %#v", impact)
	}
	wrongExpected[len(wrongExpected)-1] = "UD-0042"
	stdout.Reset()
	if exit := runDesign(wrongExpected, &stdout); exit != 0 {
		t.Fatalf("explicit design rebind failed: %d %s", exit, stdout.String())
	}

	index := readDesignChangeIndexRuntime(t)
	adoptions := index["adoptions"].([]any)
	if len(adoptions) != 2 {
		t.Fatalf("adoption history = %#v, want two receipts", adoptions)
	}
	first := adoptions[0].(map[string]any)
	second := adoptions[1].(map[string]any)
	if first["status"] != "superseded" || first["superseded_by_revision"] != float64(2) {
		t.Fatalf("first adoption receipt was not retained: %#v", first)
	}
	if second["status"] != "current" || second["revision"] != float64(2) || second["previous_change_id"] != "UD-0042" {
		t.Fatalf("second adoption receipt is incomplete: %#v", second)
	}
	if second["design_change_id"] != "UD-0043" || second["design_change_sha256"] != successorDigest {
		t.Fatalf("second adoption receipt does not retain the exact design binding: %#v", second)
	}
	for _, field := range []string{
		"impact_sha256", "impact_classes", "preserved_bindings", "invalidated_bindings",
		"reconcile_from", "reconciliation_actions", "changed_sections",
		"affected_decision_ids", "affected_handoff_contract_ids",
	} {
		if !reflect.DeepEqual(second[field], impact[field]) {
			t.Fatalf("adoption receipt %s = %#v, want impact %#v", field, second[field], impact[field])
		}
	}
}

func TestDesignQuickAdoptRequiresConfirmedExactStatusBinding(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	designPath, designDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	contractPath := writeDesignContractRuntime(t, designPath)
	workspace := filepath.Join(".planning", "quick", "001-orders")
	if err := os.MkdirAll(workspace, 0o755); err != nil {
		t.Fatal(err)
	}
	bindingRef := filepath.ToSlash(filepath.Join(workspace, "STATUS.md"))

	writeStatus := func(confirmed bool, boundChange, boundScope, bindingShape string) string {
		t.Helper()
		bindingBody := fmt.Sprintf(`ui_design_binding:
  scope: %s
  design_change_id: %s
  design_change_ref: .specify/design/changes/UD-0042/DESIGN.md
  design_change_sha256: %s
  design_contract_ref: %s
`, boundScope, boundChange, designDigest, filepath.ToSlash(contractPath))
		if bindingShape == "flat" {
			bindingBody = fmt.Sprintf(`scope: %s
design_change_id: %s
design_change_ref: .specify/design/changes/UD-0042/DESIGN.md
design_change_sha256: %s
design_contract_ref: %s
`, boundScope, boundChange, designDigest, filepath.ToSlash(contractPath))
		} else if bindingShape == "masked-mismatch" {
			bindingBody += "\n## Notes\n\ndesign_change_id: UD-0042\n"
		} else if bindingShape == "case-duplicate" {
			bindingBody += "\n## UI design binding\n\n" + bindingBody
		} else if bindingShape == "duplicate-key" {
			bindingBody = strings.Replace(
				bindingBody,
				"  scope: "+boundScope+"\n",
				"  scope: web:orders/summary\n  scope: "+boundScope+"\n",
				1,
			)
		}
		body := fmt.Sprintf(`---
understanding_confirmed: %t
---

## UI Design Binding

%s
note: exact source UD-0042
`, confirmed, bindingBody)
		if err := os.WriteFile(filepath.FromSlash(bindingRef), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
		digest := sha256.Sum256([]byte(body))
		return fmt.Sprintf("%x", digest)
	}
	writeConfirmation := func(state, boundChange string) {
		t.Helper()
		decision := quickAdoptionTestDecision(designDigest, filepath.ToSlash(contractPath), boundChange)
		digest, err := computeQuickConfirmationDigest(decision)
		if err != nil {
			t.Fatal(err)
		}
		doc := quickConfirmationDoc{
			Schema:             quickConfirmationSchema,
			ConfirmationState:  state,
			ConfirmationDigest: digest,
			Decision:           decision,
		}
		body, err := json.Marshal(doc)
		if err != nil {
			t.Fatal(err)
		}
		body = append(body, '\n')
		if err := os.WriteFile(filepath.Join(workspace, "confirmation.json"), body, 0o644); err != nil {
			t.Fatal(err)
		}
	}
	adopt := func(digest string) (int, string) {
		t.Helper()
		var stdout bytes.Buffer
		exit := runDesign([]string{
			"adopt", "quick:001-orders",
			"--change", "UD-0042",
			"--scope", "web:orders/detail",
			"--mode", "quick",
			"--binding-ref", bindingRef,
			"--binding-sha256", digest,
			"--expected-change", "none",
		}, &stdout)
		return exit, stdout.String()
	}

	writeConfirmation("staged", "UD-0042")
	if exit, output := adopt(writeStatus(false, "UD-0042", "web:orders/detail", "nested")); exit == 0 || !strings.Contains(output, "checkpoint must be confirmed") {
		t.Fatalf("unconfirmed quick adoption must block: exit=%d output=%s", exit, output)
	}
	writeConfirmation("confirmed", "UD-9999")
	if exit, output := adopt(writeStatus(true, "UD-0042", "web:orders/detail", "nested")); exit == 0 || !strings.Contains(output, "confirmed UI design binding") {
		t.Fatalf("unconfirmed replacement binding must block: exit=%d output=%s", exit, output)
	}
	writeConfirmation("confirmed", "UD-0042")
	if exit, output := adopt(writeStatus(true, "UD-0042", "web:orders/detail", "flat")); exit == 0 || !strings.Contains(output, "ui_design_binding mapping") {
		t.Fatalf("quick adoption without ui_design_binding container must block: exit=%d output=%s", exit, output)
	}
	if exit, output := adopt(writeStatus(true, "UD-9999", "web:orders/detail", "nested")); exit == 0 || !strings.Contains(output, "exact registered change fields") {
		t.Fatalf("mismatched markdown binding must block: exit=%d output=%s", exit, output)
	}
	if exit, output := adopt(writeStatus(true, "UD-0042", "web:orders/summary", "nested")); exit == 0 || !strings.Contains(output, "exact registered change fields") {
		t.Fatalf("mismatched markdown binding scope must block: exit=%d output=%s", exit, output)
	}
	if exit, output := adopt(writeStatus(true, "UD-0042", "web:orders/detail", "nested")); exit != 0 {
		t.Fatalf("confirmed exact quick adoption failed: exit=%d output=%s", exit, output)
	}
	index := readDesignChangeIndexRuntime(t)
	receipt := index["adoptions"].([]any)[0].(map[string]any)
	if len(stringList(receipt["preserved_bindings"])) != 0 || len(stringList(receipt["invalidated_bindings"])) != 0 {
		t.Fatalf("initial quick adoption must not invalidate existing work: %#v", receipt)
	}
	if receipt["reconcile_from"] != "quick-checkpoint" || !reflect.DeepEqual(stringList(receipt["reconciliation_actions"]), []string{"confirm_quick_design_binding", "compile_quick_ui_work_items"}) {
		t.Fatalf("initial quick reconciliation = %#v", receipt)
	}
}

func TestDesignQuickAdoptRejectsStatusBindingThatDiffersFromConfirmation(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	designPath, designDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	contractPath := filepath.ToSlash(writeDesignContractRuntime(t, designPath))
	workspace := filepath.Join(".planning", "quick", "001-orders")
	if err := os.MkdirAll(workspace, 0o755); err != nil {
		t.Fatal(err)
	}
	bindingRef := filepath.ToSlash(filepath.Join(workspace, "STATUS.md"))
	statusBody := fmt.Sprintf(`---
understanding_confirmed: true
---

## UI Design Binding

ui_design_binding:
  scope: web:orders/detail
  design_change_id: UD-9999
  design_change_ref: .specify/design/changes/UD-0042/DESIGN.md
  design_change_sha256: %s
  design_contract_ref: %s

## Notes

design_change_id: UD-0042
`, designDigest, contractPath)
	if err := os.WriteFile(filepath.FromSlash(bindingRef), []byte(statusBody), 0o644); err != nil {
		t.Fatal(err)
	}
	decision := quickAdoptionTestDecision(designDigest, contractPath, "UD-0042")
	confirmationDigest, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	confirmationBody, err := json.Marshal(quickConfirmationDoc{
		Schema:             quickConfirmationSchema,
		ConfirmationState:  "confirmed",
		ConfirmationDigest: confirmationDigest,
		Decision:           decision,
	})
	if err != nil {
		t.Fatal(err)
	}
	confirmationBody = append(confirmationBody, '\n')
	if err := os.WriteFile(filepath.Join(workspace, "confirmation.json"), confirmationBody, 0o644); err != nil {
		t.Fatal(err)
	}
	digest := sha256.Sum256([]byte(statusBody))
	var stdout bytes.Buffer
	exit := runDesign([]string{
		"adopt", "quick:001-orders",
		"--change", "UD-0042",
		"--scope", "web:orders/detail",
		"--mode", "quick",
		"--binding-ref", bindingRef,
		"--binding-sha256", fmt.Sprintf("%x", digest),
		"--expected-change", "none",
	}, &stdout)
	if output := stdout.String(); exit == 0 || !strings.Contains(output, "exact-match confirmation.json") {
		t.Fatalf("quick adoption with mismatched binding copies must block: exit=%d output=%s", exit, output)
	}
}

func TestDesignQuickAdoptRejectsAmbiguousStatusAndInvalidConfirmationDigest(t *testing.T) {
	tests := []struct {
		name              string
		statusShape       string
		confirmationShape string
		wantError         string
	}{
		{name: "case-insensitive duplicate heading", statusShape: "case-duplicate", confirmationShape: "valid", wantError: "exactly one"},
		{name: "duplicate binding key", statusShape: "duplicate-key", confirmationShape: "valid", wantError: "scope"},
		{name: "minimal forged digest", statusShape: "nested", confirmationShape: "minimal-forged", wantError: "confirmation digest"},
		{name: "minimal self-consistent digest", statusShape: "nested", confirmationShape: "minimal-self-consistent", wantError: "decision.goal"},
		{name: "decision changed after digest", statusShape: "nested", confirmationShape: "tampered-decision", wantError: "confirmation digest"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmp := t.TempDir()
			withCwd(t, tmp)
			designPath, designDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
			contractPath := filepath.ToSlash(writeDesignContractRuntime(t, designPath))
			workspace := filepath.Join(".planning", "quick", "001-orders")
			if err := os.MkdirAll(workspace, 0o755); err != nil {
				t.Fatal(err)
			}
			bindingRef := filepath.ToSlash(filepath.Join(workspace, "STATUS.md"))
			bindingBody := fmt.Sprintf(`ui_design_binding:
  scope: web:orders/detail
  design_change_id: UD-0042
  design_change_ref: .specify/design/changes/UD-0042/DESIGN.md
  design_change_sha256: %s
  design_contract_ref: %s
`, designDigest, contractPath)
			switch tt.statusShape {
			case "case-duplicate":
				bindingBody += "\n## UI design binding\n\n" + bindingBody
			case "duplicate-key":
				bindingBody = strings.Replace(
					bindingBody,
					"  scope: web:orders/detail\n",
					"  scope: web:orders/summary\n  scope: web:orders/detail\n",
					1,
				)
			}
			statusBody := fmt.Sprintf(`---
understanding_confirmed: true
---

## UI Design Binding

%s`, bindingBody)
			if err := os.WriteFile(filepath.FromSlash(bindingRef), []byte(statusBody), 0o644); err != nil {
				t.Fatal(err)
			}

			decision := quickAdoptionTestDecision(designDigest, contractPath, "UD-0042")
			digest, err := computeQuickConfirmationDigest(decision)
			if err != nil {
				t.Fatal(err)
			}
			var confirmation any
			switch tt.confirmationShape {
			case "minimal-forged":
				confirmation = map[string]any{
					"schema":              quickConfirmationSchema,
					"confirmation_state":  "confirmed",
					"confirmation_digest": strings.Repeat("c", 64),
					"decision": map[string]any{
						"ui_confirmation": decision.UIConfirmation,
					},
				}
			case "minimal-self-consistent":
				minimalDecision := quickConfirmationDecision{UIConfirmation: decision.UIConfirmation}
				minimalDigest, err := computeQuickConfirmationDigest(minimalDecision)
				if err != nil {
					t.Fatal(err)
				}
				confirmation = quickConfirmationDoc{
					Schema:             quickConfirmationSchema,
					ConfirmationState:  "confirmed",
					ConfirmationDigest: minimalDigest,
					Decision:           minimalDecision,
				}
			case "tampered-decision":
				decision.Goal = "Tampered after confirmation"
				confirmation = quickConfirmationDoc{
					Schema:             quickConfirmationSchema,
					ConfirmationState:  "confirmed",
					ConfirmationDigest: digest,
					Decision:           decision,
				}
			default:
				confirmation = quickConfirmationDoc{
					Schema:             quickConfirmationSchema,
					ConfirmationState:  "confirmed",
					ConfirmationDigest: digest,
					Decision:           decision,
				}
			}
			confirmationBody, err := json.Marshal(confirmation)
			if err != nil {
				t.Fatal(err)
			}
			confirmationBody = append(confirmationBody, '\n')
			if err := os.WriteFile(filepath.Join(workspace, "confirmation.json"), confirmationBody, 0o644); err != nil {
				t.Fatal(err)
			}

			digestBytes := sha256.Sum256([]byte(statusBody))
			var stdout bytes.Buffer
			exit := runDesign([]string{
				"adopt", "quick:001-orders",
				"--change", "UD-0042",
				"--scope", "web:orders/detail",
				"--mode", "quick",
				"--binding-ref", bindingRef,
				"--binding-sha256", fmt.Sprintf("%x", digestBytes),
				"--expected-change", "none",
			}, &stdout)
			if output := stdout.String(); exit == 0 || !strings.Contains(output, tt.wantError) {
				t.Fatalf("quick adoption bypass must block: exit=%d want=%q output=%s", exit, tt.wantError, output)
			}
		})
	}
}

func quickAdoptionTestDecision(designDigest, contractPath, boundChange string) quickConfirmationDecision {
	return quickConfirmationDecision{
		Goal:              "Adopt the approved orders UI",
		UserVisibleResult: "The orders detail uses the approved design",
		Scope: quickConfirmationScope{
			Include: []string{"web:orders/detail"},
			Exclude: []string{},
			Defer:   []string{},
		},
		Items: []quickConfirmationItem{
			{
				ID:          "Q1",
				Deliverable: "Apply the approved orders UI",
				DependsOn:   []string{},
				Acceptance:  "The exact design binding is used",
				WriteScope:  []string{"src/orders"},
			},
		},
		ReconfirmationTrigger: "The approved design binding changes",
		UIConfirmation: map[string]any{
			"applicable": true,
			"design_binding": map[string]any{
				"scope":                "web:orders/detail",
				"design_change_id":     boundChange,
				"design_change_ref":    ".specify/design/changes/UD-0042/DESIGN.md",
				"design_change_sha256": designDigest,
				"design_contract_ref":  contractPath,
			},
		},
	}
}

func createRegisteredDesignChangeRuntime(t *testing.T, changeID, scope string) (string, string) {
	t.Helper()
	var stdout bytes.Buffer
	if exit := runDesign([]string{"change", changeID, "--title", changeID + " design", "--type", "extension", "--scope", scope, "--profiles", "web"}, &stdout); exit != 0 {
		t.Fatalf("create %s failed: %d %s", changeID, exit, stdout.String())
	}
	path := filepath.Join(".specify", "design", "changes", changeID, "DESIGN.md")
	writeReadyDesignChangeRuntime(t, path, changeID, []string{scope}, nil)
	stdout.Reset()
	if exit := runDesign([]string{"register", path}, &stdout); exit != 0 {
		t.Fatalf("register %s failed: %d %s", changeID, exit, stdout.String())
	}
	record := designChangeRecordRuntime(t, readDesignChangeIndexRuntime(t), changeID)
	return path, record["approval_sha256"].(string)
}

func createDesignIterationRuntime(t *testing.T, sourceID, changeID, scope string) string {
	t.Helper()
	var stdout bytes.Buffer
	if exit := runDesign([]string{"iterate", sourceID, changeID, "--title", changeID + " iteration", "--scope", scope}, &stdout); exit != 0 {
		t.Fatalf("iterate %s failed: %d %s", changeID, exit, stdout.String())
	}
	return filepath.Join(".specify", "design", "changes", changeID, "DESIGN.md")
}

func writeReadyDesignIterationRuntime(t *testing.T, designPath, changeID string, scopes []string, sourceID, sourceDigest string) {
	t.Helper()
	writeReadyDesignChangeRuntime(t, designPath, changeID, scopes, []string{sourceID})
	content := readFile(t, designPath)
	baseline := ".specify/design/changes/" + sourceID + "/DESIGN.md#sha256=" + sourceDigest
	content = strings.Replace(content, "  baseline_refs: []", "  baseline_refs: [\""+baseline+"\"]", 1)
	content = strings.Replace(content, "  relationships:\n", "  relationships:\n    iteration_of: "+sourceID+"\n", 1)
	if err := os.WriteFile(designPath, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func resolveDesignIDsRuntime(t *testing.T, scope string) []string {
	t.Helper()
	var stdout bytes.Buffer
	if exit := runDesign([]string{"resolve", "--scope", scope}, &stdout); exit != 0 {
		t.Fatalf("resolve %s failed: %d %s", scope, exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	ids := make([]string, 0, len(env.Items))
	for _, raw := range env.Items {
		ids = append(ids, raw.(map[string]any)["id"].(string))
	}
	return ids
}

func writeDesignContractRuntime(t *testing.T, designPath string) string {
	t.Helper()
	rendered, err := exportDesignSystem(designPath, "json", true)
	if err != nil {
		t.Fatal(err)
	}
	contract := filepath.Join(filepath.Dir(designPath), "design-contract.json")
	if err := os.WriteFile(contract, []byte(rendered), 0o644); err != nil {
		t.Fatal(err)
	}
	return filepath.ToSlash(contract)
}

func writeDesignBindingRuntime(t *testing.T, bindingRef, changeID, digest, contractRef string) string {
	t.Helper()
	payload := map[string]any{
		"design_change_id":     changeID,
		"design_change_ref":    ".specify/design/changes/" + changeID + "/DESIGN.md",
		"design_change_sha256": digest,
		"design_contract_ref":  contractRef,
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(bindingRef), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(bindingRef, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	return fmt.Sprintf("%x", sha256.Sum256(append(raw, '\n')))
}

func writeReadyDesignChangeRuntime(t *testing.T, designPath, changeID string, scopes, supersedes []string) {
	t.Helper()
	if supersedes == nil {
		supersedes = []string{}
	}
	preview := filepath.Join(filepath.Dir(designPath), "previews", "round-01.html")
	templatePath, err := locateTemplate("design-preview-template.html")
	if err != nil {
		t.Fatal(err)
	}
	template, err := os.ReadFile(templatePath)
	if err != nil {
		t.Fatal(err)
	}
	content := string(template)
	if err := os.MkdirAll(filepath.Dir(preview), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(preview, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	configurePreviewCandidate(t, preview)
	var stdout bytes.Buffer
	stdout.Reset()
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-a"}, &stdout); exit != 0 {
		t.Fatalf("approve failed: %d %s", exit, stdout.String())
	}
	approval := decodeEnvelope(t, stdout.Bytes()).Data["approval"].(map[string]any)
	scopeJSON, _ := json.Marshal(scopes)
	supersedesJSON, _ := json.Marshal(supersedes)
	header := "design_change:\n" +
		"  schema: spec-kit-ui-design-change-v1\n" +
		"  id: " + changeID + "\n" +
		"  title: " + changeID + " approved design\n" +
		"  change_type: extension\n" +
		"  scope:\n" +
		"    surfaces: " + string(scopeJSON) + "\n" +
		"    entrypoints: []\n" +
		"    states: []\n" +
		"    platforms: [\"web\"]\n" +
		"  baseline_refs: []\n" +
		"  relationships:\n" +
		"    supersedes: " + string(supersedesJSON) + "\n" +
		"    depends_on: []\n" +
		"    conflicts_with: []\n" +
		"  constraints:\n" +
		"    must_preserve: []\n" +
		"    may_adapt: []\n" +
		"    must_not: []\n"
	design := strings.Replace(validDesignForRuntime, "design_system:\n  schema: spec-kit-design-v1\n", header, 1)
	design = strings.ReplaceAll(design, ".specify/design/previews/round-01.html", "previews/round-01.html")
	design = strings.ReplaceAll(design, ".specify/design/previews/round-01.handoff.json", "previews/round-01.handoff.json")
	design = strings.ReplaceAll(design, "PREVIEW_SHA256", approval["html_sha256"].(string))
	design = strings.ReplaceAll(design, "MANIFEST_SHA256", approval["manifest_sha256"].(string))
	design = strings.ReplaceAll(design, "HANDOFF_SHA256", approval["handoff_sha256"].(string))
	var handoffYAML []string
	for _, id := range stringList(approval["handoff_contract_ids"]) {
		handoffYAML = append(handoffYAML, "      - "+id)
	}
	design = strings.ReplaceAll(design, "HANDOFF_CONTRACT_IDS", strings.Join(handoffYAML, "\n"))
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readDesignChangeIndexRuntime(t *testing.T) map[string]any {
	t.Helper()
	var index map[string]any
	if err := json.Unmarshal([]byte(readFile(t, filepath.Join(".specify", "design", "index.json"))), &index); err != nil {
		t.Fatal(err)
	}
	return index
}

func designChangeRecordRuntime(t *testing.T, index map[string]any, changeID string) map[string]any {
	t.Helper()
	for _, raw := range index["changes"].([]any) {
		record := raw.(map[string]any)
		if record["id"] == changeID {
			return record
		}
	}
	t.Fatalf("design change %s was not found", changeID)
	return nil
}

func configurePreviewCandidate(t *testing.T, path string) {
	t.Helper()
	content := readFile(t, path)
	content = strings.ReplaceAll(content, "__ROUND_NUMBER__", "1")
	content = strings.Replace(content, `data-preview-status="scaffold"`, `data-preview-status="candidate"`, 1)
	content = strings.Replace(content, `"configured": false`, `"configured": true`, 1)
	content = strings.Replace(content, `"status": "scaffold",
    "approved_direction": null`, `"status": "candidate",
    "approved_direction": null`, 1)
	content = regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(content, "Configured design content")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func configureUITargetCandidate(t *testing.T, path string) string {
	t.Helper()
	content := readFile(t, path)
	replacements := map[string]string{
		`data-status="draft"`:             `data-status="candidate"`,
		"__FIDELITY_MODE__":               "high",
		`"configured": false`:             `"configured": true`,
		"__APPROVED_VISUAL_REF__":         ".specify/design/previews/round-01.html#direction-a",
		"__APPROVED_DIRECTION_ID__":       "direction-a",
		"__APPROVED_PREVIEW_SHA256__":     strings.Repeat("a", 64),
		"__APPROVED_MANIFEST_SHA256__":    strings.Repeat("b", 64),
		"__APPROVED_HANDOFF_REF__":        ".specify/design/previews/round-01.handoff.json",
		"__APPROVED_HANDOFF_SHA256__":     strings.Repeat("c", 64),
		"__DESIGN_DECISION_IDS__":         `DS-COMP-001", "DS-RESP-001`,
		"__DESIGN_HANDOFF_CONTRACT_IDS__": `DH-COMP-001", "DH-RESP-COMPACT-001`,
	}
	for old, newValue := range replacements {
		content = strings.ReplaceAll(content, old, newValue)
	}
	content = regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(content, "Configured content")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return content
}

func decodeEnvelope(t *testing.T, raw []byte) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		t.Fatalf("decode envelope: %v\n%s", err, raw)
	}
	return env
}

func envelopeHasDiagnostic(env Envelope, code string) bool {
	for _, item := range env.Items {
		if diagnostic, ok := item.(map[string]any); ok && diagnostic["code"] == code {
			return true
		}
	}
	return false
}

func readFile(t *testing.T, path string) string {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func withCwd(t *testing.T, dir string) {
	t.Helper()
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(old); err != nil {
			t.Fatal(err)
		}
	})
}
