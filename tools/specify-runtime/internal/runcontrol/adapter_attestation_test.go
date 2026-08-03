package runcontrol

import (
	"context"
	"testing"
)

func TestForegroundSupervisorPersistsEnforcedAdapterCapabilityAndWorkspaceAttestation(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	ctx := context.Background()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(ctx, mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "adapter_attestation")
	supervised, err := SuperviseRun(
		ctx,
		repository,
		foregroundTestParams("adapter_attestation", "write-exact", "attested.txt", "attested"),
	)
	if err != nil {
		t.Fatal(err)
	}
	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("adapter_attestation_observer"))
	capability, err := observer.GetAdapterCapability(ctx, "test-helper")
	if err != nil {
		t.Fatal(err)
	}
	if capability.LaunchMode != AdapterLaunchManaged || !capability.EnforcesCWD ||
		!capability.EnforcesWorkspaceRoot || !capability.EnforcesWritableRoots ||
		!capability.ControlsProcessTree || !capability.SupportsHeartbeat ||
		!capability.SupportsCancellation || !capability.SupportsStructuredResult ||
		capability.CapabilityDigest == "" {
		t.Fatalf("adapter capability = %#v, want enforced modifying contract", capability)
	}
	attestation, err := observer.GetWorkspaceAttestation(ctx, supervised.Workspace.WorkspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if attestation.RunID != supervised.Run.RunID ||
		attestation.WorkspaceGeneration != supervised.Workspace.Generation ||
		attestation.CanonicalRoot != supervised.Workspace.RootPath ||
		attestation.RepoCommonDir != supervised.Workspace.RepoCommonDir ||
		attestation.BaseCommitOID != supervised.Workspace.BaseCommit ||
		attestation.SnapshotID != supervised.Snapshot.SnapshotID ||
		attestation.OverlayManifestSHA256 != supervised.Snapshot.OverlayManifestSHA256 ||
		attestation.AttestationDigest != supervised.Result.WorkspaceAttestationSHA256 {
		t.Fatalf("workspace attestation = %#v, want exact supervised Result binding", attestation)
	}
}
