package main

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

type fileTransactionUpdate struct {
	Path    string
	Content []byte
	Perm    os.FileMode
}

type fileTransactionPrecondition struct {
	Path           string
	ExpectedSHA256 string
	MustNotExist   bool
}

type fileTransactionReceipt struct {
	TransactionID string   `json:"transaction_id"`
	Kind          string   `json:"kind"`
	ChangedPaths  []string `json:"changed_paths"`
	ReceiptRef    string   `json:"receipt_ref"`
}

type fileTransactionEntry struct {
	Path         string `json:"path"`
	Existed      bool   `json:"existed"`
	BeforeSHA256 string `json:"before_sha256,omitempty"`
	AfterSHA256  string `json:"after_sha256"`
	StageRef     string `json:"stage_ref"`
	BackupRef    string `json:"backup_ref,omitempty"`
	// Applied is a write-ahead rollback obligation: the target may have changed.
	// Existing v1 journals with post-write Applied flags remain recoverable.
	Applied bool `json:"applied"`
}

type fileTransactionJournal struct {
	Version       int                    `json:"version"`
	TransactionID string                 `json:"transaction_id"`
	Kind          string                 `json:"kind"`
	Phase         string                 `json:"phase"`
	Entries       []fileTransactionEntry `json:"entries"`
}

var promoteTransactionFile = atomicWriteFile

func applyFileTransaction(projectRoot, kind string, updates []fileTransactionUpdate) (fileTransactionReceipt, error) {
	return applyFileTransactionWithPreconditions(projectRoot, kind, updates, nil)
}

func applyFileTransactionWithPreconditions(projectRoot, kind string, updates []fileTransactionUpdate, preconditions []fileTransactionPrecondition) (fileTransactionReceipt, error) {
	return applyFileTransactionWithVerification(projectRoot, kind, updates, preconditions, nil)
}

// verify is a read-only check of non-file predicates (for example directory
// membership in a frozen source fingerprint). It runs under the transaction
// lock after digest CAS and before any publication. Existing callers use nil.
func applyFileTransactionWithVerification(projectRoot, kind string, updates []fileTransactionUpdate, preconditions []fileTransactionPrecondition, verify func() error) (fileTransactionReceipt, error) {
	var receipt fileTransactionReceipt
	root, err := filepath.Abs(projectRoot)
	if err != nil {
		return receipt, err
	}
	kind = strings.TrimSpace(kind)
	if kind == "" {
		return receipt, fmt.Errorf("file transaction kind is required")
	}
	if len(updates) == 0 {
		return receipt, fmt.Errorf("file transaction requires at least one update")
	}

	type normalizedUpdate struct {
		path    string
		rel     string
		content []byte
		perm    os.FileMode
	}
	normalized := make([]normalizedUpdate, 0, len(updates))
	seen := map[string]bool{}
	for _, update := range updates {
		target, err := filepath.Abs(update.Path)
		if err != nil {
			return receipt, err
		}
		relative, err := filepath.Rel(root, target)
		if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			return receipt, fmt.Errorf("file transaction target must stay inside the project: %s", update.Path)
		}
		relative = filepath.ToSlash(relative)
		if relative == ".git" || strings.HasPrefix(relative, ".git/") {
			return receipt, fmt.Errorf("file transactions cannot mutate .git")
		}
		if seen[relative] {
			return receipt, fmt.Errorf("file transaction contains duplicate target: %s", relative)
		}
		seen[relative] = true
		secured, err := secureProjectPath(root, relative)
		if err != nil {
			return receipt, err
		}
		perm := update.Perm
		if perm == 0 {
			perm = 0o644
		}
		normalized = append(normalized, normalizedUpdate{path: secured, rel: relative, content: append([]byte(nil), update.Content...), perm: perm})
	}
	sort.Slice(normalized, func(i, j int) bool { return normalized[i].rel < normalized[j].rel })
	type normalizedPrecondition struct {
		path           string
		rel            string
		expectedSHA256 string
		mustNotExist   bool
	}
	normalizedPreconditions := make([]normalizedPrecondition, 0, len(preconditions))
	seenPreconditions := map[string]bool{}
	for _, precondition := range preconditions {
		target, err := filepath.Abs(precondition.Path)
		if err != nil {
			return receipt, err
		}
		relative, err := filepath.Rel(root, target)
		if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			return receipt, fmt.Errorf("file transaction precondition must stay inside the project: %s", precondition.Path)
		}
		relative = filepath.ToSlash(relative)
		if seenPreconditions[relative] {
			return receipt, fmt.Errorf("file transaction contains duplicate precondition: %s", relative)
		}
		seenPreconditions[relative] = true
		secured, err := secureProjectPath(root, relative)
		if err != nil {
			return receipt, err
		}
		digest := strings.ToLower(strings.TrimSpace(precondition.ExpectedSHA256))
		if precondition.MustNotExist == (digest != "") {
			return receipt, fmt.Errorf("file transaction precondition for %s must require exactly one of an expected digest or absence", relative)
		}
		if digest != "" {
			decoded, decodeErr := hex.DecodeString(digest)
			if decodeErr != nil || len(decoded) != sha256.Size {
				return receipt, fmt.Errorf("file transaction precondition for %s has an invalid sha256 digest", relative)
			}
		}
		normalizedPreconditions = append(normalizedPreconditions, normalizedPrecondition{
			path: secured, rel: relative, expectedSHA256: digest, mustNotExist: precondition.MustNotExist,
		})
	}
	sort.Slice(normalizedPreconditions, func(i, j int) bool { return normalizedPreconditions[i].rel < normalizedPreconditions[j].rel })

	lockPath, err := secureProjectPath(root, ".specify/runtime/locks/file-transactions.lock")
	if err != nil {
		return receipt, err
	}
	if err := os.MkdirAll(filepath.Dir(lockPath), 0o755); err != nil {
		return receipt, err
	}
	release, err := filelock.Acquire(lockPath)
	if err != nil {
		return receipt, err
	}
	defer release()
	if err := recoverFileTransactionsLocked(root); err != nil {
		return receipt, err
	}
	// Re-resolve after acquiring the transaction lock. This closes the window
	// between normalization and mutation and rejects Windows junction/reparse
	// parents just like symlink parents.
	for index := range normalized {
		secured, secureErr := secureProjectPath(root, normalized[index].rel)
		if secureErr != nil {
			return receipt, secureErr
		}
		normalized[index].path = secured
	}
	for index := range normalizedPreconditions {
		secured, secureErr := secureProjectPath(root, normalizedPreconditions[index].rel)
		if secureErr != nil {
			return receipt, secureErr
		}
		normalizedPreconditions[index].path = secured
	}
	for _, precondition := range normalizedPreconditions {
		current, readErr := os.ReadFile(precondition.path)
		if precondition.mustNotExist {
			if readErr == nil {
				return receipt, fmt.Errorf("file transaction precondition failed for %s: expected the path to be absent", precondition.rel)
			}
			if !os.IsNotExist(readErr) {
				return receipt, fmt.Errorf("file transaction precondition failed for %s: %w", precondition.rel, readErr)
			}
			continue
		}
		if readErr != nil {
			return receipt, fmt.Errorf("file transaction precondition failed for %s: expected an existing file: %w", precondition.rel, readErr)
		}
		actual := fileContentSHA256(current)
		if actual != precondition.expectedSHA256 {
			return receipt, fmt.Errorf("file transaction precondition failed for %s: expected sha256 %s but found %s", precondition.rel, precondition.expectedSHA256, actual)
		}
	}
	if verify != nil {
		if err := verify(); err != nil {
			return receipt, fmt.Errorf("file transaction verification failed: %w", err)
		}
	}

	transactionID, err := newFileTransactionID()
	if err != nil {
		return receipt, err
	}
	txRef := filepath.ToSlash(filepath.Join(".specify", "runtime", "transactions", transactionID))
	publishedRoot, err := secureProjectPath(root, txRef)
	if err != nil {
		return receipt, err
	}
	// Preparation is not an active transaction. Publish the directory only
	// after its staged bytes, backups, and prepared journal are all durable.
	// A process interrupted while preparing must not leave a journal-less
	// active transaction that blocks every subsequent workflow mutation.
	preparingRef := filepath.ToSlash(filepath.Join(".specify", "runtime", "transactions", ".preparing", transactionID))
	txRoot, err := secureProjectPath(root, preparingRef)
	if err != nil {
		return receipt, err
	}
	if err := os.MkdirAll(txRoot, 0o755); err != nil {
		return receipt, err
	}
	journalPath := filepath.Join(txRoot, "journal.json")
	journal := fileTransactionJournal{Version: 1, TransactionID: transactionID, Kind: kind, Phase: "preparing"}

	cleanup := func() { _ = os.RemoveAll(txRoot) }
	for _, update := range normalized {
		entry := fileTransactionEntry{
			Path:        update.rel,
			AfterSHA256: fileContentSHA256(update.content),
			StageRef:    filepath.ToSlash(filepath.Join("stage", update.rel)),
		}
		current, readErr := os.ReadFile(update.path)
		switch {
		case readErr == nil:
			entry.Existed = true
			entry.BeforeSHA256 = fileContentSHA256(current)
			entry.BackupRef = filepath.ToSlash(filepath.Join("backup", update.rel))
			backupPath := filepath.Join(txRoot, filepath.FromSlash(entry.BackupRef))
			if err := os.MkdirAll(filepath.Dir(backupPath), 0o755); err != nil {
				cleanup()
				return receipt, err
			}
			if err := atomicWriteFile(backupPath, current, update.perm); err != nil {
				cleanup()
				return receipt, err
			}
		case os.IsNotExist(readErr):
		case readErr != nil:
			cleanup()
			return receipt, readErr
		}
		stagePath := filepath.Join(txRoot, filepath.FromSlash(entry.StageRef))
		if err := os.MkdirAll(filepath.Dir(stagePath), 0o755); err != nil {
			cleanup()
			return receipt, err
		}
		if err := atomicWriteFile(stagePath, update.content, update.perm); err != nil {
			cleanup()
			return receipt, err
		}
		journal.Entries = append(journal.Entries, entry)
	}
	journal.Phase = "prepared"
	if err := writeFileTransactionJournal(journalPath, journal); err != nil {
		cleanup()
		return receipt, err
	}
	if err := replaceFile(txRoot, publishedRoot); err != nil {
		cleanup()
		return receipt, fmt.Errorf("publish prepared file transaction: %w", err)
	}
	txRoot = publishedRoot
	journalPath = filepath.Join(txRoot, "journal.json")
	rollback := func(cause error) error {
		rollbackErr := rollbackFileTransaction(root, txRoot, journal)
		if rollbackErr == nil {
			cleanup()
		}
		return combineFileTransactionErrors(cause, rollbackErr)
	}

	for index, update := range normalized {
		secured, secureErr := secureProjectPath(root, update.rel)
		if secureErr != nil {
			return receipt, rollback(secureErr)
		}
		update.path = secured
		if err := os.MkdirAll(filepath.Dir(update.path), 0o755); err != nil {
			return receipt, rollback(err)
		}
		// Persist the recovery obligation before replacing the target. A crash
		// after replacement must not leave recovery unaware of the changed file.
		journal.Entries[index].Applied = true
		journal.Phase = "applying"
		if err := writeFileTransactionJournal(journalPath, journal); err != nil {
			return receipt, rollback(err)
		}
		if err := promoteTransactionFile(update.path, update.content, update.perm); err != nil {
			return receipt, rollback(err)
		}
	}
	journal.Phase = "committed"
	if err := writeFileTransactionJournal(journalPath, journal); err != nil {
		journal.Phase = "applying"
		return receipt, rollback(err)
	}

	receipt = fileTransactionReceipt{
		TransactionID: transactionID,
		Kind:          kind,
		ReceiptRef:    filepath.ToSlash(filepath.Join(".specify", "runtime", "receipts", transactionID+".json")),
	}
	for _, update := range normalized {
		receipt.ChangedPaths = append(receipt.ChangedPaths, update.rel)
	}
	receiptPath, err := secureProjectPath(root, receipt.ReceiptRef)
	if err != nil {
		return fileTransactionReceipt{}, err
	}
	receiptPayload := map[string]any{
		"version":        1,
		"transaction_id": transactionID,
		"kind":           kind,
		"status":         "committed",
		"changed_paths":  receipt.ChangedPaths,
	}
	rawReceipt, err := json.MarshalIndent(receiptPayload, "", "  ")
	if err != nil {
		return fileTransactionReceipt{}, err
	}
	if err := os.MkdirAll(filepath.Dir(receiptPath), 0o755); err != nil {
		return fileTransactionReceipt{}, err
	}
	if err := atomicWriteFile(receiptPath, append(rawReceipt, '\n'), 0o644); err != nil {
		return fileTransactionReceipt{}, err
	}
	cleanup()
	return receipt, nil
}

func recoverFileTransactionsLocked(root string) error {
	transactionsRoot, err := secureProjectPath(root, ".specify/runtime/transactions")
	if err != nil {
		return err
	}
	entries, err := os.ReadDir(transactionsRoot)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if !entry.IsDir() || entry.Name() == ".preparing" {
			continue
		}
		txRoot := filepath.Join(transactionsRoot, entry.Name())
		raw, err := os.ReadFile(filepath.Join(txRoot, "journal.json"))
		if err != nil {
			return fmt.Errorf("workflow transaction %s has no readable journal: %w", entry.Name(), err)
		}
		var journal fileTransactionJournal
		if err := json.Unmarshal(raw, &journal); err != nil || journal.Version != 1 || journal.TransactionID != entry.Name() {
			return fmt.Errorf("workflow transaction %s has an invalid journal", entry.Name())
		}
		if journal.Phase != "committed" {
			if err := rollbackFileTransaction(root, txRoot, journal); err != nil {
				return fmt.Errorf("recover workflow transaction %s: %w", entry.Name(), err)
			}
		}
		if err := os.RemoveAll(txRoot); err != nil {
			return err
		}
	}
	return nil
}

func rollbackFileTransaction(root, txRoot string, journal fileTransactionJournal) error {
	var failures []string
	for index := len(journal.Entries) - 1; index >= 0; index-- {
		entry := journal.Entries[index]
		if !entry.Applied {
			continue
		}
		if err := rollbackFileTransactionEntry(root, txRoot, entry); err != nil {
			failures = append(failures, entry.Path+": "+err.Error())
			continue
		}
		journal.Entries[index].Applied = false
		if err := writeFileTransactionJournal(filepath.Join(txRoot, "journal.json"), journal); err != nil {
			failures = append(failures, entry.Path+": persist rollback progress: "+err.Error())
		}
	}
	if len(failures) > 0 {
		return fmt.Errorf("rollback incomplete: %s", strings.Join(failures, "; "))
	}
	return nil
}

func rollbackFileTransactionEntry(root, txRoot string, entry fileTransactionEntry) error {
	target, err := secureProjectPath(root, entry.Path)
	if err != nil {
		return err
	}
	current, err := os.ReadFile(target)
	if !entry.Existed && os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	currentSHA256 := fileContentSHA256(current)
	if entry.Existed && currentSHA256 == entry.BeforeSHA256 {
		// Promotion may not have happened, or an earlier rollback restored the
		// target before its progress could be persisted.
		return nil
	}
	if currentSHA256 != entry.AfterSHA256 {
		return fmt.Errorf("target digest changed; refusing to overwrite or remove unrelated content")
	}
	if !entry.Existed {
		return os.Remove(target)
	}
	backupPath := filepath.Join(txRoot, filepath.FromSlash(entry.BackupRef))
	backup, err := os.ReadFile(backupPath)
	if err != nil {
		return err
	}
	if fileContentSHA256(backup) != entry.BeforeSHA256 {
		return fmt.Errorf("backup digest mismatch")
	}
	return atomicWriteFile(target, backup, 0o644)
}

func writeFileTransactionJournal(path string, journal fileTransactionJournal) error {
	raw, err := json.MarshalIndent(journal, "", "  ")
	if err != nil {
		return err
	}
	return atomicWriteFile(path, append(raw, '\n'), 0o644)
}

func combineFileTransactionErrors(cause, rollback error) error {
	if rollback == nil {
		return fmt.Errorf("file transaction failed and was rolled back: %w", cause)
	}
	return fmt.Errorf("file transaction failed: %v; %w", cause, rollback)
}

func newFileTransactionID() (string, error) {
	var value [12]byte
	if _, err := rand.Read(value[:]); err != nil {
		return "", err
	}
	return "TX-" + hex.EncodeToString(value[:]), nil
}

func fileContentSHA256(content []byte) string {
	sum := sha256.Sum256(content)
	return hex.EncodeToString(sum[:])
}
