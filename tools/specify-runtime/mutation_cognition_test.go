package main

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
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
