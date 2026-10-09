package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

// A queued Learning writer must keep its Do Work active until the Learning
// transaction ends. The finisher uses the real public Do lock, rather than a
// direct helper call that would bypass the supported serialization boundary.
func TestDoLearningQueuedWriterRetainsWorkUntilPublication(t *testing.T) {
	root, input := doFixture(t)
	session := playbookExecuteFixture(t, root, input)
	service := learningService{projectRoot: root, doSessionID: session.ID}
	paths, err := service.paths()
	if err != nil {
		t.Fatal(err)
	}
	lock := filepath.Join(filepath.Dir(paths.review), ".learning.lock")
	if err := os.MkdirAll(filepath.Dir(lock), 0o755); err != nil {
		t.Fatal(err)
	}
	releaseLearning, err := filelock.Acquire(lock)
	if err != nil {
		t.Fatal(err)
	}
	defer releaseLearning()
	writer := make(chan error, 1)
	go func() {
		_, err := service.withLock(func(service learningService, paths learningPaths) (map[string]any, error) {
			return map[string]any{"status": "seeded"}, nil
		})
		writer <- err
	}()
	deadline := time.Now().Add(10 * time.Second)
	for {
		current, _, err := loadDoSession(root, session.ID)
		if err != nil {
			t.Fatal(err)
		}
		if len(current.MetadataWriteScope) > 0 {
			session = current
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("queued Learning writer never registered its exact Do ownership")
		}
		time.Sleep(10 * time.Millisecond)
	}
	request, _ := json.Marshal(doFinishInput{ExpectedRevision: session.Revision, KnowledgeStatus: "not_applicable"})
	type finishResult struct {
		code int
		body string
	}
	finished := make(chan finishResult, 1)
	go func() {
		var out, stderr bytes.Buffer
		code := Run([]string{"do", "finish", session.ID, "--project-root", root, "--input-json", string(request), "--format", "json"}, &out, &stderr, "test")
		finished <- finishResult{code, out.String() + stderr.String()}
	}()
	closedBeforePublication := false
	finishReturned := false
	var result finishResult
	select {
	case result = <-finished:
		finishReturned = true
		closedBeforePublication = result.code == 0
	case <-time.After(5 * time.Second):
	}
	releaseLearning()
	select {
	case err := <-writer:
		if err != nil {
			t.Fatalf("Learning publication failed: %v", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("Learning publication did not finish")
	}
	if !finishReturned {
		select {
		case result = <-finished:
		case <-time.After(10 * time.Second):
			t.Fatal("Do finish did not resume after Learning publication")
		}
	}
	if closedBeforePublication {
		t.Fatalf("Do released Work while its queued Learning writer could still publish: %s", result.body)
	}
	if result.code != 0 {
		t.Fatalf("Do finish after serialized Learning publication failed: %s", result.body)
	}
	if _, err := os.Stat(paths.learningIndex); err != nil {
		t.Fatalf("serialized Learning transaction did not publish its index: %v", err)
	}
}
