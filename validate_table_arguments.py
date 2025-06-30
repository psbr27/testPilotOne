#!/usr/bin/env python3
"""
Table Arguments Validation Script
Validates that all required fields are properly populated before being passed to LiveProgressTable
"""

import sys
import logging
from typing import Any, Dict, List
from dataclasses import fields

# Add current directory to path to import modules
sys.path.insert(0, '.')

from test_result import TestResult, TestStep, TestFlow
from console_table_fmt import LiveProgressTable


def validate_test_result_fields(test_result: Any) -> Dict[str, Any]:
    """Validate that a test result object has all required fields for table display."""
    
    validation_results = {
        "valid": True,
        "missing_fields": [],
        "empty_fields": [],
        "field_values": {},
        "issues": []
    }
    
    # Required fields for table display
    required_fields = ["host", "sheet", "test_name", "method", "passed", "duration"]
    
    for field_name in required_fields:
        if hasattr(test_result, field_name):
            value = getattr(test_result, field_name, None)
            validation_results["field_values"][field_name] = value
            
            # Check if field is empty or None
            if value is None or (isinstance(value, str) and value.strip() == ""):
                validation_results["empty_fields"].append(field_name)
                validation_results["valid"] = False
                validation_results["issues"].append(f"Field '{field_name}' is empty or None")
        else:
            validation_results["missing_fields"].append(field_name)
            validation_results["valid"] = False
            validation_results["issues"].append(f"Field '{field_name}' is missing")
    
    # Check additional optional fields that are commonly used
    optional_fields = ["command", "result", "output", "error", "fail_reason"]
    for field_name in optional_fields:
        if hasattr(test_result, field_name):
            value = getattr(test_result, field_name, None)
            validation_results["field_values"][field_name] = value
    
    return validation_results


def create_sample_test_results() -> List[Any]:
    """Create sample test result objects to test validation."""
    
    # Sample 1: Proper TestResult object
    test_result_1 = TestResult(
        sheet="TestSheet1",
        row_idx=1,
        host="test-host-1",
        command="curl -X GET https://api.example.com/users",
        output='{"users": []}',
        error="",
        expected_status=200,
        actual_status=200,
        pattern_match=None,
        pattern_found=None,
        passed=True,
        fail_reason=None,
        test_name="User API Test",
        duration=1.25,
        method="GET"
    )
    
    # Sample 2: Failed test result
    test_result_2 = TestResult(
        sheet="TestSheet2",
        row_idx=5,
        host="test-host-2",
        command="curl -X POST https://api.example.com/login",
        output="",
        error="Connection refused",
        expected_status=200,
        actual_status=None,
        pattern_match=None,
        pattern_found=None,
        passed=False,
        fail_reason="Connection refused",
        test_name="Login API Test",
        duration=0.5,
        method="POST"
    )
    
    # Sample 3: Object with missing method (simulating the bug)
    class IncompleteResult:
        def __init__(self):
            self.sheet = "TestSheet3"
            self.host = "test-host-3"
            self.test_name = "Incomplete Test"
            self.passed = False
            self.duration = 2.0
            # Missing 'method' field
    
    incomplete_result = IncompleteResult()
    
    # Sample 4: Dry run result (converted from dict)
    dry_run_dict = {
        "sheet": "DryRunSheet",
        "test_name": "Dry Run Test",
        "host": "dry-host",
        "duration": 0.0,
        "result": "DRY-RUN",
        "command": "curl -X GET https://api.example.com/status",
        "method": "GET"
    }
    
    # Convert to object (like _convert_to_result_object does)
    dry_run_result = type(
        "DryRunResult",
        (),
        {
            "sheet": dry_run_dict["sheet"],
            "test_name": dry_run_dict["test_name"],
            "host": dry_run_dict["host"],
            "passed": False,
            "duration": dry_run_dict["duration"],
            "result": dry_run_dict["result"],
            "command": dry_run_dict["command"],
            "method": dry_run_dict["method"],
        },
    )()
    
    return [test_result_1, test_result_2, incomplete_result, dry_run_result]


def test_live_progress_table():
    """Test the LiveProgressTable with various test result objects."""
    
    print("🔍 Testing LiveProgressTable with various test result objects...\n")
    
    # Create sample test results
    test_results = create_sample_test_results()
    
    # Test each result
    for i, test_result in enumerate(test_results, 1):
        print(f"--- Test Result {i}: {type(test_result).__name__} ---")
        
        # Validate fields
        validation = validate_test_result_fields(test_result)
        
        print(f"Valid: {validation['valid']}")
        if validation['missing_fields']:
            print(f"Missing fields: {validation['missing_fields']}")
        if validation['empty_fields']:
            print(f"Empty fields: {validation['empty_fields']}")
        if validation['issues']:
            print("Issues:")
            for issue in validation['issues']:
                print(f"  - {issue}")
        
        print("Field values:")
        for field, value in validation['field_values'].items():
            print(f"  {field}: {repr(value)}")
        
        # Test with LiveProgressTable
        print("Testing with LiveProgressTable:")
        try:
            table = LiveProgressTable()
            table.add_result(test_result)
            print("  ✅ Successfully added to table")
        except Exception as e:
            print(f"  ❌ Error adding to table: {e}")
        
        print()


def test_dataclass_consistency():
    """Test that TestResult dataclass is consistent with table requirements."""
    
    print("🔍 Testing TestResult dataclass consistency...\n")
    
    # Get all fields from TestResult dataclass
    test_result_fields = [field.name for field in fields(TestResult)]
    print(f"TestResult fields: {test_result_fields}")
    
    # Required fields for table
    table_required_fields = ["host", "sheet", "test_name", "method", "passed", "duration"]
    
    missing_in_dataclass = []
    for field in table_required_fields:
        if field not in test_result_fields:
            missing_in_dataclass.append(field)
    
    if missing_in_dataclass:
        print(f"❌ Missing fields in TestResult dataclass: {missing_in_dataclass}")
    else:
        print("✅ All required fields are present in TestResult dataclass")
    
    print(f"Table required fields: {table_required_fields}")
    print()


def main():
    """Run all validation tests."""
    
    print("=" * 80)
    print("TESTPILOT TABLE ARGUMENTS VALIDATION")
    print("=" * 80)
    print()
    
    # Test dataclass consistency
    test_dataclass_consistency()
    
    # Test live progress table
    test_live_progress_table()
    
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()