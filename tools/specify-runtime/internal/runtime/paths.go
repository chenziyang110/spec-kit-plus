package runtime

import (
	"os"
	"path/filepath"
)

const (
	SpecifyDir     = ".specify"
	CognitionDir   = "project-cognition"
	StatusFileName = "status.json"
	DBFileName     = "project-cognition.db"
)

type Paths struct {
	Root         string
	RuntimeDir   string
	StatusPath   string
	DatabasePath string
}

func ResolvePaths(start string) (Paths, error) {
	root, err := FindProjectRoot(start)
	if err != nil {
		return Paths{}, err
	}
	dir := filepath.Join(root, SpecifyDir, CognitionDir)
	return Paths{
		Root:         root,
		RuntimeDir:   dir,
		StatusPath:   filepath.Join(dir, StatusFileName),
		DatabasePath: filepath.Join(dir, DBFileName),
	}, nil
}

func FindProjectRoot(start string) (string, error) {
	if start == "" {
		start = "."
	}
	abs, err := filepath.Abs(start)
	if err != nil {
		return "", err
	}
	info, err := os.Stat(abs)
	if err == nil && !info.IsDir() {
		abs = filepath.Dir(abs)
	}
	for {
		if _, err := os.Stat(filepath.Join(abs, SpecifyDir)); err == nil {
			return abs, nil
		}
		parent := filepath.Dir(abs)
		if parent == abs {
			return filepath.Abs(start)
		}
		abs = parent
	}
}
