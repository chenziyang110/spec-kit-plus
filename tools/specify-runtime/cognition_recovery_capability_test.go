package main

import (
	"bytes"
	"fmt"
	"strings"
	"testing"
)

func TestCognitionRecoveryCapabilityNegotiatesExistingOwner(t *testing.T) {
	const capability = "cognition.closeout.recovery.v1"
	for _, args := range [][]string{
		{"api", "ensure", "--capabilities", capability, "--format", "json"},
		{"api", "show", capability, "--format", "json"},
		{"api", "pack", "--capabilities", capability, "--format", "json"},
	} {
		var stdout, stderr bytes.Buffer
		if code := Run(args, &stdout, &stderr, "test"); code != 0 {
			t.Fatalf("%v exit=%d stdout=%s stderr=%s", args, code, &stdout, &stderr)
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		if payload["status"] != "ok" {
			t.Fatalf("%v returned %#v", args, payload)
		}
		if args[1] == "show" {
			item := requireObject(t, requireObject(t, payload, "data"), "capability")
			command, ok := item["command"].([]any)
			if !ok || len(command) != 3 || fmt.Sprint(command[0]) == "" || fmt.Sprint(command[1:]) != "[cognition closeout]" {
				t.Fatalf("semantic capability invented a command: %#v", item)
			}
			for _, phrase := range []string{"update lock", "same workflow owner and scope", "pending intent", "old ready receipt"} {
				if !strings.Contains(fmt.Sprint(item["input_contract"]), phrase) {
					t.Fatalf("recovery contract omits %q: %#v", phrase, item)
				}
			}
		}
	}
}
