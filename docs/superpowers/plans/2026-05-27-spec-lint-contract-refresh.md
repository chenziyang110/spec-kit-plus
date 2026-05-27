# Spec-Lint Contract Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `spec-lint` so it validates the current `sp-specify -> sp-plan` artifact contract plus the existing tiered quality checks.

**Architecture:** Keep the zero-dependency Go binary and stable CLI. Add contract checks to the existing runner, load `brainstorming/handoff-to-specify.json`, parse it with the Go standard library, and cover behavior with Go tests and current fixtures.

**Tech Stack:** Go standard library, existing `tools/spec-lint` package, Markdown text checks, JSON decoding.

---

### Task 1: Contract Test Coverage

**Files:**
- Create: `tools/spec-lint/contract_checks_test.go`
- Modify: `tools/spec-lint/testdata/good-spec/**`

- [ ] Write failing Go tests for required artifact checks, workflow-state readiness, handoff JSON readiness, source-signal disposition, must-preserve coverage, and warning-only review state.
- [ ] Run `go test ./...` in `tools/spec-lint` and verify the new tests fail because the checks do not exist yet.

### Task 2: Contract Check Implementation

**Files:**
- Modify: `tools/spec-lint/main.go`
- Modify: `tools/spec-lint/lint.go`
- Modify: `tools/spec-lint/checks.go`

- [ ] Load `brainstorming/handoff-to-specify.json` into `artifactSet`.
- [ ] Add contract check entries before the existing quality heuristic checks.
- [ ] Implement JSON parsing and tolerant object/list helpers using only the Go standard library.
- [ ] Run `go test ./...` in `tools/spec-lint` and make the tests pass.

### Task 3: Documentation and Verification

**Files:**
- Modify: `templates/spec-quality-gate.md`
- Modify: `PROJECT-HANDBOOK.md`

- [ ] Document the artifact contract gate and clarify that the old eight checks are now the quality heuristic layer.
- [ ] Run `gofmt`, `go test ./...`, `go vet ./...`, and `go build -o /dev/null .` in `tools/spec-lint`.
- [ ] Run the smallest relevant repository checks for touched docs/templates.
