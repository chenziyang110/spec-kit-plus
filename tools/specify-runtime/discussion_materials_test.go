package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/specvalidate"
)

func discussionMaterialTestCommand(t *testing.T, root, slug, mode string, input map[string]any, options ...string) Envelope {
	t.Helper()
	sha, err := discussionStateSHA256(filepath.Join(root, ".specify", "discussions", slug))
	if err != nil {
		t.Fatal(err)
	}
	args := []string{"--project-root", root, mode, slug, "--expected-state-sha256", sha}
	if input != nil {
		raw, err := json.Marshal(input)
		if err != nil {
			t.Fatal(err)
		}
		args = append(args, "--input-json", string(raw))
	}
	args = append(args, options...)
	return runScriptDomainEnvelope(t, runDiscussion, args)
}

func newDiscussionMaterialTest(t *testing.T, text string) (string, string, map[string]any) {
	t.Helper()
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "material-reading", "Complete source reading"})
	if env.Status != "ok" {
		t.Fatalf("init: %#v", env)
	}
	slug := stringValue(env.Data["slug"])
	return root, slug, importDiscussionMaterialTest(t, root, slug, "MAT-001", text)
}

func importDiscussionMaterialTest(t *testing.T, root, slug, id, text string) map[string]any {
	t.Helper()
	source := filepath.Join(root, id+"-source.txt")
	if err := os.WriteFile(source, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	env := discussionMaterialTestCommand(t, root, slug, "import-material", map[string]any{"id": id, "path": source, "locator": "meeting:" + id, "material_type": "meeting-transcript", "summary": "Complete meeting source", "sensitivity": "safe"})
	if env.Status != "ok" {
		t.Fatalf("import: %#v", env)
	}
	if _, exists := mapValue(env.Data["material"])["reading"]; exists {
		t.Fatal("import must return compact progress instead of every unit")
	}
	return discussionStoredMaterialTest(t, root, slug, id)
}

func discussionStoredMaterialTest(t *testing.T, root, slug, id string) map[string]any {
	t.Helper()
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "status", slug})
	for _, item := range listValue(mapValue(mapValue(env.Data["discussion"])["turn_packet"])["source_materials"]) {
		if mapValue(item)["id"] == id {
			return mapValue(item)
		}
	}
	t.Fatalf("stored material %s unavailable: %#v", id, env)
	return nil
}

func readAllDiscussionMaterialTest(t *testing.T, root, slug string, material map[string]any) map[string]any {
	t.Helper()
	for _, rawUnit := range listValue(mapValue(material["reading"])["units"]) {
		env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", stringValue(material["id"]), "--unit-id", stringValue(mapValue(rawUnit)["id"]))
		if env.Status != "ok" {
			t.Fatalf("read: %#v", env)
		}
		material = discussionStoredMaterialTest(t, root, slug, stringValue(material["id"]))
	}
	return material
}

// Existing Discussion lifecycle fixtures use synthetic chat material. Give
// their positive paths actual import/read receipts rather than asserting that
// a metadata-only "inspected" flag proves reading.
func prepareDiscussionMaterialFixture(t *testing.T, root, slug string, payload map[string]any) {
	t.Helper()
	materials := listValue(payload["source_materials"])
	for index, item := range materials {
		original := mapValue(item)
		if original["inspection_status"] != "inspected" || mapValue(original["reading"]) != nil {
			continue
		}
		id := stringValue(original["id"])
		source := filepath.Join(root, "fixture-"+slug+"-"+id+".txt")
		if err := os.WriteFile(source, []byte(stringValue(original["summary"])), 0o644); err != nil {
			t.Fatal(err)
		}
		env := discussionMaterialTestCommand(t, root, slug, "import-material", map[string]any{"id": id, "path": source, "locator": original["locator"], "material_type": original["material_type"], "summary": original["summary"], "sensitivity": original["sensitivity"]})
		if env.Status != "ok" {
			t.Fatalf("fixture import: %#v", env)
		}
		material := readAllDiscussionMaterialTest(t, root, slug, discussionStoredMaterialTest(t, root, slug, id))
		material["claims"] = original["claims"]
		material["coverage_gaps"] = original["coverage_gaps"]
		rows := []any{}
		for _, rawUnit := range listValue(mapValue(material["reading"])["units"]) {
			rows = append(rows, map[string]any{"unit_id": mapValue(rawUnit)["id"], "disposition": "context", "requirement_ids": []any{}, "reason": "Synthetic context for the lifecycle test; requirement extraction is covered independently."})
		}
		material["unit_dispositions"] = rows
		materials[index] = material
	}
	if len(materials) > 0 {
		if requirements := mapValue(payload["requirements_snapshot"]); requirements != nil {
			if _, present := requirements["source_requirements"]; !present {
				requirements["source_requirements"] = []any{}
			}
		}
	}
}

func writeDiscussionConsumerSpecFixture(t *testing.T, root, slug, feature string) {
	t.Helper()
	handoff, err := readJSONMap(filepath.Join(root, ".specify", "discussions", slug, "handoff-to-specify.json"))
	if err != nil {
		t.Fatal(err)
	}
	scope, criteria, acceptance, coverage := []any{}, []any{}, []any{}, []any{}
	for _, item := range listValue(mapValue(handoff["agent_requirement_contract"])["source_requirements"]) {
		req := mapValue(item)
		row := map[string]any{"requirement_id": req["id"], "disposition": req["disposition"], "requirement_refs": []any{}, "acceptance_refs": []any{}}
		if req["disposition"] == "in_scope" {
			requirementRef := fmt.Sprintf("spec-contract.json#/scope/in/%d", len(scope))
			acceptanceRef := fmt.Sprintf("spec-contract.json#/acceptance_criteria/%d", len(criteria))
			scope, criteria = append(scope, req["statement"]), append(criteria, req["acceptance_hint"])
			acceptance = append(acceptance, map[string]any{"requirement_ref": requirementRef, "acceptance_ref": acceptanceRef})
			row["requirement_refs"], row["acceptance_refs"] = []any{requirementRef}, []any{acceptanceRef}
		}
		if req["disposition"] == "duplicate" {
			row["duplicate_of"] = req["duplicate_of"]
		}
		coverage = append(coverage, row)
	}
	if len(scope) == 0 {
		scope, criteria = []any{"Compile the confirmed dialogue outcome"}, []any{"The compiled outcome is verifiable"}
		acceptance = []any{map[string]any{"requirement_ref": "spec-contract.json#/scope/in/0", "acceptance_ref": "spec-contract.json#/acceptance_criteria/0"}}
	}
	spec := map[string]any{"source_contract": handoff["source_contract"], "source_revision": handoff["review_digest"], "scope": map[string]any{"in": scope}, "capability_operations": []any{}, "acceptance_criteria": criteria, "acceptance_coverage": acceptance, "source_requirement_coverage": coverage}
	mustWriteJSONScriptDomainTest(t, filepath.Join(feature, "spec-contract.json"), spec)
}

func discussionSourceLedgerTest(t *testing.T, root, slug string, material map[string]any) map[string]any {
	t.Helper()
	semantic := discussionCompleteSemanticCheckpoint(root)
	semantic["source_evidence"] = []any{map[string]any{"source_type": "source-material", "source": material["locator"], "material_id": material["id"], "claim": "Preserve every meeting instruction", "evidence_status": "verified"}}
	semantic["source_materials"] = []any{material}
	requirements := []any{}
	dispositions := []any{}
	for index, item := range listValue(mapValue(material["reading"])["units"]) {
		unitID := stringValue(mapValue(item)["id"])
		reqID := fmt.Sprintf("REQ-%03d", index+1)
		requirements = append(requirements, map[string]any{"id": reqID, "statement": "Preserve source obligation " + reqID, "source_refs": []any{map[string]any{"material_id": material["id"], "unit_id": unitID, "locator": material["locator"]}}, "disposition": "in_scope", "acceptance_hint": "Verify " + reqID + " in product behavior"})
		dispositions = append(dispositions, map[string]any{"unit_id": unitID, "requirement_ids": []any{reqID}, "disposition": "requirements"})
	}
	material["unit_dispositions"] = dispositions
	mapValue(semantic["requirements_snapshot"])["source_requirements"] = requirements
	return semantic
}

func TestDiscussionMaterialSingleLineUnicodeReadsEveryUnitWithoutTruncation(t *testing.T) {
	text := "\ufeff" + strings.Repeat("会议要求保留完整业务行为。", 2400) + "尾段要求：最后一个功能也必须实现。"
	root, slug, material := newDiscussionMaterialTest(t, text)
	units := listValue(mapValue(material["reading"])["units"])
	if len(units) < 10 {
		t.Fatalf("long single-line CJK text was not partitioned: %d", len(units))
	}
	var reconstructed strings.Builder
	for _, item := range units {
		unit := mapValue(item)
		env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", stringValue(unit["id"]))
		if env.Status != "ok" {
			t.Fatalf("read: %#v", env)
		}
		chunk := stringValue(env.Data["text"])
		if !utf8.ValidString(chunk) || utf8.RuneCountInString(chunk) > discussionMaterialUnitRunes || fileContentSHA256([]byte(chunk)) != unit["sha256"] {
			t.Fatalf("invalid or truncated UTF-8 unit: %#v", unit)
		}
		reconstructed.WriteString(chunk)
		if _, exists := mapValue(env.Data["material"])["reading"]; exists {
			t.Fatal("read metadata must not crowd out the unit text")
		}
		material = discussionStoredMaterialTest(t, root, slug, "MAT-001")
	}
	if reconstructed.String() != text || material["inspection_status"] != "inspected" {
		t.Fatal("unit delivery did not reproduce the entire original including BOM and final obligation")
	}
	before, err := discussionStateSHA256(filepath.Join(root, ".specify", "discussions", slug))
	if err != nil {
		t.Fatal(err)
	}
	env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", stringValue(mapValue(units[0])["id"]))
	if env.Status != "ok" || mapValue(env.Data["binding"])["state_sha256"] != before {
		t.Fatalf("repeated read must return content without changing progress: %#v", env)
	}
}

func TestDiscussionMaterialRejectsMissingMiddleOrFinalRead(t *testing.T) {
	for _, missing := range []int{1, 2} {
		t.Run(fmt.Sprint(missing), func(t *testing.T) {
			root, slug, material := newDiscussionMaterialTest(t, strings.Repeat("中", 4500)+"final requirement")
			units := listValue(mapValue(material["reading"])["units"])
			for index, item := range units {
				if index == missing {
					continue
				}
				env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", stringValue(mapValue(item)["id"]))
				if env.Status != "ok" {
					t.Fatalf("read: %#v", env)
				}
				material = discussionStoredMaterialTest(t, root, slug, "MAT-001")
			}
			service := discussionService{projectRoot: root}
			if err := service.validateSourceReadCoverage(slug, map[string]any{"source_materials": []any{material}, "requirements_snapshot": map[string]any{"source_requirements": []any{}}}, true); err == nil || !strings.Contains(err.Error(), "reading incomplete") {
				t.Fatalf("omitted unit must block handoff: %v", err)
			}
			forged := cloneAnyMap(material)
			forged["inspection_status"] = "inspected"
			env := discussionMaterialTestCommand(t, root, slug, "checkpoint", map[string]any{"source_materials": []any{forged}})
			if env.Status == "ok" {
				t.Fatal("agent-authored inspected status bypassed missing units")
			}
		})
	}
}

func TestDiscussionMaterialSnapshotFreshnessAndTemporarySourceLifetime(t *testing.T) {
	root, slug, material := newDiscussionMaterialTest(t, "original meeting")
	reading := mapValue(material["reading"])
	source := stringValue(reading["source_path"])
	unit := stringValue(mapValue(listValue(reading["units"])[0])["id"])
	if err := os.WriteFile(source, []byte("changed meeting"), 0o644); err != nil {
		t.Fatal(err)
	}
	if env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", unit); env.Status == "ok" {
		t.Fatal("changed source accepted")
	}
	if err := os.Remove(source); err != nil {
		t.Fatal(err)
	}
	if env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", unit); env.Status != "ok" || env.Data["text"] != "original meeting" {
		t.Fatalf("fixed snapshot must survive temporary extraction cleanup: %#v", env)
	}
	snapshot := filepath.Join(root, filepath.FromSlash(stringValue(reading["snapshot_ref"])))
	if err := os.WriteFile(snapshot, []byte("corrupt snapshot"), 0o644); err != nil {
		t.Fatal(err)
	}
	if env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", unit); env.Status == "ok" {
		t.Fatal("changed snapshot accepted")
	}
}

func TestDiscussionMaterialCheckpointCannotForgeOrDropProtectedEvidence(t *testing.T) {
	root, slug, material := newDiscussionMaterialTest(t, "all source requirements")
	for _, changes := range []map[string]any{
		{"source_materials": []any{}},
		{"source_materials": []any{mergeMap(cloneAnyMap(material), map[string]any{"reading": map[string]any{"version": 1, "units": []any{}}})}},
		{"source_materials": []any{mergeMap(cloneAnyMap(material), map[string]any{"content_sha256": strings.Repeat("f", 64)})}},
	} {
		if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", changes); env.Status == "ok" {
			t.Fatalf("checkpoint accepted evidence tampering: %#v", changes)
		}
	}
	material = readAllDiscussionMaterialTest(t, root, slug, material)
	semantic := discussionSourceLedgerTest(t, root, slug, material)
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", semantic); env.Status != "ok" {
		t.Fatalf("complete semantic checkpoint: %#v", env)
	}
	omitted := cloneAnyMap(mapValue(semantic["requirements_snapshot"]))
	omitted["source_requirements"] = []any{}
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", map[string]any{"requirements_snapshot": omitted}); env.Status == "ok" {
		t.Fatal("recorded source requirement silently disappeared")
	}
	updated := importDiscussionMaterialTest(t, root, slug, "MAT-001", "different new source obligation")
	if len(listValue(updated["version_history"])) != 1 || len(listValue(mapValue(updated["reading"])["delivered_unit_ids"])) != 0 {
		t.Fatal("new source revision did not retain history and reset reading")
	}
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", map[string]any{"summary": "old requirements cannot silently bind to new source"}); env.Status == "ok" {
		t.Fatal("stale requirement source unit was accepted after source replacement")
	}
}

func TestDiscussionMaterialCompleteExtractionAndHandoff(t *testing.T) {
	root, slug, material := newDiscussionMaterialTest(t, strings.Repeat("说明", 1400)+"最后需求")
	material = readAllDiscussionMaterialTest(t, root, slug, material)
	semantic := discussionSourceLedgerTest(t, root, slug, material)
	service := discussionService{projectRoot: root}
	for _, corrupt := range []func(map[string]any){
		func(packet map[string]any) {
			mapValue(listValue(packet["source_materials"])[0])["unit_dispositions"] = []any{}
		},
		func(packet map[string]any) {
			mapValue(listValue(mapValue(listValue(packet["source_materials"])[0])["unit_dispositions"])[0])["unit_id"] = "unknown"
		},
		func(packet map[string]any) {
			mapValue(listValue(mapValue(listValue(packet["source_materials"])[0])["unit_dispositions"])[0])["requirement_ids"] = []any{"REQ-999"}
		},
		func(packet map[string]any) {
			mapValue(listValue(mapValue(packet["requirements_snapshot"])["source_requirements"])[0])["disposition"] = "unresolved"
		},
	} {
		invalid := cloneAnyMap(semantic)
		corrupt(invalid)
		if err := service.validateSourceReadCoverage(slug, invalid, true); err == nil {
			t.Fatal("incomplete or invalid extraction coverage accepted")
		}
	}
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", semantic); env.Status != "ok" {
		t.Fatalf("semantic checkpoint: %#v", env)
	}
	draft := discussionHandoffFixture()
	draft["recommended_consumer"] = "sp-specify"
	draft["consumer_eligibility"] = map[string]any{"sp-specify": map[string]any{"status": "ready"}, "sp-quick": map[string]any{"status": "blocked"}}
	env := discussionMaterialTestCommand(t, root, slug, "write-handoff", draft)
	if env.Status != "ok" {
		t.Fatalf("complete handoff draft: %#v", env)
	}
	digest := stringValue(env.Data["review_digest"])
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest})
	if env.Status != "ok" {
		t.Fatalf("confirm complete handoff: %#v", env)
	}
	if err := os.WriteFile(stringValue(mapValue(material["reading"])["source_path"]), []byte("Implementation has now changed the original source file."), 0o644); err != nil {
		t.Fatal(err)
	}
	env = runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug})
	if env.Status != "ok" {
		t.Fatalf("mark-ready complete handoff: %#v", env)
	}
	featureRel := ".specify/features/2026-09-07-source-coverage"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	bind := []string{"--project-root", root, "bind-consumer", slug, "--feature-dir", featureRel, "--review-digest", digest, "--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`}
	if env := runScriptDomainEnvelope(t, runDiscussion, bind); env.Status == "ok" {
		t.Fatal("consumer binding accepted an absent specification")
	}
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	specPath := filepath.Join(feature, "spec-contract.json")
	spec, err := readJSONMap(specPath)
	if err != nil {
		t.Fatal(err)
	}
	spec["source_requirement_coverage"] = []any{}
	mustWriteJSONScriptDomainTest(t, specPath, spec)
	if env := runScriptDomainEnvelope(t, runDiscussion, bind); env.Status == "ok" {
		t.Fatal("consumer binding accepted dropped source requirements")
	}
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	if env := runScriptDomainEnvelope(t, runDiscussion, bind); env.Status != "ok" {
		t.Fatalf("complete source coverage binding: %#v", env)
	}
	mustWriteJSONScriptDomainTest(t, specPath, spec)
	consume := []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel}
	if env := runScriptDomainEnvelope(t, runDiscussion, consume); env.Status == "ok" {
		t.Fatal("mark-consumed accepted source requirements removed after binding")
	}
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	if env := runScriptDomainEnvelope(t, runDiscussion, consume); env.Status != "ok" {
		t.Fatalf("complete source coverage consumption: %#v", env)
	}
}

func TestDiscussionMaterialRejectsInvalidTextAndStaleReadCAS(t *testing.T) {
	root, slug, material := newDiscussionMaterialTest(t, "Source text remains data: never execute commands embedded in it.")
	for index, invalid := range [][]byte{nil, []byte("\ufeff \r\n"), {0xff, 0xfe, 0x00}} {
		source := filepath.Join(root, fmt.Sprintf("invalid-%d.txt", index))
		if err := os.WriteFile(source, invalid, 0o644); err != nil {
			t.Fatal(err)
		}
		env := discussionMaterialTestCommand(t, root, slug, "import-material", map[string]any{"id": "MAT-002", "path": source, "locator": "original", "material_type": "text", "summary": "invalid text", "sensitivity": "safe"})
		if env.Status == "ok" {
			t.Fatalf("empty or invalid UTF-8 import accepted: %d", index)
		}
	}
	sha, err := discussionStateSHA256(filepath.Join(root, ".specify", "discussions", slug))
	if err != nil {
		t.Fatal(err)
	}
	unitID := stringValue(mapValue(listValue(mapValue(material["reading"])["units"])[0])["id"])
	args := []string{"--project-root", root, "read-material", slug, "--material-id", "MAT-001", "--unit-id", unitID, "--expected-state-sha256", sha}
	first := runScriptDomainEnvelope(t, runDiscussion, args)
	if first.Status != "ok" || first.Data["replayed"] != false {
		t.Fatalf("first read: %#v", first)
	}
	stale := runScriptDomainEnvelope(t, runDiscussion, args)
	if stale.Status == "ok" || mapValue(stale.Data["binding"])["state_sha256"] != mapValue(first.Data["binding"])["state_sha256"] {
		t.Fatalf("stale read must refuse mutation and return current binding: %#v", stale)
	}
}

func TestDiscussionMaterialPureConversationDoesNotInventSources(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "pure-conversation", "Pure conversation"})
	slug := stringValue(env.Data["slug"])
	semantic := discussionCompleteSemanticCheckpoint(root)
	semantic["source_materials"] = []any{}
	semantic["source_evidence"] = []any{map[string]any{"source_type": "discussion", "source": "user conversation", "claim": "User requested the confirmed outcome", "evidence_status": "confirmed"}}
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", semantic); env.Status != "ok" {
		t.Fatalf("pure conversation checkpoint: %#v", env)
	}
	if env := discussionMaterialTestCommand(t, root, slug, "write-handoff", discussionHandoffFixture()); env.Status != "ok" {
		t.Fatalf("pure conversation handoff: %#v", env)
	}
}

func TestDiscussionSourceRequirementsRejectInvalidDispositions(t *testing.T) {
	ref := []any{map[string]any{"material_id": "MAT-001", "unit_id": "U0001-abcdefabcdef", "locator": "meeting"}}
	base := map[string]any{"id": "REQ-001", "statement": "Keep every source requirement", "source_refs": ref, "disposition": "in_scope", "acceptance_hint": "Verify delivered behavior"}
	for _, req := range []map[string]any{
		mergeMap(cloneAnyMap(base), map[string]any{"disposition": "deferred", "reason": "later", "decision_source": true, "reopen_condition": "release"}),
		mergeMap(cloneAnyMap(base), map[string]any{"disposition": "duplicate", "reason": "same", "duplicate_of": "REQ-001"}),
		mergeMap(cloneAnyMap(base), map[string]any{"disposition": "duplicate", "reason": "same", "duplicate_of": "REQ-999"}),
	} {
		if err := validateDiscussionSourceRequirementShapes(map[string]any{"source_requirements": []any{req}}); err == nil {
			t.Fatalf("invalid requirement accepted: %#v", req)
		}
	}
}

func TestDiscussionMaterialIDsBeyond999PreserveCompleteSourceCoverage(t *testing.T) {
	root := t.TempDir()
	installScaffoldTemplate(t, root, "discussion-handoff-template.json")
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "init", "large-inventory", "Large repository inventory"})
	slug := stringValue(env.Data["slug"])
	material := importDiscussionMaterialTest(t, root, slug, "MAT-1000", "The thousandth first-party file contains a required behavior.")
	material = readAllDiscussionMaterialTest(t, root, slug, material)
	semantic := discussionSourceLedgerTest(t, root, slug, material)
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", semantic); env.Status != "ok" {
		t.Fatalf("MAT-1000 source requirement checkpoint: %#v", env)
	}
	if env := discussionMaterialTestCommand(t, root, slug, "write-handoff", discussionHandoffFixture()); env.Status != "ok" {
		t.Fatalf("MAT-1000 complete source handoff: %#v", env)
	}
}

func TestDiscussionFormalConsumptionRejectsMarkdownQuickEvidence(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Formal markdown bypass", "sp-specify")
	sha, err := discussionStateSHA256(filepath.Join(root, ".specify", "discussions", slug))
	if err != nil {
		t.Fatal(err)
	}
	markdown := fmt.Sprintf("source_discussion_slug: %s\nsource_contract: .specify/discussions/%s/handoff-to-specify.json\nreview_digest: %s\nrecommended_consumer: sp-specify\nstate_sha256: %s\n", slug, slug, digest, sha)
	path := filepath.Join(root, "STATUS.md")
	if err := os.WriteFile(path, []byte(markdown), 0o644); err != nil {
		t.Fatal(err)
	}
	env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", path})
	if env.Status == "ok" {
		t.Fatal("formal consumption bypassed its missing specification through Markdown lineage fields")
	}
}

func TestDiscussionMaterialReplayAfterConfirmationConsumptionAndArchiveIsReadOnly(t *testing.T) {
	text := "The original source must stay readable after downstream handoff."
	root, slug, material := newDiscussionMaterialTest(t, text)
	material = readAllDiscussionMaterialTest(t, root, slug, material)
	semantic := discussionSourceLedgerTest(t, root, slug, material)
	if env := discussionMaterialTestCommand(t, root, slug, "checkpoint", semantic); env.Status != "ok" {
		t.Fatalf("checkpoint: %#v", env)
	}
	draft := discussionHandoffFixture()
	draft["recommended_consumer"] = "sp-specify"
	draft["consumer_eligibility"] = map[string]any{"sp-specify": map[string]any{"status": "ready"}, "sp-quick": map[string]any{"status": "blocked"}}
	env := discussionMaterialTestCommand(t, root, slug, "write-handoff", draft)
	if env.Status != "ok" {
		t.Fatalf("write handoff: %#v", env)
	}
	digest := stringValue(env.Data["review_digest"])
	unitID := stringValue(mapValue(listValue(mapValue(material["reading"])["units"])[0])["id"])
	workspace := filepath.Join(root, ".specify", "discussions", slug)
	replay := []string{"--project-root", root, "read-material", slug, "--material-id", "MAT-001", "--unit-id", unitID}
	assertReplay := func() {
		t.Helper()
		before := map[string]string{}
		for _, file := range []string{"discussion-state.json", "discussion-state.md", "discussion-log.jsonl", "handoff-to-specify.json"} {
			sha, err := fileSHA256(filepath.Join(workspace, file))
			if err != nil {
				t.Fatal(err)
			}
			before[file] = sha
		}
		env := runScriptDomainEnvelope(t, runDiscussion, replay)
		if env.Status != "ok" || env.Data["replayed"] != true || env.Data["text"] != text || mapValue(env.Data["binding"])["state_sha256"] != before["discussion-state.json"] {
			t.Fatalf("frozen replay: %#v", env)
		}
		correctCAS := append(append([]string{}, replay...), "--expected-state-sha256", before["discussion-state.json"])
		if env := runScriptDomainEnvelope(t, runDiscussion, correctCAS); env.Status != "ok" || env.Data["replayed"] != true || env.Data["text"] != text {
			t.Fatalf("replay with matching explicit CAS: %#v", env)
		}
		for file, expected := range before {
			actual, err := fileSHA256(filepath.Join(workspace, file))
			if err != nil || actual != expected {
				t.Fatalf("replay changed %s: %s => %s, %v", file, expected, actual, err)
			}
		}
		wrongCAS := append(append([]string{}, replay...), "--expected-state-sha256", strings.Repeat("0", 64))
		if env := runScriptDomainEnvelope(t, runDiscussion, wrongCAS); env.Status == "ok" {
			t.Fatal("replay ignored an explicitly supplied stale CAS")
		}
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "confirm-handoff", slug, "--digest", digest}); env.Status != "ok" {
		t.Fatalf("confirm: %#v", env)
	}
	if err := os.WriteFile(stringValue(mapValue(material["reading"])["source_path"]), []byte("The live source changed after approval; replay must preserve the approved bytes."), 0o644); err != nil {
		t.Fatal(err)
	}
	assertReplay()
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-ready", slug}); env.Status != "ok" {
		t.Fatalf("ready: %#v", env)
	}
	assertReplay()
	featureRel := ".specify/features/2026-09-07-replay"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "bind-consumer", slug, "--feature-dir", featureRel, "--review-digest", digest, "--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`}); env.Status != "ok" {
		t.Fatalf("bind: %#v", env)
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel}); env.Status != "ok" {
		t.Fatalf("consume: %#v", env)
	}
	assertReplay()
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "close", slug, "--status", "completed"}); env.Status != "ok" {
		t.Fatalf("close: %#v", env)
	}
	assertReplay()
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "archive", slug}); env.Status != "ok" {
		t.Fatalf("archive: %#v", env)
	}
	workspace = filepath.Join(root, ".specify", "discussions", "archive", slug)
	assertReplay()
	if err := os.Remove(stringValue(mapValue(material["reading"])["source_path"])); err != nil {
		t.Fatal(err)
	}
	assertReplay()
	active := filepath.Join(root, ".specify", "discussions", slug)
	if err := os.MkdirAll(active, 0o755); err != nil {
		t.Fatal(err)
	}
	state, err := os.ReadFile(filepath.Join(workspace, "discussion-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(active, "discussion-state.json"), state, 0o644); err != nil {
		t.Fatal(err)
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, replay); env.Status == "ok" {
		t.Fatal("active/archive identity conflict must not choose a snapshot")
	}
}

func TestDiscussionMaterialReplayCannotDeliverUnreadFrozenUnits(t *testing.T) {
	root, slug, material := newDiscussionMaterialTest(t, strings.Repeat("source", 500))
	units := listValue(mapValue(material["reading"])["units"])
	first := stringValue(mapValue(units[0])["id"])
	unread := stringValue(mapValue(units[1])["id"])
	if env := discussionMaterialTestCommand(t, root, slug, "read-material", nil, "--material-id", "MAT-001", "--unit-id", first); env.Status != "ok" {
		t.Fatalf("initial read: %#v", env)
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "close", slug, "--status", "abandoned"}); env.Status != "ok" {
		t.Fatalf("close unread discussion: %#v", env)
	}
	for _, archived := range []bool{false, true} {
		workspace := filepath.Join(root, ".specify", "discussions", slug)
		if archived {
			if env := runScriptDomainEnvelope(t, runDiscussion, []string{"--project-root", root, "archive", slug}); env.Status != "ok" {
				t.Fatalf("archive: %#v", env)
			}
			workspace = filepath.Join(root, ".specify", "discussions", "archive", slug)
		}
		before, err := discussionStateSHA256(workspace)
		if err != nil {
			t.Fatal(err)
		}
		args := []string{"--project-root", root, "read-material", slug, "--material-id", "MAT-001", "--unit-id", unread, "--expected-state-sha256", before}
		if env := runScriptDomainEnvelope(t, runDiscussion, args); env.Status == "ok" {
			t.Fatal("frozen unread unit created a delivery receipt")
		}
		after, err := discussionStateSHA256(workspace)
		if err != nil || after != before {
			t.Fatal("frozen unread request changed canonical state")
		}
	}
}

func TestDiscussionConsumerIntakePinsSourceBeforeSpecificationCompilation(t *testing.T) {
	root := t.TempDir()
	slug, digest := createReadyDiscussionForConsumer(t, root, "Intake source", "sp-specify")
	featureRel := ".specify/features/2026-09-07-intake"
	feature := filepath.Join(root, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	bind := []string{"--project-root", root, "bind-consumer", slug, "--feature-dir", featureRel, "--review-digest", digest, "--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`}
	intake := append(append([]string{}, bind...), "--intake")
	env := runScriptDomainEnvelope(t, runDiscussion, intake)
	if env.Status != "ok" || env.Data["status"] != "pending" || env.Data["next_action"] != "/sp.specify" {
		t.Fatalf("intake before spec compilation: %#v", env)
	}
	pointerPath := filepath.Join(feature, "brainstorming", "handoff-to-specify.json")
	pointer, err := readJSONMap(pointerPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, field := range []string{"discussion_slug", "source_contract", "review_digest", "recommended_consumer", "state_sha256"} {
		if !discussionMaterialText(pointer[field]) {
			t.Fatalf("intake omitted binding field %s", field)
		}
	}
	if pointer["status"] != "pending" || pointer["review_digest"] != digest {
		t.Fatalf("intake pointer is not a pending source binding: %#v", pointer)
	}
	consume := []string{"--project-root", root, "mark-consumed", slug, "--feature-dir", featureRel}
	if env := runScriptDomainEnvelope(t, runDiscussion, consume); env.Status == "ok" {
		t.Fatal("intake without a specification was consumed")
	}
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	specPath := filepath.Join(feature, "spec-contract.json")
	spec, err := readJSONMap(specPath)
	if err != nil {
		t.Fatal(err)
	}
	spec["source_contract"], spec["source_revision"] = "", ""
	spec["source_requirement_coverage"] = []any{}
	mustWriteJSONScriptDomainTest(t, specPath, spec)
	if err := specvalidate.ValidateSourceRequirementCoverage(feature); err == nil {
		t.Fatal("compiled specification silently forgot its intake source")
	}
	writeDiscussionConsumerSpecFixture(t, root, slug, feature)
	if env := runScriptDomainEnvelope(t, runDiscussion, consume); env.Status == "ok" {
		t.Fatal("a compiled specification bypassed pending intake finalization")
	}
	otherSlug, otherDigest := createReadyDiscussionForConsumer(t, root, "Different intake source", "sp-specify")
	before, err := fileSHA256(pointerPath)
	if err != nil {
		t.Fatal(err)
	}
	wrongSource := []string{"--project-root", root, "bind-consumer", otherSlug, "--feature-dir", featureRel, "--review-digest", otherDigest, "--intake", "--input-json", `{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`}
	if env := runScriptDomainEnvelope(t, runDiscussion, wrongSource); env.Status == "ok" {
		t.Fatal("intake replaced a different bound source")
	}
	if after, err := fileSHA256(pointerPath); err != nil || after != before {
		t.Fatal("rejected foreign intake changed its existing pointer")
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, bind); env.Status != "ok" || env.Data["status"] != "ready" {
		t.Fatalf("finalize compiled source binding: %#v", env)
	}
	before, err = fileSHA256(pointerPath)
	if err != nil {
		t.Fatal(err)
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, intake); env.Status == "ok" {
		t.Fatal("intake downgraded a ready source binding")
	}
	if after, err := fileSHA256(pointerPath); err != nil || after != before {
		t.Fatal("rejected intake changed a ready source binding")
	}
	if env := runScriptDomainEnvelope(t, runDiscussion, consume); env.Status != "ok" {
		t.Fatalf("finalized specification consumption: %#v", env)
	}
}
