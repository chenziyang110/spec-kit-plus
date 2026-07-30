package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

const evidenceSchemaVersion = "spec-kit-evidence-v1"

var evidenceHexPattern = regexp.MustCompile(`^[0-9a-f]{64}$`)

type EvidenceRecord struct {
	SchemaVersion      string `json:"schema_version"`
	EvidenceID         string `json:"evidence_id"`
	Status             string `json:"status"`
	SHA256             string `json:"sha256"`
	Size               int64  `json:"size"`
	MIME               string `json:"mime"`
	Scope              string `json:"scope"`
	Source             string `json:"source"`
	Provenance         string `json:"provenance"`
	TaskID             string `json:"task_id,omitempty"`
	ScenarioID         string `json:"scenario_id,omitempty"`
	ObjectRef          string `json:"object_ref,omitempty"`
	RecordRef          string `json:"record_ref"`
	ExternalSourcePath string `json:"external_source_path,omitempty"`
	CreatedAt          string `json:"created_at"`
}

type evidenceService struct {
	projectRoot string
}

func runEvidence(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEvidenceEnvelope(stdout, NewEnvelope("usage-error", "missing evidence subcommand"))
	}
	projectRoot := evidenceOptionValue(args, "--project-root", ".")
	service := evidenceService{projectRoot: projectRoot}
	switch args[0] {
	case "allocate":
		env := service.allocate(evidenceCommonInput{
			Scope:      evidenceOptionValue(args, "--scope", ""),
			Source:     evidenceOptionValue(args, "--source", ""),
			Provenance: evidenceOptionValue(args, "--provenance", ""),
			TaskID:     evidenceOptionValue(args, "--task-id", ""),
			ScenarioID: evidenceOptionValue(args, "--scenario-id", ""),
		})
		return writeEvidenceEnvelope(stdout, env)
	case "import":
		env := service.importFile(
			evidenceOptionValue(args, "--file", ""),
			evidenceCommonInput{
				Scope:      evidenceOptionValue(args, "--scope", ""),
				Source:     evidenceOptionValue(args, "--source", ""),
				Provenance: evidenceOptionValue(args, "--provenance", ""),
				TaskID:     evidenceOptionValue(args, "--task-id", ""),
				ScenarioID: evidenceOptionValue(args, "--scenario-id", ""),
				MIME:       evidenceOptionValue(args, "--mime", ""),
			},
		)
		return writeEvidenceEnvelope(stdout, env)
	case "register":
		objectRef := evidenceOptionValue(args, "--object", "")
		content := evidenceOptionValue(args, "--content", "")
		input := evidenceCommonInput{
			Scope:      evidenceOptionValue(args, "--scope", ""),
			Source:     evidenceOptionValue(args, "--source", ""),
			Provenance: evidenceOptionValue(args, "--provenance", ""),
			TaskID:     evidenceOptionValue(args, "--task-id", ""),
			ScenarioID: evidenceOptionValue(args, "--scenario-id", ""),
			MIME:       evidenceOptionValue(args, "--mime", ""),
		}
		var env Envelope
		switch {
		case objectRef != "" && content != "":
			env = evidenceUsageError("evidence register accepts exactly one of --object or --content")
		case content != "":
			env = service.registerContent(content, input)
		default:
			env = service.registerObject(objectRef, input)
		}
		return writeEvidenceEnvelope(stdout, env)
	case "visual-compare":
		input, err := readAgentJSONObject(args, projectRoot, "evidence visual-compare")
		if err != nil {
			return writeEvidenceEnvelope(stdout, evidenceUsageError(err.Error()))
		}
		return writeEvidenceEnvelope(stdout, service.visualCompare(args, input))
	case "show":
		env := service.show(evidenceOptionValue(args, "--record", ""), evidenceOptionValue(args, "--view", "summary"))
		return writeEvidenceEnvelope(stdout, env)
	case "verify":
		env := service.verify(evidenceOptionValue(args, "--record", ""))
		return writeEvidenceEnvelope(stdout, env)
	default:
		return writeEvidenceEnvelope(stdout, NewEnvelope("usage-error", fmt.Sprintf("unknown evidence subcommand %q", args[0])))
	}
}

type evidenceCommonInput struct {
	Scope      string
	Source     string
	Provenance string
	TaskID     string
	ScenarioID string
	MIME       string
}

func (s evidenceService) allocate(input evidenceCommonInput) Envelope {
	if err := validateEvidenceScope(input.Scope); err != nil {
		return evidenceUsageError(err.Error())
	}
	record := s.newRecord(input)
	record.Status = "allocated"
	env, err := s.persistRecord(record)
	if err != nil {
		return evidenceBlockedError("allocate evidence record failed", err)
	}
	env.Summary = "evidence allocated"
	return env
}

func (s evidenceService) importFile(path string, input evidenceCommonInput) Envelope {
	if strings.TrimSpace(path) == "" {
		return evidenceUsageError("evidence import requires --file")
	}
	sourcePath, err := filepath.Abs(path)
	if err != nil {
		return evidenceUsageError("evidence import file path is invalid")
	}
	info, err := os.Stat(sourcePath)
	if err != nil {
		return evidenceBlockedError("evidence import file is unavailable", err)
	}
	if !info.Mode().IsRegular() {
		return evidenceUsageError("evidence import requires a regular file")
	}
	raw, err := os.ReadFile(sourcePath)
	if err != nil {
		return evidenceBlockedError("evidence import file is unavailable", err)
	}
	return s.persistContent(raw, sourcePath, input, "evidence imported")
}

func (s evidenceService) registerContent(content string, input evidenceCommonInput) Envelope {
	if content == "" {
		return evidenceUsageError("evidence register requires --object or --content")
	}
	if len([]byte(content)) > maxAgentJSONInputBytes {
		return evidenceUsageError(fmt.Sprintf("evidence register --content exceeds %d bytes", maxAgentJSONInputBytes))
	}
	return s.persistContent([]byte(content), "", input, "inline evidence registered")
}

func (s evidenceService) persistContent(raw []byte, externalSourcePath string, input evidenceCommonInput, summary string) Envelope {
	if err := validateEvidenceScope(input.Scope); err != nil {
		return evidenceUsageError(err.Error())
	}
	record := s.newRecord(input)
	record.ExternalSourcePath = externalSourcePath
	record.Size = int64(len(raw))
	record.SHA256 = digestHex(raw)
	record.MIME = evidenceFirstNonEmpty(input.MIME, detectMIME(raw))
	objectRef, objectPath, err := s.objectLocation(record.SHA256)
	if err != nil {
		return evidenceBlockedError("evidence object path is invalid", err)
	}
	if err := os.MkdirAll(filepath.Dir(objectPath), 0o755); err != nil {
		return evidenceBlockedError("evidence object directory is unavailable", err)
	}
	if _, err := os.Stat(objectPath); os.IsNotExist(err) {
		if err := evidenceAtomicWriteFile(objectPath, raw, 0o444); err != nil {
			return evidenceBlockedError("evidence object write failed", err)
		}
	} else if err != nil {
		return evidenceBlockedError("evidence object state is unavailable", err)
	}
	record.Status = "ready"
	record.ObjectRef = objectRef
	env, err := s.persistRecord(record)
	if err != nil {
		return evidenceBlockedError("evidence record write failed", err)
	}
	env.Summary = summary
	return env
}

func (s evidenceService) registerObject(objectRef string, input evidenceCommonInput) Envelope {
	if strings.TrimSpace(objectRef) == "" {
		return evidenceUsageError("evidence register requires --object or --content")
	}
	if err := validateEvidenceScope(input.Scope); err != nil {
		return evidenceUsageError(err.Error())
	}
	canonicalRef := filepath.ToSlash(strings.TrimSpace(objectRef))
	if !strings.HasPrefix(canonicalRef, ".specify/evidence/objects/sha256/") {
		return evidenceUsageError("evidence register object must stay inside .specify/evidence/objects/sha256/")
	}
	objectPath, err := secureProjectPath(s.projectRoot, canonicalRef)
	if err != nil {
		return evidenceUsageError("evidence register object path is invalid")
	}
	info, err := os.Stat(objectPath)
	if err != nil {
		return evidenceBlockedError("evidence object is unavailable", err)
	}
	if !info.Mode().IsRegular() {
		return evidenceUsageError("evidence register requires a regular object file")
	}
	raw, err := os.ReadFile(objectPath)
	if err != nil {
		return evidenceBlockedError("evidence object is unavailable", err)
	}
	record := s.newRecord(input)
	record.Status = "ready"
	record.SHA256 = digestHex(raw)
	record.Size = int64(len(raw))
	record.MIME = evidenceFirstNonEmpty(input.MIME, detectMIME(raw))
	record.ObjectRef = canonicalRef
	env, err := s.persistRecord(record)
	if err != nil {
		return evidenceBlockedError("evidence record write failed", err)
	}
	env.Summary = "evidence registered"
	return env
}

func (s evidenceService) show(recordRef, view string) Envelope {
	record, err := s.readRecord(recordRef)
	if err != nil {
		return evidenceBlockedError("evidence record is unavailable", err)
	}
	if view == "" {
		view = "summary"
	}
	if view != "summary" && view != "full" {
		return evidenceUsageError("evidence show requires --view summary or --view full")
	}
	env := NewEnvelope("ok", "evidence summary")
	env.Data = evidenceReceipt(record)
	if view == "full" {
		env.Summary = "evidence details"
		env.Data["metadata"] = evidenceMetadata(record)
	}
	return env
}

func (s evidenceService) verify(recordRef string) Envelope {
	record, err := s.readRecord(recordRef)
	if err != nil {
		return evidenceBlockedError("evidence record is unavailable", err)
	}
	if record.ObjectRef == "" {
		return evidenceUsageError("allocated evidence cannot be verified before object registration")
	}
	objectPath, err := secureProjectPath(s.projectRoot, record.ObjectRef)
	if err != nil {
		return evidenceUsageError("evidence object path is invalid")
	}
	raw, err := os.ReadFile(objectPath)
	if err != nil {
		return evidenceBlockedError("evidence object is unavailable", err)
	}
	actualSHA := digestHex(raw)
	if actualSHA != record.SHA256 || int64(len(raw)) != record.Size {
		env := NewEnvelope("invalid", "evidence verification failed")
		env.Data["record_ref"] = record.RecordRef
		env.Data["expected_sha256"] = record.SHA256
		env.Data["actual_sha256"] = actualSHA
		env.Data["expected_size"] = record.Size
		env.Data["actual_size"] = len(raw)
		return env
	}
	env := NewEnvelope("ok", "evidence verified")
	env.Data = evidenceReceipt(record)
	return env
}

func (s evidenceService) newRecord(input evidenceCommonInput) EvidenceRecord {
	now := time.Now().UTC().Format(time.RFC3339)
	evidenceID := newEvidenceID(now, input)
	recordRef := filepath.ToSlash(filepath.Join(".specify", "evidence", "records", evidenceID+".json"))
	return EvidenceRecord{
		SchemaVersion: evidenceSchemaVersion,
		EvidenceID:    evidenceID,
		Status:        "allocated",
		MIME:          strings.TrimSpace(input.MIME),
		Scope:         strings.TrimSpace(input.Scope),
		Source:        strings.TrimSpace(input.Source),
		Provenance:    strings.TrimSpace(input.Provenance),
		TaskID:        strings.TrimSpace(input.TaskID),
		ScenarioID:    strings.TrimSpace(input.ScenarioID),
		RecordRef:     recordRef,
		CreatedAt:     now,
	}
}

func (s evidenceService) persistRecord(record EvidenceRecord) (Envelope, error) {
	target, err := secureProjectPath(s.projectRoot, record.RecordRef)
	if err != nil {
		return Envelope{}, err
	}
	raw, err := json.MarshalIndent(record, "", "  ")
	if err != nil {
		return Envelope{}, err
	}
	if err := evidenceAtomicWriteFile(target, append(raw, '\n'), 0o644); err != nil {
		return Envelope{}, err
	}
	env := NewEnvelope("ok", "evidence recorded")
	env.Data = evidenceReceipt(record)
	return env, nil
}

func (s evidenceService) readRecord(recordRef string) (EvidenceRecord, error) {
	if strings.TrimSpace(recordRef) == "" {
		return EvidenceRecord{}, fmt.Errorf("evidence record is required")
	}
	target, err := secureProjectPath(s.projectRoot, filepath.ToSlash(strings.TrimSpace(recordRef)))
	if err != nil {
		return EvidenceRecord{}, err
	}
	raw, err := os.ReadFile(target)
	if err != nil {
		return EvidenceRecord{}, err
	}
	var record EvidenceRecord
	if err := json.Unmarshal(raw, &record); err != nil {
		return EvidenceRecord{}, err
	}
	return record, nil
}

func (s evidenceService) objectLocation(sha string) (string, string, error) {
	if !evidenceHexPattern.MatchString(sha) {
		return "", "", fmt.Errorf("invalid sha256")
	}
	ref := filepath.ToSlash(filepath.Join(".specify", "evidence", "objects", "sha256", sha[:2], sha))
	path, err := secureProjectPath(s.projectRoot, ref)
	if err != nil {
		return "", "", err
	}
	return ref, path, nil
}

func validateEvidenceScope(scope string) error {
	scope = strings.TrimSpace(scope)
	if scope == "" {
		return fmt.Errorf("evidence scope is required")
	}
	if strings.ContainsAny(scope, `/\`) {
		return fmt.Errorf("evidence scope must be a single logical segment")
	}
	return nil
}

func evidenceReceipt(record EvidenceRecord) map[string]any {
	return map[string]any{
		"evidence_id": record.EvidenceID,
		"status":      record.Status,
		"sha256":      record.SHA256,
		"size":        record.Size,
		"mime":        record.MIME,
		"scope":       record.Scope,
		"source":      record.Source,
		"provenance":  record.Provenance,
		"task_id":     record.TaskID,
		"scenario_id": record.ScenarioID,
		"record_ref":  record.RecordRef,
		"object_ref":  record.ObjectRef,
	}
}

func evidenceMetadata(record EvidenceRecord) map[string]any {
	return map[string]any{
		"schema_version":       record.SchemaVersion,
		"evidence_id":          record.EvidenceID,
		"status":               record.Status,
		"sha256":               record.SHA256,
		"size":                 record.Size,
		"mime":                 record.MIME,
		"scope":                record.Scope,
		"source":               record.Source,
		"provenance":           record.Provenance,
		"task_id":              record.TaskID,
		"scenario_id":          record.ScenarioID,
		"record_ref":           record.RecordRef,
		"object_ref":           record.ObjectRef,
		"external_source_path": record.ExternalSourcePath,
		"created_at":           record.CreatedAt,
	}
}

func newEvidenceID(now string, input evidenceCommonInput) string {
	seed := strings.Join([]string{
		now,
		strings.TrimSpace(input.Scope),
		strings.TrimSpace(input.TaskID),
		strings.TrimSpace(input.ScenarioID),
		strings.TrimSpace(input.Source),
		strings.TrimSpace(input.Provenance),
	}, "\x00")
	sum := sha256.Sum256([]byte(seed))
	return "evd-" + hex.EncodeToString(sum[:])[:24]
}

func digestHex(raw []byte) string {
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func detectMIME(raw []byte) string {
	if len(raw) == 0 {
		return "application/octet-stream"
	}
	return strings.TrimSpace(strings.Split(http.DetectContentType(raw), ";")[0])
}

func evidenceFirstNonEmpty(values ...string) string {
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			return value
		}
	}
	return ""
}

func evidenceOptionValue(args []string, name, fallback string) string {
	for index := 0; index < len(args); index++ {
		if args[index] == name && index+1 < len(args) {
			return args[index+1]
		}
	}
	return fallback
}

func writeEvidenceEnvelope(stdout io.Writer, env Envelope) int {
	raw, err := json.MarshalIndent(env, "", "  ")
	if err != nil {
		fallback := NewEnvelope("error", "failed to encode evidence response")
		fallback.Blockers = append(fallback.Blockers, err.Error())
		raw, _ = json.MarshalIndent(fallback, "", "  ")
		_, _ = stdout.Write(append(raw, '\n'))
		return ExitCodeForStatus(fallback.Status)
	}
	_, _ = stdout.Write(append(raw, '\n'))
	return ExitCodeForStatus(env.Status)
}

func evidenceAtomicWriteFile(path string, content []byte, perm os.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	temp, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".tmp-*")
	if err != nil {
		return err
	}
	tempPath := temp.Name()
	defer os.Remove(tempPath)
	if _, err := temp.Write(content); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Chmod(perm); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	return os.Rename(tempPath, path)
}

func evidenceUsageError(summary string) Envelope {
	return NewEnvelope("usage-error", summary)
}

func evidenceBlockedError(summary string, err error) Envelope {
	env := NewEnvelope("blocked", summary)
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}
