package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runcontrol"
)

// The complete workspace audit is immutable and separate from the changing
// checkpoint. Keep its safety bound independent of the 8 MiB session limit.
const doBaselineSizeLimit = 64 * 1024 * 1024

func doBaselineRef(id string) string {
	return path.Join(".specify/do/sessions", id, "baseline.json")
}

func doValidateBaselineBinding(session DoSession) error {
	if !doIDPattern.MatchString(session.ID) || session.BaselineRef != doBaselineRef(session.ID) {
		return fmt.Errorf("workspace baseline must reference this session's canonical baseline.json")
	}
	decoded, err := hex.DecodeString(session.BaselineSHA256)
	if err != nil || len(decoded) != 32 || session.BaselineSHA256 != strings.ToLower(session.BaselineSHA256) {
		return fmt.Errorf("workspace baseline requires its exact SHA256 binding")
	}
	return nil
}

func doValidateBaselineBytes(raw []byte) error {
	if len(raw) > doBaselineSizeLimit {
		return fmt.Errorf("workspace baseline exceeds 64 MiB safety limit")
	}
	var baseline runcontrol.WorkspaceBaseline
	if err := json.Unmarshal(raw, &baseline); err != nil {
		return fmt.Errorf("invalid workspace baseline: %w", err)
	}
	if strings.TrimSpace(baseline.HeadCommit) == "" || baseline.DirtyPaths == nil || baseline.PathDigests == nil {
		return fmt.Errorf("workspace baseline is missing its complete audit fields")
	}
	return nil
}

// Reject nonregular targets before open (including pipes), bound the bytes read
// even if the file grows, and check the opened identity against the secure path.
func doReadBaseline(root, relative string) ([]byte, error) {
	target, err := secureProjectPath(root, relative)
	if err != nil {
		return nil, err
	}
	before, err := os.Lstat(target)
	if err != nil {
		return nil, err
	}
	if !before.Mode().IsRegular() || before.Size() > doBaselineSizeLimit {
		return nil, fmt.Errorf("workspace baseline must be a regular file within 64 MiB")
	}
	file, err := os.Open(target)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil {
		return nil, err
	}
	if !opened.Mode().IsRegular() || !os.SameFile(before, opened) {
		return nil, fmt.Errorf("workspace baseline file identity changed while opening")
	}
	raw, err := io.ReadAll(io.LimitReader(file, doBaselineSizeLimit+1))
	if err != nil {
		return nil, err
	}
	if len(raw) > doBaselineSizeLimit {
		return nil, fmt.Errorf("workspace baseline exceeds 64 MiB safety limit")
	}
	target, err = secureProjectPath(root, relative)
	if err != nil {
		return nil, err
	}
	after, err := os.Lstat(target)
	if err != nil {
		return nil, err
	}
	if !after.Mode().IsRegular() || !os.SameFile(opened, after) {
		return nil, fmt.Errorf("workspace baseline file identity changed while reading")
	}
	return raw, nil
}

func doHydrateBaseline(root string, session *DoSession) error {
	if session.SchemaVersion == doLegacySessionSchema {
		if session.BaselineRef != "" || session.BaselineSHA256 != "" {
			return fmt.Errorf("legacy session cannot carry a workspace baseline reference")
		}
		return nil
	}
	if session.BaselineJSON != "" {
		return fmt.Errorf("referenced workspace baseline cannot also be stored inline")
	}
	if err := doValidateBaselineBinding(*session); err != nil {
		return err
	}
	raw, err := doReadBaseline(root, session.BaselineRef)
	if err != nil {
		return fmt.Errorf("read immutable workspace baseline: %w", err)
	}
	if doBytesDigest(raw) != session.BaselineSHA256 {
		return fmt.Errorf("immutable workspace baseline digest mismatch")
	}
	if err := doValidateBaselineBytes(raw); err != nil {
		return err
	}
	session.BaselineJSON = string(raw)
	return nil
}

// Hydrated baseline bytes remain available to the existing whole-workspace
// audit and replan consumers; only the reference is serialized for v2 sessions.
func doSerializeSession(session DoSession) ([]byte, error) {
	switch session.SchemaVersion {
	case doSessionSchema:
		if err := doValidateBaselineBinding(session); err != nil {
			return nil, err
		}
		if doBytesDigest([]byte(session.BaselineJSON)) != session.BaselineSHA256 {
			return nil, fmt.Errorf("hydrated workspace baseline changed from its immutable binding")
		}
		if err := doValidateBaselineBytes([]byte(session.BaselineJSON)); err != nil {
			return nil, err
		}
		session.BaselineJSON = ""
	case doLegacySessionSchema:
		if session.BaselineRef != "" || session.BaselineSHA256 != "" {
			return nil, fmt.Errorf("legacy session cannot carry a workspace baseline reference")
		}
	default:
		return nil, fmt.Errorf("invalid session schema")
	}
	raw, err := json.MarshalIndent(session, "", "  ")
	if err != nil {
		return nil, err
	}
	if len(raw)+1 > doSessionSizeLimit {
		return nil, fmt.Errorf("session checkpoint exceeds 8 MiB; preserve the last readable checkpoint and split the operation")
	}
	return append(raw, '\n'), nil
}
