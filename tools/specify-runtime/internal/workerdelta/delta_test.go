package workerdelta

import (
	"encoding/json"
	"math"
	"reflect"
	"strings"
	"testing"
)

func decodeTest(t *testing.T, text string) map[string]any {
	t.Helper()
	value, err := Decode([]byte(text))
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func TestVersionedDeltaIsLosslessAcrossLegacyAndTypedInputs(t *testing.T) {
	input := decodeTest(t, `{"task_id":"T1","changed_paths":["./src/old.go","src/new.go"],"changed_files":["src/new.go","src/old.go"],"path_changes":[{"kind":"renamed","old_path":"./src/old.go","new_path":"src/new.go"}],"behavior_surfaces":[{"id":"save","value":900719925474099312345,"enabled":true}],"owner_surfaces":["writer"],"consumer_surfaces":["reader"],"interfaces":[{"name":"save","nested":{"ids":[1,false,null]}}],"generated_surfaces":[{"path":"src/new.go","owner":"generator"}],"state_contracts":[{"state":"persisted"}],"verification":[{"command":"readback","result":"passed","extra":{"count":900719925474099312345}}],"evidence_refs":[{"claim_ref":"C1"}],"invalidated_claim_refs":["C1"],"known_unknowns":["none"],"confidence_notes":["observed"]}`)
	delta, paths, err := Normalize(input)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(paths, []string{"src/new.go", "src/old.go"}) {
		t.Fatalf("paths %v", paths)
	}
	if delta["schema"] != Schema || delta["version"] != 1 {
		t.Fatalf("version %v", delta)
	}
	raw, _ := json.Marshal(delta)
	if !strings.Contains(string(raw), "900719925474099312345") {
		t.Fatal("large evidence integer lost")
	}
	typed := map[string]any{"task_id": "T1", "cognition_delta": delta}
	again, _, err := Normalize(typed)
	if err != nil || !Same(again, delta) {
		t.Fatalf("typed migration lost data: %v", err)
	}
	for _, field := range []string{"behavior_surfaces", "owner_surfaces", "consumer_surfaces", "interfaces", "generated_surfaces", "state_contracts", "evidence_refs", "invalidated_claim_refs", "known_unknowns", "confidence_notes"} {
		if !Same(delta[field], input[field]) {
			t.Errorf("lost %s", field)
		}
	}
	if !Same(delta["verification_evidence"], input["verification"]) {
		t.Fatal("lost legacy verification")
	}
}

func TestDeltaRejectsConflictsUnsafePathsAndWorkerAuthority(t *testing.T) {
	cases := []string{
		`{"changed_paths":["src/a"],"changed_files":["src/b"]}`,
		`{"changed_paths":["../a"]}`,
		`{"changed_paths":["C:/a"]}`,
		`{"submission_history":[]}`,
		`{"cognition_result_binding":{}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":"1"}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1.0}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":true}}`,
		`{"task_id":"T1","cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1,"identity":{"task_id":"T2"}}}`,
		`{"changed_paths":["src/new"],"path_changes":[{"kind":"renamed","old_path":"src/old","new_path":"src/new"}]}`,
		`{"behavior_surfaces":[1],"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1,"behavior_surfaces":[true]}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1,"behavior_surfaces":null}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1,"changed_paths":"src/a"}}`,
		`{"cognition_delta":{"schema":"spec-kit-cognition-delta-v1","version":1,"identity":{"acceptance_revision":"2"}}}`,
	}
	for _, text := range cases {
		t.Run(text, func(t *testing.T) {
			if _, _, err := Normalize(decodeTest(t, text)); err == nil {
				t.Fatal("invalid candidate accepted")
			}
		})
	}
	if _, _, err := Normalize(map[string]any{"behavior_surfaces": []any{math.Inf(1)}}); err == nil {
		t.Fatal("nonfinite candidate accepted")
	}
	for _, text := range []string{`{"x":1,"x":2}`, `{"x":{"y":1,"y":2}}`, `{} {}`, `{"x":1e400}`} {
		if _, err := Decode([]byte(text)); err == nil {
			t.Fatal("duplicate/trailing JSON accepted")
		}
	}
	empty, _, err := Normalize(map[string]any{})
	if err != nil || len(empty) != 0 {
		t.Fatal("empty legacy changed")
	}
}

func TestSubmissionHistoryKeepsRejectedAndFailedAttemptsWithExactCurrentBinding(t *testing.T) {
	result := decodeTest(t, `{"task_id":"T1","status":"failed","changed_paths":["src/a"],"behavior_surfaces":[{"count":900719925474099312345}]}`)
	first, err := Append(nil, result, nil, "failed", "", "worker-results/T1.json", "owner-attempt-1", 2)
	if err != nil {
		t.Fatal(err)
	}
	before, _ := json.Marshal(first["submission_history"])
	result["status"] = "success"
	second, err := Append(first, result, nil, "success", "", "worker-results/T1.json", "owner-attempt-2", 3)
	if err != nil {
		t.Fatal(err)
	}
	if err := Accept(second, "lifecycle/T1.json", 4); err != nil {
		t.Fatal(err)
	}
	rejected := []byte(" {\"changed_files\":[\"src/rejected\"],\"changed_paths\":[\"src/other\"]} ")
	third, err := Append(second, nil, rejected, "rejected", "path aliases conflict", "worker-results/T1.json", "", 4)
	if err != nil {
		t.Fatal(err)
	}
	rows := third["submission_history"].([]any)
	if len(rows) != 3 {
		t.Fatal("history overwritten")
	}
	firstRaw, _ := json.Marshal([]any{rows[0]})
	if string(firstRaw) != string(before) {
		t.Fatal("old immutable row changed")
	}
	binding := third["cognition_result_binding"].(map[string]any)
	if fmtSequence, _ := Sequence(binding["sequence"]); fmtSequence != 2 || binding["acceptance_state"] != "accepted" {
		t.Fatal("rejected event replaced accepted projection")
	}
	row := rows[2].(map[string]any)
	if row["result_json"] != string(rejected) || row["result_sha256"] != Digest(rejected) {
		t.Fatal("raw rejected input lost")
	}
	if !reflect.DeepEqual(HistoryPaths(third), []string{"src/a", "src/other", "src/rejected"}) {
		t.Fatalf("retained paths %v", HistoryPaths(third))
	}
	candidate, err := CandidateFromStored(third)
	if err != nil {
		t.Fatal(err)
	}
	if _, present := candidate["submission_history"]; present {
		t.Fatal("worker authority exposed")
	}
	tampered := Clone(third)
	tampered["status"] = "failed"
	if ValidateStored(tampered) == nil {
		t.Fatal("projection tamper accepted")
	}
	tampered = Clone(third)
	tampered["submission_history"].([]any)[0].(map[string]any)["result_json"] = "{}"
	if ValidateStored(tampered) == nil {
		t.Fatal("history tamper accepted")
	}
	pending, err := Append(nil, nil, []byte("{bad"), "rejected", "malformed", "result.json", "", 0)
	if err != nil {
		t.Fatal(err)
	}
	if _, present := pending["cognition_result_binding"]; present {
		t.Fatal("invalid first input minted binding")
	}
	if len(PendingSequences(pending)) != 1 {
		t.Fatal("unaccounted changes lost")
	}
}

func TestMergePreservesVersionsAndSharedClaims(t *testing.T) {
	events := []Event{}
	for i, status := range []string{"failed", "blocked", "rejected", "success"} {
		events = append(events, Event{SourceRef: "result.json", Sequence: i + 1, AttemptID: status, Status: status, Accepted: status == "success", Delta: map[string]any{"behavior_surfaces": []any{status}, "invalidated_claim_refs": []any{"C1"}}, RetainedPaths: []string{"src/shared"}})
	}
	events = append(events, Event{SourceRef: "other.json", Sequence: 1, AttemptID: "worker2", Accepted: true, Delta: map[string]any{"invalidated_claim_refs": []any{"C1"}}, RetainedPaths: []string{"src/shared"}})
	merged := MergeEvents(events)
	if len(merged.Events) != 5 || len(merged.AcceptedDeltas) != 2 || len(merged.CandidateDeltas) != 3 || len(merged.Conflicts) != 2 {
		t.Fatalf("versions overwritten %#v", merged)
	}
	for _, conflict := range merged.Conflicts {
		if len(conflict.Sources) != 5 {
			t.Fatalf("conflict incomplete %#v", conflict)
		}
	}
}
