package context

import (
	"bytes"
	"encoding/json"
	"errors"
	"reflect"
	"strings"
	"testing"
)

func shadowFixture() QuickShadowSource {
	return QuickShadowSource{
		ProjectIdentity: strings.Repeat("a", 64), Workspace: "2026-09-17-demo", ItemID: "Q1",
		StatePath: ".planning/quick/2026-09-17-demo/confirmation.json", StateDigest: strings.Repeat("b", 64),
		SourceRevision: strings.Repeat("c", 40),
		OwnerPacket:    json.RawMessage(`{"schema":"quick-worker-packet-v1","work_item_id":"Q1","goal":"修复登录😀","deliverable":"login works","acceptance":"integration passes","required_acceptance":"integration passes","confirmation_state":"confirmed","ready":true,"blockers":[],"write_scope":["src/login.go"],"worker_contract":{"must_result_submit_before_accept":true,"status_md_leader_owned":true},"scope":{"exclude":["billing"],"defer":["redesign"]},"ui_confirmation":{"design_binding":{"approval":"abc"},"states":["loading","error"]},"future_owner_obligation":{"exact_integer":9007199254740993,"must_not":"deploy"}}`),
	}
}

func fixedShadow(source QuickShadowSource) func() (QuickShadowSource, error) {
	return func() (QuickShadowSource, error) { return source, nil }
}

func TestQuickShadowRetainsWholeOwnerContract(t *testing.T) {
	source := shadowFixture()
	report, err := BuildQuickShadow(fixedShadow(source))
	if err != nil {
		t.Fatal(err)
	}
	_, want, _ := canonicalShadowObject(source.OwnerPacket)
	if !bytes.Equal(want, report.OwnerPacket) {
		t.Fatal("owner contract was changed")
	}
	if !bytes.Contains(report.OwnerPacket, []byte("9007199254740993")) {
		t.Fatal("large integer lost precision")
	}
	if report.AuthorizesExecution || report.LiveCodeVerified || report.Mode != "shadow-only" {
		t.Fatal("invented authority")
	}
	if len(report.Projection.ArtifactDetails) != 1 || report.Projection.StateDigest != source.StateDigest {
		t.Fatal("missing state binding")
	}
	if err := VerifyQuickShadow(report, fixedShadow(source)); err != nil {
		t.Fatal(err)
	}
	data, _ := json.Marshal(report)
	var restored QuickShadowReport
	if err := json.Unmarshal(data, &restored); err != nil {
		t.Fatal(err)
	}
	if err := VerifyQuickShadow(restored, fixedShadow(source)); err != nil {
		t.Fatal(err)
	}
}

func TestQuickShadowFailsOnEachObservableSourceChange(t *testing.T) {
	mutations := map[string]func(*QuickShadowSource){
		"project":     func(s *QuickShadowSource) { s.ProjectIdentity = strings.Repeat("d", 64) },
		"state-bytes": func(s *QuickShadowSource) { s.StateDigest = strings.Repeat("d", 64) },
		"git":         func(s *QuickShadowSource) { s.SourceRevision = strings.Repeat("d", 40) },
		"workspace": func(s *QuickShadowSource) {
			s.Workspace = "other"
			s.StatePath = ".planning/quick/other/confirmation.json"
		},
		"item": func(s *QuickShadowSource) {
			s.ItemID = "Q2"
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte(`"Q1"`), []byte(`"Q2"`))
		},
		"ui": func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.Replace(s.OwnerPacket, []byte(`"abc"`), []byte(`"new"`), 1)
		},
		"new-field": func(s *QuickShadowSource) {
			s.OwnerPacket = append([]byte(`{"new_obligation":true,`), s.OwnerPacket[1:]...)
		},
		"acceptance": func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte("integration passes"), []byte("different acceptance"))
		},
		"scope": func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte("src/login.go"), []byte("src/other.go"))
		},
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			source, changed := shadowFixture(), shadowFixture()
			mutate(&changed)
			calls := 0
			read := func() (QuickShadowSource, error) {
				calls++
				if calls == 1 {
					return source, nil
				}
				return changed, nil
			}
			report, err := BuildQuickShadow(read)
			if err == nil || !reflect.DeepEqual(report, QuickShadowReport{}) || calls != 2 {
				t.Fatal("drift did not stop atomically", err)
			}
			previous, _ := BuildQuickShadow(fixedShadow(source))
			if VerifyQuickShadow(previous, fixedShadow(changed)) == nil {
				t.Fatal("stale context reused")
			}
		})
	}
}

func TestQuickShadowRejectsMalformedAndBlockedSources(t *testing.T) {
	bad := []func(*QuickShadowSource){
		func(s *QuickShadowSource) { s.ProjectIdentity = "" },
		func(s *QuickShadowSource) { s.StateDigest = "" },
		func(s *QuickShadowSource) { s.SourceRevision = "" },
		func(s *QuickShadowSource) { s.StatePath = ".planning/quick/other/confirmation.json" },
		func(s *QuickShadowSource) { s.Workspace = "../escape" },
		func(s *QuickShadowSource) { s.ItemID = "Q0" },
		func(s *QuickShadowSource) { s.ItemID = "Q01" },
		func(s *QuickShadowSource) { s.OwnerPacket = []byte(`[]`) },
		func(s *QuickShadowSource) { s.OwnerPacket = []byte(`null`) },
		func(s *QuickShadowSource) { s.OwnerPacket = []byte(`{"a":1,"\u0061":2}`) },
		func(s *QuickShadowSource) { s.OwnerPacket = []byte(`{"a":"\ud800"}`) },
		func(s *QuickShadowSource) { s.OwnerPacket = []byte{'{', '"', 'a', '"', ':', '"', 255, '"', '}'} },
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.Replace(s.OwnerPacket, []byte(`"ready":true`), []byte(`"ready":false`), 1)
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.Replace(s.OwnerPacket, []byte(`"blockers":[]`), []byte(`"blockers":["waiting"]`), 1)
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.Replace(s.OwnerPacket, []byte(`"blockers":[]`), []byte(`"blockers":null`), 1)
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte(`"confirmed"`), []byte(`"staged"`))
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte(`"write_scope":["src/login.go"]`), []byte(`"write_scope":[]`))
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.ReplaceAll(s.OwnerPacket, []byte(`"src/login.go"`), []byte(`"../escape"`))
		},
		func(s *QuickShadowSource) {
			s.OwnerPacket = bytes.Replace(s.OwnerPacket, []byte(`"required_acceptance":"integration passes"`), []byte(`"required_acceptance":"different"`), 1)
		},
		func(s *QuickShadowSource) { s.OwnerPacket = bytes.Repeat([]byte("x"), defaultMaxBytes+1) },
	}
	for i, mutate := range bad {
		source := shadowFixture()
		mutate(&source)
		report, err := BuildQuickShadow(fixedShadow(source))
		if err == nil || !reflect.DeepEqual(report, QuickShadowReport{}) {
			t.Errorf("case %d: invalid source accepted", i)
		}
	}
}

func TestQuickShadowDoesNotRetryOrHideOwnerErrors(t *testing.T) {
	if _, err := BuildQuickShadow(nil); err == nil {
		t.Fatal("nil owner accepted")
	}
	for _, failAt := range []int{1, 2} {
		calls := 0
		want := errors.New("owner blocked")
		read := func() (QuickShadowSource, error) {
			calls++
			if calls == failAt {
				return QuickShadowSource{}, want
			}
			return shadowFixture(), nil
		}
		report, err := BuildQuickShadow(read)
		if !errors.Is(err, want) || calls != failAt || !reflect.DeepEqual(report, QuickShadowReport{}) {
			t.Fatal("owner error hidden or retried")
		}
	}
}

func TestQuickShadowRejectsReportTampering(t *testing.T) {
	mutations := map[string]func(*QuickShadowReport){
		"authorize": func(r *QuickShadowReport) { r.AuthorizesExecution = true },
		"claim":     func(r *QuickShadowReport) { r.LiveCodeVerified = true },
		"mode":      func(r *QuickShadowReport) { r.Mode = "execute" },
		"count":     func(r *QuickShadowReport) { r.OwnerFieldCount++ },
		"contract": func(r *QuickShadowReport) {
			r.OwnerPacket = bytes.Replace(r.OwnerPacket, []byte("deploy"), []byte("publish"), 1)
		},
		"digest":     func(r *QuickShadowReport) { r.SourceFingerprint = strings.Repeat("e", 64) },
		"projection": func(r *QuickShadowReport) { r.Projection.Acceptance = nil },
		"clock":      func(r *QuickShadowReport) { r.Projection.GeneratedAt = "not-time" },
		"oversized":  func(r *QuickShadowReport) { r.Projection.GeneratedAt = strings.Repeat("x", defaultMaxBytes) },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			source := shadowFixture()
			report, _ := BuildQuickShadow(fixedShadow(source))
			mutate(&report)
			if VerifyQuickShadow(report, fixedShadow(source)) == nil {
				t.Fatal("modified report accepted")
			}
		})
	}
}

func TestQuickShadowDoesNotAliasInputAndNeverTruncates(t *testing.T) {
	source := shadowFixture()
	report, err := BuildQuickShadow(fixedShadow(source))
	if err != nil {
		t.Fatal(err)
	}
	source.OwnerPacket[0] = 'x'
	if VerifyQuickShadow(report, fixedShadow(shadowFixture())) != nil {
		t.Fatal("input aliases report")
	}
	source = shadowFixture()
	source.OwnerPacket = bytes.Replace(source.OwnerPacket, []byte("修复登录😀"), []byte(strings.Repeat("g", 70000)), 1)
	failed, err := BuildQuickShadow(fixedShadow(source))
	if err == nil || !reflect.DeepEqual(failed, QuickShadowReport{}) {
		t.Fatal("oversized combined report not rejected")
	}
}
