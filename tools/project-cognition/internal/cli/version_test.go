package cli

import (
	"bytes"
	"encoding/json"
	"testing"
)

func TestVersionCommandPublishesMachineReadableRuntimeContract(t *testing.T) {
	var stdout, stderr bytes.Buffer
	if code := Run([]string{"version", "--format", "json"}, &stdout, &stderr, "v9.9.9"); code != 0 {
		t.Fatalf("version code=%d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("decode version JSON: %v; output=%s", err, stdout.String())
	}
	if payload["version"] != "v9.9.9" || payload["runtime_protocol"] != "project-cognition.v2" || payload["schema_version"] != float64(5) {
		t.Fatalf("version payload = %#v", payload)
	}
	if payload["source_revision"] == "" {
		t.Fatalf("version payload has no source_revision: %#v", payload)
	}
	if _, ok := payload["dirty"].(bool); !ok {
		t.Fatalf("version payload dirty = %#v, want bool", payload["dirty"])
	}
}
