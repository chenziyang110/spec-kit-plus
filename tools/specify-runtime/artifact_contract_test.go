package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestArtifactPrepareSubmitAndProgressiveShow(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)

	prepared := service.Prepare(ArtifactPrepareRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
	})
	if prepared.Status != "ok" {
		t.Fatalf("prepare status = %q, want ok: %#v", prepared.Status, prepared)
	}
	leaseID, ok := prepared.Data["lease_id"].(string)
	if !ok || leaseID == "" {
		t.Fatalf("prepare lease_id = %#v, want non-empty string", prepared.Data["lease_id"])
	}
	if path := prepared.Data["canonical_path"]; path != ".specify/features/001-runtime/spec-contract.json" {
		t.Fatalf("prepare canonical_path = %#v", path)
	}

	content := json.RawMessage(`{"schema_version":1,"status":"ready","target_need":"A deterministic runtime"}`)
	submitted := service.Submit(ArtifactSubmitRequest{
		LeaseID: leaseID,
		Content: content,
	})
	if submitted.Status != "ok" {
		t.Fatalf("submit status = %q, want ok: %#v", submitted.Status, submitted)
	}
	artifactPath := filepath.Join(projectRoot, ".specify", "features", "001-runtime", "spec-contract.json")
	stored, err := os.ReadFile(artifactPath)
	if err != nil {
		t.Fatalf("read canonical artifact: %v", err)
	}
	if !json.Valid(stored) {
		t.Fatalf("canonical artifact is not JSON: %q", stored)
	}

	summary := service.Show(ArtifactShowRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
		View:      "summary",
	})
	if summary.Status != "ok" {
		t.Fatalf("summary status = %q, want ok: %#v", summary.Status, summary)
	}
	if _, leaked := summary.Data["content"]; leaked {
		t.Fatalf("summary unexpectedly exposed full content: %#v", summary.Data)
	}
	if summary.ShowArgv[0] != "specify-runtime" {
		t.Fatalf("summary show_argv = %#v, want runtime expansion command", summary.ShowArgv)
	}

	full := service.Show(ArtifactShowRequest{
		FeatureID: "001-runtime",
		Kind:      "spec-contract",
		View:      "full",
	})
	if full.Status != "ok" || full.Data["content"] == nil {
		t.Fatalf("full view = %#v, want content", full)
	}
}

func TestArtifactLeaseIsSingleUseAndCannotRedirectOutput(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewArtifactService(projectRoot)
	prepared := service.Prepare(ArtifactPrepareRequest{FeatureID: "001-runtime", Kind: "spec"})
	leaseID := prepared.Data["lease_id"].(string)

	first := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Spec\n")})
	if first.Status != "ok" {
		t.Fatalf("first submit = %#v", first)
	}
	second := service.Submit(ArtifactSubmitRequest{LeaseID: leaseID, Content: []byte("# Replayed\n")})
	if second.Status != "blocked" {
		t.Fatalf("replayed submit status = %q, want blocked: %#v", second.Status, second)
	}

	outside := filepath.Join(projectRoot, "redirected.md")
	if _, err := os.Stat(outside); !os.IsNotExist(err) {
		t.Fatalf("artifact service created an unregistered output: %v", err)
	}
}

