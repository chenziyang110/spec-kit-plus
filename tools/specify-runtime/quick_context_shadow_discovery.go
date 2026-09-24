package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
)

// Public descriptor dispatcher used by runAPI and apiCapabilityDescriptor.
// Existing capabilities retain their original descriptor owner unchanged.
// Keep the optional diagnostic's contract in one helper rather than copying
// its fields into the large legacy schema switch.
func runAPIShowWithQuickShadow(args []string, stdout io.Writer) int {
	return dispatchQuickShadowDescriptor(args, stdout, runAPIShow, writeEnvelope)
}

func dispatchQuickShadowDescriptor(args []string, stdout io.Writer,
	legacy func([]string, io.Writer) int, encode func(io.Writer, Envelope) int,
) int {
	if stdout == nil || legacy == nil || encode == nil {
		return 1
	}
	id, _, ok := apiObjectID(args, "capability")
	if !ok || id != quickShadowCapability {
		return legacy(args, stdout)
	}
	if !containsCapability(defaultCapabilities(), id) {
		return encode(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown capability %q", id)))
	}
	capability := map[string]any{
		"id":      id,
		"command": []string{"specify-runtime", "quick", "context-shadow"},
	}
	describeQuickShadowCapability(capability)
	env := NewEnvelope("ok", fmt.Sprintf("Capability %s expanded.", id))
	env.Data["capability"] = capability
	env.ShowArgv = []string{"specify-runtime", "quick", "context-shadow", "--help"}
	return encode(stdout, env)
}

// Augment only the legacy Quick help envelope, never its execution path.
// The legacy owner still selects its existing fields. Explicit context-shadow
// invocations reach the strict parser before the broad legacy help detection.
func writeQuickHelpWithShadow(
	ctx context.Context, args []string, stdout io.Writer,
	legacy func([]string, io.Writer) int, encode func(io.Writer, Envelope) int,
) int {
	if ctx == nil || stdout == nil || legacy == nil || encode == nil {
		return 1
	}
	if ctx.Err() != nil {
		return writeQuickShadowCLIEnvelopeWithContext(ctx, stdout, quickShadowCancelledEnvelope(), encode)
	}
	var raw bytes.Buffer
	code := legacy(args, &raw)
	if code != 0 {
		n, err := stdout.Write(raw.Bytes())
		if err != nil || n != raw.Len() {
			return 1
		}
		return code
	}
	var env Envelope
	decoder := json.NewDecoder(&raw)
	decoder.UseNumber()
	if err := decoder.Decode(&env); err != nil || env.Status != "ok" || env.Data == nil {
		return 1
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		return 1
	}
	commands, ok := env.Data["commands"].([]any)
	if !ok {
		return 1
	}
	found := false
	for _, command := range commands {
		name, ok := command.(string)
		if !ok {
			return 1
		}
		found = found || name == "context-shadow"
	}
	if !found {
		commands = append(commands, "context-shadow")
	}
	env.Data["commands"] = commands
	env.Data["context_shadow"] = map[string]any{
		"usage": quickShadowCommandUsage, "output_contract": quickShadowOutputContract(),
	}
	return writeQuickShadowCLIEnvelopeWithContext(ctx, stdout, env, encode)
}
