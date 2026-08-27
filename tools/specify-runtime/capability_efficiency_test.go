package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestAPIEfficiencyCommandsRejectUnknownOptions(t *testing.T) {
	for _, test := range []struct {
		args        []string
		wantBlocker string
	}{
		{args: []string{"api", "ensure", "--capabilities", "api.show", "--legacy", "true", "--format", "json"}, wantBlocker: "unknown option"},
		{args: []string{"api", "ensure", "--capabilities", "api.show", "--capabilities", "api.list", "--format", "json"}, wantBlocker: "was repeated"},
		{args: []string{"api", "pack", "--capabilities", "api.show", "--mystery", "true", "--format", "json"}, wantBlocker: "unknown option"},
		{args: []string{"api", "pack", "--capabilities", "api.show", "--format", "json", "--format", "json"}, wantBlocker: "was repeated"},
	} {
		var stdout, stderr bytes.Buffer
		code := Run(test.args, &stdout, &stderr, "test")
		if code != 2 {
			t.Fatalf("%v exit=%d stdout=%s stderr=%s", test.args, code, stdout.String(), stderr.String())
		}
		payload := decodeJSONObject(t, stdout.Bytes())
		if payload["status"] != "usage-error" {
			t.Fatalf("%v payload=%#v, want usage-error", test.args, payload)
		}
		blockers := payload["blockers"].([]any)
		if len(blockers) == 0 || !strings.Contains(blockers[0].(string), test.wantBlocker) {
			t.Fatalf("%v blockers=%#v, want %q", test.args, blockers, test.wantBlocker)
		}
	}
}
