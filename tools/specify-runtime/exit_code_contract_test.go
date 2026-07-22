package main

import "testing"

func TestExitCodeForStatusUsesStableAgentContract(t *testing.T) {
	tests := []struct {
		status string
		want   int
	}{
		{status: "ok", want: 0},
		{status: "warn", want: 0},
		{status: "repaired", want: 0},
		{status: "blocked", want: 10},
		{status: "repairable-block", want: 10},
		{status: "invalid", want: 2},
		{status: "usage-error", want: 2},
		{status: "error", want: 1},
	}

	for _, test := range tests {
		t.Run(test.status, func(t *testing.T) {
			if got := ExitCodeForStatus(test.status); got != test.want {
				t.Fatalf("ExitCodeForStatus(%q) = %d, want %d", test.status, got, test.want)
			}
		})
	}
}
