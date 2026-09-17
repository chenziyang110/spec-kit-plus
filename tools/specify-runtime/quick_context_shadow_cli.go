package main

import (
	"context"
	"fmt"
	"io"
)

// Internal command adapter prepared for the separate quick context-shadow
// registration change. Run/RunContext and capability discovery do not call or
// advertise it yet. No generated workflow or existing executor consumes it.
func runQuickContextShadow(args []string, stdout io.Writer) int {
	return runQuickContextShadowWithContext(context.Background(), args, stdout)
}

func runQuickWithContext(ctx context.Context, args []string, stdout io.Writer) int {
	if len(args) > 0 && args[0] == "context-shadow" {
		return runQuickContextShadowWithContext(ctx, args[1:], stdout)
	}
	return runQuick(args, stdout)
}

func runQuickContextShadowWithContext(ctx context.Context, args []string, stdout io.Writer) int {
	env := quickShadowCLIEnvelopeWithContext(ctx, args, func(ctx context.Context, selected quickShadowSelection) (any, error) {
		report, err := (quickService{projectRoot: selected.projectRoot}).contextShadowWithContext(ctx, selected.workspace, selected.item)
		if err != nil {
			return nil, err
		}
		if report.Schema != "quick-context-shadow-v1" || report.Mode != "shadow-only" ||
			report.AuthorizesExecution || report.LiveCodeVerified ||
			report.Workspace != selected.workspace || report.ItemID != selected.item {
			return nil, fmt.Errorf("quick-shadow-owner-contract-invalid: refuse an ambiguous or authorizing report")
		}
		return report, nil
	})
	return writeQuickShadowCLIEnvelopeWithContext(ctx, stdout, env, writeEnvelope)
}
