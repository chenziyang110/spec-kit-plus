package main

import (
	"bytes"
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func quickShadowJSONFixture(t *testing.T, number string) (quickConfirmationDoc, []byte) {
	t.Helper()
	doc := quickConfirmationDoc{
		Schema: quickConfirmationSchema, Workspace: "state-fidelity",
		ConfirmationMode: "explicit", ConfirmationState: "confirmed",
		Source: quickConfirmationSource{Kind: "prompt"},
		Decision: quickConfirmationDecision{
			Goal: "Keep the exact input contract", UserVisibleResult: "source identifiers stay unchanged",
			Scope:                 quickConfirmationScope{Include: []string{"source identifiers"}},
			Items:                 []quickConfirmationItem{{ID: "Q1", Deliverable: "bounded change", Acceptance: "original identifier preserved", WriteScope: []string{"src/id.go"}}},
			ReconfirmationTrigger: "user changes the contract",
			UIConfirmation: map[string]any{"applicable": false, "source_id": json.Number(number),
				"nested": []any{map[string]any{"threshold": json.Number("0.12345678901234567890123456789")}}},
		},
		Execution: quickConfirmationExecution{WorkItemStatus: []quickWorkItemStatus{{WorkItemID: "Q1", Status: "pending"}}},
	}
	var err error
	doc.ConfirmationDigest, err = computeQuickConfirmationDigest(doc.Decision)
	if err != nil {
		t.Fatal(err)
	}
	raw, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	return doc, raw
}

func TestQuickShadowJSONPreservesNumbersAndDecisionDigest(t *testing.T) {
	for _, value := range []string{"9007199254740993", "18446744073709551615", "1.234567890123456789e+90", "0.1"} {
		t.Run(value, func(t *testing.T) {
			original, raw := quickShadowJSONFixture(t, value)
			doc, err := decodeQuickShadowConfirmation(raw)
			if err != nil {
				t.Fatal(err)
			}
			got, ok := doc.Decision.UIConfirmation["source_id"].(json.Number)
			if !ok || got.String() != value {
				t.Fatalf("number changed: %#v", doc.Decision.UIConfirmation)
			}
			digest, err := computeQuickConfirmationDigest(doc.Decision)
			if err != nil || digest != original.ConfirmationDigest || digest != doc.ConfirmationDigest {
				t.Fatal("exact typed read changed the protected decision digest", err)
			}
			want, _ := json.Marshal(original.Decision.UIConfirmation)
			actual, _ := json.Marshal(doc.Decision.UIConfirmation)
			if !bytes.Equal(want, actual) {
				t.Fatalf("nested numeric metadata changed: %s", actual)
			}
		})
	}
}

func TestQuickShadowJSONRejectsTypedFieldAliases(t *testing.T) {
	cases := map[string]string{
		"confirmation": `{"confirmation_state":"staged","Confirmation_State":"confirmed"}`,
		"reversed":     `{"Confirmation_State":"confirmed","confirmation_state":"staged"}`,
		"single-alias": `{"Confirmation_State":"confirmed"}`,
		"decision":     `{"decision":{"goal":"first","Goal":"replacement"}}`,
		"scope":        `{"decision":{"scope":{"include":["keep"],"Include":["replace"]}}}`,
		"item":         `{"decision":{"items":[{"id":"Q1","ID":"Q2"}]}}`,
		"status":       `{"execution":{"work_item_status":[{"work_item_id":"Q1","status":"blocked","Status":"pending"}]}}`,
		"pointer":      `{"execution":{"blocked_dispatch":{"status":"subagent-blocked","Status":"none"}}}`,
		"unicode-fold": `{"execution":{"work_item_status":[{"work_item_id":"Q1","ſtatus":"pending"}]}}`,
		"escaped":      `{"execution":{"work_item_status":[{"work_item_id":"Q1","\u0053tatus":"pending"}]}}`,
	}
	for name, raw := range cases {
		t.Run(name, func(t *testing.T) {
			doc, err := decodeQuickShadowConfirmation([]byte(raw))
			if err == nil || !strings.Contains(err.Error(), "quick_shadow_field_alias") || !reflect.DeepEqual(doc, quickConfirmationDoc{}) {
				t.Fatalf("alias admitted or partial state returned: %#v %v", doc, err)
			}
		})
	}
}

func TestQuickShadowJSONKeepsDynamicMapKeysDistinct(t *testing.T) {
	raw := []byte(`{"decision":{"ui_confirmation":{"Status":"one","status":"two","nested":[{"ID":9007199254740993,"id":"different"}]}}}`)
	doc, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	ui := doc.Decision.UIConfirmation
	if ui["Status"] != "one" || ui["status"] != "two" {
		t.Fatal("dynamic metadata keys were case folded", ui)
	}
	row := ui["nested"].([]any)[0].(map[string]any)
	if row["ID"].(json.Number).String() != "9007199254740993" || row["id"] != "different" {
		t.Fatal(row)
	}
}

func TestQuickShadowJSONPreservesCanonicalLegacyWire(t *testing.T) {
	original, _ := quickShadowJSONFixture(t, "1")
	original.Decision.UIConfirmation = map[string]any{"applicable": false, "width": float64(1920), "ratio": 0.1, "labels": []any{"加载", nil, true}}
	original.Execution.BlockedDispatch = nil
	original.Delivery.Waves = nil
	raw, err := json.Marshal(original)
	if err != nil {
		t.Fatal(err)
	}
	doc, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	got, _ := json.Marshal(doc)
	if !bytes.Equal(raw, got) {
		t.Fatalf("canonical legacy wire changed: %s", got)
	}
	beforeDigest, _ := computeQuickConfirmationDigest(original.Decision)
	afterDigest, _ := computeQuickConfirmationDigest(doc.Decision)
	if beforeDigest != afterDigest {
		t.Fatal("ordinary legacy numeric values changed digest")
	}
}

func TestQuickShadowJSONRetainsWireValidationAndNoPartialResult(t *testing.T) {
	cases := []string{
		"", "null", "[]", "{", "{} {}", `{"x":1,"x":2}`, `{"x":1,"\u0078":2}`,
		`{"decision":{"ui_confirmation":{"value":"\ud800"}}}`,
		`{"schema":1}`, `{"decision":[]}`, `{"decision":{"items":{}}}`,
		`{"execution":{"work_item_status":[1]}}`, `{"decision":{"scope":{"include":[42]}}}`,
		`{"schema":"` + string([]byte{255}) + `"}`, strings.Repeat(" ", 128*1024+1),
		`{"unknown":` + strings.Repeat("[", 34) + "0" + strings.Repeat("]", 34) + "}",
	}
	for i, raw := range cases {
		doc, err := decodeQuickShadowConfirmation([]byte(raw))
		if err == nil || !reflect.DeepEqual(doc, quickConfirmationDoc{}) {
			t.Errorf("invalid wire case %d returned state", i)
		}
	}
}

func TestQuickShadowJSONDoesNotRepairStateOrDigest(t *testing.T) {
	original, raw := quickShadowJSONFixture(t, "9007199254740993")
	raw = bytes.Replace(raw, []byte(original.ConfirmationDigest), []byte("mismatched-digest"), 1)
	before := append([]byte(nil), raw...)
	doc, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	if doc.ConfirmationDigest != "mismatched-digest" || doc.ConfirmationState != "confirmed" || !bytes.Equal(before, raw) {
		t.Fatal("decoder repaired or changed source state")
	}
	expected, _ := computeQuickConfirmationDigest(doc.Decision)
	if expected == doc.ConfirmationDigest {
		t.Fatal("mismatched digest was made valid")
	}
}

func TestQuickShadowJSONNoAliasingAndUnknownFieldCompatibility(t *testing.T) {
	raw := []byte(`{"goal_note":"opaque","future_metadata":{"Status":"allowed"},"schema":"quick-confirmation-v1","decision":{"goal":"original","ui_confirmation":{"id":9007199254740993}}}`)
	before := append([]byte(nil), raw...)
	doc, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(raw, before) {
		t.Fatal("source bytes changed")
	}
	for i := range raw {
		raw[i] = 'x'
	}
	if doc.Decision.Goal != "original" || doc.Decision.UIConfirmation["id"].(json.Number).String() != "9007199254740993" {
		t.Fatal("decoded data aliases the read buffer")
	}
	// Unknown fields remain unprojected, as with the original typed owner. The
	// adapter binds the original raw bytes separately; no authority is inferred.
}

func TestQuickShadowJSONDistinctExactInputsDoNotCollapse(t *testing.T) {
	_, rawA := quickShadowJSONFixture(t, "9007199254740992")
	_, rawB := quickShadowJSONFixture(t, "9007199254740993")
	a, err := decodeQuickShadowConfirmation(rawA)
	if err != nil {
		t.Fatal(err)
	}
	b, err := decodeQuickShadowConfirmation(rawB)
	if err != nil {
		t.Fatal(err)
	}
	ha, _ := computeQuickConfirmationDigest(a.Decision)
	hb, _ := computeQuickConfirmationDigest(b.Decision)
	if ha == hb {
		t.Fatal("distinct exact decisions collapsed to one digest")
	}
}

func FuzzQuickShadowJSONNeverReturnsPartialState(f *testing.F) {
	for _, raw := range []string{`{}`, `null`, `{"decision":{"ui_confirmation":{"id":9007199254740993}}}`, `{"confirmation_state":"staged","Confirmation_State":"confirmed"}`, `{"value":"\ud800"}`} {
		f.Add([]byte(raw))
	}
	f.Fuzz(func(t *testing.T, raw []byte) {
		doc, err := decodeQuickShadowConfirmation(raw)
		if err != nil && !reflect.DeepEqual(doc, quickConfirmationDoc{}) {
			t.Fatal("failed decode returned partial state")
		}
		if err == nil {
			if _, err := json.Marshal(doc); err != nil {
				t.Fatal("decoder produced an unserializable value", err)
			}
		}
	})
}

func TestQuickShadowJSONExactNumbersSurviveOriginalPacketBuilder(t *testing.T) {
	original, raw := quickShadowJSONFixture(t, "9007199254740993")
	doc, err := decodeQuickShadowConfirmation(raw)
	if err != nil {
		t.Fatal(err)
	}
	packet, ready, blockers, err := compileQuickWorkerPacket(&doc, "Q1")
	if err != nil || !ready || len(blockers) != 0 {
		t.Fatal("original packet gate rejected exact state", err, blockers)
	}
	actual, err := json.Marshal(packet)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Contains(actual, []byte("9007199254740993")) ||
		!bytes.Contains(actual, []byte("0.12345678901234567890123456789")) ||
		packet["confirmation_digest"] != original.ConfirmationDigest {
		t.Fatalf("original packet builder lost precise contract values: %s", actual)
	}
	if packet["worker_contract"].(map[string]any)["must_result_submit_before_accept"] != true {
		t.Fatal("packet lost its result gate")
	}
}
