"""
NRF Sequence Manager - Entry point for NRF-specific operations with nfInstanceId tracking.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from .instance_tracker import NRFInstanceTracker

logger = logging.getLogger("NRFSequenceManager")

# Global session managers per test session
_session_managers: Dict[str, NRFInstanceTracker] = {}


def get_or_create_session_manager(session_id: str) -> NRFInstanceTracker:
    """Get or create a session-specific NRF instance tracker"""
    if session_id not in _session_managers:
        logger.info(f"Creating new NRF session manager for: {session_id}")
        _session_managers[session_id] = NRFInstanceTracker()
    return _session_managers[session_id]


def handle_nrf_operation(
    url: str,
    method: str,
    payload: Optional[str],
    test_context: Optional[Dict[str, Any]],
    nf_name: str,
) -> Optional[str]:
    """
    Handle NRF-specific operations with nfInstanceId tracking.

    Args:
        url: The base URL for the NRF operation
        method: HTTP method (PUT, GET, DELETE, PATCH)
        payload: JSON payload as string
        test_context: Test execution context with test_name, sheet, row_idx
        nf_name: Network function name from config

    Returns:
        Modified URL with nfInstanceId appended if applicable, None otherwise
    """
    logger.debug(f"Handling NRF operation: {method} for {nf_name}")

    # Validate URL pattern - only apply nfInstanceId logic to nnrf-nfm/v1/nf-instances/ URLs without query parameters
    if not _should_apply_nf_instance_id(url):
        logger.debug(
            f"URL pattern doesn't match nfInstanceId requirements: {url}"
        )
        return None

    # If no test context, fall back to legacy behavior
    if not test_context:
        logger.debug("No test context provided, using legacy NRF handling")
        return _legacy_nrf_handling(url, method, payload)

    # Extract session identifier
    session_id = test_context.get("session_id", "default")
    tracker = get_or_create_session_manager(session_id)

    # Track test progression for cleanup triggers
    tracker.track_test_progression(test_context)

    # Handle operation based on method
    if method == "PUT":
        # For PUT, extract nfInstanceId from payload and register it
        nf_instance_id = _extract_nf_instance_id(payload)
        if nf_instance_id:
            tracker.handle_put_operation(test_context, nf_instance_id)
            modified_url = f"{url}{nf_instance_id}"
            logger.info(
                f"PUT operation - registered nfInstanceId: {nf_instance_id}"
            )
            return modified_url
        else:
            logger.warning(
                "PUT operation but no nfInstanceId found in payload"
            )
            return None

    elif method in ["GET", "PATCH"]:
        # For GET/PATCH, use the active instance from stack
        nf_instance_id = tracker.get_active_instance_id(test_context)
        if nf_instance_id:
            modified_url = f"{url}{nf_instance_id}"
            logger.info(
                f"{method} operation - using nfInstanceId: {nf_instance_id}"
            )
            return modified_url
        else:
            logger.warning(
                f"{method} operation but no active nfInstanceId found"
            )
            return None

    elif method == "DELETE":
        # For DELETE, use active instance and remove from stack
        nf_instance_id = tracker.handle_delete_operation(test_context)
        if nf_instance_id:
            modified_url = f"{url}{nf_instance_id}"
            logger.info(
                f"DELETE operation - removed nfInstanceId: {nf_instance_id}"
            )
            return modified_url
        else:
            logger.warning("DELETE operation but no active nfInstanceId found")
            return None

    # For other methods, no modification needed
    logger.debug(f"Method {method} does not require nfInstanceId handling")
    return None


def _legacy_nrf_handling(
    url: str, method: str, payload: Optional[str]
) -> Optional[str]:
    """
    Maintain existing behavior for backward compatibility.
    This is the original logic from curl_builder.py.
    """
    if not payload:
        return None

    # Validate URL pattern - only apply nfInstanceId logic to nnrf-nfm/v1/nf-instances/ URLs without query parameters
    if not _should_apply_nf_instance_id(url):
        logger.debug(
            f"URL pattern doesn't match nfInstanceId requirements: {url}"
        )
        return None

    try:
        parsed = json.loads(payload)
        nf_instance_id = None

        if isinstance(parsed, dict):
            nf_instance_id = parsed.get("nfInstanceId")
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and "nfInstanceId" in item:
                    nf_instance_id = item["nfInstanceId"]
                    break

        if nf_instance_id:
            logger.debug(
                f"Legacy handling - found nfInstanceId: {nf_instance_id}"
            )
            return f"{url}{nf_instance_id}"

    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"Legacy handling - failed to parse payload: {e}")

    return None


def _extract_nf_instance_id(
    payload: Optional[Union[str, Dict, List]],
) -> Optional[str]:
    """Extract nfInstanceId from payload (string or dict)"""
    if not payload:
        return None

    try:
        # Handle both string (JSON) and dict payloads
        if isinstance(payload, str):
            parsed = json.loads(payload)
        elif isinstance(payload, dict):
            parsed = payload
        elif isinstance(payload, list):
            parsed = payload
        else:
            return None

        if isinstance(parsed, dict):
            # Direct nfInstanceId in payload
            nf_id = parsed.get("nfInstanceId")
            if nf_id:
                return nf_id

            # Check nested structures (e.g., nfProfile.nfInstanceId)
            if "nfProfile" in parsed and isinstance(parsed["nfProfile"], dict):
                nf_id = parsed["nfProfile"].get("nfInstanceId")
                if nf_id:
                    return nf_id

        elif isinstance(parsed, list):
            # Array of items - check each for nfInstanceId
            for item in parsed:
                if isinstance(item, dict) and "nfInstanceId" in item:
                    return item["nfInstanceId"]

    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to extract nfInstanceId from payload: {e}")

    return None


def cleanup_all_sessions():
    """Clean up all NRF sessions - typically called at test suite end"""
    logger.info(f"Cleaning up {len(_session_managers)} NRF sessions")

    for session_id, tracker in _session_managers.items():
        tracker.cleanup_all_active_instances(
            reason=f"session_cleanup_{session_id}"
        )

    _session_managers.clear()


def cleanup_session(session_id: str):
    """Clean up a specific NRF session"""
    if session_id in _session_managers:
        logger.info(f"Cleaning up NRF session: {session_id}")
        tracker = _session_managers[session_id]
        tracker.cleanup_all_active_instances(
            reason=f"session_cleanup_{session_id}"
        )
        del _session_managers[session_id]


def get_session_diagnostic_report(session_id: str) -> Optional[Dict[str, Any]]:
    """Get diagnostic report for a specific session"""
    if session_id in _session_managers:
        return _session_managers[session_id].get_diagnostic_report()
    return None


def get_global_diagnostic_report() -> Dict[str, Any]:
    """Get diagnostic report across all sessions"""
    report = {"total_sessions": len(_session_managers), "sessions": {}}

    for session_id, tracker in _session_managers.items():
        report["sessions"][session_id] = tracker.get_diagnostic_report()

    # Global statistics
    total_active = sum(
        s["active_instances"] for s in report["sessions"].values()
    )
    total_created = sum(
        s["total_instances_created"] for s in report["sessions"].values()
    )

    report["global_stats"] = {
        "total_active_instances": total_active,
        "total_instances_created": total_created,
    }

    return report


def update_from_response(
    session_id: str,
    method: str,
    response_data: Dict[str, Any],
    test_context: Optional[Dict[str, Any]] = None,
):
    """
    Update tracker with actual nfInstanceId from server response.
    Useful when server generates or modifies the nfInstanceId.
    """
    if session_id not in _session_managers:
        logger.warning(f"No session found for ID: {session_id}")
        return

    tracker = _session_managers[session_id]

    # Extract nfInstanceId from response
    nf_instance_id = None
    if isinstance(response_data, dict):
        nf_instance_id = response_data.get("nfInstanceId")

        # Check nested structures
        if not nf_instance_id and "nfProfile" in response_data:
            nf_instance_id = response_data["nfProfile"].get("nfInstanceId")

    if nf_instance_id and method == "PUT" and test_context:
        # Update the tracker with server-generated ID
        logger.info(
            f"Updating tracker with server response nfInstanceId: {nf_instance_id}"
        )
        # Note: This would require enhancing the tracker to support updates
        # For now, we log it for diagnostic purposes


def _should_apply_nf_instance_id(url: str) -> bool:
    """
    Validate if URL should have nfInstanceId appended.

    Rules:
    1. nfInstanceId shall be used only when the URL is nnrf-nfm/v1/nf-instances/
    2. nnrf-nfm/v1/nf-instances? don't add nfInstanceId when URL has '?'

    Args:
        url: The URL to validate

    Returns:
        True if nfInstanceId should be applied, False otherwise
    """
    # Check if URL contains the required NRF pattern
    if "nnrf-nfm/v1/nf-instances" not in url:
        return False

    # Rule 1a: Don't add nfInstanceId when URL has query parameters (?)
    if "?" in url:
        logger.debug(
            f"URL contains query parameters, skipping nfInstanceId: {url}"
        )
        return False

    # Rule 1: Only apply to nnrf-nfm/v1/nf-instances/ URLs (must end with / or be exact match)
    if (
        url.endswith("nnrf-nfm/v1/nf-instances")
        or "nnrf-nfm/v1/nf-instances/" in url
    ):
        return True

    return False
