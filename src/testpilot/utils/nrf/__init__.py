"""
NRF (Network Repository Function) specific utilities for managing nfInstanceId lifecycle.

This module provides specialized handling for NRF operations including:
- nfInstanceId tracking across PUT/GET/DELETE operations
- Test session management
- Automatic cleanup policies
- Diagnostic reporting
"""

from .sequence_manager import (
    cleanup_all_sessions,
    get_global_diagnostic_report,
    handle_nrf_operation,
)

__all__ = [
    "handle_nrf_operation",
    "cleanup_all_sessions",
    "get_global_diagnostic_report",
]
