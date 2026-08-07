"""Design Intelligence runtime contracts (schema + validation only)."""

from .design_context import (
    DESIGN_CONTEXT_VERSION,
    DesignContextValidationError,
    DesignContextValidationResult,
    load_design_context_schema,
    validate_design_context,
)

__all__ = [
    "DESIGN_CONTEXT_VERSION",
    "DesignContextValidationError",
    "DesignContextValidationResult",
    "load_design_context_schema",
    "validate_design_context",
]
