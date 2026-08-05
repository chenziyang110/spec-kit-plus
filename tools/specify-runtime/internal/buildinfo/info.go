// Package buildinfo exposes the machine-verifiable unified runtime contract and
// the source provenance embedded by the Go toolchain or release build.
package buildinfo

import (
	"runtime/debug"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

const RuntimeProtocol = "project-cognition.v2"

// ReleaseIdentity is the canonical, externally inspectable release marker. A
// release build sets it with -ldflags to:
//
//	specify-runtime.release.v1,version=<tag>,revision=<sha>,dirty=<bool>
//
// Current derives every reported release identity field from that one marker,
// so cross-compiled assets can be checked without executing the target binary.
// SourceRevision and BuildDirty remain compatibility overrides for local and
// older build scripts. When all overrides are unset, Current falls back to
// Go's VCS build settings.
var (
	ReleaseIdentity string
	SourceRevision  string
	BuildDirty      string
)

// Info is emitted by `specify-runtime version --format json` and consumed by
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

	if strings.TrimSpace(ReleaseIdentity) != "" {
		releaseVersion, releaseRevision, releaseDirty, ok := parseReleaseIdentity(ReleaseIdentity)
		if !ok {
			// A malformed explicit release marker must never fall back to identity
			// fields that could make an untrusted release look valid.
			version, revision, dirtySetting = "dev", "unknown", "true"
		} else {
			version, revision, dirtySetting = releaseVersion, releaseRevision, releaseDirty
		}
	}

	return Info{
		Version:         version,
		RuntimeProtocol: RuntimeProtocol,
		SchemaVersion:   store.SchemaVersion,
		SourceRevision:  revision,
		Dirty:           parseDirty(dirtySetting),
	}
}

func parseReleaseIdentity(value string) (string, string, string, bool) {
	parts := strings.Split(strings.TrimSpace(value), ",")
	if len(parts) != 4 || parts[0] != "specify-runtime.release.v1" {
		return "", "", "", false
	}
	fields := map[string]string{}
	for _, part := range parts[1:] {
		key, raw, found := strings.Cut(part, "=")
		if !found || strings.TrimSpace(key) == "" || strings.TrimSpace(raw) == "" {
			return "", "", "", false
		}
		if _, duplicate := fields[key]; duplicate {
			return "", "", "", false
		}
		fields[key] = strings.TrimSpace(raw)
	}
	version := fields["version"]
	revision := fields["revision"]
	dirty := strings.ToLower(fields["dirty"])
	if version == "" || revision == "" || (dirty != "true" && dirty != "false") {
		return "", "", "", false
	}
	return version, revision, dirty, true
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
