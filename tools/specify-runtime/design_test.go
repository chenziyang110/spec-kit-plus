package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
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
    decision_ids:
      - DS-COLOR-001
      - DS-TYPE-001
      - DS-SPACE-001
      - DS-COMP-001
      - DS-MOTION-001
      - DS-RESP-001
      - DS-CONTENT-001
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
	stdout.Reset()
	exit = runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout)
	if exit != 0 {
		t.Fatalf("approved preview should lint: exit=%d output=%s", exit, stdout.String())
	}

	mutated := strings.Replace(readFile(t, preview), "Compare all", "Compare directions", 1)
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
		`data-status="draft"`:          `data-status="candidate"`,
		"__FIDELITY_MODE__":            "high",
		`"configured": false`:          `"configured": true`,
		"__APPROVED_VISUAL_REF__":      ".specify/design/previews/round-01.html#direction-a",
		"__APPROVED_DIRECTION_ID__":    "direction-a",
		"__APPROVED_PREVIEW_SHA256__":  strings.Repeat("a", 64),
		"__APPROVED_MANIFEST_SHA256__": strings.Repeat("b", 64),
		"__DESIGN_DECISION_IDS__":      `DS-COMP-001", "DS-RESP-001`,
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
