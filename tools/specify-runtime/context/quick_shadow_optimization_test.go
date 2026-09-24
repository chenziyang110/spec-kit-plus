package context

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

// Preserve the earlier draft algorithm as a test-only comparison, not another
// production path. Benchmarks compare assembly work, not Agent cost or latency.
func twoProjectionShadow(read func() (QuickShadowSource, error)) (QuickShadowReport, error) {
	first, err := read()
	if err != nil {
		return QuickShadowReport{}, err
	}
	report, err := projectQuickShadow(first)
	if err != nil {
		return QuickShadowReport{}, err
	}
	second, err := read()
	if err != nil {
		return QuickShadowReport{}, err
	}
	current, err := projectQuickShadow(second)
	if err != nil {
		return QuickShadowReport{}, err
	}
	if current.SourceFingerprint != report.SourceFingerprint {
		return QuickShadowReport{}, fmt.Errorf("source changed")
	}
	return report, nil
}

func TestQuickShadowSingleProjectionMatchesTwoProjectionReference(t *testing.T) {
	for _, size := range []int{0, 4096, 32768} {
		source := shadowFixture()
		source.OwnerPacket = bytes.Replace(source.OwnerPacket, []byte("login works"), []byte(strings.Repeat("x", size)), 1)
		one, err := BuildQuickShadow(fixedShadow(source))
		if err != nil {
			t.Fatal(err)
		}
		two, err := twoProjectionShadow(fixedShadow(source))
		if err != nil {
			t.Fatal(err)
		}
		one.Projection.GeneratedAt, two.Projection.GeneratedAt = "", ""
		if !reflect.DeepEqual(one, two) {
			t.Fatal("single projection changed a returned field")
		}
	}
}

func TestQuickShadowRereadCannotExploitLossyIdentity(t *testing.T) {
	first := shadowFixture()
	first.Workspace = "project-\ufffd"
	first.StatePath = ".planning/quick/" + first.Workspace + "/confirmation.json"
	calls := 0
	report, err := BuildQuickShadow(func() (QuickShadowSource, error) {
		calls++
		if calls == 1 {
			return first, nil
		}
		second := first
		second.Workspace = "project-\xff"
		second.StatePath = ".planning/quick/" + second.Workspace + "/confirmation.json"
		return second, nil
	})
	if err == nil || !reflect.DeepEqual(report, QuickShadowReport{}) {
		t.Fatal("reread accepted a lossy identity collision")
	}
}

func TestQuickShadowCopiesOwnerBeforeReread(t *testing.T) {
	source := shadowFixture()
	calls := 0
	report, err := BuildQuickShadow(func() (QuickShadowSource, error) {
		calls++
		if calls == 2 {
			copy(source.OwnerPacket, bytes.Replace(source.OwnerPacket, []byte("deploy"), []byte("delete"), 1))
		}
		return source, nil
	})
	if err == nil || !reflect.DeepEqual(report, QuickShadowReport{}) {
		t.Fatal("mutable callback storage rewrote the first snapshot")
	}
}

func BenchmarkQuickShadowAssembly(b *testing.B) {
	for _, size := range []int{0, 32768} {
		source := shadowFixture()
		source.OwnerPacket = bytes.Replace(source.OwnerPacket, []byte("login works"), []byte(strings.Repeat("x", size)), 1)
		for _, mode := range []string{"two-projection", "one-projection"} {
			b.Run(fmt.Sprintf("%d/%s", size, mode), func(b *testing.B) {
				build := BuildQuickShadow
				if mode == "two-projection" {
					build = twoProjectionShadow
				}
				b.ReportAllocs()
				for i := 0; i < b.N; i++ {
					if _, err := build(fixedShadow(source)); err != nil {
						b.Fatal(err)
					}
				}
			})
		}
	}
}

func FuzzQuickShadowNeverReturnsPartial(f *testing.F) {
	for _, raw := range [][]byte{shadowFixture().OwnerPacket, []byte("null"), []byte(`{"a":"\ud800"}`)} {
		f.Add(raw)
	}
	f.Fuzz(func(t *testing.T, raw []byte) {
		source := shadowFixture()
		source.OwnerPacket = raw
		report, err := BuildQuickShadow(fixedShadow(source))
		if err != nil {
			if !reflect.DeepEqual(report, QuickShadowReport{}) {
				t.Fatal("partial report escaped failure")
			}
			return
		}
		if report.AuthorizesExecution || report.LiveCodeVerified {
			t.Fatal("assembly granted authority")
		}
		encoded, err := json.Marshal(report)
		if err != nil || len(encoded) > defaultMaxBytes {
			t.Fatal("invalid or unbounded report")
		}
		if err := VerifyQuickShadow(report, fixedShadow(source)); err != nil {
			t.Fatal(err)
		}
	})
}

func TestQuickShadowVerificationRejectsLossyReportIdentity(t *testing.T) {
	source := shadowFixture()
	source.Workspace = "project-\ufffd"
	source.StatePath = ".planning/quick/" + source.Workspace + "/confirmation.json"
	report, err := BuildQuickShadow(fixedShadow(source))
	if err != nil {
		t.Fatal(err)
	}
	report.Workspace = "project-\xff"
	if VerifyQuickShadow(report, fixedShadow(source)) == nil {
		t.Fatal("invalid report identity normalized into the genuine workspace")
	}
}
