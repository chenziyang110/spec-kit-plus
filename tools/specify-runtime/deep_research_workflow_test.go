package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDeepResearchWorkflowPublishesVerifiedPlanBinding(t *testing.T) {
	fixture := newDeepResearchFixture(t, "required")

	init := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "init",
		"--feature-dir", fixture.featureRel,
		"--mode", "repo-only",
		"--leader-id", "leader-1",
	})
	if init.Data["phase"] != "scoped" || init.Data["claim_status"] != "pending" {
		t.Fatalf("init state = %#v", init.Data)
	}
	if digest := strings.TrimSpace(asString(init.Data["source_spec_sha256"])); len(digest) != 64 {
		t.Fatalf("source_spec_sha256 = %q", digest)
	}
	for _, name := range []string{"state.json", "track-manifest.json"} {
		if _, err := os.Stat(filepath.Join(fixture.featureDir, "research", name)); err != nil {
			t.Fatalf("missing runtime artifact %s: %v", name, err)
		}
	}

	prepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, init),
		"--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, false)),
	})
	if prepared.Data["phase"] != "researching" {
		t.Fatalf("track-prepare phase = %#v", prepared.Data["phase"])
	}

	rejectedLeader, rejectedExit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "track-lease",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, prepared),
		"--worker-id", "leader-1",
	})
	if rejectedExit == 0 || rejectedLeader.Status != "blocked" {
		t.Fatalf("leader lease exit=%d env=%#v", rejectedExit, rejectedLeader)
	}

	lease := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-lease",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, prepared),
		"--worker-id", "researcher-1",
	})
	attemptID := strings.TrimSpace(asString(lease.Data["attempt_id"]))
	if attemptID == "" || lease.Data["result_protocol"] != "deep_research_track_result.v1" {
		t.Fatalf("lease packet = %#v", lease.Data)
	}

	submitted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-submit",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, lease),
		"--track-id", "TRK-001",
		"--attempt-id", attemptID,
		"--result-json", mustDeepResearchJSON(t, deepResearchTrackResult(fixture, nil, nil)),
	})
	evidencePath := filepath.Join(fixture.featureDir, "research-evidence", "EVD-001.json")
	if _, err := os.Stat(evidencePath); err != nil {
		t.Fatalf("track-submit did not materialize canonical evidence: %v", err)
	}

	accepted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-accept",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, submitted),
		"--track-id", "TRK-001",
		"--attempt-id", attemptID,
		"--leader-id", "leader-1",
	})

	synthesized := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "synthesize",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, accepted),
		"--leader-id", "leader-1",
		"--input-json", mustDeepResearchJSON(t, deepResearchSynthesis(nil)),
	})
	markdown, err := os.ReadFile(filepath.Join(fixture.featureDir, "deep-research.md"))
	if err != nil {
		t.Fatal(err)
	}
	for _, required := range []string{
		"**Status**: Complete",
		"## Feasibility Decision",
		"## Planning Handoff",
		"PH-001",
		"research-evidence/EVD-001.json",
		"## Next Command",
	} {
		if !strings.Contains(string(markdown), required) {
			t.Fatalf("derived deep-research.md missing %q:\n%s", required, markdown)
		}
	}

	auditPrepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "audit-prepare",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, synthesized),
	})
	auditRequestSHA := strings.TrimSpace(asString(auditPrepared.Data["audit_request_sha256"]))
	if len(auditRequestSHA) != 64 {
		t.Fatalf("audit_request_sha256 = %q", auditRequestSHA)
	}

	auditAccepted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "audit-accept",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, auditPrepared),
		"--auditor-id", "auditor-1",
		"--input-json", mustDeepResearchJSON(t, deepResearchAudit(auditRequestSHA)),
	})
	validated := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "validate",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, auditAccepted),
	})
	if validated.Data["claim_status"] != "complete" {
		t.Fatalf("claim_status = %#v", validated.Data["claim_status"])
	}

	published := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "publish",
		"--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, validated),
	})
	handoffRef := strings.TrimSpace(asString(published.Data["handoff_ref"]))
	handoffSHA := strings.TrimSpace(asString(published.Data["handoff_sha256"]))
	if handoffRef != fixture.featureRel+"/research/handoff-to-plan.json" || len(handoffSHA) != 64 {
		t.Fatalf("published binding = %#v", published.Data)
	}

	verified := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "verify-handoff",
		"--feature-dir", fixture.featureRel,
		"--handoff-ref", handoffRef,
		"--expected-sha256", handoffSHA,
	})
	if verified.Data["claim_status"] != "complete" {
		t.Fatalf("verified binding = %#v", verified.Data)
	}

	writeReadyPlanContract(t, fixture, published)
	for _, artifact := range []struct {
		name    string
		content string
	}{
		{"plan.md", "# Plan\n"},
		{"workflow-state.md", "# Workflow State\n"},
	} {
		if err := os.WriteFile(filepath.Join(fixture.featureDir, artifact.name), []byte(artifact.content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	planGate := validateHookArtifacts([]string{
		"--command", "plan",
		"--feature-dir", fixture.featureRel,
		"--project-root", fixture.projectRoot,
	})
	if planGate.Status != "ok" {
		t.Fatalf("verified Plan binding was rejected: %#v", planGate)
	}

	evidence, err := os.ReadFile(evidencePath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(evidencePath, append(evidence, byte(' ')), 0o644); err != nil {
		t.Fatal(err)
	}
	tampered, tamperedExit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "verify-handoff",
		"--feature-dir", fixture.featureRel,
		"--handoff-ref", handoffRef,
		"--expected-sha256", handoffSHA,
	})
	if tamperedExit == 0 || tampered.Status != "blocked" {
		t.Fatalf("tampered evidence passed: exit=%d env=%#v", tamperedExit, tampered)
	}
	if planGate := validateHookArtifacts([]string{
		"--command", "plan",
		"--feature-dir", fixture.featureRel,
		"--project-root", fixture.projectRoot,
	}); planGate.Status != "blocked" {
		t.Fatalf("Plan accepted a tampered research binding: %#v", planGate)
	}
}

func TestDeepResearchWorkflowRejectsStaleSpecAndStaleRevision(t *testing.T) {
	fixture := newDeepResearchFixture(t, "required")
	init := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "init", "--feature-dir", fixture.featureRel,
		"--mode", "external-enabled", "--leader-id", "leader-1",
	})

	staleRevision, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
		"--expected-revision", "999", "--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, false)),
	})
	if exit == 0 || staleRevision.Status != "blocked" {
		t.Fatalf("stale CAS passed: exit=%d env=%#v", exit, staleRevision)
	}

	specRaw, err := os.ReadFile(fixture.specPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(fixture.specPath, append(specRaw, byte('\n')), 0o644); err != nil {
		t.Fatal(err)
	}
	status, statusExit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "status", "--feature-dir", fixture.featureRel,
	})
	if statusExit == 0 || status.Status != "blocked" || status.Data["source_freshness"] != "stale" {
		t.Fatalf("stale source status exit=%d env=%#v", statusExit, status)
	}
	blocked, blockedExit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, init),
		"--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, false)),
	})
	if blockedExit == 0 || blocked.Status != "blocked" {
		t.Fatalf("stale source mutation passed: exit=%d env=%#v", blockedExit, blocked)
	}
}

func TestDeepResearchWorkflowRequeuesLeaderRejectedTrack(t *testing.T) {
	fixture := newDeepResearchFixture(t, "required")
	initialized := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "init", "--feature-dir", fixture.featureRel,
		"--mode", "repo-only", "--leader-id", "leader-1",
	})
	prepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, initialized),
		"--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, false)),
	})
	firstLease := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-lease", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, prepared),
		"--worker-id", "researcher-1",
	})
	firstAttempt := asString(firstLease.Data["attempt_id"])
	submitted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-submit", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, firstLease),
		"--track-id", "TRK-001", "--attempt-id", firstAttempt,
		"--result-json", mustDeepResearchJSON(t, deepResearchTrackResult(fixture, []any{}, []any{})),
	})
	rejected := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-reject", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, submitted),
		"--track-id", "TRK-001", "--attempt-id", firstAttempt,
		"--leader-id", "leader-1", "--reason", "The finding does not address the assigned rollback question.",
	})
	manifest, err := deepResearchReadManifest(filepath.Join(fixture.featureDir, "research"))
	if err != nil {
		t.Fatalf("read rejected track manifest: %v", err)
	}
	track := manifest.Tracks[0]
	if track.State != "pending" || track.WorkerID != "" || track.AttemptID != "" || track.ResultRef != "" || track.ResultSHA256 != "" {
		t.Fatalf("rejected track was not safely requeued: %#v", track)
	}
	if track.AttemptNumber != 1 || track.LastYieldReason == "" {
		t.Fatalf("rejected track lost retry history: %#v", track)
	}
	if len(track.Rejections) != 1 || track.Rejections[0].AttemptID != firstAttempt || track.Rejections[0].Reason == "" {
		t.Fatalf("rejected track did not preserve a structured rejection record: %#v", track.Rejections)
	}
	rejectionRaw, err := deepResearchReadRegularProjectFile(fixture.projectRoot, track.Rejections[0].RejectionRef)
	if err != nil || deepResearchDigest(rejectionRaw) != track.Rejections[0].RejectionSHA256 {
		t.Fatalf("rejection snapshot is unavailable or stale: err=%v rejection=%#v", err, track.Rejections[0])
	}
	secondLease := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-lease", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, rejected),
		"--worker-id", "researcher-2",
	})
	if asString(secondLease.Data["attempt_id"]) == firstAttempt {
		t.Fatalf("rejected track reused stale attempt id %s", firstAttempt)
	}
	secondAttempt := asString(secondLease.Data["attempt_id"])
	secondSubmitted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-submit", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, secondLease),
		"--track-id", "TRK-001", "--attempt-id", secondAttempt,
		"--result-json", mustDeepResearchJSON(t, deepResearchTrackResult(fixture, []any{}, []any{})),
	})
	blocked, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "track-reject", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, secondSubmitted),
		"--track-id", "TRK-001", "--attempt-id", secondAttempt,
		"--leader-id", "leader-1", "--reason", "The retry still omits the rollback proof.",
	})
	if exit != 10 || blocked.Status != "blocked" || blocked.Data["claim_status"] != "blocked" {
		t.Fatalf("second rejection did not exhaust the bounded retry: exit=%d env=%#v", exit, blocked)
	}
}

func TestDeepResearchWorkflowExternalBlockedModeRejectsExternalEvidence(t *testing.T) {
	fixture := newDeepResearchFixture(t, "required")
	initialized := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "init", "--feature-dir", fixture.featureRel,
		"--mode", "external-blocked", "--leader-id", "leader-1",
	})
	tracks := deepResearchTracksInput(fixture, false)
	track := tracks["tracks"].([]any)[0].(map[string]any)
	track["source_classes"] = []any{"primary_external"}
	prepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, initialized),
		"--input-json", mustDeepResearchJSON(t, tracks),
	})
	lease := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-lease", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, prepared),
		"--worker-id", "researcher-1",
	})
	result := deepResearchTrackResult(fixture, []any{}, []any{})
	evidence := result["evidence"].([]any)[0].(map[string]any)
	evidence["source_type"] = "primary_external"
	evidence["source_ref"] = "https://example.com/primary-docs"
	evidence["source_title"] = "Primary API documentation"
	evidence["retrieved_on"] = "2026-08-17"
	evidence["quality"] = map[string]any{
		"authority":    "primary",
		"independence": "independent",
		"recency":      "current",
		"limitations":  []any{},
	}
	env, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "track-submit", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, lease),
		"--track-id", "TRK-001", "--attempt-id", asString(lease.Data["attempt_id"]),
		"--result-json", mustDeepResearchJSON(t, result),
	})
	if exit == 0 || env.Status != "invalid" || !strings.Contains(strings.Join(deepResearchStringSlice(env.Blockers), " "), "external-blocked") {
		t.Fatalf("external-blocked mode accepted external evidence: exit=%d env=%#v", exit, env)
	}
}

func TestDeepResearchNextSubcommandResumesCurrentTrackState(t *testing.T) {
	state := deepResearchState{Status: "active", Phase: "researching"}
	tests := []struct {
		name       string
		trackState string
		want       string
	}{
		{name: "pending work can be leased", trackState: "pending", want: "track-lease"},
		{name: "leased work must be submitted", trackState: "leased", want: "track-submit"},
		{name: "submitted work must be reviewed", trackState: "submitted", want: "track-accept"},
		{name: "submitted blocker must be reviewed", trackState: "submitted-blocked", want: "track-accept"},
		{name: "accepted work can be synthesized", trackState: "accepted", want: "synthesize"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			manifest := deepResearchTrackManifest{Tracks: []deepResearchTrack{{State: test.trackState}}}
			if got := deepResearchNextSubcommand(state, manifest); got != test.want {
				t.Fatalf("deepResearchNextSubcommand(%s) = %q, want %q", test.trackState, got, test.want)
			}
		})
	}
}

func TestDeepResearchWorkflowEnforcesClosureContradictionsAndSpikes(t *testing.T) {
	t.Run("missing capability disposition", func(t *testing.T) {
		fixture := newDeepResearchFixture(t, "required")
		accepted := prepareAcceptedDeepResearchTrack(t, fixture, false, nil, nil)
		invalid := deepResearchSynthesis(nil)
		invalid["capability_dispositions"] = []any{}
		env, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
			"deep-research", "synthesize", "--feature-dir", fixture.featureRel,
			"--expected-revision", deepResearchRevisionArg(t, accepted),
			"--leader-id", "leader-1", "--input-json", mustDeepResearchJSON(t, invalid),
		})
		if exit == 0 || env.Status != "invalid" {
			t.Fatalf("missing CAP closure passed: exit=%d env=%#v", exit, env)
		}
	})

	t.Run("unresolved contradiction", func(t *testing.T) {
		fixture := newDeepResearchFixture(t, "required")
		contradictions := []any{map[string]any{
			"contradiction_id": "CON-001",
			"summary":          "Repository and external guidance disagree.",
			"evidence_refs":    []any{"EVD-001"},
		}}
		accepted := prepareAcceptedDeepResearchTrack(t, fixture, false, contradictions, nil)
		env, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
			"deep-research", "synthesize", "--feature-dir", fixture.featureRel,
			"--expected-revision", deepResearchRevisionArg(t, accepted),
			"--leader-id", "leader-1", "--input-json", mustDeepResearchJSON(t, deepResearchSynthesis(nil)),
		})
		if exit == 0 || env.Status != "invalid" {
			t.Fatalf("unresolved contradiction passed: exit=%d env=%#v", exit, env)
		}
	})

	t.Run("required spike must have a completed manifest", func(t *testing.T) {
		fixture := newDeepResearchFixture(t, "required")
		init := requireDeepResearchOK(t, fixture.projectRoot, []string{
			"deep-research", "init", "--feature-dir", fixture.featureRel,
			"--mode", "repo-only", "--leader-id", "leader-1",
		})
		prepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
			"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
			"--expected-revision", deepResearchRevisionArg(t, init),
			"--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, true)),
		})
		lease := requireDeepResearchOK(t, fixture.projectRoot, []string{
			"deep-research", "track-lease", "--feature-dir", fixture.featureRel,
			"--expected-revision", deepResearchRevisionArg(t, prepared),
			"--worker-id", "researcher-1",
		})
		env, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
			"deep-research", "track-submit", "--feature-dir", fixture.featureRel,
			"--expected-revision", deepResearchRevisionArg(t, lease),
			"--track-id", "TRK-001", "--attempt-id", asString(lease.Data["attempt_id"]),
			"--result-json", mustDeepResearchJSON(t, deepResearchTrackResult(fixture, nil, nil)),
		})
		if exit == 0 || env.Status != "invalid" {
			t.Fatalf("required spike omission passed: exit=%d env=%#v", exit, env)
		}
	})
}

func TestDeepResearchWorkflowPublishesEvidenceBackedNotNeededDecision(t *testing.T) {
	fixture := newDeepResearchFixture(t, "required")
	published := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "not-needed",
		"--feature-dir", fixture.featureRel,
		"--leader-id", "leader-1",
		"--input-json", mustDeepResearchJSON(t, map[string]any{
			"capability_dispositions": []any{map[string]any{
				"capability_ref": "CAP-001",
				"reason":         "The current repository already contains the complete implementation chain.",
				"evidence_refs":  []any{"docs/proof.md"},
			}},
		}),
	})
	if published.Data["claim_status"] != "not_needed" {
		t.Fatalf("not-needed binding = %#v", published.Data)
	}
	if ids := deepResearchStringSlice(published.Data["handoff_ids"]); len(ids) != 0 {
		t.Fatalf("not-needed path invented PH ids: %#v", ids)
	}
	markdown, err := os.ReadFile(filepath.Join(fixture.featureDir, "deep-research.md"))
	if err != nil {
		t.Fatal(err)
	}
	text := string(markdown)
	if !strings.Contains(text, "**Status**: Not needed") || strings.Contains(text, "PH-001") || strings.Contains(text, "EVD-001") {
		t.Fatalf("invalid not-needed projection:\n%s", text)
	}

	requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "verify-handoff",
		"--feature-dir", fixture.featureRel,
		"--handoff-ref", asString(published.Data["handoff_ref"]),
		"--expected-sha256", asString(published.Data["handoff_sha256"]),
	})
}

func TestDeepResearchWorkflowRejectsUnselectedSpecGate(t *testing.T) {
	fixture := newDeepResearchFixture(t, "not_selected")
	env, exit := runDeepResearchWorkflowCommand(t, fixture.projectRoot, []string{
		"deep-research", "init", "--feature-dir", fixture.featureRel,
		"--mode", "repo-only", "--leader-id", "leader-1",
	})
	if exit == 0 || env.Status != "blocked" {
		t.Fatalf("unselected feasibility gate started research: exit=%d env=%#v", exit, env)
	}
}

type deepResearchFixture struct {
	projectRoot string
	featureRel  string
	featureDir  string
	specPath    string
	proofRef    string
}

func newDeepResearchFixture(t *testing.T, decision string) deepResearchFixture {
	t.Helper()
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join(".specify", "features", "001-research"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	proofRef := "docs/proof.md"
	proofPath := filepath.Join(projectRoot, filepath.FromSlash(proofRef))
	if err := os.MkdirAll(filepath.Dir(proofPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(proofPath, []byte("# Proof\n\nThe adapter already has an executable validation route.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	capabilityRefs := []any{}
	if decision == "required" {
		capabilityRefs = []any{"CAP-001"}
	}
	spec := map[string]any{
		"version":             1,
		"status":              "planning-ready",
		"acceptance_criteria": []any{"The implementation chain is proven."},
		"feasibility_gate": map[string]any{
			"decision":        decision,
			"capability_refs": capabilityRefs,
			"reason_refs":     []any{"spec-contract.json#/constraints/0"},
		},
	}
	specPath := filepath.Join(featureDir, "spec-contract.json")
	writeDeepResearchJSON(t, specPath, spec)
	return deepResearchFixture{
		projectRoot: projectRoot,
		featureRel:  featureRel,
		featureDir:  featureDir,
		specPath:    specPath,
		proofRef:    proofRef,
	}
}

func deepResearchTracksInput(fixture deepResearchFixture, requiresSpike bool) map[string]any {
	return map[string]any{"tracks": []any{map[string]any{
		"track_id":          "TRK-001",
		"title":             "Prove the adapter implementation chain",
		"capability_refs":   []any{"CAP-001"},
		"read_paths":        []any{fixture.featureRel + "/spec-contract.json", fixture.proofRef},
		"questions":         []any{"Can the capability be planned without inventing a missing boundary?"},
		"source_classes":    []any{"repository"},
		"requires_spike":    requiresSpike,
		"completion_signal": "A traceable implementation-chain finding exists.",
	}}}
}

func deepResearchTrackResult(fixture deepResearchFixture, contradictions, spikeRefs []any) map[string]any {
	if contradictions == nil {
		contradictions = []any{}
	}
	if spikeRefs == nil {
		spikeRefs = []any{}
	}
	return map[string]any{
		"protocol":   "deep_research_track_result.v1",
		"status":     "complete",
		"paths_read": []any{fixture.featureRel + "/spec-contract.json", fixture.proofRef},
		"findings": []any{map[string]any{
			"finding_id":      "FND-001",
			"kind":            "fact",
			"summary":         "The repository proof exposes an executable adapter validation route.",
			"capability_refs": []any{"CAP-001"},
			"evidence_refs":   []any{"EVD-001"},
			"spike_refs":      spikeRefs,
		}},
		"evidence": []any{map[string]any{
			"evidence_id":     "EVD-001",
			"source_type":     "repository",
			"source_ref":      fixture.proofRef,
			"claim":           "The adapter validation route exists in the current repository.",
			"capability_refs": []any{"CAP-001"},
			"quality": map[string]any{
				"authority":    "repository",
				"independence": "direct",
				"recency":      "current",
				"limitations":  []any{},
			},
		}},
		"spike_refs":     spikeRefs,
		"constraints":    []any{"Preserve the existing adapter boundary."},
		"risks":          []any{"A future dependency upgrade can invalidate the proof."},
		"contradictions": contradictions,
	}
}

func deepResearchSynthesis(resolutions []any) map[string]any {
	if resolutions == nil {
		resolutions = []any{}
	}
	return map[string]any{
		"capability_dispositions": []any{map[string]any{
			"capability_ref": "CAP-001",
			"disposition":    "plannable",
			"reason_refs":    []any{"EVD-001"},
		}},
		"planning_handoffs": []any{map[string]any{
			"handoff_id":       "PH-001",
			"capability_refs":  []any{"CAP-001"},
			"status":           "mandatory",
			"decision":         "Plan against the repository-backed adapter boundary.",
			"evidence_refs":    []any{"EVD-001"},
			"spike_refs":       []any{},
			"constraints":      []any{"Preserve the existing adapter boundary."},
			"risks":            []any{"Revalidate after dependency upgrades."},
			"rejected_options": []any{"Do not invent a parallel adapter."},
			"validation":       []any{"Run the adapter integration test at its real entry point."},
		}},
		"evidence_dispositions": []any{map[string]any{
			"evidence_ref": "EVD-001",
			"disposition":  "consumed",
			"handoff_refs": []any{"PH-001"},
			"reason":       "Directly proves the planning decision.",
		}},
		"contradiction_resolutions": resolutions,
		"recommended_next_command":  "/sp.plan",
	}
}

func deepResearchAudit(auditRequestSHA string) map[string]any {
	checks := []any{}
	for _, checkID := range []string{
		"capability_closure",
		"evidence_integrity",
		"source_quality",
		"contradictions",
		"spikes",
		"planning_handoff",
	} {
		checks = append(checks, map[string]any{
			"check_id":      checkID,
			"status":        "pass",
			"evidence_refs": []any{},
		})
	}
	return map[string]any{
		"schema_version":       "spec-kit-deep-research-audit-v1",
		"audit_request_sha256": auditRequestSHA,
		"status":               "accepted",
		"checks":               checks,
		"findings":             []any{},
	}
}

func prepareAcceptedDeepResearchTrack(t *testing.T, fixture deepResearchFixture, requiresSpike bool, contradictions, spikeRefs []any) Envelope {
	t.Helper()
	init := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "init", "--feature-dir", fixture.featureRel,
		"--mode", "repo-only", "--leader-id", "leader-1",
	})
	prepared := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-prepare", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, init),
		"--input-json", mustDeepResearchJSON(t, deepResearchTracksInput(fixture, requiresSpike)),
	})
	lease := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-lease", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, prepared),
		"--worker-id", "researcher-1",
	})
	attemptID := asString(lease.Data["attempt_id"])
	submitted := requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-submit", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, lease),
		"--track-id", "TRK-001", "--attempt-id", attemptID,
		"--result-json", mustDeepResearchJSON(t, deepResearchTrackResult(fixture, contradictions, spikeRefs)),
	})
	return requireDeepResearchOK(t, fixture.projectRoot, []string{
		"deep-research", "track-accept", "--feature-dir", fixture.featureRel,
		"--expected-revision", deepResearchRevisionArg(t, submitted),
		"--track-id", "TRK-001", "--attempt-id", attemptID,
		"--leader-id", "leader-1",
	})
}

func writeReadyPlanContract(t *testing.T, fixture deepResearchFixture, published Envelope) {
	t.Helper()
	payload := map[string]any{
		"version":         2,
		"status":          "ready",
		"source_contract": "spec-contract.json",
		"source_revision": 1,
		"acceptance_refs": []any{"spec-contract.json#/acceptance_criteria/0"},
		"deep_research_binding": map[string]any{
			"decision":           "required",
			"handoff_ref":        published.Data["handoff_ref"],
			"handoff_sha256":     published.Data["handoff_sha256"],
			"source_spec_sha256": published.Data["source_spec_sha256"],
			"state_revision":     published.Data["state_revision"],
			"claim_status":       published.Data["claim_status"],
			"handoff_ids":        published.Data["handoff_ids"],
		},
		"transition": map[string]any{
			"version":        1,
			"status":         "ready",
			"source_ref":     "plan-contract.json",
			"semantic_delta": []any{},
			"required_refs":  []any{},
			"blockers":       []any{},
			"next_action":    "/sp.tasks",
		},
	}
	writeDeepResearchJSON(t, filepath.Join(fixture.featureDir, "plan-contract.json"), payload)
}

func runDeepResearchWorkflowCommand(t *testing.T, projectRoot string, args []string) (Envelope, int) {
	t.Helper()
	fullArgs := append([]string{}, args...)
	fullArgs = append(fullArgs, "--project-root", projectRoot, "--format", "json")
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	exit := Run(fullArgs, &stdout, &stderr, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode deep-research envelope: %v\nstdout=%s\nstderr=%s", err, stdout.String(), stderr.String())
	}
	return env, exit
}

func requireDeepResearchOK(t *testing.T, projectRoot string, args []string) Envelope {
	t.Helper()
	env, exit := runDeepResearchWorkflowCommand(t, projectRoot, args)
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("deep-research command failed: args=%v exit=%d env=%#v", args, exit, env)
	}
	return env
}

func deepResearchRevisionArg(t *testing.T, env Envelope) string {
	t.Helper()
	revision, ok := hookJSONInteger(env.Data["revision"])
	if !ok || revision < 1 {
		t.Fatalf("invalid deep-research revision: %#v", env.Data["revision"])
	}
	return fmt.Sprintf("%d", revision)
}

func mustDeepResearchJSON(t *testing.T, value any) string {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func writeDeepResearchJSON(t *testing.T, path string, value any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func deepResearchStringSlice(value any) []string {
	rows, _ := value.([]any)
	out := make([]string, 0, len(rows))
	for _, row := range rows {
		if text := strings.TrimSpace(asString(row)); text != "" {
			out = append(out, text)
		}
	}
	return out
}
