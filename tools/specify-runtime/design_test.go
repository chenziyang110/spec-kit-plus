package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
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
    direction: direction-main
    review_round: 1
    source_refs:
      - src/app/page.tsx
    visual_refs:
      - .specify/design/previews/round-01.html#direction-main
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
  professional_skill_route:
    catalog_version: spec-kit-ui-professional-v1
    status: resolved
    domain_skill_id: domain-product-workspace
    style_skill_id: style-minimal-product-linear
    specialist_skill_ids:
      - specialist-accessibility-localization
    matched_signals:
      domain-product-workspace:
        - professional workspace
    loaded_refs:
      - ui-professional-skills/domains/product-workspace.md
      - design-library/minimal-product-linear.md
      - ui-professional-skills/specialists/accessibility-localization.md
    unresolved_candidates: []
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
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: contrast report and visual capture
    - id: DS-TYPE-001
      kind: typography
      statement: preserve compact readable hierarchy
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: resolved font and visual capture
    - id: DS-SPACE-001
      kind: spacing
      statement: preserve the spacing rhythm
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: computed tokens and visual capture
    - id: DS-COMP-001
      kind: component
      statement: preserve component anatomy and states
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: state matrix and structure snapshot
    - id: DS-MOTION-001
      kind: motion
      statement: preserve purposeful feedback and reduced motion
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: runtime capture
    - id: DS-RESP-001
      kind: responsive
      statement: preserve hierarchy across target widths
      source_ref: .specify/design/previews/round-01.html#direction-main
      verification: viewport matrix
    - id: DS-CONTENT-001
      kind: content
      statement: preserve representative content density
      source_ref: .specify/design/previews/round-01.html#direction-main
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

The current concept is approved.

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

func TestDesignPreviewReadyRequiresTruthfulHTMLCapabilityRoute(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-20.html")

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview", "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, stdout.String())
	}
	configurePreviewCandidate(t, preview)
	content := readFile(t, preview)
	withoutRoute := regexp.MustCompile(`(?s)\s*"visual_collaboration"\s*:\s*\{[^{}]*\},`).ReplaceAllString(content, "")
	if err := os.WriteFile(preview, []byte(withoutRoute), 0o644); err != nil {
		t.Fatal(err)
	}
	diagnostics := lintDesignPreviewFile(preview, "ready")
	found := false
	for _, diagnostic := range diagnostics {
		if diagnostic.Code == "preview-invalid-visual-collaboration" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("missing HTML visual capability diagnostic: %#v", diagnostics)
	}

	wrongRoute := strings.Replace(content, `"image_generation": "unavailable"`, `"image_generation": "available"`, 1)
	if err := os.WriteFile(preview, []byte(wrongRoute), 0o644); err != nil {
		t.Fatal(err)
	}
	diagnostics = lintDesignPreviewFile(preview, "ready")
	found = false
	for _, diagnostic := range diagnostics {
		if diagnostic.Code == "preview-invalid-visual-collaboration" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("lying HTML visual capability route passed: %#v", diagnostics)
	}

	inspectableRoute := strings.Replace(content, `"image_inspection": "unavailable"`, `"image_inspection": "available"`, 1)
	inspectableRoute = strings.Replace(inspectableRoute, `"image_editing": "unavailable"`, `"image_editing": "available"`, 1)
	inspectableRoute = strings.Replace(inspectableRoute, `"inspection_owner": "user"`, `"inspection_owner": "agent-and-user"`, 1)
	if err := os.WriteFile(preview, []byte(inspectableRoute), 0o644); err != nil {
		t.Fatal(err)
	}
	if diagnostics := lintDesignPreviewFile(preview, "ready"); len(diagnostics) != 0 {
		t.Fatalf("valid inspectable HTML capability route failed: %#v", diagnostics)
	}
}

func TestDesignPreviewConceptLintAllowsAuthoredCandidateBeforeHandoffCompletion(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-01.html")

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview", "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, stdout.String())
	}
	configurePreviewCandidate(t, preview)
	removePreviewHandoffField(t, preview, "editing_matrix")

	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout); exit != 2 {
		t.Fatalf("incomplete handoff should fail ready lint: exit=%d output=%s", exit, stdout.String())
	}
	if env := decodeEnvelope(t, stdout.Bytes()); !envelopeHasDiagnostic(env, "preview-missing-editing-matrix") {
		t.Fatalf("ready lint did not identify the incomplete handoff: %#v", env.Items)
	}

	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", preview, "--level", "concept"}, &stdout); exit != 0 {
		t.Fatalf("authored candidate should pass concept lint before handoff completion: exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{"lint", preview, "--level", "concept"}, &stdout); exit != 2 {
		t.Fatalf("concept must remain preview-lint-specific: exit=%d output=%s", exit, stdout.String())
	}
}

func TestDesignDirectionConfirmCreatesNonConsumableIdempotentCheckpointAndRejectsDrift(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview, designPath := createDirectionCheckpointFixture(t, "UD-0060", true)
	previewBefore := readFile(t, preview)
	designBefore := readFile(t, designPath)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"direction-confirm", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
		t.Fatalf("direction-confirm failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, preview); got != previewBefore {
		t.Fatal("direction-confirm mutated the candidate preview")
	}

	base := strings.TrimSuffix(preview, filepath.Ext(preview))
	directionPath := base + ".direction.json"
	approvalPath := base + ".approval.json"
	handoffPath := base + ".handoff.json"
	manifestPath := base + ".manifest.json"
	for _, path := range []string{approvalPath, handoffPath} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("direction-confirm created consumable artifact %s: %v", path, err)
		}
	}

	var checkpoint map[string]any
	checkpointText := readFile(t, directionPath)
	if err := json.Unmarshal([]byte(checkpointText), &checkpoint); err != nil {
		t.Fatal(err)
	}
	wantDesignRef := filepath.ToSlash(designPath)
	wantCheckpoint := map[string]any{
		"schema":               "spec-kit-design-direction-checkpoint-v1",
		"status":               "confirmed",
		"authority":            "non-consumable",
		"approved":             false,
		"registered":           false,
		"consumer_eligible":    false,
		"confirmed_by":         "explicit-user-direction-confirmation",
		"design_change_id":     "UD-0060",
		"design_change_ref":    wantDesignRef,
		"design_change_sha256": sha256String(designBefore),
		"scope":                []any{"web:orders/list"},
		"capability_profile_ids": []any{
			"web",
		},
		"visual_medium":   "html",
		"preview_file":    filepath.Base(preview),
		"preview_ref":     filepath.ToSlash(preview) + "#direction-main",
		"preview_sha256":  sha256String(previewBefore),
		"direction_id":    "direction-main",
		"review_round":    "1",
		"manifest_ref":    filepath.ToSlash(manifestPath),
		"manifest_sha256": sha256String(readFile(t, manifestPath)),
	}
	if !reflect.DeepEqual(checkpoint, wantCheckpoint) {
		t.Fatalf("direction checkpoint = %#v, want %#v", checkpoint, wantCheckpoint)
	}

	stdout.Reset()
	if exit := runDesign([]string{"direction-confirm", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
		t.Fatalf("identical direction-confirm replay failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, directionPath); got != checkpointText {
		t.Fatal("identical direction-confirm replay rewrote the checkpoint")
	}

	drifted := strings.Replace(previewBefore, "Operations command center", "Operations command center revised", 1)
	if drifted == previewBefore {
		t.Fatal("preview drift fixture did not change the preview")
	}
	if err := os.WriteFile(preview, []byte(drifted), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"direction-confirm", preview, "--direction", "direction-main"}, &stdout); exit == 0 {
		t.Fatalf("direction-confirm accepted preview drift: %s", stdout.String())
	}
	if got := readFile(t, directionPath); got != checkpointText {
		t.Fatal("drift rejection changed the existing checkpoint")
	}
}

func TestDesignDirectionConfirmImageRequiresCapabilityParityAndPreservesCandidateBundle(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	image, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-0062")
	manifestBefore := readFile(t, manifestPath)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-lint", image, "--level", "concept"}, &stdout); exit != 0 {
		t.Fatalf("candidate image with deferred handoff should pass concept lint: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{
		"direction-confirm", image,
		"--direction", "direction-main",
		"--manifest", manifestPath,
		"--prompt", promptPath,
		"--image-inspection", "unavailable",
		"--image-editing", "unavailable",
	}, &stdout); exit == 0 {
		t.Fatalf("direction-confirm accepted capability drift: %s", stdout.String())
	}
	if _, err := os.Stat(strings.TrimSuffix(image, filepath.Ext(image)) + ".direction.json"); !os.IsNotExist(err) {
		t.Fatalf("rejected capability drift created a checkpoint: %v", err)
	}

	stdout.Reset()
	if exit := runDesign([]string{
		"direction-confirm", image,
		"--direction", "direction-main",
		"--manifest", manifestPath,
		"--prompt", promptPath,
		"--image-inspection", "available",
		"--image-editing", "unavailable",
	}, &stdout); exit != 0 {
		t.Fatalf("image direction-confirm failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, manifestPath); got != manifestBefore {
		t.Fatal("image direction-confirm mutated the candidate manifest")
	}
	base := strings.TrimSuffix(image, filepath.Ext(image))
	for _, path := range []string{base + ".approval.json", base + ".handoff.json"} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("image direction-confirm created consumable artifact %s: %v", path, err)
		}
	}
	var checkpoint map[string]any
	if err := json.Unmarshal([]byte(readFile(t, base+".direction.json")), &checkpoint); err != nil {
		t.Fatal(err)
	}
	for field, want := range map[string]any{
		"schema":           "spec-kit-design-direction-checkpoint-v1",
		"authority":        "non-consumable",
		"visual_medium":    "image",
		"preview_sha256":   sha256String(readFile(t, image)),
		"manifest_sha256":  sha256String(manifestBefore),
		"prompt_sha256":    sha256String(readFile(t, promptPath)),
		"image_generation": "available",
		"image_inspection": "available",
		"image_editing":    "unavailable",
		"inspection_owner": "agent-and-user",
		"prompt_strategy":  "image-generation",
	} {
		if got := checkpoint[field]; got != want {
			t.Errorf("checkpoint %s = %#v, want %#v", field, got, want)
		}
	}
}

func TestDesignDirectionConfirmedRoundCannotBeApproved(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview, _ := createDirectionCheckpointFixture(t, "UD-0061", false)
	previewBefore := readFile(t, preview)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout); exit != 0 {
		t.Fatalf("control fixture must be approval-ready before direction confirmation: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{"direction-confirm", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
		t.Fatalf("direction-confirm failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, preview); got != previewBefore {
		t.Fatal("direction-confirm mutated the approval-ready preview")
	}

	stdout.Reset()
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout); exit == 0 {
		t.Fatalf("approve accepted a direction-confirmed round: %s", stdout.String())
	}
	base := strings.TrimSuffix(preview, filepath.Ext(preview))
	for _, path := range []string{base + ".approval.json", base + ".handoff.json"} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("blocked approval created %s: %v", path, err)
		}
	}
}

func TestDesignHelpDoesNotExecutePreviewManifestOrWriteFiles(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)

	for _, args := range [][]string{
		{"--help"},
		{"preview-manifest", "--help"},
		{"approve", "--help"},
	} {
		var stdout bytes.Buffer
		if exit := runDesign(args, &stdout); exit != 0 {
			t.Fatalf("help args=%v exit=%d output=%s", args, exit, stdout.String())
		}
		output := stdout.String()
		for _, want := range []string{"specify-runtime design commands:", "preview-manifest", "direction-confirm", "import"} {
			if !strings.Contains(output, want) {
				t.Fatalf("help args=%v output=%q missing %q", args, output, want)
			}
		}
		if _, err := os.Stat(filepath.Join(".specify", "design", "previews", "round-01.manifest.json")); !os.IsNotExist(err) {
			t.Fatalf("help args=%v created a preview manifest: %v", args, err)
		}
	}

	var stdout bytes.Buffer
	explicitRef := filepath.Join(".specify", "design", "changes", "UD-0002", "references.md")
	if exit := runDesign([]string{"import", "https://example.com/other", "--notes", "help", "--out", explicitRef}, &stdout); exit != 0 {
		t.Fatalf("notes value should not trigger help: exit=%d output=%s", exit, stdout.String())
	}
	if strings.Contains(stdout.String(), "specify-runtime design commands:") {
		t.Fatalf("notes value should not trigger help output: %s", stdout.String())
	}
	if _, err := os.Stat(explicitRef); err != nil {
		t.Fatalf("notes value should still allow import: %v", err)
	}
}

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
	exit = runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout)
	if exit != 0 {
		t.Fatalf("approve exit = %d output=%s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	approval := env.Data["approval"].(map[string]any)
	if approval["direction_id"] != "direction-main" {
		t.Fatalf("direction_id = %v", approval["direction_id"])
	}
	if approval["visual_medium"] != "html" || approval["image_generation"] != "unavailable" || approval["image_inspection"] != "unavailable" || approval["image_editing"] != "unavailable" || approval["inspection_owner"] != "user" || approval["prompt_strategy"] != "html-authoring" {
		t.Fatalf("HTML capability route = %#v", approval)
	}
	html := readFile(t, preview)
	if !strings.Contains(html, `data-preview-status="approved"`) || !strings.Contains(html, `data-approved-direction="direction-main"`) {
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
	if handoffPayload["schema"] != designHandoffSchema || direction["id"] != "direction-main" || len(stringList(reproduction["contract_ids"])) == 0 {
		t.Fatalf("handoff does not freeze the selected direction contract: %#v", handoffPayload)
	}
	handoffApproval := handoffPayload["approval"].(map[string]any)
	if handoffApproval["visual_medium"] != "html" || handoffApproval["inspection_owner"] != "user" {
		t.Fatalf("HTML handoff route = %#v", handoffApproval)
	}
	capabilityModel, _ := reproduction["capability_model"].(map[string]any)
	if !reflect.DeepEqual(stringList(capabilityModel["profile_ids"]), []string{"web"}) {
		t.Fatalf("handoff does not freeze the capability model: %#v", reproduction)
	}
	for _, field := range []string{
		"surface_catalog", "scenario_matrix",
		"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix",
		"navigation_matrix", "content_matrix", "motion_contract", "usability_validation",
	} {
		if reproduction[field] == nil {
			t.Fatalf("handoff does not freeze professional contract %s: %#v", field, reproduction)
		}
	}
	professionalIDs := map[string]bool{}
	for _, field := range []string{"surface_catalog", "scenario_matrix", "interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix"} {
		for _, raw := range reproduction[field].([]any) {
			professionalIDs[strings.TrimSpace(fmt.Sprint(raw.(map[string]any)["id"]))] = true
		}
	}
	motion := reproduction["motion_contract"].(map[string]any)
	for _, raw := range motion["transitions"].([]any) {
		professionalIDs[strings.TrimSpace(fmt.Sprint(raw.(map[string]any)["id"]))] = true
	}
	contractIDs := listToStringSet(reproduction["contract_ids"])
	if !stringSetContainsAll(contractIDs, sortedBoolKeys(professionalIDs)) {
		t.Fatalf("handoff contract_ids omit professional DH-* rows: ids=%#v want=%#v", contractIDs, professionalIDs)
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
	mutated := strings.Replace(beforeMutation, "Iterative design studio", "Iterative design studio (edited)", 1)
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

func TestDesignImageApproveFreezesImageManifestPromptAndCapabilities(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	image := filepath.Join(".specify", "design", "changes", "UD-0021", "previews", "round-21.png")
	manifestPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".manifest.json"
	promptPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".prompt.md"

	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-manifest", "--out", manifestPath}, &stdout); exit != 0 {
		t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
	}
	configured := regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(readFile(t, manifestPath), "Configured design content")
	configured = strings.Replace(configured, `"applicability": "not-assessed"`, `"applicability": "not-applicable"`, 1)
	configured = strings.Replace(configured, `"configured": false`, `"configured": true`, 1)
	configured = strings.Replace(configured, `"status": "scaffold"`, `"status": "candidate"`, 1)
	configured = strings.Replace(configured, `"variance": null`, `"variance": 5`, 1)
	configured = strings.Replace(configured, `"motion": null`, `"motion": 3`, 1)
	configured = strings.Replace(configured, `"density": null`, `"density": 7`, 1)
	if err := os.WriteFile(manifestPath, []byte(configured), 0o644); err != nil {
		t.Fatal(err)
	}
	pngBytes, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(image, pngBytes, 0o644); err != nil {
		t.Fatal(err)
	}
	prompt := "# Image generation prompt\n\nOne composite UI review board for Atlas Operations. Preserve the recovery rail and labeled state specimens.\n"
	if err := os.WriteFile(promptPath, []byte(prompt), 0o644); err != nil {
		t.Fatal(err)
	}

	stdout.Reset()
	exit := runDesign([]string{
		"approve", image,
		"--direction", "direction-main",
		"--manifest", manifestPath,
		"--prompt", promptPath,
		"--image-inspection", "available",
		"--image-editing", "unavailable",
	}, &stdout)
	if exit != 0 {
		t.Fatalf("image approve failed: %d %s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	approval := env.Data["approval"].(map[string]any)
	if approval["visual_medium"] != "image" || approval["inspection_owner"] != "agent-and-user" {
		t.Fatalf("image approval route = %#v", approval)
	}
	imageDigest := sha256.Sum256(pngBytes)
	if approval["image_sha256"] != fmt.Sprintf("%x", imageDigest) {
		t.Fatalf("image digest = %#v", approval["image_sha256"])
	}
	manifest := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, manifestPath)), &manifest); err != nil {
		t.Fatal(err)
	}
	collaboration := manifest["visual_collaboration"].(map[string]any)
	if collaboration["primary_medium"] != "image-primary" || collaboration["image_inspection"] != "available" || collaboration["image_editing"] != "unavailable" {
		t.Fatalf("visual collaboration = %#v", collaboration)
	}
	handoffPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".handoff.json"
	handoff := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, handoffPath)), &handoff); err != nil {
		t.Fatal(err)
	}
	handoffApproval := handoff["approval"].(map[string]any)
	if handoffApproval["visual_medium"] != "image" || handoffApproval["preview_sha256"] != approval["image_sha256"] || handoffApproval["prompt_sha256"] != approval["prompt_sha256"] {
		t.Fatalf("image handoff approval = %#v", handoffApproval)
	}

	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", image, "--level", "ready"}, &stdout); exit != 0 {
		t.Fatalf("approved image should lint: %d %s", exit, stdout.String())
	}
	design := strings.ReplaceAll(
		validDesignForRuntime,
		".specify/design/previews/round-01.html#direction-main",
		"previews/round-21.png#direction-main",
	)
	design = strings.ReplaceAll(design, "PREVIEW_SHA256", approval["image_sha256"].(string))
	design = strings.ReplaceAll(design, "MANIFEST_SHA256", approval["manifest_sha256"].(string))
	design = strings.ReplaceAll(design, "HANDOFF_SHA256", approval["handoff_sha256"].(string))
	design = strings.ReplaceAll(
		design,
		".specify/design/previews/round-01.handoff.json",
		"previews/round-21.handoff.json",
	)
	manifestLine := "    manifest_sha256: " + approval["manifest_sha256"].(string)
	design = strings.Replace(design, manifestLine, manifestLine+
		"\n    visual_medium: image"+
		"\n    prompt_ref: previews/round-21.prompt.md"+
		"\n    prompt_sha256: "+approval["prompt_sha256"].(string)+
		"\n    inspection_owner: "+approval["inspection_owner"].(string), 1)
	var handoffYAML []string
	for _, id := range stringList(approval["handoff_contract_ids"]) {
		handoffYAML = append(handoffYAML, "      - "+id)
	}
	design = strings.ReplaceAll(design, "HANDOFF_CONTRACT_IDS", strings.Join(handoffYAML, "\n"))
	designPath := filepath.Join(".specify", "design", "changes", "UD-0021", "design-change.md")
	if err := os.MkdirAll(filepath.Dir(designPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"lint", designPath, "--level", "ready"}, &stdout); exit != 0 {
		t.Fatalf("design-change.md should accept image round: %d %s", exit, stdout.String())
	}
	if err := os.WriteFile(image, append(pngBytes, []byte("tampered")...), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", image, "--level", "ready"}, &stdout); exit != 2 {
		t.Fatalf("tampered image lint = %d %s", exit, stdout.String())
	}
	env = decodeEnvelope(t, stdout.Bytes())
	if !envelopeHasDiagnostic(env, "image-stale-approval-sidecar") {
		t.Fatalf("missing stale image diagnostic: %#v", env.Items)
	}
}

func TestDesignImageApproveSupportsDeclaredRasterFormats(t *testing.T) {
	formats := map[string][]byte{
		".jpg":  {0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 'J', 'F', 'I', 'F', 0x00},
		".jpeg": {0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 'J', 'F', 'I', 'F', 0x00},
		".webp": {'R', 'I', 'F', 'F', 0x04, 0x00, 0x00, 0x00, 'W', 'E', 'B', 'P'},
	}
	for suffix, imageBytes := range formats {
		t.Run(strings.TrimPrefix(suffix, "."), func(t *testing.T) {
			tmp := t.TempDir()
			withCwd(t, tmp)
			image := filepath.Join(".specify", "design", "previews", "round-22"+suffix)
			manifestPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".manifest.json"
			promptPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".prompt.md"

			var stdout bytes.Buffer
			if exit := runDesign([]string{"preview-manifest", "--out", manifestPath}, &stdout); exit != 0 {
				t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
			}
			configured := regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(readFile(t, manifestPath), "Configured design content")
			configured = strings.Replace(configured, `"applicability": "not-assessed"`, `"applicability": "not-applicable"`, 1)
			configured = strings.Replace(configured, `"configured": false`, `"configured": true`, 1)
			configured = strings.Replace(configured, `"status": "scaffold"`, `"status": "candidate"`, 1)
			configured = strings.Replace(configured, `"variance": null`, `"variance": 5`, 1)
			configured = strings.Replace(configured, `"motion": null`, `"motion": 3`, 1)
			configured = strings.Replace(configured, `"density": null`, `"density": 7`, 1)
			if err := os.WriteFile(manifestPath, []byte(configured), 0o644); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(image, imageBytes, 0o644); err != nil {
				t.Fatal(err)
			}
			prompt := "# Image generation prompt\n\nOne composite UI review board for Atlas Operations with a preserved recovery rail and labeled state specimens.\n"
			if err := os.WriteFile(promptPath, []byte(prompt), 0o644); err != nil {
				t.Fatal(err)
			}

			stdout.Reset()
			if exit := runDesign([]string{
				"approve", image,
				"--direction", "direction-main",
				"--manifest", manifestPath,
				"--prompt", promptPath,
				"--image-inspection", "available",
				"--image-editing", "unavailable",
			}, &stdout); exit != 0 {
				t.Fatalf("%s image approve failed: %d %s", suffix, exit, stdout.String())
			}
			if diagnostics := lintDesignImageBundle(image, "ready"); len(diagnostics) != 0 {
				t.Fatalf("%s image bundle diagnostics: %#v", suffix, diagnostics)
			}
		})
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
	exit := runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout)
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
	configured = strings.Replace(configured, `"applicability": "not-assessed"`, `"applicability": "not-applicable"`, 1)
	configured = strings.Replace(configured, `"variance": null`, `"variance": 5`, 1)
	configured = strings.Replace(configured, `"motion": null`, `"motion": 3`, 1)
	configured = strings.Replace(configured, `"density": null`, `"density": 7`, 1)
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
	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout); exit != 2 {
		t.Fatalf("unfinished rendered draft should not be ready: %d %s", exit, stdout.String())
	}
	if env := decodeEnvelope(t, stdout.Bytes()); !envelopeHasDiagnostic(env, "preview-unfinished-prototype") {
		t.Fatalf("rendered draft did not expose unfinished-prototype recovery: %#v", env.Items)
	}
	configurePreviewCandidate(t, preview)
	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", preview, "--level", "ready"}, &stdout); exit != 0 {
		t.Fatalf("authored candidate should lint: %d %s", exit, stdout.String())
	}
}

func TestDesignPreviewReadyRejectsIncompleteSourceContinuityCoverage(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	preview := filepath.Join(".specify", "design", "previews", "round-coverage.html")
	templatePath, err := locateTemplate("design-preview-template.html")
	if err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(templatePath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(preview), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(preview, raw, 0o644); err != nil {
		t.Fatal(err)
	}
	configurePreviewCandidate(t, preview)
	content := readFile(t, preview)
	manifest, err := parseJSONObject(parseHTMLSummary(content).PreviewManifestText)
	if err != nil {
		t.Fatal(err)
	}
	handoff := manifest["handoff"].(map[string]any)
	surface := handoff["surface_catalog"].([]any)[0].(map[string]any)
	interaction := handoff["interaction_matrix"].([]any)[0].(map[string]any)
	component := handoff["component_contracts"].([]any)[0].(map[string]any)
	handoff["source_continuity"] = map[string]any{
		"schema": "spec-kit-ui-source-continuity-v1", "applicability": "required",
		"mode": "implementation-backed", "reason": "Only a sampled action was mapped.",
		"coverage": map[string]any{
			"surface_ids": []any{surface["id"]}, "interaction_ids": []any{interaction["id"]},
			"component_ids": []any{component["id"]},
		},
		"authority_refs": []any{"src/source-ui"},
		"surface_bindings": []any{map[string]any{
			"id": "SC-SURFACE-001", "surface_id": surface["id"], "source_refs": []any{"src/source-ui"},
			"discovery": "measured", "disposition": "adapt", "rationale": "Preserve the source surface.",
		}},
		"action_bindings": []any{map[string]any{
			"id": "SC-ACTION-001", "interaction_id": interaction["id"], "source_refs": []any{"src/source-ui#action"},
			"user_promise": "Complete the action.", "business_outcome": "The result persists.", "side_effects": []any{},
			"final_state": "The result remains visible.", "verification": "Run source and target paths.",
		}},
		"asset_bindings": []any{map[string]any{
			"id": "SC-ASSET-001", "component_id": component["id"], "semantic_role": "primary control",
			"source_refs": []any{"src/source-ui#asset"}, "target_strategy": "preserve", "target_ref": "src/assets/control.svg",
			"provenance": "project-owned", "fallback": "Visible text label.", "placeholder_policy": "forbid-character-substitution",
		}},
		"unresolved_gaps": []any{},
	}
	updated, err := replaceEmbeddedJSON(content, designPreviewManifestID, manifest)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(preview, []byte(updated), 0o644); err != nil {
		t.Fatal(err)
	}

	diagnostics := lintDesignPreviewFile(preview, "ready")
	found := false
	for _, diagnostic := range diagnostics {
		if diagnostic.Code == "preview-source-continuity-coverage-mismatch" {
			found = true
			break
		}
	}
	if !found {
		t.Fatalf("incomplete source continuity coverage unexpectedly passed: %#v", diagnostics)
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
	handoff, _ := manifest["handoff"].(map[string]any)
	for _, raw := range handoff["component_contracts"].([]any) {
		component := raw.(map[string]any)
		if len(stringList(component["interaction_modes"])) == 0 || !validDesignDataScenarios(component["data_scenarios"]) {
			t.Fatalf("component lacks interaction/data scenarios: %#v", component)
		}
		if len(stringList(component["variants"])) == 0 || len(stringList(component["content_constraints"])) == 0 || len(stringList(component["semantic_token_refs"])) == 0 || !nonEmpty(component["governance"]) || !nonEmpty(component["iconography"]) {
			t.Fatalf("component lacks professional design-system contract: %#v", component)
		}
	}
	for _, raw := range handoff["responsive_matrix"].([]any) {
		target := raw.(map[string]any)
		if !nonEmpty(target["stretch_behavior"]) || !nonEmpty(target["overflow_behavior"]) {
			t.Fatalf("responsive target lacks stretch/overflow behavior: %#v", target)
		}
	}
	knownDecisions := stringSliceSet(manifestDecisionIDs(manifest))
	professionalIDs := map[string]bool{}
	for _, field := range []string{"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix"} {
		rows, ok := handoff[field].([]any)
		if !ok || len(rows) == 0 {
			t.Fatalf("handoff lacks %s: %#v", field, handoff)
		}
		for _, raw := range rows {
			row := raw.(map[string]any)
			professionalIDs[strings.TrimSpace(fmt.Sprint(row["id"]))] = true
			if !stringSetContainsAll(knownDecisions, stringList(row["decision_ids"])) {
				t.Fatalf("%s row references unknown decision: %#v", field, row)
			}
			if field == "interaction_matrix" {
				if !validDesignProfessionalRow(field, row) {
					t.Fatalf("interaction row lacks the complete event lifecycle: %#v", row)
				}
				blankSequence := cloneJSONMap(row)
				blankSequence["event_sequence"] = ""
				if validDesignProfessionalRow(field, blankSequence) {
					t.Fatalf("interaction row accepted a blank event sequence: %#v", blankSequence)
				}
				legacyShape := cloneJSONMap(row)
				legacyShape["expectation"] = "legacy aggregate expectation"
				if validDesignProfessionalRow(field, legacyShape) {
					t.Fatalf("interaction row accepted an extra legacy expectation: %#v", legacyShape)
				}
			}
		}
	}
	motion := handoff["motion_contract"].(map[string]any)
	if !nonEmpty(motion["purpose"]) || !nonEmpty(motion["reduced_motion"]) {
		t.Fatalf("motion contract is incomplete: %#v", motion)
	}
	for _, raw := range motion["transitions"].([]any) {
		row := raw.(map[string]any)
		professionalIDs[strings.TrimSpace(fmt.Sprint(row["id"]))] = true
		if !stringSetContainsAll(knownDecisions, stringList(row["decision_ids"])) {
			t.Fatalf("motion transition references unknown decision: %#v", row)
		}
	}
	if usability, ok := handoff["usability_validation"].(map[string]any); !ok || !nonEmpty(usability["risk_level"]) || len(stringList(usability["methods"])) == 0 || len(stringList(usability["critical_tasks"])) == 0 || len(stringList(usability["success_criteria"])) == 0 {
		t.Fatalf("usability validation is incomplete: %#v", handoff["usability_validation"])
	} else {
		highRiskWithoutReview := cloneJSONMap(usability)
		highRiskWithoutReview["risk_level"] = "high"
		highRiskWithoutReview["human_review_required"] = false
		if validDesignUsabilityValidation(highRiskWithoutReview) {
			t.Fatalf("high-risk usability incorrectly permits no human review: %#v", highRiskWithoutReview)
		}
	}
	contractIDs := stringSliceSet(manifestHandoffContractIDs(manifest))
	if !stringSetContainsAll(contractIDs, sortedBoolKeys(professionalIDs)) {
		t.Fatalf("manifest contract IDs omit professional DH-* rows: ids=%#v want=%#v", contractIDs, professionalIDs)
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

func TestDesignCapabilityProjectionUsesRelevantDecisionSubsets(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	manifestPath := filepath.Join(".specify", "design", "previews", "round-14.manifest.json")
	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-manifest", "--profiles", "web", "--out", manifestPath}, &stdout); exit != 0 {
		t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
	}
	manifest := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, manifestPath)), &manifest); err != nil {
		t.Fatal(err)
	}
	decisionsByKind := map[string]string{}
	for _, raw := range manifest["decisions"].([]any) {
		decision := raw.(map[string]any)
		decisionsByKind[strings.TrimSpace(fmt.Sprint(decision["kind"]))] = strings.TrimSpace(fmt.Sprint(decision["id"]))
	}
	handoff := manifest["handoff"].(map[string]any)
	expected := map[string][]string{
		"component_contracts": {decisionsByKind["color"], decisionsByKind["typography"], decisionsByKind["spacing"], decisionsByKind["component"], decisionsByKind["motion"]},
		"interaction_matrix":  {decisionsByKind["component"], decisionsByKind["motion"], decisionsByKind["responsive"]},
		"editing_matrix":      {decisionsByKind["typography"], decisionsByKind["spacing"], decisionsByKind["component"], decisionsByKind["motion"], decisionsByKind["responsive"], decisionsByKind["content"]},
		"data_state_matrix":   {decisionsByKind["color"], decisionsByKind["component"], decisionsByKind["content"]},
		"navigation_matrix":   {decisionsByKind["component"], decisionsByKind["responsive"], decisionsByKind["content"]},
		"content_matrix":      {decisionsByKind["color"], decisionsByKind["typography"], decisionsByKind["spacing"], decisionsByKind["content"]},
		"responsive_matrix":   {decisionsByKind["typography"], decisionsByKind["spacing"], decisionsByKind["component"], decisionsByKind["responsive"]},
	}
	for field, want := range expected {
		rows := handoff[field].([]any)
		if len(rows) == 0 {
			t.Fatalf("%s is empty", field)
		}
		wantSet := stringSliceSet(want)
		for _, raw := range rows {
			row := raw.(map[string]any)
			if !reflect.DeepEqual(stringSliceSet(stringList(row["decision_ids"])), wantSet) {
				t.Fatalf("%s decision subset = %#v, want %#v", field, row["decision_ids"], want)
			}
		}
	}
	motion := handoff["motion_contract"].(map[string]any)
	wantMotion := stringSliceSet([]string{decisionsByKind["component"], decisionsByKind["motion"]})
	for _, raw := range motion["transitions"].([]any) {
		row := raw.(map[string]any)
		if !reflect.DeepEqual(stringSliceSet(stringList(row["decision_ids"])), wantMotion) {
			t.Fatalf("motion decision subset = %#v", row["decision_ids"])
		}
	}
}

func TestDesignCapabilityProjectionBuildsBoundedScenarioGraph(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	manifestPath := filepath.Join(".specify", "design", "previews", "round-16.manifest.json")
	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-manifest", "--profiles", "web,mobile", "--out", manifestPath}, &stdout); exit != 0 {
		t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
	}
	manifest := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, manifestPath)), &manifest); err != nil {
		t.Fatal(err)
	}
	handoff := manifest["handoff"].(map[string]any)
	surfaces := handoff["surface_catalog"].([]any)
	scenarios := handoff["scenario_matrix"].([]any)
	if len(surfaces) != 2 || len(scenarios) == 0 {
		t.Fatalf("scenario graph = surfaces %d scenarios %d", len(surfaces), len(scenarios))
	}
	surfaceIDs := map[string]bool{}
	for _, raw := range surfaces {
		row := raw.(map[string]any)
		surfaceIDs[strings.TrimSpace(fmt.Sprint(row["id"]))] = true
		if len(stringList(row["source_refs"])) == 0 || len(stringList(row["specimen_ids"])) == 0 || len(stringList(row["component_ids"])) == 0 {
			t.Fatalf("surface is incomplete: %#v", row)
		}
	}
	known := map[string]map[string]bool{}
	for _, field := range []string{"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix", "responsive_matrix"} {
		ids := map[string]bool{}
		for _, raw := range handoff[field].([]any) {
			ids[strings.TrimSpace(fmt.Sprint(raw.(map[string]any)["id"]))] = true
		}
		known[field] = ids
	}
	motionIDs := map[string]bool{}
	for _, raw := range handoff["motion_contract"].(map[string]any)["transitions"].([]any) {
		motionIDs[strings.TrimSpace(fmt.Sprint(raw.(map[string]any)["id"]))] = true
	}
	known["motion_contract"] = motionIDs
	refFields := map[string]string{
		"interaction_ids": "interaction_matrix", "data_state_ids": "data_state_matrix",
		"editing_ids":       "editing_matrix",
		"accessibility_ids": "accessibility_matrix", "navigation_ids": "navigation_matrix",
		"content_ids": "content_matrix", "responsive_ids": "responsive_matrix",
		"motion_transition_ids": "motion_contract",
	}
	covered := map[string]map[string]bool{}
	for refField := range refFields {
		covered[refField] = map[string]bool{}
	}
	for _, raw := range scenarios {
		row := raw.(map[string]any)
		if !surfaceIDs[strings.TrimSpace(fmt.Sprint(row["surface_id"]))] || row["required"] != true {
			t.Fatalf("scenario has invalid surface/required: %#v", row)
		}
		script, ok := row["interaction_script"].(map[string]any)
		if !ok || len(stringList(script["preconditions"])) == 0 {
			t.Fatalf("scenario lacks executable preconditions: %#v", row)
		}
		for _, precondition := range stringList(script["preconditions"]) {
			if strings.HasSuffix(precondition, "..") {
				t.Fatalf("scenario precondition has duplicated terminal punctuation: %q", precondition)
			}
		}
		dataStateIDs := stringSliceSet(stringList(row["data_state_ids"]))
		if !dataStateIDs[strings.TrimSpace(fmt.Sprint(script["start_state_id"]))] {
			t.Fatalf("scenario start state is not selected: %#v", script)
		}
		steps, ok := script["steps"].([]any)
		if !ok || len(steps) == 0 {
			t.Fatalf("scenario lacks executable steps: %#v", row)
		}
		for _, stepRaw := range steps {
			step, ok := stepRaw.(map[string]any)
			if !ok || !nonEmpty(step["input"]) || !nonEmpty(step["action"]) || !nonEmpty(step["expected_feedback"]) {
				t.Fatalf("scenario step is incomplete: %#v", stepRaw)
			}
		}
		for _, field := range []string{"focus_checkpoint", "announcement_checkpoint", "completion_checkpoint", "recovery_checkpoint"} {
			if !nonEmpty(script[field]) {
				t.Fatalf("scenario interaction script lacks %s: %#v", field, script)
			}
		}
		branchConditions := map[string]bool{}
		branches, ok := script["branches"].([]any)
		if !ok || len(branches) == 0 {
			t.Fatalf("scenario lacks state branches: %#v", script)
		}
		for _, branchRaw := range branches {
			branch, ok := branchRaw.(map[string]any)
			if !ok || !dataStateIDs[strings.TrimSpace(fmt.Sprint(branch["expected_state_id"]))] {
				t.Fatalf("scenario branch targets an unselected state: %#v", branchRaw)
			}
			for _, condition := range stringList(branch["conditions"]) {
				if branchConditions[condition] {
					t.Fatalf("scenario branch condition is duplicated: %s", condition)
				}
				branchConditions[condition] = true
			}
			for _, field := range []string{"setup", "expected_feedback", "focus_behavior", "announcement", "continuation"} {
				if !nonEmpty(branch[field]) {
					t.Fatalf("scenario branch lacks %s: %#v", field, branch)
				}
			}
		}
		for _, condition := range []string{"success", "failure", "timeout", "cancel", "retry", "duplicate", "out_of_order"} {
			if !branchConditions[condition] {
				t.Fatalf("scenario branch coverage lacks %s: %#v", condition, branches)
			}
		}
		brokenScript := cloneJSONMap(script)
		brokenScript["announcement_checkpoint"] = ""
		if validDesignInteractionScript(brokenScript, dataStateIDs) {
			t.Fatalf("incomplete interaction script passed validation: %#v", brokenScript)
		}
		for refField, sourceField := range refFields {
			refs := stringList(row[refField])
			if len(refs) == 0 || !stringSetContainsAll(known[sourceField], refs) {
				t.Fatalf("scenario %s has invalid %s: %#v", row["id"], refField, refs)
			}
			for _, id := range refs {
				covered[refField][id] = true
			}
		}
	}
	for refField, sourceField := range refFields {
		if !reflect.DeepEqual(covered[refField], known[sourceField]) {
			t.Fatalf("scenario coverage for %s = %#v, want %#v", refField, covered[refField], known[sourceField])
		}
	}
	contractIDs := stringSliceSet(manifestHandoffContractIDs(manifest))
	for _, raw := range append(surfaces, scenarios...) {
		id := strings.TrimSpace(fmt.Sprint(raw.(map[string]any)["id"]))
		if !contractIDs[id] {
			t.Fatalf("scenario graph ID missing from contract_ids: %s", id)
		}
	}
}

func TestDesignCanonicalDecisionIDsAllowMultiSegmentNames(t *testing.T) {
	for _, id := range []string{"DS-COLOR-BRAND-001", "DS-DATA-EMPTY-STATE-002"} {
		if !uiCanonicalDecisionIDRE.MatchString(id) {
			t.Fatalf("canonical decision ID rejected: %s", id)
		}
	}
}

func TestDesignApprovedHandoffPreservesProfileSpecificMotion(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	manifestPath := filepath.Join(".specify", "design", "previews", "round-15.manifest.json")
	preview := filepath.Join(".specify", "design", "previews", "round-15.html")
	var stdout bytes.Buffer
	if exit := runDesign([]string{"preview-manifest", "--profiles", "mobile,cli", "--out", manifestPath}, &stdout); exit != 0 {
		t.Fatalf("preview-manifest failed: %d %s", exit, stdout.String())
	}
	configured := regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(readFile(t, manifestPath), "Configured design content")
	configured = strings.Replace(configured, `"applicability": "not-assessed"`, `"applicability": "not-applicable"`, 1)
	configured = strings.Replace(configured, `"variance": null`, `"variance": 5`, 1)
	configured = strings.Replace(configured, `"motion": null`, `"motion": 3`, 1)
	configured = strings.Replace(configured, `"density": null`, `"density": 7`, 1)
	if err := os.WriteFile(manifestPath, []byte(configured), 0o644); err != nil {
		t.Fatal(err)
	}
	manifest := map[string]any{}
	if err := json.Unmarshal([]byte(configured), &manifest); err != nil {
		t.Fatal(err)
	}
	expectedMotion := cloneJSONValue(manifest["handoff"].(map[string]any)["motion_contract"])
	stdout.Reset()
	if exit := runDesign([]string{"preview", "--manifest", manifestPath, "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview render failed: %d %s", exit, stdout.String())
	}
	configurePreviewCandidate(t, preview)
	stdout.Reset()
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
		t.Fatalf("approve failed: %d %s", exit, stdout.String())
	}
	handoffPath := strings.TrimSuffix(preview, filepath.Ext(preview)) + ".handoff.json"
	handoff := map[string]any{}
	if err := json.Unmarshal([]byte(readFile(t, handoffPath)), &handoff); err != nil {
		t.Fatal(err)
	}
	reproduction := handoff["reproduction"].(map[string]any)
	motion := reproduction["motion_contract"].(map[string]any)
	if !reflect.DeepEqual(motion, expectedMotion) {
		t.Fatalf("approved motion contract = %#v, want profile contract %#v", motion, expectedMotion)
	}
	byID := map[string]map[string]any{}
	for _, raw := range motion["transitions"].([]any) {
		transition := raw.(map[string]any)
		byID[strings.TrimSpace(fmt.Sprint(transition["id"]))] = transition
	}
	if duration, ok := designJSONInt(byID["DH-MOTION-MOBILE-001"]["duration_ms"]); !ok || duration != 220 {
		t.Fatalf("mobile duration = %#v, want 220", byID["DH-MOTION-MOBILE-001"]["duration_ms"])
	}
	if duration, ok := designJSONInt(byID["DH-MOTION-CLI-001"]["duration_ms"]); !ok || duration != 0 {
		t.Fatalf("CLI duration = %#v, want 0", byID["DH-MOTION-CLI-001"]["duration_ms"])
	}
	if byID["DH-MOTION-CLI-001"]["easing"] != "none" {
		t.Fatalf("CLI easing = %#v, want none", byID["DH-MOTION-CLI-001"]["easing"])
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
	preview := filepath.Join(".specify", "design", "changes", "UD-0042", "previews", "round-01.html")
	var scaffoldOut bytes.Buffer
	if exit := runDesign([]string{"preview", "--out", preview}, &scaffoldOut); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, scaffoldOut.String())
	}
	configurePreviewCandidate(t, preview)
	var stdout bytes.Buffer
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
		t.Fatalf("approve failed: %d %s", exit, stdout.String())
	}
	approval := decodeEnvelope(t, stdout.Bytes()).Data["approval"].(map[string]any)
	design := strings.ReplaceAll(validDesignForRuntime, "PREVIEW_SHA256", approval["html_sha256"].(string))
	design = strings.ReplaceAll(design, "MANIFEST_SHA256", approval["manifest_sha256"].(string))
	design = strings.ReplaceAll(design, "HANDOFF_SHA256", approval["handoff_sha256"].(string))
	design = strings.ReplaceAll(
		design,
		".specify/design/previews/round-01.html#direction-main",
		"previews/round-01.html#direction-main",
	)
	design = strings.ReplaceAll(
		design,
		".specify/design/previews/round-01.handoff.json",
		"previews/round-01.handoff.json",
	)
	var handoffYAML []string
	for _, id := range stringList(approval["handoff_contract_ids"]) {
		handoffYAML = append(handoffYAML, "      - "+id)
	}
	design = strings.ReplaceAll(design, "HANDOFF_CONTRACT_IDS", strings.Join(handoffYAML, "\n"))
	designPath := filepath.Join(".specify", "design", "changes", "UD-0042", "design-change.md")
	if err := os.MkdirAll(filepath.Dir(designPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", designPath, "--format", "tailwind"}, &stdout); exit != 0 {
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
	stdout.Reset()
	if exit := runDesign([]string{"export", designPath, "--format", "json"}, &stdout); exit != 0 {
		t.Fatalf("export json failed: %d %s", exit, stdout.String())
	}
	env = decodeEnvelope(t, stdout.Bytes())
	content = env.Data["content"].(map[string]any)
	route := content["professional_skill_route"].(map[string]any)
	if route["domain_skill_id"] != "domain-product-workspace" {
		t.Fatalf("professional skill route was not preserved: %#v", route)
	}

	legacy := strings.Replace(design, "  status: approved\n", "", 1)
	if err := os.WriteFile(designPath, []byte(legacy), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", designPath, "--format", "json"}, &stdout); exit != 10 {
		t.Fatalf("unapproved export should block, exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{"export", designPath, "--format", "json", "--allow-unapproved"}, &stdout); exit != 0 {
		t.Fatalf("legacy export should pass with escape hatch: %d %s", exit, stdout.String())
	}
}

func TestDesignLintValidatesProfessionalSkillRoute(t *testing.T) {
	t.Run("ready route must be resolved", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "design-change.md")
		base := strings.ReplaceAll(
			validDesignForRuntime,
			"HANDOFF_CONTRACT_IDS",
			"      - DH-COMP-001",
		)
		content := strings.Replace(
			base,
			"    status: resolved\n    domain_skill_id: domain-product-workspace",
			"    status: question-required\n    domain_skill_id: domain-product-workspace",
			1,
		)
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
		diagnostics := lintDesignFile(path, "ready")
		for _, diagnostic := range diagnostics {
			if diagnostic.Code == "unresolved-professional-skill-route" {
				return
			}
		}
		t.Fatalf("expected unresolved professional skill route diagnostic: %#v", diagnostics)
	})

	t.Run("route has at most two specialists", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "design-change.md")
		base := strings.ReplaceAll(
			validDesignForRuntime,
			"HANDOFF_CONTRACT_IDS",
			"      - DH-COMP-001",
		)
		content := strings.Replace(
			base,
			"      - specialist-accessibility-localization\n    matched_signals:",
			"      - specialist-accessibility-localization\n      - specialist-motion-interaction\n      - specialist-design-system\n    matched_signals:",
			1,
		)
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
		diagnostics := lintDesignFile(path, "structural")
		for _, diagnostic := range diagnostics {
			if diagnostic.Code == "invalid-professional-skill-route" {
				return
			}
		}
		t.Fatalf("expected invalid professional skill route diagnostic: %#v", diagnostics)
	})

	t.Run("loaded refs must match selected skills", func(t *testing.T) {
		path := filepath.Join(t.TempDir(), "design-change.md")
		content := strings.ReplaceAll(
			validDesignForRuntime,
			"HANDOFF_CONTRACT_IDS",
			"      - DH-COMP-001",
		)
		content = strings.Replace(
			content,
			"ui-professional-skills/domains/product-workspace.md",
			"ui-professional-skills/domains/commerce-service.md",
			1,
		)
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
		diagnostics := lintDesignFile(path, "ready")
		for _, diagnostic := range diagnostics {
			if diagnostic.Code == "professional-skill-route-ref-mismatch" {
				return
			}
		}
		t.Fatalf("expected professional skill route ref mismatch diagnostic: %#v", diagnostics)
	})
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
		t.Fatalf("import should not create root DESIGN.md")
	}

	stdout.Reset()
	explicitRef := filepath.Join(".specify", "design", "changes", "UD-0001", "references.md")
	exit = runDesign([]string{"import", "https://example.com/other", "--out", explicitRef}, &stdout)
	if exit != 0 {
		t.Fatalf("explicit reference import exit=%d output=%s", exit, stdout.String())
	}
	if content := readFile(t, explicitRef); !strings.Contains(content, "https://example.com/other") {
		t.Fatalf("explicit reference content missing source:\n%s", content)
	}
}

func TestDesignImportCopiesExternalImageIntoChangePreviewWorkspace(t *testing.T) {
	projectRoot := t.TempDir()
	externalRoot := t.TempDir()
	withCwd(t, projectRoot)

	var stdout bytes.Buffer
	if exit := runDesign([]string{
		"change", "UD-0001",
		"--title", "Windows workbench",
		"--scope", "desktop:workbench",
		"--profiles", "desktop",
	}, &stdout); exit != 0 {
		t.Fatalf("design change failed: %d %s", exit, stdout.String())
	}

	pngBytes, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatal(err)
	}
	source := filepath.Join(externalRoot, "generated-candidate.PNG")
	if err := os.WriteFile(source, pngBytes, 0o644); err != nil {
		t.Fatal(err)
	}

	stdout.Reset()
	exit := runDesign([]string{
		"import", source,
		"--change", "UD-0001",
		"--round", "01",
		"--notes", "User-approved first concept.",
	}, &stdout)
	if exit != 0 {
		t.Fatalf("design image import failed: %d %s", exit, stdout.String())
	}

	wantRef := ".specify/design/changes/UD-0001/previews/round-01.png"
	target := filepath.FromSlash(wantRef)
	gotBytes, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(gotBytes, pngBytes) {
		t.Fatalf("imported image bytes changed")
	}
	env := decodeEnvelope(t, stdout.Bytes())
	if env.Data["path"] != wantRef || env.Data["change_id"] != "UD-0001" || env.Data["round"] != "01" {
		t.Fatalf("import envelope = %#v", env.Data)
	}
	digest := sha256.Sum256(pngBytes)
	wantDigest := fmt.Sprintf("%x", digest)
	if env.Data["sha256"] != wantDigest {
		t.Fatalf("import sha256 = %#v, want %s", env.Data["sha256"], wantDigest)
	}
	references := readFile(t, filepath.Join(".specify", "design", "changes", "UD-0001", "references.md"))
	for _, want := range []string{source, wantRef, wantDigest, "User-approved first concept."} {
		if !strings.Contains(references, want) {
			t.Fatalf("change-local references missing %q:\n%s", want, references)
		}
	}
	stdout.Reset()
	if exit := runDesign([]string{
		"import", source,
		"--change", "UD-0001",
		"--round", "1",
	}, &stdout); exit != 0 {
		t.Fatalf("byte-identical import retry failed: %d %s", exit, stdout.String())
	}
	if retry := decodeEnvelope(t, stdout.Bytes()); retry.Data["already_imported"] != true {
		t.Fatalf("retry envelope = %#v", retry.Data)
	}
	if referencesAfterRetry := readFile(t, filepath.Join(".specify", "design", "changes", "UD-0001", "references.md")); !strings.Contains(referencesAfterRetry, "User-approved first concept.") {
		t.Fatalf("byte-identical retry rewrote reference notes:\n%s", referencesAfterRetry)
	}

	differentImage := append(append([]byte{}, pngBytes...), byte(0))
	if err := os.WriteFile(source, differentImage, 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	exit = runDesign([]string{
		"import", source,
		"--change", "UD-0001",
		"--round", "1",
	}, &stdout)
	if exit == 0 {
		t.Fatalf("different bytes must not replace a reviewed round: %s", stdout.String())
	}
	if got := readFile(t, target); !bytes.Equal([]byte(got), pngBytes) {
		t.Fatal("failed replacement changed the imported image")
	}
}

func TestDesignImportImageRequiresExistingDraftChange(t *testing.T) {
	projectRoot := t.TempDir()
	externalRoot := t.TempDir()
	withCwd(t, projectRoot)
	source := filepath.Join(externalRoot, "candidate.png")
	pngBytes, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(source, pngBytes, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	exit := runDesign([]string{
		"import", source,
		"--change", "UD-9999",
		"--round", "01",
	}, &stdout)
	if exit == 0 {
		t.Fatalf("missing design change must block image import: %s", stdout.String())
	}
	if _, err := os.Stat(filepath.Join(".specify", "design", "changes", "UD-9999", "previews", "round-01.png")); !os.IsNotExist(err) {
		t.Fatalf("blocked import created a preview: %v", err)
	}
}

func TestDesignImportRejectsOversizedExternalImage(t *testing.T) {
	projectRoot := t.TempDir()
	externalRoot := t.TempDir()
	withCwd(t, projectRoot)
	source := filepath.Join(externalRoot, "candidate.png")
	if err := os.WriteFile(source, []byte("\x89PNG\r\n\x1a\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Truncate(source, maxDesignImageImportBytes+1); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	exit := runDesign([]string{
		"import", source,
		"--change", "UD-0001",
		"--round", "01",
	}, &stdout)
	if exit == 0 || !strings.Contains(stdout.String(), "import limit") {
		t.Fatalf("oversized image must be rejected before import: exit=%d output=%s", exit, stdout.String())
	}
}

func TestDesignImportRequiresCompleteImageTargetOptions(t *testing.T) {
	for _, args := range [][]string{
		{"import", "candidate.png", "--change"},
		{"import", "candidate.png", "--round"},
	} {
		var stdout bytes.Buffer
		exit := runDesign(args, &stdout)
		if exit == 0 || !strings.Contains(stdout.String(), "requires both --change and --round") {
			t.Fatalf("incomplete image target options must fail: args=%v exit=%d output=%s", args, exit, stdout.String())
		}
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
	designPath := filepath.Join(".specify", "design", "changes", "UD-0042", "design-change.md")
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
	if _, err := os.Stat(filepath.Join(".specify", "design", "changes", "UD-0042", "DESIGN.md")); !os.IsNotExist(err) {
		t.Fatalf("design change must not create a change-local DESIGN.md")
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
	if changes[0].(map[string]any)["design_ref"] != ".specify/design/changes/UD-0042/design-change.md" {
		t.Fatalf("unexpected design ref: %#v", changes[0].(map[string]any)["design_ref"])
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
		path := filepath.Join(".specify", "design", "changes", id, "design-change.md")
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
	wantBaseline := ".specify/design/changes/UD-0042/design-change.md#sha256=" + sourceDigest
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

	beforeResolve := snapshotDesignDiscoveryFiles(t, tmp)
	if got := resolveDesignIDsRuntime(t, "web:orders/list"); !reflect.DeepEqual(got, []string{"UD-0043"}) {
		t.Fatalf("list resolution = %#v, want only successor", got)
	}
	if got := resolveDesignIDsRuntime(t, "web:orders/detail"); !reflect.DeepEqual(got, []string{"UD-0042"}) {
		t.Fatalf("detail resolution = %#v, want parent", got)
	}
	if got := resolveDesignIDsRuntime(t, "web:orders"); !reflect.DeepEqual(got, []string{"UD-0043", "UD-0042"}) {
		t.Fatalf("broad resolution = %#v, want explicit composite candidates", got)
	}
	if afterResolve := snapshotDesignDiscoveryFiles(t, tmp); !reflect.DeepEqual(beforeResolve, afterResolve) {
		t.Fatal("resolving valid single and composite candidates mutated design files")
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

func TestDesignPostSpecifyAdoptionPreservesSourceSpecAndReturnsToPlan(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	designPath, _ := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	writeDesignContractRuntime(t, designPath)
	bindingRef := ".specify/features/001-orders/spec-contract.json"
	if err := os.MkdirAll(filepath.Dir(bindingRef), 0o755); err != nil {
		t.Fatal(err)
	}
	sourceSpec := []byte("{\n  \"version\": 1,\n  \"status\": \"planning-ready\",\n  \"acceptance_criteria\": [\"order detail is usable\"]\n}\n")
	if err := os.WriteFile(bindingRef, sourceSpec, 0o644); err != nil {
		t.Fatal(err)
	}
	sourceDigest := fmt.Sprintf("%x", sha256.Sum256(sourceSpec))

	var stdout bytes.Buffer
	if exit := runDesign([]string{
		"impact", "feature:001-orders",
		"--change", "UD-0042",
		"--scope", "web:orders/detail",
		"--mode", "formal-post-specify",
		"--expected-change", "none",
	}, &stdout); exit != 0 {
		t.Fatalf("post-Specify impact failed: %d %s", exit, stdout.String())
	}
	impact := decodeEnvelope(t, stdout.Bytes()).Data["impact"].(map[string]any)
	if impact["reconcile_from"] != "plan" || len(stringList(impact["invalidated_bindings"])) != 0 {
		t.Fatalf("post-Specify impact must return to Plan without invalidation: %#v", impact)
	}
	if !stringSliceSet(stringList(impact["preserved_bindings"]))["feature.requirements"] {
		t.Fatalf("post-Specify impact must preserve requirements: %#v", impact)
	}

	stdout.Reset()
	if exit := runDesign([]string{
		"adopt", "feature:001-orders",
		"--change", "UD-0042",
		"--scope", "web:orders/detail",
		"--mode", "formal-post-specify",
		"--binding-ref", bindingRef,
		"--binding-sha256", sourceDigest,
		"--expected-change", "none",
	}, &stdout); exit != 0 {
		t.Fatalf("post-Specify adoption failed: %d %s", exit, stdout.String())
	}
	if got := readFile(t, bindingRef); got != string(sourceSpec) {
		t.Fatal("post-Specify adoption rewrote the source specification")
	}

	stdout.Reset()
	if exit := runDesign([]string{
		"adoption", "feature:001-orders",
		"--scope", "web:orders/detail",
		"--binding-ref", bindingRef,
		"--binding-sha256", sourceDigest,
		"--expected-change", "UD-0042",
	}, &stdout); exit != 0 {
		t.Fatalf("post-Specify adoption verification failed: %d %s", exit, stdout.String())
	}
	verified := decodeEnvelope(t, stdout.Bytes()).Data["adoption"].(map[string]any)
	if verified["verified"] != true || verified["source_spec_sha256"] != sourceDigest {
		t.Fatalf("post-Specify verification = %#v", verified)
	}
}

func TestDesignFormalAdoptRejectsBindingFromAnotherFeatureWorkspace(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	designPath, designDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	contractPath := writeDesignContractRuntime(t, designPath)
	wrongBindingRef := ".specify/features/999-orders/spec-contract.json"
	wrongDigest := writeDesignBindingRuntime(t, wrongBindingRef, "UD-0042", designDigest, contractPath)

	var stdout bytes.Buffer
	exit := runDesign([]string{
		"adopt", "feature:001-orders",
		"--change", "UD-0042",
		"--scope", "web:orders/detail",
		"--mode", "formal",
		"--binding-ref", wrongBindingRef,
		"--binding-sha256", wrongDigest,
		"--expected-change", "none",
	}, &stdout)
	if output := stdout.String(); exit == 0 || !strings.Contains(output, "feature spec-contract.json") {
		t.Fatalf("formal adoption with another feature binding must block: exit=%d output=%s", exit, output)
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
  design_change_ref: .specify/design/changes/UD-0042/design-change.md
  design_change_sha256: %s
  design_contract_ref: %s
`, boundScope, boundChange, designDigest, filepath.ToSlash(contractPath))
		if bindingShape == "flat" {
			bindingBody = fmt.Sprintf(`scope: %s
design_change_id: %s
design_change_ref: .specify/design/changes/UD-0042/design-change.md
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
		doc := quickAdoptionTestDoc(decision, digest, state)
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

func TestDesignQuickAdoptRejectsBindingFromAnotherQuickWorkspace(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	designPath, designDigest := createRegisteredDesignChangeRuntime(t, "UD-0042", "web:orders")
	contractPath := writeDesignContractRuntime(t, designPath)
	workspace := filepath.Join(".planning", "quick", "999-orders")
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
  design_change_id: UD-0042
  design_change_ref: .specify/design/changes/UD-0042/design-change.md
  design_change_sha256: %s
  design_contract_ref: %s
`, designDigest, filepath.ToSlash(contractPath))
	if err := os.WriteFile(filepath.FromSlash(bindingRef), []byte(statusBody), 0o644); err != nil {
		t.Fatal(err)
	}
	decision := quickAdoptionTestDecision(designDigest, filepath.ToSlash(contractPath), "UD-0042")
	confirmationDigest, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	confirmationBody, err := json.Marshal(quickAdoptionTestDoc(decision, confirmationDigest, "confirmed"))
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
	if output := stdout.String(); exit == 0 || !strings.Contains(output, ".planning/quick/<id>/STATUS.md") {
		t.Fatalf("quick adoption with another workspace binding must block: exit=%d output=%s", exit, output)
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
  design_change_ref: .specify/design/changes/UD-0042/design-change.md
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
	confirmationBody, err := json.Marshal(
		quickAdoptionTestDoc(decision, confirmationDigest, "confirmed"),
	)
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
  design_change_ref: .specify/design/changes/UD-0042/design-change.md
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
				confirmation = quickAdoptionTestDoc(
					decision, strings.Repeat("c", 64), "confirmed",
				)
			case "minimal-self-consistent":
				minimalDecision := quickConfirmationDecision{UIConfirmation: decision.UIConfirmation}
				minimalDigest, err := computeQuickConfirmationDigest(minimalDecision)
				if err != nil {
					t.Fatal(err)
				}
				confirmation = quickAdoptionTestDoc(
					minimalDecision, minimalDigest, "confirmed",
				)
			case "tampered-decision":
				decision.Goal = "Tampered after confirmation"
				confirmation = quickAdoptionTestDoc(
					decision, digest, "confirmed",
				)
			default:
				confirmation = quickAdoptionTestDoc(
					decision, digest, "confirmed",
				)
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
			"applicable":           true,
			"confirmation_purpose": "Approve the orders UI direction",
			"user_and_primary_job": "Operators inspect an order",
			"target_experience":    "A clear, efficient order detail",
			"acceptance_evidence":  []any{"Bound UI capture"},
			"source_continuity":    quickNotApplicableSourceContinuity(),
			"design_binding": map[string]any{
				"scope":                "web:orders/detail",
				"design_change_id":     boundChange,
				"design_change_ref":    ".specify/design/changes/UD-0042/design-change.md",
				"design_change_sha256": designDigest,
				"design_contract_ref":  contractPath,
			},
		},
	}
}

func quickAdoptionTestDoc(
	decision quickConfirmationDecision,
	digest string,
	state string,
) quickConfirmationDoc {
	return quickConfirmationDoc{
		Schema:             quickConfirmationSchema,
		Workspace:          "001-orders",
		ConfirmationMode:   "full",
		ConfirmationState:  state,
		ConfirmationDigest: digest,
		Source: quickConfirmationSource{
			Kind:          "prompt",
			SemanticDelta: false,
		},
		Decision: decision,
		Delivery: quickConfirmationDelivery{
			Waves: []quickConfirmationWave{
				{ID: "W1", ItemIDs: []string{"Q1"}, Parallel: false},
			},
		},
	}
}

func TestQuickAdoptionDigestCrossLanguageVector(t *testing.T) {
	decision := quickAdoptionDigestVectorDecision()
	digest, err := computeQuickConfirmationDigest(decision)
	if err != nil {
		t.Fatal(err)
	}
	const expected = "a7edcb09bd31b39c0d753130bd1eb9248d16ab844196377a195124685b36444e"
	if digest != expected {
		t.Fatalf("cross-language quick confirmation digest = %s, want %s", digest, expected)
	}

	changedWriteScope := decision
	changedWriteScope.Items = append([]quickConfirmationItem{}, decision.Items...)
	changedWriteScope.Items[0].WriteScope = []string{"src/changed-but-excluded"}
	changedDigest, err := computeQuickConfirmationDigest(changedWriteScope)
	if err != nil {
		t.Fatal(err)
	}
	if changedDigest != expected {
		t.Fatalf("write_scope changed protected digest: got %s want %s", changedDigest, expected)
	}
}

func quickAdoptionDigestVectorDecision() quickConfirmationDecision {
	return quickConfirmationDecision{
		Goal:              "采用订单 UI <>&\u2028next",
		UserVisibleResult: "顾客看到 résumé",
		Scope: quickConfirmationScope{
			Include: []string{"web:订单/detail"},
			Exclude: []string{"legacy:<&>"},
			Defer:   []string{},
		},
		Items: []quickConfirmationItem{
			{
				ID:          "Q2",
				Deliverable: "完成 >",
				DependsOn:   []string{"Q1"},
				Acceptance:  "通过 &",
				WriteScope:  []string{"src/ignored-two"},
			},
			{
				ID:          "Q1",
				Deliverable: "实现 <",
				DependsOn:   []string{},
				Acceptance:  "截图\u2028ok",
				WriteScope:  []string{"src/ignored-one"},
			},
		},
		RecommendedApproach:   "保持简洁",
		AssumptionsAndRisks:   []string{"风险 <>&"},
		CompletionEvidence:    []string{"证据 ✓"},
		ReconfirmationTrigger: "设计变化",
		UIConfirmation: map[string]any{
			"applicable":           true,
			"confirmation_purpose": "确认 <方向>",
			"user_and_primary_job": "运营 & 检查",
			"target_experience":    "快速 > 清晰",
			"acceptance_evidence":  []any{"截图\u2028完成"},
			"source_continuity":    quickNotApplicableSourceContinuity(),
			"design_binding": map[string]any{
				"scope":                "web:订单/detail",
				"design_change_id":     "UD-0042",
				"design_change_ref":    ".specify/design/changes/UD-0042/design-change.md",
				"design_change_sha256": strings.Repeat("a", 64),
				"design_contract_ref":  ".specify/design/changes/UD-0042/design-contract.json",
			},
		},
		UserCorrections: []string{"excluded from digest"},
	}
}

func createRegisteredDesignChangeRuntime(t *testing.T, changeID, scope string) (string, string) {
	t.Helper()
	var stdout bytes.Buffer
	if exit := runDesign([]string{"change", changeID, "--title", changeID + " design", "--type", "extension", "--scope", scope, "--profiles", "web"}, &stdout); exit != 0 {
		t.Fatalf("create %s failed: %d %s", changeID, exit, stdout.String())
	}
	path := filepath.Join(".specify", "design", "changes", changeID, "design-change.md")
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
	return filepath.Join(".specify", "design", "changes", changeID, "design-change.md")
}

func writeReadyDesignIterationRuntime(t *testing.T, designPath, changeID string, scopes []string, sourceID, sourceDigest string) {
	t.Helper()
	writeReadyDesignChangeRuntime(t, designPath, changeID, scopes, []string{sourceID})
	content := readFile(t, designPath)
	baseline := ".specify/design/changes/" + sourceID + "/design-change.md#sha256=" + sourceDigest
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
	if env.Data["registry_state"] != "present" || env.Data["requires_explicit_adoption"] != true || env.Data["composite"] != (len(env.Items) > 1) {
		t.Fatalf("resolution lost registry, composite, or explicit-adoption semantics: %#v", env)
	}
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
		"design_change_ref":    ".specify/design/changes/" + changeID + "/design-change.md",
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
	if exit := runDesign([]string{"approve", preview, "--direction", "direction-main"}, &stdout); exit != 0 {
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
		"    must_not: []\n" +
		"  style_authority:\n" +
		"    mode: inherit-existing\n" +
		"    scope_level: feature-partial\n" +
		"    source_refs:\n" +
		"      - src/app/page.tsx\n" +
		"    protected_surfaces:\n" +
		"      - global-shell\n" +
		"      - shared-components\n" +
		"    allowed_style_delta_surfaces: []\n" +
		"    authorization_source: null\n"
	design := strings.Replace(validDesignForRuntime, "design_system:\n  schema: spec-kit-design-v1\n", header, 1)
	design = strings.Replace(design, "    style_skill_id: style-minimal-product-linear\n", "    style_skill_id: null\n", 1)
	design = strings.Replace(design, "      - design-library/minimal-product-linear.md\n", "", 1)
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
	handoffPath := strings.TrimSuffix(preview, filepath.Ext(preview)) + ".handoff.json"
	var handoffPayload map[string]any
	if err := json.Unmarshal([]byte(readFile(t, handoffPath)), &handoffPayload); err != nil {
		t.Fatal(err)
	}
	reproduction, ok := handoffPayload["reproduction"].(map[string]any)
	if !ok {
		t.Fatalf("approved handoff reproduction is missing: %#v", handoffPayload)
	}
	verificationMarker := "  verification:\n    required_viewports:\n      - \"390\"\n"
	verificationBlock := verificationMarker
	for _, field := range []string{
		"source_continuity", "surface_catalog", "scenario_matrix",
		"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix",
		"navigation_matrix", "content_matrix", "motion_contract", "usability_validation",
	} {
		raw, err := json.Marshal(reproduction[field])
		if err != nil {
			t.Fatal(err)
		}
		verificationBlock += "    " + field + ": " + string(raw) + "\n"
	}
	design = strings.Replace(design, verificationMarker, verificationBlock, 1)
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

func createDirectionCheckpointFixture(t *testing.T, changeID string, incompleteHandoff bool) (string, string) {
	t.Helper()
	var stdout bytes.Buffer
	if exit := runDesign([]string{
		"change", changeID,
		"--title", "Orders direction checkpoint",
		"--scope", "web:orders/list",
		"--profiles", "web",
	}, &stdout); exit != 0 {
		t.Fatalf("design change scaffold failed: %d %s", exit, stdout.String())
	}
	designPath := filepath.Join(".specify", "design", "changes", changeID, "design-change.md")
	preview := filepath.Join(".specify", "design", "changes", changeID, "previews", "round-01.html")
	stdout.Reset()
	if exit := runDesign([]string{"preview", "--out", preview}, &stdout); exit != 0 {
		t.Fatalf("preview scaffold failed: %d %s", exit, stdout.String())
	}
	configurePreviewCandidate(t, preview)
	if incompleteHandoff {
		removePreviewHandoffField(t, preview, "editing_matrix")
	}
	writePreviewAdjacentManifest(t, preview)
	return preview, designPath
}

func createDirectionImageCheckpointFixture(t *testing.T, changeID string) (string, string, string) {
	t.Helper()
	preview, _ := createDirectionCheckpointFixture(t, changeID, false)
	content := readFile(t, preview)
	manifest, err := parseJSONObject(parseHTMLSummary(content).PreviewManifestText)
	if err != nil {
		t.Fatal(err)
	}
	manifest["visual_collaboration"] = map[string]any{
		"primary_medium":   "image-primary",
		"image_generation": "available",
		"image_inspection": "available",
		"image_editing":    "unavailable",
		"inspection_owner": "agent-and-user",
		"prompt_strategy":  "image-generation",
	}
	handoff := manifest["handoff"].(map[string]any)
	for _, field := range []string{"surface_catalog", "scenario_matrix", "component_contracts"} {
		handoff[field] = []any{}
	}
	base := strings.TrimSuffix(preview, filepath.Ext(preview))
	manifestPath := base + ".manifest.json"
	manifestText, err := marshalPretty(manifest)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(manifestPath, []byte(manifestText), 0o644); err != nil {
		t.Fatal(err)
	}
	image := base + ".png"
	pngBytes, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(image, pngBytes, 0o644); err != nil {
		t.Fatal(err)
	}
	promptPath := base + ".prompt.md"
	prompt := "# Image generation prompt\n\nOne product UI concept with a persistent recovery rail and representative operator states.\n"
	if err := os.WriteFile(promptPath, []byte(prompt), 0o644); err != nil {
		t.Fatal(err)
	}
	return image, manifestPath, promptPath
}

func writePreviewAdjacentManifest(t *testing.T, path string) {
	t.Helper()
	manifest, err := parseJSONObject(parseHTMLSummary(readFile(t, path)).PreviewManifestText)
	if err != nil {
		t.Fatal(err)
	}
	manifestText, err := marshalPretty(manifest)
	if err != nil {
		t.Fatal(err)
	}
	manifestPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".manifest.json"
	if err := os.WriteFile(manifestPath, []byte(manifestText), 0o644); err != nil {
		t.Fatal(err)
	}
}

func removePreviewHandoffField(t *testing.T, path, field string) {
	t.Helper()
	content := readFile(t, path)
	manifest, err := parseJSONObject(parseHTMLSummary(content).PreviewManifestText)
	if err != nil {
		t.Fatal(err)
	}
	handoff, ok := manifest["handoff"].(map[string]any)
	if !ok {
		t.Fatal("preview fixture handoff is missing")
	}
	delete(handoff, field)
	updated, err := replaceEmbeddedJSON(content, designPreviewManifestID, manifest)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(updated), 0o644); err != nil {
		t.Fatal(err)
	}
}

func configurePreviewCandidate(t *testing.T, path string) {
	t.Helper()
	content := readFile(t, path)
	content = strings.ReplaceAll(content, "__ROUND_NUMBER__", "1")
	content = strings.Replace(content, `data-preview-status="scaffold"`, `data-preview-status="candidate"`, 1)
	content = strings.Replace(content, `data-prototype-status="seed"`, `data-prototype-status="authored"`, 1)
	content = strings.ReplaceAll(content, "freeform-seed", "authored-concept")
	content = strings.Replace(content, "Unfinished prototype seed", "Operations command center", 1)
	content = strings.Replace(content, "Replace this seed with the complete project-specific concept before review.", "Review incidents, ownership, and recovery actions in one workspace.", 1)
	content = strings.Replace(content, `"configured": false`, `"configured": true`, 1)
	content = strings.Replace(content, `"status": "scaffold",
    "approved_direction": null`, `"status": "candidate",
    "approved_direction": null`, 1)
	content = strings.Replace(content, `"applicability": "not-assessed"`, `"applicability": "not-applicable"`, 1)
	content = regexp.MustCompile(`__[A-Z0-9_]+__`).ReplaceAllString(content, "Configured design content")
	content = strings.Replace(content, `"variance": null`, `"variance": 5`, 1)
	content = strings.Replace(content, `"motion": null`, `"motion": 3`, 1)
	content = strings.Replace(content, `"density": null`, `"density": 7`, 1)
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
		"__APPROVED_VISUAL_REF__":         ".specify/design/previews/round-01.html#direction-main",
		"__APPROVED_DIRECTION_ID__":       "direction-main",
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

func TestValidDesignComponentAdoptionRequiresNonBlankMetadata(t *testing.T) {
	valid := map[string]any{
		"resource_id": "material-ui", "action": "reuse",
		"package": "@mui/material", "version": "^7.0.0", "license": "MIT",
		"source_ref": "package.json", "component_refs": []any{"TextField"},
		"reason_codes": []any{"installed"}, "selection_basis_refs": []any{"package.json"},
		"permission_gate": "not-required", "permission_status": "authorized",
	}
	if !validDesignComponentAdoption(valid) {
		t.Fatal("complete component adoption should be valid")
	}
	for _, field := range []string{"package", "version", "license"} {
		invalid := cloneJSONMap(valid)
		invalid[field] = ""
		if validDesignComponentAdoption(invalid) {
			t.Fatalf("blank %s must be rejected", field)
		}
	}
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
