package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"unicode"
	"unicode/utf8"
)

const (
	quickShadowCapability     = "quick.context-shadow"
	quickShadowCommandUsage   = "specify-runtime quick context-shadow --workspace <exact-workspace> --item Qn [--project-root <path>] [--format json]"
	quickShadowSummary        = "Read one exact Quick owner snapshot for shadow comparison only; never authorize execution or acceptance."
	quickShadowCLIOutputLimit = 128 * 1024
)

type quickShadowSelection struct {
	projectRoot string
	workspace   string
	item        string
	help        bool
}

// This parser intentionally has no filesystem, stdin, repository scan or writes.
// Only named selectors are accepted; no guessed numeric Quick ID or JSON packet.
func parseQuickShadowSelection(args []string) (quickShadowSelection, error) {
	selected := quickShadowSelection{projectRoot: "."}
	seen := map[string]bool{}
	for i := 0; i < len(args); i++ {
		key := args[i]
		if key == "-h" {
			key = "--help"
		}
		switch key {
		case "--help", "--workspace", "--item", "--project-root", "--format":
		default:
			return quickShadowSelection{}, fmt.Errorf("unknown option or positional argument; use context-shadow --help")
		}
		if seen[key] {
			return quickShadowSelection{}, fmt.Errorf("option %s was repeated", key)
		}
		seen[key] = true
		if key == "--help" {
			selected.help = true
			continue
		}
		if i+1 == len(args) || strings.HasPrefix(args[i+1], "-") {
			return quickShadowSelection{}, fmt.Errorf("option %s requires a value", key)
		}
		i++
		value := args[i]
		if !utf8.ValidString(value) || strings.TrimSpace(value) != value || value == "" ||
			strings.IndexFunc(value, unicode.IsControl) >= 0 || len(value) > 8192 {
			return quickShadowSelection{}, fmt.Errorf("option %s requires bounded, non-empty UTF-8 without control characters", key)
		}
		switch key {
		case "--workspace":
			if len(value) > 255 || value == "." || value == ".." ||
				strings.ContainsAny(value, "/\\:") {
				return quickShadowSelection{}, fmt.Errorf("--workspace must name one exact directory, not a path")
			}
			selected.workspace = value
		case "--item":
			if len(value) < 2 || len(value) > 64 || value[0] != 'Q' ||
				value[1] < '1' || value[1] > '9' {
				return quickShadowSelection{}, fmt.Errorf("--item requires Q followed by a positive decimal integer")
			}
			for _, c := range value[2:] {
				if c < '0' || c > '9' {
					return quickShadowSelection{}, fmt.Errorf("--item requires Q followed by a positive decimal integer")
				}
			}
			selected.item = value
		case "--project-root":
			selected.projectRoot = value
		case "--format":
			if value != "json" {
				return quickShadowSelection{}, fmt.Errorf("context-shadow supports --format json only")
			}
		}
	}
	if !selected.help && (selected.workspace == "" || selected.item == "") {
		return quickShadowSelection{}, fmt.Errorf("context-shadow requires both --workspace and --item")
	}
	return selected, nil
}

// Shared by command help, api show and api pack. These are limitations, not
// additional authority, approval or a replacement for the existing owner.
func quickShadowOutputContract() map[string]any {
	return map[string]any{
		"schema":                   "quick-context-shadow-v1",
		"mode":                     "shadow-only",
		"side_effect":              "read-only",
		"authorizes_execution":     false,
		"live_code_verified":       false,
		"design_approval_verified": false,
		"acceptance_verified":      false,
		"claim_ready":              false,
		"complete_owner_packet":    "retained; the projection alone is not executable",
		"max_envelope_bytes":       quickShadowCLIOutputLimit,
		"overflow":                 "blocked-without-report; never truncate the owner contract",
		"cancellation":             "inherited by Git children and checked between reads and before output; no transaction or filesystem sandbox",
		"max_git_identity_bytes":   quickShadowGitOutputLimit,
		"exit_codes": map[string]any{
			"ok": 0, "invalid_input": 2, "blocked": 10, "write_error": 1,
		},
	}
}

func describeQuickShadowCapability(capability map[string]any) {
	capability["summary"] = quickShadowSummary
	capability["usage"] = quickShadowCommandUsage
	capability["side_effect"] = "read-only"
	capability["input_contract"] = "requires one exact workspace and Qn; accepts only --workspace, --item, --project-root, --format json and --help/-h; no stdin, JSON inputs, write flags, repair, dispatch or automatic workflow continuation"
	capability["output_contract"] = quickShadowOutputContract()
}

func addQuickShadowPackContract(id string, item map[string]any) {
	if id == quickShadowCapability {
		item["output_contract"] = quickShadowOutputContract()
	}
}

func newQuickShadowCLIEnvelope(status, summary string) Envelope {
	env := NewEnvelope(status, summary)
	env.Data["capability"] = quickShadowCapability
	env.Data["mode"] = "shadow-only"
	env.Data["authorizes_execution"] = false
	env.Data["live_code_verified"] = false
	env.Data["acceptance_verified"] = false
	env.Data["claim_ready"] = false
	env.Data["output_contract"] = quickShadowOutputContract()
	env.ShowArgv = []string{"specify-runtime", "quick", "context-shadow", "--help"}
	// NextArgv deliberately stays empty on every path.
	return env
}

// reader is supplied by the command adapter, never by user JSON. Separation
// makes parser/no-read/output tests independent of any runtime state fixtures.
func quickShadowCLIEnvelope(args []string, reader func(quickShadowSelection) (any, error)) Envelope {
	var contextual func(context.Context, quickShadowSelection) (any, error)
	if reader != nil {
		contextual = func(_ context.Context, selected quickShadowSelection) (any, error) { return reader(selected) }
	}
	return quickShadowCLIEnvelopeWithContext(context.Background(), args, contextual)
}

func quickShadowCancelledEnvelope() Envelope {
	env := newQuickShadowCLIEnvelope("blocked", "Quick shadow query was cancelled; no snapshot returned")
	env.Data["error_code"] = "quick-shadow-cancelled"
	return env
}

func quickShadowCLIEnvelopeWithContext(ctx context.Context, args []string, reader func(context.Context, quickShadowSelection) (any, error)) Envelope {
	selected, err := parseQuickShadowSelection(args)
	if err != nil {
		env := newQuickShadowCLIEnvelope("usage-error", "Quick shadow arguments are invalid")
		env.Blockers = append(env.Blockers, err.Error())
		env.Data["error_code"] = "quick-shadow-input-invalid"
		env.Data["usage"] = quickShadowCommandUsage
		return env
	}
	if ctx == nil {
		return newQuickShadowCLIEnvelope("error", "Quick shadow cancellation context is missing")
	}
	if ctx.Err() != nil {
		return quickShadowCancelledEnvelope()
	}
	if selected.help {
		env := newQuickShadowCLIEnvelope("ok", quickShadowSummary)
		env.Data["usage"] = quickShadowCommandUsage
		env.Data["selection"] = "exact workspace directory plus Qn; never inferred from task history"
		return env
	}
	if reader == nil {
		env := newQuickShadowCLIEnvelope("error", "Quick shadow owner is unavailable")
		env.Data["error_code"] = "quick-shadow-owner-unavailable"
		return env
	}
	report, err := reader(ctx, selected)
	if ctx.Err() != nil {
		return quickShadowCancelledEnvelope()
	}
	if err != nil || report == nil {
		env := newQuickShadowCLIEnvelope("blocked", "Quick shadow could not read a valid owner snapshot")
		env.Data["error_code"] = "quick-shadow-owner-blocked"
		if err != nil {
			// Bounded diagnostics only; do not echo supplied JSON or all argv.
			reason := []rune(strings.ToValidUTF8(err.Error(), "\uFFFD"))
			if len(reason) > 768 {
				reason = append(reason[:768], []rune(" [diagnostic shortened]")...)
			}
			env.Blockers = append(env.Blockers, string(reason))
		}
		env.Data["recovery"] = "Inspect the existing Quick owner; this diagnostic does not repair state or authorize a retrying mutation."
		return env
	}
	env := newQuickShadowCLIEnvelope("ok", "Quick shadow snapshot read; not execution or acceptance approval")
	env.Data["report"] = report
	return env
}

// Encode with the existing runtime writer FIRST so pinned argv and all envelope
// metadata count towards the same byte ceiling. Never emit an oversized report.
func writeQuickShadowCLIEnvelope(stdout io.Writer, env Envelope, encode func(io.Writer, Envelope) int) int {
	return writeQuickShadowCLIEnvelopeWithContext(context.Background(), stdout, env, encode)
}

// A cancellation observed during buffering replaces the success response. A
// cancellation racing with an external stdout write cannot retract written bytes.
func writeQuickShadowCLIEnvelopeWithContext(ctx context.Context, stdout io.Writer, env Envelope, encode func(io.Writer, Envelope) int) int {
	if ctx == nil || encode == nil || stdout == nil {
		return 1
	}
	if ctx.Err() != nil {
		env = quickShadowCancelledEnvelope()
	}
	var buffer bytes.Buffer
	code := encode(&buffer, env)
	if code != ExitCodeForStatus(env.Status) || !json.Valid(buffer.Bytes()) {
		return 1
	}
	if ctx.Err() != nil && env.Data["error_code"] != "quick-shadow-cancelled" {
		buffer.Reset()
		env = quickShadowCancelledEnvelope()
		code = encode(&buffer, env)
		if code != 10 || !json.Valid(buffer.Bytes()) {
			return 1
		}
	}
	if buffer.Len() > quickShadowCLIOutputLimit {
		buffer.Reset()
		env = newQuickShadowCLIEnvelope("blocked", "Quick shadow envelope exceeds its bounded output limit")
		env.Data["error_code"] = "quick-shadow-output-limit"
		env.Blockers = append(env.Blockers, "No partial report was returned. Narrow the owner context without removing required obligations.")
		code = encode(&buffer, env)
		if code != 10 || buffer.Len() > quickShadowCLIOutputLimit || !json.Valid(buffer.Bytes()) {
			return 1
		}
	}
	// A cancellation during overflow encoding must not be turned into success.
	if ctx.Err() != nil && code == 0 {
		return 1
	}
	n, err := stdout.Write(buffer.Bytes())
	if err != nil || n != buffer.Len() {
		return 1
	}
	return code
}
