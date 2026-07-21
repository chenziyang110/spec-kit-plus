// Package buildinfo exposes the machine-verifiable project-cognition runtime
// contract and the source provenance embedded by the Go toolchain or release
// build.
package buildinfo

import (
	"runtime/debug"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const RuntimeProtocol = "project-cognition.v2"

// SourceRevision and BuildDirty may be populated by release builds with
// -ldflags. When unset, Current falls back to Go's VCS build settings.
var (
	SourceRevision string
	BuildDirty     string
)

// Info is emitted by `project-cognition version --format json` and consumed by
// Specify before a cached runtime is trusted.
type Info struct {
	Version         string `json:"version"`
	RuntimeProtocol string `json:"runtime_protocol"`
	SchemaVersion   int    `json:"schema_version"`
	SourceRevision  string `json:"source_revision"`
	Dirty           bool   `json:"dirty"`
}

// Current returns build information from the running executable.
func Current(version string) Info {
	settings := map[string]string{}
	if info, ok := debug.ReadBuildInfo(); ok {
		for _, setting := range info.Settings {
			settings[setting.Key] = setting.Value
		}
	}
	return FromSettings(version, settings)
}

// FromSettings constructs Info from Go VCS build settings. It is exported so
// the contract can be tested without depending on how `go test` was invoked.
func FromSettings(version string, settings map[string]string) Info {
	version = strings.TrimSpace(version)
	if version == "" {
		version = "dev"
	}

	revision := strings.TrimSpace(SourceRevision)
	if revision == "" {
		revision = strings.TrimSpace(settings["vcs.revision"])
	}
	if revision == "" {
		revision = "unknown"
	}

	dirtySetting := strings.TrimSpace(BuildDirty)
	if dirtySetting == "" {
		dirtySetting = strings.TrimSpace(settings["vcs.modified"])
	}

	return Info{
		Version:         version,
		RuntimeProtocol: RuntimeProtocol,
		SchemaVersion:   store.SchemaVersion,
		SourceRevision:  revision,
		Dirty:           parseDirty(dirtySetting),
	}
}

func parseDirty(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "", "0", "false", "no", "off":
		return false
	case "1", "true", "yes", "on":
		return true
	default:
		// Unknown provenance must fail closed when the installer evaluates it.
		return true
	}
}
