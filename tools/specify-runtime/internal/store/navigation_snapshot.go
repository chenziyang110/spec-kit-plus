package store

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
)

// NavigationSnapshot binds advisory graph material, including same-generation
// updates. It is not evidence that the repository still implements that material.
type NavigationSnapshot struct {
	GenerationID string `json:"generation_id"`
	Digest       string `json:"digest"`
}

// NavigationRead detects commits while callers assemble a packet through the
// existing Store readers. data_version is compared on this SAME connection; it
// is a transient read guard, never a persisted freshness key or a file-mtime cache.
type NavigationRead struct {
	Snapshot NavigationSnapshot
	conn     *sql.Conn
	version  int64
}

func (s *Store) BeginNavigationRead(ctx context.Context) (*NavigationRead, error) {
	conn, err := s.db.Conn(ctx)
	if err != nil {
		return nil, err
	}
	read := &NavigationRead{conn: conn}
	if err = conn.QueryRowContext(ctx, `PRAGMA data_version`).Scan(&read.version); err == nil {
		read.Snapshot, err = navigationSnapshot(ctx, conn)
	}
	if err == nil {
		err = read.Validate(ctx)
	}
	if err != nil {
		_ = conn.Close()
		return nil, err
	}
	return read, nil
}

func (read *NavigationRead) Validate(ctx context.Context) error {
	var version int64
	if err := read.conn.QueryRowContext(ctx, `PRAGMA data_version`).Scan(&version); err != nil {
		return fmt.Errorf("validate navigation read: %w", err)
	}
	if version != read.version {
		return fmt.Errorf("project cognition changed during navigation; rerun cognition compass")
	}
	return nil
}

func (read *NavigationRead) Close() error { return read.conn.Close() }

func (s *Store) ReadNavigationSnapshot(ctx context.Context) (NavigationSnapshot, error) {
	read, err := s.BeginNavigationRead(ctx)
	if err != nil {
		return NavigationSnapshot{}, err
	}
	defer read.Close()
	return read.Snapshot, nil
}

func navigationSnapshot(ctx context.Context, conn *sql.Conn) (NavigationSnapshot, error) {
	tx, err := conn.BeginTx(ctx, &sql.TxOptions{ReadOnly: true})
	if err != nil {
		return NavigationSnapshot{}, err
	}
	defer tx.Rollback()
	var generationID string
	if err := tx.QueryRowContext(ctx, `SELECT id FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`).Scan(&generationID); err != nil {
		return NavigationSnapshot{}, fmt.Errorf("read navigation generation: %w", err)
	}
	// Hash rows in deterministic order inside one SQLite read transaction. Keep
	// current graph bases AND mutation/reconciliation history: a change then a
	// semantic reversal must not silently resurrect an older navigation packet.
	queries := []struct{ name, statement string }{
		{"metadata", `SELECT * FROM metadata ORDER BY key`},
		{"generations", `SELECT * FROM generations WHERE state = 'active' ORDER BY sequence, id`},
		{"nodes", `SELECT * FROM nodes WHERE generation_id = ? ORDER BY id`},
		{"evidence", `SELECT * FROM evidence WHERE generation_id = ? ORDER BY id`},
		{"node_evidence", `SELECT ne.* FROM node_evidence ne JOIN nodes n ON n.id = ne.node_id WHERE n.generation_id = ? ORDER BY ne.node_id, ne.evidence_id`},
		{"edges", `SELECT * FROM edges WHERE generation_id = ? ORDER BY id`},
		{"edge_evidence", `SELECT ee.* FROM edge_evidence ee JOIN edges e ON e.id = ee.edge_id WHERE e.generation_id = ? ORDER BY ee.edge_id, ee.evidence_id`},
		{"observations", `SELECT * FROM observations WHERE generation_id = ? ORDER BY id`},
		{"observation_evidence", `SELECT oe.* FROM observation_evidence oe JOIN observations o ON o.id = oe.observation_id WHERE o.generation_id = ? ORDER BY oe.observation_id, oe.evidence_id`},
		{"path_index", `SELECT * FROM path_index WHERE generation_id = ? ORDER BY id`},
		{"alias_index", `SELECT * FROM alias_index WHERE generation_id = ? ORDER BY id`},
		{"claims", `SELECT * FROM claims WHERE generation_id = ? ORDER BY id`},
		{"claim_evidence", `SELECT ce.* FROM claim_evidence ce JOIN claims c ON c.id = ce.claim_id WHERE c.generation_id = ? ORDER BY ce.claim_id, ce.evidence_id, ce.role`},
		{"claim_verifications", `SELECT * FROM claim_verifications WHERE generation_id = ? ORDER BY id`},
		{"claim_transitions", `SELECT * FROM claim_transitions WHERE generation_id = ? ORDER BY id`},
		{"claim_reconciliations", `SELECT * FROM claim_reconciliations WHERE generation_id = ? ORDER BY id`},
		{"updates", `SELECT * FROM updates WHERE generation_id = ? ORDER BY id`},
	}
	hash := sha256.New()
	encoder := json.NewEncoder(hash)
	for index, query := range queries {
		var args []any
		if index > 1 {
			args = []any{generationID}
		}
		rows, err := tx.QueryContext(ctx, query.statement, args...)
		if err != nil {
			return NavigationSnapshot{}, fmt.Errorf("read navigation %s: %w", query.name, err)
		}
		columns, err := rows.Columns()
		if err == nil {
			err = encoder.Encode([]any{query.name, columns})
		}
		for err == nil && rows.Next() {
			values := make([]any, len(columns))
			pointers := make([]any, len(columns))
			for index := range values {
				pointers[index] = &values[index]
			}
			if err = rows.Scan(pointers...); err == nil {
				err = encoder.Encode(values)
			}
		}
		if err == nil {
			err = rows.Err()
		}
		closeErr := rows.Close()
		if err != nil {
			return NavigationSnapshot{}, fmt.Errorf("hash navigation %s: %w", query.name, err)
		}
		if closeErr != nil {
			return NavigationSnapshot{}, closeErr
		}
	}
	if err := tx.Commit(); err != nil {
		return NavigationSnapshot{}, err
	}
	return NavigationSnapshot{GenerationID: generationID, Digest: "sha256:" + hex.EncodeToString(hash.Sum(nil))}, nil
}
