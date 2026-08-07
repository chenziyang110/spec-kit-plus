"""Design Intelligence runtime contracts (schema + validation only)."""

from .design_context import (
    DESIGN_CONTEXT_VERSION,
    DesignContextValidationError,
    DesignContextValidationResult,
    load_design_context_schema,
    validate_design_context,
)
from .evidence import (
    CANONICAL_EVIDENCE_TYPES,
    EVIDENCE_TYPE_ASSUMPTION,
    EVIDENCE_TYPE_INFERRED,
    EVIDENCE_TYPE_MEASURED,
    DesignEvidenceValidationError,
    DesignEvidenceValidationResult,
    load_design_evidence_schema,
    normalize_evidence_type,
    validate_design_evidence,
    validate_design_evidence_list,
)
from .ui_quality_gate import (
    GATE_REPORT_VERSION,
    UiQualityGateIssue,
    UiQualityGateReport,
    UiQualityGateReportValidationResult,
    load_ui_quality_gate_report_schema,
    run_ui_quality_gate_rules,
    validate_ui_quality_gate_report,
)

__all__ = [
    "CANONICAL_EVIDENCE_TYPES",
    "DESIGN_CONTEXT_VERSION",
    "EVIDENCE_TYPE_ASSUMPTION",
    "EVIDENCE_TYPE_INFERRED",
    "EVIDENCE_TYPE_MEASURED",
    "GATE_REPORT_VERSION",
    "DesignContextValidationError",
    "DesignContextValidationResult",
    "DesignEvidenceValidationError",
    "DesignEvidenceValidationResult",
    "UiQualityGateIssue",
    "UiQualityGateReport",
    "UiQualityGateReportValidationResult",
    "load_design_context_schema",
    "load_design_evidence_schema",
    "load_ui_quality_gate_report_schema",
    "normalize_evidence_type",
    "run_ui_quality_gate_rules",
    "validate_design_context",
    "validate_design_evidence",
    "validate_design_evidence_list",
    "validate_ui_quality_gate_report",
]
