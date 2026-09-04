package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const maxAgentJSONInputBytes = 16 * 1024 * 1024

var openAgentInputFile = os.Open

func readAgentJSONInput(args []string, projectRoot, label string) ([]byte, error) {
	if hasFlag(args, "--input") {
		return nil, fmt.Errorf("%s does not accept agent-authored input files via --input; pass bounded semantic JSON with --input-json (inline, @path, or - for stdin)", label)
	}
	if !hasFlag(args, "--input-json") {
		return nil, fmt.Errorf("%s requires --input-json", label)
	}
	raw, err := resolveAgentJSONInputBytes(optionValue(args, "--input-json", ""), projectRoot, label)
	if err != nil {
		return nil, err
	}
	if len(raw) == 0 {
		return nil, fmt.Errorf("%s --input-json must not be empty", label)
	}
	if len(raw) > maxAgentJSONInputBytes {
		return nil, fmt.Errorf("%s --input-json exceeds %d bytes", label, maxAgentJSONInputBytes)
	}
	return raw, nil
}

// resolveAgentJSONInputBytes loads --input-json content from:
//   - inline JSON text
//   - @path (project-relative or absolute file; shell-safe on Windows)
//   - - (stdin)
//
// Content is consumed at invoke time; agents must not treat the source path as
// durable workflow state. Bare --input remains rejected.
func resolveAgentJSONInputBytes(raw, projectRoot, label string) ([]byte, error) {
	return resolveJSONInputBytesFrom(raw, projectRoot, label, "--input-json", os.Stdin)
}

func resolveJSONInputBytesFrom(raw, projectRoot, label, inputFlag string, stdin io.Reader) ([]byte, error) {
	return resolveFileBackedInputBytesFrom(raw, projectRoot, label, inputFlag, stdin, maxAgentJSONInputBytes)
}

func resolveTextInputBytes(raw, projectRoot, label, inputFlag string) ([]byte, error) {
	if strings.HasPrefix(raw, "@@") {
		data := []byte(raw[1:])
		if len(data) > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxAgentJSONInputBytes)
		}
		return data, nil
	}
	// File-backed text input is opt-in only when @ is the first byte. This keeps
	// ordinary prose such as "  @operator" literal instead of turning a leading
	// mention (or an accidentally matching filename) into a local file read.
	if strings.HasPrefix(strings.TrimSpace(raw), "@") && !strings.HasPrefix(raw, "@") {
		data := []byte(raw)
		if len(data) > maxAgentJSONInputBytes {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxAgentJSONInputBytes)
		}
		return data, nil
	}
	return resolveFileBackedInputBytesFrom(raw, projectRoot, label, inputFlag, os.Stdin, maxAgentJSONInputBytes)
}

func resolveFileBackedInputBytesFrom(raw, projectRoot, label, inputFlag string, stdin io.Reader, maxBytes int) ([]byte, error) {
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		return nil, nil
	}
	if trimmed == "-" {
		if stdin == nil {
			return nil, fmt.Errorf("%s %s - requires stdin", label, inputFlag)
		}
		limited := io.LimitReader(stdin, int64(maxBytes)+1)
		data, err := io.ReadAll(limited)
		if err != nil {
			return nil, fmt.Errorf("%s %s - failed to read stdin: %w", label, inputFlag, err)
		}
		if len(data) > maxBytes {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxBytes)
		}
		return data, nil
	}
	if strings.HasPrefix(trimmed, "@") {
		path := strings.TrimSpace(strings.TrimPrefix(trimmed, "@"))
		if path == "" {
			return nil, fmt.Errorf("%s %s @path requires a non-empty path", label, inputFlag)
		}
		target, err := resolveProjectContainedInputPath(projectRoot, path)
		if err != nil {
			return nil, fmt.Errorf("%s %s @path is invalid: %w", label, inputFlag, err)
		}
		file, err := openAgentInputFile(target)
		if err != nil {
			return nil, fmt.Errorf("%s %s @path could not open %s: %w", label, inputFlag, target, err)
		}
		defer file.Close()
		openedInfo, err := file.Stat()
		if err != nil {
			return nil, fmt.Errorf("%s %s @path could not inspect opened file %s: %w", label, inputFlag, target, err)
		}
		if !openedInfo.Mode().IsRegular() {
			return nil, fmt.Errorf("%s %s @path must be a regular file", label, inputFlag)
		}
		if openedInfo.Size() > int64(maxBytes) {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxBytes)
		}
		pathInfo, err := os.Lstat(target)
		if err != nil {
			return nil, fmt.Errorf("%s %s @path could not inspect %s: %w", label, inputFlag, target, err)
		}
		if pathInfo.Mode()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("%s %s @path must not be a symlink or reparse point", label, inputFlag)
		}
		if !pathInfo.Mode().IsRegular() {
			return nil, fmt.Errorf("%s %s @path must be a regular file", label, inputFlag)
		}
		if !os.SameFile(openedInfo, pathInfo) {
			return nil, fmt.Errorf("%s %s @path changed during validation", label, inputFlag)
		}
		if pathInfo.Size() > int64(maxBytes) {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxBytes)
		}
		data, err := io.ReadAll(io.LimitReader(file, int64(maxBytes)+1))
		if err != nil {
			return nil, fmt.Errorf("%s %s @path could not read %s: %w", label, inputFlag, target, err)
		}
		if len(data) > maxBytes {
			return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxBytes)
		}
		return data, nil
	}
	data := []byte(raw)
	if len(data) > maxBytes {
		return nil, fmt.Errorf("%s %s exceeds %d bytes", label, inputFlag, maxBytes)
	}
	return data, nil
}

func resolveProjectContainedInputPath(projectRoot, rawPath string) (string, error) {
	root := strings.TrimSpace(projectRoot)
	if root == "" {
		root = "."
	}
	rootAbs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	rootAbs, err = filepath.EvalSymlinks(rootAbs)
	if err != nil {
		return "", err
	}
	var target string
	if filepath.IsAbs(rawPath) {
		target, err = filepath.Abs(rawPath)
	} else {
		target, err = filepath.Abs(filepath.Join(rootAbs, filepath.FromSlash(rawPath)))
	}
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(rootAbs, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	secured, err := secureProjectPath(rootAbs, filepath.ToSlash(rel))
	if err != nil {
		return "", err
	}
	cleanTarget := filepath.Clean(target)
	cleanSecured := filepath.Clean(secured)
	if runtime.GOOS == "windows" {
		if !strings.EqualFold(cleanTarget, cleanSecured) {
			return "", fmt.Errorf("path must stay inside the project root")
		}
		return secured, nil
	}
	if cleanTarget != cleanSecured {
		return "", fmt.Errorf("path must stay inside the project root")
	}
	return secured, nil
}

func readAgentJSONObject(args []string, projectRoot, label string) (map[string]any, error) {
	raw, err := readAgentJSONInput(args, projectRoot, label)
	if err != nil {
		return nil, err
	}
	return decodeAgentJSONObject(raw, label)
}

// decodeAgentJSONObject unmarshals a JSON object and explains common shell
// quoting failures (especially PowerShell eating double quotes).
func decodeAgentJSONObject(raw []byte, label string) (map[string]any, error) {
	var value map[string]any
	if err := json.Unmarshal(raw, &value); err != nil {
		return nil, formatJSONObjectError(label, err, raw)
	}
	if value == nil {
		return nil, fmt.Errorf("%s input must be a JSON object", label)
	}
	return value, nil
}

func formatJSONObjectError(label string, err error, raw []byte) error {
	trimmed := strings.TrimSpace(string(raw))
	hint := ""
	// PowerShell often collapses --input-json '{"k":"v"}' so the runtime sees
	// {k:v} or bare tokens; surface a Windows-safe recovery path.
	if strings.Contains(err.Error(), "invalid character") ||
		(strings.HasPrefix(trimmed, "{") && !strings.Contains(trimmed, `"`) && strings.Contains(trimmed, ":")) {
		hint = "; if you are in PowerShell/Windows, prefer --input-json - with stdin, or an existing project file via @path; do not place a here-string directly after --input-json, and remember inline single-quoted JSON often loses double quotes"
	}
	return fmt.Errorf("%s input must be a JSON object: %w%s", label, err, hint)
}
