package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestMutationCognitionReceiptGatesImplementAndWorkflowStages(t *testing.T) {
	project := t.TempDir()
	feature := filepath.Join(project, ".specify", "features", "001-mut")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := requireMutationCognitionReceipt(feature, "sp-implement"); err == nil {
		t.Fatalf("expected missing receipt to fail")
	}

	var stdout bytes.Buffer
	code := Run([]string{
		"cognition", "mutation-receipt",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--feature-dir", filepath.ToSlash(filepath.Join(".specify", "features", "001-mut")),
		"--result-state", "mark-dirty",
		"--reason", "greenfield_empty; bootstrap map later",
		"--format", "json",
	}, &stdout, &bytes.Buffer{}, "test")
	if code != 0 {
		t.Fatalf("mutation-receipt exit=%d out=%s", code, stdout.String())
	}
	if _, err := os.Stat(filepath.Join(feature, "cognition-closeout.json")); err != nil {
		t.Fatalf("receipt missing: %v", err)
	}
	if err := requireMutationCognitionReceipt(feature, "sp-implement"); err != nil {
		t.Fatalf("receipt should allow close: %v", err)
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	if data["result_state"] != "mark-dirty" {
		t.Fatalf("data=%#v", data)
	}
	if !strings.Contains(fmt.Sprint(data["warning"]), "temporary") {
		t.Fatalf("mark-dirty should warn about continuous map growth: %#v", data)
	}
}

func TestMutationCognitionReceiptRejectsPlanningWorkflows(t *testing.T) {
	var stdout bytes.Buffer
	code := Run([]string{
		"cognition", "mutation-receipt",
		"--workflow", "sp-specify",
		"--feature-dir", ".specify/features/x",
		"--result-state", "ready",
		"--format", "json",
	}, &stdout, &bytes.Buffer{}, "test")
	if code == 0 {
		t.Fatalf("planning workflow should not own mutation receipt")
	}
}

func TestMutationCognitionStatusRejectsReadyReceiptWhenUpdateIsNotFinalized(t *testing.T) {
	project := t.TempDir()
	feature := filepath.Join(project, ".specify", "features", "001-mut")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(project)
	if err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.PartialRefreshFreshness
	status.Readiness = rt.ReviewReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-db"
	status.LastUpdateID = "upd-current"
	status.LastUpdateOutcome = "partial_refresh"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := recordMutationCognitionReceipt(feature, "sp-implement", ".specify/features/001-mut", "ready", "", "upd-current", []string{})
	if err != nil {
		t.Fatal(err)
	}
	if payload["allowed_close"] == true {
		t.Fatalf("record payload allowed close for unfinalized update: %#v", payload)
	}

	gate := mutationCognitionStatus(feature)
	if gate["allowed_close"] == true {
		t.Fatalf("gate allowed ready receipt without complete-refresh finalization: %#v", gate)
	}
	if err := requireMutationCognitionReceipt(feature, "sp-implement"); err == nil {
		t.Fatalf("requireMutationCognitionReceipt accepted unfinalized ready receipt")
	}
}

func TestMutationCognitionStatusRejectsAutoRepairablePartialReceipt(t *testing.T) {
	project := t.TempDir()
	feature := filepath.Join(project, ".specify", "features", "001-mut")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	evidence, err := json.Marshal([]string{"partial_refresh_reasons: missing_passing_verification_result"})
	if err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	code := Run([]string{
		"cognition", "mutation-receipt",
		"--project-root", project,
		"--workflow", "sp-implement",
		"--feature-dir", filepath.ToSlash(filepath.Join(".specify", "features", "001-mut")),
		"--result-state", "partial",
		"--reason", "missing_passing_verification_result",
		"--evidence-json", string(evidence),
		"--format", "json",
	}, &stdout, &bytes.Buffer{}, "test")
	if code != 0 {
		t.Fatalf("mutation-receipt should record non-closeable partial debt: %s", stdout.String())
	}
	payload := decodeJSONObject(t, stdout.Bytes())
	data := requireObject(t, payload, "data")
	if data["allowed_close"] == true {
		t.Fatalf("auto-repairable partial allowed close: %#v", data)
	}
	if !strings.Contains(fmt.Sprint(data["blocked_reason"]), "missing_passing_verification_result") {
		t.Fatalf("blocked reason should name missing verification repair path: %#v", data)
	}
	if err := requireMutationCognitionReceipt(feature, "sp-implement"); err == nil {
		t.Fatalf("requireMutationCognitionReceipt accepted auto-repairable partial")
	}
}

func TestMutationCognitionStatusAllowsNonRepairablePartialDebt(t *testing.T) {
	project := t.TempDir()
	feature := filepath.Join(project, ".specify", "features", "001-mut")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}

	payload, err := recordMutationCognitionReceipt(feature, "sp-implement", ".specify/features/001-mut", "partial", "external SDK docs offline; debt tracked for map-update", "", []string{"debt:external-docs-offline"})
	if err != nil {
		t.Fatal(err)
	}
	if payload["allowed_close"] != true {
		t.Fatalf("non-repairable partial debt should allow close: %#v", payload)
	}
	if err := requireMutationCognitionReceipt(feature, "sp-implement"); err != nil {
		t.Fatalf("requireMutationCognitionReceipt rejected non-repairable partial debt: %v", err)
	}
}
