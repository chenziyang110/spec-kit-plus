package query

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestExpansionRejectsSameGenerationMutationsAndRecoversWithNewIdentity(t *testing.T) {
	for _, mutation := range []string{"claim-stale", "claim-reconcile", "rename", "delete", "status-debt"} {
		t.Run(mutation, func(t *testing.T) {
			paths := queryTestPaths(t)
			seedCompassModelSwitchGraph(t, paths)
			input := CompassInput{Intent: "debug", Query: "runtimeOverride"}
			before, err := Compass(paths, input)
			if err != nil {
				t.Fatal(err)
			}
			bundlePath, _ := expansionBundlePath(paths, before.ExpansionRef.ID)
			original, err := os.ReadFile(bundlePath)
			if err != nil {
				t.Fatal(err)
			}
			st, err := store.OpenExisting(paths)
			if err != nil {
				t.Fatal(err)
			}
			defer st.Close()
			ctx := context.Background()
			switch mutation {
			case "claim-stale":
				_, err = st.MarkClaimsStale(ctx, []string{"claim:provider-runtime-owner"}, "changed source", "snapshot-stale")
			case "claim-reconcile":
				_, err = st.ApplyClaimReconciliation(ctx, store.ClaimReconciliationBatch{
					ID: "reconcile:snapshot", PacketHash: "snapshot-packet", GenerationID: before.ActiveGenerationID, Workflow: "sp-debug", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
					Items: []store.ClaimReconciliationItem{{ClaimID: "claim:provider-runtime-owner", ExpectedState: claim.StateSupported, ExpectedRevision: 1, Reason: "fresh bounded source", Evidence: []store.ClaimReconciliationEvidence{{ID: "E-new", SourceKind: "source", SourcePath: "src/server/ws/handler.ts", Span: "L1-L2", ContentHash: "sha256:new", Role: "supporting"}}, Verification: &store.ClaimReconciliationVerification{ID: "V-new", Result: claim.VerificationPassed, Command: "fixture source assertion"}}},
				})
			case "rename", "delete":
				disposition := changemodel.DispositionAdoptable
				change := changemodel.PathChange{Path: "src/server/ws/handler.ts", Operation: changemodel.OperationDelete, NodeID: "N-provider-runtime", Disposition: &disposition, EvidenceRefs: []string{"E-ws-handler"}}
				if mutation == "rename" {
					change.OldPath = change.Path
					change.Path = "src/server/ws/renamed.ts"
					change.Operation = changemodel.OperationRename
				}
				_, err = st.ApplyTypedUpdate(ctx, store.TypedUpdate{Record: store.UpdateRecord{ID: "update:snapshot", Trigger: "workflow-finalize", ResultState: "partial", ChangedPaths: []string{change.Path}}, PathChanges: []changemodel.PathChange{change}, Workflow: "sp-debug", Reason: "fixture scoped mutation"})
				if err == nil {
					status, readErr := rt.ReadStatus(paths)
					if readErr != nil {
						t.Fatal(readErr)
					}
					status.LastUpdateID = "update:snapshot"
					status.LastUpdateOutcome = "partial"
					err = rt.WriteStatus(paths, status)
				}
			case "status-debt":
				status, readErr := rt.ReadStatus(paths)
				if readErr != nil {
					t.Fatal(readErr)
				}
				status.Dirty = true
				status.DirtyReasons = []string{"new scoped debt"}
				err = rt.WriteStatus(paths, status)
			}
			if err != nil {
				t.Fatal(err)
			}
			stale, err := Expand(paths, ExpandInput{ID: before.ExpansionRef.ID, Section: "claim_evidence"})
			if err != nil {
				t.Fatal(err)
			}
			if stale.Status != expansionStatusStaleExpansion || stale.Data != nil {
				t.Fatalf("old bundle remained consumable: %#v", stale)
			}
			assertAdvisoryEpistemicContract(t, stale.EpistemicContract)
			after, err := Compass(paths, input)
			if err != nil {
				t.Fatal(err)
			}
			if mutation == "status-debt" {
				if after.ExpansionRef != nil || !after.Degraded {
					t.Fatalf("dirty readiness must remain degraded before recovery: %#v", after)
				}
				status, readErr := rt.ReadStatus(paths)
				if readErr != nil {
					t.Fatal(readErr)
				}
				status.Dirty = false
				status.DirtyReasons = []string{}
				status.DirtyDebts = []rt.DebtRecord{}
				status.Readiness = rt.ReadyReadiness
				status.Freshness = rt.ReadyFreshness
				status.LastRefreshReason = "fixture verified refresh"
				if err := rt.WriteStatus(paths, status); err != nil {
					t.Fatal(err)
				}
				after, err = Compass(paths, input)
				if err != nil {
					t.Fatal(err)
				}
			}
			if after.ActiveGenerationID != before.ActiveGenerationID || after.ExpansionRef == nil || after.ExpansionRef.ID == before.ExpansionRef.ID {
				t.Fatalf("new snapshot has no distinct same-generation identity: before=%#v after=%#v", before.ExpansionRef, after.ExpansionRef)
			}
			fresh, err := Expand(paths, ExpandInput{ID: after.ExpansionRef.ID, Section: "claim_evidence"})
			if err != nil {
				t.Fatal(err)
			}
			if fresh.Status != expansionStatusOK {
				t.Fatalf("rerun did not recover: %#v", fresh)
			}
			retained, err := os.ReadFile(bundlePath)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(original, retained) {
				t.Fatal("rerun rewrote previously issued expansion")
			}
			staleAgain, err := Expand(paths, ExpandInput{ID: before.ExpansionRef.ID})
			if err != nil || staleAgain.Status != expansionStatusStaleExpansion {
				t.Fatalf("old reference revived: %#v %v", staleAgain, err)
			}
		})
	}
}

func TestExpansionRejectsContentTamperAndLegacySnapshotContract(t *testing.T) {
	for _, mutation := range []string{"payload", "snapshot", "status", "legacy-contract", "malformed", "trailing-json", "recovery-basis"} {
		t.Run(mutation, func(t *testing.T) {
			paths := queryTestPaths(t)
			seedCompassModelSwitchGraph(t, paths)
			compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
			if err != nil {
				t.Fatal(err)
			}
			path, bundle := readExpansionTestBundle(t, paths, compass.ExpansionRef.ID)
			want := expansionStatusInvalidExpansion
			switch mutation {
			case "payload":
				bundle.SectionPayloads["related_paths"] = []string{"src/unrelated.go"}
			case "snapshot":
				bundle.NavigationSnapshot.Digest = "sha256:" + strings.Repeat("a", 64)
			case "status":
				bundle.StatusDigest = "sha256:" + strings.Repeat("b", 64)
			case "legacy-contract":
				bundle.ExpansionContractVersion = 0
				want = expansionStatusIncompatibleExpansion
			case "recovery-basis":
				bundle.RecoveryBasis = &ExpansionRecoveryBasis{PreservedID: bundle.ID, PreservedPath: "arbitrary", SHA256: "sha256:" + strings.Repeat("c", 64)}
			}
			writeExpansionBundleFileForTest(t, path, bundle)
			if mutation == "malformed" {
				if err := os.WriteFile(path, []byte(`{"partial":`), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			if mutation == "trailing-json" {
				data, err := os.ReadFile(path)
				if err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(path, append(data, []byte(` {"trailing":true}`)...), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			got, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
			if err != nil {
				t.Fatal(err)
			}
			if got.Status != want || got.Data != nil || got.AvailableSections != nil {
				t.Fatalf("tampered/old data exposed: %#v", got)
			}
		})
	}
}

func TestExpansionRejectsSplitBrainAndReadGuardRejectsInterveningWrite(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	read, err := st.BeginNavigationRead(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	defer read.Close()
	if _, err := st.MarkClaimsStale(context.Background(), []string{"claim:provider-runtime-owner"}, "intervening change", "guard"); err != nil {
		t.Fatal(err)
	}
	if err := validateNavigationRead(paths, status, read); err == nil {
		t.Fatal("cross-query write was not rejected")
	}
	status.LastUpdateID = "unknown-update"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	got, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
	if err != nil {
		t.Fatal(err)
	}
	if got.Status != expansionStatusStaleExpansion || got.Data != nil {
		t.Fatalf("split-brain data exposed: %#v", got)
	}
}

func TestExpansionPublicationIsAtomicAndNeverReplacesExistingIdentity(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}
	_, bundle := readExpansionTestBundle(t, paths, compass.ExpansionRef.ID)
	bundle.SectionPayloads["publication_test"] = []string{strings.Repeat("complete", 10000)}
	bundle.ID = expansionBundleID(bundle)
	path, _ := expansionBundlePath(paths, bundle.ID)
	var writers sync.WaitGroup
	errorsSeen := make(chan error, 8)
	for index := 0; index < 8; index++ {
		writers.Add(1)
		go func() { defer writers.Done(); _, err := writeExpansionBundle(paths, bundle); errorsSeen <- err }()
	}
	done := make(chan struct{})
	go func() { writers.Wait(); close(done) }()
	for {
		data, err := os.ReadFile(path)
		if err == nil && !json.Valid(data) {
			t.Fatal("reader observed partial JSON")
		}
		if err != nil && !os.IsNotExist(err) {
			t.Fatal(err)
		}
		select {
		case <-done:
			goto published
		default:
		}
	}
published:
	close(errorsSeen)
	for err := range errorsSeen {
		if err != nil {
			t.Fatal(err)
		}
	}
	original, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	_, conflict := readExpansionTestBundle(t, paths, bundle.ID)
	conflict.SectionPayloads["publication_test"] = []string{"different semantics"}
	if _, err := writeExpansionBundle(paths, conflict); err == nil {
		t.Fatal("different semantics reused old identity")
	}
	if expansionBundleID(conflict) == bundle.ID {
		t.Fatal("payload did not participate in content identity")
	}
	retained, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(original, retained) {
		t.Fatal("conflicting writer replaced immutable data")
	}
	if err := os.WriteFile(path, []byte("corrupt existing file"), 0o644); err != nil {
		t.Fatal(err)
	}
	recovered, err := writeExpansionBundle(paths, bundle)
	if err != nil || recovered.ID == bundle.ID || recovered.RecoveryBasis == nil {
		t.Fatalf("writer did not recover through a distinct bound identity: %#v %v", recovered, err)
	}
	if recovered.RecoveryBasis.SHA256 != expansionBytesDigest([]byte("corrupt existing file")) || recovered.RecoveryBasis.PreservedID != bundle.ID {
		t.Fatalf("recovery did not bind exact preserved bytes: %#v", recovered)
	}
	replayed, err := writeExpansionBundle(paths, bundle)
	if err != nil || replayed.ID != recovered.ID {
		t.Fatalf("same recovery inputs were not deterministic: %#v %v", replayed, err)
	}
	retained, err = os.ReadFile(path)
	if err != nil || string(retained) != "corrupt existing file" {
		t.Fatal("corrupt file was overwritten")
	}
	recoveryPath, recoveryBundle := readExpansionTestBundle(t, paths, recovered.ID)
	if err := os.WriteFile(recoveryPath, []byte("different recovery content"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := writeExpansionBundle(paths, bundle); err == nil {
		t.Fatal("recovery collision was not rejected")
	}
	if data, err := os.ReadFile(recoveryPath); err != nil || string(data) != "different recovery content" {
		t.Fatal("recovery collision overwrote existing content")
	}
	recoveryBundle.RecoveryBasis.SHA256 = "sha256:" + strings.Repeat("d", 64)
	if expansionBundleID(recoveryBundle) == recovered.ID {
		t.Fatal("recovery basis did not participate in identity")
	}
	temporaries, err := filepath.Glob(filepath.Join(filepath.Dir(path), ".expansion-*.tmp"))
	if err != nil || len(temporaries) != 0 {
		t.Fatalf("publication leaked temporaries: %v %v", temporaries, err)
	}
}

func TestExpansionRecoveryThroughCompassPreservesCorruptOriginal(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	input := CompassInput{Intent: "debug", Query: "runtimeOverride"}
	before, err := Compass(paths, input)
	if err != nil {
		t.Fatal(err)
	}
	path, _ := expansionBundlePath(paths, before.ExpansionRef.ID)
	corrupt := []byte("preserve damaged evidence")
	if err := os.WriteFile(path, corrupt, 0o644); err != nil {
		t.Fatal(err)
	}
	for index := 0; index < 2; index++ {
		after, err := Compass(paths, input)
		if err != nil || after.ExpansionRef == nil || after.ExpansionRef.ID == before.ExpansionRef.ID {
			t.Fatalf("rerun did not recover a new reference: %#v %v", after, err)
		}
		basis := after.ExpansionRef.RecoveryBasis
		if basis == nil || basis.PreservedID != before.ExpansionRef.ID || basis.SHA256 != expansionBytesDigest(corrupt) || filepath.Join(paths.Root, filepath.FromSlash(basis.PreservedPath)) != path {
			t.Fatalf("recovery diagnostic does not identify preserved bytes/path: %#v", basis)
		}
		fresh, err := Expand(paths, ExpandInput{ID: after.ExpansionRef.ID})
		if err != nil || fresh.Status != expansionStatusOK || fresh.Data == nil {
			t.Fatalf("recovery reference not usable: %#v %v", fresh, err)
		}
		retained, err := os.ReadFile(path)
		if err != nil || !bytes.Equal(corrupt, retained) {
			t.Fatal("recovery rewrote corrupt original")
		}
	}
}

func TestExpansionStableReadRejectsInterveningContentChange(t *testing.T) {
	path := filepath.Join(t.TempDir(), "expansion.json")
	if err := os.WriteFile(path, []byte("first content"), 0o644); err != nil {
		t.Fatal(err)
	}
	before, err := os.Lstat(path)
	if err != nil {
		t.Fatal(err)
	}
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	first, err := io.ReadAll(file)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("other content"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Chtimes(path, before.ModTime(), before.ModTime()); err != nil {
		t.Fatal(err)
	}
	if err := validateExpansionFileRead(path, file, before, first); err == nil {
		t.Fatal("same-size and same-mtime change during read was accepted")
	}
}

func readExpansionTestBundle(t *testing.T, paths rt.Paths, id string) (string, ExpansionBundle) {
	t.Helper()
	path, err := expansionBundlePath(paths, id)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var bundle ExpansionBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		t.Fatal(err)
	}
	return path, bundle
}
