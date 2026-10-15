package cli

import (
	"crypto/sha256"
	"encoding/hex"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func archiveIncompatibleStoreCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("archive-incompatible-store", flag.ContinueOnError)
	fs.SetOutput(stderr)
	expectedSHA256 := fs.String("expected-sha256", "", "Expected SHA-256 of project-cognition.db")
	inspect := fs.Bool("inspect", false, "Inspect the exact database and return guarded archive argv without changing files")
	format := fs.String("format", "json", "Output format: json")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *format != "json" {
		return writeCompactErrorJSON(stdout, fmt.Errorf("archive-incompatible-store supports only --format json"))
	}
	expected := strings.ToLower(strings.TrimSpace(*expectedSHA256))
	if !*inspect {
		decoded, err := hex.DecodeString(expected)
		if err != nil || len(decoded) != sha256.Size {
			return writeCompactErrorJSON(stdout, fmt.Errorf("archive-incompatible-store requires a 64-character --expected-sha256"))
		}
	}
	if err := validateIncompatibleArchiveBoundary(paths); err != nil {
		return writeCompactErrorJSON(stdout, err)
	}

	release, err := rt.AcquireUpdateLock(paths)
	if err != nil {
		return writeCompactErrorJSON(stdout, err)
	}
	defer release()
	if err := validateIncompatibleArchiveBoundary(paths); err != nil {
		return writeCompactErrorJSON(stdout, err)
	}

	info, err := os.Lstat(paths.DatabasePath)
	if err != nil {
		return writeCompactErrorJSON(stdout, fmt.Errorf("inspect project-cognition.db: %w", err))
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return writeCompactErrorJSON(stdout, fmt.Errorf("project-cognition.db must be a regular non-symlink file"))
	}
	actual, err := fileSHA256(paths.DatabasePath)
	if err != nil {
		return writeCompactErrorJSON(stdout, err)
	}
	if *inspect {
		return writeCompactJSON(stdout, map[string]any{
			"status": "inspected",
			"path":   ".specify/project-cognition/project-cognition.db",
			"sha256": actual,
			"archive_argv": []string{
				"specify-runtime", "cognition", "archive-incompatible-store", "--expected-sha256", actual, "--format", "json",
			},
		})
	}
	if actual != expected {
		return writeCompactErrorJSON(stdout, fmt.Errorf("project-cognition.db changed after inspection: expected sha256 %s, found %s", expected, actual))
	}

	historyDir := filepath.Join(paths.RuntimeDir, "history")
	if err := os.MkdirAll(historyDir, 0o755); err != nil {
		return writeCompactErrorJSON(stdout, fmt.Errorf("create cognition history directory: %w", err))
	}
	if err := validateIncompatibleArchiveBoundary(paths); err != nil {
		return writeCompactErrorJSON(stdout, err)
	}
	archivePath := filepath.Join(historyDir, "project-cognition-incompatible-"+actual[:12]+".db")
	if _, err := os.Lstat(archivePath); err == nil {
		return writeCompactErrorJSON(stdout, fmt.Errorf("archive target already exists: %s", archivePath))
	} else if !os.IsNotExist(err) {
		return writeCompactErrorJSON(stdout, fmt.Errorf("inspect archive target: %w", err))
	}

	statusArchivePath := ""
	if statusInfo, statusErr := os.Lstat(paths.StatusPath); statusErr == nil {
		if statusInfo.Mode()&os.ModeSymlink != 0 || !statusInfo.Mode().IsRegular() {
			return writeCompactErrorJSON(stdout, fmt.Errorf("status.json must be a regular non-symlink file before store archival"))
		}
		statusArchivePath = filepath.Join(historyDir, "status-before-incompatible-"+actual[:12]+".json")
		if _, err := os.Lstat(statusArchivePath); err == nil {
			return writeCompactErrorJSON(stdout, fmt.Errorf("status archive target already exists: %s", statusArchivePath))
		} else if !os.IsNotExist(err) {
			return writeCompactErrorJSON(stdout, fmt.Errorf("inspect status archive target: %w", err))
		}
		if err := os.Rename(paths.StatusPath, statusArchivePath); err != nil {
			return writeCompactErrorJSON(stdout, fmt.Errorf("archive status.json: %w", err))
		}
	} else if !os.IsNotExist(statusErr) {
		return writeCompactErrorJSON(stdout, fmt.Errorf("inspect status.json: %w", statusErr))
	}

	if err := os.Rename(paths.DatabasePath, archivePath); err != nil {
		if statusArchivePath != "" {
			_ = os.Rename(statusArchivePath, paths.StatusPath)
		}
		return writeCompactErrorJSON(stdout, fmt.Errorf("archive project-cognition.db: %w", err))
	}
	if err := rt.WriteStatus(paths, rt.DefaultStatus(paths)); err != nil {
		_ = os.Rename(archivePath, paths.DatabasePath)
		if statusArchivePath != "" {
			_ = os.Rename(statusArchivePath, paths.StatusPath)
		}
		return writeCompactErrorJSON(stdout, fmt.Errorf("write reset cognition status: %w", err))
	}

	relativeArchive, _ := filepath.Rel(paths.Root, archivePath)
	payload := map[string]any{
		"status":       "archived",
		"sha256":       actual,
		"archive_path": filepath.ToSlash(relativeArchive),
		"next_action":  "run_map_scan_build",
		"next_argv": []string{
			"specify-runtime", "cognition", "scan-prepare", "--format", "json",
		},
	}
	if statusArchivePath != "" {
		relativeStatus, _ := filepath.Rel(paths.Root, statusArchivePath)
		payload["status_archive_path"] = filepath.ToSlash(relativeStatus)
	}
	return writeCompactJSON(stdout, payload)
}

// Archival is the only supported incompatible-store recovery. Refuse redirected
// control directories before acquiring a lock or moving either original file.
func validateIncompatibleArchiveBoundary(paths rt.Paths) error {
	root, err := filepath.Abs(paths.Root)
	if err != nil {
		return err
	}
	runtimeDir := filepath.Join(root, rt.SpecifyDir, rt.CognitionDir)
	if filepath.Clean(paths.RuntimeDir) != runtimeDir ||
		filepath.Clean(paths.DatabasePath) != filepath.Join(runtimeDir, rt.DBFileName) ||
		filepath.Clean(paths.StatusPath) != filepath.Join(runtimeDir, rt.StatusFileName) {
		return fmt.Errorf("incompatible-store archive paths must remain inside the project cognition directory")
	}
	for _, path := range []string{filepath.Join(root, rt.SpecifyDir), runtimeDir, filepath.Join(runtimeDir, "history")} {
		info, err := os.Lstat(path)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return fmt.Errorf("inspect archive directory %s: %w", path, err)
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
			return fmt.Errorf("archive directory %s must be a real non-symlink directory", path)
		}
	}
	lockPath := filepath.Join(runtimeDir, ".update.lock")
	if info, err := os.Lstat(lockPath); err == nil {
		if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
			return fmt.Errorf("archive update lock must be a regular non-symlink file")
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("inspect archive update lock: %w", err)
	}
	return nil
}

func fileSHA256(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("open project-cognition.db: %w", err)
	}
	defer file.Close()
	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", fmt.Errorf("hash project-cognition.db: %w", err)
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}
