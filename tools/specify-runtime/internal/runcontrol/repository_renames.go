package runcontrol

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"

	runtimecmd "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

type WorkspaceRename struct{ Before, After string }

// InspectWorkspaceRenames retains both endpoints from the same Git comparison
// used by the native delta owner. It also detects exact unstaged moves whose new
// endpoint is untracked, which Git diff alone represents only as a deletion.
func InspectWorkspaceRenames(ctx context.Context, root, baselineJSON string) ([]WorkspaceRename, error) {
	base, err := ReadHeadCommit(ctx, root)
	if err != nil {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		// The native Work owner also supports initialized, unborn repositories.
		base = emptyGitTreeOID
	}
	if baselineJSON != "" {
		var baseline WorkspaceBaseline
		if err := json.Unmarshal([]byte(baselineJSON), &baseline); err != nil {
			return nil, err
		}
		base = baseline.HeadCommit
	}
	if base == "" {
		base = emptyGitTreeOID
	}
	raw, err := runtimecmd.CommandOutputContext(ctx, root, nil, "git", "diff", "--name-status", "-z", "--find-renames", base)
	if err != nil {
		return nil, fmt.Errorf("inspect rename endpoints: %w", err)
	}
	fields := bytes.Split(raw, []byte{0})
	renamed := map[string]WorkspaceRename{}
	deleted := []string{}
	for i := 0; i < len(fields); {
		status := string(fields[i])
		i++
		if status == "" {
			continue
		}
		count := 1
		if strings.HasPrefix(status, "R") || strings.HasPrefix(status, "C") {
			count = 2
		}
		if i+count > len(fields) {
			return nil, fmt.Errorf("malformed Git rename delta")
		}
		paths := []string{}
		for j := 0; j < count; j++ {
			value, _, err := normalizeWorkPath(filepath.ToSlash(string(fields[i])), runtime.GOOS == "windows")
			i++
			if err != nil {
				return nil, err
			}
			paths = append(paths, value)
		}
		if strings.HasPrefix(status, "R") {
			renamed[paths[0]+"\x00"+paths[1]] = WorkspaceRename{Before: paths[0], After: paths[1]}
		}
		if status == "D" {
			deleted = append(deleted, paths[0])
		}
	}
	if len(deleted) > 0 {
		raw, err := runtimecmd.CommandOutputContext(ctx, root, nil, "git", "ls-files", "--others", "--exclude-standard", "-z")
		if err != nil {
			return nil, err
		}
		untracked := map[string][]byte{}
		for _, ref := range bytes.Split(raw, []byte{0}) {
			if len(ref) == 0 {
				continue
			}
			value, key, err := normalizeWorkPath(filepath.ToSlash(string(ref)), runtime.GOOS == "windows")
			if err != nil {
				return nil, err
			}
			if isPrivateRuntimeDeltaPath(key) {
				continue
			}
			info, err := os.Lstat(filepath.Join(root, filepath.FromSlash(value)))
			if err != nil || !info.Mode().IsRegular() {
				continue
			}
			contents, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(value)))
			if err != nil {
				return nil, err
			}
			untracked[value] = contents
		}
		for _, before := range deleted {
			contents, err := runtimecmd.CommandOutputContext(ctx, root, nil, "git", "show", base+":"+before)
			if err != nil {
				return nil, err
			}
			for after, candidate := range untracked {
				if bytes.Equal(contents, candidate) {
					renamed[before+"\x00"+after] = WorkspaceRename{Before: before, After: after}
				}
			}
		}
	}
	keys := make([]string, 0, len(renamed))
	for key := range renamed {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]WorkspaceRename, 0, len(keys))
	for _, key := range keys {
		result = append(result, renamed[key])
	}
	return result, nil
}
