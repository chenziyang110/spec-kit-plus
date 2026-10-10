package changes

import (
	"bytes"
	"fmt"
	"strings"
)

const (
	maxTrackedPathBatch     = 256
	maxTrackedPathArgBudget = 16 * 1024
	trackedPathArgOverhead  = 128
)

// trackedPathsWithCommand queries only requested paths, in bounded literal
// batches. A failure discards every partial result: Git failure is not evidence
// that a path is untracked. The caller supplies the runtime's timeout-aware
// command runner; no global cache can survive a change to the Git index.
func trackedPathsWithCommand(paths []string, run func(...string) ([]byte, error)) (map[string]bool, error) {
	requested := make(map[string]bool, len(paths))
	unique := make([]string, 0, len(paths))
	for _, path := range paths {
		if path == "" || strings.IndexByte(path, 0) >= 0 {
			return nil, fmt.Errorf("invalid explicit path for tracked-path lookup")
		}
		// Conservative quoting/UTF-16 allowance keeps Windows argv bounded too.
		if trackedPathArgCost(path) > maxTrackedPathArgBudget-trackedPathArgOverhead {
			return nil, fmt.Errorf("explicit path exceeds tracked-path argument budget")
		}
		if !requested[path] {
			requested[path] = true
			unique = append(unique, path)
		}
	}
	tracked := make(map[string]bool, len(unique))
	for start := 0; start < len(unique); {
		end, budget := start, trackedPathArgOverhead
		for end < len(unique) && end-start < maxTrackedPathBatch {
			cost := trackedPathArgCost(unique[end])
			if budget+cost > maxTrackedPathArgBudget {
				break
			}
			budget += cost
			end++
		}
		args := []string{"--literal-pathspecs", "ls-files", "--cached", "-z", "--"}
		args = append(args, unique[start:end]...)
		data, err := run(args...)
		if err != nil {
			return nil, fmt.Errorf("query tracked explicit paths: %w", err)
		}
		if len(data) > 0 && data[len(data)-1] != 0 {
			return nil, fmt.Errorf("query tracked explicit paths: unterminated NUL output")
		}
		for _, field := range bytes.Split(data, []byte{0}) {
			path := string(field)
			// A directory pathspec can return children. Only exact requested
			// index entries establish tracked status; never trim filename bytes.
			if requested[path] {
				tracked[path] = true
			}
		}
		start = end
	}
	return tracked, nil
}

func trackedPathArgCost(path string) int {
	return 2*len(path) + 3
}
