"""Backend registry primitives for orchestration runtime selection."""

from .base import BackendDescriptor, RuntimeBackend
from .detect import detect_available_backends
from .process_backend import ProcessBackend, ProcessHandle

__all__ = [
    "BackendDescriptor",
    "ProcessBackend",
    "ProcessHandle",
    "RuntimeBackend",
    "detect_available_backends",
]
