package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"testing"
)

func TestQuickShadowCLICancelledBeforeOwnerRead(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	calls := 0
	env := quickShadowCLIEnvelopeWithContext(ctx, []string{"--workspace", "demo", "--item", "Q1"}, func(context.Context, quickShadowSelection) (any, error) { calls++; return "unexpected", nil })
	if calls != 0 || env.Status != "blocked" || env.Data["error_code"] != "quick-shadow-cancelled" || len(env.NextArgv) != 0 {
		t.Fatal(calls, env)
	}
	if _, ok := env.Data["report"]; ok {
		t.Fatal("cancelled query returned report")
	}
}

func TestQuickShadowCLIDiscardsOwnerResultAfterCancellation(t *testing.T) {
	for _, failure := range []bool{false, true} {
		ctx, cancel := context.WithCancel(context.Background())
		seen := false
		env := quickShadowCLIEnvelopeWithContext(ctx, []string{"--workspace", "demo", "--item", "Q1"}, func(actual context.Context, _ quickShadowSelection) (any, error) {
			seen = actual == ctx
			cancel()
			if failure {
				return nil, errors.New("owner error")
			}
			return map[string]any{"snapshot": "late"}, nil
		})
		if !seen || env.Status != "blocked" || env.Data["error_code"] != "quick-shadow-cancelled" {
			t.Fatal(env)
		}
		if _, ok := env.Data["report"]; ok {
			t.Fatal("late success escaped")
		}
	}
}

func TestQuickShadowCLICancelDuringEncodingDropsSnapshot(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	env := newQuickShadowCLIEnvelope("ok", "snapshot")
	env.Data["report"] = map[string]any{"private_snapshot": "MUST_NOT_ESCAPE"}
	calls := 0
	encode := func(w io.Writer, e Envelope) int {
		calls++
		if calls == 1 {
			cancel()
		}
		if err := json.NewEncoder(w).Encode(e); err != nil {
			return 1
		}
		return ExitCodeForStatus(e.Status)
	}
	var out bytes.Buffer
	code := writeQuickShadowCLIEnvelopeWithContext(ctx, &out, env, encode)
	if code != 10 || calls != 2 || bytes.Contains(out.Bytes(), []byte("MUST_NOT_ESCAPE")) {
		t.Fatal(code, calls, out.String())
	}
	var actual Envelope
	if err := json.Unmarshal(out.Bytes(), &actual); err != nil {
		t.Fatal(err)
	}
	if actual.Data["error_code"] != "quick-shadow-cancelled" || actual.Data["authorizes_execution"] != false || len(actual.NextArgv) != 0 {
		t.Fatal(actual)
	}
}

func TestQuickShadowCLINilCancellationDependenciesFailClosed(t *testing.T) {
	env := quickShadowCLIEnvelopeWithContext(nil, []string{"--workspace", "demo", "--item", "Q1"}, nil)
	if env.Status != "error" {
		t.Fatal(env)
	}
	var out bytes.Buffer
	if writeQuickShadowCLIEnvelopeWithContext(nil, &out, env, nil) != 1 || out.Len() != 0 {
		t.Fatal("nil dependencies wrote output")
	}
}
