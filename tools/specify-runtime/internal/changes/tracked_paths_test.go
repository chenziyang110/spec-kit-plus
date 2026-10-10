package changes

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestTrackedPathsEmptyDoesNotRunGit(t *testing.T) {
	got, err := trackedPathsWithCommand(nil, func(...string) ([]byte, error) {
		t.Fatal("empty explicit paths must not run Git")
		return nil, nil
	})
	if err != nil || len(got) != 0 {
		t.Fatalf("got %v, %v", got, err)
	}
}

func TestTrackedPathsDeduplicatesAndBatches(t *testing.T) {
	var paths []string
	for i := 0; i < 600; i++ {
		paths = append(paths, fmt.Sprintf("src/file-%04d.go", i))
	}
	paths = append(paths, paths...)
	calls := 0
	got, err := trackedPathsWithCommand(paths, func(args ...string) ([]byte, error) {
		calls++
		prefix := []string{"--literal-pathspecs", "ls-files", "--cached", "-z", "--"}
		if !reflect.DeepEqual(args[:5], prefix) {
			t.Fatalf("unsafe argv: %q", args)
		}
		batch := args[5:]
		if len(batch) > maxTrackedPathBatch {
			t.Fatalf("unbounded batch: %d", len(batch))
		}
		budget := trackedPathArgOverhead
		for _, path := range batch {
			budget += trackedPathArgCost(path)
		}
		if budget > maxTrackedPathArgBudget {
			t.Fatalf("unbounded argv: %d", budget)
		}
		return []byte(strings.Join(batch, "\x00") + "\x00"), nil
	})
	if err != nil || len(got) != 600 || calls != 3 {
		t.Fatalf("tracked=%d calls=%d err=%v", len(got), calls, err)
	}
}

func TestTrackedPathsHonorsArgumentBudget(t *testing.T) {
	var paths []string
	for i := 0; i < 20; i++ {
		paths = append(paths, strings.Repeat("长", 300)+fmt.Sprint(i))
	}
	calls := 0
	_, err := trackedPathsWithCommand(paths, func(args ...string) ([]byte, error) {
		calls++
		budget := trackedPathArgOverhead
		for _, path := range args[5:] {
			budget += trackedPathArgCost(path)
		}
		if budget > maxTrackedPathArgBudget {
			t.Fatalf("argv budget=%d", budget)
		}
		return nil, nil
	})
	if err != nil || calls < 2 {
		t.Fatalf("calls=%d err=%v", calls, err)
	}
}

func TestTrackedPathsRejectsInvalidBeforeRunning(t *testing.T) {
	for _, invalid := range []string{"", "nul\x00path", strings.Repeat("x", maxTrackedPathArgBudget)} {
		got, err := trackedPathsWithCommand([]string{"valid.go", invalid}, func(...string) ([]byte, error) {
			t.Fatal("validate all paths before issuing commands")
			return nil, nil
		})
		if err == nil || got != nil {
			t.Fatalf("invalid path accepted: %v, %v", got, err)
		}
	}
}

func TestTrackedPathsFailureDiscardsPartialResults(t *testing.T) {
	paths := make([]string, maxTrackedPathBatch+1)
	for i := range paths {
		paths[i] = fmt.Sprintf("file%d.go", i)
	}
	failure := errors.New("index unavailable")
	calls := 0
	got, err := trackedPathsWithCommand(paths, func(args ...string) ([]byte, error) {
		calls++
		if calls == 2 {
			return nil, failure
		}
		return []byte(strings.Join(args[5:], "\x00") + "\x00"), nil
	})
	if got != nil || !errors.Is(err, failure) || calls != 2 {
		t.Fatalf("partial result escaped: %v, %v, calls=%d", got, err, calls)
	}
}

func TestTrackedPathsRejectsTruncatedOutput(t *testing.T) {
	got, err := trackedPathsWithCommand([]string{"tracked.go"}, func(...string) ([]byte, error) { return []byte("tracked.go"), nil })
	if err == nil || got != nil {
		t.Fatalf("truncated output accepted: %v, %v", got, err)
	}
}

func trackedPathGitRunner(tb testing.TB, root string) func(...string) ([]byte, error) {
	tb.Helper()
	return func(args ...string) ([]byte, error) {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, "git", args...)
		cmd.Dir = root
		return cmd.Output()
	}
}

func trackedPathRepo(tb testing.TB, names []string) (string, func(...string) ([]byte, error)) {
	tb.Helper()
	if _, err := exec.LookPath("git"); err != nil {
		tb.Skip("Git is unavailable")
	}
	root := tb.TempDir()
	run := trackedPathGitRunner(tb, root)
	if _, err := run("init", "-q"); err != nil {
		tb.Fatal(err)
	}
	for _, name := range names {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			tb.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("fixture\n"), 0o644); err != nil {
			tb.Fatal(err)
		}
	}
	if _, err := run("add", "--", "."); err != nil {
		tb.Fatal(err)
	}
	return root, run
}

func TestTrackedPathsRealGitUsesLiteralExactIndexEntries(t *testing.T) {
	names := []string{"tracked.go", "deleted.go", "with space.go", "目录/检索.go", "wild[card].go", "-option.go", "nested/child.go", "old.go"}
	if runtime.GOOS != "windows" {
		names = append(names, "line\nbreak.go", " leading and trailing ")
	}
	root, run := trackedPathRepo(t, names)
	if err := os.Remove(filepath.Join(root, "deleted.go")); err != nil {
		t.Fatal(err)
	}
	if _, err := run("mv", "--", "old.go", "new.go"); err != nil {
		t.Fatal(err)
	}
	requests := append(append([]string{}, names...), "missing.go", "nested", "new.go", "wildc.go")
	got, err := trackedPathsWithCommand(requests, run)
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range names {
		want := name != "old.go"
		if got[name] != want {
			t.Errorf("%q tracked=%v, want %v", name, got[name], want)
		}
	}
	if !got["new.go"] || got["old.go"] || got["nested"] || got["missing.go"] || got["wildc.go"] {
		t.Fatalf("not exact index membership: %v", got)
	}
	if _, err := run("rm", "--cached", "--", "tracked.go"); err != nil {
		t.Fatal(err)
	}
	updated, err := trackedPathsWithCommand([]string{"tracked.go"}, run)
	if err != nil || updated["tracked.go"] {
		t.Fatalf("stale cached index membership: %v, %v", updated, err)
	}
}

func TestTrackedPathsRealGitFailureIsNotUntracked(t *testing.T) {
	_, run := trackedPathRepo(t, []string{"tracked.go"})
	root := t.TempDir()
	run = trackedPathGitRunner(t, root)
	got, err := trackedPathsWithCommand([]string{"tracked.go"}, run)
	if err == nil || got != nil {
		t.Fatalf("non-repository accepted as untracked: %v, %v", got, err)
	}
}

var trackedPathBenchmarkSink map[string]bool

func BenchmarkTrackedPathsRealGit(b *testing.B) {
	paths := make([]string, 128)
	for i := range paths {
		paths[i] = fmt.Sprintf("file-%04d.go", i)
	}
	_, run := trackedPathRepo(b, paths)
	for _, mode := range []string{"per_path", "batched"} {
		b.Run(mode, func(b *testing.B) {
			b.ReportAllocs()
			for i := 0; i < b.N; i++ {
				var got map[string]bool
				if mode == "per_path" {
					got = make(map[string]bool, len(paths))
					for _, path := range paths {
						_, err := run("ls-files", "--error-unmatch", "--", path)
						got[path] = err == nil
					}
				} else {
					var err error
					got, err = trackedPathsWithCommand(paths, run)
					if err != nil {
						b.Fatal(err)
					}
				}
				trackedPathBenchmarkSink = got
			}
		})
	}
}
