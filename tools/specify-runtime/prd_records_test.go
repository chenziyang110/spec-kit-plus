package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestPRDRecordCLIUpsertsListsShowsAndRemovesWithoutWholeFileAuthoring(t *testing.T) {
	projectRoot := t.TempDir()
	service := prdService{projectRoot: projectRoot}
	initialized, err := service.initRun("record-crud", "sp-prd-scan", "init-scan")
	if err != nil {
		t.Fatalf("init PRD run: %v", err)
	}
	runID := initialized["workspace"].(string)
	digests := initialized["record_digests"].(map[string]any)
	expected := digests["capability"].(string)

	first := runPRDRecordCLI(t, projectRoot, []string{
		"record-upsert", runID,
		"--surface", "capability",
		"--expected-sha256", expected,
		"--input-json", `{"id":"CAP-002","tier":"high","status":"reconstruction-ready","details":"large semantic detail stays out of list output"}`,
		"--format", "json",
	})
	if first.Status != "ok" || first.Data["record_action"] != "created" {
		t.Fatalf("first record upsert = %#v", first)
	}
	expected = first.Data["file_sha256"].(string)

	second := runPRDRecordCLI(t, projectRoot, []string{
		"record-upsert", runID,
		"--surface", "capability-ledger.json",
		"--expected-sha256", expected,
		"--input-json", `{"id":"CAP-001","tier":"critical","status":"reconstruction-ready"}`,
		"--format", "json",
	})
	if second.Status != "ok" || second.Data["record_count"].(float64) != 2 {
		t.Fatalf("second record upsert = %#v", second)
	}
	expected = second.Data["file_sha256"].(string)

	path := filepath.Join(projectRoot, ".specify", "prd-runs", runID, "capability-ledger.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read capability ledger: %v", err)
	}
	var document map[string]any
	if err := json.Unmarshal(raw, &document); err != nil {
		t.Fatalf("decode capability ledger: %v", err)
	}
	records := document["capabilities"].([]any)
	if records[0].(map[string]any)["id"] != "CAP-001" || records[1].(map[string]any)["id"] != "CAP-002" {
		t.Fatalf("records are not deterministically ordered: %#v", records)
	}

	listed, listedRaw := runPRDRecordCLIWithRaw(t, projectRoot, []string{
		"record-list", runID, "--surface", "capability", "--format", "json",
	})
	if listed.Status != "ok" || listed.Data["record_count"].(float64) != 2 {
		t.Fatalf("record list = %#v", listed)
	}
	if strings.Contains(listedRaw, "large semantic detail") {
		t.Fatalf("record list leaked full record content: %s", listedRaw)
	}

	shown := runPRDRecordCLI(t, projectRoot, []string{
		"record-show", runID, "--surface", "capability", "--record-id", "CAP-002", "--format", "json",
	})
	if shown.Status != "ok" || shown.Data["record_id"] != "CAP-002" {
		t.Fatalf("record show = %#v", shown)
	}

	removed := runPRDRecordCLI(t, projectRoot, []string{
		"record-remove", runID,
		"--surface", "capability",
		"--record-id", "CAP-002",
		"--expected-sha256", expected,
		"--format", "json",
	})
	if removed.Status != "ok" || removed.Data["record_action"] != "removed" || removed.Data["record_count"].(float64) != 1 {
		t.Fatalf("record remove = %#v", removed)
	}
}

func TestPRDRecordCLIRejectsStaleDigestAndWholeDocumentPayload(t *testing.T) {
	projectRoot := t.TempDir()
	service := prdService{projectRoot: projectRoot}
	initialized, err := service.initRun("record-guards", "sp-prd-scan", "init-scan")
	if err != nil {
		t.Fatalf("init PRD run: %v", err)
	}
	runID := initialized["workspace"].(string)
	digests := initialized["record_digests"].(map[string]any)
	expected := digests["artifact"].(string)

	stale := runPRDRecordCLI(t, projectRoot, []string{
		"record-upsert", runID,
		"--surface", "artifact",
		"--expected-sha256", strings.Repeat("0", 64),
		"--input-json", `{"id":"ART-001","status":"complete"}`,
		"--format", "json",
	})
	if stale.Status != "blocked" || !strings.Contains(fmt.Sprint(stale.Blockers), "changed since inspection") {
		t.Fatalf("stale digest result = %#v", stale)
	}

	wrapper := runPRDRecordCLI(t, projectRoot, []string{
		"record-upsert", runID,
		"--surface", "artifact",
		"--expected-sha256", expected,
		"--input-json", `{"id":"ART-001","artifacts":[]}`,
		"--format", "json",
	})
	if wrapper.Status != "blocked" || !strings.Contains(fmt.Sprint(wrapper.Blockers), "not a reconstructed") {
		t.Fatalf("whole document result = %#v", wrapper)
	}
}

func TestPRDRecordArtifactsRejectGenericPrepare(t *testing.T) {
	projectRoot := t.TempDir()
	service := prdService{projectRoot: projectRoot}
	initialized, err := service.initRun("record-owner", "sp-prd-scan", "init-scan")
	if err != nil {
		t.Fatalf("init PRD run: %v", err)
	}
	runID := initialized["workspace"].(string)
	path := filepath.ToSlash(filepath.Join(".specify", "prd-runs", runID, "capability-ledger.json"))
	var stdout, stderr bytes.Buffer
	code := Run([]string{"artifact", "prepare", "--path", path, "--format", "json", "--project-root", projectRoot}, &stdout, &stderr, "test")
	if code != 2 || !strings.Contains(stdout.String(), "prd-scan record-upsert") {
		t.Fatalf("generic prepare should be rejected: code=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
}

func runPRDRecordCLI(t *testing.T, projectRoot string, args []string) Envelope {
	t.Helper()
	env, _ := runPRDRecordCLIWithRaw(t, projectRoot, args)
	return env
}

func runPRDRecordCLIWithRaw(t *testing.T, projectRoot string, args []string) (Envelope, string) {
	t.Helper()
	args = append(args, "--project-root", projectRoot)
	var stdout bytes.Buffer
	_ = runPRDScan(args, &stdout)
	return decodeEnvelope(t, stdout.Bytes()), stdout.String()
}
