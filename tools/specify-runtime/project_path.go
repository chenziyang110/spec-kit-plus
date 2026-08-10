package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

func secureProjectPath(projectRoot, relative string) (string, error) {
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return "", err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return "", err
	}
	target := filepath.Join(root, filepath.FromSlash(relative))
	relativeToRoot, err := filepath.Rel(root, target)
	if err != nil || relativeToRoot == ".." || strings.HasPrefix(relativeToRoot, ".."+string(filepath.Separator)) {
		return "", fmt.Errorf("path must stay inside the project root")
	}

	current := root
	for _, component := range strings.Split(relativeToRoot, string(filepath.Separator)) {
		if component == "" || component == "." {
			continue
		}
		current = filepath.Join(current, component)
		info, statErr := os.Lstat(current)
		if os.IsNotExist(statErr) {
			continue
		}
		if statErr != nil {
			return "", statErr
		}
		if info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("project path crosses symlink or junction %q", current)
		}
		// Windows directory junctions and other reparse points are not always
		// reported through os.ModeSymlink. Resolve every existing ancestor and
		// reject any indirection, including one that happens to land back inside
		// the project, so callers never write through an alias boundary.
		resolved, resolveErr := filepath.EvalSymlinks(current)
		if resolveErr != nil {
			return "", resolveErr
		}
		resolved, resolveErr = filepath.Abs(resolved)
		if resolveErr != nil {
			return "", resolveErr
		}
		currentAbs, currentErr := filepath.Abs(current)
		if currentErr != nil {
			return "", currentErr
		}
		same := filepath.Clean(resolved) == filepath.Clean(currentAbs)
		if runtime.GOOS == "windows" {
			same = strings.EqualFold(filepath.Clean(resolved), filepath.Clean(currentAbs))
		}
		if !same {
			return "", fmt.Errorf("project path crosses reparse point %q", current)
		}
	}
	return target, nil
}

func secureProjectReadFile(projectRoot, relative string) ([]byte, error) {
	target, err := secureProjectPath(projectRoot, relative)
	if err != nil {
		return nil, err
	}
	return os.ReadFile(target)
}
