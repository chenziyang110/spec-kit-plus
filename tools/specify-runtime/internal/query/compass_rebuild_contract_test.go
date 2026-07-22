package query

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
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
