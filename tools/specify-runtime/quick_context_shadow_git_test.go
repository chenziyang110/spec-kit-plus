package main

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

const shadowGitHelperMode = "_SPECIFY_SHADOW_GIT_HELPER_MODE"

// A copied test executable acts as the subprocess, without relying on shell,
// Python, symlink privileges, or an additional compiled fixture. This code is
// test-only. Production executes the local Git resolved on PATH.
func init() {
	mode := os.Getenv(shadowGitHelperMode)
	if mode == "" || len(os.Args) < 2 || os.Args[1] != "--no-optional-locks" {
		return
	}
	root := os.Getenv("_SPECIFY_SHADOW_GIT_HELPER_ROOT")
	marker := os.Getenv("_SPECIFY_SHADOW_GIT_HELPER_MARKER")
	if marker != "" {
		_ = os.WriteFile(marker, []byte("started"), 0600)
	}
	switch mode {
	case "hang":
		for {
			time.Sleep(time.Second)
		}
	case "flood":
		data := []byte(strings.Repeat("x", 65536))
		for {
			if _, err := os.Stdout.Write(data); err != nil {
				os.Exit(3)
			}
		}
	case "invalid-utf8":
		_, _ = os.Stdout.Write([]byte{255, '\n'})
	case "crlf":
		fmt.Printf("%s\r\n%s\r\n", root, strings.Repeat("a", 40))
	case "bad-head":
		fmt.Printf("%s\nnot-a-revision\n", root)
	case "bad-root":
		fmt.Printf("%s\n%s\n", filepath.Dir(root), strings.Repeat("a", 40))
	case "sensitive-failure":
		fmt.Fprintln(os.Stderr, "SECRET_FIXTURE_MUST_NOT_LEAK")
		os.Exit(1)
	default:
		fmt.Printf("%s\n%s\n", root, strings.Repeat("a", 40))
	}
	os.Exit(0)
}

func shadowInstallGitHelper(t *testing.T, mode string) (string, string) {
	t.Helper()
	dir := t.TempDir()
	name := "git"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	self, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(self)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, name), data, 0700); err != nil {
		t.Fatal(err)
	}
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	marker := filepath.Join(t.TempDir(), "child-started")
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
	t.Setenv(shadowGitHelperMode, mode)
	t.Setenv("_SPECIFY_SHADOW_GIT_HELPER_ROOT", root)
	t.Setenv("_SPECIFY_SHADOW_GIT_HELPER_MARKER", marker)
	return root, marker
}

func TestQuickShadowGitCancellationReapsChild(t *testing.T) {
	root, marker := shadowInstallGitHelper(t, "hang")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { _, err := quickShadowRevisionWithContext(ctx, root); done <- err }()
	deadline := time.After(3 * time.Second)
	for {
		if _, err := os.Stat(marker); err == nil {
			break
		}
		select {
		case err := <-done:
			t.Fatalf("child did not start: %v", err)
		case <-deadline:
			t.Fatal("child start not observed")
		case <-time.After(5 * time.Millisecond):
		}
	}
	cancel()
	select {
	case err := <-done:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("lost cancellation: %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("parent cancellation did not terminate and wait for Git child")
	}
}

func TestQuickShadowGitPreCancelledDoesNotSpawn(t *testing.T) {
	root, marker := shadowInstallGitHelper(t, "valid")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := quickShadowRevisionWithContext(ctx, root); !errors.Is(err, context.Canceled) {
		t.Fatal(err)
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatal("cancelled invocation spawned a child")
	}
	if _, err := quickShadowRevisionWithContext(nil, root); err == nil {
		t.Fatal("nil context accepted")
	}
}

func TestQuickShadowGitParentDeadlinePreserved(t *testing.T) {
	root, _ := shadowInstallGitHelper(t, "hang")
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Millisecond)
	defer cancel()
	start := time.Now()
	if _, err := quickShadowRevisionWithContext(ctx, root); !errors.Is(err, context.DeadlineExceeded) {
		t.Fatal(err)
	}
	if time.Since(start) > 2*time.Second {
		t.Fatal("child ignored the shorter parent deadline")
	}
}

func TestQuickShadowGitOutputOverflowStopsChild(t *testing.T) {
	root, _ := shadowInstallGitHelper(t, "flood")
	start := time.Now()
	value, err := quickShadowRevisionWithContext(context.Background(), root)
	if err == nil || !strings.Contains(err.Error(), "quick_shadow_git_output_limit") || value != "" {
		t.Fatalf("bad overflow result: %q %v", value, err)
	}
	if time.Since(start) > 2*time.Second {
		t.Fatal("overflow waited for the five-second timeout")
	}
}

func TestQuickShadowGitWireValidation(t *testing.T) {
	for _, mode := range []string{"valid", "crlf", "invalid-utf8", "bad-head", "bad-root", "sensitive-failure"} {
		t.Run(mode, func(t *testing.T) {
			root, _ := shadowInstallGitHelper(t, mode)
			value, err := quickShadowRevision(root)
			if mode == "valid" || mode == "crlf" {
				if err != nil || value != strings.Repeat("a", 40) {
					t.Fatal(value, err)
				}
			} else {
				if err == nil || value != "" {
					t.Fatal("malformed identity accepted")
				}
				if strings.Contains(err.Error(), "SECRET_FIXTURE") {
					t.Fatal("child stderr leaked")
				}
			}
		})
	}
}

// Hide WriterTo to exercise io.Copy's destination-method selection as used by
// subprocess pipes; embedding bytes.Buffer would accidentally expose ReadFrom.
type shadowReaderOnly struct{ io.Reader }

func TestQuickShadowGitBudgetCannotBeBypassedByCopy(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	b := &quickShadowGitBuffer{cancel: cancel}
	_, err := io.Copy(b, shadowReaderOnly{strings.NewReader(strings.Repeat("x", quickShadowGitOutputLimit+1))})
	if err == nil || !b.exceeded || b.Len() > quickShadowGitOutputLimit || ctx.Err() == nil {
		t.Fatal("io.Copy bypassed the bounded writer")
	}
}

func TestQuickShadowGitExactOutputLimit(t *testing.T) {
	var b quickShadowGitBuffer
	if n, err := b.Write([]byte(strings.Repeat("x", quickShadowGitOutputLimit))); err != nil || n != quickShadowGitOutputLimit {
		t.Fatal(n, err)
	}
	if _, err := b.Write([]byte("x")); err == nil || !b.exceeded || b.Len() != quickShadowGitOutputLimit {
		t.Fatal("limit was not enforced")
	}
}

func TestQuickShadowGitReadsRealRootAndIgnoresOverrides(t *testing.T) {
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("Git is required")
	}
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	run := func(args ...string) string {
		cmd := exec.Command(git, append([]string{"-C", root, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + os.DevNull}, args...)...)
		for _, e := range os.Environ() {
			k, _, _ := strings.Cut(e, "=")
			if !strings.HasPrefix(strings.ToUpper(k), "GIT_") {
				cmd.Env = append(cmd.Env, e)
			}
		}
		cmd.Env = append(cmd.Env, "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL="+os.DevNull)
		out, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("git fixture: %v %s", err, out)
		}
		return strings.TrimSpace(string(out))
	}
	run("init", "-q")
	run("commit", "--allow-empty", "-qm", "fixture")
	expected := run("rev-parse", "HEAD")
	t.Setenv("GIT_DIR", filepath.Join(t.TempDir(), "foreign"))
	t.Setenv("GIT_WORK_TREE", t.TempDir())
	got, err := quickShadowRevisionWithContext(context.Background(), root)
	if err != nil || got != expected {
		t.Fatal(got, err)
	}
	sub := filepath.Join(root, "nested")
	if err := os.Mkdir(sub, 0700); err != nil {
		t.Fatal(err)
	}
	if _, err := quickShadowRevisionWithContext(context.Background(), sub); err == nil {
		t.Fatal("parent repository accepted")
	}
}
