package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"reflect"
	"strings"
	"testing"
)

func TestQuickShadowDiscoveryHelpPreservesLegacyFields(t *testing.T) {
	calls := 0
	legacy := func(args []string, w io.Writer) int {
		calls++
		if !reflect.DeepEqual(args, []string{"--help"}) {
			t.Fatal(args)
		}
		e := NewEnvelope("ok", "quick command help")
		e.Data["commands"] = []string{"list", "item-start"}
		e.Data["close_usage"] = "original close usage"
		e.Data["future"] = json.RawMessage(`{"value":9007199254740993}`)
		return shadowCLIEncode(w, e)
	}
	var out bytes.Buffer
	if code := writeQuickHelpWithShadow(context.Background(), []string{"--help"}, &out, legacy, shadowCLIEncode); code != 0 || calls != 1 {
		t.Fatal(code, calls)
	}
	var e Envelope
	if err := json.Unmarshal(out.Bytes(), &e); err != nil {
		t.Fatal(err)
	}
	if e.Data["close_usage"] != "original close usage" ||
		!reflect.DeepEqual(e.Data["commands"], []any{"list", "item-start", "context-shadow"}) ||
		!bytes.Contains(out.Bytes(), []byte("9007199254740993")) {
		t.Fatal("legacy help changed or lost numeric precision", e)
	}
	if e.Data["context_shadow"].(map[string]any)["usage"] != quickShadowCommandUsage {
		t.Fatal(e)
	}
}

func TestQuickShadowDiscoveryHelpDoesNotDuplicateCommand(t *testing.T) {
	legacy := func(_ []string, w io.Writer) int {
		e := NewEnvelope("ok", "help")
		e.Data["commands"] = []string{"list", "context-shadow"}
		return shadowCLIEncode(w, e)
	}
	var out bytes.Buffer
	if writeQuickHelpWithShadow(context.Background(), []string{"-h"}, &out, legacy, shadowCLIEncode) != 0 {
		t.Fatal("help failed")
	}
	var e Envelope
	_ = json.Unmarshal(out.Bytes(), &e)
	if !reflect.DeepEqual(e.Data["commands"], []any{"list", "context-shadow"}) {
		t.Fatal(e)
	}
}

func TestQuickShadowDiscoveryHelpCancellationAvoidsRead(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	var out bytes.Buffer
	code := writeQuickHelpWithShadow(ctx, []string{"--help"}, &out,
		func([]string, io.Writer) int { t.Fatal("cancelled help reached old owner"); return 0 }, shadowCLIEncode)
	if code != 10 || bytes.Contains(out.Bytes(), []byte(`"status":"ok"`)) {
		t.Fatal(code, out.String())
	}
}

func TestQuickShadowDiscoveryHelpRejectsBadEnvelope(t *testing.T) {
	for _, raw := range []string{
		"not-json", `null`, `{"status":"ok","data":{"commands":null}}`,
		`{"status":"ok","data":{"commands":[{}]}}`,
		`{"status":"ok","data":{"commands":[]}} {}`,
	} {
		var out bytes.Buffer
		code := writeQuickHelpWithShadow(context.Background(), []string{"--help"}, &out,
			func(_ []string, w io.Writer) int { _, _ = io.WriteString(w, raw); return 0 }, shadowCLIEncode)
		if code != 1 || out.Len() != 0 {
			t.Fatal("invalid buffered help escaped", raw, code)
		}
	}
}

func TestQuickShadowDiscoveryHelpEnforcesCompleteEnvelopeLimit(t *testing.T) {
	legacy := func(_ []string, w io.Writer) int {
		e := NewEnvelope("ok", "help")
		e.Data["commands"] = []string{"list"}
		e.Data["large_legacy_field"] = strings.Repeat("x", quickShadowCLIOutputLimit)
		return shadowCLIEncode(w, e)
	}
	var out bytes.Buffer
	if writeQuickHelpWithShadow(context.Background(), []string{"--help"}, &out, legacy, shadowCLIEncode) != 10 || out.Len() > quickShadowCLIOutputLimit {
		t.Fatal("unbounded augmented help")
	}
}

func TestQuickShadowDiscoveryHelpPreservesLegacyFailure(t *testing.T) {
	legacy := func(_ []string, w io.Writer) int {
		return shadowCLIEncode(w, NewEnvelope("usage-error", "legacy invalid request"))
	}
	var expected, actual bytes.Buffer
	want := legacy(nil, &expected)
	got := writeQuickHelpWithShadow(context.Background(), nil, &actual, legacy, shadowCLIEncode)
	if want != got || !bytes.Equal(expected.Bytes(), actual.Bytes()) {
		t.Fatal("legacy error changed")
	}
	if writeQuickHelpWithShadow(context.Background(), nil, shadowCLIShortWriter{}, legacy, shadowCLIEncode) != 1 {
		t.Fatal("short write accepted")
	}
}

func TestQuickShadowDiscoveryDescriptorReusesOutputContract(t *testing.T) {
	for _, args := range [][]string{{quickShadowCapability}, {"--id", quickShadowCapability, "--format", "json"}} {
		var out bytes.Buffer
		code := dispatchQuickShadowDescriptor(args, &out,
			func([]string, io.Writer) int { t.Fatal("shadow used generic legacy descriptor"); return 0 }, shadowCLIEncode)
		if code != 0 {
			t.Fatal(code)
		}
		var env Envelope
		if err := json.Unmarshal(out.Bytes(), &env); err != nil {
			t.Fatal(err)
		}
		capability := env.Data["capability"].(map[string]any)
		contract := capability["output_contract"].(map[string]any)
		if capability["side_effect"] != "read-only" || contract["authorizes_execution"] != false ||
			contract["acceptance_verified"] != false || capability["usage"] != quickShadowCommandUsage ||
			len(env.NextArgv) != 0 {
			t.Fatal(env)
		}
	}
}

func TestQuickShadowDiscoveryDescriptorDelegatesOtherSelectorsExactly(t *testing.T) {
	for _, args := range [][]string{nil, {"--id"}, {"--bad"}, {"quick.item-start", "--format", "json"}, {"quick.context-shadow-unknown"}} {
		calls := 0
		var actual bytes.Buffer
		legacy := func(got []string, w io.Writer) int {
			calls++
			if !reflect.DeepEqual(args, got) {
				t.Fatal("selector changed", got)
			}
			_, _ = io.WriteString(w, "legacy-result")
			return 2
		}
		code := dispatchQuickShadowDescriptor(args, &actual, legacy,
			func(io.Writer, Envelope) int { t.Fatal("legacy output was re-encoded"); return 0 })
		if code != 2 || calls != 1 || actual.String() != "legacy-result" {
			t.Fatal(code, calls, actual.String())
		}
	}
}

func TestQuickShadowDiscoveryRegisteredExactlyOnce(t *testing.T) {
	count := 0
	for _, id := range defaultCapabilities() {
		if id == quickShadowCapability {
			count++
		}
	}
	if count != 1 {
		t.Fatalf("capability must appear exactly once, got %d", count)
	}
}
