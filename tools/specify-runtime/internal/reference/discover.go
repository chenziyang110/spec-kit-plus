package reference

import (
	"errors"
	"os"
	"path/filepath"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
)

type DiscoverPayload struct {
	Projects []ProjectInfo `json:"projects"`
}

type ProjectInfo struct {
	Root               string   `json:"root"`
	StatusPath         string   `json:"status_path"`
	GraphStorePath     string   `json:"graph_store_path"`
	ReferenceReadiness string   `json:"reference_readiness"`
	Freshness          string   `json:"freshness"`
	GraphReady         bool     `json:"graph_ready"`
	Blockers           []string `json:"blockers"`
	Warnings           []string `json:"warnings"`
}

func Discover(root string) (DiscoverPayload, error) {
	if root == "" {
		root = "."
	}
	var projects []ProjectInfo
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if !d.IsDir() || d.Name() != rt.CognitionDir || filepath.Base(filepath.Dir(path)) != rt.SpecifyDir {
			return nil
		}
		projectRoot := filepath.Dir(filepath.Dir(path))
		paths, err := rt.ResolvePaths(projectRoot)
		if err != nil {
			return nil
		}
		status, err := rt.ReadStatus(paths)
		info := ProjectInfo{
			Root:           filepath.ToSlash(projectRoot),
			StatusPath:     filepath.ToSlash(paths.StatusPath),
			GraphStorePath: ".specify/project-cognition/project-cognition.db",
			Blockers:       []string{},
			Warnings:       []string{},
		}
		if errors.Is(err, rt.ErrUnsupportedLegacy) {
			info.ReferenceReadiness = rt.UnsupportedReadiness
			info.Freshness = "unsupported"
			info.Blockers = append(info.Blockers, rt.ErrLegacyCode)
		} else if err != nil {
			info.ReferenceReadiness = "error"
			info.Blockers = append(info.Blockers, err.Error())
		} else {
			info.ReferenceReadiness = status.Readiness
			info.Freshness = status.Freshness
			info.GraphReady = status.Readiness == rt.ReadyReadiness
			if agreement, ok := runtimegate.CheckExisting(paths); ok && agreement.Status != "ok" {
				info.ReferenceReadiness = rt.BlockedReadiness
				info.GraphReady = false
				if agreement.RecoveryAction != "" {
					info.Blockers = append(info.Blockers, agreement.RecoveryAction)
				} else if agreement.RecommendedNextAction != "" {
					info.Blockers = append(info.Blockers, agreement.RecommendedNextAction)
				}
				info.Blockers = append(info.Blockers, agreement.Errors...)
			}
		}
		projects = append(projects, info)
		return filepath.SkipDir
	})
	if err != nil {
		return DiscoverPayload{}, err
	}
	return DiscoverPayload{Projects: projects}, nil
}
