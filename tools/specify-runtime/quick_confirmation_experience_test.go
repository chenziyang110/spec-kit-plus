package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func quickExperienceInput() map[string]any {
	return map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal": "Deliver search", "user_visible_result": "Search finds matching records",
			"current_state_evidence": []any{"The current search route returns no matches (src/search.go:42)."},
			"scope":                  map[string]any{"include": []any{"search"}, "exclude": []any{"publishing"}},
			"items": []any{map[string]any{
				"id": "Q1", "deliverable": "Search", "depends_on": []any{}, "acceptance": "Queries return matching records",
			}},
			"recommended_approach":   "Reuse the existing search service.",
			"assumptions_and_risks":  []any{"Keep the current query format compatible."},
			"completion_evidence":    []any{"Search and adjacent route checks pass."},
			"reconfirmation_trigger": "Change to scope or compatibility",
		},
	}
}

func quickExperienceWorkspace(t *testing.T) (quickService, string, string) {
	t.Helper()
	root := t.TempDir()
	workspace := "261011-101-confirmation"
	path := filepath.Join(root, ".planning", "quick", workspace)
	mustMkdirAllScriptDomainTest(t, path)
	mustWriteScriptDomainTest(t, filepath.Join(path, "STATUS.md"), `---
id: "261011-101"
slug: "confirmation"
title: "Confirmation"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

Unconfirmed

## Execution

Not started
`)
	return quickService{projectRoot: root}, path, workspace
}

func TestQuickExperienceEvidenceVisibleBeforeApprovalAndExecutionBlocked(t *testing.T) {
	service, path, workspace := quickExperienceWorkspace(t)
	doc, err := service.stageCheckpoint(path, workspace, quickExperienceInput(), false)
	if err != nil {
		t.Fatal(err)
	}
	if doc.ConfirmationState != "staged" {
		t.Fatalf("new request must await confirmation: %s", doc.ConfirmationState)
	}
	view := renderQuickDecisionView(doc)
	for _, marker := range []string{
		"### 当前情况与依据", "src/search.go:42", "Reuse the existing search service.",
		"Keep the current query format compatible.", "Search and adjacent route checks pass.",
		"Queries return matching records", "回复：**确认**",
	} {
		if !strings.Contains(view, marker) {
			t.Errorf("confirmation view missing %q: %s", marker, view)
		}
	}
	if strings.Contains(view, doc.ConfirmationDigest) {
		t.Fatalf("human view exposes raw confirmation digest: %s", view)
	}
	status, err := os.ReadFile(filepath.Join(path, "STATUS.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(status), "current_state_evidence:") || !strings.Contains(string(status), "src/search.go:42") {
		t.Errorf("STATUS projection lost current-state evidence: %s", status)
	}
	confirmationBefore, err := os.ReadFile(filepath.Join(path, quickConfirmationFileName))
	if err != nil {
		t.Fatal(err)
	}
	if _, _, _, err := service.startWorkItem(path, workspace, "261011-101", "Q1", nil); err == nil || !strings.Contains(err.Error(), "checkpoint is not confirmed") {
		t.Fatalf("staged decision must block item-start: %v", err)
	}
	if _, err := service.runExecution("packet-compile", "261011-101", []string{"packet-compile", "261011-101", "--item", "Q1"}); err == nil || !strings.Contains(err.Error(), "checkpoint is not confirmed") {
		t.Fatalf("staged decision must block packet writes: %v", err)
	}
	confirmationAfter, err := os.ReadFile(filepath.Join(path, quickConfirmationFileName))
	if err != nil {
		t.Fatal(err)
	}
	statusAfter, err := os.ReadFile(filepath.Join(path, "STATUS.md"))
	if err != nil {
		t.Fatal(err)
	}
	if string(confirmationBefore) != string(confirmationAfter) || string(status) != string(statusAfter) {
		t.Fatal("refused execution mutated staged confirmation or STATUS")
	}
	if _, err := os.Stat(filepath.Join(path, "packets", "Q1.json")); !os.IsNotExist(err) {
		t.Fatalf("refused execution wrote a packet: %v", err)
	}
	confirmed, err := service.confirmCheckpoint(path, workspace, doc.ConfirmationDigest)
	if err != nil || confirmed.ConfirmationState != "confirmed" {
		t.Fatalf("exact displayed decision must be confirmable: doc=%+v err=%v", confirmed, err)
	}
}

func TestQuickExperienceEvidenceDeltaRequiresFreshDigestAndShowsOnlyChange(t *testing.T) {
	service, path, workspace := quickExperienceWorkspace(t)
	input := quickExperienceInput()
	doc, err := service.stageCheckpoint(path, workspace, input, false)
	if err != nil {
		t.Fatal(err)
	}
	oldDigest := doc.ConfirmationDigest
	if _, err := service.confirmCheckpoint(path, workspace, oldDigest); err != nil {
		t.Fatal(err)
	}
	input["source"] = map[string]any{
		"kind": "delta", "semantic_delta": true, "delta_summary": "Current behavior contradicts the previous baseline",
		"changed_decision_fields": []any{"current_state_evidence"},
	}
	input["decision"].(map[string]any)["current_state_evidence"] = []any{"Current records require case-insensitive search (tests/search_test.go:18)."}
	doc, err = service.stageCheckpoint(path, workspace, input, false)
	if err != nil {
		t.Fatal(err)
	}
	if doc.ConfirmationDigest == oldDigest || doc.ConfirmationState != "staged" {
		t.Fatalf("material evidence delta reused approval: %+v", doc)
	}
	view := renderQuickDecisionView(doc)
	if !strings.Contains(view, "### 当前情况与依据") || !strings.Contains(view, "tests/search_test.go:18") || !strings.Contains(view, "未列出的决策保持不变") {
		t.Fatalf("delta view lost the changed evidence or unchanged boundary: %s", view)
	}
	for _, unchanged := range []string{"Deliver search", "### 你会看到", "### 交付与验收", "Reuse the existing search service.", "src/search.go:42"} {
		if strings.Contains(view, unchanged) {
			t.Errorf("delta view repeats unchanged or superseded field %q: %s", unchanged, view)
		}
	}
	if _, err := service.confirmCheckpoint(path, workspace, oldDigest); err == nil {
		t.Fatal("old digest confirmed changed evidence")
	}
	if _, err := service.confirmCheckpoint(path, workspace, doc.ConfirmationDigest); err != nil {
		t.Fatal(err)
	}
	input["decision"].(map[string]any)["current_state_evidence"] = []any{}
	doc, err = service.stageCheckpoint(path, workspace, input, false)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(renderQuickDecisionView(doc), "### 当前情况与依据\n\n- 无") {
		t.Fatal("an explicitly selected evidence removal must remain visible")
	}
}

func TestQuickExperienceLegacyDigestCompatibility(t *testing.T) {
	// Frozen canonical bytes produced by the pre-evidence-field algorithm.
	// This fixture deliberately does not use the current digest implementation
	// to construct its compatibility oracle.
	const legacyCanonical = `{"assumptions_and_risks":[],"completion_evidence":["Search and adjacent route checks pass."],"goal":"Deliver search","items":[{"acceptance":"Queries return matching records","deliverable":"Search","depends_on":[],"id":"Q1"}],"recommended_approach":"Reuse the existing search service.","reconfirmation_trigger":"Change to scope or compatibility","schema":"quick-confirmation-v1","scope":{"defer":[],"exclude":["publishing"],"include":["search"]},"ui_confirmation":{},"user_visible_result":"Search finds matching records"}`
	const legacyDigest = "4b677d287dc038d7d2656d06c0a86f16c1b6b921294e929d52ad816c6f20d4f8"
	sum := sha256.Sum256([]byte(legacyCanonical))
	expected := hex.EncodeToString(sum[:])
	if expected != legacyDigest {
		t.Fatal("frozen pre-field canonical digest fixture changed")
	}
	input := quickExperienceInput()["decision"].(map[string]any)
	delete(input, "current_state_evidence")
	input["assumptions_and_risks"] = []any{}
	for _, withEmpty := range []bool{false, true} {
		if withEmpty {
			input["current_state_evidence"] = []any{}
		}
		decision, err := parseQuickDecision(input)
		if err != nil {
			t.Fatal(err)
		}
		actual, err := computeQuickConfirmationDigest(decision)
		if err != nil || actual != expected {
			t.Fatalf("legacy digest changed with empty=%v: got=%s want=%s err=%v", withEmpty, actual, expected, err)
		}
	}
	input["current_state_evidence"] = []any{"Unknown: no existing search baseline was supplied."}
	decision, err := parseQuickDecision(input)
	if err != nil {
		t.Fatal(err)
	}
	digest, err := computeQuickConfirmationDigest(decision)
	if err != nil || digest == expected {
		t.Fatalf("nonempty evidence must enter the digest: got=%s legacy=%s err=%v", digest, expected, err)
	}
}

func TestQuickExperienceConfirmedAndInheritedDeliveryOnlyPreserveDecision(t *testing.T) {
	for _, inherited := range []bool{false, true} {
		for _, legacy := range []bool{false, true} {
			t.Run(map[bool]string{false: "confirmed", true: "inherited"}[inherited]+map[bool]string{false: "/with-evidence", true: "/legacy"}[legacy], func(t *testing.T) {
				service, path, workspace := quickExperienceWorkspace(t)
				input := quickExperienceInput()
				if legacy {
					delete(input["decision"].(map[string]any), "current_state_evidence")
				}
				if inherited {
					input["source"] = map[string]any{"kind": "discussion", "discussion_slug": "search", "review_digest": strings.Repeat("a", 64)}
				}
				doc, err := service.stageCheckpoint(path, workspace, input, false)
				if err != nil {
					t.Fatal(err)
				}
				if !inherited {
					doc, err = service.confirmCheckpoint(path, workspace, doc.ConfirmationDigest)
					if err != nil {
						t.Fatal(err)
					}
				}
				state, digest := doc.ConfirmationState, doc.ConfirmationDigest
				before, err := json.Marshal(doc.Decision)
				if err != nil {
					t.Fatal(err)
				}
				doc, err = service.stageCheckpoint(path, workspace, map[string]any{
					"delivery": map[string]any{"waves": []any{map[string]any{"id": "W2", "item_ids": []any{"Q1"}}}},
				}, true)
				if err != nil {
					t.Fatal(err)
				}
				after, err := json.Marshal(doc.Decision)
				if err != nil {
					t.Fatal(err)
				}
				if doc.ConfirmationState != state || doc.ConfirmationDigest != digest || string(before) != string(after) {
					t.Fatal("delivery-only change invalidated or altered the approved decision")
				}
				packet, ready, blockers, err := compileQuickWorkerPacket(doc, "Q1")
				if err != nil || !ready || len(blockers) != 0 {
					t.Fatalf("approved packet must remain ready: ready=%v blockers=%v err=%v", ready, blockers, err)
				}
				decisionInput := input["decision"].(map[string]any)
				for _, field := range []string{"current_state_evidence", "recommended_approach", "assumptions_and_risks", "completion_evidence"} {
					expected := decisionInput[field]
					if field != "recommended_approach" {
						expected = append([]string{}, quickStringSlice(expected)...)
					}
					if !reflect.DeepEqual(packet[field], expected) {
						t.Errorf("worker packet lost confirmed %s: got=%#v want=%#v", field, packet[field], expected)
					}
				}
				if inherited && (!strings.Contains(renderQuickDecisionView(doc), "无需重复确认") || strings.Contains(renderQuickDecisionView(doc), "回复：**确认**")) {
					t.Fatal("unchanged inherited decision requested a duplicate confirmation")
				}
			})
		}
	}
}

func TestQuickExperienceRejectsMalformedEvidenceWithoutDiscardingIt(t *testing.T) {
	for _, value := range []any{nil, "observation", 1, map[string]any{}, []any{1}, []any{nil}, []any{""}, []any{" \t\n "}, []any{"observation", false}} {
		t.Run(string(mustQuickExperienceJSON(t, value)), func(t *testing.T) {
			service, path, workspace := quickExperienceWorkspace(t)
			statusBefore, err := os.ReadFile(filepath.Join(path, "STATUS.md"))
			if err != nil {
				t.Fatal(err)
			}
			input := quickExperienceInput()
			input["decision"].(map[string]any)["current_state_evidence"] = value
			if _, err := service.stageCheckpoint(path, workspace, input, false); err == nil || !strings.Contains(err.Error(), "decision.current_state_evidence") {
				t.Fatalf("malformed evidence was silently coerced or discarded: value=%#v err=%v", value, err)
			}
			statusAfter, err := os.ReadFile(filepath.Join(path, "STATUS.md"))
			if err != nil {
				t.Fatal(err)
			}
			if string(statusBefore) != string(statusAfter) {
				t.Fatal("invalid evidence staging mutated STATUS")
			}
			if _, err := os.Stat(filepath.Join(path, quickConfirmationFileName)); !os.IsNotExist(err) {
				t.Fatalf("invalid evidence staging wrote confirmation: %v", err)
			}
		})
	}
}

func mustQuickExperienceJSON(t *testing.T, value any) []byte {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}
