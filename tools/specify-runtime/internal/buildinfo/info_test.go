package buildinfo

import (
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestFromSettingsPublishesRuntimeContractAndBuildProvenance(t *testing.T) {
	info := FromSettings("v1.2.3", map[string]string{
		"vcs.revision": "abc123",
		"vcs.modified": "true",
	})

	if info.Version != "v1.2.3" {
		t.Fatalf("Version = %q, want v1.2.3", info.Version)
	}
	if info.RuntimeProtocol != "project-cognition.v2" {
		t.Fatalf("RuntimeProtocol = %q, want project-cognition.v2", info.RuntimeProtocol)
	}
	if info.SchemaVersion != store.SchemaVersion {
		t.Fatalf("SchemaVersion = %d, want %d", info.SchemaVersion, store.SchemaVersion)
	}
	if info.SourceRevision != "abc123" {
		t.Fatalf("SourceRevision = %q, want abc123", info.SourceRevision)
	}
	if !info.Dirty {
		t.Fatal("Dirty = false, want true")
	}
}

func TestFromSettingsUsesExplicitOverridesAndStableUnknownRevision(t *testing.T) {
	oldIdentity, oldRevision, oldDirty := ReleaseIdentity, SourceRevision, BuildDirty
	ReleaseIdentity = ""
	SourceRevision, BuildDirty = "release-revision", "false"
	t.Cleanup(func() {
		ReleaseIdentity = oldIdentity
		SourceRevision, BuildDirty = oldRevision, oldDirty
	})

	info := FromSettings("", map[string]string{
		"vcs.revision": "debug-revision",
		"vcs.modified": "true",
	})
	if info.Version != "dev" {
		t.Fatalf("Version = %q, want dev", info.Version)
	}
	if info.SourceRevision != "release-revision" {
		t.Fatalf("SourceRevision = %q, want release-revision", info.SourceRevision)
	}
	if info.Dirty {
		t.Fatal("Dirty = true, want explicit false override")
	}

	SourceRevision, BuildDirty = "", ""
	info = FromSettings("dev", nil)
	if info.SourceRevision != "unknown" {
		t.Fatalf("SourceRevision = %q, want unknown", info.SourceRevision)
	}
	if info.Dirty {
		t.Fatal("Dirty = true without build metadata")
	}
}

func TestFromSettingsUsesOneCanonicalReleaseIdentityMarker(t *testing.T) {
	oldIdentity, oldRevision, oldDirty := ReleaseIdentity, SourceRevision, BuildDirty
	ReleaseIdentity = "specify-runtime.release.v1,version=v1.2.3,revision=0123456789abcdef,dirty=false"
	SourceRevision, BuildDirty = "conflicting-revision", "true"
	t.Cleanup(func() {
		ReleaseIdentity = oldIdentity
		SourceRevision, BuildDirty = oldRevision, oldDirty
	})

	info := FromSettings("dev", map[string]string{
		"vcs.revision": "debug-revision",
		"vcs.modified": "true",
	})
	if info.Version != "v1.2.3" || info.SourceRevision != "0123456789abcdef" || info.Dirty {
		t.Fatalf("release marker was not authoritative: %#v", info)
	}

	ReleaseIdentity = "specify-runtime.release.v1,version=v1.2.3,revision=missing-dirty"
	info = FromSettings("v1.2.3", nil)
	if info.Version != "dev" || info.SourceRevision != "unknown" || !info.Dirty {
		t.Fatalf("malformed release marker did not fail closed: %#v", info)
	}
}
