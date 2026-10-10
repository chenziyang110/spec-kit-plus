package runtime

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	goruntime "runtime"
	"testing"
	"time"
)

func TestCacheFileIdenticalBytesDoNotPublish(t *testing.T) {
	path := filepath.Join(t.TempDir(), "cache.json")
	data := []byte(`{"paths":["src/检索.go"]}`)
	if err := WriteCacheFile(path, data); err != nil {
		t.Fatal(err)
	}
	stamp := time.Unix(946684800, 0)
	if err := os.Chtimes(path, stamp, stamp); err != nil {
		t.Fatal(err)
	}
	before, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	err = writeCacheFile(path, append([]byte{}, data...), func(string, string) error {
		t.Fatal("identical bytes invoked file replacement")
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	after, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	if !before.ModTime().Equal(after.ModTime()) || !os.SameFile(before, after) {
		t.Fatal("unchanged cache churned its file identity or modification time")
	}
	entries, err := os.ReadDir(filepath.Dir(path))
	if err != nil || len(entries) != 1 {
		t.Fatalf("temporary files leaked: %v / %v", entries, err)
	}
}

func TestCacheFileFailurePreservesOldBytesAndCleansTemp(t *testing.T) {
	path := filepath.Join(t.TempDir(), "cache.json")
	before, after := []byte(`{"version":1}`), []byte(`{"version":2}`)
	if err := WriteCacheFile(path, before); err != nil {
		t.Fatal(err)
	}
	sentinel := errors.New("replacement unavailable")
	calls := 0
	err := writeCacheFile(path, after, func(tmp, target string) error {
		calls++
		if tmp == target || filepath.Dir(tmp) != filepath.Dir(target) {
			t.Fatal("not a sibling temporary file")
		}
		got, err := os.ReadFile(tmp)
		if err != nil || !bytes.Equal(got, after) {
			t.Fatalf("temporary file incomplete: %q, %v", got, err)
		}
		got, err = os.ReadFile(target)
		if err != nil || !bytes.Equal(got, before) {
			t.Fatalf("target modified before publication: %q, %v", got, err)
		}
		return sentinel
	})
	if !errors.Is(err, sentinel) || calls != 1 {
		t.Fatalf("calls=%d err=%v", calls, err)
	}
	got, err := os.ReadFile(path)
	if err != nil || !bytes.Equal(got, before) {
		t.Fatalf("failed replacement damaged previous bytes: %q, %v", got, err)
	}
	entries, err := os.ReadDir(filepath.Dir(path))
	if err != nil || len(entries) != 1 {
		t.Fatalf("failure leaked temp files: %v, %v", entries, err)
	}
	if err := WriteCacheFile(path, after); err != nil {
		t.Fatal(err)
	}
	got, err = os.ReadFile(path)
	if err != nil || !bytes.Equal(got, after) {
		t.Fatalf("recovery failed: %q, %v", got, err)
	}
}

func TestCacheFileCompareEmptyAndChunkBoundaries(t *testing.T) {
	for _, size := range []int{0, 1, 32767, 32768, 32769, 3*32768 + 7} {
		path := filepath.Join(t.TempDir(), "data")
		data := bytes.Repeat([]byte("x"), size)
		if err := WriteCacheFile(path, data); err != nil {
			t.Fatal(err)
		}
		same, err := cacheFileMatches(path, data)
		if err != nil || !same {
			t.Fatalf("size=%d same=%v err=%v", size, same, err)
		}
		changed := append(append([]byte{}, data...), 'y')
		same, err = cacheFileMatches(path, changed)
		if err != nil || same {
			t.Fatalf("different length matched: size=%d", size)
		}
		if size > 0 {
			changed = append([]byte{}, data...)
			changed[size-1] = 'z'
			same, err = cacheFileMatches(path, changed)
			if err != nil || same {
				t.Fatalf("last byte mismatch missed: size=%d", size)
			}
			if err := WriteCacheFile(path, changed); err != nil {
				t.Fatal(err)
			}
			got, err := os.ReadFile(path)
			if err != nil || !bytes.Equal(got, changed) {
				t.Fatalf("same-size update reused stale bytes")
			}
		}
	}
}

func TestCacheFileRejectsNonRegularTargets(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "directory")
	if err := os.Mkdir(dir, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := WriteCacheFile(dir, []byte("data")); err == nil {
		t.Fatal("directory accepted")
	}
	actual := filepath.Join(root, "actual")
	if err := os.WriteFile(actual, []byte("untouched"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "link")
	if err := os.Symlink(actual, link); err != nil {
		if goruntime.GOOS == "windows" {
			t.Skipf("native symlink permission unavailable: %v", err)
		}
		t.Fatal(err)
	}
	if err := WriteCacheFile(link, []byte("untouched")); err == nil {
		t.Fatal("symlink accepted by same-byte fast path")
	}
	if err := WriteCacheFile(link, []byte("changed")); err == nil {
		t.Fatal("symlink accepted by replacement path")
	}
	got, err := os.ReadFile(actual)
	if err != nil || string(got) != "untouched" {
		t.Fatal("symlink target changed")
	}
}

func TestCacheFileMissingParentDoesNotCreateState(t *testing.T) {
	root := t.TempDir()
	if err := WriteCacheFile(filepath.Join(root, "missing", "cache"), []byte("data")); err == nil {
		t.Fatal("missing parent accepted")
	}
	entries, err := os.ReadDir(root)
	if err != nil || len(entries) != 0 {
		t.Fatalf("unexpected files: %v %v", entries, err)
	}
}

func TestCacheFilePreservesPrivatePermissionBits(t *testing.T) {
	if goruntime.GOOS == "windows" {
		t.Skip("POSIX permission-bit assertion; Windows has distinct ACL semantics")
	}
	path := filepath.Join(t.TempDir(), "cache")
	if err := WriteCacheFile(path, []byte("first")); err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(path)
	if err != nil || info.Mode().Perm() != 0o600 {
		t.Fatalf("new cache not private: %v %v", info, err)
	}
	if err := os.Chmod(path, 0o640); err != nil {
		t.Fatal(err)
	}
	if err := WriteCacheFile(path, []byte("second")); err != nil {
		t.Fatal(err)
	}
	info, err = os.Stat(path)
	if err != nil || info.Mode().Perm() != 0o640 {
		t.Fatalf("existing permission bits lost: %v %v", info, err)
	}
}
