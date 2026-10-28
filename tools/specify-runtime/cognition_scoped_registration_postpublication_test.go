package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scopedregistration"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestR4ScopedRegisterNonDoPostPublicationDriftStalesScopedClaims(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)

	scopedRegistrationAfterApplyHook = func(payload scopedregistration.Payload) error {
		if len(payload.Registered["claims"]) == 0 {
			t.Fatalf("post-apply hook saw no registered claims in payload: %#v", payload.Registered)
		}
		return os.WriteFile(filepath.Join(fixture.root, filepath.FromSlash(fixture.newPath)), []byte("package app\n\nfunc NewOwner() string {\n\treturn \"r4-new-owner-drift\"\n}\n"), 0o644)
	}
	t.Cleanup(func() { scopedRegistrationAfterApplyHook = nil })

	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, r4ScopedRegistrationJSON(t, request))
	if code == 0 {
		t.Fatalf("post-publication proof drift returned success: %+v", envelope)
	}
	if got := r4EnvelopeText(envelope); !strings.Contains(got, "native proof changed during scoped registration") {
		t.Fatalf("drift failure did not report native proof drift: %s", got)
	}

	for _, claimID := range []string{"C-r4-owner-verified", "C-r4-consumer-supported"} {
		state, fresh, reason := r4ClaimLifecycle(t, fixture.root, claimID)
		if state != string(claim.StateStale) || fresh != string(claim.FreshnessStale) || !strings.Contains(reason, "scoped_registration_postcommit_source_drift:") {
			t.Fatalf("claim %s lifecycle = %q/%q/%q, want stale/stale scoped drift", claimID, state, fresh, reason)
		}
	}

	state, fresh, reason := r4ClaimLifecycle(t, fixture.root, "C-r4-unrelated-deps")
	if state != string(claim.StateVerified) || fresh != string(claim.FreshnessFresh) || reason != "fixture-unrelated-preserved" {
		t.Fatalf("unrelated claim lifecycle = %q/%q/%q, want preserved verified/fresh fixture reason", state, fresh, reason)
	}

	paths, err := rt.ResolvePaths(fixture.root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if !status.Dirty || status.Freshness != rt.StaleFreshness || status.Readiness != rt.BlockedReadiness {
		t.Fatalf("status after drift = dirty:%v freshness:%q readiness:%q, want dirty stale blocked", status.Dirty, status.Freshness, status.Readiness)
	}
	if !r4StatusHasScopedDriftDebt(status.DirtyDebts, fixture.newPath) {
		t.Fatalf("status missing scoped source drift debt for %s: %#v", fixture.newPath, status.DirtyDebts)
	}
}

func TestR4ScopedRegisterNonDoPostPublicationDriftPropagatesDebtPersistenceFailure(t *testing.T) {
	fixture := r4ScopedRegistrationFixture(t)
	request := r4ScopedRegistrationRequest(t, fixture)
	paths, err := rt.ResolvePaths(fixture.root)
	if err != nil {
		t.Fatal(err)
	}

	scopedRegistrationAfterApplyHook = func(payload scopedregistration.Payload) error {
		if len(payload.Registered["claims"]) == 0 {
			t.Fatalf("post-apply hook saw no registered claims in payload: %#v", payload.Registered)
		}
		if err := os.WriteFile(filepath.Join(fixture.root, filepath.FromSlash(fixture.newPath)), []byte("package app\n\nfunc NewOwner() string {\n\treturn \"r4-new-owner-drift\"\n}\n"), 0o644); err != nil {
			return err
		}
		if err := os.Remove(paths.StatusPath); err != nil {
			return err
		}
		return os.Mkdir(paths.StatusPath, 0o755)
	}
	t.Cleanup(func() { scopedRegistrationAfterApplyHook = nil })

	code, envelope := r4RunScopedRegisterWithStdin(t, fixture.root, r4ScopedRegistrationJSON(t, request))
	if code == 0 {
		t.Fatalf("post-publication drift persistence failure returned success: %+v", envelope)
	}
	if got := r4EnvelopeText(envelope); !strings.Contains(got, "additionally failed to mark scoped drift") {
		t.Fatalf("drift failure did not propagate scoped debt persistence error: %s", got)
	}
}

func r4EnvelopeText(envelope Envelope) string {
	parts := []string{envelope.Status, envelope.Summary}
	for _, blocker := range envelope.Blockers {
		parts = append(parts, strings.TrimSpace(fmt.Sprint(blocker)))
	}
	return strings.Join(parts, "\n")
}

func r4ClaimLifecycle(t *testing.T, root, claimID string) (string, string, string) {
	t.Helper()
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	var state, freshness, reason string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT state, freshness, state_reason FROM claims WHERE generation_id = ? AND id = ?`, generationID, claimID).Scan(&state, &freshness, &reason); err != nil {
		t.Fatalf("read claim %s lifecycle: %v", claimID, err)
	}
	return state, freshness, reason
}

func r4StatusHasScopedDriftDebt(debts []rt.DebtRecord, wantPath string) bool {
	wantPath = filepath.ToSlash(strings.TrimSpace(wantPath))
	for _, debt := range debts {
		if debt.Kind != "scoped_registration_postcommit_source_drift" || strings.TrimSpace(debt.UpdateID) == "" {
			continue
		}
		for _, path := range debt.Paths {
			if filepath.ToSlash(strings.TrimSpace(path)) == wantPath {
				return true
			}
		}
	}
	return false
}
