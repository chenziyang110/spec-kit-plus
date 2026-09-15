package main

import (
	"reflect"
	"strings"
	"testing"
)

func TestQuickScopeRejectsUnauthorizedResults(t *testing.T) {
	tests := []struct {
		name         string
		files, scope []string
	}{
		{"nil scope is no-write", []string{"src/main.go"}, nil},
		{"empty scope is no-write", []string{"src/main.go"}, []string{}},
		{"blank result is not evidence", []string{" "}, []string{"src"}},
		{"empty result entry", []string{""}, nil},
		{"control character", []string{"src/main.go\n"}, []string{"src"}},
		{"NUL", []string{"src/main.go\x00"}, []string{"src"}},
		{"invalid UTF-8", []string{"src/\xff.go"}, []string{"src"}},
		{"parent traversal", []string{"src/../outside.go"}, []string{"src"}},
		{"nested parent traversal", []string{"src/nested/../../outside.go"}, []string{"src/**"}},
		{"Windows traversal", []string{`src\..\outside.go`}, []string{`src\**`}},
		{"mixed traversal", []string{`src/..\outside.go`}, []string{"src"}},
		{"POSIX absolute", []string{"/src/main.go"}, []string{"/src"}},
		{"drive absolute", []string{`C:\src\main.go`}, []string{`C:\src`}},
		{"drive relative", []string{"C:src/main.go"}, []string{"C:src"}},
		{"UNC", []string{`\\server\src\main.go`}, []string{`\\server\src`}},
		{"device path", []string{`\\?\C:\src\main.go`}, []string{`\\?\C:\src`}},
		{"alternate stream", []string{"src/main.go:payload"}, []string{"src"}},
		{"sibling prefix", []string{"src-other/main.go"}, []string{"src"}},
		{"ancestor is not owned", []string{"src"}, []string{"src/nested"}},
		{"filename suffix", []string{"src/main.go.bak"}, []string{"src/main.go"}},
		{"changed-file wildcard", []string{"src/*.go"}, []string{"src"}},
		{"unbounded scope", []string{"src/main.go"}, []string{"**"}},
		{"project root scope", []string{"src/main.go"}, []string{"."}},
		{"project root result", []string{"."}, []string{"src"}},
		{"absolute wildcard scope", []string{"src/main.go"}, []string{"/**"}},
		{"blank scope", []string{"src/main.go"}, []string{" "}},
		{"traversing scope", []string{"outside/main.go"}, []string{"src/../outside"}},
		{"interior glob scope", []string{"src/a/main.go"}, []string{"src/**/main.go"}},
		{"malformed sibling scope", []string{"src/main.go"}, []string{"src", "../outside"}},
		{"bad scope with no changes", nil, []string{"../outside"}},
		{"mixed valid and invalid results", []string{"src/main.go", "outside.go"}, []string{"src"}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if err := validateQuickChangedFilesInScope(test.files, test.scope); err == nil {
				t.Fatalf("accepted unauthorized or malformed result: files=%q scope=%q", test.files, test.scope)
			}
			for _, file := range test.files {
				if len(test.files) == 1 && quickPathInWriteScope(file, test.scope) {
					t.Fatal("membership helper bypassed result validation")
				}
			}
		})
	}
}

func TestQuickScopePreservesValidResults(t *testing.T) {
	tests := []struct {
		name         string
		files, scope []string
	}{
		{"no-write no changes", nil, nil},
		{"empty arrays", []string{}, []string{}},
		{"no changes in declared scope", nil, []string{"src"}},
		{"exact file", []string{"src/main.go"}, []string{"src/main.go"}},
		{"directory", []string{"src/main.go", "src/nested/check.go"}, []string{"src/"}},
		{"bare bounded directory", []string{"src/nested/check.go"}, []string{"src"}},
		{"recursive suffix", []string{"src/nested/check.go"}, []string{"src/**"}},
		{"legacy suffix", []string{"src/nested/check.go"}, []string{"src/*"}},
		{"relative dots", []string{"./src/./main.go"}, []string{"./src"}},
		{"duplicate separators", []string{"src//nested/main.go"}, []string{"src/nested"}},
		{"Windows separators", []string{`src\nested\main.go`}, []string{`src\**`}},
		{"multiple scopes", []string{"src/main.go", "tests/check_test.go"}, []string{"src", "tests"}},
		{"Unicode and spaces", []string{"src/子 目录/文件.go"}, []string{"src/子 目录"}},
		{"literal bracket routes", []string{"src/app/[id]/page.tsx"}, []string{"src/app/[id]"}},
		{"dotfiles", []string{".github/workflows/test.yml"}, []string{".github/workflows"}},
		{"dots inside names", []string{"src/a..b/main.go"}, []string{"src/a..b"}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			filesBefore := append([]string(nil), test.files...)
			scopeBefore := append([]string(nil), test.scope...)
			if err := validateQuickChangedFilesInScope(test.files, test.scope); err != nil {
				t.Fatalf("rejected valid result: %v", err)
			}
			if !reflect.DeepEqual(filesBefore, append([]string(nil), test.files...)) ||
				!reflect.DeepEqual(scopeBefore, append([]string(nil), test.scope...)) {
				t.Fatal("validation mutated its input")
			}
			for _, file := range test.files {
				if !quickPathInWriteScope(file, test.scope) {
					t.Fatal("membership helper rejected valid result")
				}
			}
		})
	}
}

func TestQuickScopeDiagnosticIsBoundedAndEscaped(t *testing.T) {
	err := validateQuickChangedFilesInScope([]string{"src/file\nPRIVATE"}, []string{"src"})
	if err == nil || strings.Contains(err.Error(), "PRIVATE") || strings.Contains(err.Error(), "\n") {
		t.Fatalf("unsafe malformed-path diagnostic: %v", err)
	}
}

func FuzzQuickScopeNeverAcceptsTraversal(f *testing.F) {
	for _, seed := range []string{"main.go", "a/b", "[id]/page.tsx", "子目录/x", ""} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, tail string) {
		for _, file := range []string{"src/../" + tail, `src\..\` + tail, "/src/" + tail, "C:src/" + tail} {
			if validateQuickChangedFilesInScope([]string{file}, []string{"src", "src/**"}) == nil ||
				quickPathInWriteScope(file, []string{"src"}) {
				t.Fatal("accepted forbidden path")
			}
		}
		if validateQuickChangedFilesInScope([]string{tail}, nil) == nil {
			t.Fatal("no-write scope accepted a result entry")
		}
	})
}
