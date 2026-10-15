package main

import (
	"bytes"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workflowregistry"
)

func TestOperationAPIDiscoveryExposesUsableContracts(t *testing.T) {
	ids := []string{"do.start", "do.record", "do.validate", "do.finish", "do.resume", "do.show", "playbook.find", "playbook.show", "playbook.update", "playbook.validate", "do.prepare", "do.next", "do.complete", "playbook.metrics"}
	var out, stderr bytes.Buffer
	if code := Run([]string{"api", "pack", "--capabilities", strings.Join(ids, ","), "--include-schema", "--format", "json"}, &out, &stderr, "test"); code != 0 {
		t.Fatalf("new installation cannot discover its required API: %d %s %s", code, out.String(), stderr.String())
	}
	for _, id := range ids {
		out.Reset()
		if code := Run([]string{"api", "show", id, "--format", "json"}, &out, &stderr, "test"); code != 0 {
			t.Fatalf("%s discovery: %s", id, out.String())
		}
		capability := requireObject(t, requireObject(t, decodeJSONObject(t, out.Bytes()), "data"), "capability")
		if capability["side_effect"] == "may-write" || !strings.Contains(capability["usage"].(string), "--format json") {
			t.Fatalf("generic fallback descriptor for %s: %#v", id, capability)
		}
		if schemaID, ok := capability["input_schema"].(string); ok {
			out.Reset()
			if code := Run([]string{"api", "schema", schemaID, "--format", "json"}, &out, &stderr, "test"); code != 0 {
				t.Fatalf("unresolvable schema %s: %s", schemaID, out.String())
			}
			schema := requireObject(t, requireObject(t, decodeJSONObject(t, out.Bytes()), "data"), "schema")
			if schema["type"] != "object" || len(requireObject(t, schema, "properties")) == 0 {
				t.Fatalf("schema does not describe a usable operation payload: %#v", schema)
			}
		}
	}
}

func TestOperationStoresCannotBypassTheirOwnersThroughGenericArtifacts(t *testing.T) {
	service := NewArtifactService(t.TempDir())
	for _, path := range []string{
		".specify/do/sessions/run/definitions/000001.json",
		".specify/do/sessions/run/session.json", ".specify/do/sessions/run/cognition-closeout.json", ".specify/do/sessions/run/evidence/report.json",
		".specify/playbooks/index.json", ".specify/playbooks/pb-test/playbook.json", ".specify/playbooks/pb-test/PLAYBOOK.md",
		".specify/playbooks/pb-test/revisions/000001.json", ".specify/playbooks/pb-test/proposals/a.json", ".specify/playbooks/pb-test/usage/run.json",
	} {
		metadata, ok := LookupArtifactType(path)
		if !ok || artifactTypeAllows(metadata, "prepare") || artifactTypeAllows(metadata, "patch") || artifactTypeAllows(metadata, "delete") {
			t.Fatalf("unprotected operation artifact %s: %#v", path, metadata)
		}
		if env := service.Prepare(ArtifactPrepareRequest{Path: path}); env.Status == "ok" || env.Data["owner"] != metadata.Owner {
			t.Fatalf("generic artifact operation bypassed %s: %#v", metadata.Owner, env)
		}
	}
}

func TestDoUsesExistingCognitionCloseoutPolicy(t *testing.T) {
	for _, name := range []string{"do", "sp-do", "/sp.do"} {
		got, err := workflowregistry.CanonicalCloseoutWorkflow(name)
		if err != nil || got != "sp-do" {
			t.Fatalf("Do mutation cannot use the shared cognition protocol: %q %v", got, err)
		}
	}
	if workflowregistry.Policies()["do"].Mode != workflowregistry.ModeMutationCloseout {
		t.Fatal("Do unexpectedly became a baseline maintenance workflow")
	}
}
