package scanworkbench

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestRepositorySourceDigestStreamsExactContentAndRejectsEscape(t *testing.T) {
	root := t.TempDir()
	data := bytes.Repeat([]byte("导航\x000123456789\n"), 100000)
	if err := os.WriteFile(filepath.Join(root, "source.go"), data, 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := repositorySourceDigest(root, "source.go")
	want := sha256.Sum256(data)
	if err != nil || got != "sha256:"+hex.EncodeToString(want[:]) {
		t.Fatalf("digest = %q err=%v", got, err)
	}
	if _, err := repositorySourceDigest(root, "../outside.go"); err == nil {
		t.Fatal("outside path accepted")
	}
}

func TestRequestSourceObservationDoesNotAuthorizeChangedReplay(t *testing.T) {
	for _, replacement := range []bool{false, true} {
		t.Run(map[bool]string{false: "same-size-mtime", true: "replacement"}[replacement], func(t *testing.T) {
			paths := newScanPaths(t, []string{"src/a.go"})
			path := filepath.Join(paths.Root, "src", "a.go")
			original, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			info, err := os.Stat(path)
			if err != nil {
				t.Fatal(err)
			}
			classifications, err := classifyRepositoryPaths(paths.Root, []string{"src/a.go"}, false)
			if err != nil {
				t.Fatal(err)
			}
			before, sources, err := preparationFingerprintWithSources(paths.Root, "scan-set.json", []string{"src/a.go"}, classifications, PrepareInput{}, "")
			if err != nil {
				t.Fatal(err)
			}
			if replacement {
				if err := os.Remove(path); err != nil {
					t.Fatal(err)
				}
			}
			if err := os.WriteFile(path, bytes.Repeat([]byte("x"), len(original)), 0o644); err != nil {
				t.Fatal(err)
			}
			if err := os.Chtimes(path, info.ModTime(), info.ModTime()); err != nil {
				t.Fatal(err)
			}
			fresh, err := preparationFingerprint(paths.Root, "scan-set.json", []string{"src/a.go"}, classifications, PrepareInput{}, "")
			if err != nil || fresh == before {
				t.Fatalf("next request reused changed source: digest=%q err=%v", fresh, err)
			}
			err = replayScanCachePacket(paths, queuePacket{PacketID: "test-replay"}, scanCacheBundle{ScopePaths: []string{"src/a.go"}, SourceDigests: sources})
			if err == nil || !strings.Contains(err.Error(), "source changed") {
				t.Fatalf("changed replay accepted: %v", err)
			}
		})
	}
}

func BenchmarkRepositorySourceDigestLarge(b *testing.B) {
	root := b.TempDir()
	data := bytes.Repeat([]byte("0123456789abcdef"), 1<<20)
	if err := os.WriteFile(filepath.Join(root, "large.go"), data, 0o644); err != nil {
		b.Fatal(err)
	}
	b.ReportAllocs()
	b.SetBytes(int64(len(data)))
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := repositorySourceDigest(root, "large.go"); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkPreparationDigestAndSelection(b *testing.B) {
	root := b.TempDir()
	data := bytes.Repeat([]byte("0123456789abcdef"), 1<<16)
	files := []string{"a.go", "b.go", "c.go", "d.go", "e.go", "f.go", "g.go", "h.go"}
	for _, path := range files {
		if err := os.WriteFile(filepath.Join(root, path), data, 0o644); err != nil {
			b.Fatal(err)
		}
	}
	classifications, err := classifyRepositoryPaths(root, files, false)
	if err != nil {
		b.Fatal(err)
	}
	paths := rt.Paths{Root: root, RuntimeDir: filepath.Join(root, ".specify", "project-cognition")}
	b.ReportAllocs()
	b.SetBytes(int64(len(data) * len(files)))
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, sources, err := preparationFingerprintWithSources(root, "scan-set.json", files, classifications, PrepareInput{}, "")
		if err != nil {
			b.Fatal(err)
		}
		selection := selectReusableScanCacheWithSources(paths, classifications, files, false, sources)
		if len(selection.CurrentSource) != len(files) {
			b.Fatal("missing source digests")
		}
	}
}
