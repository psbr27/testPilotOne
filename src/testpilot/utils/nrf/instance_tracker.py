"""
NRF Instance Tracker - Core tracking logic for nfInstanceId lifecycle management.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NRFInstanceTracker")


class CleanupPolicy(Enum):
    """Cleanup policies for NRF instances"""

    TEST_END = "test_end"  # Clean when test completes
    SUITE_END = "suite_end"  # Clean when test suite completes
    SESSION_END = "session_end"  # Clean when session ends
    MANUAL_ONLY = "manual"  # Only DELETE operations clean


class NRFInstanceTracker:
    """
    Tracks nfInstanceId lifecycle for NRF operations.

    Maintains a stack-based approach where:
    - PUT operations push new instances
    - GET/PATCH operations use the active instance
    - DELETE operations pop instances
    """

    def __init__(self):
        self.instance_registry: Dict[str, Dict[str, Any]] = {}
        self.active_stack: List[str] = []
        self.test_context_history: List[Dict[str, Any]] = []
        self.current_test_context: Optional[Dict[str, Any]] = None
        logger.debug("Initialized new NRFInstanceTracker")

    def track_test_progression(self, test_context: Dict[str, Any]):
        """Track test progression and trigger cleanups when tests/suites change"""
        if self.current_test_context:
            # Check for test transition
            old_test = self.current_test_context.get("test_name")
            new_test = test_context.get("test_name")

            if old_test != new_test:
                logger.info(
                    f"Test transition detected: {old_test} -> {new_test}"
                )
                self._cleanup_test_instances(self.current_test_context)

            # Check for suite transition
            old_suite = self.current_test_context.get("sheet")
            new_suite = test_context.get("sheet")

            if old_suite != new_suite:
                logger.info(
                    f"Suite transition detected: {old_suite} -> {new_suite}"
                )
                self._cleanup_suite_instances(self.current_test_context)

        self.current_test_context = test_context
        self.test_context_history.append(test_context)

    def handle_put_operation(
        self, test_context: Dict[str, Any], nf_instance_id: str
    ):
        """Handle PUT operation - create new instance and push to stack"""
        timestamp = datetime.now()

        instance_record = {
            "nfInstanceId": nf_instance_id,
            "created_by": {
                "test_name": test_context.get("test_name"),
                "test_step": test_context.get("row_idx"),
                "sheet": test_context.get("sheet"),
                "timestamp": timestamp,
            },
            "operations": [
                {
                    "method": "PUT",
                    "timestamp": timestamp,
                    "test_step": test_context.get("row_idx"),
                }
            ],
            "status": "active",
            "cleanup_policy": self._determine_cleanup_policy(test_context),
        }

        self.instance_registry[nf_instance_id] = instance_record
        self.active_stack.append(nf_instance_id)

        logger.info(
            f"Created new NRF instance: {nf_instance_id} for test: {test_context.get('test_name')}"
        )
        logger.debug(f"Active stack size: {len(self.active_stack)}")

    def get_active_instance_id(
        self, test_context: Dict[str, Any]
    ) -> Optional[str]:
        """Get active instance ID for GET/PATCH operations"""
        # Strategy 1: Use most recent from same test
        test_name = test_context.get("test_name")

        for nf_id in reversed(self.active_stack):
            record = self.instance_registry.get(nf_id, {})
            if record.get("created_by", {}).get("test_name") == test_name:
                logger.debug(
                    f"Found matching instance for test {test_name}: {nf_id}"
                )
                self._log_operation(
                    nf_id, test_context.get("row_idx"), "GET/PATCH"
                )
                return nf_id

        # Strategy 2: Use top of stack (most recent overall)
        if self.active_stack:
            nf_id = self.active_stack[-1]
            logger.debug(f"Using top of stack instance: {nf_id}")
            self._log_operation(
                nf_id, test_context.get("row_idx"), "GET/PATCH"
            )
            return nf_id

        logger.warning(f"No active instance found for test: {test_name}")
        return None

    def handle_delete_operation(
        self, test_context: Dict[str, Any]
    ) -> Optional[str]:
        """Handle DELETE operation - remove instance from stack"""
        nf_id = self.get_active_instance_id(test_context)

        if nf_id and nf_id in self.active_stack:
            self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id, reason="DELETE_OPERATION")
            logger.info(f"Deleted NRF instance: {nf_id}")
            logger.debug(
                f"Active stack size after delete: {len(self.active_stack)}"
            )

        return nf_id

    def _determine_cleanup_policy(
        self, test_context: Dict[str, Any]
    ) -> CleanupPolicy:
        """Determine cleanup policy based on test patterns"""
        test_name = test_context.get("test_name", "").lower()

        # Pattern-based policy determination
        if "registration" in test_name:
            return CleanupPolicy.TEST_END
        elif "discovery" in test_name:
            return CleanupPolicy.SUITE_END
        elif "validation" in test_name or "validate" in test_name:
            return CleanupPolicy.TEST_END
        else:
            return CleanupPolicy.SESSION_END

    def _cleanup_test_instances(self, test_context: Dict[str, Any]):
        """Clean up instances when test ends"""
        test_name = test_context.get("test_name")
        to_cleanup = []

        for nf_id, record in self.instance_registry.items():
            if (
                record["status"] == "active"
                and record["cleanup_policy"] == CleanupPolicy.TEST_END
                and record["created_by"]["test_name"] == test_name
            ):
                to_cleanup.append(nf_id)

        if to_cleanup:
            logger.info(
                f"Auto-cleaning {len(to_cleanup)} instances for test: {test_name}"
            )

        for nf_id in to_cleanup:
            if nf_id in self.active_stack:
                self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id, reason="auto_cleanup_test_end")

    def _cleanup_suite_instances(self, test_context: Dict[str, Any]):
        """Clean up instances when suite ends"""
        sheet = test_context.get("sheet")
        to_cleanup = []

        for nf_id, record in self.instance_registry.items():
            if (
                record["status"] == "active"
                and record["cleanup_policy"] == CleanupPolicy.SUITE_END
                and record["created_by"]["sheet"] == sheet
            ):
                to_cleanup.append(nf_id)

        if to_cleanup:
            logger.info(
                f"Auto-cleaning {len(to_cleanup)} instances for suite: {sheet}"
            )

        for nf_id in to_cleanup:
            if nf_id in self.active_stack:
                self.active_stack.remove(nf_id)
            self._mark_deleted(nf_id, reason="auto_cleanup_suite_end")

    def cleanup_all_active_instances(self, reason: str = "session_end"):
        """Clean up all active instances - typically at session end"""
        active_count = len(self.active_stack)
        if active_count > 0:
            logger.info(
                f"Cleaning up {active_count} active instances: {reason}"
            )

        while self.active_stack:
            nf_id = self.active_stack.pop()
            self._mark_deleted(nf_id, reason=reason)

    def _log_operation(
        self, nf_id: str, test_step: Optional[int], method: str
    ):
        """Log operation on instance"""
        if nf_id in self.instance_registry:
            self.instance_registry[nf_id]["operations"].append(
                {
                    "method": method,
                    "timestamp": datetime.now(),
                    "test_step": test_step,
                }
            )

    def _mark_deleted(self, nf_id: str, reason: str = "DELETE"):
        """Mark instance as deleted"""
        if nf_id in self.instance_registry:
            self.instance_registry[nf_id]["status"] = "deleted"
            self.instance_registry[nf_id]["deleted_at"] = datetime.now()
            self.instance_registry[nf_id]["deletion_reason"] = reason
            logger.debug(f"Marked instance {nf_id} as deleted: {reason}")

    def get_diagnostic_report(self) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report"""
        active_instances = [
            nf_id
            for nf_id, record in self.instance_registry.items()
            if record["status"] == "active"
        ]

        return {
            "active_instances": len(active_instances),
            "active_instance_ids": active_instances,
            "active_stack_size": len(self.active_stack),
            "total_instances_created": len(self.instance_registry),
            "instances_by_test": self._group_by_test(),
            "instances_by_status": self._group_by_status(),
            "orphaned_instances": self._find_orphaned_instances(),
            "stack_trace": self.active_stack.copy(),
        }

    def _group_by_test(self) -> Dict[str, Dict[str, int]]:
        """Group instances by test name with status counts"""
        by_test = {}
        for record in self.instance_registry.values():
            test_name = record["created_by"]["test_name"]
            status = record["status"]

            if test_name not in by_test:
                by_test[test_name] = {"active": 0, "deleted": 0}

            by_test[test_name][status] = by_test[test_name].get(status, 0) + 1

        return by_test

    def _group_by_status(self) -> Dict[str, int]:
        """Group instances by status"""
        by_status = {"active": 0, "deleted": 0}
        for record in self.instance_registry.values():
            status = record["status"]
            by_status[status] = by_status.get(status, 0) + 1
        return by_status

    def _find_orphaned_instances(self) -> List[Dict[str, Any]]:
        """Find potentially orphaned instances"""
        orphaned = []
        current_test = (
            self.current_test_context.get("test_name")
            if self.current_test_context
            else None
        )

        for nf_id, record in self.instance_registry.items():
            if (
                record["status"] == "active"
                and record["created_by"]["test_name"] != current_test
                and record["cleanup_policy"] == CleanupPolicy.TEST_END
            ):

                age_seconds = (
                    datetime.now() - record["created_by"]["timestamp"]
                ).total_seconds()

                orphaned.append(
                    {
                        "nfInstanceId": nf_id,
                        "created_by": record["created_by"]["test_name"],
                        "age_minutes": round(age_seconds / 60, 2),
                        "operations_count": len(record["operations"]),
                    }
                )

        return orphaned
