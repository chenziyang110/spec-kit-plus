package query

import (
	"bytes"
	"encoding/json"
	"os"
	"reflect"
	"testing"
	"time"
)

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
}

// Exercise the current snapshot-bound Compass owner instead of the legacy
// status-only fixture. Compact encoding must preserve immutable IDs, real
// section reads, paging and the no-rewrite guarantee for repeated publication.
func TestExpansionCompactPublicationPreservesCurrentSnapshotContract(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	input := CompassInput{Intent: "debug", Query: "runtimeOverride"}
	before, err := Compass(paths, input)
	if err != nil || before.ExpansionRef == nil {
		t.Fatalf("Compass: %#v / %v", before, err)
	}
	path, err := expansionBundlePath(paths, before.ExpansionRef.ID)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(data) == 0 || bytes.Count(data, []byte{'\n'}) != 1 || data[len(data)-1] != '\n' {
		t.Fatal("expansion is not compact newline-terminated JSON")
	}
	for _, section := range []string{"related_paths", "raw_candidates", "claim_evidence"} {
		got, err := Expand(paths, ExpandInput{ID: before.ExpansionRef.ID, Section: section})
		if err != nil || got.Status != expansionStatusOK || got.Data == nil {
			t.Fatalf("Expand %s: %#v / %v", section, got, err)
		}
		if !reflect.DeepEqual(before.ExpansionRef.AvailableSections, got.AvailableSections) {
			t.Fatal("write/read metadata differs")
		}
	}
	stamp := time.Unix(946684800, 0)
	if err := os.Chtimes(path, stamp, stamp); err != nil {
		t.Fatal(err)
	}
	initial, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	after, err := Compass(paths, input)
	if err != nil || after.ExpansionRef == nil || after.ExpansionRef.ID != before.ExpansionRef.ID {
		t.Fatalf("repeated Compass changed identity: %#v / %v", after, err)
	}
	final, err := os.Stat(path)
	if err != nil || !initial.ModTime().Equal(final.ModTime()) || !os.SameFile(initial, final) {
		t.Fatalf("identical expansion was rewritten: %v", err)
	}
}
