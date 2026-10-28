package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"
	"time"
)

func writePlaybookMetricsDocument(t *testing.T, root string, definition PlaybookDefinition, parameters map[string]string) PlaybookDocument {
	t.Helper()
	digest, err := playbookDefinitionDigest(definition)
	if err != nil {
		t.Fatal(err)
	}
	resolved, bindings, err := resolvePlaybookDefinition(root, definition, parameters)
	if err != nil {
		t.Fatal(err)
	}
	sources, err := playbookSourceFingerprint(root, resolved)
	if err != nil {
		t.Fatal(err)
	}
	id := playbookID(definition)
	verification := DoPlaybookValidationReceipt{SessionID: "metrics-fixture", MethodID: id, DefinitionDigest: digest, Sources: sources, Outcome: "passed"}
	if len(definition.Parameters) > 0 {
		verification.Parameters = bindings
		verification.InstanceDigest, _ = playbookDefinitionDigest(resolved)
	}
	document := PlaybookDocument{SchemaVersion: playbookSchemaVersion, ID: id, Revision: 1, ContentDigest: digest, Status: "verified", Definition: definition, SourceFingerprint: sources, Verification: verification}
	path, err := playbookCanonicalPath(root, id)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o600); err != nil {
		t.Fatal(err)
	}
	return document
}

func TestPlaybookObservedRankingUsesComparableReliabilityBeforeCost(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	a, b := playbookNormalizeDefinition(definition), playbookNormalizeDefinition(definition)
	a.Variant, b.Variant = "a", "b"
	documents := []PlaybookDocument{writePlaybookMetricsDocument(t, root, a, nil), writePlaybookMetricsDocument(t, root, b, nil)}
	sort.Slice(documents, func(i, j int) bool { return documents[i].ID < documents[j].ID })
	// The lexically first method is slow. An observed tie-break can choose the
	// faster equivalent method, while default relevance remains unchanged.
	for j, document := range documents {
		for i := 0; i < 3; i++ {
			duration := int64(100)
			if j == 1 {
				duration = 10
			}
			writeDoMetricsSession(t, root, doMetricsSession(t, root, fmt.Sprintf("sample-%d-%d", j, i), document.Definition, context, "passed", duration))
		}
	}
	encodedContext, _ := json.Marshal(context)
	before := playbookSnapshotFiles(t, root)
	base, err := findPlaybooks(root, []string{"--context-json", string(encodedContext)})
	if err != nil {
		t.Fatal(err)
	}
	observed, err := findPlaybooks(root, []string{"--context-json", string(encodedContext), "--rank", "observed"})
	if err != nil {
		t.Fatal(err)
	}
	if base["items"].([]map[string]any)[0]["id"] != documents[0].ID || observed["items"].([]map[string]any)[0]["id"] != documents[1].ID {
		t.Fatalf("observed cost did not break a safe relevance tie: %#v %#v", base, observed)
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("observed ranking writes state")
	}
	failed := doMetricsSession(t, root, "sample-1-0", documents[1].Definition, context, "failed", 1)
	writeDoMetricsSession(t, root, failed)
	observed, err = findPlaybooks(root, []string{"--context-json", string(encodedContext), "--rank", "observed"})
	if err != nil {
		t.Fatal(err)
	}
	if observed["items"].([]map[string]any)[0]["id"] != documents[0].ID {
		t.Fatal("faster but less reliable method outranked reliable equivalent")
	}
}

func TestPlaybookObservedRankingTimingGapsPreserveSlotsWithoutBreakingOrder(t *testing.T) {
	profiles := map[string]playbookObservedProfile{
		"slow": {ComparisonKey: "same", Group: &playbookMetricsGroup{FirstPass: 4, FirstPassEligible: 6, SuccessfulToolMS: []int64{100, 100, 100, 100}}},
		"few":  {ComparisonKey: "same", Group: &playbookMetricsGroup{FirstPass: 2, FirstPassEligible: 3, SuccessfulToolMS: []int64{1, 1}}},
		"fast": {ComparisonKey: "same", Group: &playbookMetricsGroup{FirstPass: 4, FirstPassEligible: 6, SuccessfulToolMS: []int64{10, 10, 10, 10}}},
	}
	for _, names := range [][]string{{"slow", "few", "fast"}, {"slow", "fast", "few"}, {"few", "slow", "fast"}, {"few", "fast", "slow"}, {"fast", "slow", "few"}, {"fast", "few", "slow"}} {
		t.Run(fmt.Sprint(names), func(t *testing.T) {
			input := []playbookObservedProfile{profiles[names[0]], profiles[names[1]], profiles[names[2]]}
			order := playbookObservedOrder(input)
			lastTimed := ""
			for position, original := range order {
				if names[original] == "few" {
					if position != original {
						t.Fatalf("insufficient timing sample moved: %v => %v", names, order)
					}
					continue
				}
				if lastTimed == "slow" {
					t.Fatalf("timing gap prevented fast-before-slow preference: %v => %v", names, order)
				}
				lastTimed = names[original]
			}
		})
	}
}

func TestPlaybookObservedRankingRejectsWeakChecksDriftAndIncompleteEvidence(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	document := writePlaybookMetricsDocument(t, root, definition, nil)
	sessions := []DoSession{}
	for i := 0; i < 3; i++ {
		sessions = append(sessions, doMetricsSession(t, root, fmt.Sprintf("sample-%d", i), definition, context, "passed", 100))
	}
	good := playbookObservationProfile(root, document, "matched_prior_validation", context, nil, sessions, true)
	if good.ComparisonKey == "" {
		t.Fatalf("valid observed basis unavailable: %+v", good)
	}
	retired := sessions[0]
	retired.ID, retired.DefinitionEpoch = "replanned", 2
	retired.Attempts = append([]DoAttempt{}, retired.Attempts...)
	retired.Attempts[1].DefinitionEpoch = 2
	withReplan := playbookObservationProfile(root, document, "matched_prior_validation", context, nil, append(append([]DoSession{}, sessions...), retired), true)
	if withReplan.ComparisonKey == "" || withReplan.Group.FirstPassEligible != 3 {
		t.Fatal("an excluded mixed-epoch invocation permanently poisoned later comparable runs")
	}
	weaker := playbookNormalizeDefinition(definition)
	weaker.Checks[0].MinCases = 1
	weaker.Variant = "weak"
	weakDoc := writePlaybookMetricsDocument(t, root, weaker, nil)
	weakSessions := []DoSession{}
	for i := 0; i < 3; i++ {
		weakSessions = append(weakSessions, doMetricsSession(t, root, fmt.Sprintf("weak-%d", i), weaker, context, "passed", 1))
	}
	weak := playbookObservationProfile(root, weakDoc, "matched_prior_validation", context, nil, weakSessions, true)
	if good.ComparisonKey == weak.ComparisonKey || playbookObservedBetter(weak, good) {
		t.Fatal("weaker verification qualified as equivalent performance")
	}
	for _, test := range []struct {
		name, source string
		context      map[string]string
		sessions     []DoSession
		complete     bool
	}{
		{"catalog", "matched_prior_validation", context, sessions, false},
		{"drift", "changed", context, sessions, true},
		{"context", "matched_prior_validation", map[string]string{"os": context["os"], "arch": context["arch"]}, sessions, true},
		{"sample", "matched_prior_validation", context, sessions[:2], true},
	} {
		profile := playbookObservationProfile(root, document, test.source, test.context, nil, test.sessions, test.complete)
		if profile.ComparisonKey != "" {
			t.Fatalf("%s evidence became ranking authority: %+v", test.name, profile)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("changed source\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if profile := playbookObservationProfile(root, document, "matched_prior_validation", context, nil, sessions, true); profile.ComparisonKey != "" {
		t.Fatal("old source timing used for new source basis")
	}
}

func TestPlaybookMetricsAndRankingBindExactParameters(t *testing.T) {
	root, template, context := doMetricsFixture(t)
	defaultMode := "small"
	template.Parameters = map[string]PlaybookParameter{"mode": {Kind: "enum", Required: true, Example: "small", Default: &defaultMode, AllowedValues: []string{"small", "large"}}}
	template.Steps[0].Argv = []string{"tool", "test", "{{param:mode}}"}
	document := writePlaybookMetricsDocument(t, root, template, map[string]string{"mode": "small"})
	sessions := []DoSession{}
	for _, mode := range []string{"small", "large"} {
		resolved, bindings, err := resolvePlaybookDefinition(root, template, map[string]string{"mode": mode})
		if err != nil {
			t.Fatal(err)
		}
		for i := 0; i < 3; i++ {
			duration := int64(10)
			if mode == "large" {
				duration = 1000
			}
			session := doMetricsSession(t, root, fmt.Sprintf("%s-%d", mode, i), resolved, context, "passed", duration)
			session.TemplateDefinition, session.TemplateDigest, session.Parameters = &template, document.ContentDigest, bindings
			sessions = append(sessions, session)
			writeDoMetricsSession(t, root, session)
		}
	}
	profile := playbookObservationProfile(root, document, "matched_prior_validation", context, map[string]string{"mode": "small"}, sessions, true)
	if profile.ComparisonKey == "" || profile.Group.Sessions != 3 || playbookMetricsMedian(profile.Group.SuccessfulToolMS) != int64(20) {
		t.Fatalf("different parameter costs merged: %+v", profile)
	}
	metrics, err := playbookMetrics(root, []string{"--id", document.ID, "--parameters-json", `{"mode":"large"}`})
	if err != nil {
		t.Fatal(err)
	}
	groups := metrics["groups"].([]map[string]any)
	if len(groups) != 1 || groups[0]["sessions"] != 3 || groups[0]["median_successful_tool_ms"] != int64(1010) {
		t.Fatalf("parameter filter inaccurate: %#v", metrics)
	}
	for _, raw := range []string{`null`, `{"mode":1}`, `{"mode":"small","mode":"large"}`, `[]`} {
		if _, err := playbookMetricsParameters(raw); err == nil {
			t.Fatalf("accepted invalid parameter object %s", raw)
		}
	}
	var output bytes.Buffer
	if code := runPlaybook([]string{"metrics", "--id", document.ID, "--parameters-json", `{"mode":"small"}`, "--project-root", root, "--format", "json"}, &output); code != 0 {
		t.Fatalf("public metrics route rejected valid instance: %s", output.String())
	}
}

func TestDoRecoveryHintsDiscriminateSignalsAndOnlyOfferBoundDiagnostics(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	definition.Steps = append([]PlaybookStep{{ID: "probe", Purpose: "verify prerequisite", Cwd: ".", Argv: []string{"tool", "probe"}, Required: true, ExpectedResult: "prerequisite available", SideEffect: "read"}, {ID: "unrelated", Purpose: "inspect unrelated status", Cwd: ".", Argv: []string{"tool", "status"}, Required: false, ExpectedResult: "status visible", SideEffect: "read"}}, definition.Steps...)
	definition.Steps[2].DependsOn = []string{"probe"}
	session := doMetricsSession(t, root, "recovery", definition, context, "passed", 100)
	failed := session.Attempts[0]
	failed.ID, failed.Status, failed.Summary = "failed", "failed", "missing compiler"
	failed.Argv = []string{"old-tool", "test"}
	failed.Recovery = &DoRecovery{Reason: "restored tool", EvidenceRef: ".specify/do/sessions/recovery/evidence/repair.json"}
	probe := session.Attempts[0]
	probe.ID, probe.TargetID = "probe-pass", "probe"
	probe.Argv = []string{"tool", "probe"}
	start, _ := time.Parse(time.RFC3339Nano, session.Attempts[0].StartedAt)
	probe.StartedAt, probe.FinishedAt = start.Add(-10*time.Millisecond).Format(time.RFC3339Nano), start.Format(time.RFC3339Nano)
	unrelated := probe
	unrelated.ID, unrelated.TargetID = "unrelated-pass", "unrelated"
	session.Attempts = append([]DoAttempt{failed, probe, unrelated}, session.Attempts...)
	hints := doVerifiedRecoveryHints(session, *session.Validation)
	if len(hints) != 1 {
		t.Fatalf("missing recovery: %#v", hints)
	}
	hint := hints[0]
	preflights := hint["preflight_candidates"].([]map[string]any)
	if len(preflights) != 1 || preflights[0]["action_id"] != "probe" || preflights[0]["prevention_verified"] != false || hint["root_cause_proven"] != false {
		t.Fatalf("unbound diagnostic or prevention claim: %#v", hint)
	}
	if hint["failure_signature"] != doDigest(hint["failure_discriminator"]) {
		t.Fatal("failure signature cannot be reproduced")
	}
	changed := session
	changed.Attempts = append([]DoAttempt{}, session.Attempts...)
	changed.Attempts[0].Summary = "registry unavailable"
	changedHints := doVerifiedRecoveryHints(changed, *session.Validation)
	if changedHints[0]["failure_signature"] == hint["failure_signature"] {
		t.Fatal("different failures merged by operation alone")
	}
	one, two := doLearningSuggestions(session, *session.Validation), doLearningSuggestions(changed, *session.Validation)
	if len(one) != 1 || len(two) != 1 || one[0].recurrenceKey == two[0].recurrenceKey {
		t.Fatal("learning discarded failure discriminator")
	}
	if len(doVerifiedRecoveryHints(session, DoValidation{Status: "blocked"})) != 0 {
		t.Fatal("unverified recovery became advice")
	}
	session.Attempts[len(session.Attempts)-2].EvidenceOrigin = "human_assertion"
	if len(doVerifiedRecoveryHints(session, *session.Validation)) != 0 {
		t.Fatal("narration became verified recovery")
	}
}

func TestDoRecoveryHintsBindNativeActionAndObservation(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "native", definition, context, "passed", 100)
	before := session.Attempts[0]
	before.ID, before.Status, before.Argv = "failed", "failed", nil
	before.NativeAction = &PlaybookNativeAction{Kind: "connector", Tool: "fixture.inspect", Target: "old-target", Arguments: json.RawMessage(`{}`)}
	before.NativeObservationSHA256 = doDigest("old observation")
	session.Attempts[0].Argv = nil
	session.Attempts[0].NativeAction = &PlaybookNativeAction{Kind: "connector", Tool: "fixture.inspect", Target: "new-target", Arguments: json.RawMessage(`{}`)}
	session.Attempts = append([]DoAttempt{before}, session.Attempts...)
	hints := doVerifiedRecoveryHints(session, *session.Validation)
	if len(hints) != 1 {
		t.Fatal("native recovery disappeared")
	}
	delta := hints[0]["observed_delta"].(map[string]any)
	if delta["native_action_changed"] != true || hints[0]["failure_discriminator"].(map[string]any)["native_observation_sha256"] != before.NativeObservationSHA256 {
		t.Fatal("native actions collapsed to empty argv")
	}
	first := hints[0]["failure_signature"]
	session.Attempts[0].NativeObservationSHA256 = doDigest("different observation")
	if doVerifiedRecoveryHints(session, *session.Validation)[0]["failure_signature"] == first {
		t.Fatal("native snapshot evidence not bound")
	}
}
