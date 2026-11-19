package main

import (
	"context"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

type doTimingPhase struct {
	Calls     int     `json:"calls"`
	ElapsedMS float64 `json:"elapsed_ms"`
}

// Timings are invocation-local diagnostics. They never enter a checkpoint or
// contain paths, environment values, or native tool output.
type doTimings struct {
	started time.Time
	phases  map[string]doTimingPhase
	counts  map[string]int64
}

func newDoTimings() *doTimings {
	return &doTimings{started: time.Now(), phases: map[string]doTimingPhase{}, counts: map[string]int64{}}
}

func doTimingFrom(values []*doTimings) *doTimings {
	if len(values) > 0 {
		return values[0]
	}
	return nil
}

func (timings *doTimings) record(name string, duration time.Duration) {
	if timings == nil {
		return
	}
	phase := timings.phases[name]
	phase.Calls++
	phase.ElapsedMS += float64(duration) / float64(time.Millisecond)
	timings.phases[name] = phase
}

func (timings *doTimings) count(name string, count int64) {
	if timings != nil {
		timings.counts[name] += count
	}
}

func (timings *doTimings) phase(name string) func() {
	if timings == nil {
		return func() {}
	}
	start := time.Now()
	return func() { timings.record(name, time.Since(start)) }
}

func (timings *doTimings) workContext() context.Context {
	ctx := context.Background()
	if timings == nil {
		return ctx
	}
	return runcontrol.ObserveWriteLock(ctx, func(wait time.Duration) { timings.record("work_write_lock", wait) })
}

func (timings *doTimings) envelopeData() map[string]any {
	if timings == nil {
		return nil
	}
	return map[string]any{"timings": map[string]any{
		"total_ms": float64(time.Since(timings.started)) / float64(time.Millisecond),
		"phases":   timings.phases,
		"counts":   timings.counts,
	}}
}

func doWorkspaceStatus(root string, timings *doTimings) (runcontrol.WorkspaceStatus, error) {
	defer timings.phase("workspace_status")()
	status, err := runcontrol.ReadWorkspaceStatus(context.Background(), root)
	timings.count("workspace_dirty_paths", int64(len(status.DirtyPaths)))
	return status, err
}
