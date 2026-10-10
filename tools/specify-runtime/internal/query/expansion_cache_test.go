package query

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

// The fixture exercises the real disk-backed status and expansion owners, not
// a graph build or a mock ReadStatus. SQLite-backed Compass is a separate gate.
func expansionCacheFixture(t testing.TB) (rt.Paths, ExpansionBundle) {
	t.Helper()
	paths, err := rt.ResolvePaths(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness = "ok", rt.ReadyFreshness, rt.ReadyReadiness
	status.ActiveGenerationID, status.GraphReady = "GEN-cache-test", true
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	claims := make([]ClaimSignal, 25)
	for i := range claims {
		claims[i] = ClaimSignal{ID: fmt.Sprintf("claim-%d", i), Summary: "导航不是事实证明", LiveVerificationRequired: true}
	}
	bundle := ExpansionBundle{
		ClaimRetrievalContractVersion: ClaimRetrievalContractVersion,
		ActiveGenerationID:            status.ActiveGenerationID,
		CandidateUniverseVersion:      CandidateUniverseVersion,
		QueryFingerprint:              "cafebabe0123456789abcdef",
		SectionPayloads: map[string]any{
			"related_paths":  []string{"src/检索.go", "tests/retrieval_test.go"},
			"claim_evidence": claims,
			"coverage_gaps":  []CoverageDiagnostic{},
		},
	}
	bundle.ID = expansionBundleID(bundle)
	return paths, bundle
}

func TestExpansionCacheTypedCountsSurviveRoundTrip(t *testing.T) {
	for _, count := range []int{0, 1, 3, 25} {
		claims := make([]ClaimSignal, count)
		before := expansionSectionMeta(map[string]any{"claim_evidence": claims})
		data, err := json.Marshal(map[string]any{"claim_evidence": claims})
		if err != nil {
			t.Fatal(err)
		}
		var decoded map[string]any
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatal(err)
		}
		after := expansionSectionMeta(decoded)
		if before["claim_evidence"].EstimatedItems != count || !reflect.DeepEqual(before, after) {
			t.Fatalf("typed/JSON claim count drift: count=%d before=%v after=%v", count, before, after)
		}
	}
	if got := estimatedExpansionItems([]ClaimSignal(nil)); got != 0 {
		t.Fatalf("nil claims count=%d", got)
	}
}

func TestExpansionCacheWriteAndRealExpandRoundTrip(t *testing.T) {
	paths, bundle := expansionCacheFixture(t)
	ref, err := writeExpansionBundle(paths, bundle)
	if err != nil {
		t.Fatal(err)
	}
	if ref.AvailableSections["claim_evidence"].EstimatedItems != 25 {
		t.Fatalf("wrong emitted count: %#v", ref)
	}
	got, err := Expand(paths, ExpandInput{ID: ref.ID, Section: "claim_evidence"})
	if err != nil || got.Status != expansionStatusOK {
		t.Fatalf("Expand: %#v / %v", got, err)
	}
	if !reflect.DeepEqual(ref.AvailableSections, got.AvailableSections) {
		t.Fatal("write/read metadata differs")
	}
	if rows, ok := got.Data.([]any); !ok || len(rows) != 25 {
		t.Fatalf("wrong claim payload: %#v", got.Data)
	}
	if got.EpistemicContract != NewEpistemicContract() {
		t.Fatal("live-evidence boundary changed")
	}
	path, err := expansionBundlePath(paths, ref.ID)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Count(data, []byte{'\n'}) != 1 || data[len(data)-1] != '\n' {
		t.Fatal("expansion cache is not compact newline-terminated JSON")
	}
	stamp := time.Unix(946684800, 0)
	if err := os.Chtimes(path, stamp, stamp); err != nil {
		t.Fatal(err)
	}
	before, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	after, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if !before.ModTime().Equal(after.ModTime()) || !os.SameFile(before, after) {
		t.Fatal("same expansion rewrote the cache")
	}
}

func TestExpansionCacheChangedPayloadReplacesAndGenerationGateRemains(t *testing.T) {
	paths, bundle := expansionCacheFixture(t)
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	bundle.SectionPayloads["related_paths"] = []string{"src/updated-owner.go"}
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	got, err := Expand(paths, ExpandInput{ID: bundle.ID})
	if err != nil || !reflect.DeepEqual(got.Data, []any{"src/updated-owner.go"}) {
		t.Fatalf("stale bytes reused: %#v / %v", got, err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-replaced"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	got, err = Expand(paths, ExpandInput{ID: bundle.ID})
	if err != nil || got.Status != expansionStatusStaleExpansion || got.Data != nil {
		t.Fatalf("generation rejection weakened: %#v / %v", got, err)
	}
}

func TestExpansionCacheBadInputsCannotDamageExistingBundle(t *testing.T) {
	paths, bundle := expansionCacheFixture(t)
	if _, err := writeExpansionBundle(paths, bundle); err != nil {
		t.Fatal(err)
	}
	path, err := expansionBundlePath(paths, bundle.ID)
	if err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	bad := bundle
	bad.SectionPayloads = map[string]any{"unsupported": func() {}}
	if _, err := writeExpansionBundle(paths, bad); err == nil {
		t.Fatal("unencodable payload accepted")
	}
	bad = bundle
	bad.CandidateUniverseVersion--
	if _, err := writeExpansionBundle(paths, bad); err == nil {
		t.Fatal("old contract accepted")
	}
	bad = bundle
	bad.ID = "exp-wrong-identity"
	if _, err := writeExpansionBundle(paths, bad); err == nil {
		t.Fatal("wrong identity accepted")
	}
	after, err := os.ReadFile(path)
	if err != nil || !bytes.Equal(before, after) {
		t.Fatal("invalid input damaged cache")
	}
	entries, err := os.ReadDir(filepath.Dir(path))
	if err != nil || len(entries) != 1 {
		t.Fatalf("unexpected file after invalid input: %v / %v", entries, err)
	}
}

// The frozen publication baseline includes its prior pretty encoding and direct
// WriteFile, but uses the same fixture/data/ID and metadata as the updated path.
// These are cache-publication microbenchmarks, not Compass or closeout latency.
func BenchmarkExpansionCachePublication(b *testing.B) {
	for _, mode := range []string{"reference-warm", "updated-warm", "reference-change", "updated-change"} {
		b.Run(mode, func(b *testing.B) {
			paths, bundle := expansionCacheFixture(b)
			rows := make([]map[string]any, 100)
			for i := range rows {
				rows[i] = map[string]any{"path": fmt.Sprintf("src/module-%d/file.go", i), "hints": strings.Repeat("bounded live evidence ", 10)}
			}
			bundle.SectionPayloads["raw_candidates"] = rows
			bundle.Sections = expansionSectionMeta(bundle.SectionPayloads)
			bundle.CreatedAt = deterministicExpansionCreatedAt(bundle.QueryFingerprint)
			path, err := expansionBundlePath(paths, bundle.ID)
			if err != nil {
				b.Fatal(err)
			}
			if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
				b.Fatal(err)
			}
			write := func() {
				if strings.HasPrefix(mode, "reference") {
					data, err := json.MarshalIndent(bundle, "", "  ")
					if err != nil {
						b.Fatal(err)
					}
					if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
						b.Fatal(err)
					}
				} else if _, err := writeExpansionBundle(paths, bundle); err != nil {
					b.Fatal(err)
				}
			}
			write()
			info, err := os.Stat(path)
			if err != nil {
				b.Fatal(err)
			}
			b.SetBytes(info.Size())
			b.ReportAllocs()
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				if strings.HasSuffix(mode, "change") {
					rows[0]["revision"] = i
				}
				write()
			}
			b.StopTimer()
			b.ReportMetric(float64(info.Size()), "cache-bytes")
		})
	}
}
