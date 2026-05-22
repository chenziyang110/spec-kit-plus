package delta

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type BeginInput struct {
	Root              string
	RuntimeDir        string
	OriginCommand     string
	OriginFeatureDir  string
	OriginLaneID      string
	BaseCommit        string
	Branch            string
	InitialDirtyPaths []string
}

type AppendInput struct {
	RuntimeDir        string
	SessionID         string
	EventType         string
	OriginCommand     string
	OriginLaneID      string
	Phase             string
	ChangedPaths      []string
	ReadPaths         []string
	BehaviorSurfaces  []string
	GraphSemantics    map[string]any
	GeneratedSurfaces []string
	OwnerConsumers    []string
	KnownUnknowns     []string
	Verification      []string
	Confidence        string
}

type Session struct {
	SessionID     string        `json:"session_id"`
	OriginCommand string        `json:"origin_command"`
	OriginContext OriginContext `json:"origin_context"`
	Git           GitContext    `json:"git"`
	CreatedAt     string        `json:"created_at"`
}

type OriginContext struct {
	FeatureDir string `json:"feature_dir,omitempty"`
	LaneID     string `json:"lane_id,omitempty"`
}

type GitContext struct {
	Available         bool     `json:"available"`
	BaseCommit        string   `json:"base_commit,omitempty"`
	Branch            string   `json:"branch,omitempty"`
	InitialDirtyPaths []string `json:"initial_dirty_paths"`
}

type Event struct {
	EventID           string         `json:"event_id"`
	SessionID         string         `json:"session_id"`
	EventType         string         `json:"event_type"`
	OriginCommand     string         `json:"origin_command,omitempty"`
	OriginLaneID      string         `json:"origin_lane_id,omitempty"`
	Phase             string         `json:"phase,omitempty"`
	ChangedPaths      []string       `json:"changed_paths"`
	ReadPaths         []string       `json:"read_paths"`
	BehaviorSurfaces  []string       `json:"behavior_surfaces"`
	GraphSemantics    map[string]any `json:"graph_semantics,omitempty"`
	GeneratedSurfaces []string       `json:"generated_surface_notes"`
	OwnerConsumers    []string       `json:"owner_consumer_notes"`
	KnownUnknowns     []string       `json:"known_unknowns"`
	Verification      []string       `json:"verification_evidence"`
	Confidence        string         `json:"confidence,omitempty"`
	CreatedAt         string         `json:"created_at"`
}

type Bundle struct {
	Session Session `json:"session"`
	Events  []Event `json:"events"`
}

type packetEvent struct {
	EventType         string         `json:"event_type"`
	OriginCommand     string         `json:"origin_command"`
	OriginLaneID      string         `json:"origin_lane_id"`
	Phase             string         `json:"phase"`
	ChangedPaths      []string       `json:"changed_paths"`
	ReadPaths         []string       `json:"read_paths"`
	BehaviorSurfaces  []string       `json:"behavior_surfaces"`
	GraphSemantics    map[string]any `json:"graph_semantics"`
	GeneratedSurfaces []string       `json:"generated_surface_notes"`
	OwnerConsumers    []string       `json:"owner_consumer_notes"`
	KnownUnknowns     []string       `json:"known_unknowns"`
	Verification      []string       `json:"verification_evidence"`
	Confidence        string         `json:"confidence"`
}

func Begin(input BeginInput) (Session, error) {
	now := time.Now().UTC()
	session := Session{
		SessionID:     "delta-" + now.Format("20060102T150405.000000000Z"),
		OriginCommand: strings.TrimSpace(input.OriginCommand),
		OriginContext: OriginContext{
			FeatureDir: strings.TrimSpace(input.OriginFeatureDir),
			LaneID:     strings.TrimSpace(input.OriginLaneID),
		},
		Git: GitContext{
			Available:         strings.TrimSpace(input.BaseCommit) != "" || strings.TrimSpace(input.Branch) != "",
			BaseCommit:        strings.TrimSpace(input.BaseCommit),
			Branch:            strings.TrimSpace(input.Branch),
			InitialDirtyPaths: normalizePaths(input.InitialDirtyPaths),
		},
		CreatedAt: now.Format(time.RFC3339Nano),
	}

	dir := sessionDir(input.RuntimeDir, session.SessionID)
	if err := os.MkdirAll(filepath.Join(dir, "events"), 0o755); err != nil {
		return Session{}, fmt.Errorf("create delta session: %w", err)
	}
	if err := writeJSON(filepath.Join(dir, "session.json"), session); err != nil {
		return Session{}, err
	}
	return session, nil
}

func Append(input AppendInput) (Event, error) {
	if strings.TrimSpace(input.SessionID) == "" {
		return Event{}, fmt.Errorf("session id is required")
	}
	if _, err := os.Stat(filepath.Join(sessionDir(input.RuntimeDir, input.SessionID), "session.json")); err != nil {
		return Event{}, fmt.Errorf("load delta session: %w", err)
	}

	now := time.Now().UTC()
	event := Event{
		EventID:           "event-" + now.Format("20060102T150405.000000000Z"),
		SessionID:         strings.TrimSpace(input.SessionID),
		EventType:         strings.TrimSpace(input.EventType),
		OriginCommand:     strings.TrimSpace(input.OriginCommand),
		OriginLaneID:      strings.TrimSpace(input.OriginLaneID),
		Phase:             strings.TrimSpace(input.Phase),
		ChangedPaths:      normalizePaths(input.ChangedPaths),
		ReadPaths:         normalizePaths(input.ReadPaths),
		BehaviorSurfaces:  normalizeStrings(input.BehaviorSurfaces),
		GraphSemantics:    input.GraphSemantics,
		GeneratedSurfaces: normalizePaths(input.GeneratedSurfaces),
		OwnerConsumers:    normalizeStrings(input.OwnerConsumers),
		KnownUnknowns:     normalizeStrings(input.KnownUnknowns),
		Verification:      normalizeStrings(input.Verification),
		Confidence:        strings.TrimSpace(input.Confidence),
		CreatedAt:         now.Format(time.RFC3339Nano),
	}

	if err := writeJSON(filepath.Join(sessionDir(input.RuntimeDir, input.SessionID), "events", event.EventID+".json"), event); err != nil {
		return Event{}, err
	}
	return event, nil
}

func AppendPacketFile(runtimeDir string, sessionID string, packetFile string) (Event, error) {
	data, err := os.ReadFile(packetFile)
	if err != nil {
		return Event{}, fmt.Errorf("read packet file: %w", err)
	}
	var packet packetEvent
	if err := json.Unmarshal(data, &packet); err != nil {
		return Event{}, fmt.Errorf("parse packet file: %w", err)
	}
	return Append(AppendInput{
		RuntimeDir:        runtimeDir,
		SessionID:         sessionID,
		EventType:         packet.EventType,
		OriginCommand:     packet.OriginCommand,
		OriginLaneID:      packet.OriginLaneID,
		Phase:             packet.Phase,
		ChangedPaths:      packet.ChangedPaths,
		ReadPaths:         packet.ReadPaths,
		BehaviorSurfaces:  packet.BehaviorSurfaces,
		GraphSemantics:    packet.GraphSemantics,
		GeneratedSurfaces: packet.GeneratedSurfaces,
		OwnerConsumers:    packet.OwnerConsumers,
		KnownUnknowns:     packet.KnownUnknowns,
		Verification:      packet.Verification,
		Confidence:        packet.Confidence,
	})
}

func Load(runtimeDir string, sessionID string) (Bundle, error) {
	dir := sessionDir(runtimeDir, sessionID)
	data, err := os.ReadFile(filepath.Join(dir, "session.json"))
	if err != nil {
		return Bundle{}, fmt.Errorf("read delta session: %w", err)
	}
	var session Session
	if err := json.Unmarshal(data, &session); err != nil {
		return Bundle{}, fmt.Errorf("parse delta session: %w", err)
	}

	entries, err := os.ReadDir(filepath.Join(dir, "events"))
	if err != nil {
		return Bundle{}, fmt.Errorf("read delta events: %w", err)
	}
	events := make([]Event, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, "events", entry.Name()))
		if err != nil {
			return Bundle{}, fmt.Errorf("read delta event: %w", err)
		}
		var event Event
		if err := json.Unmarshal(data, &event); err != nil {
			return Bundle{}, fmt.Errorf("parse delta event: %w", err)
		}
		events = append(events, event)
	}
	sort.Slice(events, func(i, j int) bool {
		if events[i].CreatedAt == events[j].CreatedAt {
			return events[i].EventID < events[j].EventID
		}
		iCreatedAt, iErr := time.Parse(time.RFC3339Nano, events[i].CreatedAt)
		jCreatedAt, jErr := time.Parse(time.RFC3339Nano, events[j].CreatedAt)
		if iErr == nil && jErr == nil {
			if iCreatedAt.Equal(jCreatedAt) {
				return events[i].EventID < events[j].EventID
			}
			return iCreatedAt.Before(jCreatedAt)
		}
		return events[i].CreatedAt < events[j].CreatedAt
	})
	return Bundle{Session: session, Events: events}, nil
}

func sessionDir(runtimeDir string, sessionID string) string {
	return filepath.Join(runtimeDir, "delta-sessions", strings.TrimSpace(sessionID))
}

func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal json: %w", err)
	}
	data = append(data, '\n')
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return fmt.Errorf("write json: %w", err)
	}
	return nil
}

func normalizePaths(paths []string) []string {
	out := make([]string, 0, len(paths))
	seen := make(map[string]struct{}, len(paths))
	for _, path := range paths {
		normalized := filepath.ToSlash(strings.TrimSpace(path))
		for strings.HasPrefix(normalized, "./") {
			normalized = strings.TrimPrefix(normalized, "./")
		}
		normalized = strings.Trim(normalized, "/")
		if normalized == "" {
			continue
		}
		if _, ok := seen[normalized]; ok {
			continue
		}
		seen[normalized] = struct{}{}
		out = append(out, normalized)
	}
	sort.Strings(out)
	return out
}

func normalizeStrings(values []string) []string {
	out := make([]string, 0, len(values))
	seen := make(map[string]struct{}, len(values))
	for _, value := range values {
		normalized := strings.TrimSpace(value)
		if normalized == "" {
			continue
		}
		if _, ok := seen[normalized]; ok {
			continue
		}
		seen[normalized] = struct{}{}
		out = append(out, normalized)
	}
	sort.Strings(out)
	return out
}
