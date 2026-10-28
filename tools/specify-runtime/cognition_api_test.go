package main

import (
	"bytes"
	"reflect"
	"strings"
	"testing"
)

func TestCognitionVersionCapabilitiesDescribeRealReadOnlyCommands(t *testing.T) {
	cases := []struct {
		id      string
		command []string
		flags   []string
	}{
		{"cognition.expansion.snapshot.v2", []string{"specify-runtime", "cognition", "expand"}, []string{"-id", "-section"}},
		{"cognition.claim-evidence.page.v1", []string{"specify-runtime", "cognition", "expand"}, []string{"-id", "-section", "-offset"}},
		{"cognition.catalog.snapshot.v1", []string{"specify-runtime", "cognition", "lexicon", "--mode", "catalog"}, []string{"-mode", "-offset", "-catalog-revision", "-limit"}},
	}
	for _, tc := range cases {
		t.Run(tc.id, func(t *testing.T) {
			var out, errOut bytes.Buffer
			if code := Run([]string{"api", "show", tc.id, "--format", "json"}, &out, &errOut, "test"); code != 0 {
				t.Fatalf("api show failed: %d %s %s", code, out.String(), errOut.String())
			}
			data := requireObject(t, decodeJSONObject(t, out.Bytes()), "data")
			descriptor := requireObject(t, data, "capability")
			command := requireStringArray(t, descriptor, "command")
			// Envelope publication binds argv[0] to the running executable.
			if len(command) == 0 || command[0] == "" || !reflect.DeepEqual(command[1:], tc.command[1:]) || descriptor["side_effect"] != "read-only" {
				t.Fatalf("unsafe or invented descriptor: %#v", descriptor)
			}
			if len(descriptor["input_contract"].(string)) < 80 || len(descriptor["output_contract"].(string)) < 80 || strings.HasPrefix(descriptor["summary"].(string), "Execute") {
				t.Fatalf("missing concrete contract: %#v", descriptor)
			}
			out.Reset()
			errOut.Reset()
			args := append(append([]string{}, command[1:]...), "--help")
			code := Run(args, &out, &errOut, "test")
			help := out.String() + errOut.String()
			// Go flag help returns 2; the supported route must expose its real flags.
			if (code != 0 && code != 2) || !strings.Contains(help, "Usage of ") {
				t.Fatalf("descriptor help did not resolve: %d %s", code, help)
			}
			for _, flag := range tc.flags {
				if !strings.Contains(help, flag) {
					t.Fatalf("real help missing %s: %s", flag, help)
				}
			}
		})
	}
}

func TestCognitionVersionCapabilitiesEnsureAndPack(t *testing.T) {
	ids := []string{"cognition.expansion.snapshot.v2", "cognition.claim-evidence.page.v1", "cognition.catalog.snapshot.v1"}
	for _, operation := range []string{"ensure", "pack"} {
		var out, errOut bytes.Buffer
		if code := Run([]string{"api", operation, "--capabilities", strings.Join(ids, ","), "--format", "json"}, &out, &errOut, "test"); code != 0 {
			t.Fatalf("api %s failed: %d %s %s", operation, code, out.String(), errOut.String())
		}
		payload := decodeJSONObject(t, out.Bytes())
		if operation == "pack" {
			items := payload["items"].([]any)
			if len(items) != len(ids) {
				t.Fatalf("pack omitted requested cognition capabilities: %s", out.String())
			}
			for _, item := range items {
				descriptor := requireObjectValue(t, item)
				if descriptor["side_effect"] != "read-only" || !strings.Contains(descriptor["usage"].(string), "cognition ") {
					t.Fatalf("pack invented a marker command: %#v", descriptor)
				}
			}
		}
	}
}
