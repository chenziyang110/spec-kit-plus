package delta

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes/model"
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

func TestAppendRejectsSessionIDWithTraversal(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}

	if _, err := Append(AppendInput{
		RuntimeDir: runtimeDir,
		SessionID:  ".." + string(os.PathSeparator) + "outside",
		EventType:  "worker_result",
	}); err == nil {
		t.Fatal("expected invalid session id error")
	}
}

func TestLoadRejectsSessionIDWithTraversal(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}

	if _, err := Load(runtimeDir, ".."+string(os.PathSeparator)+"outside"); err == nil {
		t.Fatal("expected invalid session id error")
	}
}

func TestAppendRetriesEventIDCollisionWithoutOverwriting(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}
	fixedNow := time.Date(2026, 5, 22, 12, 0, 0, 123, time.UTC)
	previousNowUTC := nowUTC
	nowUTC = func() time.Time { return fixedNow }
	t.Cleanup(func() { nowUTC = previousNowUTC })

	eventsDir := filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events")
	firstCandidate := "event-" + fixedNow.Format("20060102T150405.000000000Z")
	existing := filepath.Join(eventsDir, firstCandidate+".json")
	existingData := []byte(`{"event_id":"` + firstCandidate + `","session_id":"` + session.SessionID + `","event_type":"existing"}` + "\n")
	if err := os.WriteFile(existing, existingData, 0o644); err != nil {
		t.Fatal(err)
	}

	event, err := Append(AppendInput{
		RuntimeDir: runtimeDir,
		SessionID:  session.SessionID,
		EventType:  "worker_result",
	})
	if err != nil {
		t.Fatal(err)
	}

	if event.EventID == firstCandidate {
		t.Fatalf("EventID reused colliding candidate %q", firstCandidate)
	}
	if event.EventID != firstCandidate+"-1" {
		t.Fatalf("EventID = %q, want %q", event.EventID, firstCandidate+"-1")
	}
	data, err := os.ReadFile(existing)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != string(existingData) {
		t.Fatalf("colliding event file was overwritten: %s", data)
	}
	if _, err := os.Stat(filepath.Join(eventsDir, event.EventID+".json")); err != nil {
		t.Fatal(err)
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

func TestAppendPacketFileAcceptsWorkflowPayloadAliases(t *testing.T) {
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
	data := []byte(`{
  "event_type": "worker_result",
  "changed_paths": ["src/a.go"],
  "generated_surfaces": ["templates/commands/quick.md"],
  "verification": ["go test ./... PASS"]
}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	event, err := AppendPacketFile(runtimeDir, session.SessionID, packet)
	if err != nil {
		t.Fatal(err)
	}
	if got := event.GeneratedSurfaces; len(got) != 1 || got[0] != "templates/commands/quick.md" {
		t.Fatalf("GeneratedSurfaces = %#v", got)
	}
	if got := event.Verification; len(got) != 1 || got[0] != "go test ./... PASS" {
		t.Fatalf("Verification = %#v", got)
	}
}

func TestAppendPacketFilePreservesTypedRenameAndDisposition(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "implement"})
	if err != nil {
		t.Fatal(err)
	}
	packet := filepath.Join(root, "typed-packet.json")
	data := []byte(`{
  "event_type": "workflow_closeout",
  "path_changes": [{
    "path": "./src/new-name.go",
    "old_path": "./src/old-name.go",
    "operation": "rename",
    "disposition": "adoptable",
    "evidence_refs": ["test:rename", "test:rename"]
  }]
}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	event, err := AppendPacketFile(runtimeDir, session.SessionID, packet)
	if err != nil {
		t.Fatal(err)
	}
	if len(event.PathChanges) != 1 {
		t.Fatalf("PathChanges = %#v, want one", event.PathChanges)
	}
	change := event.PathChanges[0]
	if change.Path != "src/new-name.go" || change.OldPath != "src/old-name.go" || change.Operation != changemodel.OperationRename {
		t.Fatalf("PathChanges[0] = %#v, want normalized rename", change)
	}
	if change.Disposition == nil || *change.Disposition != changemodel.DispositionAdoptable {
		t.Fatalf("Disposition = %#v, want adoptable", change.Disposition)
	}
	if len(change.EvidenceRefs) != 1 || change.EvidenceRefs[0] != "test:rename" {
		t.Fatalf("EvidenceRefs = %#v, want normalized evidence refs", change.EvidenceRefs)
	}
	if len(event.ChangedPaths) != 1 || event.ChangedPaths[0] != "src/new-name.go" {
		t.Fatalf("ChangedPaths = %#v, want derived new rename path", event.ChangedPaths)
	}
}

func TestAppendRejectsInvalidTypedPathChangeBeforeWritingEvent(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "implement"})
	if err != nil {
		t.Fatal(err)
	}

	_, err = Append(AppendInput{
		RuntimeDir: runtimeDir,
		SessionID:  session.SessionID,
		EventType:  "workflow_closeout",
		PathChanges: []changemodel.PathChange{{
			Path:      "src/new-name.go",
			Operation: changemodel.OperationRename,
		}},
	})
	if err == nil {
		t.Fatal("Append accepted rename without old_path")
	}
	entries, readErr := os.ReadDir(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events"))
	if readErr != nil {
		t.Fatal(readErr)
	}
	if len(entries) != 0 {
		t.Fatalf("events = %d, want no event after invalid typed change", len(entries))
	}
}

func TestAppendRejectsUnixAbsoluteTypedPathChangeBeforeWritingEvent(t *testing.T) {
	runtimeDir := t.TempDir()
	session, err := Begin(BeginInput{RuntimeDir: runtimeDir, Root: runtimeDir})
	if err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable

	_, err = Append(AppendInput{
		RuntimeDir: runtimeDir,
		SessionID:  session.SessionID,
		PathChanges: []changemodel.PathChange{{
			Path:        "/tmp/outside-repository.go",
			Operation:   changemodel.OperationAdd,
			Disposition: &disposition,
		}},
	})
	if err == nil || !strings.Contains(err.Error(), "repository-relative path") {
		t.Fatalf("Append absolute typed path error = %v", err)
	}
	entries, readErr := os.ReadDir(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events"))
	if readErr != nil {
		t.Fatal(readErr)
	}
	if len(entries) != 0 {
		t.Fatalf("events = %d, want no event after absolute typed path", len(entries))
	}
}

func TestAppendRejectsPathsThatUpdateCannotCloseOut(t *testing.T) {
	for _, path := range []string{".specify/project-cognition/status.json", "src/**/*.go"} {
		t.Run(path, func(t *testing.T) {
			runtimeDir := t.TempDir()
			session, err := Begin(BeginInput{RuntimeDir: runtimeDir, Root: runtimeDir})
			if err != nil {
				t.Fatal(err)
			}
			disposition := changemodel.DispositionAdoptable

			_, err = Append(AppendInput{
				RuntimeDir: runtimeDir,
				SessionID:  session.SessionID,
				PathChanges: []changemodel.PathChange{{
					Path:        path,
					Operation:   changemodel.OperationAdd,
					Disposition: &disposition,
				}},
			})
			if err == nil || !strings.Contains(err.Error(), "repository-relative path") {
				t.Fatalf("Append invalid closeout path error = %v", err)
			}
			entries, readErr := os.ReadDir(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "events"))
			if readErr != nil {
				t.Fatal(readErr)
			}
			if len(entries) != 0 {
				t.Fatalf("events = %d, want no event after invalid closeout path", len(entries))
			}
		})
	}
}

func TestAppendRejectsConflictingTypedPathChangeDispositions(t *testing.T) {
	runtimeDir := t.TempDir()
	session, err := Begin(BeginInput{RuntimeDir: runtimeDir, Root: runtimeDir})
	if err != nil {
		t.Fatal(err)
	}
	adoptable := changemodel.DispositionAdoptable
	reviewOnly := changemodel.DispositionReviewOnly

	_, err = Append(AppendInput{
		RuntimeDir: runtimeDir,
		SessionID:  session.SessionID,
		PathChanges: []changemodel.PathChange{
			{Path: "src/a.go", Operation: changemodel.OperationModify, Disposition: &adoptable},
			{Path: "src/a.go", Operation: changemodel.OperationModify, Disposition: &reviewOnly},
		},
	})
	if err == nil {
		t.Fatal("expected conflicting typed path dispositions to fail")
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
