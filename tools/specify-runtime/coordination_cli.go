package main

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

type parsedCoordinationCommand struct {
	positionals []string
	options     map[string]string
	packet      *runcontrol.WorkerPacketBinding
}

func parseCoordinationCommandArgs(args []string, positionalCount int, allowedOptions ...string) (parsedCoordinationCommand, error) {
	allowed := make(map[string]bool, len(allowedOptions))
	for _, name := range allowedOptions {
		allowed[name] = true
	}
	parsed := parsedCoordinationCommand{positionals: []string{}, options: map[string]string{}}
	for index := 0; index < len(args); index++ {
		argument := args[index]
		if !strings.HasPrefix(argument, "--") {
			parsed.positionals = append(parsed.positionals, argument)
			continue
		}
		if !allowed[argument] {
			return parsedCoordinationCommand{}, fmt.Errorf("unknown coordination option %q", argument)
		}
		if _, duplicate := parsed.options[argument]; duplicate {
			return parsedCoordinationCommand{}, fmt.Errorf("coordination option %s was repeated", argument)
		}
		if index+1 >= len(args) || strings.HasPrefix(args[index+1], "--") {
			return parsedCoordinationCommand{}, fmt.Errorf("coordination option %s requires a value", argument)
		}
		parsed.options[argument] = args[index+1]
		index++
	}
	if positionalCount >= 0 && len(parsed.positionals) != positionalCount {
		return parsedCoordinationCommand{}, fmt.Errorf("coordination command requires %d positional argument(s)", positionalCount)
	}
	if positionalCount < 0 && len(parsed.positionals) > 1 {
		return parsedCoordinationCommand{}, errors.New("coordination command accepts at most one positional argument")
	}
	return parsed, nil
}

func (parsed parsedCoordinationCommand) option(name, fallback string) string {
	if value, ok := parsed.options[name]; ok {
		return value
	}
	return fallback
}

func (parsed parsedCoordinationCommand) validateJSONFormat() error {
	if format, present := parsed.options["--format"]; present && strings.TrimSpace(format) != "json" {
		return errors.New("coordination commands support only --format json")
	}
	return nil
}

const maximumWorkerTaskPacketBytes int64 = 4 * 1024 * 1024

type workerTaskPacketWorkScope struct {
	WriteScope []string `json:"write_scope"`
}

type workerTaskPacket struct {
	FeatureID             string                    `json:"feature_id"`
	TaskID                string                    `json:"task_id"`
	Objective             string                    `json:"objective"`
	Scope                 workerTaskPacketWorkScope `json:"scope"`
	WriteScope            []string                  `json:"write_scope"`
	BookkeepingWriteScope []string                  `json:"bookkeeping_write_scope"`
}

type compiledPacketWorkParams struct {
	Path         string
	FeatureID    string
	TaskID       string
	TaskRef      string
	Summary      string
	WriteIntents []runcontrol.WriteIntentSpec
}

func workParamsFromTaskPacket(projectRoot, packetPath, expectedSHA256 string) (compiledPacketWorkParams, error) {
	expectedSHA256 = strings.TrimSpace(expectedSHA256)
	if !isLowerHexSHA256(expectedSHA256) {
		return compiledPacketWorkParams{}, errors.New("--work-packet-sha256 must be 64 lowercase hexadecimal characters")
	}
	resolvedPath, err := resolveWorkerTaskPacketPath(projectRoot, packetPath)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	file, err := os.Open(resolvedPath)
	if err != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("open --work-packet-file: %w", err)
	}
	content, readErr := io.ReadAll(io.LimitReader(file, maximumWorkerTaskPacketBytes+1))
	closeErr := file.Close()
	if readErr != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("read --work-packet-file: %w", readErr)
	}
	if closeErr != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("close --work-packet-file: %w", closeErr)
	}
	if int64(len(content)) > maximumWorkerTaskPacketBytes {
		return compiledPacketWorkParams{}, fmt.Errorf("--work-packet-file exceeds %d bytes", maximumWorkerTaskPacketBytes)
	}
	expectedDigest, _ := hex.DecodeString(expectedSHA256)
	actualDigest := sha256.Sum256(content)
	if subtle.ConstantTimeCompare(expectedDigest, actualDigest[:]) != 1 {
		return compiledPacketWorkParams{}, errors.New("--work-packet-sha256 does not match --work-packet-file")
	}
	var packet workerTaskPacket
	if err := json.Unmarshal(content, &packet); err != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("decode --work-packet-file: %w", err)
	}
	packet.FeatureID = strings.TrimSpace(packet.FeatureID)
	packet.TaskID = strings.TrimSpace(packet.TaskID)
	packet.Objective = strings.TrimSpace(packet.Objective)
	if packet.FeatureID == "" || packet.TaskID == "" || packet.Objective == "" {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file requires feature_id, task_id, and objective")
	}
	if !safeSegment(packet.FeatureID) || !safeSegment(packet.TaskID) {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file requires safe feature_id and task_id path segments")
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	projectRef, err := filepath.Rel(root, resolvedPath)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	projectRef = filepath.ToSlash(projectRef)
	metadata, registered := LookupArtifactType(projectRef)
	if !registered || metadata.TypeID != "worker-packet" || metadata.Owner != "specify-runtime implement packet-compile" {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file must be a registered CLI-owned implementation packet")
	}
	feature := filepath.Dir(filepath.Dir(filepath.Dir(resolvedPath)))
	if filepath.Base(feature) != packet.FeatureID && (runtime.GOOS != "windows" || !strings.EqualFold(filepath.Base(feature), packet.FeatureID)) {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file feature_id does not match its canonical feature directory")
	}
	packetRef := filepath.ToSlash(filepath.Join("implementation-review", "packets", packet.TaskID+".json"))
	expectedPath := filepath.Join(feature, filepath.FromSlash(packetRef))
	if resolvedPath != expectedPath && (runtime.GOOS != "windows" || !strings.EqualFold(resolvedPath, expectedPath)) {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file must name the exact CLI-owned implementation packet")
	}
	index, err := loadReadyImplementTaskIndex(root, feature)
	if err != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("verify compiled packet task index: %w", err)
	}
	position, task, err := findImplementTask(index, packet.TaskID)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	if filepath.ToSlash(strings.TrimSpace(anyString(task["packet_ref"]))) != packetRef {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file is not the task index's current compiled packet")
	}
	expectedPacket, err := buildImplementTaskPacket(root, feature, packet.TaskID, index, position, task)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	expectedBytes, err := marshalTaskControlJSON(expectedPacket)
	if err != nil {
		return compiledPacketWorkParams{}, err
	}
	expectedCompiledDigest := sha256.Sum256(expectedBytes)
	if subtle.ConstantTimeCompare(expectedCompiledDigest[:], actualDigest[:]) != 1 {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file does not match current CLI compilation; recompile before announcing work")
	}
	writeScope := packet.Scope.WriteScope
	if len(writeScope) == 0 {
		writeScope = packet.WriteScope
	}
	if len(writeScope) == 0 {
		return compiledPacketWorkParams{}, errors.New("--work-packet-file requires scope.write_scope")
	}
	writeScope, err = normalizeWorkClaimScope(append(append([]string(nil), writeScope...), packet.BookkeepingWriteScope...))
	if err != nil {
		return compiledPacketWorkParams{}, fmt.Errorf("compiled packet write scope: %w", err)
	}
	intents := make([]runcontrol.WriteIntentSpec, 0, len(writeScope))
	for _, path := range writeScope {
		path = strings.TrimSpace(path)
		if path == "" {
			return compiledPacketWorkParams{}, errors.New("--work-packet-file scope.write_scope cannot contain blank paths")
		}
		intents = append(intents, runcontrol.WriteIntentSpec{
			Path:       path,
			Operation:  runcontrol.WriteModify,
			Reason:     "declared by worker task packet " + packet.TaskID,
			Confidence: runcontrol.IntentConfirmed,
		})
	}
	return compiledPacketWorkParams{
		Path:         projectRef,
		FeatureID:    packet.FeatureID,
		TaskID:       packet.TaskID,
		TaskRef:      packet.FeatureID + "#" + packet.TaskID,
		Summary:      packet.Objective,
		WriteIntents: intents,
	}, nil
}

func isLowerHexSHA256(value string) bool {
	if len(value) != sha256.Size*2 {
		return false
	}
	for _, character := range value {
		if (character < '0' || character > '9') && (character < 'a' || character > 'f') {
			return false
		}
	}
	return true
}

func resolveWorkerTaskPacketPath(projectRoot, packetPath string) (string, error) {
	packetPath = strings.TrimSpace(packetPath)
	if packetPath == "" || strings.ContainsRune(packetPath, '\x00') {
		return "", errors.New("--work-packet-file requires a path")
	}
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", fmt.Errorf("resolve --project-root: %w", err)
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", fmt.Errorf("resolve --project-root: %w", err)
	}
	candidate := packetPath
	if !filepath.IsAbs(candidate) {
		candidate = filepath.Join(root, candidate)
	}
	candidate, err = filepath.Abs(candidate)
	if err != nil {
		return "", fmt.Errorf("resolve --work-packet-file: %w", err)
	}
	candidate, err = filepath.EvalSymlinks(candidate)
	if err != nil {
		return "", fmt.Errorf("resolve --work-packet-file: %w", err)
	}
	relative, err := filepath.Rel(root, candidate)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", errors.New("--work-packet-file must stay inside --project-root")
	}
	return candidate, nil
}

func coordinationErrorEnvelope(action string, err error) Envelope {
	status := "error"
	switch {
	case errors.Is(err, runcontrol.ErrInvalidArgument), errors.Is(err, runcontrol.ErrNotFound):
		status = "invalid"
	case errors.Is(err, runcontrol.ErrNotGitRepository):
		status = "usage-error"
	case errors.Is(err, runcontrol.ErrAlreadyExists),
		errors.Is(err, runcontrol.ErrRevisionConflict),
		errors.Is(err, runcontrol.ErrInvalidTransition),
		errors.Is(err, runcontrol.ErrStaleFence),
		errors.Is(err, runcontrol.ErrWorkspaceNotUsable),
		errors.Is(err, runcontrol.ErrWorkIntentConflict),
		errors.Is(err, runcontrol.ErrUnsupportedSchema):
		status = "blocked"
	}
	env := NewEnvelope(status, action+" failed")
	env.Blockers = append(env.Blockers, err.Error())
	return env
}
