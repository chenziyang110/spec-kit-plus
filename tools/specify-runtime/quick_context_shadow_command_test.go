package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"reflect"
	"strings"
	"testing"
)

func shadowCLIArgs() []string {
	return []string{"--workspace", "2026-09-17-shadow", "--item", "Q1"}
}

func shadowCLIEncode(w io.Writer, env Envelope) int {
	if err := json.NewEncoder(w).Encode(env); err != nil {
		return 1
	}
	return ExitCodeForStatus(env.Status)
}

func TestQuickShadowCLISelection(t *testing.T) {
	cases := []struct {
		name                  string
		args                  []string
		root, workspace, item string
	}{
		{"defaults", shadowCLIArgs(), ".", "2026-09-17-shadow", "Q1"},
		{"reordered", []string{"--format", "json", "--item", "Q12", "--workspace", "衣间集", "--project-root", "/tmp/my project"}, "/tmp/my project", "衣间集", "Q12"},
		{"windows", append(shadowCLIArgs(), "--project-root", `C:\Projects\Wardrobe`), `C:\Projects\Wardrobe`, "2026-09-17-shadow", "Q1"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			selected, err := parseQuickShadowSelection(tc.args)
			if err != nil || selected.help || selected.projectRoot != tc.root ||
				selected.workspace != tc.workspace || selected.item != tc.item {
				t.Fatalf("bad selection: %#v %v", selected, err)
			}
		})
	}
}

func TestQuickShadowCLIRejectsInputBeforeAnyOwnerRead(t *testing.T) {
	cases := map[string][]string{
		"empty":                   {},
		"missing-item":            {"--workspace", "demo"},
		"missing-workspace":       {"--item", "Q1"},
		"missing-value":           {"--workspace"},
		"missing-value-next-flag": {"--workspace", "--item", "Q1"},
		"positional":              {"demo", "Q1"},
		"json-input":              append(shadowCLIArgs(), "--input-json", "{}"),
		"output-path":             append(shadowCLIArgs(), "--output", "/tmp/report.json"),
		"execution":               append(shadowCLIArgs(), "--leader-direct"),
		"repair":                  append(shadowCLIArgs(), "--repair"),
		"repeat":                  append(shadowCLIArgs(), "--item", "Q2"),
		"repeat-format":           append(shadowCLIArgs(), "--format", "json", "--format", "json"),
		"repeat-help":             {"--help", "-h"},
		"equals":                  {"--workspace=demo", "--item=Q1"},
		"unknown-even-with-help":  {"--help", "--force"},
		"format":                  append(shadowCLIArgs(), "--format", "text"),
	}
	for _, value := range []string{"", ".", "..", "../other", "a/b", `a\b`, "C:other", " demo", "demo\n", "demo\tname", "\xff", strings.Repeat("w", 256)} {
		cases["workspace-"+fmt.Sprintf("%q", value)] = []string{"--workspace", value, "--item", "Q1"}
	}
	for _, value := range []string{"Q0", "Q01", "q1", "Q", "Q-1", "Q1/foo", "Q1.0", "Q１", " Q1", strings.Repeat("Q", 65)} {
		cases["item-"+value] = []string{"--workspace", "demo", "--item", value}
	}
	for _, value := range []string{"", "\x00", " root", strings.Repeat("r", 8193)} {
		cases["root-"+fmt.Sprintf("%q", value)] = append(shadowCLIArgs(), "--project-root", value)
	}
	for name, args := range cases {
		t.Run(name, func(t *testing.T) {
			called := false
			env := quickShadowCLIEnvelope(args, func(quickShadowSelection) (any, error) {
				called = true
				return nil, nil
			})
			if called || env.Status != "usage-error" || len(env.NextArgv) != 0 {
				t.Fatal("invalid request reached owner or advertised a mutation", env)
			}
			if _, ok := env.Data["report"]; ok {
				t.Fatal("partial report returned")
			}
		})
	}
}

func TestQuickShadowCLIHelpNeedsNoProject(t *testing.T) {
	for _, args := range [][]string{{"--help"}, {"-h"}, {"--format", "json", "--help"}, {"--help", "--project-root", "/not/a/repo"}} {
		env := quickShadowCLIEnvelope(args, func(quickShadowSelection) (any, error) {
			t.Fatal("help must not read a project")
			return nil, nil
		})
		if env.Status != "ok" || env.Data["usage"] != quickShadowCommandUsage || len(env.NextArgv) != 0 {
			t.Fatal(env)
		}
	}
}

func TestQuickShadowCLIOwnerCalledExactlyOnceAndReportPreserved(t *testing.T) {
	count := 0
	want := struct {
		Owner json.RawMessage `json:"owner_packet"`
	}{json.RawMessage(`{"future":{"integer":9007199254740993,"must_not":"deploy"}}`)}
	env := quickShadowCLIEnvelope(shadowCLIArgs(), func(s quickShadowSelection) (any, error) {
		count++
		if s.item != "Q1" || s.workspace != "2026-09-17-shadow" || s.projectRoot != "." {
			t.Fatal(s)
		}
		return want, nil
	})
	if count != 1 || !reflect.DeepEqual(env.Data["report"], want) {
		t.Fatal("report changed or owner repeated")
	}
	var out bytes.Buffer
	if code := writeQuickShadowCLIEnvelope(&out, env, shadowCLIEncode); code != 0 {
		t.Fatal(code)
	}
	if !bytes.Contains(out.Bytes(), []byte("9007199254740993")) {
		t.Fatal("owner integer lost precision")
	}
}

func TestQuickShadowCLINonAuthorityOnEveryPath(t *testing.T) {
	envelopes := []Envelope{
		quickShadowCLIEnvelope(nil, nil),
		quickShadowCLIEnvelope([]string{"--help"}, nil),
		quickShadowCLIEnvelope(shadowCLIArgs(), nil),
		quickShadowCLIEnvelope(shadowCLIArgs(), func(quickShadowSelection) (any, error) { return nil, nil }),
		quickShadowCLIEnvelope(shadowCLIArgs(), func(quickShadowSelection) (any, error) { return nil, errors.New("stale") }),
		quickShadowCLIEnvelope(shadowCLIArgs(), func(quickShadowSelection) (any, error) { return "test fixture", nil }),
	}
	for _, env := range envelopes {
		if len(env.NextArgv) != 0 || env.Data["mode"] != "shadow-only" {
			t.Fatal(env)
		}
		for _, name := range []string{"authorizes_execution", "live_code_verified", "acceptance_verified", "claim_ready"} {
			if env.Data[name] != false {
				t.Fatal("non-authority marker absent", name)
			}
		}
	}
}

func TestQuickShadowCLIBoundsErrorsWithoutRetry(t *testing.T) {
	calls := 0
	env := quickShadowCLIEnvelope(shadowCLIArgs(), func(quickShadowSelection) (any, error) {
		calls++
		return nil, errors.New(strings.Repeat("故障", 10000) + "\xff")
	})
	if calls != 1 || env.Status != "blocked" || len(env.Blockers) != 1 ||
		len([]rune(env.Blockers[0].(string))) > 800 {
		t.Fatal("unbounded diagnostic or retry")
	}
}

func TestQuickShadowCLIOutputBudgetIncludesActualEncoding(t *testing.T) {
	env := quickShadowCLIEnvelope(shadowCLIArgs(), func(quickShadowSelection) (any, error) {
		return strings.Repeat("r", quickShadowCLIOutputLimit), nil
	})
	var out bytes.Buffer
	if code := writeQuickShadowCLIEnvelope(&out, env, shadowCLIEncode); code != 10 {
		t.Fatal(code)
	}
	var decoded Envelope
	if err := json.Unmarshal(out.Bytes(), &decoded); err != nil {
		t.Fatal(err)
	}
	if len(out.Bytes()) > quickShadowCLIOutputLimit || decoded.Status != "blocked" ||
		decoded.Data["error_code"] != "quick-shadow-output-limit" ||
		decoded.Data["authorizes_execution"] != false {
		t.Fatal(decoded)
	}
	if _, ok := decoded.Data["report"]; ok {
		t.Fatal("truncated report escaped")
	}
	// Simulate the existing writer adding a bound launcher prefix/metadata.
	// The limit must be checked AFTER that encoder, not on the original report.
	env = newQuickShadowCLIEnvelope("ok", "fixture")
	added := func(w io.Writer, e Envelope) int {
		if e.Status == "ok" {
			e.Data["bound_writer_overhead"] = strings.Repeat("x", quickShadowCLIOutputLimit)
		}
		return shadowCLIEncode(w, e)
	}
	out.Reset()
	if code := writeQuickShadowCLIEnvelope(&out, env, added); code != 10 {
		t.Fatal("post-encoding overhead bypassed output limit", code)
	}
}

type shadowCLIShortWriter struct{}

func (shadowCLIShortWriter) Write(p []byte) (int, error) { return len(p) - 1, nil }

func TestQuickShadowCLIWriterFailure(t *testing.T) {
	env := newQuickShadowCLIEnvelope("ok", "fixture")
	if code := writeQuickShadowCLIEnvelope(shadowCLIShortWriter{}, env, shadowCLIEncode); code != 1 {
		t.Fatal(code)
	}
	var out bytes.Buffer
	failEncoder := func(w io.Writer, e Envelope) int {
		_, _ = io.WriteString(w, "partial invalid json")
		return 1
	}
	if code := writeQuickShadowCLIEnvelope(&out, env, failEncoder); code != 1 || out.Len() != 0 {
		t.Fatal("partial encoder output escaped")
	}
}

func TestQuickShadowCLIDiscoveryContractIsConsistentAndFresh(t *testing.T) {
	descriptor := map[string]any{"id": quickShadowCapability}
	describeQuickShadowCapability(descriptor)
	packed := map[string]any{}
	addQuickShadowPackContract(quickShadowCapability, packed)
	help := quickShadowCLIEnvelope([]string{"--help"}, nil)
	if !reflect.DeepEqual(descriptor["output_contract"], packed["output_contract"]) ||
		!reflect.DeepEqual(packed["output_contract"], help.Data["output_contract"]) ||
		descriptor["side_effect"] != "read-only" || descriptor["usage"] != help.Data["usage"] {
		t.Fatal("discovery contract drift")
	}
	other := map[string]any{"id": "quick.item-start"}
	before := map[string]any{"id": "quick.item-start"}
	addQuickShadowPackContract("quick.item-start", other)
	if !reflect.DeepEqual(other, before) {
		t.Fatal("unrelated capability changed")
	}
	packed["output_contract"].(map[string]any)["claim_ready"] = true
	if quickShadowOutputContract()["claim_ready"] != false {
		t.Fatal("returned contract aliases future calls")
	}
}

func TestQuickShadowCLIErrorStatusDoesNotLeakFailedEncoding(t *testing.T) {
	env := newQuickShadowCLIEnvelope("error", "owner unavailable")
	failEncoder := func(w io.Writer, e Envelope) int {
		_, _ = io.WriteString(w, "partial invalid json")
		return 1
	}
	var out bytes.Buffer
	if code := writeQuickShadowCLIEnvelope(&out, env, failEncoder); code != 1 || out.Len() != 0 {
		t.Fatal("error status and encoder failure share code 1; partial output escaped")
	}
}
