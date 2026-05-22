package delta

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestBeginCreatesSessionWithNormalizedInitialDirtyPaths(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}

	session, err := Begin(BeginInput{
		Root:              root,
		RuntimeDir:        runtimeDir,
		OriginCommand:     "quick",
		OriginFeatureDir:  ".specify/features/001-demo",
		OriginLaneID:      "lane-1",
		BaseCommit:        "abc123",
		Branch:            "main",
		InitialDirtyPaths: []string{"./src/b.go", "src/a.go", "src/a.go"},
	})
	if err != nil {
		t.Fatal(err)
	}

	if session.SessionID == "" {
		t.Fatal("SessionID is empty")
	}
	if got := session.Git.InitialDirtyPaths; len(got) != 2 || got[0] != "src/a.go" || got[1] != "src/b.go" {
		t.Fatalf("InitialDirtyPaths = %#v", got)
	}
	if _, err := os.Stat(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "session.json")); err != nil {
		t.Fatal(err)
	}
	if info, err := os.Stat(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events")); err != nil || !info.IsDir() {
		t.Fatalf("events dir: info=%v err=%v", info, err)
	}
}

func TestAppendEventPersistsNormalizedPaths(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}

	event, err := Append(AppendInput{
		RuntimeDir:        runtimeDir,
		SessionID:         session.SessionID,
		EventType:         "worker_result",
		OriginCommand:     "quick",
		OriginLaneID:      "lane-1",
		Phase:             "execute",
		ChangedPaths:      []string{"./src/a.go", "src/a.go"},
		ReadPaths:         []string{"tests/a_test.go"},
		BehaviorSurfaces:  []string{"cli:update"},
		KnownUnknowns:     []string{"consumer edge not proven"},
		Verification:      []string{"go test ./... PASS"},
		GeneratedSurfaces: []string{"templates/commands/quick.md"},
	})
	if err != nil {
		t.Fatal(err)
	}

	if event.EventID == "" {
		t.Fatal("EventID is empty")
	}
	loaded, err := Load(runtimeDir, session.SessionID)
	if err != nil {
		t.Fatal(err)
	}
	if len(loaded.Events) != 1 {
		t.Fatalf("events = %d", len(loaded.Events))
	}
	if got := loaded.Events[0].ChangedPaths; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("ChangedPaths = %#v", got)
	}
}

func TestAppendPacketFilePersistsEvent(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	event, err := AppendPacketFile(runtimeDir, session.SessionID, packet)
	if err != nil {
		t.Fatal(err)
	}

	if event.EventType != "worker_result" {
		t.Fatalf("EventType = %q", event.EventType)
	}
	if got := event.ChangedPaths; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("ChangedPaths = %#v", got)
	}
}

func TestLoadSortsEventsByParsedCreatedAtTimestamp(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}

	eventsDir := filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events")
	events := []Event{
		{
			EventID:   "event-later",
			SessionID: session.SessionID,
			EventType: "worker_result",
			CreatedAt: "2026-05-22T12:00:00.12Z",
		},
		{
			EventID:   "event-earlier",
			SessionID: session.SessionID,
			EventType: "worker_result",
			CreatedAt: "2026-05-22T12:00:00.1Z",
		},
	}
	for _, event := range events {
		data, err := json.MarshalIndent(event, "", "  ")
		if err != nil {
			t.Fatal(err)
		}
		data = append(data, '\n')
		if err := os.WriteFile(filepath.Join(eventsDir, event.EventID+".json"), data, 0o644); err != nil {
			t.Fatal(err)
		}
	}

	loaded, err := Load(runtimeDir, session.SessionID)
	if err != nil {
		t.Fatal(err)
	}
	if len(loaded.Events) != 2 {
		t.Fatalf("events = %d", len(loaded.Events))
	}
	if got := loaded.Events[0].EventID; got != "event-earlier" {
		t.Fatalf("first EventID = %q, want event-earlier", got)
	}
}

func TestLoadMissingSessionFails(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}

	if _, err := Load(runtimeDir, "missing-session"); err == nil {
		t.Fatal("expected missing session error")
	}
}
