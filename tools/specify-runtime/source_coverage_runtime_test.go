package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/specvalidate"
)

func TestValidateSpecLightRejectsMissingAcceptanceCoverage(t *testing.T) {
	feature := t.TempDir()
	if err := os.WriteFile(filepath.Join(feature, "spec.md"), []byte("# Spec\n\n## Requirements\n- Import the entire document.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	contract := map[string]any{
		"scope":                 map[string]any{"in": []any{"Import every source document unit"}},
		"capability_operations": []any{},
		"acceptance_criteria":   []any{"The last document unit is imported"},
	}
	raw, err := json.Marshal(contract)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(feature, "spec-contract.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	env := ValidateSpec(SpecValidationRequest{FeatureDir: feature, Tier: "light"})
	if env.Status != "blocked" {
		t.Fatalf("missing requirement-to-acceptance coverage passed the actual light gate: %#v", env)
	}
}

func downstreamSourceFixture(t *testing.T) (string, string, map[string]any, map[string]any) {
	t.Helper()
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "coverage")
	content := []byte("Import all units; preserve the final exception.")
	contentDigest := sha256.Sum256(content)
	digest := hex.EncodeToString(contentDigest[:])
	unitID := "U0001-" + digest[:12]
	snapshotRef := ".specify/discussions/source/materials/MAT-001/content.txt"
	if err := os.MkdirAll(filepath.Dir(filepath.Join(root, filepath.FromSlash(snapshotRef))), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(snapshotRef)), content, 0o644); err != nil {
		t.Fatal(err)
	}
	productSource := filepath.Join(root, "source-material.txt")
	if err := os.WriteFile(productSource, content, 0o644); err != nil {
		t.Fatal(err)
	}
	material := map[string]any{
		"id": "MAT-001", "inspection_status": "inspected",
		"reading": map[string]any{"version": 1, "content_sha256": digest, "snapshot_ref": snapshotRef, "source_path": productSource,
			"units": []any{map[string]any{"id": unitID, "start_rune": 0, "end_rune": len(content), "sha256": digest}}, "delivered_unit_ids": []any{unitID}},
		"unit_dispositions": []any{map[string]any{"unit_id": unitID, "disposition": "requirements", "requirement_ids": []any{"REQ-001", "REQ-002"}}},
	}
	sourceRefs := []any{map[string]any{"material_id": "MAT-001", "unit_id": unitID, "locator": "complete document"}}
	requirements := map[string]any{"source_requirements": []any{
		map[string]any{"id": "REQ-001", "statement": "Import all units", "source_refs": sourceRefs, "disposition": "in_scope"},
		map[string]any{"id": "REQ-002", "statement": "Preserve the final exception", "source_refs": sourceRefs, "disposition": "in_scope"},
	}}
	packet := map[string]any{"discussion_slug": "source", "requirements_snapshot": requirements, "source_materials": []any{material}}
	snapshotDigest, err := specvalidate.DiscussionSnapshotDigest(specvalidate.DiscussionSemanticSnapshot(packet))
	if err != nil {
		t.Fatal(err)
	}
	sourceRef := ".specify/discussions/source/handoff-to-specify.json"
	handoff := map[string]any{
		"version": 5, "entry_source": "sp-discussion", "handoff_kind": "discussion_requirement_contract", "status": "handoff-ready",
		"planning_gate_status": "ready", "coverage_status": "complete", "hard_unknown_count": 0, "open_conflict_count": 0,
		"recommended_consumer": "sp-specify", "consumer_eligibility": map[string]any{"sp-specify": map[string]any{"status": "ready"}},
		"source_contract": sourceRef, "discussion_snapshot_digest": snapshotDigest, "source_materials": []any{material}, "agent_requirement_contract": requirements,
	}
	reviewDigest, err := specvalidate.DiscussionReviewDigest(handoff)
	if err != nil {
		t.Fatal(err)
	}
	handoff["review_digest"] = reviewDigest
	handoff["quality_gate"] = map[string]any{"status": "user_confirmed", "confirmed_digest": reviewDigest}
	writeTaskRuntimeFixture(t, filepath.Join(root, filepath.FromSlash(sourceRef)), handoff)
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "discussions", "source", "discussion-state.json"), map[string]any{"turn_packet": packet, "latest_checkpoint": map[string]any{"snapshot_sha256": snapshotDigest}})
	coverage := []any{
		map[string]any{"requirement_id": "REQ-001", "disposition": "in_scope", "requirement_refs": []any{"spec-contract.json#/scope/in/0"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/0"}},
		map[string]any{"requirement_id": "REQ-002", "disposition": "in_scope", "requirement_refs": []any{"spec-contract.json#/scope/in/1"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/1"}},
	}
	spec := map[string]any{
		"source_contract": sourceRef, "source_revision": reviewDigest,
		"scope": map[string]any{"in": []any{"Import all units", "Preserve the final exception"}}, "capability_operations": []any{},
		"acceptance_criteria": []any{"All units are imported", "The final exception is applied"},
		"acceptance_coverage": []any{
			map[string]any{"requirement_ref": "spec-contract.json#/scope/in/0", "acceptance_ref": "spec-contract.json#/acceptance_criteria/0"},
			map[string]any{"requirement_ref": "spec-contract.json#/scope/in/1", "acceptance_ref": "spec-contract.json#/acceptance_criteria/1"},
		}, "source_requirement_coverage": coverage,
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "spec-contract.json"), spec)
	if err := os.WriteFile(filepath.Join(feature, "spec.md"), []byte("# Spec\n## Requirements\nImport all units and retain the final exception.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	acceptanceRefs := []any{"spec-contract.json#/acceptance_criteria/0", "spec-contract.json#/acceptance_criteria/1"}
	plan := map[string]any{
		"version": 2, "status": "ready", "source_contract": "spec-contract.json", "source_revision": 1,
		"acceptance_refs": acceptanceRefs, "source_requirement_coverage": coverage,
		"transition": map[string]any{"version": 1, "status": "ready", "source_ref": "plan-contract.json", "semantic_delta": []any{}, "required_refs": []any{}, "blockers": []any{}, "next_action": "/sp.tasks"},
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "plan-contract.json"), plan)
	index := map[string]any{
		"version": 2, "status": "ready", "source_revision": 1, "source_requirement_coverage": coverage, "acceptance_refs": acceptanceRefs,
		"tasks": []any{
			map[string]any{"id": "T001", "objective": "Import all source units", "acceptance": []any{"All units imported"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/0"}},
			map[string]any{"id": "T002", "objective": "Apply the final exception", "acceptance": []any{"Final exception retained"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/1"}},
		},
	}
	return root, feature, plan, index
}

func TestPlanAndTasksRejectDroppedSourceRequirementCoverage(t *testing.T) {
	root, feature, plan, index := downstreamSourceFixture(t)
	if err := validatePlanContract(root, feature, ".specify/features/coverage"); err != nil {
		t.Fatal(err)
	}
	if err := validateTaskControlSourceRequirements(feature, index); err != nil {
		t.Fatal(err)
	}
	delete(plan, "source_requirement_coverage")
	writeTaskRuntimeFixture(t, filepath.Join(feature, "plan-contract.json"), plan)
	if err := validatePlanContract(root, feature, ".specify/features/coverage"); err == nil {
		t.Fatal("Plan omitted reviewed source rows")
	}
	if err := validateTaskControlSourceRequirements(feature, index); err == nil {
		t.Fatal("Tasks accepted a Plan with omitted source rows")
	}
}

func TestTaskFinalizationSourceGateRejectsUnallocatedAcceptance(t *testing.T) {
	_, feature, _, index := downstreamSourceFixture(t)
	task := index["tasks"].([]any)[1].(map[string]any)
	delete(task, "acceptance_refs")
	if err := validateTaskControlSourceRequirements(feature, index); err == nil {
		t.Fatal("complete index refs hid a missing task assignment")
	}
}

func TestConfirmedSourceCoverageRemainsValidAfterProductSourceChanges(t *testing.T) {
	root, feature, _, index := downstreamSourceFixture(t)
	if err := os.WriteFile(filepath.Join(root, "source-material.txt"), []byte("Implementation legitimately changes the source product."), 0o644); err != nil {
		t.Fatal(err)
	}
	if env := ValidateSpec(SpecValidationRequest{FeatureDir: feature, Tier: "light"}); env.Status != "ok" {
		t.Fatalf("frozen reviewed source was invalidated by product edits: %#v", env)
	}
	if err := validatePlanContract(root, feature, ".specify/features/coverage"); err != nil {
		t.Fatal(err)
	}
	if err := validateTaskControlSourceRequirements(feature, index); err != nil {
		t.Fatal(err)
	}
}

func TestSourceBoundTasksNormalizePlanAcceptanceAliasesBeforeCoverage(t *testing.T) {
	for _, prefix := range []string{"plan-contract.json#/acceptance_refs/", "#/acceptance_refs/"} {
		t.Run(prefix, func(t *testing.T) {
			_, feature, _, index := downstreamSourceFixture(t)
			index["acceptance_refs"] = []any{prefix + "0", prefix + "1"}
			index["tasks"].([]any)[0].(map[string]any)["acceptance_refs"] = []any{prefix + "0"}
			index["tasks"].([]any)[1].(map[string]any)["acceptance_refs"] = []any{prefix + "1"}
			index["official_entrypoints"] = []any{map[string]any{"id": "EP-001", "command": "specify import", "ready_signal": "import complete"}}
			index["system_review_scenarios"] = []any{map[string]any{"id": "SR-001", "entrypoint_id": "EP-001", "acceptance_refs": []any{prefix + "0"}}, map[string]any{"id": "SR-002", "entrypoint_id": "EP-001", "acceptance_refs": []any{prefix + "1"}}}
			index["review_obligations"] = []any{map[string]any{"id": "RO-001", "source_ref": prefix + "0", "scenario_ids": []any{"SR-001"}}, map[string]any{"id": "RO-002", "source_ref": prefix + "1", "scenario_ids": []any{"SR-002"}}}
			index["human_acceptance_scenarios"] = []any{map[string]any{"id": "HA-001", "actor": "user", "entrypoint_id": "EP-001", "acceptance_refs": []any{prefix + "0"}}, map[string]any{"id": "HA-002", "actor": "user", "entrypoint_id": "EP-001", "acceptance_refs": []any{prefix + "1"}}}
			index["human_acceptance_obligations"] = []any{map[string]any{"id": "HAO-001", "source_ref": prefix + "0", "scenario_ids": []any{"HA-001"}}, map[string]any{"id": "HAO-002", "source_ref": prefix + "1", "scenario_ids": []any{"HA-002"}}}
			if err := validateTaskControlAcceptance(feature, index); err != nil {
				t.Fatalf("accepted plan pointer aliases must normalize before source coverage: %v", err)
			}
			if refs := anyStringSlice(index["tasks"].([]any)[1].(map[string]any)["acceptance_refs"]); len(refs) != 1 || refs[0] != "spec-contract.json#/acceptance_criteria/1" {
				t.Fatalf("task aliases were not normalized: %v", refs)
			}
			index["tasks"].([]any)[1].(map[string]any)["acceptance_refs"] = []any{prefix + "9"}
			if err := validateTaskControlAcceptance(feature, index); err == nil {
				t.Fatal("out-of-range task acceptance alias passed")
			}
		})
	}
}

func TestImplementPacketPreservesOnlyAssignedSourceRequirements(t *testing.T) {
	root, feature, _, index := downstreamSourceFixture(t)
	template, err := os.ReadFile(filepath.Join("..", "..", "templates", "task-packet-template.json"))
	if err != nil {
		t.Fatal(err)
	}
	templatePath := filepath.Join(root, ".specify", "templates", "task-packet-template.json")
	if err := os.MkdirAll(filepath.Dir(templatePath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(templatePath, template, 0o644); err != nil {
		t.Fatal(err)
	}
	task := index["tasks"].([]any)[1].(map[string]any)
	packet, err := buildImplementTaskPacket(root, feature, "T002", index, 1, task)
	if err != nil {
		t.Fatal(err)
	}
	refs := anyStringSlice(packet["source_requirement_refs"])
	if len(refs) != 1 || refs[0] != "REQ-002" {
		t.Fatalf("unexpected packet source subset: %#v", packet)
	}
	if refs := anyStringSlice(packet["acceptance_refs"]); len(refs) != 1 || refs[0] != "spec-contract.json#/acceptance_criteria/1" {
		t.Fatalf("packet inherited unrelated acceptance refs: %v", refs)
	}
	delete(task, "acceptance_refs")
	packet, err = buildImplementTaskPacket(root, feature, "T002", index, 1, task)
	if err != nil {
		t.Fatal(err)
	}
	if len(anyStringSlice(packet["acceptance_refs"])) != 0 || len(anyStringSlice(packet["source_requirement_refs"])) != 0 {
		t.Fatal("missing task refs fell back to the entire index")
	}
}
