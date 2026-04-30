"""Tests for task contract validation helpers."""

import pytest
from specify_cli.orchestration.delegation import (
    validate_task_contract,
    validate_batch_isolation,
    KNOWN_AGENT_ROLES,
)


class TestValidateTaskContract:
    def test_valid_contract_passes(self):
        result = validate_task_contract(
            task_id="T001",
            agent="security-reviewer",
            write_scope=["src/auth/middleware.ts"],
        )
        assert result.valid
        assert len(result.errors) == 0

    def test_empty_agent_auto_corrects_to_executor(self):
        result = validate_task_contract(
            task_id="T001",
            agent="",
        )
        assert result.valid
        assert result.auto_corrections.get("agent") == "executor"

    def test_unknown_agent_warns(self):
        result = validate_task_contract(
            task_id="T001",
            agent="nonexistent-role",
        )
        assert result.valid  # warning, not error
        assert len(result.warnings) >= 1

    def test_self_dependency_errors(self):
        result = validate_task_contract(
            task_id="T001",
            agent="executor",
            depends_on=["T001"],
        )
        assert not result.valid
        assert any("itself" in e for e in result.errors)

    def test_sensitive_path_in_write_scope_warns(self):
        result = validate_task_contract(
            task_id="T001",
            agent="executor",
            write_scope=["src/.env"],
        )
        assert len(result.warnings) >= 1

    def test_known_roles_include_all_required(self):
        required = {"security-reviewer", "test-engineer", "debugger", "executor"}
        assert required.issubset(KNOWN_AGENT_ROLES)


class TestValidateBatchIsolation:
    def test_isolated_write_sets_no_conflicts(self):
        tasks = [
            {"task_id": "T1", "write_scope": ["src/a.ts"]},
            {"task_id": "T2", "write_scope": ["src/b.ts"]},
        ]
        assert validate_batch_isolation(tasks) == []

    def test_overlapping_write_sets_conflict(self):
        tasks = [
            {"task_id": "T1", "write_scope": ["src/shared.ts"]},
            {"task_id": "T2", "write_scope": ["src/shared.ts"]},
        ]
        conflicts = validate_batch_isolation(tasks)
        assert len(conflicts) == 1
        assert "src/shared.ts" in conflicts[0]["overlapping_paths"]

    def test_empty_write_sets_skipped(self):
        tasks = [
            {"task_id": "T1", "write_scope": []},
            {"task_id": "T2", "write_scope": []},
        ]
        assert validate_batch_isolation(tasks) == []
