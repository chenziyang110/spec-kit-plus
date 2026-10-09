package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

func runPlaybook(args []string, stdout io.Writer) int {
	if len(args) == 0 || containsHelpFlag(args) {
		env := NewEnvelope("ok", "playbook commands")
		env.Data = map[string]any{"commands": []string{"find", "show", "validate", "update"}, "usage": map[string]string{
			"find":     "playbook find [--query TEXT] [--operation OPERATION] [--target TARGET] [--context-json JSON] [--limit N] [--cursor N] [--format json]",
			"show":     "playbook show --id ID [--section summary|steps|checks|evidence|all] [--revision N | --proposal-digest SHA256] [--format json]",
			"validate": "playbook validate (--id ID | --input-json DEFINITION) [--context-json JSON] [--format json]",
			"update":   "playbook update --input-json UPDATE [--format json]",
		}, "schemas": []string{"playbook-definition-input", "playbook-find-input", "playbook-show-input", "playbook-validate-input", "playbook-update-input"}, "execution_boundary": "native_agent_tools_only; read commands do not execute or establish a new success"}
		return writeEnvelope(stdout, env)
	}
	root, err := filepath.Abs(optionValue(args, "--project-root", "."))
	if err != nil {
		env := NewEnvelope("blocked", "playbook project root unavailable")
		env.Blockers = append(env.Blockers, "playbook_project_root_unavailable")
		return writeEnvelope(stdout, env)
	}
	var data map[string]any
	switch args[0] {
	case "find":
		err = validatePlaybookOptions(args[1:], "--query", "--operation", "--target", "--context-json", "--limit", "--cursor")
		if err == nil {
			data, err = findPlaybooks(root, args[1:])
		}
	case "show":
		err = validatePlaybookOptions(args[1:], "--id", "--section", "--revision", "--proposal-digest")
		if err == nil {
			data, err = showPlaybook(root, optionValue(args, "--id", ""), optionValue(args, "--section", "summary"), optionValue(args, "--revision", ""), optionValue(args, "--proposal-digest", ""))
		}
	case "update":
		err = validatePlaybookOptions(args[1:], "--input-json")
		if err == nil {
			var request PlaybookUpdateRequest
			err = doReadInput(optionValue(args, "--input-json", ""), &request)
			if err == nil {
				data, err = updatePlaybook(root, request)
			}
		}
	case "validate":
		err = validatePlaybookOptions(args[1:], "--id", "--input-json", "--context-json")
		if err == nil {
			data, err = validatePlaybookInput(root, args[1:])
		}
	default:
		err = fmt.Errorf("playbook_subcommand_unknown")
	}
	if err != nil {
		env := NewEnvelope("blocked", "playbook command failed")
		policy, _, _ := (learningService{projectRoot: root}).loadLearningPolicy(false)
		env.Blockers = append(env.Blockers, redactLearningTextWithPolicy(err.Error(), policy).text)
		env.Data["error_code"] = "playbook-runtime-error"
		env.Data["claim_ready"] = false
		return writeEnvelope(stdout, env)
	}
	env := NewEnvelope("ok", "playbook "+args[0]+" completed")
	env.Data = data
	return writeEnvelope(stdout, env)
}

func validatePlaybookOptions(args []string, allowed ...string) error {
	known := map[string]bool{"--project-root": true, "--format": true}
	for _, option := range allowed {
		known[option] = true
	}
	seen := map[string]bool{}
	for i := 0; i < len(args); i += 2 {
		if !known[args[i]] || seen[args[i]] || i+1 >= len(args) {
			return fmt.Errorf("playbook_option_unknown_duplicate_or_missing_value")
		}
		seen[args[i]] = true
		if args[i] == "--format" && args[i+1] != "json" {
			return fmt.Errorf("playbook_format_must_be_json")
		}
	}
	return nil
}

func findPlaybooks(root string, args []string) (map[string]any, error) {
	context, err := playbookReadContext(optionValue(args, "--context-json", ""))
	if err != nil {
		return nil, err
	}
	policy, policyWarnings, _ := (learningService{projectRoot: root}).loadLearningPolicy(false)
	query := strings.TrimSpace(redactLearningTextWithPolicy(optionValue(args, "--query", ""), policy).text)
	operation := redactLearningTextWithPolicy(optionValue(args, "--operation", ""), policy).text
	target := redactLearningTextWithPolicy(optionValue(args, "--target", ""), policy).text
	for key, value := range context {
		context[key] = redactLearningTextWithPolicy(value, policy).text
	}
	if len(query) > 2048 || len(target) > 128 {
		return nil, fmt.Errorf("playbook_query_too_long")
	}
	limit, err := strconv.Atoi(optionValue(args, "--limit", "5"))
	if err != nil || limit < 1 || limit > 20 {
		return nil, fmt.Errorf("playbook_limit_must_be_between_1_and_20")
	}
	cursor, err := strconv.Atoi(optionValue(args, "--cursor", "0"))
	if err != nil || cursor < 0 {
		return nil, fmt.Errorf("playbook_cursor_invalid")
	}
	documents, warnings, err := readPlaybookDocuments(root)
	if err != nil {
		return nil, err
	}
	proposals, proposalWarnings, err := readPlaybookUnpublishedProposals(root)
	if err != nil {
		return nil, err
	}
	for _, proposal := range proposals {
		documents = append(documents, PlaybookDocument{ID: proposal.ID, ContentDigest: proposal.DefinitionDigest, Status: "proposed", Definition: proposal.Definition})
	}
	warnings = append(warnings, proposalWarnings...)
	warnings = uniqueSortedTrimmed(append(warnings, policyWarnings...))
	type ranked struct {
		document PlaybookDocument
		score    int
		source   string
	}
	matches := []ranked{}
	excludedContext := 0
	for _, document := range documents {
		definition := document.Definition
		if operation != "" && definition.Operation != operation {
			continue
		}
		if target != "" && !strings.EqualFold(definition.Target, target) {
			continue
		}
		score := playbookMatchScore(definition, query)
		if query != "" && score == 0 {
			continue
		}
		if len(playbookCompatibility(definition, context)) > 0 {
			excludedContext++
			continue
		}
		source := "unverified"
		if document.Status == "verified" {
			source = playbookSourceStatus(root, document)
		}
		if source == "matched_prior_validation" {
			score++
		}
		matches = append(matches, ranked{document, score, source})
	}
	sort.SliceStable(matches, func(i, j int) bool {
		if matches[i].score != matches[j].score {
			return matches[i].score > matches[j].score
		}
		return matches[i].document.ID < matches[j].document.ID
	})
	total := len(matches)
	end := cursor + limit
	if end > total {
		end = total
	}
	items := []map[string]any{}
	if cursor < total {
		for _, match := range matches[cursor:end] {
			card := playbookCard(match.document, match.source)
			if match.document.Status == "proposed" {
				card["proposal_digest"] = match.document.ContentDigest
				card["show_argv"] = playbookShowArgv(match.document.ID, "summary", 0, match.document.ContentDigest)
			}
			card["match_reason"] = "goal_alias_or_canonical_operation"
			items = append(items, card)
		}
	}
	var nextCursor any
	var nextArgv any
	if end < total && cursor < total {
		nextCursor = end
		argv := []string{"specify-runtime", "playbook", "find"}
		for _, item := range []struct{ name, value string }{{"--query", query}, {"--operation", operation}, {"--target", target}} {
			if item.value != "" {
				argv = append(argv, item.name, item.value)
			}
		}
		if optionValue(args, "--context-json", "") != "" {
			encoded, _ := json.Marshal(context)
			argv = append(argv, "--context-json", string(encoded))
		}
		argv = append(argv, "--cursor", strconv.Itoa(end), "--limit", strconv.Itoa(limit), "--format", "json")
		nextArgv = argv
	}
	return map[string]any{"schema_version": playbookSchemaVersion, "read_only": true, "items": items, "pagination": map[string]any{"cursor": cursor, "limit": limit, "returned": len(items), "total": total, "next_cursor": nextCursor, "next_argv": nextArgv}, "excluded_by_applicability": excludedContext, "warnings": warnings, "live_verification_required": true, "claim_ready": false}, nil
}

func playbookMatchScore(definition PlaybookDefinition, query string) int {
	query = strings.ToLower(strings.TrimSpace(query))
	if query == "" {
		return 1
	}
	values := append([]string{definition.Title, definition.Goal, definition.Operation, definition.Target, definition.Owner, definition.Variant}, definition.Aliases...)
	score := 0
	for _, value := range values {
		value = strings.ToLower(value)
		if value == query {
			score += 10
		} else if strings.Contains(value, query) || (len([]rune(value)) > 1 && strings.Contains(query, value)) {
			score += 5
		}
	}
	terms := strings.FieldsFunc(query, func(character rune) bool { return !unicode.IsLetter(character) && !unicode.IsDigit(character) })
	joined := strings.ToLower(strings.Join(values, " "))
	for _, term := range terms {
		if len([]rune(term)) > 1 && strings.Contains(joined, term) {
			score++
		}
	}
	return score
}

func playbookCard(document PlaybookDocument, sourceStatus string) map[string]any {
	return map[string]any{"id": document.ID, "revision": document.Revision, "content_digest": document.ContentDigest, "title": document.Definition.Title, "goal": document.Definition.Goal, "operation": document.Definition.Operation, "target": document.Definition.Target, "owner": document.Definition.Owner, "variant": document.Definition.Variant, "status": document.Status, "source_status": sourceStatus, "requires_revalidation": sourceStatus != "matched_prior_validation", "step_count": len(document.Definition.Steps), "check_count": len(document.Definition.Checks), "show_argv": playbookShowArgv(document.ID, "summary", document.Revision, "")}
}

func playbookShowArgv(id, section string, revision int, proposalDigest string) []string {
	argv := []string{"specify-runtime", "playbook", "show", "--id", id, "--section", section}
	if revision > 0 {
		argv = append(argv, "--revision", strconv.Itoa(revision))
	}
	if proposalDigest != "" {
		argv = append(argv, "--proposal-digest", proposalDigest)
	}
	return append(argv, "--format", "json")
}

func showPlaybook(root, id, section, rawRevision, proposalDigest string) (map[string]any, error) {
	if section != "summary" && section != "steps" && section != "checks" && section != "evidence" && section != "all" {
		return nil, fmt.Errorf("playbook_section_invalid")
	}
	if rawRevision != "" && proposalDigest != "" {
		return nil, fmt.Errorf("playbook_revision_and_proposal_are_exclusive")
	}
	revision := 0
	if rawRevision != "" {
		var err error
		revision, err = strconv.Atoi(rawRevision)
		if err != nil || revision < 1 || revision > 999999 {
			return nil, fmt.Errorf("playbook_revision_invalid")
		}
	}
	var document PlaybookDocument
	var proposal *PlaybookProposal
	if proposalDigest != "" {
		stored, err := readPlaybookProposal(root, id, proposalDigest)
		if err != nil {
			return nil, err
		}
		proposal = &stored
		document = PlaybookDocument{ID: id, Status: "proposed", ContentDigest: proposalDigest, Definition: proposal.Definition}
	} else if revision > 0 {
		var err error
		document, err = loadPlaybookRevision(root, id, revision)
		if err != nil {
			return nil, err
		}
	} else {
		var err error
		document, err = loadPlaybookDocument(root, id)
		if err != nil {
			return nil, err
		}
	}
	sourceStatus := "unverified"
	if proposal == nil {
		sourceStatus = playbookSourceStatus(root, document)
		revision = document.Revision
	}
	data := map[string]any{"schema_version": playbookSchemaVersion, "read_only": true, "id": id, "revision": document.Revision, "content_digest": document.ContentDigest, "status": document.Status, "section": section, "live_verification_required": true, "claim_ready": false}
	switch section {
	case "summary":
		card := playbookCard(document, sourceStatus)
		card["show_argv"] = playbookShowArgv(id, "summary", revision, proposalDigest)
		data["card"] = card
		data["applicability"] = document.Definition.Applicability
		data["source_files"] = document.Definition.SourceFiles
		expand := map[string][]string{}
		for _, next := range []string{"steps", "checks", "evidence", "all"} {
			expand[next] = playbookShowArgv(id, next, revision, proposalDigest)
		}
		data["expand_argv"] = expand
		if proposal == nil {
			candidate, warnings := readPlaybookLatestProposal(root, id, document.ContentDigest)
			if candidate.ID != "" {
				data["pending_proposal"] = map[string]any{"status": "proposed", "proposal_digest": candidate.DefinitionDigest, "base_digest": candidate.BaseDigest, "verification_required": true, "show_argv": playbookShowArgv(id, "summary", 0, candidate.DefinitionDigest)}
			}
			if len(warnings) > 0 {
				data["warnings"] = warnings
			}
		}
	case "steps":
		data["steps"] = document.Definition.Steps
	case "checks":
		data["checks"] = document.Definition.Checks
	case "evidence":
		if proposal != nil {
			data["evidence_state"] = "unverified_proposal"
			data["base_digest"] = proposal.BaseDigest
		} else {
			data["verification"] = document.Verification
			data["source_fingerprint"] = document.SourceFingerprint
			data["usage"] = playbookUsageSummary(root, document)
		}
	case "all":
		data["definition"] = document.Definition
		data["source_status"] = sourceStatus
	}
	if proposal != nil {
		data["proposal_digest"] = proposalDigest
		data["base_digest"] = proposal.BaseDigest
	}
	return data, nil
}

func playbookUsageSummary(root string, document PlaybookDocument) map[string]any {
	directory, err := playbookStorePath(root, document.ID, "usage")
	if err != nil {
		return map[string]any{"verified_sessions": 0}
	}
	entries, err := os.ReadDir(directory)
	if err != nil {
		return map[string]any{"verified_sessions": 0}
	}
	count := 0
	latest := ""
	for _, entry := range entries {
		if !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		usage, found, err := readPlaybookUsage(root, document.ID, strings.TrimSuffix(entry.Name(), ".json"))
		if err == nil && found && usage.DefinitionDigest == document.ContentDigest {
			count++
			if usage.Verification.VerifiedAt > latest {
				latest = usage.Verification.VerifiedAt
			}
		}
	}
	return map[string]any{"verified_sessions": count, "last_verified_at": latest, "provenance": "agent_tool_observation", "execution_success_reused": false}
}

func validatePlaybookInput(root string, args []string) (map[string]any, error) {
	id := optionValue(args, "--id", "")
	raw := optionValue(args, "--input-json", "")
	if (id == "") == (raw == "") {
		return nil, fmt.Errorf("playbook_validate_requires_exactly_one_id_or_definition")
	}
	var definition PlaybookDefinition
	if id != "" {
		document, err := loadPlaybookDocument(root, id)
		if err != nil {
			return nil, err
		}
		definition = document.Definition
	} else {
		if err := doReadInput(raw, &definition); err != nil {
			return nil, err
		}
	}
	if err := validatePlaybookDefinition(root, definition); err != nil {
		return nil, err
	}
	context, err := playbookReadContext(optionValue(args, "--context-json", ""))
	if err != nil {
		return nil, err
	}
	reasons := playbookCompatibility(definition, context)
	sources, sourceErr := playbookSourceFingerprint(root, definition)
	if sourceErr != nil {
		reasons = append(reasons, "source_files_unavailable")
	}
	digest, err := playbookDefinitionDigest(definition)
	if err != nil {
		return nil, err
	}
	return map[string]any{"schema_version": playbookSchemaVersion, "read_only": true, "id": playbookID(definition), "definition_digest": digest, "schema_valid": true, "applicable": len(reasons) == 0, "compatibility_reasons": reasons, "source_fingerprint": sources, "validation_level": "definition_and_live_source_checks", "execution_verified": false, "claim_ready": false}, nil
}
