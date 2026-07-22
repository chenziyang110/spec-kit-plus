package main

type Envelope struct {
	Blockers []any          `json:"blockers"`
	Data     map[string]any `json:"data"`
	Items    []any          `json:"items"`
	NextArgv []string       `json:"next_argv"`
	ShowArgv []string       `json:"show_argv"`
	Status   string         `json:"status"`
	Summary  string         `json:"summary"`
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
