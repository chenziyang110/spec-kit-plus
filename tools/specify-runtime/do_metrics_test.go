package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
	"time"
)

func doMetricsFixture(t testing.TB) (string, PlaybookDefinition, map[string]string) {
	t.Helper()
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "source.txt"), []byte("metrics fixture\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	definition := playbookNormalizeDefinition(PlaybookDefinition{Operation: "test", Target: "fixture", Owner: "runtime", Variant: "baseline", TaskFamily: "fixture-verification", Title: "Verify fixture", Goal: "Verify the fixture", SourceFiles: []string{"source.txt"}, Steps: []PlaybookStep{{ID: "run", Purpose: "run fixture", Cwd: ".", Argv: []string{"tool", "test"}, Required: true, ExpectedResult: "fixture completes", SideEffect: "read"}}, Checks: []PlaybookCheck{{ID: "report", Purpose: "verify all cases", Cwd: ".", Argv: []string{}, DependsOn: []string{"run"}, Required: true, ExpectedResult: "all cases pass", Kind: "junit", ResultPath: "out/report.xml", MinCases: 4}}})
	return root, definition, map[string]string{"os": runtime.GOOS, "arch": runtime.GOARCH, "shell": "fixture-shell", "toolchain.fixture": "1"}
}

func doMetricsSession(t testing.TB, root, id string, definition PlaybookDefinition, context map[string]string, status string, duration int64) DoSession {
	t.Helper()
	digest, err := playbookDefinitionDigest(definition)
	if err != nil {
		t.Fatal(err)
	}
	sources, err := playbookSourceFingerprint(root, definition)
	if err != nil {
		t.Fatal(err)
	}
	start := time.Date(2026, 10, 1, 10, 0, 0, 0, time.UTC)
	exit := 0
	if status == "failed" {
		exit = 1
	}
	attempt := DoAttempt{ID: "run-1", TargetID: "run", Kind: "step", Status: status, DefinitionDigest: digest, SourceFingerprint: doDigest(sources), Sources: sources, AfterSources: sources, AfterSourceFingerprint: doDigest(sources), EvidenceOrigin: "agent_tool_observation", ToolCallID: "fixture-native-run", Argv: definition.Steps[0].Argv, Cwd: ".", StartedAt: start.Format(time.RFC3339Nano), FinishedAt: start.Add(time.Duration(duration) * time.Millisecond).Format(time.RFC3339Nano), ElapsedMS: duration, ExitCode: &exit}
	session := DoSession{SchemaVersion: doLegacySessionSchema, ID: id, Revision: 1, Goal: definition.Goal, Definition: definition, DefinitionDigest: digest, InitialSources: sources, BaselineJSON: `{"head_commit":"metrics-fixture","dirty_paths":[],"path_digests":{}}`, Context: context, ExecutionOutcome: status, KnowledgeStatus: "pending", Attempts: []DoAttempt{attempt}, CreatedAt: start.Format(time.RFC3339Nano), UpdatedAt: start.Add(time.Second).Format(time.RFC3339Nano)}
	if status == "passed" {
		check := attempt
		check.ID, check.TargetID, check.Kind, check.Argv = "report-1", "report", "check", []string{}
		check.StartedAt, check.FinishedAt, check.ElapsedMS = attempt.FinishedAt, start.Add(time.Duration(duration+10)*time.Millisecond).Format(time.RFC3339Nano), 10
		session.Attempts = append(session.Attempts, check)
		session.Validation = &DoValidation{Status: "passed", DefinitionDigest: digest, EvidenceDigest: doDigest(id), SourceFingerprint: doDigest(sources)}
	}
	return session
}

func TestDoMetricsRetainsFailuresAndSeparatesKnowledgeCompletion(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "recovered", definition, context, "passed", 100)
	failed := session.Attempts[0]
	failed.ID, failed.Status = "failed-run", "failed"
	one := 1
	failed.ExitCode = &one
	started, _ := time.Parse(time.RFC3339Nano, failed.StartedAt)
	failed.StartedAt, failed.FinishedAt, failed.ElapsedMS = started.Add(-50*time.Millisecond).Format(time.RFC3339Nano), started.Format(time.RFC3339Nano), 50
	session.Attempts = append([]DoAttempt{failed}, session.Attempts...)
	before := projectDoMetrics(session)
	if before.AttemptCounts["failed"] != 1 || before.AttemptCounts["passed"] != 2 || before.Retries != 1 || !before.FirstPassEligible || before.FirstPass || before.Terminal || !before.ExecutionPassed {
		t.Fatalf("recovery denominator lost: %+v", before)
	}
	if before.ExecutionMS != 150 || before.VerificationMS != 10 || before.RecoveryMS != 110 || before.ObservedSpanMS != 160 {
		t.Fatalf("observed timing incorrect: %+v", before)
	}
	session.KnowledgeStatus, session.Revision = "saved", 2
	after := projectDoMetrics(session)
	if !after.Terminal || after.Attempts != before.Attempts || after.Retries != before.Retries || after.ExecutionMS != before.ExecutionMS || after.FirstPass != before.FirstPass {
		t.Fatalf("knowledge completion invented another operation: %+v", after)
	}
}

func TestDoMetricsDisclosesResumableOutcomesAndMissingTiming(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	for _, status := range []string{"failed", "interrupted", "pending", "unexpected"} {
		session := doMetricsSession(t, root, "state", definition, context, status, 100)
		if status == "pending" {
			session.Attempts[0].Status = "running"
		}
		got := projectDoMetrics(session)
		if got.Terminal {
			t.Fatalf("%s became terminal", status)
		}
		if status == "unexpected" && (got.Disposition != "unknown" || got.Comparable) {
			t.Fatalf("unknown outcome hidden: %+v", got)
		}
		if (status == "failed" || status == "interrupted") && (!got.FirstPassEligible || got.FirstPass) {
			t.Fatalf("nonpass omitted from denominator: %+v", got)
		}
	}
	blocked := doMetricsSession(t, root, "blocked", definition, context, "failed", 100)
	blocked.Blocker = &DoBlocker{Owner: "external"}
	blocked.Attempts[0].FinishedAt = ""
	got := projectDoMetrics(blocked)
	if got.Disposition != "blocked" || got.FirstPassEligible || got.AttemptCounts["failed"] != 1 || got.MissingTiming != 1 || got.TimingComplete || got.BlockedEpisodes != 1 {
		t.Fatalf("blocked observation distorted: %+v", got)
	}
}

func TestDoMetricsMixedEpochsAreVisibleButNotComparableSamples(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "replan", definition, context, "passed", 100)
	session.DefinitionEpoch = 2
	session.Attempts[1].DefinitionEpoch = 2
	got := projectDoMetrics(session)
	if got.Historical != 1 || got.FirstPassEligible || got.Attempts != 2 || got.ExecutionMS != 100 {
		t.Fatalf("retired epoch laundered into current-method performance: %+v", got)
	}
}

func TestDoMetricsRetainedEvidenceIsNotAnotherExecution(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "retained", definition, context, "passed", 100)
	session.DefinitionEpoch = 2
	session.Attempts[1].DefinitionEpoch = 2
	session.DefinitionHistory = []DoDefinitionEpoch{
		{Epoch: 1},
		{Epoch: 2, RetainedAttempts: []DoRetainedAttempt{{TargetID: session.Attempts[0].TargetID, AttemptID: session.Attempts[0].ID, FromEpoch: 1}}},
	}
	observation := projectDoMetrics(session)
	if observation.Retained != 1 || observation.Attempts != 2 || observation.ExecutionMS != 100 || observation.Comparable {
		t.Fatalf("retained evidence was counted as new execution: %+v", observation)
	}
	card := doSessionMetrics(session)
	if card["retained_attempts"] != 1 || card["retention_policy"] != doMetricsRetentionPolicy {
		t.Fatalf("session metrics omitted retention disclosure: %#v", card)
	}
	groups := aggregatePlaybookMetrics([]DoSession{session}, playbookID(definition), nil)
	if len(groups) != 1 || groups[0].card()["retained_attempts"] != 1 || groups[0].ExecutionMS != 100 {
		t.Fatalf("aggregate duplicated retained work: %+v", groups)
	}
}

func TestDoMetricsGroupingDoesNotMergeEnvironmentOrAcceptance(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	one := doMetricsSession(t, root, "one", definition, context, "passed", 100)
	two := one
	two.ID = "two"
	two.Context = map[string]string{"os": runtime.GOOS, "arch": runtime.GOARCH, "shell": "fixture-shell", "toolchain.fixture": "2"}
	three := one
	three.ID = "three"
	three.Definition = playbookNormalizeDefinition(definition)
	three.Definition.Checks[0].MinCases = 1
	three.DefinitionDigest, _ = playbookDefinitionDigest(three.Definition)
	groups := aggregatePlaybookMetrics([]DoSession{one, two, three}, playbookID(definition), nil)
	if len(groups) != 3 {
		t.Fatalf("different environments/acceptance combined: %d", len(groups))
	}
	before := doMetricsVerificationDigest(definition)
	weaker := playbookNormalizeDefinition(definition)
	weaker.Checks[0].MinCases = 1
	if before == doMetricsVerificationDigest(weaker) {
		t.Fatal("weaker denominator appears equivalent")
	}
	closure := playbookNormalizeDefinition(definition)
	prerequisite := closure.Checks[0]
	prerequisite.ID, prerequisite.Required = "prerequisite", false
	closure.Checks[0].DependsOn = []string{"prerequisite"}
	closure.Checks = append([]PlaybookCheck{prerequisite}, closure.Checks...)
	strong := doMetricsVerificationDigest(closure)
	closure.Checks[0].MinCases = 1
	if strong == doMetricsVerificationDigest(closure) {
		t.Fatal("optional prerequisite assertion was missing from required acceptance closure")
	}
}

func writeDoMetricsSession(t testing.TB, root string, session DoSession) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(doSessionRef(session.ID)))
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(session)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o600); err != nil {
		t.Fatal(err)
	}
}

func TestDoMetricsReadProjectionHasNoWritesAndReportsCorruptSessions(t *testing.T) {
	root, definition, context := doMetricsFixture(t)
	session := doMetricsSession(t, root, "one", definition, context, "passed", 100)
	writeDoMetricsSession(t, root, session)
	path := filepath.Join(root, filepath.FromSlash(doSessionRef("broken")))
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("{broken"), 0o600); err != nil {
		t.Fatal(err)
	}
	before := playbookSnapshotFiles(t, root)
	sessions, warnings, err := readDoMetricsSessions(root)
	if err != nil || len(sessions) != 1 || len(warnings) != 1 {
		t.Fatalf("invalid sample was silently lost: %d %#v %v", len(sessions), warnings, err)
	}
	if !reflect.DeepEqual(before, playbookSnapshotFiles(t, root)) {
		t.Fatal("metrics read mutated state")
	}
}

func BenchmarkPlaybookMetricsSessionScan(b *testing.B) {
	for _, count := range []int{10, 100, 1000} {
		b.Run(fmt.Sprintf("sessions-%d", count), func(b *testing.B) {
			root, definition, context := doMetricsFixture(b)
			for i := 0; i < count; i++ {
				writeDoMetricsSession(b, root, doMetricsSession(b, root, fmt.Sprintf("sample-%04d", i), definition, context, "passed", int64(100+i)))
			}
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				sessions, warnings, err := readDoMetricsSessions(root)
				if err != nil || len(warnings) != 0 || len(sessions) != count {
					b.Fatal(err, warnings)
				}
				if len(aggregatePlaybookMetrics(sessions, playbookID(definition), context)) != 1 {
					b.Fatal("lost metrics group")
				}
			}
		})
	}
}
