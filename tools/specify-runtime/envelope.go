package main

import "encoding/json"

type Envelope struct {
	Blockers []any          `json:"blockers"`
	Data     map[string]any `json:"data"`
	Items    []any          `json:"items"`
	NextArgv []string       `json:"next_argv"`
	ShowArgv []string       `json:"show_argv"`
	Status   string         `json:"status"`
	Summary  string         `json:"summary"`
	Extra    map[string]any `json:"-"`
}

func NewEnvelope(status, summary string) Envelope {
	return Envelope{
		Blockers: []any{},
		Data:     map[string]any{},
		Items:    []any{},
		NextArgv: []string{},
		ShowArgv: []string{},
		Status:   status,
		Summary:  summary,
	}
}

func ExitCodeForStatus(status string) int {
	switch status {
	case "ok", "warn", "repaired":
		return 0
	case "blocked", "repairable-block":
		return 10
	case "invalid", "usage-error":
		return 2
	default:
		return 1
	}
}

func (env Envelope) MarshalJSON() ([]byte, error) {
	out := map[string]any{}
	for key, value := range env.Extra {
		switch key {
		case "blockers", "data", "items", "next_argv", "show_argv", "status", "summary":
			continue
		default:
			out[key] = value
		}
	}
	out["blockers"] = env.Blockers
	out["data"] = env.Data
	out["items"] = env.Items
	out["next_argv"] = env.NextArgv
	out["show_argv"] = env.ShowArgv
	out["status"] = env.Status
	out["summary"] = env.Summary
	return json.Marshal(out)
}
