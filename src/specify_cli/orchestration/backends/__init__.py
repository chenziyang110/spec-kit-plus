"""Backend registry primitives for orchestration runtime selection."""

from .base import BackendDescriptor, RuntimeBackend
from .detect import detect_available_backends
from .process_backend import ProcessBackend, ProcessHandle
from .workspace_process_backend import (
    WorkspaceBindingError,
    WorkspaceLaunchBinding,
    WorkspaceProcessBackend,
    WorkspaceProcessHandle,
)

__all__ = [
    "BackendDescriptor",
    "ProcessBackend",
    "ProcessHandle",
    "RuntimeBackend",
    "WorkspaceBindingError",
    "WorkspaceLaunchBinding",
    "WorkspaceProcessBackend",
    "WorkspaceProcessHandle",
    "detect_available_backends",
]
