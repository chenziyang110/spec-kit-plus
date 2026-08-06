package main

import (
	"strings"
	"testing"
)

func TestNormalizeMarkdownSectionTarget(t *testing.T) {
	cases := map[string]string{
		"Source Design System":          "source design system",
		"## Source Design System":       "source design system",
		"# Source Design System":        "source design system",
		"  ## Source Design System  ":   "source design system",
	}
	for in, want := range cases {
		if got := normalizeMarkdownSectionTarget(in); got != want {
			t.Fatalf("normalizeMarkdownSectionTarget(%q)=%q want %q", in, got, want)
		}
	}
}

func TestReplaceMarkdownSectionAcceptsHashMarkers(t *testing.T) {
	raw := []byte("# Doc\n\n## Source Design System\n\nold\n\n## Next\n\nbody\n")
	updated, err := replaceMarkdownSection(raw, "## Source Design System", "new body")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(updated), "new body") || !strings.Contains(string(updated), "## Source Design System") {
		t.Fatalf("updated=%s", updated)
	}
	updated, err = replaceMarkdownSection(raw, "Source Design System", "again")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(updated), "again") {
		t.Fatalf("updated=%s", updated)
	}
}
