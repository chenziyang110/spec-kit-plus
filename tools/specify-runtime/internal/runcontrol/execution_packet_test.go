package runcontrol

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestPacketBoundGuardRejectsScopeExpansionAtomically(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, _ := announcePacketExecution(t, store)
	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	before := databaseContents(t, store.db)
	for _, path := range []string{"src", "src/unrelated.go", "src/packet-other/file.go"} {
		_, err := store.GuardExecution(ctx, GuardExecutionParams{
			ActivityID: registration.Activity.ActivityID, ExpectedWorkRevision: registration.Work.Revision, Fence: registration.Work.Fence,
			ExpectedCoordinationRevision: revision, OverviewSHA256: strings.Repeat("b", 64), Reason: "attempt scope expansion",
			WriteIntents: []WriteIntentSpec{{Path: "src/packet/file.go"}, {Path: path}},
			Resources:    []ExecutionResourceIntentSpec{{ResourceType: ResourceAPI, ResourceKey: "/v1/packet", Confidence: IntentConfirmed}},
		})
		if !errors.Is(err, ErrExecutionGuardRequired) {
			t.Fatalf("guard outside packet scope %q = %v", path, err)
		}
		assertPreservedDatabaseContents(t, store.db, before)
	}
	guarded := guardTestExecution(t, store, registration)
	if guarded.Resources[0].Confidence != IntentConfirmed || guarded.WriteIntents[0].Confidence != IntentConfirmed {
		t.Fatalf("valid packet guard did not acquire file and semantic scope: %#v", guarded)
	}
	if guarded.Activity.BaselineJSON != registration.Activity.BaselineJSON {
		t.Fatal("guard changed the immutable packet binding")
	}
}

func TestPacketBoundClaimRequiresExactPacketAndPinnedScope(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, binding := announcePacketExecution(t, store)
	guarded := guardTestExecution(t, store, registration)
	cases := []struct {
		name string
		ref  string
		sha  string
		path string
		want error
	}{
		{"missing_packet", "", "", "src/packet/file.go", ErrExecutionGuardRequired},
		{"missing_digest", binding.Path, "", "src/packet/file.go", ErrExecutionGuardRequired},
		{"different_packet", ".specify/features/feature/implementation-review/packets/T002.json", binding.SHA256, "src/packet/file.go", ErrExecutionGuardRequired},
		{"changed_bytes", binding.Path, strings.Repeat("b", 64), "src/packet/file.go", ErrExecutionGuardRequired},
		{"outside_scope", binding.Path, binding.SHA256, "src/unrelated.go", ErrExecutionGuardRequired},
		{"exact_packet_child_scope", binding.Path, binding.SHA256, "src/packet/file.go", nil},
	}
	before := databaseContents(t, store.db)
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			work, intents, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
				WorkID: guarded.Work.WorkID, ExpectedRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
				PacketRef: test.ref, PacketSHA256: test.sha, Specs: []WriteIntentSpec{{Path: test.path}},
			})
			if !errors.Is(err, test.want) {
				t.Fatalf("packet claim = %v, want %v", err, test.want)
			}
			if test.want == nil && (!reflect.DeepEqual(work, guarded.Work) || len(intents) != 1) {
				t.Fatalf("packet claim returned an invalid receipt: %#v / %#v", work, intents)
			}
			assertPreservedDatabaseContents(t, store.db, before)
		})
	}
	// A legacy broad intent cannot override the narrower immutable packet.
	if _, err := store.db.Exec(`UPDATE write_intents SET path = 'src', path_key = 'src'`); err != nil {
		t.Fatal(err)
	}
	_, _, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: guarded.Work.WorkID, ExpectedRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		PacketRef: binding.Path, PacketSHA256: binding.SHA256, Specs: []WriteIntentSpec{{Path: "src/unrelated.go"}},
	})
	if !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("broad legacy intent bypassed the packet scope: %v", err)
	}
	_, err = store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID: guarded.Activity.ActivityID, ExpectedWorkRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		ChangedPaths: []string{"src/unrelated.go"}, ValidationJSON: `[{"command":"fixture validation","result":"passed"}]`, Reason: "try broad completion",
	})
	if !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("broad legacy intent bypassed packet completion audit: %v", err)
	}
}

func TestPacketBoundClaimRequiresEveryPinnedWritePath(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	bookkeeping := []string{
		".specify/features/feature/implementation-review/task-index.json",
		".specify/features/feature/implementation-review/task-state.json",
	}
	registration, binding := announcePacketExecution(t, store, bookkeeping...)
	revision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	partial, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID: registration.Activity.ActivityID, ExpectedWorkRevision: registration.Work.Revision, Fence: registration.Work.Fence,
		ExpectedCoordinationRevision: revision, OverviewSHA256: strings.Repeat("b", 64), Reason: "guard a permitted subset",
		WriteIntents: []WriteIntentSpec{{Path: "src/packet"}, {Path: bookkeeping[0]}},
		Resources:    []ExecutionResourceIntentSpec{{ResourceType: ResourceAPI, ResourceKey: "/v1/packet", Confidence: IntentConfirmed}},
	})
	if err != nil {
		t.Fatal(err)
	}
	before := databaseContents(t, store.db)
	for _, specs := range [][]WriteIntentSpec{{{Path: "src/packet/file.go"}}, nil} {
		_, intents, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
			WorkID: partial.Work.WorkID, ExpectedRevision: partial.Work.Revision, Fence: partial.Work.Fence,
			PacketRef: binding.Path, PacketSHA256: binding.SHA256, Specs: specs,
		})
		if !errors.Is(err, ErrExecutionGuardRequired) || len(intents) != 0 || !strings.Contains(err.Error(), bookkeeping[1]) {
			t.Errorf("item-start omitted pinned bookkeeping ownership: receipt=%#v, err=%v", intents, err)
		}
		assertPreservedDatabaseContents(t, store.db, before)
	}

	full := guardTestExecution(t, store, partial.ExecutionRegistration)
	before = databaseContents(t, store.db)
	work, intents, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: full.Work.WorkID, ExpectedRevision: full.Work.Revision, Fence: full.Work.Fence,
		PacketRef: binding.Path, PacketSHA256: binding.SHA256, Specs: []WriteIntentSpec{{Path: "src/packet/file.go"}},
	})
	if err != nil || !reflect.DeepEqual(work, full.Work) || len(intents) != 1 || intents[0].Path != "src/packet" {
		t.Fatalf("fully owned packet did not return the requested scope receipt: %#v / %#v, %v", work, intents, err)
	}
	assertPreservedDatabaseContents(t, store.db, before)
}

func TestPacketGuardScopeAmendmentClaimsCausalPathWithoutMutatingOriginalPacket(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, binding := announcePacketExecution(t, store)
	guarded := guardTestExecution(t, store, registration)
	originalBaseline := guarded.Activity.BaselineJSON

	amended, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID: guarded.Activity.ActivityID, ExpectedWorkRevision: guarded.Work.Revision,
		Fence: guarded.Work.Fence, ExpectedCoordinationRevision: guarded.CoordinationRevision,
		OverviewSHA256: strings.Repeat("d", 64), Reason: "guard a causally required companion test",
		WriteIntents: []WriteIntentSpec{
			{Path: "src/packet", Operation: WriteModify, Confidence: IntentConfirmed},
			{Path: "tests/pause_metadata_test.go", Operation: WriteCreate, Confidence: IntentConfirmed},
		},
		Resources: guardedResourceSpecs(guarded.Resources),
		ScopeAmendments: []ExecutionScopeAmendmentSpec{{
			Path: "tests/pause_metadata_test.go", Operation: WriteCreate,
			Reason: "implementation discovered a causally required companion test", LateDiscovery: true,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	var before, after WorkspaceBaseline
	if err := json.Unmarshal([]byte(originalBaseline), &before); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal([]byte(amended.Activity.BaselineJSON), &after); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(after.WorkerPacket, before.WorkerPacket) || !reflect.DeepEqual(after.WorkerPacket, &binding) {
		t.Fatalf("scope amendment mutated original packet binding: before=%#v after=%#v", before.WorkerPacket, after.WorkerPacket)
	}
	if len(after.ScopeAmendments) != 1 || after.ScopeAmendments[0].Path != "tests/pause_metadata_test.go" || !after.ScopeAmendments[0].LateDiscovery {
		t.Fatalf("scope amendments = %#v", after.ScopeAmendments)
	}
	if amended.Activity.GuardedOverviewRevision != guarded.CoordinationRevision || amended.Activity.GuardedOverviewSHA256 != strings.Repeat("d", 64) {
		t.Fatalf("amended overview binding = %#v", amended.Activity)
	}
	replayed, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID: amended.Activity.ActivityID, ExpectedWorkRevision: amended.Work.Revision,
		Fence: amended.Work.Fence, ExpectedCoordinationRevision: amended.CoordinationRevision,
		OverviewSHA256: strings.Repeat("e", 64), Reason: "retry the same guarded scope amendment",
		WriteIntents: []WriteIntentSpec{
			{Path: "src/packet", Operation: WriteModify, Confidence: IntentConfirmed},
			{Path: "tests/pause_metadata_test.go", Operation: WriteCreate, Confidence: IntentConfirmed},
		},
		Resources: guardedResourceSpecs(amended.Resources),
		ScopeAmendments: []ExecutionScopeAmendmentSpec{{
			Path: "tests/pause_metadata_test.go", Operation: WriteCreate,
			Reason: "implementation discovered a causally required companion test", LateDiscovery: true,
		}},
	})
	if err != nil {
		t.Fatalf("idempotent scope amendment replay failed: %v", err)
	}
	var replayedBaseline WorkspaceBaseline
	if err := json.Unmarshal([]byte(replayed.Activity.BaselineJSON), &replayedBaseline); err != nil || len(replayedBaseline.ScopeAmendments) != 1 {
		t.Fatalf("replayed amendments = %#v, err = %v", replayedBaseline.ScopeAmendments, err)
	}
	amended = replayed
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: amended.Work.WorkID, ExpectedRevision: amended.Work.Revision, Fence: amended.Work.Fence,
		PacketRef: binding.Path, PacketSHA256: binding.SHA256,
		Specs: []WriteIntentSpec{{Path: "tests/pause_metadata_test.go/unplanned-child"}},
	}); !errors.Is(err, ErrExecutionGuardRequired) {
		t.Fatalf("exact scope amendment authorized a descendant path: %v", err)
	}
	claimed, intents, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: amended.Work.WorkID, ExpectedRevision: amended.Work.Revision, Fence: amended.Work.Fence,
		PacketRef: binding.Path, PacketSHA256: binding.SHA256,
		Specs: []WriteIntentSpec{{Path: "tests/pause_metadata_test.go"}},
	})
	if err != nil || claimed.Revision != amended.Work.Revision || len(intents) != 1 || intents[0].Path != "tests/pause_metadata_test.go" {
		t.Fatalf("amended packet claim = %#v / %#v, %v", claimed, intents, err)
	}
	_, err = store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID: amended.Activity.ActivityID, ExpectedWorkRevision: amended.Work.Revision, Fence: amended.Work.Fence,
		ChangedPaths:   []string{"tests/pause_metadata_test.go"},
		ValidationJSON: `[{"command":"go test ./...","result":"passed"}]`, Reason: "try completion without drift review",
	})
	if !errors.Is(err, ErrExecutionCompletionGate) {
		t.Fatalf("scope amendment bypassed independent drift review: %v", err)
	}
	completed, err := store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID: amended.Activity.ActivityID, ExpectedWorkRevision: amended.Work.Revision, Fence: amended.Work.Fence,
		ChangedPaths:   []string{"tests/pause_metadata_test.go"},
		ValidationJSON: `[{"command":"go test ./...","result":"passed"},{"command":"scope-drift-review","result":"passed","reviewer":"independent-reviewer","independent":true}]`, Reason: "amended scope verified",
	})
	if err != nil || completed.Activity.Phase != ExecutionPhaseCompleted {
		t.Fatalf("amended execution completion = %#v, %v", completed, err)
	}
}

func TestPacketGuardScopeAmendmentRejectsGlobManualActivityAndConflictsAtomically(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, _ := announcePacketExecution(t, store)
	guarded := guardTestExecution(t, store, registration)
	other := announceExecutionTestActivity(t, store, "other-owner", "debug:other", "tests", ResourceFeature, "other")
	_ = guardTestExecution(t, store, other)
	manual := announceExecutionTestActivity(t, store, "manual-amend", "fast:manual-amend", "src/manual", ResourceFeature, "manual-amend")
	currentRevision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}

	for name, target := range map[string]struct {
		registration ExecutionRegistration
		path         string
	}{
		"filename-glob": {
			registration: guarded.ExecutionRegistration, path: "src/packet/*_test.go",
		},
		"manual-activity": {
			registration: manual, path: "src/manual/new.go",
		},
		"conflicting-path": {
			registration: guarded.ExecutionRegistration, path: "tests/new_test.go",
		},
	} {
		t.Run(name, func(t *testing.T) {
			before := databaseContents(t, store.db)
			writes := make([]WriteIntentSpec, 0, len(target.registration.WriteIntents)+1)
			for _, intent := range target.registration.WriteIntents {
				writes = append(writes, WriteIntentSpec{Path: intent.Path, Operation: intent.Operation, Confidence: IntentConfirmed})
			}
			writes = append(writes, WriteIntentSpec{Path: target.path, Operation: WriteCreate, Confidence: IntentConfirmed})
			_, err := store.GuardExecution(ctx, GuardExecutionParams{
				ActivityID: target.registration.Activity.ActivityID, ExpectedWorkRevision: target.registration.Work.Revision,
				Fence: target.registration.Work.Fence, ExpectedCoordinationRevision: currentRevision,
				OverviewSHA256: strings.Repeat("e", 64), WriteIntents: writes,
				Resources: guardedResourceSpecs(target.registration.Resources), Reason: "attempt explicit packet amendment",
				ScopeAmendments: []ExecutionScopeAmendmentSpec{{Path: target.path, Operation: WriteCreate, Reason: "causal scope repair"}},
			})
			if err == nil {
				t.Fatal("invalid scope amendment succeeded")
			}
			assertPreservedDatabaseContents(t, store.db, before)
		})
	}
}

func guardedResourceSpecs(resources []ExecutionResourceIntent) []ExecutionResourceIntentSpec {
	result := make([]ExecutionResourceIntentSpec, 0, len(resources))
	for _, resource := range resources {
		result = append(result, ExecutionResourceIntentSpec{
			ResourceType: resource.ResourceType, ResourceKey: resource.ResourceKey,
			Mode: resource.Mode, Confidence: IntentConfirmed, Reason: resource.Reason,
		})
	}
	return result
}

func TestPacketBaselineMetadataIsPreservedAndMalformedBindingsFailBeforeAnnouncement(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, binding := announcePacketExecution(t, store)
	var baseline WorkspaceBaseline
	if err := json.Unmarshal([]byte(registration.Activity.BaselineJSON), &baseline); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(baseline.WorkerPacket, &binding) || baseline.HeadCommit != "baseline-head" {
		t.Fatalf("baseline lost packet metadata: %#v", baseline)
	}
	for _, packetJSON := range []string{
		`null`,
		`{"path":"packet.json","sha256":"bad","write_scope":["src"]}`,
		`{"path":"packet.json","sha256":"` + binding.SHA256 + `"}`,
		`{"path":"packet.json","sha256":"` + binding.SHA256 + `","write_scope":["../outside"]}`,
	} {
		before := databaseContents(t, store.db)
		_, err := store.AnnounceExecution(context.Background(), AnnounceExecutionParams{
			ActivityID: "bad-packet", WorkID: "bad-packet", Workflow: ExecutionWorkflowImplement, SubjectID: "bad-packet",
			Summary: "bad packet", AgentID: "agent", AdapterID: "codex", WorkspaceRoot: t.TempDir(), LeaseUntil: time.Now().UTC().Add(time.Hour),
			BaselineJSON: `{"worker_packet":` + packetJSON + `}`,
		})
		if !errors.Is(err, ErrInvalidArgument) {
			t.Fatalf("malformed packet binding accepted: %s, error %v", packetJSON, err)
		}
		assertPreservedDatabaseContents(t, store.db, before)
	}
}

func TestManualGuardCanStillAmendScope(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration := announceExecutionTestActivity(t, store, "manual", "fast:manual", "src/original", ResourceAPI, "/v1/manual")
	first := guardTestExecution(t, store, registration)
	amended, err := store.GuardExecution(ctx, GuardExecutionParams{
		ActivityID: first.Activity.ActivityID, ExpectedWorkRevision: first.Work.Revision, Fence: first.Work.Fence,
		ExpectedCoordinationRevision: first.CoordinationRevision, OverviewSHA256: strings.Repeat("b", 64), Reason: "confirmed scope amendment",
		WriteIntents: []WriteIntentSpec{{Path: "src/original"}, {Path: "src/additional"}},
		Resources:    []ExecutionResourceIntentSpec{{ResourceType: ResourceAPI, ResourceKey: "/v1/manual", Confidence: IntentConfirmed}},
	})
	if err != nil || len(amended.WriteIntents) != 2 || len(amended.Resources) != 1 {
		t.Fatalf("manual scope amendment = %#v, %v", amended, err)
	}
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, ClaimWorkIntentsParams{
		WorkID: amended.Work.WorkID, ExpectedRevision: amended.Work.Revision, Fence: amended.Work.Fence,
		PacketRef: "an-outer-packet-reference", PacketSHA256: strings.Repeat("c", 64),
		Specs: []WriteIntentSpec{{Path: "src/additional/file.go"}},
	}); err != nil {
		t.Fatalf("optional packet arguments affected unbound manual activity: %v", err)
	}
}

func announcePacketExecution(t *testing.T, store *Store, extraWriteScope ...string) (ExecutionRegistration, WorkerPacketBinding) {
	t.Helper()
	binding := WorkerPacketBinding{
		Path:   ".specify/features/feature/implementation-review/packets/T001.json",
		SHA256: strings.Repeat("a", 64), WriteScope: []string{"src/packet/**"},
	}
	binding.WriteScope = append(binding.WriteScope, extraWriteScope...)
	writes := []WriteIntentSpec{{Path: "src/packet", Confidence: IntentCandidate}}
	for _, path := range extraWriteScope {
		writes = append(writes, WriteIntentSpec{Path: path, Confidence: IntentCandidate})
	}
	baseline, err := EncodeWorkspaceBaseline(WorkspaceBaseline{HeadCommit: "baseline-head", WorkerPacket: &binding})
	if err != nil {
		t.Fatal(err)
	}
	registration, err := store.AnnounceExecution(context.Background(), AnnounceExecutionParams{
		ActivityID: "packet", WorkID: "packet", Workflow: ExecutionWorkflowImplement, SubjectID: "feature", ItemID: "T001",
		TaskRef: "implement:feature#T001", Summary: "packet work", SourceRef: binding.Path,
		AgentID: "agent", AdapterID: "codex", WorkspaceRoot: t.TempDir(), LeaseUntil: time.Now().UTC().Add(time.Hour),
		BaselineJSON: baseline, PlannedWriteIntents: writes,
		Resources: []ExecutionResourceIntentSpec{{ResourceType: ResourceAPI, ResourceKey: "/v1/packet", Confidence: IntentCandidate}},
	})
	if err != nil {
		t.Fatal(err)
	}
	return registration, binding
}
