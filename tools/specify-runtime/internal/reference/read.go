package reference

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtimegate"
)

type ReadPayload struct {
	Admission        map[string]any `json:"admission"`
	Slice            any            `json:"slice"`
	Graph            map[string]any `json:"graph"`
	Provenance       map[string]any `json:"provenance"`
	MinimalReadOrder []string       `json:"minimal_read_order"`
}

func Read(project, slice string, includeGraphs []string) (ReadPayload, error) {
	if project == "" {
		project = "."
	}
	if slice == "" {
		slice = "overview"
	}
	paths, err := rt.ResolvePaths(project)
	if err != nil {
		return ReadPayload{}, err
	}
	if err := blockSplitBrainReference(paths); err != nil {
		return ReadPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return ReadPayload{}, err
	}
	if status.Freshness != rt.ReadyFreshness || status.Readiness != rt.ReadyReadiness {
		return ReadPayload{}, fmt.Errorf("reference project is not fresh and query-ready")
	}
	slicePath := filepath.Join(paths.RuntimeDir, "slices", slice+".json")
	slicePayload, err := readJSON(slicePath)
	if err != nil {
		return ReadPayload{}, err
	}
	graph := map[string]any{}
	readOrder := []string{filepath.ToSlash(slicePath)}
	for _, name := range includeGraphs {
		graphPath := filepath.Join(paths.RuntimeDir, "graphs", name+".json")
		payload, err := readJSON(graphPath)
		if err != nil {
			return ReadPayload{}, err
		}
		graph[name] = payload
		readOrder = append(readOrder, filepath.ToSlash(graphPath))
	}
	return ReadPayload{
		Admission: map[string]any{
			"status":    "accepted",
			"freshness": status.Freshness,
			"readiness": status.Readiness,
		},
		Slice: slicePayload,
		Graph: graph,
		Provenance: map[string]any{
			"project":     filepath.ToSlash(paths.Root),
			"status_path": filepath.ToSlash(paths.StatusPath),
		},
		MinimalReadOrder: readOrder,
	}, nil
}

func readJSON(path string) (any, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var raw any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}
	return raw, nil
}

func blockSplitBrainReference(paths rt.Paths) error {
	return runtimegate.BlockIfExisting(paths)
}
