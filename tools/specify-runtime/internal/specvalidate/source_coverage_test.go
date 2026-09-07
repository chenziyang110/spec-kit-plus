package specvalidate

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func validAcceptanceSpec() map[string]any {
	return map[string]any{
		"scope":                 map[string]any{"in": []any{"Read the document body", "Preserve the final exception"}},
		"capability_operations": []any{},
		"acceptance_criteria":   []any{"The body is read completely", "The final exception changes the result"},
		"acceptance_coverage": []any{
			map[string]any{"requirement_ref": "spec-contract.json#/scope/in/0", "acceptance_ref": "spec-contract.json#/acceptance_criteria/0"},
			map[string]any{"requirement_ref": "spec-contract.json#/scope/in/1", "acceptance_ref": "spec-contract.json#/acceptance_criteria/1"},
		},
		"source_requirement_coverage": []any{
			map[string]any{"requirement_id": "REQ-001", "disposition": "in_scope", "requirement_refs": []any{"spec-contract.json#/scope/in/0"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/0"}},
			map[string]any{"requirement_id": "REQ-002", "disposition": "in_scope", "requirement_refs": []any{"spec-contract.json#/scope/in/1"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/1"}},
		},
	}
}

func TestAcceptanceCoverageRejectsMissingAndAmbiguousClosure(t *testing.T) {
	tests := map[string]func(map[string]any){
		"missing coverage":    func(spec map[string]any) { delete(spec, "acceptance_coverage") },
		"omitted requirement": func(spec map[string]any) { spec["acceptance_coverage"] = spec["acceptance_coverage"].([]any)[:1] },
		"shared criterion": func(spec map[string]any) {
			spec["acceptance_coverage"].([]any)[1].(map[string]any)["acceptance_ref"] = "spec-contract.json#/acceptance_criteria/0"
		},
		"unknown requirement": func(spec map[string]any) {
			spec["acceptance_coverage"].([]any)[1].(map[string]any)["requirement_ref"] = "spec-contract.json#/scope/in/9"
		},
		"empty actual requirement": func(spec map[string]any) { spec["scope"].(map[string]any)["in"].([]any)[1] = "" },
		"empty actual criterion":   func(spec map[string]any) { spec["acceptance_criteria"].([]any)[1] = "" },
		"orphan criterion": func(spec map[string]any) {
			spec["acceptance_criteria"] = append(spec["acceptance_criteria"].([]any), "Another independent check")
		},
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			spec := validAcceptanceSpec()
			if err := ValidateAcceptanceCoverage(spec); err != nil {
				t.Fatal(err)
			}
			mutate(spec)
			if err := ValidateAcceptanceCoverage(spec); err == nil {
				t.Fatal("incomplete acceptance closure passed")
			}
		})
	}
}

func TestAcceptanceCoverageSupportsEscapedOperationPointersAndMultipleCriteria(t *testing.T) {
	spec := validAcceptanceSpec()
	spec["capability_operations"] = map[string]any{"read/all~units": "Read every unit"}
	spec["acceptance_criteria"] = append(spec["acceptance_criteria"].([]any), "Read trailing unit", "Read leading unit")
	spec["acceptance_coverage"] = append(spec["acceptance_coverage"].([]any),
		map[string]any{"requirement_ref": "spec-contract.json#/capability_operations/read~1all~0units", "acceptance_ref": "spec-contract.json#/acceptance_criteria/2"},
		map[string]any{"requirement_ref": "spec-contract.json#/capability_operations/read~1all~0units", "acceptance_ref": "spec-contract.json#/acceptance_criteria/3"},
	)
	if err := ValidateAcceptanceCoverage(spec); err != nil {
		t.Fatal(err)
	}
}

func sourceCoverageFixture(t *testing.T) (string, map[string]any, map[string]any) {
	t.Helper()
	root := t.TempDir()
	feature := filepath.Join(root, ".specify", "features", "source-coverage")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	// One long CJK line: the final condition cannot be covered by reading only
	// the first line or by using byte offsets as rune offsets.
	body := strings.Repeat("正文要求🐱", 5500)
	tail := "但最后一项必须保留，失败时不能静默省略。"
	content := body + tail
	snapshotRef := ".specify/discussions/source/materials/MAT-001/content.txt"
	snapshot := filepath.Join(root, filepath.FromSlash(snapshotRef))
	if err := os.MkdirAll(filepath.Dir(snapshot), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(snapshot, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	firstID := "U0001-" + coverageDigest([]byte(body))[:12]
	lastID := "U0002-" + coverageDigest([]byte(tail))[:12]
	material := map[string]any{
		"id": "MAT-001", "inspection_status": "inspected",
		"reading": map[string]any{
			"version": 1, "content_sha256": coverageDigest([]byte(content)), "snapshot_ref": snapshotRef, "source_path": filepath.Join(root, "already-removed-extraction.txt"),
			"units": []any{
				map[string]any{"id": firstID, "start_rune": 0, "end_rune": len([]rune(body)), "sha256": coverageDigest([]byte(body))},
				map[string]any{"id": lastID, "start_rune": len([]rune(body)), "end_rune": len([]rune(content)), "sha256": coverageDigest([]byte(tail))},
			},
			"delivered_unit_ids": []any{firstID, lastID},
		},
		"unit_dispositions": []any{
			map[string]any{"unit_id": firstID, "requirement_ids": []any{"REQ-001"}, "disposition": "requirements"},
			map[string]any{"unit_id": lastID, "requirement_ids": []any{"REQ-002"}, "disposition": "requirements"},
		},
	}
	handoff := map[string]any{
		"version": 5, "handoff_kind": "discussion_requirement_contract", "entry_source": "sp-discussion",
		"status": "handoff-ready", "coverage_status": "complete", "planning_gate_status": "ready",
		"recommended_consumer": "sp-specify", "consumer_eligibility": map[string]any{"sp-specify": map[string]any{"status": "ready"}},
		"hard_unknown_count": 0, "open_conflict_count": 0,
		"source_contract":  ".specify/discussions/source/handoff-to-specify.json",
		"source_materials": []any{material},
		"agent_requirement_contract": map[string]any{"source_requirements": []any{
			map[string]any{"id": "REQ-001", "statement": "Read the complete document body", "disposition": "in_scope", "source_refs": []any{map[string]any{"material_id": "MAT-001", "unit_id": firstID, "locator": "body"}}},
			map[string]any{"id": "REQ-002", "statement": tail, "disposition": "in_scope", "source_refs": []any{map[string]any{"material_id": "MAT-001", "unit_id": lastID, "locator": "final exception"}}},
		}},
	}
	spec := validAcceptanceSpec()
	spec["source_contract"] = handoff["source_contract"]
	signSourceCoverageFixture(t, spec, handoff)
	writeSourceCoverageFixture(t, feature, spec, handoff)
	return feature, spec, handoff
}

func signSourceCoverageFixture(t *testing.T, spec, handoff map[string]any) {
	t.Helper()
	snapshotDigest, err := DiscussionSnapshotDigest(DiscussionSemanticSnapshot(sourceFixturePacket(handoff)))
	if err != nil {
		t.Fatal(err)
	}
	handoff["discussion_snapshot_digest"] = snapshotDigest
	digest, err := DiscussionReviewDigest(handoff)
	if err != nil {
		t.Fatal(err)
	}
	handoff["review_digest"] = digest
	handoff["quality_gate"] = map[string]any{"status": "user_confirmed", "confirmed_digest": digest}
	spec["source_revision"] = digest
}

func writeSourceCoverageFixture(t *testing.T, feature string, spec, handoff map[string]any) {
	t.Helper()
	writeCoverageJSON(t, filepath.Join(feature, "spec-contract.json"), spec)
	root := filepath.Dir(filepath.Dir(filepath.Dir(feature)))
	sourcePath := filepath.Join(root, filepath.FromSlash(valueString(handoff["source_contract"])))
	writeCoverageJSON(t, sourcePath, handoff)
	writeCoverageJSON(t, filepath.Join(filepath.Dir(sourcePath), "discussion-state.json"), map[string]any{
		"turn_packet": sourceFixturePacket(handoff), "latest_checkpoint": map[string]any{"snapshot_sha256": handoff["discussion_snapshot_digest"]},
	})
}

func sourceFixturePacket(handoff map[string]any) map[string]any {
	return map[string]any{"discussion_slug": "source", "requirements_snapshot": handoff["agent_requirement_contract"], "source_materials": handoff["source_materials"]}
}

func writeCoverageJSON(t *testing.T, path string, value any) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestSourceRequirementCoveragePreservesLongCJKLineTail(t *testing.T) {
	feature, spec, handoff := sourceCoverageFixture(t)
	if err := ValidateSourceRequirementCoverage(feature); err != nil {
		t.Fatal(err)
	}
	spec["source_requirement_coverage"] = spec["source_requirement_coverage"].([]any)[:1]
	writeSourceCoverageFixture(t, feature, spec, handoff)
	if err := ValidateSourceRequirementCoverage(feature); err == nil {
		t.Fatal("omitted trailing source requirement passed")
	}
}

func TestSourceRequirementCoverageRejectsDetachedOrReinterpretedSources(t *testing.T) {
	tests := map[string]func(map[string]any, map[string]any){
		"unread final unit": func(spec, source map[string]any) {
			source["source_materials"].([]any)[0].(map[string]any)["reading"].(map[string]any)["delivered_unit_ids"] = []any{}
		},
		"missing reading contract": func(spec, source map[string]any) {
			delete(source["source_materials"].([]any)[0].(map[string]any), "reading")
		},
		"missing source inventory": func(spec, source map[string]any) {
			delete(source["agent_requirement_contract"].(map[string]any), "source_requirements")
		},
		"unmapped source unit": func(spec, source map[string]any) {
			source["source_materials"].([]any)[0].(map[string]any)["unit_dispositions"].([]any)[1].(map[string]any)["requirement_ids"] = []any{}
		},
		"invented reference": func(spec, source map[string]any) {
			spec["source_requirement_coverage"].([]any)[1].(map[string]any)["acceptance_refs"] = []any{"spec-contract.json#/acceptance_criteria/9"}
		},
		"wrong requirement pair": func(spec, source map[string]any) {
			spec["source_requirement_coverage"].([]any)[1].(map[string]any)["requirement_refs"] = []any{"spec-contract.json#/scope/in/0"}
		},
		"one generic criterion for two sources": func(spec, source map[string]any) {
			row := spec["source_requirement_coverage"].([]any)[1].(map[string]any)
			row["requirement_refs"] = []any{"spec-contract.json#/scope/in/0"}
			row["acceptance_refs"] = []any{"spec-contract.json#/acceptance_criteria/0"}
		},
		"invented downstream deferral": func(spec, source map[string]any) {
			spec["source_requirement_coverage"].([]any)[1].(map[string]any)["disposition"] = "deferred"
		},
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			_, spec, handoff := sourceCoverageFixture(t)
			mutate(spec, handoff)
			signSourceCoverageFixture(t, spec, handoff)
			if err := ValidateSourceRequirementCoverageAgainstHandoff(spec, handoff); err == nil {
				t.Fatal("invalid source mapping passed")
			}
		})
	}
}

func TestSourceRequirementCoverageRechecksHandoffAndSnapshotBytes(t *testing.T) {
	for _, target := range []string{"handoff", "snapshot"} {
		t.Run(target, func(t *testing.T) {
			feature, spec, handoff := sourceCoverageFixture(t)
			if target == "handoff" {
				handoff["agent_requirement_contract"].(map[string]any)["source_requirements"].([]any)[1].(map[string]any)["statement"] = "Silently changed"
				writeSourceCoverageFixture(t, feature, spec, handoff)
			} else {
				root := filepath.Dir(filepath.Dir(filepath.Dir(feature)))
				reading := handoff["source_materials"].([]any)[0].(map[string]any)["reading"].(map[string]any)
				if err := os.WriteFile(filepath.Join(root, filepath.FromSlash(valueString(reading["snapshot_ref"]))), []byte("only summary"), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			if err := ValidateSourceRequirementCoverage(feature); err == nil {
				t.Fatal("changed source bytes passed")
			}
		})
	}
}

func TestSourceRequirementCoverageCannotDetachBoundDiscussion(t *testing.T) {
	feature, spec, handoff := sourceCoverageFixture(t)
	writeCoverageJSON(t, filepath.Join(feature, "brainstorming", "handoff-to-specify.json"), map[string]any{
		"discussion_slug": "source", "source_contract": handoff["source_contract"], "review_digest": handoff["review_digest"],
	})
	spec["source_contract"], spec["source_revision"], spec["source_requirement_coverage"] = nil, nil, []any{}
	writeSourceCoverageFixture(t, feature, spec, handoff)
	if err := ValidateSourceRequirementCoverage(feature); err == nil {
		t.Fatal("clearing source fields detached the bound Discussion")
	}
}

func TestSourceRequirementCoverageAllowsUnboundPendingBootstrap(t *testing.T) {
	feature, _, _ := sourceCoverageFixture(t)
	writeCoverageJSON(t, filepath.Join(feature, "brainstorming", "handoff-to-specify.json"), map[string]any{
		"status": "pending", "discussion_slug": nil, "source_contract": nil, "review_digest": nil,
	})
	if err := ValidateSourceRequirementCoverage(feature); err != nil {
		t.Fatal(err)
	}
}

func TestSourceRequirementCoverageRejectsUnreadyOrForeignConsumer(t *testing.T) {
	for _, field := range []string{"status", "planning_gate_status", "recommended_consumer", "hard_unknown_count"} {
		t.Run(field, func(t *testing.T) {
			_, spec, handoff := sourceCoverageFixture(t)
			switch field {
			case "hard_unknown_count":
				handoff[field] = 1
			case "recommended_consumer":
				handoff[field] = "sp-quick"
			default:
				handoff[field] = "draft"
			}
			signSourceCoverageFixture(t, spec, handoff)
			if err := ValidateSourceRequirementCoverageAgainstHandoff(spec, handoff); err == nil {
				t.Fatal("confirmed bytes alone authorized an unready or foreign handoff")
			}
		})
	}
}

func TestSourceRequirementCoverageRejectsNewUncheckedStateMaterials(t *testing.T) {
	feature, _, handoff := sourceCoverageFixture(t)
	root := filepath.Dir(filepath.Dir(filepath.Dir(feature)))
	statePath := filepath.Join(root, ".specify", "discussions", "source", "discussion-state.json")
	state, err := readCoverageObject(statePath)
	if err != nil {
		t.Fatal(err)
	}
	packet := state["turn_packet"].(map[string]any)
	packet["source_materials"] = append(packet["source_materials"].([]any), map[string]any{"id": "MAT-002", "inspection_status": "pending"})
	writeCoverageJSON(t, statePath, state)
	if err := ValidateSourceRequirementCoverage(feature); err == nil {
		t.Fatal("old ready handoff hid a new unread material")
	}
	state["turn_packet"] = sourceFixturePacket(handoff)
	state["status"] = "consumed"
	writeCoverageJSON(t, statePath, state)
	if err := ValidateSourceRequirementCoverage(feature); err != nil {
		t.Fatalf("unchanged consumed source must remain usable: %v", err)
	}
}

func TestSourceRequirementCoverageSurvivesExactDiscussionArchive(t *testing.T) {
	feature, _, handoff := sourceCoverageFixture(t)
	root := filepath.Dir(filepath.Dir(filepath.Dir(feature)))
	writeCoverageJSON(t, filepath.Join(feature, "brainstorming", "handoff-to-specify.json"), map[string]any{
		"discussion_slug": "source", "source_contract": handoff["source_contract"], "review_digest": handoff["review_digest"],
	})
	workspace := filepath.Join(root, ".specify", "discussions", "source")
	archive := filepath.Join(root, ".specify", "discussions", "archive", "source")
	if err := os.MkdirAll(filepath.Dir(archive), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(workspace, archive); err != nil {
		t.Fatal(err)
	}
	if err := ValidateSourceRequirementCoverage(feature); err != nil {
		t.Fatalf("exact archived reviewed source should remain consumable: %v", err)
	}
	if err := os.MkdirAll(workspace, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := ValidateSourceRequirementCoverage(feature); err == nil {
		t.Fatal("simultaneous active/archive workspaces must not choose silently")
	}
}

func TestTaskSourceCoverageRequiresActualAssignmentsAndDerivesPacketSubset(t *testing.T) {
	spec := validAcceptanceSpec()
	index := map[string]any{
		"source_requirement_coverage": spec["source_requirement_coverage"],
		"acceptance_refs":             []any{"spec-contract.json#/acceptance_criteria/0", "spec-contract.json#/acceptance_criteria/1"},
		"tasks": []any{
			map[string]any{"id": "T001", "acceptance": []any{"Complete body read"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/0"}},
			map[string]any{"id": "T002", "acceptance": []any{"Retain tail exception"}, "acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/1"}},
		},
	}
	if err := ValidateTaskSourceRequirementCoverage(index); err != nil {
		t.Fatal(err)
	}
	task := index["tasks"].([]any)[1].(map[string]any)
	refs, err := SourceRequirementRefsForTask(index, task)
	if err != nil || len(refs) != 1 || refs[0] != "REQ-002" {
		t.Fatalf("wrong packet subset: %v %v", refs, err)
	}
	task["acceptance_refs"] = []any{}
	if err := ValidateTaskSourceRequirementCoverage(index); err == nil {
		t.Fatal("top-level acceptance refs substituted for missing task assignment")
	}
	task["acceptance_refs"] = []any{"spec-contract.json#/acceptance_criteria/1"}
	task["status"] = "deferred"
	if err := ValidateTaskSourceRequirementCoverage(index); err == nil {
		t.Fatal("a deferred task silently closed an in_scope requirement")
	}
}

func TestSourceCoverageInheritanceRejectsOmittedAndReorderedRows(t *testing.T) {
	spec := validAcceptanceSpec()
	rows := spec["source_requirement_coverage"].([]any)
	for _, actual := range []any{[]any{}, []any{rows[0]}, []any{rows[1], rows[0]}} {
		if err := ValidateSourceCoverageInheritance(spec, map[string]any{"source_requirement_coverage": actual}); err == nil {
			t.Fatal("changed inherited inventory passed")
		}
	}
	if err := ValidateSourceCoverageInheritance(spec, spec); err != nil {
		t.Fatal(err)
	}
}
