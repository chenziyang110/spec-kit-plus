package scanset

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

const DefaultOutputPath = ".specify/project-cognition/tmp/scan-files.json"

type Input struct {
	Scopes   []string
	Out      string
	MaxBytes int64
}

type Summary struct {
	Files string `json:"files"`
	Count int    `json:"count"`
}

type FileList struct {
	Files []string `json:"files"`
}

func Resolve(paths rt.Paths, input Input) (Summary, error) {
	outRel, outAbs, err := resolveOutput(paths.Root, input.Out)
	if err != nil {
		return Summary{}, err
	}
	files, err := Collect(paths, input, outRel)
	if err != nil {
		return Summary{}, err
	}
	if err := os.MkdirAll(filepath.Dir(outAbs), 0o755); err != nil {
		return Summary{}, fmt.Errorf("create scan set output dir: %w", err)
	}
	data, err := json.Marshal(FileList{Files: files})
	if err != nil {
		return Summary{}, fmt.Errorf("encode scan set: %w", err)
	}
	if err := os.WriteFile(outAbs, append(data, '\n'), 0o644); err != nil {
		return Summary{}, fmt.Errorf("write scan set: %w", err)
	}
	return Summary{Files: outRel, Count: len(files)}, nil
}

func Collect(paths rt.Paths, input Input, outputRel string) ([]string, error) {
	scopes := input.Scopes
	if len(scopes) == 0 {
		scopes = []string{"."}
	}
	matcher := ignore.Load(paths.Root)
	selected := map[string]bool{}
	for _, rawScope := range scopes {
		scopeRel, scopeAbs, err := normalizeRepoPath(paths.Root, rawScope)
		if err != nil {
			return nil, fmt.Errorf("invalid scope %q: %w", rawScope, err)
		}
		info, err := os.Stat(scopeAbs)
		if err != nil {
			return nil, fmt.Errorf("read scope %q: %w", rawScope, err)
		}
		if info.IsDir() {
			if err := collectDir(paths.Root, scopeAbs, matcher, input.MaxBytes, outputRel, selected); err != nil {
				return nil, err
			}
			continue
		}
		if err := maybeAddFile(scopeAbs, scopeRel, matcher, input.MaxBytes, outputRel, selected); err != nil {
			return nil, err
		}
	}
	files := make([]string, 0, len(selected))
	for path := range selected {
		files = append(files, path)
	}
	sort.Strings(files)
	return files, nil
}

func collectDir(root string, dir string, matcher ignore.Matcher, maxBytes int64, outputRel string, selected map[string]bool) error {
	return filepath.WalkDir(dir, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		rel = normalizeRel(rel)
		if rel == "" {
			return nil
		}
		if entry.IsDir() {
			if matcher.Ignored(rel) && !matcher.MayReincludeDescendant(rel) {
				return filepath.SkipDir
			}
			return nil
		}
		return maybeAddFile(path, rel, matcher, maxBytes, outputRel, selected)
	})
}

func maybeAddFile(abs string, rel string, matcher ignore.Matcher, maxBytes int64, outputRel string, selected map[string]bool) error {
	rel = normalizeRel(rel)
	if rel == "" || rel == outputRel || matcher.Ignored(rel) || secretPath(rel) {
		return nil
	}
	info, err := os.Stat(abs)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return nil
	}
	if maxBytes > 0 && info.Size() > maxBytes {
		return nil
	}
	if binaryPath(rel) || looksBinary(abs) {
		return nil
	}
	selected[rel] = true
	return nil
}

func resolveOutput(root string, raw string) (string, string, error) {
	if strings.TrimSpace(raw) == "" {
		raw = DefaultOutputPath
	}
	rel, abs, err := normalizeRepoPath(root, raw)
	if err != nil {
		return "", "", err
	}
	if rel == "" {
		return "", "", fmt.Errorf("output must be a file path inside the repository")
	}
	return rel, abs, nil
}

func normalizeRepoPath(root string, raw string) (string, string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" || raw == "." {
		return "", root, nil
	}
	var abs string
	if filepath.IsAbs(raw) {
		abs = filepath.Clean(raw)
	} else {
		abs = filepath.Join(root, filepath.FromSlash(raw))
	}
	rel, err := filepath.Rel(root, abs)
	if err != nil {
		return "", "", err
	}
	if rel == "." {
		return "", abs, nil
	}
	if strings.HasPrefix(rel, ".."+string(filepath.Separator)) || rel == ".." || filepath.IsAbs(rel) {
		return "", "", fmt.Errorf("path escapes repository root")
	}
	return normalizeRel(rel), abs, nil
}

func normalizeRel(path string) string {
	rel := filepath.ToSlash(strings.TrimSpace(path))
	for strings.HasPrefix(rel, "./") {
		rel = strings.TrimPrefix(rel, "./")
	}
	return strings.Trim(rel, "/")
}

func secretPath(path string) bool {
	base := strings.ToLower(filepath.Base(path))
	if base == ".env" || strings.HasPrefix(base, ".env.") {
		return true
	}
	switch base {
	case "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519":
		return true
	}
	switch strings.ToLower(filepath.Ext(base)) {
	case ".key", ".pem", ".p12", ".pfx":
		return true
	default:
		return false
	}
}

func binaryPath(path string) bool {
	switch strings.ToLower(filepath.Ext(path)) {
	case ".7z", ".a", ".avi", ".bin", ".bmp", ".class", ".db", ".dll", ".dylib",
		".exe", ".gif", ".gz", ".ico", ".jar", ".jpeg", ".jpg", ".mov", ".mp3",
		".mp4", ".o", ".obj", ".pdf", ".png", ".pyc", ".so", ".sqlite", ".tar",
		".tgz", ".ttf", ".wasm", ".webp", ".woff", ".woff2", ".zip":
		return true
	default:
		return false
	}
}

func looksBinary(path string) bool {
	file, err := os.Open(path)
	if err != nil {
		return false
	}
	defer file.Close()
	buf := make([]byte, 8192)
	n, err := file.Read(buf)
	if err != nil && err != io.EOF {
		return false
	}
	return bytes.IndexByte(buf[:n], 0) >= 0
}
