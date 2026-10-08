package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
)

const doArtifactSizeLimit = int64(2 * 1024 * 1024 * 1024)
const doFileArtifactSchema = "spec-kit-do-file-evidence-v1"

// Large build/package artifacts stay at their declared output path. Only their
// bounded receipt is snapshotted; validation streams the actual file again.
type doFileArtifactReceipt struct {
	SchemaVersion string `json:"schema_version"`
	Path          string `json:"path"`
	SHA256        string `json:"sha256"`
	Size          int64  `json:"size"`
}

func doHashArtifact(root, p string) (string, int64, error) {
	target, err := secureProjectPath(root, p)
	if err != nil {
		return "", 0, err
	}
	file, err := os.Open(target)
	if err != nil {
		return "", 0, err
	}
	defer file.Close()
	before, err := file.Stat()
	if err != nil {
		return "", 0, err
	}
	if !before.Mode().IsRegular() || before.Size() <= 0 || before.Size() > doArtifactSizeLimit {
		return "", 0, fmt.Errorf("file artifact must be nonempty, regular, and at most 2 GiB")
	}
	digest := sha256.New()
	size, err := io.Copy(digest, io.LimitReader(file, doArtifactSizeLimit+1))
	if err != nil {
		return "", 0, err
	}
	after, err := file.Stat()
	if err != nil || size != before.Size() || size > doArtifactSizeLimit || after.Size() != before.Size() || !after.ModTime().Equal(before.ModTime()) {
		return "", 0, fmt.Errorf("file artifact changed while its bytes were being verified")
	}
	return hex.EncodeToString(digest.Sum(nil)), size, nil
}

func doVerifyArtifactReceipt(root string, ref DoResultRef) error {
	raw, err := secureProjectReadFile(root, ref.SnapshotRef)
	if err != nil {
		return err
	}
	if len(raw) > 4096 || doBytesDigest(raw) != ref.SnapshotSHA256 {
		return fmt.Errorf("file artifact receipt changed")
	}
	var receipt doFileArtifactReceipt
	if err := json.Unmarshal(raw, &receipt); err != nil {
		return fmt.Errorf("invalid file artifact receipt: %w", err)
	}
	if receipt.SchemaVersion != doFileArtifactSchema || receipt.Path != ref.Path || receipt.SHA256 != ref.SHA256 || receipt.Size != ref.Size {
		return fmt.Errorf("file artifact receipt binding mismatch")
	}
	digest, size, err := doHashArtifact(root, ref.Path)
	if err != nil {
		return err
	}
	if digest != ref.SHA256 || size != ref.Size {
		return fmt.Errorf("recorded file artifact is missing or changed")
	}
	return nil
}
