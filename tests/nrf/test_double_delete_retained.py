"""
Test Double DELETE Scenario with Retained Instance IDs
"""

import logging
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from src.testpilot.utils.nrf.instance_tracker import NRFInstanceTracker

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestDoubleDeleteRetained(unittest.TestCase):
    """Test cases for double DELETE scenario with retention"""

    def setUp(self):
        """Set up test fixtures"""
        self.tracker = NRFInstanceTracker()

    def test_double_delete_retains_instance_id(self):
        """Test that second DELETE can still access the deleted instance ID"""
        test_context = {
            "test_name": "test_nf_registration",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }

        # 1. PUT - Create new instance
        nf_instance_id = "test-instance-123"
        self.tracker.handle_put_operation(test_context, nf_instance_id)

        # Verify instance is in active stack
        self.assertEqual(len(self.tracker.active_stack), 1)
        self.assertEqual(len(self.tracker.deleted_stack), 0)

        # 2. GET - Should use the active instance
        test_context["row_idx"] = 2
        active_id = self.tracker.get_active_instance_id(test_context)
        self.assertEqual(active_id, nf_instance_id)

        # 3. First DELETE - Should move to deleted stack
        test_context["row_idx"] = 3
        deleted_id = self.tracker.handle_delete_operation(test_context)
        self.assertEqual(deleted_id, nf_instance_id)

        # Verify instance moved from active to deleted stack
        self.assertEqual(len(self.tracker.active_stack), 0)
        self.assertEqual(len(self.tracker.deleted_stack), 1)
        self.assertEqual(self.tracker.deleted_stack[0], nf_instance_id)

        # 4. Second DELETE - Should still return the deleted instance ID
        test_context["row_idx"] = 4
        verify_id = self.tracker.handle_delete_operation(test_context)
        self.assertEqual(verify_id, nf_instance_id)

        # Deleted stack should still contain the instance
        self.assertEqual(len(self.tracker.deleted_stack), 1)

        # Check diagnostic report
        report = self.tracker.get_diagnostic_report()
        self.assertEqual(report["active_stack_size"], 0)
        self.assertEqual(report["deleted_stack_size"], 1)

    def test_cleanup_removes_deleted_instances(self):
        """Test that test cleanup removes instances from deleted stack"""
        test_context1 = {
            "test_name": "test_registration_1",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }

        # Create and delete an instance in test 1
        nf_id1 = "instance-1"
        self.tracker.handle_put_operation(test_context1, nf_id1)
        self.tracker.handle_delete_operation(test_context1)

        # Verify instance is in deleted stack
        self.assertEqual(len(self.tracker.deleted_stack), 1)

        # Transition to test 2
        test_context2 = {
            "test_name": "test_registration_2",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }
        self.tracker.track_test_progression(test_context1)
        self.tracker.track_test_progression(test_context2)

        # Deleted stack should be cleared after test transition
        self.assertEqual(len(self.tracker.deleted_stack), 0)

    def test_multiple_tests_with_double_deletes(self):
        """Test multiple tests each with double DELETE operations"""
        # Test 1: PUT-GET-DELETE-DELETE
        test1_context = {
            "test_name": "test_1",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }

        nf_id1 = "instance-test1"
        self.tracker.handle_put_operation(test1_context, nf_id1)

        # First DELETE
        test1_context["row_idx"] = 2
        delete1 = self.tracker.handle_delete_operation(test1_context)
        self.assertEqual(delete1, nf_id1)

        # Second DELETE (verification)
        test1_context["row_idx"] = 3
        delete2 = self.tracker.handle_delete_operation(test1_context)
        self.assertEqual(delete2, nf_id1)

        # Test 2: Another PUT-GET-DELETE-DELETE
        test2_context = {
            "test_name": "test_2",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }

        # Track test progression
        self.tracker.track_test_progression(test1_context)
        self.tracker.track_test_progression(test2_context)

        # Deleted stack should be cleared
        self.assertEqual(len(self.tracker.deleted_stack), 0)

        nf_id2 = "instance-test2"
        self.tracker.handle_put_operation(test2_context, nf_id2)

        # First DELETE
        test2_context["row_idx"] = 2
        delete1 = self.tracker.handle_delete_operation(test2_context)
        self.assertEqual(delete1, nf_id2)

        # Second DELETE
        test2_context["row_idx"] = 3
        delete2 = self.tracker.handle_delete_operation(test2_context)
        self.assertEqual(delete2, nf_id2)

    def test_session_cleanup_clears_all(self):
        """Test that session cleanup clears both active and deleted stacks"""
        test_context = {
            "test_name": "test_cleanup",
            "row_idx": 1,
            "sheet": "NRF_Tests",
        }

        # Create multiple instances
        for i in range(3):
            self.tracker.handle_put_operation(test_context, f"instance-{i}")

        # Delete some instances
        self.tracker.handle_delete_operation(test_context)
        self.tracker.handle_delete_operation(test_context)

        # Verify state before cleanup
        self.assertEqual(len(self.tracker.active_stack), 1)
        self.assertEqual(len(self.tracker.deleted_stack), 2)

        # Perform session cleanup
        self.tracker.cleanup_all_active_instances("session_end")

        # Both stacks should be empty
        self.assertEqual(len(self.tracker.active_stack), 0)
        self.assertEqual(len(self.tracker.deleted_stack), 0)


if __name__ == "__main__":
    unittest.main()
