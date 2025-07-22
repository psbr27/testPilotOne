"""
Unit tests for NRF Sequence Manager
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from testpilot.utils.nrf import sequence_manager
from testpilot.utils.nrf.sequence_manager import (
    _extract_nf_instance_id,
    _legacy_nrf_handling,
    cleanup_all_sessions,
    cleanup_session,
    get_global_diagnostic_report,
    get_or_create_session_manager,
    get_session_diagnostic_report,
    handle_nrf_operation,
)


class TestNRFSequenceManager:
    """Test cases for NRF Sequence Manager"""

    def setup_method(self):
        """Set up test environment before each test"""
        # Clear global session managers
        sequence_manager._session_managers.clear()

        self.test_context = {
            "test_name": "test_5_1_6_SMF_Registration",
            "sheet": "NRFRegistration",
            "row_idx": 21,
            "session_id": "test_session_1",
        }

        self.nf_instance_id = "6faf1bbc-6e4a-4454-a507-a14ef8e1bc5a"
        self.test_payload = json.dumps(
            {
                "nfInstanceId": self.nf_instance_id,
                "nfType": "SMF",
                "nfStatus": "REGISTERED",
            }
        )

    def test_get_or_create_session_manager(self):
        """Test session manager creation and retrieval"""
        # First call should create new manager
        manager1 = get_or_create_session_manager("session1")
        assert "session1" in sequence_manager._session_managers

        # Second call should return same manager
        manager2 = get_or_create_session_manager("session1")
        assert manager1 is manager2

        # Different session should create new manager
        manager3 = get_or_create_session_manager("session2")
        assert manager3 is not manager1
        assert len(sequence_manager._session_managers) == 2

    def test_handle_nrf_operation_put(self):
        """Test handle_nrf_operation for PUT method"""
        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

        result = handle_nrf_operation(
            url=url,
            method="PUT",
            payload=self.test_payload,
            test_context=self.test_context,
            nf_name="NRF",
        )

        # Should return URL with nfInstanceId appended
        expected_url = f"{url}{self.nf_instance_id}"
        assert result == expected_url

        # Verify instance is tracked
        manager = get_or_create_session_manager(
            self.test_context["session_id"]
        )
        assert len(manager.active_stack) == 1
        assert manager.active_stack[0] == self.nf_instance_id

    def test_handle_nrf_operation_get(self):
        """Test handle_nrf_operation for GET method"""
        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

        # First PUT to create instance
        handle_nrf_operation(
            url=url,
            method="PUT",
            payload=self.test_payload,
            test_context=self.test_context,
            nf_name="NRF",
        )

        # Then GET should use same instance
        result = handle_nrf_operation(
            url=url,
            method="GET",
            payload=None,
            test_context=self.test_context,
            nf_name="NRF",
        )

        expected_url = f"{url}{self.nf_instance_id}"
        assert result == expected_url

    def test_handle_nrf_operation_delete(self):
        """Test handle_nrf_operation for DELETE method"""
        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

        # PUT to create instance
        handle_nrf_operation(
            url=url,
            method="PUT",
            payload=self.test_payload,
            test_context=self.test_context,
            nf_name="NRF",
        )

        # DELETE should remove instance
        result = handle_nrf_operation(
            url=url,
            method="DELETE",
            payload=None,
            test_context=self.test_context,
            nf_name="NRF",
        )

        expected_url = f"{url}{self.nf_instance_id}"
        assert result == expected_url

        # Verify instance is removed from stack
        manager = get_or_create_session_manager(
            self.test_context["session_id"]
        )
        assert len(manager.active_stack) == 0

    def test_handle_nrf_operation_no_context(self):
        """Test handle_nrf_operation falls back to legacy when no context"""
        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

        result = handle_nrf_operation(
            url=url,
            method="PUT",
            payload=self.test_payload,
            test_context=None,  # No context
            nf_name="NRF",
        )

        # Should use legacy handling
        expected_url = f"{url}{self.nf_instance_id}"
        assert result == expected_url

        # No session manager should be created
        assert len(sequence_manager._session_managers) == 0

    def test_extract_nf_instance_id_from_dict(self):
        """Test extracting nfInstanceId from dict payload"""
        # Direct nfInstanceId
        payload = json.dumps({"nfInstanceId": "test-id-123"})
        assert _extract_nf_instance_id(payload) == "test-id-123"

        # Nested in nfProfile
        payload = json.dumps({"nfProfile": {"nfInstanceId": "nested-id-456"}})
        assert _extract_nf_instance_id(payload) == "nested-id-456"

        # No nfInstanceId
        payload = json.dumps({"nfType": "SMF"})
        assert _extract_nf_instance_id(payload) is None

    def test_extract_nf_instance_id_from_list(self):
        """Test extracting nfInstanceId from list payload"""
        payload = json.dumps(
            [
                {"nfType": "SMF"},
                {"nfInstanceId": "list-id-789"},
                {"nfType": "UDR"},
            ]
        )
        assert _extract_nf_instance_id(payload) == "list-id-789"

        # Empty list
        payload = json.dumps([])
        assert _extract_nf_instance_id(payload) is None

    def test_extract_nf_instance_id_invalid_json(self):
        """Test extracting nfInstanceId from invalid JSON"""
        assert _extract_nf_instance_id("not-json") is None
        assert _extract_nf_instance_id(None) is None
        assert _extract_nf_instance_id("") is None

    def test_legacy_nrf_handling(self):
        """Test legacy NRF handling function"""
        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"
        payload = json.dumps({"nfInstanceId": "legacy-id"})

        result = _legacy_nrf_handling(url, "PUT", payload)
        assert result == f"{url}legacy-id"

        # No payload
        assert _legacy_nrf_handling(url, "PUT", None) is None

        # Invalid JSON
        assert _legacy_nrf_handling(url, "PUT", "invalid-json") is None

    def test_cleanup_session(self):
        """Test cleaning up specific session"""
        # Create two sessions
        manager1 = get_or_create_session_manager("session1")
        manager2 = get_or_create_session_manager("session2")

        # Add instances to both
        manager1.handle_put_operation(self.test_context, "id-1")
        manager2.handle_put_operation(self.test_context, "id-2")

        # Cleanup session1
        cleanup_session("session1")

        # Session1 should be removed
        assert "session1" not in sequence_manager._session_managers
        assert "session2" in sequence_manager._session_managers

    def test_cleanup_all_sessions(self):
        """Test cleaning up all sessions"""
        # Create multiple sessions
        get_or_create_session_manager("session1")
        get_or_create_session_manager("session2")
        get_or_create_session_manager("session3")

        assert len(sequence_manager._session_managers) == 3

        # Cleanup all
        cleanup_all_sessions()

        assert len(sequence_manager._session_managers) == 0

    def test_get_session_diagnostic_report(self):
        """Test getting diagnostic report for specific session"""
        # Create session and add instances
        handle_nrf_operation(
            url="http://nrf:8081/",
            method="PUT",
            payload=self.test_payload,
            test_context=self.test_context,
            nf_name="NRF",
        )

        report = get_session_diagnostic_report(self.test_context["session_id"])

        assert report is not None
        assert report["active_instances"] == 1
        assert report["total_instances_created"] == 1

        # Non-existent session
        assert get_session_diagnostic_report("non-existent") is None

    def test_get_global_diagnostic_report(self):
        """Test getting global diagnostic report"""
        # Create multiple sessions with instances
        context1 = self.test_context.copy()
        context1["session_id"] = "session1"

        context2 = self.test_context.copy()
        context2["session_id"] = "session2"

        handle_nrf_operation(
            url="http://nrf:8081/",
            method="PUT",
            payload=self.test_payload,
            test_context=context1,
            nf_name="NRF",
        )

        handle_nrf_operation(
            url="http://nrf:8081/",
            method="PUT",
            payload=json.dumps({"nfInstanceId": "id-2"}),
            test_context=context2,
            nf_name="NRF",
        )

        report = get_global_diagnostic_report()

        assert report["total_sessions"] == 2
        assert "session1" in report["sessions"]
        assert "session2" in report["sessions"]
        assert report["global_stats"]["total_active_instances"] == 2
        assert report["global_stats"]["total_instances_created"] == 2

    def test_complex_multi_session_scenario(self):
        """Test complex scenario with multiple sessions and operations"""
        # Session 1: PUT-GET-DELETE
        context1 = {
            "session_id": "sess1",
            "test_name": "test1",
            "sheet": "NRF",
            "row_idx": 1,
        }
        payload1 = json.dumps({"nfInstanceId": "id-sess1"})

        url = "http://nrf:8081/nnrf-nfm/v1/nf-instances/"

        # PUT
        result = handle_nrf_operation(url, "PUT", payload1, context1, "NRF")
        assert result == f"{url}id-sess1"

        # GET
        result = handle_nrf_operation(url, "GET", None, context1, "NRF")
        assert result == f"{url}id-sess1"

        # DELETE
        result = handle_nrf_operation(url, "DELETE", None, context1, "NRF")
        assert result == f"{url}id-sess1"

        # Session 2: PUT-PUT-GET
        context2 = {
            "session_id": "sess2",
            "test_name": "test2",
            "sheet": "NRF",
            "row_idx": 2,
        }
        payload2a = json.dumps({"nfInstanceId": "id-sess2-a"})
        payload2b = json.dumps({"nfInstanceId": "id-sess2-b"})

        # PUT first
        handle_nrf_operation(url, "PUT", payload2a, context2, "NRF")

        # PUT second
        handle_nrf_operation(url, "PUT", payload2b, context2, "NRF")

        # GET should return most recent
        result = handle_nrf_operation(url, "GET", None, context2, "NRF")
        assert result == f"{url}id-sess2-b"

        # Verify global state
        report = get_global_diagnostic_report()
        assert report["total_sessions"] == 2
        assert report["sessions"]["sess1"]["active_instances"] == 0  # Deleted
        assert (
            report["sessions"]["sess2"]["active_instances"] == 2
        )  # Both still active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
