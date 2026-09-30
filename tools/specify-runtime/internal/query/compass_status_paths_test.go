package query

import (
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestDegradedStatusPathsStayRepositoryRelativeAcrossPlatforms(t *testing.T) {
	for _, candidate := range []string{
		"/outside.go", `/outside/../secret.go`, `\outside.go`,
		`\outside\..\secret.go`, "../outside.go", `..\outside.go`,
		"C:/outside.go", `C:\outside.go`, "c:outside.go",
		"//server/share/outside.go", `\\server\share\outside.go`,
		".", "..", "/", `\`,
	} {
		t.Run(candidate, func(t *testing.T) {
			lane, ok := degradedStatusPathLane(rt.Status{
				StalePaths:      []string{candidate},
				DirtyScopePaths: []string{"src/retained.go"},
			}, nil)
			if !ok || len(lane.FirstPassPaths) != 1 || lane.FirstPassPaths[0].Path != "src/retained.go" {
				t.Fatalf("candidate %q escaped repository-relative filtering: %#v", candidate, lane.FirstPassPaths)
			}
		})
	}

	for _, test := range []struct {
		input string
		want  string
	}{
		{"src/handler.go", "src/handler.go"},
		{`src\nested\handler.go`, "src/nested/handler.go"},
		{"./src/handler.go", "src/handler.go"},
		{"src/./handler.go", "src/handler.go"},
		{"src/../handler.go", "handler.go"},
	} {
		t.Run(test.input, func(t *testing.T) {
			lane, ok := degradedStatusPathLane(rt.Status{StalePaths: []string{test.input}}, nil)
			if !ok || len(lane.FirstPassPaths) != 1 || lane.FirstPassPaths[0].Path != test.want {
				t.Fatalf("repository path %q = %#v, want %q", test.input, lane.FirstPassPaths, test.want)
			}
		})
	}
}
