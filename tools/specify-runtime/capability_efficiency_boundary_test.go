package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestAPICapabilityJSONRejectsCompetingSelectors(t *testing.T) {
	for _, raw := range []string{
		`{"capabilities":["missing"],"capabilities":["api.show"]}`,
		`{"capabilities":["missing"],"capabiliti\u0065s":["api.show"]}`,
		`{"capabilities":["api.show"],"Capabilities":["missing"]}`,
		`{"capabilities":["api.show"],"capabilitieſ":["missing"]}`,
		`{"capabilities":["api.show"],"metadata":1,"metadata":2}`,
	} {
		t.Run(raw, func(t *testing.T) {
			if got, err := parseCapabilityRequirementsJSON([]byte(raw), "api ensure"); err == nil || got != nil {
				t.Fatal("ambiguous input returned a selection", got, err)
			}
		})
	}
}

func TestAPICapabilityJSONMalformedOrMissingSelection(t *testing.T) {
	for _, raw := range []string{"", "null", "[]", "true", "{}", "{", "{\"capabilities\":",
		`{"capabilities":null}`, `{"capabilities":{}}`, `{"capabilities":[]}`,
		`{"capabilities":[null]}`, `{"capabilities":[1]}`, `{"capabilities":[true]}`,
		`{"capabilities":[""]}`, `{"capabilities":[" "]}`,
		`{"capabilities":["api.show"," api.show "]}`,
		`{"capabilities":["api.show"]} {}`, `{"capabilities":["api.show"]} null`,
		`{"capabilities":["api.show"]} trailing`,
		"{\"capabilities\":[\"api.\xff\"]}",
	} {
		t.Run(raw, func(t *testing.T) {
			if got, err := parseCapabilityRequirementsJSON([]byte(raw), "api pack"); err == nil || got != nil {
				t.Fatal("invalid selection returned partial data", got, err)
			}
		})
	}
}

func TestAPICapabilityJSONRetainsForwardMetadataCompatibility(t *testing.T) {
	// Unrelated metadata is syntactically checked but not interpreted or returned.
	raw := []byte(`{"metadata":{"large":9007199254740993,"labels":["中文","😀"]},"capabiliti\u0065s":[" api.show ","quick.context-shadow"],"future":[null,true]}` + "\n\t ")
	before := append([]byte(nil), raw...)
	got, err := parseCapabilityRequirementsJSON(raw, "api pack")
	if err != nil || !reflect.DeepEqual(got, []string{"api.show", "quick.context-shadow"}) || !bytes.Equal(raw, before) {
		t.Fatal("forward-compatible metadata or exact selection was changed", got, err)
	}
}

func TestAPICapabilityJSONInputByteBoundary(t *testing.T) {
	prefix, suffix := `{"capabilities":["api.show"],"padding":"`, `"}`
	for _, size := range []int{maxAPICapabilityInputBytes - 1, maxAPICapabilityInputBytes, maxAPICapabilityInputBytes + 1} {
		raw := []byte(prefix + strings.Repeat("x", size-len(prefix)-len(suffix)) + suffix)
		got, err := parseCapabilityRequirementsJSON(raw, "api ensure")
		if size > maxAPICapabilityInputBytes {
			if err == nil || got != nil {
				t.Fatal("oversized input returned a selection")
			}
		} else if err != nil || !reflect.DeepEqual(got, []string{"api.show"}) {
			t.Fatal("inclusive byte limit rejected valid input", size, err)
		}
	}
}

func TestAPICapabilityCSVAndJSONSelectSameIDs(t *testing.T) {
	want := []string{"api.show", "api.list", "quick.context-shadow"}
	csv, _, ok := parseCapabilityCSV(" api.show,api.list , quick.context-shadow ", "api pack")
	encoded, _ := json.Marshal(map[string]any{"capabilities": want})
	object, err := parseCapabilityRequirementsJSON(encoded, "api pack")
	if !ok || err != nil || !reflect.DeepEqual(csv, want) || !reflect.DeepEqual(object, want) {
		t.Fatal("selector forms disagree", csv, object, err)
	}
}

func TestAPICapabilitySelectionCountStillBounded(t *testing.T) {
	ids := make([]string, maxAPICapabilitySelection+1)
	for i := range ids {
		ids[i] = "capability." + strings.Repeat("x", i+1)
	}
	for _, count := range []int{maxAPICapabilitySelection, maxAPICapabilitySelection + 1} {
		raw, _ := json.Marshal(map[string]any{"capabilities": ids[:count]})
		selected, err := parseCapabilityRequirementsJSON(raw, "api ensure")
		csv, _, ok := parseCapabilityCSV(strings.Join(ids[:count], ","), "api ensure")
		if count == maxAPICapabilitySelection {
			if err != nil || !ok || !reflect.DeepEqual(selected, csv) {
				t.Fatal("valid count rejected", err)
			}
		} else if err == nil || selected != nil || ok || csv != nil {
			t.Fatal("count overflow accepted")
		}
	}
}

func TestAPICapabilityCSVRejectsOversizeAndLossyInput(t *testing.T) {
	for _, raw := range []string{"api.\xff", strings.Repeat("x", maxAPICapabilityInputBytes+1)} {
		got, env, ok := parseCapabilityCSV(raw, "api pack")
		if ok || got != nil || env.Status != "usage-error" {
			t.Fatal("invalid CSV accepted", env)
		}
	}
	// Exact byte limit remains inclusive; this is syntax, not capability availability.
	if _, _, ok := parseCapabilityCSV(strings.Repeat("x", maxAPICapabilityInputBytes), "api ensure"); !ok {
		t.Fatal("inclusive CSV limit rejected")
	}
}

func TestAPICapabilityResponseCountsMetadataAndEnvelope(t *testing.T) {
	env := NewEnvelope("ok", "capability pack assembled")
	env.Items = []any{map[string]any{"summary": strings.Repeat("x", maxAPIPackOutputBytes-512)}}
	env.Data["runtime"] = map[string]any{"cli_version": strings.Repeat("v", 2048)}
	items, _ := json.Marshal(env.Items)
	if len(items) >= maxAPIPackOutputBytes {
		t.Fatal("fixture must pass the old items-only check")
	}
	var output bytes.Buffer
	if code := writeAPICapabilityEnvelope(&output, env); code != 2 || output.Len() > maxAPIPackOutputBytes {
		t.Fatal("complete envelope escaped its bound", code, output.Len())
	}
	var got Envelope
	if err := json.Unmarshal(output.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	if got.Data["error_code"] != "api-capability-output-limit" || len(got.Items) != 0 || len(got.NextArgv) != 0 {
		t.Fatal("overflow returned a truncated contract or executable continuation", got)
	}
}

func TestAPICapabilityResponseInclusiveWireBoundary(t *testing.T) {
	for _, delta := range []int{-1, 0, 1} {
		env := NewEnvelope("ok", "fixture")
		env.Data["padding"] = ""
		var reference bytes.Buffer
		if writeEnvelope(&reference, env) != 0 {
			t.Fatal("reference serialization failed")
		}
		env.Data["padding"] = strings.Repeat("x", maxAPIPackOutputBytes-reference.Len()+delta)
		reference.Reset()
		writeEnvelope(&reference, env)
		if reference.Len() != maxAPIPackOutputBytes+delta {
			t.Fatal("invalid wire-boundary fixture")
		}
		var output bytes.Buffer
		code := writeAPICapabilityEnvelope(&output, env)
		if delta <= 0 {
			if code != 0 || !bytes.Equal(reference.Bytes(), output.Bytes()) {
				t.Fatal("valid complete envelope changed", delta, code)
			}
		} else if code != 2 || bytes.Equal(reference.Bytes(), output.Bytes()) {
			t.Fatal("one-byte overflow accepted")
		}
	}
}

func TestAPICapabilityResponsePreservesNormalBytesAndStatus(t *testing.T) {
	for _, status := range []string{"ok", "blocked", "usage-error", "error"} {
		env := NewEnvelope(status, "original response")
		env.Items = []any{map[string]any{"side_effect": "read-only", "count": json.Number("9007199254740993")}}
		env.ShowArgv = []string{"specify-runtime", "api", "show", "api.pack"}
		var expected, got bytes.Buffer
		want := writeEnvelope(&expected, env)
		code := writeAPICapabilityEnvelope(&got, env)
		if code != want || !bytes.Equal(got.Bytes(), expected.Bytes()) {
			t.Fatal("valid response or runtime argv binding changed", status, code)
		}
	}
}

func TestAPICapabilityResponseEncodingFailurePublishesNothing(t *testing.T) {
	for _, status := range []string{"ok", "error"} {
		env := NewEnvelope(status, "fixture")
		env.Data["unsupported"] = make(chan int)
		var output bytes.Buffer
		if code := writeAPICapabilityEnvelope(&output, env); code != 1 || output.Len() != 0 {
			t.Fatal("serializer error emitted partial data", status, code)
		}
	}
}

type apiBoundaryWriter func([]byte) (int, error)

func (write apiBoundaryWriter) Write(data []byte) (int, error) { return write(data) }

func TestAPICapabilityResponseWriteFailureDoesNotRetry(t *testing.T) {
	for _, short := range []bool{false, true} {
		calls := 0
		writer := apiBoundaryWriter(func(data []byte) (int, error) {
			calls++
			if short {
				return len(data) - 1, nil
			}
			return 0, io.ErrClosedPipe
		})
		if code := writeAPICapabilityEnvelope(writer, NewEnvelope("ok", "fixture")); code != 1 || calls != 1 {
			t.Fatal("failed delivery was accepted or retried", code, calls)
		}
	}
	if code := writeAPICapabilityEnvelope(nil, NewEnvelope("ok", "fixture")); code != 1 {
		t.Fatal("missing output destination accepted")
	}
}

func TestAPICapabilityResponseOverflowDoesNotMutateCaller(t *testing.T) {
	env := NewEnvelope("ok", "fixture")
	env.Items = []any{strings.Repeat("x", maxAPIPackOutputBytes)}
	env.Data["contract"] = map[string]any{"authorizes_execution": false}
	before, _ := json.Marshal(env)
	if code := writeAPICapabilityEnvelope(io.Discard, env); code != 2 {
		t.Fatal(code)
	}
	after, _ := json.Marshal(env)
	if !bytes.Equal(before, after) {
		t.Fatal("overflow changed the source contract to make it fit")
	}
}

func TestAPICapabilitySelectorReadsRealProjectFileWithoutWrites(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "requirements.json")
	for _, raw := range []string{
		`{"capabilities":["api.show","quick.context-shadow"],"note":"保留"}`,
		`{"capabilities":["missing"],"capabilities":["api.show"]}`,
	} {
		if err := os.WriteFile(file, []byte(raw), 0600); err != nil {
			t.Fatal(err)
		}
		before, _ := os.Stat(file)
		got, _, ok := apiRequestedCapabilities([]string{"--requires-json", "@requirements.json"}, root, "api ensure")
		if strings.Contains(raw, "missing") {
			if ok || got != nil {
				t.Fatal("file-backed duplicate selector was accepted")
			}
		} else if !ok || !reflect.DeepEqual(got, []string{"api.show", "quick.context-shadow"}) {
			t.Fatal("file-backed selection changed", got)
		}
		after, _ := os.Stat(file)
		data, err := os.ReadFile(file)
		if err != nil || string(data) != raw || !before.ModTime().Equal(after.ModTime()) || before.Mode() != after.Mode() {
			t.Fatal("selector read modified input evidence")
		}
	}
}

func TestAPICapabilitySelectorFileLimitUsesSharedBoundedReader(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "requirements.json")
	data := []byte(strings.Repeat("x", maxAPICapabilityInputBytes+1))
	if err := os.WriteFile(file, data, 0600); err != nil {
		t.Fatal(err)
	}
	got, env, ok := apiRequestedCapabilities([]string{"--requires-json", "@requirements.json"}, root, "api pack")
	if ok || got != nil || env.Status != "usage-error" || len(env.Blockers) == 0 || !strings.Contains(env.Blockers[0].(string), "exceeds 131072 bytes") {
		t.Fatal("the input reader did not apply the capability-specific limit", env)
	}
	after, err := os.ReadFile(file)
	if err != nil || !bytes.Equal(data, after) {
		t.Fatal("oversized input was changed")
	}
}

func TestAPICapabilitySelectorRetainsPathContainment(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "foreign.json")
	if err := os.WriteFile(outside, []byte(`{"capabilities":["api.show"]}`), 0600); err != nil {
		t.Fatal(err)
	}
	got, env, ok := apiRequestedCapabilities([]string{"--requires-json", "@" + outside}, root, "api pack")
	if ok || got != nil || env.Status != "usage-error" {
		t.Fatal("input escaped project containment")
	}
}

func TestAPICapabilitySelectorStdinUsesSameValidation(t *testing.T) {
	root := t.TempDir()
	for _, raw := range []string{
		`{"capabilities":["api.show"]}`,
		`{"capabilities":["missing"],"capabiliti\u0065s":["api.show"]}`,
		strings.Repeat("x", maxAPICapabilityInputBytes+1),
	} {
		file := filepath.Join(root, "stdin.json")
		if err := os.WriteFile(file, []byte(raw), 0600); err != nil {
			t.Fatal(err)
		}
		input, err := os.Open(file)
		if err != nil {
			t.Fatal(err)
		}
		got, ok := func() ([]string, bool) {
			original := os.Stdin
			os.Stdin = input
			defer func() { os.Stdin = original; _ = input.Close() }()
			ids, _, valid := apiRequestedCapabilities([]string{"--requires-json", "-"}, root, "api ensure")
			return ids, valid
		}()
		if strings.Contains(raw, "missing") || len(raw) > maxAPICapabilityInputBytes {
			if ok || got != nil {
				t.Fatal("invalid stdin selection was accepted")
			}
		} else if !ok || !reflect.DeepEqual(got, []string{"api.show"}) {
			t.Fatal("stdin selector changed", got)
		}
	}
}

func TestAPICapabilitySelectorStillRequiresExactlyOneSource(t *testing.T) {
	for _, args := range [][]string{nil, {"--capabilities", "api.show", "--requires-json", `{"capabilities":["api.list"]}`}} {
		got, env, ok := apiRequestedCapabilities(args, t.TempDir(), "api pack")
		if ok || got != nil || env.Status != "usage-error" {
			t.Fatal("missing or competing input sources accepted")
		}
	}
}
