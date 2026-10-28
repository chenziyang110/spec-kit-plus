package main

import (
	"bytes"
	"context"
	"encoding/json"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"os"
	"path/filepath"
	"testing"
)

func TestQuickScopeAvailabilityRealProducer(t *testing.T) {
	for _, mode := range []string{"missing", "empty", "valid"} {
		t.Run(mode, func(t *testing.T) {
			root := initCoordinationCLIRepository(t)
			workspace := filepath.Join(root, ".planning", "quick", "260805-010-exec")
			mustMkdirAllScriptDomainTest(t, workspace)
			mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), "---\nid: \"260805-010\"\nslug: \"exec\"\ntitle: \"Exec\"\nstatus: gathering\nunderstanding_confirmed: false\n---\n\n## Understanding Checkpoint\n\nx\n\n## Execution\n\ny\n")
			item := map[string]any{"id": "Q1", "deliverable": "change A", "depends_on": []any{}, "acceptance": "tests pass", "write_scope": []any{"src/a.go"}}
			if mode == "empty" {
				item["read_scope"] = []any{}
			}
			if mode == "valid" {
				item["read_scope"] = []any{"src/dependency.go"}
			}
			payload := map[string]any{"source": map[string]any{"kind": "prompt"}, "decision": map[string]any{"goal": "change A", "user_visible_result": "A works", "scope": map[string]any{"include": []any{"A"}, "exclude": []any{}}, "items": []any{item}, "reconfirmation_trigger": "scope change"}}
			raw, _ := json.Marshal(payload)
			env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "checkpoint-stage", "260805-010", "--input-json", string(raw)})
			digest := stringValue(env.Data["confirmation_digest"])
			runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "checkpoint-confirm", "260805-010", "--digest", digest})
			env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "packet-compile", "260805-010", "--item", "Q1"})
			packetRef := stringValue(env.Data["packet_path"])
			data, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(packetRef)))
			if err != nil {
				t.Fatal(err)
			}
			var packet map[string]any
			json.Unmarshal(data, &packet)
			_, present := packet["read_scope"]
			if present != (mode != "missing") {
				t.Fatalf("read declaration lost: %s", data)
			}
			doc, err := (quickService{projectRoot: root}).loadConfirmation(workspace)
			if err != nil {
				t.Fatal(err)
			}
			savedDigest := doc.ConfirmationDigest
			reads := []string{"src/other.go"}
			doc.Decision.Items[0].ReadScope = &reads
			changedDigest, err := computeQuickConfirmationDigest(doc.Decision)
			if err != nil || changedDigest != savedDigest {
				t.Fatal("execution read metadata changed approval digest")
			}
			paths := workerPlannerFixture(t, root, []string{"src/a.go", "src/dependency.go", "src/unrelated.go"})
			owner, err := store.OpenExisting(paths)
			if err != nil {
				t.Fatal(err)
			}
			for _, path := range []string{"src/a.go", "src/dependency.go", "src/unrelated.go"} {
				b, _ := os.ReadFile(filepath.Join(root, filepath.FromSlash(path)))
				_, err = owner.DB().ExecContext(context.Background(), `UPDATE evidence SET content_hash=? WHERE source_path=?`, "sha256:"+fileContentSHA256(b), path)
				if err != nil {
					t.Fatal(err)
				}
			}
			owner.Close()
			status, _ := rt.ReadStatus(paths)
			status.DirtyDebts = []rt.DebtRecord{{ID: "unrelated", Kind: "mark_dirty", Paths: []string{"src/unrelated.go"}, Reason: "pending unrelated"}}
			status.Freshness = rt.StaleFreshness
			status.Readiness = rt.ReviewReadiness
			rt.WriteStatus(paths, status)
			old, err := os.Getwd()
			if err != nil {
				t.Fatal(err)
			}
			if err = os.Chdir(root); err != nil {
				t.Fatal(err)
			}
			defer os.Chdir(old)
			var stdout, stderr bytes.Buffer
			code := Run([]string{"cognition", "check", "--task-packet", packetRef, "--format", "json"}, &stdout, &stderr, "test")
			availability := requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")
			if (availability["scope_ready"] == true) != (mode != "missing") {
				t.Fatalf("mode=%s code=%d out=%s err=%s", mode, code, stdout.String(), stderr.String())
			}
			if mode == "valid" {
				mustWriteScriptDomainTest(t, filepath.Join(root, "src", "dependency.go"), "changed bytes")
				stdout.Reset()
				Run([]string{"cognition", "check", "--task-packet", packetRef, "--format", "json"}, &stdout, &stderr, "test")
				if requireObject(t, decodeJSONObject(t, stdout.Bytes()), "data")["scope_ready"] == true {
					t.Fatal("read source drift kept Quick ready")
				}
			}
		})
	}
}

func TestQuickScopeAvailabilityMalformedReadDeclarations(t *testing.T) {
	for _, value := range []any{nil, "src/a.go", 1, []any{1}, []any{""}, []any{" src/a.go"}} {
		entry := map[string]any{"read_scope": value}
		root := t.TempDir()
		payload := map[string]any{"source": map[string]any{"kind": "prompt"}, "decision": map[string]any{"goal": "A", "user_visible_result": "A", "scope": map[string]any{"include": []any{"A"}, "exclude": []any{}}, "items": []any{map[string]any{"id": "Q1", "deliverable": "A", "depends_on": []any{}, "acceptance": "A", "read_scope": value}}, "reconfirmation_trigger": "changed"}}
		if _, err := (quickService{projectRoot: root}).stageCheckpoint(root, "quick", payload, false); err == nil {
			t.Fatalf("actual checkpoint stage accepted malformed read declaration %#v", value)
		}
		if _, err := os.Stat(filepath.Join(root, quickConfirmationFileName)); !os.IsNotExist(err) {
			t.Fatal("malformed checkpoint persisted")
		}

		if _, err := parseQuickReadScope(entry); err == nil {
			t.Fatalf("accepted %#v", value)
		}
		raw, _ := json.Marshal(entry)
		var item quickConfirmationItem
		if err := json.Unmarshal(raw, &item); err == nil {
			t.Fatalf("persisted malformed input accepted %#v", value)
		}
	}
}
