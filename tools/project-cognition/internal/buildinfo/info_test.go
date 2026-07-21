package buildinfo

import (
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
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
	oldRevision, oldDirty := SourceRevision, BuildDirty
	SourceRevision, BuildDirty = "release-revision", "false"
	t.Cleanup(func() {
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
