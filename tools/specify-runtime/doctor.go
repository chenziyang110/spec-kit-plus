package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	goruntime "runtime"
	"strings"

	runtimepaths "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func runDoctor(args []string, stdout io.Writer) int {
	cwd, err := os.Getwd()
	if err != nil {
		return writeEnvelope(stdout, doctorBlocked(".", "working-directory-unavailable", err.Error()))
	}
	projectRoot, err := runtimepaths.FindProjectRoot(cwd)
	if err != nil {
		return writeEnvelope(stdout, doctorBlocked(cwd, "project-root-unavailable", err.Error()))
	}
	return writeEnvelope(stdout, diagnoseProjectRuntime(projectRoot))
}

func diagnoseProjectRuntime(projectRoot string) Envelope {
	env := NewEnvelope("ok", "project runtime binding is healthy")
	env.Data["project_root"] = projectRoot
	env.Data["runtime_entrypoint"] = projectRuntimeRelativeEntrypoint()

	specifyDir := filepath.Join(projectRoot, ".specify")
	if info, statErr := os.Stat(specifyDir); statErr != nil || !info.IsDir() {
		return doctorBlocked(projectRoot, "missing-specify-project", "the project has no .specify directory")
	}

	entrypoint := filepath.Join(projectRoot, filepath.FromSlash(strings.TrimPrefix(normalizedRuntimeEntrypoint(), "./")))
	info, statErr := os.Lstat(entrypoint)
	if statErr != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return doctorBlocked(
			projectRoot,
			"missing-project-runtime",
			fmt.Sprintf("project runtime entrypoint is missing or unsafe: %s", projectRuntimeRelativeEntrypoint()),
		)
	}

	configPath := filepath.Join(specifyDir, "config.json")
	raw, readErr := os.ReadFile(configPath)
	if readErr != nil {
		return doctorBlocked(projectRoot, "missing-runtime-config", "cannot read .specify/config.json")
	}
	var config map[string]any
	if jsonErr := json.Unmarshal(raw, &config); jsonErr != nil {
		return doctorBlocked(projectRoot, "invalid-runtime-config", jsonErr.Error())
	}
	launcher, ok := config["runtime_launcher"].(map[string]any)
	if !ok {
		return doctorBlocked(projectRoot, "missing-runtime-launcher", "runtime_launcher is not configured")
	}
	argv, ok := launcher["argv"].([]any)
	if !ok || len(argv) != 1 {
		return doctorBlocked(projectRoot, "invalid-runtime-launcher", "runtime_launcher.argv must contain one project-relative entrypoint")
	}
	configured, ok := argv[0].(string)
	if !ok || normalizeRuntimePath(configured) != normalizedRuntimeEntrypoint() {
		return doctorBlocked(projectRoot, "nonlocal-runtime-launcher", "runtime_launcher must use the project-local .specify/bin entrypoint")
	}

	binding, ok := config["runtime_launcher_binding"].(map[string]any)
	if !ok {
		return doctorBlocked(projectRoot, "missing-runtime-binding", "runtime_launcher_binding is not configured")
	}
	expectedDigest, _ := binding["runtime_binary_sha256"].(string)
	actualDigest, digestErr := doctorFileSHA256(entrypoint)
	if digestErr != nil {
		return doctorBlocked(projectRoot, "runtime-digest-unavailable", digestErr.Error())
	}
	if expectedDigest == "" || !strings.EqualFold(expectedDigest, actualDigest) {
		return doctorBlocked(projectRoot, "runtime-digest-mismatch", "project runtime digest does not match its binding")
	}
	env.Data["runtime_binary_sha256"] = actualDigest
	env.Data["config_path"] = ".specify/config.json"
	return env
}

func doctorBlocked(projectRoot, code, cause string) Envelope {
	env := NewEnvelope("blocked", "project runtime binding requires bootstrap repair")
	env.Data["project_root"] = projectRoot
	env.Data["error_code"] = code
	env.Data["bootstrap_required"] = true
	env.Blockers = append(env.Blockers, map[string]any{
		"code":              code,
		"owner":             "user",
		"cause":             cause,
		"exact_next_action": "Run the trusted external Specify bootstrap/upgrade flow from the project root, then rerun the interrupted SP/SPX command.",
		"unblock_criteria":  "specify-runtime doctor returns status ok using the project-local entrypoint",
	})
	return env
}

func projectRuntimeRelativeEntrypoint() string {
	name := "specify-runtime"
	if goruntime.GOOS == "windows" {
		name += ".exe"
		return `.\.specify\bin\` + name
	}
	return "./.specify/bin/" + name
}

func normalizedRuntimeEntrypoint() string {
	return normalizeRuntimePath(projectRuntimeRelativeEntrypoint())
}

func normalizeRuntimePath(value string) string {
	normalized := filepath.ToSlash(strings.TrimSpace(value))
	if strings.HasPrefix(normalized, "./") {
		return normalized
	}
	return "./" + strings.TrimLeft(normalized, "/")
}

func doctorFileSHA256(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()
	digest := sha256.New()
	if _, err := io.Copy(digest, file); err != nil {
		return "", err
	}
	return hex.EncodeToString(digest.Sum(nil)), nil
}
