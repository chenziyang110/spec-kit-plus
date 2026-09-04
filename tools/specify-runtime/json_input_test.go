package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolveJSONInputBytesFromStdin(t *testing.T) {
	raw, err := resolveJSONInputBytesFrom("-", t.TempDir(), "test", "--input-json", strings.NewReader(`{"stdin":true}`))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != `{"stdin":true}` {
		t.Fatalf("stdin = %q", raw)
	}
}

func TestResolveJSONInputBytesRejectsOversizedStdin(t *testing.T) {
	_, err := resolveJSONInputBytesFrom("-", t.TempDir(), "test", "--input-json", bytes.NewReader(make([]byte, maxAgentJSONInputBytes+1)))
	if err == nil || !strings.Contains(err.Error(), "exceeds") {
		t.Fatalf("oversized stdin error = %v", err)
	}
}

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

func TestResolveAgentJSONInputBytesRejectsAtPathOutsideProject(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	path := filepath.Join(outside, "payload.json")
	if err := os.WriteFile(path, []byte(`{"outside":true}`), 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := resolveAgentJSONInputBytes("@"+path, root, "test")
	if err == nil || !strings.Contains(err.Error(), "project root") {
		t.Fatalf("outside @path error = %v", err)
	}
}

func TestResolveAgentJSONInputBytesRejectsAtPathThroughSymlink(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	link := filepath.Join(root, "linked")
	if err := os.Symlink(outside, link); err != nil {
		t.Skipf("symlink unavailable: %v", err)
	}
	if err := os.WriteFile(filepath.Join(outside, "payload.json"), []byte(`{"escaped":true}`), 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := resolveAgentJSONInputBytes("@linked/payload.json", root, "test")
	if err == nil || !strings.Contains(err.Error(), "symlink") {
		t.Fatalf("symlink @path error = %v", err)
	}
}

func TestResolveAgentJSONInputBytesRejectsDirectoryPath(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "payload"), 0o755); err != nil {
		t.Fatal(err)
	}
	_, err := resolveAgentJSONInputBytes("@payload", root, "test")
	if err == nil || !strings.Contains(err.Error(), "regular file") {
		t.Fatalf("directory @path error = %v", err)
	}
}

func TestResolveAgentJSONInputBytesRejectsChangedFileHandle(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(root, "payload.json")
	outside := filepath.Join(t.TempDir(), "outside.json")
	if err := os.WriteFile(target, []byte(`{"safe":true}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(outside, []byte(`{"outside":true}`), 0o644); err != nil {
		t.Fatal(err)
	}
	originalOpen := openAgentInputFile
	openAgentInputFile = func(string) (*os.File, error) { return os.Open(outside) }
	t.Cleanup(func() { openAgentInputFile = originalOpen })

	_, err := resolveAgentJSONInputBytes("@payload.json", root, "test")
	if err == nil || !strings.Contains(err.Error(), "changed during validation") {
		t.Fatalf("changed file handle error = %v", err)
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
	if !strings.Contains(err.Error(), "PowerShell") ||
		!strings.Contains(err.Error(), "--input-json - with stdin") ||
		!strings.Contains(strings.ToLower(err.Error()), "here-string") {
		t.Fatalf("error = %v", err)
	}
}
