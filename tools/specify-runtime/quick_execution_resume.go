package main

import "fmt"

// quickResumePersistenceError identifies the failed persistence phase without
// hiding the underlying filesystem error. It does not release or replace the
// existing Work claim: recovery must retry under the same guarded identity.
type quickResumePersistenceError struct {
	phase string
	cause error
}

func (err *quickResumePersistenceError) Error() string {
	return fmt.Sprintf("quick item resume %s failed; retain the current Work claim and retry after repair: %v", err.phase, err.cause)
}

func (err *quickResumePersistenceError) Unwrap() error { return err.cause }

// persistQuickExecutionResume orders canonical persistence before projection.
// A failed step must never produce a successful start/dispatch receipt. The
// callbacks keep failure injection local to the call, without mutable global
// test hooks or changes to normal Work/Activity ownership.
func persistQuickExecutionResume(persist, project func() error) error {
	if err := persist(); err != nil {
		return &quickResumePersistenceError{phase: "confirmation persistence", cause: err}
	}
	if err := project(); err != nil {
		return &quickResumePersistenceError{phase: "status projection", cause: err}
	}
	return nil
}
