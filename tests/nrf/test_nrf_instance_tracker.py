"""
Unit tests for NRF Instance Tracker
"""

from datetime import datetime

import pytest

from testpilot.utils.nrf.instance_tracker import (
    CleanupPolicy,
    NRFInstanceTracker,
)


class TestNRFInstanceTracker:
    """Test cases for NRFInstanceTracker"""

    def setup_method(self):
        """Set up test environment before each test"""
        self.tracker = NRFInstanceTracker()
        self.test_context = {
            "test_name": "test_5_1_6_SMF_Registration",
            "sheet": "NRFRegistration",
            "row_idx": 21,
            "session_id": "NRFRegistration_test_5_1_6",
        }

    def test_initialization(self):
        """Test tracker initializes with empty state"""
        assert len(self.tracker.instance_registry) == 0
        assert len(self.tracker.active_stack) == 0
        assert self.tracker.current_test_context is None

    def test_handle_put_operation(self):
        """Test PUT operation creates and tracks instance"""
        nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"

        self.tracker.handle_put_operation(self.test_context, nf_id)

        # Verify instance is registered
        assert nf_id in self.tracker.instance_registry
        assert self.tracker.instance_registry[nf_id]["status"] == "active"
        assert (
            self.tracker.instance_registry[nf_id]["created_by"]["test_name"]
            == "test_5_1_6_SMF_Registration"
        )

        # Verify instance is on stack
        assert len(self.tracker.active_stack) == 1
        assert self.tracker.active_stack[0] == nf_id

    def test_get_active_instance_same_test(self):
        """Test GET operation retrieves correct instance for same test"""
        nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
        self.tracker.handle_put_operation(self.test_context, nf_id)

        # GET from same test should return same instance
        retrieved_id = self.tracker.get_active_instance_id(self.test_context)
        assert retrieved_id == nf_id

        # Verify operation was logged
        operations = self.tracker.instance_registry[nf_id]["operations"]
        assert len(operations) == 2  # PUT + GET/PATCH
        assert operations[1]["method"] == "GET/PATCH"

    def test_get_active_instance_different_test(self):
        """Test GET operation with different test uses top of stack"""
        nf_id1 = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
        nf_id2 = "7faf1bbc-6e4a-4454-a507-a14ef8e1bc5b"

        # Create first instance
        self.tracker.handle_put_operation(self.test_context, nf_id1)

        # Create second instance with different test
        different_context = self.test_context.copy()
        different_context["test_name"] = "test_5_1_7_UDR_Update"
        self.tracker.handle_put_operation(different_context, nf_id2)

        # GET from original test should still return first instance
        retrieved_id = self.tracker.get_active_instance_id(self.test_context)
        assert retrieved_id == nf_id1

        # GET from different test should return its instance
        retrieved_id = self.tracker.get_active_instance_id(different_context)
        assert retrieved_id == nf_id2

    def test_handle_delete_operation(self):
        """Test DELETE operation removes instance from stack"""
        nf_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
        self.tracker.handle_put_operation(self.test_context, nf_id)

        # DELETE should remove from stack
        deleted_id = self.tracker.handle_delete_operation(self.test_context)
        assert deleted_id == nf_id
        assert len(self.tracker.active_stack) == 0

        # Instance should be marked as deleted
        assert self.tracker.instance_registry[nf_id]["status"] == "deleted"
        assert (
            self.tracker.instance_registry[nf_id]["deletion_reason"]
            == "DELETE_OPERATION"
        )

    def test_complex_sequence(self):
        """Test complex PUT-GET-PUT-GET-DELETE-PUT sequence"""
        # PUT 1
        nf_id1 = "id-1"
        self.tracker.handle_put_operation(self.test_context, nf_id1)
        assert len(self.tracker.active_stack) == 1

        # GET 1
        assert self.tracker.get_active_instance_id(self.test_context) == nf_id1

        # PUT 2
        nf_id2 = "id-2"
        self.tracker.handle_put_operation(self.test_context, nf_id2)
        assert len(self.tracker.active_stack) == 2

        # GET 2 (should get most recent from same test)
        assert self.tracker.get_active_instance_id(self.test_context) == nf_id2

        # DELETE 2
        deleted = self.tracker.handle_delete_operation(self.test_context)
        assert deleted == nf_id2
        assert len(self.tracker.active_stack) == 1

        # PUT 3
        nf_id3 = "id-3"
        self.tracker.handle_put_operation(self.test_context, nf_id3)
        assert len(self.tracker.active_stack) == 2
        assert self.tracker.active_stack == [nf_id1, nf_id3]

    def test_cleanup_policy_determination(self):
        """Test cleanup policy is determined correctly"""
        # Registration test should get TEST_END policy
        registration_context = {
            "test_name": "test_5_1_6_registration_flow",
            "sheet": "NRFRegistration",
        }
        policy = self.tracker._determine_cleanup_policy(registration_context)
        assert policy == CleanupPolicy.TEST_END

        # Discovery test should get SUITE_END policy
        discovery_context = {
            "test_name": "test_5_2_3_discovery_request",
            "sheet": "NRFDiscovery",
        }
        policy = self.tracker._determine_cleanup_policy(discovery_context)
        assert policy == CleanupPolicy.SUITE_END

        # Other tests should get SESSION_END policy
        other_context = {
            "test_name": "test_functional_use_case",
            "sheet": "NRFFunctional",
        }
        policy = self.tracker._determine_cleanup_policy(other_context)
        assert policy == CleanupPolicy.SESSION_END

    def test_test_transition_cleanup(self):
        """Test automatic cleanup on test transition"""
        # Create instance with TEST_END policy
        nf_id1 = "id-1"
        self.tracker.track_test_progression(self.test_context)
        self.tracker.handle_put_operation(self.test_context, nf_id1)

        # Transition to new test
        new_test_context = self.test_context.copy()
        new_test_context["test_name"] = "test_5_1_7_new_test"
        self.tracker.track_test_progression(new_test_context)

        # First instance should be cleaned up
        assert self.tracker.instance_registry[nf_id1]["status"] == "deleted"
        assert (
            self.tracker.instance_registry[nf_id1]["deletion_reason"]
            == "auto_cleanup_test_end"
        )
        assert len(self.tracker.active_stack) == 0

    def test_diagnostic_report(self):
        """Test diagnostic report generation"""
        # Create some test data
        nf_id1 = "id-1"
        nf_id2 = "id-2"

        self.tracker.handle_put_operation(self.test_context, nf_id1)
        self.tracker.handle_put_operation(self.test_context, nf_id2)
        self.tracker.handle_delete_operation(self.test_context)  # Deletes id-2

        report = self.tracker.get_diagnostic_report()

        assert report["active_instances"] == 1
        assert report["active_instance_ids"] == [nf_id1]
        assert report["active_stack_size"] == 1
        assert report["total_instances_created"] == 2
        assert report["instances_by_status"]["active"] == 1
        assert report["instances_by_status"]["deleted"] == 1

    def test_orphaned_instance_detection(self):
        """Test detection of orphaned instances"""
        # Create instance in one test
        nf_id1 = "orphan-id"
        test1_context = {
            "test_name": "test_1",
            "sheet": "NRFRegistration",
            "row_idx": 1,
        }
        self.tracker.track_test_progression(test1_context)
        self.tracker.handle_put_operation(test1_context, nf_id1)

        # Move to different test without cleanup
        test2_context = {
            "test_name": "test_2",
            "sheet": "NRFRegistration",
            "row_idx": 2,
        }
        # Don't call track_test_progression to simulate missing cleanup
        self.tracker.current_test_context = test2_context

        # Check orphaned instances
        orphaned = self.tracker._find_orphaned_instances()
        assert len(orphaned) == 1
        assert orphaned[0]["nfInstanceId"] == nf_id1
        assert orphaned[0]["created_by"] == "test_1"

    def test_no_active_instance_returns_none(self):
        """Test GET/DELETE operations return None when no active instances"""
        # No instances created
        assert self.tracker.get_active_instance_id(self.test_context) is None
        assert self.tracker.handle_delete_operation(self.test_context) is None

    def test_cleanup_all_active_instances(self):
        """Test cleanup of all active instances"""
        # Create multiple instances
        nf_id1 = "id-1"
        nf_id2 = "id-2"
        nf_id3 = "id-3"

        self.tracker.handle_put_operation(self.test_context, nf_id1)
        self.tracker.handle_put_operation(self.test_context, nf_id2)
        self.tracker.handle_put_operation(self.test_context, nf_id3)

        assert len(self.tracker.active_stack) == 3

        # Cleanup all
        self.tracker.cleanup_all_active_instances(reason="test_cleanup")

        assert len(self.tracker.active_stack) == 0
        assert all(
            self.tracker.instance_registry[nf_id]["status"] == "deleted"
            for nf_id in [nf_id1, nf_id2, nf_id3]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
