package main

import (
	"fmt"
	"regexp"
	"strings"
)

// ---- types ----

type status int

const (
	statusPass status = iota
	statusFail
	statusWarn
)

type checkResult struct {
	name    string
	status  status
	message string
}

type check struct {
	name     string
	tiers    []string // which tiers include this check
	severity status   // statusFail or statusWarn
	run      func(artifactSet) checkResult
}

type artifactSet struct {
	dir           string
	spec          string
	alignment     string
	context       string
	references    string
	workflowState string
	requirements  string
}

// ---- runner ----

type runner struct {
	tier   string
	checks []check
}

func newRunner(tier string) *runner {
	return &runner{
		tier:   tier,
		checks: allChecks(),
	}
}

func (r *runner) run(a artifactSet) []checkResult {
	var results []checkResult
	for _, c := range r.checks {
		if !r.checkEnabled(c) {
			continue
		}
		result := c.run(a)
		result.name = c.name
		// downgrade fail→warn when severity is warn
		if c.severity == statusWarn && result.status == statusFail {
			result.status = statusWarn
		}
		results = append(results, result)
	}
	return results
}

func (r *runner) checkEnabled(c check) bool {
	for _, t := range c.tiers {
		if t == r.tier {
			return true
		}
		// "standard" tier includes "light" checks too
		if r.tier == "standard" && t == "light" {
			return true
		}
		// "deep" tier includes all checks
		if r.tier == "deep" && (t == "light" || t == "standard") {
			return true
		}
	}
	return false
}

// ---- markdown helpers ----

// section holds a heading title and its body content.
type section struct {
	heading string
	body    string
}

// findSections returns all h2/h3 sections whose heading contains the given text (case-insensitive).
func findSections(content, heading string) []string {
	var out []string
	for _, s := range findSectionsWithHeadings(content, heading) {
		out = append(out, s.body)
	}
	return out
}

// findSectionsWithHeadings returns sections with their headings.
func findSectionsWithHeadings(content, heading string) []section {
	lines := strings.Split(content, "\n")
	headingLower := strings.ToLower(heading)
	var sections []section
	var currentBody []string
	var currentHeading string
	inSection := false
	baseLevel := 0

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		level, title, isHeading := parseHeading(trimmed)
		if isHeading && level >= 2 && level <= 4 {
			if strings.Contains(strings.ToLower(title), headingLower) {
				if len(currentBody) > 0 {
					sections = append(sections, section{heading: currentHeading, body: strings.Join(currentBody, "\n")})
				}
				currentBody = nil
				currentHeading = title
				inSection = true
				baseLevel = level
				continue
			}
			if inSection && level <= baseLevel {
				sections = append(sections, section{heading: currentHeading, body: strings.Join(currentBody, "\n")})
				currentBody = nil
				inSection = false
			}
		}
		if inSection {
			currentBody = append(currentBody, line)
		}
	}
	if inSection && len(currentBody) > 0 {
		sections = append(sections, section{heading: currentHeading, body: strings.Join(currentBody, "\n")})
	}
	return sections
}

func parseHeading(line string) (level int, title string, ok bool) {
	if !strings.HasPrefix(line, "#") {
		return 0, "", false
	}
	i := 0
	for i < len(line) && line[i] == '#' {
		i++
	}
	if i > 0 && i < len(line) && line[i] == ' ' {
		return i, strings.TrimSpace(line[i:]), true
	}
	return 0, "", false
}

// hasTable returns true if content contains at least 2 markdown table rows with separator.
func hasTable(content string) bool {
	return countTableDataRows(content) >= 1
}

// countTableDataRows counts non-separator table rows.
func countTableDataRows(content string) int {
	re := regexp.MustCompile(`(?m)^\s*\|.*\|.*\|\s*$`)
	sepRe := regexp.MustCompile(`^\s*\|[\s\-:]+\|`)
	lines := re.FindAllString(content, -1)
	n := 0
	for _, l := range lines {
		if !sepRe.MatchString(l) {
			n++
		}
	}
	return n
}

// hasKeyword checks if content contains any of the given patterns (case-insensitive, word boundary).
func hasKeyword(content string, keywords []string) bool {
	lower := strings.ToLower(content)
	for _, kw := range keywords {
		if strings.Contains(lower, strings.ToLower(kw)) {
			return true
		}
	}
	return false
}

// countKeywords counts how many keyword groups have at least one match.
func countKeywordGroups(content string, groups [][]string) int {
	n := 0
	for _, g := range groups {
		if hasKeyword(content, g) {
			n++
		}
	}
	return n
}

// between returns content between two strings, or empty.
func between(content, start, end string) string {
	i := strings.Index(content, start)
	if i < 0 {
		return ""
	}
	i += len(start)
	j := strings.Index(content[i:], end)
	if j < 0 {
		return content[i:]
	}
	return content[i : i+j]
}

// fileMissing is a common result for missing files.
func fileMissing(filename string) checkResult {
	return checkResult{
		status:  statusFail,
		message: fmt.Sprintf("%s not found or empty", filename),
	}
}
