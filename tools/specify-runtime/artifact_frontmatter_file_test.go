package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestArtifactPatchBindsLargeFileBackedJSONIntoNestedFrontmatter(t *testing.T) {
	tmp := t.TempDir()
	withCwd(t, tmp)

	designPath, err := scaffoldDesignChange(
		"UD-0042",
		"Large handoff binding",
		"extension",
		[]string{"web:workshop"},
		[]string{"web"},
		nil,
		nil,
		"",
		"",
	)
	if err != nil {
		t.Fatal(err)
	}

	reproduction := map[string]any{
		"source_continuity": map[string]any{
			"schema":           "spec-kit-ui-source-continuity-v1",
			"applicability":    "not-assessed",
			"mode":             "none",
			"coverage":         map[string]any{"surface_ids": []any{}, "interaction_ids": []any{}, "component_ids": []any{}},
			"authority_refs":   []any{},
			"surface_bindings": []any{},
			"action_bindings":  []any{},
			"asset_bindings":   []any{},
			"unresolved_gaps":  []any{},
		},
		"required_viewports":   []any{},
		"required_states":      []any{},
		"surface_catalog":      []any{},
		"scenario_matrix":      []any{},
		"interaction_matrix":   []any{},
		"editing_matrix":       []any{},
		"data_state_matrix":    []any{},
		"accessibility_matrix": []any{},
		"navigation_matrix":    []any{},
		"content_matrix":       []any{},
		"motion_contract":      map[string]any{},
		"usability_validation": map[string]any{},
		"visual_tolerance":     nil,
		"accepted_deviations":  []any{},
		"large_payload_probe":  strings.Repeat("handoff-contract-", 5000),
	}
	handoff := map[string]any{
		"schema":       designHandoffSchema,
		"reproduction": reproduction,
	}
	handoffRaw, err := json.MarshalIndent(handoff, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if len(handoffRaw) <= 32*1024 {
		t.Fatalf("fixture must exceed the practical Windows argv limit: %d bytes", len(handoffRaw))
	}
	handoffPath := filepath.Join(filepath.Dir(designPath), "previews", "round-01.handoff.json")
	if err := os.MkdirAll(filepath.Dir(handoffPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(handoffPath, handoffRaw, 0o644); err != nil {
		t.Fatal(err)
	}

	service := NewArtifactService(".")
	lease := service.Prepare(ArtifactPrepareRequest{Path: filepath.ToSlash(designPath)})
	leaseID, _ := lease.Data["lease_id"].(string)
	if lease.Status != "ok" || leaseID == "" {
		t.Fatalf("prepare design contract lease: %#v", lease)
	}

	var stdout, stderr bytes.Buffer
	exit := Run([]string{
		"artifact", "patch",
		"--project-root", ".",
		"--lease", leaseID,
		"--frontmatter-pointer", "/design_change/verification",
		"--value-json", "@" + filepath.ToSlash(handoffPath),
		"--value-json-pointer", "/reproduction",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if exit != 0 {
		t.Fatalf("file-backed nested frontmatter patch exit=%d stdout=%s stderr=%s", exit, stdout.String(), stderr.String())
	}

	doc, err := parseDesignMarkdown(readFile(t, designPath), designPath)
	if err != nil {
		t.Fatalf("patched design contract must remain parseable: %v", err)
	}
	verification, ok := doc.DesignSystem["verification"].(map[string]any)
	if !ok {
		t.Fatalf("verification is not a mapping: %#v", doc.DesignSystem["verification"])
	}
	if canonicalJSONSHA256(verification) != canonicalJSONSHA256(reproduction) {
		t.Fatal("nested frontmatter did not bind the exact handoff reproduction")
	}
}
