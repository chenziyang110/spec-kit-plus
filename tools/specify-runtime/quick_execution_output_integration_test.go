package main

import (
	"bytes"
	"encoding/json"
	"os"
	"reflect"
	"strings"
	"testing"
)

// These require a complete checkout. Standalone helper tests do not execute
// Run, the real capability registry, or the Quick service/Work lifecycle.
func quickPackedOutputCLI(t *testing.T, args ...string) (int, Envelope) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, &stdout, &stderr, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode: %v; stdout=%s stderr=%s", err, stdout.String(), stderr.String())
	}
	return code, env
}

func TestQuickOutputPackDiscovery(t *testing.T) {
	ids := []string{"quick.item-start", "quick.allow-inline", "quick.item-accept", "quick.item-status", "quick.packet-compile", "quick.close"}
	for _, includeSchema := range []bool{false, true} {
		t.Run(map[bool]string{false: "references", true: "include-schema"}[includeSchema], func(t *testing.T) {
			root := t.TempDir()
			args := []string{"api", "pack", "--capabilities", strings.Join(ids, ","), "--project-root", root, "--format", "json"}
			if includeSchema {
				args = append(args, "--include-schema")
			}
			code, packed := quickPackedOutputCLI(t, args...)
			if code != 0 || packed.Status != "ok" || len(packed.Items) != len(ids) {
				t.Fatalf("pack failed: code=%d env=%#v", code, packed)
			}
			for index, id := range ids {
				code, shown := quickPackedOutputCLI(t, "api", "show", id, "--format", "json")
				if code != 0 {
					t.Fatalf("show %s: %#v", id, shown)
				}
				capability := shown.Data["capability"].(map[string]any)
				item := packed.Items[index].(map[string]any)
				for _, key := range []string{"id", "summary", "command", "usage", "side_effect", "input_contract"} {
					if !reflect.DeepEqual(item[key], capability[key]) {
						t.Errorf("pack changed existing %s for %s", key, id)
					}
				}
				contract, exists := item["output_contract"]
				if (index < 4) != exists {
					t.Errorf("wrong compact support for %s: %#v", id, contract)
					continue
				}
				if exists && contract.(map[string]any)["response_schema"] != quickExecutionCompactSchema {
					t.Errorf("wrong producer schema for %s", id)
				}
			}
			if entries, err := os.ReadDir(root); err != nil || len(entries) != 0 {
				t.Fatalf("discovery modified the project: %v %v", entries, err)
			}
		})
	}
}

func TestQuickOutputExecutionRejectsInvalidOptionBeforeWorkspace(t *testing.T) {
	for _, mode := range []string{"item-start", "allow-inline", "item-accept", "item-status", "packet-compile"} {
		for _, flags := range [][]string{{"--compact=false"}, {"--compact", "--compact"}} {
			t.Run(mode+"/"+strings.Join(flags, " "), func(t *testing.T) {
				root := t.TempDir()
				args := []string{"quick", mode, "missing-quick", "--project-root", root}
				args = append(args, flags...)
				code, env := quickPackedOutputCLI(t, args...)
				if code == 0 || env.Status != "usage-error" || env.Data["error_code"] != "quick-output-option-invalid" {
					t.Fatalf("did not reject before lookup: code=%d env=%#v", code, env)
				}
				if entries, err := os.ReadDir(root); err != nil || len(entries) != 0 {
					t.Fatalf("invalid presentation option modified project: %v %v", entries, err)
				}
			})
		}
	}
}
