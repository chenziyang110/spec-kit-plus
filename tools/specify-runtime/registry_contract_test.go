package main

import (
	"bytes"
	"fmt"
	"io"
	"reflect"
	"testing"
)

type fakeCognitionCommand struct {
	called bool
	args   []string
}

func (*fakeCognitionCommand) Name() string {
	return "cognition"
}

func (*fakeCognitionCommand) Capabilities() []string {
	return []string{"cognition.status", "cognition.query"}
}

func (command *fakeCognitionCommand) Run(args []string, stdout, _ io.Writer) int {
	command.called = true
	command.args = append([]string(nil), args...)
	_, _ = fmt.Fprintln(stdout, `{"status":"ok"}`)
	return 0
}

func TestCognitionCommandCanBeRegisteredAndResolved(t *testing.T) {
	registry := NewRegistry()
	command := &fakeCognitionCommand{}

	if err := registry.Register(command); err != nil {
		t.Fatalf("register cognition command: %v", err)
	}
	registered, ok := registry.Lookup("cognition")
	if !ok {
		t.Fatal("lookup cognition command: not found")
	}
	if capabilities := registry.Capabilities(); !reflect.DeepEqual(
		capabilities,
		[]string{"cognition.query", "cognition.status"},
	) {
		t.Fatalf("registry capabilities = %#v, want sorted cognition capabilities", capabilities)
	}

	var stdout, stderr bytes.Buffer
	if code := registered.Run([]string{"status", "--format", "json"}, &stdout, &stderr); code != 0 {
		t.Fatalf("registered cognition exit code = %d, stderr=%q", code, stderr.String())
	}
	if !command.called || !reflect.DeepEqual(command.args, []string{"status", "--format", "json"}) {
		t.Fatalf("registered cognition call = called:%t args:%#v", command.called, command.args)
	}
}
