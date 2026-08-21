package query

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	_ "modernc.org/sqlite"
)

func TestCompassNeedsRebuildReportsConcreteReasons(t *testing.T) {
	tests := []struct {
		name         string
		prepare      func(t *testing.T) rt.Paths
		wantCode     string
		wantEvidence map[string]any
	}{
		{
			name: "missing baseline",
			prepare: func(t *testing.T) rt.Paths {
				return queryTestPaths(t)
			},
			wantCode: "missing_baseline",
			wantEvidence: map[string]any{
				"status_exists":      false,
				"graph_store_exists": false,
			},
		},
		{
			name: "unsupported graph schema",
			prepare: func(t *testing.T) rt.Paths {
				paths := queryTestPaths(t)
				seedCompassModelSwitchGraph(t, paths)
				setCompassSchemaVersion(t, paths, 1)
				return paths
			},
			wantCode: "unsupported_schema",
			wantEvidence: map[string]any{
				"detected_schema": float64(1),
				"required_schema": float64(store.SchemaVersion),
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			payload := serializedCompassPayload(t, tt.prepare(t))
			if payload["readiness"] != rt.NeedsRebuildReadiness {
				t.Fatalf("readiness = %#v, want %q; payload=%#v", payload["readiness"], rt.NeedsRebuildReadiness, payload)
			}

			reason := rebuildReasonByCode(t, payload, tt.wantCode)
			message, ok := reason["message"].(string)
			if !ok || message == "" {
				t.Fatalf("rebuild reason %q message = %#v, want non-empty string; reason=%#v", tt.wantCode, reason["message"], reason)
			}
			evidence, ok := reason["evidence"].(map[string]any)
			if !ok {
				t.Fatalf("rebuild reason %q evidence = %#v, want object; reason=%#v", tt.wantCode, reason["evidence"], reason)
			}
			for key, want := range tt.wantEvidence {
				if got := evidence[key]; got != want {
					t.Fatalf("rebuild reason %q evidence[%q] = %#v, want %#v; reason=%#v", tt.wantCode, key, got, want, reason)
				}
			}
		})
	}
}

func TestCompassNeedsRebuildReturnsProfileAwareWorkflowRoutes(t *testing.T) {
	payload := serializedCompassPayload(t, queryTestPaths(t))

	action, ok := payload["recommended_next_action"].(map[string]any)
	if !ok {
		t.Fatalf("recommended_next_action = %#v, want structured action object instead of an internal action string", payload["recommended_next_action"])
	}
	if action["action_id"] != "project_cognition.rebuild" {
		t.Fatalf("recommended_next_action.action_id = %#v, want project_cognition.rebuild; action=%#v", action["action_id"], action)
	}
	routes, ok := action["workflow_routes"].(map[string]any)
	if !ok {
		t.Fatalf("recommended_next_action.workflow_routes = %#v, want profile route object; action=%#v", action["workflow_routes"], action)
	}
	assertWorkflowSteps(t, routes, "advanced", []string{"spx-map-rebuild"})
	assertWorkflowSteps(t, routes, "classic", []string{"sp-map-scan", "sp-map-build"})
}

func TestCompassBlockedUsesCompatibleGraphForDegradedNavigation(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.RecommendedNextAction = "run_map_update"
	status.Dirty = true
	status.DirtyReasons = []string{"closeout transport failed"}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Compass(paths, CompassInput{
		Intent: "specify",
		Query:  "runtimeOverride provider model switch",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Readiness != rt.BlockedReadiness || payload.CompassState != compassStateBlocked {
		t.Fatalf("readiness/state = %q/%q, want %q/%q", payload.Readiness, payload.CompassState, rt.BlockedReadiness, compassStateBlocked)
	}
	if payload.RecommendedNextAction.ActionID != "run_map_update" {
		t.Fatalf("recommended_next_action = %#v, want blocked recovery action unchanged", payload.RecommendedNextAction)
	}
	assertDegradedCompassNavigation(t, payload)
}

func TestCompassNeedsRebuildUsesCompatibleGraphForDegradedNavigationWithoutChangingRebuildAction(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "run_map_scan_build"
	status.GraphReady = false
	status.Dirty = true
	status.StaleReasons = []string{"baseline must be rebuilt"}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Compass(paths, CompassInput{
		Intent: "plan",
		Query:  "runtimeOverride provider model switch",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Readiness != rt.NeedsRebuildReadiness || payload.CompassState != compassStateBlocked {
		t.Fatalf("readiness/state = %q/%q, want %q/%q", payload.Readiness, payload.CompassState, rt.NeedsRebuildReadiness, compassStateBlocked)
	}
	if payload.RecommendedNextAction.ActionID != compassRecommendedActionRebuild || payload.RecoveryAction != compassRecommendedActionRebuild {
		t.Fatalf("rebuild action = %#v recovery=%q, want rebuild action unchanged", payload.RecommendedNextAction, payload.RecoveryAction)
	}
	assertDegradedCompassNavigation(t, payload)
}

func TestCompassLegacyBlockedGreenfieldRepairsToRebuildAndUsesRecordedStalePaths(t *testing.T) {
	paths := queryTestPaths(t)
	seedGreenfieldEmptyRuntime(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.RecommendedNextAction = "run_map_update"
	status.GraphReady = false
	status.Dirty = true
	status.StalePaths = []string{
		"../outside.go",
		`C:\outside.go`,
		"backend/internal/bom/arrival.go",
		"backend/internal/bom/service.go",
		"frontend/src/views/BomPage.vue",
		"frontend/src/api/bom.ts",
		"backend/internal/project/service.go",
		"backend/internal/auth/permissions.go",
		"docs/bom-arrival.md",
	}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Compass(paths, CompassInput{
		Intent: "specify",
		Query:  "BOM arrival control",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Readiness != rt.NeedsRebuildReadiness || payload.RecommendedNextAction.ActionID != compassRecommendedActionRebuild {
		t.Fatalf("readiness/action = %q/%#v, want repaired rebuild route", payload.Readiness, payload.RecommendedNextAction)
	}
	foundGreenfieldConflict := false
	for _, reason := range payload.RebuildReasons {
		if hasString(reason.Evidence.Reasons, rt.GreenfieldBaselineHasProjectCodeReason) {
			foundGreenfieldConflict = true
			break
		}
	}
	if !foundGreenfieldConflict {
		t.Fatalf("rebuild reasons = %#v, want greenfield project-code conflict", payload.RebuildReasons)
	}
	assertDegradedCompassNavigation(t, payload)
	if len(payload.EvidenceLanes) != 1 || payload.EvidenceLanes[0].ID != "degraded:status-stale-paths" {
		t.Fatalf("evidence lanes = %#v, want one typed status stale-path lane", payload.EvidenceLanes)
	}
	if got := len(payload.MinimalLiveReads); got != maxCompassPathsPerLane {
		t.Fatalf("minimal_live_reads count = %d, want bounded %d from status stale paths", got, maxCompassPathsPerLane)
	}
	if !hasString(payload.MinimalLiveReads, "backend/internal/bom/arrival.go") || !hasString(payload.MinimalLiveReads, "frontend/src/views/BomPage.vue") {
		t.Fatalf("minimal_live_reads = %#v, want recorded BOM stale paths", payload.MinimalLiveReads)
	}
	if hasString(payload.MinimalLiveReads, "../outside.go") || hasString(payload.MinimalLiveReads, "C:/outside.go") {
		t.Fatalf("minimal_live_reads = %#v, want repository-relative paths only", payload.MinimalLiveReads)
	}
}

func TestCompassUnsafeBlockedRuntimeDoesNotEmitDegradedNavigation(t *testing.T) {
	tests := []struct {
		name    string
		prepare func(t *testing.T) rt.Paths
	}{
		{
			name: "missing graph store",
			prepare: func(t *testing.T) rt.Paths {
				paths := queryTestPaths(t)
				status := rt.DefaultStatus(paths)
				status.Status = "stale"
				status.Freshness = rt.StaleFreshness
				status.Readiness = rt.BlockedReadiness
				status.RecommendedNextAction = "run_map_update"
				if err := rt.WriteStatus(paths, status); err != nil {
					t.Fatal(err)
				}
				return paths
			},
		},
		{
			name: "incompatible graph schema",
			prepare: func(t *testing.T) rt.Paths {
				paths := queryTestPaths(t)
				seedCompassModelSwitchGraph(t, paths)
				setCompassSchemaVersion(t, paths, 1)
				return paths
			},
		},
		{
			name: "unreadable graph store",
			prepare: func(t *testing.T) rt.Paths {
				paths := queryTestPaths(t)
				status := rt.DefaultStatus(paths)
				status.Status = "stale"
				status.Freshness = rt.StaleFreshness
				status.Readiness = rt.BlockedReadiness
				status.RecommendedNextAction = "run_map_update"
				if err := rt.WriteStatus(paths, status); err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(paths.DatabasePath, []byte("not a sqlite database"), 0o644); err != nil {
					t.Fatal(err)
				}
				return paths
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			payload, err := Compass(tt.prepare(t), CompassInput{
				Intent: "specify",
				Query:  "runtimeOverride provider model switch",
			})
			if err != nil {
				t.Fatal(err)
			}
			if len(payload.MinimalLiveReads) != 0 || len(payload.EvidenceLanes) != 0 {
				t.Fatalf("unsafe runtime emitted navigation reads=%#v lanes=%#v", payload.MinimalLiveReads, payload.EvidenceLanes)
			}
			if payload.Degraded {
				t.Fatalf("Degraded = true, want false when no graph was safely read")
			}
		})
	}
}

func TestCompassNeedsRebuildPreservesInProgressScanResumeAction(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "scanning"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "complete_scan_packets"
	status.GraphReady = false
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := serializedCompassPayload(t, paths)
	action, ok := payload["recommended_next_action"].(map[string]any)
	if !ok || action["action_id"] != "complete_scan_packets" {
		t.Fatalf("recommended_next_action = %#v, want complete_scan_packets continuation", payload["recommended_next_action"])
	}
	if _, exists := action["workflow_routes"]; exists {
		t.Fatalf("recommended_next_action.workflow_routes = %#v, want omitted for scan continuation", action["workflow_routes"])
	}
	if _, exists := payload["rebuild_reasons"]; exists {
		t.Fatalf("rebuild_reasons = %#v, want omitted while scan packets are resumable", payload["rebuild_reasons"])
	}
	if _, exists := payload["recovery_action"]; exists {
		t.Fatalf("recovery_action = %#v, want omitted while status owns the resume action", payload["recovery_action"])
	}
}

func TestCompassStatusRebuildReasonPreservesRecordedCauseAndScope(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "run_map_scan_build"
	status.Dirty = true
	status.StaleReasons = []string{"affected closure cannot be bounded safely"}
	status.DirtyReasons = []string{"project structure changed"}
	status.StalePaths = []string{"src/ownership.go"}
	status.DirtyScopePaths = []string{"templates/commands"}
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := serializedCompassPayload(t, paths)
	reason := rebuildReasonByCode(t, payload, "status_requires_rebuild")
	evidence, ok := reason["evidence"].(map[string]any)
	if !ok {
		t.Fatalf("rebuild reason evidence = %#v, want object", reason["evidence"])
	}
	assertJSONStringsEqual(t, evidence["reasons"], []string{
		"affected closure cannot be bounded safely",
		"project structure changed",
	})
	assertJSONStringsEqual(t, evidence["affected_paths"], []string{
		"src/ownership.go",
		"templates/commands",
	})
}

func TestCompassGraphMetadataFailureUsesTypedRebuildReason(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(
		context.Background(),
		`UPDATE metadata SET value_json = '"wrong-runtime"' WHERE key = 'runtime_format'`,
	); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	payload := serializedCompassPayload(t, paths)
	action, ok := payload["recommended_next_action"].(map[string]any)
	if !ok || action["action_id"] != "project_cognition.rebuild" {
		t.Fatalf("recommended_next_action = %#v, want rebuild", payload["recommended_next_action"])
	}
	reason := rebuildReasonByCode(t, payload, "graph_store_metadata_invalid")
	evidence, ok := reason["evidence"].(map[string]any)
	if !ok || evidence["diagnostic"] == "" {
		t.Fatalf("reason evidence = %#v, want diagnostic", reason["evidence"])
	}
}

func TestAgreementRebuildReasonsMapsGraphUnreadableCauseExplicitly(t *testing.T) {
	paths := queryTestPaths(t)
	if err := os.MkdirAll(filepath.Dir(paths.StatusPath), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.StatusPath, []byte(`{}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.DatabasePath, []byte("not a sqlite database"), 0o644); err != nil {
		t.Fatal(err)
	}
	reasons := AgreementRebuildReasons(paths, runtimegate.Agreement{
		CauseCode:  runtimegate.CauseGraphStoreUnreadable,
		CauseOwner: runtimegate.CauseOwnerGraphStore,
		Errors:     []string{"read DB active generation: disk I/O error"},
	})
	if len(reasons) != 1 || reasons[0].Code != "graph_store_unreadable" {
		t.Fatalf("reasons = %#v, want explicit graph_store_unreadable", reasons)
	}
}

func serializedCompassPayload(t *testing.T, paths rt.Paths) map[string]any {
	t.Helper()
	payload, err := Compass(paths, CompassInput{
		Intent: "plan",
		Query:  "find the project cognition route",
	})
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	var encoded map[string]any
	if err := json.Unmarshal(data, &encoded); err != nil {
		t.Fatal(err)
	}
	return encoded
}

func rebuildReasonByCode(t *testing.T, payload map[string]any, wantCode string) map[string]any {
	t.Helper()
	reasons, ok := payload["rebuild_reasons"].([]any)
	if !ok || len(reasons) == 0 {
		t.Fatalf("rebuild_reasons = %#v, want non-empty array for readiness=%q; payload=%#v", payload["rebuild_reasons"], rt.NeedsRebuildReadiness, payload)
	}
	for _, item := range reasons {
		reason, ok := item.(map[string]any)
		if ok && reason["code"] == wantCode {
			return reason
		}
	}
	t.Fatalf("rebuild_reasons = %#v, want reason code %q", reasons, wantCode)
	return nil
}

func assertWorkflowSteps(t *testing.T, routes map[string]any, profile string, want []string) {
	t.Helper()
	route, ok := routes[profile].(map[string]any)
	if !ok {
		t.Fatalf("workflow_routes[%q] = %#v, want route object; routes=%#v", profile, routes[profile], routes)
	}
	steps, ok := route["steps"].([]any)
	if !ok || len(steps) != len(want) {
		t.Fatalf("workflow_routes[%q].steps = %#v, want %#v", profile, route["steps"], want)
	}
	for index, wantStep := range want {
		if steps[index] != wantStep {
			t.Fatalf("workflow_routes[%q].steps[%d] = %#v, want %q", profile, index, steps[index], wantStep)
		}
	}
}

func assertJSONStringsEqual(t *testing.T, value any, want []string) {
	t.Helper()
	items, ok := value.([]any)
	if !ok || len(items) != len(want) {
		t.Fatalf("JSON strings = %#v, want %#v", value, want)
	}
	for index, wantValue := range want {
		if items[index] != wantValue {
			t.Fatalf("JSON strings[%d] = %#v, want %q; all=%#v", index, items[index], wantValue, value)
		}
	}
}

func setCompassSchemaVersion(t *testing.T, paths rt.Paths, version int) {
	t.Helper()
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = db.Close() })
	if _, err := db.ExecContext(
		context.Background(),
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', ?, CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = CURRENT_TIMESTAMP`,
		fmt.Sprint(version),
	); err != nil {
		t.Fatal(err)
	}
}

func assertDegradedCompassNavigation(t *testing.T, payload CompassPayload) {
	t.Helper()
	if !payload.Degraded || payload.Freshness != rt.StaleFreshness {
		t.Fatalf("degraded/freshness = %v/%q, want true/%q", payload.Degraded, payload.Freshness, rt.StaleFreshness)
	}
	if len(payload.EvidenceLanes) == 0 || len(payload.MinimalLiveReads) == 0 {
		t.Fatalf("degraded navigation lanes/reads = %#v/%#v, want bounded non-empty hints", payload.EvidenceLanes, payload.MinimalLiveReads)
	}
	if len(payload.EvidenceLanes) > maxCompassLanes || len(payload.MinimalLiveReads) > maxCompassReads || compassLanePathCount(payload.EvidenceLanes) > maxCompassReads {
		t.Fatalf("degraded navigation exceeded bounds: lanes=%d reads=%d lane_paths=%d", len(payload.EvidenceLanes), len(payload.MinimalLiveReads), compassLanePathCount(payload.EvidenceLanes))
	}
	for _, lane := range payload.EvidenceLanes {
		if lane.Freshness != rt.StaleFreshness {
			t.Fatalf("lane %q freshness = %q, want %q", lane.ID, lane.Freshness, rt.StaleFreshness)
		}
	}
	if !compassDiagnosticsContain(payload.CoverageDiagnostics, "stale_cognition_degraded_navigation") {
		t.Fatalf("coverage diagnostics = %#v, want explicit stale degraded-navigation warning", payload.CoverageDiagnostics)
	}
	if !strings.Contains(strings.ToLower(payload.Summary), "stale") || !strings.Contains(strings.ToLower(payload.Summary), "live") {
		t.Fatalf("summary = %q, want stale/live-verification warning", payload.Summary)
	}
}
