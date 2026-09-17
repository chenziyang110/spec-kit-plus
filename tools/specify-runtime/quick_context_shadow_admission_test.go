package main

import (
	"reflect"
	"testing"
)

func quickShadowAdmissionFixture() *quickConfirmationDoc {
	return &quickConfirmationDoc{
		Decision: quickConfirmationDecision{Items: []quickConfirmationItem{
			{ID: "Q1"}, {ID: "Q2", DependsOn: []string{"Q1"}},
		}},
		Execution: quickConfirmationExecution{WorkItemStatus: []quickWorkItemStatus{
			{WorkItemID: "Q1", Status: "accepted"}, {WorkItemID: "Q2", Status: "ready"},
		}},
	}
}

func TestQuickShadowAdmissionAcceptsOwnerReadyWithoutMutation(t *testing.T) {
	// The original item-accept owner marks newly unblocked successors "ready".
	// Diagnostic admission must not reject this valid state or start the item.
	for _, status := range []string{"pending", "ready", "in_progress"} {
		t.Run(status, func(t *testing.T) {
			doc := quickShadowAdmissionFixture()
			doc.Execution.WorkItemStatus[1].Status = status
			before := append([]quickWorkItemStatus(nil), doc.Execution.WorkItemStatus...)
			if err := validateQuickShadowSelection(doc, "Q2"); err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(before, doc.Execution.WorkItemStatus) {
				t.Fatal("diagnostic admission changed execution state")
			}
		})
	}
}

func TestQuickShadowAdmissionKeepsBlockedAndTerminalGates(t *testing.T) {
	for _, status := range []string{"blocked", "accepted", "done", "completed", "", "unexpected", "READY"} {
		doc := quickShadowAdmissionFixture()
		doc.Execution.WorkItemStatus[1].Status = status
		if validateQuickShadowSelection(doc, "Q2") == nil {
			t.Errorf("invalid or terminal status admitted: %q", status)
		}
	}
	for _, itemID := range []string{"", "Q2"} {
		doc := quickShadowAdmissionFixture()
		doc.Execution.BlockedDispatch = &quickBlockedDispatch{Status: "subagent-blocked", ItemID: itemID}
		if validateQuickShadowSelection(doc, "Q2") == nil {
			t.Fatal("dispatch blocker bypassed by ready state")
		}
	}
}

func TestQuickShadowAdmissionKeepsAmbiguityChecks(t *testing.T) {
	for _, mutate := range []func(*quickConfirmationDoc){
		func(d *quickConfirmationDoc) { d.Decision.Items = append(d.Decision.Items, d.Decision.Items[1]) },
		func(d *quickConfirmationDoc) {
			d.Execution.WorkItemStatus = append(d.Execution.WorkItemStatus, d.Execution.WorkItemStatus[1])
		},
		func(d *quickConfirmationDoc) {
			d.Execution.WorkItemStatus = append(d.Execution.WorkItemStatus, quickWorkItemStatus{WorkItemID: "Q99", Status: "ready"})
		},
	} {
		doc := quickShadowAdmissionFixture()
		mutate(doc)
		if validateQuickShadowSelection(doc, "Q2") == nil {
			t.Fatal("ambiguous state was admitted")
		}
	}
	doc := quickShadowAdmissionFixture()
	doc.Execution.WorkItemStatus = doc.Execution.WorkItemStatus[:1]
	if err := validateQuickShadowSelection(doc, "Q2"); err != nil {
		t.Fatal("original absent-row pending default changed", err)
	}
	// This admission helper still does not decide prerequisite acceptance; the
	// existing compileQuickWorkerPacket gate remains mandatory in the adapter.
}

func TestQuickShadowAdmissionReadyDoesNotBypassExistingPacketGates(t *testing.T) {
	doc := quickShadowAdmissionFixture()
	doc.ConfirmationState = "confirmed"
	doc.Execution.WorkItemStatus[0].Status = "pending"
	if err := validateQuickShadowSelection(doc, "Q2"); err != nil {
		t.Fatal(err)
	}
	packet, ready, blockers, err := compileQuickWorkerPacket(doc, "Q2")
	if err != nil || ready || len(blockers) == 0 || packet["ready"] != false {
		t.Fatal("ready label bypassed the original prerequisite gate", packet, err)
	}
	doc.Execution.WorkItemStatus[0].Status = "accepted"
	packet, ready, blockers, err = compileQuickWorkerPacket(doc, "Q2")
	if err != nil || !ready || len(blockers) != 0 || packet["requires_worker"] != true {
		t.Fatal("valid ready successor did not preserve the original worker contract", packet, err)
	}
	contract := packet["worker_contract"].(map[string]any)
	if contract["must_result_submit_before_accept"] != true {
		t.Fatal("diagnostic admission removed result submission")
	}
	doc.ConfirmationState = "staged"
	_, ready, blockers, err = compileQuickWorkerPacket(doc, "Q2")
	if err != nil || ready || len(blockers) == 0 {
		t.Fatal("ready status bypassed checkpoint confirmation")
	}
}
