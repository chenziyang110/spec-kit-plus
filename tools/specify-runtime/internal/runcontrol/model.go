package runcontrol

import "errors"

// Sentinel errors let callers classify coordination failures with errors.Is.
var (
	ErrNotFound           = errors.New("coordination record not found")
	ErrAlreadyExists      = errors.New("coordination record already exists")
	ErrInvalidArgument    = errors.New("invalid coordination argument")
	ErrRevisionConflict   = errors.New("work revision conflict")
	ErrInvalidTransition  = errors.New("invalid work state transition")
	ErrStaleFence         = errors.New("stale work fence")
	ErrUnsupportedSchema  = errors.New("unsupported work board schema")
	ErrWorkspaceNotUsable = errors.New("workspace is not usable")
)

type Event struct {
	EventID           int64
	AggregateType     string
	AggregateID       string
	AggregateRevision int64
	EventType         string
	Reason            string
	PayloadJSON       string
	CreatedAtMS       int64
}
