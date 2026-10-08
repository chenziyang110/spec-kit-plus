package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestAssetRouteNoWorkflowNoSideEffects(t *testing.T) {
	root := t.TempDir()
	service := NewAssetService(root)
	env := service.Route(AssetRouteRequest{Purpose: "guide", Slug: "getting-started"})
	if env.Status != "ok" || env.Data["action"] != "create-new" || env.Data["path"] != "docs/guides/getting-started.md" {
		t.Fatalf("unexpected route: %#v", env)
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatal("routing created project state")
	}
	for _, relative := range []string{".specify/features/test/spec.md", ".specify/features/test/misc.md", ".specify/runtime/assets/journal.json", ".assets/manifest.json"} {
		env = service.Route(AssetRouteRequest{Purpose: "report", Path: relative})
		if env.Status != "blocked" || env.Data["action"] != "owner-required" || len(env.NextArgv) != 0 {
			t.Fatalf("owner path was rerouted: %#v", env)
		}
	}
	env = service.Route(AssetRouteRequest{Purpose: "report", FeatureID: "test", Slug: "summary"})
	if env.Data["action"] != "owner-required" {
		t.Fatalf("workflow scope invented an ordinary asset: %#v", env)
	}
}

func TestAssetRouteUsesNativeRootsAndExistingFiles(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "docs/how-to/install.md", "# Existing\n")
	service := NewAssetService(root)
	env := service.Route(AssetRouteRequest{Purpose: "guide", Slug: "install"})
	if env.Status != "ok" || env.Data["path"] != "docs/how-to/install.md" || env.Data["action"] != "reuse-existing" {
		t.Fatalf("native document was not reused: %#v", env)
	}
	env = service.Route(AssetRouteRequest{Purpose: "guide", Slug: "upgrade"})
	if env.Data["path"] != "docs/how-to/upgrade.md" {
		t.Fatalf("existing native directory ignored: %#v", env)
	}
	assetTestWrite(t, root, "docs/install.md", "# Other\n")
	env = service.Route(AssetRouteRequest{Purpose: "guide", Slug: "install"})
	if env.Status != "blocked" {
		t.Fatalf("ambiguous duplicate was silently chosen: %#v", env)
	}
	assetTestWrite(t, root, assetDefaultPolicyPath, `{"schema_version":1,"roots":{"guide":"handbook/how-to"}}`)
	env = service.Route(AssetRouteRequest{Purpose: "guide", Slug: "install"})
	if env.Status != "ok" || env.Data["path"] != "handbook/how-to/install.md" {
		t.Fatalf("explicit project route lost: %#v", env)
	}
}

func TestAssetRouteNamingAndTemporaryIsolation(t *testing.T) {
	service := NewAssetService(t.TempDir())
	env := service.Route(AssetRouteRequest{Purpose: "temporary", Slug: "preview.json", TaskID: "T012", WorkerID: "worker-a"})
	if env.Status != "ok" || env.Data["path"] != ".specify/tmp/assets/T012/worker-a/preview.json" || env.Data["retention"] != "7d" {
		t.Fatalf("temporary isolation failed: %#v", env)
	}
	other := service.Route(AssetRouteRequest{Purpose: "temporary", Slug: "preview.json", TaskID: "T012", WorkerID: "worker-b", Retention: "session"})
	if other.Status != "ok" || other.Data["path"] == env.Data["path"] || other.Data["retention"] != "session" {
		t.Fatalf("parallel worker names collided: %#v", other)
	}
	for _, request := range []AssetRouteRequest{
		{Purpose: "temporary", Slug: "preview.json", TaskID: "T012"},
		{Purpose: "temporary", Slug: "preview.json", TaskID: "T012", WorkerID: "worker", Retention: "forever"},
		{Purpose: "guide", Slug: "Final Report"},
		{Purpose: "asset", Slug: "diagram"},
		{Purpose: "report", Slug: "test", Date: "2026-02-30"},
		{Purpose: "source", Slug: "main.go"},
	} {
		if got := service.Route(request); got.Status != "invalid" {
			t.Fatalf("invalid route accepted: %#v => %#v", request, got)
		}
	}
	env = service.Route(AssetRouteRequest{Purpose: "report", Slug: "acceptance", Date: "2026-10-08", TaskID: "task-a", WorkerID: "worker-a"})
	if env.Status != "ok" || env.Data["path"] != "docs/reports/task-a/worker-a/2026-10-08-acceptance.md" {
		t.Fatalf("unexpected report destination: %#v", env)
	}
}

func TestAssetRouteDecisionSequenceIsReadOnlyAndReuses(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "docs/adr/0002-keep-api.md", "# Existing\n")
	service := NewAssetService(root)
	env := service.Route(AssetRouteRequest{Purpose: "decision", Slug: "keep-api"})
	if env.Status != "ok" || env.Data["path"] != "docs/adr/0002-keep-api.md" || env.Data["action"] != "reuse-existing" {
		t.Fatalf("decision not reused: %#v", env)
	}
	env = service.Explain(AssetRouteRequest{Purpose: "decision", Slug: "use-json"})
	if env.Status != "ok" || env.Data["path"] != "docs/adr/0003-use-json.md" || env.Data["side_effects"] != "none" {
		t.Fatalf("unexpected decision route: %#v", env)
	}
	if _, err := os.Stat(filepath.Join(root, "docs/adr/0003-use-json.md")); !os.IsNotExist(err) {
		t.Fatal("read-only decision routing reserved a file")
	}
}

func TestAssetRouteCannotUsePurposeToOverridePlacement(t *testing.T) {
	service := NewAssetService(t.TempDir())
	for _, request := range []AssetRouteRequest{
		{Purpose: "source", Path: "report.md"},
		{Purpose: "temporary", Path: "docs/report.md"},
		{Purpose: "guide", Path: "docs/Bad_Name.md"},
		{Purpose: "report", Path: "report.md"},
	} {
		if got := service.Route(request); got.Status != "blocked" {
			t.Fatalf("invalid destination was accepted: %#v => %#v", request, got)
		}
	}
	if got := service.Route(AssetRouteRequest{Purpose: "source", Path: "src/Bad_Name.md"}); got.Status != "ok" {
		t.Fatalf("native source naming was overridden: %#v", got)
	}
}
