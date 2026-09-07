package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestDesignPromptCreatesRuntimeOwnedPromptFromManifest(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	image, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9101")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	exit := runDesign([]string{"prompt", manifestPath, "--content", exactTestDesignImagePrompt}, &stdout)

	if exit != 0 {
		t.Fatalf("design prompt failed: exit=%d output=%s", exit, stdout.String())
	}
	if _, err := os.Stat(promptPath); err != nil {
		t.Fatalf("runtime-owned prompt was not written next to %s: %v", image, err)
	}
	prompt := readFile(t, promptPath)
	for _, want := range []string{
		"Image Generation Prompt",
		"direction-main",
		"Must preserve",
		"Must not",
	} {
		if !strings.Contains(prompt, want) {
			t.Fatalf("prompt missing %q:\n%s", want, prompt)
		}
	}
}

func TestDesignPromptBindsExactStdinContentCreateOnly(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9110")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	exactPrompt := "# Exact ImageGen Edit Prompt\n\nEdit only the attached live-product baseline.\n"

	var stdout bytes.Buffer
	exit := runDesignWithPromptStdin(t, exactPrompt, []string{"prompt", manifestPath, "--content", "-"}, &stdout)
	if exit != 0 {
		t.Fatalf("design prompt stdin create failed: exit=%d output=%s", exit, stdout.String())
	}
	if actual := readFile(t, promptPath); actual != exactPrompt {
		t.Fatalf("prompt bytes differ from stdin:\nactual=%q\nwant=%q", actual, exactPrompt)
	}
	createdPayload := decodeJSONObject(t, stdout.Bytes())
	createdData := requireObject(t, createdPayload, "data")
	createdReceipt := requireObject(t, createdData, "receipt")
	expectedPromptPath, err := filepath.Abs(promptPath)
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Clean(fmt.Sprint(createdData["path"])) != filepath.Clean(expectedPromptPath) || createdData["sha256"] != sha256String(exactPrompt) || createdReceipt["content_authority"] != "agent-authored-exact" {
		t.Fatalf("design prompt response did not return canonical path, digest, and receipt: %#v", createdData)
	}
	generation := readDesignIterationGuardJSONFile(t, strings.TrimSuffix(promptPath, ".prompt.md")+".generation.json")
	if generation["content_authority"] != "agent-authored-exact" {
		t.Fatalf("content authority = %#v", generation["content_authority"])
	}
	if generation["prompt_sha256"] != sha256String(exactPrompt) {
		t.Fatalf("prompt digest = %#v", generation["prompt_sha256"])
	}
	var showOut, showErr bytes.Buffer
	if code := Run([]string{"artifact", "show", "--path", promptPath, "--format", "json"}, &showOut, &showErr, "test"); code != 0 {
		t.Fatalf("artifact show failed: code=%d stdout=%s stderr=%s", code, showOut.String(), showErr.String())
	}
	showPayload := decodeJSONObject(t, showOut.Bytes())
	showData := requireObject(t, showPayload, "data")
	if showData["owner"] != "specify-runtime design prompt" || showData["sha256"] != sha256String(exactPrompt) {
		t.Fatalf("artifact show did not expose prompt owner and digest: %#v", showData)
	}
	var prepareOut, prepareErr bytes.Buffer
	if code := Run([]string{"artifact", "prepare", "--path", promptPath, "--format", "json"}, &prepareOut, &prepareErr, "test"); code == 0 || !strings.Contains(prepareOut.String(), "specify-runtime design prompt") {
		t.Fatalf("generic artifact prepare bypassed prompt ownership: code=%d stdout=%s stderr=%s", code, prepareOut.String(), prepareErr.String())
	}

	stdout.Reset()
	if exit := runDesignWithPromptStdin(t, exactPrompt, []string{"prompt", manifestPath, "--content", "-"}, &stdout); exit != 0 {
		t.Fatalf("identical retry failed: exit=%d output=%s", exit, stdout.String())
	}
	replacement := strings.Replace(exactPrompt, "only", "and redraw everything", 1)
	stdout.Reset()
	if exit := runDesignWithPromptStdin(t, replacement, []string{"prompt", manifestPath, "--content", "-"}, &stdout); exit == 0 || !strings.Contains(strings.ToLower(stdout.String()), "new numbered round") {
		t.Fatalf("different prompt replaced the immutable prompt: exit=%d output=%s", exit, stdout.String())
	}
	if actual := readFile(t, promptPath); actual != exactPrompt {
		t.Fatalf("rejected replacement changed prompt bytes: %q", actual)
	}
	stdout.Reset()
	if exit := runDesignWithPromptStdin(t, replacement, []string{"prompt", manifestPath, "--content", "-", "--force"}, &stdout); exit == 0 {
		t.Fatalf("legacy --force bypassed create-only prompt ownership: %s", stdout.String())
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesignWithPromptStdin(t, exactPrompt, []string{"prompt", manifestPath, "--content", "-"}, &stdout); exit == 0 || !strings.Contains(strings.ToLower(stdout.String()), "partial") {
		t.Fatalf("partial prompt bundle was silently repaired: exit=%d output=%s", exit, stdout.String())
	}
}

func TestDesignPromptRejectsInvalidExactContent(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9111")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	for _, content := range []string{"   \n", "valid prefix\x00invalid suffix", strings.Repeat("x", maxDesignImagePromptBytes+1)} {
		var stdout bytes.Buffer
		if exit := runDesignWithPromptStdin(t, content, []string{"prompt", manifestPath, "--content", "-"}, &stdout); exit == 0 {
			t.Fatalf("design prompt accepted invalid content %q: %s", content, stdout.String())
		}
	}
}

func TestDesignPromptRejectsNonDraftAndRoundMismatch(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9112")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	index := readDesignChangeIndexRuntime(t)
	record := designChangeRecordRuntime(t, index, "UD-9112")
	record["status"] = "approved"
	writeDesignIterationGuardJSONFile(t, filepath.Join(".specify", "design", "index.json"), index)

	var stdout bytes.Buffer
	if exit := runDesign([]string{"prompt", manifestPath, "--content", exactTestDesignImagePrompt}, &stdout); exit == 0 || !strings.Contains(strings.ToLower(stdout.String()), "draft workspace") {
		t.Fatalf("design prompt accepted non-draft change: exit=%d output=%s", exit, stdout.String())
	}
	record["status"] = "draft"
	writeDesignIterationGuardJSONFile(t, filepath.Join(".specify", "design", "index.json"), index)
	manifest := readDesignIterationGuardJSONFile(t, manifestPath)
	manifest["review"].(map[string]any)["round"] = "13"
	writeDesignIterationGuardJSONFile(t, manifestPath, manifest)
	stdout.Reset()
	if exit := runDesign([]string{"prompt", manifestPath, "--content", exactTestDesignImagePrompt}, &stdout); exit == 0 || !strings.Contains(strings.ToLower(stdout.String()), "filename") {
		t.Fatalf("design prompt accepted mismatched round: exit=%d output=%s", exit, stdout.String())
	}
}

func TestDesignPromptRejectsUnresolvedSurfacePosture(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9108")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	designPath := filepath.Join(".specify", "design", "changes", "UD-9108", "design-change.md")
	design := strings.Replace(readFile(t, designPath), "    mode: greenfield", "    mode: unresolved", 1)
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	if exit := runDesign([]string{"prompt", manifestPath, "--content", exactTestDesignImagePrompt}, &stdout); exit == 0 || !strings.Contains(strings.ToLower(stdout.String()), "surface posture") {
		t.Fatalf("design prompt accepted unresolved surface posture: %s", stdout.String())
	}
}

func TestDesignPromptForInheritExistingRequiresEditBaseline(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	imagePath, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9102")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	designPath := filepath.Join(".specify", "design", "changes", "UD-9102", "design-change.md")
	design := inheritExistingDesignText(t, readFile(t, designPath))
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
	current := filepath.Join("src", "app", "materials", "current.png")
	if err := os.MkdirAll(filepath.Dir(current), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(current, mustReadBytes(t, imagePath), 0o644); err != nil {
		t.Fatal(err)
	}
	manifest := readDesignIterationGuardJSONFile(t, manifestPath)
	manifest["input_images"] = []any{
		map[string]any{
			"ref": "src/app/materials/current.png", "role": "edit-source",
			"surface_ids": []any{"global-shell", "shared-components"}, "fidelity": "exact",
		},
	}
	manifest["visual_collaboration"].(map[string]any)["image_editing"] = "available"
	handoff := manifest["handoff"].(map[string]any)
	continuity := handoff["source_continuity"].(map[string]any)
	coverage := continuity["coverage"].(map[string]any)
	coverage["surface_ids"] = append(stringList(coverage["surface_ids"]), "global-shell", "shared-components")
	surfaceBindings := continuity["surface_bindings"].([]any)
	for index, surface := range []string{"global-shell", "shared-components"} {
		surfaceBindings = append(surfaceBindings, map[string]any{
			"id":          fmt.Sprintf("SC-SURFACE-90%d", index+1),
			"surface_id":  surface,
			"source_refs": []any{"src/app/materials/current.png"},
			"discovery":   "measured",
			"disposition": "preserve",
			"use_intent":  "exact",
			"fidelity":    "exact",
			"rationale":   "Protected live-product baseline.",
		})
	}
	continuity["surface_bindings"] = surfaceBindings
	writeDesignIterationGuardJSONFile(t, manifestPath, manifest)

	var stdout bytes.Buffer
	inheritedPrompt := "# Image Generation Prompt\n\nOperation: edit\n\nEdit src/app/materials/current.png while preserving global-shell and shared-components exactly.\n"
	exit := runDesign([]string{"prompt", manifestPath, "--content", inheritedPrompt}, &stdout)

	if exit != 0 {
		t.Fatalf("design prompt failed: exit=%d output=%s", exit, stdout.String())
	}
	prompt := strings.ToLower(readFile(t, promptPath))
	for _, want := range []string{
		"operation: edit",
		"src/app/materials/current.png",
		"global-shell",
		"shared-components",
	} {
		if !strings.Contains(prompt, want) {
			t.Fatalf("inherit-existing prompt missing %q:\n%s", want, prompt)
		}
	}
}

func TestDesignPromptRejectsManifestStyleAuthorityShadow(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	_, manifestPath, _ := createDirectionImageCheckpointFixture(t, "UD-9106")
	manifest := readDesignIterationGuardJSONFile(t, manifestPath)
	manifest["style_authority"] = map[string]any{"mode": "inherit-existing"}
	writeDesignIterationGuardJSONFile(t, manifestPath, manifest)

	var stdout bytes.Buffer
	exit := runDesign([]string{"prompt", manifestPath, "--content", exactTestDesignImagePrompt}, &stdout)

	if exit == 0 {
		t.Fatalf("design prompt accepted manifest.style_authority shadow: %s", stdout.String())
	}
	if !strings.Contains(strings.ToLower(stdout.String()), "manifest.style_authority") {
		t.Fatalf("design prompt failed for the wrong reason: %s", stdout.String())
	}
}

func TestDesignPreviewLintConceptWritesReceiptSidecar(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	image, _, promptPath := createDirectionImageCheckpointFixture(t, "UD-9103")

	var stdout bytes.Buffer
	exit := runDesign([]string{"preview-lint", image, "--level", "concept"}, &stdout)

	if exit != 0 {
		t.Fatalf("concept lint failed: exit=%d output=%s", exit, stdout.String())
	}
	receiptPath := strings.TrimSuffix(image, filepath.Ext(image)) + ".concept.json"
	receipt := readDesignIterationGuardJSONFile(t, receiptPath)
	if receipt["schema"] != "spec-kit-design-concept-lint-receipt-v1" {
		t.Fatalf("concept receipt schema = %#v", receipt["schema"])
	}
	if receipt["prompt_sha256"] != sha256String(readFile(t, promptPath)) {
		t.Fatalf("concept receipt did not bind the current prompt: %#v", receipt)
	}
}

func TestDesignDirectionConfirmRequiresCurrentConceptReceipt(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	image, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9104")

	var stdout bytes.Buffer
	exit := runDesign([]string{
		"direction-confirm", image,
		"--direction", "direction-main",
		"--manifest", manifestPath,
		"--prompt", promptPath,
		"--image-inspection", "available",
		"--image-editing", "unavailable",
	}, &stdout)

	if exit == 0 {
		t.Fatalf("direction-confirm accepted an image round without concept receipt: %s", stdout.String())
	}
	if !strings.Contains(strings.ToLower(stdout.String()), "concept receipt") {
		t.Fatalf("direction-confirm failed for the wrong reason: %s", stdout.String())
	}
}

func TestDesignInheritExistingConceptReceiptRequiresProtectedSurfaceInspection(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	imagePath, manifestPath, promptPath := createDirectionImageCheckpointFixture(t, "UD-9107")
	if err := os.Remove(promptPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(strings.TrimSuffix(promptPath, ".prompt.md") + ".generation.json"); err != nil {
		t.Fatal(err)
	}
	designPath := filepath.Join(".specify", "design", "changes", "UD-9107", "design-change.md")
	design := inheritExistingDesignText(t, readFile(t, designPath))
	if err := os.WriteFile(designPath, []byte(design), 0o644); err != nil {
		t.Fatal(err)
	}
	baselineRef := filepath.ToSlash(filepath.Join("src", "app", "materials", "current.png"))
	if err := os.MkdirAll(filepath.Dir(baselineRef), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(baselineRef, mustReadBytes(t, imagePath), 0o644); err != nil {
		t.Fatal(err)
	}
	manifest := readDesignIterationGuardJSONFile(t, manifestPath)
	manifest["visual_collaboration"].(map[string]any)["image_editing"] = "available"
	manifest["input_images"] = []any{map[string]any{
		"ref": baselineRef, "role": "edit-source",
		"surface_ids": []any{"global-shell", "shared-components"}, "fidelity": "exact",
	}}
	continuity := manifest["handoff"].(map[string]any)["source_continuity"].(map[string]any)
	coverage := continuity["coverage"].(map[string]any)
	coverage["surface_ids"] = append(stringList(coverage["surface_ids"]), "global-shell", "shared-components")
	bindings := continuity["surface_bindings"].([]any)
	for index, surface := range []string{"global-shell", "shared-components"} {
		bindings = append(bindings, map[string]any{
			"id": fmt.Sprintf("SC-SURFACE-91%d", index+1), "surface_id": surface,
			"source_refs": []any{baselineRef}, "discovery": "measured",
			"disposition": "preserve", "use_intent": "exact", "fidelity": "exact",
			"rationale": "Protected live-product baseline.",
		})
	}
	continuity["surface_bindings"] = bindings
	writeDesignIterationGuardJSONFile(t, manifestPath, manifest)

	var stdout bytes.Buffer
	inheritedPrompt := "# Image Generation Prompt\n\nOperation: edit\n\nEdit src/app/materials/current.png while preserving global-shell and shared-components exactly.\n"
	if exit := runDesign([]string{"prompt", manifestPath, "--content", inheritedPrompt}, &stdout); exit != 0 {
		t.Fatalf("design prompt failed: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", imagePath, "--level", "concept"}, &stdout); exit == 0 || !strings.Contains(stdout.String(), "inspection-json") {
		t.Fatalf("concept lint accepted missing protected-surface inspection: %s", stdout.String())
	}
	review := map[string]any{
		"verdict": "pass", "reviewer": "agent",
		"protected_surfaces": []any{
			map[string]any{"surface_id": "global-shell", "baseline_ref": baselineRef, "status": "preserved", "evidence": "Compared saved pixels with the exact baseline."},
			map[string]any{"surface_id": "shared-components", "baseline_ref": baselineRef, "status": "preserved", "evidence": "Compared saved pixels with the exact baseline."},
		},
		"observed_differences": []any{map[string]any{
			"surface_id": "web:orders/list", "summary": "Changed only the bounded workbench.", "authorized": true,
		}},
	}
	reviewRaw, err := json.Marshal(review)
	if err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if exit := runDesign([]string{"preview-lint", imagePath, "--level", "concept", "--inspection-json", string(reviewRaw)}, &stdout); exit != 0 {
		t.Fatalf("concept lint rejected valid inspection: %d %s", exit, stdout.String())
	}
	receipt := readDesignIterationGuardJSONFile(t, strings.TrimSuffix(imagePath, filepath.Ext(imagePath))+".concept.json")
	if !reflect.DeepEqual(receipt["visual_review"], review) {
		t.Fatalf("visual review receipt = %#v, want %#v", receipt["visual_review"], review)
	}
}

func TestDesignImportImageRoundRequiresGenerationSidecar(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)
	var stdout bytes.Buffer
	if exit := runDesign([]string{
		"change", "UD-9105",
		"--title", "Generation-bound import",
		"--scope", "web:materials/list",
		"--profiles", "web",
	}, &stdout); exit != 0 {
		t.Fatalf("design change scaffold failed: %d %s", exit, stdout.String())
	}
	source := filepath.Join(tmp, "generated.png")
	pngBytes, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII=")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(source, pngBytes, 0o644); err != nil {
		t.Fatal(err)
	}

	stdout.Reset()
	exit := runDesign([]string{"import", source, "--change", "UD-9105", "--round", "1"}, &stdout)

	if exit == 0 {
		t.Fatalf("design import accepted an image round without generation sidecar: %s", stdout.String())
	}
	if !strings.Contains(strings.ToLower(stdout.String()), "generation") {
		t.Fatalf("design import failed for the wrong reason: %s", stdout.String())
	}
}

func readDesignIterationGuardJSONFile(t *testing.T, path string) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal([]byte(readFile(t, path)), &payload); err != nil {
		t.Fatalf("decode %s: %v", path, err)
	}
	return payload
}

func writeDesignIterationGuardJSONFile(t *testing.T, path string, payload map[string]any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func runDesignWithPromptStdin(t *testing.T, content string, args []string, stdout *bytes.Buffer) int {
	t.Helper()
	input, err := os.CreateTemp(t.TempDir(), "design-prompt-stdin-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := input.WriteString(content); err != nil {
		t.Fatal(err)
	}
	if _, err := input.Seek(0, 0); err != nil {
		t.Fatal(err)
	}
	priorStdin := os.Stdin
	os.Stdin = input
	defer func() {
		os.Stdin = priorStdin
		_ = input.Close()
	}()
	return runDesign(args, stdout)
}

func mustReadBytes(t *testing.T, path string) []byte {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

func inheritExistingDesignText(t *testing.T, design string) string {
	t.Helper()
	marker := strings.Index(design, "  style_authority:")
	if marker < 0 {
		t.Fatal("design fixture has no style_authority block")
	}
	prefix, authority := design[:marker], design[marker:]
	authority = strings.Replace(authority, "    mode: greenfield", "    mode: inherit-existing", 1)
	authority = strings.Replace(authority, "    scope_level: null", "    scope_level: feature-partial", 1)
	authority = strings.Replace(authority, "    source_refs: []", "    source_refs: [\"src/app/materials/page.tsx\"]", 1)
	authority = strings.Replace(authority, "    protected_surfaces: []", "    protected_surfaces: [\"global-shell\",\"shared-components\"]", 1)
	return prefix + authority
}
