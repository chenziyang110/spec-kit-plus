-- Representative historical rows. Expired Run authority must stay inert;
-- live and recovery-held shared work must retain its fences and ownership.

-- schema-version: 3
INSERT INTO metadata VALUES ('legacy_setting', 'preserve this value');
INSERT INTO supervisor_instances VALUES ('legacy-owner', 'active', 1, 1, NULL);
INSERT INTO runs VALUES ('legacy-run', 'quick', 'quick', 'legacy', 'refs/heads/main',
    'TEST_SHA256', 'legacy-owner', 'active', 4, 9, 1, 1);
INSERT INTO activities VALUES ('legacy-activity', 'legacy-run', 'execute', 1,
    'TEST_SHA256', 'active', 3, 1, 1);
INSERT INTO workspaces VALUES ('legacy-workspace', 'legacy-run', 1, 'git_worktree',
    'legacy-workspace', 'legacy-common-dir', 'refs/heads/main', 'legacy-commit',
    'refs/heads/legacy-private', 'in_use', 3, 1, 1);
INSERT INTO attempts VALUES ('legacy-attempt', 'legacy-run', 'legacy-activity',
    'legacy-workspace', 1, 'active', 'codex', 'managed', 'legacy-owner', 9, 1, 1, 3, 1, 1);
INSERT INTO operations VALUES ('legacy-operation', 'attempt.launch', 'run', 'legacy-run',
    'legacy-run', 'legacy-attempt', 'legacy-activity', 'legacy-workspace', 'legacy-owner',
    9, 4, 'legacy-operation-key', 'TEST_SHA256', 'executing', 2, 1, 1);
INSERT INTO events VALUES (100, 'run', 'legacy-run', 4, 'run.transitioned', 'historic event', '{}', 1);

-- schema-version: 4
INSERT INTO workspace_allocations VALUES ('legacy-allocation', 'legacy-run', 'legacy-workspace',
    1, 'legacy-owner', 4, 3, 'legacy-allocation-key', 'TEST_SHA256', 'executing',
    'do not recover on board open', 2, 1, 1);

-- schema-version: 6
INSERT INTO snapshots VALUES ('legacy-snapshot', 'legacy-run', 'legacy-attempt', 'legacy-workspace',
    1, 'refs/heads/main', 'legacy-source', 'legacy-workspace', 'legacy-common-dir',
    'refs/heads/legacy-private', 'legacy-commit', 'legacy-tree', 'TEST_SHA256',
    'TEST_SHA256', 'context_only', 1, 1, 1);
INSERT INTO snapshot_entries VALUES ('legacy-entry', 'legacy-snapshot', 1, 'ambient.txt',
    'untracked', 'file', 420, 'TEST_SHA256', 'legacy-object', 12, 'context_only', 1);
INSERT INTO resource_claims VALUES ('legacy-claim', 'filesystem', 'legacy-workspace',
    'legacy-run', 'legacy-attempt', 'legacy-activity', 'legacy-workspace', 'legacy-owner',
    9, 'exclusive', 'active', 'legacy ownership', '{}', 1, 1, 1, 1, 0);

-- schema-version: 7
INSERT INTO run_results VALUES ('legacy-result', 'legacy-run', 1, 'legacy-attempt',
    'legacy-activity', 'legacy-workspace', 1, 9, 'legacy-snapshot', 'refs/heads/main',
    'legacy-commit', 'legacy-result-tree', 'legacy-result-commit', 'refs/legacy/result',
    'TEST_SHA256', 'TEST_SHA256', 'TEST_SHA256', 'ready', '[]', '[]', '[]', 1);
INSERT INTO run_result_paths VALUES ('legacy-result', 1, 'src/legacy.go');
INSERT INTO run_reopen_intents VALUES ('legacy-run', 'legacy-result', NULL, 'historical repair request', 1, 0);

-- schema-version: 8
INSERT INTO candidate_builds VALUES ('legacy-build', 'refs/heads/main', 'legacy-commit',
    'TEST_SHA256', 'legacy-candidate-workspace', 'succeeded', 'historical build', 1, 1);
INSERT INTO frozen_candidates VALUES ('legacy-candidate', 'legacy-build', 'refs/heads/main',
    'legacy-commit', 'legacy-candidate-tree', 'legacy-candidate-commit', 'refs/legacy/candidate',
    'TEST_SHA256', 'succeeded', 1);
INSERT INTO frozen_candidate_members VALUES ('legacy-candidate', 1, 'legacy-result', 'TEST_SHA256');

-- schema-version: 9
INSERT INTO candidate_reviews VALUES ('legacy-review', 'legacy-candidate', 'TEST_SHA256',
    'legacy-candidate-tree', 'legacy-candidate-commit', 'legacy-reviewer', 'passed',
    'TEST_SHA256', 'TEST_SHA256', '[]', 1);
INSERT INTO candidate_acceptances VALUES ('legacy-acceptance', 'legacy-candidate', 'legacy-review',
    'TEST_SHA256', 'TEST_SHA256', 'accepted', 'legacy-user', 'TEST_SHA256', 1);
INSERT INTO candidate_publications VALUES ('legacy-publication', 'legacy-candidate', 'legacy-acceptance',
    'refs/heads/main', 'legacy-commit', 'legacy-candidate-commit', 'legacy-tree', 'executing',
    'TEST_SHA256', 'do not resume publication', 1, 1);
INSERT INTO candidate_syncs VALUES ('legacy-sync', 'legacy-candidate', 'legacy-publication',
    'legacy-source', 'succeeded', 'TEST_SHA256', 1);

-- schema-version: 10
INSERT INTO adapter_capabilities VALUES ('codex', 'managed', 1, 1, 1, 1, 1, 1, 1, 'TEST_SHA256', 1);
INSERT INTO workspace_attestations VALUES ('legacy-attestation', 'legacy-workspace', 'legacy-run',
    1, 'legacy-workspace', 'legacy-common-dir', 'legacy-admin-dir', 'refs/heads/main',
    'legacy-commit', 'refs/heads/legacy-private', 'legacy-snapshot', 'TEST_SHA256',
    '["legacy-workspace"]', 'TEST_SHA256', 1);

-- schema-version: 11
INSERT INTO workspace_routes VALUES ('legacy-workspace', 'primary', 'legacy-run', 1);
INSERT INTO primary_workspace_slots VALUES (1, 'legacy-run', 'legacy-owner', 'legacy-workspace', 1);

-- schema-version: 12
INSERT INTO work_items VALUES ('legacy-live', '', 'legacy-run', 'fast:legacy-live', 'active shared work',
    'legacy-agent', 'codex', 'legacy-workspace', 'legacy-commit', 'active', 'continue guarded work',
    '', 4, 7, 4102444800000, 1, 0, '[]', 1, 1);
INSERT INTO write_intents VALUES ('legacy-write', 'legacy-live', 'src/owned.go', 'src/owned.go',
    'modify', 'keep active ownership', 'confirmed', 'active', 2, 1, 1, 0);
INSERT INTO work_items VALUES ('legacy-recovery', '', '', 'quick:legacy-recovery', 'dirty shared work',
    'legacy-agent', 'codex', 'legacy-workspace', 'legacy-commit', 'interrupted', 'recover dirty work',
    'lease expired with dirty paths', 6, 8, 1, 1, 1, '["src/recovery.go"]', 1, 1);
INSERT INTO write_intents VALUES ('legacy-recovery-write', 'legacy-recovery', 'src/recovery.go',
    'src/recovery.go', 'modify', 'keep dirty ownership', 'confirmed', 'recovery', 2, 1, 1, 0);
INSERT INTO events VALUES (200, 'work', 'legacy-live', 7, 'work.scope_claimed', 'historical guard', '{}', 1);
INSERT INTO events VALUES (201, 'work', 'legacy-recovery', 8, 'work.interrupted', 'dirty recovery', '{}', 1);

-- schema-version: 13
INSERT INTO execution_activities VALUES ('legacy-execution', 'legacy-live', 'fast', 'legacy-live', '',
    'fast:legacy-live', 'legacy-source-ref', 'active shared work', 'executing',
    '{"head_commit":"legacy-commit","dirty_paths":[],"path_digests":{}}',
    201, 'TEST_SHA256', '[]', '', 3, 0, 1, 1);
INSERT INTO execution_resource_intents VALUES ('legacy-resource', 'legacy-execution', 'legacy-live',
    'api', '/v1/legacy', '/v1/legacy', 'exclusive', 'confirmed', 'active', 'keep API ownership', 2, 1, 1, 0);
INSERT INTO execution_activities VALUES ('legacy-recovery-execution', 'legacy-recovery', 'quick',
    'legacy-recovery', '', 'quick:legacy-recovery', '', 'dirty shared work', 'interrupted', '{}',
    201, 'TEST_SHA256', '[]', '', 3, 0, 1, 1);
INSERT INTO execution_resource_intents VALUES ('legacy-recovery-resource', 'legacy-recovery-execution',
    'legacy-recovery', 'schema', 'legacy-schema', 'legacy-schema', 'exclusive', 'confirmed', 'recovery',
    'keep semantic recovery hold', 2, 1, 1, 0);
INSERT INTO events VALUES (202, 'execution_activity', 'legacy-execution', 3, 'execution.guarded',
    'historical guard', '{}', 1);
INSERT INTO events VALUES (203, 'execution_activity', 'legacy-recovery-execution', 3, 'execution.interrupted',
    'dirty recovery', '{}', 1);
