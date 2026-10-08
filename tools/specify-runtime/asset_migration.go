package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	assetMigrationMaxMoves     = 64
	assetMigrationMaxRefs      = 256
	assetMigrationMaxFileBytes = 64 << 20
	assetMigrationMaxRefBytes  = 2 << 20
	assetMigrationMaxBytes     = 128 << 20
	assetMigrationMaxChanges   = 2048
)

type AssetMigrationMove struct {
	From string `json:"from"`
	To   string `json:"to"`
}

type AssetMigrationPlanRequest struct {
	PolicyPath             string               `json:"policy_path,omitempty"`
	Moves                  []AssetMigrationMove `json:"moves"`
	ReferencePaths         []string             `json:"reference_paths,omitempty"`
	ReferenceSearchRoots   []string             `json:"reference_search_roots,omitempty"`
	ReferenceScopeComplete bool                 `json:"reference_scope_complete,omitempty"`
}

type AssetMigrationPlannedMove struct {
	From        string `json:"from"`
	To          string `json:"to"`
	SHA256      string `json:"sha256"`
	AfterSHA256 string `json:"after_sha256"`
	Bytes       int64  `json:"bytes"`
	Mode        uint32 `json:"mode"`
	Reason      string `json:"reason"`
}

type AssetMigrationReferenceChange struct {
	Line   int    `json:"line"`
	Before string `json:"before"`
	After  string `json:"after"`
	Reason string `json:"reason"`
}

type AssetMigrationReference struct {
	Path        string                          `json:"path"`
	Destination string                          `json:"destination"`
	SHA256      string                          `json:"sha256"`
	AfterSHA256 string                          `json:"after_sha256"`
	Bytes       int64                           `json:"bytes"`
	Mode        uint32                          `json:"mode"`
	Changes     []AssetMigrationReferenceChange `json:"changes"`
}

type AssetMigrationUnsupported struct {
	Path   string `json:"path"`
	Reason string `json:"reason"`
}

type AssetMigrationCoverage struct {
	Mode                  string                       `json:"mode"`
	DeclaredScopeComplete bool                         `json:"declared_scope_complete"`
	GlobalScanPerformed   bool                         `json:"global_scan_performed"`
	Unsupported           []AssetMigrationUnsupported  `json:"unsupported"`
	Limitations           []string                     `json:"limitations"`
	ReferenceProbe        AssetMigrationReferenceProbe `json:"reference_probe"`
}

type AssetMigrationReferenceProbe struct {
	Status       string   `json:"status"`
	SearchRoots  []string `json:"search_roots"`
	FilesChecked int      `json:"files_checked"`
	BytesChecked int64    `json:"bytes_checked"`
	Fingerprint  string   `json:"fingerprint,omitempty"`
}

// Plans are returned to the caller, never written by the read-only planner.
// Their digest binds the project, effective policy, inputs and every read file.
type AssetMigrationPlan struct {
	SchemaVersion     int                         `json:"schema_version"`
	ProjectRoot       string                      `json:"project_root"`
	Request           AssetMigrationPlanRequest   `json:"request"`
	PolicySHA256      string                      `json:"policy_sha256"`
	Moves             []AssetMigrationPlannedMove `json:"moves"`
	References        []AssetMigrationReference   `json:"references"`
	CreateDirectories []string                    `json:"create_directories"`
	Coverage          AssetMigrationCoverage      `json:"coverage"`
	Digest            string                      `json:"digest"`
}

type AssetMigrationApplyRequest struct {
	Plan           AssetMigrationPlan `json:"plan"`
	ExpectedDigest string             `json:"expected_digest"`
}

func (s *AssetService) MigrationPlan(request AssetMigrationPlanRequest) Envelope {
	plan, _, err := s.buildAssetMigrationPlan(request)
	if err != nil {
		return assetMigrationFailure("migration-plan-invalid", err)
	}
	status, summary := "ok", "Read-only migration plan prepared for the explicit reference scope"
	if len(plan.Coverage.Unsupported) != 0 {
		status, summary = "blocked", "Unsupported references prevent migration; no files were changed"
	} else if !plan.Coverage.DeclaredScopeComplete {
		status, summary = "warn", "Plan is limited to explicit references; declare the intended scope before applying"
	}
	env := NewEnvelope(status, summary)
	env.Data["plan"] = plan
	env.Data["digest"] = plan.Digest
	env.Data["coverage"] = "explicit-references-only"
	env.Data["read_only"] = true
	for _, unsupported := range plan.Coverage.Unsupported {
		env.Blockers = append(env.Blockers, map[string]any{"code": "unsupported-reference", "path": unsupported.Path, "message": unsupported.Reason})
	}
	return env
}

func (s *AssetService) buildAssetMigrationPlan(request AssetMigrationPlanRequest) (AssetMigrationPlan, map[string][]byte, error) {
	var plan AssetMigrationPlan
	if len(request.Moves) == 0 || len(request.Moves) > assetMigrationMaxMoves || len(request.ReferencePaths) > assetMigrationMaxRefs {
		return plan, nil, fmt.Errorf("migration requires 1..%d explicit moves and at most %d reference paths", assetMigrationMaxMoves, assetMigrationMaxRefs)
	}
	root, err := filepath.Abs(s.projectRoot)
	if err != nil {
		return plan, nil, err
	}
	policy, err := s.LoadPolicy(request.PolicyPath)
	if err != nil {
		return plan, nil, err
	}
	policyRaw, err := json.Marshal(policy)
	if err != nil {
		return plan, nil, err
	}
	plan = AssetMigrationPlan{
		SchemaVersion: 1, ProjectRoot: filepath.ToSlash(root), PolicySHA256: fileContentSHA256(policyRaw),
		Moves: []AssetMigrationPlannedMove{}, References: []AssetMigrationReference{}, CreateDirectories: []string{},
		Coverage: AssetMigrationCoverage{Mode: "explicit-references-only", DeclaredScopeComplete: request.ReferenceScopeComplete,
			Unsupported: []AssetMigrationUnsupported{}, Limitations: []string{
				"Only explicit reference files and moved Markdown documents can be rewritten; the caller's scope declaration is not proof of global completeness.",
				"When Git is available, a bounded lexical text probe detects omitted incoming references within reference_search_roots; it does not resolve code imports, engine/package graphs, external URLs or catalog identity.",
				"New destination publication requires hard-link support on the journal/destination filesystem; unsupported or cross-device publication fails and rolls back.",
				"Writers using the shared transaction lock are serialized. Existing files are captured and retained before replacement; external editors with long-lived file descriptors can still modify a captured inode after verification. Close other editors during apply; no atomic guarantee is made for uncooperative external writers.",
			}},
	}
	request.Moves = append([]AssetMigrationMove(nil), request.Moves...)
	request.ReferencePaths = append([]string(nil), request.ReferencePaths...)
	request.ReferenceSearchRoots = append([]string(nil), request.ReferenceSearchRoots...)
	if len(request.ReferenceSearchRoots) == 0 {
		request.ReferenceSearchRoots = []string{"."}
	}
	if len(request.ReferenceSearchRoots) > 16 {
		return plan, nil, fmt.Errorf("at most 16 explicit reference_search_roots are supported")
	}
	searchRoots := map[string]bool{}
	for _, root := range request.ReferenceSearchRoots {
		if root != "." {
			if _, err := assetMigrationNormalizePath(root); err != nil {
				return plan, nil, err
			}
		}
		searchRoots[root] = true
	}
	request.ReferenceSearchRoots = []string{}
	for root := range searchRoots {
		request.ReferenceSearchRoots = append(request.ReferenceSearchRoots, root)
	}
	sort.Strings(request.ReferenceSearchRoots)
	fromSet, toSet := map[string]bool{}, map[string]bool{}
	caseTargets := map[string]string{}
	mapping := map[string]string{}
	contents := map[string][]byte{}
	fileInfo := map[string]os.FileInfo{}
	total := int64(0)
	read := func(relative string, max int64) ([]byte, os.FileInfo, error) {
		if data, exists := contents[relative]; exists {
			if int64(len(data)) > max {
				return nil, nil, fmt.Errorf("reference exceeds the %d-byte read limit: %s", max, relative)
			}
			return data, fileInfo[relative], nil
		}
		data, info, readErr := assetMigrationRead(root, relative, max)
		if readErr != nil {
			return nil, nil, readErr
		}
		total += int64(len(data))
		if total > assetMigrationMaxBytes {
			return nil, nil, fmt.Errorf("migration exceeds the %d-byte total read limit", assetMigrationMaxBytes)
		}
		contents[relative], fileInfo[relative] = data, info
		return data, info, nil
	}
	for index, move := range request.Moves {
		from, pathErr := assetMigrationNormalizePath(move.From)
		if pathErr != nil {
			return plan, nil, pathErr
		}
		to, pathErr := assetMigrationNormalizePath(move.To)
		if pathErr != nil {
			return plan, nil, pathErr
		}
		if strings.EqualFold(from, to) || fromSet[from] || toSet[to] {
			return plan, nil, fmt.Errorf("duplicate, identity, or case-only move is not supported: %s -> %s", from, to)
		}
		for folded, previous := range caseTargets {
			if strings.EqualFold(folded, to) {
				return plan, nil, fmt.Errorf("case-colliding targets: %s and %s", previous, to)
			}
		}
		caseTargets[to] = to
		fromSet[from], toSet[to], mapping[from] = true, true, to
		request.Moves[index] = AssetMigrationMove{From: from, To: to}
	}
	for from := range fromSet {
		if toSet[from] {
			return plan, nil, fmt.Errorf("move chains and swaps require separate reviewed plans: %s", from)
		}
	}
	sort.Slice(request.Moves, func(i, j int) bool { return request.Moves[i].From < request.Moves[j].From })
	refs := map[string]bool{}
	for _, reference := range request.ReferencePaths {
		relative, pathErr := assetMigrationNormalizePath(reference)
		if pathErr != nil {
			return plan, nil, pathErr
		}
		refs[relative] = true
	}
	request.ReferencePaths = nil
	for relative := range refs {
		request.ReferencePaths = append(request.ReferencePaths, relative)
	}
	sort.Strings(request.ReferencePaths)
	plan.Request = request
	for _, move := range request.Moves {
		if err := s.assetMigrationCheckClass(move.From, policy, false); err != nil {
			return plan, nil, err
		}
		if err := s.assetMigrationCheckClass(move.To, policy, true); err != nil {
			return plan, nil, err
		}
		for _, relative := range []string{move.From, move.To} {
			if err := assetMigrationNativeBoundary(root, relative); err != nil {
				return plan, nil, err
			}
		}
		if !assetMigrationSupportedSource(move.From) || !strings.EqualFold(filepath.Ext(move.From), filepath.Ext(move.To)) {
			return plan, nil, fmt.Errorf("unsupported source format or extension change: %s -> %s; use its owning tool", move.From, move.To)
		}
		for _, relative := range []string{move.From, move.To} {
			if err := assetMigrationCaseCheck(root, relative); err != nil {
				return plan, nil, err
			}
		}
		target, err := secureProjectPath(root, move.To)
		if err != nil {
			return plan, nil, err
		}
		if _, err := os.Lstat(target); !os.IsNotExist(err) {
			return plan, nil, fmt.Errorf("migration target must be absent: %s", move.To)
		}
		raw, info, err := read(move.From, assetMigrationMaxFileBytes)
		if err != nil {
			return plan, nil, err
		}
		plan.Moves = append(plan.Moves, AssetMigrationPlannedMove{From: move.From, To: move.To, SHA256: fileContentSHA256(raw),
			AfterSHA256: fileContentSHA256(raw), Bytes: int64(len(raw)), Mode: uint32(info.Mode().Perm()),
			Reason: "Explicit relocation; the destination satisfies the current project asset policy"})
		if assetMigrationMarkdown(move.From) {
			refs[move.From] = true
		}
	}
	refPaths := []string{}
	for reference := range refs {
		refPaths = append(refPaths, reference)
	}
	sort.Strings(refPaths)
	outputs := map[string][]byte{}
	for _, move := range plan.Moves {
		outputs[move.To] = contents[move.From]
	}
	changes := 0
	for _, reference := range refPaths {
		if err := s.assetMigrationReferenceBoundary(reference, policy); err != nil {
			plan.Coverage.Unsupported = append(plan.Coverage.Unsupported, AssetMigrationUnsupported{Path: reference, Reason: err.Error()})
			continue
		}
		raw, info, err := read(reference, assetMigrationMaxRefBytes)
		if err != nil {
			return plan, nil, err
		}
		destination := reference
		if moved, exists := mapping[reference]; exists {
			destination = moved
		}
		updated, edits, rewriteErr := assetMigrationRewriteMarkdown(reference, destination, raw, mapping)
		if rewriteErr != nil {
			plan.Coverage.Unsupported = append(plan.Coverage.Unsupported, AssetMigrationUnsupported{Path: reference, Reason: rewriteErr.Error()})
			updated, edits = raw, []AssetMigrationReferenceChange{}
		}
		changes += len(edits)
		if changes > assetMigrationMaxChanges {
			return plan, nil, fmt.Errorf("migration exceeds the %d-reference-change limit", assetMigrationMaxChanges)
		}
		plan.References = append(plan.References, AssetMigrationReference{Path: reference, Destination: destination,
			SHA256: fileContentSHA256(raw), AfterSHA256: fileContentSHA256(updated), Bytes: int64(len(raw)), Mode: uint32(info.Mode().Perm()), Changes: edits})
		if destination != reference || !bytes.Equal(raw, updated) {
			outputs[destination] = updated
		}
	}
	for index := range plan.Moves {
		plan.Moves[index].AfterSHA256 = fileContentSHA256(outputs[plan.Moves[index].To])
	}
	probe, unsupported, err := s.assetMigrationProbeReferences(root, policy, plan.Request, refs)
	if err != nil {
		return plan, nil, err
	}
	plan.Coverage.ReferenceProbe = probe
	plan.Coverage.Unsupported = append(plan.Coverage.Unsupported, unsupported...)
	missingDirectories := map[string]bool{}
	for target := range outputs {
		for parent := path.Dir(target); parent != "."; parent = path.Dir(parent) {
			secured, secureErr := secureProjectPath(root, parent)
			if secureErr != nil {
				return plan, nil, secureErr
			}
			info, statErr := os.Stat(secured)
			if statErr == nil {
				if !info.IsDir() {
					return plan, nil, fmt.Errorf("migration destination parent is not a directory: %s", parent)
				}
				break
			}
			if !os.IsNotExist(statErr) {
				return plan, nil, statErr
			}
			missingDirectories[parent] = true
		}
	}
	for directory := range missingDirectories {
		plan.CreateDirectories = append(plan.CreateDirectories, directory)
	}
	sort.Slice(plan.CreateDirectories, func(i, j int) bool {
		if strings.Count(plan.CreateDirectories[i], "/") != strings.Count(plan.CreateDirectories[j], "/") {
			return strings.Count(plan.CreateDirectories[i], "/") < strings.Count(plan.CreateDirectories[j], "/")
		}
		return plan.CreateDirectories[i] < plan.CreateDirectories[j]
	})
	plan.Digest, err = assetMigrationPlanDigest(plan)
	return plan, outputs, err
}

func (s *AssetService) assetMigrationCheckClass(relative string, policy AssetPolicy, target bool) error {
	classification, err := s.ClassifyPath(relative, policy)
	if err != nil {
		return err
	}
	if _, owned := LookupArtifactType(relative); owned || classification.Protected || classification.Temporary || classification.Cache || classification.Kind == "source" || assetIsFixedName(path.Base(relative), policy) {
		return fmt.Errorf("migration cannot change an owned, protected, source-code, cache, or temporary path: %s", relative)
	}
	if classification.Kind != "document" && classification.Kind != "media" {
		return fmt.Errorf("migration supports only ordinary documents and single-file media: %s", relative)
	}
	if target && !classification.Compliant {
		return fmt.Errorf("migration target violates the asset policy: %s (%v)", relative, classification.Issues)
	}
	return nil
}

func (s *AssetService) assetMigrationReferenceBoundary(relative string, policy AssetPolicy) error {
	classification, err := s.ClassifyPath(relative, policy)
	if err != nil {
		return err
	}
	if _, owned := LookupArtifactType(relative); owned || classification.Protected || classification.Temporary || classification.Cache || classification.Kind != "document" {
		return fmt.Errorf("reference is owned, source/template/fixture, protected, transient, or not an ordinary document; its owning tool must update it: %s", relative)
	}
	if !assetMigrationMarkdown(relative) {
		return fmt.Errorf("only ordinary Markdown inline/image links and link reference definitions support verified rewriting: %s", relative)
	}
	return assetMigrationNativeBoundary(s.projectRoot, relative)
}

func assetMigrationNativeBoundary(root, relative string) error {
	for _, component := range strings.Split(relative, "/") {
		if component == "Assets" || component == "Content" || component == "res" || strings.HasSuffix(component, ".xcassets") || strings.HasSuffix(component, ".imageset") || strings.HasSuffix(component, ".appiconset") {
			return fmt.Errorf("native engine/platform resources require their owning tool for relocation: %s", relative)
		}
	}
	for _, suffix := range []string{".meta", ".import", ".uid"} {
		sidecar, err := secureProjectPath(root, relative+suffix)
		if err != nil {
			return err
		}
		if _, err := os.Lstat(sidecar); err == nil {
			return fmt.Errorf("resource has a native sidecar; its owning tool must move both and maintain references: %s", relative)
		} else if !os.IsNotExist(err) {
			return err
		}
	}
	extension := path.Ext(relative)
	stem := strings.TrimSuffix(relative, extension)
	for _, suffix := range []string{"@1x", "@2x", "@3x"} {
		stem = strings.TrimSuffix(stem, suffix)
	}
	for _, suffix := range []string{"", "@1x", "@2x", "@3x"} {
		variant := stem + suffix + extension
		if variant == relative {
			continue
		}
		secured, err := secureProjectPath(root, variant)
		if err != nil {
			return err
		}
		if _, err := os.Lstat(secured); err == nil {
			return fmt.Errorf("resource has resolution variants; its owning platform must move the complete set: %s", relative)
		} else if !os.IsNotExist(err) {
			return err
		}
	}
	return nil
}

func assetMigrationNormalizePath(relative string) (string, error) {
	if relative == "" || len(relative) > 1024 || !utf8.ValidString(relative) || strings.TrimSpace(relative) != relative || strings.ContainsAny(relative, "\\:\x00\r\n") || strings.HasPrefix(relative, "/") || path.Clean(relative) != relative || relative == "." || relative == ".." || strings.HasPrefix(relative, "../") {
		return "", fmt.Errorf("migration requires a normalized project-relative path: %q", relative)
	}
	return relative, nil
}

func assetMigrationRead(root, relative string, maximum int64) ([]byte, os.FileInfo, error) {
	secured, err := secureProjectPath(root, relative)
	if err != nil {
		return nil, nil, err
	}
	pathInfo, err := os.Lstat(secured)
	if err != nil {
		return nil, nil, err
	}
	if !pathInfo.Mode().IsRegular() {
		return nil, nil, fmt.Errorf("migration requires a regular file, not a symlink/device/pipe: %s", relative)
	}
	file, err := os.Open(secured)
	if err != nil {
		return nil, nil, err
	}
	defer file.Close()
	before, err := file.Stat()
	if err != nil || !before.Mode().IsRegular() || !os.SameFile(pathInfo, before) {
		return nil, nil, fmt.Errorf("migration requires an existing regular file: %s", relative)
	}
	if before.Size() > maximum {
		return nil, nil, fmt.Errorf("migration file exceeds the %d-byte limit: %s", maximum, relative)
	}
	raw, err := io.ReadAll(io.LimitReader(file, maximum+1))
	if err != nil || int64(len(raw)) > maximum {
		return nil, nil, fmt.Errorf("migration file could not be read within its byte limit: %s", relative)
	}
	after, err := file.Stat()
	if err != nil || before.Size() != after.Size() || before.Mode() != after.Mode() || !before.ModTime().Equal(after.ModTime()) {
		return nil, nil, fmt.Errorf("migration file changed while being inspected: %s", relative)
	}
	afterPath, err := os.Lstat(secured)
	if err != nil || !afterPath.Mode().IsRegular() || !os.SameFile(before, afterPath) {
		return nil, nil, fmt.Errorf("migration file path changed while being inspected: %s", relative)
	}
	return raw, before, nil
}

func assetMigrationCaseCheck(root, relative string) error {
	current := root
	for _, component := range strings.Split(relative, "/") {
		directory, err := os.Open(current)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		entries, err := directory.ReadDir(4097)
		_ = directory.Close()
		if err != nil && err != io.EOF {
			return err
		}
		if len(entries) > 4096 {
			return fmt.Errorf("directory exceeds the bounded case-collision check: %s", current)
		}
		for _, entry := range entries {
			if strings.EqualFold(entry.Name(), component) && entry.Name() != component {
				return fmt.Errorf("case-colliding path component %s conflicts with %s", component, entry.Name())
			}
		}
		current = filepath.Join(current, component)
	}
	return nil
}

func assetMigrationMarkdown(relative string) bool {
	extension := strings.ToLower(filepath.Ext(relative))
	return extension == ".md" || extension == ".markdown"
}

func assetMigrationSupportedSource(relative string) bool {
	if assetMigrationMarkdown(relative) {
		return true
	}
	switch strings.ToLower(filepath.Ext(relative)) {
	case ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".ico", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".mp4", ".webm", ".mov":
		return true
	default:
		return false
	}
}

// Detect omitted incoming references without rewriting them. This is bounded
// lexical evidence over Git-visible text, not a complete dependency graph.
func (s *AssetService) assetMigrationProbeReferences(root string, policy AssetPolicy, request AssetMigrationPlanRequest, explicit map[string]bool) (AssetMigrationReferenceProbe, []AssetMigrationUnsupported, error) {
	probe := AssetMigrationReferenceProbe{Status: "unavailable-no-git-root", SearchRoots: append([]string(nil), request.ReferenceSearchRoots...)}
	unsupported := []AssetMigrationUnsupported{}
	top, err := s.assetGit("rev-parse", "--show-toplevel")
	if err != nil {
		if _, statErr := os.Lstat(filepath.Join(root, ".git")); statErr == nil {
			return probe, unsupported, fmt.Errorf("cannot inspect the existing Git repository for incoming references: %w", err)
		}
		return probe, unsupported, nil
	}
	gitRoot, err := filepath.Abs(strings.TrimSpace(string(top)))
	if err != nil || gitRoot != root {
		probe.Status = "unavailable-project-is-not-git-root"
		return probe, unsupported, nil
	}
	for _, searchRoot := range request.ReferenceSearchRoots {
		if searchRoot == "." {
			continue
		}
		secured, err := secureProjectPath(root, searchRoot)
		if err != nil {
			return probe, unsupported, err
		}
		info, err := os.Stat(secured)
		if err != nil || !info.IsDir() {
			return probe, unsupported, fmt.Errorf("reference search root must be an existing directory: %s", searchRoot)
		}
	}
	arguments := append([]string{"ls-files", "--cached", "--others", "--exclude-standard", "-z", "--"}, request.ReferenceSearchRoots...)
	inventory, err := s.assetGit(arguments...)
	if err != nil {
		return probe, unsupported, err
	}
	paths := map[string]bool{}
	for _, relative := range assetNullFields(inventory) {
		if _, err := assetMigrationNormalizePath(relative); err != nil {
			return probe, unsupported, err
		}
		if !assetMigrationProbeText(relative) || assetUnder(relative, ".specify/runtime") || assetUnder(relative, ".specify/tmp") || assetUnder(relative, ".assets/cache") || assetUnder(relative, ".assets/tmp") {
			continue
		}
		classification := classifyAssetPath(relative, policy)
		if classification.Cache || classification.Temporary {
			continue
		}
		for _, skillRoot := range []string{".agents", ".codex", ".claude", ".gemini"} {
			if assetUnder(relative, skillRoot) {
				classification.Cache = true
			}
		}
		if classification.Cache {
			continue
		}
		paths[relative] = true
		if len(paths) > 2000 {
			probe.Status = "blocked-inventory-limit"
			unsupported = append(unsupported, AssetMigrationUnsupported{Path: ".", Reason: "Git-visible text exceeds 2000 files; narrow reference_search_roots and review the explicitly limited scope"})
			return probe, unsupported, nil
		}
	}
	ordered := []string{}
	for relative := range paths {
		ordered = append(ordered, relative)
	}
	sort.Strings(ordered)
	var fingerprints bytes.Buffer
	for _, relative := range ordered {
		raw, _, err := assetMigrationRead(root, relative, assetMigrationMaxRefBytes)
		if os.IsNotExist(err) {
			fmt.Fprintf(&fingerprints, "%s\x00missing\n", relative)
			continue
		}
		if err != nil {
			probe.Status = "blocked-file-inspection"
			unsupported = append(unsupported, AssetMigrationUnsupported{Path: relative, Reason: "Incoming-reference probe could not inspect this Git-visible text file safely: " + err.Error()})
			return probe, unsupported, nil
		}
		probe.FilesChecked++
		probe.BytesChecked += int64(len(raw))
		if probe.BytesChecked > 16<<20 {
			probe.Status = "blocked-byte-limit"
			unsupported = append(unsupported, AssetMigrationUnsupported{Path: relative, Reason: "Incoming-reference probe exceeds 16 MiB; narrow reference_search_roots and review the explicitly limited scope"})
			return probe, unsupported, nil
		}
		fmt.Fprintf(&fingerprints, "%s\x00%s\n", relative, fileContentSHA256(raw))
		if explicit[relative] {
			continue
		}
		if !utf8.Valid(raw) || bytes.IndexByte(raw, 0) >= 0 {
			unsupported = append(unsupported, AssetMigrationUnsupported{Path: relative, Reason: "Git-visible text candidate has an unsupported encoding; incoming references cannot be checked"})
			continue
		}
		for _, move := range request.Moves {
			candidates := []string{move.From, "/" + move.From}
			local, err := filepath.Rel(filepath.FromSlash(path.Dir(relative)), filepath.FromSlash(move.From))
			if err != nil {
				return probe, unsupported, err
			}
			local = filepath.ToSlash(local)
			candidates = append(candidates, local, "./"+local)
			for _, publicRoot := range []string{"public/", "static/"} {
				if strings.HasPrefix(move.From, publicRoot) {
					candidates = append(candidates, "/"+strings.TrimPrefix(move.From, publicRoot))
				}
			}
			matched := false
			for _, candidate := range candidates {
				if bytes.Contains(raw, []byte(candidate)) || bytes.Contains(raw, []byte(assetMigrationEscapePath(candidate))) || bytes.Contains(raw, []byte(strings.ReplaceAll(candidate, "/", "\\"))) {
					matched = true
					break
				}
			}
			if matched {
				reason := "Unlisted incoming reference to " + move.From + "; add this file to reference_paths for supported Markdown rewriting or update it through its owning tool"
				if !assetMigrationMarkdown(relative) || classifyAssetPath(relative, policy).Protected {
					reason = "Unsupported code/configuration/owned incoming reference to " + move.From + "; its owner must handle this relocation before it can be applied"
				}
				unsupported = append(unsupported, AssetMigrationUnsupported{Path: relative, Reason: reason})
				break
			}
		}
	}
	probe.Status = "bounded-git-text-inspection"
	probe.Fingerprint = fileContentSHA256(fingerprints.Bytes())
	return probe, unsupported, nil
}

func assetMigrationProbeText(relative string) bool {
	basename := strings.ToLower(path.Base(relative))
	if strings.HasPrefix(basename, ".env") || strings.HasPrefix(basename, "secrets.") || strings.HasPrefix(basename, ".secrets") || basename == "credentials" || basename == "credentials.json" || basename == "service-account.json" || basename == "id_rsa" || basename == "id_ed25519" {
		return false
	}
	switch strings.ToLower(path.Ext(relative)) {
	case ".md", ".markdown", ".mdx", ".rst", ".txt", ".json", ".jsonl", ".ndjson", ".yaml", ".yml", ".toml", ".xml", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".go", ".py", ".rs", ".java", ".kt", ".kts", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".sh", ".ps1", ".ini", ".cfg", ".conf", ".gd", ".tscn", ".tres", ".shader", ".gdshader":
		return true
	}
	return path.Ext(relative) == "" && !strings.HasPrefix(basename, ".") || basename == ".gitignore" || basename == ".gitattributes" || basename == ".gitmodules"
}

func assetMigrationPlanDigest(plan AssetMigrationPlan) (string, error) {
	plan.Digest = ""
	raw, err := json.Marshal(plan)
	if err != nil {
		return "", err
	}
	return fileContentSHA256(raw), nil
}

// This deliberately recognizes a bounded Markdown subset, not arbitrary code,
// HTML, MDX, engine imports, or URL-to-public-directory mappings.
var assetMigrationInlineLink = regexp.MustCompile(`!?\[[^\]\r\n]*\]\([ \t]*(<[^<>\r\n]*>|[^ \t\r\n()<>"']+)(?:[ \t]+(?:"[^"\r\n]*"|'[^'\r\n]*'|\([^()\r\n]*\)))?[ \t]*\)`)
var assetMigrationDefinition = regexp.MustCompile(`(?m)^[ ]{0,3}\[[^\]\r\n]+\]:[ \t]*(<[^<>\r\n]*>|[^ \t\r\n()<>"']+)(?:[ \t]+(?:"[^"\r\n]*"|'[^'\r\n]*'|\([^()\r\n]*\)))?[ \t]*\r?$`)
var assetMigrationHTMLReference = regexp.MustCompile(`(?i)\b(?:href|src|srcset)[ \t]*=`)

type assetMigrationLinkSpan struct {
	start, end, wholeStart, wholeEnd int
}

func assetMigrationRewriteMarkdown(oldPath, newPath string, raw []byte, mapping map[string]string) ([]byte, []AssetMigrationReferenceChange, error) {
	edits := []AssetMigrationReferenceChange{}
	if !utf8.Valid(raw) || bytes.IndexByte(raw, 0) >= 0 {
		return nil, edits, fmt.Errorf("reference is not plain UTF-8 Markdown")
	}
	spans := []assetMigrationLinkSpan{}
	mask := assetMigrationCodeMask(raw)
	for _, pattern := range []*regexp.Regexp{assetMigrationInlineLink, assetMigrationDefinition} {
		for _, match := range pattern.FindAllSubmatchIndex(raw, -1) {
			if match[2] < 0 || mask[match[0]] {
				continue
			}
			spans = append(spans, assetMigrationLinkSpan{start: match[2], end: match[3], wholeStart: match[0], wholeEnd: match[1]})
		}
	}
	sort.Slice(spans, func(i, j int) bool { return spans[i].start < spans[j].start })
	remainder := append([]byte(nil), raw...)
	var out bytes.Buffer
	cursor := 0
	for _, span := range spans {
		if span.start < cursor {
			return nil, edits, fmt.Errorf("overlapping Markdown constructs require manual reference handling")
		}
		before := string(raw[span.start:span.end])
		after, reason, err := assetMigrationRewriteLink(oldPath, newPath, before, mapping)
		if err != nil {
			return nil, edits, err
		}
		out.Write(raw[cursor:span.start])
		out.WriteString(after)
		cursor = span.end
		for index := span.wholeStart; index < span.wholeEnd; index++ {
			remainder[index] = ' '
		}
		if after != before {
			edits = append(edits, AssetMigrationReferenceChange{Line: bytes.Count(raw[:span.start], []byte{'\n'}) + 1, Before: before, After: after, Reason: reason})
		}
	}
	out.Write(raw[cursor:])
	// A literal path outside the supported constructs could be a code import,
	// HTML attribute, escaped link or plain text reference. Do not guess.
	for from := range mapping {
		relative, err := filepath.Rel(filepath.FromSlash(path.Dir(oldPath)), filepath.FromSlash(from))
		if err != nil {
			return nil, edits, err
		}
		candidates := []string{from, filepath.ToSlash(relative), assetMigrationEscapePath(from), assetMigrationEscapePath(filepath.ToSlash(relative))}
		for _, publicRoot := range []string{"public/", "static/"} {
			if strings.HasPrefix(from, publicRoot) {
				alias := "/" + strings.TrimPrefix(from, publicRoot)
				candidates = append(candidates, alias, assetMigrationEscapePath(alias))
			}
		}
		for _, candidate := range candidates {
			if candidate != "" && bytes.Contains(remainder, []byte(candidate)) {
				return nil, edits, fmt.Errorf("unhandled occurrence of %s outside supported Markdown links; include a supported owner-specific reference update", candidate)
			}
		}
	}
	if path.Dir(oldPath) != path.Dir(newPath) && (bytes.Contains(remainder, []byte("](")) || assetMigrationHTMLReference.Match(remainder)) {
		return nil, edits, fmt.Errorf("moving this document could invalidate unsupported relative HTML/code/Markdown references")
	}
	return out.Bytes(), edits, nil
}

func assetMigrationRewriteLink(oldPath, newPath, token string, mapping map[string]string) (string, string, error) {
	angle := strings.HasPrefix(token, "<") && strings.HasSuffix(token, ">")
	value := token
	if angle {
		value = value[1 : len(value)-1]
	}
	parsed, err := url.Parse(value)
	if err != nil {
		return "", "", fmt.Errorf("invalid Markdown destination %q", value)
	}
	if parsed.Scheme != "" || parsed.Host != "" || parsed.Path == "" {
		return token, "", nil
	}
	if strings.Contains(parsed.Path, "\\") {
		return "", "", fmt.Errorf("platform-dependent Markdown destination requires manual handling: %s", value)
	}
	rooted := strings.HasPrefix(parsed.Path, "/")
	resolved := path.Clean(path.Join(path.Dir(oldPath), parsed.Path))
	if rooted {
		resolved = strings.TrimPrefix(path.Clean(parsed.Path), "/")
	}
	if resolved == ".." || strings.HasPrefix(resolved, "../") {
		return "", "", fmt.Errorf("Markdown destination escapes the project: %s", value)
	}
	target := resolved
	reason := "Preserve a relative destination after moving its document"
	if relocated, exists := mapping[resolved]; exists {
		target = relocated
		reason = "Update a link to an explicitly relocated file"
	} else {
		for from := range mapping {
			for _, publicRoot := range []string{"public/", "static/"} {
				if strings.HasPrefix(from, publicRoot) && strings.TrimPrefix(from, publicRoot) == resolved {
					return "", "", fmt.Errorf("possible public/static URL %s refers to %s; the framework owner must update its URL mapping", value, from)
				}
			}
		}
	}
	if target == resolved && (rooted || path.Dir(oldPath) == path.Dir(newPath)) {
		return token, "", nil
	}
	newLink := "/" + target
	if !rooted {
		relative, err := filepath.Rel(filepath.FromSlash(path.Dir(newPath)), filepath.FromSlash(target))
		if err != nil {
			return "", "", err
		}
		newLink = filepath.ToSlash(relative)
		if strings.HasPrefix(parsed.Path, "./") && !strings.HasPrefix(newLink, ".") {
			newLink = "./" + newLink
		}
	}
	newLink = assetMigrationEscapePath(newLink)
	if parsed.RawQuery != "" || parsed.ForceQuery {
		newLink += "?" + parsed.RawQuery
	}
	if strings.Contains(value, "#") {
		newLink += "#" + parsed.EscapedFragment()
	}
	if angle {
		newLink = "<" + newLink + ">"
	}
	return newLink, reason, nil
}

func assetMigrationEscapePath(value string) string {
	parts := strings.Split(value, "/")
	for index := range parts {
		parts[index] = url.PathEscape(parts[index])
	}
	return strings.Join(parts, "/")
}

func assetMigrationCodeMask(raw []byte) []bool {
	mask := make([]bool, len(raw)+1)
	fence := byte(0)
	fenceLength := 0
	offset := 0
	for _, line := range bytes.SplitAfter(raw, []byte{'\n'}) {
		trimmed := bytes.TrimLeft(line, " ")
		indent := len(line) - len(trimmed)
		run := 0
		if len(trimmed) > 0 && (trimmed[0] == '`' || trimmed[0] == '~') {
			for run < len(trimmed) && trimmed[run] == trimmed[0] {
				run++
			}
		}
		code := fence != 0 || indent >= 4
		if indent < 4 && run >= 3 && (fence == 0 || trimmed[0] == fence && run >= fenceLength) {
			code = true
			if fence == 0 {
				fence, fenceLength = trimmed[0], run
			} else {
				fence, fenceLength = 0, 0
			}
		}
		if code {
			for index := range line {
				mask[offset+index] = true
			}
		} else {
			for index := 0; index < len(line); index++ {
				if line[index] != '`' {
					continue
				}
				endRun := index + 1
				for endRun < len(line) && line[endRun] == '`' {
					endRun++
				}
				end := bytes.Index(line[endRun:], line[index:endRun])
				if end >= 0 {
					end += endRun + (endRun - index)
					for cursor := index; cursor < end; cursor++ {
						mask[offset+cursor] = true
					}
					index = end - 1
				} else {
					index = endRun - 1
				}
			}
		}
		offset += len(line)
	}
	return mask
}

func assetMigrationFailure(code string, err error) Envelope {
	env := NewEnvelope("blocked", err.Error())
	env.Blockers = append(env.Blockers, map[string]any{"code": code, "message": err.Error()})
	return env
}

type assetMigrationEntry struct {
	Path               string `json:"path"`
	Existed            bool   `json:"existed"`
	Delete             bool   `json:"delete"`
	BeforeSHA256       string `json:"before_sha256,omitempty"`
	AfterSHA256        string `json:"after_sha256,omitempty"`
	Mode               uint32 `json:"mode"`
	CaptureRef         string `json:"capture_ref,omitempty"`
	RollbackCaptureRef string `json:"rollback_capture_ref"`
	Applied            bool   `json:"applied"`
}

type assetMigrationJournal struct {
	SchemaVersion int                   `json:"schema_version"`
	PlanDigest    string                `json:"plan_digest"`
	ProjectRoot   string                `json:"project_root"`
	Phase         string                `json:"phase"`
	Entries       []assetMigrationEntry `json:"entries"`
	CreatedDirs   []string              `json:"created_dirs"`
}

// publish is replaceable by focused failure-injection tests. Normal execution
// preserves bytes in durable backups before either a replacement or a removal.
var assetMigrationPublish = publishAssetMigrationEntry

// The journal records the capture destination and intent before this boundary.
// Keeping the captured inode also preserves writes through an already open FD.
var assetMigrationCapture = captureAssetMigrationEntry

func (s *AssetService) MigrationApply(request AssetMigrationApplyRequest) Envelope {
	plan := request.Plan
	digest, err := assetMigrationPlanDigest(plan)
	if err != nil || plan.SchemaVersion != 1 || request.ExpectedDigest == "" || plan.Digest != digest || request.ExpectedDigest != digest {
		return assetMigrationFailure("migration-digest-mismatch", fmt.Errorf("apply requires an unchanged schema-1 plan and its exact expected_digest"))
	}
	root, err := filepath.Abs(s.projectRoot)
	if err != nil || filepath.ToSlash(root) != plan.ProjectRoot {
		return assetMigrationFailure("migration-project-mismatch", fmt.Errorf("migration plan is bound to a different project"))
	}
	if plan.Coverage.Mode != "explicit-references-only" || plan.Coverage.GlobalScanPerformed || len(plan.Coverage.Unsupported) > 0 || !plan.Request.ReferenceScopeComplete {
		return assetMigrationFailure("migration-reference-coverage", fmt.Errorf("apply requires a declared explicit reference scope with no unsupported references; this does not establish global coverage"))
	}
	if err := s.assetMigrationRecoveryBoundaries(plan); err != nil {
		return assetMigrationFailure("migration-owner-boundary", err)
	}
	journalRef := ".specify/runtime/asset-migrations/" + digest
	journalRoot, err := secureProjectPath(root, journalRef)
	if err != nil {
		return assetMigrationFailure("migration-unsafe-journal", err)
	}
	_, existingErr := os.Lstat(journalRoot)
	if os.IsNotExist(existingErr) {
		// Invalid/stale requests have no filesystem side effects, including locks.
		fresh, _, buildErr := s.buildAssetMigrationPlan(plan.Request)
		if buildErr != nil {
			return assetMigrationFailure("migration-precondition", buildErr)
		}
		if fresh.Digest != digest {
			return assetMigrationFailure("migration-precondition", fmt.Errorf("project files, paths, modes, policy, references, or destination directories changed after planning; review a new plan"))
		}
	} else if existingErr != nil {
		return assetMigrationFailure("migration-journal-unavailable", existingErr)
	}
	lockPath, err := secureProjectPath(root, ".specify/runtime/locks/file-transactions.lock")
	if err != nil {
		return assetMigrationFailure("migration-lock-invalid", err)
	}
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return assetMigrationFailure("migration-lock-unavailable", err)
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return assetMigrationFailure("migration-lock-unavailable", err)
	}
	defer release()
	journalRoot, err = secureProjectPath(root, journalRef)
	if err != nil {
		return assetMigrationFailure("migration-unsafe-journal", err)
	}
	if err := assetMigrationCheckPending(root, digest); err != nil {
		return assetMigrationFailure("migration-recovery-required", err)
	}
	if _, statErr := os.Lstat(journalRoot); statErr == nil {
		journal, readErr := readAssetMigrationJournal(root, journalRef)
		if readErr != nil {
			return assetMigrationFailure("migration-journal-invalid", readErr)
		}
		if err := validateAssetMigrationJournal(plan, journal); err != nil {
			return assetMigrationFailure("migration-journal-invalid", err)
		}
		if journal.Phase == "committed" {
			if err := verifyAssetMigrationCaptures(root, journalRef, journal.Entries); err != nil {
				return assetMigrationFailure("migration-captured-original-changed", err)
			}
			if err := verifyAssetMigrationResult(root, journal.Entries); err != nil {
				return assetMigrationFailure("migration-committed-files-changed", err)
			}
			return assetMigrationApplied(plan, journalRef, true)
		}
		if err := rollbackAssetMigration(root, journalRef, &journal); err != nil {
			env := assetMigrationFailure("migration-rollback-incomplete", err)
			env.Data["journal_ref"] = journalRef + "/journal.json"
			env.Data["rollback_complete"] = false
			return env
		}
		if _, err := retainAssetMigrationJournal(root, journalRef); err != nil {
			return assetMigrationFailure("migration-recovery-cleanup", err)
		}
	}
	fresh, outputs, err := s.buildAssetMigrationPlan(plan.Request)
	if err != nil {
		return assetMigrationFailure("migration-precondition", err)
	}
	if fresh.Digest != digest || len(fresh.Coverage.Unsupported) > 0 {
		return assetMigrationFailure("migration-precondition", fmt.Errorf("the reviewed plan no longer matches the current project; prepare and review a new plan"))
	}
	entries := assetMigrationEntries(plan)
	transactionID, err := newFileTransactionID()
	if err != nil {
		return assetMigrationFailure("migration-prepare", err)
	}
	preparingRef := ".specify/runtime/asset-migrations/.preparing/" + transactionID
	preparingRoot, err := secureProjectPath(root, preparingRef)
	if err != nil {
		return assetMigrationFailure("migration-prepare", err)
	}
	if err := os.MkdirAll(preparingRoot, 0o755); err != nil {
		return assetMigrationFailure("migration-prepare", err)
	}
	cleanupPreparation := func() { _ = os.RemoveAll(preparingRoot) }
	journal := assetMigrationJournal{SchemaVersion: 1, PlanDigest: digest, ProjectRoot: plan.ProjectRoot, Phase: "prepared", Entries: entries, CreatedDirs: []string{}}
	for index, entry := range entries {
		if entry.Existed {
			raw, info, err := assetMigrationRead(root, entry.Path, assetMigrationMaxFileBytes)
			if err != nil || fileContentSHA256(raw) != entry.BeforeSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
				cleanupPreparation()
				return assetMigrationFailure("migration-precondition", fmt.Errorf("source changed before backup: %s", entry.Path))
			}
			backup := filepath.Join(preparingRoot, fmt.Sprintf("backup-%04d", index))
			if err := atomicWriteFile(backup, raw, os.FileMode(entry.Mode)); err != nil {
				cleanupPreparation()
				return assetMigrationFailure("migration-prepare", err)
			}
		}
		if !entry.Delete {
			raw, exists := outputs[entry.Path]
			if !exists || fileContentSHA256(raw) != entry.AfterSHA256 {
				cleanupPreparation()
				return assetMigrationFailure("migration-prepare", fmt.Errorf("staged output mismatch: %s", entry.Path))
			}
			stage := filepath.Join(preparingRoot, fmt.Sprintf("stage-%04d", index))
			if err := atomicWriteFile(stage, raw, os.FileMode(entry.Mode)); err != nil {
				cleanupPreparation()
				return assetMigrationFailure("migration-prepare", err)
			}
		}
	}
	// Backing up and staging large media can take time. Recheck the complete
	// bounded read set and incoming-reference inventory immediately before the
	// first publication, while still under the shared transaction lock.
	latest, _, verifyErr := s.buildAssetMigrationPlan(plan.Request)
	if verifyErr != nil || latest.Digest != plan.Digest {
		cleanupPreparation()
		return assetMigrationFailure("migration-precondition", fmt.Errorf("project changed during migration preparation; no source/reference was modified"))
	}
	if err := writeAssetMigrationJournal(preparingRoot, journal); err != nil {
		cleanupPreparation()
		return assetMigrationFailure("migration-prepare", err)
	}
	if err := os.Rename(preparingRoot, journalRoot); err != nil {
		cleanupPreparation()
		return assetMigrationFailure("migration-prepare", err)
	}
	rollback := func(cause error) Envelope {
		rollbackErr := rollbackAssetMigration(root, journalRef, &journal)
		retainedRef := ""
		if rollbackErr == nil {
			var cleanupErr error
			if retainedRef, cleanupErr = retainAssetMigrationJournal(root, journalRef); cleanupErr != nil {
				rollbackErr = cleanupErr
			}
		}
		env := assetMigrationFailure("migration-apply-failed", cause)
		env.Data["rollback_complete"] = rollbackErr == nil
		if retainedRef != "" {
			env.Data["retained_journal_ref"] = retainedRef + "/journal.json"
		}
		if rollbackErr != nil {
			env.Blockers = append(env.Blockers, map[string]any{"code": "migration-rollback-incomplete", "message": rollbackErr.Error()})
			env.Data["journal_ref"] = journalRef + "/journal.json"
		}
		return env
	}
	for _, directory := range plan.CreateDirectories {
		secured, secureErr := secureProjectPath(root, directory)
		if secureErr != nil {
			return rollback(secureErr)
		}
		if _, err := os.Lstat(secured); !os.IsNotExist(err) {
			return rollback(fmt.Errorf("planned new directory is no longer absent: %s", directory))
		}
		journal.CreatedDirs = append(journal.CreatedDirs, directory)
		if err := writeAssetMigrationJournal(journalRoot, journal); err != nil {
			return rollback(err)
		}
		if err := os.Mkdir(secured, 0o755); err != nil {
			journal.CreatedDirs = journal.CreatedDirs[:len(journal.CreatedDirs)-1]
			_ = writeAssetMigrationJournal(journalRoot, journal)
			return rollback(err)
		}
	}
	for index := range journal.Entries {
		entry := journal.Entries[index]
		if err := verifyAssetMigrationBefore(root, entry); err != nil {
			return rollback(err)
		}
		if err := assetMigrationCaseCheck(root, entry.Path); err != nil {
			return rollback(err)
		}
		journal.Entries[index].Applied = true
		journal.Phase = "capturing"
		if err := writeAssetMigrationJournal(journalRoot, journal); err != nil {
			return rollback(err)
		}
		if err := assetMigrationPublish(root, journalRoot, index, entry); err != nil {
			return rollback(err)
		}
		journal.Phase = "applying"
		if err := writeAssetMigrationJournal(journalRoot, journal); err != nil {
			return rollback(err)
		}
	}
	if err := verifyAssetMigrationCaptures(root, journalRef, journal.Entries); err != nil {
		return rollback(err)
	}
	if err := verifyAssetMigrationResult(root, journal.Entries); err != nil {
		return rollback(err)
	}
	journal.Phase = "committed"
	if err := writeAssetMigrationJournal(journalRoot, journal); err != nil {
		journal.Phase = "applying"
		return rollback(err)
	}
	return assetMigrationApplied(plan, journalRef, false)
}

func (s *AssetService) assetMigrationRecoveryBoundaries(plan AssetMigrationPlan) error {
	policy, err := s.LoadPolicy(plan.Request.PolicyPath)
	if err != nil {
		return err
	}
	if len(plan.Moves) == 0 || len(plan.Moves) > assetMigrationMaxMoves || len(plan.Moves) != len(plan.Request.Moves) || len(plan.References) > assetMigrationMaxRefs+assetMigrationMaxMoves {
		return fmt.Errorf("migration plan shape exceeds its supported bounds")
	}
	mapping := map[string]string{}
	for index, move := range plan.Moves {
		if move.From != plan.Request.Moves[index].From || move.To != plan.Request.Moves[index].To {
			return fmt.Errorf("planned moves differ from their explicit request")
		}
		for _, relative := range []string{move.From, move.To} {
			if _, err := assetMigrationNormalizePath(relative); err != nil {
				return err
			}
		}
		if err := s.assetMigrationCheckClass(move.From, policy, false); err != nil {
			return err
		}
		if err := s.assetMigrationCheckClass(move.To, policy, true); err != nil {
			return err
		}
		if !assetMigrationSupportedSource(move.From) || !strings.EqualFold(path.Ext(move.From), path.Ext(move.To)) {
			return fmt.Errorf("unsupported source format in migration recovery")
		}
		for _, relative := range []string{move.From, move.To} {
			if err := assetMigrationNativeBoundary(s.projectRoot, relative); err != nil {
				return err
			}
		}
		mapping[move.From] = move.To
	}
	for _, reference := range plan.References {
		if _, err := assetMigrationNormalizePath(reference.Path); err != nil {
			return err
		}
		if err := s.assetMigrationReferenceBoundary(reference.Path, policy); err != nil {
			return err
		}
		expectedDestination := reference.Path
		if moved, exists := mapping[reference.Path]; exists {
			expectedDestination = moved
		}
		if reference.Destination != expectedDestination {
			return fmt.Errorf("reference destination differs from the explicit move map")
		}
	}
	for _, directory := range plan.CreateDirectories {
		if _, err := assetMigrationNormalizePath(directory); err != nil {
			return err
		}
		parentOfDestination := false
		for _, move := range plan.Moves {
			parentOfDestination = parentOfDestination || strings.HasPrefix(move.To, directory+"/")
		}
		if !parentOfDestination {
			return fmt.Errorf("planned directory is not a parent of a reviewed destination: %s", directory)
		}
	}
	return nil
}

func assetMigrationEntries(plan AssetMigrationPlan) []assetMigrationEntry {
	entries := []assetMigrationEntry{}
	for _, move := range plan.Moves {
		entries = append(entries,
			assetMigrationEntry{Path: move.To, AfterSHA256: move.AfterSHA256, Mode: move.Mode},
			assetMigrationEntry{Path: move.From, Existed: true, Delete: true, BeforeSHA256: move.SHA256, Mode: move.Mode})
	}
	for _, reference := range plan.References {
		if reference.Path == reference.Destination && reference.SHA256 != reference.AfterSHA256 {
			entries = append(entries, assetMigrationEntry{Path: reference.Path, Existed: true, BeforeSHA256: reference.SHA256, AfterSHA256: reference.AfterSHA256, Mode: reference.Mode})
		}
	}
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Delete != entries[j].Delete {
			return !entries[i].Delete
		}
		return entries[i].Path < entries[j].Path
	})
	for index := range entries {
		if entries[index].Existed {
			entries[index].CaptureRef = fmt.Sprintf("captured-%04d", index)
		}
		entries[index].RollbackCaptureRef = fmt.Sprintf("rollback-captured-%04d", index)
	}
	return entries
}

func assetMigrationApplied(plan AssetMigrationPlan, journalRef string, repeated bool) Envelope {
	env := NewEnvelope("ok", "Reviewed migration applied within the explicit reference scope")
	env.Data["digest"] = plan.Digest
	env.Data["coverage"] = "explicit-references-only"
	env.Data["global_references_verified"] = false
	env.Data["already_applied"] = repeated
	env.Data["journal_ref"] = journalRef + "/journal.json"
	env.Data["source_backups_ref"] = journalRef
	env.Data["moved_files"] = len(plan.Moves)
	changed := []string{}
	for _, entry := range assetMigrationEntries(plan) {
		changed = append(changed, entry.Path)
	}
	env.Data["changed_paths"] = changed
	return env
}

func verifyAssetMigrationBefore(root string, entry assetMigrationEntry) error {
	secured, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	if !entry.Existed {
		if _, err := os.Lstat(secured); os.IsNotExist(err) {
			return nil
		}
		return fmt.Errorf("destination is no longer absent: %s", entry.Path)
	}
	raw, info, err := assetMigrationRead(root, entry.Path, assetMigrationMaxFileBytes)
	if err != nil || fileContentSHA256(raw) != entry.BeforeSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
		return fmt.Errorf("source/reference content or mode changed: %s", entry.Path)
	}
	return nil
}

func publishAssetMigrationEntry(root, journalRoot string, index int, entry assetMigrationEntry) error {
	// The journal write and staging checks between the outer validation and this
	// call can be slow. Repeat the source/reference check at the mutation point
	// so a change during that interval is preserved and stops the transaction.
	if err := verifyAssetMigrationBefore(root, entry); err != nil {
		return err
	}
	target, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	stage := filepath.Join(journalRoot, fmt.Sprintf("stage-%04d", index))
	if !entry.Delete {
		raw, err := os.ReadFile(stage)
		if err != nil || fileContentSHA256(raw) != entry.AfterSHA256 {
			return fmt.Errorf("staged content is unavailable or changed for %s", entry.Path)
		}
	}
	if entry.Existed {
		before, err := os.Lstat(target)
		if err != nil {
			return err
		}
		if err := assetMigrationCapture(root, journalRoot, index, entry); err != nil {
			return err
		}
		captureRef, err := filepath.Rel(root, filepath.Join(journalRoot, entry.CaptureRef))
		if err != nil {
			return err
		}
		raw, captured, err := assetMigrationRead(root, filepath.ToSlash(captureRef), assetMigrationMaxFileBytes)
		if err != nil || !os.SameFile(before, captured) || fileContentSHA256(raw) != entry.BeforeSHA256 || uint32(captured.Mode().Perm()) != entry.Mode {
			return fmt.Errorf("captured source/reference drifted at publication; its actual version is retained in %s", entry.CaptureRef)
		}
	}
	if entry.Delete {
		return nil // Removal is the durable capture, never an unlink of the source.
	}
	// Both new destinations and rewritten references use create-only publication.
	// A file recreated after capture is preserved instead of being overwritten.
	if err := os.Link(stage, target); err != nil {
		return fmt.Errorf("cannot safely publish a destination/reference without overwrite: %s: %w", entry.Path, err)
	}
	// Break the hard-link relationship immediately; later user edits must not
	// alter a retained staged copy in the transaction journal.
	return os.Remove(stage)
}

func captureAssetMigrationEntry(root, journalRoot string, _ int, entry assetMigrationEntry) error {
	target, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	if !entry.Existed || entry.CaptureRef == "" || path.Base(entry.CaptureRef) != entry.CaptureRef {
		return fmt.Errorf("capture requires the journal's exact existing-file entry")
	}
	capture := filepath.Join(journalRoot, entry.CaptureRef)
	if _, err := os.Lstat(capture); !os.IsNotExist(err) {
		return fmt.Errorf("capture destination must be absent: %s", entry.CaptureRef)
	}
	// The private journal slot and its write-ahead intent are created under the
	// shared lock. Rename captures the actual inode, including a racing edit.
	return os.Rename(target, capture)
}

func verifyAssetMigrationCaptures(root, journalRef string, entries []assetMigrationEntry) error {
	for _, entry := range entries {
		if !entry.Existed {
			continue
		}
		raw, info, err := assetMigrationRead(root, journalRef+"/"+entry.CaptureRef, assetMigrationMaxFileBytes)
		if err != nil || fileContentSHA256(raw) != entry.BeforeSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
			return fmt.Errorf("captured original changed before commit; preserve and review %s/%s", journalRef, entry.CaptureRef)
		}
	}
	return nil
}

func retainAssetMigrationJournal(root, journalRef string) (string, error) {
	id, err := newFileTransactionID()
	if err != nil {
		return "", err
	}
	retainedRef := ".specify/runtime/asset-migrations/.retained/" + path.Base(journalRef) + "-" + id
	target, err := secureProjectPath(root, retainedRef)
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return "", err
	}
	original, err := secureProjectPath(root, journalRef)
	if err != nil {
		return "", err
	}
	if err := os.Rename(original, target); err != nil {
		return "", err
	}
	return retainedRef, nil
}

func verifyAssetMigrationResult(root string, entries []assetMigrationEntry) error {
	for _, entry := range entries {
		secured, err := secureProjectPath(root, entry.Path)
		if err != nil {
			return err
		}
		if entry.Delete {
			if _, err := os.Lstat(secured); os.IsNotExist(err) {
				continue
			}
			return fmt.Errorf("removed source unexpectedly exists: %s", entry.Path)
		}
		raw, info, err := assetMigrationRead(root, entry.Path, assetMigrationMaxFileBytes)
		if err != nil || fileContentSHA256(raw) != entry.AfterSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
			return fmt.Errorf("migration result changed: %s", entry.Path)
		}
	}
	return nil
}

func writeAssetMigrationJournal(journalRoot string, journal assetMigrationJournal) error {
	raw, err := json.Marshal(journal)
	if err != nil {
		return err
	}
	return atomicWriteFile(filepath.Join(journalRoot, "journal.json"), append(raw, '\n'), 0o600)
}

func readAssetMigrationJournal(root, journalRef string) (assetMigrationJournal, error) {
	var journal assetMigrationJournal
	raw, _, err := assetMigrationRead(root, journalRef+"/journal.json", assetMigrationMaxRefBytes)
	if err != nil {
		return journal, err
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&journal); err != nil {
		return journal, err
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		return journal, fmt.Errorf("migration journal must contain one JSON object")
	}
	return journal, nil
}

func validateAssetMigrationJournal(plan AssetMigrationPlan, journal assetMigrationJournal) error {
	if journal.SchemaVersion != 1 || journal.PlanDigest != plan.Digest || journal.ProjectRoot != plan.ProjectRoot {
		return fmt.Errorf("migration journal identity differs from the reviewed plan")
	}
	switch journal.Phase {
	case "prepared", "capturing", "applying", "rolling-back", "rolled-back", "committed":
	default:
		return fmt.Errorf("unknown migration journal phase")
	}
	expected := assetMigrationEntries(plan)
	if len(expected) != len(journal.Entries) {
		return fmt.Errorf("migration journal contains unexpected entries")
	}
	for index, entry := range journal.Entries {
		entry.Applied = false
		if entry != expected[index] {
			return fmt.Errorf("migration journal entry differs from the reviewed plan")
		}
	}
	allowedDirs := map[string]bool{}
	for _, directory := range plan.CreateDirectories {
		allowedDirs[directory] = true
	}
	seen := map[string]bool{}
	for _, directory := range journal.CreatedDirs {
		if !allowedDirs[directory] || seen[directory] {
			return fmt.Errorf("migration journal contains an unexpected created directory")
		}
		seen[directory] = true
	}
	return nil
}

func rollbackAssetMigration(root, journalRef string, journal *assetMigrationJournal) error {
	journalRoot, err := secureProjectPath(root, journalRef)
	if err != nil {
		return err
	}
	journal.Phase = "rolling-back"
	if err := writeAssetMigrationJournal(journalRoot, *journal); err != nil {
		return err
	}
	var failures []string
	for index := len(journal.Entries) - 1; index >= 0; index-- {
		entry := journal.Entries[index]
		if !entry.Applied {
			continue
		}
		if err := rollbackAssetMigrationEntry(root, journalRef, index, entry); err != nil {
			failures = append(failures, entry.Path+": "+err.Error())
			continue
		}
		journal.Entries[index].Applied = false
		if err := writeAssetMigrationJournal(journalRoot, *journal); err != nil {
			failures = append(failures, err.Error())
		}
	}
	if len(failures) > 0 {
		return fmt.Errorf("rollback incomplete; original backups remain in %s: %s", journalRef, strings.Join(failures, "; "))
	}
	for index := len(journal.CreatedDirs) - 1; index >= 0; index-- {
		secured, err := secureProjectPath(root, journal.CreatedDirs[index])
		if err != nil {
			return err
		}
		if err := os.Remove(secured); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("original files restored; cannot remove newly created directory without deleting unrelated contents: %s", journal.CreatedDirs[index])
		}
		journal.CreatedDirs = journal.CreatedDirs[:index]
		if err := writeAssetMigrationJournal(journalRoot, *journal); err != nil {
			return err
		}
	}
	journal.Phase = "rolled-back"
	return writeAssetMigrationJournal(journalRoot, *journal)
}

func rollbackAssetMigrationEntry(root, journalRef string, _ int, entry assetMigrationEntry) error {
	_, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	rollbackRef := journalRef + "/" + entry.RollbackCaptureRef
	rollbackRaw, rollbackInfo, rollbackErr := assetMigrationRead(root, rollbackRef, assetMigrationMaxFileBytes)
	rollbackCaptured := !os.IsNotExist(rollbackErr)
	if rollbackCaptured && (rollbackErr != nil || fileContentSHA256(rollbackRaw) != entry.AfterSHA256 || uint32(rollbackInfo.Mode().Perm()) != entry.Mode) {
		// A rollback rename may have captured a concurrent edit. Restore that
		// exact inode if the path is still free, and retain it in either case.
		_ = restoreAssetMigrationCapture(root, rollbackRef, entry.Path)
		return fmt.Errorf("rollback captured an unexpected version; it remains at %s and any recreated target was preserved", rollbackRef)
	}

	current, info, readErr := assetMigrationRead(root, entry.Path, assetMigrationMaxFileBytes)
	absent := os.IsNotExist(readErr)
	if readErr != nil && !absent {
		return readErr
	}
	if !entry.Existed {
		if absent {
			return nil // Either publication never ran, or rollback already captured it.
		}
		if rollbackCaptured || fileContentSHA256(current) != entry.AfterSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
			return fmt.Errorf("target changed after publication/rollback; refusing to remove unrelated content")
		}
		return captureAssetMigrationRollback(root, journalRef, entry, info)
	}

	captureRef := journalRef + "/" + entry.CaptureRef
	captured, captureInfo, captureErr := assetMigrationRead(root, captureRef, assetMigrationMaxFileBytes)
	if os.IsNotExist(captureErr) {
		// Applied is a write-ahead obligation; a crash can precede the rename.
		if !rollbackCaptured && readErr == nil && fileContentSHA256(current) == entry.BeforeSHA256 && uint32(info.Mode().Perm()) == entry.Mode {
			return nil
		}
		return fmt.Errorf("original capture is absent and the path has changed; refusing backup overwrite")
	}
	validCapture := captureErr == nil && fileContentSHA256(captured) == entry.BeforeSHA256 && uint32(captureInfo.Mode().Perm()) == entry.Mode
	if captureErr == nil && readErr == nil && os.SameFile(info, captureInfo) {
		if validCapture {
			return nil // A previous recovery already restored this exact inode.
		}
		return fmt.Errorf("restored source/reference changed; the actual captured inode remains at %s", captureRef)
	}
	if !absent {
		if entry.Delete || rollbackCaptured || fileContentSHA256(current) != entry.AfterSHA256 || uint32(info.Mode().Perm()) != entry.Mode {
			return fmt.Errorf("a source/reference was recreated or changed; preserve it and the original at %s", captureRef)
		}
		if err := captureAssetMigrationRollback(root, journalRef, entry, info); err != nil {
			return err
		}
	}
	if err := restoreAssetMigrationCapture(root, captureRef, entry.Path); err != nil {
		return fmt.Errorf("original retained at %s; create-only restore failed: %w", captureRef, err)
	}
	if !validCapture {
		return fmt.Errorf("captured content or mode changed; its actual version was restored and retained at %s", captureRef)
	}
	return nil
}

func captureAssetMigrationRollback(root, journalRef string, entry assetMigrationEntry, before os.FileInfo) error {
	target, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	captureRef := journalRef + "/" + entry.RollbackCaptureRef
	capture, err := secureProjectPath(root, captureRef)
	if err != nil {
		return err
	}
	if _, err := os.Lstat(capture); !os.IsNotExist(err) {
		return fmt.Errorf("rollback capture slot is already occupied: %s", captureRef)
	}
	if err := os.Rename(target, capture); err != nil {
		return err
	}
	raw, captured, readErr := assetMigrationRead(root, captureRef, assetMigrationMaxFileBytes)
	if readErr != nil || !os.SameFile(before, captured) || fileContentSHA256(raw) != entry.AfterSHA256 || uint32(captured.Mode().Perm()) != entry.Mode {
		_ = restoreAssetMigrationCapture(root, captureRef, entry.Path)
		return fmt.Errorf("target drifted while rollback captured it; actual version retained at %s", captureRef)
	}
	return nil
}

func restoreAssetMigrationCapture(root, captureRef, targetRef string) error {
	capture, err := secureProjectPath(root, captureRef)
	if err != nil {
		return err
	}
	target, err := secureProjectPath(root, targetRef)
	if err != nil {
		return err
	}
	info, err := os.Lstat(capture)
	if err != nil || !info.Mode().IsRegular() {
		return fmt.Errorf("captured entry cannot be automatically restored; inspect %s", captureRef)
	}
	if current, err := os.Lstat(target); err == nil {
		if os.SameFile(info, current) {
			return nil
		}
		return fmt.Errorf("target was recreated; refusing to overwrite %s", targetRef)
	} else if !os.IsNotExist(err) {
		return err
	}
	// Linking is create-only and restores the captured inode itself. Bytes added
	// through a pre-existing file descriptor remain reachable after recovery.
	return os.Link(capture, target)
}

func assetMigrationCheckPending(root, currentDigest string) error {
	base, err := secureProjectPath(root, ".specify/runtime/asset-migrations")
	if err != nil {
		return err
	}
	directory, err := os.Open(base)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	defer directory.Close()
	entries, err := directory.ReadDir(1025)
	if err != nil && err != io.EOF {
		return err
	}
	if len(entries) > 1024 {
		return fmt.Errorf("migration journal inventory exceeds its bounded limit; archive reviewed committed journals before applying more migrations")
	}
	for _, entry := range entries {
		if entry.Name() == ".preparing" || entry.Name() == ".retained" || entry.Name() == currentDigest {
			continue
		}
		if !entry.IsDir() || entry.Type()&os.ModeSymlink != 0 {
			return fmt.Errorf("unexpected migration journal entry: %s", entry.Name())
		}
		journal, err := readAssetMigrationJournal(root, ".specify/runtime/asset-migrations/"+entry.Name())
		if err != nil || journal.SchemaVersion != 1 || journal.PlanDigest != entry.Name() || journal.ProjectRoot != filepath.ToSlash(root) {
			return fmt.Errorf("unreadable or invalid prior migration journal: %s", entry.Name())
		}
		if journal.Phase != "committed" && journal.Phase != "rolled-back" {
			return fmt.Errorf("resume the exact reviewed plan for pending migration %s before starting another", entry.Name())
		}
	}
	return nil
}
