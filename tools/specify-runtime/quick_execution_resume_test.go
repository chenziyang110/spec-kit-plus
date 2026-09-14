package main

import (
	"errors"
	"reflect"
	"strings"
	"testing"
)

func TestQuickResumePersistencePropagatesFailures(t *testing.T) {
	failure := errors.New("injected write failure")
	for _, tc := range []struct {
		name       string
		persistErr error
		projectErr error
		wantCalls  []string
		wantPhase  string
	}{
		{"success", nil, nil, []string{"persist", "project"}, ""},
		{"canonical failure stops projection", failure, nil, []string{"persist"}, "confirmation persistence"},
		{"projection failure is not success", nil, failure, []string{"persist", "project"}, "status projection"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var calls []string
			err := persistQuickExecutionResume(
				func() error { calls = append(calls, "persist"); return tc.persistErr },
				func() error { calls = append(calls, "project"); return tc.projectErr },
			)
			if !reflect.DeepEqual(calls, tc.wantCalls) {
				t.Fatalf("calls = %v, want %v", calls, tc.wantCalls)
			}
			if tc.wantPhase == "" {
				if err != nil {
					t.Fatal(err)
				}
				return
			}
			if !errors.Is(err, failure) {
				t.Fatalf("underlying failure was hidden: %v", err)
			}
			var typed *quickResumePersistenceError
			if !errors.As(err, &typed) || typed.phase != tc.wantPhase {
				t.Fatalf("wrong recovery phase: %v", err)
			}
			if !strings.Contains(err.Error(), "retain the current Work claim") {
				t.Fatalf("missing safe recovery guidance: %v", err)
			}
		})
	}
}

func TestQuickResumePersistenceCanRetryAfterRepair(t *testing.T) {
	broken := true
	persistCalls, projectCalls := 0, 0
	persist := func() error { persistCalls++; return nil }
	project := func() error {
		projectCalls++
		if broken {
			return errors.New("projection unavailable")
		}
		return nil
	}
	if err := persistQuickExecutionResume(persist, project); err == nil {
		t.Fatal("failed projection reported success")
	}
	broken = false
	if err := persistQuickExecutionResume(persist, project); err != nil {
		t.Fatalf("retry after repair: %v", err)
	}
	if persistCalls != 2 || projectCalls != 2 {
		t.Fatalf("retry skipped persistence: %d, %d", persistCalls, projectCalls)
	}
}
