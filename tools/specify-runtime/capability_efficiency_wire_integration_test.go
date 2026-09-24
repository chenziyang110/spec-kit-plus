package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/buildinfo"
)

func capabilityBoundaryInvoke(t *testing.T, cliVersion string, args ...string) (int, Envelope, []byte) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, cliVersion)
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatal("response is not one JSON envelope", err, stderr.String())
	}
	if code != ExitCodeForStatus(env.Status) || stderr.Len() != 0 {
		t.Fatal("status or output channel mismatch", code, env.Status, stderr.String())
	}
	return code, env, stdout.Bytes()
}

func TestAPICapabilityEndpointRejectsAmbiguousJSON(t *testing.T) {
	for _, command := range []string{"ensure", "pack"} {
		for _, fromFile := range []bool{false, true} {
			root := t.TempDir()
			raw := `{"capabilities":["unavailable"],"capabiliti\u0065s":["quick.context-shadow"]}`
			input := raw
			file := filepath.Join(root, "requirements.json")
			if fromFile {
				if err := os.WriteFile(file, []byte(raw), 0600); err != nil {
					t.Fatal(err)
				}
				input = "@requirements.json"
			}
			code, env, _ := capabilityBoundaryInvoke(t, "test", "api", command, "--requires-json", input, "--project-root", root)
			if code != 2 || len(env.Items) != 0 || len(env.NextArgv) != 0 {
				t.Fatal("ambiguous selector was resolved instead of rejected", command, fromFile, code)
			}
			if fromFile {
				after, err := os.ReadFile(file)
				if err != nil || string(after) != raw {
					t.Fatal("invalid requirement evidence was changed")
				}
			}
		}
	}
}

func TestAPICapabilityEndpointPackLimitsCompleteMetadata(t *testing.T) {
	// Inflate only the explicit build-version argument. Descriptors, dispatch,
	// identity construction and serialization remain the production owners.
	// This exercises the boundary even when today's descriptor list is small.
	release := buildinfo.ReleaseIdentity
	buildinfo.ReleaseIdentity = ""
	defer func() { buildinfo.ReleaseIdentity = release }()
	version := strings.Repeat("v", maxAPIPackOutputBytes)
	code, env, wire := capabilityBoundaryInvoke(t, version, "api", "pack", "--capabilities", "quick.context-shadow", "--format", "json")
	if code != 2 || len(wire) > maxAPIPackOutputBytes || len(env.Items) != 0 ||
		env.Data["error_code"] != "api-capability-output-limit" || bytes.Contains(wire, []byte(version)) {
		t.Fatal("runtime metadata bypassed the complete response limit", code, len(wire))
	}
}

func TestAPICapabilityEndpointEnsureLimitsRepeatedUnknownIDs(t *testing.T) {
	// Syntactically valid, below the input limit, but repeated in requested and
	// missing fields. Oversized diagnostics must not escape via an error path.
	unknown := strings.Repeat("x", 70*1024)
	code, env, wire := capabilityBoundaryInvoke(t, "test", "api", "ensure", "--capabilities", unknown)
	if code != 2 || len(wire) > maxAPIPackOutputBytes || env.Data["error_code"] != "api-capability-output-limit" {
		t.Fatal("unknown selection produced an unbounded response", code, len(wire))
	}
	if bytes.Contains(wire, []byte(unknown)) || len(env.NextArgv) != 0 {
		t.Fatal("overflow response retained the payload or scheduled work")
	}
}

func TestAPICapabilityEndpointPreservesShadowDiscoveryContract(t *testing.T) {
	_, help, _ := capabilityBoundaryInvoke(t, "test", "quick", "context-shadow", "--help")
	code, shown, _ := capabilityBoundaryInvoke(t, "test", "api", "show", "quick.context-shadow", "--format", "json")
	if code != 0 {
		t.Fatal(shown)
	}
	code, packed, _ := capabilityBoundaryInvoke(t, "test", "api", "pack", "--capabilities", "quick.context-shadow", "--include-schema", "--format", "json")
	if code != 0 || len(packed.Items) != 1 {
		t.Fatal(packed)
	}
	show := shown.Data["capability"].(map[string]any)
	pack := packed.Items[0].(map[string]any)
	if !reflect.DeepEqual(show["output_contract"], pack["output_contract"]) ||
		!reflect.DeepEqual(pack["output_contract"], help.Data["output_contract"]) || pack["side_effect"] != "read-only" {
		t.Fatal("Help/Show/Pack contract drift")
	}
	if pack["output_contract"].(map[string]any)["authorizes_execution"] != false {
		t.Fatal("diagnostic acquired authority")
	}
	code, ensured, _ := capabilityBoundaryInvoke(t, "test", "api", "ensure", "--requires-json", `{"capabilities":["quick.context-shadow"],"metadata":{"note":"保留"}}`)
	if code != 0 || len(ensured.Data["missing"].([]any)) != 0 {
		t.Fatal("legitimate selector stopped working", ensured)
	}
}

func TestAPICapabilityEndpointMissingCapabilityStillBlocked(t *testing.T) {
	code, env, _ := capabilityBoundaryInvoke(t, "test", "api", "ensure", "--capabilities", "quick.not-an-available-capability")
	if code != 10 || env.Status != "blocked" || len(env.Data["missing"].([]any)) != 1 {
		t.Fatal("ordinary missing capability no longer reports blocked", env)
	}
}

func TestAPICapabilityEndpointClosedPipeIsDeliveryFailure(t *testing.T) {
	for _, command := range []string{"ensure", "pack"} {
		reader, writer, err := os.Pipe()
		if err != nil {
			t.Fatal(err)
		}
		if err := reader.Close(); err != nil {
			_ = writer.Close()
			t.Fatal(err)
		}
		code := Run([]string{"api", command, "--capabilities", "quick.context-shadow"}, writer, io.Discard, "test")
		_ = writer.Close()
		if code != 1 {
			t.Fatal("failed public API output returned success", command, code)
		}
	}
}
