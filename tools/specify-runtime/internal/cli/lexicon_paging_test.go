package cli

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestLexiconCommandBindsContinuationAndRejectsWrongRevision(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "debug", "--mode", "catalog", "--limit", "1", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("initial page: %d %s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	page := payload["catalog_page"].(map[string]any)
	if page["snapshot_bound"] != true || page["contract_version"] != float64(1) {
		t.Fatalf("first page is not an explicit anchor: %#v", page)
	}
	revision := page["revision"].(string)
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"lexicon", "--intent", "debug", "--mode", "catalog", "--limit", "1", "--offset", "1", "--catalog-revision", revision, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("bound continuation: %d %s", code, stderr.String())
	}
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["catalog_page"].(map[string]any)["snapshot_bound"] != true {
		t.Fatal("matched continuation was not bound")
	}
	stdout.Reset()
	stderr.Reset()
	code = Run([]string{"lexicon", "--intent", "debug", "--mode", "catalog", "--limit", "1", "--offset", "1", "--catalog-revision", "sha256:" + strings.Repeat("0", 64), "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 || stdout.Len() != 0 || !strings.Contains(stderr.String(), "stale_catalog") {
		t.Fatalf("wrong revision was consumable: %d %s %s", code, stdout.String(), stderr.String())
	}
}
