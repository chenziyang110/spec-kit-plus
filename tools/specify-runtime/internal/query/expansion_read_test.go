package query

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestExpansionRawItemCountMatchesGenericDecode(t *testing.T) {
	fixtures := []string{
		`null`, `[]`, `[ ]`, `{}`, `true`, `false`, `0`, `-0.0`, `1.7976931348623157e308`,
		`1e-1000`, `"comma, bracket] and quote\""`, `[[1,2],{"key":[3,4]},null]`,
		`["\\\"", "[,{,]", "中文\u0000", [], {}, 1e2, -0.2]`,
		`{"a,b":"not an array","n":123,"nested":[1,2,3]}`,
		" \n\t[ \n true , false \t ] \r", `1e309`, `[-1e309]`,
		`{"deep":[[[1e1000]]]}`, strings.Repeat("9", 309), `"1e9999"`,
	}
	for _, raw := range fixtures {
		t.Run(raw[:min(len(raw), 60)], func(t *testing.T) {
			assertExpansionRawCount(t, []byte(raw))
		})
	}
}

func assertExpansionRawCount(t testing.TB, raw []byte) {
	t.Helper()
	// The scanner's production caller always validates JSON first.
	if !json.Valid(raw) {
		return
	}
	var eager any
	err := json.Unmarshal(raw, &eager)
	got, gotErr := expansionRawItemCount(raw)
	if (gotErr != nil) != (err != nil) {
		t.Fatalf("numeric rejection differs for %q: eager=%v projected=%v", raw, err, gotErr)
	}
	if err == nil && got != estimatedExpansionItems(eager) {
		t.Fatalf("section count changed for %q: eager=%d projected=%d", raw, estimatedExpansionItems(eager), got)
	}
}

func FuzzExpansionRawItemCount(f *testing.F) {
	for _, seed := range []string{`null`, `[]`, `["[,]",{"a":[1,2]},3]`, `{"x":-1e999}`, `"\\\""`, `1.7976931348623157e308`} {
		f.Add([]byte(seed))
	}
	f.Fuzz(func(t *testing.T, raw []byte) {
		if len(raw) > 65536 {
			return
		}
		assertExpansionRawCount(t, raw)
	})
}

func TestExpansionProjectedReadMatchesEagerPacket(t *testing.T) {
	paths, bundle := expansionCacheFixture(t)
	bundle.SectionPayloads["raw_candidates"] = []any{
		map[string]any{"id": "node,one", "paths": []string{"src/a.go", "test/[b].go"}},
		map[string]any{"count": 42.25, "attrs": map[string]any{"quoted": "\\\"[},]"}},
	}
	bundle.SectionPayloads["null"] = nil
	bundle.SectionPayloads["scalar"] = "bounded, one [item]"
	bundle.SectionPayloads["object"] = map[string]any{"a": []int{1, 2}, "b": true}
	bundle.SectionPayloads[" "] = []int{1, 2, 3}
	bundlePath, err := expansionBundlePath(paths, bundle.ID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	good, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, section := range []string{"", "related_paths", "raw_candidates", "coverage_gaps", "claim_evidence", "null", "scalar", "object", "missing", " "} {
		t.Run(section, func(t *testing.T) {
			assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID, Section: section})
		})
	}
	// Repeated top-level map fields merge the same way as encoding/json did
	// for the previous reader; duplicate section names retain the last value.
	duplicate := strings.TrimSuffix(strings.TrimSpace(string(good)), "}") + `,"section_payloads":{"extra":[1,2],"related_paths":["last.go"]}}`
	if err := os.WriteFile(bundlePath, []byte(duplicate), 0o600); err != nil {
		t.Fatal(err)
	}
	assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID})
	assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID, Section: "extra"})

	for _, mutation := range []struct{ from, to string }{
		{`"claim_retrieval_contract_version":2`, `"claim_retrieval_contract_version":999`},
		{`"candidate_universe_version":2`, `"candidate_universe_version":999`},
		{`"active_generation_id":"GEN-cache-test"`, `"active_generation_id":"GEN-other"`},
		{bundle.ID, "exp-wrong"},
		{`"scalar":"bounded, one [item]"`, `"scalar":1e999`},
		{`"scalar":"bounded, one [item]"`, `"scalar":[1,]`},
	} {
		changed := strings.Replace(string(good), mutation.from, mutation.to, 1)
		if changed == string(good) {
			t.Fatalf("mutation missed: %s", mutation.from)
		}
		if err := os.WriteFile(bundlePath, []byte(changed), 0o600); err != nil {
			t.Fatal(err)
		}
		assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID})
	}
	if err := os.WriteFile(bundlePath, good, 0o600); err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-new"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID})
	assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: "exp-missing"})
	assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: "../../outside"})
}

// encoding/json rejects a numeric overflow even when a later duplicate map
// key, field or null value would replace it. Deferred hydration must not hide
// that first invalid value merely because it is outside the selected section.
func TestExpansionProjectedReadRejectsShadowedOverflow(t *testing.T) {
	paths, bundle := expansionCacheFixture(t)
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	target, err := expansionBundlePath(paths, bundle.ID)
	if err != nil {
		t.Fatal(err)
	}
	good, err := os.ReadFile(target)
	if err != nil {
		t.Fatal(err)
	}
	prefix := strings.TrimSuffix(strings.TrimSpace(string(good)), "}")
	for _, suffix := range []string{
		`,"section_payloads":{"raw_candidates":1e999,"raw_candidates":[]}}`,
		`,"section_payloads":{"raw_candidates":{"nested":1e999}},"section_payloads":{"raw_candidates":[]}}`,
		`,"section_payloads":{"raw_candidates":-1e999},"section_payloads":null}`,
		`,"section_payloads":{" ":1e999," ":null}}`,
	} {
		t.Run(suffix, func(t *testing.T) {
			if err := os.WriteFile(target, []byte(prefix+suffix), 0o600); err != nil {
				t.Fatal(err)
			}
			if _, err := expansionEagerReadReference(paths, ExpandInput{ID: bundle.ID}); err == nil {
				t.Fatal("negative fixture must be rejected by eager reference")
			}
			assertExpansionPacketEquivalent(t, paths, ExpandInput{ID: bundle.ID})
		})
	}
}

func assertExpansionPacketEquivalent(t testing.TB, paths rt.Paths, input ExpandInput) {
	t.Helper()
	want, wantErr := expansionEagerReadReference(paths, input)
	got, gotErr := Expand(paths, input)
	if (gotErr != nil) != (wantErr != nil) {
		t.Fatalf("error behavior changed: want=%v got=%v", wantErr, gotErr)
	}
	if wantErr == nil && !reflect.DeepEqual(got, want) {
		t.Fatalf("wire packet changed:\nwant=%#v\ngot=%#v", want, got)
	}
}

var expansionReadSink ExpandPayload

func BenchmarkExpansionSelectedSectionRead(b *testing.B) {
	for _, count := range []int{10, 3000} {
		paths, bundle := expansionCacheFixture(b)
		rows := make([]any, count)
		for i := range rows {
			rows[i] = map[string]any{
				"id": fmt.Sprintf("node-%d", i), "title": "unrequested graph candidate",
				"paths":        []string{"src/owner.go", "tests/owner_test.go"},
				"evidence_ids": []string{"evidence-1", "evidence-2"},
				"attrs":        map[string]any{"reason": strings.Repeat("navigation ", 10), "confidence": "medium", "score": i},
			}
		}
		bundle.SectionPayloads["raw_candidates"] = rows
		if _, err := writeExpansionBundle(paths, bundle); err != nil {
			b.Fatal(err)
		}
		input := ExpandInput{ID: bundle.ID, Section: "related_paths"}
		assertExpansionPacketEquivalent(b, paths, input)
		for _, mode := range []string{"eager", "selected_section"} {
			b.Run(fmt.Sprintf("candidates_%d/%s", count, mode), func(b *testing.B) {
				b.ReportAllocs()
				read := Expand
				if mode == "eager" {
					read = expansionEagerReadReference
				}
				for i := 0; i < b.N; i++ {
					var err error
					expansionReadSink, err = read(paths, input)
					if err != nil || expansionReadSink.Status != expansionStatusOK {
						b.Fatalf("read: %v %s", err, expansionReadSink.Status)
					}
				}
			})
		}
	}
}

// This differential check exercises complete envelope decoding independently
// of filesystem state, including duplicate fields and unusual JSON scalars.
func FuzzExpansionReadEnvelope(f *testing.F) {
	for _, seed := range []string{
		`{}`, `null`, `{"section_payloads":null}`,
		`{"section_payloads":{"a":[1,2],"b":{"v":"[,]"}," ":null}}`,
		`{"section_payloads":{"x":1e999,"x":[]}}`,
		`{"section_payloads":{"x":[1]},"section_payloads":null}`,
		`{"Section_Payloads":{"x":[true]},"sections":{"x":{"estimated_items":1}}}`,
	} {
		f.Add([]byte(seed))
	}
	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) > 65536 {
			return
		}
		var eager ExpansionBundle
		eagerErr := json.Unmarshal(data, &eager)
		got, sections, meta, gotErr := decodeExpansionReadBundle(data)
		if (eagerErr != nil) != (gotErr != nil) {
			t.Fatalf("envelope rejection differs: eager=%v projected=%v input=%q", eagerErr, gotErr, data)
		}
		if eagerErr != nil {
			return
		}
		if !reflect.DeepEqual(meta, expansionSectionMeta(eager.SectionPayloads)) {
			t.Fatalf("metadata differs for %q", data)
		}
		if len(sections) != len(eager.SectionPayloads) {
			t.Fatalf("sections differ for %q", data)
		}
		for key, raw := range sections {
			var value any
			if err := json.Unmarshal(raw, &value); err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(value, eager.SectionPayloads[key]) {
				t.Fatalf("section %q differs", key)
			}
		}
		eager.SectionPayloads = nil
		if !reflect.DeepEqual(got, eager) {
			t.Fatalf("envelope differs for %q", data)
		}
	})
}

// Bulk inspection deliberately preserves the original eager read path.
func BenchmarkExpansionBulkSectionRead(b *testing.B) {
	paths, bundle := expansionCacheFixture(b)
	rows := make([]any, 3000)
	for i := range rows {
		rows[i] = map[string]any{"id": fmt.Sprintf("node-%d", i), "paths": []string{"src/owner.go", "test/owner_test.go"}, "hints": strings.Repeat("navigation ", 10), "score": i}
	}
	bundle.SectionPayloads["raw_candidates"] = rows
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		b.Fatal(err)
	}
	input := ExpandInput{ID: bundle.ID, Section: "raw_candidates"}
	assertExpansionPacketEquivalent(b, paths, input)
	for _, mode := range []string{"eager", "bulk_path"} {
		b.Run(mode, func(b *testing.B) {
			read := Expand
			if mode == "eager" {
				read = expansionEagerReadReference
			}
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				var err error
				expansionReadSink, err = read(paths, input)
				if err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}
