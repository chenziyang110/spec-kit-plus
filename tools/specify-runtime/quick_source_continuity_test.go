package main

import (
	"strings"
	"testing"
)

func sourceContinuityQuickInput() map[string]any {
	return map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal":                "Reconstruct a source-grounded interface without losing behavior.",
			"user_visible_result": "The target UI preserves visible structure, business actions, and assets.",
			"scope": map[string]any{
				"include": []any{"main workspace"},
				"exclude": []any{"unrelated settings"},
			},
			"items": []any{
				map[string]any{
					"id": "Q1", "deliverable": "source-grounded UI reconstruction",
					"depends_on": []any{}, "acceptance": "source and target click paths reach the same final result",
				},
			},
			"reconfirmation_trigger": "A source surface, business action, asset disposition, or unresolved gap changes.",
			"ui_confirmation": map[string]any{
				"applicable":                       true,
				"confirmation_purpose":             "Confirm visual and behavioral continuity.",
				"user_and_primary_job":             "An operator exports the current document.",
				"design_basis_and_source_material": []any{"main-window.png", "legacy/main_window.cpp"},
				"target_experience":                "The reconstructed workspace behaves like the source where preserved.",
				"acceptance_evidence":              []any{"source-target click-path comparison"},
				"source_continuity": map[string]any{
					"schema":        "spec-kit-ui-source-continuity-v1",
					"applicability": "required",
					"mode":          "mixed",
					"reason":        "Visual, runtime, and implementation sources govern the reconstruction.",
					"authority_refs": []any{
						"main-window.png", "legacy/main_window.cpp",
					},
					"surface_bindings": []any{
						map[string]any{
							"id": "SC-SURFACE-001", "surface_id": "main-workspace",
							"source_refs": []any{"legacy/main_window.cpp"},
							"discovery": "measured", "disposition": "adapt",
							"rationale": "Preserve the workspace while adapting platform chrome.",
						},
					},
					"action_bindings": []any{
						map[string]any{
							"id": "SC-ACTION-001", "interaction_id": "export-action",
							"source_refs": []any{"legacy/main_window.cpp#exportAction"},
							"user_promise": "Export the current document.",
							"business_outcome": "A selected file contains the current document.",
							"side_effects": []any{"write one file"},
							"final_state": "The exported path is visible and the workspace remains usable.",
							"verification": "Run the source and target click path with the same document.",
						},
					},
					"asset_bindings": []any{
						map[string]any{
							"id": "SC-ASSET-001", "component_id": "export-button",
							"semantic_role": "export action", "source_refs": []any{"assets/export.svg"},
							"target_strategy": "preserve", "target_ref": "src/assets/export.svg",
							"provenance": "project-owned", "fallback": "Export text label",
							"placeholder_policy": "forbid-character-substitution",
						},
					},
					"unresolved_gaps": []any{},
				},
			},
		},
	}
}

func TestQuickSourceContinuityIsValidatedRenderedAndPacketized(t *testing.T) {
	input := sourceContinuityQuickInput()
	doc, err := normalizeQuickConfirmationInput(input, "260826-001", nil, false)
	if err != nil {
		t.Fatalf("normalize source continuity checkpoint: %v", err)
	}
	if err := validateQuickConfirmation(doc); err != nil {
		t.Fatalf("validate source continuity checkpoint: %v", err)
	}

	view := renderQuickDecisionView(doc)
	for _, marker := range []string{
		"来源连续性", "Export the current document", "A selected file contains the current document",
		"forbid-character-substitution", "未解决缺口：无",
	} {
		if !strings.Contains(view, marker) {
			t.Fatalf("source continuity decision view missing %q: %s", marker, view)
		}
	}

	doc.ConfirmationState = "confirmed"
	doc.ConfirmationDigest = strings.Repeat("a", 64)
	packet, ready, blockers, err := compileQuickWorkerPacket(doc, "Q1")
	if err != nil || !ready || len(blockers) != 0 {
		t.Fatalf("compile packet ready=%v blockers=%v err=%v", ready, blockers, err)
	}
	ui := packet["ui_confirmation"].(map[string]any)
	if len(mapValue(ui["source_continuity"])) == 0 {
		t.Fatalf("worker packet lost source continuity: %#v", packet)
	}
}

func TestQuickSourceContinuityRejectsMissingActionsOpenGapsAndCharacterPlaceholders(t *testing.T) {
	input := sourceContinuityQuickInput()
	ui := mapValue(mapValue(input["decision"])["ui_confirmation"])
	continuity := mapValue(ui["source_continuity"])
	continuity["action_bindings"] = []any{}
	continuity["unresolved_gaps"] = []any{"secondary dialogs are unexplored"}
	assets := continuity["asset_bindings"].([]any)
	asset := assets[0].(map[string]any)
	asset["placeholder_policy"] = "allow-character-substitution"
	asset["target_ref"] = "text:★"

	doc, err := normalizeQuickConfirmationInput(input, "260826-002", nil, false)
	if err != nil {
		t.Fatalf("normalize invalid source continuity checkpoint: %v", err)
	}
	err = validateQuickConfirmation(doc)
	if err == nil {
		t.Fatal("invalid source continuity checkpoint unexpectedly passed")
	}
	message := strings.ToLower(err.Error())
	if !strings.Contains(message, "source_continuity") {
		t.Fatalf("unexpected validation error: %v", err)
	}
}

