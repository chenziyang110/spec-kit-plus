package main

import (
	"bytes"
	stdcontext "context"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
	"unicode/utf8"
)

const quickShadowGitOutputLimit = 16 * 1024

// Only the os/exec copying goroutine writes this buffer. It is examined after
// Cmd.Run joins that goroutine, including the cancelled/overflow path.
type quickShadowGitBuffer struct {
	buffer   bytes.Buffer
	exceeded bool
	cancel   stdcontext.CancelFunc
}

func (b *quickShadowGitBuffer) Len() int      { return b.buffer.Len() }
func (b *quickShadowGitBuffer) Bytes() []byte { return b.buffer.Bytes() }

// Do not embed bytes.Buffer: its promoted ReadFrom method would allow io.Copy
// to bypass Write and its budget/cancellation checks on subprocess pipes.
func (b *quickShadowGitBuffer) Write(data []byte) (int, error) {
	remaining := quickShadowGitOutputLimit - b.Len()
	if b.exceeded || len(data) > remaining {
		b.exceeded = true
		if b.cancel != nil {
			b.cancel()
		}
		return 0, io.ErrShortBuffer
	}
	return b.buffer.Write(data)
}

// A single local read-only Git invocation identifies BOTH the project and HEAD.
// Ambient GIT_DIR/config overrides cannot silently redirect the selected repo.
func quickShadowRevision(root string) (string, error) {
	return quickShadowRevisionWithContext(stdcontext.Background(), root)
}

func quickShadowRevisionWithContext(parent stdcontext.Context, root string) (string, error) {
	if parent == nil {
		return "", fmt.Errorf("quick_shadow_context_missing")
	}
	if err := parent.Err(); err != nil {
		return "", err
	}
	ctx, cancel := stdcontext.WithTimeout(parent, 5*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "--no-optional-locks", "-C", root,
		"rev-parse", "--show-toplevel", "--verify", "HEAD")
	cmd.WaitDelay = time.Second
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		if !strings.HasPrefix(strings.ToUpper(key), "GIT_") {
			cmd.Env = append(cmd.Env, entry)
		}
	}
	cmd.Env = append(cmd.Env, "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL="+os.DevNull,
		"GIT_TERMINAL_PROMPT=0", "GIT_NO_LAZY_FETCH=1")
	// A misbehaving local Git executable must not allocate unbounded stdout.
	var output quickShadowGitBuffer
	output.cancel = cancel
	cmd.Stdout, cmd.Stderr = &output, io.Discard
	err := cmd.Run()
	if output.exceeded {
		return "", fmt.Errorf("quick_shadow_git_output_limit: identity exceeds %d bytes", quickShadowGitOutputLimit)
	}
	if ctx.Err() != nil {
		return "", fmt.Errorf("quick_shadow_query_cancelled: %w", ctx.Err())
	}
	if err != nil {
		return "", fmt.Errorf("quick_shadow_git_unavailable: require a local Git root with HEAD; no fallback identity")
	}
	raw := output.Bytes()
	if !utf8.Valid(raw) {
		return "", fmt.Errorf("quick_shadow_git_identity_invalid: require UTF-8")
	}
	// Strip only the record terminator. TrimSpace would change a real path.
	lines := strings.Split(strings.TrimSuffix(string(raw), "\n"), "\n")
	if len(lines) != 2 {
		return "", fmt.Errorf("quick_shadow_git_identity_invalid")
	}
	top, err := filepath.EvalSymlinks(strings.TrimSuffix(lines[0], "\r"))
	if err != nil {
		return "", err
	}
	same := filepath.Clean(top) == filepath.Clean(root)
	if runtime.GOOS == "windows" {
		same = strings.EqualFold(filepath.Clean(top), filepath.Clean(root))
	}
	if !same {
		return "", fmt.Errorf("quick_shadow_git_root_mismatch: do not bind a parent repository")
	}
	revision := strings.TrimSuffix(lines[1], "\r")
	decoded, err := hex.DecodeString(revision)
	if err != nil || (len(decoded) != 20 && len(decoded) != 32) || strings.ToLower(revision) != revision {
		return "", fmt.Errorf("quick_shadow_git_revision_invalid")
	}
	if err := ctx.Err(); err != nil {
		return "", err
	}
	return revision, nil
}
