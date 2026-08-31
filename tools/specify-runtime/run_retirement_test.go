package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunRetirementRemovesDiscoveryButPreservesSharedWorkflowCapabilities(t *testing.T) {
	retired := []string{
		"run.create", "run.launch", "run.supervise", "run.show", "run.events", "run.cancel",
		"result.list", "result.show", "result.reopen", "result.depend",
		"candidate.build", "candidate.show", "candidate.review", "accept.receipt", "cas.publish", "sync.safe",
	}
	var help, stderr bytes.Buffer
	if code := Run([]string{"help"}, &help, &stderr, "test"); code != 0 {
		t.Fatalf("help = %d: %s", code, help.String())
	}
	for _, line := range strings.Split(help.String(), "\n") {
		switch strings.TrimSpace(line) {
		case "run", "candidate", "cas", "sync":
			t.Fatalf("retired command remains in help: %q", line)
		}
	}
	for _, query := range []string{"list", "handshake"} {
		code, payload := invokeCoordinationCLI(t, "api", query, "--format", "json")
		if code != 0 {
			t.Fatalf("api %s = %d: %#v", query, code, payload)
		}
		encoded, err := json.Marshal(payload)
		if err != nil {
			t.Fatal(err)
		}
		for _, capability := range retired {
			if strings.Contains(string(encoded), `"`+capability+`"`) {
				t.Fatalf("api %s advertises retired capability %s", query, capability)
			}
		}
	}
	for _, capability := range retired {
		code, payload := invokeCoordinationCLI(t, "api", "show", capability, "--format", "json")
		if code == 0 {
			t.Fatalf("retired api show %s succeeded: %#v", capability, payload)
		}
	}
	for _, capability := range []string{
		"board.show", "board.feature-bootstrap", "work.claim", "work.interrupt", "work.resume",
		"execution.announce", "execution.guard", "execution.complete", "execution.overview",
		"result.path", "result.submit", "review.prepare", "review.closeout", "accept.prepare", "accept.closeout",
	} {
		code, payload := invokeCoordinationCLI(t, "api", "show", capability, "--format", "json")
		if code != 0 {
			t.Fatalf("preserved api show %s = %d: %#v", capability, code, payload)
		}
	}
}

func TestRunRetirementRejectsOldEntryPointsWithoutCreatingState(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	for _, command := range [][]string{
		{"run", "create", "--run-id", "retired", "--kind", "quick", "--subject-type", "feature", "--subject-id", "retired", "--target-ref", "HEAD", "--intent-sha256", strings.Repeat("a", 64)},
		{"run", "launch", "--run-id", "retired", "--", "must-not-launch"},
		{"run", "supervise", "retired", "--", "must-not-launch"},
		{"candidate", "build"}, {"cas", "publish"}, {"sync", "safe"},
		{"result", "list"}, {"result", "show", "retired"}, {"accept", "receipt", "retired"},
	} {
		args := append(append([]string(nil), command...), "--project-root", root, "--format", "json")
		code, payload := invokeCoordinationCLI(t, args...)
		if code == 0 {
			t.Fatalf("retired entrypoint %v succeeded: %#v", command, payload)
		}
	}
	for _, path := range []string{filepath.Join(root, ".git", "specify-runtime"), filepath.Join(root, ".worktrees")} {
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatalf("retired command created state at %s: %v", path, err)
		}
	}
}

func TestExecutionAnnounceUsesExactCompiledWorkerPacketWithoutRun(t *testing.T) {
	root := initCoordinationCLIRepository(t)
	path, digest := writeRetirementWorkerPacket(t, root)
	code, payload := invokeCoordinationCLI(t,
		"execution", "announce", "--project-root", root,
		"--activity-id", "packet-work", "--workflow", "implement",
		"--agent-id", "worker", "--adapter-id", "codex",
		"--work-packet-file", path, "--work-packet-sha256", digest, "--format", "json",
	)
	if code != 0 {
		t.Fatalf("packet announce = %d: %#v", code, payload)
	}
	activity := requireObject(t, requireObject(t, payload, "data"), "execution_activity")
	for key, want := range map[string]string{
		"subject_id": "feature-packet", "item_id": "T001", "task_ref": "feature-packet#T001",
		"title": "Implement the compiled objective", "phase": "announced",
	} {
		if activity[key] != want {
			t.Fatalf("activity.%s = %#v, want %q", key, activity[key], want)
		}
	}
	planned := anyStringSlice(activity["planned_write_scope"])
	if len(planned) != 7 || planned[len(planned)-1] != "src/packet" || len(anyStringSlice(activity["confirmed_write_scope"])) != 0 {
		t.Fatalf("packet announce granted or lost scope: %#v", activity)
	}
	code, board := invokeCoordinationCLI(t, "board", "show", "--project-root", root, "--format", "json")
	if code != 0 || len(requireObjectSlice(t, board, "items")) != 1 {
		t.Fatalf("packet Work is not visible on shared board: %d %#v", code, board)
	}
}

func TestExecutionPacketRejectionDoesNotRegisterWork(t *testing.T) {
	for _, test := range []string{"missing-digest", "digest-mismatch", "manual-scope", "manual-identity", "outside-root", "wrong-workflow", "noncanonical-path"} {
		t.Run(test, func(t *testing.T) {
			root := initCoordinationCLIRepository(t)
			path, digest := writeRetirementWorkerPacket(t, root)
			args := []string{"execution", "announce", "--project-root", root,
				"--workflow", "implement", "--agent-id", "worker", "--adapter-id", "codex"}
			switch test {
			case "digest-mismatch":
				digest = strings.Repeat("0", 64)
			case "manual-scope":
				args = append(args, "--planned-write-scope-json", `["src/unapproved"]`)
			case "manual-identity":
				args = append(args, "--task-ref", "different#T999")
			case "outside-root":
				path, digest = writeRetirementWorkerPacket(t, t.TempDir())
			case "wrong-workflow":
				args[5] = "quick"
			case "noncanonical-path":
				content, err := os.ReadFile(path)
				if err != nil {
					t.Fatal(err)
				}
				path = filepath.Join(root, "forged-worker-packet.json")
				if err := os.WriteFile(path, content, 0o600); err != nil {
					t.Fatal(err)
				}
			}
			args = append(args, "--work-packet-file", path)
			if test != "missing-digest" {
				args = append(args, "--work-packet-sha256", digest)
			}
			args = append(args, "--format", "json")
			code, payload := invokeCoordinationCLI(t, args...)
			if code == 0 || payload["status"] != "usage-error" {
				t.Fatalf("invalid packet announce = %d: %#v", code, payload)
			}
			if _, err := os.Stat(filepath.Join(root, ".git", "specify-runtime")); !os.IsNotExist(err) {
				t.Fatalf("invalid packet registered shared state: %v", err)
			}
		})
	}
}

func TestExecutionPacketGuardRejectsScopeWideningAndChangedPacket(t *testing.T) {
	for _, scenario := range []string{"wider-scope", "changed-packet"} {
		t.Run(scenario, func(t *testing.T) {
			root := initCoordinationCLIRepository(t)
			path, digest := writeRetirementWorkerPacket(t, root)
			code, payload := invokeCoordinationCLI(t,
				"execution", "announce", "--project-root", root,
				"--activity-id", "pinned-packet", "--workflow", "implement",
				"--agent-id", "worker", "--adapter-id", "codex",
				"--work-packet-file", path, "--work-packet-sha256", digest, "--format", "json",
			)
			if code != 0 {
				t.Fatalf("announce = %d %#v", code, payload)
			}
			announced := requireObject(t, requireObject(t, payload, "data"), "execution_activity")
			scope := `["src/packet"]`
			if scenario == "wider-scope" {
				scope = `["src"]`
			} else {
				content, err := os.ReadFile(path)
				if err != nil {
					t.Fatal(err)
				}
				if err := os.WriteFile(path, append(content, '\n'), 0o600); err != nil {
					t.Fatal(err)
				}
			}
			overview := executionOverviewCLI(t, root, "pinned-packet")
			code, blocked := invokeCoordinationCLI(t,
				"execution", "guard", "pinned-packet", "--project-root", root,
				"--expected-revision", executionJSONNumberString(announced["work_revision"]),
				"--fence", executionJSONNumberString(announced["fence"]),
				"--expected-overview-revision", executionJSONNumberString(overview["coordination_revision"]),
				"--expected-overview-sha256", stringValue(overview["snapshot_sha256"]),
				"--write-scope-json", scope, "--resources-json", "[]", "--reason", "verify packet boundary", "--format", "json",
			)
			if code == 0 || blocked["status"] != "blocked" {
				t.Fatalf("invalid packet guard = %d %#v", code, blocked)
			}
			code, shown := invokeCoordinationCLI(t, "execution", "show", "pinned-packet", "--project-root", root, "--format", "json")
			if code != 0 {
				t.Fatalf("show = %d %#v", code, shown)
			}
			current := requireObject(t, requireObject(t, shown, "data"), "execution_activity")
			if current["work_revision"] != announced["work_revision"] || len(anyStringSlice(current["confirmed_write_scope"])) != 0 {
				t.Fatalf("rejected packet guard changed authority: %#v", current)
			}
		})
	}
}

func writeRetirementWorkerPacket(t *testing.T, root string) (string, string) {
	t.Helper()
	featureID, taskID := "feature-packet", "T001"
	feature := filepath.Join(root, ".specify", "features", featureID)
	packetRef := "implementation-review/packets/T001.json"
	writeArtifactTestFile(t, root, ".specify/templates/task-packet-template.json", `{"version":2}`)
	index := map[string]any{"version": 2, "status": "ready", "feature_id": featureID, "tasks": []any{
		map[string]any{"id": taskID, "objective": "Implement the compiled objective", "expected_write_scope": []string{"src/packet"}, "packet_ref": packetRef},
	}}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), index)
	normalized, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		t.Fatal(err)
	}
	position, task, err := findImplementTask(normalized, taskID)
	if err != nil {
		t.Fatal(err)
	}
	packet, err := buildImplementTaskPacket(root, feature, taskID, normalized, position, task)
	if err != nil {
		t.Fatal(err)
	}
	content, err := marshalTaskControlJSON(packet)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(feature, filepath.FromSlash(packetRef))
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatal(err)
	}
	digest := sha256.Sum256(content)
	return path, hex.EncodeToString(digest[:])
}
