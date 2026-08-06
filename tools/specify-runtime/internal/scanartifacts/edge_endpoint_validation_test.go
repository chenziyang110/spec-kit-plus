package scanartifacts

import (
	"path/filepath"
	"testing"
)

func TestValidateBlocksAmbiguousPathEdgeEndpoints(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[
		{"id":"N-a","type":"capability","title":"A","confidence":"verified","paths":["shared/contract.md"],"evidence_ids":["E-001"],"attrs":{"owner":"a"}},
		{"id":"N-b","type":"capability","title":"B","confidence":"verified","paths":["shared/contract.md"],"evidence_ids":["E-001"],"attrs":{"owner":"b"}}
	]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), []byte(`{"edges":[{
		"id":"EDGE-ambig","type":"depends_on","source":"N-a","target":"shared/contract.md","confidence":"verified","evidence_ids":["E-001"],"attrs":{}
	}]}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})
	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, `edge EDGE-ambig target endpoint "shared/contract.md" is ambiguous`) {
		t.Fatalf("Errors = %#v, want ambiguous target endpoint", result.Errors)
	}
}

func TestValidateBlocksNodeMissingConfidence(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), []byte(`{"nodes":[
		{"id":"N-app","type":"capability","title":"App","paths":["src/app.go"],"evidence_ids":["E-001"],"attrs":{"owner":"app"}}
	]}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})
	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "node N-app is missing confidence") {
		t.Fatalf("Errors = %#v, want missing confidence", result.Errors)
	}
}
