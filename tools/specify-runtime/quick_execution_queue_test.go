package main

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestQuickQueueHonorsExplicitBlockWithoutHidingIndependentWork(t *testing.T) {
	var doc quickConfirmationDoc
	if err := json.Unmarshal([]byte(`{
		"decision":{"items":[
			{"id":"Q1","depends_on":[]},
			{"id":"Q2","depends_on":["Q1"]},
			{"id":"Q3","depends_on":[]},
			{"id":"Q4","depends_on":[]},
			{"id":"Q5","depends_on":[]},
			{"id":"Q6","depends_on":[]}
		]},
		"execution":{"work_item_status":[
			{"work_item_id":"Q1","status":"blocked"},
			{"work_item_id":"Q2","status":"pending"},
			{"work_item_id":"Q3","status":"ready"},
			{"work_item_id":"Q4","status":"in_progress"},
			{"work_item_id":"Q5","status":"accepted"},
			{"work_item_id":"Q6","status":"BLOCKED"}
		]}
	}`), &doc); err != nil {
		t.Fatal(err)
	}
	before, _ := json.Marshal(doc)
	if got := readyQuickItemIDs(&doc); !reflect.DeepEqual(got, []string{"Q3"}) {
		t.Fatalf("ready=%v; explicitly blocked items must not be advertised as ready", got)
	}
	if got := blockedQuickItemIDs(&doc); !reflect.DeepEqual(got, []string{"Q1", "Q2", "Q6"}) {
		t.Fatalf("blocked=%v; include explicit blocks even with satisfied dependencies", got)
	}
	after, _ := json.Marshal(doc)
	if string(before) != string(after) {
		t.Fatal("queue queries mutated lifecycle state")
	}
}

func TestQuickQueuePreservesDependencyReleaseAndEmptyResults(t *testing.T) {
	var doc quickConfirmationDoc
	if err := json.Unmarshal([]byte(`{
		"decision":{"items":[{"id":"Q1","depends_on":[]},{"id":"Q2","depends_on":["Q1"]}]},
		"execution":{"work_item_status":[{"work_item_id":"Q1","status":"accepted"}]}
	}`), &doc); err != nil {
		t.Fatal(err)
	}
	if got := readyQuickItemIDs(&doc); !reflect.DeepEqual(got, []string{"Q2"}) {
		t.Fatalf("accepted dependency did not release Q2: %v", got)
	}
	if got := blockedQuickItemIDs(&doc); got == nil || len(got) != 0 {
		t.Fatalf("expected non-nil empty blocked list, got %v", got)
	}
}
