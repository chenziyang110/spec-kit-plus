package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveAgentJSONInputBytesInline(t *testing.T) {
	raw, err := resolveAgentJSONInputBytes(`{"ok":true}`, t.TempDir(), "test")
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != `{"ok":true}` {
		t.Fatalf("inline = %q", raw)
	}
}

func TestResolveAgentJSONInputBytesAtPath(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "payload.json")
	if err := os.WriteFile(path, []byte(`{"from":"file"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	raw, err := resolveAgentJSONInputBytes("@payload.json", root, "test")
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != `{"from":"file"}` {
		t.Fatalf("@path = %q", raw)
	}

	raw, err = resolveAgentJSONInputBytes("@"+path, root, "test")
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != `{"from":"file"}` {
		t.Fatalf("absolute @path = %q", raw)
	}
}

func TestReadAgentJSONInputRejectsBareInputFlag(t *testing.T) {
	_, err := readAgentJSONInput([]string{"--input", "x.json", "--input-json", `{}`}, t.TempDir(), "bind-consumer")
	if err == nil || !strings.Contains(err.Error(), "does not accept agent-authored input files via --input") {
		t.Fatalf("bare --input error = %v", err)
	}
}

func TestReadAgentJSONObjectFromAtPath(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "obj.json")
	if err := os.WriteFile(path, []byte(`{"semantic_delta":[],"required_refs":[],"blockers":[],"recovery":null}`), 0o644); err != nil {
		t.Fatal(err)
	}
	obj, err := readAgentJSONObject([]string{"--input-json", "@obj.json"}, root, "bind-consumer")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := obj["semantic_delta"].([]any); !ok {
		t.Fatalf("object = %#v", obj)
	}
}

func TestFormatJSONObjectErrorHintsPowerShellQuoting(t *testing.T) {
	_, err := decodeAgentJSONObject([]byte(`{handoff_goal:test}`), "handoff")
	if err == nil {
		t.Fatal("expected decode error")
	}
	if !strings.Contains(err.Error(), "PowerShell") || !strings.Contains(err.Error(), "@payload.json") {
		t.Fatalf("error = %v", err)
	}
}
