package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"
)

const (
	assetDefaultPolicyPath    = ".asset-policy.json"
	assetDefaultTemporaryRoot = ".specify/tmp/assets"
	assetMaxPolicyBytes       = 256 * 1024
	assetMaxContentBytes      = 2 * 1024 * 1024
	assetMaxCheckPaths        = 1000
)

// AssetService provides read-only placement and validation. Ordinary assets do
// not become workflow artifacts, acquire leases, or create workflow state.
type AssetService struct{ projectRoot string }

func NewAssetService(projectRoot string) *AssetService {
	return &AssetService{projectRoot: projectRoot}
}

// Omitted policy fields use built-in conventions. User lists extend, rather
// than replace, ownership boundaries and conventional filename exceptions.
type AssetPolicy struct {
	SchemaVersion      int               `json:"schema_version"`
	Roots              map[string]string `json:"roots,omitempty"`
	TemporaryRoot      string            `json:"temporary_root,omitempty"`
	TemporaryRetention string            `json:"temporary_retention,omitempty"`
	SourceRoots        []string          `json:"source_roots,omitempty"`
	ProtectedRoots     []string          `json:"protected_roots,omitempty"`
	FixedNames         []string          `json:"fixed_names,omitempty"`
	AllowedRootFiles   []string          `json:"allowed_root_files,omitempty"`
	AssetKit           AssetKitPolicy    `json:"assetkit,omitempty"`
	PolicyPath         string            `json:"-"`
}

type AssetIssue struct {
	Path       string `json:"path"`
	Code       string `json:"code"`
	Message    string `json:"message"`
	Dependency string `json:"dependency,omitempty"`
}

type AssetClassification struct {
	Path      string       `json:"path"`
	Purpose   string       `json:"purpose,omitempty"`
	Kind      string       `json:"kind"`
	Owner     string       `json:"owner,omitempty"`
	TypeID    string       `json:"type_id,omitempty"`
	RuleID    string       `json:"rule_id"`
	Protected bool         `json:"protected"`
	Temporary bool         `json:"temporary"`
	Cache     bool         `json:"cache"`
	Compliant bool         `json:"compliant"`
	Issues    []AssetIssue `json:"issues"`
}

var assetPurposeRoots = map[string][]string{
	"architecture": {"docs/architecture", "docs/design", "doc/architecture", "documentation/architecture"},
	"decision":     {"docs/decisions", "docs/adr", "doc/decisions", "decisions"},
	"guide":        {"docs/guides", "docs/how-to", "docs/guide", "doc/guides", "documentation/guides"},
	"reference":    {"docs/reference", "docs/references", "doc/reference", "documentation/reference"},
	"report":       {"docs/reports", "reports", "docs/research"},
	"asset":        {"assets", "docs/assets", "public", "static", "images", "media"},
}

var assetBuiltInSourceRoots = []string{
	"src", "source", "lib", "app", "apps", "packages", "tools", "scripts",
	"tests", "test", "templates", "fixtures", "testdata", "examples", "extensions",
}

var assetBuiltInProtectedRoots = []string{
	".git", ".assets", ".specify", ".planning", "specs", ".claude", ".codex",
	".agents", ".agent", ".cursor", ".gemini", ".opencode", ".github", ".githooks",
	".husky", ".idea", ".vscode", ".windsurf", ".roo", ".kilocode", ".kiro",
}

var assetCacheSegments = map[string]bool{
	"node_modules": true, ".venv": true, "venv": true, "__pycache__": true,
	".cache": true, ".pytest_cache": true, ".ruff_cache": true, ".mypy_cache": true,
	".next": true, ".nuxt": true, "coverage": true, "dist": true, "build": true, "target": true,
}

var assetFixedNames = []string{
	"README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONTRIBUTING.md",
	"CHANGELOG.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "CODEOWNERS", "LICENSE",
	"LICENSE.md", "NOTICE", "NOTICE.md", "AUTHORS", "AUTHORS.md", "PROJECT-HANDBOOK.md",
	"SKILL.md", "Dockerfile", "Containerfile", "Makefile", "CMakeLists.txt", "Justfile",
	"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock",
	"pyproject.toml", "uv.lock", "requirements.txt", "go.mod", "go.sum", "Cargo.toml",
	"Cargo.lock", "composer.json", "composer.lock", "Gemfile", "Gemfile.lock",
	".gitignore", ".gitattributes", ".gitmodules", ".editorconfig", ".pre-commit-config.yaml",
	assetDefaultPolicyPath,
}

var assetKebabName = regexp.MustCompile(`^[a-z0-9]+(?:-[a-z0-9]+)*$`)
var assetConventionalReadme = regexp.MustCompile(`^README(?:\.[A-Za-z0-9-]+)*\.md$`)
var assetADRName = regexp.MustCompile(`^[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*$`)
var assetDatePrefix = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}-`)
var assetRetention = regexp.MustCompile(`^[1-9][0-9]{0,2}d$`)
var assetProcessFilename = regexp.MustCompile(`(?i)^(?:plan|todo|notes|summary|report|progress|audit|final[-_]report|implementation[-_]summary|test[-_]results)(?:[-_].*)?\.(?:txt|json|jsonl|csv|tsv|yaml|yml)$`)
var assetWindowsDeviceName = regexp.MustCompile(`(?i)^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)`)

func defaultAssetPolicy() AssetPolicy {
	return AssetPolicy{SchemaVersion: 1, Roots: map[string]string{}, TemporaryRoot: assetDefaultTemporaryRoot,
		TemporaryRetention: "7d", PolicyPath: "builtin"}
}

func (service *AssetService) LoadPolicy(policyPath string) (AssetPolicy, error) {
	policy := defaultAssetPolicy()
	explicit := policyPath != ""
	if !explicit {
		policyPath = assetDefaultPolicyPath
	}
	relative, err := assetNormalizePath(policyPath)
	if err != nil {
		return policy, fmt.Errorf("invalid asset policy path: %w", err)
	}
	absolute, err := secureProjectPath(service.projectRoot, relative)
	if err != nil {
		return policy, fmt.Errorf("asset policy boundary: %w", err)
	}
	raw, err := assetReadLimitedFile(absolute, assetMaxPolicyBytes)
	if os.IsNotExist(err) && !explicit {
		return policy, nil
	}
	if err != nil {
		return policy, fmt.Errorf("read asset policy: %w", err)
	}
	return decodeAssetPolicy(raw, relative)
}

func decodeAssetPolicy(raw []byte, policyPath string) (AssetPolicy, error) {
	policy := defaultAssetPolicy()
	if !utf8.Valid(raw) {
		return policy, fmt.Errorf("asset policy must be UTF-8 JSON")
	}
	if err := assetRejectDuplicateJSONKeys(raw); err != nil {
		return policy, err
	}
	var supplied AssetPolicy
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&supplied); err != nil {
		return policy, fmt.Errorf("decode asset policy: %w", err)
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		return policy, fmt.Errorf("asset policy must contain one JSON object")
	}
	if supplied.SchemaVersion != 1 {
		return policy, fmt.Errorf("asset policy schema_version must be 1")
	}
	if supplied.Roots != nil {
		policy.Roots = supplied.Roots
	}
	if supplied.TemporaryRoot != "" {
		policy.TemporaryRoot = supplied.TemporaryRoot
	}
	if supplied.TemporaryRetention != "" {
		policy.TemporaryRetention = supplied.TemporaryRetention
	}
	policy.SourceRoots = supplied.SourceRoots
	policy.ProtectedRoots = supplied.ProtectedRoots
	policy.FixedNames = supplied.FixedNames
	policy.AllowedRootFiles = supplied.AllowedRootFiles
	policy.AssetKit = supplied.AssetKit
	policy.PolicyPath = policyPath
	if err := validateAssetPolicy(policy); err != nil {
		return defaultAssetPolicy(), err
	}
	return policy, nil
}

func validateAssetPolicy(policy AssetPolicy) error {
	if policy.TemporaryRetention != "session" && !assetRetention.MatchString(policy.TemporaryRetention) {
		return fmt.Errorf("temporary_retention must be session or a positive number of days such as 7d")
	}
	for purpose, root := range policy.Roots {
		if _, ok := assetPurposeRoots[purpose]; !ok {
			return fmt.Errorf("unsupported asset purpose %q in roots", purpose)
		}
		normalized, err := assetNormalizePath(root)
		if err != nil || normalized != root {
			return fmt.Errorf("asset root %q must be a normalized project-relative directory", root)
		}
		for _, protected := range append(append([]string{}, assetBuiltInProtectedRoots...), policy.ProtectedRoots...) {
			if assetUnder(strings.ToLower(root), strings.ToLower(protected)) || assetUnder(strings.ToLower(protected), strings.ToLower(root)) {
				return fmt.Errorf("asset root %q overlaps protected root %q", root, protected)
			}
		}
		for _, source := range append(append([]string{}, assetBuiltInSourceRoots...), policy.SourceRoots...) {
			if assetPathsOverlap(root, source) {
				return fmt.Errorf("asset root %q overlaps source root %q", root, source)
			}
		}
		for otherPurpose, otherRoot := range policy.Roots {
			if otherPurpose != purpose && strings.EqualFold(root, otherRoot) {
				return fmt.Errorf("asset purposes %s and %s cannot share the same explicit root", purpose, otherPurpose)
			}
		}
	}
	temporary, err := assetNormalizePath(policy.TemporaryRoot)
	if err != nil || temporary != policy.TemporaryRoot {
		return fmt.Errorf("temporary_root must be a normalized project-relative directory")
	}
	for _, protected := range assetBuiltInProtectedRoots {
		if assetUnder(strings.ToLower(temporary), strings.ToLower(protected)) || assetUnder(strings.ToLower(protected), strings.ToLower(temporary)) {
			if protected == ".specify" && assetUnder(temporary, assetDefaultTemporaryRoot) {
				continue
			}
			return fmt.Errorf("temporary_root overlaps protected root %q", protected)
		}
	}
	for _, source := range append(append([]string{}, assetBuiltInSourceRoots...), policy.SourceRoots...) {
		if assetPathsOverlap(temporary, source) {
			return fmt.Errorf("temporary_root overlaps source root %q", source)
		}
	}
	for _, roots := range assetPurposeRoots {
		for _, root := range roots {
			if assetPathsOverlap(root, temporary) {
				return fmt.Errorf("temporary_root overlaps persistent asset root %q", root)
			}
		}
	}
	for _, root := range policy.Roots {
		if assetPathsOverlap(root, temporary) {
			return fmt.Errorf("temporary_root overlaps persistent asset root %q", root)
		}
	}
	for _, root := range append(append([]string{}, policy.SourceRoots...), policy.ProtectedRoots...) {
		if normalized, err := assetNormalizePath(root); err != nil || normalized != root {
			return fmt.Errorf("policy root %q must be normalized and project-relative", root)
		}
		if assetPathsOverlap(temporary, root) {
			return fmt.Errorf("policy root %q overlaps temporary_root", root)
		}
	}
	for _, name := range append(append([]string{}, policy.FixedNames...), policy.AllowedRootFiles...) {
		if normalized, err := assetNormalizePath(name); err != nil || normalized != name || strings.Contains(name, "/") {
			return fmt.Errorf("filename exception %q must be an exact basename", name)
		}
	}
	return nil
}

// Reject duplicate keys instead of silently accepting whichever policy value
// happened to appear last. This also rejects trailing JSON values.
func assetRejectDuplicateJSONKeys(raw []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(raw))
	var value func() error
	value = func() error {
		token, err := decoder.Token()
		if err != nil {
			return err
		}
		delimiter, composite := token.(json.Delim)
		if !composite {
			return nil
		}
		switch delimiter {
		case '{':
			seen := map[string]bool{}
			for decoder.More() {
				keyToken, err := decoder.Token()
				if err != nil {
					return err
				}
				key, ok := keyToken.(string)
				if !ok {
					return fmt.Errorf("asset policy has invalid object key")
				}
				if seen[key] {
					return fmt.Errorf("asset policy contains duplicate key %q", key)
				}
				seen[key] = true
				if err := value(); err != nil {
					return err
				}
			}
		case '[':
			for decoder.More() {
				if err := value(); err != nil {
					return err
				}
			}
		default:
			return fmt.Errorf("invalid asset policy JSON delimiter")
		}
		_, err = decoder.Token()
		return err
	}
	if err := value(); err != nil {
		return fmt.Errorf("invalid asset policy JSON: %w", err)
	}
	if _, err := decoder.Token(); err != io.EOF {
		return fmt.Errorf("asset policy must contain one JSON value")
	}
	return nil
}

func assetNormalizePath(relative string) (string, error) {
	if relative == "" || strings.TrimSpace(relative) != relative || !utf8.ValidString(relative) {
		return "", fmt.Errorf("path must be nonempty UTF-8 without surrounding whitespace")
	}
	if strings.ContainsAny(relative, "\\:") || strings.HasPrefix(relative, "/") || filepath.IsAbs(relative) || filepath.VolumeName(relative) != "" {
		return "", fmt.Errorf("path must be project-relative and use forward slashes")
	}
	for _, char := range relative {
		if unicode.IsControl(char) {
			return "", fmt.Errorf("path must not contain control characters")
		}
	}
	for _, part := range strings.Split(relative, "/") {
		if part == ".." {
			return "", fmt.Errorf("path must not traverse parent directories")
		}
		if part != "." && (strings.HasSuffix(part, ".") || strings.HasSuffix(part, " ") || assetWindowsDeviceName.MatchString(part)) {
			return "", fmt.Errorf("path contains a nonportable trailing dot/space or reserved device name")
		}
	}
	normalized := path.Clean(relative)
	if normalized == "." || normalized == ".." || strings.HasPrefix(normalized, "../") {
		return "", fmt.Errorf("path must name an item inside the project")
	}
	return normalized, nil
}

func assetReadLimitedFile(absolute string, limit int64) ([]byte, error) {
	file, err := os.Open(absolute)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() {
		return nil, fmt.Errorf("path must name a regular file")
	}
	if info.Size() > limit {
		return nil, fmt.Errorf("file exceeds %d byte inspection limit", limit)
	}
	raw, err := io.ReadAll(io.LimitReader(file, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(raw)) > limit {
		return nil, fmt.Errorf("file exceeds %d byte inspection limit", limit)
	}
	return raw, nil
}

func assetUnder(relative, root string) bool {
	return relative == root || strings.HasPrefix(relative, root+"/")
}

// Policy directories must not rely on case differences to separate owners or
// persistent and temporary output on case-insensitive filesystems.
func assetPathsOverlap(left, right string) bool {
	left, right = strings.ToLower(left), strings.ToLower(right)
	return assetUnder(left, right) || assetUnder(right, left)
}

func (service *AssetService) ClassifyPath(relative string, policy AssetPolicy) (AssetClassification, error) {
	normalized, err := assetNormalizePath(relative)
	if err != nil {
		return AssetClassification{}, err
	}
	if _, err := secureProjectPath(service.projectRoot, normalized); err != nil {
		return AssetClassification{}, err
	}
	classification := classifyAssetPath(normalized, policy)
	if err := assetCheckFilesystemCase(service.projectRoot, normalized); err != nil {
		classification.Issues = append(classification.Issues, AssetIssue{Path: normalized, Code: "case-conflict", Message: err.Error()})
		classification.Compliant = false
	}
	return classification, nil
}

func classifyAssetPath(relative string, policy AssetPolicy) AssetClassification {
	classification := AssetClassification{Path: relative, Kind: "other", RuleID: "unmanaged-file", Compliant: true, Issues: []AssetIssue{}}
	if metadata, found := LookupArtifactType(relative); found {
		classification.Kind = "workflow-artifact"
		classification.Protected = true
		classification.Owner = metadata.Owner
		classification.TypeID = metadata.TypeID
		classification.RuleID = "artifact-registry"
		return classification
	}
	if relative == assetDefaultPolicyPath || relative == policy.PolicyPath {
		classification.Kind = "configuration"
		classification.Protected = true
		classification.Owner = "project asset policy"
		classification.RuleID = "asset-policy"
		return classification
	}
	if assetUnder(relative, policy.TemporaryRoot) {
		classification.Kind = "temporary"
		classification.Purpose = "temporary"
		classification.Temporary = true
		classification.RuleID = "temporary-scope"
		parts := strings.Split(strings.TrimPrefix(relative, policy.TemporaryRoot+"/"), "/")
		if len(parts) < 3 || !safeSegment(parts[0]) || !safeSegment(parts[1]) {
			classification.Issues = append(classification.Issues, AssetIssue{Path: relative, Code: "temporary-scope", Message: "temporary assets require task and worker directories below temporary_root"})
		}
		assetValidateBasename(&classification, policy)
		classification.Compliant = len(classification.Issues) == 0
		return classification
	}
	for _, root := range append(append([]string{}, assetBuiltInProtectedRoots...), policy.ProtectedRoots...) {
		if assetUnder(strings.ToLower(relative), strings.ToLower(root)) {
			classification.Kind = "protected"
			classification.Protected = true
			classification.Owner = "project/tool owner"
			classification.RuleID = "protected-root"
			if root == ".specify" || root == ".planning" || root == "specs" {
				classification.Owner = "specify-runtime artifact/state owner"
			}
			if assetContains([]string{".github", ".githooks", ".husky", ".vscode", ".idea"}, root) {
				classification.Kind = "configuration"
				classification.RuleID = "project-tool-configuration"
			}
			return classification
		}
	}
	basename := path.Base(relative)
	for _, root := range append(append([]string{}, assetBuiltInSourceRoots...), policy.SourceRoots...) {
		if assetUnder(relative, root) {
			classification.Kind = "source"
			classification.Purpose = "source"
			classification.RuleID = "native-source-root"
			return classification
		}
	}
	for _, segment := range strings.Split(relative, "/") {
		if segment == "templates" || segment == "fixtures" || segment == "__fixtures__" || segment == "testdata" || segment == "__snapshots__" {
			classification.Kind = "source"
			classification.Purpose = "source"
			classification.RuleID = "native-template-fixture"
			return classification
		}
	}
	if canonicalName := assetCanonicalControlName(basename); canonicalName != "" {
		classification.Kind = "configuration"
		classification.Protected = true
		classification.Owner = "project/integration owner"
		classification.RuleID = "project-control-file"
		if basename != canonicalName {
			classification.Compliant = false
			classification.Issues = append(classification.Issues, AssetIssue{Path: relative, Code: "fixed-filename-case", Message: "preserve the conventional filename casing: " + canonicalName})
		}
		return classification
	}
	for _, part := range strings.Split(relative, "/") {
		if assetCacheSegments[part] {
			classification.Kind = "cache"
			classification.Cache = true
			classification.Protected = true
			classification.Owner = "project build/tool cache"
			classification.RuleID = "tool-cache"
			return classification
		}
	}
	bestRoot := ""
	for _, purpose := range sortedAssetPurposes() {
		roots := assetPurposeRoots[purpose]
		candidates := append([]string{}, roots...)
		if root, ok := policy.Roots[purpose]; ok {
			candidates = append(candidates, root)
		}
		for _, root := range candidates {
			if assetUnder(relative, root) && (len(root) > len(bestRoot) || (len(root) == len(bestRoot) && root == policy.Roots[purpose])) {
				bestRoot = root
				classification.Purpose = purpose
				classification.RuleID = "purpose-root:" + purpose
			}
		}
	}
	extension := strings.ToLower(path.Ext(relative))
	switch {
	case assetIsMediaExtension(extension):
		classification.Kind = "media"
		if classification.Purpose == "" {
			classification.Purpose = "asset"
		}
	case extension == ".md" || extension == ".markdown" || extension == ".mdx" || extension == ".rst":
		classification.Kind = "document"
		if classification.Purpose == "" {
			classification.Purpose = "guide"
		}
	case classification.Purpose == "report":
		classification.Kind = "document"
	case !strings.Contains(relative, "/") && assetProcessFilename.MatchString(basename) && !assetIsFixedName(basename, policy):
		classification.Kind = "document"
		classification.Purpose = "report"
		classification.RuleID = "root-process-artifact"
	default:
		return classification
	}
	if !strings.Contains(relative, "/") && !assetIsFixedName(basename, policy) && !assetContains(policy.AllowedRootFiles, basename) {
		classification.Issues = append(classification.Issues, AssetIssue{Path: relative, Code: "root-artifact", Message: "ordinary documents and media belong in an existing project asset/document directory; route the asset before writing"})
	}
	if strings.Contains(relative, "/") && bestRoot == "" {
		knownLocation := false
		for _, root := range []string{"docs", "doc", "documentation", "plans", "design"} {
			if assetUnder(relative, root) {
				knownLocation = true
				break
			}
		}
		if !knownLocation {
			classification.Issues = append(classification.Issues, AssetIssue{Path: relative, Code: "asset-location", Message: "asset location is not a known project document/media directory; declare its purpose root in the asset policy"})
		}
	}
	assetValidateBasename(&classification, policy)
	classification.Compliant = len(classification.Issues) == 0
	return classification
}

func assetValidateBasename(classification *AssetClassification, policy AssetPolicy) {
	basename := path.Base(classification.Path)
	if assetIsFixedName(basename, policy) || (!strings.Contains(classification.Path, "/") && assetContains(policy.AllowedRootFiles, basename)) {
		return
	}
	extension := path.Ext(basename)
	stem := strings.TrimSuffix(basename, extension)
	if !assetKebabName.MatchString(stem) || extension != strings.ToLower(extension) {
		classification.Issues = append(classification.Issues, AssetIssue{Path: classification.Path, Code: "filename-style", Message: "ordinary asset filenames must use lower-case kebab-case; preserve owner-defined fixed filenames"})
	}
}

func assetCanonicalControlName(name string) string {
	for _, canonical := range []string{"AGENTS.md", "CLAUDE.md", "GEMINI.md", "SKILL.md", "CODEOWNERS", assetDefaultPolicyPath} {
		if strings.EqualFold(name, canonical) {
			return canonical
		}
	}
	return ""
}

func assetIsFixedName(name string, policy AssetPolicy) bool {
	return assetContains(assetFixedNames, name) || assetContains(policy.FixedNames, name) || assetConventionalReadme.MatchString(name)
}

func assetContains(values []string, value string) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}
	return false
}

func assetIsMediaExtension(extension string) bool {
	return assetContains([]string{".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".svg", ".ico", ".pdf", ".mp4", ".webm", ".mov", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".woff", ".woff2", ".ttf", ".otf", ".pptx", ".docx", ".xlsx"}, extension)
}

func assetCheckFilesystemCase(projectRoot, relative string) error {
	root, err := secureProjectPath(projectRoot, "")
	if err != nil {
		return err
	}
	current := root
	for _, component := range strings.Split(relative, "/") {
		entries, err := assetReadDirectory(current, 20000)
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		for _, entry := range entries {
			if strings.EqualFold(entry.Name(), component) && entry.Name() != component {
				return fmt.Errorf("path component %q collides with existing %q", component, entry.Name())
			}
		}
		current = filepath.Join(current, component)
	}
	return nil
}

func assetReadDirectory(absolute string, limit int) ([]os.DirEntry, error) {
	directory, err := os.Open(absolute)
	if err != nil {
		return nil, err
	}
	defer directory.Close()
	entries, err := directory.ReadDir(limit + 1)
	if err != nil && err != io.EOF {
		return nil, err
	}
	if len(entries) > limit {
		return nil, fmt.Errorf("directory exceeds %d entry inspection limit", limit)
	}
	return entries, nil
}

func sortedAssetPurposes() []string {
	purposes := make([]string, 0, len(assetPurposeRoots))
	for purpose := range assetPurposeRoots {
		purposes = append(purposes, purpose)
	}
	sort.Strings(purposes)
	return purposes
}
