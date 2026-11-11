package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func boundFallbackQuickFixture(t *testing.T) (string, string, string) {
	t.Helper()
	root, workspace, id := newQuickOptimizationFixture(t)
	r3SeedGraph(t, root, []string{"src/a.go"})
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "integration.json"), map[string]any{"integration": "codex"})
	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1"})
	if env.Status != "ok" {
		t.Fatal(env)
	}
	mustWriteScriptDomainTest(t, filepath.Join(root, "src", "a.go"), "accepted source\n")
	result := map[string]any{
		"task_id": "Q1", "status": "success", "summary": "accepted source",
		"cognition_delta":    workerDeltaFixture("Q1", "accepted source", []string{"src/a.go"}),
		"validation_results": []any{map[string]any{"command": "required check", "status": "passed"}},
	}
	if code, got := runResultInProject(t, root, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", marshalJSONForCLI(t, result)}); code != 0 {
		t.Fatal(got)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "current readback"})
	if env.Status != "ok" {
		t.Fatal(env)
	}
	r3Claim(t, root, os.Getenv("SPECIFY_WORK_ID"), []string{projectRelativeSlash(root, workspace), ".specify/project-cognition"})
	return root, workspace, id
}

func downgradeFallbackGraph(t *testing.T, root string) {
	t.Helper()
	paths, _ := rt.ResolvePaths(root)
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("UPDATE metadata SET value_json='2' WHERE key='schema_version'"); err != nil {
		db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
}

func TestQuickBoundFallbackClosesAcceptedWorkWithVisibleGraphDebt(t *testing.T) {
	for _, missing := range []bool{false, true} {
		t.Run(map[bool]string{false: "legacy", true: "missing"}[missing], func(t *testing.T) {
			root, workspace, id := boundFallbackQuickFixture(t)
			paths, _ := rt.ResolvePaths(root)
			if missing {
				if err := os.Remove(paths.DatabasePath); err != nil {
					t.Fatal(err)
				}
			} else {
				downgradeFallbackGraph(t, root)
			}
			statusBefore, _ := os.ReadFile(paths.StatusPath)
			graphBefore, _ := os.ReadFile(paths.DatabasePath)
			scope := projectRelativeSlash(root, workspace)
			proof := r3Seal(t, root, r3Begin(t, root, scope, "quick", os.Getenv("SPECIFY_WORK_ID"), nil, nil))
			env := runScriptDomainEnvelope(t, runQuick, []string{
				"--project-root", root, "cognition-closeout", id, "--result-state", "mark-dirty",
				"--binding-id", proof.ID, "--reason", "index recovery remains pending",
			})
			if env.Status != "ok" || env.Data["allowed_close"] != true {
				t.Fatalf("bound fallback: %+v", env)
			}
			loaded, err := loadMutationCognitionReceipt(workspace)
			if err != nil || loaded.GraphDebt == nil || loaded.StrongBinding == nil || loaded.Scope != scope || loaded.ResultState != "mark-dirty" {
				t.Fatalf("missing proof/debt: %+v %v", loaded, err)
			}
			if !equalCloseoutPaths(loaded.ChangedPaths, proof.OwnedDelta) {
				t.Fatal("fallback lost exact source delta")
			}
			gate := (quickService{projectRoot: root}).cognitionCloseoutStatus(workspace)
			if gate["allowed_close"] != true || gate["graph_debt"] == nil {
				t.Fatalf("reloaded gate: %#v", gate)
			}
			if env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "close", id, "resolved"}); env.Status != "ok" {
				t.Fatalf("actual close: %+v", env)
			}
			statusAfter, _ := os.ReadFile(paths.StatusPath)
			graphAfter, _ := os.ReadFile(paths.DatabasePath)
			if !bytes.Equal(statusBefore, statusAfter) || !bytes.Equal(graphBefore, graphAfter) {
				t.Fatal("unclean fallback changed cognition graph or status")
			}
			if missing {
				if _, err := os.Stat(paths.DatabasePath); !os.IsNotExist(err) {
					t.Fatal("fallback created a missing graph")
				}
			}
		})
	}
}

func TestQuickBoundFallbackRefusesHealthyStaleAndPendingProof(t *testing.T) {
	for _, scenario := range []string{"healthy", "stale", "pending"} {
		t.Run(scenario, func(t *testing.T) {
			root, workspace, id := boundFallbackQuickFixture(t)
			scope := projectRelativeSlash(root, workspace)
			proof := r3Seal(t, root, r3Begin(t, root, scope, "quick", os.Getenv("SPECIFY_WORK_ID"), nil, nil))
			paths, _ := rt.ResolvePaths(root)
			switch scenario {
			case "stale":
				downgradeFallbackGraph(t, root)
				mustWriteScriptDomainTest(t, filepath.Join(root, "src", "a.go"), "source changed after validation\n")
			case "pending":
				downgradeFallbackGraph(t, root)
				payload := marshalJSONForCLI(t, map[string]any{"workflow": "sp-quick", "changed_paths": []string{"src/a.go"}})
				if _, _, _, err := ensureCloseoutIntent(paths, "sp-quick", scope, "pending fixture", payload, "", "", []string{"src/a.go"}); err != nil {
					t.Fatal(err)
				}
			}
			env := runScriptDomainEnvelope(t, runQuick, []string{
				"--project-root", root, "cognition-closeout", id, "--result-state", "mark-dirty",
				"--binding-id", proof.ID, "--reason", "refused fallback",
			})
			if env.Status == "ok" {
				t.Fatalf("%s proof allowed fallback", scenario)
			}
			if _, err := os.Stat(mutationCognitionReceiptPath(workspace)); !os.IsNotExist(err) {
				t.Fatal("refused fallback published a receipt")
			}
		})
	}
}

func TestQuickLegacyFallbackDoesNotAdvertiseResolvedClose(t *testing.T) {
	root, workspace, id := boundFallbackQuickFixture(t)
	downgradeFallbackGraph(t, root)
	env := runScriptDomainEnvelope(t, runQuick, []string{
		"--project-root", root, "cognition-closeout", id, "--result-state", "mark-dirty", "--reason", "audit only",
	})
	if env.Status != "ok" || len(env.NextArgv) != 0 || env.Data["allowed_close"] != false {
		t.Fatalf("legacy audit advertised close: %+v", env)
	}
	gate := (quickService{projectRoot: root}).cognitionCloseoutStatus(workspace)
	if gate["allowed_close"] == true || gate["blocked_reason"] != "legacy_receipt_missing_strong_binding" {
		t.Fatalf("legacy audit became proof: %#v", gate)
	}
}

func TestSharedMutationReceiptBoundFallbackIsQuickOnly(t *testing.T) {
	root, workspace, _ := boundFallbackQuickFixture(t)
	downgradeFallbackGraph(t, root)
	scope := projectRelativeSlash(root, workspace)
	proof := r3Seal(t, root, r3Begin(t, root, scope, "quick", os.Getenv("SPECIFY_WORK_ID"), nil, nil))
	var out bytes.Buffer
	args := []string{"--project-root", root, "--workflow", "sp-quick", "--scope-dir", scope, "--result-state", "mark-dirty", "--binding-id", proof.ID, "--reason", "index recovery pending"}
	if code := runMutationCognitionReceiptCLI(args, &out); code != 0 {
		t.Fatalf("shared Quick fallback: %s", out.String())
	}
	var env Envelope
	if err := json.Unmarshal(out.Bytes(), &env); err != nil || env.Data["allowed_close"] != true {
		t.Fatalf("shared proof: %s", out.String())
	}
	out.Reset()
	args[3] = "sp-implement"
	if code := runMutationCognitionReceiptCLI(args, &out); code == 0 || !strings.Contains(out.String(), "requires workflow sp-quick") {
		t.Fatalf("non-Quick accepted binding fallback: %s", out.String())
	}
}
