package main

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestQuickDirectOptionBoundaries(t *testing.T) {
	cases := []struct {
		name, mode string
		args       []string
		want, bad  bool
	}{
		{"legacy", "item-start", []string{"item-start", "id", "--item", "Q1"}, false, false},
		{"direct", "item-start", []string{"item-start", "id", "--item", "Q1", "--leader-direct"}, true, false},
		{"literal", "item-start", []string{"--reason", "--leader-direct"}, false, false},
		{"literal then flag", "item-start", []string{"--evidence", "--leader-direct", "--leader-direct"}, true, false},
		{"duplicate", "item-start", []string{"--leader-direct", "--leader-direct"}, false, true},
		{"assigned", "item-start", []string{"--leader-direct=false"}, false, true},
		{"accept cannot select", "item-accept", []string{"--leader-direct"}, false, true},
		{"fallback cannot select", "allow-inline", []string{"--leader-direct"}, false, true},
		{"preview cannot select", "packet-compile", []string{"--leader-direct"}, false, true},
		{"status cannot select", "item-status", []string{"--leader-direct"}, false, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := parseQuickLeaderDirectOption(tc.mode, tc.args)
			if (err != nil) != tc.bad || got != tc.want {
				t.Fatalf("got %v %v", got, err)
			}
		})
	}
}

func TestQuickDirectModeSelectionAndResume(t *testing.T) {
	cases := []struct {
		status, recorded  string
		inline, requested bool
		want              string
		bad               bool
	}{
		{"pending", "", false, false, "worker", false},
		{"ready", "", false, true, quickLeaderDirectMode, false},
		{"pending", "", false, true, quickLeaderDirectMode, false},
		{"in_progress", "", false, true, "", true},
		{"in_progress", "worker", false, true, "", true},
		{"blocked", "", false, true, "", true},
		{"accepted", "worker", false, true, "", true},
		{"ready", "", true, true, "", true},
		{"in_progress", quickLeaderDirectMode, false, false, quickLeaderDirectMode, false},
		{"in_progress", quickLeaderDirectMode, false, true, quickLeaderDirectMode, false},
		{"blocked", quickLeaderDirectMode, false, false, quickLeaderDirectMode, false},
		{"in_progress", quickLeaderDirectMode, true, false, "", true},
		{"in_progress", "leader-inline", true, false, "worker", false},
		{"ready", "unknown-mode", false, false, "", true},
	}
	for i, tc := range cases {
		got, err := resolveQuickItemExecutionMode(tc.status, tc.recorded, tc.inline, tc.requested)
		if got != tc.want || (err != nil) != tc.bad {
			t.Fatalf("case %d: %q %v", i, got, err)
		}
	}
}

func TestQuickDirectRequiresGreenStructuredEvidence(t *testing.T) {
	valid := func() map[string]any {
		return map[string]any{
			"validation_results": []map[string]string{{"command": "go test ./example", "status": "passed"}},
			"blockers":           []string{},
		}
	}
	if err := validateQuickLeaderDirectResult(valid()); err != nil {
		t.Fatal(err)
	}
	for _, status := range []string{"failed", "skipped", "", "success"} {
		v := valid()
		v["validation_results"].([]map[string]string)[0]["status"] = status
		if err := validateQuickLeaderDirectResult(v); err == nil {
			t.Fatalf("accepted %q", status)
		}
	}
	for _, v := range []map[string]any{
		nil, {}, {"validation_results": []map[string]string{}, "blockers": []string{}},
		{"validation_results": []map[string]string{{"command": " ", "status": "passed"}}, "blockers": []string{}},
		{"validation_results": []map[string]string{{"command": "test", "status": "passed"}}},
		{"validation_results": []map[string]string{{"command": "test", "status": "passed"}}, "blockers": []string{"missing proof"}},
		{"validation_results": "passed", "blockers": []string{}},
	} {
		if err := validateQuickLeaderDirectResult(v); err == nil {
			t.Fatalf("accepted %#v", v)
		}
	}
}

func TestQuickDirectDiscoveryPreservesContracts(t *testing.T) {
	contract := quickItemDispatchContract("quick.item-start")
	if contract["schema"] != quickDispatchSchema || contract["result_submit_required"] != true {
		t.Fatal(contract)
	}
	if quickItemDispatchContract("quick.item-accept") != nil {
		t.Fatal("accept must not select mode")
	}
	for _, owned := range []any{nil, "owned", map[string]any{"schema": "future"}} {
		item := map[string]any{"usage": "existing", "execution_contract": owned}
		addQuickPackOutputContract("quick.item-start", nil, item)
		if !reflect.DeepEqual(item["execution_contract"], owned) || item["usage"] != "existing" {
			t.Fatal(item)
		}
		fresh := map[string]any{}
		addQuickPackOutputContract("quick.item-start", item, fresh)
		if !reflect.DeepEqual(fresh["execution_contract"], owned) {
			t.Fatal(fresh)
		}
	}
	data := map[string]any{"commands": []string{"item-start", "item-status"}}
	addQuickHelpOutputContracts(data)
	got := data["execution_contracts"].(map[string]any)["quick.item-start"]
	if !reflect.DeepEqual(got, contract) {
		t.Fatal(data)
	}
	contract["default"] = "corrupt"
	if quickItemDispatchContract("quick.item-start")["default"] != "worker" {
		t.Fatal("shared mutable discovery")
	}
	_, err := json.Marshal(data)
	if err != nil {
		t.Fatal(err)
	}
}

func FuzzQuickDirectLiteralOptionValue(f *testing.F) {
	for _, v := range []string{"--leader-direct", "--leader-direct=true", "--compact", "", "含 空格"} {
		f.Add(v)
	}
	f.Fuzz(func(t *testing.T, value string) {
		for _, flag := range []string{"--evidence", "--reason", "--project-root", "--item"} {
			got, err := parseQuickLeaderDirectOption("item-start", []string{flag, value})
			if err != nil || got {
				t.Fatalf("literal became flag: %q", value)
			}
			got, err = parseQuickLeaderDirectOption("item-start", []string{flag, value, "--leader-direct"})
			if err != nil || !got {
				t.Fatalf("real flag lost: %q", value)
			}
			compact, err := parseQuickExecutionCompactOption("item-start", []string{flag, value, "--leader-direct"})
			if err != nil || compact {
				t.Fatal("direct flag changed compact mode")
			}
		}
		_, err := parseQuickLeaderDirectOption("item-start", []string{"--leader-direct=" + strings.ReplaceAll(value, "\x00", "")})
		if err == nil {
			t.Fatal("accepted assigned boolean")
		}
	})
}
